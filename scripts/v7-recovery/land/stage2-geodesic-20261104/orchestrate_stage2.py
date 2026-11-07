#!/usr/bin/env python3
"""Direct stage 2 fresh-source orchestration.

All seed, resolution and hint products are generated from the pinned inputs in
this invocation. No historical assignment or checkpoint is accepted. Outputs
remain research-only.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
import build_seed_tiles,build_stage2,checkpoints,contracts,verify_inputs
import representatives,verify_physical_lineage

HERE=Path(__file__).resolve().parent
BASE_INPUTS={'decision_snapshot','physical_rows','physical_runs','physical_report','component_rows','component_runs','component_manifest','component_source','component_builder_binary','physical_lineage_request','resolution_request','closure_checker','terminal_checker','closure_contract','seed_builder','seed_kernel'}
SEED_NAMES=('seed_worker.py','seed_producer.py','export_adapter.py','seed_rules.py','region_client.py','region_worker.py','regions.py','closure_client.py')
# The launcher is pinned in the orchestration identity, while the producer's
# own report binds the actual producer modules and rasterizer separately.
SEED_REPORT_NAMES=tuple(n for n in SEED_NAMES if n!='seed_worker.py')
HINT_NAMES=('hints.py','run_diagnostic.py')
# Historical seed producer pins, retained to reject the modified direct-run
# implementation until a fresh independent review explicitly installs it.
REVIEWED_SEED_FREEZE={'seed_producer.py': '5a1eb9d9ba14ed7a7ecd2dd9d9f0deba00262f7e9b26b52c56e745690d248306', 'export_adapter.py': '2ade004c620acccb52ab70d1702f08a760c91f3a78328c97f5610111cbd0f598', 'seed_rules.py': '0e98f77341b8f297b434d46250f2e8e9f615e6a3764cad176fe3cdf40c52f342', 'region_client.py': '9f5c51269abe890ba2db71c8ea91c600f002ea2f1fb6331739c0d84cb5dbc795', 'region_worker.py': 'c4db765b5c2d89ccd715e5c659dc46b7355a4e23843fb4c146d7237f66539fbe', 'regions.py': '7a4e47a3c8e8bd21c72a8aa5a318e043df784e642943c0fe00c229625b581f22', 'closure_client.py': '9e5439bdfaf4228ca01a4e3d533c8436c4afc6e5e0a29e65fd0c28fdd3c80dbf'}
SEED_FREEZE_CURRENT=False  # New direct-run producer implementation needs a new independent freeze review.
SELECTED_POLICY_CROSSWALK_READY=True

def need(v,msg):
 if not v:raise ValueError(msg)
def pin(path,guard):
 p=Path(path).resolve(strict=True);return {'path':str(p),'sha256':verify_inputs.sha_file(p,guard)}
def write_json(path,obj):
 data=(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 created=False
 try:
  with open(path,'xb') as f:created=True;f.write(data);f.flush();os.fsync(f.fileno())
  fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 except OSError as exc:
  if created:raise RuntimeError('orchestration file may exist; durability uncertain, inspect before retry') from exc
  raise
 return hashlib.sha256(data).hexdigest()
def code_hashes(guard):
 names=['orchestrate_stage2.py','representatives.py','build_seed_tiles.py']+[f'seed-producer/{x}' for x in SEED_NAMES]+[f'hint-producer/{x}' for x in HINT_NAMES]+list(build_stage2.CODE_NAMES)
 return {n:verify_inputs.sha_file(HERE/n,guard) for n in names}
def load_config(path):
 raw=build_stage2.read_bytes(path);obj=json.loads(raw)
 keys={'schema','grid','inputs','policy_id','policy_version','controls','seed_controls'}
 need(isinstance(obj,dict) and set(obj)==keys and obj['schema']=='stage2-fresh-orchestration-v1' and isinstance(obj['inputs'],dict) and set(obj['inputs']) in (BASE_INPUTS,BASE_INPUTS|{'prior_physical_report'}),'invalid fresh orchestration config or historical input')
 build_stage2.validate_controls(obj['controls'])
 s=obj['seed_controls'];need(isinstance(s,dict) and set(s)=={'strip_rows'} and type(s['strip_rows']) is int and 1<=s['strip_rows']<=64,'invalid seed controls')
 need(all(isinstance(obj[k],str) and obj[k] for k in ('policy_id','policy_version')),'invalid policy controls')
 return raw,obj

def run(config_path,work_dir,output_dir,resume=False,provisional_only=False):
 processing_started=time.monotonic()
 cp,work,out=map(lambda p:Path(p).resolve(),(config_path,work_dir,output_dir));raw,cfg=load_config(cp);c=cfg['controls']
 need('prior_physical_report' not in cfg['inputs'] or provisional_only,'prior physical report is provisional-only')
 need(work.parent.is_dir() and out.parent.is_dir() and work!=out and not work.is_relative_to(out) and not out.is_relative_to(work),'invalid work/output')
 guard=lambda:checkpoints.guard(work.parent,c['minimum_free_bytes']);guard()
 paths={k:build_stage2.pin(v,guard) for k,v in cfg['inputs'].items()}
 for p in [cp,HERE,*paths.values()]:
  d=p if p==HERE else p.parent
  need(all(not t.is_relative_to(d) and not d.is_relative_to(t) for t in (work,out)),'work/output overlaps code or input')
 code=code_hashes(guard);seed_code={n:code['seed-producer/'+n] for n in SEED_NAMES}
 if provisional_only:
  # This path is only for isolated profiling. The distinct names flow into the
  # work identity and final report, which the candidate validator rejects.
  need(work.name.endswith('-provisional-only') and out.name.endswith('-provisional-only'),
       'provisional run requires separate *-provisional-only work and output paths')
 else:
  need(SEED_FREEZE_CURRENT and REVIEWED_SEED_FREEZE is not None and seed_code==REVIEWED_SEED_FREEZE,'current reviewed seed producer freeze not installed')
 need(SELECTED_POLICY_CROSSWALK_READY,'selected land-policy crosswalk not yet implemented')
 grid=cfg['grid'];need(isinstance(grid,dict) and set(grid)=={'width','height','west','north','step'} and type(grid['width']) is int and type(grid['height']) is int and 1<grid['width']<=0xffffffff and 0<grid['height']<=0xffffffff and grid['west']==-180 and grid['north']==90 and grid['step']==360/grid['width'] and 90-grid['height']*grid['step']>=-90-1e-8,'invalid global grid')
 closure_contract=json.loads(build_stage2.read_bytes(paths['closure_contract'],guard));need((closure_contract.get('schema')=='physical-water-closure-contract-v1' or (provisional_only and closure_contract.get('schema')=='physical-water-closure-contract-v2')) and closure_contract.get('physical',{}).get('rows_sha256')==cfg['inputs']['physical_rows']['sha256'] and closure_contract.get('physical',{}).get('runs_sha256')==cfg['inputs']['physical_runs']['sha256'] and closure_contract.get('physical',{}).get('report_sha256')==cfg['inputs']['physical_report']['sha256'],'physical closure contract/input mismatch')
 snapshot=json.loads(build_stage2.read_bytes(paths['decision_snapshot'],guard));need(snapshot.get('source')!='local-derived-from-neon-export' or (provisional_only and 'prior_physical_report' in paths),'local candidate requires provisional prior report');rev=snapshot.get('decision_revision',{}).get('id');entity=snapshot.get('entity_revision',{}).get('id');contracts.snap_policy(snapshot,rev,entity,cfg['policy_id'],cfg['policy_version'],allow_local=provisional_only)
 pins={k:v['sha256'] for k,v in cfg['inputs'].items()};lineage=verify_physical_lineage.validate_combined(snapshot,pins['decision_snapshot'],paths['physical_lineage_request'],pins['physical_report'],pins['physical_rows'],pins['physical_runs'],cfg['grid'],guard);manifest=json.loads(build_stage2.read_bytes(paths['component_manifest'],guard));contracts.component_manifest(manifest,grid,pins)
 physical=json.loads(build_stage2.read_bytes(paths['physical_report'],guard));po=physical.get('physical_output_sha256',physical.get('output_sha256',{}));need(physical.get('status') in ('candidate-only','stage1-complete') and physical.get('grid')==grid and po.get('rows.u32le')==pins['physical_rows'] and po.get('runs.u32le')==pins['physical_runs'],'physical report mismatch')
 rr=json.loads(build_stage2.read_bytes(paths['resolution_request'],guard));rnames={'resolver':'v7-land/mainland-witness-prototype/resolve_mainland.py','helper':'v7-land/point-component-prototype/resolve.py','named_identity':'v7-land/named-identity-prototype/named_identity.py'}
 need(rr.get('schema')=='mainland-witness-request-v1' and rr.get('grid')==grid and rr.get('code_sha256')=={k:code[v] for k,v in rnames.items()},'resolution request/code mismatch')
 for rk,ik in (('snapshot','decision_snapshot'),('component_manifest','component_manifest'),('component_source','component_source'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('component_rows','component_rows'),('component_runs','component_runs')):need(rr.get(rk,{}).get('sha256')==pins[ik],'resolution request pin mismatch: '+rk)
 identity={'schema':'stage2-fresh-work-v1','config_sha256':hashlib.sha256(raw).hexdigest(),'input_sha256':{k:v['sha256'] for k,v in cfg['inputs'].items()},'code_sha256':code,'output_path':str(out),'provisional_only':provisional_only}
 need(not out.exists(),'output already exists')
 if resume:
  need(work.is_dir() and json.loads(build_stage2.read_bytes(work/'identity.json',guard))==identity,'resume identity mismatch')
  return finish_from_marker(cfg,raw,work,out,code,guard,True,provisional_only,processing_started)
 need(not work.exists(),'fresh work already exists')
 work.mkdir(mode=0o700)
 try:
  fd=os.open(work.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 except OSError as exc:raise RuntimeError('work directory may exist; durability uncertain, inspect before retry') from exc
 for name in ('resolution','requests','seed-work-parent','tiles-parent','reps','hints-parent','core-requests','derived','lineage'):(work/name).mkdir(mode=0o700)
 write_json(work/'identity.json',identity);write_json(work/'lineage'/'report.json',lineage)
 rr=paths['resolution_request'];rout=work/'resolution'/'report.json'
 subprocess.run([sys.executable,str(HERE/'v7-land/mainland-witness-prototype/resolve_mainland.py'),str(rr),str(rout)]+(['--allow-local-provisional'] if provisional_only else []),check=True)
 resolution=json.loads(build_stage2.read_bytes(rout,guard));snapshot=json.loads(build_stage2.read_bytes(paths['decision_snapshot'],guard));need(snapshot.get('source')!='local-derived-from-neon-export' or (provisional_only and 'prior_physical_report' in paths),'local candidate requires provisional prior report');rev=snapshot['decision_revision']['id'];entity=snapshot['entity_revision']['id'];metric,categories,_=contracts.snap_policy(snapshot,rev,entity,cfg['policy_id'],cfg['policy_version'],allow_local=provisional_only)
 rp=pin(rout,guard);si={}
 for dst,src in (('snapshot','decision_snapshot'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('physical_report','physical_report'),('component_rows','component_rows'),('component_runs','component_runs'),('component_manifest','component_manifest'),('closure_checker','closure_checker'),('terminal_checker','terminal_checker'),('closure_contract','closure_contract'),('seed_builder','seed_builder'),('seed_kernel','seed_kernel')):si[dst]=cfg['inputs'][src]
 if 'prior_physical_report' in cfg['inputs']:si['prior_physical_report']=cfg['inputs']['prior_physical_report']
 seedrequest=work/'requests'/'seed.json';seedwork=work/'seed-work-parent'/'build';seedout=work/'seed-work-parent'/'output'
 sr={'schema':'worldatlas-stage2-seed-request-v1','grid':cfg['grid'],'inputs':si,'controls':{'disk_reserve_bytes':c['minimum_free_bytes'],**cfg['seed_controls']}};si['resolution']=rp;sr['inputs']=si;write_json(seedrequest,sr)
 subprocess.run([sys.executable,str(HERE/'seed-producer'/'seed_worker.py'),str(seedrequest),str(seedwork),str(seedout)]+(['--allow-local-provisional'] if provisional_only else []),check=True);seed=json.loads(build_stage2.read_bytes(seedout/'report.json',guard))
 srows=pin(seedout/'rows.u32le',guard);sruns=pin(seedout/'runs.u32le',guard)
 # Verify selected rules, source/region traces and tie policy before using seed.
 groups={g['group_id']:g for g in resolution['groups']};entity_codes={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b['physical_class']=='land'}
 equivalent=False
 if snapshot.get('source')=='local-derived-from-neon-export':
  pins={k:v['sha256'] for k,v in cfg['inputs'].items()};prior=json.loads(build_stage2.read_bytes(paths['prior_physical_report'],guard));equivalent=contracts.provisional_reproof(snapshot,seed,pins,prior,cfg['grid'])
 contracts.validate_selected_seed_decisions(snapshot,seed,groups,entity_codes,metric,guard=guard,provisional_equivalence=equivalent)
 tileout=work/'tiles-parent'/'tiles';g=cfg['grid'];tile=build_seed_tiles.build(srows['path'],sruns['path'],srows['sha256'],sruns['sha256'],g['width'],g['height'],tileout,disk_floor_bytes=c['minimum_free_bytes'])
 reps=work/'reps'/'representatives.u32le';representatives.build(tileout,tileout/'manifest.txt',tile['manifest_sha256'],reps,work/'reps'/'report.json',width=g['width'],height=g['height'],disk_floor_bytes=c['minimum_free_bytes'])
 # A separately compiled complete seed/tile verifier must precede hints. The
 # core repeats this verification and validates representative cell membership.

 source=HERE/'verify_seed_index.cpp';source_data=build_stage2.read_bytes(source,guard);need(hashlib.sha256(source_data).hexdigest()==code['verify_seed_index.cpp'],'verifier source changed')
 source_copy=work/'requests'/'tile-verifier.cpp'
 with open(source_copy,'xb') as f:f.write(source_data);f.flush();os.fsync(f.fileno())
 binary=work/'requests'/'tile-verifier';subprocess.run(['g++','-O3','-std=c++17','-Wall','-Wextra','-Werror',str(source_copy),'-lcrypto','-o',str(binary)],check=True)
 need(verify_inputs.sha_file(source,guard)==code['verify_seed_index.cpp'] and verify_inputs.sha_file(source_copy,guard)==code['verify_seed_index.cpp'],'verifier source changed during compilation')
 guard();check=subprocess.run([str(binary),srows['path'],sruns['path'],str(tileout),str(g['width']),str(g['height']),'1024'],capture_output=True,text=True,check=True)
 need(json.loads(check.stdout).get('status')=='verified','fresh seed/tile verification failed')
 import numpy as np

 rdata=build_stage2.read_bytes(reps,guard);need(len(rdata)%20==0,'bad representative data');arr=np.frombuffer(rdata,dtype='<u4').reshape(-1,5)
 verify_inputs.verify_representatives(tileout,tileout/'manifest.txt',arr,g['width'],g['height'],guard=guard)
 hi={k:cfg['inputs'][k] for k in ('physical_rows','physical_runs','component_rows','component_runs','decision_snapshot','component_manifest')};hi.update({'seed_rows':srows,'seed_runs':sruns,'resolution_report':rp,'representatives':pin(reps,guard),'tile_manifest':pin(tileout/'manifest.txt',guard)})
 hr={'schema':'source-only-hints-diagnostic-request-v1','grid':g,'codes':sorted(categories),'inputs':hi,'decision_revision':rev,'entity_revision':entity,'policy_id':cfg['policy_id'],'policy_version':cfg['policy_version'],'minimum_free_bytes':c['minimum_free_bytes']}
 hreq=work/'requests'/'hints.json';write_json(hreq,hr);hout=work/'hints-parent'/'hints'
 subprocess.run([sys.executable,str(HERE/'hint-producer'/'run_diagnostic.py'),str(hreq),str(hout)]+(['--allow-local-provisional'] if provisional_only else []),check=True)
 artifacts={'resolution_report':rp,'seed_rows':srows,'seed_runs':sruns,'seed_report':pin(seedout/'report.json',guard),'tile_manifest':pin(tileout/'manifest.txt',guard),'representatives':pin(reps,guard),'hint_roots':pin(hout/'roots.u32le',guard),'hint_codes':pin(hout/'hints.u8',guard),'hint_report':pin(hout/'report.json',guard)}
 for spec in cfg['inputs'].values():build_stage2.pin(spec,guard)
 need(build_stage2.read_bytes(cp,guard)==raw and code_hashes(guard)==code,'orchestration input or code changed')
 marker={'schema':'stage2-fresh-derived-v1','outer_config_sha256':hashlib.sha256(raw).hexdigest(),'orchestrator_sha256':code['orchestrate_stage2.py'],'artifacts':artifacts,'seed_request_sha256':verify_inputs.sha_file(seedrequest,guard),'hint_request_sha256':verify_inputs.sha_file(hreq,guard),'seed_tile_verification':json.loads(check.stdout),'physical_lineage_report':pin(work/'lineage'/'report.json',guard),'tile_directory':str(tileout),'code_sha256':code,'provisional_only':provisional_only}
 write_json(work/'derived'/'manifest.json',marker)
 return finish_from_marker(cfg,raw,work,out,code,guard,False,provisional_only,processing_started)

def finish_from_marker(cfg,raw,work,out,code,guard,resume,provisional_only=False,processing_started=None):
 marker_path=work/'derived'/'manifest.json';marker_pin=pin(marker_path,guard);marker=json.loads(build_stage2.read_bytes(marker_path,guard));outer=hashlib.sha256(raw).hexdigest()
 need(marker.get('schema')=='stage2-fresh-derived-v1' and marker.get('outer_config_sha256')==outer and marker.get('orchestrator_sha256')==code['orchestrate_stage2.py'] and marker.get('code_sha256')==code and marker.get('provisional_only') is provisional_only,'derived manifest mismatch')
 snapshot=json.loads(build_stage2.read_bytes(cfg['inputs']['decision_snapshot']['path'],guard));lineage=verify_physical_lineage.validate_combined(snapshot,cfg['inputs']['decision_snapshot']['sha256'],cfg['inputs']['physical_lineage_request']['path'],cfg['inputs']['physical_report']['sha256'],cfg['inputs']['physical_rows']['sha256'],cfg['inputs']['physical_runs']['sha256'],cfg['grid'],guard);lineage_pin=marker.get('physical_lineage_report');need(isinstance(lineage_pin,dict) and Path(lineage_pin.get('path','')).resolve()==work/'lineage'/'report.json' and json.loads(build_stage2.read_bytes(build_stage2.pin(lineage_pin,guard),guard))==lineage,'physical lineage resume mismatch')

 artifacts=marker.get('artifacts');names={'resolution_report','seed_rows','seed_runs','seed_report','hint_roots','hint_codes','hint_report','tile_manifest','representatives'}
 need(isinstance(artifacts,dict) and set(artifacts)==names,'incomplete derived artifacts')
 expected={'resolution_report':work/'resolution'/'report.json','seed_rows':work/'seed-work-parent'/'output'/'rows.u32le','seed_runs':work/'seed-work-parent'/'output'/'runs.u32le','seed_report':work/'seed-work-parent'/'output'/'report.json','hint_roots':work/'hints-parent'/'hints'/'roots.u32le','hint_codes':work/'hints-parent'/'hints'/'hints.u8','hint_report':work/'hints-parent'/'hints'/'report.json','tile_manifest':work/'tiles-parent'/'tiles'/'manifest.txt','representatives':work/'reps'/'representatives.u32le'}
 need(all(Path(artifacts[k].get('path','')).resolve()==v for k,v in expected.items()),'derived artifact path is not fresh work output')
 for p in artifacts.values():build_stage2.pin(p,guard)
 for p in cfg['inputs'].values():build_stage2.pin(p,guard)
 seedreq=work/'requests'/'seed.json';hintreq=work/'requests'/'hints.json'
 need(verify_inputs.sha_file(seedreq,guard)==marker.get('seed_request_sha256') and verify_inputs.sha_file(hintreq,guard)==marker.get('hint_request_sha256'),'derived request hash mismatch')
 sr=json.loads(build_stage2.read_bytes(seedreq,guard));hr=json.loads(build_stage2.read_bytes(hintreq,guard));snap=json.loads(build_stage2.read_bytes(cfg['inputs']['decision_snapshot']['path'],guard))
 expected_seed={dst:cfg['inputs'][src] for dst,src in (('snapshot','decision_snapshot'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('physical_report','physical_report'),('component_rows','component_rows'),('component_runs','component_runs'),('component_manifest','component_manifest'),('closure_checker','closure_checker'),('terminal_checker','terminal_checker'),('closure_contract','closure_contract'),('seed_builder','seed_builder'),('seed_kernel','seed_kernel'))};expected_seed['resolution']=artifacts['resolution_report']
 if 'prior_physical_report' in cfg['inputs']:expected_seed['prior_physical_report']=cfg['inputs']['prior_physical_report']
 c=cfg['controls'];need(expected_seed['resolution']['sha256']==artifacts['resolution_report']['sha256'] and sr.get('schema')=='worldatlas-stage2-seed-request-v1' and sr.get('grid')==cfg['grid'] and sr.get('inputs')==expected_seed and sr.get('controls')=={'disk_reserve_bytes':c['minimum_free_bytes'],**cfg['seed_controls']},'seed request linkage mismatch')
 hint_inputs={k:cfg['inputs'][k] for k in ('physical_rows','physical_runs','component_rows','component_runs','decision_snapshot','component_manifest')};hint_inputs.update({k:artifacts[k] for k in ('seed_rows','seed_runs','resolution_report','representatives','tile_manifest')})
 rev=snap.get('decision_revision',{}).get('id');entity=snap.get('entity_revision',{}).get('id');_,categories,_=contracts.snap_policy(snap,rev,entity,cfg['policy_id'],cfg['policy_version'],allow_local=provisional_only)
 need(hr=={'schema':'source-only-hints-diagnostic-request-v1','grid':cfg['grid'],'codes':sorted(categories),'inputs':hint_inputs,'decision_revision':rev,'entity_revision':entity,'policy_id':cfg['policy_id'],'policy_version':cfg['policy_version'],'minimum_free_bytes':c['minimum_free_bytes']},'hint request linkage mismatch')
 seed_report=json.loads(build_stage2.read_bytes(artifacts['seed_report']['path'],guard));hint_report=json.loads(build_stage2.read_bytes(artifacts['hint_report']['path'],guard));need(seed_report.get('request_sha256')==marker['seed_request_sha256'] and seed_report.get('input_sha256')=={k:v['sha256'] for k,v in expected_seed.items()} and hint_report.get('request_sha256')==marker['hint_request_sha256'],'request/report provenance mismatch')
 tiles=work/'tiles-parent'/'tiles';need(marker.get('tile_directory')==str(tiles) and tiles.is_dir() and marker.get('seed_tile_verification',{}).get('status')=='verified','tile verification binding mismatch')
 inputs={k:v for k,v in cfg['inputs'].items() if k in build_stage2.INPUTS or k=='prior_physical_report'};inputs.update(artifacts)
 need(set(inputs)==build_stage2.INPUTS|({'prior_physical_report'} if 'prior_physical_report' in cfg['inputs'] else set()),'core input mapping mismatch')
 seed_files={n:pin(HERE/'seed-producer'/n,guard) for n in SEED_REPORT_NAMES};seed_files.update({'rasterizer':cfg['inputs']['seed_builder'],'rasterizer_kernel':cfg['inputs']['seed_kernel']})
 resolver_files={'resolver':'v7-land/mainland-witness-prototype/resolve_mainland.py','helper':'v7-land/point-component-prototype/resolve.py','named_identity':'v7-land/named-identity-prototype/named_identity.py'}
 core={'schema':'stage2-source-geodesic-v1','grid':cfg['grid'],'inputs':inputs,'seed_code_files':seed_files,'resolution_code_files':{k:pin(HERE/v,guard) for k,v in resolver_files.items()},'hint_code_files':{n:pin(HERE/'hint-producer'/n,guard) for n in ('hints.py','run_diagnostic.py')},'tile_directory':str(tiles),'policy_id':cfg['policy_id'],'policy_version':cfg['policy_version'],'controls':cfg['controls'],'orchestration':{'outer_config_sha256':outer,'orchestrator_sha256':code['orchestrate_stage2.py'],'derived_manifest':marker_pin,'physical_lineage_report':lineage_pin,'provisional_only':provisional_only}}
 cp=work/'core-requests'/'config.json'
 core_work=work/'core'
 if cp.exists():need(resume and json.loads(build_stage2.read_bytes(cp,guard))==core,'core resume config mismatch')
 else:
  need(not core_work.exists(),'core work exists without its config');write_json(cp,core)
 return build_stage2.build(cp,core_work,out,resume=resume and core_work.exists(),processing_started=processing_started,orchestration_resumed=resume)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('work');p.add_argument('output');p.add_argument('--resume',action='store_true');p.add_argument('--provisional-only',action='store_true',help='run only in distinct provisional paths; output cannot pass candidate validation');a=p.parse_args()
 try:
  run(a.config,a.work,a.output,a.resume,a.provisional_only)
 except Exception as exc:print('error: '+str(exc),file=sys.stderr);raise SystemExit(1)
