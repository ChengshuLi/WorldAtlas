#!/usr/bin/env python3
"""Build all partial V2 coastal-band tiles with bounded concurrency and shared pins."""
import argparse,concurrent.futures,hashlib,json,math,shutil,sys
from pathlib import Path
import coastal_band as band
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import assemble_coastal_tiles as assembly
import exclusive_outputs as xo

def tile_job(task):
 config,out,verified=task
 return band.build(config,out,_verified_inputs=verified)

def build(config_path,output):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();c=json.loads(raw);names=('physical_rows','physical_runs','land_rows','land_runs','land_report');required={'schema','grid',*names,'tile_width','tile_height','pad_degrees'}
 if not required<=set(c)<=required|{'workers','chunk','max_shore_segments','minimum_free_bytes'} or c['schema']!='simple-v2-coastal-batch-v1':raise ValueError('invalid batch config')
 g=c['grid'];w,h=g['width'],g['height'];step=g['step'];tw,th=c['tile_width'],c['tile_height'];workers=c.get('workers',1);chunk=c.get('chunk',5000);limit=c.get('max_shore_segments',1000000);reserve=c.get('minimum_free_bytes',2*(1<<30));pad=c['pad_degrees']
 if (set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or g['north']!=90 or type(step) not in (int,float) or not math.isfinite(step) or step!=360/w or 90-h*step < -90-1e-8):raise ValueError('invalid grid')
 if (any(type(x) is not int for x in (tw,th,workers,chunk,limit,reserve)) or not 1<=tw<=w or not 1<=th<=h or not 1<=workers<=8 or not 1<=chunk<=50000 or limit<1 or reserve<0 or type(pad) not in (int,float) or not math.isfinite(pad) or pad<=0):raise ValueError('invalid tile/resource settings')
 verified={k:{'spec':c[k],'path':str(band.pin(c[k]))} for k in names};inputs=[config_path,*[Path(v['path']) for v in verified.values()]]
 land_report=json.loads(Path(verified['land_report']['path']).read_bytes())
 if (land_report.get('schema')!='simple-v2-land-report-v1' or land_report.get('status')!='research-not-published' or land_report.get('grid')!=g or any(land_report.get('inputs',{}).get(k)!=c[k] for k in ('physical_rows','physical_runs')) or land_report.get('output_rows_sha256')!=c['land_rows']['sha256'] or land_report.get('output_runs_sha256')!=c['land_runs']['sha256']):raise ValueError('land report does not bind inputs')
 out=Path(output).resolve();code_paths={'batch':Path(__file__).resolve(),'band':Path(band.__file__).resolve(),'core':Path(band.core.__file__).resolve(),'shore':Path(band.core.shore.__file__).resolve(),'geometry':Path(band.core.shore.geom.__file__).resolve(),'grid_io':Path(band.grid_io.__file__).resolve(),'output_io':Path(xo.__file__).resolve(),'coverage_io':Path(assembly.__file__).resolve()};code={k:band.sha(v) for k,v in code_paths.items()}
 if out.exists() or any(p==out or p.is_relative_to(out) or out.is_relative_to(p.parent) for p in [*inputs,*code_paths.values()]):raise ValueError('output must be new and outside input directories')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 xo.create_directory_exclusive(out);configs=out/'configs';tiles=out/'tiles';configs.mkdir(mode=0o700);tiles.mkdir(mode=0o700)
 def tasks():
  i=0
  for y in range(0,h,th):
   for x in range(0,w,tw):
    if shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
    box=[x,min(w,x+tw),y,min(h,y+th)];cfg={'schema':'simple-v2-coastal-band-v1','grid':g,**{k:c[k] for k in names},'core':box,'pad_degrees':pad,'chunk':chunk,'max_shore_segments':limit,'minimum_free_bytes':reserve}
    config=configs/f'{i:06d}.json';xo.write_json_exclusive(config,cfg);yield (str(config),str(tiles/f'{i:06d}'),verified);i+=1
 results=[]
 if workers==1:
  for task in tasks():results.append(tile_job(task))
 else:
  iterator=iter(tasks())
  with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
   pending={}
   try:
    for _ in range(workers*2):
     try:task=next(iterator)
     except StopIteration:break
     pending[pool.submit(tile_job,task)]=task
    while pending:
     done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
     for future in done:
      pending.pop(future);results.append(future.result())
      try:task=next(iterator)
      except StopIteration:continue
      pending[pool.submit(tile_job,task)]=task
   except BaseException:
    for future in pending:future.cancel()
    raise
 for k in names:band.pin(c[k])
 if config_path.read_bytes()!=raw or any(band.sha(p)!=code[k] for k,p in code_paths.items()):raise ValueError('batch input or code changed')
 records=[];boxes=[]
 for m in results:
  box=m['core'];idx=(box[2]//th)*math.ceil(w/tw)+(box[0]//tw);rp=tiles/f'{idx:06d}'/'report.json';span=rp.parent/m['span_file']['path']
  if json.loads(rp.read_bytes())!=m or band.sha(span)!=m['span_file']['sha256']:raise ValueError('tile output changed')
  boxes.append(box);records.append({'core':box,'report_path':str(rp.relative_to(out)),'report_sha256':band.sha(rp),'assigned_cells':m['assigned_cells'],'physical_water_cells':m['physical_water_cells']})
 assembly.cover(boxes,w,h);records.sort(key=lambda x:(x['core'][2],x['core'][0]))
 result={'schema':'simple-v2-coastal-batch-report-v1','status':'research-partial-not-published','grid':g,'config_sha256':hashlib.sha256(raw).hexdigest(),'inputs':{k:c[k] for k in names},'code_sha256':code,'workers':workers,'tile_count':len(records),'assigned_cells':sum(x['assigned_cells'] for x in records),'physical_water_cells':sum(x['physical_water_cells'] for x in records),'tile_cores_cover_grid':True,'tiles':records,'limitations':'Complete core tessellation of the 12 nm candidate band only; open ocean is unassigned. Same-run shared input verification is not source authentication or historical proof.'};xo.write_json_exclusive(out/'report.json',result,indent=2);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(build(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
