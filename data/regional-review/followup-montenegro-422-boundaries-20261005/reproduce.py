#!/usr/bin/env python3
"""Reproduce the exact #996 subject crosswalk and source-area comparisons.

This compares a previously measured, immutable 2017 OSM/Wambacher-derived
GeoBoundaries layer to transcribed official statistical area tables. It does
not measure geometry anew and never treats area similarity as boundary proof.
"""
from __future__ import annotations
import hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'data/regional-review/followup-montenegro-422-boundaries-20261005'
BASELINE = 'b6cfaada43a1e0472cd833d16733d1fd6065eaec'
PRIOR = 'data/regional-review/regional-review-3c4fe25a21fa428d/source'
NEW = 'data/regional-review/followup-montenegro-422-boundaries-20261005'
BASE_CACHE: dict[str, bytes] = {}

def git_bytes(path: str) -> bytes:
    if path not in BASE_CACHE:
        BASE_CACHE[path] = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{BASELINE}:{path}'])
    return BASE_CACHE[path]

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_json_bytes(data: bytes):
    return json.loads(data)

def norm(name: str) -> str:
    value = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    value = re.sub(r'\b(municipality|capital|metropolis)\b', ' ', value)
    return re.sub(r'[^a-z0-9]+', '', value)

def official_match(source_name: str, lookup: dict[str, tuple[str, int]]) -> tuple[str, int]:
    key = norm(source_name)
    if key not in lookup:
        raise ValueError(f'No exact normalized official municipality name: {source_name}')
    return lookup[key]

