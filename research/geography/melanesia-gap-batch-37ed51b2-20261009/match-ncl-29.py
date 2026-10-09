#!/usr/bin/env python3
"""Source-relative match for the 29 New Caledonia mapped-land candidates."""
import datetime, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[3]
OWNED = 'research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN = 'ncl-targeted-source-match-029-001'
PIN_PATH = ROOT / OWNED / 'ncl-targeted-source-pins.json'
PIN_META = json.loads(PIN_PATH.read_text())
COMMIT = PIN_META['baseline_commit']
helper_path = 'scripts/evidence/immutable.py'
helper_raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', COMMIT + ':' + helper_path])
ns = {'__name__': 'pinned_evidence', '__file__': str(ROOT / helper_path)}
exec(compile(helper_raw, str(ROOT / helper_path), 'exec'), ns)
Baseline, NewVintage, canonical_json = ns['Baseline'], ns['NewVintage'], ns['canonical_json']
baseline = Baseline(ROOT, COMMIT, PIN_META['files'])
started = time.monotonic()

def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(baseline.pinned_bytes(path))

source_review_path = 'data/regional-review/new-caledonia-valid-province-source-20261005/'
review = load(source_review_path + 'sources.json')
review_readme = baseline.pinned_bytes(source_review_path + 'README.md').decode()
assert all(x in review_readme for x in ('NCL-559', 'NCL-1259', 'NCL-1258'))
georep = next(x for x in review['sources'] if x['id'] == 'NCL-GeoReP-2024')
assert georep['license_status'] == 'redistributable as recorded by the source registry'
assert georep['limit'].startswith('The retained query used maxAllowableOffset=0.00005 degrees')
source_root = 'data/regional-review/regional-review-1aa97b490604ea4e/sources/new-caledonia-province-parts/'
source_files = {
    'PROVINCE NORD': ('province-nord.geojson', 'NCL-559'),
    'PROVINCE SUD': ('province-sud.geojson', 'NCL-1259'),
    'PROVINCE DES ILES': ('province-des-iles.geojson', 'NCL-1258'),
}
registry_rows = {x['path']: x for x in georep['source_files']}
source_features = []
for name, (filename, target_id) in source_files.items():
    path = source_root + filename
    raw = baseline.pinned_bytes(path)
    registry_path = path
    assert registry_path in registry_rows
    assert len(raw) == registry_rows[path]['bytes'] and sha(raw) == registry_rows[path]['sha256']
    data = json.loads(raw)
    assert len(data['features']) == 1
    feat = data['features'][0]
    assert feat['properties']['nom'] == name
    source_features.append({'province_name': name, 'source_path': path, 'source_file_sha256': sha(raw),
        'feature_id': feat['id'], 'feature_sha256': sha(canonical_json(feat)),
        'geometry_sha256': sha(canonical_json(feat['geometry'])), 'target_stable_location_id': target_id,
        'geometry': shape(feat['geometry'])})

# Resolve each named province ID against the exact pinned current geography row.
part_path = 'data/geography/part-28.json'
part = load(part_path)
current = {}
for feat in part['features']:
    if feat.get('id') in {x['target_stable_location_id'] for x in source_features}:
        assert feat['id'] not in current
        current[feat['id']] = {'feature': feat, 'feature_sha256': sha(canonical_json(feat)),
            'geometry_sha256': sha(canonical_json(feat['geometry'])), 'geometry': shape(feat['geometry'])}
assert set(current) == {x['target_stable_location_id'] for x in source_features}

