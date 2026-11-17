"""Extract physical shores once; attach owners and select reference views."""

from array import array
import threading
import numpy as np

from worldatlas.map_build.core.rle import row
from worldatlas.map_build.division.intervals import overlay, spans
from worldatlas.map_build.division.scope import complete_row, selected
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
                    [
                        (int(a), int(b), int(e))
                        for a, b, e in zip(
                            self.starts[lo:hi], self.ends[lo:hi], self.codes[lo:hi]
                        )
                    ],
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

    def attach(self, ownership, order, *, components=None, reference_components=None):
        """Overlay child ownership; optionally select physical reference components.

        Geometry remains fixed. Reattaching island labels never scans neighbours
        or creates shores along ownership lines or the parent's artificial edge.
        """
        grid = self.grid
        source = self.spans
        offsets = array("Q", [0])
        starts = array("I")
        ends = array("I")
        owners = array("I")
        roots = (
            np.asarray(sorted(reference_components), dtype=np.uint32)
            if reference_components is not None
            else None
        )
        for y in range(grid.height):
            lo, hi = map(int, source.offsets[y : y + 2])
            if lo == hi:
                offsets.append(offsets[-1])
                continue
            geometry = complete_row(
                grid.width,
                np.column_stack(
                    (
                        source.starts[lo:hi],
                        source.ends[lo:hi],
                        np.ones(hi - lo, dtype=np.uint32),
                    )
                ),
            )
            a, b, (shore, owner) = overlay(geometry, row(ownership, y, grid.width))
            keep = (shore != 0) & (owner != 0)
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
            records = spans(a, b, np.where(keep, owner, 0))
            starts.extend(r[0] for r in records)
            ends.extend(r[1] for r in records)
            owners.extend(r[2] for r in records)
            offsets.append(len(starts))
        return ReferenceCells(
            grid,
            np.asarray(offsets, dtype=np.uint64),
            np.asarray(starts, dtype=np.uint32),
            np.asarray(ends, dtype=np.uint32),
            np.asarray(owners, dtype=np.uint32),
            order,
        )
