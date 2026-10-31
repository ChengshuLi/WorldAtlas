"""Replace unsupported long shortcuts with source-mapped divide continuations."""
import json,gzip,numpy as np,argparse
from functools import lru_cache
from pathlib import Path
from shapely.geometry import shape,Point,LineString,box,mapping
from shapely.ops import unary_union,nearest_points,substring
from scipy.spatial import cKDTree
from correct_suez import xyz
parser=argparse.ArgumentParser();parser.add_argument('parent',type=Path);parser.add_argument('basins',type=Path);parser.add_argument('published',type=Path);parser.add_argument('northern_interface',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
meta=json.loads((args.parent/'proposal.json').read_text());S=meta['step'];rr=np.frombuffer(gzip.decompress((args.parent/'rows.u32.gz').read_bytes()),'<u4');vv=np.frombuffer(gzip.decompress((args.parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
@lru_cache(maxsize=64)
def row(y):
 a=vv[rr[y]:rr[y+1]];return np.repeat(a[:,1],np.diff(np.r_[0,a[:,0]])).astype('uint8')
r=json.loads((args.parent/'eurasia-boundary-reference.geojson').read_text());original=json.loads(json.dumps(r));bs=json.loads(gzip.decompress(args.basins.read_bytes()))['features'];pub=json.loads(args.published.read_text())
def biggest(g):return max(g.geoms,key=lambda p:p.area) if g.geom_type=='MultiPolygon' else g
def arc(ring,a,b,guides):
 l=LineString(ring.coords);u,v=sorted([l.project(Point(a)),l.project(Point(b))]);opts=[substring(l,u,v),LineString(list(substring(l,v,l.length).coords)+list(substring(l,0,u).coords)[1:])];g=min(opts,key=lambda q:sum(q.distance(Point(p)) for p in guides));c=list(g.coords)
 if Point(c[0]).distance(Point(a))>Point(c[-1]).distance(Point(a)):c.reverse()
 return c
def coast_snap(q):
 x0,x1=int((q[0]+180-.15)/S),int((q[0]+180+.15)/S)+1;y0,y1=int((90-q[1]-.1)/S),int((90-q[1]+.1)/S)+1;best=None
 for y in range(y0,y1):
  for x in range(x0,x1):
   if int(row(y)[x])<16:continue
   lo=-180+(x+.5)*S;la=90-(y+.5)*S
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
    if int(row(y+dy)[x+dx])>=16:continue
    p=(lo+dx*S/2,float(np.clip(q[1],la-S/2,la+S/2))) if dx else (float(np.clip(q[0],lo-S/2,lo+S/2)),la-dy*S/2)
    d=np.linalg.norm(xyz([p[0]],[p[1]])-xyz([q[0]],[q[1]]))
    if best is None or d<best[0]:best=(d,p)
 assert best is not None,'No nearby native coastline'
 return list(best[1]),float(2*6371.0088*np.arcsin(best[0]/2))
def is_land(p):return int(row(int((90-p[1])/S))[int((p[0]+180)/S)])>=16
def clip_from_sea(line):
 coords=list(line.coords);assert not is_land(coords[0]);last=np.array(coords[0])
 for j,(a,b) in enumerate(zip(coords,coords[1:])):
  a=np.array(a);b=np.array(b);n=max(2,int(np.ceil(np.max(np.abs(b-a))/.0005))+1)
  for q in np.linspace(a,b,n)[1:]:
   if is_land(q):
    left=last.copy();right=q.copy()
    for _ in range(35):
     mid=(left+right)/2
     if is_land(mid):right=mid
     else:left=mid
    # Native shore intersection lies on the published segment itself.
    return [((left+right)/2).tolist(),q.tolist()]+coords[j+1:]
   last=q
 raise ValueError('No native coast intersection')
# Continue the same mapped drainage divide to its source-defined coast endpoint.
eu=biggest(unary_union([shape(f['geometry']).intersection(box(50,53,75,72)) for f in bs if f['properties']['level']==4]));shared=shape(json.loads(args.northern_interface.read_text())['geometry']);verts=[p for g in shared.geoms for p in g.coords];north=max(verts,key=lambda p:p[1]);snap,km=coast_snap(north);river_source=original['features'][1]['geometry']['coordinates'][0];south=nearest_points(Point(river_source),eu.boundary)[1];u=LineString([snap]+arc(eu.exterior,north,(south.x,south.y),[(66.4,68.24),(64.392,66.72),(60.115,65.033),(59.5,62),(60.1,57)]))
# Replace the headwater-to-crest straight shortcut with documented ridge tracing.
pub_source=LineString(list(pub['features'][396]['geometry']['coordinates'])+pub['features'][397]['geometry']['coordinates'][1:]);ints=u.intersection(pub_source).intersection(box(59.3,54.70,59.55,54.75));points=list(ints.geoms) if hasattr(ints,'geoms') else [ints];points=[p for p in points if p.geom_type=='Point'];join=min(points,key=u.project);near=nearest_points(Point(river_source),pub_source)[1];prefix=list(substring(u,0,u.project(join)).coords);tail=list(substring(pub_source,pub_source.project(join),pub_source.project(near)).coords);uc=prefix+tail[1:]+[river_source];assert LineString(uc).is_simple
r['features'][0]['geometry']=mapping(LineString(uc));r['features'][0]['properties']={'name':'Urals watershed','source':'BasinATLAS v1.0 drainage divide, including its northern continuation; published ridge tracing near Ural headwaters','source_url':'https://doi.org/10.6084/m9.figshare.9890531','license':'BasinATLAS: CC BY4.0; selected ridge tracing: attribution to Alexandr Trubetskoy','attribution':'Linke et al. (2019); Alexandr Trubetskoy, https://sashamaps.net/resources/europe-asia-boundary/','north_source_endpoint':list(north),'native_coast_endpoint':snap,'north_coast_alignment_km':km,'headwater_join':[join.x,join.y],'headwater_alignment_degrees':near.distance(Point(river_source)),'note':'The northern straight lowland shortcut is removed. The native-coast snap accommodates shoreline differences; no land/water cells are created.'}
# Western Caucasus: retain central watershed, use corroborated published ridge
# continuation west to its actual intersection with the native coastline.
a=LineString(original['features'][2]['geometry']['coordinates'][1:-1]);b=shape(pub['features'][462]['geometry']);ints=a.intersection(b).intersection(box(37.6,44.7,37.85,44.9));points=list(ints.geoms);join=min(points,key=lambda p:p.x);west_segment=substring(b,b.project(join),b.length);west_segment=LineString(list(west_segment.coords)[::-1]);wc=clip_from_sea(west_segment);cc=wc+list(substring(a,a.project(join),a.length).coords)[1:]+[original['features'][2]['geometry']['coordinates'][-1]];assert LineString(cc).is_simple
r['features'][2]['geometry']=mapping(LineString(cc));p=r['features'][2]['properties'];p['coast_connectors']=[p['coast_connectors'][-1]];p['western_ridge_source']='Alexandr Trubetskoy, https://sashamaps.net/resources/europe-asia-boundary/ (attribution required)';p['western_native_coast_endpoint']=wc[0];p['western_join']=[join.x,join.y];p['western_validation']='Compared with Copernicus GLO-90 elevation: follows the ridge westward, unlike the removed constant-longitude valley-crossing shortcut.'
args.output.write_text(json.dumps(r));print('north coastal alignment km',km,'source',north,'native',snap);print('western coast',wc[0],'join',join);print('Ural source residual gap km',2*6371.0088*np.arcsin(np.linalg.norm(xyz([near.x],[near.y])-xyz([river_source[0]],[river_source[1]]))/2));print('vertices',len(uc),len(cc))
