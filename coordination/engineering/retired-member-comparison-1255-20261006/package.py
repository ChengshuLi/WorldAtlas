"""Retain actual complete two-run products and ordinary evidence inventory."""
import datetime,gzip,hashlib,json,pathlib,shutil,subprocess,sys
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];PREFIX=str(P.relative_to(R));sys.path.insert(0,str(R/'scripts'))
from evidence.immutable import canonical_json as canon
H=lambda b:hashlib.sha256(b).hexdigest();METHOD='complete-retired-member-diagnostics-v1';BASE='fbc64bcdd39d72e27c4dbc937281a7b3b2f0e9c2';FREEZE='c501ec6f6a11563286997c85e6d0edd004905c29';NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
index=json.loads((P/'input-index.json').read_bytes());report=json.loads((P/'.cache/final-run-one/report.json').read_bytes())
for name in ['one','two']:
 src=P/('.cache/final-run-'+name);dst=P/('run-'+name)
 if not dst.exists():shutil.copytree(src,dst)
 for f in src.rglob('*'):
  if f.is_file()and f.read_bytes()!=(dst/f.relative_to(src)).read_bytes():raise ValueError('Actual scientific retention differs')
v=P/'verification';v.mkdir(exist_ok=True)
def write(name,obj):(v/name).write_bytes(canon(obj))
controls=json.loads((P/'.cache/controls-seven.json').read_bytes());full=json.loads((P/'.cache/full-readback-one.json').read_bytes())
write('controls.json',controls);write('positive-control.json',{'method_id':METHOD,'kind':'positive-control','outcome':'passed','actual_complete_readback':full,'directed_controls_count':controls['count'],'source_and_physical_approval':False})
write('negative-control.json',{'method_id':METHOD,'kind':'negative-control','outcome':'passed','directed_actual_controls':controls,'coherently_rebound_diagnostics_and_omissions_rejected':True,'source_and_physical_approval':False})
(v/'reproducibility.json').write_bytes((P/'.cache/two-run-reproducibility.json').read_bytes())
(v/'input-preflight.json').write_bytes((P/'.cache/complete-input-preflight.json').read_bytes())
(v/'failed-input-preflight-270fb.log').write_bytes((P/'.cache/run-one.log').read_bytes())
write('failed-input-preflight-270fb.json',{'actual_tool_session':50211,'actual_exit_code':1,'executed_commit':'270fb1c4b1d48f6ad6b31c3cc382566025af25c9','phase':'whole input authentication before output mkdir or geometry loop','scientific_output_directory_created':False,'reason':'non-JSON retained recipe bytes were incorrectly passed to json.loads','preserved_log':'failed-input-preflight-270fb.log','counted_as_complete_scientific_run':False})
for name in ['one','two']:(v/('run-'+name+'.log')).write_bytes((P/('.cache/final-run-'+name+'.log')).read_bytes())
modules=[]
for row in report['executed_project_modules']:
 p=row['path'];actual=(R/p).read_bytes();frozen=subprocess.check_output(['git','show',FREEZE+':'+p],cwd=R);preflight=subprocess.check_output(['git','show','8494ff2e8c84c8fc709147f66358f38d58835720:'+p],cwd=R)
 if actual!=frozen or frozen!=preflight:raise ValueError('Executed/preflight module bytes differ')
 modules.append({'path':p,'bytes':len(actual),'sha256':H(actual),'actual_scientific_code_commit':FREEZE,'input_only_preflight_commit':'8494ff2e8c84c8fc709147f66358f38d58835720','all_three_whole_payloads_equal':True})
