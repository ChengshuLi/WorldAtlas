"""Execute a fresh simple mainland seed from selected Neon L2 decisions.

The caller authenticates the pinned Neon export and independently resolves the
current stage-1 component witnesses before invoking this producer. No historical
continent map, prior assignment checkpoint, or List 1 override is accepted.
"""
import hashlib,json,os,re,shutil,signal,tempfile,time,runpy
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from export_adapter import load_pinned_snapshot,boundary_records,selected_regions,no_duplicates
from seed_rules import compile_rules
from region_client import execute as build_region
from closure_client import sha
from atomic_move import move_noreplace,output_path
BASE=Path(__file__).resolve().parent
CODE=('seed_producer.py','export_adapter.py','seed_rules.py','region_client.py','region_worker.py','regions.py','closure_client.py')
TRUSTED_CODE={'seed_builder':'1600dc513a0889658963d3e5737f2490ba8de0f363a2910555f5b7111e87569b','seed_kernel':'d3ae7c6cada77a2c06b4b940a5478077d77d794d8596f193f19c599516d06c63','closure_checker':'1e796c7f9bc8843252398eed54093265581446c9f4cac10dcb3b4c424b6e1bd1'}
# Explicit research-only checker supporting a directly pinned producer path.
PROVISIONAL_CLOSURE_CHECKER='4491d971541fcfe7317d40abf2e8320c308d58af5c7f8115348362f0f71da327'
TRUSTED_TERMINAL_CHECKER='fb0058f368f0db8ca07d1c9347aaf1192cb5b2fc20c3691e167623531f5570f1'
PROVISIONAL_TERMINAL_CHECKER='a89a7cfc0a91983aa9babf6df72d93eb4aa3484b4ca9010c26d9f9e6abb1d473'
INPUTS={'snapshot','resolution','physical_rows','physical_runs','physical_report','component_rows','component_runs','component_manifest','closure_checker','closure_contract','seed_builder','seed_kernel'}
def validate_executable_pins(inp,allow_local):
 for key,digest in TRUSTED_CODE.items():
  allowed = {digest}
  if key == 'closure_checker' and allow_local:
   allowed.add(PROVISIONAL_CLOSURE_CHECKER)
  if inp[key].get('sha256') not in allowed:raise ValueError('unreviewed executable code')
 if 'terminal_checker' in inp and inp['terminal_checker'].get('sha256')!=TRUSTED_TERMINAL_CHECKER and not (allow_local and inp['terminal_checker'].get('sha256')==PROVISIONAL_TERMINAL_CHECKER):raise ValueError('unreviewed terminal checker code')

def validate_provisional_checker_source(inp,snapshot,allow_local):
 provisional=(inp['closure_checker'].get('sha256')==PROVISIONAL_CLOSURE_CHECKER or inp.get('terminal_checker',{}).get('sha256')==PROVISIONAL_TERMINAL_CHECKER)
 if provisional and not (allow_local and snapshot.get('source')=='local-derived-from-neon-export'):raise ValueError('provisional checker requires local provisional snapshot')

def rasterizer_sources(inp):
 directory=BASE.parents[1]/'neon-mainland-regions-20261104/rasterizer'
 expected=(directory/'build_seed.py',directory/'seed_runtime.py')
 actual=tuple(Path(inp[key]['path']).resolve(strict=True) for key in ('seed_builder','seed_kernel'))
 if actual!=tuple(path.resolve(strict=True) for path in expected):raise ValueError('checked-in rasterizer source pair required')
 return actual

def execute_rasterizer(inp,config_path,seedout,guard):
 builder,kernel=rasterizer_sources(inp)
 for key,path in (('seed_builder',builder),('seed_kernel',kernel)):
  if sha(path,guard)!=inp[key]['sha256']:raise ValueError('rasterizer source mismatch')
 result=runpy.run_path(str(builder))['build'](str(config_path),str(seedout))
 for key,path in (('seed_builder',builder),('seed_kernel',kernel)):
  if sha(path,guard)!=inp[key]['sha256']:raise ValueError('rasterizer source changed')
 return result

