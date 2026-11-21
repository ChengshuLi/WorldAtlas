"""One nearest engine with component and cell query kernels over physical shores."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import numpy as np

from worldatlas.map_build.core.layers import merge_rows, patch_rows, write_layer
from worldatlas.map_build.division.areas import assign_area
from worldatlas.map_build.division.intervals import overlay, spans
from worldatlas.map_build.division.scope import Scope, complete_row, selected
from worldatlas.map_build.division.shores import ReferenceCells, ReferenceSubset
from worldatlas.map_build.land.assignments import assign_components, read_assignments
from worldatlas.map_build.land.reference_index import build_reference_index
from worldatlas.map_build.water import shared_nearest
from worldatlas.map_build.water.rectangle_nearest import classify


def query_roots(scope: Scope) -> set[int]:
    """Collect the IDs of land components with eligible cells.

    Args:
        scope: Prepared rule scope.

    Returns:
        Set of physical component IDs, cached for this scope.
    """
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


def component_queries(
    scope: Scope, references: ReferenceCells, directory: Path | str
) -> dict[str, Any]:
    """Assign each selected land component to the closest reference shore.

    Args:
        scope: Scope of the cells eligible for assignment.
        references: Labelled shore runs for all eligible owners.
        directory: New directory for the reference index, search and claims.

    Returns:
        Layer report, including component search statistics for a nonempty scope.
    """
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

    def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
        """Emit the chosen owner for each eligible part of a component.

        Yields:
            (row, spans) with child entity IDs.
        """
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
    scope: Scope,
    reference_cells: ReferenceCells | ReferenceSubset,
    unit: str,
    distance_limit: float | None = None,
    *,
    directory: Path | str,
) -> dict[str, Any]:
    """Assign prepared cells or land components to the nearest eligible shore.

    Args:
        scope: Eligible cells the rule may assign.
        reference_cells: Labelled shore runs and spatial indexes.
        unit: "cell" for individual cells or "component" for whole islands.
        distance_limit: Optional cutoff in metres for cell assignments.
        directory: New directory for the output layer.

    Returns:
        Layer report with assigned bounds and counts by owner.

    Raises:
        ValueError: The decision unit or distance cutoff is incompatible, or
            the input cannot be assigned.
    """
    if unit not in ("cell", "component"):
        raise ValueError("nearest requires a cell or component decision unit")
    if unit == "component":
        if distance_limit is not None:
            raise ValueError(
                "component nearest does not support a coastal distance limit"
            )
        return component_queries(
            scope, cast(ReferenceCells, reference_cells), directory
        )
    grid = scope.grid
    pairs = reference_cells.pairs
    if not pairs and distance_limit is not None:
        return write_layer(directory, grid, ())
    if len(pairs) == 1 and distance_limit is None:
        return assign_area(scope, pairs[0][0], directory)

    def points(lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, int, int]:
        """Classify a batch of cell centres using exact WGS84 distances as needed.

        Args:
            lat: Array of query latitudes in degrees.
            lon: Matching array of query longitudes in degrees.

        Returns:
            (owners, bounded_count, exact_count).
        """
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

    def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
        """Process the eligible windows and merge their assigned spans in row order.

        Yields:
            (row, spans) with the nearest eligible owner.
        """
        for first, last, windows in scope.query_windows():
            streams = []
            for left, right, mask in windows:
                if not pairs:
                    raise ValueError("selected cells have no eligible reference shores")
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
                streams.append(patch_rows(values, (left, right, first, last), grid))
            yield from merge_rows(streams)

    return write_layer(directory, grid, rows())