def run() -> dict:
    issue = json.loads((PACKET / 'source/issue-996-api-response.json').read_bytes())
    assert issue['number'] == 996 and issue['state'] == 'open'
    marker = re.search(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->', issue['body'])
    assert marker, 'issue contract missing'
    spec = json.loads(marker.group(1))
    quality = spec['evidence_quality']
    ids = quality['subject_ids']
    assert spec['mode'] == 'geography' and spec['max_prs'] == 1 and quality['review_kind'] == 'geometry'
    assert spec['owned_paths'] == [NEW + '/'] and spec['depends_on'] == [422] and len(ids) == 23
    assert json.loads((PACKET / 'reservation.json').read_text())['accepted'] is True

    # Current issue pins refer to immutable main baseline bytes, never the mutable checkout.
    for name, digest in quality['pins'].items():
        assert sha(git_bytes(name)) == digest, f'pin mismatch: {name}'
    idx = read_json_bytes(git_bytes('data/world-index.json'))
    hierarchy = {row['id']: row for row in read_json_bytes(git_bytes('data/hierarchy.json'))}
    occurrences = {identity: [] for identity in ids}
    subject_props = {}
    for rel in idx['parts']:
        data = read_json_bytes(git_bytes('data/' + rel))
        for feature in data['features']:
            p = feature.get('properties', {})
            identity = p.get('id')
            if identity in occurrences:
                occurrences[identity].append((rel, feature, p))
                subject_props[identity] = p
    assert all(len(occurrences[i]) == 1 for i in ids), 'scope IDs must occur exactly once in indexed geometry'
    paths = {occurrences[i][0][0] for i in ids}
    assert len(paths) == 1, f'Unexpectedly split containing files: {sorted(paths)}'
    containing = next(iter(paths))
    assert containing == 'geography/part-15.json'

    old_area = read_json_bytes(git_bytes(PRIOR + '/area-assessments.json'))
    old_subjects = read_json_bytes(git_bytes(PRIOR + '/subject-assessments.json'))['subjects']
    old_by_id = {r['location_id']: r for r in old_area['subjects'] if r['source_id'] == 'gb:MNE:ADM1'}
    subject_by_id = {r['location_id']: r for r in old_subjects if r['source_id'] == 'gb:MNE:ADM1'}
    assert set(old_by_id) == set(ids) == set(subject_by_id)
    assert old_area['evaluation_vintage'] == 'source'
    assert old_area['method']['area_method'] == 'WGS84 straight-source-edge ellipsoidal integral'

    official17 = json.loads((PACKET / 'source/official-municipal-areas-2017.json').read_text())
    official18 = json.loads((PACKET / 'source/official-municipal-areas-2018.json').read_text())
    name17 = {norm(name): (name, value) for name, value in official17['areas_km2'].items()}
    name18 = {norm(name): (name, value) for name, value in official18['areas_km2'].items()}
    source_geometry = read_json_bytes((PACKET / 'source/gb-MNE-ADM1-geoBoundaries-2017.geojson').read_bytes())
    assert len(source_geometry['features']) == 23
    features_by_shape = {f['properties']['shapeID']: f for f in source_geometry['features']}
    assert len(features_by_shape) == 23
    geo_rows = []
    parent_children = {}
    for identity in ids:
        p = subject_props[identity]
        assessment = subject_by_id[identity]
        area = old_by_id[identity]
        original_id = identity.rsplit(':', 1)[1]
        f = features_by_shape[original_id]
        assert p['metadata']['source_id'] == 'gb:MNE:ADM1'
        assert p['metadata']['reference_year'] == '2017'
        assert p['metadata']['original_id'] == original_id
        assert assessment['original_id'] == original_id and assessment['source_shape_id'] == original_id
        assert assessment['source_sha256'] == '9674292fbc0a50c68c6584a2ae23fae768e76cc796bdb7e3e009c0197aec6ae3'
        assert area['source_sha256'] == assessment['source_sha256']
        assert assessment['source_feature_name'] == f['properties']['shapeName']
        reported_name, reported17 = official_match(assessment['source_feature_name'], name17)
        reported18_name, reported18 = official_match(assessment['source_feature_name'], name18)
        parent_id = p['parent_id']
        assert parent_id in hierarchy and hierarchy[parent_id]['level'] == 'province'
        parent_children.setdefault(parent_id, []).append(identity)
        geom = f['geometry']
        components = len(geom['coordinates']) if geom['type'] == 'MultiPolygon' else 1
        holes = (sum(max(0, len(poly) - 1) for poly in geom['coordinates'])
                 if geom['type'] == 'MultiPolygon' else max(0, len(geom['coordinates']) - 1))
        measured = float(area['area_km2'])
        geo_rows.append({
            'subject_id': identity,
            'atlas_name': p['name'],
            'source_feature_name': assessment['source_feature_name'],
            'shape_id': original_id,
            'atlas_parent_id': parent_id,
            'atlas_parent_name': hierarchy[parent_id]['name'],
            'atlas_parent_level': hierarchy[parent_id]['level'],
            'atlas_parent_declared_child_count': hierarchy[parent_id]['metadata']['child_count'],
            'source_vintage': '2017 representative year (source date not established)',
            'source_geometry_type': geom['type'],
            'source_polygon_components': components,
            'source_hole_rings': holes,
            'source_coordinate_vertices': assessment['coordinate_vertices'],
            'retained_geometry_area_km2_wgs84': measured,
            'official_2017_report_name': reported_name,
            'official_2017_report_area_km2': reported17,
            'area_delta_2017_official_minus_geometry_km2': round(reported17 - measured, 6),
            'area_delta_2017_pct_of_official': round(100 * (reported17 - measured) / reported17, 6),
            'official_2018_report_name': reported18_name,
            'official_2018_report_area_km2': reported18,
            'area_delta_2018_official_minus_geometry_km2': round(reported18 - measured, 6),
            'area_delta_2018_pct_of_official': round(100 * (reported18 - measured) / reported18, 6),
            'result': 'area-only correspondence signal; not boundary verification'
        })
    assert set(parent_children) == {subject_props[i]['parent_id'] for i in ids}
    assert len(parent_children) == 23 and all(len(children) == 1 for children in parent_children.values())
    assert len(name17) == 23 and set(name17) == {norm(subject_by_id[i]['source_feature_name']) for i in ids}
    current_roster = json.loads((PACKET / 'source/current-municipalities-2025.json').read_text())
    assert len(current_roster) == 25
    geo_rows_by_id = {r['subject_id']: r for r in geo_rows}
    rows = [geo_rows_by_id[i] for i in ids]
    geometry_total = round(sum(old_by_id[i]['area_km2'] for i in ids), 6)
    sum17 = sum(official17['areas_km2'].values())
    sum18 = sum(official18['areas_km2'].values())
    summary = {
        'issue_subject_count': len(ids), 'matched_2017_official_names': len(name17),
        'retained_2017_features': len(features_by_shape), 'unique_subject_containing_files': 1,
        'containing_file': 'data/' + containing,
        'atlas_singleton_parent_count': len(parent_children),
        'retained_source_geometry_types': {
            k: sum(1 for row in rows if row['source_geometry_type'] == k)
            for k in sorted({row['source_geometry_type'] for row in rows})},
        'coastal_source_municipality_count': 6,
        'retained_source_multipolygon_component_count': sum(r['source_polygon_components'] for r in rows),
        'retained_source_hole_ring_count': sum(r['source_hole_rings'] for r in rows),
        'retained_area_sum_km2': geometry_total,
        'official_2017_table_area_sum_km2': sum17,
        'official_2017_reported_montenegro_area_km2': official17['national_area_km2'],
        'official_2017_table_minus_country_km2': sum17 - official17['national_area_km2'],
        'official_2018_table_area_sum_km2': sum18,
        'official_2018_reported_montenegro_area_km2': official18['national_area_km2'],
        'official_2018_country_minus_municipalities_km2': official18['national_area_km2'] - sum18,
        'official_2018_country_difference_source_explanation': 'MONSTAT footnote attributes this to Lake Skadar area belonging to Montenegro',
        'current_2025_official_roster_count': len(current_roster),
        'reproducibility': 'Rows are sorted in exact issue scope order; JSON serialization is UTF-8, sorted keys, indent 2 and one trailing newline.'
    }
    return {
        'version': 1, 'issue': 996, 'baseline_commit': BASELINE,
        'scope_source': 'source/issue-996-api-response.json#worldatlas-work:v1.evidence_quality.subject_ids',
        'area_method_source': PRIOR + '/source/area-assessments.json',
        'official_table_inputs': ['source/official-municipal-areas-2017.json', 'source/official-municipal-areas-2018.json'],
        'summary': summary, 'subjects': rows,
        'limits': [
            'An area comparison does not validate boundary position, legal status, topological correctness, islands or coastline completeness.',
            '2017 official area table values sum to 13,969 km2, 157 km2 more than its reported national area; the report does not explain this discrepancy.',
            '2018 MONSTAT table is post-Tuzi (24-unit roster); Tuzi area was temporary pending Podgorica demarcation.',
            'Official reusable municipal boundary geometry was not obtained; current portal display terms and vintage are undocumented in the inspected pages.'
        ]
    }

def main():
    first_data = run()
    first = json.dumps(first_data, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    second_data = run()
    second = json.dumps(second_data, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    assert first == second, 'same-input source comparison did not reproduce byte-identically'
    path = PACKET / 'comparison.json'
    path.write_text(first, encoding='utf-8')
    positive_detail = f"{len(first_data['subjects'])} exact issue subjects passed the pinned containing-file, source-shape and official-name crosswalk assertions."
    assert len(first_data['subjects']) == 23
    (PACKET / 'positive-control.json').write_text(json.dumps({
        'method_id': 'source-crosswalk-and-area-comparison', 'kind': 'positive-control',
        'outcome': 'passed', 'detail': positive_detail
    }, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    official17 = json.loads((PACKET / 'source/official-municipal-areas-2017.json').read_text())
    lookup17 = {norm(name): (name, value) for name, value in official17['areas_km2'].items()}
    impossible_name = 'Not a Municipality in Montenegro'
    try:
        official_match(impossible_name, lookup17)
    except ValueError as error:
        negative_detail = f"Rejected synthetic unmatched input {impossible_name!r}: {error}"
    else:
        raise AssertionError('negative control failed: unmatched name was accepted')
    (PACKET / 'negative-control.json').write_text(json.dumps({
        'method_id': 'source-crosswalk-and-area-comparison', 'kind': 'negative-control',
        'outcome': 'passed', 'input': impossible_name, 'detail': negative_detail
    }, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    result = {
        'method_id': 'source-crosswalk-and-area-comparison', 'kind': 'reproducibility',
        'outcome': 'passed', 'run_one_sha256': hashlib.sha256(first.encode()).hexdigest(),
        'run_two_sha256': hashlib.sha256(second.encode()).hexdigest(),
        'runs': 2, 'baseline_commit': BASELINE,
        'positive_control': '23 exact issue subjects each found once in the pinned world index, matched to a pinned original source feature and one 2017 official municipality-area table row.',
        'negative_control': 'The reproducer submitted a synthetic unmatched name to official_match and verified it raises ValueError before recording a passed negative control.',
        'scope_and_pin_controls': 'All nine issue pins hash from the immutable baseline commit; every subject is confirmed in its actual world-index containing part.'
    }
    control = PACKET / 'reproduction-control.json'
    control.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'rows': len(first_data['subjects']), 'comparison_sha256': sha(first.encode()), 'control_sha256': sha(control.read_bytes())}, indent=2))

if __name__ == '__main__':
    main()
