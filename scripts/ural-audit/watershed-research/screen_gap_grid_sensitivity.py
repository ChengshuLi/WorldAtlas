import json,math,hashlib,numpy as np
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,polygonize
from shapely.prepared import prep

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
inputs={'physical_rows':('/tmp/ural-draft82/physical-rows.u32le','6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468'),'physical_runs':('/tmp/ural-draft82/physical-runs.u32le','1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7')}
for k,(p,h) in inputs.items():
 if sha(p)!=h:raise ValueError('hash mismatch '+k)
rows=np.memmap(inputs['physical_rows'][0],dtype='<u4',mode='r');runs=np.memmap(inputs['physical_runs'][0],dtype='<u4',mode='r').reshape(-1,2);W=131072;H=54614;step=0.00274658203125
for n in ('00','02'):
 for variant in ('30m-arctic','30m-cop','30m-smaller-domain'):
  ap='/tmp/ural-gap'+n+'-d8-15m-research.json'; bp={'30m-arctic':'/tmp/ural-gap'+n+'-d8-interface-research.json','30m-cop':'/tmp/ural-gap'+n+'-cop-d8-interface-research.json','30m-smaller-domain':'/tmp/ural-gap'+n+'-d8-smaller-domain-research.json'}[variant]
  a=LineString(json.load(open(ap))['coordinates']);b=LineString(json.load(open(bp))['coordinates'])
  if not a.is_simple or not b.is_simple or a.coords[0]!=b.coords[0] or a.coords[-1]!=b.coords[-1]:raise ValueError('invalid lines or unshared endpoints')
  faces=list(polygonize(unary_union([a,b])));shape=unary_union(faces);result={'gap':n,'variant':variant,'line_a_sha256':sha(ap),'line_b_sha256':sha(bp),'faces':len(faces),'cell_events':[],'caveat':'Planar longitude/latitude topology between two exploratory lines with common endpoints; exact native-grid cell centers. Potential side differences only, no map rebuilt, not a selected boundary. No labels or mask exceptions decided.'}
  if faces:
   w,s,e,nn=shape.bounds;x0=max(0,math.ceil((w+180)/step-.5));x1=min(W-1,math.floor((e+180)/step-.5));y0=max(0,math.ceil((90-nn)/step-.5));y1=min(H-1,math.floor((90-s)/step-.5));ps=prep(shape)
   for y in range(y0,y1+1):
    row=runs[rows[y]:rows[y+1]]
    for x in range(x0,x1+1):
     p=Point(-180+(x+.5)*step,90-(y+.5)*step)
     if shape.boundary.intersects(p):raise ValueError('center on polygon boundary')
     if ps.contains(p):result['cell_events'].append([x,y,int(row[np.searchsorted(row[:,0],x,side='right'),1])])
  result['land_cells']=sum(v[2]==17 for v in result['cell_events']);result['water_cells']=sum(v[2]==1 for v in result['cell_events']);print(json.dumps(result,sort_keys=True),flush=True)
for k,(p,h) in inputs.items():
 if sha(p)!=h:raise ValueError('input changed '+k)
