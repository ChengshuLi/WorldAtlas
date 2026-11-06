"""Screen an Anapa closure using the pinned draft163 mask; not a proof."""
import importlib.util, hashlib, json, heapq
from pathlib import Path
import numpy as np
from fractions import Fraction
snapshot=json.loads(Path('caucasus-real-snapshot-recipe-local.json').read_text())
old=next(r for r in snapshot['routes'] if r['route_id']=='europe_exterior_closure_v1')['geometry']['coordinates']
ural=next(r for r in snapshot['mainland_boundaries'] if r['boundary_id']=='ural_kara_coast_to_caspian')['geometry']
candidate=json.loads(Path('/tmp/caucasus-anapa-candidate-r2.json').read_text())
path=json.loads(Path('/tmp/anapa-impact-route.json').read_text())['water_path_coordinates']
step=360/131072
def xy(q):return [-180+(q[1]+.5)*step,90-(q[0]+.5)*step]
rows=np.fromfile('/tmp/ural-draft82/physical-rows.u32le',dtype='<u4');runs=np.memmap('/tmp/ural-draft82/physical-runs.u32le',dtype='<u4',mode='r').reshape(-1,2)
def code(x,y):
 a=runs[rows[y]:rows[y+1]]
 return int(a[np.searchsorted(a[:,0],x,side='right'),1])
def route(start,end):
 queue=[start]; previous={start:None}
 for q in queue:
  if q==end:break
  for dr,dc in ((0,-1),(-1,0),(1,0),(0,1)):
   p=(q[0]+dr,q[1]+dc)
   if 16380<p[0]<16510 and 79000<p[1]<79200 and p not in previous and code(p[1],p[0])==1:previous[p]=q;queue.append(p)
 if end not in previous:raise ValueError('no water path')
 out=[];q=end
 while q is not None:out.append(q);q=previous[q]
 return out[::-1]
anchor=(16419,79065); via=(16436,79065); terminal=(16457,79141)
track=route(anchor,via)+route(via,terminal)[1:]
points=old[:-2]+[xy(q) for q in track]+[candidate['coordinates'][0]]
geom={'type':'LineString','coordinates':points}
raw=json.dumps(geom,sort_keys=True,separators=(',',':')).encode()
Path('/tmp/anapa-new-closure.json').write_bytes(raw)
checker=Path('caucasus-v2-new/mainland-seed-l2/closure-checkers/validate_terminal_closure.py')
s=importlib.util.spec_from_file_location('terminal',checker);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.m.WIDTH=131072;m.m.HEIGHT=54614;m.m.WEST=Fraction(-180);m.m.NORTH=Fraction(90);m.m.STEP=Fraction(360,131072)
_,pts=m.m.geom_and_points(raw)
_,start=m.m.geom_and_points(json.dumps(ural).encode())
_,end=m.m.geom_and_points(json.dumps(candidate).encode())
result=m.verify_path(pts,start[0],end[0],code,1,17,10000000)
print(json.dumps({'candidate_closure_sha256':hashlib.sha256(raw).hexdigest(),'vertices':len(points),'screen':result},indent=2))
