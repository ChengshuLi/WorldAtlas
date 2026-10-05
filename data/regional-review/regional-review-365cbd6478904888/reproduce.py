#!/usr/bin/env python3
"""Reproduce the exact-scope/source identity audit for GitHub issue #449.

This verifies batch membership and correspondence to the pinned 2017 gbOpen file.
It cannot certify current legal boundaries or current administrative status.
"""
import hashlib, json, re, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ISSUE = json.loads((ROOT / 'issue-api-snapshot.json').read_text())
BODY = ISSUE['body']
SCOPE = next(json.loads(m.group(1)) for m in re.finditer(r'```json\n(.*?)\n```', BODY, re.S)
             if 'member_location_ids' in json.loads(m.group(1)))
ids = SCOPE['member_location_ids']
assert len(ids) == SCOPE['location_count'] == 228
assert len(set(ids)) == len(ids)
assert hashlib.sha256(('\n'.join(sorted(ids))).encode()).hexdigest() == SCOPE['member_location_ids_sha256']

features = {}
for part in ('part-3.json', 'part-4.json'):
    doc = json.loads((ROOT / '../../geography' / part).resolve().read_text())
    for f in doc['features']:
        props = f['properties']
        if props.get('id') in ids:
            assert props['id'] not in features
            features[props['id']] = f
assert set(features) == set(ids)

source_path = ROOT / 'source/geoBoundaries-CHN-ADM2.geojson'
meta_path = ROOT / 'source/geoBoundaries-CHN-ADM2-metaData.json'
source = json.loads(source_path.read_text())
meta = json.loads(meta_path.read_text())
source_by_id = {}
for f in source['features']:
    sid = f['properties']['shapeID']
    assert sid not in source_by_id
    source_by_id[sid] = f
assert meta['boundaryID'] == 'CHN-ADM2-17275852'
assert meta['boundaryYear'] == '2017' and meta['boundaryType'] == 'ADM2'
assert int(meta['admUnitCount']) == len(source['features']) == 2391

rows = []
for iid in ids:
    f = features[iid]
    p = f['properties']
    original_id = p['metadata']['original_id']
    sf = source_by_id.get(original_id)
    assert sf, f'missing pinned original source feature: {iid} / {original_id}'
    sp = sf['properties']

    def round4(value):
        if isinstance(value, dict): return {key: round4(item) for key, item in value.items()}
        if isinstance(value, list): return [round4(item) for item in value]
        if isinstance(value, float): return round(value, 4)
        return value
    same_geom = round4(sf['geometry']) == f['geometry']
    def vertex_count(value):
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(item, (float, int)) for item in value[:2]): return 1
        if isinstance(value, list): return sum(vertex_count(item) for item in value)
        return 0
    source_vertices = vertex_count(sf['geometry']['coordinates'])
    atlas_vertices = vertex_count(f['geometry']['coordinates'])
    rows.append({
        'atlas_id': iid,
        'atlas_name': p['name'],
        'parent_id': p['parent_id'],
        'parent_source_level': p['metadata'].get('parent_source_level'),
        'parent_assignment_source': p['metadata'].get('hierarchy_source'),
        'parent_assignment_method_claim': p['metadata'].get('parent_match'),
        'source_name_matches_atlas_name': sp['shapeName'] == p['name'],
        'original_source_id': original_id,
        'source_name_2017': sp['shapeName'],
        'source_type': sp['shapeType'],
        'source_geometry_type': sf['geometry']['type'],
        'atlas_geometry_type': f['geometry']['type'],
        'source_interior_ring_count': max(0, len(sf['geometry']['coordinates']) - 1) if sf['geometry']['type'] == 'Polygon' else None,
        'atlas_interior_ring_count': max(0, len(f['geometry']['coordinates']) - 1) if f['geometry']['type'] == 'Polygon' else None,
        'source_geometry_matches_after_4dp_rounding': same_geom,
        'source_vertex_count': source_vertices,
        'atlas_vertex_count': atlas_vertices,
        'atlas_role_claim': p['metadata'].get('source_role'),
        'atlas_reference_year_claim': p['metadata'].get('reference_year'),
        'administrative_status_2026': 'insufficient-evidence: authoritative current code/name roster not retained or verified for this row',
        'legal_boundary_status': 'insufficient-evidence: gbOpen source vintage is 2017 and is not legal boundary determination evidence',
    })
assert len(rows) == 228
assert len({r['original_source_id'] for r in rows}) == 228
assert all(r['source_type'] == 'ADM2' for r in rows)

with (ROOT / 'findings/location-source-crosswalk.csv').open('w', newline='') as fp:
    w = csv.DictWriter(fp, fieldnames=list(rows[0]), lineterminator='\n')
    w.writeheader(); w.writerows(sorted(rows, key=lambda r: r['atlas_id']))

areas = {a['name']: a for a in SCOPE['area_scopes']}
hierarchy = {unit['id']: unit for unit in json.loads((ROOT / '../../hierarchy.json').resolve().read_text())}
parent_counts = {}
for row in rows: parent_counts[row['parent_id']] = parent_counts.get(row['parent_id'], 0) + 1
province_scopes = []
for p in SCOPE['province_scopes']:
    unit = hierarchy.get(p['id'])
    assert unit, f"missing parent unit {p['id']}"
    province_scopes.append({'id': p['id'], 'issue_name': p['name'], 'atlas_name': unit['name'], 'scope_member_count': parent_counts.get(p['id'], 0), 'issue_full_province_locations': p['full_province_locations'], 'partial': p['partial'], 'assessment': 'insufficient-evidence: current official roster and authoritative boundary references not retained/verified'})
