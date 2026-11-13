"""Stream complete current components through certificates and exact WGS84 search."""
from pathlib import Path
import numpy as np

def positions(ids,roots,seed_roots):
 if len(seed_roots)==0:raise ValueError('no seed roots')
 if not len(roots):
  if np.any(~np.isin(ids,seed_roots)):raise ValueError('unknown component')
  return np.zeros(len(ids),dtype=np.int64),np.zeros(len(ids),dtype=bool)
 pos=np.searchsorted(roots,ids);safe=np.minimum(pos,len(roots)-1);match=(pos<len(roots))&(roots[safe]==ids);seed=np.isin(ids,seed_roots)
 if np.any(match&seed) or np.any(~match&~seed):raise ValueError('unknown or conflicting component')
 return pos,match

def blocks(path,cursor=0,block_records=100000,guard=lambda:None):
 size=Path(path).stat().st_size
 if size%12 or cursor<0 or cursor>size//12 or block_records<1:raise ValueError('invalid component stream/cursor')
 off=cursor
 with open(path,'rb') as f:
  f.seek(cursor*12)
  while True:
   guard();b=f.read(block_records*12)
   if not b:break
   if len(b)%12:raise ValueError('truncated component runs')
   a=np.frombuffer(b,dtype='<u4').reshape(-1,3);yield off,a;off+=len(a)

def first_points(path,co,roots,seed_roots,width,guard=lambda:None):
 roots=np.asarray(roots,dtype=np.uint32);seed_roots=np.asarray(seed_roots,dtype=np.uint32);ys=np.full(len(roots),-1,dtype=np.int32);xs=np.full(len(roots),-1,dtype=np.int32);seen_seed=set();last=0
 for off,a in blocks(path,guard=guard):
  if np.any(a[:,0]>=a[:,1]) or np.any(a[:,1]>width):raise ValueError('invalid component run')
  pos,match=positions(a[:,2],roots,seed_roots);seen_seed.update(map(int,np.unique(a[~match,2])))
  ix=np.flatnonzero(match)
  if len(ix):
   ids,first=np.unique(pos[ix],return_index=True);pick=ix[first];unset=ys[ids]<0;ids=ids[unset];pick=pick[unset]
   ys[ids]=(np.searchsorted(co,off+pick,side='right')-1).astype(np.int32);xs[ids]=a[pick,0]
  last=off+len(a)
 if last!=int(co[-1]) or set(map(int,seed_roots))!=seen_seed or np.any(ys<0) or np.any(ys>=len(co)-1):raise ValueError('incomplete component coverage')
 return ys,xs

def component_witnesses(path,co,roots,seed_roots,width,index,hints,guard=lambda:None):
 """Tighten each component upper bound with actual cells across its extent.

 A component's first northern cell can be far from its closest mainland.
 Batched endpoint witnesses cost far less than proving a loose first-cell
 bound against every run of a large island. These samples are upper bounds,
 never decisions: both endpoints are actual component cells and every chosen
 mainland representative has already been independently authenticated.
 """
 roots=np.asarray(roots,dtype=np.uint32);seed_roots=np.asarray(seed_roots,dtype=np.uint32);hints=np.asarray(hints,dtype=np.uint32)
 if hints.shape!=roots.shape or np.any(~np.isin(hints,index.codes)):raise ValueError('invalid witness hints')
 upper=np.full(len(roots),np.inf);seen_seed=set();last=0
 for off,a in blocks(path,guard=guard):
  if np.any(a[:,0]>=a[:,1]) or np.any(a[:,1]>width):raise ValueError('invalid component run')
  pos,match=positions(a[:,2],roots,seed_roots);seen_seed.update(map(int,np.unique(a[~match,2])))
  ix=np.flatnonzero(match);wide=ix[a[ix,1]-a[ix,0]>1]
  chosen=np.r_[ix,wide];cols=np.r_[a[ix,0],a[wide,1]-1]
  for start in range(0,len(chosen),8192):
   guard();selected=chosen[start:start+8192];p=pos[selected]
   rows=np.searchsorted(co,off+selected,side='right')-1
   if np.any((rows<0)|(rows>=len(co)-1)):raise ValueError('invalid witness row')
   distances,_=index.witnesses(rows,cols[start:start+8192],hints[p])
   if np.asarray(distances).shape!=p.shape or np.any(~np.isfinite(distances)) or np.any(distances<0):raise ValueError('invalid WGS84 witness bound')
   np.minimum.at(upper,p,distances)
  last=off+len(a)
 if last!=int(co[-1]) or set(map(int,seed_roots))!=seen_seed or np.any(~np.isfinite(upper)):raise ValueError('incomplete component witness coverage')
 return upper

