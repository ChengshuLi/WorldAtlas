#!/usr/bin/python3
"""Compare a previously source-cut mainland graph against stage2; no closure, no V7.

The graph is an existing independently swept diagnostic. Residual side by nearest
oriented source segment is experimental and is not an accepted policy.
"""
import hashlib,json,math,os,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent;OUT=Path(__file__).resolve().parent/'result.json'
P={
 'graph_report':('mainland-source-recovery-20261104/topology-proposal/partition-draft-20261104/report.json','35fcd1f6dcf3851bb62b5db6eb99bb0c378a81a6cc62963376315611daac186e'),
 'sweep':('mainland-source-recovery-20261104/topology-proposal/partition-independent-sweep.json','7d9ba187e1a8ba992673ac60b7cc74734c2b5e04df1feee9c3f1cdf505293c65'),
 'witness':('fresh-witness-output-20261104/resolution.json','27ec973caf3eedb267e2c0277a710dceef04254075f81b689f5762d513d88ea5'),
 'stage2':('actual-stage2-geodesic-output-20261104/report.json','9086511ba0fb64a9331847cc8271129c125cec4e0e873ab04ad719023a503a20'),
 'source':('mainland-source-recovery-20261104/v5-europe-asia-sourcecut-candidate.geojson','b0401ee291aff8b6b5fdaabb4501e7321cbf6c8e9eba9be19cdca6e7ab846382')}
def need(x,msg):
 if not x:raise ValueError(msg)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads((ROOT/p).read_bytes())
def prefix(end,codes,pos,target):
 start=np.r_[0,end[:-1]]; lengths=(end-start)*(codes==target); cumul=np.r_[0,np.cumsum(lengths,dtype=np.int64)];idx=np.searchsorted(end,pos,side='left');return cumul[idx]+np.where(idx<len(end),(pos-np.r_[start, end[-1]][idx])*(np.r_[codes,-1][idx]==target),0)
def count_match(end,codes,start,stop,target):
 return int((prefix(end,codes,stop,target)-prefix(end,codes,start,target)).sum())
def nearest_side(lon,lat,coords):
 raise RuntimeError('planar nearest-side method retired; a reviewed WGS84 replacement is required')

