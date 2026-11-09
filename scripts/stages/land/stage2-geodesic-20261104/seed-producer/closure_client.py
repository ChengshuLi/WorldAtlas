"""Directly run pinned closure checkers and validate their proofs."""
import contextlib,hashlib,io,json,os,runpy,sys,tempfile
from pathlib import Path
from regions import geometry_hash

def sha(path,guard):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()

def _run_checker(script,args,log_path):
 old=sys.argv[:];sys.argv=[str(script),*map(str,args)]
 try:
  with open(log_path,'w+') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
   try:runpy.run_path(str(script),run_name='__main__')
   except SystemExit as exc:
    if exc.code not in (None,0):
     log.flush();log.seek(0);raise ValueError('closure checker rejected: '+log.read(4096))
 finally:sys.argv=old
class ClosureChecker:
 def __init__(self,checker_path,checker_sha256,physical_dir,physical_rows_sha256,physical_runs_sha256,contract_path,contract_sha256,work_parent,guard,terminal_checker_path=None,terminal_checker_sha256=None):
  self.checker=Path(checker_path).resolve(strict=True);self.expected=checker_sha256;self.physical=Path(physical_dir).resolve(strict=True);self.rows=physical_rows_sha256;self.runs=physical_runs_sha256;self.contract=Path(contract_path).resolve(strict=True);self.contract_sha=contract_sha256;self.work=Path(work_parent).resolve(strict=True);self.guard=guard
  self.terminal_checker=Path(terminal_checker_path).resolve(strict=True) if terminal_checker_path else None;self.terminal_expected=terminal_checker_sha256
  if bool(self.terminal_checker)!=bool(self.terminal_expected):raise ValueError('incomplete terminal checker pin')
  if not callable(guard) or not self.physical.is_dir() or not self.work.is_dir() or any(len(x)!=64 for x in (checker_sha256,physical_rows_sha256,physical_runs_sha256,contract_sha256)):raise ValueError('invalid closure checker configuration')
  if self.terminal_checker and (self.work==self.terminal_checker.parent or self.work in self.terminal_checker.parents or self.terminal_checker.parent in self.work.parents):raise ValueError('closure work directory overlaps terminal checker')
  if self.work==self.physical or self.work in self.physical.parents or self.physical in self.work.parents or self.work==self.checker.parent or self.work in self.checker.parents or self.checker.parent in self.work.parents or self.work==self.contract.parent or self.work in self.contract.parents or self.contract.parent in self.work.parents:raise ValueError('closure work directory overlaps inputs')
 def _terminal(self,selected,terminals):
  if self.terminal_checker is None or not isinstance(terminals,list) or len(terminals)!=2:raise ValueError('terminal checker or endpoints missing')
  self.guard()
  if sha(self.terminal_checker,self.guard)!=self.terminal_expected or sha(self.checker,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha:raise ValueError('terminal checker code/contract pin mismatch')
  geom={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in selected]};expected_geom=geometry_hash(geom)
  with tempfile.TemporaryDirectory(prefix='terminal-check-',dir=self.work) as t:
   d=Path(t);closure=d/'closure.json';closure.write_text(json.dumps(geom,sort_keys=True,separators=(',',':'),allow_nan=False));proof=d/'proof.json';log=d/'checker.log';captured_inputs={closure:closure.read_bytes()};args=[]
   for side,terminal in zip(('start','end'),terminals):
    if not isinstance(terminal,dict) or terminal.get('endpoint') not in ('start','end') or geometry_hash(terminal.get('geometry'))!=terminal.get('geometry_sha256'):raise ValueError('invalid terminal geometry')
    path=d/(side+'.json');path.write_text(json.dumps(terminal['geometry'],sort_keys=True,separators=(',',':'),allow_nan=False));captured_inputs[path]=path.read_bytes();args += ['--'+side+'-geometry',str(path),'--'+side+'-geometry-sha256',terminal['geometry_sha256'],'--'+side+'-endpoint',terminal['endpoint']]
   checker_copy=d/'terminal.py';support_copy=d/'validate_water_closure_v2.py'
   for source,target,digest in ((self.terminal_checker,checker_copy,self.terminal_expected),(self.checker,support_copy,self.expected)):
    data=source.read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('captured terminal checker mismatch')
    target.write_bytes(data)
   _run_checker(checker_copy,['--contract',self.contract,'--contract-sha256',self.contract_sha,'--closure',closure,'--closure-sha256',expected_geom,'--physical-dir',self.physical,*args,'--output',proof],log)
   result=json.loads(proof.read_bytes())
   if result.get('schema')!='physical-terminal-closure-proof-v1' or result.get('status')!='valid' or result.get('geometry_sha256')!=expected_geom or result.get('physical_rows_sha256')!=self.rows or result.get('physical_runs_sha256')!=self.runs or result.get('checker_sha256')!=self.terminal_expected or result.get('support_checker_sha256')!=self.expected or result.get('contract_sha256')!=self.contract_sha or result.get('no_land_land_edge_touched') is not True:raise ValueError('terminal proof pin mismatch')
   for side,ref in zip(('start','end'),terminals):
    if result.get(side+'_geometry_sha256')!=ref['geometry_sha256'] or result.get(side+'_endpoint')!=ref['endpoint']:raise ValueError('terminal proof reference mismatch')
   if sha(self.terminal_checker,self.guard)!=self.terminal_expected or sha(self.checker,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha or sha(checker_copy,self.guard)!=self.terminal_expected or sha(support_copy,self.guard)!=self.expected or any(path.read_bytes()!=data for path,data in captured_inputs.items()):raise ValueError('terminal checker or inputs changed during execution')
   return result
 def __call__(self,record,selected,terminals=None):
  if terminals is not None:return self._terminal(selected,terminals)
  self.guard()
  if sha(self.checker,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha:raise ValueError('closure checker code/contract pin mismatch')
  geom={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in selected]};expected_geom=geometry_hash(geom)
  with tempfile.TemporaryDirectory(prefix='closure-check-',dir=self.work) as t:
   d=Path(t);geometry=d/'geometry.json';proof=d/'proof.json';log=d/'checker.log';captured=d/'checker.py'
   geometry.write_text(json.dumps(geom,sort_keys=True,separators=(',',':'),allow_nan=False));geometry_bytes=geometry.read_bytes();source=self.checker.read_bytes()
   if hashlib.sha256(source).hexdigest()!=self.expected:raise ValueError('captured checker mismatch')
   captured.write_bytes(source);os.chmod(captured,0o500)
   _run_checker(captured,['--contract',self.contract,'--contract-sha256',self.contract_sha,'--geometry',geometry,'--geometry-sha256',expected_geom,'--physical-dir',self.physical,'--output',proof],log)
   proof_bytes=proof.read_bytes()
   result=json.loads(proof_bytes)
   if result.get('schema')!='physical-water-closure-proof-v1' or result.get('status')!='valid' or result.get('geometry_sha256')!=expected_geom or result.get('physical_rows_sha256')!=self.rows or result.get('physical_runs_sha256')!=self.runs or result.get('checker_sha256')!=self.expected or result.get('contract_sha256')!=self.contract_sha:raise ValueError('closure proof pin mismatch')
   if sha(self.checker,self.guard)!=self.expected or sha(captured,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha or geometry.read_bytes()!=geometry_bytes:raise ValueError('closure checker, contract or geometry changed during execution')
   return result
