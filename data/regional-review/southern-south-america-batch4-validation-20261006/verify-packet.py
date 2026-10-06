#!/usr/bin/env python3
"""Reproduce #1116's immutable-baseline crosswalk audit and controls.

Reads only committed Git objects and retained issue evidence. It never downloads
or rewrites source geometry. Outputs are written only under this owned packet.
"""
import argparse
import contextlib
import csv
import hashlib
import io
import json
import os
import re
import runpy
import subprocess
import sys
from pathlib import Path

BASELINE = '7245eca6d56ee71fd1f40631c72116167ac5037d'
PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
ORIGINAL = REPO / 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b'
ISSUE = PACKET / 'issue-1116-contract.json'
SCOPE_PATH = 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json'
CROSSWALK_PATH = 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/crosswalk.csv'
PARENT_PATH = 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/province-review.csv'
AREA_PATH = 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-review.csv'
SOURCE_REGISTER_PATH = 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json'
ISSUE_MARKER = re.compile(r'<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->')


def git_bytes(commit, path):
    return subprocess.check_output(['git', '-C', str(REPO), 'show', commit + ':' + path])


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_csv(raw):
    return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline='')))


def json_bytes(raw):
    return json.loads(raw.decode('utf-8'))


def coord_count(value):
    if isinstance(value, list):
        if len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
            return 1
        return sum(coord_count(item) for item in value)
    return 0


def scope_contract():
    issue = json.loads(ISSUE.read_text(encoding='utf-8'))
    match = ISSUE_MARKER.search(issue.get('body', ''))
    if not match:
        raise ValueError('Current issue snapshot lacks worldatlas-work:v1')
    contract = json.loads(match.group(1))
    quality = contract.get('evidence_quality', {})
    ids = quality.get('subject_ids', [])
    if issue.get('number') != 1116 or contract.get('mode') != 'geography' or contract.get('max_prs') != 1:
        raise ValueError('Issue identity, lane or PR budget changed')
    if contract.get('owned_paths') != ['data/regional-review/southern-south-america-batch4-validation-20261006/']:
        raise ValueError('Issue-owned path changed')
    if len(ids) != 215 or len(set(ids)) != 215:
        raise ValueError('Issue must declare 215 unique subjects')
    return issue, contract, ids


def baseline_inputs():
    names = [
        'data/world-index.json', 'data/hierarchy.json',
        'data/geography/part-2.json', 'data/geography/part-20.json', 'data/geography/part-28.json',
        SCOPE_PATH, CROSSWALK_PATH, PARENT_PATH, AREA_PATH,
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/evidence-quality.json',
        SOURCE_REGISTER_PATH,
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/geoBoundaries-CHL-ADM3-metaData.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/geoBoundaries-PRY-ADM2-metaData.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce.py',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduction-summary.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/source-review.md',
    ]
    raw = {name: git_bytes(BASELINE, name) for name in names}
    pins = {
        'world-index': ('data/world-index.json', 'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03'),
        'hierarchy': ('data/hierarchy.json', '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b'),
        'original-scope': (SCOPE_PATH, '29a5984b06b96dff899a2c4d16659e63b66f75ab25dd2a744191e0267bc21af8'),
        'original-crosswalk': (CROSSWALK_PATH, '7a48c634a5e9d817cd3da977e1a023c7ffe0cc88340811817e68333ea2683ece'),
        'original-reproducer': ('data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce.py', 'f077ca8ab415b812e9832eb0340037313314be76947575b2ea6bfbafa56f2d0b'),
        'original-manifest': ('data/regional-review/regional-review-9b6d6a9ecf8f6c3b/evidence-quality.json', '85d43d138de43b4cde705217276e47716e835f5625263f75f9fc729be19d3aa0'),
        'original-summary': ('data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduction-summary.json', '6a417f7419cbdf940aa6c84fe7e62504f2030e2c3399907a6d4ee39efdf3766b'),
        'original-source-register': (SOURCE_REGISTER_PATH, '24d34c91f5e3517d1a05e29f1733cc4c0a656422f54ea71a855f63de95f9f57a'),
    }
    for key, (path, expected) in pins.items():
        if digest(raw[path]) != expected:
            raise ValueError('Immutable issue pin differs: ' + key)
    return raw, pins


