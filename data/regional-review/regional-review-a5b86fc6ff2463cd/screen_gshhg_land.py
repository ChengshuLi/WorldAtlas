#!/usr/bin/env python3
"""Screen exact #134 locations against GSHHG 2.3.7 high-resolution L1 physical land.
Usage: python screen_gshhg_land.py /path/to/GSHHS_f_L1.shp
"""
import hashlib,json,sys
from pathlib import Path
import shapefile
from pyproj import Transformer
from shapely.geometry import box,shape
from shapely.ops import transform,unary_union
OUT=Path(__file__).resolve().parent
base=json.loads((OUT/'baseline-extract.json').read_text())
ids=base['scope_location_ids']; feats={k:shape(base['locations'][k]['geometry']) for k in ids}
project=lambda g:transform(Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform,g)
feats_m={k:project(g) for k,g in feats.items()}
# Includes assigned groups and immediately neighboring Fiji, Kiribati/Line and Cook islands.
windows=[{'id':'western','bbox':[165.0,-24.0,180.0,-4.0]},{'id':'central-eastern','bbox':[-180.0,-24.0,-152.0,-4.0]}]
def window_ids(bb):return [w['id'] for w in windows if bb[0]<=w['bbox'][2] and bb[2]>=w['bbox'][0] and bb[1]<=w['bbox'][3] and bb[3]>=w['bbox'][1]]
def rn(x):return round(float(x),8)
r=shapefile.Reader(sys.argv[1]); rows=[];geoms=[]
for ix,sr in enumerate(r.iterShapeRecords()):
 p=sr.record.as_dict()
 if p.get('level')!=1:continue
 bb=list(sr.shape.bbox); wins=window_ids(bb)
 if not wins:continue
 g=shape(sr.shape.__geo_interface__)
 wids=[w['id'] for w in windows if w['id'] in wins and g.intersects(box(*w['bbox']))]
 if not wids:continue
 gm=project(g); overlap={}
 for k,loc in feats_m.items():
  a=gm.intersection(loc).area
  if a>100:overlap[k]=rn(a/1e6)
 dist={k:rn(gm.distance(loc)/1000) for k,loc in feats_m.items()}
 rows.append({'feature_index':ix,'gshhg_id':p.get('id'),'source':p.get('source'),'parent_id':p.get('parent_id'),'sibling_id':p.get('sibling_id'),'source_area_km2':p.get('area'),'equal_area_geometry_km2':rn(gm.area/1e6),'bbox':[rn(x) for x in bb],'windows':wids,'parts':len(g.geoms) if g.geom_type=='MultiPolygon' else 1,'vertices':len(sr.shape.points),'geometry_sha256_wkb':hashlib.sha256(g.wkb).hexdigest(),'overlap_km2_by_location':overlap,'distance_km_by_location':dist})
 geoms.append(g)
union_m=project(unary_union(geoms))
hits=[x for x in rows if x['overlap_km2_by_location']]
nearest={}
for k in ids:
 subset=[x for x in rows if k not in x['overlap_km2_by_location']]
 subset.sort(key=lambda x:(x['distance_km_by_location'][k],x['bbox']))
 nearest[k]=subset[:10]
metrics={}
for k,g in feats.items():
 gm=feats_m[k]; inter=gm.intersection(union_m)
 metrics[k]={'name':base['locations'][k]['properties']['name'],'current_equal_area_km2':rn(gm.area/1e6),'gshhg_intersection_km2':rn(inter.area/1e6),'current_area_fraction_intersecting_gshhg':rn(inter.area/gm.area),'bbox':[rn(x) for x in g.bounds],'parts':len(g.geoms) if g.geom_type=='MultiPolygon' else 1}
summary={'product':'GSHHG 2.3.7 high-resolution/full L1 physical coastline polygons','archive_url':'https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-shp-2.3.7.zip','windows':windows,'source_level1_records_scanned':len(r),'candidate_records_in_windows':len(rows),'positive_location_overlap_records':len(hits),'location_metrics':metrics,'all_gshhg_records_overlapping_locations':sorted(hits,key=lambda x:(x['windows'],x['bbox'])),'nearest_unmatched_land_candidates_per_location':nearest,'interpretation':['This is generalized physical coastline/land evidence, not an administrative or political boundary.','GSHHG release notes warn mixed source dates and possible misregistration against newer sources.','Candidate visibility and intersection cannot prove omitted land or dictate legal/political ownership; source-scale, atoll/lagoon and tiny-islet limitations apply.','The land screen excludes Antarctica.']}
p=OUT/'gshhg-land-screen.json';p.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'candidate_records':len(rows),'overlap_records':len(hits),'metrics':metrics,'output_bytes':p.stat().st_size},indent=2,ensure_ascii=False))
