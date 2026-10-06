#!/usr/bin/env python3
"""Offline, read-only audit of #1179's retained v9/v10 lineage contradiction."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path('data/regional-review/montenegro-evidence-996-lineage-erratum')
PACKET = Path('data/regional-review/montenegro-evidence-996-erratum')
BASELINE = 'b4e110df5a0a0953e91bf9abc89dccdb0b05e6e1'
OLD_MANIFEST = PACKET / 'evidence-quality.json'
EXPECTED_IDS_HASH = 'a3247490b6758e44570b1288cce6f352f6e59a52a8934e55f9dd452ed82b1757'
EXPECTED_SCOPE_SNAPSHOT_SHA256 = '4555f40de1427681c9f7717af6dca01a1777a2d9d12b511e1cae361ed15a3261'

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def git_blob(commit: str, name: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{name}'])

def load_pinned_inputs():
    scope_raw = (ROOT / OWNED / 'issue-scope-snapshot.json').read_bytes()
    if digest(scope_raw) != EXPECTED_SCOPE_SNAPSHOT_SHA256:
        raise ValueError('issue contract snapshot bytes changed')
    scope = json.loads(scope_raw)
    if scope['issue'] != 1207 or scope['evidence_quality']['version'] != 1:
        raise ValueError('unexpected issue scope snapshot')
    if len(scope['evidence_quality']['subject_ids']) != 23:
        raise ValueError('scope must retain the exact 23-subject roster')
    if digest(json.dumps(sorted(scope['evidence_quality']['subject_ids']),separators=(',',':')).encode()) != EXPECTED_IDS_HASH:
        raise ValueError('subject roster differs from accepted issue contract')
    pins = scope['evidence_quality']['pins']
    if len(pins) != 20:
        raise ValueError('expected exactly the 20 issue-declared input pins')
    checked = {}
    for key, expected in sorted(pins.items()):
        commit, name = key.split(':', 1)
        raw = git_blob(commit, name)
        if digest(raw) != expected:
            raise ValueError(f'issue pin mismatch: {key}')
        # The current evidence-quality v1 baseline is one commit. Verify every
        # mixed issue pin is byte-identical at its truthful common baseline.
        baseline_raw = git_blob(BASELINE, name)
        if digest(baseline_raw) != expected:
            raise ValueError(f'pin unavailable at common baseline: {key}')
        checked[name] = {'bytes':len(raw),'sha256':expected,'pin':key}
    original = json.loads(git_blob(BASELINE, str(OLD_MANIFEST)))
    old_runner_path = str(PACKET / 'reproduce.py')
    old_runner = git_blob(BASELINE, old_runner_path).decode('utf-8')
    for fragment in (
        'run_dirs = [PACKET / "runs/2026-10-06/anchored-v10/run-1", PACKET / "runs/2026-10-06/anchored-v10/run-2"]',
        '"run_dir": "runs/2026-10-06/anchored-v10/run-1", "reason": "Superseded because its research note predates the corrected metric input provenance and final substantive review."',
        '"superseded_control": {"path": "data/regional-review/montenegro-evidence-996-erratum/reproducibility-control-anchored-v10.json"',
    ):
        if fragment not in old_runner:
            raise ValueError('pinned predecessor finalizer no longer matches the recorded contradiction')
    ids = set(scope['evidence_quality']['subject_ids'])
    part_path = 'data/geography/part-15.json'
    part = json.loads(git_blob(BASELINE, part_path))
    selected = [f for f in part['features'] if (f.get('id') or f.get('properties',{}).get('id')) in ids]
    selected_ids = [f.get('id') or f.get('properties',{}).get('id') for f in selected]
    if len(selected) != 23 or set(selected_ids) != ids or len(set(selected_ids)) != 23:
        raise ValueError('pinned part-15 does not contain the exact 23 issue subjects once each')
    source_rows = []
    for feature in sorted(selected, key=lambda f:f.get('id') or f['properties']['id']):
        props = feature.get('properties') or {}; metadata = props.get('metadata') or {}
        source_rows.append({'id':feature.get('id') or props.get('id'),
          'display_name':props.get('name'),'source_id':metadata.get('source_id'),
          'source_role':metadata.get('source_role'),'source_reference_year':metadata.get('reference_year'),
          'source_license':metadata.get('license'),'atlas_parent_id':props.get('parent_id')})
    parents = [row['atlas_parent_id'] for row in source_rows]
    if len(set(parents)) != 23 or any(not x for x in parents):
        raise ValueError('expected the retained one-to-one parent-context roster')
    hierarchy_path = 'data/hierarchy.json'
    hierarchy = json.loads(git_blob(BASELINE, hierarchy_path))
    nodes = {node['id']:node for node in hierarchy}
    for row in source_rows:
        parent = nodes.get(row['atlas_parent_id'])
        if not parent or parent.get('level') != 'province' or parent.get('metadata',{}).get('child_count') != 1:
            raise ValueError(f"unexpected read-only Atlas parent context: {row['atlas_parent_id']}")
        row['atlas_parent_level'] = parent['level']
        row['atlas_parent_child_count_metadata'] = parent['metadata']['child_count']
        row['atlas_parent_framework_status'] = parent['metadata'].get('framework_status')
        row['atlas_parent_boundary_review_status'] = parent['metadata'].get('semantic_review',{}).get('boundary_status')
    if {r['atlas_parent_framework_status'] for r in source_rows} != {'retained-reference'} or \
       {r['atlas_parent_boundary_review_status'] for r in source_rows} != {'open'}:
        raise ValueError('parent context is not consistently marked as retained and unapproved')
    if {(r['source_id'],r['source_role'],r['source_reference_year'],r['source_license']) for r in source_rows} != {
        ('gb:MNE:ADM1','Municipality','2017','Open Data Commons Open Database License 1.0')
    }:
        raise ValueError('retained scoped source identity/vintage/license metadata changed')
    checked[part_path] = {'bytes':len(git_blob(BASELINE,part_path)),
      'sha256':digest(git_blob(BASELINE,part_path)), 'pin':'b6cfaada43a1e0472cd833d16733d1fd6065eaec:'+part_path}
    return scope, original, checked, source_rows

def corrected_selection(original, source_rows):
    repro = original['reproduction']
    active = [row['run_dir'] for row in repro['runs']]
    superseded_rows = repro['superseded_runs']
    superseded = [row['run_dir'] for row in superseded_rows]
    if active != ['runs/2026-10-06/anchored-v10/run-1','runs/2026-10-06/anchored-v10/run-2']:
        raise ValueError('authoritative active runs are not the retained v10 pair')
    overlap = sorted(set(active) & set(superseded))
    if len(overlap) != 2:
        raise ValueError('expected precisely the two active/superseded v10 path contradictions')
    v10_control = 'data/regional-review/montenegro-evidence-996-erratum/reproducibility-control-anchored-v10.json'
    v9_control = 'data/regional-review/montenegro-evidence-996-erratum/reproducibility-control-anchored-v9.json'
    validation_paths = [x['evidence_path'] for x in original['validation'] if x.get('kind') == 'reproducibility']
    if repro['superseded_control']['path'] != v10_control or validation_paths != [v10_control]:
        raise ValueError('the original control path conflict differs from issue report')
    if 'v9' not in repro['superseded_control']['reason'].lower():
        raise ValueError('original superseded-control reason does not describe v9')
    preserved_rows = [row for row in superseded_rows if row['run_dir'] not in active]
    return {
        'version':1,
        'authoritative_version':'anchored-v10',
        'authoritative_runs':active,
        'authoritative_control':v10_control,
        'authoritative_control_sha256':digest(git_blob(BASELINE,v10_control)),
        'authoritative_runner':json.loads(git_blob(BASELINE,v10_control))['finalizer_runner_code_pin'],
        'comparison_sha256':repro['runs'][0]['outputs']['comparison.json'],
        'authoritative_runs_byte_identical':True,
        'superseded_runs':preserved_rows,
        'superseded_control':{
            'path':v9_control,
            'sha256':digest(git_blob(BASELINE,v9_control)),
            'reason':'The anchored-v9 control is retained as historical evidence and is superseded by the accepted anchored-v10 pair/control.'
        },
        'validation_control_path':v10_control,
        'removed_active_superseded_intersections':overlap,
        'historical_contradiction':{
            'active_runs':active,
            'superseded_run_rows':[row for row in superseded_rows if row['run_dir'] in active],
            'old_superseded_control':repro['superseded_control'],
            'old_validation_control_path':validation_paths[0]
        },
        'scope_subject_count':23,
        'scope_subject_ids_sha256':EXPECTED_IDS_HASH,
        'scoped_retained_identity_context':source_rows,
        'distinct_read_only_atlas_parent_contexts':23,
        'context_limit':'Retained feature labels/source metadata and parent IDs are identity context only; they do not verify official legal parentage, boundary accuracy, or complete national coverage.',
        'geographic_scope':'lineage metadata only; no new territorial, boundary, or parentage finding'
    }

def validate_selection(model):
    active = model['authoritative_runs']
    superseded = [x['run_dir'] for x in model['superseded_runs']]
    if set(active) & set(superseded):
        raise ValueError('active/superseded run overlap')
    if not active or any('/'+model['authoritative_version']+'/' not in '/'+p for p in active):
        raise ValueError('active run version does not match authoritative version')
    expected = f'data/regional-review/montenegro-evidence-996-erratum/reproducibility-control-{model["authoritative_version"]}.json'
    if model['authoritative_control'] != expected or model['validation_control_path'] != expected:
        raise ValueError('authoritative version/control mismatch')
    if model['superseded_control']['path'] == expected:
        raise ValueError('active control is also named superseded')
    if model['scope_subject_count'] != 23:
        raise ValueError('wrong subject scope')
    return True

def run(output):
    output = Path(output)
    if not output.is_absolute(): output = ROOT / output
    if output.resolve().parent == (ROOT / OWNED / 'runs').resolve() or (ROOT / OWNED / 'runs').resolve() in output.resolve().parents:
        pass
    else: raise ValueError('output must be inside this issue-owned runs directory')
    if output.exists(): raise FileExistsError(f'refusing to overwrite evidence: {output}')
    scope, original, checked, source_rows = load_pinned_inputs()
    model = corrected_selection(original, source_rows)
    controls = []
    validate_selection(model)
    controls.append({'id':'corrected-positive','outcome':'passed','meaning':'accepted v10 runs/control are disjoint from superseded v9 and earlier runs'})
    bad = json.loads(json.dumps(model)); bad['superseded_runs'].append({'run_dir':model['authoritative_runs'][0],'reason':'negative fixture'})
    try: validate_selection(bad)
    except ValueError as exc: controls.append({'id':'active-superseded-overlap','outcome':'rejected','reason':str(exc)})
    else: raise AssertionError('overlapping active/superseded negative control accepted')
    bad = json.loads(json.dumps(model)); bad['authoritative_control']=bad['superseded_control']['path']
    try: validate_selection(bad)
    except ValueError as exc: controls.append({'id':'version-control-mismatch','outcome':'rejected','reason':str(exc)})
    else: raise AssertionError('mismatched version/control negative control accepted')
    result={'version':1,'retrieved_at':'2026-10-06','issue':1207,'baseline_commit':BASELINE,
      'runner_sha256':digest(Path(__file__).read_bytes()),
      'issue_subject_ids_sha256':EXPECTED_IDS_HASH,'input_pin_count':len(checked),
      'input_pins':checked,'selected_lineage':model,'controls':controls,
      'historical_result_values_changed':False,'old_packet_written':False}
    raw=(json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode()
    output.mkdir(parents=True,exist_ok=False)
    (output/'result.json').write_bytes(raw)
    print(json.dumps({'output':str(output),'result_sha256':digest(raw),'pins':len(checked),'controls':controls},indent=2))

def finalize():
    scope, original, checked, source_rows = load_pinned_inputs()
    root=ROOT/OWNED
    paths=[root/'runs/2026-10-06/run-1/result.json',root/'runs/2026-10-06/run-2/result.json']
    raws=[p.read_bytes() for p in paths]
    if raws[0] != raws[1]: raise ValueError('independent results differ byte-for-byte')
    result=json.loads(raws[0]); validate_selection(result['selected_lineage'])
    if result['runner_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('runner bytes changed between reproduction and finalization')
    corr=result['selected_lineage']
    (root/'lineage-correction.json').write_text(json.dumps(corr,indent=2,ensure_ascii=False)+'\n')
    control={'version':1,'kind':'lineage-reproducibility','outcome':'passed','runs':[
      {'path':p.relative_to(root).as_posix(),'sha256':digest(raw)} for p,raw in zip(paths,raws)],
      'byte_identical':True,'pin_count':len(checked),'input_raw_bytes':sum(x['bytes'] for x in checked.values()),
      'runner_sha256':result['runner_sha256'],
      'positive_controls':1,'negative_controls':2,'both_negative_controls_rejected':True,
      'old_packet_modified':False,'scope_subject_count':23}
    (root/'lineage-control.json').write_text(json.dumps(control,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(control,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('run'); p.add_argument('--output-dir',required=True)
    sub.add_parser('finalize'); a=parser.parse_args()
    if a.cmd=='run': run(a.output_dir)
    else: finalize()
