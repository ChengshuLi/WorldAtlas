#!/usr/bin/env python3
"""Validate issue #1124's exact parent roster and companion area ancestry."""
import argparse, csv, hashlib, io, json, subprocess, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path

BASELINE = '93c901e1c0b44073233fd3d48d403985a0cf2c52'
PACKET = 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b'
OWNED = 'data/regional-review/south-america-b4-area-validation-20261006'
PARTS = (0, 2, 20, 25, 28, 29)
AREA = {
 'framework:area:chile-central:4657b9c2c6bd': ('Chile Central', 'CLC'),
 'framework:area:chile-north:dae240b20a69': ('Chile North', 'CLN'),
 'framework:area:chile-south:f59e68fc819a': ('Chile South', 'CLS'),
 'framework:area:juan-fernandez-is:fba2727a951e': ('Juan Fernández Is.', 'JNF'),
 'framework:area:paraguay:b8f36a1a90ee': ('Paraguay', 'PAR'),
}
AREA_COUNTS = {
 'framework:area:chile-central:4657b9c2c6bd': (75, 252),
 'framework:area:chile-north:dae240b20a69': (29, 29),
 'framework:area:chile-south:f59e68fc819a': (62, 62),
 'framework:area:juan-fernandez-is:fba2727a951e': (1, 1),
 'framework:area:paraguay:b8f36a1a90ee': (48, 243),
}
EXPECTED_PINS = {
 'hierarchy': ('data/hierarchy.json', '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b'),
 'world_index': ('data/world-index.json', 'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03'),
 'original_scope': (f'{PACKET}/scope/embedded-workload-scope.json', '29a5984b06b96dff899a2c4d16659e63b66f75ab25dd2a744191e0267bc21af8'),
 'parent_rows': (f'{PACKET}/findings/province-review.csv', '26fa50de3fa6515fface069755f89b13dc6cb674b41fb95d9abcb9fbd0f91c2f'),
 'area_rows': (f'{PACKET}/findings/area-review.csv', '7971335af98f6c8be11ab8699caca7f698384b2dd871983f5059b66da3fad17a'),
 'area_crosswalk': (f'{PACKET}/findings/area-source-crosswalk.csv', '66093ef613629ec10f28ba7390e38f75f91ace2b3b2d7fdc9ae19f5119798790'),
 'area_reproducer': (f'{PACKET}/findings/reproduce-area-source-crosswalk.py', '6ba491ef8e7f514ebeb8a480308ef2f9716528e2dbe728cf87471c128b530bbc'),
 'companion_scopes': (f'{PACKET}/scope/companion-workload-scopes.json', '40c1faa8fb3fa51eff8653eb92312af753692d1790558a8597f9e96d9ca70ec1'),
 'source_register': (f'{PACKET}/source/source-register.json', '1e124f1c15ce6b9396ffd97e2d791b2d7cc995eb7d134f2d6dcfed1f18f235ca'),
}
LEVEL3_SHA = '7eaf281dfbdca610c93938326c333d7c62d8e82ce3cba63b299d5a3a01d0003f'
LEVEL4_SHA = '6fa350a0bb5939df0c665ae6cf253ddb0aa85fef6daa684c87ba400faf93b1c2'

class InvalidEvidence(ValueError): pass

def require(ok, message):
    if not ok: raise InvalidEvidence(message)

def sha(data): return hashlib.sha256(data).hexdigest()
def subject_hash(ids): return sha(json.dumps(sorted(ids), ensure_ascii=False, separators=(',', ':')).encode())
def roster_hash(ids): return sha('\n'.join(ids).encode())
def git_bytes(repo, commit, path):
    return subprocess.check_output(['git', '-C', str(repo), 'show', f'{commit}:{path}'], timeout=60)
def read_json(raw, label):
    try: return json.loads(raw)
    except Exception as exc: raise InvalidEvidence(f'{label}: invalid JSON: {exc}') from exc
def csv_rows(raw, label):
    try: return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    except Exception as exc: raise InvalidEvidence(f'{label}: invalid CSV: {exc}') from exc

def lineage_for(feature, hierarchy):
    parent_id = feature.get('parent_id')
    parent = hierarchy.get(parent_id)
    require(parent is not None and parent.get('level') == 'province', f'No pinned province parent for {feature.get("id")}')
    area_id = parent.get('parent_id')
    area = hierarchy.get(area_id)
    require(area is not None and area.get('level') == 'area', f'No pinned area ancestor for {feature.get("id")}')
    return parent, area