def oversized_run_queries(a,base,co,pos,index,chunk,max_queries):
 """Stream one very long valid run without rejecting or dropping chunks."""
 start=int(a[index,0]);end=int(a[index,1]);row=int(np.searchsorted(co,base+index,side='right')-1);root_position=int(pos[index])
 while start<end:
  n=min(max_queries,(end-start+chunk-1)//chunk)
  starts=start+np.arange(n,dtype=np.int64)*chunk
  ends=np.minimum(starts+chunk,end)
  yield (np.full(n,row,dtype=np.int32),starts.astype(np.int32),ends.astype(np.int32),np.full(n,root_position,dtype=np.int64))
  start=int(ends[-1])

def expanded(a,base,co,roots,seed_roots,chunk=1024,max_queries=65536):
 if not (1<=chunk<=1024 and max_queries>=128):raise ValueError('invalid query chunk')
 if np.any(a[:,0]>=a[:,1]):raise ValueError('bad component interval')
 pos,match=positions(a[:,2],roots,seed_roots);idx=np.flatnonzero(match);last=0
 # Process entire input block; each yielded query group is bounded.
 while last<len(idx):
  lengths=a[idx[last:],1].astype(np.int64)-a[idx[last:],0].astype(np.int64);counts=(lengths+chunk-1)//chunk
  if counts[0]>max_queries:
   yield from oversized_run_queries(a,base,co,pos,int(idx[last]),chunk,max_queries);last+=1;continue
  cum=np.cumsum(counts);n=max(1,int(np.searchsorted(cum,max_queries,side='right')));chosen=idx[last:last+n];cc=counts[:n]
  repeat=np.repeat(np.arange(n),cc);within=np.arange(len(repeat))-np.repeat(np.cumsum(cc)-cc,cc);start=a[chosen[repeat],0].astype(np.int64)+within*chunk;end=np.minimum(a[chosen[repeat],1].astype(np.int64),start+chunk);p=pos[chosen[repeat]];rows=np.searchsorted(co,base+chosen[repeat],side='right')-1
  yield rows.astype(np.int32),start.astype(np.int32),end.astype(np.int32),p.astype(np.int64)
  last+=n

def expanded_ambiguous(a,base,co,roots,seed_roots,amb,chunk=1024,max_queries=65536):
 """Expand only runs belonging to components that need exact search.

 The exact pass still validates every label in each source block, but most
 component runs are already certified. Filtering before chunk expansion avoids
 allocating query arrays for those irrelevant runs.
 """
 if not (1<=chunk<=1024 and max_queries>=128):raise ValueError('invalid query chunk')
 if np.any(a[:,0]>=a[:,1]):raise ValueError('bad component interval')
 pos,match=positions(a[:,2],roots,seed_roots)
 chosen=np.flatnonzero(match)
 if len(chosen):chosen=chosen[np.asarray(amb,dtype=bool)[pos[chosen]]]
 last=0
 while last<len(chosen):
  lengths=a[chosen[last:],1].astype(np.int64)-a[chosen[last:],0].astype(np.int64)
  counts=(lengths+chunk-1)//chunk
  if counts[0]>max_queries:
   yield from oversized_run_queries(a,base,co,pos,int(chosen[last]),chunk,max_queries);last+=1;continue
  cum=np.cumsum(counts);n=max(1,int(np.searchsorted(cum,max_queries,side='right')))
  run_ix=chosen[last:last+n];cc=counts[:n]
  repeat=np.repeat(np.arange(n),cc)
  within=np.arange(len(repeat))-np.repeat(np.cumsum(cc)-cc,cc)
  start=a[run_ix[repeat],0].astype(np.int64)+within*chunk
  end=np.minimum(a[run_ix[repeat],1].astype(np.int64),start+chunk)
  p=pos[run_ix[repeat]]
  rows=np.searchsorted(co,base+run_ix[repeat],side='right')-1
  yield rows.astype(np.int32),start.astype(np.int32),end.astype(np.int32),p.astype(np.int64)
  last+=n

def certificate_pass(path,co,roots,seed_roots,index,upper,hints,amb,cursor=0,chunk=1024,tolerance=1e-5,guard=lambda:None,progress=lambda *x:None,block_records=100000):
 roots=np.asarray(roots,dtype=np.uint32);upper=np.asarray(upper,dtype=float);hints=np.asarray(hints,dtype=np.uint32)
 if len(upper)!=len(roots) or len(hints)!=len(roots) or len(amb)!=len(roots) or np.any(~np.isfinite(upper)) or np.any(upper<0):raise ValueError('bad certificate state')
 count=0;endcursor=cursor
 for off,a in blocks(path,cursor,block_records,guard):
  for y,x,z,p in expanded(a,off,co,roots,seed_roots,chunk):
   good=index.certify_runs(y,x,z,upper[p],hints[p],tolerance);np.logical_or.at(amb,p,~good);count+=len(p)
  endcursor=off+len(a);progress(endcursor,count,amb)
 if endcursor!=int(co[-1]):raise ValueError('incomplete certificate stream')
 return amb,count,endcursor

def exact_pass(path,co,roots,seed_roots,index,hints,amb,best,cursor=0,chunk=1024,tolerance=1e-5,guard=lambda:None,progress=lambda *x:None,block_records=10000):
 roots=np.asarray(roots,dtype=np.uint32);hints=np.asarray(hints,dtype=np.uint32);amb=np.asarray(amb,dtype=bool)
 if len(hints)!=len(roots) or len(amb)!=len(roots) or best.shape!=(len(roots),len(index.codes)):raise ValueError('bad exact state')
 if np.any(~np.isfinite(best[np.arange(len(roots)),np.searchsorted(index.codes,hints)])):raise ValueError('missing real upper witness')
 count=0;endcursor=cursor
 for off,a in blocks(path,cursor,block_records,guard):
  for ys,xs,ends,pos in expanded_ambiguous(a,off,co,roots,seed_roots,amb,chunk):
   for i in range(len(pos)):
    guard();p=int(pos[i]);upper=float(np.min(best[p]));ds,_=index.nearest_run(int(ys[i]),int(xs[i]),int(ends[i]),upper,tolerance)
    for code,d in ds.items():
     if code not in index.codes or not np.isfinite(d) or d<0:raise ValueError('invalid exact distance')
     column=index.codes.index(code)
     best[p,column]=min(best[p,column],d)
    count+=1
  endcursor=off+len(a);progress(endcursor,count,best)
 if endcursor!=int(co[-1]):raise ValueError('incomplete exact stream')
 return best,count,endcursor

def finalize(hints,amb,best,category_codes,tolerance=1e-5):
 """Choose the lowest bound code within the selected distance tie policy."""
 hints=np.asarray(hints,dtype=np.uint32);amb=np.asarray(amb,dtype=bool)
 categories=np.asarray(category_codes,dtype=np.uint32)
 if (best.shape!=(len(hints),len(categories)) or len(amb)!=len(hints) or tolerance<0
     or not len(categories) or np.any(categories[1:]<=categories[:-1])):raise ValueError('invalid final state')
 codes=hints.copy();ties=[]
 for i in np.flatnonzero(amb):
  values=best[i];minimum=float(np.min(values))
  if not np.isfinite(minimum):raise ValueError('no WGS84 witness')
  winners=np.flatnonzero(values<=minimum+tolerance)
  codes[i]=categories[winners[0]]
  if len(winners)>1:ties.append({'position':int(i),'codes':list(map(int,categories[winners])),'minimum_m':minimum})
 return codes,ties

def prefix_query_count(path,roots,seed_roots,cursor,chunk=1024,amb=None,guard=lambda:None):
 if cursor<0 or cursor>Path(path).stat().st_size//12:raise ValueError('invalid prefix cursor')
 roots=np.asarray(roots,dtype=np.uint32);total=0
 for off,a in blocks(path,0,100000,guard):
  if off>=cursor:break
  a=a[:min(len(a),cursor-off)];pos,match=positions(a[:,2],roots,seed_roots)
  if amb is not None:
   valid=np.zeros(len(a),dtype=bool);valid[match]=np.asarray(amb,dtype=bool)[pos[match]];match &= valid
  length=a[match,1].astype(np.uint64)-a[match,0].astype(np.uint64);total+=int(((length+chunk-1)//chunk).sum())
 return total
