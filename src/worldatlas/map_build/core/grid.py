"""The global cell-center grid, with longitude wrapping and native row alignment."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

import numpy as np


def column_windows(first: int, end: int, width: int) -> tuple[tuple[int, int], ...]:
    """Split a window no wider than one turn into ordinary column ranges.

    Args:
        first: First unwrapped column, which can be negative.
        end: Exclusive end column.
        width: Number of columns in the full grid.

    Returns:
        One or two (start, end) ranges in traversal order. For example, a
        width of 8 splits [6, 10) into [6, 8) followed by [0, 2).
    """
    start = first % width
    stop = start + end - first
    if stop <= width:
        return ((start, stop),)
    return ((start, width), (0, stop - width))


@dataclass(frozen=True)
class Grid:
    """Describe a WGS84 grid that starts at 90°N and wraps at ±180°.

    The step is 360 / width degrees. Height counts the rows retained from
    the north. Row zero is the northernmost row.
    """

    width: int
    height: int
    step: float
    west: float = -180.0
    north: float = 90.0

    def __post_init__(self) -> None:
        """Require full longitude coverage and aligned rows starting at 90°N.

        Latitude spans half as many degrees as longitude, so twice the number
        of rows must fit within the number of columns.

        Raises:
            ValueError: The origin, dimensions, or cell step is invalid.
        """
        if (
            type(self.width) is not int
            or type(self.height) is not int
            or self.width <= 0
            or self.height <= 0
            or not math.isfinite(self.step)
            or self.step <= 0
            or self.step != 360 / self.width
            or 2 * self.height > self.width
            or self.west != -180
            or self.north != 90
        ):
            raise ValueError('expected an aligned global longitude/latitude grid')

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Return the full window in grid coordinates.

        Returns:
            (first_column, end_column, first_row, end_row). Ends are exclusive.
        """
        return (0, self.width, 0, self.height)

    def longitude(
        self, columns: int | Sequence[int] | np.ndarray
    ) -> float | np.ndarray:
        """Find the longitude at each given column centre.

        Args:
            columns: Column index or array of column indices. Indices wrap at the
                grid width.

        Returns:
            Longitude in degrees, as a scalar or an array shaped like the input.
        """
        return self.west + (np.asarray(columns) % self.width + 0.5) * self.step

    def latitude(self, rows: int | Sequence[int] | np.ndarray) -> float | np.ndarray:
        """Find the latitude at each given row centre.

        Args:
            rows: Row index or array of row indices, counted from the north.

        Returns:
            Latitude in degrees, as a scalar or an array shaped like the input.
        """
        return self.north - (np.asarray(rows) + 0.5) * self.step

    def cell_at(self, longitude: float, latitude: float) -> tuple[int, int] | None:
        """Locate the cell that contains a geographic point.

        Args:
            longitude: WGS84 longitude in degrees. Both -180 and 180 select column
                zero.
            latitude: WGS84 latitude in degrees. The north edge is included and
                the south edge of the grid is excluded.

        Returns:
            (column, row), or None if the point is outside the retained grid.
        """
        if not (-180 <= longitude <= 180 and -90 < latitude <= 90):
            return None
        step = Fraction(self.step)
        column = (Fraction(longitude) - Fraction(self.west)) // step
        row = (Fraction(self.north) - Fraction(latitude)) // step
        if 2 * self.height == self.width:
            # A rounded step can leave a gap before the exact southern edge
            # of a full-world grid. These points belong to its last row.
            row = min(row, self.height - 1)
        if 0 <= row < self.height:
            # The rounded step can also leave a gap just west of 180°E.
            return (0 if longitude == 180 else min(column, self.width - 1)), row

    def window_for_extent(
        self, extent: tuple[float, float, float, float]
    ) -> tuple[int, int, int, int] | None:
        """Find the grid rows and columns a geographic extent could touch.

        The last row or column can be included when the extent ends exactly
        at its edge. The rasterizer determines which cells are covered.

        A valid extent can lie outside the grid. For example, a polygon south
        of the last retained row has no candidate cells to rasterize.

        Args:
            extent: (west, south, east, north) in degrees, without wrapping.

        Returns:
            (first_column, end_column, first_row, end_row) with exclusive ends,
            clipped to the grid. Return None for an extent with no candidate cells.
        """
        west, south, east, north = extent
        first_column = max(0, math.floor((west - self.west) / self.step))
        end_column = min(self.width, math.floor((east - self.west) / self.step) + 1)
        first_row = max(0, math.floor((self.north - north) / self.step))
        end_row = min(self.height, math.floor((self.north - south) / self.step) + 1)
        if first_column >= end_column or first_row >= end_row:
            return None
        return first_column, end_column, first_row, end_row
