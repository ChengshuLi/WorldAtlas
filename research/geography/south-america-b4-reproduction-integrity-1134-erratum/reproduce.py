#!/usr/bin/env python3
"""Safely reproduce the pinned PR #1134 products twice and expose legacy defects.

This adapter is intentionally narrow: it authenticates original bytes at the
immutable #1124 baseline, redirects only the validator's scratch path, and gives
its unchanged main() a new private output directory for each invocation.
"""
from __future__ import annotations
import contextlib, datetime as dt, hashlib, importlib.util, json, os, pathlib, runpy, shutil, sys, tempfile, time, uuid

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = 'research/geography/south-america-b4-reproduction-integrity-1134-erratum/'
PACKET = 'data/regional-review/south-america-b4-area-validation-20261006'
BASE = '93c901e1c0b44073233fd3d48d403985a0cf2c52'
MAIN = '0c30d0bf9cee9a8c300c7e3c8f45720b471a74ff'
VALIDATOR = PACKET + '/validate_area_crosswalk.py'
BUILDER = PACKET + '/build_manifest.py'
SCOPE = PACKET + '/scope.json'
EXPECTED = ('companion-membership.csv','subject-parent-area.csv','report.json','positive-control.json','negative-control.json')
TDWG = ('scratch/tdwg-52da7828/tblLevel3.txt','scratch/tdwg-52da7828/tblLevel4.txt')
TDWG_HASHES = ('7eaf281dfbdca610c93938326c333d7c62d8e82ce3cba63b299d5a3a01d0003f','6fa350a0bb5939df0c665ae6cf253ddb0aa85fef6daa684c87ba400faf93b1c2')
PINNED = {
 'hierarchy':'data/hierarchy.json','world_index':'data/world-index.json',
 'original_scope':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json',
 'parent_rows':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/province-review.csv',
 'area_rows':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-review.csv',
 'area_crosswalk':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-source-crosswalk.csv',
 'area_reproducer':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce-area-source-crosswalk.py',
 'companion_scopes':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/companion-workload-scopes.json',
 'source_register':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json'}

def sha(b): return hashlib.sha256(b).hexdigest()
def git_blob(commit, path):
    import subprocess
    return subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{path}'],timeout=60)
def check(ok, msg):
    if not ok: raise ValueError(msg)
def digest_file(path):
    p=pathlib.Path(path)
    check(p.is_file() and not p.is_symlink(),f'Expected an ordinary file: {p}')
    raw=p.read_bytes(); return {'bytes':len(raw),'sha256':sha(raw)}
def canonical(v): return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def validate_products(products):
    check(isinstance(products,dict) and set(products)==set(EXPECTED),f'Producer output set mismatch: {sorted(products) if isinstance(products,dict) else type(products).__name__}')
    check(all(isinstance(v,bytes) and len(v)>0 for v in products.values()),'Producer emitted a missing or empty product')

def private_output(directory):
    p=pathlib.Path(directory)
    check(not p.exists() and not p.is_symlink(),'Output destination already exists')
    p.mkdir(parents=True,exist_ok=False)
    return p

@contextlib.contextmanager
def redirect_validator_scratch(safe_scratch):
    """Redirect exactly OWNED/'scratch' in the unchanged legacy validator."""
    old = pathlib.Path.__truediv__
    target = (ROOT / PACKET).resolve()
    safe_scratch = pathlib.Path(safe_scratch).resolve()
    def redirected(left, right):
        if pathlib.Path(left).resolve() == target and right == 'scratch':
            return safe_scratch
        return old(left, right)
    pathlib.Path.__truediv__ = redirected
    try: yield
    finally: pathlib.Path.__truediv__ = old

def invoke_validator(level3, level4, scope_path, output_dir, safe_scratch):
    src=git_blob(MAIN,VALIDATOR)
    check(sha(src)=='eed92403eaa4470e4df25f97522d22eb0a17df3afc5df94dc4b4e85e0fa390b4','Pinned validator source hash mismatch')
    child = r"""import hashlib,json,pathlib,runpy,sys
root=pathlib.Path(sys.argv[1]).resolve(); script=pathlib.Path(sys.argv[2]).resolve()
level3,level4,scope,out,scratch=map(pathlib.Path,sys.argv[3:8])
raw=script.read_bytes()
if hashlib.sha256(raw).hexdigest()!='eed92403eaa4470e4df25f97522d22eb0a17df3afc5df94dc4b4e85e0fa390b4': raise SystemExit('materialized validator drift')
old=pathlib.Path.__truediv__; owner=(root/'data/regional-review/south-america-b4-area-validation-20261006').resolve(); safe=scratch.resolve()
def redirected(left,right):
 if pathlib.Path(left).resolve()==owner and right=='scratch': return safe
 return old(left,right)
pathlib.Path.__truediv__=redirected
try:
 ns=runpy.run_path(str(script),run_name='worldatlas_pinned_validator')
 sys.argv=[str(script),'--level3',str(level3),'--level4',str(level4),'--scope',str(scope),'--output-dir',str(out)]
 ns['main']()
 print(json.dumps({'child_pid':__import__('os').getpid(),'status':'success'}))
finally: pathlib.Path.__truediv__=old
"""
    args=[sys.executable,'-c',child,str(ROOT),str(ROOT/VALIDATOR),str(level3),str(level4),str(scope_path),str(pathlib.Path(output_dir).relative_to(ROOT)),str(safe_scratch)]
    import subprocess
    completed=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=600)
    check(completed.returncode==0,'Actual validator process failed: '+completed.stderr[-2000:])
    try: child_record=json.loads(completed.stdout.strip().splitlines()[-1])
    except Exception as exc: raise ValueError('Missing child execution receipt: '+completed.stdout[-1000:]) from exc
    check(child_record.get('status')=='success','Validator child did not report successful completion')
    products={p.name:p.read_bytes() for p in pathlib.Path(output_dir).iterdir() if p.is_file() and not p.is_symlink()}
    validate_products(products)
    return products,child_record['child_pid']