write('executions.json',{'version':1,'actual_code_commit':FREEZE,'two_actual_complete_sessions':[45335,91808],'two_actual_exit_codes':[0,0],'complete_scientific_tree_reports':['run-one/report.json','run-two/report.json'],'actual_software':report['software'],'actual_input_and_code_rosters':'Both complete ordinary reports retain all actual consumed input/module whole-file descriptors.','same_executed_modules_as_complete_input_only_preflight':modules,'counts_do_not_include':'Controls, failed input preflight, full pointset readback and recorded-field aggregation are not additional producer executions.'})
prep=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/1184-retired-member-preparation-20261006');(P/'diagnostic-unknowns.json.gz').write_bytes((prep/'full-6281-diagnostic-unknown-aggregation.json.gz').read_bytes())
write('original-scope-independent-review.json',json.loads((prep/'root-full-scope-custody-review.json').read_bytes()))
job={'version':2,'record_kind':'resumable_execution_artifact','job_id':P.name,'github_issue':1255,'lane':'engineering','branch':'engineering/'+P.name,'base_main_commit':BASE,'date_timezone':'America/Los_Angeles','task_status_source':'Linked GitHub issue','scope':'Complete literal retired-original-member coverage diagnostics for all2476 physical-only families/20032components/2438members/869contacts','completed':['Complete original encoded and decoded source byte custody','Two actual complete same-producer executions and full whole-record/pointset readback'],'checks':['65 directed controls and full immutable family/source/contact relations passed'],'blockers':[],'dependencies':[1184],'pull_request':None,'evidence_paths':[PREFIX+'/run-one/report.json',PREFIX+'/run-two/report.json',PREFIX+'/evidence-quality.json'],'maintenance':{'active':False,'required':False,'reason':None},'deployment':'Offline diagnostic evidence; physical/authority/cause and production remain unapproved','next_action':'Independent exact-head review and normal hosted checks/merge queue','updated_at':NOW}
(R/(PREFIX+'.json')).write_bytes(canon(job))
raw_fragments={PREFIX+'/'+x['ordinary']['path']for x in index['archive']['encoded']['parts']}
def descriptor(path,b=None):
 b=(R/path).read_bytes()if b is None else b;d={'path':path,'bytes':len(b),'sha256':H(b),'hash_kind':'file-bytes'}
 if b[:2]==b'\x1f\x8b'and path not in raw_fragments:
  raw=gzip.decompress(b);d.update(uncompressed_bytes=len(raw),uncompressed_sha256=H(raw))
 if d['bytes']>32*1024*1024 or d.get('uncompressed_bytes',0)>32*1024*1024:raise ValueError('Ordinary limit exceeded '+path)
 return d
pins=['a5423b1e62b5a0793b83999d87d1f6d50916db482cf2ec74973f75555c2bda6c','3d95a15d3797943290997c9a16fede48e6eb6e0941b0071a5fcd410375c49d46','3527014045c5aedc2b26be8bb5dff97e3e34097b7d4cb66a9b2fe3fcf33a6856','8180ea63d6c898940fbb2ea8b09c8604550c5883b74e9110f9bdee2d7a3a30d1','266c4f0f6e91381a26bfa6868d3c0df22b30140fa7f8551977be10b423295831']
baseline=[]
for h in pins:
 a=next(x for x in index['aliases']if x['original']['sha256']==h);path=a['original']['path'];b=subprocess.check_output(['git','show',BASE+':'+path],cwd=R)
 if H(b)!=h:raise ValueError('Required original report pin differs')
 baseline.append(descriptor(path,b))
path='scripts/evidence/immutable.py';baseline.append(descriptor(path,subprocess.check_output(['git','show',BASE+':'+path],cwd=R)))
files=sorted([f for f in P.rglob('*')if f.is_file()and'.cache'not in f.relative_to(P).parts and f.name!='evidence-quality.json']);files+=[R/(PREFIX+'.json')]
sources=[];outputs=[]
for f in files:
 d=descriptor(str(f.relative_to(R)))
 if f.parent.name=='inputs'or f.name in ['input-index.json','scope.json.gz','remaining-plan.json.gz']:sources.append(d)
 else:outputs.append(d)
