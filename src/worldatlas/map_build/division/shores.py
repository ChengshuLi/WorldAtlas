"""Extract physical shores once; attach owners and select reference views."""

import threading
import numpy as np

from worldatlas.map_build.core.rle import row
from worldatlas.map_build.division.scope import selected
from worldatlas.map_build.water.shore_spans import ShoreSpans
from worldatlas.map_build.water.shore_index import ShoreIndex
from worldatlas.map_build.water.shared_nearest import make_indexes


class ReferenceCells(ShoreSpans):
    """Labelled physical shore spans with reusable complete point indexes."""

    def __init__(self, grid, offsets, starts, ends, owners, order):
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
    def indexes(self):
        with self._index_lock:
            if self._indexes is None:
                if not self.pairs:
                    raise ValueError("no eligible physical shores")
                centers = self.centers_for_crop(
                    self.grid.bounds, self.grid.step, [p[0] for p in self.pairs]
                )
                self._indexes = make_indexes(centers, self.pairs)
            return self._indexes

    def layer_rows(self):
        for y in range(self.height):
            lo, hi = map(int, self.offsets[y : y + 2])
            if lo != hi:
                yield (
                    y,
                    np.column_stack(
                        (self.starts[lo:hi], self.ends[lo:hi], self.codes[lo:hi])
                    ),
                )

    def filtered(self, owners):
        return ReferenceSubset(self, owners)


class ReferenceSubset:
    def __init__(self, source, owners):
        self.source = source
        self.pairs = [p for p in source.pairs if p[0] in owners]
        if set(owners) - {p[0] for p in self.pairs}:
            raise ValueError("basin participant lacks an eligible physical shore")

    @property
    def indexes(self):
        return {p[0]: self.source.indexes[p[0]] for p in self.pairs}


class ShoreGeometry:
    def __init__(self, physical, grid):
        self.grid = grid
        self.spans = ShoreIndex(
            physical, physical, grid.width, grid.height, land_codes=[17]
        )

    def attach(
        self,
        ownership,
        order,
        *,
        components=None,
        reference_components=None,
        reference_owners=None,
    ):
        """Overlay child ownership; optionally select physical reference components.

        Geometry remains fixed. Reattaching island labels never scans neighbours
        or creates shores along ownership lines or the parent's artificial edge.
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

        def combine(parts):
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
