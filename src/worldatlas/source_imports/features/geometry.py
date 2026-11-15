"""Canonical geographic geometry and atomic storage of source-derived features."""

import hashlib
import json
import math

from psycopg.types.json import Jsonb
from shapely.geometry import shape


def geometry_bytes(geometry):
    """Hash the coordinate representation retained by PostgreSQL JSONB."""
    return json.dumps(
        storage_geometry(geometry),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def geometry_hash(geometry):
    return hashlib.sha256(geometry_bytes(geometry)).hexdigest()


def storage_geometry(geometry):
    # PostgreSQL JSONB stores -0.0 as 0.0. Hash the same coordinates that the
    # database can retain; all other coordinate values remain unchanged.
    def coordinates(value):
        if isinstance(value, (list, tuple)):
            return [coordinates(child) for child in value]
        return 0.0 if type(value) is float and value == 0 else value

    return {
        "type": geometry["type"],
        "coordinates": coordinates(geometry["coordinates"]),
    }


def validate_geometry(geometry):
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


def save_features(database, features, recipe):
    """Save a complete import atomically; existing relationships survive."""
    identifiers = [feature["feature_id"] for feature in features]
    if (
        not identifiers
        or any(not isinstance(value, str) or not value.strip() for value in identifiers)
        or len(set(identifiers)) != len(identifiers)
    ):
        raise ValueError("feature IDs must be nonempty and unique")
    records, hashes = [], {}
    for feature in features:
        validate_geometry(feature["geometry"])
        geometry = storage_geometry(feature["geometry"])
        digest = geometry_hash(geometry)
        hashes[feature["feature_id"]] = digest
        records.append(
            (
                feature["feature_id"],
                feature["source_feature_id"],
                Jsonb(geometry),
                recipe["recipe_id"],
            )
        )
    with database.transaction():
        # Serialize edits of lines in the same assembled seed region.
        database.execute(
            'SELECT r.id FROM atlas.decision_mainland_seed_regions r '
            'WHERE EXISTS (SELECT 1 FROM atlas.decision_mainland_region_segments s '
            'WHERE s.region_id=r.id AND s.boundary_id=ANY(%s)) '
            'ORDER BY r.id FOR UPDATE', (identifiers,),
        ).fetchall()
        with database.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO atlas.source_features "
                "(id,source_feature_id,"
                "geometry,construction_id) "
                "VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (id) DO UPDATE SET "
                "source_feature_id=EXCLUDED.source_feature_id,"
                "geometry=EXCLUDED.geometry,"
                "construction_id=EXCLUDED.construction_id",
                records,
            )
        for feature_id in identifiers:
            _validate_regions(database, feature_id)
    return hashes


def _validate_regions(database, feature_id):
    """Reject edits that break a selected region's joins or polygon validity."""
    from shapely.geometry import Polygon

    regions = database.execute(
        'SELECT DISTINCT region_id FROM atlas.decision_mainland_region_segments '
        'WHERE boundary_id=%s', (feature_id,),
    ).fetchall()
    for (region_id,) in regions:
        rows = database.execute(
            'SELECT s.reverse,coalesce(b.geometry,r.geometry) '
            'FROM atlas.decision_mainland_region_segments s '
            "LEFT JOIN atlas.source_features b ON s.kind='boundary' "
            'AND b.id=s.boundary_id '
            "LEFT JOIN atlas.decision_mainland_closure_routes r ON s.kind='route' "
            'AND r.id=s.route_id '
            'WHERE s.region_id=%s ORDER BY s.ordinal',
            (region_id,),
        ).fetchall()
        ring = []
        for reverse, geometry in rows:
            if geometry is None or geometry.get('type') != 'LineString':
                raise ValueError('region references a missing or non-line feature')
            points = [[float(x), float(y)] for x, y in geometry['coordinates']]
            if reverse:
                points.reverse()
            if len(points) < 2 or (ring and ring[-1] != points[0]):
                raise ValueError('updated boundary does not join its region exactly')
            ring.extend(points if not ring else points[1:])
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError('updated boundary does not form a closed region')
        if not Polygon(ring).is_valid:
            raise ValueError('updated boundary creates an invalid region polygon')
