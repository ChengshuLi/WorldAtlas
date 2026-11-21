"""Extract physical shores once; attach owners and select reference views."""

from __future__ import annotations

import threading
from collections.abc import Collection, Iterator, Sequence

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import row
from worldatlas.map_build.division.scope import selected
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.water.shared_nearest import ShoreIndexes, make_indexes
from worldatlas.map_build.water.shore_index import ShoreIndex
from worldatlas.map_build.water.shore_spans import ShoreSpans


class ReferenceCells(ShoreSpans):
    """Store shore runs labelled with the owners of the adjacent land."""

    def __init__(
        self,
        grid: Grid,
        offsets: np.ndarray,
        starts: np.ndarray,
        ends: np.ndarray,
        owners: np.ndarray,
        order: Sequence[int],
    ) -> None:
        """Keep labelled runs and prepare the search order.

        Args:
            grid: Dimensions and coordinates of the source grid.
            offsets: First shore-run index per row, plus the final offset.
            starts: First column of each run.
            ends: Exclusive end column of each run.
            owners: Child entity ID of each run.
            order: Child IDs in the order used for exact ties.
        """
        self.grid = grid
        self.width = grid.width
        self.height = grid.height
        self.offsets = offsets
        self.starts = starts
        self.ends = ends
        self.codes = owners
        present = set(map(int, np.unique(owners)))
        self.pairs = [(e, e, e) for e in order if e in present]
        if present - {p[0] for p in self.pairs}:
            raise ValueError("shore owner is not a selected child")
        self._indexes = None
        self._index_lock = threading.Lock()

    @property
    def indexes(self) -> ShoreIndexes:
        """Build or read the complete shore indexes for the participating owners.

        Returns:
            Owner ID mapped to its shore coordinates and complete spatial index.

        Raises:
            ValueError: There are no eligible shores.
        """
        with self._index_lock:
            if self._indexes is None:
                if not self.pairs:
                    raise ValueError("no eligible physical shores")
                centers = self.centers_for_crop(
                    self.grid.bounds, self.grid.step, [p[0] for p in self.pairs]
                )
                self._indexes = make_indexes(centers, self.pairs)
            return self._indexes

    def layer_rows(self) -> Iterator[tuple[int, np.ndarray]]:
        """Read labelled runs in row order without expanding the cells.

        Yields:
            (row, records), where records is an N-by-3 array of
            (start_column, end_column, owner_id).
        """
        for y in range(self.height):
            lo, hi = map(int, self.offsets[y : y + 2])
            if lo != hi:
                yield (
                    y,
                    np.column_stack(
                        (self.starts[lo:hi], self.ends[lo:hi], self.codes[lo:hi])
                    ),
                )

    def filtered(self, owners: Collection[int]) -> ReferenceSubset:
        """Use only the shore indexes for a given set of owners.

        Args:
            owners: IDs allowed to receive the assignments.

        Returns:
            View of the reference cells for those owners.
        """
        return ReferenceSubset(self, owners)


class ReferenceSubset:
    """Expose selected owners' shore indexes without copying their cells."""

    def __init__(self, source: ReferenceCells, owners: Collection[int]) -> None:
        """Select the participating owner records.

        Args:
            source: Complete shore run and index data.
            owners: Allowed owner IDs.

        Raises:
            ValueError: An allowed owner has no eligible shore.
        """
        self.source = source
        self.pairs = [p for p in source.pairs if p[0] in owners]
        if set(owners) - {p[0] for p in self.pairs}:
            raise ValueError("basin participant lacks an eligible physical shore")

    @property
    def indexes(self) -> ShoreIndexes:
        """Find the shared indexes for the selected owners.

        Returns:
            Owner IDs mapped to their complete spatial indexes and shore coordinates.
        """
        return {p[0]: self.source.indexes[p[0]] for p in self.pairs}


