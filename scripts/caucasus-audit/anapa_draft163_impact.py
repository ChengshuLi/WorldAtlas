"""Bounded Anapa comparison on the verified draft163 physical mask.

The water path is a diagnostic closure, not a production closure proof. Only
land cell centers are counted; inputs, hashes, and ambiguity are reported.
"""
import argparse, hashlib, heapq, json, math
from pathlib import Path
import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union, polygonize
from geodesic_nearest import nearest_cell

parser=argparse.ArgumentParser()
parser.add_argument('--physical-rows',required=True)
parser.add_argument('--physical-runs',required=True)
parser.add_argument('--selected',required=True)
parser.add_argument('--candidate',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--offshore-waypoint',action='store_true')
args=parser.parse_args()
ROWS=args.physical_rows
RUNS=args.physical_runs
EXPECTED=('6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468','1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7')
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
assert tuple(map(digest,(ROWS,RUNS)))==EXPECTED
assert digest(args.selected)=='8c001c61c46ced35905239eccdc4f17b16858df0e1cb76b3e7815f3d61cfde3b'
assert digest(args.candidate)=='1c30e158f222ffe2c23293e69a69a99a1d8fbcf03f6032cb8401d320d94628bc'
step=360/131072
rows=np.fromfile(ROWS,dtype='<u4'); runs=np.memmap(RUNS,dtype='<u4',mode='r').reshape(-1,2)
def ij(p):return (int((90-p[1])/step),int((p[0]+180)/step))
def xy(q):return (-180+(q[1]+.5)*step,90-(q[0]+.5)*step)
def cls(q):
 a=runs[rows[q[0]]:rows[q[0]+1]]
 return int(a[np.searchsorted(a[:,0],q[1],side='right'),1])
def nearest_water(p):
 row,col=ij(p); water=[]
 for dr in range(-4,5):
  for dc in range(-4,5):
   q=(row+dr,col+dc)
   if cls(q)==1: water.append((q,*xy(q)))
 if not water: raise ValueError('no nearby water cell')
 return nearest_cell(p, water)
def path(start,end):
 # Exact 4-neighbor water path, restricted to a local coastal window.
 queue=[(0,start)]; dist={start:0}; previous={}
 while queue:
  cost,q=heapq.heappop(queue)
  if cost!=dist[q]:continue
  if q==end:
   result=[q]
   while q!=start:q=previous[q];result.append(q)
   return result[::-1]
  for dr,dc in ((0,-1),(-1,0),(1,0),(0,1)):
   n=(q[0]+dr,q[1]+dc)
   if not (16350<n[0]<16550 and 79000<n[1]<79230) or cls(n)!=1:continue
   new=cost+1
   if new<dist.get(n,10**9): dist[n]=new; previous[n]=q;heapq.heappush(queue,(new,n))
 raise ValueError('no water path')
old=json.load(open(args.selected))['coordinates']
new=json.load(open(args.candidate))['coordinates']
assert old[-1]==new[-1]
start,end=nearest_water(new[0]),nearest_water(old[0])
waypoint=(16436,79065) if args.offshore_waypoint else None
if waypoint is not None and cls(waypoint)!=1:raise ValueError('offshore waypoint is not water')
route=path(start,end) if waypoint is None else path(start,waypoint)+path(waypoint,end)[1:]
ring=old+list(reversed(new[:-1]))+[xy(q) for q in route]+[old[0]]
def odd_crossing(point):
 x,y=point.x,point.y; parity=False
 for a,b in zip(ring,ring[1:]):
  if (a[1]>y)!=(b[1]>y):
   cross=a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
   if x<cross:parity=not parity
 return parity
faces=list(polygonize(unary_union(LineString(ring))))
poly=unary_union([p for p in faces if odd_crossing(p.representative_point())])
if poly.is_empty or not poly.is_valid:raise ValueError('diagnostic closure produces invalid area')
lo,bot,hi,top=poly.bounds
land=[];water=0
for row in range(max(0,int((90-top)/step)-1),int((90-bot)/step)+2):
 for col in range(int((lo+180)/step)-1,int((hi+180)/step)+2):
  q=(row,col)
  if poly.contains(Point(xy(q))):
   if cls(q)==17:land.append(q)
   elif cls(q)==1:water+=1
   else:raise ValueError('unexpected physical code')
out={'status':'bounded_diagnostic_not_production_closure','physical_rows_sha256':EXPECTED[0],'physical_runs_sha256':EXPECTED[1],
     'candidate_sha256':digest(args.candidate),'selected_sha256':digest(args.selected),
     'land_cell_count':len(land),'land_cells':land,'water_cell_count':water,'water_path_centers':len(route),
     'candidate_endpoint_cell_code':cls(ij(new[0])),'selected_endpoint_cell_code':cls(ij(old[0])),
     'bounded_faces':len(faces),
     'offshore_waypoint':waypoint,
     'water_path_start':list(start),'water_path_end':list(end),
     'limitations':['draft163 stand-in mask, latest generation unverified','diagnostic water-cell path, not a production closure proof','terminal connection to coast is not independently water-closure validated']}
Path(args.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='land_cells'},indent=2))
