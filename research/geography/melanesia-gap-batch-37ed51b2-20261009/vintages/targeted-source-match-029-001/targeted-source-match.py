#!/usr/bin/env python3
"""Match the 29 mapped-land candidates lacking a retained source-comparison row.

This is a targeted source overlay, not a new legal or political boundary claim.
It reads only the reviewed immutable baseline pins and publishes a new evidence
vintage through the repository's Baseline/NewVintage custody helper.
"""
import datetime
import gzip
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[3]
OWNED = 'research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN = 'targeted-source-match-029-001'
PIN_PATH = ROOT / OWNED / 'targeted-source-pins.json'
PIN_META = json.loads(PIN_PATH.read_text())
COMMIT = PIN_META['baseline_commit']
HELPER = 'scripts/evidence/immutable.py'
pins = list(PIN_META['files'])
helper_raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', COMMIT + ':' + HELPER])
helper_pin = next((x for x in pins if x['path'] == HELPER), None)
if helper_pin is None:
    pins.append({'path': HELPER, 'bytes': len(helper_raw), 'sha256': hashlib.sha256(helper_raw).hexdigest(), 'hash_kind': 'file-bytes'})
else:
    assert helper_pin['bytes'] == len(helper_raw) and helper_pin['sha256'] == hashlib.sha256(helper_raw).hexdigest()
ns = {'__name__': 'pinned_evidence', '__file__': str(ROOT / HELPER)}
exec(compile(helper_raw, str(ROOT / HELPER), 'exec'), ns)
Baseline, NewVintage, canonical_json = ns['Baseline'], ns['NewVintage'], ns['canonical_json']
baseline = Baseline(ROOT, COMMIT, pins)
started = time.monotonic()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(path):
    raw = baseline.pinned_bytes(path)
    if raw[:2] == b'\x1f\x8b':
        decoded = gzip.decompress(raw)
        baseline.admit(path + ':decoded', len(decoded))
        return json.loads(decoded)
    return json.loads(raw)

# Verify the exact products consumed by scripts/administrative.py are selected
# through the pinned source registry's simplifiedGeometryGeoJSON fields.
consumer = baseline.pinned_bytes('scripts/administrative.py').decode()
assert "simplifiedGeometryGeoJSON" in consumer and "_simplified.geojson" in consumer
registry = load('data/administrative-sources.json')
product_specs = [next(x for x in PIN_META['files'] if x['path'] == path) for path in PIN_META['source_products']]
source_by_code = {}
source_inventory = []
for spec in product_specs:
    path = spec['path']
    corpus_code = Path(path).name.removeprefix('gb-').removesuffix('-000.bin.gz')
    source_id = 'gb:' + corpus_code.replace('-', ':')
    row = registry[source_id]
    country, level = corpus_code.split('-')
    assert row['simplifiedGeometryGeoJSON'].endswith('/' + country + '/' + level + '/geoBoundaries-' + corpus_code + '_simplified.geojson')
    raw = baseline.pinned_bytes(path)
    assert len(raw) == spec['bytes'] and sha(raw) == spec['sha256']
    decoded = gzip.decompress(raw)
    assert len(decoded) == spec['decoded_bytes'] and sha(decoded) == row['sha256']
    baseline.admit(path + ':decoded', len(decoded))
    product = json.loads(decoded)
    rows = []
    for index, feat in enumerate(product['features']):
        feature_sha = sha(canonical_json(feat))
        geometry_sha = sha(canonical_json(feat['geometry']))
        rows.append({'index': index, 'feature': feat, 'feature_sha256': feature_sha,
                     'geometry_sha256': geometry_sha, 'geom': shape(feat['geometry'])})
    source_by_code[corpus_code] = rows
    source_by_code[corpus_code + ':tree'] = STRtree([x['geom'] for x in rows])
    source_inventory.append({'source_id': source_id, 'boundaryID': row['boundaryID'],
        'represented_year': row['boundaryYearRepresented'], 'simplifiedGeometryGeoJSON': row['simplifiedGeometryGeoJSON'],
        'source_registry_decoded_sha256': row['sha256'], 'retained_compressed_path': path,
        'retained_compressed_sha256': sha(raw), 'decoded_sha256': sha(decoded), 'feature_count': len(rows)})

