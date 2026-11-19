"""Validate the WGS84 GeoJSON used by source imports and map builds."""

import math

from shapely.geometry import shape


def validate_geometry(geometry):
    """Check the supported GeoJSON shape and its finite WGS84 coordinates.

    Args:
        geometry: A point, line, polygon, or corresponding multi-geometry.

    Returns:
        The validated two-dimensional Shapely geometry.

    Raises:
        ValueError: The geometry is empty, malformed, invalid, or out of range.
    """
    if (
        not isinstance(geometry, dict)
        or set(geometry) != {"type", "coordinates"}
        or geometry["type"]
        not in {
            "Point",
            "MultiPoint",
            "LineString",
            "MultiLineString",
            "Polygon",
            "MultiPolygon",
        }
    ):
        raise ValueError("expected a point, line or polygon geometry")

    def coordinates(values):
        if not isinstance(values, (tuple, list)) or not values:
            raise ValueError("geometry coordinates must be nonempty arrays")
        if isinstance(values[0], (tuple, list)):
            for child in values:
                coordinates(child)
        elif len(values) != 2 or any(
            type(value) not in (int, float) or not math.isfinite(value)
            for value in values
        ):
            raise ValueError("expected finite two-dimensional numeric coordinates")
        elif not (-180 <= values[0] <= 180 and -90 <= values[1] <= 90):
            raise ValueError("coordinates are outside WGS84 longitude/latitude ranges")

    coordinates(geometry["coordinates"])
    result = shape(geometry)
    if result.is_empty or not result.is_valid or result.has_z:
        raise ValueError("expected valid, nonempty two-dimensional geometry")
    return result
