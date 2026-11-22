"""Validate the WGS84 GeoJSON used by source imports and map builds."""

import math
from collections.abc import Mapping

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from worldatlas.shared.files import JSONValue


def validate_geometry(geometry: Mapping[str, JSONValue]) -> BaseGeometry:
    """Check that a GeoJSON geometry is valid in two-dimensional WGS84.

    Args:
        geometry: Dictionary with "type" and "coordinates". Each coordinate pair
            is (longitude, latitude) in degrees.

    Returns:
        A Shapely point, line, polygon, or corresponding multi-geometry.

    Raises:
        ValueError: The geometry is empty, malformed, invalid, or out of range.
    """
    if (
        not isinstance(geometry, dict)
        or set(geometry) != {"type", "coordinates"}
        or geometry["type"]
        not in (
            "Point",
            "MultiPoint",
            "LineString",
            "MultiLineString",
            "Polygon",
            "MultiPolygon",
        )
    ):
        raise ValueError("expected a point, line or polygon geometry")

    def coordinates(values: JSONValue) -> None:
        """Check nested coordinate arrays down to each longitude and latitude pair.

        Args:
            values: Coordinates belonging to a GeoJSON geometry.

        Raises:
            ValueError: A coordinate is missing, nonfinite, or outside WGS84.
        """
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
