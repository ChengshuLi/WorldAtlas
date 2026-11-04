#!/usr/bin/env python3
"""Resumable, single-worker V2-style coastal band. Never reads V2 labels."""
import argparse,fcntl,hashlib,json,math,os,shutil,sys
from pathlib import Path
import coastal_band_adaptive as band
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import assemble_coastal_tiles as assembly
import exclusive_outputs as xo

NAMES=('physical_rows','physical_runs','land_rows','land_runs','land_report')
def build(config_path,output,max_tiles=None):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();c=json.loads(raw)
 required={'schema','grid',*NAMES,'tile_width','tile_height','pad_degrees'}
 if not required<=set(c)<=required|{'chunk','max_shore_segments','minimum_free_bytes'} or c['schema']!='simple-v2-coastal-resumable-v1':raise ValueError('invalid config')
 g=c['grid'];w,h=g['width'],g['height'];step=g['step'];tw,th=c['tile_width'],c['tile_height'];pad=c['pad_degrees'];chunk=c.get('chunk',5000);limit=c.get('max_shore_segments',1000000);reserve=c.get('minimum_free_bytes',2*(1<<30))
 if (set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or g['north']!=90 or type(step) not in (int,float) or not math.isfinite(step) or step!=360/w or 90-h*step < -90-1e-8):raise ValueError('invalid grid')
 if (any(type(x) is not int for x in (tw,th,chunk,limit,reserve)) or not 1<=tw<=w or not 1<=th<=h or not 1<=chunk<=50000 or limit<1 or reserve<0 or type(pad) not in (int,float) or not math.isfinite(pad) or pad<=0 or (max_tiles is not None and (type(max_tiles) is not int or max_tiles<1))):raise ValueError('invalid resource settings')
 verified={k:{'spec':c[k],'path':str(band.pin(c[k]))} for k in NAMES}
 land=json.loads(Path(verified['land_report']['path']).read_bytes())
 if (land.get('schema')!='simple-v2-land-report-v1' or land.get('status')!='research-not-published' or land.get('grid')!=g or any(land.get('inputs',{}).get(k)!=c[k] for k in ('physical_rows','physical_runs')) or land.get('output_rows_sha256')!=c['land_rows']['sha256'] or land.get('output_runs_sha256')!=c['land_runs']['sha256']):raise ValueError('land report does not bind inputs')
 paths={'runner':Path(__file__).resolve(),'coastal_band':Path(band.__file__).resolve(),'core':Path(band.core.__file__).resolve(),'shore':Path(band.core.shore.__file__).resolve(),'geometry':Path(band.core.shore.geom.__file__).resolve(),'grid_io':Path(band.grid_io.__file__).resolve(),'output_io':Path(xo.__file__).resolve(),'coverage_io':Path(assembly.__file__).resolve()};code={k:band.sha(v) for k,v in paths.items()}
 out=Path(output).resolve();inputs=[config_path,*[Path(v['path']) for v in verified.values()],*paths.values()]
 if any(p==out or p.is_relative_to(out) or out.is_relative_to(p.parent) for p in inputs):raise ValueError('output must be outside input directories')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 out.mkdir(mode=0o700,exist_ok=True);lock=out/'run.lock'
 with lock.open('a') as lf:
  try:fcntl.flock(lf,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('another runner holds the output lock') from None
  identity={'schema':'simple-v2-coastal-resumable-identity-v1','config_sha256':hashlib.sha256(raw).hexdigest(),'code_sha256':code}
  identity_path=out/'identity.json'
  if identity_path.exists():
   if json.loads(identity_path.read_bytes())!=identity:raise ValueError('resume identity differs')
  else:
   if any(x.name not in {'run.lock'} for x in out.iterdir()):raise ValueError('unrecognized output directory')
   xo.write_json_exclusive(identity_path,identity)
  configs=out/'configs';tiles=out/'tiles';configs.mkdir(mode=0o700,exist_ok=True);tiles.mkdir(mode=0o700,exist_ok=True)
  if (out/'report.json').exists():raise ValueError('batch already complete; preserve report')
  records=[];boxes=[];built=0;stopped=False
  tile_code={k:code[k] for k in ('coastal_band','core','shore','geometry','grid_io','output_io')}
  for y in range(0,h,th):
   for x in range(0,w,tw):
    if shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
    idx=(y//th)*math.ceil(w/tw)+(x//tw);box=[x,min(w,x+tw),y,min(h,y+th)];cfg={'schema':'simple-v2-coastal-band-v1','grid':g,**{k:c[k] for k in NAMES},'core':box,'pad_degrees':pad,'chunk':chunk,'max_shore_segments':limit,'minimum_free_bytes':reserve}
    cp=configs/f'{idx:06d}.json'
    if cp.exists():
     if json.loads(cp.read_bytes())!=cfg:raise ValueError('tile config changed')
    else:xo.write_json_exclusive(cp,cfg)
    expected_config=band.sha(cp);td=tiles/f'{idx:06d}';td.mkdir(mode=0o700,exist_ok=True);valid=[]
    for rp in sorted(td.glob('attempt-*/report.json')):
     m=json.loads(rp.read_bytes());span=(rp.parent/m['span_file']['path']).resolve()
     if (not span.is_relative_to(rp.parent) or band.sha(span)!=m['span_file']['sha256'] or m.get('schema')!='simple-v2-coastal-tile-report-v1' or m.get('status')!='research-partial-not-published' or m.get('config_sha256')!=expected_config or m.get('grid')!=g or m.get('core')!=box or m.get('inputs')!={k:c[k] for k in NAMES} or m.get('code_sha256')!=tile_code):raise ValueError('saved tile failed verification')
     valid.append((rp,m))
    if len(valid)>1:raise ValueError('duplicate completed tile')
    if valid:rp,m=valid[0]
    elif max_tiles is not None and built>=max_tiles:stopped=True;break
    else:
     n=1
     while (td/f'attempt-{n:04d}').exists():n+=1
     attempt=td/f'attempt-{n:04d}';m=band.build(cp,attempt,_verified_inputs=verified);rp=attempt/'report.json';built+=1
     print(json.dumps({'completed_tile':idx,'core':box,'assigned_cells':m['assigned_cells']}),flush=True)
    boxes.append(box);records.append({'core':box,'report_path':str(rp.relative_to(out)),'report_sha256':band.sha(rp),'assigned_cells':m['assigned_cells'],'physical_water_cells':m['physical_water_cells']})
   if stopped:break
  for k in NAMES:band.pin(c[k])
  if config_path.read_bytes()!=raw or any(band.sha(p)!=code[k] for k,p in paths.items()):raise ValueError('input or code changed during batch')
  if stopped:return {'status':'paused-research-partial','completed_tiles':len(records),'new_tiles':built}
  assembly.cover(boxes,w,h)
  result={'schema':'simple-v2-coastal-batch-report-v1','status':'research-partial-not-published','grid':g,'config_sha256':identity['config_sha256'],'inputs':{k:c[k] for k in NAMES},'code_sha256':code,'workers':1,'tile_count':len(records),'assigned_cells':sum(x['assigned_cells'] for x in records),'physical_water_cells':sum(x['physical_water_cells'] for x in records),'tile_cores_cover_grid':True,'tiles':records,'limitations':'Complete 12 nm candidate band only; open ocean is unassigned. Adaptive longitude halo and checks preserve a conservative spherical-distance certificate; historical geometry and tie conventions remain unverified.'}
  xo.write_json_exclusive(out/'report.json',result,indent=2);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');p.add_argument('--max-tiles',type=int);a=p.parse_args()
 try:print(json.dumps(build(a.config,a.output,a.max_tiles),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
