#!/usr/bin/env python3
"""Temporary local harness: use unchanged PR4 orchestration/stages, staging each full R2 shard just in time."""
import datetime, hashlib, importlib.util, json, os, pathlib, subprocess, sys, threading, time
from pathlib import Path
root=Path(__file__).resolve().parent
repo=Path('/tmp/worldatlas-pr4-rerun')
script=repo/'scripts/v7-raw-mask/build_physical.py'
modspec=importlib.util.spec_from_file_location('build_physical_current',script)
bp=importlib.util.module_from_spec(modspec); modspec.loader.exec_module(bp)
manifest=json.loads((root/'inputs/manifest.json').read_text())
entries={str((root/'inputs'/x['path']).resolve()):x for x in manifest['files']}
wrangler=Path('/workspace/scratch/127991fc8b8e/recovered-tmp/memory-headroom-20261103/worldatlas-wrangler-cli/node_modules/wrangler/bin/wrangler.js')
logs=root/'logs'; logs.mkdir(exist_ok=True)
lock=threading.Lock(); counts={'download_bytes':0,'download_seconds_sum':0.0,'verification_seconds_sum':0.0,'raster_seconds_sum':0.0,'shards_completed':0}

def record(obj):
 with lock:
  with (logs/'events.jsonl').open('a') as f: f.write(json.dumps(obj,sort_keys=True)+'\n')

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def stage_run(name,*args):
 name=str(name)
 if name != 'overture/rasterize_water_shard.py':
  t=time.monotonic(); bp_run_stage(name,*args); dt=time.monotonic()-t
  record({'event':'stage','stage':name,'seconds':dt})
  return
 src=Path(args[0]).resolve(); expected=str(args[1]).lower(); dest=Path(args[3]).resolve()
 entry=entries.get(str(src))
 if not entry or entry['sha256'] != expected: raise RuntimeError('raw source path/hash not in full official manifest')
 fetch_s=verify_s=0.0
 if not src.exists():
  src.parent.mkdir(parents=True,exist_ok=True)
  partial=src.with_name(src.name+'.partial')
  if partial.exists(): raise RuntimeError(f'partial exists; inspect before retry: {partial}')
  cmd=['node',str(wrangler),'r2','object','get',f"{entry['r2_bucket']}/{entry['r2_key']}",'--file',str(partial),'--remote']
  env=os.environ.copy(); env['XDG_CONFIG_HOME']='/workspace/scratch/127991fc8b8e/.private-wrangler-config'
  logpath=logs/(src.name+'.wrangler.log')
  t=time.monotonic()
  with logpath.open('wb') as log: proc=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  fetch_s=time.monotonic()-t
  if proc.returncode:
   raise RuntimeError(f'Wrangler R2 GET failed for {entry["source_id"]}; see staging log')
  t=time.monotonic()
  size=partial.stat().st_size; sha=digest(partial)
  verify_s=time.monotonic()-t
  if size != entry['size'] or sha != expected:
   raise RuntimeError(f'R2 size/SHA mismatch for {entry["source_id"]}')
  partial.replace(src)
  with lock:
   counts['download_bytes']+=size; counts['download_seconds_sum']+=fetch_s; counts['verification_seconds_sum']+=verify_s
 else:
  t=time.monotonic(); size=src.stat().st_size; sha=digest(src); verify_s=time.monotonic()-t
  if size != entry['size'] or sha != expected: raise RuntimeError(f'existing staged file size/SHA mismatch for {entry["source_id"]}')
  with lock: counts['verification_seconds_sum']+=verify_s
  fetch_s=0.0
 t=time.monotonic()
 try: bp_run_stage(name,*args)
 except Exception: record({'event':'shard_failed','source_id':entry['source_id'],'source':str(src),'download_seconds':fetch_s,'verification_seconds':verify_s}); raise
 raster_s=time.monotonic()-t
 report_path=dest/'report.json'
 rep=json.loads(report_path.read_text())
 if rep.get('status')!='candidate-only' or rep.get('source_sha256') != expected: raise RuntimeError(f'complete shard report mismatch {entry["source_id"]}')
 # Remove only this exact, hash-verified temporary R2 copy after a complete report exists.
 src.unlink()
 with lock:
  counts['raster_seconds_sum']+=raster_s; counts['shards_completed']+=1
 record({'event':'shard_complete','source_id':entry['source_id'],'source':str(src),'size':size,'sha256':sha,'download_seconds':fetch_s,'verification_seconds':verify_s,'raster_seconds':raster_s,'output':str(dest/'water.tif'),'output_sha256':rep['output_sha256'],'deleted_staged_source':True})

bp_run_stage=bp.run_stage
bp.run_stage=stage_run
start=time.monotonic(); started=datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
 bp.run(sys.argv[1],sys.argv[2])
finally:
 elapsed=time.monotonic()-start
 result={'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pipeline_elapsed_seconds':elapsed,'download_bytes':counts['download_bytes'],'download_seconds_sum':counts['download_seconds_sum'],'verification_seconds_sum':counts['verification_seconds_sum'],'water_raster_seconds_sum':counts['raster_seconds_sum'],'shards_completed':counts['shards_completed']}
 (Path(sys.argv[2])/'staging-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
 print('STAGING_BENCHMARK '+json.dumps(result),flush=True)