def run_legacy_builder_case(root, second_names):
    """Execute unchanged builder with only Path.cwd root discovery redirected."""
    builder=git_blob(MAIN,BUILDER)
    check(sha(builder)=='c344eb709d56a355948cb7b387ca6ce38c1133491fff10786e57efcd11f9f206','Pinned builder hash mismatch')
    root=pathlib.Path(root).resolve(); d=root/PACKET
    for p in (d/'output',d/'scratch'/'run-two-output'): p.mkdir(parents=True,exist_ok=True)
    old_cwd=pathlib.Path.__dict__['cwd']
    pathlib.Path.cwd=classmethod(lambda cls: root)
    try:
        code=compile(builder,str(ROOT/BUILDER),'exec')
        exec(code,{'__name__':'worldatlas_pinned_builder','__file__':str(ROOT/BUILDER)})
    finally: pathlib.Path.cwd=old_cwd
    repro=json.loads((d/'output'/'reproducibility.json').read_text())
    evidence=json.loads((d/'evidence-quality.json').read_text())
    return {'fixture_second_run_files':list(second_names),'builder_exit':'success','reproducibility_outcome':repro.get('outcome'),'claimed_runs':repro.get('runs'),'claimed_output_count':len(repro.get('outputs_sha256',{})),'manifest_written':evidence.get('version')==1}

