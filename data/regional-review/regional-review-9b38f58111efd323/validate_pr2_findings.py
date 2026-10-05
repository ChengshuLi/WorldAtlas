#!/usr/bin/env python3
"""Validate #451 PR2 evidence bindings, scope, parent counts, and source coverage."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(rel):
    return json.loads((ROOT / rel).read_text())

scope = read('scope.json')
assessment = read('assessment.json')
parents = read('findings/area-purpose-parent-assessment.json')
comparison = read('findings/boundary-lineage-comparison.json')
register = read('sources/pr2-source-access-register.json')
ids = scope['member_location_ids']
roster_hash = hashlib.sha256(json.dumps(ids, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
assert len(ids) == len(set(ids)) == 40
assert assessment['scope_count'] == parents['scope_count'] == comparison['scope_count'] == 40
assert parents['scope_ids_sha256'] == roster_hash
assert parents['area_scope'] if 'area_scope' in parents else parents['full_area_inventory_count'] == 125
assert parents['full_area_inventory_count'] == 125 and parents['owned_area_members'] == 40
assert sum(assessment['counts'].values()) == 40
assert len(assessment['rows']) == 40 and {r['id'] for r in assessment['rows']} == set(ids)
assert len(comparison['results']['per_location']) == 40
assert {r['id'] for r in comparison['results']['per_location']} == set(ids)
assert comparison['results']['same_at_4dp'] + comparison['results']['different_at_4dp'] == 40
assert comparison['results']['same_at_4dp'] == 0 and comparison['results']['different_at_4dp'] == 40
assert [(p['atlas_owned_member_count'], p['official_2025_count']) for p in parents['parent_assessments']] == [(13,13),(8,9),(11,11),(8,8)]
assert all(p['disposition'] in {'insufficient-evidence','correction-needed'} for p in parents['parent_assessments'])
assert all(source.get('sha256') is None and source.get('restoration') for source in register['sources'] if source['id'] in {'yunnan-civil-affairs-administrative-setup','yunnan-local-administrative-code-standards-release'})
rows = comparison['results']['per_location']
assert comparison['results']['unique_source_features'] == len({r['source_shape_id'] for r in rows}) == 40
assert comparison['results']['same_at_4dp'] == sum(r['same_geometry_after_coordinate_rounding_to_4dp_and_ring_normalization'] for r in rows)
assert comparison['results']['different_at_4dp'] == sum(not r['same_geometry_after_coordinate_rounding_to_4dp_and_ring_normalization'] for r in rows)
for key, row_key in [('source_parts_total', 'source_polygon_parts'), ('atlas_parts_total', 'atlas_polygon_parts'), ('source_rings_total', 'source_ring_count'), ('atlas_rings_total', 'atlas_ring_count'), ('source_vertices_total', 'source_vertex_count'), ('atlas_vertices_total', 'atlas_vertex_count')]:
    assert comparison['results'][key] == sum(r[row_key] for r in rows)
assert len({r['source_shape_id'] for r in rows}) == 40
assert parents['area_assessment']['disposition'] == 'insufficient-evidence'
assert scope['regional_interiors_approved'] is False and scope['location_attribute_imports_ready'] is False
print(json.dumps({'issue':451,'scope_count':40,'roster_sha256':roster_hash,'source_coverage':len(register['sources']),'parent_counts':[p['atlas_owned_member_count'] for p in parents['parent_assessments']],'lineage_differences':comparison['results']['different_at_4dp'],'status':'passed'},indent=2))
