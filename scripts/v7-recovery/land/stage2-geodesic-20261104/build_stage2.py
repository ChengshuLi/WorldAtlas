#!/usr/bin/env /usr/bin/python3
"""Fresh-source WGS84 stage-2 land build; no historical checkpoint input.

Research-only: selected seed/region provenance and topology must be authenticated
independently. Hints are performance suggestions, never final assignments.
"""
import argparse,hashlib,importlib.util,json,os,resource,subprocess,time,uuid
from pathlib import Path
import numpy as np,pyproj,scipy
import atomic_move,baseline_runner,checkpoints,contracts,engine,preflight,verify_inputs,verify_physical_lineage,ural_delta
from certificate import CertificateIndex
from exact_index import ExactIndex
from write_land_stream import write_land_stream

HERE=Path(__file__).resolve().parent
CODE_NAMES=('build_stage2.py','contracts.py','atomic_move.py','baseline_runner.py','certificate.py','checkpoints.py','engine.py','exact_index.py','point_prototype.py','preflight.py','run_pair.py','verify_inputs.py','verify_physical_lineage.py','verify_seed_index.cpp','write_land_stream.py','ural_delta.py','v7-land/mainland-witness-prototype/resolve_mainland.py','v7-land/point-component-prototype/resolve.py','v7-land/named-identity-prototype/named_identity.py')
INPUTS={'decision_snapshot','physical_rows','physical_runs','physical_report','component_rows','component_runs','component_manifest','component_source','component_builder_binary','physical_lineage_request','resolution_request','resolution_report','seed_rows','seed_runs','seed_report','hint_roots','hint_codes','hint_report','tile_manifest','representatives'}

def need(x,msg):
 if not x:raise ValueError(msg)
def read_bytes(path,guard=lambda:None):
 chunks=[]
 with open(path,'rb') as f:
  while True:
   guard();block=f.read(1<<20)
   if not block:break
   chunks.append(block)
 return b''.join(chunks)
def read_json(path,guard):return json.loads(read_bytes(path,guard))
def representative_byte_limit(tile_count):return tile_count*6*32*20
def pin(spec,guard):
 need(isinstance(spec,dict) and set(spec)=={'path','sha256'} and isinstance(spec['path'],str) and isinstance(spec['sha256'],str) and contracts.HEX.fullmatch(spec['sha256']),'invalid file pin')
 p=Path(spec['path']).resolve();need(p.is_file() and verify_inputs.sha_file(p,guard)==spec['sha256'],'input hash mismatch: '+str(p));return p

def validate_controls(c):
 keys={'minimum_free_bytes','chunk_columns','checkpoint_seconds','numerical_guard_metres','block_records'}
 need(isinstance(c,dict) and set(c)==keys and type(c['minimum_free_bytes']) is int and c['minimum_free_bytes']>0 and type(c['chunk_columns']) is int and 1<=c['chunk_columns']<=1024 and type(c['block_records']) is int and 1<=c['block_records']<=100000 and type(c['checkpoint_seconds']) in (int,float) and 0<c['checkpoint_seconds']<=3600 and type(c['numerical_guard_metres']) in (int,float) and c['numerical_guard_metres']>=1000,'invalid resource/algorithm controls')

def disjoint(cfg,config_path,work,output):
 specs=list(cfg['inputs'].values())+list(cfg['seed_code_files'].values())+list(cfg['resolution_code_files'].values())+list(cfg['hint_code_files'].values())+[cfg['orchestration']['derived_manifest'],cfg['orchestration']['physical_lineage_report']]
 dirs={Path(x['path']).resolve().parent for x in specs}|{HERE,config_path.parent,Path(cfg['tile_directory']).resolve()}
 for t in (work,output):need(all(not t.is_relative_to(d) and not d.is_relative_to(t) for d in dirs),'work/output overlaps input or code')
 need(all(not (work.parent/(work.name+'.lock')).is_relative_to(d) for d in dirs),'lock overlaps input')