assert len(province_scopes) == 22
assert sum(x['scope_member_count'] for x in province_scopes) == 228
with (ROOT / 'findings/parent-scope-review.csv').open('w', newline='') as fp:
    w = csv.DictWriter(fp, fieldnames=list(province_scopes[0]), lineterminator='\n'); w.writeheader(); w.writerows(province_scopes)
area_scopes = []
for a in SCOPE['area_scopes']:
    unit = hierarchy.get(a['id'])
    assert unit, f"missing area unit {a['id']}"
    md = unit.get('metadata', {})
    area_scopes.append({'id': a['id'], 'name': a['name'], 'declared_basis': md.get('basis'), 'declared_source': md.get('source'), 'declared_source_url': md.get('source_url'), 'hierarchy_child_count': md.get('child_count'), 'issue_owned_location_count': a['owned_member_location_count'], 'area_full_location_count': a['full_area_location_count'], 'partial': a['partial'], 'preexisting_review_reasons': '; '.join(md.get('review_reasons', [])), 'assessment': 'insufficient-evidence: declared source and structural grouping do not establish current full area purpose/boundary; component administrative roles and source completeness remain open'})
assert len(area_scopes) == 3
with (ROOT / 'findings/area-scope-review.csv').open('w', newline='') as fp:
    w = csv.DictWriter(fp, fieldnames=list(area_scopes[0]), lineterminator='\n'); w.writeheader(); w.writerows(area_scopes)
summary = {
 'issue': ISSUE['number'], 'title': ISSUE['title'],
 'scope_ids': len(ids), 'unique_scope_ids': len(set(ids)),
 'scope_digest_valid': True, 'pinned_source_feature_count': len(source['features']),
 'source_unique_shape_ids': len(source_by_id), 'matched_scoped_source_features': len(rows),
 'unique_scoped_source_features': len({r['original_source_id'] for r in rows}),
 'matches_after_rounding_source_to_atlas_4dp': sum(r['source_geometry_matches_after_4dp_rounding'] for r in rows),
 'atlas_vertices_total': sum(r['atlas_vertex_count'] for r in rows),
 'source_vertices_total': sum(r['source_vertex_count'] for r in rows),
 'rows_with_reduced_vertex_count': sum(r['atlas_vertex_count'] < r['source_vertex_count'] for r in rows),
 'source_name_matches_atlas_name': sum(r['source_name_matches_atlas_name'] for r in rows),
 'source_geometry_types': dict(sorted({t: sum(r['source_geometry_type'] == t for r in rows) for t in {r['source_geometry_type'] for r in rows}}.items())),
 'source_rows_with_interior_rings': sum((r['source_interior_ring_count'] or 0) > 0 for r in rows),
 'atlas_rows_with_interior_rings': sum((r['atlas_interior_ring_count'] or 0) > 0 for r in rows),
 'coordinate_differences_beyond_4dp_rounding': sum(not r['source_geometry_matches_after_4dp_rounding'] for r in rows),
 'coordinate_difference_ids': [r['atlas_id'] for r in rows if not r['source_geometry_matches_after_4dp_rounding']],
 'all_source_features_adm2': all(r['source_type'] == 'ADM2' for r in rows),
 'source_feature_property_fields': sorted(source['features'][0]['properties'].keys()),
 'parent_assignment_sources': dict(sorted({name: sum(r['parent_assignment_source'] == name for r in rows) for name in {r['parent_assignment_source'] for r in rows}}.items())),
 'parent_source_levels': dict(sorted({name: sum(r['parent_source_level'] == name for r in rows) for name in {r['parent_source_level'] for r in rows}}.items())),
 'source_metadata': {k: meta.get(k) for k in ('boundaryID','boundaryYear','boundaryType','boundaryCanonical','boundaryLicense','licenseDetail','licenseSource','boundarySource','boundarySourceURL','sourceDataUpdateDate','buildDate','admUnitCount')},
 'scoped_area_counts': {name: {'owned': a['owned_member_location_count'], 'full_area': a['full_area_location_count'], 'partial': a['partial']} for name,a in areas.items()},
 'current_status_dispositions': {'insufficient-evidence': len(rows)},
 'area_scope_count': len(area_scopes),
 'area_scope_dispositions': {'insufficient-evidence': len(area_scopes)},
 'province_scope_count': len(province_scopes),
 'province_scope_membership_total': sum(x['scope_member_count'] for x in province_scopes),
 'province_scope_dispositions': {'insufficient-evidence': len(province_scopes)},
 'interpretation': 'All 228 Atlas records map one-to-one to the matching 2017 geoBoundaries source shapeID. Only rows matching all source coordinates after source rounding to the Atlas apparent 4-decimal precision count as matching. Coordinate mismatches can reflect clipping, vertex edits or other transformations; this audit does not identify their cause or verify present legal geometry, current official roster, classification or completeness.',
}
(ROOT / 'findings/reproduction-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