class ShoreGeometry:
    """Keep one copy of the physical shores for all divisions of this grid."""

    def __init__(self, physical: tuple[np.ndarray, np.ndarray], grid: Grid) -> None:
        """Find land cells touching water along a grid edge.

        Args:
            physical: Physical row offsets and run data.
            grid: Dimensions and coordinates of the physical grid.
        """
        self.grid = grid
        self.spans = ShoreIndex(
            physical, physical, grid.width, grid.height, land_codes=[17]
        )

    def attach(
        self,
        ownership: tuple[np.ndarray, np.ndarray],
        order: Sequence[int],
        *,
        components: ComponentGrid | None = None,
        reference_components: Collection[int] | None = None,
        reference_owners: Collection[int] | None = None,
    ) -> ReferenceCells:
        """Label physical shores with their current owners.

        Keep the same physical shore when ownership changes.

        Args:
            ownership: Row-run streams of current owners.
            order: Owner IDs in exact tie order.
            components: Physical component grid when selecting reference components.
            reference_components: Optional IDs of land components eligible as
                references.
            reference_owners: Optional filter for eligible owners.

        Returns:
            Labelled shore runs for the eligible owners and components.
        """
        grid = self.grid
        source = self.spans
        offsets = [0]
        starts, ends, owners = [], [], []
        roots = (
            np.asarray(sorted(reference_components), dtype=np.uint32)
            if reference_components is not None
            else None
        )
        eligible_owners = (
            np.asarray(sorted(reference_owners), dtype=np.uint32)
            if reference_owners is not None and set(order) - set(reference_owners)
            else None
        )
        for y in range(grid.height):
            lo, hi = map(int, source.offsets[y : y + 2])
            if lo == hi:
                offsets.append(offsets[-1])
                continue
            a, b = source.starts[lo:hi], source.ends[lo:hi]
            stops, codes = row(ownership, y, grid.width)
            first = np.searchsorted(stops, a, side="right")
            last = np.searchsorted(stops, b, side="left")
            if np.any(first != last):
                # A shore span can cross an ownership boundary on continuous land.
                # Expand only by overlapping owner runs, never by grid cells.
                lengths = last - first + 1
                index = np.repeat(np.arange(len(a)), lengths)
                offsets_in_span = np.arange(len(index)) - np.repeat(
                    lengths.cumsum() - lengths, lengths
                )
                first = first[index] + offsets_in_span
                a = np.maximum(a[index], np.r_[0, stops[:-1]][first])
                b = np.minimum(b[index], stops[first])
            owner = codes[first]
            keep = owner != 0
            if eligible_owners is not None:
                keep &= np.isin(owner, eligible_owners)
            if roots is not None and keep.any():
                if components is None:
                    raise ValueError(
                        "component-filtered shores need physical components"
                    )
                records = components.row(y)
                positions = np.searchsorted(records[:, 1], a[keep], side="right")
                valid = positions < len(records)
                safe = np.minimum(positions, len(records) - 1)
                if not valid.all() or np.any(records[safe, 0] > a[keep]):
                    raise ValueError("owned shore is outside parent land components")
                allowed = selected(records[safe, 2], roots)
                keep[np.flatnonzero(keep)] = allowed
            a, b, owner = a[keep], b[keep], owner[keep]
            if len(a):
                joins = (b[:-1] == a[1:]) & (owner[:-1] == owner[1:])
                starts.append(a[np.r_[True, ~joins]])
                ends.append(b[np.r_[~joins, True]])
                owners.append(owner[np.r_[True, ~joins]])
                offsets.append(offsets[-1] + len(starts[-1]))
            else:
                offsets.append(offsets[-1])

        def combine(parts: Sequence[np.ndarray]) -> np.ndarray:
            """Join the nonempty arrays collected from each row.

            Args:
                parts: Arrays of columns or owner IDs.

            Returns:
                One uint32 array in row order, empty when there are no parts.
            """
            return (
                np.concatenate(parts, dtype=np.uint32)
                if parts
                else np.empty(0, dtype=np.uint32)
            )

        return ReferenceCells(
            grid,
            np.asarray(offsets, dtype=np.uint64),
            combine(starts),
            combine(ends),
            combine(owners),
            order,
        )
