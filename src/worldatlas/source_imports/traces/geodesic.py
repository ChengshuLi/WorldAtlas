"""Connect reviewed source-figure points with WGS84 geodesics."""

import math

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.geodesy.wgs84 import geodesic
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import save_features


def construct(points, max_step_metres):
    """Sample the geodesic segments connecting consecutive control points.

    Args:
        points: Ordered WGS84 longitude and latitude pairs.
        max_step_metres: Maximum spacing between adjacent output vertices.

    Returns:
        A GeoJSON LineString that includes every supplied control point.

    Raises:
        ValueError: The points or spacing do not define a valid simple trace.
    """
    if (type(max_step_metres) not in (int, float)
            or not math.isfinite(max_step_metres) or max_step_metres <= 0):
        raise ValueError("max_step_metres must be a finite positive number")
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError("at least two control points are required")
    # Validate the control coordinates before sampling. The crossing check
    # belongs on the sampled line because geodesics can curve in longitude
    # and latitude.
    validate_geometry({"type": "LineString", "coordinates": points})
    coordinates = []
    seen_segments = set()
    for first, last in zip(points, points[1:]):
        # Sampling the same geodesic in reverse can differ by floating-point
        # roundoff. Check the unordered endpoints to catch an exact retrace.
        endpoints = frozenset((tuple(first), tuple(last)))
        if endpoints in seen_segments:
            raise ValueError("boundary trace must not cross or retrace itself")
        seen_segments.add(endpoints)
        segment = geodesic(first, last, max_step_metres)
        coordinates.extend(segment if not coordinates else segment[1:])
    if any(abs(a[0] - b[0]) > 180 for a, b in zip(coordinates, coordinates[1:])):
        raise ValueError("longitude-seam crossings need split source geometry")
    geometry = {"type": "LineString", "coordinates": [list(p) for p in coordinates]}
    if not validate_geometry(geometry).is_simple:
        raise ValueError("boundary trace must not cross or retrace itself")
    return geometry


def geodesic_trace(
    runtime: Runtime,
    *,
    source_ids: list[SourceId],
    feature_id: NonEmptyText,
    points: list[tuple[float, float]],
    max_step_metres: float,
):
    """Save the WGS84 trace of reviewed source-figure control points.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_ids: Distinct catalog IDs for the supporting source figures.
        feature_id: Output feature ID in Neon.
        points: Ordered WGS84 longitude and latitude pairs.
        max_step_metres: Maximum spacing between adjacent output vertices.

    Returns:
        Saved feature ID and vertex count.

    Raises:
        ValueError: The trace is invalid, a cited source is missing or
            repeated, or the geometry cannot be saved for the current recipe.
    """
    if not source_ids or len(set(source_ids)) != len(source_ids):
        raise ValueError("trace sources must be nonempty and distinct")
    geometry = construct(points, max_step_metres)
    acquire_sources(runtime, [], evidence_source_ids=source_ids)
    save_features(runtime, [dict(feature_id=feature_id, geometry=geometry)])
    return dict(feature_id=feature_id, vertices=len(geometry['coordinates']))
