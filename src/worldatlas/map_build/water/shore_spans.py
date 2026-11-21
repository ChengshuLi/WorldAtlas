"""Read-only coastal spans and exact cell-centre views for selected crops."""

import math
from collections.abc import Sequence

import numpy as np

from worldatlas.map_build.water import shared_nearest as shore


class ShoreSpans:
    """Read shore cell centres from precomputed horizontal runs."""

    width: int
    height: int
    offsets: np.ndarray
    starts: np.ndarray
    ends: np.ndarray
    codes: np.ndarray

    def centers_for_crop(
        self,
        bounds: tuple[int, int, int, int],
        step: float,
        land_codes: Sequence[int] | np.ndarray,
    ) -> dict[str, np.ndarray]:
        """Expand eligible shore runs within a grid window.

        Args:
            bounds: (first_column, end_column, first_row, end_row), possibly
                wrapping at ±180 degrees.
            step: Cell size in degrees.
            land_codes: Owner codes to include.

        Returns:
            Dictionary of arrays with latitude, longitude, and category for
            each shore cell, plus the N-by-3 unit-sphere positions under "mids".
        """
        x0, x1, y0, y1 = bounds
        width, height = self.width, self.height
        if not (
            0 <= y0 < y1 <= height
            and 0 < x1 - x0 <= width
            and math.isfinite(step)
            and step > 0
        ):
            raise ValueError("invalid crop")
        selected = np.asarray(land_codes, dtype=np.uint32)
        latitudes, longitudes, categories = [], [], []
        for y in range(y0, y1):
            first, last = map(int, self.offsets[y : y + 2])
            if first == last:
                continue
            starts, ends, codes = (
                self.starts[first:last],
                self.ends[first:last],
                self.codes[first:last],
            )
            x = x0
            while x < x1:
                xm = x % width
                stop = min(width, xm + x1 - x)
                a, b = (
                    np.searchsorted(ends, xm, side="right"),
                    np.searchsorted(starts, stop, side="left"),
                )
                if a < b:
                    keep = np.isin(codes[a:b], selected)
                    aa = np.maximum(starts[a:b][keep].astype(np.int64), xm) - xm + x
                    bb = np.minimum(ends[a:b][keep].astype(np.int64), stop) - xm + x
                    if len(aa):
                        lengths = bb - aa
                        offsets = np.repeat(np.cumsum(lengths) - lengths, lengths)
                        xx = (
                            np.repeat(aa, lengths)
                            + np.arange(int(lengths.sum()))
                            - offsets
                        )
                        latitudes.append(np.full(len(xx), 90 - (y + 0.5) * step))
                        longitudes.append(
                            ((-180 + (xx + 0.5) * step + 180) % 360) - 180
                        )
                        categories.append(np.repeat(codes[a:b][keep], bb - aa))
                x += stop - xm
        if not latitudes:
            raise ValueError("no participant shorelines in crop")
        lat, lon, category = (
            np.concatenate(latitudes),
            np.concatenate(longitudes),
            np.concatenate(categories),
        )
        return {
            "mids": shore.unit(lat, lon),
            "lat": lat,
            "lon": lon,
            "category": category,
        }
