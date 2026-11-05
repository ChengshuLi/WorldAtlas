#!/usr/bin/python3
"""Fresh-source Panama-only graph experiment. Never alters current stage2.

Uses selected OSM line and current physical-component witness; it does not read
or use the stored exterior closure or V7. Nearest-line residual sides are an
experimental hypothesis and any ambiguous point stops the run.
"""
import hashlib,json,math,os,struct,sys
from array import array
from pathlib import Path
import numpy as np
from osgeo import ogr,gdal
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'mainland-source-recovery-20261104/topology-proposal'))
sys.path.insert(0,str(ROOT/'audit/ocean-interfaces-20261103/fresh-water-partition'))
from build_partition import partition
from partition_core import rasterize_barriers
from compare import nearest_side
W,H,STEP=131072,54614,360/131072
PINS={
 'actual-neon-boundary-export-20261104/v6/snapshot.json':'2de24700528fbf2d44acc4b67c17f6fe3b9bb594eba0add5c940e5d1cd569882',
 'fresh-witness-output-20261104/resolution.json':'27ec973caf3eedb267e2c0277a710dceef04254075f81b689f5762d513d88ea5',
 'fresh-components-output-20261104/rows.u32le':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7',
 'fresh-components-output-20261104/runs.u32le':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'}
def need(v,m):
 if not v:raise ValueError(m)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
class TripleRows:
 """Read checked uint32 triple rows with bounded per-row memory."""
 def __init__(self,rows_path,spans_path,height):
  self.offsets=np.fromfile(rows_path,dtype='<u4')
  self.fd=os.open(spans_path,os.O_RDONLY)
  try:
   need(len(self.offsets)==height+1 and self.offsets[0]==0 and np.all(self.offsets[1:]>=self.offsets[:-1]),'invalid triple row offsets')
   need(os.fstat(self.fd).st_size==int(self.offsets[-1])*12,'invalid triple stream size')
  except BaseException:
   os.close(self.fd);self.fd=None;raise
 def row(self,y):
  need(type(y) is int and 0<=y<len(self.offsets)-1,'row out of range')
  a,b=map(int,self.offsets[y:y+2]);data=os.pread(self.fd,(b-a)*12,a*12)
  need(len(data)==(b-a)*12,'short triple row')
  return np.frombuffer(data,dtype='<u4').reshape(-1,3)
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None
 def __del__(self):
  if getattr(self,'fd',None) is not None:self.close()
def reject_invalid_line(line):
 need(isinstance(line,list) and len(line)>=2 and all(isinstance(p,list) and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in p) and -180<=p[0]<=180 and -90<=p[1]<=90 for p in line),'invalid source line')
 need(all(a!=b and abs(a[0]-b[0])<=180 for a,b in zip(line,line[1:])),'degenerate or antimeridian source line')
 geom=ogr.CreateGeometryFromJson(json.dumps({'type':'LineString','coordinates':line}));need(geom is not None and geom.IsSimple(),'self-intersecting source line')
def reject_center_hits(path,width,height,eps=1e-9):
 # In grid coordinates, fail rather than apply the inherited left-side tie.
 for (x0,y0),(x1,y1) in zip(path,path[1:]):
  dx=x1-x0
  if abs(dx)<=eps:
   ix=round(x0-.5);near=abs(x0-(ix+.5))<=eps and abs(x1-(ix+.5))<=eps
   first=max(0,math.ceil(min(y0,y1)-.5-eps));last=min(height-1,math.floor(max(y0,y1)-.5+eps))
   if near and 0<=ix<width and first<=last:raise ValueError('source line intersects a cell center')
  else:
   first=max(0,math.ceil(min(x0,x1)-.5-eps));last=min(width-1,math.floor(max(x0,x1)-.5+eps))
   for ix in range(first,last+1):
    t=(ix+.5-x0)/dx
    if -eps<=t<=1+eps:
     y=y0+t*(y1-y0);iy=round(y-.5)
     if 0<=iy<height and abs(y-(iy+.5))<=eps:raise ValueError('source line intersects a cell center')
def reject_terminal_near_land(path,width,height,eligible,eps=1e-9):
 # An endpoint within one graph-edge length of a land center could truncate a
 # land-to-land cut. Fail closed instead of extrapolating the boundary.
 for x,y in (path[0],path[-1]):
  for iy in range(max(0,math.floor(y)-2),min(height,math.floor(y)+3)):
   for ix in range(max(0,math.floor(x)-2),min(width,math.floor(x)+3)):
    if (ix+.5-x)**2+(iy+.5-y)**2 <= (1+eps)**2 and eligible(ix,iy):
     raise ValueError('source endpoint too close to selected land')