def actual_features(raw, ids):
    index = json_bytes(raw['data/world-index.json'])
    listed = set(index.get('parts', []))
    needed = ['geography/part-2.json', 'geography/part-20.json', 'geography/part-28.json']
    if any(name not in listed for name in needed):
        raise ValueError('Issue feature parts are absent from pinned world index')
    found, containing = {}, {}
    for part in needed:
        path = 'data/' + part
        data = json_bytes(raw[path])
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            fid = feature.get('id') or props.get('id')
            if fid in ids:
                if fid in found:
                    raise ValueError('Duplicate baseline feature identity: ' + fid)
                found[fid], containing[fid] = feature, path
    if set(found) != set(ids):
        raise ValueError('Pinned baseline does not contain the exact issue roster')
    return found, containing


def check_candidate(rows, ids, features):
    if len(rows) != len(ids) or len({r.get('location_id') for r in rows}) != len(rows):
        raise ValueError('Candidate rows are not unique and complete')
    if {r.get('location_id') for r in rows} != set(ids):
        raise ValueError('Candidate subject roster differs')
    for row in rows:
        fid = row['location_id']
        feature = features[fid]
        props, meta = feature.get('properties', {}), feature.get('properties', {}).get('metadata', {})
        for field in ('name', 'parent_id'):
            if row.get(field, '') != str(props.get(field, '') or ''):
                raise ValueError('Baseline ' + field + ' mismatch for ' + fid)
        if row.get('source_id', '') != str(meta.get('source_id', '') or ''):
            raise ValueError('Baseline source_id mismatch for ' + fid)
        if row.get('source_role', '') != str(meta.get('source_role', '') or ''):
            raise ValueError('Baseline source_role mismatch for ' + fid)
        if row.get('source_year', '') != str(meta.get('reference_year', '') or ''):
            raise ValueError('Baseline source_year mismatch for ' + fid)
        if row.get('license', '') != str(meta.get('license', '') or ''):
            raise ValueError('Baseline license mismatch for ' + fid)
        if meta.get('original_id') is not None:
            if row.get('source_shape_id', '') != str(meta.get('original_id', '')):
                raise ValueError('Baseline original/source member ID mismatch for ' + fid)
            if row.get('source_name', '') != str(props.get('name', '')):
                raise ValueError('Baseline source member name mismatch for ' + fid)
            if row.get('name_exact_match', '') != 'True':
                raise ValueError('Baseline exact-name linkage flag mismatch for ' + fid)
        elif row.get('source_shape_id', '') or row.get('source_name', '') or row.get('name_exact_match', ''):
            raise ValueError('Unexpected direct source join for aggregate ' + fid)
    return True


def feature_rows(raw, ids):
    features, containing = actual_features(raw, ids)
    crosswalk = parse_csv(raw[CROSSWALK_PATH])
    check_candidate(crosswalk, ids, features)
    return features, containing, crosswalk


