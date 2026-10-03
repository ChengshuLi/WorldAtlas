#!/usr/bin/env python3
"""Check TAAF-referenced Prince Edward/M/Marion land against current world membership.

This is a macro-routing lead only. It neither assigns islands nor changes envelopes.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import shapefile
from shapely.geometry import shape,box
from shapely.ops import transform
from shapely.wkb import loads
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
ENV=ROOT/'data/macro-foundation/envelopes-v5';WINDOW=box(36.5,-47.5,38.7,-46.0)
ids={'757':'Marion Island candidate','2328':'Prince Edward Island candidate'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--shapefile',required=True,type=Path);ap.add_argument('--check',action='store_true');a=ap.parse_args()
reader=shapefile.Reader(str(a.shapefile));source={}
for sr in reader.iterShapeRecords():
 d=dict(zip([x[0]for x in reader.fields[1:]],sr.record));i=str(d['id'])
 if i in ids:source[i]={'id':i,'official_crosswalk_name_lead':ids[i],'source_code':d['source'],'area_attribute_km2':float(d['area']),'bbox_wgs84':list(shape(sr.shape.__geo_interface__).bounds),'geometry':shape(sr.shape.__geo_interface__)}
if set(source)!=set(ids):raise SystemExit('expected independent land candidates were not found')
features=[]
for p in sorted((ROOT/'data/geography').glob('part-*.json')):
 for f in json.loads(p.read_text())['features']:
  g=f.get('geometry')
  if g and shape(g).intersects(WINDOW):features.append({'id':f.get('id'),'name':f.get('properties',{}).get('name')})
with gzip.open(ROOT/'data/macro-foundation/regional-handoffs.json.gz','rt') as f:h=json.load(f)
project=Transformer.from_crs(4326,6933,always_xy=True).transform;regions=[]
for r in h['regions']:
 p=ENV/r['envelope']['path'];g=loads(gzip.decompress(p.read_bytes()))
 regions.append((r,p,transform(project,g)))
nearest={}
for key,item in source.items():
 gm=transform(project,item.pop('geometry'));rows=[]
 for r,p,g in regions:rows.append({'region_id':r['region_id'],'name':r['name'],'distance_km_epsg6933':g.distance(gm)/1000,'envelope_path':r['envelope']['path'],'envelope_geometry_sha256':r['envelope']['geometry_sha256']})
 nearest[key]=sorted(rows,key=lambda x:x['distance_km_epsg6933'])[:5]
result={'method':'Window-scan every current geography part for polygon overlap with GSHHG candidate bounds; read the 81 frozen v5 region envelope geometries and measure polygon-to-polygon distances after EPSG:6933 projection. This is an assignment-routing diagnostic, not legal/administrative classification. The island-name crosswalk remains a sourced hypothesis based on TAAF text and these coordinate matches.','baseline_commit':json.loads((OUT/'baseline-extract.json').read_text())['baseline_commit'],'window_wgs84':list(WINDOW.bounds),'gshhg_shapefile_sha256':digest(a.shapefile),'source_candidates':source,'current_atlas_features_intersecting_window':features,'current_region_member_ids':json.loads((OUT/'baseline-extract.json').read_text())['region_member_location_ids'],'nearest_region_envelopes':nearest,'coordination_needed':True,'no_region_assignment_or_envelope_change':True}
payload=json.dumps(result,indent=2)+'\n';out=OUT/'neighbor-routing-check.json'
if a.check:
 if not out.exists() or out.read_text()!=payload:raise SystemExit('neighbor routing screen differs')
else:out.write_text(payload)
print(json.dumps({'result':'passed' if a.check else 'written','current_features_in_window':len(features),'nearest':{k:[(x['name'],round(x['distance_km_epsg6933'],1))for x in v[:3]]for k,v in nearest.items()}},indent=2))
