from pathlib import Path
import json,gzip,subprocess,shutil,tempfile,hashlib,struct
D=Path('/workspace/scratch/127991fc8b8e/global-unassigned-census-20261014');R=Path(__file__).parent;T=Path(tempfile.mkdtemp(prefix='physical-selector-',dir=R));q=json.load(open(D/'physical-package-queue.json'));pidx={p['package_id']:p for p in q['packages']}
shutil.copy(D/'physical-batch-intervals.py',T/'physical-batch-intervals.py');shutil.copy(D/'physical-package-queue.json',T/'physical-package-queue.json')
# Copy no interval data: immutable inputs are linked only; intentional corruptions use detached copies.
def links(x):
 if isinstance(x,dict):
  if 'path' in x and (D/x['path']).is_file() and not (T/x['path']).exists():
   (T/x['path']).parent.mkdir(parents=True,exist_ok=True);(T/x['path']).symlink_to(D/x['path'])
  for v in x.values():links(v)
 elif isinstance(x,list):
  for v in x:links(v)
links(q)
def run(pkg,out):return subprocess.run(['python',str(T/'physical-batch-intervals.py'),pkg,str(T/out)],capture_output=True,text=True)
results=[]
for pkg,expected,records in [('physical-southern-l1-islands',43998,0),('physical-invalid-source-2380',948,1),('physical-antarctic-policy-coverage',0,673)]:
 out=pkg+'-output';x=run(pkg,out);assert x.returncode==0,x.stderr;m=json.loads(x.stdout);assert m['extracted_scope_cells']==expected and m['source_records']==records
 assert m['counted_global_work_cells']==(expected if pkg=='physical-southern-l1-islands' else 0)
 if expected:
  rr=[json.loads(l) for l in gzip.open(T/out/'intervals.jsonl.gz','rt')];assert sum(z-a for y,a,z in rr)==expected;assert rr==sorted(rr)
 collision=run(pkg,out);assert collision.returncode!=0 and 'FileExistsError' in collision.stderr
 results.append({'package_id':pkg,'extracted_scope_cells':expected,'source_records':records,'collision_rejected':True})
pin=pidx['physical-southern-l1-islands']['input_blocks'][0]['physical_input'];f=T/pin['path'];body=f.read_bytes();f.unlink();f.write_bytes(body+b' ');bad=run('physical-southern-l1-islands','corrupted-input-output');assert bad.returncode!=0 and 'Whole input hash/length mismatch' in bad.stderr;assert not (T/'corrupted-input-output'/'manifest.json').exists()
# Independent rectangle partition accounting and boundary cell checks.
scopes=[p for p in q['packages'] if p['accounting_role']=='disjoint-counted-global-work-domain'];assert len(scopes)==14 and sum(p['native_cells'] for p in scopes)==100304914
size=262166;lat=struct.unpack('<'+'d'*size,(D/'native-latitudes.f64le').read_bytes());edges=sorted({0,size,*[v for p in scopes for v in [p['selector']['row_start'],p['selector']['row_end']]]})
for y in edges[:-1]:
 spans=sorted((p['selector']['x_start'],p['selector']['x_end']) for p in scopes if p['selector']['row_start']<=y<p['selector']['row_end']);at=0
 for a,z in spans:assert a==at;at=z
 assert at==size
for p in scopes:
 s=p['selector'];west,south,east,north=s['longitude_latitude_bounds'];assert sum(x['package_cells'] for x in p['input_blocks'])==p['native_cells']
 for x in [s['x_start']-1,s['x_start'],s['x_end']-1,s['x_end']]:
  if 0<=x<size:assert (west<=360*(x+.5)/size-180<east)==(s['x_start']<=x<s['x_end'])
 for y in [s['row_start']-1,s['row_start'],s['row_end']-1,s['row_end']]:
  if 0<=y<size:assert (south<=lat[y]<north)==(s['row_start']<=y<s['row_end'])
result={'relocated_executor':'pass','cases':results,'corrupt_source_guard':'pass','no_completion_manifest_on_failure':'pass','independent_rectangle_partition':'14 disjoint complete-world rectangles; counts sum 100304914','boundary_cell_checks':'pass','script_sha256':hashlib.sha256((T/'physical-batch-intervals.py').read_bytes()).hexdigest(),'fixture':str(T)};(R/'physical-extractor-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