def load_config(path):
 raw=read_bytes(path);cfg=json.loads(raw)
 keys={'schema','grid','inputs','seed_code_files','resolution_code_files','hint_code_files','tile_directory','policy_id','policy_version','controls','orchestration'}
 need(set(cfg)==keys and cfg['schema']=='stage2-source-geodesic-v1' and isinstance(cfg['inputs'],dict) and set(cfg['inputs']) in (INPUTS,INPUTS|{'prior_physical_report'}),'invalid stage-2 config or unsupported historical inputs')
 for k in ('seed_code_files','resolution_code_files','hint_code_files'):need(isinstance(cfg[k],dict) and bool(cfg[k]) and all(isinstance(x,str) and x and '/' not in x for x in cfg[k]),'invalid code file pins')
 need(set(cfg['hint_code_files'])=={'hints.py','run_diagnostic.py'} and isinstance(cfg['tile_directory'],str) and isinstance(cfg['policy_id'],str) and cfg['policy_id'] and isinstance(cfg['policy_version'],str) and cfg['policy_version'],'invalid hint code or policy')
 o=cfg['orchestration'];need(isinstance(o,dict) and set(o)=={'outer_config_sha256','orchestrator_sha256','derived_manifest','physical_lineage_report','provisional_only'} and type(o.get('provisional_only')) is bool and all(isinstance(o.get(k),str) and contracts.HEX.fullmatch(o[k]) for k in ('outer_config_sha256','orchestrator_sha256')),'missing fresh-orchestration provenance')
 need('prior_physical_report' not in cfg['inputs'] or o['provisional_only'],'prior physical report is provisional-only');validate_controls(cfg['controls']);return raw,cfg

def build(config_path,work_dir,output_dir,resume=False,processing_started=None,orchestration_resumed=False):
 cp=Path(config_path).resolve();work=Path(work_dir).resolve();output=Path(output_dir).resolve();need(work.parent.is_dir() and output.parent.is_dir() and work!=output and not work.is_relative_to(output) and not output.is_relative_to(work),'invalid work/output')
 raw,cfg=load_config(cp);disjoint(cfg,cp,work,output)
 with checkpoints.exclusive_lock(work.parent/(work.name+'.lock')):
  return _build(cp,work,output,resume,raw,cfg,processing_started,orchestration_resumed)

def validate_resume_checkpoint(work,resume):
 if resume:need((work/'checkpoint.npz').is_file(),'partial core work has no checkpoint; inspect before retry')

