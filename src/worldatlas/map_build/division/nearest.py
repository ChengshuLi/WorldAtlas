"""One nearest engine with component and cell query kernels over physical shores."""

from pathlib import Path

import numpy as np

from worldatlas.map_build.core.layers import merge_rows, patch_rows, write_layer
from worldatlas.map_build.division.areas import assign_area
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
    for y in scope.query_rows():
        parts = components.row(y)
        if not len(parts):
            continue
        roots = complete_row(
            scope.grid.width,
            np.column_stack((parts[:, :2], parts[:, 2] + np.uint32(1))),
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
    index = directory / "reference-index"
    build_reference_index(scope.grid, references.layer_rows(), index)
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
        for y in scope.query_rows():
            parts = scope.components("land").row(y)
            parts = parts[selected(parts[:, 2], ids)]
            claimed = complete_row(
                scope.grid.width,
                np.column_stack(
                    (parts[:, :2], entities[np.searchsorted(ids, parts[:, 2])])
                ),
            )
            starts, ends, (eligible, owned) = overlay(scope.query_row(y), claimed)
            records = spans(starts, ends, np.where(eligible != 0, owned, 0))
            if records:
                yield y, records

    result = write_layer(directory / "claims", scope.grid, rows())
    result["component_search"] = report
    return result


def nearest(
    scope,
    reference_cells,
    unit,
    distance_limit=None,
    *,
    directory,
    superset_winners=None,
):
    """Assign prepared queries, optionally reusing winners from a reference superset.

    The caller must establish identical shore geometry, distance and tie semantics.
    A superset winner retained in these references is also their exact winner.
    Zero/absent winners still require the complete calculation.
    """
    if unit not in ("cell", "component"):
        raise ValueError("nearest requires a cell or component decision unit")
    if unit == "component":
        if superset_winners is not None:
            raise ValueError("cell winners cannot certify a component distance")
        if distance_limit is not None:
            raise ValueError(
                "component nearest does not support a coastal distance limit"
            )
        return component_queries(scope, reference_cells, directory)
    grid = scope.grid
    pairs = reference_cells.pairs
    reused = 0
    if len(pairs) == 1 and distance_limit is None:
        result = assign_area(scope, pairs[0][0], directory)
        if superset_winners is not None:
            result["reused_superset_winner_cells"] = 0
        return result

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
        nonlocal reused
        for first, last, windows in scope.query_windows():
            streams = []
            for left, right, mask in windows:
                if not pairs:
                    raise ValueError("selected cells have no eligible reference shores")
                known = None
                if superset_winners is not None:
                    if distance_limit is not None:
                        raise ValueError(
                            "winner reuse without recorded distances needs an unrestricted query"
                        )
                    known = np.stack(
                        [
                            shared_nearest.crop(
                                *superset_winners, y, left, right, grid.width
                            )
                            for y in range(first, last)
                        ]
                    )
                    known = np.where(
                        mask & np.isin(known, [p[0] for p in pairs]), known, 0
                    )
                    reused += int(np.count_nonzero(known))
                pending = mask if known is None else mask & (known == 0)
                if pending.any():
                    values, _ = classify(
                        pending,
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
                    if known is not None:
                        values = np.where(known != 0, known, values)
                else:
                    values = known
                streams.append(patch_rows(values, (left, right, first, last), grid))
            yield from merge_rows(streams)

    result = write_layer(directory, grid, rows())
    if superset_winners is not None:
        result["reused_superset_winner_cells"] = reused
    return result
