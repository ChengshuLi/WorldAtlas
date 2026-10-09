"""Actual projection, admission and paired-report metadata controls."""
import contextlib,io,json,pathlib,sys,uuid
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import refresh
b=refresh.bio;Q=refresh.Q
repo=pathlib.Path(refresh.git(pathlib.Path.cwd(),'rev-parse','--show-toplevel').decode().strip());head=refresh.git(repo,'rev-parse','HEAD').decode().strip();destination=repo/Q/'vintages'/sys.argv[1]
planpath=Q+'inputs/control-pins.json';raw=refresh.metadata(repo,head,planpath);pins=refresh.declaration(repo,head)+json.loads(raw)+[{'commit':head,'path':planpath,'bytes':len(raw),'sha256':b.sha(raw)}];code=[]
for path in (*refresh.CODE,Q+'refresh-controls.py',Q+'control-runner.py'):
 body=refresh.metadata(repo,head,path);b.need(body==(repo/path).read_bytes(),'Actual control code');code.append({'commit':head,'path':path,'bytes':len(body),'sha256':b.sha(body)})
runtime=json.loads(refresh.metadata(repo,head,Q+'inputs/runtime.json'));phase=b.Phase(repo,destination,pins+code,2097152,runtime['files']);bodies={p['path']:phase.read(p) for p in phase.pins.values()}
capture=io.StringIO()
with contextlib.redirect_stdout(capture):exec(compile(bodies[Q+'refresh-controls.py'],Q+'refresh-controls.py','exec'),{'__file__':str(repo/Q/'refresh-controls.py')})
controls=json.loads(capture.getvalue());b.need(controls['positive_count']==4 and controls['negative_count']==13,'Complete actual helper controls')
reports=[v for p,v in bodies.items() if p.endswith('/report.json')];b.need(len(reports)==2 and reports[0]==reports[1],'Complete actual parent report equality');report=json.loads(reports[0]);b.need(report['component_count']==95173 and report['counts']['accepted_source_relative_repair_decisions']==16 and report['counts']['fully_integrated']==2 and report['counts']['delivered']==0,'Actual complete report domain counts')
pairs=[json.loads(v) for p,v in bodies.items() if p.endswith('/pair.json')];b.need(len(pairs)==7 and all(p['whole_equal'] for p in pairs) and sum(p['component_count'] for p in pairs)==95173,'All seven complete whole output pairs')
real=b.subprocess.check_output;calls=[];b.subprocess.check_output=lambda *a,**k:calls.append(a) or real(*a,**k);neg=[]
def reject(name,fn):
 try:fn()
 except ValueError as e:b.need(not calls,'Body read before rejected admission');neg.append({'case':name,'reason':str(e),'git_body_calls':0})
 else:raise AssertionError(name+' admitted')
fake=[{'commit':head,'path':Q+f'fake{i}.gz','bytes':33554432,'sha256':'0'*64,'uncompressed_bytes':33554432,'uncompressed_sha256':'0'*64} for i in range(4)]
reject('complete-phase-overcap',lambda:b.Phase(repo,destination,fake,8192,runtime['files']))
reject('execution-runtime-overcap',lambda:b.Phase(repo,destination,[],8192,[dict(runtime['files'][0],bytes=33554433)]))
reject('descriptor-overcap',lambda:b.Phase(repo,destination,[{'commit':head,'path':Q+f'fake{i}','bytes':0,'sha256':'0'*64} for i in range(513)],8192))
existing=repo/Q/'vintages/parent-run-1';sentinel=(existing/'publication.json').read_bytes();reject('exclusive-existing-output',lambda:b.Phase(repo,existing,[],8192));b.need(sentinel==(existing/'publication.json').read_bytes(),'Original sentinel changed')
link=destination.parent/('control-dangling-'+uuid.uuid4().hex);link.symlink_to(destination)
try:reject('dangling-output',lambda:b.Phase(repo,link,[],8192))
finally:link.unlink()
b.subprocess.check_output=real
phase.output('helper-controls.json',b.canonical(controls));phase.output('admission-controls.json',b.canonical({'negative_count':len(neg),'negatives':neg,'fixture_limit':'Prospective rejection controls only; no geographic execution.'}))
for kind,v in [('positive-control',{'actual_helper_positives':4,'component_count':95173,'accepted_source_relative_repair_decisions':16,'fully_integrated':2,'delivered':0}),('negative-control',{'actual_helper_negatives':13,'admission_negatives':5}),('reproducibility',{'run_one_sha256':b.sha(reports[0]),'run_two_sha256':b.sha(reports[1]),'complete_catalog_pairs':pairs})]:phase.output(kind+'.json',b.canonical({'method_id':'catalog-progress-refresh','kind':kind,'outcome':'passed',**v}))
print(json.dumps(refresh.finish(phase,code,{'stage':'refresh-controls','actual_helper_positives':4,'actual_helper_negatives':13,'admission_negatives':5,'limits':'Metadata-only controls; no new geographic/source/native/runtime scientific qualification.'}),sort_keys=True))
