"""Read-only verification for authenticated mainland tiles and witnesses."""
from pathlib import Path
import hashlib,re
import numpy as np

def sha_file(path,guard=lambda:None):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()

def bounded_bytes(path,max_bytes,guard=lambda:None):
 import os
 if type(max_bytes) is not int or max_bytes<0:raise ValueError('invalid byte limit')
 chunks=[];total=0
 with open(path,'rb') as f:
  if os.fstat(f.fileno()).st_size>max_bytes:raise ValueError('file exceeds size limit')
  while True:
   guard();b=f.read(min(1<<20,max_bytes-total+1))
   if not b:break
   total+=len(b)
   if total>max_bytes:raise ValueError('file exceeds size limit')
   chunks.append(b)
 return b''.join(chunks)

def manifest(path, width=None, height=None, tile_size=1024, guard=lambda:None):
 # Bounded streaming: an adversarial manifest cannot allocate an unbounded list.
 if (width is None)!=(height is None) or (width is not None and (width<1 or height<1 or tile_size<1)):raise ValueError('invalid grid')
 result={};total=0;max_bytes=8<<20;max_records=tile_size*tile_size
 with open(path,'rb') as f:
  while True:
   guard();line=f.readline(257)
   if not line:break
   total+=len(line)
   if len(line)>256 or total>max_bytes:raise ValueError('manifest exceeds size limit')
   try:z=line.decode('ascii').split();y,x,n,mask=map(int,z[:4]);digest=z[4]
   except (UnicodeError,ValueError,IndexError):raise ValueError('bad manifest') from None
   if len(z)!=5 or y<0 or x<0 or n<1 or n>max_records or not 0<mask<64 or not re.fullmatch('[0-9a-f]{64}',digest) or (y,x) in result:raise ValueError('invalid/duplicate tile manifest')
   if width is not None:
    h=min(tile_size,height-y*tile_size);w=min(tile_size,width-x*tile_size)
    if h<=0 or w<=0 or n>h*w:raise ValueError('tile exceeds grid bounds')
   result[y,x]=(n,mask,digest)
 if not result:raise ValueError('empty tile manifest')
 return result

def read_tile(path,count,max_records,guard=lambda:None):
 if type(count) is not int or count<1 or count>max_records:raise ValueError('tile count exceeds bound')
 expected=count*16;parts=[];left=expected
 with open(path,'rb') as f:
  import os
  if os.fstat(f.fileno()).st_size!=expected:raise ValueError('tile size mismatch')
  while left:
   guard();b=f.read(min(left,1<<20))
   if not b:raise ValueError('tile size mismatch')
   parts.append(b);left-=len(b)
  guard()
  if f.read(1):raise ValueError('tile size mismatch')
 return b''.join(parts)

def verify_representatives(directory,tile_manifest,representatives,width,height,tile_size=1024,guard=lambda:None):
 # All data are pinned/verified by the caller, and files are checked again here.
 T=manifest(tile_manifest,width,height,tile_size,guard);r=np.asarray(representatives,dtype=np.uint32)
 if r.ndim!=2 or r.shape[1]!=5 or not len(r):raise ValueError('bad representatives')
 # Grouping does not presume input order; integer keys are unique for given W.
 nx=(width+tile_size-1)//tile_size;keys=r[:,0].astype(np.uint64)*nx+r[:,1];order=np.argsort(keys);r=r[order];keys=keys[order]
 uniq,start=np.unique(keys,return_index=True);end=np.r_[start[1:],len(r)];seen=set()
 for key,a,b in zip(uniq,start,end):
  guard();ty,tx=divmod(int(key),nx)
  if (ty,tx) not in T:raise ValueError('representative references unknown tile')
  seen.add((ty,tx));count,mask,expected=T[ty,tx];max_records=min(tile_size,height-ty*tile_size)*min(tile_size,width-tx*tile_size);raw=read_tile(Path(directory)/f'{ty:05d}-{tx:05d}.bin',count,max_records,guard)
  if len(raw)!=count*16 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('tile hash mismatch')
  data=np.frombuffer(raw,dtype='<u4').reshape(-1,4)
  if np.any(data[:,0]>=height) or np.any(data[:,0]//tile_size!=ty) or np.any(data[:,1]//tile_size!=tx) or np.any(data[:,1]>=data[:,2]) or np.any(data[:,2]>min(width,(tx+1)*tile_size)):raise ValueError('invalid tile record')
  codes=set(map(int,np.unique(data[:,3])))
  if codes!={i+17 for i in range(6) if mask&(1<<i)}:raise ValueError('category mask mismatch')
  if len(data)>1 and (np.any(data[1:,0]<data[:-1,0]) or np.any((data[1:,0]==data[:-1,0])&(data[1:,1]<data[:-1,1]))):raise ValueError('unsorted tile')
  ys=data[:,0]
  for _,_,y,x,c in r[a:b]:
   lo=int(np.searchsorted(ys,y,'left'));hi=int(np.searchsorted(ys,y,'right'))
   if lo==hi:raise ValueError('representative has no seed row')
   row=data[lo:hi];i=int(np.searchsorted(row[:,1],x,'right'))-1
   if i<0 or not (int(row[i,1])<=int(x)<int(row[i,2])) or int(row[i,3])!=int(c):raise ValueError('representative is not an actual seed cell')
  present=set(map(int,r[a:b,4]));
  if present!=codes:raise ValueError('tile/category lacks a representative')
 if seen!=set(T):raise ValueError('tile lacks representatives')
 return [(ty,tx,sorted(i+17 for i in range(6) if mask&(1<<i)),n,sha) for (ty,tx),(n,mask,sha) in sorted(T.items())]
