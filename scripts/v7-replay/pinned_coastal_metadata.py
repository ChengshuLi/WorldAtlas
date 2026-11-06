"""Same-descriptor JSON verification for legacy direct-land research.

Reject all other lineage schemas rather than downgrading their checks.
"""
import hashlib,json,os,stat
from pathlib import Path

def digest_ok(v):return isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)

def pinned_bytes(path,expected):
 if not digest_ok(expected):raise ValueError('invalid metadata pin')
 fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode):raise ValueError('metadata is not regular')
  chunks=[];total=0;h=hashlib.sha256()
  while True:
   z=os.read(fd,1024*1024)
   if not z:break
   total+=len(z)
   if total>before.st_size:raise ValueError('metadata changed during read')
   chunks.append(z);h.update(z)
  after=os.fstat(fd)
  if total!=before.st_size or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or h.hexdigest()!=expected:raise ValueError('metadata changed or hash mismatch')
  return b''.join(chunks)
 finally:os.close(fd)

def pinned_json(path,expected):return json.loads(pinned_bytes(path,expected))

def file_sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def validate_physical(doc,physical,grid):
 out=doc.get('physical_output_sha256',doc.get('output_sha256',{}))
 if doc.get('status')!='candidate-only' or doc.get('grid')!=grid or out.get('rows.u32le')!=physical['rows_sha256'] or out.get('runs.u32le')!=physical['runs_sha256']:raise ValueError('physical report grid or output mismatch')
 if all(k in doc for k in ('physical_output_sha256','source_manifest','land_config','water_config','stage_reports')):
  for item in (doc['source_manifest'],doc['land_config'],doc['water_config']):
   if not isinstance(item,dict) or not item.get('path') or not digest_ok(item.get('sha256')):raise ValueError('raw physical source pins missing')
 else:
  inputs=doc.get('inputs',{})
  if not digest_ok(doc.get('configuration_sha256')) or any(not isinstance(inputs.get(k),dict) or not digest_ok(inputs[k].get('sha256')) or not inputs[k].get('path') for k in ('land','water')):raise ValueError('physical source pins missing')

def validate_legacy_direct(doc,report_path,physical,land,snapshot_hash,revision,root,grid):
 # No streaming, nearest or mixed report is accepted by this narrow mode.
 if doc.get('schema')!='direct-neon-land-build-report-v1':raise ValueError('unsupported land lineage; legacy direct only')
 root=Path(root).resolve();base=Path(report_path).resolve().parent;config_path=(base/'config.json').resolve()
 if not config_path.is_relative_to(root):raise ValueError('land config outside input root')
 config=pinned_json(config_path,doc.get('config_sha256'))
 verified=doc.get('component_verification',{})
 for name,key in (('component-builder','builder_binary_sha256'),('verified-component-rows.u32le','rows_sha256'),('verified-component-runs.u32le','runs_sha256')):
  artifact=(base/name).resolve()
  if not artifact.is_relative_to(root) or not artifact.is_file() or not digest_ok(verified.get(key)) or file_sha(artifact)!=verified[key]:raise ValueError('component artifact pin mismatch')
 if config.get('grid')!=grid or config.get('snapshot',{}).get('sha256')!=snapshot_hash or config.get('physical_rows',{}).get('sha256')!=physical['rows_sha256'] or config.get('physical_runs',{}).get('sha256')!=physical['runs_sha256']:raise ValueError('direct land configuration mismatch')
 comp=doc.get('compiler_report',{});pins=comp.get('input_sha256',{})
 if (not all(digest_ok(verified.get(k)) for k in ('builder_source_sha256','builder_binary_sha256','rows_sha256','runs_sha256')) or not verified.get('compiler_version') or not verified.get('builder_output') or verified.get('rows_sha256')!=pins.get('component_rows') or verified.get('runs_sha256')!=pins.get('component_runs') or doc.get('status')!='unverified-research-not-published' or doc.get('snapshot_sha256')!=snapshot_hash or doc.get('decision_revision')!=revision.get('id') or doc.get('decision_revision_asserted_status')!=revision.get('status') or doc.get('entity_revision')!=revision.get('entity_revision') or comp.get('schema')!='land-decision-compiler-prototype-report-v1' or pins.get('physical_rows')!=physical['rows_sha256'] or pins.get('physical_runs')!=physical['runs_sha256'] or comp.get('output_rows_sha256')!=land['rows_sha256'] or comp.get('output_runs_sha256')!=land['runs_sha256']):raise ValueError('direct land lineage mismatch')
 if land['resolved_rows']!=(base/'land/rows.u32le').resolve() or land['resolved_runs']!=(base/'land/runs.u32le').resolve():raise ValueError('direct land output location mismatch')
