"""Bind a direct cut to selected, pinned snapshot and physical-component evidence.

These checks establish internal consistency, not Neon authentication or approval.
"""
import hashlib
import json
import math
from osgeo import ogr


def need(value, message):
    if not value:
        raise ValueError(message)


def unique(items, key, identity):
    need(isinstance(items, list), 'missing records: ' + key)
    matches = [x for x in items if isinstance(x, dict) and x.get(key) == identity]
    need(len(matches) == 1, 'missing or duplicate selected record: ' + key)
    return matches[0]


def selected_cut(snapshot, witness_report, snapshot_sha, component_hashes, rule_id, boundary_id, grid):
    need(snapshot.get('source') == 'neon-export', 'snapshot is not a Neon export')
    revision = snapshot.get('decision_revision', {})
    entity_revision = snapshot.get('entity_revision', {})
    need(revision.get('status') == entity_revision.get('status') == 'draft'
         and revision.get('id') and revision.get('entity_revision') == entity_revision.get('id'),
         'matching draft decision and entity revisions required')
    need(witness_report.get('schema') == 'mainland-witness-resolution-v1'
         and witness_report.get('status') == 'selected-research-identity-claims-not-mainland-proof'
         and witness_report.get('snapshot_sha256') == snapshot_sha
         and witness_report.get('decision_revision') == revision['id']
         and witness_report.get('entity_revision') == entity_revision['id']
         and witness_report.get('grid') == grid, 'witness lineage mismatch')
    need(all(witness_report.get('input_sha256', {}).get(k) == v
             for k, v in component_hashes.items()), 'component lineage mismatch')
    rule = unique(snapshot.get('mainland_component_rules'), 'rule_id', rule_id)
    need(rule.get('execution_status') == 'selected_for_research'
         and rule.get('decision_revision') == revision['id'] and rule.get('region_id'),
         'selected split rule required')
    region = unique(snapshot.get('seed_regions'), 'region_id', rule['region_id'])
    boundary = unique(snapshot.get('mainland_boundaries'), 'boundary_id', boundary_id)
    for record in (region, boundary):
        need(record.get('execution_status') == 'selected_for_research'
             and record.get('decision_revision') == revision['id'], 'unselected or stale record')
    need(boundary.get('method') == 'stored_linestring_v1' and boundary.get('coordinate_reference') == 'OGC:CRS84'
         and boundary.get('geometry_hash_method') == 'binary64-sorted-compact-geojson-v1',
         'unsupported boundary representation')
    geometry = boundary.get('geometry', {})
    coords = geometry.get('coordinates') if isinstance(geometry,dict) and set(geometry)=={'type','coordinates'} and geometry.get('type') == 'LineString' else None
    need(isinstance(coords, list) and 2 <= len(coords) <= 100000, 'invalid source line')
    need(all(isinstance(p, list) and len(p) == 2 and all(type(v) in (int, float, str)
             and len(str(v)) <= 80 for v in p) for p in coords), 'invalid line coordinate')
    try:
        line = [[float(v) for v in p] for p in coords]
    except (ValueError, OverflowError):
        raise ValueError('invalid line coordinate') from None
    need(all(math.isfinite(p[0]) and math.isfinite(p[1]) and -180 <= p[0] <= 180
             and -90 <= p[1] <= 90 for p in line), 'invalid line coordinate')
    need(all(a != b and abs(a[0] - b[0]) <= 180 for a, b in zip(line, line[1:])), 'degenerate or wrapped line')
    obj = {'type': 'LineString', 'coordinates': line}
    data = json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    need(hashlib.sha256(data).hexdigest() == boundary.get('geometry_sha256'), 'boundary geometry hash mismatch')
    geom = ogr.CreateGeometryFromJson(json.dumps(obj))
    need(geom is not None and geom.IsSimple(), 'self-intersecting boundary')
    segs = [x for x in region.get('segments', []) if x.get('kind') == 'boundary']
    need(len(segs) == 1 and segs[0].get('id') == boundary_id, 'exactly one selected boundary is supported')
    need(segs[0].get('start') == 0 and segs[0].get('end') == len(line)
         and type(segs[0].get('reverse')) is bool, 'split must use full selected boundary')
    group = unique(witness_report.get('groups'), 'group_id', rule.get('group_id'))
    need(group.get('role') == 'mainland' and type(group.get('component_id_current_generation_only')) is int,
         'mainland component witness required')
    ids = (rule.get('inside_entity_id'), rule.get('outside_entity_id'))
    need(all(type(x) is int for x in ids) and ids[0] != ids[1]
         and isinstance(group.get('target_entity_ids'), list) and len(group['target_entity_ids']) == 2
         and set(ids) == set(group['target_entity_ids']), 'witness target mismatch')
    bindings = snapshot.get('category_bindings', [])
    codes = []
    for entity in ids:
        matches = [b.get('code') for b in bindings if b.get('entity_id') == entity and b.get('physical_class') == 'land']
        need(len(matches) == 1 and type(matches[0]) is int and 0 < matches[0] < 2**32, 'invalid land binding')
        codes.append(matches[0])
    need(codes[0] != codes[1] and isinstance(region.get('witnesses'), list) and region['witnesses'],
         'invalid split bindings or witnesses')
    return {'line': line, 'inside_code': codes[0], 'outside_code': codes[1],
            'component': group['component_id_current_generation_only'], 'witnesses': region['witnesses'],
            'boundary_sha256': boundary['geometry_sha256']}
