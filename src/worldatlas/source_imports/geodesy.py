"""WGS84 geodesic segments shared by boundary constructors."""

import math

from pyproj import Geod

GEOD = Geod(ellps="WGS84")


def geodesic(first, last, max_step_m):
    """Return points along a shortest WGS84 path between the supplied endpoints.

    Supply ``first`` and ``last`` as ``(longitude, latitude)`` in degrees.
    The returned list preserves both endpoints in order and adds evenly
    spaced points so each step is at most ``max_step_m`` metres.
    """
    if not math.isfinite(max_step_m) or max_step_m <= 0:
        raise ValueError("positive geodesic spacing is required")
    azimuth, _, length = GEOD.inv(*first, *last)
    if not math.isfinite(length) or length == 0:
        raise ValueError("distinct finite connector endpoints are required")
    count = max(1, math.ceil(length / max_step_m))
    return (
        [tuple(first)]
        + [GEOD.fwd(*first, azimuth, length * i / count)[:2] for i in range(1, count)]
        + [tuple(last)]
    )
