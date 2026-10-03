#!/usr/bin/env python3
"""Extract the four exact Natural Earth ADM1 source rows by pinned ID.

Input shapefile must be restored from the pinned public-domain source in the
README. Only this script and resulting audit JSON are written in the owned path.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import shapefile
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
IDS=['ATF-5916','ATF-5917','ATF-5918','HMD+00?'];LOC={f'atlas:coverage:{i}':i for i in IDS}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def current_features():
 out={}
 for p in sorted((ROOT/'data/geography').glob('part-*.json')):
  for f in json.loads(p.read_text())['features']:
   if f.get('id') in LOC:out[LOC[f['id']]]=f
 return out
ap=argparse.ArgumentParser();ap.add_argument('--shapefile',required=True,type=Path);ap.add_argument('--check',action='store_true');a=ap.parse_args()
if not a.shapefile.exists():raise SystemExit('shapefile not found')
cur=current_features()
if set(cur)!=set(IDS):raise SystemExit('baseline location inventory changed')
reader=shapefile.Reader(str(a.shapefile));records=[]; fields=('featurecla','scalerank','adm1_code','iso_3166_2','iso_a2','sov_a3','adm0_a3','admin','geonunit','gu_a3','name','name_en','name_fr','gn_id','gn_name','gn_level','gn_a1_code','latitude','longitude','ne_id','wikidataid')
to_area=Transformer.from_crs(4326,6933,always_xy=True).transform
for sr in reader.iterShapeRecords():
 d=dict(zip([x[0] for x in reader.fields[1:]],sr.record));i=d.get('adm1_code')
 if i not in IDS:continue
 source_geom=sr.shape.__geo_interface__;atlas=cur[i]
 sg=shape(source_geom);ag=shape(atlas['geometry']);sm=transform(to_area,sg);am=transform(to_area,ag)
 records.append({'source_id':i,'atlas_location_id':atlas['id'],'attributes':{k:d.get(k) for k in fields},'source_geometry_type':sg.geom_type,'source_ring_count':len(sr.shape.parts),'source_vertices':len(sr.shape.points),'source_bounds_wgs84':list(sg.bounds),'source_geometry_sha256':hashlib.sha256(json.dumps(source_geom,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'atlas_geometry_type':ag.geom_type,'atlas_component_count':len(ag.geoms) if hasattr(ag,'geoms') else 1,'atlas_vertices_including_closure':sum(len(x.exterior.coords)for x in ag.geoms) if hasattr(ag,'geoms') else len(ag.exterior.coords),'atlas_bounds_wgs84':list(ag.bounds),'source_area_epsg6933_km2':sm.area/1e6,'atlas_area_epsg6933_km2':am.area/1e6,'source_atlas_symmetric_difference_epsg6933_km2':sm.symmetric_difference(am).area/1e6,'source_atlas_hausdorff_distance_m_epsg6933':sm.hausdorff_distance(am)})
if {x['source_id'] for x in records}!=set(IDS):raise SystemExit('pinned Natural Earth rows missing')
source_files={}
for ext in ('shp','dbf','shx','prj','cpg','VERSION.txt'):
 p=a.shapefile.with_suffix('.'+ext)
 if p.exists():source_files[ext]={'bytes':p.stat().st_size,'sha256':digest(p)}
result={'dataset':'Natural Earth 10m cultural vectors: ne_10m_admin_1_states_provinces','source_repository_commit':'ca96624a56bd078437bca8184e78163e5039ad19','source_commit_date':'2022-06-02','dataset_version':'5.1.1','license':'Public domain under Natural Earth terms of use','source_files':source_files,'records':sorted(records,key=lambda x:x['source_id'])}
payload=json.dumps(result,indent=2,ensure_ascii=False)+'\n';out=OUT/'natural-earth-source.json'
if a.check:
 if not out.exists() or out.read_text()!=payload:raise SystemExit('source extract differs')
else:out.write_text(payload)
print(json.dumps({'result':'passed' if a.check else 'written','rows':len(records),'source_files':source_files},indent=2))
