"""Prepare an in-memory, derived view of a pinned mainland snapshot.

This does not authenticate the gate report or write a Neon snapshot. The caller
must independently pin and verify the original bytes, raw source files and code.
"""
import copy
import hashlib
import json

from caucasus_seed_gate import BOUNDARY, assembled_region_hash


def geomhash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def derive(snapshot, derived_geometry, gate_report, original_snapshot_sha256):
    if gate_report.get('schema') != 'caucasus-source-seed-gate-v1' or gate_report.get('snapshot_sha256') != original_snapshot_sha256:
        raise ValueError('gate report does not reference the authenticated snapshot')
    if not isinstance(derived_geometry, dict) or set(derived_geometry) != {'type', 'coordinates'} or derived_geometry['type'] != 'LineString':
        raise ValueError('invalid derived geometry')
    original = [b for b in snapshot.get('mainland_boundaries', []) if b.get('boundary_id') == BOUNDARY]
    if len(original) != 1:
        raise ValueError('expected one selected boundary')
    boundary = original[0]
    normal = {'type': 'LineString', 'coordinates': [[float(x), float(y)] for x, y in boundary['geometry']['coordinates']]}
    if geomhash(normal) != boundary.get('geometry_sha256') or gate_report.get('selected_geometry_sha256') != boundary.get('geometry_sha256'):
        raise ValueError('selected boundary digest mismatch')
    decision = boundary.get('provenance', {}).get('source_assembly_v1', {})
    if decision.get('recipe_sha256') != gate_report.get('recipe_sha256'):
        raise ValueError('selected recipe mismatch')
    new_hash = geomhash(derived_geometry)
    if new_hash != gate_report.get('assembly', {}).get('geometry_sha256'):
        raise ValueError('derived boundary does not match gate result')
    if normal['coordinates'][0] != derived_geometry['coordinates'][0] or normal['coordinates'][-1] != derived_geometry['coordinates'][-1]:
        raise ValueError('derived line changes a closure endpoint')
    effective = copy.deepcopy(snapshot)
    before = {('boundary', b['boundary_id']): b for b in snapshot['mainland_boundaries']}
    before.update({('route', r['route_id']): r for r in snapshot['routes']})
    after = {('boundary', b['boundary_id']): b for b in effective['mainland_boundaries']}
    after.update({('route', r['route_id']): r for r in effective['routes']})
    target = after[('boundary', BOUNDARY)]
    target['geometry'] = copy.deepcopy(derived_geometry)
    target['geometry_sha256'] = new_hash
    changes = []
    for old, new in zip(snapshot['seed_regions'], effective['seed_regions']):
        if not any(x.get('kind') == 'boundary' and x.get('id') == BOUNDARY for x in old['segments']):
            continue
        old_hash = assembled_region_hash(old, before)
        if old_hash != old['geometry_sha256']:
            raise ValueError('selected region digest mismatch')
        updated_hash = assembled_region_hash(new, after)
        new['geometry_sha256'] = updated_hash
        changes.append({'region_id': old['region_id'], 'selected_sha256': old_hash, 'derived_sha256': updated_hash})
    if not changes:
        raise ValueError('no selected region consumes the boundary')
    return effective, {'schema': 'caucasus-effective-snapshot-v1',
                       'original_snapshot_sha256': original_snapshot_sha256,
                       'selected_geometry_sha256': boundary['geometry_sha256'],
                       'derived_geometry_sha256': new_hash, 'regions': changes}
