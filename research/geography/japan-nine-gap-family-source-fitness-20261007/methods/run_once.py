"""Run one exact frozen full overlay once; never retries a failed execution."""
import argparse,datetime,hashlib,json,os,pathlib,platform,subprocess,sys,time
import shapely,pyproj,numpy
ROOT=pathlib.Path(__file__).resolve().parents[1];REPO=ROOT.parents[2]
FREEZE_PATH=ROOT/'inputs/runtime-freeze.json';MAX=33554432
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args],stderr=subprocess.PIPE)
def safe(rel):
 p=pathlib.PurePosixPath(rel)
 if p.is_absolute() or '\\' in rel or any(x in ('','.','..') for x in rel.split('/')):raise ValueError('unsafe run path')
 return p
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execution',required=True);ap.add_argument('--run',required=True,choices=['one','two']);ap.add_argument('--output',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--log',required=True);a=ap.parse_args()
 if len(a.execution)!=40 or any(c not in '0123456789abcdef' for c in a.execution):raise ValueError('exact lowercase 40-hex freeze commit required')
 if git('rev-parse','HEAD').decode().strip()!=a.execution:raise ValueError('HEAD must equal the exact frozen execution commit')
 freeze_raw=FREEZE_PATH.read_bytes();freeze=json.loads(freeze_raw)
 if git('show',f"{a.execution}:research/geography/japan-nine-gap-family-source-fitness-20261007/inputs/runtime-freeze.json")!=freeze_raw:raise ValueError('runtime freeze manifest differs from exact execution commit')
 if len(freeze.get('data_baseline_commit',''))!=40 or freeze['schema']!='japan-nine-source-overlay-freeze-v1':raise ValueError('invalid freeze manifest or source baseline')
 if (sys.version!=freeze['runtime']['python_version'] or str(pathlib.Path(sys.executable).resolve())!=freeze['runtime']['python_executable'] or shapely.__version__!=freeze['runtime']['shapely'] or shapely.geos_version_string!=freeze['runtime']['geos'] or pyproj.__version__!=freeze['runtime']['pyproj'] or pyproj.proj_version_str!=freeze['runtime']['proj'] or numpy.__version__!=freeze['runtime']['numpy']):raise ValueError('runtime versions differ from freeze')
 # Every executed source module must be exactly the committed/frozen ordinary body.
 code_checks=[]
 for d in freeze['code_files']:
  committed=git('show',f"{a.execution}:{d['path']}")
  current=(REPO/d['path']).read_bytes()
  if len(committed)!=d['bytes'] or sha(committed)!=d['sha256'] or current!=committed:raise ValueError('executed code differs from freeze: '+d['path'])
  code_checks.append({'path':d['path'],'bytes':len(current),'sha256':sha(current)})
 # Whole unchanged baseline input bodies, with gzip whole and decoded digests.
 baseline_checks=[]
 for d in freeze['baseline_inputs']:
  raw=git('show',f"{freeze['data_baseline_commit']}:{d['path']}")
  if len(raw)!=d['bytes'] or sha(raw)!=d['sha256']:raise ValueError('baseline input body differs: '+d['path'])
  if 'uncompressed_sha256' in d:
   import gzip
   unpacked=gzip.decompress(raw)
   if len(unpacked)!=d['uncompressed_bytes'] or sha(unpacked)!=d['uncompressed_sha256']:raise ValueError('baseline decoded input differs: '+d['path'])
  baseline_checks.append(d['path'])
 candidate_checks=[]
 for d in freeze['candidate_inputs']:
  p=REPO/d['path'];raw=p.read_bytes()
  if len(raw)!=d['bytes'] or sha(raw)!=d['sha256']:raise ValueError('candidate input body differs: '+d['path'])
  candidate_checks.append(d['path'])
 for d in freeze['external_inputs']:
  p=REPO/d['path'];h=hashlib.sha256();n=0
  with p.open('rb') as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block);n+=len(block)
  if n!=d['bytes'] or h.hexdigest()!=d['sha256']:raise ValueError('external restoration-only source differs: '+d['path'])
 runtime_checks=[]
 for d in freeze['runtime']['files']:
  p=pathlib.Path(d['path']);raw=p.read_bytes()
  if len(raw)!=d['bytes'] or sha(raw)!=d['sha256']:raise ValueError('runtime file changed: '+d['path'])
  runtime_checks.append(d['path'])
 output_rel=safe(a.output);receipt_rel=safe(a.receipt);log_rel=safe(a.log)
 if a.run=='one':
  expected=('research/geography/japan-nine-gap-family-source-fitness-20261007/results/source-overlays.json','research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-one.json','research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-one.log')
 else:
  expected=('.cache/japan-nine-gap-run-two/source-overlays.json','research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-two.json','research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-two.log')
 if (str(output_rel),str(receipt_rel),str(log_rel))!=expected:raise ValueError('run-specific output/receipt/log paths differ')
 out=REPO/str(output_rel);rec=REPO/str(receipt_rel);log=REPO/str(log_rel)
 if out.exists() or rec.exists() or log.exists():raise ValueError('run output/receipt/log path already exists; each attempt is single-use')
 out.parent.mkdir(parents=True,exist_ok=True);rec.parent.mkdir(parents=True,exist_ok=True);log.parent.mkdir(parents=True,exist_ok=True)
 command=[freeze['runtime']['python_executable'],'-B',str(REPO/'research/geography/japan-nine-gap-family-source-fitness-20261007/methods/producer.py'),str(out)]
 env=os.environ.copy();env.update({'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','PROJ_NETWORK':'OFF'})
 start=utc();mono=time.monotonic();proc=subprocess.Popen(command,cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 pid=proc.pid;captured=proc.communicate()[0];code=proc.returncode;end=utc();elapsed=time.monotonic()-mono
 log.write_bytes(captured)
 out_bytes=out.read_bytes() if out.exists() else b''
 if out.exists() and len(out_bytes)>MAX:raise ValueError('complete output exceeds ordinary file bound')
 receipt={'schema':'japan-source-overlay-execution-v1','run':a.run,'status':'complete' if code==0 and out.exists() else 'failed','execution_commit':a.execution,'freeze_manifest_sha256':sha(freeze_raw),'command':command,'working_directory':'repository root','environment_overrides':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','PROJ_NETWORK':'OFF'},'start_utc':start,'end_utc':end,'elapsed_seconds':elapsed,'pid':pid,'exit_code':code,'log_path':str(log_rel),'log_bytes':len(captured),'log_sha256':sha(captured),'output_path':str(output_rel),'output_bytes':len(out_bytes),'output_sha256':sha(out_bytes) if out_bytes else None,'executed_code':code_checks,'baseline_input_count':len(baseline_checks),'baseline_input_paths_sha256':sha(json.dumps(baseline_checks,separators=(',',':')).encode()),'candidate_input_count':len(candidate_checks),'candidate_input_paths_sha256':sha(json.dumps(candidate_checks,separators=(',',':')).encode()),'external_input_count':len(freeze['external_inputs']),'runtime_file_count':len(runtime_checks),'runtime_versions':{k:freeze['runtime'][k] for k in ('python_version','platform','shapely','geos','pyproj','proj','numpy')}}
 rec.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(receipt,ensure_ascii=False))
 if receipt['status']!='complete':raise SystemExit(code if code else 1)
if __name__=='__main__':main()
