"""Execute a fresh simple mainland seed from selected Neon L2 decisions.

The caller authenticates the pinned Neon export and independently resolves the
current stage-1 component witnesses before invoking this producer. No historical
continent map, prior assignment checkpoint, or List 1 override is accepted.
"""
import hashlib,json,os,shutil,signal,subprocess,tempfile,time,ctypes
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from export_adapter import load_pinned_snapshot,boundary_records,selected_regions,no_duplicates
from seed_rules import compile_rules
from region_client import execute as build_region
from closure_client import sha
BASE=Path(__file__).resolve().parent
CODE=('seed_producer.py','export_adapter.py','seed_rules.py','region_client.py','region_worker.py','regions.py','closure_client.py','guarded_exec.py','guarded_raster_exec.py')
TRUSTED_CODE={'seed_builder':'d6dd107e46024b08915e31aa2a47d8a93e0a5bb52c5d11d1ae601e71a0de2579','seed_kernel':'b8109861272d3dc0ea514575a4dc3803cf2691c76d0a77e76e4ab4bb382fccfe','closure_checker':'1d5e2a978870e05cf7f1f2c57389f65ffbc1c1a5de11056b5d5196b1a80b6f01'}
TRUSTED_TERMINAL_CHECKER='347aaa7f5414c2f3ac5826082a3b5b5c645558be1471f1ff3cc4b55eb206d8f7'
INPUTS={'snapshot','resolution','physical_rows','physical_runs','physical_report','component_rows','component_runs','component_manifest','closure_checker','closure_contract','seed_builder','seed_kernel'}
def bounded_json(pin,guard,limit=16<<20):
 h=hashlib.sha256();chunks=[];n=0
 with open(pin['path'],'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   n+=len(b)
   if n>limit:raise ValueError('JSON input exceeds bound')
   chunks.append(b);h.update(b)
 if h.hexdigest()!=pin['sha256']:raise ValueError('JSON pin mismatch')
 return json.loads(b''.join(chunks))
def group_rss_kib(pgid):
 # Sum RSS for the isolated process group; shared pages may be counted more
 # than once, intentionally conservative. Races with process exit are benign.
 total=0;pagesize=os.sysconf('SC_PAGE_SIZE')
 for name in os.listdir('/proc'):
  if not name.isdecimal():continue
  try:
   with open('/proc/'+name+'/stat') as f:s=f.read()
   fields=s[s.rfind(')')+2:].split()
   if int(fields[2])!=pgid:continue
   with open('/proc/'+name+'/statm') as f:rss_pages=int(f.read().split()[1])
   total+=rss_pages*pagesize//1024
  except (FileNotFoundError,ProcessLookupError,IndexError,ValueError):continue
 return total

def run(request_path,work_dir,output_dir,guard):
 if not callable(guard):raise ValueError('resource guard required')
 request_path=Path(request_path).resolve(strict=True);work=Path(work_dir).resolve();output=Path(output_dir).resolve();guard()
 if work.exists() or output.exists() or not work.parent.is_dir() or not output.parent.is_dir() or work==output or work in output.parents or output in work.parents:raise ValueError('invalid work/output directory')
 with open(request_path,'rb') as f:raw=f.read((1<<20)+1)
 if len(raw)>1<<20:raise ValueError('request too large')
 req=json.loads(raw,object_pairs_hook=no_duplicates);inp=req.get('inputs');grid=req.get('grid');controls=req.get('controls')
 if req.get('schema')!='worldatlas-stage2-seed-request-v1' or not isinstance(inp,dict) or set(inp) not in (INPUTS,INPUTS|{'terminal_checker'}) or not isinstance(grid,dict) or set(grid)!={'width','height','west','north','step'} or not isinstance(controls,dict) or set(controls)!={'memory_floor_kib','disk_reserve_bytes','timeout_seconds','strip_rows','max_group_rss_kib'}:raise ValueError('invalid seed request')
 if type(controls['memory_floor_kib']) is not int or controls['memory_floor_kib']<0 or type(controls['disk_reserve_bytes']) is not int or controls['disk_reserve_bytes']<0 or not 0<controls['timeout_seconds']<=3600 or type(controls['strip_rows']) is not int or not 1<=controls['strip_rows']<=64 or type(controls['max_group_rss_kib']) is not int or not 262144<=controls['max_group_rss_kib']<=786432:raise ValueError('invalid seed controls')
 external_guard=guard
 def guard():
  external_guard()
  with open('/proc/meminfo') as f:a=next(int(line.split()[1]) for line in f if line.startswith('MemAvailable:'))
  if a<controls['memory_floor_kib'] or shutil.disk_usage(work.parent).free<controls['disk_reserve_bytes']:raise RuntimeError('seed resource guard reached')
 guard()
 for key,digest in TRUSTED_CODE.items():
  if inp[key].get('sha256')!=digest:raise ValueError('unreviewed executable code')
 if 'terminal_checker' in inp and inp['terminal_checker'].get('sha256')!=TRUSTED_TERMINAL_CHECKER:raise ValueError('unreviewed terminal checker code')
 for pin in inp.values():
  if not isinstance(pin,dict) or set(pin)!={'path','sha256'} or not isinstance(pin['sha256'],str) or len(pin['sha256'])!=64 or sha(pin['path'],guard)!=pin['sha256']:raise ValueError('input pin mismatch')
 sources={Path(p['path']).resolve().parent for p in inp.values()}|{BASE,request_path.parent}
 for target in (work,output):
  if any(target==d or target in d.parents or d in target.parents for d in sources):raise ValueError('seed work/output overlaps inputs')
 if shutil.disk_usage(work.parent).free<controls['disk_reserve_bytes']:raise RuntimeError('disk reserve reached')
 snapshot=load_pinned_snapshot(inp['snapshot']['path'],inp['snapshot']['sha256'],guard);resolution=bounded_json(inp['resolution'],guard);rev,entity,boundaries,source_catalog=boundary_records(snapshot)
 if resolution.get('grid')!=grid or resolution.get('component_manifest_sha256')!=inp['component_manifest']['sha256'] or any(resolution.get('input_sha256',{}).get(k)!=inp[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')):raise ValueError('witness resolution input mismatch')
 regions,records=selected_regions(snapshot,rev,boundaries,source_catalog);rules=compile_rules(snapshot,resolution,inp['snapshot']['sha256'],[r['region_id'] for r in regions])
 report=bounded_json(inp['physical_report'],guard);outputs=report.get('physical_output_sha256',report.get('output_sha256',{}))
 if report.get('status') not in ('candidate-only','stage1-complete') or report.get('grid')!=grid or outputs.get('rows.u32le')!=inp['physical_rows']['sha256'] or outputs.get('runs.u32le')!=inp['physical_runs']['sha256']:raise ValueError('physical report mismatch')
 contract=bounded_json(inp['closure_contract'],guard);physical=contract.get('physical',{});cg=contract.get('grid',{})
 if contract.get('schema')!='physical-water-closure-contract-v1' or physical.get('rows_sha256')!=inp['physical_rows']['sha256'] or physical.get('runs_sha256')!=inp['physical_runs']['sha256'] or physical.get('report_sha256')!=inp['physical_report']['sha256'] or physical.get('water_code')!=1 or physical.get('land_code')!=17 or cg.get('crs')!='EPSG:4326' or cg.get('width')!=grid['width'] or cg.get('height')!=grid['height'] or Fraction(str(cg.get('west')))!=Fraction(str(grid['west'])) or Fraction(str(cg.get('north')))!=Fraction(str(grid['north'])) or Fraction(cg.get('step_numerator'),cg.get('step_denominator'))!=Fraction(str(grid['step'])):raise ValueError('physical contract mismatch')
 for key,record in records.items():
  if key[0]!='route':continue
  p=record['provenance'];expected={'physical_rows_sha256':inp['physical_rows']['sha256'],'physical_runs_sha256':inp['physical_runs']['sha256'],'physical_report_sha256':inp['physical_report']['sha256'],'encoding_evidence_sha256':physical.get('encoding_evidence_sha256'),'contract_sha256':inp['closure_contract']['sha256'],'support_checker_sha256':inp['closure_checker']['sha256'],'checker_sha256':inp.get('terminal_checker',{}).get('sha256') if record['closure_method']=='physical_terminal_closure_v1' else inp['closure_checker']['sha256']}
  if any(p.get(k)!=v for k,v in expected.items()):raise ValueError('route physical provenance differs from current stage-1 inputs')

 code_hashes={name:sha(BASE/name,guard) for name in CODE};code_hashes['rasterizer']=inp['seed_builder']['sha256'];code_hashes['rasterizer_kernel']=inp['seed_kernel']['sha256']
 work.mkdir(mode=0o700)
 if os.stat(work).st_dev!=os.stat(output.parent).st_dev:raise ValueError('seed output must share work filesystem')
 rinput=work/'region-input';rinput.mkdir();regionwork=work/'region-work';regionwork.mkdir();codework=work/'rasterizer-code';codework.mkdir();seedout=work/'seed-output'
 # Execute only reviewed byte-pinned rasterizer source copies.
 for key,name in (('seed_builder','build_seed.py'),('seed_kernel','seed_kernel.cpp')):
  with open(inp[key]['path'],'rb') as f:data=f.read((1<<20)+1)
  if len(data)>1<<20 or hashlib.sha256(data).hexdigest()!=inp[key]['sha256']:raise ValueError('rasterizer source mismatch')
  (codework/name).write_bytes(data)
 closure={'checker_path':inp['closure_checker']['path'],'checker_sha256':inp['closure_checker']['sha256'],'physical_dir':str(Path(inp['physical_rows']['path']).resolve().parent),'physical_rows_sha256':inp['physical_rows']['sha256'],'physical_runs_sha256':inp['physical_runs']['sha256'],'contract_path':inp['closure_contract']['path'],'contract_sha256':inp['closure_contract']['sha256'],'timeout_seconds':controls['timeout_seconds']}
 if 'terminal_checker' in inp:closure.update({'terminal_checker_path':inp['terminal_checker']['path'],'terminal_checker_sha256':inp['terminal_checker']['sha256']})
 if Path(inp['physical_runs']['path']).resolve().parent!=Path(closure['physical_dir']):raise ValueError('physical files must be colocated')
 source_list=[{'source_id':k[0],'version':k[1],**v} for k,v in source_catalog.items()];region_configs=[];region_traces=[]
 for decision in regions:
  guard();result=build_region({'schema':'stage2-region-worker-request-v1','memory_floor_kib':controls['memory_floor_kib'],'revision_id':rev,'records':list(records.values()),'sources':source_list,'decision':decision,'closure':closure},regionwork,guard,controls['timeout_seconds']);
  if any(result['code_sha256'].get(n)!=code_hashes[n] for n in ('region_worker.py','regions.py','closure_client.py','guarded_exec.py')):raise ValueError('region worker code mismatch')
  g=result['geometry'];name=hashlib.sha256(decision['region_id'].encode()).hexdigest()+'.geojson';p=rinput/name;data=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':g}]},sort_keys=True,separators=(',',':'),allow_nan=False).encode();p.write_bytes(data);region_configs.append({'id':decision['region_id'],'geometry':{'path':str(p),'sha256':hashlib.sha256(data).hexdigest()},'witnesses':[{'lon':float(w['lon']),'lat':float(w['lat']),'inside':w['inside']} for w in decision['witnesses']]});region_traces.append(result['report'])
 raster_rules=[{'component_id':r['component_id_current_generation_only'],'region_id':r['region_id'],'inside_code':r['inside_code'],'outside_code':r['outside_code']} for r in rules]
 config={'schema':'direct-region-seed-research-v1','grid':{**grid,'crs':'EPSG:4326'},'component_rows':inp['component_rows'],'component_runs':inp['component_runs'],'regions':region_configs,'rules':raster_rules,'evidence':[inp[k] for k in ('snapshot','resolution','physical_rows','physical_runs','physical_report','component_manifest','closure_checker','closure_contract')],'strip_rows':controls['strip_rows'],'reserve_bytes':controls['disk_reserve_bytes']};config_path=rinput/'seed-config.json';config_path.write_text(json.dumps(config,sort_keys=True,indent=2)+'\n')
 err=work/'rasterizer.log';peak_group_rss_kib=0
 with open(err,'w+b') as log:
  env=os.environ.copy()
  for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[k]='1'
  p=subprocess.Popen(['/usr/bin/python3',str(BASE/'guarded_raster_exec.py'),str(os.getpid()),str(codework/'build_seed.py'),str(config_path),str(seedout)],stdout=log,stderr=log,env=env);start=time.monotonic()
  try:
   while p.poll() is None:
    try:
     guard();rss=group_rss_kib(os.getpgrp());peak_group_rss_kib=max(peak_group_rss_kib,rss)
     if rss>controls['max_group_rss_kib']:raise RuntimeError('rasterizer process-group RSS limit reached')
    except BaseException:p.kill();p.wait();raise
    if time.monotonic()-start>controls['timeout_seconds']:p.kill();p.wait();raise RuntimeError('seed rasterizer timed out')
    time.sleep(.1)
   if p.returncode:log.seek(0);raise ValueError('seed rasterizer failed: '+log.read(4096).decode(errors='replace'))
  finally:
   if p.poll() is None:p.kill();p.wait()
 raster=bounded_json({'path':str(seedout/'report.json'),'sha256':sha(seedout/'report.json',guard)},guard)
 rows=sha(seedout/'rows.u32le',guard);runs=sha(seedout/'runs.u32le',guard)
 if raster.get('schema')!='direct-region-seed-research-report-v1' or raster.get('outputs_sha256')!={'rows':rows,'runs':runs} or raster.get('component_rows_sha256')!=inp['component_rows']['sha256'] or raster.get('component_runs_sha256')!=inp['component_runs']['sha256']:raise ValueError('seed rasterizer output mismatch')
 populations=raster.get('rule_population');counts=raster.get('category_cell_counts')
 if not isinstance(populations,dict) or set(populations)!={str(r['component_id_current_generation_only']) for r in rules} or not isinstance(counts,dict) or set(counts)!={str(x) for x in range(17,23)} or any(type(v) is not int or v<=0 for v in counts.values()):raise ValueError('missing mainland category population')
 for r in rules:
  pop=populations[str(r['component_id_current_generation_only'])]
  if not isinstance(pop,dict) or type(pop.get('inside_cells')) is not int or type(pop.get('outside_cells')) is not int or pop['inside_cells']<=0 or (r['region_id'] is not None and pop['outside_cells']<=0):raise ValueError('empty mainland rule partition')
 for pin in inp.values():
  if sha(pin['path'],guard)!=pin['sha256']:raise ValueError('input changed during seed build')
 with open(request_path,'rb') as f:request_after=f.read((1<<20)+1)
 if request_after!=raw or {name:sha(BASE/name,guard) for name in CODE}!={k:v for k,v in code_hashes.items() if k in CODE}:raise ValueError('request or producer code changed')
 (seedout/'report.json').rename(seedout/'rasterizer-report.json')
 rasterizer_report_sha=sha(seedout/'rasterizer-report.json',guard)
 out={'schema':'worldatlas-stage2-mainland-seed-report-v1','status':'diagnostic-seed-pending-independent-provenance','publishable':False,'grid':grid,'decision_snapshot_sha256':inp['snapshot']['sha256'],'decision_revision':rev,'entity_revision':entity,'resolution_report_sha256':inp['resolution']['sha256'],'physical_rows_sha256':inp['physical_rows']['sha256'],'physical_runs_sha256':inp['physical_runs']['sha256'],'component_rows_sha256':inp['component_rows']['sha256'],'component_runs_sha256':inp['component_runs']['sha256'],'component_manifest_sha256':inp['component_manifest']['sha256'],'physical_report_sha256':inp['physical_report']['sha256'],'physical_code_contract':{'water':1,'land':17},'input_sha256':{k:v['sha256'] for k,v in inp.items()},'rasterizer_report_sha256':rasterizer_report_sha,'resource_controls':controls,'peak_rasterizer_group_rss_kib':peak_group_rss_kib,'seed_rows_sha256':rows,'seed_runs_sha256':runs,'seed_roots':sorted(r['component_id_current_generation_only'] for r in rules),'rule_population':populations,'category_cell_counts':counts,'region_traces':region_traces,'seed_rules':rules,'code_sha256':code_hashes,'request_sha256':hashlib.sha256(raw).hexdigest(),'limitations':['Caller must authenticate the Neon export and independently re-execute witness resolution and full physical/component coverage before accepting this seed.','Witnesses support component identity but do not prove absence of unintended bridges.','Stored boundary lineage and historical V2/V7 raster equivalence may be incomplete.','Stored route proof hashes are unverified evidence references; fresh closure checks are executed separately.','No island or List 1 overrides are applied.']}
 with open(seedout/'report.json','x') as f:json.dump(out,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(seedout/'rasterizer-report.json',os.O_RDONLY);os.fsync(fd);os.close(fd);fd=os.open(seedout,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 guard();libc=ctypes.CDLL(None,use_errno=True);rc=libc.renameat2(-100,os.fsencode(seedout),-100,os.fsencode(output),1)
 if rc:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
 fd=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);return out
