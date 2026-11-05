#!/usr/bin/env python3
"""Check closed-cell contacts of a pinned closure using independent GEOS boxes.

Manifest inputs physical_rows, physical_runs and closure have path and byte
sha256; closure is a JSON point list. geometry_sha256 hashes canonical GeoJSON
with sorted keys and compact UTF-8 serialization. config contains width,
height, west, north, step_degrees, physical_land_code and physical_water_code.
Caller authenticates the manifest, selected route and its terminal policy,
and independently verifies full RLE structure. This floating-point topology
screen is not a certified exact supercover or a geographic source validation.
"""
import argparse,collections,hashlib,json,math
if not __debug__: raise RuntimeError('optimized Python disables audit assertions')
import numpy as np
from shapely.geometry import LineString,box

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);a=p.parse_args()
m=json.load(open(a.manifest));cfg=m['config'];names=['physical_rows','physical_runs','closure'];inputs=m['inputs'];paths=[inputs[n]['path'] for n in names];pins=[inputs[n]['sha256'] for n in names]
assert [sha(path) for path in paths]==pins,'input hash mismatch'
points=json.load(open(paths[2]));geometry={'type':'LineString','coordinates':points};canonical=json.dumps(geometry,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
assert hashlib.sha256(canonical).hexdigest()==m['geometry_sha256'],'selected closure mismatch'
width,height=cfg['width'],cfg['height'];step=cfg['step_degrees'];west,north=cfg['west'],cfg['north'];land,water=cfg['physical_land_code'],cfg['physical_water_code']
rows=np.memmap(paths[0],dtype='<u4',mode='r');runs=np.memmap(paths[1],dtype='<u4',mode='r').reshape(-1,2);assert len(rows)==height+1 and rows[0]==0 and rows[-1]==len(runs)
gp=[((lon-west)/step,(north-lat)/step) for lon,lat in points];assert len(gp)>=2
assert all(abs(x-round(x))>1e-12 and abs(y-round(y))>1e-12 for x,y in (gp[0],gp[-1])), 'terminal falls on grid edge'
visited=set(); land_by_segment=collections.defaultdict(set);visits=0
for i,(start,end) in enumerate(zip(gp,gp[1:])):
 line=LineString((start,end));assert not line.is_empty and line.length>0
 for x in range(math.floor(min(start[0],end[0]))-1,math.floor(max(start[0],end[0]))+2):
  for y in range(math.floor(min(start[1],end[1]))-1,math.floor(max(start[1],end[1]))+2):
   if not line.intersects(box(x,y,x+1,y+1)):continue
   assert 0<=x<width and 0<=y<height;visits+=1;assert visits<=m.get('max_cell_visits',2000000)
   row=runs[int(rows[y]):int(rows[y+1])];assert len(row) and row[-1,0]==width
   code=int(row[np.searchsorted(row[:,0],x,side='right'),1]);assert code in (water,land)
   visited.add((x,y,code))
   if code==land:land_by_segment[i].add((x,y))
terminal_cells=[(math.floor(x),math.floor(y)) for x,y in (gp[0],gp[-1])]
permitted=[bool(m['allow_land_at_start']),bool(m['allow_land_at_end'])];last=len(gp)-2
ok=all((i==0 and permitted[0] and cells=={terminal_cells[0]}) or (i==last and permitted[1] and cells=={terminal_cells[1]}) for i,cells in land_by_segment.items())
assert [sha(path) for path in paths]==pins,'input changed during check'
codes=collections.Counter(c for _,_,c in visited);out={'geometry_sha256':m['geometry_sha256'],'inputs':inputs,'segments':last+1,'cell_visits':visits,'unique_cells':len(visited),'code_counts':dict(codes),'terminals':terminal_cells,'land_cells_by_segment':{str(k):sorted(v) for k,v in land_by_segment.items()},'terminal_policy_satisfied':ok,'limitations':['GEOS floating-point line/closed-box intersections are not an exact rational supercover proof.','Does not establish source geography, current selection or correctness of caller-supplied terminal policy.']}
with open(a.output,'x') as f:json.dump(out,f,sort_keys=True,indent=2)
print(json.dumps({k:out[k] for k in ('segments','cell_visits','unique_cells','code_counts','terminal_policy_satisfied')}))
