#!/usr/bin/env python3
"""Partial V2 research candidate: 12 nm nearest physical-grid shore per tile.

Reads physical and newly built land only. Open water outside the band is not
assigned; historical V2 labels are never read. Distances and tie rules are
explicit approximations, not a claim of recovered historical implementation.
"""
import argparse,hashlib,json,math,shutil,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import coastal_core as core
import build_coastal_tile as grid_io
import exclusive_outputs as output_io
from build_coastal_tile import open_grid
from exclusive_outputs import create_directory_exclusive,create_gzip_text_exclusive,write_json_exclusive

BAND_METRES=12*1852
TIE_TOLERANCE_METRES=0.00001
PAIRS=[(i,i+16,i) for i in range(1,7)]

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def pin(spec):
 if not isinstance(spec,dict) or set(spec)!={'path','sha256'} or not isinstance(spec['path'],str) or not isinstance(spec['sha256'],str) or len(spec['sha256'])!=64 or any(x not in '0123456789abcdef' for x in spec['sha256']):raise ValueError('invalid input pin')
 p=Path(spec['path']).resolve()
 if sha(p)!=spec['sha256']:raise ValueError('input hash mismatch: '+str(p))
 return p

def build(config_path,output,*,_verified_inputs=None):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();cfg=json.loads(raw)
 required={'schema','grid','physical_rows','physical_runs','land_rows','land_runs','land_report','core','pad_degrees'}
 if not required<=set(cfg)<=required|{'max_shore_segments','chunk','minimum_free_bytes'} or cfg['schema']!='simple-v2-coastal-band-v1':raise ValueError('invalid config')
 g=cfg['grid'];w,h,west,north,step=(g[k] for k in ('width','height','west','north','step'))
 if (set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or west!=-180 or north!=90 or type(step) not in (int,float) or not math.isfinite(step) or step!=360/w or north-h*step < -90-1e-8):raise ValueError('invalid global grid')
 box=cfg['core'];pad=cfg['pad_degrees'];chunk=cfg.get('chunk',5000);limit=cfg.get('max_shore_segments',1000000);reserve=cfg.get('minimum_free_bytes',2*(1<<30))
 if type(reserve) is not int or reserve<0:raise ValueError('invalid disk reserve')
 if not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box):raise ValueError('invalid core')
 x0,x1,y0,y1=box
 if not (0<=x0<x1<=w and 0<=y0<y1<=h) or type(chunk) is not int or not 1<=chunk<=50000 or type(limit) is not int or limit<1 or type(pad) not in (int,float) or not math.isfinite(pad) or pad<=0:raise ValueError('invalid tile/resource settings')
 names=('physical_rows','physical_runs','land_rows','land_runs','land_report')
 if _verified_inputs is None:pins={k:pin(cfg[k]) for k in names}
 else:
  if set(_verified_inputs)!=set(names) or any(cfg[k]!=_verified_inputs[k]['spec'] or Path(cfg[k]['path']).resolve()!=Path(_verified_inputs[k]['path']) for k in names):raise ValueError('batch input specifications differ')
  pins={k:Path(_verified_inputs[k]['path']) for k in names}
 land_report=json.loads(pins['land_report'].read_bytes())
 if (land_report.get('schema')!='simple-v2-land-report-v1' or land_report.get('status')!='research-not-published' or land_report.get('grid')!=g or any(land_report.get('inputs',{}).get(k)!=cfg[k] for k in ('physical_rows','physical_runs')) or land_report.get('output_rows_sha256')!=cfg['land_rows']['sha256'] or land_report.get('output_runs_sha256')!=cfg['land_runs']['sha256']):raise ValueError('land report does not bind physical and land inputs')
 out=Path(output).resolve();inputs=[config_path,*pins.values()]
 if out.exists() or any(p==out or p.is_relative_to(out) or out.is_relative_to(p.parent) for p in inputs):raise ValueError('output must be new and outside input directories')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 physical=open_grid(pins['physical_rows'],pins['physical_runs'],w,h);land=open_grid(pins['land_rows'],pins['land_runs'],w,h)
 code_paths={'coastal_band':Path(__file__).resolve(),'core':Path(core.__file__).resolve(),'shore':Path(core.shore.__file__).resolve(),'geometry':Path(core.shore.geom.__file__).resolve(),'grid_io':Path(grid_io.__file__).resolve(),'output_io':Path(output_io.__file__).resolve()};code_hashes={k:sha(v) for k,v in code_paths.items()}
 crop=core.shore.crop_bounds(box,w,h,step,pad)
 try:edges=core.shore.edges_for_crop(physical,land,crop,w,h,step,[x[1] for x in PAIRS],max_segments=limit)
 except ValueError as e:
  if str(e)!='no participant shorelines in crop':raise
  edges={'mids':np.empty((0,3))}
 indices=core.index_present(edges,PAIRS);create_directory_exclusive(out);span_path=out/'coastal-spans.jsonl.gz';cells=spans=water=bounded=exact=0
 with create_gzip_text_exclusive(span_path,encoding='utf8') as f:
  for y in range(y0,y1):
   if (y-y0)%128==0 and shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
   p=core.shore.crop(*physical,y,x0,x1,w);l=core.shore.crop(*land,y,x0,x1,w)
   if np.any(~np.isin(p,[1,17])) or np.any((p==17)&~np.isin(l,range(17,23))) or np.any((p==1)&(l!=0)):raise ValueError('land/physical values mismatch')
   selected=np.flatnonzero(p==1);water+=len(selected);records=[]
   for i in range(0,len(selected),chunk):
    xs=selected[i:i+chunk]+x0;lat=np.full(len(xs),90-(y+.5)*step);lon=-180+(xs+.5)*step
    codes,stats=core.classify(lat,lon,crop,w,h,step,PAIRS,TIE_TOLERANCE_METRES,BAND_METRES,0,indices);bounded+=stats['bounded'];exact+=stats['exact']
    keep=codes!=0;xx=xs[keep];cc=codes[keep];cells+=int(keep.sum())
    if len(xx):
     cuts=np.r_[0,np.flatnonzero((np.diff(xx)>1)|(cc[1:]!=cc[:-1]))+1,len(xx)]
     for a,b in zip(cuts[:-1],cuts[1:]):
      start,end,code=int(xx[a]),int(xx[b-1])+1,int(cc[a])
      if records and records[-1]['end']==start and records[-1]['code']==code:records[-1]['end']=end
      else:records.append({'start':start,'end':end,'code':code})
   if records:spans+=len(records);f.write(json.dumps({'row':y,'spans':records},separators=(',',':'))+'\n')
 if _verified_inputs is None:
  for k in names:pin(cfg[k])
 if config_path.read_bytes()!=raw or any(sha(v)!=code_hashes[k] for k,v in code_paths.items()):raise ValueError('input or code changed during build')
 report={'schema':'simple-v2-coastal-tile-report-v1','status':'research-partial-not-published','config_sha256':hashlib.sha256(raw).hexdigest(),'grid':g,'core':box,'inputs':{k:cfg[k] for k in names},'span_file':{'path':span_path.name,'sha256':sha(span_path)},'physical_water_cells':water,'assigned_cells':cells,'unassigned_water_cells':water-cells,'span_count':spans,'bounded_cells':bounded,'exact_cells':exact,'code_sha256':code_hashes,'method':'12 nautical miles inclusive; spherical distance to physical-grid land/water edge; lowest continent code wins ties within 0.00001 metres','limitations':'Partial candidate: open water beyond 12 nm is unassigned. Historical coastline, distance and tie conventions are unverified. No V2 labels or named-water exceptions used.'}
 write_json_exclusive(out/'report.json',report,indent=2);return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(build(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
