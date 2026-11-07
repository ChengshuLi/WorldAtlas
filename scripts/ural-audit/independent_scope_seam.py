#!/usr/bin/env python3
"""Independently screen pinned RLE overlay sides and land-to-land scope seams.

The input manifest has candidate_revision, config (bounds, width, height,
west, north, step_degrees, europe_code, asia_code), physical_land_code,
independent_europe_witness, and inputs. Each input (base_rows, base_runs,
physical_rows, physical_runs, overlay_rows, overlay_runs, divider) supplies
path and uncompressed sha256. Divider is a source-derived lon/lat point list.

Caller must authenticate the selected source, category codec and manifest,
verify complete RLE structure, and establish the witness's side independently.
This is a floating-point ray-parity diagnostic, not certified exact geometry,
a water seam check, an independent geographic survey, or a global diff.
"""
import json,hashlib,math,collections,argparse
if not __debug__: raise RuntimeError('optimized Python disables audit assertions')
import numpy as np
from shapely.geometry import LineString, Point

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
parser=argparse.ArgumentParser(description='Independent witness-ray audit of pinned base and overlay scope')
parser.add_argument('--manifest',required=True,help='JSON config with paths and SHA-256 pins; caller authenticates source selection')
parser.add_argument('--output',required=True,help='new output JSON path')
args=parser.parse_args(); manifest=json.load(open(args.manifest)); cfg=manifest['config']
names=['base_rows','base_runs','physical_rows','physical_runs','overlay_rows','overlay_runs']
paths=[manifest['inputs'][n]['path'] for n in names];pins=[manifest['inputs'][n]['sha256'] for n in names]
assert [sha(p) for p in paths]==pins
dividerpath=manifest['inputs']['divider']['path'];assert sha(dividerpath)==manifest['inputs']['divider']['sha256']
rows=[np.memmap(paths[i],dtype='<u4',mode='r') for i in (0,2,4)]
runs=[np.memmap(paths[i],dtype='<u4',mode='r').reshape(-1,2) for i in (1,3,5)]
def value(which,x,y):
 row=runs[which][int(rows[which][y]):int(rows[which][y+1])]
 return int(row[np.searchsorted(row[:,0],x,side='right'),1])
step=cfg['step_degrees'];w,s,e,n=cfg['bounds'];west,north=cfg['west'],cfg['north']
eu_code,asia_code=cfg['europe_code'],cfg['asia_code'];physical_land=manifest['physical_land_code']
lon=lambda x:west+(x+.5)*step
lat=lambda y:north-(y+.5)*step
x0=math.floor((w-west)/step-.5);x1=math.floor((e-west)/step-.5)
y0=math.floor((north-n)/step-.5);y1=math.floor((north-s)/step-.5)
assert lon(x0)<w<lon(x0+1) and lon(x1)<e<lon(x1+1)
assert lat(y0)>n>lat(y0+1) and lat(y1)>s>lat(y1+1)
assert 0<=x0<x1+1<cfg['width'] and 0<=y0<y1+1<cfg['height']
divider=LineString(json.load(open(dividerpath)));witness=Point(*manifest['independent_europe_witness'])
assert w<witness.x<e and s<witness.y<n and not divider.intersects(witness)
counts=collections.Counter();details=[]
def count_crossings(g):
 if g.is_empty:return 0
 if g.geom_type=='Point':return 1
 if g.geom_type=='MultiPoint':return len(g.geoms)
 raise ValueError('ambiguous ray/line intersection '+g.geom_type)
def screen(name,inside,outside):
 counts[name+'_pairs']+=1
 x,y=inside; a,b=outside
 if value(1,x,y)!=physical_land or value(1,a,b)!=physical_land:counts[name+'_not_both_land']+=1;return
 iv,ov=value(0,x,y),value(0,a,b)
 if iv not in (asia_code,eu_code) or ov not in (asia_code,eu_code):counts[name+'_other_labels']+=1;return
 pt=Point(lon(x),lat(y)); q=Point(lon(a),lat(b)); cross=LineString([pt,q]).intersection(divider)
 if not cross.is_empty:counts[name+'_divider_contacts']+=1;return
 z=LineString([witness,pt]).intersection(divider); side=eu_code if count_crossings(z)%2==0 else asia_code
 actual=value(2,x,y); actual_outside=value(2,a,b)
 if actual!=side:counts[name+'_ray_vs_actual_overlay']+=1
 if actual_outside!=ov:counts[name+'_outside_changed']+=1
 counts[name+'_eligible_land_pairs']+=1
 counts[name+'_before_mismatch']+=int(iv!=ov);counts[name+'_after_mismatch']+=int(actual!=actual_outside)
 if actual!=actual_outside:details.append({'edge':name,'inside':[x,y],'outside':[a,b],'base_inside':iv,'base_outside':ov,'overlay_inside':actual,'overlay_outside':actual_outside})
for y in range(y0+1,y1+1):
 screen('west',(x0+1,y),(x0,y));screen('east',(x1,y),(x1+1,y))
for x in range(x0+1,x1+1):
 screen('north',(x,y0+1),(x,y0));screen('south',(x,y1),(x,y1+1))
full_scope=collections.Counter();full_examples=[]
for y in range(y0+1,y1+1):
 for x in range(x0+1,x1+1):
  if value(1,x,y)!=physical_land:continue
  full_scope['physical_land']+=1
  actual=value(2,x,y)
  if actual not in (asia_code,eu_code):full_scope['other_labels']+=1;continue
  pt=Point(lon(x),lat(y))
  if divider.intersects(pt):raise ValueError('physical center on divider')
  side=eu_code if count_crossings(LineString([witness,pt]).intersection(divider))%2==0 else asia_code
  if actual!=side:
   full_scope['ray_vs_actual_mismatches']+=1
   if len(full_examples)<20:full_examples.append([x,y,actual,side])
assert [sha(p) for p in paths]==pins and sha(dividerpath)==manifest['inputs']['divider']['sha256'], 'input changed during check'
out={'candidate_revision':manifest['candidate_revision'],'inputs':manifest['inputs'],'counts':dict(counts),'after_mismatch_details':details,'full_scope':dict(full_scope),'full_scope_mismatch_examples':full_examples,'method':'Independent witness-ray crossing parity compared to all physical-land actual-overlay centers and neighboring actual overlay outside labels. For seams both cells physical land, Europe/Asia labels only; pairs intersecting the selected divider excluded. This is not an independent geographic survey. Point intersections use GEOS floating-point geometry; ambiguity at tangencies or crossings through vertices not mathematically certified. Selection remains point-in-time.'}
with open(args.output,'x') as f:json.dump(out,f,sort_keys=True,indent=2)
print(json.dumps({'candidate_revision':out['candidate_revision'],'counts':out['counts'],'full_scope':out['full_scope']}))
