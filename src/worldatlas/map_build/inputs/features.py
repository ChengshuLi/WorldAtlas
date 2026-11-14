"""Validate selected basin geometry and provider identities before processing."""


def affiliation_selection(rule, features):
    """Read current or frozen affiliation data and check its feature references."""
    selection = rule.get('component_selection', rule.get('evidence', {}).get('component_selection'))
    if (not isinstance(selection, dict) or selection.get('combine') not in ('all', 'any')
            or not isinstance(selection.get('conditions'), list) or not selection['conditions']):
        raise ValueError('affiliation needs conditions and an all/any component selection')
    references = set()
    for key in ('conditions', 'exclusions'):
        if not isinstance(selection.get(key, []), list):
            raise ValueError('component selection conditions must be lists')
        for condition in selection.get(key, []):
            if (not isinstance(condition, dict)
                    or condition.get('relation') not in ('point_component', 'intersects_component', 'contains_component')
                    or not isinstance(condition.get('feature_id'), str)):
                raise ValueError('invalid component selection condition')
            references.add(condition['feature_id'])
    assertions = selection.get('source_assertions', [])
    if not isinstance(assertions, list):
        raise ValueError('source assertions must be a list')
    for assertion in assertions:
        if (not isinstance(assertion, dict)
                or any(not isinstance(assertion.get(key), str) for key in ('point_feature_id', 'area_feature_id'))):
            raise ValueError('source assertion needs point and area feature IDs')
        references.update((assertion['point_feature_id'], assertion['area_feature_id']))
    if references - features:
        raise ValueError('component selection refers to a missing feature: ' + str(sorted(references - features)))
    return selection


def feature_geometry(feature, types, *, coordinate_reference='OGC:CRS84'):
    """Read imported geometry in the declared coordinates."""
    geometry = feature.get('geometry')
    if (
        not isinstance(geometry, dict)
        or geometry.get('type') not in types
        or feature.get('coordinate_reference', 'OGC:CRS84') != coordinate_reference
    ):
        raise ValueError(f'feature needs imported geometry in {coordinate_reference}')
    return geometry


def selected_basins(domain):
    """Return basin/feature pairs; reject duplicate active selections."""
    features = {feature['feature_id']: feature for feature in domain['features']}
    if len(features) != len(domain['features']):
        raise ValueError('duplicate geographic feature ID')
    result, identities = [], set()
    for basin in domain['basins']:
        feature = features.get(basin['feature_id'])
        if feature is None:
            raise ValueError('basin refers to a missing geographic feature')
        feature_geometry(feature, ('Polygon', 'MultiPolygon'))
        identity = tuple(
            feature[key] for key in ('source_id', 'source_feature_id')
        )
        if identity in identities:
            raise ValueError('a provider area is selected more than once')
        identities.add(identity)
        result.append((basin, feature))
    return result
