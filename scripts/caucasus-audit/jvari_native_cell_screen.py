import json,math,hashlib
import numpy as np
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,polygonize
old=LineString(json.load(open('jvari-current-cut-research.json'))['coordinates']);new=LineString(json.load(open('jvari-jaxa-cut-research.json'))['coordinates']);faces=list(polygonize(unary_union([old,new])));shape=unary_union(faces);print('faces',len(faces),'area_square_degrees',shape.area)
rows=np.fromfile('/tmp/ural-draft82/physical-rows.u32le',dtype='<u4');runs=np.memmap('/tmp/ural-draft82/physical-runs.u32le',dtype='<u4',mode='r').reshape(-1,2);step=360/131072;lo,bot,hi,top=shape.bounds;cells=[]
for r in range(max(0,int((90-top)/step)-1),int((90-bot)/step)+2):
 data=runs[rows[r]:rows[r+1]]
 for c in range(int((lo+180)/step)-1,int((hi+180)/step)+2):
  if not shape.contains(Point(-180+(c+.5)*step,90-(r+.5)*step)):continue
  typ=int(data[np.searchsorted(data[:,0],c,side='right'),1])
  if typ==17:cells.append([r,c])
  elif typ!=1:raise ValueError('unexpected cell type')
print('draft163 land centers',len(cells),'cells',cells);json.dump({'physical_mask':'draft163 historical stand-in','land_centers':cells,'bounded_faces':len(faces)},open('jvari-jaxa-impact-draft163-research.json','w'))
