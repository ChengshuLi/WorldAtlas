#!/usr/bin/env python3
"""Stage 2 fresh-source orchestration under the supervising guardian.

A fresh same-run seed or the separately monitored, independently checked seed
handoff may be used. Hints are regenerated and no historical assignment or
checkpoint is accepted. All outputs remain research-only.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
import build_seed_tiles,build_stage2,checkpoints,contracts,verify_inputs
import representatives,verify_physical_lineage

HERE=Path(__file__).resolve().parent
BASE_INPUTS={'decision_snapshot','physical_rows','physical_runs','physical_report','component_rows','component_runs','component_manifest','component_source','component_builder_binary','physical_lineage_request','resolution_request','closure_checker','terminal_checker','closure_contract','seed_builder','seed_kernel'}
SEED_NAMES=('seed_producer.py','export_adapter.py','seed_rules.py','region_client.py','region_worker.py','regions.py','closure_client.py','guarded_exec.py','guarded_raster_exec.py')
HINT_NAMES=('hints.py','run_diagnostic.py','watch_diagnostic.py')
# Reviewed candidate seed and worker hashes; input and scientific checks remain independent.
REVIEWED_SEED_FREEZE={'seed_producer.py': '116d43c4b7d510ef16e02a20deaee83ad7424f34e527037dd23e4db68aa1f416', 'export_adapter.py': 'b13d2a5868542cf2946b25c495a12d1aa793470ec55f8744a4af9f96630213f9', 'seed_rules.py': '0e98f77341b8f297b434d46250f2e8e9f615e6a3764cad176fe3cdf40c52f342', 'region_client.py': '9f5c51269abe890ba2db71c8ea91c600f002ea2f1fb6331739c0d84cb5dbc795', 'region_worker.py': '25d888715984a6ba4ed04a154af5980a114f24599baa670ebcc0a2b993b63314', 'regions.py': 'd8cf1c7629321e603c64bd96671498aab4ff78b6921d36b0a735e00a9b7705b0', 'closure_client.py': 'bc976967797ae67c99ab1aff712c25636ab1b3f01f7c7a558c59b530b573fb1b', 'guarded_exec.py': '31bd7364765a2b8c181956cf275fabd6ae764207574f984d7b90c26b1474e7f3', 'guarded_raster_exec.py': '0179c973476ec172bbd2deed4e6e449edffaea8bc77cd3b96296f3ec9e6f7e89'}
REVIEWED_SEED_WORKER_SHA256='5c178ae0f1d5e0878c2b8902aba7a54b86f01b4c85fe9e6833d0c9f2ae83e24d'
SEED_FREEZE_CURRENT=True
SELECTED_POLICY_CROSSWALK_READY=True

def need(v,msg):
 if not v:raise ValueError(msg)
def require_reviewed_seed(code):
 need(isinstance(code,dict),'missing seed code hashes')
 seed_code={n:code.get('seed-producer/'+n) for n in SEED_NAMES}
 need(SEED_FREEZE_CURRENT and REVIEWED_SEED_FREEZE is not None and seed_code==REVIEWED_SEED_FREEZE,'current reviewed seed producer freeze not installed')
 need(code.get('seed-producer/seed_worker.py')==REVIEWED_SEED_WORKER_SHA256,'reviewed seed worker mismatch')

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
 names=['orchestrate_stage2.py','representatives.py','build_seed_tiles.py','seed-producer/seed_worker.py']+[f'seed-producer/{x}' for x in SEED_NAMES]+[f'hint-producer/{x}' for x in HINT_NAMES]+list(build_stage2.CODE_NAMES)
 return {n:verify_inputs.sha_file(HERE/n,guard) for n in names}
def load_config(path):
 raw=verify_inputs.bounded_bytes(path,1<<20);obj=json.loads(raw)
 keys={'schema','grid','inputs','policy_id','policy_version','controls','seed_controls','hint_max_rss_kib'}
 need(isinstance(obj,dict) and set(obj) in (keys,keys|{'seed_handoff'}) and obj['schema']=='stage2-fresh-orchestration-v1' and isinstance(obj['inputs'],dict) and set(obj['inputs'])==BASE_INPUTS,'invalid fresh orchestration config or historical input')
 if 'seed_handoff' in obj:need(isinstance(obj['seed_handoff'],dict) and set(obj['seed_handoff'])=={'attestation','seed_watchdog_code','seed_guardian_code','witness_report','witness_monitor','witness_watchdog_code','witness_guardian_code','component_report','component_monitor','component_watchdog_code','component_guardian_code','component_config','component_driver_code','witness_config','witness_driver_code'},'invalid monitored seed handoff')
 build_stage2.validate_controls(obj['controls'])
 s=obj['seed_controls'];need(isinstance(s,dict) and set(s)=={'timeout_seconds','strip_rows','max_group_rss_kib'} and type(s['timeout_seconds']) in (int,float) and 0<s['timeout_seconds']<=1800 and type(s['strip_rows']) is int and 1<=s['strip_rows']<=64 and type(s['max_group_rss_kib']) is int and 262144<=s['max_group_rss_kib']<=786432,'invalid seed controls')
 need(type(obj['hint_max_rss_kib']) is int and obj['hint_max_rss_kib']>0 and all(isinstance(obj[k],str) and obj[k] for k in ('policy_id','policy_version')),'invalid hint/policy controls')
 return raw,obj

def seed_monitor_floor_matches(monitor, seed_controls):
 # A null floor means the outer monitor observed memory but did not enforce a floor.
 return ('memory_floor_kib' in monitor and
         (monitor['memory_floor_kib'] is None or
          (type(monitor['memory_floor_kib']) is int and monitor['memory_floor_kib']==seed_controls['memory_floor_kib'])))

def require_closure_floor(contract,controls):
 resources=contract.get('resources') if isinstance(contract,dict) else None
 need(isinstance(resources,dict) and type(resources.get('memory_floor_kib')) is int and resources['memory_floor_kib']>0 and controls['minimum_memory_kib']>=resources['memory_floor_kib'],'monitor memory floor is below closure checker contract')

def require_guardian():
 parent=os.getppid();need(parent==os.getpgrp(),'stage-2 guardian/monitor required')
 try:
  argv=Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0')
  valid=len(argv)>=3 and Path(os.fsdecode(argv[1])).resolve()==(HERE/'guardian.py').resolve()
 except (OSError,ValueError):valid=False
 need(valid and os.getppid()==parent,'stage-2 guardian/monitor required')

def validate_seed_handoff(cfg,code,guard):
 h=cfg['seed_handoff'];paths={k:build_stage2.pin(v,guard) for k,v in h.items()}
 read=lambda p:json.loads(verify_inputs.bounded_bytes(p,16<<20,guard))
 a=read(paths['attestation']);need(a.get('schema')=='stage2-seed-readback-attestation-v1' and a.get('status')=='sampled-complete','seed attestation incomplete')
 ap={k:build_stage2.pin(a[k],guard) for k in ('request','monitor','report','seed_rows','seed_runs')};q=read(ap['request']);report=read(ap['report']);mon=read(ap['monitor']);need(a.get('seed_worker_sha256')==code['seed-producer/seed_worker.py'] and a.get('producer_code_sha256')==report.get('code_sha256'),'seed code attestation mismatch')
 expected_code={n:code['seed-producer/'+n] for n in SEED_NAMES};expected_code.update({'rasterizer':cfg['inputs']['seed_builder']['sha256'],'rasterizer_kernel':cfg['inputs']['seed_kernel']['sha256']});need(report.get('code_sha256')==expected_code,'seed producer code mismatch')
 need(q.get('schema')=='worldatlas-stage2-seed-request-v1' and q.get('grid')==cfg['grid'] and report.get('schema')=='worldatlas-stage2-mainland-seed-report-v1' and report.get('status')=='diagnostic-seed-pending-independent-provenance' and report.get('publishable') is False and report.get('request_sha256')==a['request']['sha256'],'seed request/report mismatch')
 for dst,src in (('snapshot','decision_snapshot'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('physical_report','physical_report'),('component_rows','component_rows'),('component_runs','component_runs'),('component_manifest','component_manifest'),('closure_checker','closure_checker'),('terminal_checker','terminal_checker'),('closure_contract','closure_contract'),('seed_builder','seed_builder'),('seed_kernel','seed_kernel')):need(q.get('inputs',{}).get(dst,{}).get('sha256')==cfg['inputs'][src]['sha256'],'seed handoff input mismatch: '+dst)
 need(report.get('input_sha256')=={k:v['sha256'] for k,v in q['inputs'].items()} and report.get('seed_rows_sha256')==a['seed_rows']['sha256'] and report.get('seed_runs_sha256')==a['seed_runs']['sha256'] and a.get('snapshot_sha256')==cfg['inputs']['decision_snapshot']['sha256'] and a.get('resolution_sha256')==q['inputs']['resolution']['sha256'] and a.get('component_manifest_sha256')==cfg['inputs']['component_manifest']['sha256'],'seed handoff hashes mismatch')
 sc=q.get('controls',{});need(type(sc.get('memory_floor_kib')) is int and sc['memory_floor_kib']>=1730151 and type(sc.get('disk_reserve_bytes')) is int and sc['disk_reserve_bytes']>=2*1024**3 and all(sc.get(k)==v for k,v in cfg['seed_controls'].items()),'seed resource controls mismatch')
 closure=json.loads(verify_inputs.bounded_bytes(cfg['inputs']['closure_contract']['path'],65536,guard));closure_floor=closure.get('resources',{}).get('memory_floor_kib');need(type(closure_floor) is int and closure_floor>0 and mon.get('minimum_available_kib',0)>=closure_floor,'seed monitor below selected closure floor')
 need(mon.get('schema')=='sampled-process-group-watchdog-v1' and mon.get('status')=='complete' and mon.get('watchdog_sha256')==h['seed_watchdog_code']['sha256'] and mon.get('guardian_sha256')==h['seed_guardian_code']['sha256'] and seed_monitor_floor_matches(mon,sc) and type(mon.get('disk_floor_bytes')) is int and mon['disk_floor_bytes']>=sc['disk_reserve_bytes'] and mon.get('group_rss_limit_kib')==sc['max_group_rss_kib'] and type(mon.get('samples')) is int and mon['samples']>0 and type(mon.get('minimum_available_kib')) is int and mon['minimum_available_kib']>=sc['memory_floor_kib'] and type(mon.get('peak_group_rss_kib')) is int and 0<mon['peak_group_rss_kib']<=sc['max_group_rss_kib'] and type(mon.get('sample_interval_seconds')) in (int,float) and 0<mon['sample_interval_seconds']<=.1,'seed monitor incomplete')
 wr=read(paths['witness_report']);wm=read(paths['witness_monitor']);cr=read(paths['component_report']);cm=read(paths['component_monitor']);wc=read(paths['witness_config']);cc=read(paths['component_config'])
 need(wr.get('schema')=='fresh-mainland-witness-report-v1' and wr.get('status')=='research-awaiting-monitor' and wr.get('publishable') is False and wr.get('resolution_sha256')==a['resolution_sha256'] and wr.get('request_sha256')==cfg['inputs']['resolution_request']['sha256'] and wr.get('component_report_sha256')==h['component_report']['sha256'] and wr.get('component_monitor_sha256')==h['component_monitor']['sha256'],'witness handoff mismatch')
 need(wm.get('schema')=='fresh-mainland-witness-watchdog-v1' and wm.get('status')=='sampled-complete' and wm.get('report_sha256')==h['witness_report']['sha256'] and wm.get('watchdog_sha256')==h['witness_watchdog_code']['sha256'] and wm.get('guardian_sha256')==h['witness_guardian_code']['sha256'] and wm.get('driver_sha256')==wr.get('driver_sha256')==h['witness_driver_code']['sha256'] and wm.get('config_sha256')==wr.get('config_sha256')==h['witness_config']['sha256'] and type(wm.get('samples')) is int and wm['samples']>0 and wm.get('minimum_memory_kib')==wc.get('controls',{}).get('minimum_memory_kib') and wm.get('minimum_available_kib',0)>=wm.get('minimum_memory_kib',1)>0 and 0<wm.get('peak_process_group_rss_kib',0)<=wm.get('maximum_process_group_rss_kib',0) and type(wm.get('sample_interval_seconds')) in (int,float) and 0<wm['sample_interval_seconds']<=.1,'witness monitor mismatch')
 need(cr.get('schema')=='fresh-physical-components-report-v1' and cr.get('status')=='research-awaiting-monitor' and cr.get('publishable') is False and cr.get('manifest_sha256')==cfg['inputs']['component_manifest']['sha256'] and cr.get('component_rows_sha256')==cfg['inputs']['component_rows']['sha256'] and cr.get('component_runs_sha256')==cfg['inputs']['component_runs']['sha256'] and all(cr.get('input_sha256',{}).get(k)==cfg['inputs'][k]['sha256'] for k in ('physical_rows','physical_runs','physical_report','component_source')),'component handoff mismatch')
 need(cm.get('schema')=='fresh-physical-components-watchdog-v1' and cm.get('status')=='sampled-complete' and cm.get('report_sha256')==h['component_report']['sha256'] and cm.get('watchdog_sha256')==h['component_watchdog_code']['sha256'] and cm.get('guardian_sha256')==h['component_guardian_code']['sha256'] and cm.get('driver_sha256')==cr.get('driver_sha256')==h['component_driver_code']['sha256'] and cm.get('config_sha256')==cr.get('config_sha256')==h['component_config']['sha256'] and type(cm.get('samples')) is int and cm['samples']>0 and cm.get('minimum_memory_kib')==cc.get('controls',{}).get('minimum_memory_kib') and cm.get('minimum_available_kib',0)>=cm.get('minimum_memory_kib',1)>0 and 0<cm.get('peak_process_group_rss_kib',0)<=cm.get('maximum_process_group_rss_kib',0) and type(cm.get('sample_interval_seconds')) in (int,float) and 0<cm['sample_interval_seconds']<=.1,'component monitor mismatch')
 return a,q,report,ap

def run(config_path,work_dir,output_dir,resume=False):
 require_guardian()
 cp,work,out=map(lambda p:Path(p).resolve(),(config_path,work_dir,output_dir));raw,cfg=load_config(cp);c=cfg['controls']
 need(work.parent.is_dir() and out.parent.is_dir() and work!=out and not work.is_relative_to(out) and not out.is_relative_to(work),'invalid work/output')
 guard=lambda:checkpoints.guard(work.parent,c['minimum_memory_kib'],c['minimum_free_bytes']);guard()
 paths={k:build_stage2.pin(v,guard) for k,v in cfg['inputs'].items()};handoff_paths={k:build_stage2.pin(v,guard) for k,v in cfg.get('seed_handoff',{}).items()}
 for p in [cp,HERE,*paths.values(),*handoff_paths.values()]:
  d=p if p==HERE else p.parent
  need(all(not t.is_relative_to(d) and not d.is_relative_to(t) for t in (work,out)),'work/output overlaps code or input')
 code=code_hashes(guard);require_reviewed_seed(code)
 need(SELECTED_POLICY_CROSSWALK_READY,'selected land-policy crosswalk not yet implemented')
 grid=cfg['grid'];need(isinstance(grid,dict) and set(grid)=={'width','height','west','north','step'} and type(grid['width']) is int and type(grid['height']) is int and 1<grid['width']<=1000000 and 0<grid['height']<=1000000 and grid['west']==-180 and grid['north']==90 and grid['step']==360/grid['width'] and 90-grid['height']*grid['step']>=-90-1e-8,'invalid global grid')
 closure_contract=json.loads(verify_inputs.bounded_bytes(paths['closure_contract'],65536,guard));require_closure_floor(closure_contract,c)
 snapshot=json.loads(verify_inputs.bounded_bytes(paths['decision_snapshot'],16<<20,guard));rev=snapshot.get('decision_revision',{}).get('id');entity=snapshot.get('entity_revision',{}).get('id');contracts.snap_policy(snapshot,rev,entity,cfg['policy_id'],cfg['policy_version'])
 pins={k:v['sha256'] for k,v in cfg['inputs'].items()};lineage=verify_physical_lineage.validate_combined(snapshot,pins['decision_snapshot'],paths['physical_lineage_request'],pins['physical_report'],pins['physical_rows'],pins['physical_runs'],cfg['grid'],guard);manifest=json.loads(verify_inputs.bounded_bytes(paths['component_manifest'],16<<20,guard));contracts.component_manifest(manifest,grid,pins)
 physical=json.loads(verify_inputs.bounded_bytes(paths['physical_report'],16<<20,guard));po=physical.get('physical_output_sha256',physical.get('output_sha256',{}));need(physical.get('status') in ('candidate-only','stage1-complete') and physical.get('grid')==grid and po.get('rows.u32le')==pins['physical_rows'] and po.get('runs.u32le')==pins['physical_runs'],'physical report mismatch')
 rr=json.loads(verify_inputs.bounded_bytes(paths['resolution_request'],16<<20,guard));rnames={'resolver':'v7-land/mainland-witness-prototype/resolve_mainland.py','helper':'v7-land/point-component-prototype/resolve.py','named_identity':'v7-land/named-identity-prototype/named_identity.py','identity_watch':'v7-land/named-identity-prototype/identity_watch.py'}
 need(rr.get('schema')=='mainland-witness-request-v1' and rr.get('grid')==grid and rr.get('code_sha256')=={k:code[v] for k,v in rnames.items()},'resolution request/code mismatch')
 for rk,ik in (('snapshot','decision_snapshot'),('component_manifest','component_manifest'),('component_source','component_source'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('component_rows','component_rows'),('component_runs','component_runs')):need(rr.get(rk,{}).get('sha256')==pins[ik],'resolution request pin mismatch: '+rk)
 handoff=validate_seed_handoff(cfg,code,guard) if 'seed_handoff' in cfg else None
 identity={'schema':'stage2-fresh-work-v1','config_sha256':hashlib.sha256(raw).hexdigest(),'input_sha256':{k:v['sha256'] for k,v in cfg['inputs'].items()},'handoff_sha256':{k:v['sha256'] for k,v in cfg.get('seed_handoff',{}).items()},'code_sha256':code,'output_path':str(out)}
 need(not out.exists(),'output already exists')
 if resume:
  need(work.is_dir() and json.loads(verify_inputs.bounded_bytes(work/'identity.json',16<<20,guard))==identity,'resume identity mismatch')
  return finish_from_marker(cfg,raw,work,out,code,guard,True)
 need(not work.exists(),'fresh work already exists')
 work.mkdir(mode=0o700)
 try:
  fd=os.open(work.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 except OSError as exc:raise RuntimeError('work directory may exist; durability uncertain, inspect before retry') from exc
 for name in ('resolution','requests','seed-work-parent','tiles-parent','reps','hints-parent','core-requests','derived','lineage'):(work/name).mkdir(mode=0o700)
 write_json(work/'identity.json',identity);write_json(work/'lineage'/'report.json',lineage)
 rr=paths['resolution_request'];rout=work/'resolution'/'report.json'
 subprocess.run([sys.executable,str(HERE/'v7-land/mainland-witness-prototype/resolve_mainland.py'),str(rr),str(rout)],check=True)
 resolution=json.loads(verify_inputs.bounded_bytes(rout,16<<20,guard));snapshot=json.loads(verify_inputs.bounded_bytes(paths['decision_snapshot'],16<<20,guard));rev=snapshot['decision_revision']['id'];entity=snapshot['entity_revision']['id'];metric,categories,_=contracts.snap_policy(snapshot,rev,entity,cfg['policy_id'],cfg['policy_version'])
 rp=pin(rout,guard);si={}
 for dst,src in (('snapshot','decision_snapshot'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('physical_report','physical_report'),('component_rows','component_rows'),('component_runs','component_runs'),('component_manifest','component_manifest'),('closure_checker','closure_checker'),('terminal_checker','terminal_checker'),('closure_contract','closure_contract'),('seed_builder','seed_builder'),('seed_kernel','seed_kernel')):si[dst]=cfg['inputs'][src]
 seedrequest=work/'requests'/'seed.json';seedwork=work/'seed-work-parent'/'build';seedout=work/'seed-work-parent'/'output'
 if handoff:
  att,sr,seed,ap=handoff;need(sr['inputs']['resolution']['sha256']==rp['sha256'],'fresh witness differs from monitored seed witness');si['resolution']=sr['inputs']['resolution'];need(all(sr['inputs'][k]['sha256']==v['sha256'] for k,v in si.items()),'handoff request inputs differ')
  for p in ap.values():need(all(not t.is_relative_to(p.parent) and not p.parent.is_relative_to(t) for t in (work,out)),'handoff artifact overlaps work/output')
  os.link(ap['request'],seedrequest);seedout.mkdir(mode=0o700)
  for src,dst in (('report','report.json'),('seed_rows','rows.u32le'),('seed_runs','runs.u32le')):os.link(ap[src],seedout/dst)
  for d in (seedrequest.parent,seedout,seedout.parent):
   fd=os.open(d,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 else:
  si['resolution']=rp;sr={'schema':'worldatlas-stage2-seed-request-v1','grid':cfg['grid'],'inputs':si,'controls':{'memory_floor_kib':c['minimum_memory_kib'],'disk_reserve_bytes':c['minimum_free_bytes'],**cfg['seed_controls']}};write_json(seedrequest,sr)
  subprocess.run([sys.executable,str(HERE/'seed-producer'/'seed_worker.py'),str(seedrequest),str(seedwork),str(seedout)],check=True);seed=json.loads(verify_inputs.bounded_bytes(seedout/'report.json',16<<20,guard))
 srows=pin(seedout/'rows.u32le',guard);sruns=pin(seedout/'runs.u32le',guard)
 # Verify selected rules, source/region traces and tie policy before using seed.
 groups={g['group_id']:g for g in resolution['groups']};entity_codes={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b['physical_class']=='land'}
 contracts.validate_selected_seed_decisions(snapshot,seed,groups,entity_codes,metric,guard=guard)
 tileout=work/'tiles-parent'/'tiles';g=cfg['grid'];tile=build_seed_tiles.build(srows['path'],sruns['path'],srows['sha256'],sruns['sha256'],g['width'],g['height'],tileout,memory_floor_kib=c['minimum_memory_kib'],disk_floor_bytes=c['minimum_free_bytes'])
 reps=work/'reps'/'representatives.u32le';representatives.build(tileout,tileout/'manifest.txt',tile['manifest_sha256'],reps,work/'reps'/'report.json',width=g['width'],height=g['height'],memory_floor_kib=c['minimum_memory_kib'],disk_floor_bytes=c['minimum_free_bytes'])
 # A separately compiled complete seed/tile verifier must precede hints. The
 # core repeats this verification and validates representative cell membership.
 need(checkpoints.memory_available_kib()>=c['minimum_memory_kib']+262144,'insufficient verifier compilation headroom')
 source=HERE/'verify_seed_index.cpp';source_data=verify_inputs.bounded_bytes(source,1<<20,guard);need(hashlib.sha256(source_data).hexdigest()==code['verify_seed_index.cpp'],'verifier source changed')
 source_copy=work/'requests'/'tile-verifier.cpp'
 with open(source_copy,'xb') as f:f.write(source_data);f.flush();os.fsync(f.fileno())
 binary=work/'requests'/'tile-verifier';subprocess.run(['g++','-O3','-std=c++17','-Wall','-Wextra','-Werror',str(source_copy),'-lcrypto','-o',str(binary)],check=True)
 need(verify_inputs.sha_file(source,guard)==code['verify_seed_index.cpp'] and verify_inputs.sha_file(source_copy,guard)==code['verify_seed_index.cpp'],'verifier source changed during compilation')
 guard();check=subprocess.run([str(binary),srows['path'],sruns['path'],str(tileout),str(g['width']),str(g['height']),'1024',str(c['minimum_memory_kib'])],capture_output=True,text=True,check=True)
 need(json.loads(check.stdout).get('status')=='verified','fresh seed/tile verification failed')
 import numpy as np
 need(checkpoints.memory_available_kib()>=c['minimum_memory_kib']+65536+reps.stat().st_size//4,'insufficient representative verification headroom')
 rdata=verify_inputs.bounded_bytes(reps,128<<20,guard);need(len(rdata)%20==0,'bad representative data');arr=np.frombuffer(rdata,dtype='<u4').reshape(-1,5)
 verify_inputs.verify_representatives(tileout,tileout/'manifest.txt',arr,g['width'],g['height'],guard=guard)
 hi={k:cfg['inputs'][k] for k in ('physical_rows','physical_runs','component_rows','component_runs','decision_snapshot','component_manifest')};hi.update({'seed_rows':srows,'seed_runs':sruns,'resolution_report':rp,'representatives':pin(reps,guard),'tile_manifest':pin(tileout/'manifest.txt',guard)})
 hr={'schema':'source-only-hints-diagnostic-request-v1','grid':g,'codes':sorted(categories),'inputs':hi,'decision_revision':rev,'entity_revision':entity,'policy_id':cfg['policy_id'],'policy_version':cfg['policy_version'],'minimum_memory_kib':c['minimum_memory_kib'],'minimum_free_bytes':c['minimum_free_bytes']}
 hreq=work/'requests'/'hints.json';write_json(hreq,hr);hout=work/'hints-parent'/'hints'
 subprocess.run([sys.executable,str(HERE/'hint-producer'/'watch_diagnostic.py'),str(hreq),str(hout),str(cfg['hint_max_rss_kib'])],check=True)
 artifacts={'resolution_report':rp,'seed_rows':srows,'seed_runs':sruns,'seed_report':pin(seedout/'report.json',guard),'tile_manifest':pin(tileout/'manifest.txt',guard),'representatives':pin(reps,guard),'hint_roots':pin(hout/'roots.u32le',guard),'hint_codes':pin(hout/'hints.u8',guard),'hint_report':pin(hout/'report.json',guard),'hint_monitor':pin(hout/'monitor.json',guard)}
 for spec in cfg['inputs'].values():build_stage2.pin(spec,guard)
 need(verify_inputs.bounded_bytes(cp,1<<20,guard)==raw and code_hashes(guard)==code,'orchestration input or code changed')
 marker={'schema':'stage2-fresh-derived-v1','outer_config_sha256':hashlib.sha256(raw).hexdigest(),'orchestrator_sha256':code['orchestrate_stage2.py'],'artifacts':artifacts,'seed_request_sha256':verify_inputs.sha_file(seedrequest,guard),'hint_request_sha256':verify_inputs.sha_file(hreq,guard),'seed_tile_verification':json.loads(check.stdout),'physical_lineage_report':pin(work/'lineage'/'report.json',guard),'seed_handoff_attestation':cfg['seed_handoff']['attestation'] if handoff else None,'tile_directory':str(tileout),'code_sha256':code}
 write_json(work/'derived'/'manifest.json',marker)
 return finish_from_marker(cfg,raw,work,out,code,guard,False)

def finish_from_marker(cfg,raw,work,out,code,guard,resume):
 marker_path=work/'derived'/'manifest.json';marker_pin=pin(marker_path,guard);marker=json.loads(verify_inputs.bounded_bytes(marker_path,16<<20,guard));outer=hashlib.sha256(raw).hexdigest()
 need(marker.get('schema')=='stage2-fresh-derived-v1' and marker.get('outer_config_sha256')==outer and marker.get('orchestrator_sha256')==code['orchestrate_stage2.py'] and marker.get('code_sha256')==code,'derived manifest mismatch')
 snapshot=json.loads(verify_inputs.bounded_bytes(cfg['inputs']['decision_snapshot']['path'],16<<20,guard));lineage=verify_physical_lineage.validate_combined(snapshot,cfg['inputs']['decision_snapshot']['sha256'],cfg['inputs']['physical_lineage_request']['path'],cfg['inputs']['physical_report']['sha256'],cfg['inputs']['physical_rows']['sha256'],cfg['inputs']['physical_runs']['sha256'],cfg['grid'],guard);lineage_pin=marker.get('physical_lineage_report');need(isinstance(lineage_pin,dict) and Path(lineage_pin.get('path','')).resolve()==work/'lineage'/'report.json' and json.loads(verify_inputs.bounded_bytes(build_stage2.pin(lineage_pin,guard),16<<20,guard))==lineage,'physical lineage resume mismatch')
 handoff=validate_seed_handoff(cfg,code,guard) if 'seed_handoff' in cfg else None
 need(marker.get('seed_handoff_attestation')==(cfg['seed_handoff']['attestation'] if handoff else None),'seed handoff marker mismatch')
 artifacts=marker.get('artifacts');names={'resolution_report','seed_rows','seed_runs','seed_report','hint_roots','hint_codes','hint_report','hint_monitor','tile_manifest','representatives'}
 need(isinstance(artifacts,dict) and set(artifacts)==names,'incomplete derived artifacts')
 expected={'resolution_report':work/'resolution'/'report.json','seed_rows':work/'seed-work-parent'/'output'/'rows.u32le','seed_runs':work/'seed-work-parent'/'output'/'runs.u32le','seed_report':work/'seed-work-parent'/'output'/'report.json','hint_roots':work/'hints-parent'/'hints'/'roots.u32le','hint_codes':work/'hints-parent'/'hints'/'hints.u8','hint_report':work/'hints-parent'/'hints'/'report.json','hint_monitor':work/'hints-parent'/'hints'/'monitor.json','tile_manifest':work/'tiles-parent'/'tiles'/'manifest.txt','representatives':work/'reps'/'representatives.u32le'}
 need(all(Path(artifacts[k].get('path','')).resolve()==v for k,v in expected.items()),'derived artifact path is not fresh work output')
 for p in artifacts.values():build_stage2.pin(p,guard)
 for p in cfg['inputs'].values():build_stage2.pin(p,guard)
 seedreq=work/'requests'/'seed.json';hintreq=work/'requests'/'hints.json'
 need(verify_inputs.sha_file(seedreq,guard)==marker.get('seed_request_sha256') and verify_inputs.sha_file(hintreq,guard)==marker.get('hint_request_sha256'),'derived request hash mismatch')
 sr=json.loads(verify_inputs.bounded_bytes(seedreq,1<<20,guard));hr=json.loads(verify_inputs.bounded_bytes(hintreq,1<<20,guard));snap=json.loads(verify_inputs.bounded_bytes(cfg['inputs']['decision_snapshot']['path'],16<<20,guard))
 expected_seed={dst:cfg['inputs'][src] for dst,src in (('snapshot','decision_snapshot'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('physical_report','physical_report'),('component_rows','component_rows'),('component_runs','component_runs'),('component_manifest','component_manifest'),('closure_checker','closure_checker'),('terminal_checker','terminal_checker'),('closure_contract','closure_contract'),('seed_builder','seed_builder'),('seed_kernel','seed_kernel'))};expected_seed['resolution']=sr['inputs']['resolution'] if handoff else artifacts['resolution_report']
 c=cfg['controls'];need(expected_seed['resolution']['sha256']==artifacts['resolution_report']['sha256'] and sr.get('schema')=='worldatlas-stage2-seed-request-v1' and sr.get('grid')==cfg['grid'] and sr.get('inputs')==expected_seed and (sr.get('controls')==handoff[1]['controls'] if handoff else sr.get('controls')=={'memory_floor_kib':c['minimum_memory_kib'],'disk_reserve_bytes':c['minimum_free_bytes'],**cfg['seed_controls']}),'seed request linkage mismatch')
 hint_inputs={k:cfg['inputs'][k] for k in ('physical_rows','physical_runs','component_rows','component_runs','decision_snapshot','component_manifest')};hint_inputs.update({k:artifacts[k] for k in ('seed_rows','seed_runs','resolution_report','representatives','tile_manifest')})
 rev=snap.get('decision_revision',{}).get('id');entity=snap.get('entity_revision',{}).get('id');_,categories,_=contracts.snap_policy(snap,rev,entity,cfg['policy_id'],cfg['policy_version'])
 need(hr=={'schema':'source-only-hints-diagnostic-request-v1','grid':cfg['grid'],'codes':sorted(categories),'inputs':hint_inputs,'decision_revision':rev,'entity_revision':entity,'policy_id':cfg['policy_id'],'policy_version':cfg['policy_version'],'minimum_memory_kib':c['minimum_memory_kib'],'minimum_free_bytes':c['minimum_free_bytes']},'hint request linkage mismatch')
 seed_report=json.loads(verify_inputs.bounded_bytes(artifacts['seed_report']['path'],16<<20,guard));hint_report=json.loads(verify_inputs.bounded_bytes(artifacts['hint_report']['path'],16<<20,guard));need(seed_report.get('request_sha256')==marker['seed_request_sha256'] and seed_report.get('input_sha256')=={k:v['sha256'] for k,v in expected_seed.items()} and hint_report.get('request_sha256')==marker['hint_request_sha256'],'request/report provenance mismatch')
 tiles=work/'tiles-parent'/'tiles';need(marker.get('tile_directory')==str(tiles) and tiles.is_dir() and marker.get('seed_tile_verification',{}).get('status')=='verified','tile verification binding mismatch')
 inputs={k:v for k,v in cfg['inputs'].items() if k in build_stage2.INPUTS};inputs.update(artifacts)
 need(set(inputs)==build_stage2.INPUTS,'core input mapping mismatch')
 seed_files={n:pin(HERE/'seed-producer'/n,guard) for n in SEED_NAMES};seed_files.update({'rasterizer':cfg['inputs']['seed_builder'],'rasterizer_kernel':cfg['inputs']['seed_kernel']})
 resolver_files={'resolver':'v7-land/mainland-witness-prototype/resolve_mainland.py','helper':'v7-land/point-component-prototype/resolve.py','named_identity':'v7-land/named-identity-prototype/named_identity.py','identity_watch':'v7-land/named-identity-prototype/identity_watch.py'}
 core={'schema':'stage2-source-geodesic-v1','grid':cfg['grid'],'inputs':inputs,'seed_code_files':seed_files,'resolution_code_files':{k:pin(HERE/v,guard) for k,v in resolver_files.items()},'hint_code_files':{n:pin(HERE/'hint-producer'/n,guard) for n in ('hints.py','run_diagnostic.py')},'hint_watchdog_code':pin(HERE/'hint-producer'/'watch_diagnostic.py',guard),'tile_directory':str(tiles),'policy_id':cfg['policy_id'],'policy_version':cfg['policy_version'],'controls':cfg['controls'],'orchestration':{'outer_config_sha256':outer,'orchestrator_sha256':code['orchestrate_stage2.py'],'derived_manifest':marker_pin,'physical_lineage_report':lineage_pin,'seed_handoff_attestation':cfg['seed_handoff']['attestation'] if handoff else None,'seed_handoff_context':cfg.get('seed_handoff')}}
 cp=work/'core-requests'/'config.json'
 core_work=work/'core'
 if cp.exists():need(resume and json.loads(verify_inputs.bounded_bytes(cp,1<<20,guard))==core,'core resume config mismatch')
 else:
  need(not core_work.exists(),'core work exists without its config');write_json(cp,core)
 return build_stage2.build(cp,core_work,out,resume=resume and core_work.exists())

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('work');p.add_argument('output');p.add_argument('--resume',action='store_true');a=p.parse_args()
 try:
  run(a.config,a.work,a.output,a.resume)
 except Exception as exc:print('error: '+str(exc),file=sys.stderr);raise SystemExit(1)
