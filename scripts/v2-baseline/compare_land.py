#!/usr/bin/env python3
"""Compare candidate land runs with preserved V2 labels, without using them in a build."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'v7-replay'));sys.path.insert(0,str(HERE.parent))
import build_coastal_tile as grid_io
import file_integrity as band_io
import exclusive_outputs as output_io
from build_coastal_tile import open_grid
from exclusive_outputs import write_json_exclusive
from file_integrity import pin,sha

def compare(config_path,output):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();cfg=json.loads(raw)
 keys={'schema','grid','candidate_rows','candidate_runs','candidate_report','reference_rows','reference_runs'}
 if set(cfg)!=keys or cfg['schema']!='simple-v2-land-comparison-v1':raise ValueError('invalid comparison config')
 g=cfg['grid'];w,h=g['width'],g['height']
 if (set(g)!={'width','height','step','west','north'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or g['north']!=90 or type(g['step']) not in (int,float) or not math.isfinite(g['step']) or g['step']!=360/w or g['north']-h*g['step'] < -90-1e-8):raise ValueError('invalid global grid')
 names=('candidate_rows','candidate_runs','candidate_report','reference_rows','reference_runs');paths={k:pin(cfg[k]) for k in names};output=Path(output).resolve()
 if output.exists() or any(p==output or p.is_relative_to(output) or output.is_relative_to(p.parent) for p in [config_path,*paths.values()]):raise ValueError('output must be new and outside input directories')
 code_paths={'compare':Path(__file__).resolve(),'grid_io':Path(grid_io.__file__).resolve(),'pin_io':Path(band_io.__file__).resolve(),'output_io':Path(output_io.__file__).resolve()};code_hashes={k:sha(v) for k,v in code_paths.items()}
 candidate=json.loads(paths['candidate_report'].read_bytes())
 if (candidate.get('schema')!='simple-v2-land-report-v1' or candidate.get('status')!='research-not-published' or candidate.get('grid')!=g or candidate.get('output_rows_sha256')!=cfg['candidate_rows']['sha256'] or candidate.get('output_runs_sha256')!=cfg['candidate_runs']['sha256']):raise ValueError('candidate report mismatch')
 cr,cu=open_grid(paths['candidate_rows'],paths['candidate_runs'],w,h);rr,ru=open_grid(paths['reference_rows'],paths['reference_runs'],w,h);counts=np.zeros((23,23),dtype=np.uint64)
 for y in range(h):
  ca,cb=int(cr[y]),int(cr[y+1]);ra,rb=int(rr[y]),int(rr[y+1]);ce=cu[2*ca:2*cb:2];cv=cu[2*ca+1:2*cb:2];re=ru[2*ra:2*rb:2];rv=ru[2*ra+1:2*rb:2]
  if not len(ce) or not len(re) or int(ce[-1])!=w or int(re[-1])!=w or int(ce[0])<=0 or int(re[0])<=0 or np.any(ce[1:]<=ce[:-1]) or np.any(re[1:]<=re[:-1]) or np.any(~np.isin(cv,[0,17,18,19,20,21,22])) or np.any(~np.isin(rv,[1,2,3,4,5,6,7,8,9,10,17,18,19,20,21,22])):raise ValueError('invalid row or code')
  ends=np.union1d(ce,re);starts=np.r_[np.uint32(0),ends[:-1]];lens=(ends-starts).astype(np.uint64);a=rv[np.searchsorted(re,starts,side='right')];b=cv[np.searchsorted(ce,starts,side='right')]
  np.add.at(counts,(a,b),lens)
 for k in names:pin(cfg[k])
 if config_path.read_bytes()!=raw or any(sha(p)!=code_hashes[k] for k,p in code_paths.items()):raise ValueError('comparison config or code changed')
 both=counts[17:23,17:23];equal=int(np.trace(both));both_total=int(both.sum());candidate_extra=int(counts[1:11,17:23].sum());candidate_missing=int(counts[17:23,0].sum())
 report={'schema':'simple-v2-land-comparison-report-v1','status':'research-validation-only','config_sha256':hashlib.sha256(raw).hexdigest(),'grid':g,'candidate_report_sha256':cfg['candidate_report']['sha256'],'code_sha256':code_hashes,'inputs':{k:cfg[k] for k in names},'both_land_cells':both_total,'matching_land_cells':equal,'different_continent_land_cells':both_total-equal,'candidate_land_reference_water':candidate_extra,'candidate_water_reference_land':candidate_missing,'confusion_reference_to_candidate':{str(a):{str(b):int(counts[a,b]) for b in range(17,23)} for a in range(17,23)},'limitation':'The historical V2 grid is used only as a comparison reference. Physical differences are separate from continent disagreements; this is not proof of historical algorithm or geographic correctness.'}
 write_json_exclusive(output,report,indent=2);return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(compare(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
