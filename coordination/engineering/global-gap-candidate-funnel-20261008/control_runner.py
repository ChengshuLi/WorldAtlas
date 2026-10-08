"""Fresh bounded result writer for contract, IO and complete-report controls."""
import json,subprocess,sys,hashlib,uuid,copy
from pathlib import Path
import bounded_io as b
P='coordination/engineering/global-gap-candidate-funnel-20261008/'
def main():
    repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel']).decode().strip());head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
    destination=b.ordinary(repo/P/'vintages'/sys.argv[1]);b.need(destination.parent.is_dir() and not destination.exists() and not destination.is_symlink(),'Fresh control result destination required')
    planpath=P+'inputs/control-pins.json';raw=subprocess.check_output(['git','show',head+':'+planpath]);b.need(len(raw)<=16384,'Small frozen control plan required');pins=json.loads(raw);pins.append({'commit':head,'path':planpath,'bytes':len(raw),'sha256':b.sha(raw)})
    codepins=[]
    for name in ('control_runner.py','controls.py','catalog.py','bounded_io.py'):
        path=P+name;body=subprocess.check_output(['git','show',head+':'+path]);b.need(len(body)<=65536,'Bounded actual control code');b.need(body==(repo/path).read_bytes(),'Executed control code drift');codepins.append({'commit':head,'path':path,'bytes':len(body),'sha256':b.sha(body)})
    phase=b.Phase(repo,destination,pins+codepins,2*1024*1024);bodies={p['path']:phase.read(p) for p in phase.pins.values()}
    namespace={'__file__':str(repo/P/'controls.py')};saved=sys.stdout
    import contextlib,io
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):exec(compile(bodies[P+'controls.py'],P+'controls.py','exec'),namespace)
    contract=json.loads(capture.getvalue());b.need(contract['negative_count']==14 and contract['positives']==3,'Complete original adverse control scope')
    reports=[body for path,body in bodies.items() if path.endswith('/report.json')];b.need(len(reports)==2 and reports[0]==reports[1],'Complete parent two-run output drift');report=json.loads(reports[0]);b.need(report['component_count']==95173 and report['counts']['implemented']==2 and report['counts']['fully_integrated']==0 and report['counts']['delivered']==0,'Complete measured report transitions drift')
    calls=[];real=b.subprocess.check_output
    def spy(args,*a,**kw):calls.append(args);return real(args,*a,**kw)
    b.subprocess.check_output=spy;neg=[]
    fake=[{'commit':head,'path':P+f'fake{i}.gz','bytes':33554432,'sha256':'0'*64,'uncompressed_bytes':33554432,'uncompressed_sha256':'0'*64} for i in range(4)]
    try:b.Phase(repo,destination,fake,8192);raise AssertionError('Overcap admitted')
    except ValueError as e:b.need(not calls,'Pre-admission body read');neg.append({'case':'overcap','rejection':str(e),'git_calls':0})
    # The already-existing frozen scope result supplies a real sentinel; no fixture
    # file or parent is changed to exercise collision rejection.
    existing=repo/P/'vintages/scope-one';sentinel=(existing/'publication.json').read_bytes()
    try:b.Phase(repo,existing,[],8192);raise AssertionError('Existing destination admitted')
    except ValueError as e:b.need(not calls and (existing/'publication.json').read_bytes()==sentinel,'Collision changed source sentinel');neg.append({'case':'existing-output','rejection':str(e),'git_calls':0,'sentinel_sha256':b.sha(sentinel)})
    link=destination.parent/('control-dangling-'+uuid.uuid4().hex);link.symlink_to(destination)
    try:
        try:b.Phase(repo,link,[],8192);raise AssertionError('Dangling destination admitted')
        except ValueError as e:b.need(not calls and link.is_symlink(),'Dangling target altered');neg.append({'case':'dangling-output','rejection':str(e),'git_calls':0})
    finally:link.unlink()
    b.subprocess.check_output=real
    phase.output('contract-controls.json',b.canonical({'execution_commit':head,**contract}));phase.output('io-controls.json',b.canonical({'execution_commit':head,'negatives':neg}))
    for kind,details in [('positive-control',{'complete_original_ids':95173,'accepted_classifications':2,'implemented':2,'fully_integrated':0,'delivered':0}),('negative-control',{'contract_negative_count':14,'whole_admission_negative_count':3,'scope':'Schema/join/transition and data admission controls; no geographical experiment.'}),('reproducibility',{'run_one_sha256':b.sha(reports[0]),'run_two_sha256':b.sha(reports[1]),'catalog_pairs':json.loads(next(body for path,body in bodies.items() if path.endswith('/pair-readback.json')))})]:phase.output(kind+'.json',b.canonical({'method_id':'bounded-candidate-funnel','kind':kind,'outcome':'passed',**details}))
    for p in codepins:b.need(b.sha((repo/p['path']).read_bytes())==p['sha256'],'Post-control source code drift')
    print(json.dumps(phase.finish({'stage':'control-run','execution_commit':head,'contract_negatives':14,'admission_negatives':3,'limits':'Engineering metadata controls only; no physical/source/native-runtime/RSS qualification.'}),sort_keys=True))
if __name__=='__main__':main()