def audit(raw, ids, issue):
    features, containing, rows = feature_rows(raw, ids)
    hierarchy = json_bytes(raw['data/hierarchy.json'])
    hmap = {x.get('id'): x for x in hierarchy if x.get('id')}
    parent_rows = parse_csv(raw[PARENT_PATH])
    expected_parent_ids = sorted({features[fid]['properties'].get('parent_id') for fid in ids})
    if len(expected_parent_ids) != 39:
        raise ValueError('Expected 39 actual scoped parents')
    if sorted(r['province_id'] for r in parent_rows) != expected_parent_ids:
        raise ValueError('Original parent roster differs from actual baseline parent IDs')
    per_parent = {pid: [] for pid in expected_parent_ids}
    row_audit = []
    for row in rows:
        fid = row['location_id']
        feature = features[fid]
        props, meta = feature['properties'], feature['properties'].get('metadata', {})
        geom = feature.get('geometry') or {}
        native = row['source_id'].startswith('gb:')
        parent = hmap.get(props.get('parent_id'))
        if not parent or parent.get('level') != 'province':
            raise ValueError('Scoped parent is absent or not a province record: ' + fid)
        per_parent[parent['id']].append(fid)
        row_audit.append({
            'subject_id': fid,
            'baseline_file': containing[fid],
            'baseline_name': props.get('name'),
            'candidate_name_matches_baseline': True,
            'baseline_parent_id': props.get('parent_id'),
            'baseline_parent_name': parent.get('name'),
            'baseline_parent_level': parent.get('level'),
            'baseline_parent_matches_candidate': True,
            'baseline_source_id': meta.get('source_id'),
            'baseline_original_id': meta.get('original_id'),
            'candidate_source_member_id_matches_baseline': row.get('source_shape_id', '') == str(meta.get('original_id', '') or ''),
            'candidate_source_member_name_matches_baseline': (row.get('source_name', '') == props.get('name')) if meta.get('original_id') else row.get('source_name', '') == '',
            'baseline_geometry_type': geom.get('type'),
            'candidate_baseline_geometry_type_matches': row.get('baseline_geometry_type') == geom.get('type'),
            'candidate_baseline_vertex_count_matches': row.get('baseline_vertex_count') == str(coord_count(geom.get('coordinates'))),
            'candidate_external_geometry_fields_status': 'author-recorded observation; original source geometry not retained here',
            'candidate_ine_fields_status': 'author-recorded statistical crosswalk; exact response bytes not retained here' if row.get('source_id') == 'gb:PRY:ADM2' else 'not applicable',
            'upstream_source_relationship_independently_reverified': False,
            'boundary_authority_completeness_and_legal_parentage_established': False,
        })
    if any(not row['candidate_baseline_geometry_type_matches'] or not row['candidate_baseline_vertex_count_matches'] for row in row_audit):
        raise ValueError('Candidate baseline geometry observations differ')
    for parent_row in parent_rows:
        parent = hmap[parent_row['province_id']]
        if parent_row['province_name'] != parent.get('name'):
            raise ValueError('Parent review name differs from pinned hierarchy')
        actual_count = len(per_parent[parent['id']])
        if actual_count != int(parent_row['full_scope_location_count']):
            raise ValueError('Parent scope count differs from exact scoped IDs: ' + parent['id'])
    areas = parse_csv(raw[AREA_PATH])
    scope = json_bytes(raw[SCOPE_PATH])
    if len(areas) != len(scope.get('area_scopes', [])) or len(areas) != 5:
        raise ValueError('Area scope roster differs')
    area_scope = {x['id']: x for x in scope['area_scopes']}
    if {x['area_id'] for x in areas} != set(area_scope):
        raise ValueError('Area review IDs differ from immutable scope')
    for area_row in areas:
        area_id = area_row['area_id']
        area = hmap.get(area_id)
        declared = area_scope[area_id]
        if not area or area.get('level') != 'area' or area_row['area_name'] != area.get('name') or declared.get('name') != area.get('name'):
            raise ValueError('Area identity/name differs from pinned hierarchy: ' + area_id)
        if int(area_row['owned_member_count']) != int(declared['owned_member_location_count']) or int(area_row['full_area_member_count']) != int(declared['full_area_location_count']):
            raise ValueError('Area counts differ from immutable workload scope: ' + area_id)
        if area_row['partial_area'] != str(bool(declared['partial'])):
            raise ValueError('Area partial/full flag differs: ' + area_id)
    expected_child_parents = set()
    for row in rows:
        p = features[row['location_id']]['properties']
        expected_child_parents.add(p['parent_id'])
    return {
        'issue': 1116,
        'evaluation_commit': BASELINE,
        'scope_id_count': len(ids),
        'scope_digest': hashlib.sha256(('\n'.join(ids)).encode()).hexdigest(),
        'candidate_crosswalk_row_count': len(rows),
        'baseline_feature_matches': len(features),
        'distinct_actual_parent_count': len(expected_parent_ids),
        'parent_review_rows_checked': len(parent_rows),
        'area_records_preserved_and_checked': len(areas),
        'companion_issues_preserved': [444, 446],
        'source_profile_counts': {
            'Chile geoBoundaries ADM3 candidate rows': sum(r['source_id'] == 'gb:CHL:ADM3' for r in rows),
            'Paraguay geoBoundaries ADM2 candidate rows': sum(r['source_id'] == 'gb:PRY:ADM2' for r in rows),
            'Asunción aggregate rows': sum(r['location_id'] == 'atlas:city:PRY-4837' for r in rows),
            'retained-baseline-member-ID-name matches': sum(bool(r.get('source_shape_id')) for r in rows),
            'independently reverified upstream source rows': 0,
            'Paraguay INE candidate attribute rows': sum(r['source_id'] == 'gb:PRY:ADM2' and bool(r.get('ine_2022_name')) for r in rows),
            'Paraguay INE response bytes independently reverified': 0,
        },
        'row_audit': row_audit,
        'parent_audit': [
            {'parent_id': pid, 'parent_name': hmap[pid].get('name'), 'parent_level': hmap[pid].get('level'),
             'region_parent_id': hmap[pid].get('parent_id'), 'scoped_child_count': len(per_parent[pid]),
             'scoped_child_ids': sorted(per_parent[pid]),
             'current_legal_identity_and_boundary_status': 'unresolved; retained baseline parentage is not legal boundary verification'}
            for pid in expected_parent_ids
        ],
        'findings': [
            'The legacy reproducer passes a fabricated source_shape_id because it checks row counts and name_exact_match flags but never compares candidate source IDs/names against retained baseline member metadata or restored original files.',
            'The new audit independently checks each of 214 source member IDs and names against the exact retained #935 baseline feature metadata; this establishes candidate-to-baseline agreement only.',
            'The 2020 Chile / 2012 Paraguay geoBoundaries full-country source originals were not restored in this packet; upstream source rows, current authority and positional geometry were not reverified.',
            'The 47 Paraguay INE 2022 names/codes/parents remain candidate statistical crosswalk observations; response bytes are unretained and the source is explicitly not legal boundary evidence.',
            'The Asunción aggregate remains unresolved: four source-member IDs and an undated Natural Earth-derived city territory are retained baseline descriptions, not independent evidence of administrative identity or extent.',
            'Chile is represented as 2020 geoBoundaries ADM3 communes; Paraguay as 2012 geoBoundaries ADM2 districts. Five Atlas macro-areas are documented in inherited WGSRPD and area-purpose evidence, a botanical/historical recording framework rather than an administrative equivalence. Neighboring granularity and current legal authority remain unresolved.',
        ],
        'outcome': 'limited; baseline identity links corrected, no external source or legal-boundary certification',
    }


