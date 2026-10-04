#!/usr/bin/env python3
"""Independent structural, source-pin, coverage and negative-control checks."""
import csv, gzip, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'data/regional-review/regional-review-4254da254d94f450'

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def validate_rows(rows):
    ids = [r['source_shape_id'] for r in rows]
    assert len(rows) == 376 and len(set(ids)) == 376
    for r in rows:
        chain = r['complete_parent_chain']
        assert len(chain) == 6 and chain[0]['id'] == r['location_id']
        assert chain[0]['parent_id'] == r['current_parent_id']
        assert all(chain[i]['parent_id'] == chain[i+1]['id'] for i in range(5))
        assert chain[-1]['parent_id'] is None and chain[-1]['name'] == 'North America'
    assert all(r['parent_cd_code_consistent'] and r['current_parent_cd_consistent_2021'] for r in rows)
    assert all(r['selected_2016_csd_uid'] and r['candidate_2021_csd_uid_from_485'] for r in rows)
    assert len({r['selected_2016_csd_uid'] for r in rows}) == 376
    assert len({r['candidate_2021_csd_uid_from_485'] for r in rows}) == 374
    return ids

assessment = json.loads((HERE / 'crosswalk-2016-source-to-csd-assessment.json').read_text())
rows = assessment['results']
ids = validate_rows(rows)
roster = json.loads((HERE / 'source-member-roster.json').read_text())['members']
assert len(roster) == 376 and {m['source_shape_id'] for m in roster} == set(ids)
assert all(len(m['complete_parent_chain']) == 6 for m in roster)
source_ids = set()
for part in range(1, 5):
    data = json.loads((HERE / f'geoboundaries-bc-2016-members-part-{part:02d}-of-04.geojson').read_text())
    assert data['type'] == 'FeatureCollection'
    source_ids.update(f['properties']['shapeID'] for f in data['features'])
assert source_ids == set(ids)
csd2016 = json.loads((HERE / 'statistics-canada-british-columbia-census-subdivisions-2016.geojson').read_text())
assert len(csd2016['features']) == 737
csd2016_ids = {str(f['properties']['CSDUID']) for f in csd2016['features']}
assert {r['selected_2016_csd_uid'] for r in rows} <= csd2016_ids
csd2021 = json.loads((HERE / 'statistics-canada-2021-csd-identity-extract.json').read_text())
assert csd2021['extract_count'] == 374 and len(csd2021['records']) == 374
assert {str(r['CSDUID']) for r in csd2021['records']} == {r['candidate_2021_csd_uid_from_485'] for r in rows}
targets2021 = json.loads((HERE / 'statistics-canada-bc-csd-2021-low-overlap-targets.geojson').read_text())
assert len(targets2021['features']) == 33
assert len({r['location_id'] for r in rows}) == 19
no_name = [r for r in rows if r['inherited_2021_screen_flags']['no_exact_2021_name']]
ambiguous = [r for r in rows if r['inherited_2021_screen_flags']['multiple_exact_2021_names']]
low = [r for r in rows if r['inherited_2021_screen_flags']['best_2021_overlap_below_95']]
assert (len(no_name), len(ambiguous), len(low)) == (20, 5, 33)
assert {str(f['properties']['CSDUID']) for f in targets2021['features']} == {r['best_2021_csd_id'] for r in low}
assert sum(r['prior_overlap_pct'] < 50 for r in low) == 3
assert all(abs(r['prior_overlap_pct'] - r['recomputed_source_to_2021_candidate_overlap_pct']) < .002 for r in low)
assert all(r['selected_2016_csd_uid'] in {c['csduid'] for c in r['same_name_2021_candidates_in_parent_cd']} for r in ambiguous)
name_differences = [r for r in rows if not r['official_2016_csd_match']['name_exact_normalized']]
assert len(name_differences) == 7
assert sum('*' in r['source_name'] for r in name_differences) == 6
assert sum('Ã' in r['source_name'] for r in name_differences) == 1
assert sum(r['official_2016_csd_match']['source_covered_pct'] < 95 for r in rows) == 17
assert sum(r['official_2016_csd_match']['csd_covered_pct'] < 95 for r in rows) == 134
assert sum(r['official_2016_csd_match']['source_covered_pct'] < 95 or r['official_2016_csd_match']['csd_covered_pct'] < 95 for r in rows) == 141
assert sum((r['official_2016_to_2021_candidate_overlap_2016_covered_pct'] or 100) < 95 or (r['official_2016_to_2021_candidate_overlap_2021_covered_pct'] or 100) < 95 for r in low) == 16

