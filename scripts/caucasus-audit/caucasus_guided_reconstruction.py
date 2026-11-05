"""Reconstruct a research line from verified sources plus the selected guide.

The guide supplies order, source assignment, 142 projection queries and the
two endpoints. This is not an independent derivation or historical replay.
Grid test conservatively screens the convex hull between corresponding edges.
"""
import argparse
import hashlib
import json
import math
import shapefile
from pyproj import Geod
from shapely.geometry import LineString, MultiPoint, Point


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


p = argparse.ArgumentParser(description=__doc__)
for name in ('selected','shp','author','edge-screen','edge-screen-sha256','output'):
    p.add_argument('--'+name, required=True)
a = p.parse_args()
with open(a.selected, encoding='utf-8') as f:
    selected = json.load(f)
normal = dict(selected)
normal['coordinates'] = [[float(v) for v in pt] for pt in selected['coordinates']]
canonical = json.dumps(normal,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()
if hashlib.sha256(canonical).hexdigest() != '9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52':
    raise ValueError('selected geometry hash mismatch')
if file_hash(a.shp) != 'aad745e7f15498fc99c34ad9ffc16271ec927cd1e3c223794747220a4dbe2203':
    raise ValueError('HydroBASINS shp hash mismatch')
if file_hash(a.author) != 'c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6':
    raise ValueError('author file hash mismatch')
if file_hash(a.edge_screen) != a.edge_screen_sha256:
    raise ValueError('edge-screen bytes mismatch')
with open(a.edge_screen,encoding='utf-8') as f:
    screen=json.load(f)['records']
lookup={r['index']:r for r in screen}
if len(screen)!=144 or len(lookup)!=144 or 0 not in lookup or 2291 not in lookup:
    raise ValueError('unexpected edge-screen records')
for i,r in lookup.items():
    if [r['lon'],r['lat']] != selected['coordinates'][i]:
        raise ValueError('edge-screen was not generated for selected line')
    if i not in (0,2291) and r['nearest_edge_wgs84_m'] > .001:
        raise ValueError('unresolved interior projection')
with open(a.author,encoding='utf-8') as f:
    author=json.load(f)['features'][463]['geometry']['coordinates']
selected_coords=selected['coordinates']
target={tuple(pt) for i,pt in enumerate(selected_coords) if i not in lookup and i < 1894}
source_vertices={}
for geom in shapefile.Reader(shp=a.shp).iterShapes():
    x0,y0,x1,y1=geom.bbox
    if x1<37 or x0>51 or y1<39 or y0>46: continue
    for pt in geom.points:
        if pt in target:
            source_vertices[pt] = pt
if len(target)!=1751 or len(source_vertices)!=1751:
    raise ValueError('exact source vertices missing or ambiguous')
candidate=[]
for i,pt in enumerate(selected_coords):
    if i in (0,2291): candidate.append(pt) # explicit stored endpoint decisions
    elif i in lookup: candidate.append(lookup[i]['nearest_coordinate'])
    elif 1894 <= i <= 2290:
        source_point=author[i-1893]
        if tuple(source_point)!=tuple(pt): raise ValueError('author run mismatch')
        candidate.append(source_point)
    else:
        if tuple(pt) not in source_vertices: raise ValueError('source vertex mismatch')
        candidate.append(list(source_vertices[tuple(pt)]))
old=LineString(selected_coords); new=LineString(candidate)
if not old.is_simple or not new.is_simple:
    raise ValueError('one of the lines is not simple')
geod=Geod(ellps='WGS84')
displacements=[geod.inv(x,y,u,v)[2] for (x,y),(u,v) in zip(selected_coords,candidate)]
# Existing V7 grid: all cell centres, not just land. A point that changes
# sides under a continuous same-endpoint edge morph must intersect a swept
# edge hull. Convex hulls overapproximate that sweep. Floating-point geometry
# and boundary-tie conventions still need independent pipeline verification.
step=360/131072; west=-180; north=90; width=131072; height=54614
changed_edges=0; tested_centers=0; possible=set()
for i in range(len(candidate)-1):
    if candidate[i]==selected_coords[i] and candidate[i+1]==selected_coords[i+1]: continue
    changed_edges+=1
    hull=MultiPoint([selected_coords[i],selected_coords[i+1],candidate[i],candidate[i+1]]).convex_hull
    minx,miny,maxx,maxy=hull.bounds
    c0=max(0,math.ceil((minx-west)/step-.5));c1=min(width-1,math.floor((maxx-west)/step-.5))
    r0=max(0,math.ceil((north-maxy)/step-.5));r1=min(height-1,math.floor((north-miny)/step-.5))
    for row in range(r0,r1+1):
        for col in range(c0,c1+1):
            tested_centers+=1
            if hull.covers(Point(west+(col+.5)*step,north-(row+.5)*step)):
                possible.add((row,col))
result={'mode':'guided_research_not_historical_replay','geometry':{'type':'LineString','coordinates':candidate},
        'comparison':{'exact_binary64_vertices':sum(tuple(x)==tuple(y) for x,y in zip(selected_coords,candidate)),
        'changed_vertices':sum(tuple(x)!=tuple(y) for x,y in zip(selected_coords,candidate)),
        'max_wgs84_vertex_displacement_m':max(displacements),'changed_edges':changed_edges,
        'grid_width':width,'grid_height':height,'tested_bounding_box_centers':tested_centers,
        'possible_changed_centers':len(possible),'possible_centers':sorted(possible),
        'assumption':'same endpoints, same external closure, simple lines; conservative swept hulls'}}
with open(a.output,'x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result['comparison'],indent=2))
