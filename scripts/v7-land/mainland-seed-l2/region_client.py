"""Run pinned L2 region assembly in a bounded, parent-protected child."""
import hashlib,json,os,signal,subprocess,tempfile,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
CODE=('region_worker.py','regions.py','closure_client.py','guarded_exec.py')
def execute(request,work_parent,guard,timeout_seconds=1800):
 if not callable(guard) or not 0<timeout_seconds<=1800:raise ValueError('invalid worker controls')
 work=Path(work_parent).resolve(strict=True);guard();captured={}
 c=request.get('closure',{})
 try:
  protected=(BASE,Path(c['checker_path']).resolve().parent,Path(c['contract_path']).resolve().parent,Path(c['physical_dir']).resolve())
  if c.get('terminal_checker_path'):protected=protected+(Path(c['terminal_checker_path']).resolve().parent,)
 except (TypeError,KeyError):raise ValueError('missing closure input paths')
 if any(work==d or work in d.parents or d in work.parents for d in protected):raise ValueError('region work directory overlaps inputs')
 for name in CODE:
  p=BASE/name
  with open(p,'rb') as f:data=f.read((1<<20)+1)
  if len(data)>1<<20:raise ValueError('region code exceeds size limit')
  captured[name]=data
 hashes={k:hashlib.sha256(v).hexdigest() for k,v in captured.items()}
 with tempfile.TemporaryDirectory(prefix='stage2-region-',dir=work) as t:
  d=Path(t);code=d/'code';code.mkdir();cw=d/'closure-work';cw.mkdir()
  for name,data in captured.items():(code/name).write_bytes(data)
  req=dict(request);req['closure']={**req['closure'],'work_parent':str(cw)};raw=json.dumps(req,sort_keys=True,allow_nan=False).encode()
  if len(raw)>16<<20:raise ValueError('region request exceeds size bound')
  r=d/'request.json';r.write_bytes(raw);o=d/'result.json';errpath=d/'stderr';env=os.environ.copy()
  for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[k]='1'
  with open(errpath,'w+b') as err:
   proc=subprocess.Popen(['/usr/bin/python3',str(code/'guarded_exec.py'),str(os.getpid()),str(code/'region_worker.py'),str(r),str(o)],stdout=err,stderr=err,env=env);start=time.monotonic()
   try:
    while proc.poll() is None:
     try:guard()
     except BaseException:proc.kill();proc.wait();raise
     if time.monotonic()-start>timeout_seconds:proc.kill();proc.wait();raise RuntimeError('region assembly timed out')
     time.sleep(.1)
    if proc.returncode:
     err.seek(0);raise ValueError('region assembly rejected: '+err.read(4096).decode(errors='replace'))
    if not o.is_file() or o.stat().st_size>8<<20:raise ValueError('invalid region output size')
    with open(o,'rb') as f:raw=f.read((8<<20)+1)
    if len(raw)>8<<20:raise ValueError('region output exceeds bound')
    result=json.loads(raw)
    if result.get('schema')!='stage2-region-worker-result-v1' or result.get('status')!='selected-research-region':raise ValueError('invalid region result')
    for name,digest in hashes.items():
     guard()
     if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest or hashlib.sha256((code/name).read_bytes()).hexdigest()!=digest:raise ValueError('region code changed during execution')
    result['code_sha256']=hashes;return result
   finally:
    if proc.poll() is None:proc.kill();proc.wait()
