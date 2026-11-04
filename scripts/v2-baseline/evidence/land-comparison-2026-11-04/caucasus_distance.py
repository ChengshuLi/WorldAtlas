#!/usr/bin/env /usr/bin/python3
"""Sample Caucasus transition distance to candidate route; not historical causation."""
import argparse,csv,json,hashlib
from pathlib import Path
import numpy as np
from osgeo import ogr,osr
ap=argparse.ArgumentParser();ap.add_argument('--spans',required=True,type=Path);ap.add_argument('--source',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--sample-stride',type=int,default=20);v=ap.parse_args();SRC=v.source;SP=v.spans;OUT=v.output;step=360/131072
if OUT.exists() or v.sample_stride<1:raise ValueError('output exists or invalid sample stride')
features=json.loads(SRC.read_bytes())['features'];feature=next(f for f in features if f['properties']['cut_id']=='caucasus_blacksea_anapa_to_caspian');line=ogr.CreateGeometryFromJson(json.dumps(feature['geometry']))
a=osr.SpatialReference();a.ImportFromEPSG(4326);a.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);b=osr.SpatialReference();b.ImportFromEPSG(32638);b.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);transform=osr.CoordinateTransformation(a,b);line.Transform(transform)
dist=[];count=0
with SP.open() as f:
 for r in csv.DictReader(f,delimiter='\t'):
  if int(r['reference'])!=18 or int(r['candidate'])!=19 or int(r['mainland_seed'])==0:continue
  y,a0,b0=map(int,(r['row'],r['start'],r['end']));lat=90-(y+.5)*step
  if not 40.8<=lat<=44.91:continue
  for x in range(a0,b0):
   lon=-180+(x+.5)*step
   if not 37.31<=lon<=49.33:continue
   if count%v.sample_stride==0:
    p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(lon,lat);p.Transform(transform);dist.append(p.Distance(line)/1000)
   count+=1
r={'schema':'caucasus-candidate-cut-distance-sample-v1','status':'research-validation-only','candidate_transition':'reference Asia to candidate Europe on seeded mainland','bounds_degrees':{'west':37.31,'east':49.33,'south':40.8,'north':44.91},'sample':f'every {v.sample_stride}th qualifying grid cell in row-major order','qualifying_cells':count,'sample_cells':len(dist),'distance_km_percentiles':{str(q):float(np.percentile(dist,q)) for q in [0,25,50,75,90,95,99,100]},'within_1km':int(np.sum(np.array(dist)<=1)),'within_5km':int(np.sum(np.array(dist)<=5)),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'spans_sha256':hashlib.sha256(SP.read_bytes()).hexdigest(),'projection':'EPSG:32638 (local planar approximation across Caucasus)','limitation':'Distance to candidate cut characterizes spatial pattern only; historical V2 source cut is unrecovered. Region box is a diagnostic envelope, not an authoritative Caucasus boundary.'}
OUT.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
