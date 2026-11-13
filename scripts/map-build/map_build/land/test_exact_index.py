import tempfile,unittest,pathlib,hashlib,collections,math
import numpy as np
from pyproj import Geod
from map_build.land.exact_search import ExactIndex
from map_build.land.certificates import CertificateIndex
G=Geod(ellps='WGS84')
class Exact(unittest.TestCase):
 def make(self,seeds,w=36,C=4):
  t=tempfile.TemporaryDirectory();d=pathlib.Path(t.name);tiles=collections.defaultdict(list)
  for y,x,c in sorted(seeds):tiles[y//C,x//C].append((y,x,x+1,c))
  manifest=[];ctiles=[]
  for (ty,tx),rows in sorted(tiles.items()):
   raw=np.asarray(rows,dtype='<u4').tobytes();(d/f'{ty:05d}-{tx:05d}.bin').write_bytes(raw);codes=sorted(set(x[3] for x in rows));manifest.append((ty,tx,codes,len(rows),hashlib.sha256(raw).hexdigest()));ctiles.append((ty,tx,codes))
  idx=ExactIndex(d,w,w//2,360/w,90,manifest,tile_cells=C)
  cert=CertificateIndex(w,w//2,360/w,90,ctiles,seeds,tile_cells=C)
  return t,idx,cert
 def oracle(self,runs,seeds,w,tol):
  best={};step=360/w
  for y,a,b in runs:
   for x in range(a,b):
    for yy,xx,c in seeds:
     v=G.inv(-180+(x+.5)*step,90-(y+.5)*step,-180+(xx+.5)*step,90-(yy+.5)*step)[2];best[c]=min(best.get(c,math.inf),v)
  m=min(best.values());return {c for c,v in best.items() if v<=m+tol}
 def run_case(self,seeds,runs,hint,w=36,tol=.00001):
  tmp,idx,cert=self.make(seeds,w);self.addCleanup(tmp.cleanup);u,_=cert.witnesses([runs[0][0]],[runs[0][1]],[hint]);best={hint:float(u[0])}
  for y,a,b in runs:
   v,_=idx.nearest_run(y,a,b,min(best.values()),tol)
   for c,d in v.items():best[c]=min(best.get(c,math.inf),d)
  m=min(best.values());self.assertEqual({c for c,d in best.items() if d<=m+tol},self.oracle(runs,seeds,w,tol))
 def test_random(self):
  rng=np.random.default_rng(312)
  for _ in range(60):
   seeds=[(int(rng.integers(18)),int(rng.integers(36)),17+i) for i in range(6)]
   # Unique cell coordinates avoid a non-physical overlapping code fixture.
   if len({(y,x) for y,x,c in seeds})<6:continue
   runs=[(int(rng.integers(18)),int(x),int(x)+1) for x in rng.integers(36,size=3)]
   self.run_case(seeds,runs,17+int(rng.integers(6)))
 def test_random_long_query_and_seed_runs(self):
  rng=np.random.default_rng(687);w=36;C=4
  for _ in range(50):
   seeds=[];tiles=collections.defaultdict(list);occupied=set()
   for code in range(17,23):
    while True:
     y=int(rng.integers(w//2));x=int(rng.integers(w));end=min((x//C+1)*C,w,x+int(rng.integers(1,5)))
     if not any((y,z) in occupied for z in range(x,end)):break
    occupied.update((y,z) for z in range(x,end));seeds.extend((y,z,code) for z in range(x,end));tiles[y//C,x//C].append((y,x,end,code))
   runs=[]
   for _ in range(3):
    y=int(rng.integers(w//2));x=int(rng.integers(w));runs.append((y,x,min(w,x+int(rng.integers(1,12)))))
   with tempfile.TemporaryDirectory() as d:
    manifest=[];ctiles=[]
    for (ty,tx),rows in sorted(tiles.items()):
     raw=np.asarray(sorted(rows),dtype='<u4').tobytes();(pathlib.Path(d)/f'{ty:05d}-{tx:05d}.bin').write_bytes(raw);codes=sorted({r[3] for r in rows});manifest.append((ty,tx,codes,len(rows),hashlib.sha256(raw).hexdigest()));ctiles.append((ty,tx,codes))
    idx=ExactIndex(d,w,w//2,360/w,90,manifest,tile_cells=C);cert=CertificateIndex(w,w//2,360/w,90,ctiles,seeds,tile_cells=C);hint=int(rng.integers(17,23));u,_=cert.witnesses([runs[0][0]],[runs[0][1]],[hint]);best={hint:float(u[0])}
    for y,a,b in runs:
     values,_=idx.nearest_run(y,a,b,min(best.values()),.00001)
     for c,v in values.items():best[c]=min(best.get(c,math.inf),v)
    m=min(best.values());self.assertEqual({c for c,v in best.items() if v<=m+.00001},self.oracle(runs,seeds,w,.00001))
 def test_antimeridian_poles(self):self.run_case([(0,35,17),(0,1,18),(8,9,19),(8,18,20),(9,27,21),(17,20,22)],[(0,0,1)],20)
 def test_tie(self):self.run_case([(9,17,17),(9,19,18),(4,9,19),(4,18,20),(9,27,21),(17,20,22)],[(9,18,19)],17)
 def test_late_competitor(self):self.run_case([(6,1,17),(6,8,18),(6,14,19),(6,20,20),(6,26,21),(6,32,22)],[(6,2,3),(6,8,9)],17)
 def test_tampered_tile_fails(self):
  seeds=[(6,1,17),(6,8,18),(6,14,19),(6,20,20),(6,26,21),(6,32,22)];tmp,idx,cert=self.make(seeds);self.addCleanup(tmp.cleanup)
  for p in pathlib.Path(tmp.name).glob('*.bin'):p.write_bytes(b'x'*p.stat().st_size)
  with self.assertRaisesRegex(ValueError,'integrity'):idx.nearest_run(6,2,3,20e6)
if __name__=='__main__':unittest.main()
