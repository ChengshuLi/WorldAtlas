#!/usr/bin/env python3
"""Measure GSHHG L1 land-polygon intersections with all assigned locations."""
import gzip,hashlib,json,math,pathlib,struct,sys
from shapely.geometry import shape,Polygon
from shapely.ops import transform,unary_union
from pyproj import Transformer
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[2]
MEMBER_SHA='af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
if len(sys.argv)!=2: raise SystemExit('usage: screen-gshhg-overlaps.py /path/to/gshhs_f.b')
data=pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(data).hexdigest()!=MEMBER_SHA: raise SystemExit('GSHHG member SHA mismatch')
s=json.loads((HERE/'issue-scope.json').read_text()); ids=s['member_location_ids']
index=json.loads((ROOT/'data/world-index.json').read_text()); features={}
for part in index['parts']:
 for f in json.loads((ROOT/'data'/part).read_text())['features']:
  if f['id'] in ids: features[f['id']]=f
if set(features)!=set(ids): raise SystemExit('current scope mismatch')
tr=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
units={i:{'feature':f,'geom':transform(tr,shape(f['geometry'])),'bounds':shape(f['geometry']).bounds,'land':[]} for i,f in features.items()}
records=[]; pos=total=l1=0
while pos<len(data):
 rid,n,flag,west,east,south,north,area,area_full,container,ancestor=struct.unpack_from('>IIIiiiiIIii',data,pos)
 start=pos; pos+=44; end=pos+n*8
 if end>len(data):raise SystemExit('truncated GSHHG record')
 total+=1
 if flag&255==1:
  l1+=1
  west/=1e6;east/=1e6;south/=1e6;north/=1e6
  if west>=180:west-=360;east-=360
  maybe=[i for i,u in units.items() if west<=u['bounds'][2] and east>=u['bounds'][0] and south<=u['bounds'][3] and north>=u['bounds'][1]]
  if maybe:
   coords=[]
   for j in range(n):
    x,y=struct.unpack_from('>ii',data,pos+j*8);x/=1e6;y/=1e6
    if x>180:x-=360
    coords.append((x,y))
   try: g=Polygon(coords)
   except Exception: pos=end;continue
   if not g.is_valid:g=g.make_valid()
   touched=[]
   ge=transform(tr,g)
   for i in maybe:
    intr=units[i]['geom'].intersection(ge)
    a=intr.area
    if a>1:
     units[i]['land'].append(intr)
     touched.append({'id':i,'intersection_area_km2':a/1e6})
   if touched:
    records.append({'record_id':rid,'bbox':[west,south,east,north],'source_area_km2':ge.area/1e6,'source_centroid':[g.centroid.x,g.centroid.y],'matches':touched,'bytes':data[start:end]})
 pos=end
selected=b''.join(r['bytes'] for r in records); packed=gzip.compress(selected,mtime=0)
(HERE/'sources/gshhg-land-intersections.bin.gz').write_bytes(packed)
per={}
for i,u in units.items():
 land=unary_union(u['land']) if u['land'] else None
 per[i]={'name':u['feature']['properties']['name'],'gshhg_l1_intersecting_records':len(u['land']),'gshhg_l1_intersection_area_km2':land.area/1e6 if land else 0,'current_footprint_area_km2':u['geom'].area/1e6,'gshhg_land_fraction_of_current_footprint':land.area/u['geom'].area if land and u['geom'].area else 0,'interpretation':'coarse physical-land overlap screen only; GSHHG 2017 level-1 boundaries include no administrative or settlement evidence and do not resolve small/sub-grid islands'}
report={'source':{'title':'GSHHG full-resolution global shoreline database version 2.3.7','release_date':'2017-06-15','archive_url':'https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip','archive_sha256':'28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc','member':'gshhs_f.b','member_sha256':MEMBER_SHA,'license':'LGPLv3 or later; retained sources/gshhg-LGPL.txt'},'scope_count':len(ids),'source_records_scanned':total,'source_level1_records_scanned':l1,'retained':{'path':'sources/gshhg-land-intersections.bin.gz','records':len(records),'raw_bytes':len(selected),'raw_sha256':hashlib.sha256(selected).hexdigest(),'gzip_bytes':len(packed),'gzip_sha256':hashlib.sha256(packed).hexdigest()},'method':'All 179,832 GSHHG level-1 polygons were scanned. Candidate bbox intersections were constructed from complete source ring coordinate records, repaired only in transient memory when invalid, projected to equal-area EPSG:6933 and intersected against every bbox-compatible current location. The per-location land fraction is the unary union of GSHHG L1 intersection pieces divided by the assigned geometry area. Inland lake boundaries (GSHHG level 2), sub-threshold rocks, coast-date differences, admin source differences, attribution and settlement completeness are not certified.','summary':{'locations_intersecting_gshhg_l1':sum(x['gshhg_l1_intersecting_records']>0 for x in per.values()),'locations_no_gshhg_l1_overlap':[i for i,x in per.items() if not x['gshhg_l1_intersecting_records']],'minimum_positive_land_fraction':min((x['gshhg_land_fraction_of_current_footprint'] for x in per.values() if x['gshhg_l1_intersecting_records']),default=None),'locations_land_fraction_lt_50pct':[{'id':i,'name':x['name'],'fraction':x['gshhg_land_fraction_of_current_footprint']} for i,x in per.items() if x['gshhg_land_fraction_of_current_footprint']<0.5]},'per_location':per,'retained_candidate_records':[{'record_id':r['record_id'],'bbox':r['bbox'],'source_area_km2':r['source_area_km2'],'matches':r['matches']} for r in records]}
(HERE/'gshhg-overlap-screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
