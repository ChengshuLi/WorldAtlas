#!/usr/bin/env python3
"""Positive, negative, exact-reproduction, and no-overwrite controls for #1185."""
import csv, hashlib, importlib.util, json, shutil, uuid, io, os
from pathlib import Path
SCRIPT = Path(__file__).with_name('reproduce_immutable.py').resolve()
spec = importlib.util.spec_from_file_location('reproduce_immutable', SCRIPT)
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
REPO = SCRIPT.parents[4]
OWNED_ROOT = REPO / runner.OWNED
VINTAGES = OWNED_ROOT / 'vintages'
HIST_PATH = runner.OLD_PACKET + 'source/gurs-obcine-h-53-codes-2017.json'
ROSTER_PATH = 'data/regional-review/regional-review-d282e62cf0209796/slovenia-name-correction-candidates.csv'
def digest(raw): return hashlib.sha256(raw).hexdigest()
def bundle(products):
    return digest(b''.join(name.encode()+b'\0'+digest(raw).encode()+b'\n' for name,raw in sorted(products.items())))
def require(ok,msg):
    if not ok: raise AssertionError(msg)
def main():
    VINTAGES.mkdir(parents=True,exist_ok=True)
    code_sha=runner.verify_code_pin(SCRIPT)
    run_names=['control-run-one-'+uuid.uuid4().hex,'control-run-two-'+uuid.uuid4().hex]
    collision_names=['control-existing-'+uuid.uuid4().hex,'control-partial-'+uuid.uuid4().hex]
    cleanup=[]; control_paths=[]; control_root=(OWNED_ROOT/'controls'/'code-pin-v2') if os.environ.get('WORLDATLAS_RETAIN_CONTROLS') else OWNED_ROOT/('test-controls-'+uuid.uuid4().hex)
    try:
        first_path=runner.run(REPO,run_names[0]); cleanup.append(first_path)
        second_path=runner.run(REPO,run_names[1]); cleanup.append(second_path)
        first={p.name:p.read_bytes() for p in first_path.iterdir()}
        second={p.name:p.read_bytes() for p in second_path.iterdir()}
        originals=runner.load_pinned(REPO)[1]
        require(first==second,'Two complete runs differ')
        require(first['2017-name-assessment.csv']==originals[runner.OLD_ASSESSMENT],'Historical CSV bytes changed')
        require(first['reproduction-summary.json']==originals[runner.OLD_SUMMARY],'Historical summary bytes changed')
        context=json.loads(first['territorial-context.json'])
        require(context['subject_count']==53 and len(set(context['subject_ids']))==53,'Exact 53 identity scope changed')
        require(context['current_official_municipality_count']==212 and context['current_official_subject_matches']==53,'Current roster match is incomplete')
        positive={'version':1,'issue':1185,'method_id':'slovenia-history-reproduction','kind':'positive-control','outcome':'passed',
          'verified_input_files':23,'issue_pins_verified':19,'exact_subjects':53,'current_official_subject_matches':53,
          'historic_reference_dates':list(runner.TARGET_DATES),'historical_name_rows_resolved_at_each_date':53,
          'all_inputs_verified_before_parse':True}
        trusted=runner.load_pinned(REPO)[1]
        changed=json.loads(trusted[HIST_PATH]); matches=[f for f in changed['features'] if str(int(f['properties']['SIFRA'])).zfill(3)=='121']
        require(matches,'Control source has no municipality code 121')
        matches[0]['properties']['NAZIV']='Auditor synthetic historical name'
        synthetic_history=(json.dumps(changed,ensure_ascii=False,separators=(',',':'))+'\n').encode()
        source_error=None; source_vintage='control-source-drift-'+uuid.uuid4().hex
        try: runner.run(REPO,source_vintage,overrides={HIST_PATH:synthetic_history})
        except ValueError as exc: source_error=str(exc)
        require(source_error and not (VINTAGES/source_vintage).exists(),'Changed historical response was not rejected before output')
        reader=csv.DictReader(io.StringIO(trusted[ROSTER_PATH].decode('utf-8-sig'),newline=''))
        fields=reader.fieldnames; roster_rows=list(reader); roster_rows[0]['location_id']='gb:SVN:ADM2:synthetic-outside-roster'
        buf=io.StringIO(newline=''); writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n'); writer.writeheader(); writer.writerows(roster_rows)
        synthetic_roster=buf.getvalue().encode(); roster_error=None; roster_vintage='control-roster-drift-'+uuid.uuid4().hex
        try: runner.run(REPO,roster_vintage,overrides={ROSTER_PATH:synthetic_roster})
        except ValueError as exc: roster_error=str(exc)
        require(roster_error and not (VINTAGES/roster_vintage).exists(),'Changed roster was not rejected before output')
        code_error=None; altered=OWNED_ROOT/('altered-runner-'+uuid.uuid4().hex+'.py')
        altered.write_bytes(SCRIPT.read_bytes()+b'\n# synthetic code drift\n')
        try: runner.verify_code_pin(altered)
        except ValueError as exc: code_error=str(exc)
        finally: altered.unlink(missing_ok=True)
        require(code_error,'Modified runner bytes were not rejected against its fixed code pin')
        sentinels=[]
        for name,payload in zip(collision_names,[b'preexisting-sentinel\n',b'interrupted-partial-sentinel\n']):
            directory=VINTAGES/name; directory.mkdir(); sentinel=directory/'2017-name-assessment.csv'; sentinel.write_bytes(payload)
            sentinels.append((directory,sentinel,payload))
        collisions=[]
        for name in collision_names:
            try: runner.run(REPO,name)
            except FileExistsError as exc: collisions.append(str(exc))
        require(len(collisions)==2 and all(s.read_bytes()==payload and [p.name for p in d.iterdir()]==['2017-name-assessment.csv'] for d,s,payload in sentinels),'Existing/partial outputs changed')
        negative={'version':1,'issue':1185,'method_id':'slovenia-history-reproduction','kind':'negative-control','outcome':'passed',
          'source_name_drift':{'field':'NAZIV','municipality_code':'121','synthetic_value':'Auditor synthetic historical name','fixture_bytes':len(synthetic_history),'fixture_sha256':digest(synthetic_history),'rejected_before_output':True,'error':source_error},
          'exact_subject_roster_drift':{'field':'location_id','fixture_bytes':len(synthetic_roster),'fixture_sha256':digest(synthetic_roster),'rejected_before_output':True,'error':roster_error},
          'runner_code_drift':{'rejected_before_output':True,'error':code_error},
          'existing_destination_and_interrupted_partial':{'rejected_before_write':True,'sentinel_sha256':[digest(x[2]) for x in sentinels],'errors':collisions,'files_unchanged':True}}
        reproducibility={'version':1,'issue':1185,'method_id':'slovenia-history-reproduction','kind':'reproducibility','outcome':'passed',
          'run_one_sha256':bundle(first),'run_two_sha256':bundle(second),
          'run_one_outputs':{n:{'bytes':len(b),'sha256':digest(b)} for n,b in sorted(first.items())},
          'run_two_outputs':{n:{'bytes':len(b),'sha256':digest(b)} for n,b in sorted(second.items())},
          'historical_assessment_exact':True,'historical_summary_exact':True,'complete_inputs_pinned_before_generation':True,
          'code_sha256':code_sha,'baseline_commit':runner.BASELINE_COMMIT}
        for name,value in [('positive-control.json',positive),('negative-control.json',negative),('reproducibility.json',reproducibility)]:
            path=control_root/name; path.parent.mkdir(parents=True,exist_ok=True)
            with open(path,'xb') as stream: stream.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
            control_paths.append(path)
        print(json.dumps({'outcome':'passed','exact_historical_reports':True,'run_bundle_sha256':reproducibility['run_one_sha256'],'controls':[str(p.relative_to(REPO)) for p in control_paths]},indent=2))
    finally:
        for path in cleanup: shutil.rmtree(path)
        if control_root.exists() and not os.environ.get('WORLDATLAS_RETAIN_CONTROLS'): shutil.rmtree(control_root)
        for name in collision_names:
            path=VINTAGES/name
            if path.exists(): shutil.rmtree(path)
if __name__=='__main__': main()
