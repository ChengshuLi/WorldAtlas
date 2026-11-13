"""Apply selected line, geographic-group and direct-satellite island rules."""
import hashlib
import json

from shapely.geometry import Point, shape

from map_build.core.distances import run_pair
from map_build.inputs.features import feature_geometry
from map_build.land.line_groups import LatitudeLine, buffered_bounds, collect_runs, resolve_sides, scan_components
from map_build.land.satellites import apply_satellites
from map_build.land.source_groups import apply_groups


def resolve_islands(policy, line_record, features, sources, components, selected_entities, bindings, *, protected=()):
    """Resolve complete current components from structured geographic choices.

    Source imports provide point and polygon geometry. The policy identifies
    line sides, scope, source groups, source-backed anchors and distance rules.
    Groups establish their targets before the single direct-satellite pass.
    """
    codes = {b['entity_id']: b['code'] for b in bindings if b['physical_class'] == 'land'}
    features = {f['feature_id']: f for f in features}
    sources = {(s['source_id'], s['version']): s for s in sources}
    geometry = line_record['geometry']
    checksum = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                                         ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    if checksum != line_record['geometry_sha256'] or line_record['line_id'] != policy['line_id']:
        raise ValueError('selected geographic line identity or geometry differs')
    line = LatitudeLine(geometry, policy['boundary_tolerance_degrees'])
    scope = policy['bounds_lon_lat']
    satellite = policy['satellite_policy']
    region = scan_components(components, scope, line)
    buffer = scan_components(components, buffered_bounds(scope, satellite['max_gap_m'] + satellite['tie_m']), line)
    selected = {root: codes[entity] for root, entity in selected_entities.items()}
    side_codes = {side: codes[entity] for side, entity in policy['side_entity_ids'].items()}
    result = resolve_sides(buffer, selected, side_codes, protected=protected)
    result['competitor_targets'] = {r: c for r, c in selected.items() if r in buffer}
    windows, explicit_anchors = [], {}

    def source_anchor(feature, code, description):
        source = sources[feature['source_id'], feature['source_version']]
        return dict(code=code, source_id=feature['source_id'], source_version=feature['source_version'],
                    source_feature_id=feature['source_feature_id'], source_sha256=source['sha256'],
                    main_island_evidence=description)

    for group in policy['groups']:
        code = codes[group['target_entity_id']]
        if group['mode'] == 'geographic_extent':
            members = scan_components(components, group['bounds_lon_lat'], line)
        elif group['mode'] == 'source_features':
            members = {}
            for item in group['members']:
                area = features[item['area_feature_id']]
                polygon = feature_geometry(area, ('Polygon', 'MultiPolygon'))
                if item.get('point_feature_id'):
                    witness = features[item['point_feature_id']]
                    point = feature_geometry(witness, ('Point',))['coordinates']
                else:
                    point = item['coordinates']
                    witness = dict(source_id=item['source_id'], source_version=item['source_version'],
                                   source_feature_id=item['source_feature_id'])
                if not shape(polygon).contains(Point(point)):
                    raise ValueError('selected named group witness is outside its source area')
                root = components.component_at(*point)
                counts = components.profile(polygon)
                whole = {r: dict(total=buffer[r]['total'], in_scope=buffer[r]['total'])
                         for r, count in counts.items() if r in buffer
                         and buffer[r]['in_scope'] == buffer[r]['total'] == count}
                if root not in whole:
                    raise ValueError('named group witness needs complete source-area and component coverage')
                members.update(whole)
                if item.get('anchor'):
                    if root in explicit_anchors:
                        raise ValueError('two selected group anchors resolve to one component')
                    explicit_anchors[root] = source_anchor(witness, code, 'Selected source-named group witness.')
        else:
            raise ValueError('unsupported geographic group selection')
        windows.append(dict(group_id=group['group_id'], code=code, components=members,
                            source=group.get('source', {})))
    # Anchor eligibility comes from independent affiliations or line sides.
    # A source-group change cannot create a new implicit anchor.
    anchors = {}
    for ident in sorted(policy['anchor_feature_ids']):
        feature = features[ident]
        point = feature_geometry(feature, ('Point',))['coordinates']
        root = components.component_at(*point)
        if (root not in buffer or buffer[root]['total'] <= satellite['max_satellite_cells']
                or root not in result['proposals'] or root in anchors):
            continue
        proposal = result['proposals'][root]
        if proposal['basis'] not in policy['anchor_assignment_bases']:
            continue
        anchors[root] = source_anchor(feature, proposal['code'], 'Source island point on an independently assigned component.')
    result = apply_groups(result, windows)
    anchors = {root: anchor for root, anchor in anchors.items()
               if root not in result['review'] and result['proposals'].get(root, {}).get('code') == anchor['code']}
    for root, anchor in explicit_anchors.items():
        proposal = result['proposals'].get(root)
        if root not in result['review'] and proposal and proposal['code'] == anchor['code']:
            anchors[root] = anchor
    runs = collect_runs(components, buffer)
    result = apply_satellites(result, buffer, runs, anchors, run_pair,
        width=components.grid.width, north=components.grid.north,
        max_satellite_cells=satellite['max_satellite_cells'], max_gap_m=satellite['max_gap_m'],
        tie_m=satellite['tie_m'], candidate_roots=set(region),
        allow_anchored_over_unknown_nearer=satellite['allow_anchored_over_unknown_nearer'])
    result['proposals'] = {r: p for r, p in result['proposals'].items() if r in region}
    result['review'] = {r: p for r, p in result['review'].items() if r in region}
    for witness in policy.get('side_witnesses', []):
        root = components.component_at(*witness['coordinates'])
        item = region.get(root)
        side = witness['side']
        if (item is None or item['in_scope'] != item['total'] or item[side] != item['total']
                or result['proposals'].get(root, {}).get('code') != side_codes[side]):
            raise ValueError('selected whole-component line-side witness is not satisfied')
    entities = {code: entity for entity, code in codes.items()}
    result['source_anchors'] = anchors
    result['regional_roots'] = len(region)
    result['buffer_roots'] = len(buffer)
    result['component_entities'] = {root: entities[p['code']] for root, p in result['proposals'].items()}
    return result
