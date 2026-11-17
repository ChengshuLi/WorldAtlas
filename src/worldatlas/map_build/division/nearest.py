"""One nearest engine with component and cell query kernels over physical shores."""

from pathlib import Path

import numpy as np

from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.division.intervals import overlay, spans
from worldatlas.map_build.division.scope import complete_row, selected
from worldatlas.map_build.land.assignments import assign_components, read_assignments
from worldatlas.map_build.land.reference_index import build_reference_index
from worldatlas.map_build.water.rectangle_nearest import classify
from worldatlas.map_build.water import shared_nearest


def query_roots(scope):
    if hasattr(scope, "_query_roots"):
        return scope._query_roots
    components = scope.components("land")
    found = set()
    for y in range(scope.grid.height):
        parts = components.row(y)
        if not len(parts):
            continue
        roots = complete_row(
            scope.grid.width, [(int(a), int(b), int(root) + 1) for a, b, root in parts]
        )
        _, _, (eligible, root) = overlay(scope.query_row(y), roots)
        found.update(int(r) - 1 for r in np.unique(root[(eligible != 0) & (root != 0)]))
    scope._query_roots = found
    return found


def component_queries(scope, references, directory):
    roots = query_roots(scope)
    if not roots:
        return write_layer(directory, scope.grid, ())
    directory = Path(directory)
    directory.mkdir()
    reference_directory = directory / "reference-cells"
    write_layer(reference_directory, scope.grid, references.layer_rows())
    index = directory / "reference-index"
    build_reference_index(scope.grid, reference_directory, index)
    bindings = [
        dict(code=e, entity_id=e, physical_class="land") for e, _, _ in references.pairs
    ]
    report = assign_components(
        scope.components("land"),
        index,
        bindings,
        directory / "distances",
        roots=roots,
        priority_codes=[p[0] for p in references.pairs],
    )
    owners = read_assignments(report)
    ids = np.asarray(sorted(owners), dtype=np.uint32)
    entities = np.asarray([owners[int(root)] for root in ids], dtype=np.uint32)

    def rows():
        for y in range(scope.grid.height):
            parts = scope.components("land").row(y)
            parts = parts[selected(parts[:, 2], ids)]
            claimed = complete_row(
                scope.grid.width,
                [
                    (int(a), int(b), int(entities[np.searchsorted(ids, root)]))
                    for a, b, root in parts
                ],
            )
            starts, ends, (eligible, owned) = overlay(scope.query_row(y), claimed)
            records = spans(starts, ends, np.where(eligible != 0, owned, 0))
            if records:
                yield y, records

    result = write_layer(directory / "claims", scope.grid, rows())
    result["component_search"] = report
    return result


def nearest(scope, reference_cells, unit, distance_limit=None, *, directory):
    """Assign the prepared query scope; never filter ownership a second time."""
    if unit not in ("cell", "component"):
        raise ValueError("nearest requires a cell or component decision unit")
    if unit == "component":
        if distance_limit is not None:
            raise ValueError(
                "component nearest does not support a coastal distance limit"
            )
        return component_queries(scope, reference_cells, directory)
    grid = scope.grid
    pairs = reference_cells.pairs

    def points(lat, lon):
        codes, stats = shared_nearest.classify_wgs84(
            lat,
            lon,
            grid.bounds,
            grid.width,
            grid.height,
            grid.step,
            pairs,
            reference_cells.indexes,
            band=distance_limit,
        )
        return codes, stats["bounded"], stats["exact"]

    def rows():
        # Skip rows excluded by source geometry. Crop query buffers to actual
        # eligible intervals; references still cover their complete shore sets.
        y0, y1 = (
            (scope.bounds[2], scope.bounds[3])
            if scope.bounds and not any(len(p) for p in scope.points.values())
            else (0, grid.height)
        )
        for first in range(y0, y1, 64):
            last = min(first + 64, y1)
            queries = []
            left = grid.width
            right = 0
            for y in range(first, last):
                ends, values = scope.query_row(y)
                queries.append((ends, values))
                starts = np.r_[0, ends[:-1]]
                active = np.flatnonzero(values != 0)
                if len(active):
                    left = min(left, int(starts[active[0]]))
                    right = max(right, int(ends[active[-1]]))
            if left >= right:
                continue
            masks = []
            for ends, values in queries:
                cuts = np.r_[left, ends[(ends > left) & (ends < right)], right]
                chosen = values[np.searchsorted(ends, cuts[:-1], side="right")]
                masks.append(np.repeat(chosen != 0, np.diff(cuts)))
            mask = np.asarray(masks, dtype=bool)
            if not pairs:
                raise ValueError("selected cells have no eligible reference shores")
            if len(pairs) == 1 and distance_limit is None:
                values = np.where(mask, pairs[0][0], 0).astype(np.uint32)
            else:
                values, _ = classify(
                    mask,
                    left,
                    first,
                    grid.bounds,
                    grid.width,
                    grid.height,
                    grid.step,
                    pairs,
                    reference_cells.indexes,
                    points,
                    band=distance_limit,
                )
            yield from patch_rows(values, (left, right, first, last), grid)

    return write_layer(directory, grid, rows())
