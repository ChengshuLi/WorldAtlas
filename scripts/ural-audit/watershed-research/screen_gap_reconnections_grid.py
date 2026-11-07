import json,hashlib,math,numpy as np
if not __debug__: raise RuntimeError('optimized Python disables validation assertions')
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,polygonize
from shapely.prepared import prep
step=0.00274658203125
p='/tmp/ural-draft82/physical-rows.u32le';q='/tmp/ural-draft82/physical-runs.u32le'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
assert sha(p)=='6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468';assert sha(q)=='1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7'
rows=np.memmap(p,dtype='<u4');runs=np.memmap(q,dtype='<u4').reshape(-1,2)
for n in ('00','02'):
 a='/tmp/ural-gap'+n+'-arctic-intersection-route.json';b='/tmp/ural-gap'+n+'-cop-intersection-route.json';x=LineString(json.load(open(a))['reconnected_source_coordinates']);y=LineString(json.load(open(b))['reconnected_source_coordinates']);assert x.is_simple and y.is_simple and x.coords[0]==y.coords[0] and x.coords[-1]==y.coords[-1]
 z=unary_union(list(polygonize(unary_union([x,y]))));w,s,e,top=z.bounds;pix=[]
 for row in range(math.ceil((90-top)/step-.5),math.floor((90-s)/step-.5)+1):
  r=runs[rows[row]:rows[row+1]]
  for col in range(math.ceil((w+180)/step-.5),math.floor((e+180)/step-.5)+1):
   pt=Point(-180+(col+.5)*step,90-(row+.5)*step)
   if z.boundary.intersects(pt):raise ValueError('ambiguous center')
   if z.contains(pt):pix.append([col,row,int(r[np.searchsorted(r[:,0],col,side='right'),1])])
 print(json.dumps({'gap':n,'physical_land':sum(i[2]==17 for i in pix),'physical_water':sum(i[2]==1 for i in pix),'candidate_cells':pix,'arctic_file_sha256':sha(a),'copernicus_file_sha256':sha(b),'limits':'research polygons only; same fallback source and cuts, no map or labels produced'}),flush=True)
assert sha(p)=='6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468';assert sha(q)=='1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7'
