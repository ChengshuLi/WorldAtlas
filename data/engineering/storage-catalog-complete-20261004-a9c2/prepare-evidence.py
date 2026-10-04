import hashlib,json,subprocess
from pathlib import Path
job='storage-catalog-complete-20261004-a9c2';owned=Path('data/engineering')/job
base='678d7e8f8686f575e024b593ce4e744a8bb4d79a';manifest=Path('coordination/engineering')/job/'evidence-quality.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def gitbytes(p):return subprocess.check_output(['git','show',base+':'+p])
def desc(p,b,role=None):
 d={'path':str(p),'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'}
 if role:d['role']=role
 return d
changed=['scripts/measure-neon-storage.mjs','test/neon-table-storage.test.mjs']
inputs=changed+['scripts/neon-forward-migrations.mjs','scripts/verify-neon-project.mjs','.github/operations/neon-forward-production.json','.github/workflows/neon-table-storage.yml','postgres/schema.sql','package-lock.json','data/hosted-type-catalog.json']
baselines=[desc(p,gitbytes(p),None if p in changed else 'original-source') for p in inputs]
paths=[Path(p) for p in changed]+[Path('coordination/engineering')/(job+'.json')]+sorted(p for p in owned.rglob('*') if p.is_file())
outputs=[desc(p,p.read_bytes()) for p in paths];metrics=[];bindings=[]
def metric(mid,value,unit,path,pointer,commit,inputsha):
 metrics.append({'id':mid,'value':value,'unit':unit,'vintage':'archived','evaluation_commit':commit,'input_sha256':inputsha});bindings.append({'metric_id':mid,'path':str(path),'json_pointer':pointer})
rp=owned/'tests-receipt-01.json';rv=json.loads(rp.read_text())
for k in ['test_count','pass_count','exit_code']:metric('catalog-tests-'+k,rv[k],'count',rp,'/'+k,base,sha((owned/'source-inventory-01.json').read_bytes()))
p=owned/'production-first-01.raw.json';raw=p.read_bytes();assert sha(raw)=='9bef7434c14a36282e9e0965373c77f1c6ec633335b5b6105332098453b9829c';r=json.loads(raw)
def numeric(v,parts=[]):
 if type(v) is int and parts!=['version']:
  key=parts[-1];unit='bytes' if key.endswith('_bytes') else 'MiB' if key.endswith('_mib') else 'estimated rows' if key.startswith('estimated_') else 'count'
  metric('retained-first-'+'-'.join(parts),v,unit,p,'/'+'/'.join(parts),'6d6bfa8e97d53d702d1d3035c3cb5cd9c3eb369e',sha(raw))
 elif isinstance(v,dict):
  for k,x in v.items():numeric(x,parts+[k])
 elif isinstance(v,list):
  for i,x in enumerate(v):numeric(x,parts+[str(i)])
numeric(r)
limit='Retained first23-fact-table observation is incomplete for owner registry/public metadata, unchanged raw source at actual6d6bfa8 commit, not current/new-query proof. Original private API/SQL credential responses are not retained; complete sanitized stdout and immutable Actions/GitHub provenance are retained. Production billing/reclaimable bytes/second-run inventory and geographic approval remain unverified.'
m={'version':1,'issue':738,'lane':'engineering','worker_id':'engineering-storage-diagnostic-a9c25e14-20261004','subject_ids':[],'subject_ids_sha256':sha(b'[]'),'baseline':{'commit':base,'files':baselines,'pins':{},'pin_files':{},'subject_files':{}},
'sources':[{'id':'retained-storage-contract','url':'https://github.com/ChengshuLi/WorldAtlas/issues/738#issuecomment-5979550512','role':'Existing project/target/schema and original actual sanitized first capacity observation; not a factual geography/historical assertion','vintage':'Baseline678d7e8; actual first observation source6d6bfa8/time2026-10-04T11:38:43.308Z','retrieved_at':'2026-10-04','license':{'status':'unknown','terms':'Existing locked dependencies; authorized sanitized private capacity metadata, not raw facts/credentials.'},'retention':'restoration-only','verification':'unverified','temporal_status':'reference','restoration':'Original raw sanitized stdout is retained whole in candidate with exact9bef7434 pin and in immutable issue comment5979550512/Actionsrun37199366909. Restore exact JSON plus newline from fenced comment; checkout baseline/npmci/data-hosted-type-catalog for isolated controls. No private cache/DB needed.','limit':limit}],
'outputs':outputs,'methods':[{'id':'public-catalog-completeness','kind':'code','description':'Enumerate bounded complete public catalog; explicit known application/registry/other-public/outside-public accounting, with unchanged exact-target READ ONLY redaction/timeouts. Actual isolated public/registry/non-application controls.','software':'Node24.19.0, locked Neon driver and PGlite','units':'bytes and estimated rows; isolated test counts'},{'id':'retained-capacity-observation','kind':'source','description':'Verify original actual sanitized first stdout byte pin, target/read-only/accounting provenance and reject deliberate corruption. Actual original private API responses and billing not independently verified; no new live measurement.','software':'Node24.19.0 SHA256','units':'Original archived catalog/provider bytes and explicitly estimated rows'}],
'validation':[{'method_id':mid,'kind':kind,'outcome':'passed','evidence_path':str(owned/(prefix+kind+'-01.json'))} for mid,prefix in [('public-catalog-completeness',''),('retained-capacity-observation','retained-')] for kind in ['positive-control','negative-control']],
'metrics':metrics,'metric_bindings':bindings,'summaries':[{'metric_id':x['id'],'value':x['value'],'unit':x['unit']} for x in metrics],
'conclusions':[{'text':'First actual source retained unchanged; second bounded implementation addresses owner-registry inventory gap. Current complete production inventory is not measured before review/accepted merge. No live write/normalization/provider change or physical reclamation claim.','status':'unresolved','source_ids':['retained-storage-contract']}],
'stages':{'research':'partial','implementation':'proposed','geographic_approval':'not-requested'},'commands':['node data/engineering/'+job+'/run-controls.mjs','node data/engineering/'+job+'/verify-retained-observation.mjs','python3 data/engineering/'+job+'/prepare-evidence.py','node scripts/evidence-quality.mjs '+str(manifest)],
'change_receipts':[{'path':str(p),'status':'modified','original_sha256':sha(gitbytes(str(p)))} if str(p) in changed else {'path':str(p),'status':'added'} for p in paths]+[{'path':str(manifest),'status':'added'}]}
manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'descriptors':len(outputs)+len(baselines),'bytes':sum(d['bytes'] for d in baselines+outputs),'changed_files':len(paths)+1,'metric_bindings':len(bindings),'manifest_sha256':sha(manifest.read_bytes())}))
