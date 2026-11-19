"""Connect reviewed source-figure points with WGS84 geodesics."""

import math

from worldatlas.source_imports.features.geometry import validate_geometry
from worldatlas.geodesy.wgs84 import geodesic


def construct(points, max_step_metres):
    """Keep every control point; sampling adds coordinates along each segment."""
    if (type(max_step_metres) not in (int, float)
            or not math.isfinite(max_step_metres) or max_step_metres <= 0):
        raise ValueError("max_step_metres must be a finite positive number")
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError("at least two control points are required")
    if not validate_geometry({"type": "LineString", "coordinates": points}).is_simple:
        raise ValueError("boundary trace must not cross or retrace itself")
    coordinates = []
    for first, last in zip(points, points[1:]):
        segment = geodesic(first, last, max_step_metres)
        coordinates.extend(segment if not coordinates else segment[1:])
    if any(abs(a[0] - b[0]) > 180 for a, b in zip(coordinates, coordinates[1:])):
        raise ValueError("longitude-seam crossings need split source geometry")
    geometry = {"type": "LineString", "coordinates": [list(p) for p in coordinates]}
    if not validate_geometry(geometry).is_simple:
        raise ValueError("boundary trace must not cross or retrace itself")
    return geometry