def exercise_admission_guards(baseline,stamp,scratch_root):
    from evidence.immutable import NewVintage
    results={}
    # Existing directory and its sentinel are preserved after a failed admission.
    name='control-existing-'+stamp; root=ROOT/OWNED/'vintages'/name; root.mkdir(parents=True,exist_ok=False)
    marker=root/'keep.txt'; marker.write_bytes(b'owned sentinel\n')
    try:
        try: NewVintage(baseline,OWNED,name,['only.json'])
        except FileExistsError: results['existing_destination']='rejected-before-write'
        else: raise ValueError('Existing destination unexpectedly admitted')
        check(marker.read_bytes()==b'owned sentinel\n','Existing destination marker changed')
    finally: shutil.rmtree(root)
    # Symlink parents fail closed; remove only the link created by this control.
    name='control-symlink-'+stamp; root=ROOT/OWNED/'vintages'/name; outside=scratch_root/(name+'-target'); outside.mkdir(exist_ok=False); root.symlink_to(outside,target_is_directory=True)
    try:
        try: NewVintage(baseline,OWNED,name,['only.json'])
        except ValueError: results['symlink_destination']='rejected-before-write'
        else: raise ValueError('Symlink destination unexpectedly admitted')
        check(not list(outside.iterdir()),'Symlink target was modified')
    finally: root.unlink(); outside.rmdir()
    # Unsafe and incomplete whole-file output sets fail before a success receipt.
    try: NewVintage(baseline,OWNED,'control-escape-'+stamp,['../escape.json'])
    except ValueError: results['path_escape']='rejected'
    else: raise ValueError('Path traversal unexpectedly admitted')
    admitted=NewVintage(baseline,OWNED,'control-partial-'+stamp,['one.json','two.json'])
    try: admitted.publish_bytes({'one.json':b'{}\n'})
    except ValueError: results['partial_output_set']='rejected-before-write'
    else: raise ValueError('Partial output set unexpectedly published')
    check(not admitted.root.exists(),'Rejected partial set left output directory')
    results['failed_run_receipt']='no completion receipt on incomplete output set'
    for label,fixture in [('empty',{}),('one-product',{'report.json':b'{}\n'}),('extra',{'report.json':b'{}\n','unexpected.json':b'{}\n'})]:
        try: validate_products(fixture)
        except ValueError: results['producer_'+label]='rejected-before-publication'
        else: raise ValueError('Malformed producer set unexpectedly accepted: '+label)
    return results

