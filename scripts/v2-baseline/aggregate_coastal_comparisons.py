#!/usr/bin/env python3
"""Aggregate V2 coastal-tile comparisons only after exact full-grid coverage."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import coastal_band as band
import assemble_coastal_tiles as assembly
import exclusive_outputs as output_io
from exclusive_outputs import write_json_exclusive

COUNT_KEYS=('matched_continental_water','different_continent_water','candidate_band_reference_ocean','candidate_band_reference_land','reference_band_missing_from_candidate','candidate_land_reference_water','candidate_water_reference_land')
def aggregate(config_path,output):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();cfg=json.loads(raw)
 if set(cfg)!={'schema','grid','comparisons'} or cfg['schema']!='simple-v2-coastal-comparisons-v1' or not isinstance(cfg['comparisons'],list) or not cfg['comparisons']:raise ValueError('invalid aggregation config')
 g=cfg['grid'];w,h=g['width'],g['height']
 if set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or g['north']!=90 or g['step']!=360/w or 90-h*g['step'] < -90-1e-8:raise ValueError('invalid grid')
 code_paths={'aggregate':Path(__file__).resolve(),'band_io':Path(band.__file__).resolve(),'coverage_io':Path(assembly.__file__).resolve(),'output_io':Path(output_io.__file__).resolve()};code_hashes={k:band.sha(v) for k,v in code_paths.items()}
 cache={};files=[]
 def check(spec):
  if not isinstance(spec,dict) or set(spec)!={'path','sha256'}:raise ValueError('invalid pin')
  key=(spec['path'],spec['sha256'])
  if key not in cache:cache[key]=band.pin(spec)
  files.append(cache[key]);return cache[key]
 boxes=[];baseline=None;totals={k:0 for k in COUNT_KEYS};cells=0
 for spec in cfg['comparisons']:
  cp=check(spec);c=json.loads(cp.read_bytes());source=c.get('inputs',{})
  if c.get('schema')!='simple-v2-coastal-comparison-report-v1' or c.get('status')!='research-validation-only' or c.get('grid')!=g or not isinstance(source,dict) or set(source)!={'schema','tile_report','reference_rows','reference_runs'} or source.get('schema')!='simple-v2-coastal-comparison-v1':raise ValueError('invalid comparison report')
  tp=check(source['tile_report']);t=json.loads(tp.read_bytes());box=t.get('core')
  if t.get('schema')!='simple-v2-coastal-tile-report-v1' or t.get('status')!='research-partial-not-published' or t.get('grid')!=g or c.get('core')!=box or c.get('tile_report_sha256')!=source['tile_report']['sha256'] or not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box):raise ValueError('invalid tile lineage')
  span=t.get('span_file',{});sp=(tp.parent/span.get('path','')).resolve()
  if not sp.is_relative_to(tp.parent):raise ValueError('tile span escapes report')
  check({'path':str(sp),'sha256':span.get('sha256')})
  inp=t.get('inputs',{});required={'physical_rows','physical_runs','land_rows','land_runs','land_report'}
  if not isinstance(inp,dict) or set(inp)!=required:raise ValueError('invalid tile inputs')
  for pin in inp.values():check(pin)
  for k in ('reference_rows','reference_runs'):check(source[k])
  tile_code=t.get('code_sha256');comparison_code=c.get('code_sha256');digest=lambda x:isinstance(x,str) and len(x)==64 and all(ch in '0123456789abcdef' for ch in x)
  if (not isinstance(tile_code,dict) or set(tile_code)!={'coastal_band','core','shore','geometry','grid_io','output_io'} or not all(digest(x) for x in tile_code.values()) or not isinstance(comparison_code,dict) or set(comparison_code)!={'compare','band_io','grid_io','output_io','shore','core'} or not all(digest(x) for x in comparison_code.values()) or t.get('method')!='12 nautical miles inclusive; spherical distance to physical-grid land/water edge; lowest continent code wins ties within 0.00001 metres'):raise ValueError('invalid algorithm lineage')
  lineage={'tile_inputs':inp,'tile_code':tile_code,'method':t['method'],'comparison_code':comparison_code,'reference_rows':source['reference_rows'],'reference_runs':source['reference_runs']}
  if baseline is None:baseline=lineage
  elif lineage!=baseline:raise ValueError('mixed candidate, reference or algorithm lineage')
  counts=c.get('counts',{});n=c.get('candidate_band_cells')
  if not isinstance(counts,dict) or set(counts)!=set(COUNT_KEYS) or any(type(counts[k]) is not int or counts[k]<0 for k in COUNT_KEYS) or type(n) is not int or n<0 or n!=t.get('assigned_cells') or sum(counts[k] for k in COUNT_KEYS[:4])!=n or any(counts[k]>(box[1]-box[0])*(box[3]-box[2]) for k in COUNT_KEYS):raise ValueError('invalid comparison counts')
  for k in COUNT_KEYS:totals[k]+=counts[k]
  cells+=n;boxes.append(box)
 assembly.cover(boxes,w,h);output=Path(output).resolve()
 if output.exists() or any(p==output or p.is_relative_to(output) or output.is_relative_to(p.parent) for p in [config_path,*files]):raise ValueError('output must be new and outside input directories')
 # Recheck unique pins at the end, avoiding repeated multi-gigabyte source hashes.
 for path,digest in cache:band.pin({'path':path,'sha256':digest})
 if config_path.read_bytes()!=raw or any(band.sha(v)!=code_hashes[k] for k,v in code_paths.items()):raise ValueError('config or code changed during aggregation')
 result={'schema':'simple-v2-coastal-comparisons-report-v1','status':'research-validation-only','grid':g,'config_sha256':hashlib.sha256(raw).hexdigest(),'comparison_count':len(boxes),'comparisons':cfg['comparisons'],'code_sha256':code_hashes,'candidate_band_cells':cells,'counts':totals,'lineage':baseline,'limitation':'Full tile coverage is verified, but geographic and historical correctness are not. Open ocean assignment remains unresolved.'};write_json_exclusive(output,result,indent=2);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(aggregate(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