def _build(cp,work,output,resume,raw,cfg,processing_started=None,orchestration_resumed=False):
 validate_resume_checkpoint(work,resume)
 start=time.monotonic();ctrl=cfg['controls'];guard=lambda:checkpoints.guard(work.parent,ctrl['minimum_free_bytes']);guard()
 need(not output.exists() and (work.is_dir() if resume else not work.exists()),'output exists or invalid resume work')
 inp=cfg['inputs'];paths={k:pin(v,guard) for k,v in inp.items()};pins={k:v['sha256'] for k,v in inp.items()}
 code_files={}
 for field in ('seed_code_files','resolution_code_files','hint_code_files'):
  code_files[field]={name:pin(v,guard) for name,v in cfg[field].items()}
 derived_path=pin(cfg['orchestration']['derived_manifest'],guard);derived=read_json(derived_path,guard);need(derived.get('schema')=='stage2-fresh-derived-v1' and derived.get('outer_config_sha256')==cfg['orchestration']['outer_config_sha256'] and derived.get('orchestrator_sha256')==cfg['orchestration']['orchestrator_sha256'] and derived.get('provisional_only') is cfg['orchestration']['provisional_only'] and all(derived.get('artifacts',{}).get(k)==inp[k] for k in ('resolution_report','seed_rows','seed_runs','seed_report','hint_roots','hint_codes','hint_report','tile_manifest','representatives')),'derived manifest mismatch');disjoint(cfg,cp,work,output)
 lineage_path=pin(cfg['orchestration']['physical_lineage_report'],guard);lineage=verify_physical_lineage.validate_combined(read_json(paths['decision_snapshot'],guard),pins['decision_snapshot'],paths['physical_lineage_request'],pins['physical_report'],pins['physical_rows'],pins['physical_runs'],cfg['grid'],guard);need(read_json(lineage_path,guard)==lineage,'physical lineage report mismatch')
 if not resume:work.mkdir(mode=0o700)
 need(os.stat(work).st_dev==os.stat(output.parent).st_dev,'atomic output requires same filesystem')
 code={n:verify_inputs.sha_file(HERE/n,guard) for n in CODE_NAMES};source_code={field:{n:cfg[field][n]['sha256'] for n in cfg[field]} for field in code_files}
 request={'schema':'stage2-source-geodesic-work-v1','config_sha256':hashlib.sha256(raw).hexdigest(),'input_sha256':pins,'code_sha256':code,'dependency_sha256':source_code,'runtime':{'numpy':np.__version__,'scipy':scipy.__version__,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str},'output_path':str(output)}
 rp=work/'request.json'
 if resume:need(rp.is_file() and read_json(rp,guard)==request,'work request mismatch; historic checkpoints are not accepted')
 else:
  with open(rp,'x') as f:json.dump(request,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  fd=os.open(work,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 g=cfg['grid'];need(isinstance(g,dict) and set(g)=={'width','height','west','north','step'} and type(g['width']) is int and type(g['height']) is int and g['width']>1 and g['height']>0 and g['west']==-180 and g['north']==90 and type(g['step']) in (int,float) and g['step']==360/g['width'] and 90-g['height']*g['step']>=-90-1e-8,'invalid global grid');w,h=g['width'],g['height']
 snap=read_json(paths['decision_snapshot'],guard);rev=snap.get('decision_revision',{}).get('id');ent=snap.get('entity_revision',{}).get('id');metric,categories,entity_codes=contracts.snap_policy(snap,rev,ent,cfg['policy_id'],cfg['policy_version'],allow_local=cfg['orchestration']['provisional_only']);need(snap.get('source')!='local-derived-from-neon-export' or (cfg['orchestration']['provisional_only'] and 'prior_physical_report' in paths),'local candidate requires provisional prior report')
 manifest=read_json(paths['component_manifest'],guard);contracts.component_manifest(manifest,g,pins)
 physical=read_json(paths['physical_report'],guard);po=physical.get('physical_output_sha256',physical.get('output_sha256',{}));need(physical.get('status') in ('candidate-only','stage1-complete') and physical.get('grid')==g and po.get('rows.u32le')==pins['physical_rows'] and po.get('runs.u32le')==pins['physical_runs'],'physical report mismatch')
 resolution=read_json(paths['resolution_report'],guard);groups=contracts.resolution_roots(resolution,g,pins,rev,ent);need(resolution.get('code_sha256')==source_code['resolution_code_files'],'resolution code provenance mismatch')
 expected_resolver={'resolver':code['v7-land/mainland-witness-prototype/resolve_mainland.py'],'helper':code['v7-land/point-component-prototype/resolve.py'],'named_identity':code['v7-land/named-identity-prototype/named_identity.py']}
 need(source_code['resolution_code_files']==expected_resolver,'unreviewed resolver implementation')
 rr=read_json(paths['resolution_request'],guard);need(rr.get('schema')=='mainland-witness-request-v1' and rr.get('grid')==g and rr.get('code_sha256')==expected_resolver,'resolution request mismatch')
 for rk,ik in (('snapshot','decision_snapshot'),('component_manifest','component_manifest'),('component_source','component_source'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('component_rows','component_rows'),('component_runs','component_runs')):need(rr.get(rk,{}).get('sha256')==pins[ik],'resolution request input mismatch: '+rk)
 extra=[Path(x['path']).resolve() for x in rr.get('source_files',[])]
 need(extra and all(not t.is_relative_to(p.parent) and not p.parent.is_relative_to(t) for p in extra for t in (work,output)),'resolution source/work overlap')
 spec=importlib.util.spec_from_file_location('stage2_mainland_witness',HERE/'v7-land/mainland-witness-prototype/resolve_mainland.py');resolver=importlib.util.module_from_spec(spec);spec.loader.exec_module(resolver)
 fresh=resolver.resolve(rr,allow_local=True) if cfg['orchestration']['provisional_only'] else resolver.resolve(rr);fresh['request_sha256']=pins['resolution_request'];need(fresh==resolution,'fresh witness re-resolution differs from consumed report')
 seed=read_json(paths['seed_report'],guard);seed_roots=contracts.seed_report(seed,g,pins,rev,ent,groups,entity_codes,source_code['seed_code_files'])
 equivalent=False
 if snap.get('source')=='local-derived-from-neon-export':equivalent=contracts.provisional_reproof(snap,seed,pins,read_json(paths['prior_physical_report'],guard),g)
 hint=read_json(paths['hint_report'],guard);count=contracts.hints_report(hint,g,pins,rev,ent,metric,seed_roots,source_code['hint_code_files'])
 # The exact snapshot rules/region trace and land-policy crosswalk is still
 # validated by a required separate contract routine, never inferred from V7.
 land_policy=contracts.validate_selected_seed_decisions(snap,seed,groups,entity_codes,metric,guard=guard,provisional_equivalence=equivalent)
 ural_rule=ural_delta.compile_rule(snap,categories,g)
 tolerance=contracts.policy_tolerance_metres(land_policy)
 need(paths['hint_roots'].stat().st_size==count*4 and paths['hint_codes'].stat().st_size==count,'hint array size mismatch')
 roots=np.frombuffer(verify_inputs.bounded_bytes(paths['hint_roots'],count*4,guard),dtype='<u4').copy();hints=np.frombuffer(verify_inputs.bounded_bytes(paths['hint_codes'],count,guard),dtype='u1').copy()
 need(len(roots)==count and len(hints)==count and np.all(roots[1:]>roots[:-1]) and np.all(np.isin(hints,list(categories))),'invalid fresh root/hint arrays')
 # Verify every tile byte against the current selected seed with a freshly built verifier.
 src=HERE/'verify_seed_index.cpp';src_bytes=read_bytes(src,guard);need(hashlib.sha256(src_bytes).hexdigest()==code[src.name],'verifier changed')
 builddir=work/('verifier-build-'+uuid.uuid4().hex);builddir.mkdir();copy=builddir/src.name;copy.write_bytes(src_bytes);binary=builddir/'verifier'
 subprocess.run(['g++','-O3','-std=c++17','-Wall','-Wextra','-Werror',str(copy),'-lcrypto','-o',str(binary)],check=True)
 need(verify_inputs.sha_file(src,guard)==code[src.name] and verify_inputs.sha_file(copy,guard)==code[src.name],'verifier changed during compilation');guard()
 v=subprocess.run([str(binary),str(paths['seed_rows']),str(paths['seed_runs']),cfg['tile_directory'],str(w),str(h),'1024'],check=True,capture_output=True,text=True);tilecheck=json.loads(v.stdout);need(tilecheck.get('status')=='verified','seed/tile verification failed')
 spec=verify_inputs.manifest(paths['tile_manifest'],w,h,1024,guard);rep_bytes=verify_inputs.bounded_bytes(paths['representatives'],representative_byte_limit(len(spec)),guard);rep=np.frombuffer(rep_bytes,dtype='<u4');need(len(rep)%5==0,'invalid representative shape');rep=rep.reshape(-1,5)
 tiles=verify_inputs.verify_representatives(cfg['tile_directory'],paths['tile_manifest'],rep,w,h,guard=guard);need(len(tiles)==tilecheck['tiles'],'tile set mismatch')
 run_count=paths['component_runs'].stat().st_size//12;co=engine.offsets(paths['component_rows'],h,run_count)
 coverage=preflight.validate(w,h,paths['component_rows'],paths['component_runs'],paths['physical_rows'],paths['physical_runs'],paths['seed_rows'],paths['seed_runs'],roots,seed_roots,required_codes=categories.keys(),guard=guard,seed_rules=seed['seed_rules'],expected_rule_population=seed['rule_population'],expected_category_counts=seed['category_cell_counts'])
 identity={'schema':'stage2-source-geodesic-checkpoint-identity-v1','request':request,'verifier_binary_sha256':verify_inputs.sha_file(binary,guard)}
 cert=CertificateIndex(w,h,g['step'],g['north'],[(ty,tx,codes) for ty,tx,codes,n,sha in tiles],rep[:,2:5],tile_cells=1024,numerical_guard_m=ctrl['numerical_guard_metres']);exact=ExactIndex(cfg['tile_directory'],w,h,g['step'],g['north'],tiles,tile_cells=1024,guard_m=ctrl['numerical_guard_metres'])
 def progress(phase,cursor,queries):
  event={'schema':'stage2-source-geodesic-progress-v1','phase':phase,'component_run_cursor':cursor,'component_runs':run_count,'queries':queries,'elapsed_seconds':time.monotonic()-start}
  with open(work/'progress.jsonl','a') as f:f.write(json.dumps(event,separators=(',',':'))+'\n');f.flush()
 result=baseline_runner.run(paths['component_runs'],co,roots,hints,seed_roots,w,cert,exact,work/'checkpoint.npz',identity,resume=resume,chunk=ctrl['chunk_columns'],tolerance=tolerance,disk_floor_bytes=ctrl['minimum_free_bytes'],checkpoint_seconds=ctrl['checkpoint_seconds'],block_records=ctrl['block_records'],guard=guard,progress=progress)
 tag=uuid.uuid4().hex;rootpath=work/('roots-'+tag+'.u32le');codepath=work/('codes-'+tag+'.u8');result['roots'].astype('<u4').tofile(rootpath);result['codes'].astype('u1').tofile(codepath);partial=work/('final-'+tag+'.partial')
 writer=write_land_stream(w,h,paths['component_rows'],paths['component_runs'],paths['physical_rows'],paths['physical_runs'],paths['seed_rows'],paths['seed_runs'],rootpath,codepath,seed_roots,partial,disk_reserve_bytes=ctrl['minimum_free_bytes'],delta_rule=ural_rule);need(writer['land_cells']==coverage['land_cells'],'output land coverage mismatch')
 for v in inp.values():pin(v,guard)
 for field in code_files:
  for v in cfg[field].values():pin(v,guard)
 pin(cfg['orchestration']['derived_manifest'],guard);pin(cfg['orchestration']['physical_lineage_report'],guard);need(verify_physical_lineage.validate_combined(read_json(paths['decision_snapshot'],guard),pins['decision_snapshot'],paths['physical_lineage_request'],pins['physical_report'],pins['physical_rows'],pins['physical_runs'],cfg['grid'],guard)==lineage,'physical lineage changed');need(read_bytes(cp,guard)==raw and {n:verify_inputs.sha_file(HERE/n,guard) for n in CODE_NAMES}==code,'input or code changed')
 v=subprocess.run([str(binary),str(paths['seed_rows']),str(paths['seed_runs']),cfg['tile_directory'],str(w),str(h),'1024'],check=True,capture_output=True,text=True);need(json.loads(v.stdout).get('status')=='verified','seed/tile recheck failed')
 os.replace(partial/'report.json',partial/'writer-report.json')
 provisional=cfg['orchestration']['provisional_only']
 report={'schema':'stage2-source-geodesic-report-v1','status':'stage2-provisional-only' if provisional else 'stage2-research-complete','publishable':False,'provisional_only':provisional,'orchestration':cfg['orchestration'],'config_sha256':hashlib.sha256(raw).hexdigest(),'grid':g,'decision_snapshot_sha256':pins['decision_snapshot'],'decision_revision':rev,'entity_revision':ent,'distance_policy':metric,'land_baseline_policy':land_policy,'ural_delta':writer['ural_delta'],'seed_report_sha256':pins['seed_report'],'resolution_report_sha256':pins['resolution_report'],'hint_report_sha256':pins['hint_report'],'inputs_sha256':pins,'categories':categories,'code_sha256':code,'dependency_sha256':source_code,'runtime':request['runtime'],'physical_coverage':coverage,'physical_lineage_report_sha256':cfg['orchestration']['physical_lineage_report']['sha256'],'physical_lineage_status':lineage['status'],'tile_verification':tilecheck,'certified_components':result['certified_count'],'exact_search_components':result['exact_count'],'exact_queries':result['exact_queries'],'ties':result['ties'],'checkpoint_sha256':verify_inputs.sha_file(work/'checkpoint.npz',guard),'output_rows_sha256':writer['rows_sha256'],'output_runs_sha256':writer['runs_sha256'],'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'method':'WGS84 ellipsoidal minimum over physical component and selected mainland cell centers; bounded Ural delta land cells are overridden by cell-center side of the selected Ural divider; no other island overrides or water assignment','limitations':['Research only; selected source and component provenance require independent authentication.','The numerical bound guard is tested but not a formal proof for all floating-point operations.','Source-only hints are performance suggestions and never accepted without certificate or exact search.','The Ural delta override is limited to its recorded scope and snapshot geometry; the Caspian closure proof must be current for any later global snapshot.']}

 report['processing_elapsed_seconds']=time.monotonic()-(processing_started if processing_started is not None else start)
 report['processing_elapsed_scope']='resumed invocation only; prior work not measured' if resume or orchestration_resumed else ('fresh orchestration invocation' if processing_started is not None else 'core invocation only')
 with open(partial/'report.json','x') as f:json.dump(report,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 guard();fd=os.open(partial,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 atomic_move.move_noreplace(partial,output)
 try:
  fd=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 except OSError as exc:
  raise RuntimeError('output rename occurred; durability uncertain, inspect before retry') from exc
 return report

if __name__=='__main__':
 raise SystemExit('use orchestrate_stage2.py directly to build a fresh stage-2 candidate')