def bounded_json(pin,guard):
 h=hashlib.sha256();chunks=[]
 with open(pin['path'],'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   chunks.append(b);h.update(b)
 if h.hexdigest()!=pin['sha256']:raise ValueError('JSON pin mismatch')
 return json.loads(b''.join(chunks))
def run(request_path,work_dir,output_dir,guard, *, allow_local=False):
 if not callable(guard):raise ValueError('resource guard required')
 request_path=Path(request_path).resolve(strict=True);work=output_path(work_dir);output=output_path(output_dir);guard()
 if os.path.lexists(work) or os.path.lexists(output) or not work.parent.is_dir() or not output.parent.is_dir() or work==output or work in output.parents or output in work.parents:raise ValueError('invalid work/output directory')
 with open(request_path,'rb') as f:raw=f.read()
 req=json.loads(raw,object_pairs_hook=no_duplicates);inp=req.get('inputs');grid=req.get('grid');controls=req.get('controls')
 if req.get('schema')!='worldatlas-stage2-seed-request-v1' or not isinstance(inp,dict) or set(inp) not in (INPUTS,INPUTS|{'terminal_checker'},INPUTS|{'terminal_checker','prior_physical_report'}) or not isinstance(grid,dict) or set(grid)!={'width','height','west','north','step'} or not isinstance(controls,dict) or set(controls)!={'disk_reserve_bytes','strip_rows'}:raise ValueError('invalid seed request')
 if 'prior_physical_report' in inp and not allow_local:raise ValueError('prior physical report is provisional-only')
 if type(controls['disk_reserve_bytes']) is not int or controls['disk_reserve_bytes']<0  or type(controls['strip_rows']) is not int or not 1<=controls['strip_rows']<=64:raise ValueError('invalid seed controls')
 external_guard=guard
 def guard():
  external_guard()
  if shutil.disk_usage(work.parent).free<controls['disk_reserve_bytes']:raise RuntimeError('disk reserve reached')
 guard()
 validate_executable_pins(inp,allow_local)
 for pin in inp.values():
  if not isinstance(pin,dict) or set(pin)!={'path','sha256'} or not isinstance(pin['sha256'],str) or len(pin['sha256'])!=64 or sha(pin['path'],guard)!=pin['sha256']:raise ValueError('input pin mismatch')
 sources={Path(p['path']).resolve().parent for p in inp.values()}|{BASE,request_path.parent}
 for target in (work,output):
  if any(target==d or target in d.parents or d in target.parents for d in sources):raise ValueError('seed work/output overlaps inputs')
 if shutil.disk_usage(work.parent).free<controls['disk_reserve_bytes']:raise RuntimeError('disk reserve reached')
 snapshot=load_pinned_snapshot(inp['snapshot']['path'],inp['snapshot']['sha256'],guard);validate_provisional_checker_source(inp,snapshot,allow_local);resolution=bounded_json(inp['resolution'],guard);rev,entity,boundaries,source_catalog=boundary_records(snapshot,allow_local=allow_local)
 if resolution.get('grid')!=grid or resolution.get('component_manifest_sha256')!=inp['component_manifest']['sha256'] or any(resolution.get('input_sha256',{}).get(k)!=inp[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')):raise ValueError('witness resolution input mismatch')
 regions,records=selected_regions(snapshot,rev,boundaries,source_catalog);rules=compile_rules(snapshot,resolution,inp['snapshot']['sha256'],[r['region_id'] for r in regions],allow_local=allow_local)
 report=bounded_json(inp['physical_report'],guard);outputs=report.get('physical_output_sha256',report.get('output_sha256',{}))
 if report.get('status') not in ('candidate-only','stage1-complete') or report.get('grid')!=grid or outputs.get('rows.u32le')!=inp['physical_rows']['sha256'] or outputs.get('runs.u32le')!=inp['physical_runs']['sha256']:raise ValueError('physical report mismatch')
 contract=bounded_json(inp['closure_contract'],guard);physical=contract.get('physical',{});cg=contract.get('grid',{})
 if (contract.get('schema')!='physical-water-closure-contract-v1' and not (allow_local and snapshot.get('source')=='local-derived-from-neon-export' and contract.get('schema')=='physical-water-closure-contract-v2')) or physical.get('rows_sha256')!=inp['physical_rows']['sha256'] or physical.get('runs_sha256')!=inp['physical_runs']['sha256'] or physical.get('report_sha256')!=inp['physical_report']['sha256'] or physical.get('water_code')!=1 or physical.get('land_code')!=17 or cg.get('crs')!='EPSG:4326' or cg.get('width')!=grid['width'] or cg.get('height')!=grid['height'] or Fraction(str(cg.get('west')))!=Fraction(str(grid['west'])) or Fraction(str(cg.get('north')))!=Fraction(str(grid['north'])) or Fraction(cg.get('step_numerator'),cg.get('step_denominator'))!=Fraction(str(grid['step'])):raise ValueError('physical contract mismatch')
 local_candidate=allow_local and snapshot.get('source')=='local-derived-from-neon-export'
 prior=None
 if local_candidate:
  if 'prior_physical_report' not in inp:raise ValueError('local candidate requires prior physical report')
  prior=bounded_json(inp['prior_physical_report'],guard)
  prior_out=prior.get('physical_output_sha256',prior.get('output_sha256',{}))
  if prior.get('status') not in ('candidate-only','stage1-complete') or prior.get('grid')!=grid or prior_out.get('rows.u32le')!=inp['physical_rows']['sha256'] or prior_out.get('runs.u32le')!=inp['physical_runs']['sha256']:raise ValueError('prior physical streams not equivalent')
 elif 'prior_physical_report' in inp:raise ValueError('prior report requires local provisional snapshot')
 historical={}
 for key,record in records.items():
  if key[0]!='route':continue
  p=record['provenance'];expected={'physical_rows_sha256':inp['physical_rows']['sha256'],'physical_runs_sha256':inp['physical_runs']['sha256'],'physical_report_sha256':inp['physical_report']['sha256'],'encoding_evidence_sha256':physical.get('encoding_evidence_sha256'),'contract_sha256':inp['closure_contract']['sha256'],'support_checker_sha256':inp['closure_checker']['sha256'],'checker_sha256':inp.get('terminal_checker',{}).get('sha256') if record['closure_method']=='physical_terminal_closure_v1' else inp['closure_checker']['sha256']}
  if local_candidate:
   if p.get('physical_rows_sha256')!=expected['physical_rows_sha256'] or p.get('physical_runs_sha256')!=expected['physical_runs_sha256'] or p.get('physical_report_sha256')!=inp['prior_physical_report']['sha256'] or any(not isinstance(p.get(k),str) or not re.fullmatch('[0-9a-f]{64}',p[k]) for k in expected):raise ValueError('historical route physical provenance mismatch')
   historical[record['id']]=p
  elif any(p.get(k)!=v for k,v in expected.items()):raise ValueError('route physical provenance differs from current stage-1 inputs')

 code_hashes={name:sha(BASE/name,guard) for name in CODE};code_hashes['rasterizer']=inp['seed_builder']['sha256'];code_hashes['rasterizer_kernel']=inp['seed_kernel']['sha256']
 work.mkdir(mode=0o700)
 if os.stat(work).st_dev!=os.stat(output.parent).st_dev:raise ValueError('seed output must share work filesystem')
 rinput=work/'region-input';rinput.mkdir();regionwork=work/'region-work';regionwork.mkdir();seedout=work/'seed-output'
 rasterizer_sources(inp)
 closure={'checker_path':inp['closure_checker']['path'],'checker_sha256':inp['closure_checker']['sha256'],'physical_dir':str(Path(inp['physical_rows']['path']).resolve().parent),'physical_rows_sha256':inp['physical_rows']['sha256'],'physical_runs_sha256':inp['physical_runs']['sha256'],'contract_path':inp['closure_contract']['path'],'contract_sha256':inp['closure_contract']['sha256']}
 if 'terminal_checker' in inp:closure.update({'terminal_checker_path':inp['terminal_checker']['path'],'terminal_checker_sha256':inp['terminal_checker']['sha256']})
 if Path(inp['physical_runs']['path']).resolve().parent!=Path(closure['physical_dir']):raise ValueError('physical files must be colocated')
 source_list=[{'source_id':k[0],'version':k[1],**v} for k,v in source_catalog.items()];region_configs=[];region_traces=[]
 for decision in regions:
  guard();result=build_region({'schema':'stage2-region-worker-request-v1','revision_id':rev,'records':list(records.values()),'sources':source_list,'decision':decision,'closure':closure},regionwork,guard);
  if any(result['code_sha256'].get(n)!=code_hashes[n] for n in ('region_worker.py','regions.py','closure_client.py')):raise ValueError('region worker code mismatch')
  g=result['geometry'];name=hashlib.sha256(decision['region_id'].encode()).hexdigest()+'.geojson';p=rinput/name;data=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':g}]},sort_keys=True,separators=(',',':'),allow_nan=False).encode();p.write_bytes(data);region_configs.append({'id':decision['region_id'],'geometry':{'path':str(p),'sha256':hashlib.sha256(data).hexdigest()},'witnesses':[{'lon':float(w['lon']),'lat':float(w['lat']),'inside':w['inside']} for w in decision['witnesses']]});region_traces.append(result['report'])
 if local_candidate:
  route_ids=set(historical);verified=set()
  for trace in region_traces:
   for item in trace.get('input_trace',[]):
    if item.get('kind')=='route':
     proof=item.get('closure_proof',{});rid=item.get('id')
     if rid not in historical or item.get('route_provenance')!=historical[rid] or proof.get('status')!='valid' or proof.get('physical_rows_sha256')!=inp['physical_rows']['sha256'] or proof.get('physical_runs_sha256')!=inp['physical_runs']['sha256'] or proof.get('contract_sha256')!=inp['closure_contract']['sha256']:raise ValueError('fresh route reproof missing or mismatched')
     verified.add(rid)
  if verified!=route_ids:raise ValueError('not every selected route was freshly reproved')
  equivalence={'prior_report_sha256':inp['prior_physical_report']['sha256'],'current_report_sha256':inp['physical_report']['sha256'],'rows_sha256':inp['physical_rows']['sha256'],'runs_sha256':inp['physical_runs']['sha256'],'historical_route_provenance':historical,'fresh_reproof_route_ids':sorted(verified),'status':'equivalent-streams-fresh-proofs-provisional-only'}
 raster_rules=[{'component_id':r['component_id_current_generation_only'],'region_id':r['region_id'],'inside_code':r['inside_code'],'outside_code':r['outside_code']} for r in rules]
 config={'schema':'direct-region-seed-research-v1','grid':{**grid,'crs':'EPSG:4326'},'component_rows':inp['component_rows'],'component_runs':inp['component_runs'],'regions':region_configs,'rules':raster_rules,'evidence':[inp[k] for k in ('snapshot','resolution','physical_rows','physical_runs','physical_report','component_manifest','closure_checker','closure_contract')]+([inp['prior_physical_report']] if local_candidate else []),'strip_rows':controls['strip_rows'],'reserve_bytes':controls['disk_reserve_bytes']};config_path=rinput/'seed-config.json';config_path.write_text(json.dumps(config,sort_keys=True,indent=2)+'\n')
 execute_rasterizer(inp,config_path,seedout,guard)
 raster=bounded_json({'path':str(seedout/'report.json'),'sha256':sha(seedout/'report.json',guard)},guard)
 rows=sha(seedout/'rows.u32le',guard);runs=sha(seedout/'runs.u32le',guard)
 if raster.get('schema')!='direct-region-seed-research-report-v2' or raster.get('outputs_sha256')!={'rows':rows,'runs':runs} or raster.get('component_rows_sha256')!=inp['component_rows']['sha256'] or raster.get('component_runs_sha256')!=inp['component_runs']['sha256']:raise ValueError('seed rasterizer output mismatch')
 populations=raster.get('rule_population');counts=raster.get('category_cell_counts')
 if not isinstance(populations,dict) or set(populations)!={str(r['component_id_current_generation_only']) for r in rules} or not isinstance(counts,dict) or set(counts)!={str(x) for x in range(17,23)} or any(type(v) is not int or v<=0 for v in counts.values()):raise ValueError('missing mainland category population')
 for r in rules:
  pop=populations[str(r['component_id_current_generation_only'])]
  if not isinstance(pop,dict) or type(pop.get('inside_cells')) is not int or type(pop.get('outside_cells')) is not int or pop['inside_cells']<=0 or (r['region_id'] is not None and pop['outside_cells']<=0):raise ValueError('empty mainland rule partition')
 for pin in inp.values():
  if sha(pin['path'],guard)!=pin['sha256']:raise ValueError('input changed during seed build')
 with open(request_path,'rb') as f:request_after=f.read()
 if request_after!=raw or {name:sha(BASE/name,guard) for name in CODE}!={k:v for k,v in code_hashes.items() if k in CODE}:raise ValueError('request or producer code changed')
 (seedout/'report.json').rename(seedout/'rasterizer-report.json')
 rasterizer_report_sha=sha(seedout/'rasterizer-report.json',guard)
 out={'schema':'worldatlas-stage2-mainland-seed-report-v1','status':'diagnostic-seed-pending-independent-provenance','publishable':False,'grid':grid,'decision_snapshot_sha256':inp['snapshot']['sha256'],'decision_revision':rev,'entity_revision':entity,'resolution_report_sha256':inp['resolution']['sha256'],'physical_rows_sha256':inp['physical_rows']['sha256'],'physical_runs_sha256':inp['physical_runs']['sha256'],'component_rows_sha256':inp['component_rows']['sha256'],'component_runs_sha256':inp['component_runs']['sha256'],'component_manifest_sha256':inp['component_manifest']['sha256'],'physical_report_sha256':inp['physical_report']['sha256'],'physical_code_contract':{'water':1,'land':17},'input_sha256':{k:v['sha256'] for k,v in inp.items()},'rasterizer_report_sha256':rasterizer_report_sha,'resource_controls':controls,'seed_rows_sha256':rows,'seed_runs_sha256':runs,'seed_roots':sorted(r['component_id_current_generation_only'] for r in rules),'rule_population':populations,'category_cell_counts':counts,'region_traces':region_traces,'seed_rules':rules,'code_sha256':code_hashes,'request_sha256':hashlib.sha256(raw).hexdigest(),'limitations':['Caller must authenticate the source snapshot and independently re-execute witness resolution and full physical/component coverage; a local-derived snapshot is provisional only.','Witnesses support component identity but do not prove absence of unintended bridges.','Stored boundary lineage and historical V2/V7 raster equivalence may be incomplete.','Stored route proof hashes are unverified evidence references; fresh closure checks are executed separately.','No island or List 1 overrides are applied.']}
 if local_candidate:out['provisional_physical_equivalence']=equivalence
 with open(seedout/'report.json','x') as f:json.dump(out,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(seedout/'rasterizer-report.json',os.O_RDONLY);os.fsync(fd);os.close(fd);fd=os.open(seedout,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 guard();move_noreplace(seedout,output)
 fd=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);return out
