"""Compare complete grids and retain the exact locations of changed cells."""

import time
from collections import Counter
from collections.abc import Iterable
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.inputs.selection_types import MapCodeBinding
from worldatlas.shared.files import sha256_file, write_json


def reference_lookup(
    reference_bindings: Iterable[MapCodeBinding],
    candidate_bindings: Iterable[MapCodeBinding],
) -> tuple[np.ndarray, np.ndarray] | None:
    """Match reference codes to candidate codes by owner and physical class.

    Args:
        reference_bindings: Reference records with code, entity_id and
            physical_class.
        candidate_bindings: Candidate records with the same fields.

    Returns:
        None when the code meanings already match. Otherwise, return
        (old_codes, new_codes) as sorted uint32 keys and int64 values.
        A missing match has value -1.
    """

    def by_code(bindings: Iterable[MapCodeBinding]) -> dict[int, tuple[int, str]]:
        """Index the meaning of every code.

        Args:
            bindings: Code, entity ID and class records.

        Returns:
            Map from each code to (entity_id, physical_class).
        """
        return {b["code"]: (b["entity_id"], b["physical_class"]) for b in bindings}

    reference = by_code(reference_bindings)
    candidate = by_code(candidate_bindings)
    if reference == candidate:
        return None
    candidate_codes = {category: code for code, category in candidate.items()}
    codes = sorted(reference)
    return (
        np.asarray([0, *codes], dtype=np.uint32),
        np.asarray(
            [0, *(candidate_codes.get(reference[c], -1) for c in codes)],
            dtype=np.int64,
        ),
    )


def comparable_codes(
    codes: np.ndarray, lookup: tuple[np.ndarray, np.ndarray] | None
) -> np.ndarray:
    """Translate one array of reference codes into candidate codes.

    Args:
        codes: Codes to look up.
        lookup: Lookup from reference_lookup.

    Returns:
        Array of the same shape, returning codes itself if lookup is None.

    Raises:
        ValueError: A reference code is missing from the lookup.
    """
    if lookup is None:
        return codes
    keys, translated = lookup
    indices = np.searchsorted(keys, codes)
    if np.any(indices == len(keys)) or np.any(keys[indices] != codes):
        raise ValueError("reference grid uses an unknown map category code")
    return translated[indices]


def compare(
    candidate: Path | str,
    reference: Path | str,
    grid: Grid,
    directory: Path | str,
    reference_sha256: dict[str, str],
    *,
    candidate_sha256: dict[str, str],
    reference_bindings: Iterable[MapCodeBinding] | None = None,
    candidate_bindings: Iterable[MapCodeBinding] | None = None,
) -> dict[str, Any]:
    """Compare every cell in two grids and write the changed spans.

    Args:
        candidate: Directory with the new grid.
        reference: Directory with the baseline grid.
        grid: Shared grid dimensions.
        directory: New directory for the comparison files.
        reference_sha256: Verified digests for the reference rows and runs.
        candidate_sha256: Verified digests for the candidate rows and runs.
        reference_bindings: Optional code meanings for the reference.
        candidate_bindings: Code meanings for the candidate, required when
            reference meanings are supplied.

    Returns:
        Report dictionary with counts by transition, changed bounds, input
        hashes and elapsed seconds. The binary change file stores uint32
        (row, first_column, end_column, old_code, new_code) records.

    Raises:
        ValueError: A grid or lookup is invalid or a file changes.
    """
    candidate, reference, directory = map(Path, (candidate, reference, directory))
    if (reference_bindings is None) != (candidate_bindings is None):
        raise ValueError("both category mappings are required to compare assignments")
    lookup = None
    if reference_bindings is not None and candidate_bindings is not None:
        lookup = reference_lookup(reference_bindings, candidate_bindings)
    names = ("rows.u32le", "runs.u32le")
    if set(reference_sha256) != set(names) or set(candidate_sha256) != set(names):
        raise ValueError("both stream checksums are required for each grid")
    start = time.monotonic()
    before = {"reference": reference_sha256, "candidate": candidate_sha256}
    changed, transitions, offsets = 0, Counter(), [0]
    bounds = None
    with ExitStack() as files:
        new = files.enter_context(open_grid(candidate, grid))
        old = files.enter_context(open_grid(reference, grid))
        directory.mkdir()
        stream = files.enter_context((directory / "changes.u32le").open("xb"))
        for y in range(grid.height):
            a, b = row(old, y, grid.width), row(new, y, grid.width)
            translated = comparable_codes(a[1], lookup)
            records = []
            if not (np.array_equal(a[0], b[0]) and np.array_equal(translated, b[1])):
                ends = np.union1d(a[0], b[0])
                starts = np.r_[np.uint32(0), ends[:-1]]
                ai = np.searchsorted(a[0], starts, side="right")
                av = a[1][ai]
                bv = b[1][np.searchsorted(b[0], starts, side="right")]
                for i in np.flatnonzero(translated[ai] != bv):
                    left, right, prior, after = map(
                        int, (starts[i], ends[i], av[i], bv[i])
                    )
                    count = right - left
                    changed += count
                    transitions[f"{prior}->{after}"] += count
                    records.append((y, left, right, prior, after))
                    if bounds is None:
                        bounds = [left, right, y, y + 1]
                    else:
                        bounds = [
                            min(bounds[0], left),
                            max(bounds[1], right),
                            bounds[2],
                            y + 1,
                        ]
            np.asarray(records, dtype="<u4").tofile(stream)
            offsets.append(offsets[-1] + len(records))
    np.asarray(offsets, dtype="<u8").tofile(directory / "change-rows.u64le")
    after = {
        label: {name: sha256_file(root / name) for name in names}
        for label, root in (("reference", reference), ("candidate", candidate))
    }
    if after != before:
        raise ValueError("grid input changed during comparison")
    result = {
        "grid": vars(grid),
        "changed_cells": changed,
        "compared_by": "map_code"
        if reference_bindings is None
        else "entity_and_physical_class",
        "pair_counts": dict(sorted(transitions.items())),
        "changed_bounds": bounds,
        "byte_identical": before["reference"] == before["candidate"],
        "input_sha256": before,
        "elapsed_seconds": time.monotonic() - start,
        "change_record_fields": ["row", "start", "end", "before_code", "after_code"],
    }
    write_json(directory / "report.json", result)
    return result
