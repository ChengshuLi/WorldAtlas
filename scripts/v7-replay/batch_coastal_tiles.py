#!/usr/bin/env python3
"""Research-only WGS84 coastal tiles using a single sealed input generation.

Linux memfd seals prevent writes, growth, shrinking and further seal changes.
A batch-complete record is written only after every tile and metadata recheck.
"""
from __future__ import annotations
import argparse,contextlib,fcntl,hashlib,json,math,os,stat
from pathlib import Path
import numpy as np
import build_coastal_tile as tile
import decision_snapshot,exclusive_outputs,pinned_coastal_metadata
from decision_snapshot import validate_revision
from pinned_coastal_metadata import pinned_bytes,pinned_json,validate_physical,validate_legacy_direct
from exclusive_outputs import create_directory_exclusive,write_json_exclusive

F_SEALS=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def sealed_copy(path,expected):
 """Return a sealed memfd holding precisely the SHA-pinned input bytes."""
 if not isinstance(expected,str) or len(expected)!=64 or any(x not in '0123456789abcdef' for x in expected):raise ValueError('invalid SHA-256')
 if not hasattr(os,'memfd_create') or not hasattr(os,'MFD_ALLOW_SEALING'):raise RuntimeError('Linux sealing-enabled memfd is required')
 source=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0));target=None
 try:
  st=os.fstat(source)
  if not stat.S_ISREG(st.st_mode):raise ValueError('source is not regular')
  target=os.memfd_create('worldatlas-pinned-input',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING);h=hashlib.sha256();total=0
  while True:
   b=os.read(source,1024*1024)
   if not b:break
   total+=len(b)
   if total>st.st_size:raise ValueError('source grew during copy')
   h.update(b);view=memoryview(b)
   while view:
    n=os.write(target,view)
    if n<=0:raise OSError('short memfd write')
    view=view[n:]
  aft=os.fstat(source)
  if total!=st.st_size or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)!=(aft.st_dev,aft.st_ino,aft.st_size,aft.st_mtime_ns) or h.hexdigest()!=expected:raise ValueError('source changed or SHA-256 mismatch')
  fcntl.fcntl(target,fcntl.F_ADD_SEALS,F_SEALS)
  if fcntl.fcntl(target,fcntl.F_GET_SEALS)&F_SEALS!=F_SEALS:raise RuntimeError('seals not established')
  os.lseek(target,0,os.SEEK_SET);out=target;target=None;return out,total
 finally:
  os.close(source)
  if target is not None:os.close(target)

def validate_plan(plan,width,height):
 if not isinstance(plan,dict) or set(plan)!={'tiles','pad_degrees','chunk'}:raise ValueError('invalid batch plan keys')
 boxes=plan['tiles'];pad=plan['pad_degrees'];chunk=plan['chunk']
 if not isinstance(boxes,list) or not boxes or type(chunk)!=int or chunk<1 or isinstance(pad,bool) or not isinstance(pad,(int,float)) or not math.isfinite(pad) or not 0<pad:raise ValueError('invalid batch plan values')
 for i,b in enumerate(boxes):
  if not isinstance(b,list) or len(b)!=4 or any(type(v)!=int for v in b):raise ValueError('invalid tile bounds')
  x0,x1,y0,y1=b
  if not(0<=x0<x1<=width and 0<=y0<y1<=height):raise ValueError('tile outside grid')
  for p in boxes[:i]:
   if max(x0,p[0])<min(x1,p[1]) and max(y0,p[2])<min(y1,p[3]):raise ValueError('overlapping tiles')
 return boxes

