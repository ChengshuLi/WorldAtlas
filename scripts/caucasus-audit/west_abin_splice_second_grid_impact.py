"""Exploratory SRTM versus source raster impact, no selected geography."""
import json,math,gzip
from collections import Counter
import numpy as np
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,polygonize
from shapely.strtree import STRtree
from geodesic_line import GeodesicLine
source=json.load(open('caucasus-line.json'))['coordinates'];candidate=json.load(open('west-abin-splice-second-cut-research.json'))['coordinates']
s=LineString(source);c=LineString(candidate);polys=list(polygonize(unary_union([s,c])));print('bounded faces',len(polys),flush=True)
if not polys:raise ValueError('no closed faces')
tree=STRtree(polys);bbox=unary_union(polys).bounds;step=360/131072
source_line=GeodesicLine(source);candidate_line=GeodesicLine(candidate)
rows=np.fromfile('draft93/candidate-rows.u32le',dtype='<u4');runs=np.memmap('draft93/candidate-runs.u32le',dtype='<u4',mode='r').reshape(-1,2)
v7rows=np.frombuffer(gzip.open('v7-rows.gz','rb').read(),dtype='<u4');counts=Counter();cells=[]
with gzip.open('v7-runs.gz','rb') as stream:
 for row in range(math.floor((90-bbox[3])/step)-1,math.ceil((90-bbox[1])/step)+1):
  x=runs[rows[row]:rows[row+1]];start,end=int(v7rows[row]),int(v7rows[row+1]);stream.seek(start*8);v7=np.frombuffer(stream.read((end-start)*8),dtype='<u4').reshape(-1,2)
  for col in range(math.floor((bbox[0]+180)/step)-1,math.ceil((bbox[2]+180)/step)+1):
   lon=-180+(col+.5)*step;lat=90-(row+.5)*step;p=Point(lon,lat)
   if not any(polys[int(i)].contains(p) for i in tree.query(p)):continue
   old=int(x[np.searchsorted(x[:,0],col,side='right'),1]);ref=int(v7[np.searchsorted(v7[:,0],col,side='right'),1])
   a=source_line.closest((lon,lat));b=candidate_line.closest((lon,lat));ss='ambiguous' if a['ambiguous'] else source_line.side((lon,lat),a['station_m']);cs='ambiguous' if b['ambiguous'] else candidate_line.side((lon,lat),b['station_m'])
   counts[(old,ref,ss,cs)]+=1;cells.append([row,col,old,ref,ss,cs])
print('faces cell_count',len(cells),'counts',dict(counts),flush=True)
json.dump({'spans_bounded_face_count':len(polys),'cells':cells},open('west-abin-splice-second-hypothetical-impact.json','w'))
