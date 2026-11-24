"""Uniform-area and multi-face assignment over the same prepared scope."""

from collections import defaultdict
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.partition import divide_regions, geographic_cuts
from worldatlas.map_build.core.rle import open_mapped_array, overlay
from worldatlas.map_build.division.contracts import CompiledTarget, point_coordinates
from worldatlas.map_build.division.intervals import spans
from worldatlas.map_build.division.scope import Scope, complete_row, selected
from worldatlas.map_build.inputs.selection_types import GeographicFeature


def assign_area(scope: Scope, target: int, directory: Path | str) -> dict[str, Any]:
    """Give every eligible cell in the scope to one child.

    Args:
        scope: Prepared geographic scope and output filters.
        target: Child entity ID to assign.
        directory: New directory for the rule's claim layer.

    Returns:
        Layer report with bounds, run count, and cell count for the child.
    """

    def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
        """Read eligible cells row by row and label them with the target.

        Yields:
            (row, spans) with the target entity ID on each span.
        """
        for y in scope.query_rows():
            ends, values = scope.query_row(y)
            starts = np.r_[0, ends[:-1]]
            output = np.where(values != 0, target, 0).astype(np.uint32)
            records = spans(starts, ends, output)
            if records:
                yield y, records

    return write_layer(directory, scope.grid, rows())


class Faces:
    """Read the regions and owner labels produced by cutting a scope."""

    def __init__(
        self, offsets: np.ndarray, nodes: np.ndarray, owners: dict[int, int], grid: Grid
    ) -> None:
        """Index the owner labels for the supplied region runs.

        Args:
            offsets: 1-D uint64 array of row offsets into the runs.
            nodes: Flat uint32 array of (first column, end column, region ID) runs.
            owners: Region root IDs mapped to child entity IDs.
            grid: Dimensions of the grid.
        """
        self.grid = grid
        self.offsets = offsets
        self.nodes = nodes.reshape(-1, 3)
        self.roots = np.asarray(sorted(owners), dtype=np.uint32)
        self.owners = np.asarray(
            [owners[int(root)] for root in self.roots], dtype=np.uint32
        )

    def row(self, y: int, *, by_face: bool = False) -> tuple[np.ndarray, np.ndarray]:
        """Read one row of labelled regions.

        Args:
            y: Zero-based row index.
            by_face: Use distinct face IDs instead of child entity IDs.

        Returns:
            Two uint32 arrays of exclusive run ends and IDs. Unlabelled cells
            have value zero.
        """
        nodes = np.asarray(self.nodes[int(self.offsets[y]) : int(self.offsets[y + 1])])
        if not len(nodes):
            return complete_row(self.grid.width, ())
        positions = np.searchsorted(self.roots, nodes[:, 2])
        safe = np.minimum(positions, len(self.roots) - 1)
        matched = (positions < len(self.roots)) & (self.roots[safe] == nodes[:, 2])
        # Use one-based label positions so zero always means unlabelled.
        values = np.where(matched, safe + 1 if by_face else self.owners[safe], 0)
        return complete_row(
            self.grid.width,
            np.column_stack((nodes[:, :2], values)),
        )


def component_owners(scope: Scope, faces: Faces) -> dict[str, dict[int, int]]:
    """Assign each selected component to the labelled face covering most of it.

    Args:
        scope: Rule scope giving eligible physical components.
        faces: Labelled regions of the scope.

    Returns:
        Physical class mapped to dictionaries of component ID to child ID.

    Raises:
        ValueError: A component lacks a labelled face covering over half of it.
    """
    results = {}
    counts = defaultdict(int)
    eligible = scope.eligible_components()
    for y in scope.query_rows():
        face = faces.row(y, by_face=True)
        for kind, roots in eligible.items():
            components = scope.components(kind)
            records = components.row(y)
            chosen = records[selected(records[:, 2], roots)]
            if not len(chosen):
                continue
            component = complete_row(
                scope.grid.width,
                np.column_stack((chosen[:, :2], chosen[:, 2].astype(np.uint64) + 1)),
            )
            starts, ends, (component_ids, face_ids) = overlay(component, face)
            valid = (component_ids != 0) & (face_ids != 0)
            component_roots = component_ids[valid].astype(np.uint64) - 1
            keys = (component_roots << 32) | face_ids[valid].astype(np.uint64)
            unique, inverse = np.unique(keys, return_inverse=True)
            lengths = np.zeros(len(unique), dtype=np.uint64)
            np.add.at(lengths, inverse, (ends[valid] - starts[valid]).astype(np.uint64))
            for key, n in zip(unique, lengths):
                counts[kind, int(key) >> 32, int(key) & 0xFFFFFFFF] += int(n)
    for kind, roots in eligible.items():
        totals = scope.components(kind).totals()
        result = {
            root: int(faces.owners[face_id - 1])
            for (which, root, face_id), n in counts.items()
            if which == kind and n * 2 > totals[root]
        }
        for root in map(int, roots):
            if root not in result:
                raise ValueError(
                    f"rule {scope.rule['id']}: component {root} lacks one majority face"
                )
        results[kind] = result
    return results


