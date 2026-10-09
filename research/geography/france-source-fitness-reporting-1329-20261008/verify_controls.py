#!/usr/bin/env python3
"""Exercise the original and corrected France report entry points in owned scratch."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

OWNED = 'research/geography/france-source-fitness-reporting-1329-20261008/'
ORIGINAL = 'research/geography/france-nine-gap-family-source-fitness-20261007/'
PYTHON = sys.executable


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def write_exclusive(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def invoke(command, repo, *, control=False):
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if control:
        env['WORLDATLAS_CONTROL_MODE'] = '1'
    result = subprocess.run(command, cwd=repo, env=env, text=True, capture_output=True)
    return {'returncode': result.returncode, 'stdout': result.stdout[:2000], 'stderr': result.stderr[:2000],
            'stdout_sha256': sha(result.stdout.encode()), 'stderr_sha256': sha(result.stderr.encode())}


def expect_reject(record, contains=None):
    if record['returncode'] == 0:
        raise AssertionError('Expected the actual CLI to reject this control')
    if contains and contains.lower() not in record['stderr'].lower():
        raise AssertionError('CLI rejected for an unexpected reason: ' + record['stderr'])


def old_mirror(root, directory, report_bytes, run1_bytes, run2_bytes):
    (directory / 'verification').mkdir(parents=True)
    write_exclusive(directory / 'summarize.py', report_bytes)
    write_exclusive(directory / 'verification/run-1.json', run1_bytes)
    write_exclusive(directory / 'verification/run-2.json', run2_bytes)


def run_suite(repo, vintage):
    repo = Path(repo).resolve()
    owned = repo / OWNED
    scratch_parent = owned / '.scratch'
    if scratch_parent.is_symlink():
        raise RuntimeError('Owned scratch root is a symlink')
    scratch_parent.mkdir(exist_ok=True)
    module_spec = importlib.util.spec_from_file_location('france_report_cli', owned / 'report.py')
    report = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(report)
    ctx = report.context(repo)
    verifier_raw = Path(__file__).read_bytes()
    ctx['baseline'].admit('candidate:' + OWNED + 'verify_controls.py', len(verifier_raw))
    report_path = owned / 'report.py'
    report_raw = report_path.read_bytes()
    report_sha = sha(report_raw)
    request = ctx['request']
    baseline_commit = request['baseline_commit']
    run1_path = ORIGINAL + 'verification/run-1.json'
    run2_path = ORIGINAL + 'verification/run-2.json'
    old_script_path = ORIGINAL + 'summarize.py'
    run1 = git(repo, 'cat-file', 'blob', git(repo, 'ls-tree', '-z', baseline_commit, '--', run1_path).rstrip(b'\0').split(b'\t')[0].split()[2].decode())
    run2 = git(repo, 'cat-file', 'blob', git(repo, 'ls-tree', '-z', baseline_commit, '--', run2_path).rstrip(b'\0').split(b'\t')[0].split()[2].decode())
    old_script = git(repo, 'cat-file', 'blob', git(repo, 'ls-tree', '-z', baseline_commit, '--', old_script_path).rstrip(b'\0').split(b'\t')[0].split()[2].decode())
    if run1 != run2:
        raise AssertionError('Pinned original complete run files are not equal')
    for path, raw in ((run1_path, run1), (run2_path, run2), (old_script_path, old_script)):
        descriptor = ctx['by_path'].get(path)
        if not descriptor or descriptor['bytes'] != len(raw) or descriptor['sha256'] != sha(raw):
            raise AssertionError('Baseline report input hash differs: ' + path)

    # Admit the final control-receipt destination before creating scratch or
    # executing any CLI. A failed test run is not a success receipt.
    control_output = ctx['shared'].NewVintage(ctx['baseline'], OWNED, vintage, ['control-results.json'])
    results = {'version': 1, 'issue': 1489, 'baseline_commit': baseline_commit,
        'report_sha256': report_sha, 'verifier_sha256': sha(verifier_raw),
        'original_runs_sha256': sha(run1), 'original_runs_bytes_each': len(run1),
        'checks': [], 'retained_partial_attempts': []}
    report_cli = [PYTHON, '-I', '-B', str(report_path), '--repo', str(repo)]
    with tempfile.TemporaryDirectory(prefix='control-', dir=scratch_parent) as temp_value:
        temp = Path(temp_value)

        # Actual historical CLI, intact complete reports: reproduce the frozen
        # products in a private copy and compare every documented result byte.
        positive = temp / 'old-positive'
        old_mirror(repo, positive, old_script, run1, run2)
        positive_run = invoke([PYTHON, '-I', '-B', str(positive / 'summarize.py')], repo)
        if positive_run['returncode'] != 0:
            raise AssertionError('Original intact summarize.py CLI did not complete')
        expected_old = [
            'candidate-findings.csv', 'family-findings.csv', 'contact-findings.csv', 'summary-metrics.json',
            'validation-positive.json', 'validation-negative.json', 'validation-reproducibility.json']
        old_outputs = {}
        for name in expected_old:
            expected = git(repo, 'cat-file', 'blob', git(repo, 'ls-tree', '-z', baseline_commit, '--', ORIGINAL + name).rstrip(b'\0').split(b'\t')[0].split()[2].decode())
            actual = (positive / name).read_bytes()
            old_outputs[name] = {'sha256': sha(actual), 'bytes': len(actual), 'matches_frozen': actual == expected}
            if actual != expected:
                raise AssertionError('Intact old CLI output differs from its frozen output: ' + name)
        results['checks'].append({'id': 'original-full-positive', 'entrypoint': 'original summarize.py',
            'command_result': positive_run, 'outputs': old_outputs, 'outcome': 'passed'})

        # The old CLI says a false negative control passed, despite its evidence
        # object explicitly recording that the required rejection was false.
        false_control = temp / 'old-false-control'
        false1 = json.loads(run1); false2 = json.loads(run2)
        false1['controls']['scope_roster']['negative_omission_rejected'] = False
        false2['controls']['scope_roster']['negative_omission_rejected'] = False
        false1_raw = json.dumps(false1, ensure_ascii=False, separators=(',', ':')).encode()
        false2_raw = json.dumps(false2, ensure_ascii=False, separators=(',', ':')).encode()
        old_mirror(repo, false_control, old_script, false1_raw, false2_raw)
        false_run = invoke([PYTHON, '-I', '-B', str(false_control / 'summarize.py')], repo)
        receipt = json.loads((false_control / 'validation-negative.json').read_bytes())
        if false_run['returncode'] != 0 or receipt['outcome'] != 'passed' or receipt['evidence']['omission_rejected'] is not False:
            raise AssertionError('Original false-control defect did not reproduce')
        results['checks'].append({'id': 'original-false-control', 'entrypoint': 'original summarize.py',
            'command_result': false_run, 'mutated_run_sha256': sha(false1_raw),
            'receipt_outcome': receipt['outcome'], 'receipt_evidence_omission_rejected': receipt['evidence']['omission_rejected'],
            'outcome': 'defect-reproduced'})

        # The old CLI retains source geometries but substitutes static summary
        # counts; an internally valid run pair with empty relation lists still
        # reports the old 42/8/34/6 values.
        static_case = temp / 'old-static-counts'
        static1 = json.loads(run1); static2 = json.loads(run2)
        for candidate in static1['candidates']:
            candidate['official_2026_whole_layer_relations']['exact_whole_feature_intersections'] = []
        for candidate in static2['candidates']:
            candidate['official_2026_whole_layer_relations']['exact_whole_feature_intersections'] = []
        static1_raw = json.dumps(static1, ensure_ascii=False, separators=(',', ':')).encode()
        static2_raw = json.dumps(static2, ensure_ascii=False, separators=(',', ':')).encode()
        old_mirror(repo, static_case, old_script, static1_raw, static2_raw)
        static_run = invoke([PYTHON, '-I', '-B', str(static_case / 'summarize.py')], repo)
        static_metrics = json.loads((static_case / 'summary-metrics.json').read_bytes())['values']
        derived_intersects = sum(bool(x['official_2026_whole_layer_relations']['exact_whole_feature_intersections']) for x in static1['candidates'])
        if static_run['returncode'] != 0 or derived_intersects != 0 or static_metrics['official_2026_intersect'] != 42 or static_metrics['official_2026_no_intersection'] != 6:
            raise AssertionError('Original hard-coded-count defect did not reproduce')
        results['checks'].append({'id': 'original-static-counts', 'entrypoint': 'original summarize.py',
            'command_result': static_run, 'mutated_run_sha256': sha(static1_raw),
            'derived_intersects_from_fixture': derived_intersects,
            'reported_intersects': static_metrics['official_2026_intersect'],
            'reported_no_intersection': static_metrics['official_2026_no_intersection'],
            'outcome': 'defect-reproduced'})

        # The original overwrite writer follows a dangling-summary target. The
        # target and script copy are inside this task's private owned scratch.
        symlink_case = temp / 'old-symlink-writer'
        symlink_case.mkdir()
        source_dir = symlink_case / 'verification'; source_dir.mkdir()
        write_exclusive(symlink_case / 'summarize.py', old_script)
        write_exclusive(source_dir / 'run-1.json', run1); write_exclusive(source_dir / 'run-2.json', run2)
        sentinel = temp / 'sentinel-target.json'
        sentinel_original = b'outside-packet-scratch sentinel\n'
        write_exclusive(sentinel, sentinel_original)
        link = symlink_case / 'summary-metrics.json'
        link.symlink_to(sentinel)
        link_run = invoke([PYTHON, '-I', '-B', str(symlink_case / 'summarize.py')], repo)
        sentinel_after = sentinel.read_bytes()
        if link_run['returncode'] != 0 or sentinel_after == sentinel_original:
            raise AssertionError('Original symlink-following output defect did not reproduce')
        results['checks'].append({'id': 'original-symlink-output', 'entrypoint': 'original summarize.py',
            'command_result': link_run, 'target_sha256_before': sha(sentinel_original),
            'target_sha256_after': sha(sentinel_after), 'target_changed': True, 'outcome': 'defect-reproduced'})

        # New validator CLI: positive fixture and semantic rejections all run
        # through its documented no-output entry point.
        fixture_dir = temp / 'fixtures'; fixture_dir.mkdir()
        def put_pair(name, first, second):
            d = fixture_dir / name; d.mkdir()
            p1=d/'run-one.json'; p2=d/'run-two.json'
            write_exclusive(p1, first); write_exclusive(p2, second)
            return str(p1.relative_to(repo)), str(p2.relative_to(repo))

        def run_fixture(name, first, second, expected, fragment=None):
            p1,p2=put_pair(name,first,second)
            record=invoke(report_cli+['check-fixture','--run-one',p1,'--run-two',p2],repo)
            if expected=='accepted' and record['returncode']!=0:
                raise AssertionError(f'{name} valid fixture rejected: {record["stderr"]}')
            if expected=='rejected': expect_reject(record,fragment)
            results['checks'].append({'id':'corrected-'+name,'entrypoint':'report.py check-fixture',
                'command_result':record,'expected':expected,'outcome':'passed'})

        run_fixture('intact-run-control', run1, run2, 'accepted')
        false1=json.loads(run1); false1['controls']['scope_roster']['negative_omission_rejected']=False
        false_raw=json.dumps(false1,ensure_ascii=False,separators=(',',':')).encode()
        run_fixture('false-control-rejected',false_raw,false_raw,'rejected','required omission')
        count1=json.loads(run1); count1['candidate_count']=47
        count_raw=json.dumps(count1,ensure_ascii=False,separators=(',',':')).encode()
        run_fixture('count-mismatch-rejected',count_raw,count_raw,'rejected','metric counts')
        omit1=json.loads(run1); omit1['candidates'].pop()
        omit_raw=json.dumps(omit1,ensure_ascii=False,separators=(',',':')).encode()
        run_fixture('omitted-candidate-rejected',omit_raw,omit_raw,'rejected','omitted or foreign')
        duplicate1=json.loads(run1); duplicate1['candidates'].append(copy.deepcopy(duplicate1['candidates'][0]))
        duplicate_raw=json.dumps(duplicate1,ensure_ascii=False,separators=(',',':')).encode()
        run_fixture('duplicate-candidate-rejected',duplicate_raw,duplicate_raw,'rejected','duplicate identities')
        foreign1=json.loads(run1); foreign1['candidates'][0]['component_id']='physical-component:'+('f'*64)
        foreign_raw=json.dumps(foreign1,ensure_ascii=False,separators=(',',':')).encode()
        run_fixture('foreign-candidate-rejected',foreign_raw,foreign_raw,'rejected','omitted or foreign')
        changed1=json.loads(run1)
        first_hit=next(x for x in changed1['candidates'] if x['official_2026_whole_layer_relations']['exact_whole_feature_intersections'])
        first_hit['official_2026_whole_layer_relations']['exact_whole_feature_intersections'].pop()
        changed_raw=json.dumps(changed1,ensure_ascii=False,separators=(',',':')).encode()
        run_fixture('relation-count-drift-rejected',changed_raw,changed_raw,'rejected','differs from the frozen summary')
        run_fixture('run-mismatch-rejected',run1,run2+b'\n','rejected','differ byte-for-byte')

        # Issue contract drift and baseline pin substitution must fail closed
        # before a fresh report run can create any output.
        issue_copy=fixture_dir/'issue-drift.json'; write_exclusive(issue_copy, (owned/'issue-snapshot.json').read_bytes()+b'\n')
        req_issue=json.loads((owned/'request.json').read_bytes()); req_issue['issue_snapshot']['path']=str(issue_copy.relative_to(repo))
        req_issue_path=fixture_dir/'issue-drift-request.json'; write_exclusive(req_issue_path,json.dumps(req_issue).encode())
        issue_vintage='control-issue-drift'
        issue_call=invoke([PYTHON,'-I','-B',str(report_path),'--repo',str(repo),'--request',str(req_issue_path.relative_to(repo)),'run','--vintage',issue_vintage],repo)
        expect_reject(issue_call,'issue snapshot changed')
        if (owned/'vintages'/issue_vintage).exists(): raise AssertionError('Issue-drift control wrote output')
        results['checks'].append({'id':'issue-contract-drift-rejected','entrypoint':'report.py run',
            'command_result':issue_call,'output_absent':True,'outcome':'passed'})

        req_input=json.loads((owned/'request.json').read_bytes())
        descriptor=next(x for x in req_input['baseline_files'] if x['path']==run1_path)
        descriptor['sha256']='0'*64
        req_input_path=fixture_dir/'input-drift-request.json'; write_exclusive(req_input_path,json.dumps(req_input).encode())
        input_vintage='control-input-drift'
        input_call=invoke([PYTHON,'-I','-B',str(report_path),'--repo',str(repo),'--request',str(req_input_path.relative_to(repo)),'run','--vintage',input_vintage],repo)
        expect_reject(input_call,'issue pins')
        if (owned/'vintages'/input_vintage).exists(): raise AssertionError('Input-drift control wrote output')
        results['checks'].append({'id':'baseline-input-pin-drift-rejected','entrypoint':'report.py run',
            'command_result':input_call,'output_absent':True,'outcome':'passed'})

        mutated=fixture_dir/'mutated-report.py'; write_exclusive(mutated,report_raw+b'\n# controlled code drift\n')
        code_vintage='control-code-drift'
        code_call=invoke([PYTHON,'-I','-B',str(mutated),'--repo',str(repo),'run','--vintage',code_vintage,
            '--expected-code-sha256',report_sha],repo)
        expect_reject(code_call,'producer code drifted')
        if (owned/'vintages'/code_vintage).exists(): raise AssertionError('Code-drift control wrote output')
        results['checks'].append({'id':'producer-code-drift-rejected','entrypoint':'report.py run',
            'command_result':code_call,'expected_sha256':report_sha,'mutated_sha256':sha(mutated.read_bytes()),
            'output_absent':True,'outcome':'passed'})

        # Complete-set collision and both live and dangling symlink rejection.
        collision='control-ordinary-collision'
        collision_root=owned/'vintages'/collision
        collision_root.mkdir(parents=True)
        sentinel=collision_root/'sentinel.txt'; write_exclusive(sentinel,b'preserve me\n')
        sentinel_before=sha(sentinel.read_bytes())
        collision_call=invoke(report_cli+['run','--vintage',collision],repo)
        expect_reject(collision_call,'already exists')
        if sha(sentinel.read_bytes())!=sentinel_before: raise AssertionError('Collision sentinel changed')
        shutil.rmtree(collision_root)
        results['checks'].append({'id':'ordinary-destination-collision-rejected','entrypoint':'report.py run',
            'command_result':collision_call,'sentinel_sha256':sentinel_before,'sentinel_preserved':True,'outcome':'passed'})

        vintages=owned/'vintages'; vintages.mkdir(exist_ok=True)
        target_dir=temp/'live-link-target'; target_dir.mkdir()
        target_file=target_dir/'sentinel.txt'; write_exclusive(target_file,b'live target intact\n')
        live_target_hash=sha(target_file.read_bytes())
        live_link=vintages/'control-live-symlink'
        if live_link.exists() or live_link.is_symlink(): raise AssertionError('Live symlink target name already exists')
        live_link.symlink_to(target_dir, target_is_directory=True)
        live_call=invoke(report_cli+['run','--vintage','control-live-symlink'],repo)
        expect_reject(live_call,'symlink')
        if sha(target_file.read_bytes())!=live_target_hash: raise AssertionError('Live symlink target changed')
        live_link.unlink()
        results['checks'].append({'id':'live-symlink-ancestor-rejected','entrypoint':'report.py run',
            'command_result':live_call,'target_sha256':live_target_hash,'target_preserved':True,'outcome':'passed'})

        missing_target=temp/'absent-broken-link-target.json'
        broken_link=vintages/'control-broken-symlink'
        if broken_link.exists() or broken_link.is_symlink() or missing_target.exists(): raise AssertionError('Broken symlink control path is not fresh')
        broken_link.symlink_to(missing_target)
        broken_call=invoke(report_cli+['run','--vintage','control-broken-symlink'],repo)
        expect_reject(broken_call,'symlink')
        if missing_target.exists(): raise AssertionError('Broken symlink target was created')
        broken_link.unlink()
        results['checks'].append({'id':'dangling-symlink-ancestor-rejected','entrypoint':'report.py run',
            'command_result':broken_call,'target_not_created':True,'outcome':'passed'})

        # Verify deterministic positive output bytes from earlier complete runs;
        # attempting the exact same fresh name is the actual rerun rejection.
        first=owned/'vintages/corrected-run-01'
        records={name:sha((first/name).read_bytes()) for name in ['erratum.json','erratum.md','candidate-reconciliation.csv','execution.json','publication.json']}
        rerun_call=invoke(report_cli+['run','--vintage','corrected-run-01'],repo)
        expect_reject(rerun_call,'already exists')
        after={name:sha((first/name).read_bytes()) for name in records}
        if records!=after: raise AssertionError('Rerun collision modified a prior complete output')
        results['checks'].append({'id':'rerun-refused-preserves-whole-output','entrypoint':'report.py run',
            'command_result':rerun_call,'output_hashes':records,'outputs_preserved':True,'outcome':'passed'})

        # The helper's final-receipt link is failed after every planned output
        # byte and the temporary receipt are written. Keep this partial vintage
        # as a failed attempt and prove it has no accepted publication.json.
        failed_name='failed-publication-03'
        failed_call=invoke(report_cli+['run','--vintage',failed_name,'--test-fail-publication-receipt'],repo,control=True)
        expect_reject(failed_call,'controlled failure')
        partial=owned/'vintages'/failed_name
        if not partial.is_dir() or (partial/'publication.json').exists():
            raise AssertionError('Injected partial publication lacks the expected failed/no-receipt state')
        partial_hashes={str(path.relative_to(repo)):sha(path.read_bytes()) for path in sorted(partial.iterdir()) if path.is_file()}
        if '.publication-incomplete' not in {path.name for path in partial.iterdir()}:
            raise AssertionError('Failed final-receipt attempt evidence was not retained')
        results['retained_partial_attempts'].append({'id':failed_name,'command_result':failed_call,
            'publication_receipt_absent':True,'file_hashes':partial_hashes,'accepted':False})
        results['checks'].append({'id':'partial-publication-failure-not-accepted','entrypoint':'report.py run',
            'command_result':failed_call,'publication_receipt_absent':True,'outcome':'passed'})

    results['summary']={'check_count':len(results['checks']),
        'original_defects_reproduced':sum(x.get('outcome')=='defect-reproduced' for x in results['checks']),
        'corrected_controls_passed':sum(x.get('outcome')=='passed' for x in results['checks']),
        'all_publication_failure_artifacts_retained':True}
    control_output.publish({'control-results.json':results})
    return results


def main():
    if len(sys.argv)!=3 or sys.argv[1]!='--repo':
        raise SystemExit('Use verify_controls.py --repo CHECKOUT --vintage FRESH_NAME')
    results=run_suite(sys.argv[2], 'controls-run-03')
    print(json.dumps(results['summary'],sort_keys=True))


if __name__=='__main__':
    main()
