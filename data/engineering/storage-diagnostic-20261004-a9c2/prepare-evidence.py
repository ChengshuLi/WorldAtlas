import hashlib,json,subprocess
from pathlib import Path
root=Path('.');job='storage-diagnostic-20261004-a9c2';owned=Path('data/engineering')/job
base='7f67c1118741c0c2dae92c16b895a65ad4d81de3';manifest=Path('coordination/engineering')/job/'evidence-quality.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def desc(p,b,role=None):
 d={'path':str(p),'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'}
 if role:d['role']=role
 return d
inputs=['scripts/verify-neon-project.mjs','scripts/verify-neon-capacity.mjs','scripts/verify-neon-sql.mjs','.github/operations/neon-forward-production.json','.github/workflows/neon-verify.yml','postgres/schema.sql','package-lock.json','data/hosted-type-catalog.json']
baselines=[desc(p,subprocess.check_output(['git','show',base+':'+p]),'original-source') for p in inputs]
paths=[Path('scripts/measure-neon-storage.mjs'),Path('test/neon-table-storage.test.mjs'),Path('.github/workflows/neon-table-storage.yml'),Path('coordination/engineering')/(job+'.json')]+sorted(p for p in owned.rglob('*') if p.is_file())
outputs=[desc(p,p.read_bytes()) for p in paths]
metrics=[];bindings=[]
receipt=owned/'tests-receipt-01.json';values=json.loads(receipt.read_text())
for key in ['test_count','pass_count','exit_code']:
 mid='isolated-tests-'+key;metrics.append({'id':mid,'value':values[key],'unit':'count','vintage':'archived','evaluation_commit':base,'input_sha256':sha((owned/'source-inventory-01.json').read_bytes())});bindings.append({'metric_id':mid,'path':str(receipt),'json_pointer':'/'+key})
m={'version':1,'issue':738,'lane':'engineering','worker_id':'engineering-storage-diagnostic-a9c25e14-20261004','subject_ids':[],'subject_ids_sha256':sha(b'[]'),'baseline':{'commit':base,'files':baselines,'pins':{},'pin_files':{},'subject_files':{}},
'sources':[{'id':'existing-neon-contract','url':'https://github.com/ChengshuLi/WorldAtlas','role':'Existing exact project/production target, pinned driver and unchanged schema; no new geographic/factual source','vintage':base,'retrieved_at':'2026-10-04','license':{'status':'unknown','terms':'No new upstream redistribution; existing dependency licenses remain in locked packages.'},'retention':'restoration-only','verification':'unverified','temporal_status':'reference','restoration':'Checkout the pinned baseline and npm ci on Node24; whole baseline originals, new source/control bytes and logs are hashed. Restore all data/source/research independently from Git, not an inherited database.','limit':'Repository and synthetic isolated controls do not verify current production credentials, actual branch storage or billing. Isolated source inventory pins uncommitted measured candidate bytes; baseline ancestry is not a clean-tree measurement claim. No primary historical/geographic fact, release approval or production proof is asserted.'}],
'outputs':outputs,'methods':[{'id':'fixed-readonly-catalog','kind':'code','description':'Fixed main-only bounded catalog reads, exact project/branch/host/SQL identity and enforced READ ONLY/timeouts with sanitized output; real isolated PostgreSQL and mocked management negative controls.','software':'Node24.19.0, locked Neon driver and PGlite','units':'bytes and explicitly estimated rows; isolated test counts'}],
'validation':[{'method_id':'fixed-readonly-catalog','kind':kind,'outcome':'passed','evidence_path':str(owned/(kind+'-01.json'))} for kind in ['positive-control','negative-control']],
'metrics':metrics,'metric_bindings':bindings,'summaries':[{'metric_id':m['id'],'value':m['value'],'unit':m['unit']} for m in metrics],
'conclusions':[{'text':'Tooling is validated against isolated PostgreSQL and synthetic metadata only. Actual production observation and capacity interpretation await reviewed accepted main dispatch; no hypothetical physical reclaim or billing claim.','status':'unresolved','source_ids':['existing-neon-contract']}],
'stages':{'research':'partial','implementation':'proposed','geographic_approval':'not-requested'},'commands':['node data/engineering/'+job+'/run-controls.mjs','python3 data/engineering/'+job+'/prepare-evidence.py','node scripts/evidence-quality.mjs '+str(manifest)],'change_receipts':[{'path':str(p),'status':'added'} for p in paths]}
manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'descriptors':len(outputs)+len(baselines),'bytes':sum(d['bytes'] for d in baselines+outputs),'changed_files':len(paths)+1,'manifest_sha256':sha(manifest.read_bytes())}))
