"""Validate the WGS84 GeoJSON used by source imports and map builds."""

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import AfterValidator, BeforeValidator, Field, TypeAdapter
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


def _closed_ring[PointCoordinates](
    points: list[PointCoordinates],
) -> list[PointCoordinates]:
    """Check that the ring includes its closing vertex.

    Args:
        points: Positions in ring order, including the repeated first point.

    Returns:
        The same list of positions.

    Raises:
        ValueError: The first and last positions differ.
    """
    if points[0] != points[-1]:
        raise ValueError("polygon rings must be closed")
    return points


type Ring[PointCoordinates] = Annotated[
    Coordinates[PointCoordinates], Field(min_length=4), AfterValidator(_closed_ring)
]


class Geometry[Kind: str, Coordinates](TypedDict, closed=True):
    """Record the GeoJSON type and coordinate arrays for one geometry."""

    type: Kind
    coordinates: Coordinates


type Point[PointCoordinates = Position] = Geometry[Literal["Point"], PointCoordinates]
type Polygon[PointCoordinates = Position] = Geometry[
    Literal["Polygon"], Coordinates[Ring[PointCoordinates]]
]

type GeoJSONGeometry[PointCoordinates = list[float]] = Annotated[
    Point[PointCoordinates]
    | Geometry[Literal["MultiPoint", "LineString"], Coordinates[PointCoordinates]]
    | Geometry[Literal["MultiLineString"], Coordinates[Coordinates[PointCoordinates]]]
    | Polygon[PointCoordinates]
    | Geometry[
        Literal["MultiPolygon"], Coordinates[Coordinates[Ring[PointCoordinates]]]
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
