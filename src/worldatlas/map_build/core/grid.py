"""The global cell-center grid, with longitude wrapping and native row alignment."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

import numpy as np


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
            or self.height * self.step > 180
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
            latitude: WGS84 latitude in degrees.

        Returns:
            (column, row), or None if the point is outside the retained grid.
        """
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            return None
        step = Fraction(self.step)
        # Keep the last representable longitude west of 180 in the last column.
        column = (Fraction(longitude) - Fraction(self.west)) // step
        row = (Fraction(self.north) - Fraction(latitude)) // step
        if 0 <= row < self.height:
            return (0 if longitude == 180 else column), row

    def extent(
        self, bounds: tuple[int, int, int, int]
    ) -> tuple[float, float, float, float]:
        """Find the outside edges of a grid window in degrees.

        Args:
            bounds: (first_column, end_column, first_row, end_row), with exclusive
                ends.

        Returns:
            (west, south, east, north) in WGS84 degrees.

        Raises:
            ValueError: The window is empty or falls outside the grid.
        """
        x0, x1, y0, y1 = bounds
        if not (0 <= x0 < x1 <= self.width and 0 <= y0 < y1 <= self.height):
            raise ValueError('invalid grid window')
        return (
            self.west + x0 * self.step,
            self.north - y1 * self.step,
            self.west + x1 * self.step,
            self.north - y0 * self.step,
        )
