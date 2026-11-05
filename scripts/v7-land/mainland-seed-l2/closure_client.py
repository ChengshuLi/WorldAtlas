"""Run a pinned physical-water closure checker as an isolated subprocess."""
import hashlib,json,os,subprocess,sys,tempfile
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
class ClosureChecker:
 def __init__(self,checker_path,checker_sha256,physical_dir,physical_rows_sha256,physical_runs_sha256,contract_path,contract_sha256,work_parent,guard,terminal_checker_path=None,terminal_checker_sha256=None,physical_report_sha256=None):
  self.checker=Path(checker_path).resolve(strict=True);self.expected=checker_sha256;self.physical=Path(physical_dir).resolve(strict=True);self.rows=physical_rows_sha256;self.runs=physical_runs_sha256;self.report=physical_report_sha256;self.contract=Path(contract_path).resolve(strict=True);self.contract_sha=contract_sha256;self.work=Path(work_parent).resolve(strict=True);self.guard=guard
  self.terminal_checker=Path(terminal_checker_path).resolve(strict=True) if terminal_checker_path else None;self.terminal_expected=terminal_checker_sha256
  if bool(self.terminal_checker)!=bool(self.terminal_expected):raise ValueError('incomplete terminal checker pin')
  if not callable(guard) or not self.physical.is_dir() or not self.work.is_dir() or not isinstance(physical_report_sha256,str) or any(len(x)!=64 for x in (checker_sha256,physical_rows_sha256,physical_runs_sha256,physical_report_sha256,contract_sha256)):raise ValueError('invalid closure checker configuration')
  if self.terminal_checker and (self.work==self.terminal_checker.parent or self.work in self.terminal_checker.parents or self.terminal_checker.parent in self.work.parents):raise ValueError('closure work directory overlaps terminal checker')
  if self.work==self.physical or self.work in self.physical.parents or self.physical in self.work.parents or self.work==self.checker.parent or self.work in self.checker.parents or self.checker.parent in self.work.parents or self.work==self.contract.parent or self.work in self.contract.parents or self.contract.parent in self.work.parents:raise ValueError('closure work directory overlaps inputs')
 def _terminal(self,selected,terminals):
  if self.terminal_checker is None or not isinstance(terminals,list) or len(terminals)!=2:raise ValueError('terminal checker or endpoints missing')
  self.guard()
  if sha(self.terminal_checker,self.guard)!=self.terminal_expected or sha(self.checker,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha:raise ValueError('terminal checker code/contract pin mismatch')
  geom={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in selected]};expected_geom=geometry_hash(geom)
  with tempfile.TemporaryDirectory(prefix='terminal-check-',dir=self.work) as t:
   d=Path(t);closure=d/'closure.json';closure.write_text(json.dumps(geom,sort_keys=True,separators=(',',':'),allow_nan=False));proof=d/'proof.json';errpath=d/'stderr'
   captured_inputs={closure:closure.read_bytes()};args=[]
   for side,terminal in zip(('start','end'),terminals):
    if not isinstance(terminal,dict) or terminal.get('endpoint') not in ('start','end') or geometry_hash(terminal.get('geometry'))!=terminal.get('geometry_sha256'):raise ValueError('invalid terminal geometry')
    path=d/(side+'.json');path.write_text(json.dumps(terminal['geometry'],sort_keys=True,separators=(',',':'),allow_nan=False));captured_inputs[path]=path.read_bytes();args += ['--'+side+'-geometry',str(path),'--'+side+'-geometry-sha256',terminal['geometry_sha256'],'--'+side+'-endpoint',terminal['endpoint']]
   for source,name,digest in ((self.terminal_checker,'terminal.py',self.terminal_expected),(self.checker,'validate_water_closure_v2.py',self.expected)):
    with open(source,'rb') as f:data=f.read((1<<20)+1)
    if len(data)>1<<20 or hashlib.sha256(data).hexdigest()!=digest:raise ValueError('captured terminal checker mismatch')
    (d/name).write_bytes(data)
   env=os.environ.copy()
   cmd=[sys.executable,str(d/'terminal.py'),'--contract',str(self.contract),'--contract-sha256',self.contract_sha,'--closure',str(closure),'--closure-sha256',expected_geom,'--physical-dir',str(self.physical),*args,'--output',str(proof)]
   with open(errpath,'w+b') as err:
    p=subprocess.run(cmd,stdout=err,stderr=err,env=env)
    if p.returncode:err.seek(0);raise ValueError('terminal closure rejected: '+err.read(4096).decode(errors='replace'))
    with open(proof,'rb') as f:raw=f.read((1<<20)+1)
    if len(raw)>1<<20:raise ValueError('terminal proof exceeds bound')
    result=json.loads(raw)
    if result.get('schema')!='physical-terminal-closure-proof-v1' or result.get('status')!='valid' or result.get('geometry_sha256')!=expected_geom or result.get('physical_rows_sha256')!=self.rows or result.get('physical_runs_sha256')!=self.runs or result.get('physical_report_sha256')!=self.report or result.get('checker_sha256')!=self.terminal_expected or result.get('support_checker_sha256')!=self.expected or result.get('contract_sha256')!=self.contract_sha or result.get('no_land_land_edge_touched') is not True:raise ValueError('terminal proof pin mismatch')
    for side,ref in zip(('start','end'),terminals):
     if result.get(side+'_geometry_sha256')!=ref['geometry_sha256'] or result.get(side+'_endpoint')!=ref['endpoint']:raise ValueError('terminal proof reference mismatch')
    if sha(self.terminal_checker,self.guard)!=self.terminal_expected or sha(self.checker,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha or sha(d/'terminal.py',self.guard)!=self.terminal_expected or sha(d/'validate_water_closure_v2.py',self.guard)!=self.expected or any(path.read_bytes()!=data for path,data in captured_inputs.items()):raise ValueError('terminal checker or inputs changed during execution')
    return result
 def __call__(self,record,selected,terminals=None):
  if terminals is not None:return self._terminal(selected,terminals)
  self.guard()
  if sha(self.checker,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha:raise ValueError('closure checker code/contract pin mismatch')
  geom={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in selected]};expected_geom=geometry_hash(geom)
  with tempfile.TemporaryDirectory(prefix='closure-check-',dir=self.work) as t:
   d=Path(t);geometry=d/'geometry.json';proof=d/'proof.json';error=d/'stderr';captured=d/'checker.py'
   geometry.write_text(json.dumps(geom,sort_keys=True,separators=(',',':'),allow_nan=False));geometry_bytes=geometry.read_bytes()
   with open(self.checker,'rb') as f:source=f.read((1<<20)+1)
   if len(source)>1<<20 or hashlib.sha256(source).hexdigest()!=self.expected:raise ValueError('captured checker mismatch')
   captured.write_bytes(source);os.chmod(captured,0o500)
   env=os.environ.copy()
   with open(error,'w+b') as err:
    p=subprocess.run([sys.executable,str(captured),'--contract',str(self.contract),'--contract-sha256',self.contract_sha,'--geometry',str(geometry),'--geometry-sha256',expected_geom,'--physical-dir',str(self.physical),'--output',str(proof)],stdout=err,stderr=err,env=env)
    if p.returncode:
     err.seek(0);raise ValueError('closure checker rejected route: '+err.read(4096).decode(errors='replace'))
    if not proof.is_file() or proof.stat().st_size>1<<20:raise ValueError('invalid closure proof file')
    with open(proof,'rb') as f:proof_bytes=f.read((1<<20)+1)
    if len(proof_bytes)>1<<20:raise ValueError('invalid closure proof size')
    result=json.loads(proof_bytes)
    if result.get('schema')!='physical-water-closure-proof-v1' or result.get('status')!='valid' or result.get('geometry_sha256')!=expected_geom or result.get('physical_rows_sha256')!=self.rows or result.get('physical_runs_sha256')!=self.runs or result.get('physical_report_sha256')!=self.report or result.get('checker_sha256')!=self.expected or result.get('contract_sha256')!=self.contract_sha:raise ValueError('closure proof pin mismatch')
    if sha(self.checker,self.guard)!=self.expected or sha(captured,self.guard)!=self.expected or sha(self.contract,self.guard)!=self.contract_sha or geometry.read_bytes()!=geometry_bytes:raise ValueError('closure checker, contract or geometry changed during execution')
    return result