candidate_path = 'research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/candidate-capture-001/candidate-capture.json'
capture = load(candidate_path)
candidate_by_id = {x['component_id']: x for x in capture['candidate_records']}
join_path = 'research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/source-comparison-capture-001/batch-source-comparisons.json'
join = load(join_path)
targets = [x for x in join['cases'] if x['disposition'] == 'targeted-source-match-needed']
assert len(targets) == 29
assert all(x['prior_physical_support'] == 'mapped-land-support' and x['source_product_codes'] == '' for x in targets)
source_tree = STRtree([x['geometry'] for x in source_features])
cases = []
counts = {}
for row in targets:
    candidate = candidate_by_id[row['component_id']]
    geom = shape(candidate['feature']['geometry'])
    hits = []
    for ix in source_tree.query(geom):
        source = source_features[int(ix)]
        inter = geom.intersection(source['geometry'])
        if inter.is_empty:
            continue
        if inter.area <= 0:
            dim = 'line' if inter.length > 0 else 'point'
        else:
            dim = 'area'
        target = source['target_stable_location_id']
        current_row = current[target]
        current_intersection = geom.intersection(current_row['geometry'])
        hits.append({'province_name': source['province_name'], 'source_path': source['source_path'],
            'source_file_sha256': source['source_file_sha256'], 'source_feature_id': source['feature_id'],
            'source_feature_sha256': source['feature_sha256'], 'source_geometry_sha256': source['geometry_sha256'],
            'intersection_dimension': dim, 'intersection_area_degree2': inter.area,
            'intersection_length_degree': inter.length, 'intersection_geometry': mapping(inter),
            'candidate_area_covered_fraction': inter.area / geom.area if geom.area else None,
            'target_stable_location_id': target, 'current_location_part': part_path,
            'current_location_feature_sha256': current_row['feature_sha256'],
            'current_location_geometry_sha256': current_row['geometry_sha256'],
            'candidate_current_location_intersection_dimension': 'area' if current_intersection.area > 0 else ('line' if current_intersection.length > 0 else ('point' if not current_intersection.is_empty else 'none')),
            'candidate_current_location_area_degree2': current_intersection.area,
            'candidate_current_location_length_degree': current_intersection.length})
    area_hits = [x for x in hits if x['intersection_dimension'] == 'area']
    subject_ids = sorted({x['target_stable_location_id'] for x in area_hits})
    if not area_hits: disposition = 'no-positive-area-georep-province-match'
    elif len(subject_ids) > 1: disposition = 'multiple-positive-area-province-matches'
    else: disposition = 'unique-positive-area-georep-province-match'
    counts[disposition] = counts.get(disposition, 0) + 1
    cases.append({'component_id': row['component_id'],
        'candidate_feature_sha256': candidate['component_feature_sha256'],
        'candidate_geometry_sha256': candidate['component_geometry_sha256'],
        'candidate_feature': candidate['feature'], 'prior_source_status': row['source_comparison_status'],
        'prior_source_prerequisite': row['original_next_prerequisite'],
        'province_intersections': hits, 'positive_area_target_stable_location_ids': subject_ids,
        'disposition': disposition})

source_out = [{'province_name': x['province_name'], 'source_path': x['source_path'],
    'source_file_sha256': x['source_file_sha256'], 'source_feature_id': x['feature_id'],
    'source_feature_sha256': x['feature_sha256'], 'source_geometry_sha256': x['geometry_sha256'],
    'target_stable_location_id': x['target_stable_location_id'],
    'current_location_feature_sha256': current[x['target_stable_location_id']]['feature_sha256'],
    'current_location_geometry_sha256': current[x['target_stable_location_id']]['geometry_sha256']} for x in source_features]
result = {'schema': 'melanesia-ncl-targeted-source-match-029/v1', 'batch_id': capture['batch_id'],
    'target_count': len(cases), 'disposition_counts': counts, 'source_product': {
        'id': georep['id'], 'url': georep['url'], 'vintage': georep['vintage'],
        'license_status': georep['license_status'], 'limit': georep['limit'], 'features': source_out},
    'current_location_binding_basis': 'Exact source review subject mapping from the pinned New Caledonia valid province source packet, checked against unique current feature IDs in data/geography/part-28.json; no names-only spatial guess.',
    'method': 'Each exact candidate geometry was intersected with the three retained generalized GeoReP province geometries. Only positive-area source intersections create candidate province links; line/point contacts are retained descriptively. The source-file hashes are checked against sources.json.',
    'cases': cases,
    'limits': ['The retained GeoReP query was generalized with maxAllowableOffset=0.00005 degrees and geometryPrecision=6; it is not the full-resolution 1:10,000 administrative database.',
        'This source-relative match establishes no present legal boundary, effective date, historical process cause, or superior boundary authority.',
        'Only candidate intersection geometry is eligible for a native-grid proposal; unsupported candidate remainder is excluded.',
        'No assignments are changed. Actual unowned-cell testing, complete assignment conservation, and acceptance remain outstanding.']}
script_raw = Path(__file__).read_bytes()
execution = {'status': 'completed', 'completed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_commit': COMMIT, 'script_path': str(Path(__file__).relative_to(ROOT)), 'script_bytes': len(script_raw),
    'script_sha256': sha(script_raw), 'runtime': {'python': platform.python_version(), 'shapely': __import__('shapely').__version__},
    'custody': 'pinned Baseline + exclusive NewVintage', 'admitted_input_bytes': sum(baseline.consumed.values()),
    'elapsed_seconds': time.monotonic() - started}
values = {'ncl-source-matches-029.json': canonical_json(result), 'execution.json': canonical_json(execution),
    'match-ncl-29.py': script_raw, 'input-pins.json': canonical_json({'schema': 'melanesia-ncl-29-run-inputs/v1',
        'baseline_commit': COMMIT, 'files': PIN_META['files']})}
NewVintage(baseline, OWNED, RUN, list(values)).publish_bytes(values)
print(json.dumps({'status': 'published', 'targets': len(cases), 'dispositions': counts,
    'admitted_input_bytes': sum(baseline.consumed.values())}, sort_keys=True))
