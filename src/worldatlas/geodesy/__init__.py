"""Share WGS84 geodesic calculations and ellipsoid bounds."""

from .wgs84 import GEOD, MAX_RADIUS, MIN_RADIUS, geodesic

__all__ = ["GEOD", "MAX_RADIUS", "MIN_RADIUS", "geodesic"]
