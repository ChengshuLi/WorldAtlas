#!/usr/bin/env python3
"""Compare one partial coastal-band tile with V2, without using V2 to build it."""
import argparse,gzip,hashlib,json,math,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import coastal_band as band
import build_coastal_tile as grid_io
import exclusive_outputs as output_io
from exclusive_outputs import write_json_exclusive

def compare(config_path,output,*,_verified_shared=None):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();cfg=json.loads(raw)
 if set(cfg)!={'schema','tile_report','reference_rows','reference_runs'} or cfg['schema']!='simple-v2-coastal-comparison-v1':raise ValueError('invalid comparison config')
 names=('tile_report','reference_rows','reference_runs');paths={'tile_report':band.pin(cfg['tile_report'])}
 if _verified_shared is None:
  paths.update({k:band.pin(cfg[k]) for k in ('reference_rows','reference_runs')})
 else:
  if set(_verified_shared)!={'reference_rows','reference_runs','physical_rows','physical_runs'} or any(cfg[k]!=_verified_shared[k]['spec'] or Path(cfg[k]['path']).resolve()!=Path(_verified_shared[k]['path']) for k in ('reference_rows','reference_runs')):raise ValueError('batch reference specifications differ')
  paths.update({k:Path(_verified_shared[k]['path']) for k in ('reference_rows','reference_runs')})
 report=json.loads(paths['tile_report'].read_bytes())
 if report.get('schema')!='simple-v2-coastal-tile-report-v1' or report.get('status')!='research-partial-not-published':raise ValueError('invalid partial tile report')
 g=report['grid'];w,h=g['width'],g['height'];box=report['core']
 if set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or g['north']!=90 or type(g['step']) not in (int,float) or not math.isfinite(g['step']) or g['step']!=360/w or g['north']-h*g['step'] < -90-1e-8 or not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box):raise ValueError('invalid grid or core')
 x0,x1,y0,y1=box
 if not (0<=x0<x1<=w and 0<=y0<y1<=h):raise ValueError('invalid core')
 source=report['span_file'];span=(paths['tile_report'].parent/source['path']).resolve()
 if not span.is_relative_to(paths['tile_report'].parent) or band.sha(span)!=source['sha256']:raise ValueError('span hash/path mismatch')
 if _verified_shared is None:physical={k:band.pin(report['inputs'][k]) for k in ('physical_rows','physical_runs')}
 else:
  if any(report['inputs'][k]!=_verified_shared[k]['spec'] or Path(report['inputs'][k]['path']).resolve()!=Path(_verified_shared[k]['path']) for k in ('physical_rows','physical_runs')):raise ValueError('batch physical specifications differ')
  physical={k:Path(_verified_shared[k]['path']) for k in ('physical_rows','physical_runs')}
 inputs=[config_path,*paths.values(),span,*physical.values()];output=Path(output).resolve()
 if output.exists() or any(p==output or p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs):raise ValueError('output must be new and outside input directories')
 code_paths={'compare':Path(__file__).resolve(),'band_io':Path(band.__file__).resolve(),'grid_io':Path(grid_io.__file__).resolve(),'output_io':Path(output_io.__file__).resolve(),'shore':Path(band.core.shore.__file__).resolve(),'core':Path(band.core.__file__).resolve()};code={k:band.sha(v) for k,v in code_paths.items()}
 pr,pu=grid_io.open_grid(physical['physical_rows'],physical['physical_runs'],w,h);rr,ru=grid_io.open_grid(paths['reference_rows'],paths['reference_runs'],w,h);counts={'matched_continental_water':0,'different_continent_water':0,'candidate_band_reference_ocean':0,'candidate_band_reference_land':0,'reference_band_missing_from_candidate':0,'candidate_land_reference_water':0,'candidate_water_reference_land':0};seen_cells=seen_spans=0
 with gzip.open(span,'rt',encoding='utf8') as f:
  def nextrow():
   line=f.readline();return None if not line else json.loads(line)
  current=nextrow()
  for y in range(y0,y1):
   p=band.core.shore.crop(pr,pu,y,x0,x1,w);ref=band.core.shore.crop(rr,ru,y,x0,x1,w)
   if np.any(~np.isin(p,[1,17])) or np.any(~np.isin(ref,[1,2,3,4,5,6,7,8,9,10,17,18,19,20,21,22])):raise ValueError('invalid reference or physical class')
   pred=np.zeros(x1-x0,dtype=np.uint8)
   if current is not None:
    row=current.get('row');spans=current.get('spans')
    if type(row) is not int or row<y or row>=y1 or not isinstance(spans,list) or not spans:raise ValueError('invalid or unordered tile row')
    if row==y:
     end=x0
     for item in spans:
      if not isinstance(item,dict) or set(item)!={'start','end','code'} or any(type(item[k]) is not int for k in item) or not end<=item['start']<item['end']<=x1 or item['code'] not in range(1,7):raise ValueError('invalid or overlapping span')
      pred[item['start']-x0:item['end']-x0]=item['code'];end=item['end'];seen_cells+=item['end']-item['start'];seen_spans+=1
     current=nextrow()
   if np.any((pred>0)&(p!=1)):raise ValueError('coastal prediction covers physical land')
   active=pred>0;ref_coast=np.isin(ref,range(1,7));ref_ocean=np.isin(ref,range(7,11));ref_land=ref>=17
   counts['matched_continental_water']+=int(np.count_nonzero(active&ref_coast&(pred==ref)))
   counts['different_continent_water']+=int(np.count_nonzero(active&ref_coast&(pred!=ref)))
   counts['candidate_band_reference_ocean']+=int(np.count_nonzero(active&ref_ocean))
   counts['candidate_band_reference_land']+=int(np.count_nonzero(active&ref_land))
   counts['reference_band_missing_from_candidate']+=int(np.count_nonzero((p==1)&~active&ref_coast))
   counts['candidate_land_reference_water']+=int(np.count_nonzero((p==17)&~ref_land))
   counts['candidate_water_reference_land']+=int(np.count_nonzero((p==1)&ref_land))
  if current is not None:raise ValueError('extra tile rows')
 if seen_cells!=report.get('assigned_cells') or seen_spans!=report.get('span_count'):raise ValueError('tile count mismatch')
 band.pin(cfg['tile_report'])
 if _verified_shared is None:
  for k in ('reference_rows','reference_runs'):band.pin(cfg[k])
  for k in ('physical_rows','physical_runs'):band.pin(report['inputs'][k])
 if band.sha(span)!=source['sha256'] or config_path.read_bytes()!=raw or any(band.sha(p)!=code[k] for k,p in code_paths.items()):raise ValueError('input or code changed')
 result={'schema':'simple-v2-coastal-comparison-report-v1','status':'research-validation-only','config_sha256':hashlib.sha256(raw).hexdigest(),'grid':g,'core':box,'tile_report_sha256':cfg['tile_report']['sha256'],'inputs':cfg,'code_sha256':code,'candidate_band_cells':seen_cells,'counts':counts,'limitation':'Partial tile comparison only. Preserved V2 is validation input, never a build input. Open ocean assignment and geographic correctness remain unresolved.'};write_json_exclusive(output,result,indent=2);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(compare(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
