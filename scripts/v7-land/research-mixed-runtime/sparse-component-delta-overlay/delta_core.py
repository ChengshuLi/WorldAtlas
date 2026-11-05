"""Bounded RLE delta arithmetic; does not authenticate claims or establish geography."""
from collections import defaultdict
import numpy as np

def need(x,msg):
 if not x: raise ValueError(msg)

def selected_spans(rows,runs,width,targets,chunk=2_000_000):
 """One generation-pinned RLE pass for all targets; include whole components."""
 need(isinstance(targets,dict) and targets and all(type(k) is int and 0<=k<0xffffffff and type(v) is int and v>0 for k,v in targets.items()),'invalid targets')
 need(type(width) is int and 0<width<=0xffffffff and type(chunk) is int and chunk>0,'invalid grid/chunk')
 offsets=np.asarray(rows);need(offsets.ndim==1 and len(offsets)>1 and int(offsets[0])==0 and int(offsets[-1])==len(runs) and np.all(offsets[1:]>=offsets[:-1]),'bad component row offsets')
 need(offsets.dtype.kind=='u' and offsets.dtype.itemsize==4 and len(runs.shape)==2 and runs.shape[1]==3 and runs.dtype.kind=='u' and runs.dtype.itemsize==4,'bad component runs');wanted=np.array(sorted(targets),dtype=np.uint32);need(all(int(x)==y for x,y in zip(wanted,sorted(targets))),'root overflow')
 found=defaultdict(list); counts=defaultdict(int)
 for start in range(0,len(runs),chunk):
  data=runs[start:min(start+chunk,len(runs)),2];ids=np.flatnonzero(np.isin(data,wanted))+start
  if not len(ids):continue
  ys=np.searchsorted(offsets,ids,side='right')-1
  for j,y in zip(ids.tolist(),ys.tolist()):
   a=int(offsets[y]);b=int(offsets[y+1]);need(a<=j<b,'invalid component index')
   lo=int(runs[j,0]);end=int(runs[j,1]);root=int(runs[j,2]);need(0<=lo<end<=width,'invalid component span')
   found[y].append((lo,end,root));counts[root]+=end-lo
 need(set(counts)==set(targets),'target root absent')
 # Fully validate the affected rows; trusted source hashes authenticate other rows.
 for y,spans in found.items():
  a,b=map(int,offsets[y:y+2]); x=runs[a:b];need(len(x)>0 and np.all(x[:,0]<x[:,1]) and int(x[-1,1])<=width and np.all(x[1:,0]>=x[:-1,1]) and np.all(x[:,2]<0xffffffff),'invalid component row')
  need(all(spans[i][1]<=spans[i+1][0] for i in range(len(spans)-1)),'overlapping root spans')
 return dict(found),dict(counts)

def row(rows,runs,y,width,allowed):
 need(rows.ndim==1 and rows.dtype.kind=='u' and rows.dtype.itemsize==4 and runs.ndim==2 and runs.shape[1]==2 and runs.dtype.kind=='u' and runs.dtype.itemsize==4,'bad row stream dtype/shape');a,b=map(int,rows[y:y+2]);need(0<=a<b<=len(runs),'bad row offsets');r=runs[a:b];ends=r[:,0];values=r[:,1]
 need(int(ends[0])>0 and int(ends[-1])==width and np.all(ends[1:]>ends[:-1]) and np.all(np.isin(values,list(allowed))),'bad row coverage/category')
 return ends,values

def compare_delta(spans,targets,base_rows,base_runs,reference_rows,reference_runs,width,land,water):
 """Counts old/new shared-land mismatches in every affected component cell."""
 need(type(width) is int and 0<width<=0xffffffff,'invalid grid width')
 need(isinstance(land,(set,frozenset)) and isinstance(water,(set,frozenset)) and land and water and all(type(x) is int and 0<x<=0xffffffff for x in land|water) and not (land&water),'invalid categories')
 need(isinstance(targets,dict) and targets and all(type(k) is int and 0<=k<0xffffffff and type(v) is int and v in land for k,v in targets.items()),'nonland or invalid target')
 total={'affected_cells':0,'reference_water_cells':0,'old_mismatch':0,'new_mismatch':0,'new_mismatch_from_match':0,'resolved_mismatch':0,'unchanged_mismatch':0};per={r:dict(total) for r in targets}
 for y,items in spans.items():
  need(type(y) is int and 0<=y<len(base_rows)-1 and y<len(reference_rows)-1 and isinstance(items,list) and all(type(a) is int and type(z) is int and type(r) is int for a,z,r in items) and all(items[i][1]<=items[i+1][0] for i in range(len(items)-1)),'invalid or overlapping span rows')
  be,bv=row(base_rows,base_runs,y,width,set(land)|{0});re,rv=row(reference_rows,reference_runs,y,width,set(land)|set(water))
  for a,z,root in items:
   need(root in targets and 0<=a<z<=width,'bad selected span')
   boundaries=np.unique(np.concatenate((np.array([a,z],dtype=np.uint32),be[(be>a)&(be<z)],re[(re>a)&(re<z)])))
   starts=boundaries[:-1];length=(boundaries[1:]-starts).astype(np.int64);b=bv[np.searchsorted(be,starts,side='right')];r=rv[np.searchsorted(re,starts,side='right')]
   need(np.all(np.isin(b,list(land))),'selected root overlaps candidate water');shared=np.isin(r,list(land));old=shared&(b!=r);new=shared&(targets[root]!=r)
   vals={'affected_cells':int(length.sum()),'reference_water_cells':int(length[~shared].sum()),'old_mismatch':int(length[old].sum()),'new_mismatch':int(length[new].sum()),'new_mismatch_from_match':int(length[new&~old].sum()),'resolved_mismatch':int(length[old&~new].sum()),'unchanged_mismatch':int(length[old&new].sum())}
   for k,v in vals.items():total[k]+=v;per[root][k]+=v
 need(total['old_mismatch']-total['resolved_mismatch']+total['new_mismatch_from_match']==total['new_mismatch'],'delta identity failed')
 return {'total':total,'roots':per}
