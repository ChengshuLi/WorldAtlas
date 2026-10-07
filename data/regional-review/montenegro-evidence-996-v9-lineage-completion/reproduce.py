#!/usr/bin/env python3
"""Safely reproduce the complete retained Montenegro run-lineage roster."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path('data/regional-review/montenegro-evidence-996-v9-lineage-completion')
PREDECESSOR = Path('data/regional-review/montenegro-evidence-996-lineage-erratum')
PACKET = Path('data/regional-review/montenegro-evidence-996-erratum')
SNAPSHOT = OWNED / 'issue-scope-snapshot.json'
BASELINE = 'd401d1040c698d7273fda37c6449447548052083'
EXPECTED_RUNS = {
    f'runs/2026-10-06/{version}/run-{n}'
    for version in ['final', 'anchored', 'anchored-v2', 'anchored-v3', 'anchored-v4',
                    'anchored-v5', 'anchored-v6', 'anchored-v7', 'anchored-v8',
                    'anchored-v9', 'anchored-v10'] for n in [1, 2]
}
V9_RUNS = ['runs/2026-10-06/anchored-v9/run-1', 'runs/2026-10-06/anchored-v9/run-2']
V10_RUNS = ['runs/2026-10-06/anchored-v10/run-1', 'runs/2026-10-06/anchored-v10/run-2']
V9_CONTROL = str(PACKET / 'reproducibility-control-anchored-v9.json')
V10_CONTROL = str(PACKET / 'reproducibility-control-anchored-v10.json')
IDS_SHA256 = 'a3247490b6758e44570b1288cce6f352f6e59a52a8934e55f9dd452ed82b1757'

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def git_blob(commit: str, name: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{name}'])

def issue_scope():
    scope = json.loads((ROOT / SNAPSHOT).read_text())
    if scope['issue'] != 1235 or scope['state'] != 'open':
        raise ValueError('Issue snapshot is not the current open #1235 contract')
    contract = scope['contract']
    if contract['mode'] != 'geography' or contract['owned_paths'] != [str(OWNED) + '/']:
        raise ValueError('Unexpected issue mode or owned prefix')
    spec = contract['evidence_quality']
    ids = spec['subject_ids']
    if len(ids) != 23 or len(set(ids)) != 23 or digest(canonical(sorted(ids))) != IDS_SHA256:
        raise ValueError('The exact 23-subject issue roster changed')
    return scope, contract, spec

def inputs():
    _, _, spec = issue_scope()
    pins = spec['pins']
    if len(pins) != 28:
        raise ValueError(f'Expected 28 exact issue pins, got {len(pins)}')
    checked = {}
    for key, expected in sorted(pins.items()):
        commit, name = key.split(':', 1)
        if commit != BASELINE:
            raise ValueError(f'Issue pin does not use the accepted #1214 merge baseline: {key}')
        raw = git_blob(commit, name)
        if digest(raw) != expected:
            raise ValueError(f'Issue pin mismatch: {key}')
        baseline_raw = git_blob(BASELINE, name)
        if baseline_raw != raw:
            raise ValueError(f'Pin differs at the common evidence baseline: {key}')
        checked[name] = {'bytes': len(raw), 'sha256': expected, 'pin': key}
    correction_path = str(PREDECESSOR / 'lineage-correction.json')
    correction = json.loads(git_blob(BASELINE, correction_path))
    prior_result_paths = [str(PREDECESSOR / f'runs/2026-10-06/run-{n}/result.json') for n in [1, 2]]
    prior_result_raws = [git_blob(BASELINE, name) for name in prior_result_paths]
    if prior_result_raws[0] != prior_result_raws[1]:
        raise ValueError('Pinned predecessor runs are not byte-identical')
    prior_selector = json.loads(prior_result_raws[0])['selected_lineage']
    prior_superseded = [row['run_dir'] for row in prior_selector['superseded_runs']]
    if len(prior_superseded) != 18 or any(path in prior_superseded for path in V9_RUNS) or \
       prior_selector['authoritative_runs'] != V10_RUNS:
        raise ValueError('Pinned predecessor result does not contain the issue-reported 18-row v9 omission')
    part_path = 'data/geography/part-15.json'
    part_raw = git_blob(BASELINE, part_path)
    part = json.loads(part_raw)
    hierarchy = json.loads(git_blob(BASELINE, 'data/hierarchy.json'))
    nodes = {node['id']: node for node in hierarchy}
    ids = set(spec['subject_ids'])
    selected = [f for f in part['features'] if (f.get('id') or f.get('properties', {}).get('id')) in ids]
    found = [(f.get('id') or f.get('properties', {}).get('id')) for f in selected]
    if len(found) != 23 or set(found) != ids or len(set(found)) != 23:
        raise ValueError('Pinned part-15 does not contain every issue subject exactly once')
    contexts = []
    for feature in sorted(selected, key=lambda f: f.get('id') or f['properties']['id']):
        props = feature.get('properties') or {}
        parent_id = props.get('parent_id')
        parent = nodes.get(parent_id)
        if not parent or parent.get('level') != 'province':
            raise ValueError(f'Unexpected read-only parent identity: {parent_id}')
        contexts.append({'id': feature.get('id') or props.get('id'), 'display_name': props.get('name'),
          'source_id': (props.get('metadata') or {}).get('source_id'),
          'source_role': (props.get('metadata') or {}).get('source_role'),
          'source_reference_year': (props.get('metadata') or {}).get('reference_year'),
          'source_license': (props.get('metadata') or {}).get('license'), 'atlas_parent_id': parent_id,
          'atlas_parent_level': parent.get('level'),
          'atlas_parent_child_count_metadata': parent.get('metadata', {}).get('child_count'),
          'atlas_parent_framework_status': parent.get('metadata', {}).get('framework_status'),
          'atlas_parent_boundary_review_status': parent.get('metadata', {}).get('semantic_review', {}).get('boundary_status')})
    if len({r['atlas_parent_id'] for r in contexts}) != 23:
        raise ValueError('Expected 23 distinct read-only parent contexts')
    if {(r['source_id'], r['source_role'], r['source_reference_year'], r['source_license']) for r in contexts} != {
        ('gb:MNE:ADM1', 'Municipality', '2017', 'Open Data Commons Open Database License 1.0')
    }:
        raise ValueError('The retained 23-subject source identity/vintage/license metadata changed')
    if {r['atlas_parent_child_count_metadata'] for r in contexts} != {1}:
        raise ValueError('Expected the recorded one-child parent context for each retained feature')
    if {r['atlas_parent_framework_status'] for r in contexts} != {'retained-reference'} or \
       {r['atlas_parent_boundary_review_status'] for r in contexts} != {'open'}:
        raise ValueError('Read-only parent context is not consistently retained and unapproved')
    control = json.loads(git_blob(BASELINE, V9_CONTROL))
    comparison_path = f'{PACKET}/runs/2026-10-06/anchored-v9/run-1/comparison.json'
    comparison = json.loads(git_blob(BASELINE, comparison_path))
    if control.get('outcome') != 'passed' or control.get('runs') != 2:
        raise ValueError('Pinned v9 control does not report its two historical runs')
    if comparison.get('baseline_commit') != 'b6cfaada43a1e0472cd833d16733d1fd6065eaec':
        raise ValueError('Unexpected v9 comparison source baseline')
    comparison_hashes = {digest(git_blob(BASELINE, f'{PACKET}/runs/2026-10-06/{version}/run-{n}/comparison.json'))
                         for version in ['anchored-v9', 'anchored-v10'] for n in [1, 2]}
    if comparison_hashes != {correction['comparison_sha256']}:
        raise ValueError('Historical v9/v10 comparison bytes differ from the accepted unchanged comparison hash')
    return spec, correction, checked, contexts, control, comparison

def retained_run_dirs():
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', BASELINE, '--', str(PACKET / 'runs')], text=True)
    found = set()
    for name in raw.splitlines():
        match = re.search(r'/(runs/2026-10-06/[^/]+/run-[12])/', name)
        if match:
            found.add(match.group(1))
    return found

def build_roster(spec, correction, checked, contexts, v9_control, comparison):
    actual = retained_run_dirs()
    if actual != EXPECTED_RUNS:
        raise ValueError(f'Retained run inventory mismatch: missing={sorted(EXPECTED_RUNS-actual)}, extra={sorted(actual-EXPECTED_RUNS)}')
    older = correction['superseded_runs']
    if len(older) != 18 or any(row['run_dir'] in V9_RUNS + V10_RUNS for row in older):
        raise ValueError('Expected exactly the 18 preserved superseded rows through anchored-v8')
    authoritative = correction['authoritative_runs']
    if authoritative != V10_RUNS or correction['authoritative_control'] != V10_CONTROL:
        raise ValueError('The accepted anchored-v10 pair/control is not the authoritative lineage')
    comparison_inputs = [comparison.get('scope_source'), comparison.get('area_method_source'), *comparison.get('official_table_inputs', [])]
    run_inputs = []
    for path in comparison_inputs:
        if path and path not in run_inputs:
            run_inputs.append(path)
    additions = []
    for run_dir in V9_RUNS:
        run_no = run_dir.rsplit('-', 1)[-1]
        comparison_path = f'{PACKET}/{run_dir}/comparison.json'
        positive_path = f'{PACKET}/{run_dir}/positive-control.json'
        negative_path = f'{PACKET}/{run_dir}/negative-control.json'
        additions.append({'run_dir': run_dir,
          'reason': 'Superseded: the issue-approved anchored-v10 pair/control is the authoritative final lineage; this retained anchored-v9 run and its control are historical and remain preserved.',
          'superseded_by': {'version': 'anchored-v10', 'runs': V10_RUNS, 'control': V10_CONTROL},
          'run_control_reference': {'path': V9_CONTROL, 'sha256': digest(git_blob(BASELINE, V9_CONTROL))},
          'run_evidence': [{'path': p, 'sha256': digest(git_blob(BASELINE, p))} for p in [comparison_path, positive_path, negative_path]],
          'reported_input_references': run_inputs,
          'input_reference_limit': 'These paths are reproduced verbatim from the pinned comparison report; #1235 does not declare their original source-file bytes as pins.'})
    rows = older + additions
    active = correction['authoritative_runs']
    roster = {'version': 1, 'issue': 1235, 'source_merge': BASELINE,
      'authoritative_version': 'anchored-v10', 'authoritative_runs': active,
      'authoritative_control': {'path': V10_CONTROL, 'sha256': digest(git_blob(BASELINE, V10_CONTROL))},
      'historical_comparison_sha256': digest(git_blob(BASELINE, f'{PACKET}/{V9_RUNS[0]}/comparison.json')),
      'superseded_runs': rows,
      'superseded_control': {'path': V9_CONTROL, 'sha256': digest(git_blob(BASELINE, V9_CONTROL)),
        'reason': 'The retained anchored-v9 control documents the historical v9 pair; the accepted anchored-v10 pair/control is authoritative.'},
      'preserved_prior_superseded_rows': len(older), 'added_v9_superseded_rows': len(additions),
      'scope_subject_count': len(spec['subject_ids']), 'scope_subject_ids_sha256': IDS_SHA256,
      'scoped_retained_identity_context': contexts, 'distinct_read_only_atlas_parent_contexts': len(contexts),
      'context_limit': 'Source roles, 2017 reference metadata and Atlas parent IDs are retained identity context only; they do not verify legal parentage, boundary accuracy, or current completeness.',
      'geographic_scope': 'Lineage metadata only; no new territorial, boundary, license, or parentage finding.'}
    validate_roster(roster, actual)
    return roster

def validate_roster(model, actual=None):
    active = model['authoritative_runs']
    rows = model['superseded_runs']
    superseded = [row['run_dir'] for row in rows]
    if len(active) != 2 or len(set(active)) != len(active):
        raise ValueError('Authoritative run paths must be exactly two unique members')
    if len(set(superseded)) != len(superseded):
        raise ValueError('duplicate superseded run classification')
    if set(active) & set(superseded):
        raise ValueError('active/superseded run overlap')
    if actual is not None and set(active) | set(superseded) != actual:
        raise ValueError('run classification is incomplete or contains fabricated paths')
    if len(superseded) != 20:
        raise ValueError('Superseded run paths must contain exactly 20 members')
    if set(active) != set(V10_RUNS) or any('/anchored-v10/' not in f'/{path}/' for path in active):
        raise ValueError('active version does not match anchored-v10')
    if model['authoritative_control']['path'] != V10_CONTROL:
        raise ValueError('authoritative version/control mismatch')
    if model['superseded_control']['path'] != V9_CONTROL:
        raise ValueError('superseded version/control mismatch')
    if set(superseded) - EXPECTED_RUNS:
        raise ValueError('fabricated run directory')
    if any(not row.get('reason') for row in rows):
        raise ValueError('every superseded run needs a reason')
    return True

def controls(roster, actual, old_correction):
    rows = []
    def check(control_id, model, expected=True):
        try:
            validate_roster(model, actual)
        except ValueError as exc:
            if expected: raise AssertionError(f'{control_id} unexpectedly failed: {exc}')
            rows.append({'id': control_id, 'outcome': 'rejected', 'reason': str(exc)})
        else:
            if not expected: raise AssertionError(f'{control_id} unexpectedly passed')
            rows.append({'id': control_id, 'outcome': 'passed'})
    check('complete-22-run-positive', json.loads(json.dumps(roster)))
    for run_dir in V9_RUNS:
        incomplete = json.loads(json.dumps(roster)); incomplete['superseded_runs'] = [r for r in incomplete['superseded_runs'] if r['run_dir'] != run_dir]
        check('missing-v9-member-' + run_dir.rsplit('-', 1)[-1], incomplete, False)
    duplicate = json.loads(json.dumps(roster)); duplicate['superseded_runs'][-1] = json.loads(json.dumps(duplicate['superseded_runs'][-2]))
    check('duplicate-classification', duplicate, False)
    fabricated = json.loads(json.dumps(roster)); fabricated['superseded_runs'][-1]['run_dir'] = 'runs/2026-10-06/anchored-v99/run-9'
    check('fabricated-run', fabricated, False)
    overlap = json.loads(json.dumps(roster)); overlap['superseded_runs'][-1]['run_dir'] = overlap['authoritative_runs'][0]
    check('active-superseded-overlap', overlap, False)
    mismatch = json.loads(json.dumps(roster)); mismatch['authoritative_control']['path'] = V9_CONTROL
    check('version-control-mismatch', mismatch, False)
    old = json.loads(json.dumps(roster)); old['superseded_runs'] = old_correction['superseded_runs']
    check('incomplete-18-row-selector', old, False)
    return rows

def safe_output(raw):
    path = Path(raw)
    if not path.is_absolute(): path = ROOT / path
    owned = ROOT / OWNED
    resolved_parent = path.parent.resolve()
    if resolved_parent != owned.resolve() and owned.resolve() not in resolved_parent.parents:
        raise ValueError('output must be inside this issue-owned prefix')
    cursor = path.parent
    while cursor != ROOT.parent:
        if cursor.exists() and cursor.is_symlink(): raise ValueError(f'symlink output ancestor refused: {cursor}')
        if cursor == ROOT: break
        cursor = cursor.parent
    if path.exists(): raise FileExistsError(f'refusing to overwrite evidence: {path}')
    return path

def run(output):
    output = safe_output(output)
    spec, correction, checked, contexts, control, comparison = inputs()
    _, _, current_spec = issue_scope()
    roster = build_roster(current_spec, correction, checked, contexts, control, comparison)
    control_rows = controls(roster, retained_run_dirs(), correction)
    result = {'version': 1, 'issue': 1235, 'baseline_commit': BASELINE,
      'runner_sha256': digest(Path(__file__).read_bytes()), 'issue_subject_ids_sha256': IDS_SHA256,
      'issue_pin_count': len(checked), 'input_pins': checked, 'retained_run_directory_count': len(retained_run_dirs()),
      'selected_lineage': roster, 'controls': control_rows,
      'historical_comparison_values_changed': False, 'historical_packets_written': False,
      'geography_approval': 'unapproved'}
    raw = (json.dumps(result, indent=2, ensure_ascii=False) + '\n').encode()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'result.json').write_bytes(raw)
    print(json.dumps({'output': str(output), 'result_sha256': digest(raw), 'pins': len(checked),
      'runs': result['retained_run_directory_count'], 'controls': control_rows}, indent=2))

def finalize():
    _, correction, checked, contexts, control, comparison = inputs()
    root = ROOT / OWNED
    paths = [root / 'runs/2026-10-07/final-v4/run-1/result.json', root / 'runs/2026-10-07/final-v4/run-2/result.json']
    raws = [p.read_bytes() for p in paths]
    if raws[0] != raws[1]: raise ValueError('independent complete reproduction reports differ byte-for-byte')
    report = json.loads(raws[0])
    roster = report['selected_lineage']
    actual = retained_run_dirs()
    validate_roster(roster, actual)
    if report['runner_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('runner bytes changed between reproduction runs and finalization')
    (root / 'lineage-completion.json').write_text(json.dumps(roster, indent=2, ensure_ascii=False) + '\n')
    audit = {'version': 1, 'kind': 'complete-retained-lineage-roster', 'outcome': 'passed',
      'runs': [{'path': p.relative_to(root).as_posix(), 'sha256': digest(raw)} for p, raw in zip(paths, raws)],
      'byte_identical': True, 'issue_pin_count': len(checked), 'retained_run_directory_count': len(actual),
      'authoritative_run_count': len(roster['authoritative_runs']), 'superseded_run_count': len(roster['superseded_runs']),
      'preserved_prior_superseded_rows': roster['preserved_prior_superseded_rows'],
      'added_v9_superseded_rows': roster['added_v9_superseded_rows'],
      'positive_controls': 1, 'negative_controls': 7, 'both_v9_members_rejected_when_missing': True,
      'subject_count': 23, 'distinct_read_only_parent_contexts': len(contexts),
      'historical_packets_modified': False, 'geography_approval': 'unapproved'}
    (root / 'lineage-control.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(audit, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('run'); p.add_argument('--output-dir', required=True)
    sub.add_parser('finalize'); args = parser.parse_args()
    if args.cmd == 'run': run(args.output_dir)
    else: finalize()
