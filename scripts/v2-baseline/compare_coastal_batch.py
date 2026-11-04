#!/usr/bin/env python3
"""Compare a complete candidate coastal tile batch with V2 using shared pins."""
import argparse,concurrent.futures,hashlib,json,shutil,sys
from pathlib import Path
import coastal_band as band
import compare_coastal as compare
import aggregate_coastal_comparisons as aggregate
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import assemble_coastal_tiles as assembly
import exclusive_outputs as xo

def compare_job(task):
 config,out,verified=task
 return compare.compare(config,out,_verified_shared=verified)

def build(config_path,output):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();c=json.loads(raw);required={'schema','candidate_batch','reference_rows','reference_runs'}
 if not required<=set(c)<=required|{'workers','minimum_free_bytes'} or c['schema']!='simple-v2-coastal-comparison-batch-v1':raise ValueError('invalid batch config')
 workers=c.get('workers',1);reserve=c.get('minimum_free_bytes',2*(1<<30))
 if type(workers) is not int or not 1<=workers<=8 or type(reserve) is not int or reserve<0:raise ValueError('invalid resource settings')
 batch_path=band.pin(c['candidate_batch']);candidate=json.loads(batch_path.read_bytes());grid=candidate.get('grid',{});tiles=candidate.get('tiles')
 if (candidate.get('schema')!='simple-v2-coastal-batch-report-v1' or candidate.get('status')!='research-partial-not-published' or candidate.get('tile_cores_cover_grid') is not True or not isinstance(tiles,list) or not tiles or candidate.get('tile_count')!=len(tiles)):raise ValueError('invalid candidate batch')
 names=('physical_rows','physical_runs','land_rows','land_runs','land_report');inputs=candidate.get('inputs',{})
 if not isinstance(inputs,dict) or set(inputs)!=set(names):raise ValueError('invalid candidate batch inputs')
 pins={k:band.pin(inputs[k]) for k in names};refs={k:band.pin(c[k]) for k in ('reference_rows','reference_runs')};verified={k:{'spec':inputs[k],'path':str(pins[k])} for k in ('physical_rows','physical_runs')};verified.update({k:{'spec':c[k],'path':str(refs[k])} for k in refs})
 boxes=[];sources=[]
 for item in tiles:
  if not isinstance(item,dict) or set(item)!={'core','report_path','report_sha256','assigned_cells','physical_water_cells'}:raise ValueError('invalid tile record')
  path=(batch_path.parent/item['report_path']).resolve()
  if not path.is_relative_to(batch_path.parent):raise ValueError('tile report escapes batch')
  source={'path':str(path),'sha256':item['report_sha256']};band.pin(source);tile=json.loads(path.read_bytes())
  if tile.get('core')!=item['core'] or tile.get('assigned_cells')!=item['assigned_cells'] or tile.get('physical_water_cells')!=item['physical_water_cells'] or tile.get('inputs')!=inputs or tile.get('grid')!=grid:raise ValueError('tile record mismatch')
  boxes.append(item['core']);sources.append(source)
 assembly.cover(boxes,grid['width'],grid['height'])
 out=Path(output).resolve();code_paths={'batch_compare':Path(__file__).resolve(),'compare':Path(compare.__file__).resolve(),'aggregate':Path(aggregate.__file__).resolve(),'band':Path(band.__file__).resolve(),'coverage_io':Path(assembly.__file__).resolve(),'output_io':Path(xo.__file__).resolve()};code={k:band.sha(v) for k,v in code_paths.items()}
 if out.exists() or any(p==out or p.is_relative_to(out) or out.is_relative_to(p.parent) for p in [config_path,batch_path,*pins.values(),*refs.values(),*code_paths.values()]):raise ValueError('output must be new and outside input directories')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 xo.create_directory_exclusive(out);configs=out/'configs';reports=out/'comparisons';configs.mkdir(mode=0o700);reports.mkdir(mode=0o700)
 def tasks():
  for i,source in enumerate(sources):
   if shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
   path=configs/f'{i:06d}.json';xo.write_json_exclusive(path,{'schema':'simple-v2-coastal-comparison-v1','tile_report':source,'reference_rows':c['reference_rows'],'reference_runs':c['reference_runs']});dest=reports/f'{i:06d}';dest.mkdir(mode=0o700);yield str(path),str(dest/'report.json'),verified
 results=[]
 if workers==1:
  for task in tasks():results.append((task[1],compare_job(task)))
 else:
  iterator=iter(tasks())
  with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
   pending={}
   try:
    for _ in range(workers*2):
     try:task=next(iterator)
     except StopIteration:break
     pending[pool.submit(compare_job,task)]=task
    while pending:
     done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
     for future in done:
      task=pending.pop(future);results.append((task[1],future.result()))
      try:task=next(iterator)
      except StopIteration:continue
      pending[pool.submit(compare_job,task)]=task
   except BaseException:
    for future in pending:future.cancel()
    raise
 comparison_pins=[]
 for path,result in sorted(results):
  p=Path(path)
  if json.loads(p.read_bytes())!=result:raise ValueError('comparison output changed')
  comparison_pins.append({'path':str(p),'sha256':band.sha(p)})
 aggregate_config=configs/'aggregate.json';xo.write_json_exclusive(aggregate_config,{'schema':'simple-v2-coastal-comparisons-v1','grid':grid,'comparisons':comparison_pins});summary=aggregate.aggregate(aggregate_config,out/'aggregate.json')
 for k in names:band.pin(inputs[k])
 for k in refs:band.pin(c[k])
 band.pin(c['candidate_batch'])
 if config_path.read_bytes()!=raw or any(band.sha(p)!=code[k] for k,p in code_paths.items()):raise ValueError('batch input or code changed')
 result={'schema':'simple-v2-coastal-comparison-batch-report-v1','status':'research-validation-only','grid':grid,'candidate_batch_sha256':c['candidate_batch']['sha256'],'reference_rows':c['reference_rows'],'reference_runs':c['reference_runs'],'config_sha256':hashlib.sha256(raw).hexdigest(),'code_sha256':code,'workers':workers,'aggregate_sha256':band.sha(out/'aggregate.json'),'counts':summary['counts'],'candidate_band_cells':summary['candidate_band_cells'],'comparison_count':summary['comparison_count'],'limitation':'Full tile coverage of a partial 12 nm band comparison. V2 was validation-only; open ocean remains unresolved.'};xo.write_json_exclusive(out/'report.json',result,indent=2);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(build(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
