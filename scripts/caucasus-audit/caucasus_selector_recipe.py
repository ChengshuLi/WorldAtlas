"""Build a non-selected source-selector recipe from the stored line guide.

The recipe's origin is the selected line, not independent geographic evidence.
"""
import argparse
import hashlib
import json
import shapefile
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()


p=argparse.ArgumentParser(description=__doc__)
for n in ('selected','shp','edge-screen','edge-screen-sha256','output'):p.add_argument('--'+n,required=True)
a=p.parse_args()
with open(a.selected,encoding='utf-8') as f: line=json.load(f)
normal=dict(line);normal['coordinates']=[[float(v) for v in pt] for pt in line['coordinates']]
h=hashlib.sha256(json.dumps(normal,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
if h!='9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52':raise ValueError('selected hash')
if sha(a.shp)!='aad745e7f15498fc99c34ad9ffc16271ec927cd1e3c223794747220a4dbe2203':raise ValueError('shp hash')
if sha(a.edge_screen)!=a.edge_screen_sha256:raise ValueError('edge screen hash')
with open(a.edge_screen,encoding='utf-8') as f: screen=json.load(f)['records']
points=line['coordinates'];interior={r['index']:r for r in screen if r['index'] not in (0,2291)}
if len(interior)!=142 or any(r['nearest_edge_wgs84_m']>.001 or [r['lon'],r['lat']]!=points[i] for i,r in interior.items()):raise ValueError('screen mismatch')
targets={tuple(points[i]):i for i in range(1,1894) if i not in interior}
if len(targets)!=1751:raise ValueError('unexpected exact targets')
vertex_refs={};rings=[];ring_meta=[]
for shape_i, geom in enumerate(shapefile.Reader(shp=a.shp).iterShapes()):
    x0,y0,x1,y1=geom.bbox
    if x1<37 or x0>51 or y1<39 or y0>46:continue
    for point_i,pt in enumerate(geom.points):
        if pt in targets:
            i=targets[pt];ref=[shape_i,point_i]
            if i not in vertex_refs or ref<vertex_refs[i]:vertex_refs[i]=ref
    if not any(x0-1e-8 <= r['nearest_coordinate'][0] <= x1+1e-8 and y0-1e-8 <= r['nearest_coordinate'][1] <= y1+1e-8 for r in interior.values()):continue
    bounds=list(geom.parts)+[len(geom.points)]
    for begin,end in zip(bounds,bounds[1:]):
        if end-begin<2:continue
        coords=geom.points[begin:end];rings.append(LineString(coords));ring_meta.append((shape_i,begin,coords))
if len(vertex_refs)!=1751:raise ValueError('missing exact source vertices')
tree=STRtree(rings);edge_refs={}
for i,r in interior.items():
    pt=Point(r['nearest_coordinate']);candidates=[]
    for j in tree.query(pt.buffer(1e-8)):
        shape_i,begin,coords=ring_meta[int(j)]
        for k,(u,v) in enumerate(zip(coords,coords[1:])):
            seg=LineString([u,v]);dist=seg.distance(pt)
            if dist<=1e-10:
                t=seg.project(pt,normalized=True)
                candidates.append((dist,shape_i,begin+k,t))
    if not candidates:raise ValueError('no matching source segment for '+str(i))
    best=min(x[0] for x in candidates)
    _,shape_i,point_i,t=min((x for x in candidates if x[0]<=best+1e-12),key=lambda x:(x[1],x[2]))
    edge_refs[i]=[shape_i,point_i,t]
selectors=[]
for i in range(1,1894):
    if i in interior:selectors.append({'kind':'edge','ref':edge_refs[i]})
    else:selectors.append({'kind':'vertex','ref':vertex_refs[i]})
recipe={'schema':'caucasus-selector-research-v1','status':'unselected_research',
 'selected_guide_geometry_sha256':h,'hydro_shp_sha256':sha(a.shp),
 'author_file_sha256':'c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6',
 'hydro_selectors':selectors,'author_feature_index':463,'author_start':1,'author_stop':398,
 'start_endpoint':points[0],'end_endpoint':points[-1],
 'limits':'Derived from the selected guide; not a historical construction or accepted watershed.'}
with open(a.output,'x',encoding='utf-8') as f:json.dump(recipe,f,sort_keys=True,separators=(',',':'))
print('selectors',len(selectors),'vertices',len(vertex_refs),'edge_interpolations',len(edge_refs),'recipe_sha256',sha(a.output))
