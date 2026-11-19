"""Provide WGS84 geodesic calculations and ellipsoid curvature bounds."""

import math

from pyproj import Geod

GEOD = Geod(ellps="WGS84")
MIN_RADIUS = GEOD.a * (1 - GEOD.f * (2 - GEOD.f))
MAX_RADIUS = GEOD.a / (1 - GEOD.f)


def geodesic(first, last, max_step_m):
    """Sample a shortest geodesic on WGS84.

    Args:
        first: Starting ``(longitude, latitude)`` in degrees.
        last: Ending ``(longitude, latitude)`` in degrees.
        max_step_m: Maximum spacing between adjacent points in metres.

    Returns:
        A list of evenly spaced coordinate pairs in path order, including
        both original endpoints.

    Raises:
        ValueError: The spacing is nonpositive or nonfinite, or the
            endpoints coincide or do not define a finite geodesic.
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
