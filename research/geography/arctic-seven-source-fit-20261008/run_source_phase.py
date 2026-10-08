#!/usr/bin/env python3
"""Admit and run one frozen Arctic source-fit phase against immutable Git bytes.

This is cooperative provenance and bounded-execution tooling, not a sandbox.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, platform, re, stat, subprocess, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent
CAP=256*1024*1024
RECEIPT_RESERVE=4096
EXECUTION_RECEIPT_MAX=16384

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
GIT_EXECUTABLE=None
NATIVE_TOOLS_BYTES=0
NATIVE_TOOLS_LOCK_SHA256=None
NATIVE_TOOLS_LOCK_BYTES=0
def git(*args)->bytes:
 if GIT_EXECUTABLE is None:raise RuntimeError('Pinned Git executable has not been admitted')
 return subprocess.check_output([GIT_EXECUTABLE,'-C',str(ROOT),*args],stderr=subprocess.PIPE)
def canonical(value):return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()

def bounded_file_read(path:Path,maximum:int,*,exact:bool=False)->bytes:
 with path.open('rb') as stream:
  info=os.fstat(stream.fileno())
  if not stat.S_ISREG(info.st_mode) or info.st_size>maximum or (exact and info.st_size!=maximum):
   raise ValueError('File size/type exceeds its admitted bound: '+str(path))
  raw=stream.read(maximum+1)
  if len(raw)>maximum or (exact and len(raw)!=maximum) or stream.read(1):
   raise ValueError('File grew beyond its admitted bound: '+str(path))
  return raw

def load_native_tools(plan):
 global GIT_EXECUTABLE,NATIVE_TOOLS_BYTES,NATIVE_TOOLS_LOCK_SHA256,NATIVE_TOOLS_LOCK_BYTES
 lock_path='research/geography/arctic-seven-source-fit-20261008/native-tools-lock-r11.json'
 lock_file=ROOT/lock_path
 if lock_file.is_symlink() or not lock_file.is_file():raise ValueError('Native tools lock must be an ordinary file')
 raw=bounded_file_read(lock_file,65536)
 expected=plan.get('native_tools_lock_sha256')
 if sha(raw)!=expected:raise ValueError('Native executable lock whole-file SHA-256 mismatch')
 lock=json.loads(raw)
 if lock.get('system')!=platform.system() or lock.get('release')!=platform.release() or lock.get('machine')!=platform.machine():
  raise ValueError('Native executable host differs from the locked host')
 rows={row['path']:row for row in lock.get('files',[])}
 git_path=lock.get('commands',{}).get('git')
 if not isinstance(git_path,str) or not Path(git_path).is_absolute():raise ValueError('Native lock has no absolute Git executable')
 git_row=rows.get(git_path)
 if not git_row or git_row.get('kind')!='executable':raise ValueError('Pinned Git executable is absent from native lock inventory')
 if any(not Path(path).is_absolute() for path in rows):raise ValueError('Native runtime inventory paths must be absolute')
 if len(rows)!=len(lock.get('files',[])) or sum(row['bytes'] for row in rows.values())!=lock.get('total_bytes'):
  raise ValueError('Native executable inventory has duplicate paths or an invalid byte total')
 NATIVE_TOOLS_BYTES=lock['total_bytes']
 NATIVE_TOOLS_LOCK_SHA256=expected
 NATIVE_TOOLS_LOCK_BYTES=len(raw)
 return lock,rows

def verify_native_tools(lock,rows):
 global GIT_EXECUTABLE
 for row in rows.values():
  path=Path(row['path'])
  if path.is_symlink() or not path.is_file():raise ValueError('Locked native runtime path is not an ordinary file: '+str(path))
  body=bounded_file_read(path,row['bytes'],exact=True)
  if sha(body)!=row['sha256']:raise ValueError('Locked native executable/library drift: '+str(path))
 GIT_EXECUTABLE=lock['commands']['git']

def blob_info(commit,path):
 if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Require an immutable full baseline commit')
 row=git('ls-tree','-z',commit,'--',path).decode().rstrip('\0')
 if not row.startswith(('100644 ','100755 ')) or row[row.find('\t'):]!='\t'+path:
  raise ValueError('Expected ordinary committed file: '+path)
 oid=row.split()[2]
 size=int(git('cat-file','-s',oid))
 return oid,size

def resolve_predecessors(rows,plan,plan_sha):
 resolved=[]
 for source in rows:
  row=dict(source); target=ROOT/row['path']
  if Path(row['path']).is_absolute() or '\\' in row['path'] or any(x in ('','.','..') for x in row['path'].split('/')):
   raise ValueError('Unsafe predecessor path')
  try: rel=target.absolute().relative_to(ROOT.absolute()).as_posix()
  except ValueError:raise ValueError('Predecessor path escapes the repository')
  for ancestor in [target,*target.parents]:
   if ancestor==ROOT.parent:break
   if ancestor.is_symlink():raise ValueError('Symlink in predecessor path')
  publication=target.parent/'publication.json'; execution=target.parent/'execution-receipt.json'
  for control in [publication,execution]:
   max_size=RECEIPT_RESERVE if control==publication else EXECUTION_RECEIPT_MAX
   if control.is_symlink() or not control.is_file() or control.stat().st_size>max_size:
    raise ValueError('Missing, unsafe or oversized predecessor completion receipt')
  publication_raw=bounded_file_read(publication,RECEIPT_RESERVE)
  execution_raw=bounded_file_read(execution,EXECUTION_RECEIPT_MAX)
  pub=json.loads(publication_raw); exe=json.loads(execution_raw)
  if pub.get('status')!='complete' or exe.get('status')!='complete' or exe.get('phase')!=row['phase']:
   raise ValueError('Predecessor phase is not complete')
  if exe.get('plan_sha256')!=plan_sha or exe.get('baseline_commit')!=plan['execution_commit']:
   raise ValueError('Predecessor execution provenance mismatch')
  descriptors=[x for x in pub.get('outputs',[]) if x.get('path')==rel]
  if len(descriptors)!=1:raise ValueError('Predecessor output absent/duplicated in publication receipt')
  descriptor=descriptors[0]
  if not isinstance(descriptor.get('bytes'),int) or descriptor['bytes']>row['max_bytes']:
   raise ValueError('Predecessor output exceeds its reserved downstream bound')
  receipt_path=str(execution.relative_to(ROOT))
  if not any(x.get('path')==receipt_path and x.get('sha256')==sha(execution_raw) and x.get('bytes')==len(execution_raw) for x in pub.get('outputs',[])):
   raise ValueError('Predecessor execution receipt is not covered by its publication')
  row.update(bytes=descriptor['bytes'],sha256=descriptor['sha256'],
   publication_bytes=len(publication_raw),publication_sha256=sha(publication_raw),
   execution_receipt_bytes=len(execution_raw),execution_receipt_sha256=sha(execution_raw),
   execution_receipt=exe)
  resolved.append(row)
 return resolved

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('phase')
 parser.add_argument('--baseline',required=True)
 parser.add_argument('--plan-sha256',required=True)
 parser.add_argument('--phase-plan',default='research/geography/arctic-seven-source-fit-20261008/phase-plan-r11.json')
 args=parser.parse_args()
 plan_path=args.phase_plan
 if Path(plan_path).is_absolute() or '\\' in plan_path or any(part in ('','.','..') for part in plan_path.split('/')):
  raise ValueError('Phase-plan path must be a contained repository-relative path')
 plan_file=ROOT/plan_path
 if plan_file.is_symlink() or not plan_file.is_file():raise ValueError('Phase plan must be an ordinary workspace file')
 plan_raw=bounded_file_read(plan_file,1024*1024); plan_size=len(plan_raw)
 if sha(plan_raw)!=args.plan_sha256:raise ValueError('Phase-plan whole-file SHA-256 mismatch')
 plan=json.loads(plan_raw); phases={row['name']:row for row in plan['phases']}
 native_lock,native_rows=load_native_tools(plan)
 if len(phases)!=len(plan['phases']) or len({row['path'] for row in plan['baseline_files']})!=len(plan['baseline_files']):
  raise ValueError('Phase plan names and baseline paths must be unique')
 if plan.get('cap_bytes')!=CAP or plan.get('receipt_reserve_bytes')!=RECEIPT_RESERVE:
  raise ValueError('Phase plan byte-cap policy differs from the reviewed runner')
 if plan['execution_commit']!=args.baseline:raise ValueError('Plan execution commit differs from requested immutable baseline')
 phase=phases[args.phase]
 if phase['name']!=args.phase:raise ValueError('Phase identity mismatch')
 if phase.get('kind','python')!='python':raise ValueError('Native shell phase must use its separately admitted native entry point')
 all_files={row['path']:row for row in plan['baseline_files']}
 runtime_lock_path=plan['runtime']['lock_path']; lock_desc=all_files[runtime_lock_path]
 runtime_total=int(phase['runtime_bytes'])
 native_lock_path='research/geography/arctic-seven-source-fit-20261008/native-tools-lock-r11.json'
 if native_lock_path not in all_files or all_files[native_lock_path]['bytes']!=NATIVE_TOOLS_LOCK_BYTES or all_files[native_lock_path]['sha256']!=plan['native_tools_lock_sha256']:
  raise ValueError('Native-tools lock is absent from or differs from the frozen baseline inventory')
 if NATIVE_TOOLS_BYTES!=phase['native_runtime_bytes'] or NATIVE_TOOLS_LOCK_BYTES!=phase['native_tools_lock_revalidation_bytes']:
  raise ValueError('Native runtime byte total differs from the reviewed phase reservation')
 decoded=int(phase['decoded_source_bytes']); scratch=int(phase['scratch_reserved_bytes'])
 output_reserve=int(phase['output_reserved_bytes'])
 phase_paths=set(phase['baseline_paths'])|set(phase['code_paths'])|{runtime_lock_path,native_lock_path}
 if not phase_paths<=set(all_files):raise ValueError('Phase references an unpinned baseline path')
 baseline_total=sum(all_files[p]['bytes'] for p in phase_paths)
 predecessor_rows=resolve_predecessors(phase.get('predecessors',[]),plan,sha(plan_raw))
 predecessor_total=sum(row['bytes']+row['publication_bytes']+row['execution_receipt_bytes'] for row in predecessor_rows)
 prospective=(baseline_total+NATIVE_TOOLS_LOCK_BYTES+plan_size+runtime_total+NATIVE_TOOLS_BYTES+decoded+scratch+output_reserve+
              predecessor_total+RECEIPT_RESERVE)
 if prospective>CAP:raise ValueError(f'Prospective phase exceeds 256 MiB before input reads: {prospective}')

 # Verify the full native executable closure before Git reads source objects.
 verify_native_tools(native_lock,native_rows)
 if git('rev-parse','HEAD').decode().strip()!=args.baseline:raise ValueError('Runner checkout HEAD differs from its frozen execution commit')
 byte_counts={}
 for path,row in all_files.items():
  oid,size=blob_info(args.baseline,path)
  if size!=row['bytes']:raise ValueError('Git blob byte count differs from plan: '+path)
  byte_counts[path]=size
 native_oid,native_size=blob_info(args.baseline,native_lock_path)
 if native_size!=all_files[native_lock_path]['bytes'] or sha(git('cat-file','blob',native_oid))!=plan['native_tools_lock_sha256']:
  raise ValueError('Native tools lock differs from the frozen execution commit')
 lock_oid,lock_size=blob_info(args.baseline,runtime_lock_path)
 runtime_lock_raw=git('cat-file','blob',lock_oid)
 if lock_size!=lock_desc['bytes'] or sha(runtime_lock_raw)!=plan['runtime']['lock_sha256']:
  raise ValueError('Runtime lock differs from the frozen execution commit')
 runtime_lock=json.loads(runtime_lock_raw); runtime_files=runtime_lock['files']
 if sum(row['bytes'] for row in runtime_files)!=runtime_total or len({row['path'] for row in runtime_files})!=len(runtime_files):
  raise ValueError('Runtime inventory differs from its preflight byte reservation')

 # Runtime inventory is checked before imports of GIS packages or phase code.
 for row in runtime_files:
  path=Path(row['path'])
  if row['kind']=='symlink':
   if not path.is_symlink():raise ValueError('Runtime symlink drift: '+str(path))
   raw=str(path.readlink()).encode()
   if raw.decode()!=row.get('target'):raise ValueError('Runtime symlink target drift: '+str(path))
  elif row['kind']=='file':
   if path.is_symlink() or not path.is_file():raise ValueError('Runtime inventory path is not an ordinary file: '+str(path))
   raw=bounded_file_read(path,row['bytes'],exact=True)
  else:raise ValueError('Unknown runtime inventory entry kind')
  if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('Installed runtime drift: '+str(path))
 locked_paths={Path(row['path']).resolve() for row in runtime_files}
 if Path(sys.executable).resolve() not in locked_paths:raise ValueError('Executing interpreter is outside the locked runtime')
 if runtime_lock.get('python_version')!=sys.version.split()[0]:raise ValueError('Python version differs from locked runtime')
 if runtime_lock.get('python_prefix')!=sys.prefix or runtime_lock.get('python_base_prefix')!=sys.base_prefix:
  raise ValueError('Python environment differs from locked prefix')
 if runtime_lock.get('platform')!=platform.platform() or runtime_lock.get('machine')!=platform.machine():
  raise ValueError('Operating-system platform differs from locked runtime')

 # Verify the fresh output destination before loading baseline inputs or GIS.
 immutable_row=all_files['scripts/evidence/immutable.py']
 immutable_oid,_=blob_info(args.baseline,immutable_row['path'])
 immutable_raw=git('cat-file','blob',immutable_oid)
 if sha(immutable_raw)!=immutable_row['sha256']:raise ValueError('Shared immutable helper pin mismatch')
 immutable=types.ModuleType('worldatlas_immutable')
 exec(compile(immutable_raw,immutable_row['path'],'exec'),immutable.__dict__)
 class CapturedBaseline(immutable.Baseline):
  """Cache authenticated Git blobs so repeated phase access reads each once."""
  def __init__(self,*args,**kwargs):
   repo=args[0] if args else kwargs.get('repo')
   if repo is None or Path(repo).resolve()!=ROOT.resolve():
    raise ValueError('Captured baseline repository differs from the admitted checkout')
   self._captured={}
   super().__init__(*args,**kwargs)
  def _git(self,*git_args):
   if Path(self.repo).resolve()!=ROOT.resolve():
    raise ValueError('Captured baseline repository changed after admission')
   return git(*git_args)
  def read(self,name):
   if name not in self._captured:self._captured[name]=super().read(name)
   return self._captured[name]
 files=[row for row in plan['baseline_files'] if row['path'] in phase_paths]
 runner_row=all_files['research/geography/arctic-seven-source-fit-20261008/run_source_phase.py']
 runner_oid,_=blob_info(args.baseline,runner_row['path'])
 runner_baseline=git('cat-file','blob',runner_oid)
 if sha(runner_baseline)!=runner_row['sha256'] or sha(bounded_file_read(ROOT/runner_row['path'],runner_row['bytes'],exact=True))!=runner_row['sha256']:
  raise ValueError('Executed runner differs from the frozen code commit')
 input_budget=CAP-NATIVE_TOOLS_LOCK_BYTES-plan_size-runtime_total-NATIVE_TOOLS_BYTES-decoded-scratch-output_reserve-predecessor_total-RECEIPT_RESERVE
 complete_payload_budget=CAP-NATIVE_TOOLS_LOCK_BYTES-plan_size-runtime_total-NATIVE_TOOLS_BYTES-decoded-scratch-predecessor_total-RECEIPT_RESERVE
 if input_budget<=0:raise ValueError('No phase input budget remains after prospective reservations')
 immutable.admit_destination(types.SimpleNamespace(repo=str(ROOT)),phase['owned_path'],phase['vintage'],phase['output_names'])
 baseline=CapturedBaseline(ROOT,args.baseline,files,max_phase_bytes=input_budget)
 # The initial limit reserves the full declared output envelope before any
 # source body is admitted. Publication then checks actual payload bytes
 # against the cap after all fixed runtime, plan, predecessor and decode costs.
 baseline.max_phase_bytes=complete_payload_budget
 vintage=immutable.NewVintage(baseline,phase['owned_path'],phase['vintage'],phase['output_names'])
 candidate_bytes={}
 for path in phase.get('candidate_paths',[]):candidate_bytes[path]=baseline.pinned_bytes(path)
 predecessor_receipts={}; predecessor_executions={}
 for row in predecessor_rows:
  path=ROOT/row['path']
  if path.is_symlink():raise ValueError('Predecessor output is a symlink: '+row['path'])
  raw=bounded_file_read(path,row['bytes'],exact=True)
  if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:
   raise ValueError('Predecessor output drift: '+row['path'])
  predecessor_receipts[row['path']]={'bytes':raw,'sha256':row['sha256']}
  if row.get('alias'):candidate_bytes[row['alias']]=raw
  predecessor_executions[row['path']]=row['execution_receipt']

 module_names=phase['modules']
 modules=baseline.load_modules(module_names)
 bridge=modules['source_phase_runtime']
 bridge.configure(root=ROOT,packet=PACKET,phase=phase,baseline=baseline,
                  candidate_bytes=candidate_bytes,predecessor_receipts=predecessor_receipts,
                  predecessor_executions=predecessor_executions,plan=plan,plan_sha256=sha(plan_raw))
 for name in phase.get('required_import_roots',[]):
  spec=importlib.util.find_spec(name)
  origin=(spec.origin if spec else None)
  allowed=[Path(row['path']).resolve() for row in runtime_files]
  if not origin or Path(origin).resolve() not in allowed:
   raise ValueError('Required installed import is outside the locked runtime: '+name)

 old_argv=sys.argv[:]
 try:
  sys.argv=[phase['entry_module']+'.py',*phase.get('entry_args',[])]
  modules[phase['entry_module']].main()
 finally:sys.argv=old_argv
 for module in tuple(sys.modules.values()):
  spec=getattr(module,'__spec__',None); origin=getattr(spec,'origin',None) or getattr(module,'__file__',None)
  if not isinstance(origin,str) or origin in ('built-in','frozen'):continue
  origin_path=Path(origin).resolve()
  try:origin_path.relative_to(ROOT.resolve()); continue
  except ValueError:pass
  if '.zip/' in origin:
   archive=Path(origin.split('.zip/',1)[0]+'.zip').resolve()
   if archive not in locked_paths:raise ValueError('Executed module archive is outside the locked runtime: '+origin)
  elif origin_path.exists() and origin_path not in locked_paths:
   raise ValueError('Executed installed module is outside the locked runtime: '+str(origin_path))
 outputs=bridge.outputs()
 receipt={'version':1,'status':'complete','phase':phase['name'],'baseline_commit':args.baseline,
  'plan_sha256':sha(plan_raw),'runtime_lock_sha256':sha(runtime_lock_raw),
  'native_tools_lock_sha256':NATIVE_TOOLS_LOCK_SHA256,'native_runtime_bytes':NATIVE_TOOLS_BYTES,
  'native_tools_lock_revalidation_bytes':NATIVE_TOOLS_LOCK_BYTES,
  'prospective_charge_bytes':prospective,'actual_baseline_input_bytes':sum(baseline.consumed.values()),
  'runtime_bytes':runtime_total,'decoded_source_reservation_bytes':decoded,
  'scratch_reserved_bytes':scratch,'output_reserved_bytes':output_reserve,
  'baseline_inputs':[{'path':name,'bytes':row['bytes'],'sha256':row['sha256']}
   for name,row in sorted(baseline.pins.items())],
  'predecessors':[{'path':x['path'],'bytes':x['bytes'],'sha256':x['sha256'],
   'publication_sha256':x['publication_sha256'],'execution_receipt_sha256':x['execution_receipt_sha256']}
   for x in predecessor_rows]}
 outputs['execution-receipt.json']=canonical(receipt)
 vintage.publish_bytes(outputs)
 print(json.dumps({'status':'complete','phase':phase['name'],'prospective_bytes':prospective,
   'output_bytes':sum(map(len,outputs.values())),'vintage':phase['vintage']},sort_keys=True))

if __name__=='__main__':main()
