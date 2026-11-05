#!/usr/bin/env python3
"""Assemble explicit pinned line, water-route and connector segments into research regions."""
import argparse,hashlib,json,math,re,shutil,sys
from functools import lru_cache
from pathlib import Path
import numpy as np
from osgeo import ogr
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import file_integrity as band
import build_coastal_tile as grid_io
import shared_nearest as shore
import exclusive_outputs as xo
ogr.UseExceptions()

def build(config_path,output):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();cfg=json.loads(raw);required={'schema','grid','regions','evidence'}
 if not required<=set(cfg)<=required|{'join_tolerance_degrees','max_route_cells','minimum_free_bytes'} or cfg['schema']!='simple-v2-regions-v1':raise ValueError('invalid region config')
 g=cfg['grid'];w,h=g['width'],g['height'];step=g['step'];tol=cfg.get('join_tolerance_degrees',0);limit=cfg.get('max_route_cells',2000000);reserve=cfg.get('minimum_free_bytes',2*(1<<30))
 if (set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or g['north']!=90 or type(step) not in (int,float) or not math.isfinite(step) or step!=360/w or 90-h*step < -90-1e-8):raise ValueError('invalid grid')
 if type(tol) not in (int,float) or not math.isfinite(tol) or not 0<=tol<=1e-6 or type(limit) is not int or not 1<=limit<=10000000 or type(reserve) is not int or reserve<0:raise ValueError('invalid limits')
 if not isinstance(cfg['regions'],list) or not cfg['regions'] or not isinstance(cfg['evidence'],list):raise ValueError('invalid region/evidence list')
 pins=[];paths=[];route_physical=None
 def check(spec):
  p=band.pin(spec);pins.append(spec);paths.append(p);return p
 for spec in cfg['evidence']:check(spec)
 def coordinate(value):
  if not isinstance(value,list) or len(value)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value) or not -180<=value[0]<=180 or not -90<=value[1]<=90:raise ValueError('invalid longitude/latitude')
  return [float(value[0]),float(value[1])]
 def get_segment(segment):
  nonlocal route_physical
  if not isinstance(segment,dict):raise ValueError('invalid segment')
  kind=segment.get('kind')
  if kind=='points' and set(segment)=={'kind','coordinates'}:
   coords=segment['coordinates']
  elif kind=='feature' and set(segment)=={'kind','file','id_property','id_value','reverse'}:
   if type(segment['reverse']) is not bool or not isinstance(segment['id_property'],str) or not segment['id_property'] or not isinstance(segment['id_value'],str):raise ValueError('invalid feature selector')
   doc=json.loads(check(segment['file']).read_bytes());features=doc.get('features')
   if doc.get('type')!='FeatureCollection' or not isinstance(features,list) or ('crs' in doc and doc['crs'] not in (None,{'type':'name','properties':{'name':'urn:ogc:def:crs:OGC:1.3:CRS84'}})):raise ValueError('feature source must be WGS84 GeoJSON')
   matches=[f for f in features if isinstance(f,dict) and f.get('type')=='Feature' and isinstance(f.get('properties'),dict) and segment['id_property'] in f['properties'] and str(f['properties'][segment['id_property']])==segment['id_value']]
   if len(matches)!=1 or matches[0].get('geometry',{}).get('type')!='LineString':raise ValueError('feature line must be unique')
   coords=matches[0]['geometry']['coordinates'];coords=list(reversed(coords)) if segment['reverse'] else coords
  elif kind=='water-route' and set(segment)=={'kind','report','reverse'}:
   if type(segment['reverse']) is not bool:raise ValueError('invalid route direction')
   rp=check(segment['report']);r=json.loads(rp.read_bytes());box=r.get('bounds')
   if r.get('schema')!='simple-v2-water-route-report-v1' or r.get('status')!='unreviewed-research-not-published' or r.get('grid')!=g or not isinstance(box,list) or len(box)!=4:raise ValueError('invalid route report')
   x0,x1,y0,y1=box
   if any(type(v) is not int for v in box) or not (0<=x0<x1<=w and 0<=y0<y1<=h):raise ValueError('invalid route bounds')
   q=r.get('route',{});route_path=(rp.parent/q.get('path','')).resolve()
   if not route_path.is_relative_to(rp.parent) or not route_path.is_file():raise ValueError('route path escapes report')
   check({'path':str(route_path),'sha256':q.get('sha256')});pr=check(r['physical_rows']);pu=check(r['physical_runs']);current_physical=(r['physical_rows']['sha256'],r['physical_runs']['sha256'])
   if route_physical is not None and route_physical!=current_physical:raise ValueError('routes use different physical grids')
   route_physical=current_physical;rows,runs=grid_io.open_grid(pr,pu,w,h)
   if route_path.stat().st_size%4 or not 0<route_path.stat().st_size//4<=limit:raise ValueError('invalid route size')
   ids=np.fromfile(route_path,dtype='<u4');width=x1-x0
   if np.any(ids>=width*(y1-y0)):raise ValueError('route index outside bounds')
   xs=(ids%width).astype(np.int64)+x0;ys=(ids//width).astype(np.int64)+y0
   if [int(xs[0]),int(ys[0])]!=r.get('start') or [int(xs[-1]),int(ys[-1])]!=r.get('end') or np.any(np.abs(np.diff(xs))+np.abs(np.diff(ys))!=1):raise ValueError('invalid route path')
   @lru_cache(maxsize=8)
   def physical_row(y):return shore.crop(rows,runs,y,x0,x1,w)
   for x,y in zip(xs,ys):
    if physical_row(int(y))[int(x)-x0]!=1:raise ValueError('route crosses land')
   coords=[[-180+(int(x)+.5)*step,90-(int(y)+.5)*step] for x,y in zip(xs,ys)];coords=list(reversed(coords)) if segment['reverse'] else coords
  else:raise ValueError('unsupported segment')
  if not isinstance(coords,list) or len(coords)<2:raise ValueError('segment needs at least two coordinates')
  coords=[coordinate(x) for x in coords]
  if any(abs(a[0]-b[0])>180 for a,b in zip(coords,coords[1:])):raise ValueError('unsplit antimeridian segment')
  return coords
 regions=[];ids=set()
 for region in cfg['regions']:
  if not isinstance(region,dict) or set(region)!={'id','segments','witnesses'} or not isinstance(region['id'],str) or not re.fullmatch('[A-Za-z0-9_-]+',region['id']) or region['id'] in ids or not isinstance(region['segments'],list) or not region['segments'] or not isinstance(region['witnesses'],list):raise ValueError('invalid region')
  ids.add(region['id']);chain=[]
  for segment in region['segments']:
   points=get_segment(segment)
   if chain:
    if max(abs(chain[-1][i]-points[0][i]) for i in (0,1))>tol:raise ValueError('segment endpoints do not join')
    chain.extend(points[1:])
   else:chain.extend(points)
  if len(chain)<4 or max(abs(chain[-1][i]-chain[0][i]) for i in (0,1))>tol:raise ValueError('region is not explicitly closed')
  chain[-1]=chain[0];geometry={'type':'Polygon','coordinates':[chain]};geom=ogr.CreateGeometryFromJson(json.dumps(geometry))
  if geom is None or geom.IsEmpty() or not geom.IsValid():raise ValueError('invalid region polygon')
  for witness in region['witnesses']:
   if not isinstance(witness,dict) or set(witness)!={'lon','lat','inside'} or type(witness['inside']) is not bool:raise ValueError('invalid witness')
   lon,lat=coordinate([witness['lon'],witness['lat']]);point=ogr.Geometry(ogr.wkbPoint);point.AddPoint_2D(lon,lat)
   if geom.Boundary().Distance(point)<1e-12 or bool(geom.Contains(point))!=witness['inside']:raise ValueError('witness fails')
  regions.append((region['id'],geometry))
 out=Path(output).resolve();code_paths={'builder':Path(__file__).resolve(),'band_io':Path(band.__file__).resolve(),'grid_io':Path(grid_io.__file__).resolve(),'shore':Path(shore.__file__).resolve(),'output_io':Path(xo.__file__).resolve()};code={k:band.sha(v) for k,v in code_paths.items()}
 if out.exists() or any(out==p or out in p.parents or p.parent in out.parents for p in [config_path,*paths,*code_paths.values()]):raise ValueError('output must be new and outside input directories')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 xo.create_directory_exclusive(out);outputs=[]
 for ident,geometry in regions:
  path=out/(ident+'.geojson');xo.write_json_exclusive(path,{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'region':ident},'geometry':geometry}]},indent=2);outputs.append({'id':ident,'path':path.name,'sha256':band.sha(path)})
 for spec in pins:band.pin(spec)
 if config_path.read_bytes()!=raw or any(band.sha(v)!=code[k] for k,v in code_paths.items()):raise ValueError('input or code changed')
 report={'schema':'simple-v2-regions-report-v1','status':'unreviewed-research-not-published','grid':g,'config_sha256':hashlib.sha256(raw).hexdigest(),'inputs':pins,'outputs':outputs,'code_sha256':code,'join_tolerance_degrees':tol,'route_physical_sha256':route_physical,'limitations':'Caller-selected segment order, connectors, route bounds, closures and witnesses are exploratory; file pins and water-path checks do not establish historical V2 policy or geography.'};xo.write_json_exclusive(out/'report.json',report,indent=2);return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(build(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