def run_batch(snapshot,snapshot_sha,paths,pins,plan,plan_sha,out,width,height,check_metadata,*,metadata_pins):
 """Generate partial research tiles; caller must authenticate objects and callback.

 Hash strings are caller assertions. Only the CLI validates pinned metadata and
 provides the required lineage callback; a completion record gates the batch.
 """
 boxes=validate_plan(plan,width,height)
 names=('physical_rows','physical_runs','land_rows','land_runs')
 if set(paths)!=set(names) or set(pins)!=set(names):raise ValueError('four grid inputs required')
 if set(metadata_pins)!={'physical_report','land_report'} or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in metadata_pins.values()):raise ValueError('two report SHA-256 pins required')
 code_paths={'algorithm':Path(tile.__file__),'core':Path(tile.core.__file__),'shore':Path(tile.core.shore.__file__),'geometry':Path(tile.core.shore.__file__),'accelerator':Path(tile.coastal_block.__file__)};code_pins={k:sha(v) for k,v in code_paths.items()}
 support_paths={'metadata':Path(pinned_coastal_metadata.__file__),'snapshot':Path(decision_snapshot.__file__),'output':Path(exclusive_outputs.__file__)};support_pins={k:sha(v) for k,v in support_paths.items()}
 check_metadata()
 with contextlib.ExitStack() as stack:
  sealed={};used=0
  for k in names:
   fd,n=sealed_copy(paths[k],pins[k]);used+=n;stack.callback(os.close,fd);sealed[k]=os.fdopen(os.dup(fd),'rb');stack.callback(sealed[k].close)
  physical=tile.open_grid(sealed['physical_rows'],sealed['physical_runs'],width,height);land=tile.open_grid(sealed['land_rows'],sealed['land_runs'],width,height)
  root=create_directory_exclusive(out);manifests=[]
  inputs={k+'_sha256':pins[k] for k in names};inputs.update({k+'_sha256':v for k,v in metadata_pins.items()})
  for i,box in enumerate(boxes):
   dest=root/f'tile-{i:04d}'
   manifest=tile.run(snapshot,snapshot_sha,physical,land,dest,width,height,box,plan['pad_degrees'],inputs,chunk=plan['chunk'],allow_selected_research=True)
   if any(manifest[k+'_sha256']!=v for k,v in code_pins.items()):raise ValueError('tile code pin changed within batch')
   manifests.append({'tile':i,'box':box,'manifest_sha256':sha(dest/'manifest.json')})
  check_metadata()
  if sha(Path(__file__))!=CODE_SHA or any(sha(path)!=code_pins[k] for k,path in code_paths.items()) or any(sha(path)!=support_pins[k] for k,path in support_paths.items()):raise ValueError('batch code changed during generation')
  result={'schema':'worldatlas-sealed-coastal-batch-v1','status':'complete-research-not-published','snapshot_sha256':snapshot_sha,'plan_sha256':plan_sha,'grid':{'width':width,'height':height},'sealed_input_sha256':pins,'metadata_sha256':metadata_pins,'sealed_input_bytes':used,'driver_sha256':CODE_SHA,'tile_code_sha256':code_pins,'support_code_sha256':support_pins,'tiles':manifests,'limitations':['Tiles remain research candidates and require separate global coverage, source and geographic review.','Sealed input bytes do not establish the correctness or acceptance of their source or decision metadata.','On-disk code hashes are change indicators, not proof of already-imported Python module bytes.']}
  write_json_exclusive(root/'batch-complete.json',result);return result

CODE_SHA=sha(Path(__file__))

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('snapshot','snapshot-sha256','physical-rows','physical-rows-sha256','physical-runs','physical-runs-sha256','physical-report','physical-report-sha256','land-rows','land-rows-sha256','land-runs','land-runs-sha256','land-report','land-report-sha256','input-root','plan','plan-sha256','out'):ap.add_argument('--'+k,required=True)
 ap.add_argument('--allow-unverified-snapshot',action='store_true');ap.add_argument('--allow-draft',action='store_true');ap.add_argument('--allow-selected-research-policy',action='store_true');a=ap.parse_args()
 if not(a.allow_unverified_snapshot and a.allow_draft and a.allow_selected_research_policy):raise ValueError('all explicit research opt-ins are required')
 root=Path(a.input_root).resolve();out=Path(a.out).resolve();files={k:Path(getattr(a,k)).resolve() for k in ('snapshot','physical_rows','physical_runs','physical_report','land_rows','land_runs','land_report','plan')};expected={k:getattr(a,k+'_sha256') for k in files}
 if not root.is_dir() or any(not p.is_relative_to(root) for p in files.values()) or any(out==p or p.is_relative_to(out) for p in files.values()):raise ValueError('inputs must be inside input root and outside output')
 snapshot=pinned_json(files['snapshot'],expected['snapshot']);validate_revision(snapshot,allow_draft=True)
 plan=pinned_json(files['plan'],expected['plan']);width,height=131072,54614;validate_plan(plan,width,height)
 physical={'rows_sha256':expected['physical_rows'],'runs_sha256':expected['physical_runs']};land={'rows_sha256':expected['land_rows'],'runs_sha256':expected['land_runs'],'resolved_rows':files['land_rows'],'resolved_runs':files['land_runs']}
 def check_metadata():
  pinned_bytes(files['snapshot'],expected['snapshot']);pinned_bytes(files['plan'],expected['plan'])
  physical_doc=pinned_json(files['physical_report'],expected['physical_report']);land_doc=pinned_json(files['land_report'],expected['land_report'])
  grid={'width':width,'height':height,'west':-180,'north':90,'step':360/width}
  validate_physical(physical_doc,physical,grid)
  validate_legacy_direct(land_doc,files['land_report'],physical,land,expected['snapshot'],snapshot['decision_revision'],root,grid)
 grid={k:files[k] for k in ('physical_rows','physical_runs','land_rows','land_runs')};pins={k:expected[k] for k in grid}
 result=run_batch(snapshot,expected['snapshot'],grid,pins,plan,expected['plan'],out,width,height,check_metadata,metadata_pins={k:expected[k] for k in ('physical_report','land_report')})
 print(json.dumps({'status':result['status'],'tiles':len(result['tiles']),'output':str(out)}))
if __name__=='__main__':main()

