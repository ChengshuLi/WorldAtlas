"""Canonical geographic geometry and atomic storage of source-derived features."""
import hashlib
import json
import math

from psycopg.types.json import Jsonb
from shapely.geometry import shape


def geometry_bytes(geometry):
    """Hash the coordinate representation retained by PostgreSQL JSONB."""
    return json.dumps(storage_geometry(geometry), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def geometry_hash(geometry):
    return hashlib.sha256(geometry_bytes(geometry)).hexdigest()


def storage_geometry(geometry):
    # PostgreSQL JSONB stores -0.0 as 0.0. Hash the same coordinates that the
    # database can retain; all other coordinate values remain unchanged.
    def coordinates(value):
        if isinstance(value, (list, tuple)):
            return [coordinates(child) for child in value]
        return 0.0 if type(value) is float and value == 0 else value
    return {'type': geometry['type'], 'coordinates': coordinates(geometry['coordinates'])}


def validate_geometry(geometry, coordinate_reference='OGC:CRS84'):
    if (not isinstance(geometry, dict) or set(geometry) != {'type', 'coordinates'}
            or geometry['type'] not in {'Point', 'MultiPoint', 'LineString',
                                        'MultiLineString', 'Polygon', 'MultiPolygon'}):
        raise ValueError('expected a point, line or polygon geometry')
    def coordinates(values):
        if not isinstance(values, (tuple, list)) or not values:
            raise ValueError('geometry coordinates must be nonempty arrays')
        if isinstance(values[0], (tuple, list)):
            for child in values:
                coordinates(child)
        elif (len(values) != 2 or any(type(value) not in (int, float)
                                     or not math.isfinite(value) for value in values)):
            raise ValueError('expected finite two-dimensional numeric coordinates')
        elif coordinate_reference == 'OGC:CRS84' and not (-180 <= values[0] <= 180 and -90 <= values[1] <= 90):
            raise ValueError('coordinates are outside WGS84 longitude/latitude ranges')
    coordinates(geometry['coordinates'])
    result = shape(geometry)
    if result.is_empty or not result.is_valid or result.has_z:
        raise ValueError('expected valid, nonempty two-dimensional geometry')
    return result


def save_features(database, features, recipe):
    """Save a complete import together; unrelated evidence and links survive."""
    identifiers = [feature['feature_id'] for feature in features]
    if (not identifiers or any(not isinstance(value, str) or not value.strip() for value in identifiers)
            or len(set(identifiers)) != len(identifiers)):
        raise ValueError('feature IDs must be nonempty and unique')
    records, hashes = [], {}
    for feature in features:
        reference = feature.get('coordinate_reference', 'OGC:CRS84')
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError('feature coordinate reference is required')
        validate_geometry(feature['geometry'], reference)
        geometry = storage_geometry(feature['geometry'])
        digest = geometry_hash(geometry)
        hashes[feature['feature_id']] = digest
        evidence = dict(feature.get('evidence', {}), basis=recipe['basis'])
        records.append((feature['feature_id'], feature['source_id'], feature['source_feature_id'],
                        digest, Jsonb(geometry), reference, Jsonb(evidence),
                        recipe['recipe_id']))
    with database.transaction():
        with database.cursor() as cursor:
            cursor.executemany(
                'INSERT INTO atlas.decision_features '
                '(feature_id,source_id,source_feature_id,'
                'geometry_sha256,geometry,coordinate_reference,evidence,construction_id) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s) '
                'ON CONFLICT (feature_id) DO UPDATE SET '
                'source_id=EXCLUDED.source_id,'
                'source_feature_id=EXCLUDED.source_feature_id,'
                'geometry_sha256=EXCLUDED.geometry_sha256,geometry=EXCLUDED.geometry,'
                'coordinate_reference=EXCLUDED.coordinate_reference,'
                'construction_id=EXCLUDED.construction_id,'
                'evidence=atlas.decision_features.evidence || EXCLUDED.evidence', records)
    return hashes
