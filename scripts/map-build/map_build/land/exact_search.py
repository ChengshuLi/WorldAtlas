"""Complete WGS84 tile/run search with conservative bounds and no cache limit."""
from pathlib import Path
import hashlib,math,sys
import numpy as np
from scipy.spatial import cKDTree
from map_build.core.distances import run_pairs_batch
from map_build.land.certificates import _unit,M_MIN


class ExactIndex:
 def __init__(self,directory,width,height,step,north,tiles,tile_cells=1024,guard_m=1000.):
  self.dir=Path(directory);self.w=width;self.h=height;self.step=step;self.north=north;self.C=tile_cells;self.guard=guard_m;self.cache={}
  self.leaf_cells=min(tile_cells,128);self.leaves=None;self.leaf_cache={}
  if width<2 or height<1 or abs(width*step-360)>1e-8 or tile_cells<1 or guard_m<1000:raise ValueError('invalid config')
  self.records={};self.ids=[];pos=[];radius=[]
  for ty,tx,codes,count,sha in tiles:
   if (ty,tx) in self.records or count<=0 or not codes or len(sha)!=64 or any(type(c) is not int or not 0<c<2**32 for c in codes):raise ValueError('invalid tile manifest')
   y0=ty*tile_cells;y1=min(height,y0+tile_cells);x0=tx*tile_cells;x1=min(width,x0+tile_cells)
   if not (0<=y0<y1 and 0<=x0<x1):raise ValueError('tile outside grid')
   self.records[(ty,tx)]=(set(codes),count,sha);self.ids.append((ty,tx));pos.append((north-(y0+y1)*step/2,-180+(x0+x1)*step/2));radius.append(((y1-y0)+(x1-x0))*step*math.pi/360)
  if not self.ids:raise ValueError('empty tile index')
  self.codes=tuple(sorted({code for codes,count,sha in self.records.values() for code in codes}))
  pos=np.asarray(pos);self.xyz=_unit(pos[:,0],pos[:,1]);self.tree=cKDTree(self.xyz);self.radii=np.asarray(radius);self.maxrad=float(self.radii.max())
 def _load(self,key):
  if key in self.cache:
   return self.cache[key]
  codes,count,sha=self.records[key];ty,tx=key;max_records=min(self.C,self.h-ty*self.C)*min(self.C,self.w-tx*self.C);path=self.dir/f'{ty:05d}-{tx:05d}.bin'
  if path.stat().st_size!=count*16 or count>max_records:raise ValueError('seed tile dimensions or record count differ')
  raw=path.read_bytes()
  if len(raw)!=count*16 or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('tile integrity failure')
  x=np.frombuffer(raw,dtype='<u4').reshape(-1,4)
  if len(x) and (np.any(x[:,0]>=self.h) or np.any(x[:,1]>=x[:,2]) or np.any(x[:,2]>self.w) or set(map(int,np.unique(x[:,3])))!=codes):raise ValueError('invalid tile data')
  # The complete pinned seed-tile index is small enough for normal host RAM;
  # retain verified tiles so a global exact pass does not repeatedly reread
  # and re-hash them as the component stream revisits nearby regions.
  self.cache[key]=x
  return x
 def prepare_leaves(self):
  """Index occupied fine leaves without changing the authenticated tile files.

  A 1024-cell source tile is an I/O unit, not a useful search bound: a coastal
  query otherwise scans thousands of unrelated mainland interior runs. Fine
  leaves cover exactly the same seed cells. Their clipped runs are materialized
  only when visited, while the original verified source tiles remain cached.
  """
  if self.leaves is not None:return
  C=self.leaf_cells;leaves=[];positions=[];radii=[];codes=[]
  for key in self.ids:
   data=self._load(key);ty,tx=key;y0=ty*self.C;y1=min(self.h,y0+self.C);x0=tx*self.C;x1=min(self.w,x0+self.C)
   if np.any((data[:,0]<y0)|(data[:,0]>=y1)|(data[:,1]<x0)|(data[:,2]>x1)):raise ValueError('seed run outside authenticated tile')
   for sy in range(y0,y1,C):
    ey=min(y1,sy+C);band=np.flatnonzero((data[:,0]>=sy)&(data[:,0]<ey))
    if not len(band):continue
    rows=data[band]
    for sx in range(x0,x1,C):
     ex=min(x1,sx+C);selected=band[(rows[:,1]<ex)&(rows[:,2]>sx)]
     if not len(selected):continue
     leaves.append((key,sy,ey,sx,ex,selected))
     positions.append((self.north-(sy+ey)*self.step/2,-180+(sx+ex)*self.step/2))
     radii.append(((ey-sy)+(ex-sx))*self.step*math.pi/360)
     codes.append(tuple(map(int,np.unique(data[selected,3]))))
  if not leaves:raise ValueError('empty fine seed index')
  self.leaves=leaves;self.leaf_codes=codes;self.leaf_xyz=_unit(*np.asarray(positions).T)
  self.leaf_tree=cKDTree(self.leaf_xyz);self.leaf_radii=np.asarray(radii);self.leaf_maxrad=float(max(radii))
 @property
 def certificate_tiles(self):
  self.prepare_leaves()
  # Production source tiles are an exact multiple of the fine leaf grid.
  if self.C%self.leaf_cells:raise ValueError('unaligned fine seed index')
  return [(sy//self.leaf_cells,sx//self.leaf_cells,codes) for (_,sy,ey,sx,ex,selected),codes in zip(self.leaves,self.leaf_codes)]
 def _load_leaf(self,i):
  if i not in self.leaf_cache:
   key,sy,ey,sx,ex,selected=self.leaves[i];data=self._load(key)[selected].copy()
   data[:,1]=np.maximum(data[:,1],sx);data[:,2]=np.minimum(data[:,2],ex)
   self.leaf_cache[i]=data
  return self.leaf_cache[i]
 def nearest_run(self,y,a,b,upper,tolerance=1e-5):
  if not (type(y) is int and type(a) is int and type(b) is int and 0<=y<self.h and 0<=a<b<=self.w and math.isfinite(upper) and upper>=0 and math.isfinite(tolerance) and tolerance>=0):raise ValueError('invalid query')
  lat=self.north-(y+.5)*self.step;lon=-180+((a+b-1)/2+.5)*self.step;point=_unit(np.array([lat]),np.array([lon]))[0];qr=(b-a-1)*self.step*math.pi/360
  self.prepare_leaves()
  limit=(upper+tolerance+self.guard)/M_MIN+self.leaf_maxrad+qr
  indices=np.arange(len(self.leaves),dtype=np.int64) if limit>=math.pi else np.asarray(self.leaf_tree.query_ball_point(point,2*math.sin(limit/2),eps=0,workers=1),dtype=np.int64)
  # Test the nearest tile center first. A real WGS84 result found early then
  # tightens the conservative radius for the rest of this query. Do not sort
  # the entire candidate set: most queries need only the first few tiles, so
  # an O(k log k) ordering cost can exceed the distance work it avoids.
  if len(indices)>1:
   chords=np.linalg.norm(self.leaf_xyz[indices]-point,axis=1)
   nearest=int(np.argmin(chords))
   if nearest:
    indices[[0,nearest]]=indices[[nearest,0]];chords[[0,nearest]]=chords[[nearest,0]]
  else:
   chords=np.linalg.norm(self.leaf_xyz[indices]-point,axis=1) if len(indices) else np.empty(0)
  out={};seen=0;tested=0
  for i,c in zip(indices,chords):
   # Distances above the best known component-to-continent witness cannot win
   # or tie. Since M_MIN is a conservative WGS84 lower-bound radius, this
   # tighter test only removes tiles that cannot affect the final label.
   incumbent=min(upper,min(out.values(),default=upper))
   lim=(incumbent+tolerance+self.guard)/M_MIN+self.leaf_radii[i]+qr
   if lim<math.pi and c>2*math.sin(lim/2):continue
   data=self._load_leaf(int(i));seen+=len(data)
   if not len(data):continue
   # Minimum longitude gap of two circular integer intervals, vectorized.
   aa=data[:,1].astype(np.int64);bb=data[:,2].astype(np.int64);gap=np.full(len(data),self.w,dtype=np.int64)
   for shift in (-self.w,0,self.w):gap=np.minimum(gap,np.maximum(0,np.maximum(aa+shift-(b-1),a-(bb-1+shift))))
   p1=math.radians(lat);p2=np.deg2rad(self.north-(data[:,0].astype(float)+.5)*self.step);dl=np.deg2rad(gap*self.step);dp=p2-p1;hav=np.sin(dp/2)**2+math.cos(p1)*np.cos(p2)*np.sin(dl/2)**2;angle=2*np.arcsin(np.sqrt(np.clip(hav,0,1)))
   selected=np.flatnonzero(angle*M_MIN<=incumbent+tolerance+self.guard)
   ds,count=run_pairs_batch(y,a,b,data[selected],self.w,north=self.north,incumbent=incumbent,tol=tolerance);tested+=count
   for code,d in ds.items():out[code]=min(out.get(code,math.inf),d)
  return out,{'tiles':len(indices),'seed_runs_scanned':seen,'run_pairs_wgs84_tested':tested}
