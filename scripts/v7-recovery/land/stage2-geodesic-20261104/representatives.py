"""Build bounded, real seed-cell witness samples from authenticated tiles."""
import hashlib,json,os,struct,time,resource
from pathlib import Path
import numpy as np
from checkpoints import guard
from verify_inputs import manifest,sha_file,read_tile
REC=struct.Struct('<IIIII')
def build(tile_dir,manifest_path,manifest_sha256,output,report,*,width,height,tile_size=1024,samples_per_category=32,memory_floor_kib=0,disk_floor_bytes=0):
 src=Path(tile_dir).resolve();mp=Path(manifest_path).resolve();out=Path(output).resolve();rp=Path(report).resolve()
 if not src.is_dir() or not out.parent.is_dir() or out==rp or out.is_relative_to(src) or rp.is_relative_to(src) or not (type(width) is int and width>0 and type(height) is int and height>0 and type(tile_size) is int and tile_size>0 and type(samples_per_category) is int and 1<=samples_per_category<=32):raise ValueError('invalid representative config')
 g=lambda:guard(out.parent,memory_floor_kib,disk_floor_bytes);g()
 if sha_file(mp,g)!=manifest_sha256:raise ValueError('manifest pin mismatch')
 T=manifest(mp,width,height,tile_size,g);h=hashlib.sha256();n=0;per={c:0 for c in range(17,23)};start=time.monotonic()
 with open(out,'xb') as o:
  for (ty,tx),(count,mask,expected) in sorted(T.items()):
   g();max_records=min(tile_size,height-ty*tile_size)*min(tile_size,width-tx*tile_size);raw=read_tile(src/f'{ty:05d}-{tx:05d}.bin',count,max_records,g)
   if len(raw)!=count*16 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('source tile hash mismatch')
   a=np.frombuffer(raw,dtype='<u4').reshape(-1,4)
   if np.any(a[:,0]>=height) or np.any(a[:,0]//tile_size!=ty) or np.any(a[:,1]//tile_size!=tx) or np.any(a[:,1]>=a[:,2]) or np.any(a[:,2]>min(width,(tx+1)*tile_size)):raise ValueError('invalid tile record')
   codes=sorted(set(map(int,np.unique(a[:,3]))))
   if codes!=[17+i for i in range(6) if mask&(1<<i)]:raise ValueError('tile category mismatch')
   for c in codes:
    z=np.flatnonzero(a[:,3]==c);chosen=z[np.unique(np.linspace(0,len(z)-1,min(samples_per_category,len(z)),dtype=int))]
    for j in chosen:
     y,left,right,code=map(int,a[j]);b=REC.pack(ty,tx,y,(left+right-1)//2,code);o.write(b);h.update(b);n+=1;per[c]+=1
  o.flush();os.fsync(o.fileno())
 g();result={'schema':'wgs84-representative-seed-cells-v1','status':'research-only','tile_manifest_sha256':manifest_sha256,'width':width,'height':height,'tile_size':tile_size,'samples_per_category':samples_per_category,'representatives':n,'per_code':{str(k):v for k,v in per.items()},'output_sha256':h.hexdigest(),'numpy_version':np.__version__,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'method':'Evenly spaced source runs per tile/category, choosing an actual midpoint seed cell; used only for upper witnesses.'}
 with open(rp,'x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 return result
