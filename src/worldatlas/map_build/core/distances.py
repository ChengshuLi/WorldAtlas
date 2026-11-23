"""Find the shortest WGS84 distance between horizontal runs of cells.

The calculation compares possible column gaps, which avoids walking every
pair of cells. Longitude wraps at the edges of the grid.
"""

import math

import numpy as np
from numpy.typing import ArrayLike

from worldatlas.geodesy.wgs84 import MIN_RADIUS, geodesic_distances

# Keep more candidates for the exact calculation when pruning by lower bounds.
CUSHION_M = 1000.0


def run_pairs_batch(
    y: int,
    a: int,
    b: int,
    records: ArrayLike,
    width: int,
    north: float = 90.0,
    *,
    incumbent: float,
) -> tuple[dict[int, float], int]:
    """Compare one run of cells with many reference runs.

    For fixed latitudes, reducing the wrapped longitude gap cannot lengthen
    the shortest path. Each reference run therefore needs only its smallest
    possible gap. A lower bound skips runs that cannot improve the result.

    Args:
        y: Row of the query run.
        a: First column of the query run.
        b: Exclusive end column of the query run.
        records: N-by-4 array of (row, first_column, end_column, code) values.
        width: Number of columns in one full turn.
        north: Latitude of the grid's top edge in degrees.
        incumbent: Finite distance bound in metres used for pruning.

    Returns:
        (closest_by_code, count). The dictionary gives the minimum tested
        distance in metres per reference code. Count is the number of records.

    Raises:
        ValueError: A run, record shape, latitude, or distance bound is invalid.
    """
    if not (
        type(width) is int
        and width >= 2
        and all(type(x) is int for x in (y, a, b))
        and 0 <= a < b <= width
        and y >= 0
        and math.isfinite(incumbent)
        and incumbent >= 0
    ):
        raise ValueError("invalid runs")
    r = np.asarray(records)
    if not len(r):
        return {}, 0
    if r.ndim != 2 or r.shape[1] != 4:
        raise ValueError("invalid records")
    yy = r[:, 0].astype(np.int64)
    left = r[:, 1].astype(np.int64)
    right = r[:, 2].astype(np.int64)
    codes = r[:, 3].astype(np.int64)
    if (
        np.any(yy < 0)
        or np.any(left < 0)
        or np.any(left >= right)
        or np.any(right > width)
        or np.any((codes <= 0) | (codes >= 2**32))
    ):
        raise ValueError("invalid runs")
    step = 360 / width
    lat1 = north - (y + 0.5) * step
    lat2 = north - (yy.astype(float) + 0.5) * step
    if abs(lat1) > 90 or np.any(np.abs(lat2) > 90):
        raise ValueError("invalid latitude")
    gap = np.full(len(r), width, dtype=np.int64)
    for shift in (-width, 0, width):
        gap = np.minimum(
            gap,
            np.maximum(0, np.maximum(left + shift - (b - 1), a - (right - 1 + shift))),
        )
    dl = np.deg2rad(gap * step)
    p1 = math.radians(lat1)
    p2 = np.deg2rad(lat2)
    x = np.cos(p2) * np.sin(dl)
    z = math.cos(p1) * np.sin(p2) - math.sin(p1) * np.cos(p2) * np.cos(dl)
    dot = math.sin(p1) * np.sin(p2) + math.cos(p1) * np.cos(p2) * np.cos(dl)
    angles = np.arctan2(np.hypot(x, z), dot)
    keep = np.flatnonzero(angles * MIN_RADIUS <= incumbent + CUSHION_M)
    if not len(keep):
        return {}, len(r)
    ds = geodesic_distances(0.0, lat1, gap[keep] * step, lat2[keep])
    selected_codes = codes[keep]
    result = {}
    for code in np.unique(selected_codes):
        result[int(code)] = float(np.min(ds[selected_codes == code]))
    return result, len(r)
