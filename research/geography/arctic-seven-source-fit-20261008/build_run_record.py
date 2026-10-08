#!/usr/bin/env python3
"""Bind the completed Arctic r5 phase reservations and output receipts."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent
CAP=268435456
RECEIPT_RESERVE=4096
EXECUTION_RECEIPT_MAX=16384

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):
 target=ROOT/path
 if target.is_symlink() or not target.is_file():raise ValueError('Expected ordinary run evidence: '+path)
 return target.read_bytes()
def descriptor_check(row):
 raw=read(row['path'])
 if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('Published output drift: '+row['path'])
 return raw
def main():
 plan_raw=read('research/geography/arctic-seven-source-fit-20261008/phase-plan.json')
 if len(plan_raw)>1024*1024:raise ValueError('Oversized frozen phase plan')
 plan=json.loads(plan_raw); plan_sha=sha(plan_raw)
 if plan['execution_commit']!= 'a4649c264adbb74a4e98a36522f336604b7ba2c8':raise ValueError('Unexpected reviewed execution commit')
 if plan['cap_bytes']!=CAP:raise ValueError('Unexpected phase cap')
 pins={row['path']:row for row in plan['baseline_files']}
 if len(pins)!=len(plan['baseline_files']):raise ValueError('Duplicate whole-file plan pins')
 runtime=json.loads(read(plan['runtime']['lock_path']))
 runtime_total=runtime['total_bytes']
 if sha(read(plan['runtime']['lock_path']))!=plan['runtime']['lock_sha256']:raise ValueError('Runtime lock drift')
 rows=[]
 for phase in plan['phases']:
  prefix=phase['owned_path']+'vintages/'+phase['vintage']+'/'
  publication_raw=read(prefix+'publication.json'); pub=json.loads(publication_raw)
  execution_raw=read(prefix+'execution-receipt.json'); exe=json.loads(execution_raw)
  if len(publication_raw)>RECEIPT_RESERVE or len(execution_raw)>EXECUTION_RECEIPT_MAX:raise ValueError('Oversized phase receipt')
  if pub.get('status')!='complete' or exe.get('status')!='complete' or exe.get('phase')!=phase['name']:
   raise ValueError('Incomplete phase output: '+phase['name'])
  if exe.get('baseline_commit')!=plan['execution_commit'] or exe.get('plan_sha256')!=plan_sha:
   raise ValueError('Execution provenance mismatch: '+phase['name'])
  descriptors=pub.get('outputs',[])
  expected_names=set(phase['output_names'])
  if {Path(row['path']).name for row in descriptors}!=expected_names or len(descriptors)!=len(expected_names):
   raise ValueError('Phase output inventory mismatch: '+phase['name'])
  for descriptor in descriptors:descriptor_check(descriptor)
  unique_paths=set(phase['baseline_paths'])|set(phase['code_paths'])
  if phase.get('kind')=='native-shell':
   native_lock=pins['research/geography/arctic-seven-source-fit-20261008/native-tools-lock.json']
   archive_paths=[f'data/semantic-evidence/part-{i:02}.bin' for i in range(6)]
   planned=(sum(pins[p]['bytes'] for p in unique_paths)+len(plan_raw)*5+
    phase['native_runtime_bytes']+phase['decoded_source_bytes']+phase['scratch_reserved_bytes']+
    phase['output_reserved_bytes']+RECEIPT_RESERVE+
    sum(pins[p]['bytes'] for p in archive_paths)+
    pins['data/semantic-sources.json']['bytes']*(phase['registry_read_multiplicity']-1)+
    2*sum(pins[p]['bytes'] for p in phase['code_paths'])+native_lock['bytes'])
  else:
   unique_paths.add(plan['runtime']['lock_path'])
   planned=(sum(pins[p]['bytes'] for p in unique_paths)+len(plan_raw)+runtime_total+
    phase['decoded_source_bytes']+phase['scratch_reserved_bytes']+phase['output_reserved_bytes']+
    sum(x['max_bytes']+RECEIPT_RESERVE+EXECUTION_RECEIPT_MAX for x in phase.get('predecessors',[]))+
    RECEIPT_RESERVE)
  actual=exe['prospective_charge_bytes']
  predecessor_charge=0
  for pred in exe.get('predecessors',[]):
   output_raw=descriptor_check({'path':pred['path'],'bytes':pred['bytes'],'sha256':pred['sha256']})
   parent=Path(pred['path']).parent.as_posix()
   pred_publication=read(parent+'/publication.json'); pred_execution=read(parent+'/execution-receipt.json')
   if sha(pred_publication)!=pred['publication_sha256'] or sha(pred_execution)!=pred['execution_receipt_sha256']:
    raise ValueError('Predecessor receipt changed after phase completion: '+pred['path'])
   predecessor_charge+=len(output_raw)+len(pred_publication)+len(pred_execution)
  if planned>CAP or actual>planned or actual>CAP:raise ValueError('Phase charge exceeds the frozen reservation/cap: '+phase['name'])
  rows.append({'phase':phase['name'],'vintage':phase['vintage'],'kind':phase.get('kind','python'),
   'planned_max_bytes':planned,'actual_charged_bytes':actual,'headroom_bytes':CAP-actual,
   'predecessor_count':len(exe.get('predecessors',[])),'predecessor_charge_bytes':predecessor_charge,
   'execution_receipt':{'path':prefix+'execution-receipt.json','bytes':len(execution_raw),'sha256':sha(execution_raw)},
   'publication_receipt':{'path':prefix+'publication.json','bytes':len(publication_raw),'sha256':sha(publication_raw)},
   'output_count':len(descriptors),'outputs':[{'path':x['path'],'bytes':x['bytes'],'sha256':x['sha256']} for x in descriptors]})
  if phase.get('kind')=='python':
   reproduced=(sum(pins[p]['bytes'] for p in unique_paths)+len(plan_raw)+runtime_total+
    phase['decoded_source_bytes']+phase['scratch_reserved_bytes']+phase['output_reserved_bytes']+
    predecessor_charge+
    RECEIPT_RESERVE)
   if actual!=reproduced:raise ValueError('Observed phase accounting is not reproducible from admitted receipts: '+phase['name'])
 result={'version':1,'status':'complete','issue':1481,'execution_commit':plan['execution_commit'],
  'phase_plan_sha256':plan_sha,'cap_bytes':CAP,'runtime_lock_sha256':plan['runtime']['lock_sha256'],
  'candidate_count':plan['candidate_scope']['component_count'],
  'active_feature_count':plan['candidate_scope']['active_feature_count'],'phases':rows,
  'all_phases_under_cap':all(row['actual_charged_bytes']<=CAP for row in rows)}
 raw=(json.dumps(result,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 target=PACKET/'r5-execution-budget.json'
 if target.is_symlink():raise ValueError('Run record destination cannot be a symlink')
 if target.exists():
  if target.read_bytes()!=raw:raise FileExistsError('Preserve existing execution budget record')
 else:
  with target.open('xb') as stream:stream.write(raw)
 print(json.dumps({'status':'run-record-built','path':str(target),'bytes':len(raw),'sha256':sha(raw),
  'phase_count':len(rows),'max_actual_bytes':max(row['actual_charged_bytes'] for row in rows)},sort_keys=True))

if __name__=='__main__':main()
