"""The global cell-center grid, with longitude wrapping and native row alignment."""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    step: float
    west: float = -180.
    north: float = 90.

    def __post_init__(self):
        if (type(self.width) is not int or type(self.height) is not int
                or self.width <= 0 or self.height <= 0 or not math.isfinite(self.step)
                or self.step <= 0 or abs(self.width * self.step - 360) > 1e-8
                or self.height * self.step > 180 or self.west != -180 or self.north != 90):
            raise ValueError('expected an aligned global longitude/latitude grid')

    @property
    def bounds(self):
        return (0, self.width, 0, self.height)

    def longitude(self, columns):
        return self.west + (np.asarray(columns) % self.width + .5) * self.step

    def latitude(self, rows):
        return self.north - (np.asarray(rows) + .5) * self.step

    def extent(self, bounds):
        x0, x1, y0, y1 = bounds
        if not (0 <= x0 < x1 <= self.width and 0 <= y0 < y1 <= self.height):
            raise ValueError('invalid grid window')
        return (self.west + x0 * self.step, self.north - y1 * self.step,
                self.west + x1 * self.step, self.north - y0 * self.step)
