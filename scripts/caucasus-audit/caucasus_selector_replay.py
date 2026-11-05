"""Replay an explicit unselected selector recipe; optionally compare a guide.

The selectors were extracted from a stored guide, not independently verified.
"""
import argparse
import hashlib
import json
import math
import shapefile
from pyproj import Geod
from shapely.geometry import LineString,MultiPoint,Point


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


p=argparse.ArgumentParser(description=__doc__)
for n in ('recipe','recipe-sha256','shp','author','output'):p.add_argument('--'+n,required=True)
p.add_argument('--compare',help='optional selected geometry for research validation')
a=p.parse_args()
if sha(a.recipe)!=a.recipe_sha256:raise ValueError('recipe hash mismatch')
with open(a.recipe,encoding='utf-8') as f:r=json.load(f)
if r.get('schema')!='caucasus-selector-research-v1' or r.get('status')!='unselected_research':raise ValueError('wrong recipe')
if sha(a.shp)!=r['hydro_shp_sha256'] or sha(a.author)!=r['author_file_sha256']:raise ValueError('source hash mismatch')
selectors=r['hydro_selectors']
if len(selectors)!=1893:raise ValueError('unexpected selector count')
needed={q['ref'][0] for q in selectors};shapes={}
for i,g in enumerate(shapefile.Reader(shp=a.shp).iterShapes()):
    if i in needed:shapes[i]=g
if set(shapes)!=needed:raise ValueError('source shapes missing')
coords=[r['start_endpoint']]
for q in selectors:
    si,pi=q['ref'][:2];g=shapes[si]
    if not (0<=pi<len(g.points)):raise ValueError('bad point index')
    u=g.points[pi]
    if q['kind']=='vertex':coords.append(list(u))
    elif q['kind']=='edge':
        if len(q['ref'])!=3 or pi+1>=len(g.points) or pi+1 in g.parts:raise ValueError('bad ring edge')
        t=q['ref'][2]
        if not math.isfinite(t) or not 0<=t<=1:raise ValueError('bad interpolation')
        v=g.points[pi+1];coords.append([u[0]+t*(v[0]-u[0]),u[1]+t*(v[1]-u[1])])
    else:raise ValueError('bad selector kind')
with open(a.author,encoding='utf-8') as f:author=json.load(f)['features'][r['author_feature_index']]['geometry']['coordinates']
coords.extend(author[r['author_start']:r['author_stop']]);coords.append(r['end_endpoint'])
if len(coords)!=2292 or not LineString(coords).is_simple:raise ValueError('invalid replay geometry')
normal={'type':'LineString','coordinates':[[float(v) for v in pt] for pt in coords]}
canonical=hashlib.sha256(json.dumps(normal,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
result={'status':'unselected_research','geometry':normal,'geometry_sha256':canonical}
if a.compare:
    with open(a.compare,encoding='utf-8') as f:guide=json.load(f)
    normal_guide=dict(guide)
    normal_guide['coordinates']=[[float(v) for v in pt] for pt in guide['coordinates']]
    guide_hash=hashlib.sha256(json.dumps(normal_guide,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    if guide_hash!=r['selected_guide_geometry_sha256']:raise ValueError('comparison guide hash mismatch')
    other=guide['coordinates']
    if len(other)!=len(coords) or not LineString(other).is_simple:raise ValueError('invalid comparison geometry')
    if tuple(other[0])!=tuple(coords[0]) or tuple(other[-1])!=tuple(coords[-1]):raise ValueError('endpoints differ')
    geod=Geod(ellps='WGS84');dist=[geod.inv(*x,*y)[2] for x,y in zip(other,coords)]
    width=131072;height=54614;step=360/width;possible=set();tests=0;edges=0
    for i in range(len(coords)-1):
        if coords[i]==other[i] and coords[i+1]==other[i+1]:continue
        edges+=1
        hull=MultiPoint([coords[i],coords[i+1],other[i],other[i+1]]).convex_hull.buffer(1e-10)
        x0,y0,x1,y1=hull.bounds
        c0=max(0,math.ceil((x0+180)/step-.5));c1=min(width-1,math.floor((x1+180)/step-.5))
        r0=max(0,math.ceil((90-y1)/step-.5));r1=min(height-1,math.floor((90-y0)/step-.5))
        for row in range(r0,r1+1):
            for col in range(c0,c1+1):
                tests+=1
                if hull.covers(Point(-180+(col+.5)*step,90-(row+.5)*step)):possible.add((row,col))
    result['comparison']={'exact_vertices':sum(tuple(x)==tuple(y) for x,y in zip(other,coords)),
     'changed_vertices':sum(tuple(x)!=tuple(y) for x,y in zip(other,coords)),
     'maximum_wgs84_vertex_displacement_m':max(dist),'changed_edges':edges,
     'grid_width':width,'grid_height':height,'bounding_box_center_tests':tests,
     'possible_changed_centers':len(possible),'possible_centers':sorted(possible),
     'assumption':'same endpoints and external closure; conservative padded edge hulls'}
with open(a.output,'x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='geometry'},indent=2))
