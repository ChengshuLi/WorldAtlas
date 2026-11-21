"""Measure distances and sample paths on the WGS84 ellipsoid."""

import math

import numpy as np
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")
MIN_RADIUS = _GEOD.a * (1 - _GEOD.f * (2 - _GEOD.f))
MAX_RADIUS = _GEOD.a / (1 - _GEOD.f)


def geodesic_distance(first, second):
    """Measure the shortest surface distance between two WGS84 points.

    Args:
        first: First ``(longitude, latitude)`` pair in degrees.
        second: Second ``(longitude, latitude)`` pair in degrees.

    Returns:
        The distance in metres, or zero for coincident points.

    Raises:
        ValueError: The points do not yield a finite distance.
    """
    value = _GEOD.inv(*first, *second)[2]
    if not math.isfinite(value):
        raise ValueError("invalid WGS84 coordinates")
    return value


def geodesic_distances(lon1, lat1, lon2, lat2):
    """Measure WGS84 surface distances for a batch of point pairs.

    Args:
        lon1: Starting longitudes in degrees, as a scalar or array.
        lat1: Starting latitudes in degrees, as a scalar or array.
        lon2: Ending longitudes in degrees, as a scalar or array.
        lat2: Ending latitudes in degrees, as a scalar or array.

    Returns:
        A float64 array with one distance in metres at each position in
        the common NumPy shape. For N pairs supplied as four length-N
        arrays, the result has shape (N,). Scalar coordinates can repeat
        across the array, such as one target shared by all starting points.
        Preserve NaN results so callers can apply their own validity rules.

    Raises:
        ValueError: The input shapes cannot be broadcast together.
    """
    lon1, lat1, lon2, lat2 = np.broadcast_arrays(lon1, lat1, lon2, lat2)
    return np.asarray(_GEOD.inv(lon1, lat1, lon2, lat2)[2], dtype=np.float64)


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
    azimuth, _, length = _GEOD.inv(*first, *last)
    if not math.isfinite(length) or length == 0:
        raise ValueError("distinct finite connector endpoints are required")
    count = max(1, math.ceil(length / max_step_m))
    return (
        [tuple(first)]
        + [_GEOD.fwd(*first, azimuth, length * i / count)[:2] for i in range(1, count)]
        + [tuple(last)]
    )