capture_path = PIN_META['candidate_capture']
capture = load(capture_path)
candidates = {r['component_id']: r for r in capture['candidate_records']}
join = load(PIN_META['source_comparison_join'])
target_rows = [r for r in join['cases'] if r['disposition'] == 'targeted-source-match-needed']
assert len(target_rows) == 29
assert all(r['prior_physical_support'] == 'mapped-land-support' and r['source_product_codes'] == '' for r in target_rows)

# Index the 34-part current geography snapshot. Exact source_id + original_id
# lookup is used after geometry matching; no names or polity labels are used.
geo_features = []
geo_metadata = {}
for path in PIN_META['geography_parts']:
    for feat in load(path)['features']:
        props = feat.get('properties', {})
        key = (props.get('metadata', {}).get('source_id'), props.get('metadata', {}).get('original_id'))
        rec = {'id': feat.get('id'), 'feature_sha256': sha(canonical_json(feat)),
               'geometry_sha256': sha(canonical_json(feat['geometry'])), 'geometry': shape(feat['geometry']),
               'part': path, 'properties': props}
        geo_features.append(rec)
        if all(key):
            geo_metadata.setdefault(key, []).append(rec)
geo_tree = STRtree([x['geometry'] for x in geo_features])

results = []
for row in target_rows:
    component_id = row['component_id']
    feature = candidates[component_id]['feature']
    candidate_geom = shape(feature['geometry'])
    product_codes = sorted({Path(x['path']).name.removeprefix('gb-').removesuffix('-000.bin.gz') for x in product_specs})
    intersections = []
    for code in product_codes:
        country = code.split('-')[0]
        source_rows = source_by_code[code]
        source_tree = source_by_code[code + ':tree']
        for ix in source_tree.query(candidate_geom):
            src = source_rows[int(ix)]
            inter = candidate_geom.intersection(src['geom'])
            if inter.is_empty:
                continue
            intersects_area = inter.area > 0
            if not intersects_area and inter.length <= 0:
                continue
            source_id = 'gb:' + country + ':' + src['feature']['properties']['shapeType']
            stable_id = source_id + ':' + src['feature']['properties']['shapeID']
            matches = geo_metadata.get((source_id, src['feature']['properties']['shapeID']), [])
            intersections.append({'source_id': source_id, 'feature_index': src['index'],
                'shapeID': src['feature']['properties']['shapeID'], 'shapeName': src['feature']['properties'].get('shapeName'),
                'source_feature_sha256': src['feature_sha256'], 'source_geometry_sha256': src['geometry_sha256'],
                'intersection_dimension': 'area' if intersects_area else 'line',
                'intersection_area_degree2': inter.area, 'intersection_length_degree': inter.length,
                'intersection_geometry': mapping(inter), 'stable_subject_id': stable_id,
                'current_stable_subject_match_count': len(matches),
                'current_stable_subject_matches': [{'id': x['id'], 'feature_sha256': x['feature_sha256'],
                    'geometry_sha256': x['geometry_sha256'], 'part': x['part'],
                    'administrative_assignment': x['properties'].get('administrative_assignment'),
                    'reference_owner_id': x['properties'].get('reference_owner_id')}
                    for x in matches]})
    positive_area = [x for x in intersections if x['intersection_dimension'] == 'area']
    stable_ids = sorted({x['stable_subject_id'] for x in positive_area})
    unique_current = all(x['current_stable_subject_match_count'] == 1 for x in positive_area)
    candidate_current = []
    # Exact full snapshot intersection facts. This records candidate geometries
    # against current reference features without inferring adjacency or law.
    for ix in geo_tree.query(candidate_geom):
        rec = geo_features[int(ix)]
        inter = candidate_geom.intersection(rec['geometry'])
        if not inter.is_empty:
            candidate_current.append({'id': rec['id'], 'feature_sha256': rec['feature_sha256'],
                'geometry_sha256': rec['geometry_sha256'], 'part': rec['part'],
                'dimension': 'area' if inter.area > 0 else ('line' if inter.length > 0 else 'point'),
                'area_degree2': inter.area, 'length_degree': inter.length,
                'administrative_assignment': rec['properties'].get('administrative_assignment'),
                'reference_owner_id': rec['properties'].get('reference_owner_id')})
    if not positive_area:
        disposition = 'no-positive-area-match-in-five-retained-products'
    elif len(stable_ids) > 1:
        disposition = 'multiple-positive-area-source-subjects'
    elif not unique_current:
        disposition = 'source-subject-not-uniquely-present-in-current-snapshot'
    else:
        disposition = 'unique-positive-area-source-subject-current-snapshot-match'
    results.append({'component_id': component_id,
        'candidate_feature_sha256': candidates[component_id]['component_feature_sha256'],
        'candidate_geometry_sha256': candidates[component_id]['component_geometry_sha256'],
        'candidate_feature': feature, 'prior_source_status': row['source_comparison_status'],
        'prior_next_prerequisite': row['original_next_prerequisite'],
        'source_intersections': intersections, 'positive_area_stable_subject_ids': stable_ids,
        'current_snapshot_intersections': candidate_current, 'disposition': disposition})

