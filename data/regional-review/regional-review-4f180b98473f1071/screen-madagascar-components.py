#!/usr/bin/env python3
"""Screen COD-AB 2018-valid ADM2 components not represented in current Madagascar union."""
import gzip,hashlib,json,pathlib,struct,sys
from shapely.geometry import shape,Polygon
from shapely import make_valid
from shapely.ops import transform,unary_union,nearest_points
from shapely.strtree import STRtree
from pyproj import Transformer
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCH='28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc'; MEMBER='af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
if len(sys.argv)!=2:raise SystemExit('usage: screen-madagascar-components.py /path/to/gshhs_f.b')
data=pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(data).hexdigest()!=MEMBER:raise SystemExit('GSHHG member hash mismatch')
tr=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
inv=Transformer.from_crs('EPSG:6933','EPSG:4326',always_xy=True).transform
features={}
for part in json.loads((ROOT/'data/world-index.json').read_text())['parts']:
 for f in json.loads((ROOT/'data'/part).read_text())['features']:
  if f['id'] in json.loads((HERE/'issue-scope.json').read_text())['member_location_ids'] and f['id'].startswith('gb:MDG:ADM2:'):features[f['id']]=f
current=unary_union([transform(tr,shape(f['geometry'])) for f in features.values()])
source=json.loads(gzip.decompress((HERE/'sources/mdg-COD-AB-ADM2-2026-reviewed.geojson.gz').read_bytes()))['features']
candidates=[]
for f in source:
 geom=transform(tr,shape(f['geometry']));pieces=list(geom.geoms) if hasattr(geom,'geoms') else [geom]
 for ix,g in enumerate(pieces):
  if g.area < 10000:continue
  covered=g.intersection(current).area/g.area if g.area else 1
  if covered<.01:
   a,b=nearest_points(g,current); lon,lat=inv(a.x,a.y); c_lon,c_lat=inv(b.x,b.y)
   candidates.append({'source_name':f['properties']['adm2_name'],'source_pcode':f['properties']['adm2_pcode'],'source_parent':f['properties']['adm1_name'],'component_index':ix,'source_component_area_km2':g.area/1e6,'overlap_with_current_MDG_union_percent':100*covered,'nearest_current_union_distance_m':g.distance(current),'component_centroid_lonlat':list(inv(g.centroid.x,g.centroid.y)),'nearest_point_on_component_lonlat':[lon,lat],'nearest_point_on_current_union_lonlat':[c_lon,c_lat],'geometry':g})
if not candidates:raise SystemExit('no unmatched component candidates found')
# Scan all GSHHG L1 records against candidate components; preserve the exact records that intersect.
tree=STRtree([x['geometry'] for x in candidates]); land=[[] for x in candidates];records=[];pos=total=l1=0;cb=(min(x['geometry'].bounds[0] for x in candidates),min(x['geometry'].bounds[1] for x in candidates),max(x['geometry'].bounds[2] for x in candidates),max(x['geometry'].bounds[3] for x in candidates))
while pos<len(data):
 rid,n,flag,west,east,south,north,area,area_full,container,ancestor=struct.unpack_from('>IIIiiiiIIii',data,pos);start=pos;pos+=44;end=pos+n*8
 if end>len(data):raise SystemExit('truncated GSHHG record')
 total+=1
 if flag&255==1:
  l1+=1; west/=1e6;east/=1e6;south/=1e6;north/=1e6
  if west>=180:west-=360;east-=360
  if west>cb[2] or east<cb[0] or south>cb[3] or north<cb[1]:pos=end;continue
  coords=[]
  for j in range(n):
   xx,yy=struct.unpack_from('>ii',data,pos+j*8);xx/=1e6;yy/=1e6
   if xx>180:xx-=360
   coords.append((xx,yy))
  try:g=Polygon(coords)
  except Exception:pos=end;continue
  if not g.is_valid:g=make_valid(g)
  ge=transform(tr,g); hits=[]
  for jx in tree.query(ge):
   j=int(jx); intr=ge.intersection(candidates[j]['geometry']).area
   if intr>1:
    land[j].append(intr);hits.append({'candidate_index':j,'intersection_area_km2':intr/1e6})
  if hits:records.append({'record_id':rid,'matches':hits,'bytes':data[start:end]})
 pos=end
for i,x in enumerate(candidates):
 x.pop('geometry'); x['gshhg_L1_intersecting_record_count']=sum(1 for r in records if any(h['candidate_index']==i for h in r['matches']))
 x['gshhg_L1_intersection_area_km2']=unary_union([]).area if not land[i] else sum(land[i])/1e6
 x['interpretation']='GSHHG L1 is coarse physical screening; component non-detection is not absence proof. Administrative island component must be reconciled to appropriate current source.'
raw=b''.join(r['bytes'] for r in records);packed=gzip.compress(raw,mtime=0)
(HERE/'sources/gshhg-madagascar-component-candidates.bin.gz').write_bytes(packed)
report={'source_COD_AB':'sources/mdg-COD-AB-ADM2-2026-reviewed.geojson.gz','source_unit_count':len(source),'current_assigned_MDG_feature_count':len(features),'method':{'projection':'EPSG:6933 equal-area','candidate_rule':'For each OCHA COD-AB ADM2 polygon component over 0.01 km2, retain component when less than 1% of its area intersects the union of all current 119 scoped Madagascar ADM2 polygons.','physical_screen':'Scan every source GSHHG 2.3.7 L1 record against all candidate parts. Screen outcomes do not establish legal ownership, source accuracy or physical land absence.','validity':'Invalid geometries are repaired only on ephemeral comparison copies.'},'gshhg_source':{'archive_sha256':ARCH,'member_sha256':MEMBER,'records_scanned':total,'L1_records_scanned':l1,'retained_matches':len(records),'retained_raw_sha256':hashlib.sha256(raw).hexdigest(),'retained_gzip_sha256':hashlib.sha256(packed).hexdigest(),'retained_gzip_bytes':len(packed)},'candidate_count':len(candidates),'candidate_total_source_area_km2':sum(x['source_component_area_km2'] for x in candidates),'candidates_with_L1_intersection':sum(x['gshhg_L1_intersecting_record_count']>0 for x in candidates),'candidates':candidates}
(HERE/'madagascar-disconnected-component-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='candidates'},ensure_ascii=False,indent=2))
print('Largest candidate records:')
for x in sorted(candidates,key=lambda z:z['source_component_area_km2'],reverse=True)[:20]:print(x['source_name'],x['source_pcode'],'part',x['component_index'],'km2',round(x['source_component_area_km2'],4),'GSHHG-L1 records',x['gshhg_L1_intersecting_record_count'],'land km2',round(x['gshhg_L1_intersection_area_km2'],5))
