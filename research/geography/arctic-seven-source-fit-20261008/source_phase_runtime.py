"""Narrow I/O bridge for the admitted Arctic source-fit phase runner."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path

ROOT=None
PACKET=None
PHASE=None
BASELINE=None
CANDIDATE_BYTES={}
PREDECESSOR_RECEIPTS={}
PREDECESSOR_EXECUTIONS={}
PLAN={}
PLAN_SHA256=None
OUTPUTS={}

def configure(*,root,packet,phase,baseline,candidate_bytes,predecessor_receipts,predecessor_executions,plan,plan_sha256):
 global ROOT,PACKET,PHASE,BASELINE,CANDIDATE_BYTES,PREDECESSOR_RECEIPTS,PREDECESSOR_EXECUTIONS,PLAN,PLAN_SHA256,OUTPUTS
 ROOT=Path(root); PACKET=Path(packet); PHASE=phase; BASELINE=baseline
 CANDIDATE_BYTES=dict(candidate_bytes); PREDECESSOR_RECEIPTS=dict(predecessor_receipts)
 PREDECESSOR_EXECUTIONS=dict(predecessor_executions); PLAN=plan; PLAN_SHA256=plan_sha256; OUTPUTS={}

def require_phase(name):
 if PHASE is None or PHASE.get('name')!=name:
  raise RuntimeError('Run only through the matching admitted source-fit phase wrapper')

def _relative(path):
 p=Path(path)
 candidate=Path(os.path.abspath(p if p.is_absolute() else ROOT/p))
 try: relative=candidate.relative_to(ROOT.absolute())
 except ValueError: raise ValueError('Input path escapes the repository root')
 for ancestor in [candidate,*candidate.parents]:
  if ancestor==ROOT.absolute().parent:break
  if ancestor.is_symlink():raise ValueError('Symlink in consumed input path')
 return relative.as_posix()

def read_bytes(path):
 name=_relative(path)
 if name in CANDIDATE_BYTES:
  return CANDIDATE_BYTES[name]
 if name in BASELINE.pins:
  return BASELINE.pinned_bytes(name)
 if name in PREDECESSOR_RECEIPTS:
  return PREDECESSOR_RECEIPTS[name]['bytes']
 raise ValueError('Unadmitted Arctic source-fit input: '+name)

def read_json(path):
 return json.loads(read_bytes(path))

def predecessor_execution(path):
 name=_relative(path)
 for row in PHASE.get('predecessors',[]):
  if row.get('alias')==name:
   receipt=PREDECESSOR_EXECUTIONS.get(row['path'])
   if receipt is None:raise ValueError('Predecessor execution receipt was not admitted: '+name)
   return receipt
 raise ValueError('No admitted predecessor execution receipt: '+name)

def execution_plan():
 return PLAN

def execution_plan_sha256():
 return PLAN_SHA256

def sha(raw):
 return hashlib.sha256(raw).hexdigest()

def write_packet_output(path,raw):
 if not isinstance(raw,bytes): raise TypeError('Output must be complete bytes')
 target=Path(path)
 if not target.is_absolute():target=ROOT/target
 if target.parent.absolute()!=PACKET.absolute():raise ValueError('Phase output must be in the owned packet root')
 name=target.name
 if name not in PHASE['output_names'] or name in OUTPUTS:
  raise ValueError('Unexpected or duplicate phase output: '+name)
 OUTPUTS[name]=raw

def outputs():
 expected=set(PHASE['output_names'])-{'execution-receipt.json'}
 if set(OUTPUTS)!=expected:
  raise ValueError('Phase output set differs from its frozen reservation')
 return dict(OUTPUTS)
