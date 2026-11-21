"""Read current land components and answer source-neutral geographic queries."""

from contextlib import ExitStack
from pathlib import Path

import numpy as np

from worldatlas.map_build.core.geometry import (
    PolygonRasterizer,
    reject_boundary_centers,
)
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.core.wrapping import wrapped_grid_bounds
from worldatlas.map_build.execution.control import check_cancelled


class ComponentGrid:
    """Run-scoped mapped streams with physical coverage checked once per row.

    Component runs contain [start, end, root]; physical runs contain [end, code].
    The caller owns input checksums and checkpoint reuse. Root IDs are meaningful
    only within these streams.
    """

    def __init__(
        self, physical_directory, component_directory, grid, *, physical_code=17
    ):
        self.grid = grid
        self.physical_code = physical_code
        self.directory = Path(component_directory)
        self.resources = ExitStack()
        self.validated = np.zeros(grid.height, dtype=bool)
        self.populations = None
        try:
            self.physical = self.resources.enter_context(
                open_grid(physical_directory, grid)
            )
            directory = self.directory
            self.offsets = self._map(directory / "rows.u32le")
            self.runs = self._map(directory / "runs.u32le")
            if (
                len(self.offsets) != grid.height + 1
                or len(self.runs) % 3
                or self.offsets[0] != 0
                or int(self.offsets[-1]) != len(self.runs) // 3
                or np.any(self.offsets[1:] < self.offsets[:-1])
            ):
                raise ValueError("invalid component stream offsets")
            self.runs = self.runs.reshape(-1, 3)
        except BaseException:
            self.close()
            raise

    def _map(self, path):
        if path.stat().st_size % 4:
            raise ValueError("incomplete component u32 stream")
        if not path.stat().st_size:
            return np.empty(0, dtype="<u4")
        values = np.memmap(path, dtype="<u4", mode="r")
        self.resources.callback(values._mmap.close)
        return values

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.close()

    def close(self):
        self.resources.close()

    def row(self, y):
        if type(y) is not int or not 0 <= y < self.grid.height:
            raise ValueError("component row outside grid")
        first, last = map(int, self.offsets[y : y + 2])
        spans = np.asarray(self.runs[first:last])
        if self.validated[y]:
            return spans
        ends, codes = row(self.physical, y, self.grid.width)
        starts = np.r_[np.uint32(0), ends[:-1]]
        if np.any(~np.isin(codes, [0, 1, 17])):
            raise ValueError("invalid physical class")
        lo, hi, roots = spans.T
        if (
            np.any(lo >= hi)
            or np.any(hi > self.grid.width)
            or np.any(roots == 2**32 - 1)
            or np.any(hi[:-1] > lo[1:])
        ):
            raise ValueError("invalid component row")

        def union(a, b):
            if not len(a):
                return a, b
            return a[np.r_[True, a[1:] != b[:-1]]], b[np.r_[b[:-1] != a[1:], True]]

        expected = union(
            starts[codes == self.physical_code], ends[codes == self.physical_code]
        )
        actual = union(lo, hi)
        if any(not np.array_equal(a, b) for a, b in zip(expected, actual)):
            raise ValueError("component coverage differs from its physical class")
        self.validated[y] = True
        return spans

    def totals(self):
        if self.populations is None:
            for y in range(self.grid.height):
                check_cancelled()
                self.row(y)
            roots, inverse = np.unique(self.runs[:, 2], return_inverse=True)
            totals = np.zeros(len(roots), dtype=np.uint64)
            np.add.at(
                totals, inverse, self.runs[:, 1].astype(np.uint64) - self.runs[:, 0]
            )
            self.populations = {
                int(root): int(total) for root, total in zip(roots, totals)
            }
        return self.populations

    def row_bounds(self, roots):
        """Locate the full selected components, including cells outside a polygon."""
        positions = np.flatnonzero(np.isin(self.runs[:, 2], roots))
        if not len(positions):
            return 0, 0
        first, last = (
            np.searchsorted(self.offsets, positions[[0, -1]], side="right") - 1
        )
        return int(first), int(last) + 1

    def component_at(self, longitude, latitude):
        """Locate a geographic point's physical component.

        Args:
            longitude: WGS84 longitude in degrees.
            latitude: WGS84 latitude in degrees.

        Returns:
            The component ID, or None if the point does not identify one.
        """
        cell = self.grid.cell_at(longitude, latitude)
        return self._at_cell(*cell) if cell is not None else None

    def _at_cell(self, x, y):
        spans = self.row(y)
        index = int(np.searchsorted(spans[:, 1], x, side="right"))
        if index == len(spans) or not int(spans[index, 0]) <= x < int(spans[index, 1]):
            return None
        return int(spans[index, 2])

    def profile(self, geometry, *, rows_per_batch=64):
        """Count component centers within a polygon, including holes and wrapping."""
        if type(rows_per_batch) is not int or rows_per_batch <= 0:
            raise ValueError("row batch must be positive")
        reject_boundary_centers(
            geometry,
            self.grid,
            selected=lambda x, y: self._at_cell(x % self.grid.width, y) is not None,
        )
        (x0, x1, y0, y1), _ = wrapped_grid_bounds(
            geometry, self.grid.width, self.grid.height, self.grid.step
        )
        counts = {}
        windows = [(x0, min(x1, self.grid.width))]
        if x1 > self.grid.width:
            windows.append((0, x1 - self.grid.width))
        rasterizer = PolygonRasterizer(geometry, self.grid)
        for first in range(y0, y1, rows_per_batch):
            check_cancelled()
            last = min(first + rows_per_batch, y1)
            _, mask = rasterizer.rasterize((x0, x1, first, last))
            for y in range(first, last):
                spans = self.row(y)
                for a, b in windows:
                    relevant = spans[(spans[:, 0] < b) & (spans[:, 1] > a)]
                    for lo, hi, root in relevant:
                        lo, hi, root = max(int(lo), a), min(int(hi), b), int(root)
                        offset = (a - x0) % self.grid.width
                        count = int(
                            np.count_nonzero(
                                mask[y - first, offset + lo - a : offset + hi - a]
                            )
                        )
                        if count:
                            counts[root] = counts.get(root, 0) + count
        return counts
