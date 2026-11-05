#!/usr/bin/env /usr/bin/python3
"""Resolve actual selected witness groups on fresh monitored physical components."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'stage2-geodesic-20261104';sys.path.insert(0,str(BASE))
import checkpoints,verify_inputs,atomic_move

def need(x,msg):
 if not x:raise ValueError(msg)
def sync_dir(path):
 d=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(d)
 finally:os.close(d)
def pin(spec,guard):
 need(isinstance(spec,dict) and set(spec)=={'path','sha256'} and isinstance(spec['sha256'],str) and len(spec['sha256'])==64,'invalid pin');p=Path(spec['path']).resolve(strict=True);need(p.is_file() and verify_inputs.sha_file(p,guard)==spec['sha256'],'input hash mismatch');return p
def run(config_path,work_dir,output_dir):
 parent=os.getppid();need(parent==os.getpgrp(),'monitored guardian required');args=Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0');need(len(args)>2 and Path(os.fsdecode(args[1])).resolve()==(HERE/'guardian.py').resolve() and os.getppid()==parent,'monitored guardian required')
 cp,work,out=map(lambda x:Path(x).resolve(),(config_path,work_dir,output_dir));raw=verify_inputs.bounded_bytes(cp,1<<20);cfg=json.loads(raw);need(set(cfg)=={'schema','inputs','controls'} and cfg['schema']=='fresh-mainland-witness-v1' and set(cfg['inputs'])=={'request','component_report','component_monitor'},'invalid witness request')
 c=cfg['controls'];need(set(c)=={'minimum_memory_kib','minimum_free_bytes'} and type(c['minimum_memory_kib']) is int and c['minimum_memory_kib']>=1730151 and type(c['minimum_free_bytes']) is int and c['minimum_free_bytes']>=2*1024**3,'invalid resource floors')
 need(work.parent.is_dir() and out.parent.is_dir() and os.stat(work.parent).st_dev==os.stat(out.parent).st_dev and not work.exists() and not out.exists() and work!=out and not work.is_relative_to(out) and not out.is_relative_to(work),'fresh same-filesystem work/output required')
 guard=lambda:checkpoints.guard(work.parent,c['minimum_memory_kib'],c['minimum_free_bytes']);guard();paths={k:pin(v,guard) for k,v in cfg['inputs'].items()}
 for p in [cp,HERE,BASE,*paths.values()]:
  d=p if p in (HERE,BASE) else p.parent;need(all(not t.is_relative_to(d) and not d.is_relative_to(t) for t in (work,out)),'work/output overlaps inputs or code')
 request=json.loads(verify_inputs.bounded_bytes(paths['request'],1<<20,guard));report=json.loads(verify_inputs.bounded_bytes(paths['component_report'],16<<20,guard));monitor=json.loads(verify_inputs.bounded_bytes(paths['component_monitor'],16<<20,guard))
 need(report.get('schema')=='fresh-physical-components-report-v1' and report.get('status')=='research-awaiting-monitor' and report.get('publishable') is False and report.get('manifest_sha256')==request.get('component_manifest',{}).get('sha256') and report.get('component_rows_sha256')==request.get('component_rows',{}).get('sha256') and report.get('component_runs_sha256')==request.get('component_runs',{}).get('sha256') and report.get('input_sha256',{}).get('component_source')==request.get('component_source',{}).get('sha256'),'component report mismatch')
 need(monitor.get('schema')=='fresh-physical-components-watchdog-v1' and monitor.get('status')=='sampled-complete' and monitor.get('report_sha256')==cfg['inputs']['component_report']['sha256'] and monitor.get('config_sha256')==report.get('config_sha256') and monitor.get('driver_sha256')==report.get('driver_sha256') and type(monitor.get('samples')) is int and monitor['samples']>0 and monitor.get('minimum_available_kib',0)>=monitor.get('minimum_memory_kib',1)>0 and 0<monitor.get('peak_process_group_rss_kib',0)<=monitor.get('maximum_process_group_rss_kib',0),'component monitor incomplete')
 need(checkpoints.memory_available_kib()>=c['minimum_memory_kib']+256*1024,'insufficient witness parsing headroom')
 work.mkdir(mode=0o700);sync_dir(work.parent);stage=work/'result.partial';stage.mkdir(mode=0o700);resolver=BASE/'v7-land/mainland-witness-prototype/resolve_mainland.py';driver_sha=verify_inputs.sha_file(HERE/'run_witness.py',guard);start=time.monotonic()
 subprocess.run([sys.executable,str(resolver),str(paths['request']),str(stage/'resolution.json')],check=True);guard();resolution=json.loads(verify_inputs.bounded_bytes(stage/'resolution.json',16<<20,guard));need(resolution.get('schema')=='mainland-witness-resolution-v1' and resolution.get('status')=='selected-research-identity-claims-not-mainland-proof' and resolution.get('publishable') is False and resolution.get('request_sha256')==cfg['inputs']['request']['sha256'],'witness resolution mismatch')
 for spec in cfg['inputs'].values():pin(spec,guard)
 need(verify_inputs.bounded_bytes(cp,1<<20,guard)==raw and verify_inputs.sha_file(HERE/'run_witness.py',guard)==driver_sha,'request or code changed');result={'schema':'fresh-mainland-witness-report-v1','status':'research-awaiting-monitor','publishable':False,'config_sha256':hashlib.sha256(raw).hexdigest(),'driver_sha256':driver_sha,'request_sha256':cfg['inputs']['request']['sha256'],'component_report_sha256':cfg['inputs']['component_report']['sha256'],'component_monitor_sha256':cfg['inputs']['component_monitor']['sha256'],'resolution_sha256':verify_inputs.sha_file(stage/'resolution.json',guard),'decision_revision':resolution['decision_revision'],'groups':resolution['groups'],'elapsed_seconds':time.monotonic()-start,'limitations':['Witnesses identify current physical roots but do not prove all component geography or absence of unintended land bridges.','No seed or continent assignment is produced.']}
 with open(stage/'report.json','x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 guard();sync_dir(stage);atomic_move.move_noreplace(stage,out)
 try:sync_dir(out.parent)
 except OSError as exc:raise RuntimeError('witness output may exist; durability uncertain, inspect before retry') from exc
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('work');p.add_argument('output');a=p.parse_args()
 try:run(a.config,a.work,a.output)
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