def rows_to_csv(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


def legacy_false_positive(raw, ids, features, valid_rows):
    bad_rows = [dict(row) for row in valid_rows]
    bad_rows[1]['source_shape_id'] = 'FABRICATED-NOT-A-SOURCE-ID'
    bad_bytes = rows_to_csv(bad_rows)
    old_open = Path.open
    target = (ORIGINAL / 'findings/crosswalk.csv').resolve()

    def patched_open(path, *args, **kwargs):
        if Path(path).resolve() == target:
            return io.StringIO(bad_bytes.decode('utf-8'))
        return old_open(path, *args, **kwargs)

    saved_argv = sys.argv[:]
    capture = io.StringIO()
    try:
        Path.open = patched_open
        sys.argv = [str(ORIGINAL / 'findings/reproduce.py')]
        with contextlib.redirect_stdout(capture):
            runpy.run_path(str(ORIGINAL / 'findings/reproduce.py'), run_name='__main__')
    finally:
        Path.open = old_open
        sys.argv = saved_argv
    legacy_result = json.loads(capture.getvalue())
    if legacy_result.get('exact_source_name_links') != 214 or legacy_result.get('restoration_source_hashes_reverified') != 0:
        raise ValueError('Did not reproduce the auditor-reported false positive')
    try:
        check_candidate(bad_rows, ids, features)
        raise ValueError('Corrective validator accepted fabricated source member ID')
    except ValueError as error:
        if 'fabricated' in str(error).lower():
            raise
        if 'source member ID mismatch' not in str(error):
            raise
    return {
        'legacy_reproducer_outcome': 'passed-with-fabricated-member-id',
        'legacy_output': legacy_result,
        'mutated_subject_id': bad_rows[1]['location_id'],
        'mutated_value': bad_rows[1]['source_shape_id'],
        'mutated_candidate_csv_sha256': digest(bad_bytes),
        'new_validator_outcome': 'rejected-source-member-ID-mismatch',
        'note': 'Candidate bytes and any recomputed digest do not replace semantic row-to-baseline validation.',
    }


def controls(raw, ids, features, valid_rows):
    cases = []
    tests = [
        ('fabricated-subject', lambda r: r[0].update(location_id='gb:CHL:ADM3:INVENTED')),
        ('missing-subject', lambda r: r.pop()),
        ('duplicate-subject-row', lambda r: r.append(dict(r[0]))),
        ('wrong-baseline-name', lambda r: r[1].update(name='Wrong name')),
        ('wrong-parent-id', lambda r: r[1].update(parent_id='framework:province:invented')),
        ('fabricated-source-shape-id-even-with-rehashed-candidate', lambda r: r[1].update(source_shape_id='FABRICATED-NOT-A-SOURCE-ID')),
        ('fabricated-source-name', lambda r: r[1].update(source_name='Unrelated Source Name')),
        ('wrong-source-tier', lambda r: r[1].update(source_id='gb:CHL:ADM2')),
        ('stale-name-match-flag', lambda r: r[1].update(name_exact_match='False')),
    ]
    for name, mutate in tests:
        candidate = [dict(row) for row in valid_rows]
        mutate(candidate)
        rehashed = digest(rows_to_csv(candidate))
        try:
            check_candidate(candidate, ids, features)
        except ValueError as error:
            cases.append({'name': name, 'outcome': 'rejected', 'reason': str(error),
                          'candidate_sha256_recomputed': rehashed, 'digest_recomputation_does_not_bypass': True})
        else:
            raise ValueError('Negative control was accepted: ' + name)
    return {'method_id': 'southern-south-america-crosswalk-baseline-audit', 'kind': 'negative-control',
            'outcome': 'passed', 'controls_executed': len(cases), 'controls': cases}


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def run(outdir, legacy=None):
    _, contract, ids = scope_contract()
    raw, _ = baseline_inputs()
    scope = json_bytes(raw[SCOPE_PATH])
    if scope.get('member_location_ids') != ids:
        raise ValueError('Issue #1116 and immutable #445 subject order/content differ')
    if digest(('\n'.join(ids)).encode()) != scope.get('member_location_ids_sha256'):
        raise ValueError('Immutable #445 subject digest mismatch')
    features, _, rows = feature_rows(raw, ids)
    result = audit(raw, ids, ISSUE)
    if result['scope_digest'] != scope['member_location_ids_sha256']:
        raise ValueError('Audit subject digest differs from inherited scope')
    negative = controls(raw, ids, features, rows)
    if legacy is None:
        legacy = legacy_false_positive(raw, ids, features, rows)
    result['legacy_false_positive_reproduction'] = legacy
    positive = {'method_id': 'southern-south-america-crosswalk-baseline-audit', 'kind': 'positive-control',
                'outcome': 'passed', 'exact_subjects': len(ids), 'candidate_rows_verified': len(rows),
                'distinct_parents_verified': result['distinct_actual_parent_count'],
                'upstream_source_files_restored': 0, 'scope_hash': result['scope_digest']}
    result['positive_control_sha256'] = digest(json.dumps(positive, ensure_ascii=False, indent=2, sort_keys=True).encode() + b'\n')
    result['negative_control_sha256'] = digest(json.dumps(negative, ensure_ascii=False, indent=2, sort_keys=True).encode() + b'\n')
    write_json(outdir / 'crosswalk-baseline-audit.json', result)
    write_json(outdir / 'positive-control.json', positive)
    write_json(outdir / 'negative-controls.json', negative)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args()
    target = (PACKET / args.out_dir).resolve() if not Path(args.out_dir).is_absolute() else Path(args.out_dir).resolve()
    if PACKET.resolve() not in target.parents:
        raise ValueError('Output must remain under the issue-owned packet')
    _, _, ids = scope_contract()
    raw, _ = baseline_inputs()
    features, _, rows = feature_rows(raw, ids)
    false_positive = legacy_false_positive(raw, ids, features, rows)
    write_json(PACKET / 'legacy-false-positive-reproduction.json', false_positive)
    run(target, false_positive)


if __name__ == '__main__':
    main()
