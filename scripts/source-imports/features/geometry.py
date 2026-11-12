"""Canonical geographic geometry and atomic storage of source-derived features."""
import hashlib
import json

from psycopg.types.json import Jsonb
from shapely.geometry import shape


def geometry_bytes(geometry):
    return json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def geometry_hash(geometry):
    return hashlib.sha256(geometry_bytes(geometry)).hexdigest()


def validate_geometry(geometry):
    if (not isinstance(geometry, dict) or set(geometry) != {'type', 'coordinates'}
            or geometry['type'] not in {'Point', 'MultiPoint', 'LineString',
                                        'MultiLineString', 'Polygon', 'MultiPolygon'}):
        raise ValueError('expected a point, line or polygon geometry')
    # JSON rejects non-finite values before GEOS receives them.
    geometry_bytes(geometry)
    result = shape(geometry)
    if result.is_empty or not result.is_valid or result.has_z:
        raise ValueError('expected valid, nonempty two-dimensional geometry')
    return result


def save_features(database, revision, features, recipe):
    """Save a complete import together; unrelated evidence and links survive."""
    identifiers = [feature['feature_id'] for feature in features]
    if (not identifiers or any(not isinstance(value, str) or not value.strip() for value in identifiers)
            or len(set(identifiers)) != len(identifiers)):
        raise ValueError('feature IDs must be nonempty and unique')
    records = []
    for feature in features:
        validate_geometry(feature['geometry'])
        digest = geometry_hash(feature['geometry'])
        evidence = dict(feature.get('evidence', {}), basis=recipe['basis'],
                        construction_ref={'source_id': recipe['recipe_id'],
                                          'version': recipe['recipe_version']})
        records.append((revision, feature['feature_id'], feature['source_id'],
                        feature['source_version'], feature['source_feature_id'],
                        digest, Jsonb(feature['geometry']), 'OGC:CRS84', Jsonb(evidence)))
    with database.transaction():
        with database.cursor() as cursor:
            cursor.executemany(
                'INSERT INTO atlas.decision_features '
                '(revision,feature_id,source_id,source_version,source_feature_id,'
                'geometry_sha256,geometry,coordinate_reference,evidence) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                'ON CONFLICT (revision,feature_id) DO UPDATE SET '
                'source_id=EXCLUDED.source_id,source_version=EXCLUDED.source_version,'
                'source_feature_id=EXCLUDED.source_feature_id,'
                'geometry_sha256=EXCLUDED.geometry_sha256,geometry=EXCLUDED.geometry,'
                'coordinate_reference=EXCLUDED.coordinate_reference,'
                'evidence=atlas.decision_features.evidence || EXCLUDED.evidence', records)
    return {feature['feature_id']: geometry_hash(feature['geometry']) for feature in features}
