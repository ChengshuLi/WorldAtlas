"""WGS84 geodesic segments shared by boundary constructors."""

import math

from pyproj import Geod

GEOD = Geod(ellps="WGS84")


def geodesic(first, last, max_step_m):
    """Sample a shortest geodesic, preserving both supplied endpoints."""
    if not math.isfinite(max_step_m) or max_step_m <= 0:
        raise ValueError("positive geodesic spacing is required")
    azimuth, _, length = GEOD.inv(*first, *last)
    if not math.isfinite(length) or length == 0:
        raise ValueError("distinct finite connector endpoints are required")
    count = max(1, math.ceil(length / max_step_m))
    return [tuple(first)] + [
        GEOD.fwd(*first, azimuth, length * i / count)[:2]
        for i in range(1, count)
    ] + [tuple(last)]


def spherical_rhumb_points(points, step_km):
    """Densify rhumb segments straight in spherical Mercator coordinates.

    This matches the interpolated construction lines in IHO S-130 Ed.1.0.0.
    The conservative step bound limits arc length on a sphere of radius 6378137m.
    The original longitude/latitude endpoints are retained exactly.
    """
    if not 0 < step_km <= 1:
        raise ValueError('rhumb max_step_km must be in (0,1]')

    def psi(phi):
        return math.asinh(math.tan(phi))

    dense = []
    for start, end in zip(points, points[1:]):
        if abs(end[0] - start[0]) > 180:
            raise ValueError('antimeridian-crossing rhumb unsupported')
        if abs(start[1]) >= 90 or abs(end[1]) >= 90:
            raise ValueError('rhumb endpoints at a pole unsupported')
        p0, p1 = psi(math.radians(start[1])), psi(math.radians(end[1]))
        dlambda = math.radians(end[0] - start[0])
        # Spherical Mercator's scale is at least one, so planar length is an upper bound.
        bound_m = 6378137.0 * math.hypot(p1 - p0, dlambda)
        count = max(1, math.ceil(bound_m / (1000 * step_km)))
        dense.append(start)
        for i in range(1, count):
            t = i / count
            dense.append(
                (
                    start[0] + (end[0] - start[0]) * t,
                    math.degrees(math.atan(math.sinh(p0 + (p1 - p0) * t))),
                )
            )
    dense.append(points[-1])
    return dense
