"""Postprocessing only: retain real completed runs and bind the original issue contract."""
import pathlib,json,hashlib,subprocess,shutil,re,os
N=pathlib.Path(__file__).absolute().parent; W=N.parents[2]; PREFIX=N.relative_to(W).as_posix()+'/'
FREEZE='2c8ff13e141498887676b6983fff449d83e0d504'; ORIGINAL='0796a3a86616aa87e4b89cbd6ce2ec8beb727d07'
def raw(commit,name):return subprocess.check_output(['git','-C',str(W),'show',commit+':'+name])
def h(b):return hashlib.sha256(b).hexdigest()
def save(name,value):
 p=N/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False).encode()+b'\n')
def file(name):
 p=W/name;b=p.read_bytes();assert p.is_file() and not p.is_symlink() and len(b)<=33554432
 return dict(path=name,bytes=len(b),sha256=h(b),hash_kind='file-bytes')
def main():
 plan=json.loads((N/'input-plan.json').read_bytes());codes=json.loads((N/'code-list.json').read_bytes())
 for name in codes:assert (N/name).read_bytes()==raw(FREEZE,PREFIX+name)
 for tag in ['one','two']:
  src=W/('.cache/1421-2c8-run-'+tag);logs=W/('.cache/1421-2c8-run-'+tag+'-execution');execution=json.loads((logs/'execution.json').read_bytes())
  assert execution['exit_code']==0 and execution['execution_commit']==FREEZE
  target=N/('run-'+tag);target.mkdir()
  for name in ['comparison.json','input-receipt.json']:shutil.copy2(src/name,target/name)
  for name in ['execution.json','stdout','stderr']:shutil.copy2(logs/name,target/name)
  for p in target.iterdir():os.chmod(p,0o644)
 comparison=json.loads((N/'run-one/comparison.json').read_bytes())
 for name in ['comparison.json','input-receipt.json']:assert (N/'run-one'/name).read_bytes()==(N/'run-two'/name).read_bytes()
 assert comparison==json.loads(raw(ORIGINAL,'research/geography/mongolia-russia-gap-source-fitness-20261007/runs/comparison-run-1.json'))
 for name,src in [('entry-controls.json','1421-entry-controls-2c8.json'),('method-controls.json','1421-method-controls-2c8.json'),('full-pair-and-history.json','1421-2c8-full-pair-structural-history-readback.json'),('operating-admission.json','1421-2c8-complete-publication-prepair-admission.json')]:
  save('v/'+name,json.loads((W/'.cache'/src).read_bytes()))
 method='guarded-original-source-overlay'
 for kind,src in [('positive-control','method-controls.json'),('negative-control','entry-controls.json'),('reproducibility','full-pair-and-history.json')]:
  obj=dict(method_id=method,kind=kind,outcome='passed',basis=PREFIX+'v/'+src,scope='Complete actual two-run outputs and separate literal entry/tiny method controls; no new source conclusion.')
  if kind=='reproducibility':obj.update(run_one_sha256=h((N/'run-one/comparison.json').read_bytes()),run_two_sha256=h((N/'run-two/comparison.json').read_bytes()))
  save('v/'+kind+'.json',obj)
 issue=json.loads((W/'.cache/1421-prepublication-current-issue.json').read_bytes());spec=json.loads(re.search(r'<!-- worldatlas-work:v1\s*(.*?)\s*-->',issue['body'],re.S).group(1))['evidence_quality']
 old=json.loads(raw(ORIGINAL,'research/geography/mongolia-russia-gap-source-fitness-20261007/evidence-quality.json'))
 baseline=list(plan['original_files'])
 for name in ['research/geography/mongolia-russia-gap-source-fitness-20261007/evidence-quality.json','scripts/evidence/immutable.py']:
  b=raw(ORIGINAL,name);baseline.append(dict(path=name,bytes=len(b),sha256=h(b),hash_kind='file-bytes'))
 pins=spec['pins'];pin_files={key:next(x['path']for x in baseline if x['sha256']==sha)for key,sha in pins.items()}
 sources=[]
 for source in old['sources']:
  source=dict(source);source.pop('files',None);source['retention']='restoration-only';source['restoration']='The entire original source packet is durably retained at immutable merge '+ORIGINAL+'; all original containing bodies are named in this manifest baseline. Actual consumed source aliases and encoded/decoded relations are in input-plan.json and both input-receipt.json files. The original source citation, license/date/authority uncertainties and original packet remain unchanged.';source['limit']=source.get('limit','Original source date, precision and authority are not independently approved.')
  sources.append(source)
 outputs=[file(p.relative_to(W).as_posix())for p in sorted(N.rglob('*'))if p.is_file()and'__pycache__'not in p.parts and p.name!='evidence-quality.json']
 m=dict(version=1,issue=1421,lane='engineering',worker_id='01a10fea-fe9b-7722-a974-0269a733a330',subject_ids=spec['subject_ids'],subject_ids_sha256=h(json.dumps(sorted(spec['subject_ids']),separators=(',',':')).encode()),baseline=dict(commit=ORIGINAL,files=baseline,pins=pins,pin_files=pin_files),sources=sources,outputs=outputs,methods=[dict(id=method,kind='geography',description='Original literal full48-component source predicates/intersections and ellipsoidal-area loops, guarded before helper imports and actual source reads. No acquisition, geometry repair, assignment or new geographic conclusion. Two real same-freeze subprocess executions; full original scientific JSON equality; source/runtime/code callable authentication before and after operations.',software='Python3.12, NumPy2.3.5, Shapely2.1.2/GEOS3.13.1, pyproj3.7.2; all actual installed module/native/PROJ-data origins bound to whole r/ aliases. macOS system shared-cache image identities are explicit platform dependencies.',units='source features, component IDs, positive polygon areas in square metres',axis_order='longitude-latitude',crs='EPSG:4326',area_method='WGS84 straight-source-edge ellipsoidal integral',distance_method='WGS84 inverse geodesic',helper_version='worldatlas-evidence-geometry-v1')],metrics=[],metric_bindings=[],summaries=[],conclusions=[dict(status='supported',source_ids=[s['id']for s in sources],text='Both genuinely guarded same-freeze complete48+8 source comparison results match one another and all original scientific values; original full source pointsets, source properties, predicates, scalar values, and all unknowns remain unchanged. This is an executed-provenance correction, not new geographic evidence.'),dict(status='unresolved',source_ids=[s['id']for s in sources],text='Original source temporal/legal/precision/physical-water/ownership and cause limitations remain; Russia has2327 actual versus2328 advertised features. Prior1417 ignored-cache preservation remains unverified; this task does not recover it. macOS shared-cache system images remain platform identities rather than ordinary byte aliases.')],stages=dict(research='complete',implementation='implemented',geographic_approval='unapproved'),commands=[f'git checkout --detach {FREEZE}',f'Run the frozen record.py with the authenticated primary Python, -I -S -B, --commit {FREEZE}, and two distinct exclusive --name values; exact executed isolated scientific commands/cwd/environment/start/end/PID/exit are retained in run-one/execution.json and run-two/execution.json. No extraction/source acquisition.'],validation=[dict(method_id=method,kind=k,outcome='passed',evidence_path=PREFIX+'v/'+k+'.json')for k in ['positive-control','negative-control','reproducibility']])
 for key,value in comparison['result_counts'].items():
  m['metrics'].append(dict(id=key,value=value,unit='identities',vintage='baseline',input_sha256=h((N/'run-one/comparison.json').read_bytes()),evaluation_commit=ORIGINAL));m['metric_bindings'].append(dict(metric_id=key,path=PREFIX+'run-one/comparison.json',json_pointer='/result_counts/'+key));m['summaries'].append(dict(metric_id=key,value=value,unit='identities'))
 names=[x['path']for x in outputs]+[PREFIX+'evidence-quality.json'];m['change_receipts']=[dict(path=name,status='added')for name in sorted(names)]
 assert len(baseline)+len(outputs)<=512 and sum(x['bytes']for x in baseline+outputs)+786432<=268435456
 save('evidence-quality.json',m)
 print(json.dumps(dict(status='PASS',descriptors=len(baseline)+len(outputs),encoded=sum(x['bytes']for x in baseline+outputs),changed=len(names),manifest_sha256=h((N/'evidence-quality.json').read_bytes()),finalizer_sha256=h(pathlib.Path(__file__).read_bytes()))))
if __name__=='__main__':main()
