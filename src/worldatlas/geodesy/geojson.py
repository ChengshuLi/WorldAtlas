"""Validate the WGS84 GeoJSON used by source imports and map builds."""

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, TypeAdapter
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from typing_extensions import TypedDict

from worldatlas.shared.files import JSONValue


def _coordinate_array(value: JSONValue) -> list[JSONValue] | tuple[JSONValue, ...]:
    """Require an ordered array of coordinates.

    Args:
        value: Coordinate input. JSON arrays are lists, and Python importers
            can also supply tuples.

    Returns:
        The input list or tuple.

    Raises:
        ValueError: The input is neither a list nor a tuple.
    """
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected a coordinate array")
    return value


type Coordinates[Item] = Annotated[
    list[Item], BeforeValidator(_coordinate_array), Field(min_length=1)
]
type Longitude = Annotated[float, Field(strict=True, ge=-180, le=180)]
type Latitude = Annotated[float, Field(strict=True, ge=-90, le=90)]
type Position = Annotated[
    tuple[Longitude, Latitude], BeforeValidator(_coordinate_array)
]


class Geometry[Kind: str, Coordinates](TypedDict, closed=True):
    """Record the GeoJSON type and coordinate arrays for one geometry."""

    type: Kind
    coordinates: Coordinates


type GeoJSONGeometry[PointCoordinates = list[float]] = Annotated[
    Geometry[Literal["Point"], PointCoordinates]
    | Geometry[Literal["MultiPoint", "LineString"], Coordinates[PointCoordinates]]
    | Geometry[
        Literal["MultiLineString", "Polygon"],
        Coordinates[Coordinates[PointCoordinates]],
    ]
    | Geometry[
        Literal["MultiPolygon"], Coordinates[Coordinates[Coordinates[PointCoordinates]]]
    ],
    Field(discriminator="type"),
]

_GEOMETRY = TypeAdapter(GeoJSONGeometry[Position])


def validate_geometry(geometry: Mapping[str, JSONValue]) -> BaseGeometry:
    """Read two-dimensional WGS84 GeoJSON and check the resulting shape.

    Args:
        geometry: Dictionary with "type" and "coordinates". Each coordinate pair
            is (longitude, latitude) in degrees.

    Returns:
        The validated Shapely geometry.

    Raises:
        ValueError: The input fields, coordinates, or geometry are invalid.
    """
    result = shape(dict(_GEOMETRY.validate_python(geometry)))
    if not result.is_valid:
        raise ValueError("expected valid geometry")
    return result
