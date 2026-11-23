"""Stream complete current components through certificates and exact WGS84 search."""

from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike

from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.land.certificates import CertificateIndex
from worldatlas.map_build.land.exact_search import ExactIndex


def positions(ids: np.ndarray, roots: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Find selected component IDs in a sorted reference array.

    Args:
        ids: Component IDs to check.
        roots: Sorted IDs of the components being assigned.

    Returns:
        (positions, found), with the insertion index and a bool match flag
        for each input ID.
    """
    if not len(roots):
        return np.zeros(len(ids), dtype=np.int64), np.zeros(len(ids), dtype=bool)
    pos = np.searchsorted(roots, ids)
    safe = np.minimum(pos, len(roots) - 1)
    return pos, (pos < len(roots)) & (roots[safe] == ids)


def blocks(
    path: Path | str,
    cursor: int = 0,
    block_records: int = 100000,
    guard: Callable[[], None] = check_cancelled,
) -> Iterator[tuple[int, np.ndarray]]:
    """Read component runs without loading the entire file at once.

    Args:
        path: Little-endian uint32 component run file.
        cursor: First run record index to read.
        block_records: Maximum records to read together.
        guard: Cancellation callback before each read.

    Yields:
        (first_record, array), with N-by-3 records of (start, end, component_id).

    Raises:
        ValueError: The cursor or file length is invalid.
    """
    size = Path(path).stat().st_size
    if size % 12 or cursor < 0 or cursor > size // 12 or block_records < 1:
        raise ValueError("invalid component stream/cursor")
    off = cursor
    with open(path, "rb") as f:
        f.seek(cursor * 12)
        while True:
            guard()
            b = f.read(block_records * 12)
            if not b:
                break
            if len(b) % 12:
                raise ValueError("truncated component runs")
            a = np.frombuffer(b, dtype="<u4").reshape(-1, 3)
            yield off, a
            off += len(a)


def first_points(
    path: Path | str,
    co: np.ndarray,
    roots: ArrayLike,
    width: int,
    guard: Callable[[], None] = check_cancelled,
) -> tuple[np.ndarray, np.ndarray]:
    """Find the first cell of each selected component.

    Args:
        path: Component run file.
        co: Row offsets into the run file.
        roots: Component IDs to locate.
        width: Number of columns.
        guard: Cancellation callback.

    Returns:
        Arrays of row and column indices in component order.
    """
    roots = np.asarray(roots, dtype=np.uint32)
    ys = np.full(len(roots), -1, dtype=np.int32)
    xs = np.full(len(roots), -1, dtype=np.int64)
    last = 0
    for off, a in blocks(path, guard=guard):
        if np.any(a[:, 0] >= a[:, 1]) or np.any(a[:, 1] > width):
            raise ValueError("invalid component run")
        pos, match = positions(a[:, 2], roots)
        ix = np.flatnonzero(match)
        if len(ix):
            ids, first = np.unique(pos[ix], return_index=True)
            pick = ix[first]
            unset = ys[ids] < 0
            ids = ids[unset]
            pick = pick[unset]
            ys[ids] = (np.searchsorted(co, off + pick, side="right") - 1).astype(
                np.int32
            )
            xs[ids] = a[pick, 0]
        last = off + len(a)
    if last != int(co[-1]) or np.any(ys < 0) or np.any(ys >= len(co) - 1):
        raise ValueError("incomplete component coverage")
    return ys, xs


def component_witnesses(
    path: Path | str,
    co: np.ndarray,
    roots: np.ndarray,
    width: int,
    index: CertificateIndex,
    hints: np.ndarray,
    guard: Callable[[], None] = check_cancelled,
) -> np.ndarray:
    """Tighten distance bounds using actual cells in the selected components.

    Args:
        path: Component run file.
        co: Row offsets into the run file.
        roots: Selected component IDs.
        width: Grid width in cells.
        index: Index of representative reference cells.
        hints: Candidate owner per selected component.
        guard: Cancellation callback.

    Returns:
        1-D array with one distance bound in metres per selected component.
    """
    roots = np.asarray(roots, dtype=np.uint32)
    hints = np.asarray(hints, dtype=np.uint32)
    if hints.shape != roots.shape or np.any(~np.isin(hints, index.codes)):
        raise ValueError("invalid witness hints")
    upper = np.full(len(roots), np.inf)
    last = 0
    for off, a in blocks(path, guard=guard):
        if np.any(a[:, 0] >= a[:, 1]) or np.any(a[:, 1] > width):
            raise ValueError("invalid component run")
        pos, match = positions(a[:, 2], roots)
        ix = np.flatnonzero(match)
        wide = ix[a[ix, 1] - a[ix, 0] > 1]
        chosen = np.r_[ix, wide]
        cols = np.r_[a[ix, 0], a[wide, 1] - 1]
        for start in range(0, len(chosen), 8192):
            guard()
            selected = chosen[start : start + 8192]
            p = pos[selected]
            rows = np.searchsorted(co, off + selected, side="right") - 1
            if np.any((rows < 0) | (rows >= len(co) - 1)):
                raise ValueError("invalid witness row")
            distances, _ = index.witnesses(rows, cols[start : start + 8192], hints[p])
            if (
                np.asarray(distances).shape != p.shape
                or np.any(~np.isfinite(distances))
                or np.any(distances < 0)
            ):
                raise ValueError("invalid WGS84 witness bound")
            np.minimum.at(upper, p, distances)
        last = off + len(a)
    if last != int(co[-1]) or np.any(~np.isfinite(upper)):
        raise ValueError("incomplete component witness coverage")
    return upper


def oversized_run_queries(
    a: np.ndarray,
    base: int,
    co: np.ndarray,
    pos: np.ndarray,
    index: int,
    chunk: int,
    max_queries: int,
) -> Iterator[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Split one long component run into batches of smaller query intervals.

    Args:
        a: Block of component run records.
        base: Index of the block's first record in the file.
        co: Row offsets into the run file.
        pos: Index of each input run's component in the selected roots.
        index: Run index within the block.
        chunk: Maximum length of a query interval, in cells.
        max_queries: Number of intervals to emit together.

    Yields:
        Arrays of rows, first columns, end columns and component positions.
    """
    start = int(a[index, 0])
    end = int(a[index, 1])
    row = int(np.searchsorted(co, base + index, side="right") - 1)
    root_position = int(pos[index])
    while start < end:
        n = min(max_queries, (end - start + chunk - 1) // chunk)
        starts = start + np.arange(n, dtype=np.int64) * chunk
        ends = np.minimum(starts + chunk, end)
        yield (
            np.full(n, row, dtype=np.int32),
            starts,
            ends,
            np.full(n, root_position, dtype=np.int64),
        )
        start = int(ends[-1])


def expanded(
    a: np.ndarray,
    base: int,
    co: np.ndarray,
    roots: np.ndarray,
    chunk: int = 1024,
    max_queries: int = 65536,
    *,
    ambiguous: np.ndarray | None = None,
) -> Iterator[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Split the selected runs into bounded length query intervals.

    Args:
        a: N-by-3 block of component runs.
        base: Index of the first record in the file.
        co: Row offsets into the run file.
        roots: Sorted component IDs to search.
        chunk: Maximum length of each interval in cells.
        max_queries: Number of intervals to process per batch.
        ambiguous: Optional mask limiting queries to unresolved components.

    Yields:
        Arrays of rows, first columns, end columns and selected component positions.
    """
    if not (1 <= chunk <= 1024 and max_queries >= 128):
        raise ValueError("invalid query chunk")
    if np.any(a[:, 0] >= a[:, 1]):
        raise ValueError("bad component interval")
    pos, match = positions(a[:, 2], roots)
    idx = np.flatnonzero(match)
    if ambiguous is not None:
        idx = idx[ambiguous[pos[idx]]]
    lengths = a[idx, 1].astype(np.int64) - a[idx, 0].astype(np.int64)
    counts = (lengths + chunk - 1) // chunk
    cumulative = np.r_[0, np.cumsum(counts)]
    first = 0
    # Process entire input block; each yielded query group is bounded.
    while first < len(idx):
        if counts[first] > max_queries:
            yield from oversized_run_queries(
                a, base, co, pos, int(idx[first]), chunk, max_queries
            )
            first += 1
            continue
        # Choose the last whole run whose intervals fit in this batch.
        limit = cumulative[first] + max_queries
        stop = int(np.searchsorted(cumulative, limit, side="right")) - 1
        sizes = counts[first:stop]
        chosen = np.repeat(idx[first:stop], sizes)
        within = np.arange(cumulative[first], cumulative[stop]) - np.repeat(
            cumulative[first:stop], sizes
        )
        start = a[chosen, 0].astype(np.int64) + within * chunk
        end = np.minimum(a[chosen, 1].astype(np.int64), start + chunk)
        rows = np.searchsorted(co, base + chosen, side="right") - 1
        yield (
            rows.astype(np.int32),
            start,
            end,
            pos[chosen],
        )
        first = stop


def certificate_pass(
    path: Path | str,
    co: np.ndarray,
    roots: np.ndarray,
    index: CertificateIndex,
    upper: np.ndarray,
    hints: np.ndarray,
    amb: np.ndarray,
    cursor: int = 0,
    chunk: int = 1024,
    guard: Callable[[], None] = check_cancelled,
    progress: Callable[..., None] = lambda *x: None,
    block_records: int = 100000,
) -> tuple[np.ndarray, int, int]:
    """Try to prove the candidate owner for every run of each component.

    Args:
        path: Component run file.
        co: Row offsets into the run file.
        roots: Sorted IDs of the selected components.
        index: Index for bounding distances to reference cells.
        upper: Measured upper distance bound per component, in metres.
        hints: Candidate owner per component.
        amb: Bool array to mark when a component needs exact search.
        cursor: First run record index to read.
        chunk: Maximum size of an interval, in cells.
        guard: Cancellation callback.
        progress: Optional progress callback.
        block_records: Input run records per read.

    Returns:
        (ambiguity_mask, tested_interval_count, end_record_index).
    """
    roots = np.asarray(roots, dtype=np.uint32)
    upper = np.asarray(upper, dtype=float)
    hints = np.asarray(hints, dtype=np.uint32)
    if (
        len(upper) != len(roots)
        or len(hints) != len(roots)
        or len(amb) != len(roots)
        or np.any(~np.isfinite(upper))
        or np.any(upper < 0)
    ):
        raise ValueError("bad certificate state")
    count = 0
    endcursor = cursor
    for off, a in blocks(path, cursor, block_records, guard):
        for y, x, z, p in expanded(a, off, co, roots, chunk):
            good = index.certify_runs(y, x, z, upper[p], hints[p])
            np.logical_or.at(amb, p, ~good)
            count += len(p)
        endcursor = off + len(a)
        progress(endcursor, count, amb)
    if endcursor != int(co[-1]):
        raise ValueError("incomplete certificate stream")
    return amb, count, endcursor


def exact_pass(
    path: Path | str,
    co: np.ndarray,
    roots: np.ndarray,
    index: ExactIndex,
    hints: np.ndarray,
    amb: np.ndarray,
    best: np.ndarray,
    cursor: int = 0,
    chunk: int = 1024,
    guard: Callable[[], None] = check_cancelled,
    progress: Callable[..., None] = lambda *x: None,
    block_records: int = 10000,
) -> tuple[np.ndarray, int, int]:
    """Find exact WGS84 distance minima for the components still unresolved.

    Args:
        path: Component run file.
        co: Row offsets into the run file.
        roots: Sorted component IDs.
        index: Complete reference run index.
        hints: Candidate owners.
        amb: Bool array marking components needing exact distances.
        best: Component-by-owner distance minima to update, in metres.
        cursor: First input run record to process.
        chunk: Maximum query interval length in cells.
        guard: Cancellation callback.
        progress: Optional progress callback.
        block_records: Input run records per read.

    Returns:
        (distance_minima, tested_interval_count, end_record_index).
    """
    roots = np.asarray(roots, dtype=np.uint32)
    hints = np.asarray(hints, dtype=np.uint32)
    amb = np.asarray(amb, dtype=bool)
    if (
        len(hints) != len(roots)
        or len(amb) != len(roots)
        or best.shape != (len(roots), len(index.codes))
    ):
        raise ValueError("bad exact state")
    columns, found = positions(hints, np.asarray(index.codes, dtype=np.uint32))
    if not found.all() or not np.isfinite(best[np.arange(len(roots)), columns]).all():
        raise ValueError("missing real upper witness")
    count = 0
    endcursor = cursor
    for off, a in blocks(path, cursor, block_records, guard):
        for ys, xs, ends, pos in expanded(a, off, co, roots, chunk, ambiguous=amb):
            for i in range(len(pos)):
                guard()
                p = int(pos[i])
                upper = float(np.min(best[p]))
                ds, _ = index.nearest_run(int(ys[i]), int(xs[i]), int(ends[i]), upper)
                for code, d in ds.items():
                    if code not in index.codes or not np.isfinite(d) or d < 0:
                        raise ValueError("invalid exact distance")
                    column = index.codes.index(code)
                    best[p, column] = min(best[p, column], d)
                count += 1
        endcursor = off + len(a)
        progress(endcursor, count, best)
    if endcursor != int(co[-1]):
        raise ValueError("incomplete exact stream")
    return best, count, endcursor


def finalize(
    hints: np.ndarray,
    amb: np.ndarray,
    best: np.ndarray,
    category_codes: ArrayLike,
    *,
    priority_codes: Sequence[int] | None = None,
) -> np.ndarray:
    """Keep proven owners and choose the shortest exact distance for the rest.

    Args:
        hints: Initial owner code per component.
        amb: Bool array marking components that need exact results.
        best: Component-by-owner matrix of measured distances in metres.
        category_codes: Owner codes in the order of the distance columns.
        priority_codes: Optional tie order. The first owner wins when the
            measured distances are equal.

    Returns:
        Owner code array in component order.

    Raises:
        ValueError: The inputs disagree or an unresolved component has no distance.
    """
    hints = np.asarray(hints, dtype=np.uint32)
    amb = np.asarray(amb, dtype=bool)
    categories = np.asarray(category_codes, dtype=np.uint32)
    if (
        best.shape != (len(hints), len(categories))
        or len(amb) != len(hints)
        or not len(categories)
        or np.any(categories[1:] <= categories[:-1])
    ):
        raise ValueError("invalid final state")
    codes = hints.copy()
    if priority_codes is None:
        order = np.arange(len(categories))
    else:
        priority = [
            int(code) for code in priority_codes if code in set(map(int, categories))
        ]
        if len(priority) != len(categories) or set(priority) != set(
            map(int, categories)
        ):
            raise ValueError("tie order must cover every reference owner once")
        order = np.searchsorted(categories, priority)
    positions = np.flatnonzero(amb)
    if len(positions):
        values = best[positions][:, order]
        winners = np.argmin(values, axis=1)
        if not np.all(np.isfinite(values[np.arange(len(positions)), winners])):
            raise ValueError("no WGS84 witness")
        codes[positions] = categories[order[winners]]
    return codes
