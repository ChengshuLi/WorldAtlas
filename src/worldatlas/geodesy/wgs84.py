"""Measure distances and sample paths on the WGS84 ellipsoid."""

import math
from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")
MIN_RADIUS = _GEOD.a * (1 - _GEOD.f * (2 - _GEOD.f))
MAX_RADIUS = _GEOD.a / (1 - _GEOD.f)


def unit_sphere(latitudes: ArrayLike, longitudes: ArrayLike) -> np.ndarray:
    """Convert paired coordinates into Cartesian positions on a unit sphere.

    Args:
        latitudes: Latitudes in degrees.
        longitudes: Matching longitudes in degrees.

    Returns:
        N-by-3 float array, one XYZ position per input point.
    """
    lat, lon = np.deg2rad(latitudes), np.deg2rad(longitudes)
    cosine = np.cos(lat)
    return np.column_stack((cosine * np.cos(lon), cosine * np.sin(lon), np.sin(lat)))


def geodesic_distance(first: Sequence[float], second: Sequence[float]) -> float:
    """Measure the shortest distance along the WGS84 surface.

    Args:
        first: First point as (longitude, latitude) in degrees.
        second: Second point in the same format.

    Returns:
        Distance in metres. Coincident points are zero metres apart.

    Raises:
        ValueError: The coordinates do not yield a finite distance.
    """
    lon1, lat1 = first
    lon2, lat2 = second
    value = _GEOD.inv(lon1, lat1, lon2, lat2)[2]
    if not math.isfinite(value):
        raise ValueError("invalid WGS84 coordinates")
    return value


def geodesic_distances(
    lon1: ArrayLike, lat1: ArrayLike, lon2: ArrayLike, lat2: ArrayLike
) -> NDArray[np.float64]:
    """Measure WGS84 surface distances for pairs of points.

    Args:
        lon1: Starting longitudes in degrees.
        lat1: Starting latitudes in degrees.
        lon2: Ending longitudes in degrees.
        lat2: Ending latitudes in degrees.

    Returns:
        A float64 array of distances in metres, in the common broadcast shape
        of the four inputs. For example, length-N starting arrays and scalar
        ending coordinates give N distances to the same point. Invalid
        coordinates can produce NaN values.

    Raises:
        ValueError: The four inputs cannot be broadcast to a common shape.
    """
    lon1, lat1, lon2, lat2 = np.broadcast_arrays(lon1, lat1, lon2, lat2)
    return np.asarray(_GEOD.inv(lon1, lat1, lon2, lat2)[2], dtype=np.float64)


def geodesic(
    first: Sequence[float],
    last: Sequence[float],
    max_step_m: float,
) -> list[tuple[float, float]]:
    """Sample points along a shortest path on the WGS84 surface.

    Args:
        first: Starting (longitude, latitude) in degrees.
        last: Ending (longitude, latitude) in degrees.
        max_step_m: Largest distance allowed between adjacent points, in metres.

    Returns:
        (longitude, latitude) pairs in path order, including both endpoints.

    Raises:
        ValueError: Spacing is nonpositive or nonfinite, or the endpoints
            coincide or do not define a finite path.
    """
    if not math.isfinite(max_step_m) or max_step_m <= 0:
        raise ValueError("positive geodesic spacing is required")
    lon1, lat1 = first
    lon2, lat2 = last
    azimuth, _, length = _GEOD.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(length) or length == 0:
        raise ValueError("distinct finite connector endpoints are required")
    count = max(1, math.ceil(length / max_step_m))
    return (
        [(lon1, lat1)]
        + [
            _GEOD.fwd(lon1, lat1, azimuth, length * i / count)[:2]
            for i in range(1, count)
        ]
        + [(lon2, lat2)]
    )