def select_witnesses(witnesses,xy,eligible,side):
 # Region witnesses may be in water on the physical grid. Use those that land
 # on the selected root as graph seeds; use only unambiguous oriented sides to
 # check the mapping, and never use an ambiguous endpoint as evidence.
 need(isinstance(witnesses,list) and witnesses,'missing witnesses')
 seeds={};checks={20:[],21:[]};oriented={20:0,21:0}
 for w in witnesses:
  need(isinstance(w,dict) and set(w)=={'lon','lat','inside'} and type(w['inside']) is bool,'invalid witness')
  try:lon,lat=float(w['lon']),float(w['lat'])
  except (TypeError,ValueError):raise ValueError('invalid witness coordinates') from None
  need(math.isfinite(lon) and math.isfinite(lat) and -180<=lon<=180 and -90<=lat<=90,'invalid witness coordinates')
  code,expected=(20,1) if w['inside'] else (21,-1)
  sign=side(lon,lat);need(sign in (-1,0,1),'invalid witness side')
  if sign:
   need(sign==expected,'conflicting witness orientation');oriented[code]+=1
  cell=xy(w)
  if eligible(*cell):
   checks[code].append(cell);seeds.setdefault(code,cell)
 need(set(seeds)=={20,21},'missing eligible side witness')
 need(all(oriented.values()),'missing unambiguous orientation witness')
 return seeds,checks,oriented

def verify_witness_assignments(stream,checks):
 for code,cells in checks.items():
  for x,y in cells:
   row=stream.row(y);i=int(np.searchsorted(row[:,1],x,side='right'))
   need(i<len(row) and int(row[i,0])<=x<int(row[i,1]) and int(row[i,2])==code,'witness assignment mismatch')
def resolve_fragments(groups,cuts,line,west,north,step,width,height,eligible,max_cells=100000,side_codes=(20,21)):
 need(len(side_codes)==2 and side_codes[0]!=side_codes[1],'invalid side codes')
 # A cut-created fragment must touch the cut, have one unambiguous side,
 # and never use the finite line's endpoint as an extrapolation.
 result={};total=0;seen=set()
 for group,points in groups.items():
  need(points,'empty fragment');total+=len(points);need(total<=max_cells,'residual resource cap');need(len(set(points))==len(points) and not seen.intersection(points),'duplicate fragment cell');seen.update(points)
  touched=False;signs=set()
  for x,y in points:
   need(type(x) is int and type(y) is int and 0<=x<width and 0<=y<height,'invalid fragment cell')
   touched |= ((x<width-1 and x in cuts.horizontal.get(y,()) and eligible(x+1,y)) or (x>0 and x-1 in cuts.horizontal.get(y,()) and eligible(x-1,y)) or (y<height-1 and x in cuts.vertical.get(y,()) and eligible(x,y+1)) or (y>0 and x in cuts.vertical.get(y-1,()) and eligible(x,y-1)) or ((x==0 or x==width-1) and y in cuts.wrap and eligible(width-1 if x==0 else 0,y)))
   sign,_=nearest_side(west+(x+.5)*step,north-(y+.5)*step,line);need(sign!=0,'ambiguous residual side');signs.add(sign)
  need(touched,'disconnected fragment does not touch source cut');need(len(signs)==1,'fragment spans conflicting line sides');result[group]=side_codes[0] if next(iter(signs))>0 else side_codes[1]
 return result
