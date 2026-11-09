"""Resumable WGS84 search engine; preflight and outputs owned by caller."""
import math,time
import numpy as np
import checkpoints,engine

def run(component_runs,co,roots,hints,seed_roots,width,cert_index,exact_index,checkpoint,identity,*,resume=False,chunk=1024,tolerance=1e-5,disk_floor_bytes=0,checkpoint_seconds=60,block_records=100000,guard=lambda:None,progress=lambda *x:None):
 roots=np.asarray(roots,dtype=np.uint32);hints=np.asarray(hints,dtype=np.uint8);seed_roots=np.asarray(seed_roots,dtype=np.uint32);N=len(roots)
 if len(hints)!=N or not N or np.any(roots[1:]<=roots[:-1]) or np.any((hints<17)|(hints>22)) or not 1<=chunk<=1024 or checkpoint_seconds<0:raise ValueError('invalid runner inputs')
 # Reconstruct actual full-extent physical witnesses on resume too. A saved
 # checkpoint cannot silently replace the current real WGS84 upper bounds.
 upper=engine.component_witnesses(component_runs,co,roots,seed_roots,width,cert_index,hints,guard)
 if resume:
  meta,a=checkpoints.read(checkpoint,identity,roots,guard)
  if not np.array_equal(a['hints'],hints) or not np.array_equal(a['upper'],upper):raise ValueError('checkpoint witness mismatch')
  phase=meta['phase'];cursor=meta['cursor'];base=meta['queries'];amb=a['amb'];best=a['best']
  if cursor>int(co[-1]):raise ValueError('checkpoint cursor exceeds stream')
  expected=engine.prefix_query_count(component_runs,roots,seed_roots,cursor,chunk,amb if phase in ('exact','complete') else None,guard)
  if base!=expected:raise ValueError('checkpoint cursor/query count mismatch')
  if phase=='complete' and cursor!=int(co[-1]):raise ValueError('incomplete final checkpoint')
 else:
  amb=np.zeros(N,dtype=bool);best=np.full((N,6),np.inf);best[np.arange(N),hints.astype(np.int64)-17]=upper;phase='cert';cursor=base=0
  checkpoints.write(checkpoint,identity,phase,cursor,base,{'roots':roots,'hints':hints,'upper':upper,'amb':amb,'best':best},disk_floor_bytes)
 def arrays():return {'roots':roots,'hints':hints,'upper':upper,'amb':amb,'best':best}
 last=time.monotonic()
 if phase=='cert':
  def cert_progress(pos,count,_):
   nonlocal last
   if time.monotonic()-last>=checkpoint_seconds:
    checkpoints.write(checkpoint,identity,'cert',pos,base+count,arrays(),disk_floor_bytes);progress('cert',pos,base+count);last=time.monotonic()
  amb,count,cursor=engine.certificate_pass(component_runs,co,roots,seed_roots,cert_index,upper,hints,amb,cursor,chunk,tolerance,guard,cert_progress,block_records)
  phase='exact';cursor=base=0;checkpoints.write(checkpoint,identity,phase,cursor,base,arrays(),disk_floor_bytes);progress('exact',0,0);last=time.monotonic()
 if phase=='exact':
  def exact_progress(pos,count,_):
   nonlocal last
   if time.monotonic()-last>=checkpoint_seconds:
    checkpoints.write(checkpoint,identity,'exact',pos,base+count,arrays(),disk_floor_bytes);progress('exact',pos,base+count);last=time.monotonic()
  best,count,cursor=engine.exact_pass(component_runs,co,roots,seed_roots,exact_index,hints,amb,best,cursor,chunk,tolerance,guard,exact_progress,min(block_records,256))
  phase='complete';base+=count;checkpoints.write(checkpoint,identity,phase,cursor,base,arrays(),disk_floor_bytes);progress('complete',cursor,base)
 codes,ties=engine.finalize(hints,amb,best,tolerance,numerical_tie_guard_m=.0001)
 return {'roots':roots,'codes':codes,'ambiguous':amb,'ties':ties,'certified_count':int((~amb).sum()),'exact_count':int(amb.sum()),'exact_queries':base}
