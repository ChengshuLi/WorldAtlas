"""Crash-safe single-file research checkpoints, bound to full input identity."""
import hashlib,json,math,os,shutil,uuid
from pathlib import Path
import numpy as np

def guard(directory,disk_floor_bytes):
 if shutil.disk_usage(directory).free<disk_floor_bytes:raise RuntimeError('disk guard reached')

def _checksum(meta,arrays):
 h=hashlib.sha256(json.dumps(meta,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
 for k in sorted(arrays):
  a=np.ascontiguousarray(arrays[k]);h.update(k.encode());h.update(a.dtype.str.encode());h.update(json.dumps(a.shape,separators=(',',':')).encode());h.update(memoryview(a).cast('B'))
 return h.hexdigest()

def write(path,identity,phase,cursor,queries,arrays,disk_floor_bytes):
 p=Path(path);guard(p.parent,disk_floor_bytes)
 if phase not in ('cert','exact','complete') or type(cursor) is not int or cursor<0 or type(queries) is not int or queries<0:raise ValueError('bad checkpoint cursor')
 if set(arrays)!={'roots','hints','upper','amb','best'}:raise ValueError('bad checkpoint arrays')
 meta={'schema':'wgs84-baseline-checkpoint-v1','identity':identity,'phase':phase,'cursor':cursor,'queries':queries};meta['state_sha256']=_checksum(meta,arrays);metadata=json.dumps(meta,sort_keys=True,separators=(',',':'),allow_nan=False)
 tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.partial')
 try:
  with open(tmp,'xb') as f:
   np.savez(f,metadata=np.frombuffer(metadata.encode(),dtype=np.uint8),**arrays);f.flush();os.fsync(f.fileno())
  guard(p.parent,disk_floor_bytes);os.replace(tmp,p)
  d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(d)
  finally:os.close(d)
 finally:
  if tmp.exists():tmp.unlink()

def read(path,identity,expected_roots,guard=lambda:None):
 # Capture an immutable copy; reject compressed ZIPs and forged NPY shapes
 # before NumPy loads the arrays. Array sizes derive from the expected roots.
 import io,zipfile
 n=len(expected_roots);chunks=[]
 with open(path,'rb') as stream:
  while True:
   guard();block=stream.read(1<<20)
   if not block:break
   chunks.append(block)
 raw=b''.join(chunks)
 expected={'roots':(np.dtype('uint32'),(n,)),'hints':(np.dtype('uint8'),(n,)),'upper':(np.dtype('float64'),(n,)),'amb':(np.dtype('bool'),(n,)),'best':(np.dtype('float64'),(n,6))}
 with zipfile.ZipFile(io.BytesIO(raw)) as zf:
  names=zf.namelist()
  if len(names)!=6 or set(names)!={k+'.npy' for k in (*expected,'metadata')}:raise ValueError('bad checkpoint contents')
  for name in names:
   info=zf.getinfo(name)
   if info.compress_type!=zipfile.ZIP_STORED:raise ValueError('compressed checkpoint member unsupported')
   with zf.open(info) as f:
    version=np.lib.format.read_magic(f)
    if version==(1,0):shape,fortran,dtype=np.lib.format.read_array_header_1_0(f)
    elif version in ((2,0),(3,0)):shape,fortran,dtype=np.lib.format.read_array_header_2_0(f)
    else:raise ValueError('unsupported NPY version')
    key=name[:-4]
    if key=='metadata':
     if dtype!=np.dtype('uint8') or len(shape)!=1 or fortran:raise ValueError('bad checkpoint metadata shape')
    elif (dtype,shape)!=expected[key] or fortran:raise ValueError('bad checkpoint array shape')
    if info.file_size!=f.tell()+math.prod(shape)*dtype.itemsize:raise ValueError('bad checkpoint member length')
 guard()
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:
  if set(z.files)!={'metadata','roots','hints','upper','amb','best'}:raise ValueError('bad checkpoint contents')
  meta=json.loads(z['metadata'].tobytes());a={k:z[k] for k in ('roots','hints','upper','amb','best')}
 saved=meta.pop('state_sha256',None)
 if saved!=_checksum(meta,a):raise ValueError('checkpoint checksum mismatch')
 if meta.get('schema')!='wgs84-baseline-checkpoint-v1' or meta.get('identity')!=identity or meta.get('phase') not in ('cert','exact','complete') or type(meta.get('cursor')) is not int or meta['cursor']<0 or type(meta.get('queries')) is not int or meta['queries']<0:raise ValueError('checkpoint identity/cursor mismatch')
 n=len(expected_roots)
 if a['roots'].dtype!=np.uint32 or not np.array_equal(a['roots'],expected_roots) or a['hints'].dtype!=np.uint8 or a['hints'].shape!=(n,) or np.any((a['hints']<17)|(a['hints']>22)) or a['upper'].shape!=(n,) or a['upper'].dtype!=np.float64 or not np.all(np.isfinite(a['upper'])) or np.any(a['upper']<0) or a['amb'].dtype!=np.bool_ or a['amb'].shape!=(n,) or a['best'].shape!=(n,6) or a['best'].dtype!=np.float64 or np.any(np.isnan(a['best'])) or np.any(a['best']<0):raise ValueError('checkpoint state mismatch')
 return meta,a

from contextlib import contextmanager
import fcntl
@contextmanager
def exclusive_lock(path):
 p=Path(path)
 with open(p,'a+b') as f:
  try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('baseline checkpoint is locked by another process')
  try:yield
  finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
