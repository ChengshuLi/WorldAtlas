#!/usr/bin/env python3
"""Screen eight original/current footprints against every local GSHHG 2.3.7 L1 polygon.
Usage: python3 screen_gshhg.py /restored/path/gshhs_f.b
"""
import gzip,hashlib,json,math,pathlib,struct,sys
from shapely.geometry import Polygon,shape
from shapely.ops import transform
from pyproj import Transformer
HERE=pathlib.Path(__file__).resolve().parent
RAW_SHA='af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
ARCHIVE_SHA='28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc'
if len(sys.argv)!=2: raise SystemExit('usage: python3 screen_gshhg.py /path/to/gshhs_f.b')
data=pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(data).hexdigest()!=RAW_SHA: raise SystemExit('GSHHG source member SHA-256 mismatch')
scope=json.loads((HERE/'issue-scope.json').read_text()); prof=json.loads((HERE/'natural-earth-source-profiles.json').read_text())
ids=scope['member_location_ids']; raw={x['location_id']:shape(x['source_geometry']) for x in prof['records']}
# Read current geometry from baseline part named by independently pinned inventory.
features={}
for row in scope['locations']:
 f=json.loads((HERE.parents[2]/row['containing_file']).read_text())['features']
 features[row['id']]=next(x for x in f if x['id']==row['id'])
cur={i:shape(features[i]['geometry']) for i in ids}
project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
units={}
for i in ids:
 for vintage,geom in [('natural_earth',raw[i]),('current_baseline',cur[i])]:
  units[(i,vintage)]={'geom':transform(project,geom),'count':0,'intersections':[],'bbox':geom.bounds}
# Wide windows envelope all assigned geography with a 0.6 degree margin for unmatched island/coast leads.
windows={'American Samoa':(-173.5,-16.0,-167.0,-9.0),'Wallis-Futuna':(-180.0,-16.0,-174.0,-11.0)}
id_group={i:('Wallis-Futuna' if i.startswith('WLF-') else 'American Samoa') for i in ids}
def round8(v):return round(float(v),8)
pos=total=l1=0; nearby=[]; window_counts={k:0 for k in windows}; nearest={k:[] for k in units}
while pos<len(data):
 start=pos
 lid,n,flag,west,east,south,north,area,area_full,container,ancestor=struct.unpack_from('>IIIiiiiIIii',data,pos);pos+=44
 end=pos+n*8
 if end>len(data):raise SystemExit('truncated GSHHG record')
 total+=1;level=flag&255
 if level==1:
  l1+=1; w,s,e,no=[q/1e6 for q in (west,south,east,north)]
  if w>180:w-=360;e-=360
  center=((w+e)/2,(s+no)/2)
  group=next((g for g,b in windows.items() if w<=b[2] and e>=b[0] and s<=b[3] and no>=b[1]),None)
  if group:
   window_counts[group]+=1
   xy=[struct.unpack_from('>ii',data,pos+j*8) for j in range(n)]
   coords=[(x/1e6-(360 if x/1e6>180 else 0),y/1e6) for x,y in xy]
   pg=Polygon(coords)
   if not pg.is_empty and pg.is_valid:
    pm=transform(project,pg); near_record={'id':lid,'group':group,'level':level,'bbox':[round8(v) for v in (w,s,e,no)],'centroid':[round8(v) for v in center],
      'source_area_header':area,'area_full_header':area_full,'parent_id':container,'ancestor_id':ancestor,'vertices':n,'geometry_sha256_wkb':hashlib.sha256(pg.wkb).hexdigest(),'original_record':data[start:end]}
    row_hits=[]; distances=[]
    for (i,vintage),u in units.items():
     if id_group[i]!=group:continue
     g=u['geom']
     intersection=pm.intersection(g).area
     distance=pm.distance(g)
     if intersection>1:
      u['count']+=1;u['intersections'].append({'gshhg_id':lid,'area_km2':round8(intersection/1e6),'gshhg_polygon_area_km2':round8(pm.area/1e6),'fraction_gshhg_polygon':round8(intersection/pm.area) if pm.area else 0})
      row_hits.append({'unit':i,'vintage':vintage,'intersection_km2':round8(intersection/1e6),'fraction_gshhg_polygon':round8(intersection/pm.area) if pm.area else 0})
     else:distances.append({'unit':i,'vintage':vintage,'distance_km':round8(distance/1000)})
    near_record['hits']=row_hits;near_record['distances']=distances;nearby.append(near_record)
 pos=end
# Compress exact original records; deterministic timestamp.
rawbytes=b''.join(x['original_record'] for x in nearby);packed=gzip.compress(rawbytes,mtime=0)
(HERE/'sources/gshhg-local-records.bin.gz').write_bytes(packed)
report={'source':{'name':'GSHHG 2.3.7 full-resolution L1 physical coastline polygons','release_date':'2017-06-15','archive_url':'https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip','archive_sha256':ARCHIVE_SHA,'member_name':'gshhs_f.b','member_bytes':len(data),'member_sha256':hashlib.sha256(data).hexdigest(),'license_file':'sources/gshhg-LGPL.txt'},
 'method':{'scan':'Every L1 record in 5-degree regional windows for both assigned island groups; original selected record bytes preserved compressed.','axis_order':'longitude-latitude','crs':'EPSG:6933','intersection':'Equal-area overlay of source physical-land polygon with original Natural Earth and published baseline feature geometry; invalid GSHHG rings are omitted from overlay and recorded as a method limit.','distance':'Projected Euclidean boundary distance; screening only.'},
 'scope_count':len(ids),'source_total_records_scanned':total,'source_level1_records_scanned':l1,'regional_window_candidate_records':len(nearby),'regional_window_level1_counts':window_counts,
 'retained':{'path':'sources/gshhg-local-records.bin.gz','record_count':len(nearby),'uncompressed_bytes':len(rawbytes),'uncompressed_sha256':hashlib.sha256(rawbytes).hexdigest(),'compressed_bytes':len(packed),'compressed_sha256':hashlib.sha256(packed).hexdigest()},
 'location_metrics':{f'{i}:{v}':{'name':features[i]['properties']['name'],'positive_intersecting_record_count':u['count'],'total_intersection_area_km2':round8(sum(x['area_km2'] for x in u['intersections'])),'gshhg_record_intersections':u['intersections']} for (i,v),u in units.items()},
 'nearby_candidate_records':[{k:v for k,v in x.items() if k!='original_record'} for x in nearby],
 'limits':['GSHHG is physical shoreline evidence, not administrative boundary or ownership evidence.','GSHHG documents mixed-vintage source data and potential misregistration; zero intersection/non-detection does not prove land absent.','This screen preserves every L1 record in two broad nearby-island windows and computes geometry intersections; the windows include neighboring islands outside the assigned scope. It is not a complete inventory of reef, lagoon, intertidal, tiny or emerged land.','Antarctica is excluded and is outside this assigned scope.']}
(HERE/'gshhg-screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'source_rows_scanned':total,'level1':l1,'retained':len(nearby),'bytes':len(packed),'results':{k:v['positive_intersecting_record_count'] for k,v in report['location_metrics'].items()}},indent=2))
