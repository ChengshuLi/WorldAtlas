#!/usr/bin/env python3
"""Build an explicitly specified local water-cell path for exploratory closure."""
import argparse,hashlib,json,math,shutil,subprocess,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import build_coastal_tile as io
import shared_nearest as shore
import exclusive_outputs as xo
import file_integrity as band_io
from file_integrity import pin,sha

def build(config_path,output):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();c=json.loads(raw);required={'schema','grid','physical_rows','physical_runs','bounds','start','end'}
 if not required<=set(c)<=required|{'max_window_cells','minimum_free_bytes'} or c['schema']!='simple-v2-water-route-v2' or sys.byteorder!='little':raise ValueError('invalid config or byte order')
 g=c['grid'];w,h=g['width'],g['height'];step=g['step'];box=c['bounds'];start,end=c['start'],c['end'];limit=c.get('max_window_cells',30000000);reserve=c.get('minimum_free_bytes',2*(1<<30))
 if set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or g['north']!=90 or type(step) not in (int,float) or not math.isfinite(step) or step!=360/w or 90-h*step < -90-1e-8:raise ValueError('invalid grid')
 if not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box):raise ValueError('invalid bounds')
 x0,x1,y0,y1=box
 if not (0<=x0<x1<=w and 0<=y0<y1<=h) or type(limit) is not int or not 1<=limit<=100000000 or (x1-x0)*(y1-y0)>min(limit,2**31-1) or type(reserve) is not int or reserve<0:raise ValueError('invalid bounds or resource limit')
 for point in (start,end):
  if not isinstance(point,list) or len(point)!=2 or any(type(v) is not int for v in point) or not (x0<=point[0]<x1 and y0<=point[1]<y1):raise ValueError('endpoint outside bounds')
 pins={k:pin(c[k]) for k in ('physical_rows','physical_runs')};out=Path(output).resolve();inputs=[config_path,*pins.values()];code_paths={'builder':Path(__file__).resolve(),'kernel':HERE/'water_route.cpp','grid_io':Path(io.__file__).resolve(),'shore':Path(shore.__file__).resolve(),'output_io':Path(xo.__file__).resolve(),'pin_io':Path(band_io.__file__).resolve()};hashes={k:sha(v) for k,v in code_paths.items()}
 if out.exists() or any(out==p or out in p.parents or p.parent in out.parents for p in [*inputs,*code_paths.values()]):raise ValueError('output must be new and outside input directories')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 rows,runs=io.open_grid(pins['physical_rows'],pins['physical_runs'],w,h);xo.create_directory_exclusive(out);mask=out/'water-mask.u8'
 with mask.open('xb') as f:
  for y in range(y0,y1):
   if (y-y0)%128==0 and shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
   row=shore.crop(rows,runs,y,x0,x1,w)
   if np.any(~np.isin(row,[1,17])):raise ValueError('invalid physical code')
   (row==17).astype(np.uint8).tofile(f)
 if shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
 # Each move is costed by the WGS84 inverse distance between adjacent cell
 # centers. Integer micrometres make equal-cost path ties deterministic.
 east_costs=np.empty(y1-y0,dtype='<u8');north_costs=np.empty(max(0,y1-y0-1),dtype='<u8')
 def edge_cost(lon1,lat1,lon2,lat2):
  value=float(shore.GEOD.inv(lon1,lat1,lon2,lat2)[2])
  if not math.isfinite(value) or value<0:raise ValueError('invalid WGS84 grid-edge distance')
  return max(1,int(round(value*1_000_000)))
 for local_y,y in enumerate(range(y0,y1)):
  lat=g['north']-(y+.5)*step;lon=g['west']+(x0+.5)*step
  east_costs[local_y]=edge_cost(lon,lat,lon+step,lat) if x1-x0>1 else 1
  if local_y<len(north_costs):
   next_lat=g['north']+(y+1.5)*-step
   north_costs[local_y]=edge_cost(lon,lat,lon,next_lat)
 east_cost_path=out/'east-costs.u64le';north_cost_path=out/'north-costs.u64le'
 with east_cost_path.open('xb') as f:east_costs.tofile(f)
 with north_cost_path.open('xb') as f:north_costs.tofile(f)
 executable=out/'water-route';build_cmd=['g++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(HERE/'water_route.cpp'),'-o',str(executable)];subprocess.run(build_cmd,check=True,capture_output=True)
 args=[str(executable),str(mask),str(x1-x0),str(y1-y0),str(start[0]-x0),str(start[1]-y0),str(end[0]-x0),str(end[1]-y0),str(east_cost_path),str(north_cost_path),str(out/'route.u32le')];proc=subprocess.run(args,capture_output=True,text=True)
 if proc.returncode:raise ValueError('water path failed: '+proc.stderr.strip())
 if shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
 for k in pins:pin(c[k])
 if config_path.read_bytes()!=raw or any(sha(v)!=hashes[k] for k,v in code_paths.items()):raise ValueError('input or code changed')
 try:distance_um=int(proc.stdout.strip())
 except ValueError:raise ValueError('water route did not report a valid WGS84 path length') from None
 if distance_um<0:raise ValueError('water route reported a negative WGS84 path length')
 result={'schema':'simple-v2-water-route-report-v2','status':'unreviewed-research-not-published','grid':g,'bounds':box,'start':start,'end':end,'physical_rows':c['physical_rows'],'physical_runs':c['physical_runs'],'config_sha256':hashlib.sha256(raw).hexdigest(),'route':{'path':'route.u32le','sha256':sha(out/'route.u32le'),'distance_m':distance_um/1_000_000,'metric':'WGS84 ellipsoidal cell-center edge distances; integer-micrometre weighted Dijkstra'},'mask_sha256':sha(mask),'edge_costs':{'east':{'path':east_cost_path.name,'sha256':sha(east_cost_path)},'north':{'path':north_cost_path.name,'sha256':sha(north_cost_path)}},'code_sha256':hashes,'binary_sha256':sha(executable),'compiler_version':subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],'geodesic_software_versions':{'pyproj':__import__('pyproj').__version__,'proj':__import__('pyproj').proj_version_str},'builder_output':proc.stderr.strip(),'limitations':'Exploratory WGS84-weighted four-neighbor route within explicitly selected bounds; cell-center edges, endpoints and closure policy are not verified historical decisions.'};xo.write_json_exclusive(out/'report.json',result,indent=2);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(build(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
