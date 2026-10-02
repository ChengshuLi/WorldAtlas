from pathlib import Path
import json,gzip,struct,hashlib,math
import numpy as np
from shapely import from_wkb,make_valid,to_wkb,orient_polygons,STRtree,union_all
from shapely.geometry import Polygon
from pyproj import Geod
P=Path('/tmp/worldatlas-macro-coverage-africa-americas');repo=Path('/workspace/WorldAtlas');geod=Geod(ellps='WGS84');obj=json.load(open(P/'components-reviewed.json'));cs=obj['components'];selected={c['gshhg_id'] for c in cs};children={};level3children={};records=[];rawpack=[];offsetpack=0
f=(P/'gshhs_f.b').open('rb')
while hdr:=f.read(44):
 v=struct.unpack('>11i',hdr);offset=f.tell()-44;raw=f.read(v[1]*8);lev=v[2]&255
 if lev!=2 or v[9] not in selected:continue
 co=np.frombuffer(raw,dtype='>i4').reshape(v[1],2).astype('float64')/1e6;xs=np.rad2deg(np.unwrap(np.deg2rad(co[:,0])));xs-=360*math.floor((float(xs.mean())+180)/360);co[:,0]=xs;g=Polygon(co);valid=g.is_valid
 if not valid:g=make_valid(g)
 children.setdefault(v[9],[]).append((v[0],g));b=hdr+raw;rawpack.append(b);records.append(dict(id=v[0],level=lev,parent_id=v[9],source_offset=offset,source_bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),pack_offset=offsetpack,source_polygon_valid=valid));offsetpack+=len(b)
(P/'selected-gshhg-water-records.bin.gz').write_bytes(gzip.compress(b''.join(rawpack),mtime=0));(P/'water-record-index.json').write_text(json.dumps({'source_binary_sha256':hashlib.sha256((P/'gshhs_f.b').read_bytes()).hexdigest(),'record_pack_sha256':hashlib.sha256((P/'selected-gshhg-water-records.bin.gz').read_bytes()).hexdigest(),'records':records},separators=(',',':')))
rs=[x for x in json.load(open(repo/'data/macro-foundation/envelopes-v3/envelope-index.json'))['groups'] if x['level']=='region'];rg=[from_wkb(gzip.decompress((repo/'data/macro-foundation/envelopes-v3'/x['path']).read_bytes())) for x in rs];rt=STRtree(rg)
def area(g):
 if g.is_empty:return 0
 if g.geom_type=='Polygon':return abs(geod.geometry_area_perimeter(orient_polygons(g))[0])/1e6
 if hasattr(g,'geoms'):return sum(area(x) for x in g.geoms)
 return 0
(P/'dry-land-candidates').mkdir(exist_ok=True);cache={};changed=0
for c in cs:
 i=c['gshhg_id']
 if i in cache:c.update(cache[i]);continue
 coastal=from_wkb(gzip.decompress((P/'candidate-components'/f'{i}.wkb.gz').read_bytes()));ch=children.get(i,[]);dry=coastal.difference(union_all([g for _,g in ch])) if ch else coastal;ak=area(dry)
 if ch:
  ovs=[]
  for j in rt.query(dry):
   ai=area(dry.intersection(rg[int(j)]))
   if ai>1e-9:ovs.append(dict(region_id=rs[int(j)]['id'],region=rs[int(j)]['name'],intersection_km2=ai,share=min(1,ai/ak) if ak else 0))
  ovs.sort(key=lambda x:x['intersection_km2'],reverse=True);(P/'dry-land-candidates'/f'{i}.wkb.gz').write_bytes(gzip.compress(to_wkb(dry),mtime=0));changed+=1
 else:ovs=c['all_region_overlaps']
 fields={'dry_land_area_km2':ak,'direct_level2_water_ids':[identity for identity,_ in ch],'dry_land_wkb_sha256':hashlib.sha256(to_wkb(dry)).hexdigest(),'dry_land_majority_region':ovs[0] if ovs else None,'dry_land_all_region_overlaps':ovs,'dry_land_scope':'GSHHG ocean-coast Level1 minus direct Level2 inlandwaters; Level3 freshwater islands evaluated separately, not included in this ocean-island inventory'};cache[i]=fields;c.update(fields)
obj['method']={'dry_land':'Subtract exact directGSHHG Level2children fromLevel1coastline components; do not treat enclosed waters asmissingland. Lakeislands(Level3)outsidecoastal-island inventory scope.','area':'WGS84 ellipsoidal Geod oriented rings, allpolygonparts sum; datelineunwrapped','normalization':'Audit-only longitudeunwrap andmake_valid forinvalidsourcepolygons, never publishedgeometrymutation','source_revision':'GSHHG2.3.7 2017-06-15; positional offsets againstcurrentOSMmaybesubstantial','water_polygons_retained':len(records),'coastal_components_with_water':changed}
(P/'components-dry-land.json').write_text(json.dumps(obj,separators=(',',':')));print(json.dumps(obj['method']));print('waterrecords',len(records),'parents',len(children),'changed',changed,'waterpackgz',(P/'selected-gshhg-water-records.bin.gz').stat().st_size)
