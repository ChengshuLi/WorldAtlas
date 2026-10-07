#!/usr/bin/env python3
"""Run actual separate-process positives and directed no-publication controls."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = ROOT / 'data/regional-review/northern-macedonia-method-995-guard-erratum'
OLD = ROOT / 'data/regional-review/northern-macedonia-method-995-erratum'
RUNNER = OWNED / 'guarded_reproduce.py'
OLD_RESULT_SHA = 'd3d23c61368d3db4fb5acf049cfaff9f3533a1da7c37c5b96d02070d50b3fef3'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def load_runner():
    spec = importlib.util.spec_from_file_location('guarded_reproduce', RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def rejected(action, fn):
    try:
        fn()
    except Exception as exc:
        return {'id': action, 'outcome': 'rejected-before-publication', 'exception': type(exc).__name__, 'reason': str(exc)}
    raise AssertionError(action + ' unexpectedly passed')

def main():
    started = now()
    OWNED.joinpath('controls').mkdir(parents=True, exist_ok=True)
    module = load_runner()
    index, blobs = module._descriptor()

    # Actual end-to-end replays are separate Python processes. The callable checks
    # code and sources, then opens only a no-follow, exclusive destination fd.
    original = (OLD / 'v1/run-one.json').read_bytes()
    if sha(original) != OLD_RESULT_SHA:
        raise AssertionError('retained historical report is not the pinned expected sentinel')
    runs = []
    for name in ('run-one.json', 'run-two.json'):
        output = str(module.OWNED_REL / 'v1' / name)
        target = ROOT / output
        if target.exists():
            if sha(target.read_bytes()) != OLD_RESULT_SHA:
                raise AssertionError('refusing to replace unexpected pre-existing author output: ' + output)
            target.unlink()
        launched = now()
        process = subprocess.run([sys.executable, str(RUNNER), output], cwd=ROOT,
                                  text=True, capture_output=True, check=False)
        exited = now()
        if process.returncode:
            raise RuntimeError(f'positive {name} failed: {process.stderr[-1000:]}')
        receipt = json.loads(process.stdout.strip().splitlines()[-1])
        raw = target.read_bytes()
        report = json.loads(raw)
        if sha(raw) != OLD_RESULT_SHA or raw != original or sha(raw) != receipt['sha256']:
            raise AssertionError('fresh complete report differs from historical retained bytes')
        if report['scope']['native_subject_count'] != 84 or report['scope']['unique_subject_count'] != 84 or len(report['scope']['parent_context_ids']) != 8:
            raise AssertionError('exact 84-subject / eight read-only parent scope failed')
        code = receipt['executed_code']
        if set(code) != {'_authenticated_prior_phase','pinned_original_reproducer','evidence.geometry','ellipsoidal_area'}:
            raise AssertionError('not all actually executed project source modules are authenticated')
        runs.append({'output': output, 'launched_at_utc': launched, 'exited_at_utc': exited,
                     'bytes': len(raw), 'sha256': sha(raw), 'subjects': 84, 'parent_contexts': 8,
                     'executed_code': code, 'stdout': process.stdout.strip()})

    # Inventory each declared subject and its retained source/parent context.
    # The current statistical crosswalk is prior evidence, not rerun here.
    issue_snapshot = json.loads((OWNED/'issue-scope-snapshot.json').read_bytes())
    match = re.search(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->', issue_snapshot['body'])
    if not match: raise AssertionError('issue snapshot has no reviewed work contract')
    contract = json.loads(match.group(1))
    exact_ids = contract['evidence_quality']['subject_ids']
    report = json.loads((ROOT / runs[0]['output']).read_bytes())
    pairs = {row['location_id']: row for row in report['results']['pairs']}
    assessment_path = 'data/regional-review/regional-review-3c4fe25a21fa428d/source/subject-assessments.json'
    assessments = {row['location_id']: row for row in json.loads(blobs[assessment_path])['subjects']
                   if row.get('location_id','').startswith('gb:MKD:ADM2:')}
    hierarchy = {row['id']: row for row in json.loads(blobs['data/hierarchy.json'])}
    crosswalk_path = 'data/regional-review/followup-northern-macedonia-422-roster-20261005/crosswalk-results.json'
    crosswalk = {row['location_id']: row for row in json.loads(blobs[crosswalk_path])['rows']}
    if len(exact_ids) != 84 or set(exact_ids) != set(pairs) or set(exact_ids) != set(assessments) or set(exact_ids) != set(crosswalk):
        raise AssertionError('issue contract, source run and retained prior crosswalk rosters differ')
    parent_ids = sorted({assessments[sid]['parent_id'] for sid in exact_ids})
    parents = []
    for parent_id in parent_ids:
        parent = hierarchy[parent_id]
        review = parent.get('metadata',{}).get('semantic_review',{})
        parents.append({'id':parent_id,'name':parent['name'],'parent_id':parent.get('parent_id'),
            'basis':parent.get('metadata',{}).get('basis'),
            'framework_status':parent.get('metadata',{}).get('framework_status'),
            'semantic_review_action':review.get('action'),
            'remaining_reasons':review.get('remaining_reasons',[])})
    metadata_path = 'data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/MKD-ADM2-geoBoundaries-MKD-ADM2-metaData.json'
    meta = json.loads(blobs[metadata_path])
    rows = []
    for sid in sorted(exact_ids):
        pair, assessment, prior = pairs[sid], assessments[sid], crosswalk[sid]
        parent = hierarchy[assessment['parent_id']]
        rows.append({'subject_id':sid,'source_shape_id':sid.rsplit(':',1)[1],
            'geoBoundaries_source_name':pair['source_name'],'source_boundary_type':meta['boundaryType'],
            'source_boundary_year':meta['boundaryYear'],'source_canonical_label':meta['boundaryCanonical'],
            'read_only_atlas_parent_id':assessment['parent_id'],'read_only_atlas_parent_name':parent['name'],
            'prior_hdx_statistical_region':prior['hdx_source_statistical_region'],
            'prior_ntes_code':prior['current_ntes_code'],'prior_ntes_name':prior['current_ntes_name'],
            'prior_crosswalk_outcome':prior['outcome'],
            'prior_crosswalk_retrieved_at_utc':json.loads(blobs[crosswalk_path])['retrieved_at_utc'],
            'reproduced_area_fraction':pair['symmetric_difference_area_fraction'],
            'area_fraction_screen_pass':pair['below_1e-8_area_fraction_screen']})
    roster_path = 'data/regional-review/followup-northern-macedonia-422-roster-20261005/official-roster.json'
    roster = json.loads(blobs[roster_path])
    atlas_path = 'data/regional-review/northern-macedonia-method-995-erratum/v1/atlas-geometry-check.json'
    atlas_raw = module.git('show', f'{module.OLD_PACKET_MERGE}:{atlas_path}')
    atlas = json.loads(atlas_raw)
    if atlas['subjects'] != 84 or atlas['exact_equal_count'] != 0 or atlas['atlas_fewer_vertex_count'] != 84:
        raise AssertionError('prior separate Atlas representation finding changed')
    scope_audit = {'version':1,'issue':1237,'issue_snapshot_sha256':sha((OWNED/'issue-scope-snapshot.json').read_bytes()),
        'scope_basis':'exact subject_ids in the current reviewed issue contract; preserved prior native roster and named source-to-source comparison',
        'subject_count':len(rows),'unique_subject_count':len({r['subject_id'] for r in rows}),
        'parent_context_count':len(parents),'parent_contexts':parents,
        'source_layer':{'path':metadata_path,'boundary_type':meta['boundaryType'],'boundary_year':meta['boundaryYear'],
            'boundary_source':meta['boundarySource'],'boundary_canonical':meta['boundaryCanonical'],
            'metadata_claimed_license':meta['boundaryLicense'],'metadata_license_url':meta.get('licenseSource'),
            'source_feature_count':int(meta['admUnitCount']),'source_metadata_sha256':sha(blobs[metadata_path]),
            'license_or_legal_effective_date_approved':False,
            'metadata_dates':'source-data update/build dates are standardization dates, not proved legal effective dates'},
        'official_neighboring_granularity_context':{'source_title':roster['source']['title'],
            'source_url':roster['source']['url'],'retrieved_at_utc':roster['source']['retrieved_at_utc'],
            'archive_sha256':roster['source']['archive_sha256'],'level_counts':roster['level_counts'],
            'reuse_status':roster['source']['reuse_status'],
            'territorial_role_limit':'NTES level 3 regions are statistical; municipalities are level 4 and settlements level 5. The retained layer counts and reported NTES crosswalk do not prove legal membership or source completeness.'},
        'prior_crosswalk_context':{'path':crosswalk_path,'sha256':sha(blobs[crosswalk_path]),
            'retrieved_at_utc':json.loads(blobs[crosswalk_path])['retrieved_at_utc'],
            'summary':json.loads(blobs[crosswalk_path])['summary'],
            'status':'retained prior evidence only; not recomputed by this guard correction'},
        'comparison_run':{'path':runs[0]['output'],'sha256':runs[0]['sha256'],
            'metric':'symmetric-difference ellipsoidal area fraction, not distance',
            'screen':'dimensionless 1e-8 area fraction; all retained pairs are nonzero and below screen',
            'results':{'pair_count':report['results']['pair_count'],
                'nonzero_residual_count':report['results']['nonzero_residual_count'],
                'within_area_fraction_screen_count':report['results']['within_area_fraction_screen_count'],
                'maximum_symmetric_difference_area_fraction':report['results']['maximum_symmetric_difference_area_fraction']}},
        'separate_prior_atlas_representation_finding':{'path':atlas_path,'sha256':sha(atlas_raw),
            'baseline_commit':atlas['baseline_commit'],'source_sha256':atlas['source_sha256'],'atlas_sha256':atlas['atlas_sha256'],
            'subjects':atlas['subjects'],'exact_equal_count':atlas['exact_equal_count'],
            'atlas_fewer_vertex_count':atlas['atlas_fewer_vertex_count'],'comparison':atlas['comparison'],
            'status':'preserved prior finding; not rerun by this read-boundary guard issue'},
        'subjects':rows,
        'limits':['The 84 source rows and eight parents are exact issue scope and read-only context, not a completeness certificate.',
            'The retained 84-versus-80 relationship and old-to-current roster correspondence are inherited from prior evidence; this issue does not certify territorial matching.',
            'The eight Atlas parent units have open semantic reviews. No hierarchy or boundary correction is proposed by this issue.',
            'The metadata CC BY 4.0 claim is not accepted as verified because its recorded source URL is malformed; upstream reuse terms remain unresolved.',
            'Area-fraction similarity is not proof of legal validity, distance tolerance, current AKN correctness or whole-region coverage.']}
    (OWNED/'scope-audit.json').write_text(json.dumps(scope_audit,ensure_ascii=False,indent=2)+'\n')

    target_absent = OLD / 'v1/guard-control-must-not-exist.json'
    if target_absent.exists(): raise AssertionError('outside-prefix traversal sentinel already exists')
    sentinels = {name: sha((OLD / 'v1' / name).read_bytes()) for name in ('run-one.json','run-two.json')}
    traversal = str(module.OWNED_REL / '..' / 'northern-macedonia-method-995-erratum' / 'v1' / 'guard-control-must-not-exist.json')
    path_result = rejected('dot-dot traversal to preserved sibling packet', lambda: module.run(traversal))
    if target_absent.exists(): raise AssertionError('traversal target was created outside the new owned prefix')
    absolute_result = rejected('absolute destination', lambda: module.run(str(OLD / 'v1/guard-control-must-not-exist.json')))

    scratch = OWNED / 'controls/symlink-parent'
    if scratch.exists() or scratch.is_symlink(): raise AssertionError('symlink-control path unexpectedly exists')
    os.symlink(str(OLD), scratch)
    try:
        symlink_output = str(module.OWNED_REL / 'controls/symlink-parent' / 'guard-control-must-not-exist.json')
        symlink_result = rejected('symlink parent escaping to preserved sibling packet', lambda: module.run(symlink_output))
    finally:
        scratch.unlink()
    if target_absent.exists(): raise AssertionError('symlink target was created outside the new owned prefix')
    after_sentinels = {name: sha((OLD / 'v1' / name).read_bytes()) for name in ('run-one.json','run-two.json')}
    if sentinels != after_sentinels: raise AssertionError('historical outside sentinels changed')

    rejected_outputs = [
        OWNED/'controls/rejected-geometry-drift.json', OWNED/'controls/rejected-ellipsoidal-drift.json',
        OWNED/'controls/rejected-original-reproducer-drift.json', OWNED/'controls/rejected-descriptor-drift.json',
        OWNED/'controls/rejected-input-drift.json', OWNED/'controls/rejected-runner-drift.json',
        OWNED/'controls/rejected-runner-pin-drift.json'
    ]
    existing_sentinel = OWNED/'controls/existing-output-sentinel.json'
    sentinel_bytes = b'{"sentinel":"existing output must not be replaced"}\n'
    if existing_sentinel.exists():
        if existing_sentinel.read_bytes() != sentinel_bytes:
            raise AssertionError('refusing to replace unexpected existing-output control sentinel')
    else:
        existing_sentinel.write_bytes(sentinel_bytes)
    existing_result = rejected('existing output remains protected', lambda: module.run(
        str(existing_sentinel.relative_to(ROOT))))
    if existing_sentinel.read_bytes() != sentinel_bytes:
        raise AssertionError('existing destination sentinel changed')
    for path in rejected_outputs:
        if path.exists(): raise AssertionError('a rejected drift control published output: ' + str(path))

    controls_dir = OWNED / 'controls'
    geometry_raw = blobs['scripts/evidence/geometry.py']
    area_raw = blobs['scripts/ellipsoidal_area.py']
    geometry_fixture = geometry_raw.replace(b'return area(canonical_land(geometry))', b'return area(canonical_land(geometry)) + 1.0', 1)
    area_fixture = area_raw.replace(b'A = 6378137.0', b'A = 6378138.0', 1)
    if geometry_fixture == geometry_raw or area_fixture == area_raw:
        raise AssertionError('full-code helper drift fixture could not be constructed')
    (controls_dir / 'geometry-helper-drift.py').write_bytes(geometry_fixture)
    (controls_dir / 'ellipsoidal-area-helper-drift.py').write_bytes(area_fixture)
    geometry_control = rejected('complete geometry helper code supplied at actual import boundary', lambda: module.run(
        str(module.OWNED_REL / 'controls/rejected-geometry-drift.json'),
        code_overrides={'scripts/evidence/geometry.py': geometry_fixture}))
    area_control = rejected('complete ellipsoidal helper code supplied at actual import boundary', lambda: module.run(
        str(module.OWNED_REL / 'controls/rejected-ellipsoidal-drift.json'),
        code_overrides={'scripts/ellipsoidal_area.py': area_fixture}))
    original_reproducer_path = 'data/regional-review/followup-northern-macedonia-422-roster-20261005/reproduce.py'
    original_fixture = blobs[original_reproducer_path].replace(b'expected_ids = sorted(assessment_by_id)', b'expected_ids = sorted(assessment_by_id)[:83]', 1)
    if original_fixture == blobs[original_reproducer_path]: raise AssertionError('reproducer drift fixture failed')
    reproducer_control = rejected('complete original decoder/reproducer drift at actual import boundary', lambda: module.run(
        str(module.OWNED_REL / 'controls/rejected-original-reproducer-drift.json'),
        code_overrides={original_reproducer_path: original_fixture}))

    descriptor_raw = (OLD / 'baseline-inputs.json').read_bytes()
    changed_descriptor = descriptor_raw + b' '
    descriptor_control = rejected('wrong complete input descriptor bytes', lambda: module.run(
        str(module.OWNED_REL / 'controls/rejected-descriptor-drift.json'), descriptor_override=changed_descriptor))
    input_path = 'data/geography/part-15.json'
    changed_input = bytearray(blobs[input_path]); changed_input[-1] ^= 1
    input_control = rejected('wrong immutable whole input bytes', lambda: module.run(
        str(module.OWNED_REL / 'controls/rejected-input-drift.json'), input_overrides={input_path: bytes(changed_input)}))
    runner_path = 'data/regional-review/northern-macedonia-method-995-erratum/reproduce-retained-phase.py'
    prior_runner = module.git('show', f'{module.OLD_PACKET_MERGE}:{runner_path}')
    changed_runner = prior_runner + b'\n# synthetic code drift\n'
    runner_control = rejected('complete prior runner drift', lambda: module.run(
        str(module.OWNED_REL / 'controls/rejected-runner-drift.json'), runner_override=changed_runner))
    prior_pin = module.git('show', f'{module.OLD_PACKET_MERGE}:{module.OLD_REL}/runner-pin.json')
    bad_pin = json.dumps({'sha256': '0' * 64}).encode()
    pin_control = rejected('wrong prior runner pin bytes', lambda: module.run(
        str(module.OWNED_REL / 'controls/rejected-runner-pin-drift.json'), runner_pin_override=bad_pin))
    self_pin_control = rejected('wrong current runner pin bytes', lambda: module._verify_self_pin(RUNNER.read_bytes(), b'{\"sha256\":\"' + b'0' * 64 + b'\"}'))

    negative = {'version':1,'method_id':'retained-source-area-comparison','kind':'negative-control','outcome':'passed','recorded_at_utc':now(),'controls':[
        path_result,absolute_result,symlink_result,geometry_control,area_control,reproducer_control,
        descriptor_control,input_control,runner_control,pin_control,self_pin_control],
        'no_result_outputs_created':True,'rejected_output_paths_checked':[str(p.relative_to(ROOT)) for p in rejected_outputs],
        'existing_output_control':{'path':str(existing_sentinel.relative_to(ROOT)),'sha256':sha(sentinel_bytes),'bytes_unchanged':True,'result':existing_result},
        'outside_prefix_absent_target':str(target_absent.relative_to(ROOT)),
        'outside_sentinel_files':sentinels,'outside_sentinels_unchanged':sentinels==after_sentinels,
        'full_code_fixtures':{
            'scripts/evidence/geometry.py':{'path':str((controls_dir/'geometry-helper-drift.py').relative_to(ROOT)),'bytes':len(geometry_fixture),'sha256':sha(geometry_fixture),'synthetic_change':'entire original helper with canonical area return increased by 1 m²'},
            'scripts/ellipsoidal_area.py':{'path':str((controls_dir/'ellipsoidal-area-helper-drift.py').relative_to(ROOT)),'bytes':len(area_fixture),'sha256':sha(area_fixture),'synthetic_change':'entire original helper with semimajor axis increased by 1 m'},
            original_reproducer_path:{'bytes':len(original_fixture),'sha256':sha(original_fixture),'synthetic_change':'complete source with native scope truncated to 83 IDs'}}}
    (controls_dir / 'negative-control.json').write_text(json.dumps(negative,ensure_ascii=False,indent=2)+'\n')
    positive = {'version':1,'method_id':'retained-source-area-comparison','kind':'positive-control','outcome':'passed','recorded_at_utc':now(),'runs':runs,
                'expected_historical_report_sha256':OLD_RESULT_SHA,'byte_identical_to_both_prior_retained_runs':True,
                'exact_scope':{'native_subjects':84,'unique_subjects':84,'read_only_parent_contexts':8},
                'source_pair_and_boundary_validity_approval':False}
    (controls_dir / 'positive-control.json').write_text(json.dumps(positive,ensure_ascii=False,indent=2)+'\n')
    reproducibility = {'version':1,'method_id':'retained-source-area-comparison','kind':'reproducibility','outcome':'passed','run_count':2,'recorded_at_utc':now(),
        'actual_independent_processes':True,'outputs_byte_identical':runs[0]['sha256']==runs[1]['sha256'],
        'run_one_sha256':runs[0]['sha256'],'run_two_sha256':runs[1]['sha256'],
        'same_complete_pinned_inputs':True,'same_complete_executed_project_code':runs[0]['executed_code']==runs[1]['executed_code'],
        'comparison_to_historical':OLD_RESULT_SHA,'run_observation_path':str((OWNED/'controls/run-observations.json').relative_to(ROOT))}
    (controls_dir / 'reproducibility-control.json').write_text(json.dumps(reproducibility,ensure_ascii=False,indent=2)+'\n')
    observation = {'version':1,'started_at_utc':started,'finished_at_utc':now(),
        'python':sys.version,'python_executable':sys.executable,
        'shapely':__import__('shapely').__version__,'pyproj':__import__('pyproj').__version__,
        'runs':runs,'all_runs_are_source_only':True,'no_external_network_requests':True}
    (controls_dir / 'run-observations.json').write_text(json.dumps(observation,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'runs':len(runs),'sha256':OLD_RESULT_SHA,'negative_controls':len(negative['controls']),'outside_sentinels_unchanged':True},sort_keys=True))

if __name__ == '__main__': main()
