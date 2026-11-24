"""One nearest engine with component and cell query kernels over physical shores."""

from collections.abc import Collection, Iterator
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.layers import merge_rows, patch_rows, write_layer
from worldatlas.map_build.core.rle import complete_row, overlay
from worldatlas.map_build.division.areas import assign_area
from worldatlas.map_build.division.intervals import spans
from worldatlas.map_build.division.scope import Scope, selected
from worldatlas.map_build.division.shores import ReferenceCells, ReferenceSubset
from worldatlas.map_build.land.assignments import assign_components
from worldatlas.map_build.land.reference_index import build_reference_index
from worldatlas.map_build.water import shared_nearest
from worldatlas.map_build.water.rectangle_nearest import classify


def query_roots(scope: Scope) -> set[int]:
    """Collect the IDs of land components with eligible cells.

    Args:
        scope: Prepared rule scope.

    Returns:
        Set of physical component IDs.
    """
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
    return found


def component_queries(
    scope: Scope,
    references: ReferenceCells,
    roots: Collection[int],
    directory: Path | str,
) -> dict[str, Any]:
    """Assign each selected land component to the closest reference shore.

    Args:
        scope: Scope of the cells eligible for assignment.
        references: Labelled shore runs for all eligible owners.
        roots: Selected land-component IDs to search.
        directory: New directory for the reference index, search and claims.

    Returns:
        Layer report, including component search statistics for a nonempty scope.
    """
    directory = Path(directory)
    directory.mkdir()
    index = directory / "reference-index"
    build_reference_index(scope.grid, references.layer_rows(), index)
    report, ids, entities = assign_components(
        scope.components("land"),
        index,
        directory / "distances",
        roots=roots,
        priority_codes=references.owners,
    )

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


def cell_queries(
    scope: Scope,
    reference_cells: ReferenceCells | ReferenceSubset,
    distance_limit: float | None = None,
    *,
    directory: Path | str,
) -> dict[str, Any]:
    """Assign prepared water cells to the nearest eligible shore.

    Args:
        scope: Eligible cells the rule may assign.
        reference_cells: Labelled shore runs and spatial indexes.
        distance_limit: Optional cutoff in metres for cell assignments.
        directory: New directory for the output layer.

    Returns:
        Layer report with assigned bounds and counts by owner.

    Raises:
        ValueError: The prepared cells cannot be assigned.
    """
    grid = scope.grid
    owners = reference_cells.owners
    if not owners and distance_limit is not None:
        return write_layer(directory, grid, ())
    if len(owners) == 1 and distance_limit is None:
        return assign_area(scope, owners[0], directory)

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
            owners,
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
                if not owners:
                    raise ValueError("selected cells have no eligible reference shores")
                values, _ = classify(
                    mask,
                    left,
                    first,
                    grid.bounds,
                    grid.width,
                    grid.height,
                    grid.step,
                    owners,
                    reference_cells.indexes,
                    points,
                    band=distance_limit,
                )
                streams.append(patch_rows(values, (left, right, first, last), grid))
            yield from merge_rows(streams)

    return write_layer(directory, grid, rows())