by_old = {r['selected_2016_csd_uid']: r for r in rows}
assert by_old['5909849']['official_transition_status'] == 'direct_successor_in_official_change_table'
assert by_old['5909849']['direct_successor_csd_uids_from_change_table'] == ['5909020']
assert by_old['5915835']['official_transition_status'] == 'direct_successor_in_official_change_table'
assert by_old['5915835']['direct_successor_csd_uids_from_change_table'] == ['5915075']
for r in (by_old['5909849'], by_old['5915835']):
    assert any(e['Gaining Change Code Description'].casefold() == 'area gained due to complete annexation' and e['Losing Change Code Description'].casefold() == 'dissolution' for e in r['relevant_official_change_table_rows'])

findings = json.loads((HERE / 'exception-findings.json').read_text())
assert len(findings['no_exact_2021_names']) == 20
assert len(findings['ambiguous_2021_names']) == 5
assert len(findings['low_overlap_2021_geometry_cases']) == 33
assert len(findings['all_2016_source_target_extent_cases']) == 141
assert len(findings['additional_2016_extent_cases']) >= 1
with (HERE / 'exception-review.csv').open(encoding='utf-8') as f:
    assert sum(1 for _ in csv.DictReader(f)) == 159
reproduction = json.loads((HERE / 'reproduction-results.json').read_text())
assert reproduction['kind'] == 'reproducibility' and reproduction['outcome'] == 'passed'
assert reproduction['run_one_sha256'] == reproduction['run_two_sha256']
assert len(reproduction['outputs']) == 12 and all(row['equal'] and row['run_one_sha256'] == row['run_two_sha256'] for row in reproduction['outputs'])
for row in reproduction['outputs']:
    assert sha(HERE / row['path']) == row['run_one_sha256'], row['path']

# Verify retained source bytes and inherited source pins independently of generator output.
receipts = json.loads((HERE / 'source-receipts.json').read_text())
for source in receipts['sources']:
    path = source.get('retained_path') or source.get('derived_path')
    if not path:
        continue
    file_path = HERE / path if path.startswith(('sources/', 'statistics-canada-', 'geoboundaries-')) else ROOT / path
    expected_bytes = source.get('retained_bytes') if source.get('retained_path') else source.get('derived_bytes')
    expected_hash = source.get('retained_sha256') if source.get('retained_path') else source.get('derived_sha256')
    assert file_path.is_file() and file_path.stat().st_size == expected_bytes, path
    assert sha(file_path) == expected_hash, path
    if source.get('uncompressed_sha256'):
        with gzip.open(file_path,'rb') as f: raw=f.read()
        assert len(raw) == source['uncompressed_bytes']
        assert hashlib.sha256(raw).hexdigest() == source['uncompressed_sha256']
assert sha(BASE / 'assessment.json') == '2ab2c0610e37d50f020d031538fa5a22aecf4c7389bd64f6ec17b79487b60499'
assert sha(BASE / 'sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz') == 'a16ca45708ab0ccd898994e5e792187d5a108741c2ff6f5f9f74e91242206ad4'

# Negative controls: duplicate scope members and a broken parent assertion must fail.
def rejects(fn):
    try:
        fn()
    except (AssertionError, KeyError):
        return True
    return False

assert rejects(lambda: validate_rows(rows + [rows[0]]))
broken = [dict(rows[0], parent_cd_code_consistent=False)] + rows[1:]
assert rejects(lambda: validate_rows(broken))
broken_chain = [dict(rows[0], complete_parent_chain=[dict(rows[0]['complete_parent_chain'][0], parent_id='missing')]+rows[0]['complete_parent_chain'][1:])] + rows[1:]
assert rejects(lambda: validate_rows(broken_chain))
assert rejects(lambda: validate_rows(rows[:-1]))

result = {
    'method_id': 'crosswalk-packet-validation', 'kind': 'measurement', 'outcome': 'passed',
    'evidence_path': 'control-results.json',
    'assigned_subjects': len(rows), 'unique_2016_csd_uids': len({r['selected_2016_csd_uid'] for r in rows}),
    'unique_2021_target_uids': len({r['candidate_2021_csd_uid_from_485'] for r in rows}),
    'original_flag_counts': {'no_exact_name':len(no_name),'ambiguous_name':len(ambiguous),'overlap_below_95':len(low)},
    'extent_union': 141,
    'positive_controls': ['complete 376-ID roster and parent chains', 'all 33 low-overlap ratios reproduced', 'two annexation IDs/event descriptions verified', 'all recorded source hashes verified'],
    'negative_controls': ['duplicate ID rejected', 'broken parent consistency rejected', 'incomplete roster rejected']
}
(HERE / 'control-results.json').write_text(json.dumps(result, indent=2) + '\n')
for kind, checks in (
    ('positive-control', result['positive_controls']),
    ('negative-control', result['negative_controls']),
):
    receipt = {'method_id': 'crosswalk-packet-validation', 'kind': kind,
               'outcome': 'passed', 'checks': checks}
    (HERE / f'control-{kind}.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(result, indent=2))
