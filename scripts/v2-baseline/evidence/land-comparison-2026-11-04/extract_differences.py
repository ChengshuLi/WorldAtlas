#!/usr/bin/env python3
"""Export all candidate/V2 land discrepancies as grid-aligned spans.

A separate mainland seed is used only for explaining the candidate provenance.
"""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np
W=131072;H=54614
ap=argparse.ArgumentParser();ap.add_argument('--candidate-dir',required=True,type=Path);ap.add_argument('--reference-dir',required=True,type=Path);ap.add_argument('--seed-dir',required=True,type=Path);ap.add_argument('--output-dir',required=True,type=Path);v=ap.parse_args();P=v.candidate_dir;R=v.reference_dir;S=v.seed_dir;O=v.output_dir
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
paths={'candidate_rows':P/'rows.u32le','candidate_runs':P/'runs.u32le','reference_rows':R/'v2-rows.u32','reference_runs':R/'v2-runs.u32','seed_rows':S/'rows.u32le','seed_runs':S/'runs.u32le'}
before={k:sha(v) for k,v in paths.items()}
if O.exists():raise RuntimeError('output exists')
O.mkdir()
def grid(r,u):
 rows=np.memmap(r,mode='r',dtype='<u4');runs=np.memmap(u,mode='r',dtype='<u4').reshape(-1,2)
 if len(rows)!=H+1 or rows[0]!=0 or rows[-1]!=len(runs):raise ValueError('bad offsets')
 return rows,runs
cr,cu=grid(P/'rows.u32le',P/'runs.u32le');rr,ru=grid(R/'v2-rows.u32',R/'v2-runs.u32');sr,su=grid(S/'rows.u32le',S/'runs.u32le');counts={};nspan=0
with (O/'spans.tsv').open('x') as f:
 f.write('row\tstart\tend\treference\tcandidate\tmainland_seed\n')
 for y in range(H):
  cv=cu[int(cr[y]):int(cr[y+1])];rv=ru[int(rr[y]):int(rr[y+1])];sv=su[int(sr[y]):int(sr[y+1])]
  for a in (cv,rv,sv):
   if len(a)==0 or int(a[-1,0])!=W or int(a[0,0])<=0 or np.any(a[1:,0]<=a[:-1,0]):raise ValueError('invalid row')
  ends=np.union1d(np.union1d(cv[:,0],rv[:,0]),sv[:,0]);starts=np.r_[np.uint32(0),ends[:-1]]
  old=rv[np.searchsorted(rv[:,0],starts,side='right'),1];new=cv[np.searchsorted(cv[:,0],starts,side='right'),1];seed=sv[np.searchsorted(sv[:,0],starts,side='right'),1]
  different=(old!=new)&(((old>=17)&(old<=22))|((new>=17)&(new<=22)))
  for a,b,o,n,s in zip(starts[different],ends[different],old[different],new[different],seed[different]):
   key=f'{o}:{n}:{"mainland" if s else "offshore_or_physical"}';counts[key]=counts.get(key,0)+int(b-a);f.write(f'{y}\t{a}\t{b}\t{o}\t{n}\t{s}\n');nspan+=1
if {k:sha(v) for k,v in paths.items()}!=before:raise ValueError('input changed during extraction')
r={'schema':'simple-v2-land-geography-differences-v1','status':'research-validation-only','spans':nspan,'cells_by_transition_seed_status':counts,'spans_sha256':sha(O/'spans.tsv'),'candidate_rows_sha256':sha(P/'rows.u32le'),'candidate_runs_sha256':sha(P/'runs.u32le'),'reference_rows_sha256':sha(R/'v2-rows.u32'),'reference_runs_sha256':sha(R/'v2-runs.u32'),'seed_rows_sha256':sha(S/'rows.u32le'),'seed_runs_sha256':sha(S/'runs.u32le'),'limitation':'Mainland seed is a candidate provenance classification, not an explanation of historical V2 source or geographic correctness.'}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