def main():
    # Authenticate the local issue scope against the immutable accepted bytes.
    scope_raw=git_blob(MAIN,SCOPE)
    check((ROOT/SCOPE).read_bytes()==scope_raw,'Materialized issue scope differs from fresh-main bytes')
    check(sha(scope_raw)=='058efe6265e78274409485aa2ecd7e5087435d1621074c2cb462952a6affa3e2','Issue #1124 source scope changed')
    scope=json.loads(scope_raw)
    check(len(scope['subject_ids'])==215 and len(set(scope['subject_ids']))==215,'Expected exact 215 unique original subjects')
    pins=scope['issue_evidence_quality']['pins']
    check(set(pins)==set(PINNED),'Unexpected issue source pin inventory')
    for key,path in PINNED.items(): check(sha(git_blob(BASE,path))==pins[key],f'Original issue pin mismatch: {key}')
    check(sha(git_blob(MAIN,'scripts/evidence/immutable.py'))=='a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46','Shared immutable helper pin mismatch')
    level3,level4=[ROOT/OWNED/p for p in TDWG]
    for p,h in zip((level3,level4),TDWG_HASHES): check(digest_file(p)['sha256']==h,'TDWG restoration hash mismatch')
    check(not level3.is_symlink() and not level4.is_symlink(),'Symlinked source file')

    # The helper admits every destination before either actual run starts.
    sys.path.insert(0,str(ROOT/'scripts'))
    from evidence.immutable import Baseline, NewVintage, descriptor, deterministic_gzip
    from datetime import timezone
    # Bind baseline inputs/code/helpers and the actual subject-bearing parts.
    bind_paths=[SCOPE,VALIDATOR,BUILDER,'scripts/evidence/immutable.py']+list(PINNED.values())
    part_paths=[f'data/geography/part-{n}.json' for n in (0,2,20,25,28,29)]
    input_paths=list(dict.fromkeys(bind_paths+part_paths))
    baseline_rows=[]
    for path in input_paths:
        raw=git_blob(MAIN,path)
        baseline_rows.append({'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
    baseline=Baseline(ROOT,MAIN,baseline_rows,max_phase_bytes=256*1024*1024)
    for path in input_paths: baseline.pinned_bytes(path)
    baseline.pinned_bytes(VALIDATOR); baseline.pinned_bytes(BUILDER)
    # Current checked out helper is pinned at fresh-main commit, but Baseline's
    # pin API reads from one commit, so separately authenticate its exact bytes.
    helper=(ROOT/'scripts/evidence/immutable.py').read_bytes()
    check(sha(helper)=='a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46','Materialized helper drift')

    stamp=dt.datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    vintage='runs-'+stamp
    filenames=[f"run-{i}-{name}{'.gz' if name.endswith('.csv') else ''}" for i in (1,2) for name in EXPECTED]+['run-receipts.json','two-run-comparison.json','legacy-controls.json']
    admitted=NewVintage(baseline,OWNED,vintage,filenames)
    # Input files are also checked again by NewVintage immediately before publish.
    scratch_root=ROOT/OWNED/'scratch'; scratch_root.mkdir(parents=True,exist_ok=True)
    outputs=[]; run_receipts=[]
    runner_sha=sha(pathlib.Path(__file__).read_bytes())
    for ordinal in (1,2):
        safe_scratch=scratch_root/f'{stamp}-run-{ordinal}-private'; safe_scratch.mkdir(exist_ok=False)
        out=scratch_root/f'{stamp}-run-{ordinal}-output'
        out.mkdir(exist_ok=False)
        start=dt.datetime.now(timezone.utc).isoformat()
        before=time.monotonic_ns()
        products,child_pid=invoke_validator(level3,level4,ROOT/SCOPE,out,safe_scratch)
        elapsed=time.monotonic_ns()-before
        end=dt.datetime.now(timezone.utc).isoformat()
        outputs.append(products)
        run_receipts.append({'run':ordinal,'run_id':uuid.uuid4().hex,'status':'success','started_at':start,'finished_at':end,'elapsed_monotonic_ns':elapsed,'process_id':child_pid,'baseline_commit':BASE,'runner_path':str(pathlib.Path(__file__).resolve().relative_to(ROOT)),'runner_sha256':runner_sha,'scope_sha256':sha(scope_raw),'validator_sha256':sha(git_blob(MAIN,VALIDATOR)),'source_files':[{'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name,**digest_file(p)} for p in (level3,level4)],'products':[{'name':n,'bytes':len(products[n]),'sha256':sha(products[n])} for n in EXPECTED]})
    first,second=outputs
    check(set(first)==set(EXPECTED) and set(second)==set(EXPECTED),'Both actual executions must emit exactly five products')
    comparison={name:{'run1_sha256':sha(first[name]),'run2_sha256':sha(second[name]),'byte_equal':first[name]==second[name],'bytes':len(first[name])} for name in EXPECTED}
    check(all(row['byte_equal'] for row in comparison.values()),'Whole output bytes differ between actual executions')
    check(run_receipts[0]['run_id']!=run_receipts[1]['run_id'] and run_receipts[0]['started_at']!=run_receipts[1]['started_at'] and run_receipts[0]['process_id']!=run_receipts[1]['process_id'],'Run identities/processes are not distinct')

    # Demonstrate unsafe overwrite only against our own five private sentinels.
    sentinel=scratch_root/f'{stamp}-legacy-overwrite-private'; sentinel.mkdir(exist_ok=False)
    sentinels={name:(f'private sentinel {name}\n').encode() for name in EXPECTED}
    for name,raw in sentinels.items(): (sentinel/name).write_bytes(raw)
    invoke_validator(level3,level4,ROOT/SCOPE,sentinel,scratch_root/f'{stamp}-legacy-overwrite-scratch')
    overwritten=all((sentinel/n).read_bytes()!=raw for n,raw in sentinels.items())
    check(overwritten,'Expected legacy CLI to overwrite the private sentinel fixture')

    # Exercise actual unchanged builder with complete, empty and one-product run 2.
    builder_cases={}
    source_packet=ROOT/PACKET
    for case,names in [('complete',EXPECTED),('empty',()),('one-product',(EXPECTED[3],)),('copied-first-run',EXPECTED)]:
        case_root=scratch_root/f'{stamp}-builder-{case}'; d=case_root/PACKET
        (d/'output').mkdir(parents=True); (d/'scratch'/'run-two-output').mkdir(parents=True)
        (d/'scope.json').write_bytes(scope_raw)
        # Original builder requires the report metrics and subject roster. These
        # are read from pinned legacy outputs and copied only into this sandbox.
        for name in ('report.json','subject-parent-area.csv'):
            (d/'output'/name).write_bytes(git_blob(MAIN,f'{PACKET}/output/{name}'))
        for name in EXPECTED: (d/'output'/name).write_bytes(git_blob(MAIN,f'{PACKET}/output/{name}'))
        for name in names:
            raw=outputs[0][name] if case=='copied-first-run' else git_blob(MAIN,f'{PACKET}/output/{name}')
            (d/'scratch'/'run-two-output'/name).write_bytes(raw)
        builder_cases[case]=run_legacy_builder_case(case_root,names)
    check(all(builder_cases[k]['reproducibility_outcome']=='passed' and builder_cases[k]['claimed_runs']==2 for k in ('complete','empty','one-product','copied-first-run')),'Legacy builder false-pass controls did not reproduce')
    admission_controls=exercise_admission_guards(baseline,stamp,scratch_root)
    controls={'method_id':'safe-output','kind':'negative-control','outcome':'passed','private_sentinel_overwrite_reproduced':overwritten,'admission_controls':admission_controls,'legacy_builder_cases':builder_cases,'safe_runner_guards':{'reject_existing_destination':'tested by NewVintage admission; no files touched','exact_five_names':'passed for both actual runs','reject_empty_or_partial_actual_products':'pre-publication exact-set assertion','byte_compare_each_product':'passed','distinct_run_receipts':'passed'},'interpretation':'Legacy controls are reproductions of defects, not accepted success receipts. Sentinels and malformed builder fixtures were private generated scratch only.'}
    values={}
    stored_outputs=[]
    for i,products in enumerate(outputs,1):
        for name,raw in products.items():
            stored=f"run-{i}-{name}{'.gz' if name.endswith('.csv') else ''}"
            values[stored]=deterministic_gzip(raw) if name.endswith('.csv') else raw
            stored_outputs.append({'path':f'{OWNED}vintages/{vintage}/{stored}','compression':'gzip' if name.endswith('.csv') else 'none','stored_bytes':len(values[stored]),'stored_sha256':sha(values[stored]),'uncompressed_bytes':len(raw),'uncompressed_sha256':sha(raw)})
    values['run-receipts.json']=canonical({'version':1,'status':'two-complete-actual-runs','runs':run_receipts,'stored_outputs':stored_outputs,'baseline_inputs':baseline_rows,'tdwg_restoration_inputs':[{'source_commit':'52da7828aba9d461dd133c27b3bd7a4407161f54','path':f'109-488-1-ED/2nd Edition/{pathlib.Path(f).name}','retrieved_at':'2026-10-07','retention':'private-restoration-only; terms not located','bytes':digest_file(f)['bytes'],'sha256':digest_file(f)['sha256']} for f in (level3,level4)]})
    values['two-run-comparison.json']=canonical({'version':1,'method_id':'exact-roster-and-ancestry','kind':'reproducibility','outcome':'passed','status':'passed','actual_run_count':len(run_receipts),'expected_product_count_per_run':len(EXPECTED),'exact_whole_file_match_count':sum(row['byte_equal'] for row in comparison.values()),'expected_products':list(EXPECTED),'run1_id':run_receipts[0]['run_id'],'run2_id':run_receipts[1]['run_id'],'products':comparison,'identity_subjects':len(scope['subject_ids']),'subject_ids_sha256':scope['subject_ids_sha256'],'claim_limit':'This establishes reproducibility of the unchanged validator outputs against the pinned historical source tables and Atlas ancestry snapshots only; no current legal-boundary or regional-completeness approval.'})
    values['legacy-controls.json']=canonical(controls)
    admitted.publish_bytes(values)
    print(json.dumps({'status':'complete','vintage':vintage,'output_count':len(values),'comparison':comparison,'builder_controls':builder_cases,'sentinel_overwrite':overwritten},indent=2))

if __name__=='__main__': main()