def main():
 raise RuntimeError('planar nearest-side method retired; a reviewed WGS84 replacement is required')
 need(not OUT.exists(),'output exists')
 for path,h in P.values():need(sha(ROOT/path)==h,'pin '+path)
 graph=read(P['graph_report'][0]);w=read(P['witness'][0]);b=read(P['stage2'][0]);src=read(P['source'][0]);sweep=read(P['sweep'][0]);need(sweep['status']=='passed-local-draft-only' and sweep['partition_report_sha256']==P['graph_report'][1],'sweep lineage')
 groups=[x for x in w['groups'] if x['group_id']=='mainland-americas'];need(len(groups)==1,'witness');america=groups[0]['component_id_current_generation_only'];need(america in graph['component_ids'],'component lineage')
 line=next(f['geometry']['coordinates'] for f in src['features'] if f['properties']['cut_id']=='panama_colombia_osm_admin_boundary');anchors={x['side']:x for x in graph['witnesses'] if x['side'] in ('North America','South America')};need(set(anchors)=={'North America','South America'} and all(x['component_id']==america for x in anchors.values()),'anchor lineage');need(nearest_side(*anchors['North America']['source_lonlat'],line)[0]==1 and nearest_side(*anchors['South America']['source_lonlat'],line)[0]==-1,'witness orientation')
 need(graph['grid']=={'width':131072,'height':54614} and b['grid']=={'width':131072,'height':54614,'west':-180,'north':90,'step':360/131072},'grid lineage');need(all(b['inputs_sha256'][k]==w['input_sha256'][k] for k in ('component_rows','component_runs','physical_rows','physical_runs')),'stage2 lineage');need(graph['pins']['land-decision-rebuild-20261103/newer-physical-components/rows.u32le']==w['input_sha256']['component_rows'] and graph['pins']['land-decision-rebuild-20261103/newer-physical-components/runs.u32le']==w['input_sha256']['component_runs'] and graph['pins']['mainland-source-recovery-20261104/v5-europe-asia-sourcecut-candidate.geojson']==P['source'][1],'graph source lineage')
 streams={'gr':('mainland-source-recovery-20261104/topology-proposal/partition-draft-20261104/partition-rows.u32le',graph['outputs']['partition-rows.u32le']['sha256']),'gs':('mainland-source-recovery-20261104/topology-proposal/partition-draft-20261104/partition-spans.u32le',graph['outputs']['partition-spans.u32le']['sha256']),'rr':('mainland-source-recovery-20261104/topology-proposal/partition-draft-20261104/residual-rows.u32le',graph['outputs']['residual-rows.u32le']['sha256']),'rs':('mainland-source-recovery-20261104/topology-proposal/partition-draft-20261104/residual-spans.u32le',graph['outputs']['residual-spans.u32le']['sha256']),'br':('actual-stage2-geodesic-output-20261104/rows.u32le',b['output_rows_sha256']),'bs':('actual-stage2-geodesic-output-20261104/runs.u32le',b['output_runs_sha256']),'cr':('fresh-components-output-20261104/rows.u32le',w['input_sha256']['component_rows']),'cs':('fresh-components-output-20261104/runs.u32le',w['input_sha256']['component_runs'])}
 for path,h in streams.values():need(sha(ROOT/path)==h,'stream pin '+path)
 H=54614;W=131072; step=360/W
 def rows(k):
  v=np.fromfile(ROOT/streams[k][0],dtype='<u4');need(len(v)==H+1 and v[0]==0 and np.all(v[1:]>=v[:-1]),'rows');return v
 gr,rr,br,cr=map(rows,('gr','rr','br','cr'))
 def mm(k,cols):
  v=np.memmap(ROOT/streams[k][0],mode='r',dtype='<u4');need(len(v)%cols==0,'stream shape');return v.reshape(-1,cols)
 gs,rs,bs,cs=mm('gs',3),mm('rs',3),mm('bs',2),mm('cs',3);need(int(gr[-1])==len(gs) and int(rr[-1])==len(rs) and int(br[-1])==len(bs) and int(cr[-1])==len(cs),'offset sizes')
 counts={'graph_classified_cells':0,'graph_matching_stage2':0,'residual_cells':0,'residual_matching_stage2':0,'residual_ambiguous':0}; residual=[]
 for y in range(H):
  base=bs[br[y]:br[y+1]].astype(np.int64); need(len(base)>0 and base[-1,0]==W and np.all(base[1:,0]>base[:-1,0]),'base row invalid'); ends=base[:,0];codes=base[:,1]
  a=gs[gr[y]:gr[y+1]].astype(np.int64);a=a[np.isin(a[:,2],[20,21])]
  for code in (20,21):
   z=a[a[:,2]==code];counts['graph_classified_cells']+=int((z[:,1]-z[:,0]).sum());counts['graph_matching_stage2']+=count_match(ends,codes,z[:,0],z[:,1],code)
  r=rs[rr[y]:rr[y+1]]
  if len(r):
   comp=cs[cr[y]:cr[y+1]];ce=comp[:,1]
   for start,end,_ in r:
    i=int(np.searchsorted(ce,int(start),side='right'));need(i<len(comp) and int(comp[i,0])<=int(start) and int(comp[i,1])>=int(end),'residual component span')
    if int(comp[i,2])!=america:continue
    for x in range(int(start),int(end)):
     sign,dist=nearest_side(-180+(x+.5)*step,90-(y+.5)*step,line);value=20 if sign==1 else 21 if sign==-1 else None;old=int(codes[np.searchsorted(ends,x,side='right')]);counts['residual_cells']+=1;counts['residual_ambiguous']+=value is None;counts['residual_matching_stage2']+=value==old;residual.append({'x':x,'y':y,'experimental_code':value,'stage2_code':old,'distance_degrees':dist})
 for path,h in list(P.values())+list(streams.values()):need(sha(ROOT/path)==h,'post-run pin '+path)
 result={'schema':'panama-source-cut-direct-split-diagnostic-v1','status':'experimental-not-selected','counts':counts,'residual':residual,'limitations':['Four-neighbor cut graph and local nearest-line residual side are experimental; no selection or pipeline update.','Graph-unseeded fragments may have ambiguous geometry, especially at a bend or endpoint.','Comparison is against the current stage2 mainland baseline, not historical V7.','The line is selected OSM geometry; input provenance and existing graph sweep remain separate.']}
 with open(OUT,'x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(counts))
if __name__=='__main__':main()

