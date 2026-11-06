"""Direct invocation of pinned region assembly, with independent result checks."""
import hashlib
import json
import sys
from pathlib import Path

BASE=Path(__file__).resolve().parent
CODE=('region_worker.py','regions.py','closure_client.py')

def execute(request,work_parent,guard):
 if not callable(guard):raise ValueError('invalid worker guard')
 work=Path(work_parent).resolve(strict=True);guard();captured={}
 c=request.get('closure',{})
 try:
  protected=(BASE,Path(c['checker_path']).resolve().parent,Path(c['contract_path']).resolve().parent,Path(c['physical_dir']).resolve())
  if c.get('terminal_checker_path'):protected+=(Path(c['terminal_checker_path']).resolve().parent,)
 except (TypeError,KeyError):raise ValueError('missing closure input paths')
 if any(work==d or work in d.parents or d in work.parents for d in protected):raise ValueError('region work directory overlaps inputs')
 for name in CODE:
  p=BASE/name
  data=p.read_bytes()
  if len(data)>1<<20:raise ValueError('region code exceeds size limit')
  captured[name]=hashlib.sha256(data).hexdigest()
 req=dict(request);req['closure']={**c,'work_parent':str(work)}
 raw=json.dumps(req,sort_keys=True,allow_nan=False).encode()
 if len(raw)>16<<20:raise ValueError('region request exceeds size bound')
 import runpy
 old_path=list(sys.path)
 try:
  sys.path.insert(0,str(BASE))
  namespace=runpy.run_path(str(BASE/'region_worker.py'))
  result=namespace['execute'](req,guard=guard)
 finally:sys.path[:]=old_path
 if result.get('schema')!='stage2-region-worker-result-v1' or result.get('status')!='selected-research-region':raise ValueError('invalid region result')
 for name,digest in captured.items():
  guard()
  if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest:raise ValueError('region code changed during execution')
 result['code_sha256']=captured
 return result