def main():
 raise RuntimeError('planar nearest-side method retired; a reviewed WGS84 replacement is required')
 out=ROOT/'panama-direct-split-fresh-output-20261104';need(not out.exists(),'output exists')
 for p,h in PINS.items():need(sha(ROOT/p)==h,'input hash mismatch '+p)
 snap=json.loads((ROOT/'actual-neon-boundary-export-20261104/v6/snapshot.json').read_bytes());w=json.loads((ROOT/'fresh-witness-output-20261104/resolution.json').read_bytes());b=[x for x in snap['mainland_boundaries'] if x['boundary_id']=='panama_colombia_osm_admin_boundary' and x['execution_status']=='selected_for_research'];need(len(b)==1 and b[0]['geometry_sha256']=='cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17','selected boundary')
 need(w['snapshot_sha256']==PINS['actual-neon-boundary-export-20261104/v6/snapshot.json'] and w['decision_revision']==snap['decision_revision']['id'] and b[0]['method']=='stored_linestring_v1','selected revision lineage')
 line=[[float(v) for v in p] for p in b[0]['geometry']['coordinates']];need(len(line)==5254 and all(len(p)==2 and all(math.isfinite(v) for v in p) for p in line),'boundary shape')
 norm=json.dumps({'type':'LineString','coordinates':line},sort_keys=True,separators=(',',':'),allow_nan=False).encode();need(hashlib.sha256(norm).hexdigest()==b[0]['geometry_sha256'],'boundary geometry hash')
 g=[x for x in w['groups'] if x['group_id']=='mainland-americas'];need(len(g)==1,'mainland witness');root=g[0]['component_id_current_generation_only'];need(w['input_sha256']['component_rows']==PINS['fresh-components-output-20261104/rows.u32le'] and w['input_sha256']['component_runs']==PINS['fresh-components-output-20261104/runs.u32le'],'component lineage')
 region=[x for x in snap['seed_regions'] if x['region_id']=='north_america_mainland_region_v1' and x['execution_status']=='selected_for_research'];need(len(region)==1,'side witnesses');witnesses=region[0]['witnesses'];
 def xy(x):return math.floor((float(x['lon'])+180)/STEP),math.floor((90-float(x['lat']))/STEP)
 components=TripleRows(ROOT/'fresh-components-output-20261104/rows.u32le',ROOT/'fresh-components-output-20261104/runs.u32le',H)
 def rows(y):
  a=components.row(y);return [(int(x),int(z)) for x,z,k in a if int(k)==root]
 def eligible(x,y):
  row=components.row(y);i=int(np.searchsorted(row[:,1],x,side='right'));return i<len(row) and int(row[i,0])<=x<int(row[i,1]) and int(row[i,2])==root
 seeds,witness_checks,witness_oriented=select_witnesses(witnesses,xy,eligible,lambda lon,lat:nearest_side(lon,lat,line)[0])
 reject_invalid_line(line);paths=[[[((lon+180)/STEP),((90-lat)/STEP)] for lon,lat in line]];reject_center_hits(paths[0],W,H);reject_terminal_near_land(paths[0],W,H,eligible);cuts=rasterize_barriers(paths,W,H)
 result=partition(rows,W,H,cuts,seeds,out)
 graph=TripleRows(out/'partition-rows.u32le',out/'partition-spans.u32le',H);remaining=TripleRows(out/'residual-rows.u32le',out/'residual-spans.u32le',H)
 groups={};residual=0
 for y in np.flatnonzero(remaining.offsets[1:]!=remaining.offsets[:-1]):
  for a,z,group in remaining.row(int(y)):
   need(0<=int(a)<int(z)<=W,'invalid residual span');residual+=int(z)-int(a);need(residual<=100000,'residual resource cap');groups.setdefault(int(group),[]).extend((x,int(y)) for x in range(int(a),int(z)))
 need(residual*max(1,len(line)-1)<=10000000,'residual search compute budget')
 fragment_codes=resolve_fragments(groups,cuts,line,-180,90,STEP,W,H,eligible)
 offsets_out=array('I',[0]);count=0
 with (out/'direct-spans.u32le').open('xb') as f:
  for y in range(H):
   parts=[(int(a),int(z),int(k)) for a,z,k in graph.row(y)]
   for a,z,group in remaining.row(y):parts.append((int(a),int(z),fragment_codes[int(group)]))
   parts.sort();merged=[]
   for a,z,k in parts:
    need(0<=a<z<=W and (not merged or merged[-1][1]<=a),'overlapping output')
    if merged and merged[-1][1]==a and merged[-1][2]==k:merged[-1]=(merged[-1][0],z,k)
    else:merged.append((a,z,k))
   expected=sum(z-a for a,z in rows(y));need(sum(z-a for a,z,_ in merged)==expected,'component coverage')
   for a,z,k in merged:f.write(struct.pack('<III',a,z,k))
   count+=len(merged);need(count<=0xffffffff,'offset overflow');offsets_out.append(count)
 np.asarray(offsets_out,dtype='<u4').tofile(out/'direct-rows.u32le');components.close();graph.close();remaining.close()
 direct=TripleRows(out/'direct-rows.u32le',out/'direct-spans.u32le',H);verify_witness_assignments(direct,witness_checks);direct.close()
 for p,h in PINS.items():need(sha(ROOT/p)==h,'input changed '+p)
 report={'schema':'panama-direct-source-split-prototype-v1','status':'unselected-research','boundary_sha256':b[0]['geometry_sha256'],'snapshot_sha256':PINS['actual-neon-boundary-export-20261104/v6/snapshot.json'],'inputs_sha256':PINS,'component_id_current_generation_only':root,'runtime':{'gdal':gdal.VersionInfo('RELEASE_NAME'),'numpy':np.__version__},'graph':result,'witnesses':{'eligible_cells_by_code':{str(k):len(v) for k,v in witness_checks.items()},'unambiguous_orientation_by_code':{str(k):v for k,v in witness_oriented.items()}},'residual_cells_assigned_by_experimental_side':residual,'direct_rows_sha256':sha(out/'direct-rows.u32le'),'direct_spans_sha256':sha(out/'direct-spans.u32le'),'limitations':['Land-to-land cut-touching, internally consistent nearest-segment side is experimental, not a proven general partition.','Boundary-center and finite-endpoint ties must fail closed; no historical V7 input or closure is used.','External guard, independent input/coverage audit and whole-mainland comparison required.']}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'spans':count,'residual':residual,'cells':result['selected_cells']}))
if __name__=='__main__':main()