def divide_area(
    scope: Scope,
    boundaries: Sequence[GeographicFeature],
    targets: Sequence[CompiledTarget],
    directory: Path | str,
) -> dict[str, Any]:
    """Cut the geographic scope along lines and assign each labelled region.

    The cuts use the whole geographic scope. Physical class and existing
    owners filter the cells the rule can claim after the split.

    Args:
        scope: Prepared area and output filters.
        boundaries: Source features holding boundary lines.
        targets: Child IDs and their label point features.
        directory: New directory for face files and claim layer.

    Returns:
        Layer report with the assigned cells and number of labelled faces
        when the scope is nonempty.

    Raises:
        ValueError: A label is invalid, two labels disagree, or an eligible
            cell or component has no labelled face.
    """
    context_rows = scope.context_rows()
    if not context_rows:
        return write_layer(directory, scope.grid, ())
    directory = Path(directory)
    directory.mkdir()
    grid = scope.grid
    labels = []
    for target in targets:
        # Compilation requires a point for every divide_area target.
        lon, lat = point_coordinates(cast(GeographicFeature, target["point"]))
        cell = grid.cell_at(lon, lat)
        if cell is None:
            raise ValueError("divided-face label is outside the grid")
        labels.append((target["entity_id"], *cell))
    cuts = geographic_cuts([dict(f["geometry"]) for f in boundaries], grid)
    faces_directory = directory / "faces"
    owners = divide_regions(
        scope.context_intervals,
        grid,
        cuts,
        labels,
        faces_directory,
        rows=context_rows,
    )
    with (
        open_mapped_array(faces_directory / "rows.u64le", "<u8") as offsets,
        open_mapped_array(faces_directory / "nodes.u32le", "<u4") as nodes,
    ):
        faces = Faces(offsets, nodes, owners, grid)
        by_component = (
            component_owners(scope, faces)
            if scope.rule["unit"] == "component"
            else None
        )
        compiled = {}
        if by_component is not None:
            for kind, values in by_component.items():
                roots = np.asarray(sorted(values), dtype=np.uint32)
                compiled[kind] = (
                    roots,
                    np.asarray([values[int(r)] for r in roots], dtype=np.uint32),
                )

        def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
            """Read each eligible row and claim the owner chosen by the split.

            Yields:
                (row, spans) with child entity IDs.

            Raises:
                ValueError: An eligible cell has no owner.
            """
            for y in scope.query_rows():
                query = scope.query_row(y)
                if by_component is None:
                    proposed = faces.row(y)
                else:
                    records = []
                    for kind, (roots, owners) in compiled.items():
                        pieces = scope.components(kind).row(y)
                        pieces = pieces[selected(pieces[:, 2], roots)]
                        for a, b, root in pieces:
                            entity = int(owners[np.searchsorted(roots, root)])
                            records.append((int(a), int(b), entity))
                    proposed = complete_row(grid.width, sorted(records))
                starts, ends, (eligible, owned) = overlay(query, proposed)
                missing = (eligible != 0) & (owned == 0)
                if missing.any():
                    x = int(starts[np.flatnonzero(missing)[0]])
                    raise ValueError(
                        f"rule {scope.rule['id']}: eligible cell {x},{y} has no face label"
                    )
                result = spans(starts, ends, np.where(eligible != 0, owned, 0))
                if result:
                    yield y, result

        report = write_layer(directory / "claims", grid, rows())
        report["faces"] = len(owners)
        return report
