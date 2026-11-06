#!/usr/bin/python3
"""Compare mapped and row-streamed inputs on a bounded real graph window.

A resource-guarded I/O regression, not a whole-mainland scientific proof.
Seeds here are sampled from a prior research graph solely for this regression.
"""
import hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
from candidate_kernel import H,W,STEP,ROOT,TripleRows,need,sha,partition,rasterize_barriers
PINS={'fresh-components-output-20261104/rows.u32le':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7','fresh-components-output-20261104/runs.u32le':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961','actual-neon-boundary-export-20261104/v6/snapshot.json':'2de24700528fbf2d44acc4b67c17f6fe3b9bb594eba0add5c940e5d1cd569882','fresh-witness-output-20261104/resolution.json':'27ec973caf3eedb267e2c0277a710dceef04254075f81b689f5762d513d88ea5','mainland-source-recovery-20261104/topology-proposal/partition-draft-20261104/report.json':'35fcd1f6dcf3851bb62b5db6eb99bb0c378a81a6cc62963376315611daac186e'}
X0,X1,Y0,Y1=37080,37480,29480,30250

def main():
 start=time.monotonic();out=ROOT/'panama-window-reader-check-output-20261104';need(not out.exists(),'output exists')
 for p,h in PINS.items():need(sha(ROOT/p)==h,'pin mismatch '+p)
 graph=ROOT/'mainland-source-recovery-20261104/topology-proposal/partition-draft-20261104';rep=json.loads((graph/'report.json').read_text())
 for n in ('partition-rows.u32le','partition-spans.u32le'):
  PINS[str((graph/n).relative_to(ROOT))]=rep['outputs'][n]['sha256'];need(sha(graph/n)==PINS[str((graph/n).relative_to(ROOT))],'graph pin mismatch')
 snap=json.loads((ROOT/'actual-neon-boundary-export-20261104/v6/snapshot.json').read_text());b=next(x for x in snap['mainland_boundaries'] if x['boundary_id']=='panama_colombia_osm_admin_boundary');coords=[[float(v) for v in p] for p in b['geometry']['coordinates']];path=[[(lon+180)/STEP-X0,(90-lat)/STEP-Y0] for lon,lat in coords];need(all(0<=x<X1-X0 and 0<=y<Y1-Y0 for x,y in path),'line outside window');cuts=rasterize_barriers([path],X1-X0,Y1-Y0)
 witness=json.loads((ROOT/'fresh-witness-output-20261104/resolution.json').read_text());groups=[g for g in witness['groups'] if g['group_id']=='mainland-americas'];need(len(groups)==1,'missing mainland witness');root=groups[0]['component_id_current_generation_only']
 components=ROOT/'fresh-components-output-20261104';stream=TripleRows(components/'rows.u32le',components/'runs.u32le',H);mapped=np.memmap(components/'runs.u32le',dtype='<u4',mode='r').reshape(-1,3)
 def clipped(row):return [(max(X0,int(a))-X0,min(X1,int(z))-X0) for a,z,k in row if int(k)==root and int(a)<X1 and int(z)>X0]
 for y in range(Y0,Y1):
  a,b=map(int,stream.offsets[y:y+2]);need(np.array_equal(stream.row(y),mapped[a:b]),'reader mismatch at row '+str(y))
 old=TripleRows(graph/'partition-rows.u32le',graph/'partition-spans.u32le',H);seeds={}
 for y in range(Y0,Y1):
  for a,z,k in old.row(y):
   if int(k) in (20,21) and int(a)<X1 and int(z)>X0 and int(k) not in seeds:
    seeds[int(k)]=(max(X0,int(a))-X0,y-Y0)
 need(set(seeds)=={20,21},'missing window regression seeds')
 out.mkdir(mode=0o700)
 def by_stream(y):return clipped(stream.row(Y0+y))
 def by_map(y):
  yy=Y0+y;a,b=map(int,stream.offsets[yy:yy+2]);return clipped(mapped[a:b])
 result1=partition(by_stream,X1-X0,Y1-Y0,cuts,seeds,out/'stream');result2=partition(by_map,X1-X0,Y1-Y0,cuts,seeds,out/'mapped');need(result1==result2,'graph summaries differ')
 names=('nodes.u32le','partition-rows.u32le','partition-spans.u32le','residual-rows.u32le','residual-spans.u32le')
 hashes={n:sha(out/'stream'/n) for n in names}
 for n,h in hashes.items():need(sha(out/'mapped'/n)==h,'graph output differs '+n)
 stream.close();old.close();del mapped
 for p,h in PINS.items():need(sha(ROOT/p)==h,'input changed '+p)
 result={'schema':'panama-window-reader-regression-v1','status':'passed-window-only','window':[X0,X1,Y0,Y1],'seeds_from_prior_research_graph':seeds,'rows_checked':Y1-Y0,'inputs_sha256':PINS,'result':result1,'output_sha256':hashes,'elapsed_seconds':time.monotonic()-start,'limitations':['Window equivalence checks I/O and graph reproducibility only; it is not a fresh whole-mainland test or historical-map proof.','Seeds came from a prior source-cut research graph for this I/O regression, not as inputs to a production build.']}
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'rows':Y1-Y0,'selected_cells':result1['selected_cells']}))
if __name__=='__main__':main()
