"""Shared WGS84 ellipsoid and conservative global metric bounds."""
from pyproj import Geod

A = 6378137.
F = 1 / 298.257223563
MIN_RADIUS = A * (1 - F * (2 - F))
MAX_RADIUS = A / (1 - F)
GEOD = Geod(a=A, f=F)
# Existing conservative cushion for spherical broad-phase calculations.
CUSHION_M = 1000.