def validate_issue_scope(issue_ids, issue_hash, source_scope):
    require(len(issue_ids) == 215 and len(set(issue_ids)) == 215, 'Issue #1124 scope must contain exactly 215 unique subjects')
    require(subject_hash(issue_ids) == issue_hash, 'Issue #1124 subject hash mismatch')
    source_ids = source_scope['member_location_ids']
    require(len(source_ids) == 215 and len(set(source_ids)) == 215, 'Pinned #445 scope is not 215 unique IDs')
    require(roster_hash(source_ids) == source_scope['member_location_ids_sha256'], 'Pinned #445 source roster hash mismatch')
    require(set(issue_ids) == set(source_ids), 'Rehashed or stale #1124 subject scope differs from immutable #445 roster')

def validate_parent_rows(rows, issue_ids, features, hierarchy):
    expected = defaultdict(set)
    for sid in issue_ids:
        require(sid in features, f'Missing native feature: {sid}')
        props = features[sid]
        require(props.get('id') == sid, f'Feature/property ID mismatch: {sid}')
        parent, area = lineage_for(props, hierarchy)
        expected[parent['id']].add(sid)
    row_ids = [r.get('province_id', '') for r in rows]
    require(len(rows) == 39 and len(set(row_ids)) == 39, 'Parent table must contain 39 unique parent IDs')
    require(set(row_ids) == set(expected), 'Parent table IDs differ from the exact native subject parents')
    for row in rows:
        pid = row['province_id']; node = hierarchy.get(pid)
        require(node is not None and node.get('level') == 'province', f'Unknown/non-province parent: {pid}')
        require(row['province_name'] == node.get('name'), f'Parent name mismatch: {pid}')
        listed = row['scoped_location_ids'].split(';')
        require(len(listed) == len(set(listed)), f'Duplicate subject assignment under {pid}')
        require(set(listed) == expected[pid], f'Parent subject roster mismatch: {pid}')
        require(int(row['full_scope_location_count']) == len(expected[pid]), f'Parent count mismatch: {pid}')
        require(not row['partial_province'].strip().lower() in ('true', 'yes', '1'), f'Parent scope is marked partial: {pid}')
        require(node.get('metadata', {}).get('child_count') == len(expected[pid]), f'Pinned hierarchy child count mismatch: {pid}')
    return expected

def validate_crosswalk(rows, area_rows, parent_rows, issue_ids, features, hierarchy):
    keys = [(r.get('record_type'), r.get('area_id') if r.get('record_type') == 'area' else r.get('parent_id')) for r in rows]
    require(len(rows) == 44 and len(keys) == len(set(keys)), 'Crosswalk must have 44 unique area/parent rows')
    require({r.get('area_id') for r in rows if r.get('record_type') == 'area'} == set(AREA), 'Crosswalk area IDs differ')
    parent_by_id = {r['province_id']: r for r in parent_rows}
    area_by_id = {r['area_id']: r for r in area_rows}
    require(set(area_by_id) == set(AREA), 'Area table must have exactly the five scoped areas')
    issue_area_counts = Counter(lineage_for(features[sid], hierarchy)[1]['id'] for sid in issue_ids)
    all_area_counts = Counter()
    for sid, props in features.items():
        if props.get('parent_id') in hierarchy:
            parent = hierarchy[props['parent_id']]
            if parent.get('level') == 'province' and parent.get('parent_id') in AREA:
                all_area_counts[parent['parent_id']] += 1
    for aid, (name, code) in AREA.items():
        node = hierarchy.get(aid); row = area_by_id[aid]
        require(node is not None and node.get('level') == 'area' and node.get('name') == name, f'Area identity mismatch: {aid}')
        require(row['area_name'] == name, f'Area review name mismatch: {aid}')
        issue_count, full_count = AREA_COUNTS[aid]
        require(issue_area_counts[aid] == issue_count and int(row['owned_member_count']) == issue_count, f'Issue owned area count mismatch: {aid}')
        require(all_area_counts[aid] == full_count and int(row['full_area_member_count']) == full_count, f'Native full area roster/count mismatch: {aid}')
        cross = next(r for r in rows if r.get('record_type') == 'area' and r.get('area_id') == aid)
        require(cross['area_name'] == name and cross['parent_id'] == node.get('parent_id'), f'Area crosswalk name/parent mismatch: {aid}')
        require(int(cross['area_owned_member_count']) == issue_count and int(cross['full_area_member_count']) == full_count, f'Area crosswalk population mismatch: {aid}')
        require(int(cross['atlas_province_child_count']) == node['metadata']['child_count'], f'Area child count mismatch: {aid}')
        require(cross['wgsrpd_code'] == code and cross['wgsrpd_l2'] == '85,00', f'Area source label/region mismatch: {aid}')
    expected_parent_ids = set(parent_by_id)
    cross_parent_ids = {r.get('parent_id') for r in rows if r.get('record_type') == 'parent'}
    require(cross_parent_ids == expected_parent_ids and len(cross_parent_ids) == 39, 'Crosswalk parent roster differs from exact issue scope')
    for row in (r for r in rows if r.get('record_type') == 'parent'):
        pid = row['parent_id']; node = hierarchy[pid]; source = parent_by_id[pid]
        require(row['area_id'] == node.get('parent_id') and row['area_id'] in AREA, f'Parent area ancestry mismatch: {pid}')
        require(row['area_name'] == AREA[row['area_id']][0], f'Parent area label mismatch: {pid}')
        require(row['atlas_province_child_count'] == source['full_scope_location_count'] == str(node['metadata']['child_count']), f'Parent child count mismatch: {pid}')
    return issue_area_counts, all_area_counts

