"""Read current land components and answer source-neutral geographic queries."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from types import TracebackType
from typing import Self

import numpy as np
from numpy.typing import ArrayLike
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from worldatlas.map_build.core.geometry import (
    PolygonRasterizer,
    reject_boundary_centers,
)
from worldatlas.map_build.core.grid import Grid, column_windows
from worldatlas.map_build.core.rle import open_grid, open_mapped_array, row
from worldatlas.map_build.execution.control import check_cancelled


class ComponentGrid:
    """Read connected components as horizontal runs.

    A run stores (first_column, end_column, component_id). Component IDs
    are local to this build. Coverage is checked when a row is first read.
    """

    def __init__(
        self,
        physical_directory: Path | str,
        component_directory: Path | str,
        grid: Grid,
        *,
        physical_code: int = 17,
    ) -> None:
        """Open the component and physical grids for one physical class.

        Args:
            physical_directory: Directory with the physical row-run files.
            component_directory: Directory with component runs and row offsets.
            grid: Expected dimensions and coordinates.
            physical_code: Class represented by the components, normally land (17)
                or water (1).

        Raises:
            ValueError: The component offsets or file sizes are invalid.
        """
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
            self.offsets = self.resources.enter_context(
                open_mapped_array(directory / "rows.u32le", "<u4")
            )
            self.runs = self.resources.enter_context(
                open_mapped_array(directory / "runs.u32le", "<u4")
            )
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

    def __enter__(self) -> Self:
        """Use the open component grid inside a context.

        Returns:
            This component grid.
        """
        return self

    def __exit__(
        self, *exception: type[BaseException] | BaseException | TracebackType | None
    ) -> None:
        """Close the component grid when the context exits.

        Args:
            exception: Exception details supplied by the context manager, if any.
        """
        self.close()

    def close(self) -> None:
        """Close all files mapped by this grid."""
        self.resources.close()

    def row(self, y: int) -> np.ndarray:
        """Read one row's component runs and verify physical coverage on first use.

        Args:
            y: Zero-based row index.

        Returns:
            N-by-3 uint32 array of (first_column, end_column, component_id).

        Raises:
            ValueError: The row is outside the grid or its runs do not match the physical class.
        """
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

        def union(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            """Join adjacent spans to compare their coverage.

            Args:
                a: Sorted first columns.
                b: Matching exclusive end columns.

            Returns:
                Start and end arrays after joining contiguous spans.
            """
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

    def totals(self) -> dict[int, int]:
        """Count all cells in each component once and cache the counts.

        Returns:
            Component IDs mapped to total cell counts.
        """
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

    def row_bounds(self, roots: ArrayLike) -> tuple[int, int]:
        """Find the full north-south extent of selected components.

        Args:
            roots: IDs to include.

        Returns:
            (first_row, end_row), where the end is exclusive. An empty
            selection gives (0, 0).
        """
        positions = np.flatnonzero(np.isin(self.runs[:, 2], roots))
        if not len(positions):
            return 0, 0
        first, last = (
            np.searchsorted(self.offsets, positions[[0, -1]], side="right") - 1
        )
        return int(first), int(last) + 1

    def component_at(self, longitude: float, latitude: float) -> int | None:
        """Find the component containing a geographic point.

        Args:
            longitude: Longitude in WGS84 degrees.
            latitude: Latitude in WGS84 degrees.

        Returns:
            Component ID, or None outside this grid or physical class.
        """
        cell = self.grid.cell_at(longitude, latitude)
        return self._at_cell(*cell) if cell is not None else None

    def _at_cell(self, x: int, y: int) -> int | None:
        """Look up a component at one grid cell.

        Args:
            x: Column containing the point.
            y: Row containing the point.

        Returns:
            Component ID, or None when no component covers the cell.
        """
        spans = self.row(y)
        index = int(np.searchsorted(spans[:, 1], x, side="right"))
        if index == len(spans) or not int(spans[index, 0]) <= x < int(spans[index, 1]):
            return None
        return int(spans[index, 2])

    def profile(
        self, geometry: BaseGeometry, *, rows_per_batch: int = 64
    ) -> dict[int, int]:
        """Count component cells whose centres fall inside a polygon.

        Args:
            geometry: Validated WGS84 polygon or multipolygon.
            rows_per_batch: Number of rows to rasterize together.

        Returns:
            Dictionary from intersecting component ID to its cell count inside
            the polygon. Holes and the longitude seam are respected.
        """
        if type(rows_per_batch) is not int or rows_per_batch <= 0:
            raise ValueError("row batch must be positive")
        reject_boundary_centers(
            mapping(geometry),
            self.grid,
            selected=lambda x, y: self._at_cell(x % self.grid.width, y) is not None,
        )
        rasterizer = PolygonRasterizer(geometry, self.grid)
        x0, x1, y0, y1 = rasterizer.bounds
        counts = {}
        windows = column_windows(x0, x1, self.grid.width)
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