counts = {}
for x in results: counts[x['disposition']] = counts.get(x['disposition'], 0) + 1
output = {'schema': 'melanesia-targeted-source-match-029/v1',
    'batch_id': capture['batch_id'], 'target_count': len(results), 'disposition_counts': counts,
    'source_products': source_inventory, 'current_geography_feature_count': len(geo_features),
    'current_geography_parts': PIN_META['geography_parts'],
    'cases': results,
    'method': 'For each of the 29 mapped-land candidates lacking a retained comparison, intersected the exact captured candidate geometry against every feature in each of the five retained simplified GeoJSON products; then matched positive-area source features by exact source_id + shapeID to the pinned current geography snapshot.',
    'limits': ['Source product represented years and registry dates are descriptive, not effective dates or legal authority.',
        'Geometric source matches are source-relative evidence; they do not establish current law, historical causality, or boundary authority.',
        'A unique source match is only a native-grid payload candidate; actual unowned-cell assignment and conservation checks remain required.',
        'No candidate is assigned or repaired by this analysis.']}

script_raw = Path(__file__).read_bytes()
execution = {'status': 'completed', 'completed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_commit': COMMIT, 'script_path': str(Path(__file__).relative_to(ROOT)),
    'script_bytes': len(script_raw), 'script_sha256': sha(script_raw),
    'runtime': {'python': platform.python_version(), 'shapely': __import__('shapely').__version__},
    'custody': 'pinned Baseline + exclusive NewVintage', 'admitted_input_bytes': sum(baseline.consumed.values()),
    'elapsed_seconds': time.monotonic() - started}
pin_output = {'schema': 'melanesia-targeted-source-match-029-input-pins/v1', 'baseline_commit': COMMIT,
    'files': [{'path': p['path'], 'bytes': p['bytes'], 'sha256': p['sha256'], 'hash_kind': p.get('hash_kind', 'file-bytes')} for p in pins],
    'source_product_registry': source_inventory}
values = {'targeted-source-match-029.json': canonical_json(output), 'execution.json': canonical_json(execution),
    'targeted-source-match.py': script_raw, 'input-pins.json': canonical_json(pin_output)}
NewVintage(baseline, OWNED, RUN, list(values)).publish_bytes(values)
print(json.dumps({'status': 'published', 'target_count': len(results), 'dispositions': counts,
    'current_geography_feature_count': len(geo_features), 'admitted_input_bytes': sum(baseline.consumed.values())}, sort_keys=True))