def write_csv(path, columns, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n'); writer.writeheader(); writer.writerows(rows)

def negative_controls(parent_rows, area_rows, crosswalk_rows, issue_ids, issue_hash, source_scope, features, hierarchy):
    cases = []
    def rejected(name, fn):
        try: fn()
        except (InvalidEvidence, KeyError, ValueError):
            cases.append({'case': name, 'rejected': True})
        else: raise InvalidEvidence(f'Negative control unexpectedly passed: {name}')
    rejected('duplicate-parent-row', lambda: validate_parent_rows(parent_rows + [dict(parent_rows[0])], issue_ids, features, hierarchy))
    rejected('missing-parent-row', lambda: validate_parent_rows(parent_rows[:-1], issue_ids, features, hierarchy))
    foreign = [dict(r) for r in parent_rows]; foreign[0]['province_id'] = 'atlas:foreign:parent'
    rejected('foreign-parent', lambda: validate_parent_rows(foreign, issue_ids, features, hierarchy))
    duplicate = [dict(r) for r in parent_rows]; duplicate[0]['scoped_location_ids'] += ';' + duplicate[1]['scoped_location_ids'].split(';')[0]
    rejected('duplicate-subject-assignment', lambda: validate_parent_rows(duplicate, issue_ids, features, hierarchy))
    missing = [dict(r) for r in parent_rows]; missing[0]['scoped_location_ids'] = ';'.join(missing[0]['scoped_location_ids'].split(';')[1:])
    rejected('missing-subject-assignment', lambda: validate_parent_rows(missing, issue_ids, features, hierarchy))
    badname = [dict(r) for r in parent_rows]; badname[0]['province_name'] += ' altered'
    rejected('wrong-parent-name', lambda: validate_parent_rows(badname, issue_ids, features, hierarchy))
    badcount = [dict(r) for r in parent_rows]; badcount[0]['full_scope_location_count'] = str(int(badcount[0]['full_scope_location_count']) + 1)
    rejected('wrong-parent-count', lambda: validate_parent_rows(badcount, issue_ids, features, hierarchy))
    changed_scope = list(issue_ids); changed_scope[0] = 'atlas:foreign:subject'
    rejected('rehash-does-not-authorize-foreign-scope', lambda: validate_issue_scope(changed_scope, subject_hash(changed_scope), source_scope))
    badcross = [dict(r) for r in crosswalk_rows]
    area_row = next(r for r in badcross if r['record_type'] == 'area'); area_row['wgsrpd_code'] = 'ZZZ'
    rejected('wrong-area-source-label', lambda: validate_crosswalk(badcross, area_rows, parent_rows, issue_ids, features, hierarchy))
    require(len(cases) == 9, 'Expected nine negative controls')
    return {'method_id':'exact-roster-and-ancestry','kind':'negative-control','outcome':'passed','cases':cases}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--level3', required=True); parser.add_argument('--level4', required=True)
    parser.add_argument('--scope', default=f'{OWNED}/scope.json')
    parser.add_argument('--output-dir', default=f'{OWNED}/output')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    owned = repo / OWNED; scratch = owned / 'scratch'; output = repo / args.output_dir
    scratch.mkdir(parents=True, exist_ok=True); output.mkdir(parents=True, exist_ok=True)
    level3 = Path(args.level3).read_bytes(); level4 = Path(args.level4).read_bytes()
    require(sha(level3) == LEVEL3_SHA, 'TDWG Level 3 source hash mismatch')
    require(sha(level4) == LEVEL4_SHA, 'TDWG Level 4 source hash mismatch')
    issue_scope = read_json((repo / args.scope).read_bytes(), 'issue scope')
    source_paths = {name: path for name, (path, _) in EXPECTED_PINS.items()}
    input_bytes = {path: git_bytes(repo, BASELINE, path) for path in source_paths.values()}
    for name, (path, expected) in EXPECTED_PINS.items():
        require(sha(input_bytes[path]) == expected, f'Issue pin mismatch: {name}')
    source_scope = read_json(input_bytes[EXPECTED_PINS['original_scope'][0]], 'pinned #445 scope')
    companion = read_json(input_bytes[EXPECTED_PINS['companion_scopes'][0]], 'companion snapshots')
    issue_ids = issue_scope['subject_ids']; validate_issue_scope(issue_ids, issue_scope['subject_ids_sha256'], source_scope)
    require(companion.get('retrieved_at') == '2026-10-05' and {x['issue'] for x in companion['issues']} == {444, 446}, 'Unexpected companion snapshots')
    hierarchy_raw = git_bytes(repo, BASELINE, 'data/hierarchy.json'); hierarchy_list = read_json(hierarchy_raw, 'pinned hierarchy')
    hierarchy = {node['id']: node for node in hierarchy_list}
    world_index = read_json(git_bytes(repo, BASELINE, 'data/world-index.json'), 'pinned world index')
    indexed = set(world_index.get('parts', [])); feature_map = {}; feature_part = {}
    part_bytes = {}
    for number in PARTS:
        path = f'data/geography/part-{number}.json'; raw = git_bytes(repo, BASELINE, path); part_bytes[path] = raw
        require(path.replace('data/', '') in indexed or path in indexed, f'Part absent from pinned world index: {path}')
        collection = read_json(raw, path)
        for feature in collection.get('features', []):
            fid = feature.get('id') or feature.get('properties', {}).get('id')
            if fid in feature_map:
                require(feature_map[fid] == feature.get('properties', {}), f'Duplicate/different feature across parts: {fid}')
            feature_map[fid] = feature.get('properties', {}); feature_part[fid] = path
    parent_rows = csv_rows(input_bytes[EXPECTED_PINS['parent_rows'][0]], 'parent rows')
    area_rows = csv_rows(input_bytes[EXPECTED_PINS['area_rows'][0]], 'area rows')
    crosswalk_raw = input_bytes[EXPECTED_PINS['area_crosswalk'][0]]
    crosswalk_rows = csv_rows(crosswalk_raw, 'source crosswalk')
    parent_groups = validate_parent_rows(parent_rows, issue_ids, feature_map, hierarchy)
    negative = negative_controls(parent_rows, area_rows, crosswalk_rows, issue_ids, issue_scope['subject_ids_sha256'], source_scope, feature_map, hierarchy)
    # Validate all three issue rosters against native parent->area ancestry.
    roster_rows = []
    roster_ids = {}
    for number, ids, area_scopes in [(445, source_scope['member_location_ids'], source_scope['area_scopes'])] + [(x['issue'], x['member_location_ids'], x['area_scopes']) for x in companion['issues']]:
        require(len(ids) == len(set(ids)) and roster_hash(ids) == (source_scope['member_location_ids_sha256'] if number == 445 else next(x['member_location_ids_sha256'] for x in companion['issues'] if x['issue'] == number)), f'Issue #{number} snapshot identity/hash mismatch')
        roster_ids[number] = ids
        actual_counts = Counter(); area_members = defaultdict(set)
        for sid in ids:
            require(sid in feature_map, f'Companion native member missing from pinned parts: #{number} {sid}')
            parent, area = lineage_for(feature_map[sid], hierarchy)
            actual_counts[area['id']] += 1; area_members[area['id']].add(sid)
            roster_rows.append({'scope_issue': f'#{number}', 'subject_id': sid, 'parent_id': parent['id'], 'parent_name': parent['name'], 'area_id': area['id'], 'area_name': area['name'], 'source_part': feature_part[sid]})
        for scope_area in area_scopes:
            aid = scope_area['id']; require(aid in hierarchy and hierarchy[aid]['level'] == 'area', f'Companion scope area not in baseline hierarchy: #{number} {aid}')
            require(actual_counts[aid] == scope_area['owned_member_location_count'], f'Companion actual area membership/count mismatch: #{number} {aid}')
            require(scope_area['full_area_location_count'] == hierarchy[aid]['metadata']['member_location_count'] if 'member_location_count' in hierarchy[aid].get('metadata', {}) else True, f'Companion full area count mismatch: #{number} {aid}')
    # The issue and companion snapshots must partition the complete Chile Central and Paraguay native descendants.
    native_area_members = defaultdict(set)
    for sid, props in feature_map.items():
        parent = hierarchy.get(props.get('parent_id'))
        if parent and parent.get('level') == 'province' and parent.get('parent_id') in AREA:
            native_area_members[parent['parent_id']].add(sid)
    all_scoped = set(roster_ids[445]) | set(roster_ids[444]) | set(roster_ids[446])
    for aid in AREA:
        require(native_area_members[aid] == {sid for sid in all_scoped if lineage_for(feature_map[sid], hierarchy)[1]['id'] == aid}, f'Issue/companion IDs do not exhaust native area descendants: {aid}')
    issue_area_counts, native_area_counts = validate_crosswalk(crosswalk_rows, area_rows, parent_rows, issue_ids, feature_map, hierarchy)
    # Restore exact baseline reproducer/input files to bounded scratch; never alter their originals.
    with tempfile.TemporaryDirectory(prefix='run-one-', dir=scratch) as d1, tempfile.TemporaryDirectory(prefix='run-two-', dir=scratch) as d2:
        runs = []
        for dirname in (d1, d2):
            temp = Path(dirname); source_dir = temp / 'inputs'; source_dir.mkdir()
            copied = {}
            for path in [EXPECTED_PINS['hierarchy'][0], EXPECTED_PINS['parent_rows'][0], EXPECTED_PINS['area_rows'][0], EXPECTED_PINS['original_scope'][0], EXPECTED_PINS['companion_scopes'][0]]:
                dest = source_dir / (str(len(copied)) + '-' + Path(path).name); dest.write_bytes(input_bytes[path]); copied[path] = dest
            old_script_path = temp / 'reproduce-area-source-crosswalk.py'; old_script_path.write_bytes(input_bytes[EXPECTED_PINS['area_reproducer'][0]])
            generated = temp / 'crosswalk.csv'
            cmd = [sys.executable, str(old_script_path), '--level3', str(Path(args.level3).resolve()), '--level4', str(Path(args.level4).resolve()), '--hierarchy', str(copied[EXPECTED_PINS['hierarchy'][0]]), '--parents', str(copied[EXPECTED_PINS['parent_rows'][0]]), '--areas', str(copied[EXPECTED_PINS['area_rows'][0]]), '--workload-scope', str(copied[EXPECTED_PINS['original_scope'][0]]), '--companion-scopes', str(copied[EXPECTED_PINS['companion_scopes'][0]]), '--output', str(generated)]
            subprocess.run(cmd, cwd=repo, check=True, capture_output=True, text=True, timeout=60)
            runs.append(generated.read_bytes())
        require(runs[0] == runs[1] == crosswalk_raw, 'Original source crosswalk does not reproduce byte-for-byte twice')
        crosswalk_hash = sha(runs[0])
    # Record one exact native roster mapping per source workload; tables contain IDs, not free-standing counts.
    enriched = []
    for row in roster_rows:
        props = feature_map[row['subject_id']]; metadata = props.get('metadata', {})
        enriched.append({**row, 'feature_name': props.get('name', ''), 'source_id': metadata.get('source_id', ''),
          'source_name': metadata.get('source_name', ''), 'source_url': metadata.get('source_url', ''),
          'reference_year': metadata.get('reference_year', ''), 'license': metadata.get('license', ''),
          'administrative_level': metadata.get('administrative_level', ''), 'source_role': metadata.get('source_role', '')})
    cols = ['scope_issue','subject_id','feature_name','parent_id','parent_name','area_id','area_name','source_part','source_id','source_name','source_url','reference_year','license','administrative_level','source_role']
    write_csv(output / 'companion-membership.csv', cols, enriched)
    issue_rows = [r for r in enriched if r['scope_issue'] == '#445']
    write_csv(output / 'subject-parent-area.csv', cols[1:], [{k:r[k] for k in cols[1:]} for r in issue_rows])
    companion_counts = {str(n): dict(Counter(r['area_name'] for r in roster_rows if r['scope_issue'] == f'#{n}')) for n in (445,444,446)}
    metrics = {
      'issue_1124_subjects': len(issue_ids), 'native_subject_matches': sum(sid in feature_map for sid in issue_ids),
      'distinct_parent_ids': len(parent_groups), 'parent_rows': len(parent_rows), 'parent_assignments': sum(len(x) for x in parent_groups.values()),
      'companion_issue_444_members': len(roster_ids[444]), 'companion_issue_446_members': len(roster_ids[446]),
      'companion_native_members_checked': sum(len(x) for x in roster_ids.values()), 'companion_area_membership_mismatches': 0,
      'source_crosswalk_rows': len(crosswalk_rows), 'source_crosswalk_reproduced_runs': 2,
    }
    for aid, (name, _) in AREA.items():
        key = name.casefold().replace(' ', '_').replace('ñ','n').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('.','').replace('(','').replace(')','').replace('fernandez','fernandez')
        metrics[f'{key}_issue_members'] = issue_area_counts[aid]
        metrics[f'{key}_native_members'] = native_area_counts[aid]
    for issue in (445,444,446):
        for name, value in companion_counts[str(issue)].items():
            metrics[f'issue_{issue}_{name.casefold().replace(" ","_").replace("ñ","n").replace("á","a").replace("í","i").replace("ó","o").replace("ú","u")}'] = value
    report = {
      'version': 1, 'issue': 1124, 'baseline_commit': BASELINE, 'status': 'validated-with-limits',
      'issue_subject_hash': issue_scope['subject_ids_sha256'], 'source_scope_hash': source_scope['member_location_ids_sha256'],
      'metrics': metrics, 'area_membership_by_scope_issue': companion_counts,
      'native_full_area_counts': {name: native_area_counts[aid] for aid,(name,_) in AREA.items()},
      'parent_roster_sha256': sha('\n'.join(sorted(parent_groups)).encode()),
      'reproduced_source_crosswalk_sha256': crosswalk_hash,
      'checks': {'issue_scope_matches_immutable_445': True, 'all_subject_parent_assignments_match_native_parts': True,
        'all_parent_rows_unique_and_exact': True, 'all_companion_snapshots_match_native_ancestry': True,
        'all_five_area_populations_match_native_descendants': True, 'source_crosswalk_reproduced_twice_byte_identically': True},
      'limits': ['Membership and ancestry are checked against the pinned Atlas hierarchy and retained source snapshots, not independently adjudicated legal boundaries.',
        'Chile source crosswalk remains tied to geoBoundaries 2020; current SUBDERE 2023 polygons could not be extracted/reuse-cleared in the earlier source review.',
        'Paraguay source crosswalk remains a 2012 geoBoundaries roster supplemented by 2022 statistical attributes; INE lines are referential, not legal boundary evidence.',
        'The TDWG WGSRPD Level 3/4 tables are historical botanical distribution units, not current administrative crosswalks; exact upstream hashes and restoration instructions are retained, while unknown reuse terms prevent redistribution.']}
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'positive-control.json').write_text(json.dumps({'method_id':'exact-roster-and-ancestry','kind':'positive-control','outcome':'passed','description':'The immutable 215-ID issue roster, exact 39 parent rows, all three issue snapshots, native parents and five area populations pass.'}, ensure_ascii=False, indent=2)+'\n')
    (output / 'negative-control.json').write_text(json.dumps(negative, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status':report['status'],'metrics':metrics,'companion_counts':companion_counts,'crosswalk_sha256':crosswalk_hash},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(f'validation failed: {exc}', file=sys.stderr); sys.exit(1)
