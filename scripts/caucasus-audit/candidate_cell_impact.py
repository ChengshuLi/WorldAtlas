"""Count native land-centre changes inside candidate/source bounded faces."""
import sys,json,math,hashlib
import numpy as np
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,polygonize
old=LineString(json.load(open(sys.argv[1]))['coordinates']);new=LineString(json.load(open(sys.argv[2]))['coordinates']);faces=list(polygonize(unary_union([old,new])));p=unary_union(faces)
if p.is_empty:raise ValueError('no bounded differences')
rowfile='/tmp/ural-draft82/physical-rows.u32le';runfile='/tmp/ural-draft82/physical-runs.u32le';expected=('6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468','1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7')
for f,want in zip((rowfile,runfile),expected):
 h=hashlib.sha256()
 with open(f,'rb') as stream:
  for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
 if h.hexdigest()!=want:raise ValueError('unexpected physical input')
rows=np.fromfile(rowfile,dtype='<u4');runs=np.memmap(runfile,dtype='<u4',mode='r').reshape(-1,2);step=360/131072;lo,bot,hi,top=p.bounds;land=[];water=0
for r in range(max(0,int((90-top)/step)-1),int((90-bot)/step)+2):
 a=runs[rows[r]:rows[r+1]]
 for c in range(int((lo+180)/step)-1,int((hi+180)/step)+2):
  if not p.contains(Point(-180+(c+.5)*step,90-(r+.5)*step)):continue
  typ=int(a[np.searchsorted(a[:,0],c,side='right'),1])
  if typ==17:land.append([r,c])
  elif typ==1:water+=1
  else:raise ValueError('unknown physical type')
print('faces',len(faces),'land_centers',len(land),'water_centers',water);json.dump({'mask':'historical draft163','rows_sha256':expected[0],'runs_sha256':expected[1],'land_centers':land,'water_centers':water,'faces':len(faces)},open(sys.argv[3],'w'))
