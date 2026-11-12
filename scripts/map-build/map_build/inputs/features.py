"""Validate selected basin geometry and provider identities before processing."""
import hashlib
import json


def selected_basins(domain):
    """Return basin/feature pairs; reject duplicate or nested active selections."""
    features = {feature['feature_id']: feature for feature in domain['features']}
    if len(features) != len(domain['features']):
        raise ValueError('duplicate geographic feature ID')
    result, identities = [], set()
    for basin in domain['basins']:
        feature = features.get(basin['feature_id'])
        if feature is None:
            raise ValueError('basin refers to a missing geographic feature')
        geometry = feature.get('geometry')
        if (not isinstance(geometry, dict) or geometry.get('type') not in ('Polygon', 'MultiPolygon')
                or feature.get('coordinate_reference') != 'OGC:CRS84'):
            raise ValueError('basin needs imported WGS84 longitude/latitude polygon geometry')
        digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                                          ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        if digest != feature['geometry_sha256'] or digest != basin['geometry_sha256']:
            raise ValueError('basin geometry checksum differs from its selected feature')
        identity = tuple(feature[key] for key in ('source_id', 'source_version', 'source_feature_id'))
        if identity in identities:
            raise ValueError('a provider area is selected more than once')
        identities.add(identity)
        result.append((basin, feature))
    for _, feature in result:
        for parent in feature.get('evidence', {}).get('source_parent_feature_ids', []):
            if (feature['source_id'], feature['source_version'], parent) in identities:
                raise ValueError('a basin and its provider parent cannot both be active')
    return result