scope_descriptor=next(d for d in sources if d['path']==PREFIX+'/scope.json.gz');metrics=[];bindings=[];summaries=[]
values={k:report[k]for k in ['complete_components','complete_families','complete_members','complete_contacts']}
values.update({'status_'+k:v for k,v in report['counts'].items()})
for k,value in values.items():
 metric={'id':k,'value':value,'unit':'records','vintage':'archived','evaluation_commit':FREEZE,'input_sha256':scope_descriptor['sha256']};metrics.append(metric);bindings.append({'metric_id':k,'path':PREFIX+'/run-one/report.json','json_pointer':'/'+k if k.startswith('complete_')else'/counts/'+k[7:]});summaries.append({'metric_id':k,'value':value,'unit':'records'})
manifest={'version':1,'issue':1255,'worker_id':'01a112b0-39fb-7f02-a3c7-d21d0916009f','lane':'engineering','subject_ids':[],'subject_ids_sha256':H(b'[]'),'baseline':{'commit':BASE,'files':baseline},'sources':[{'id':'complete-retired-member-ordinary-custody','url':'https://github.com/ChengshuLi/WorldAtlas/issues/1255','role':'Whole original immutable component/family/context aliases, complete original encoded and decoded archive fragments and recorded original attribution; no source authority approval','vintage':'Each whole original alias retains exact immutable commit/path and payload byte proof; archive whole encoded and decoded relationship preserved.','retrieved_at':NOW,'license':{'status':'redistributable','terms':'Previously retained repository and geoBoundaries derivative bytes. Complete derivative citation/use terms and individual original attribution retained; underlying government Direct Permission remains independently unverified, not a new permission claim.'},'retention':'retained','verification':'unverified','temporal_status':'reference','files':sources}],'outputs':outputs,'methods':[{'id':METHOD,'kind':'generator','helper_version':'worldatlas-evidence-preparation-v1','description':'Complete literal original archived member union/intersection/difference diagnostics; full pointsets, validity/operation/partition unknowns and all immutable family/contact/source relations retained. No numeric repair, physical classification or historical recipe reproduction.','software':'Actual pinned Python3.12.14 NumPy2.3.5 Shapely2.1.2 GEOS3.13.1 zlib1.2.12; frozen execution c501ec6f6a11563286997c85e6d0edd004905c29','units':'Planar longitude/latitude coordinate units and record counts; no physical area measurement'}],'metrics':metrics,'metric_bindings':bindings,'summaries':summaries,'conclusions':[],'stages':{'research':'partial','implementation':'implemented','geographic_approval':'not-requested'},'validation':[{'method_id':METHOD,'kind':kind,'outcome':'passed','evidence_path':PREFIX+'/verification/'+name}for kind,name in [('positive-control','positive-control.json'),('negative-control','negative-control.json'),('reproducibility','reproducibility.json')]],'commands':['See producer.py --help and verification/executions.json. Both actual complete runs use c501ec6f6a11563286997c85e6d0edd004905c29 and distinct safe owned outputs.','controls.py --code-commit c501ec6f6a11563286997c85e6d0edd004905c29 --output OWNED_NEW_CONTROL_RECEIPT','verify.py --run OWNED_COMPLETE_RUN --output OWNED_NEW_READBACK_RECEIPT'],'change_receipts':[{'path':str(f.relative_to(R)),'status':'added'}for f in files]+[{'path':PREFIX+'/evidence-quality.json','status':'added'}]}
(P/'evidence-quality.json').write_bytes(json.dumps(manifest,sort_keys=True,indent=2).encode()+b'\n')
print(json.dumps({'descriptors':len(baseline)+len(sources)+len(outputs),'actual_declared_bytes':sum(d['bytes']for d in baseline+sources+outputs),'scientific_files_retained_both':32,'manifest_sha256':H((P/'evidence-quality.json').read_bytes())}))
