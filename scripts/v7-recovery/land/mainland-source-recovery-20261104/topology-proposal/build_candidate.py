#!/usr/bin/env python3
"""Local provisional diagnostic, never a build/acceptance. No continent grid read."""
import bisect, hashlib, json, math, sys, time
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'audit/ocean-interfaces-20261103/fresh-water-partition'))
from partition_core import rasterize_barriers
from rle_inputs import RunRasterU32LE
W,H,STEP=131072,54614,360/131072
GEO=BASE/'mainland-source-recovery-20261104/v5-europe-asia-sourcecut-candidate.geojson'
PR=BASE/'physical-direct-output-20261103/rows.u32le'; PU=BASE/'physical-direct-output-20261103/runs.u32le'
CR=BASE/'land-decision-rebuild-20261103/newer-physical-components/rows.u32le';CU=BASE/'land-decision-rebuild-20261103/newer-physical-components/runs.u32le'
PINS={GEO:'b0401ee291aff8b6b5fdaabb4501e7321cbf6c8e9eba9be19cdca6e7ab846382',PR:'6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468',PU:'1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7',CR:'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7',CU:'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'}
# City coordinates come from UNGEGN/United Nations Cartographic Section; proposed
# continent assignment is a draft interpretation, not a claim that UNGEGN decides it.
SEEDS=[('Europe','Paris',2.47842902664,48.8090362616,'https://ungegn.un.org/dashboard/cities/details?id=145'),('Asia','Beijing',116.326721268,39.9248428735,'https://ungegn.un.org/dashboard/cities/details?crM49=156&id=130'),('North America','Panama City',-79.4413147673,9.06267069615,'https://ungegn.un.org/dashboard/cities/details?id=191'),('South America','Bogota',-74.0931168302,4.5802522049,'https://ungegn.un.org/dashboard/cities/details?id=208'),('Africa','Cairo',31.3001002622,30.0918064966,'https://ungegn.un.org/dashboard/cities/details?id=71')]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def xy(lon,lat):return math.floor((lon+180)/STEP),math.floor((90-lat)/STEP)
def main():
 for p,h in PINS.items():
  if sha(p)!=h:raise ValueError('pin mismatch '+str(p))
 offsets=np.memmap(CR,dtype='<u4',mode='r');runs=np.memmap(CU,dtype='<u4',mode='r').reshape(-1,3)
 def root(x,y):
  r=runs[offsets[y]:offsets[y+1]]; i=np.searchsorted(r[:,1],x,side='right')
  return int(r[i,2]) if i<len(r) and r[i,0]<=x<r[i,1] else None
 def mask_code(raster,x,y):
  if not (0<=x<W and 0<=y<H):return None
  row=raster.row(y);i=bisect.bisect_right([e for e,c in row],x);return row[i][1]
 src=json.loads(GEO.read_bytes());out={'schema':'mainland-cut-topology-research-v1','status':'local-unreviewed-not-partition','pins':{str(p.relative_to(BASE)):h for p,h in PINS.items()},'seed_proposals':[], 'routes':[], 'warning':'Four-neighbor edge blocking and left-of-oriented-line vertex tie are exploratory algorithm proposals from existing ocean barrier code, not approved mainland tie/closure decisions. Source points do not independently prove continental affiliation. No ocean/V2/V6 assignment used.'}
 with RunRasterU32LE(PR,PU,W,H) as r:
  for side,name,lon,lat,url in SEEDS:
   x,y=xy(lon,lat);out['seed_proposals'].append({'side':side,'city':name,'source_lonlat':[lon,lat],'source_url':url,'grid_x':x,'grid_y':y,'grid_center_lonlat':[-180+(x+.5)*STEP,90-(y+.5)*STEP],'physical_code':mask_code(r,x,y),'component_id':root(x,y),'status':'draft-source-point-label-not-reviewed'})
  for f in src['features']:
   fid=f['properties']['cut_id'];points=f['geometry']['coordinates'];ends=[]
   for lon,lat in (points[0],points[-1]):
    x,y=xy(lon,lat);cnt={}
    for dy in range(-3,4):
     for dx in range(-3,4):
      c=mask_code(r,x+dx,y+dy);cnt[str(c)]=cnt.get(str(c),0)+1
    ends.append({'lonlat':[lon,lat],'grid_xy':[x,y],'physical_code':mask_code(r,x,y),'component_id':root(x,y),'physical_codes_7x7':cnt})
   path=[((lon+180)/STEP,(90-lat)/STEP) for lon,lat in points]
   cuts=rasterize_barriers([path],W,H)
   count=sum(map(len,cuts.horizontal.values()))+sum(map(len,cuts.vertical.values()))
   file=OUT/(fid+'.candidate-edges.u32le');cuts.write_u32le(file)
   out['routes'].append({'feature_id':fid,'vertex_count':len(points),'endpoints':ends,'edge_file':str(file),'edge_sha256':sha(file),'edge_count':count,'edge_kind':'uint32 triples kind,row,x; 0 horizontal, 1 vertical','status':'exploratory-not-reviewed'})
  for p,h in PINS.items():
   if sha(p)!=h:raise ValueError('input changed '+str(p))
 file=OUT/'topology-proposal.json';file.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
