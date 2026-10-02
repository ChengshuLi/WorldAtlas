import os,json,gzip,struct,math,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely import from_wkb,to_wkb,make_valid
from shapely.ops import unary_union
from pyproj import Geod
P=Path(__file__).parent;geod=Geod(ellps='WGS84');res=json.load(open(P/'result.json'));cs=json.load(open(P/'components.json'))['components'];selected=set([2595,2673])
for e in res['entries']:
 for n in e['named_gap_candidates']:
  if n.get('source_polygon_candidate'):selected.add(n['source_polygon_candidate']['gshhg_id'])
source={c['gshhg_id']:c for c in cs if c['gshhg_id'] in selected};lakeids=set();islandids=set();pondids=set();water=[]
with Path(os.environ.get('WORLDATLAS_GSHHG_BINARY','/tmp/worldatlas-macro-coverage-africa-americas/gshhs_f.b')).open('rb') as f:
 while h:=f.read(44):
  v=struct.unpack('>11i',h);raw=f.read(v[1]*8);lev=v[2]&255;cont=v[9]
  if not(lev==2 and cont in selected or lev==3 and cont in lakeids or lev==4 and cont in islandids):continue
  if lev==2:lakeids.add(v[0])
  elif lev==3:islandids.add(v[0])
  else:pondids.add(v[0])
  coords=np.frombuffer(raw,dtype='>i4').reshape(v[1],2).astype('float64')/1e6;xs=np.rad2deg(np.unwrap(np.deg2rad(coords[:,0])));xs-=360*math.floor((float(xs.mean())+180)/360);coords[:,0]=xs;g=Polygon(coords);valid=g.is_valid
  if not valid:g=make_valid(g)
  path='candidate-components/'+str(v[0])+'-water-mask.wkb.gz';(P/path).write_bytes(gzip.compress(to_wkb(g),mtime=0));water.append(dict(gshhg_id=v[0],level=lev,container=cont,geom=g,path=path,valid=valid))
def area(g):
 if g.is_empty:return 0.
 if g.geom_type=='Polygon':return abs(geod.geometry_area_perimeter(orient(g,1))[0])/1e6
 if g.geom_type in ('GeometryCollection','MultiPolygon'):return sum(area(x) for x in g.geoms)
 return 0.
out=[]
for sid,c in source.items():
 outer=from_wkb(gzip.decompress((P/c['candidate_geometry_path']).read_bytes()));lakes=[a for a in water if a['level']==2 and a['container']==sid];lakeparents={a['gshhg_id'] for a in lakes};islands=[a for a in water if a['level']==3 and a['container'] in lakeparents];islandparents={a['gshhg_id'] for a in islands};ponds=[a for a in water if a['level']==4 and a['container'] in islandparents];land=outer.difference(unary_union([a['geom'] for a in lakes]));land=land.union(unary_union([a['geom'] for a in islands]));land=land.difference(unary_union([a['geom'] for a in ponds]));raw=to_wkb(land);path=f'candidate-components/{sid}-dryland.wkb.gz';(P/path).write_bytes(gzip.compress(raw,mtime=0));out.append(dict(gshhg_id=sid,outer_source_area_km2=area(outer),dryland_area_km2=area(land),lake_ids=sorted(lakeparents),island_in_lake_ids=sorted(islandparents),pond_ids=[a['gshhg_id'] for a in ponds],dryland_geometry_path=path,dryland_geometry_sha256=hashlib.sha256(raw).hexdigest(),source_version='GSHHG2.3.7 full, native level2minus/3plus/4minus hierarchy',audit_only=True))
(P/'water-mask-review.json').write_text(json.dumps(dict(candidate_sources=out,source_hole_fragments=[{k:v for k,v in x.items() if k!='geom'} for x in water]),separators=(',',':'))+'\n');print('sourcecandidates',len(out),'lakefragments',len(water),[(x['gshhg_id'],round(x['outer_source_area_km2'],2),round(x['dryland_area_km2'],2)) for x in out])
