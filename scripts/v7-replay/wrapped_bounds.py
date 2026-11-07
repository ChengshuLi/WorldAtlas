"""Conservative circular envelopes and fail-closed nearest-shore fallback.
Each Polygon component's full ordinary longitude projection is retained, so
actual planar edges are never reinterpreted across the antimeridian. The optional wrapped-index path keeps exact WGS84 classification and falls back
to a streamed full crop whenever omitted shores cannot be certified.
"""
import math

def _pairs(x):
 if isinstance(x,(list,tuple)) and len(x)>=2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in x[:2]):
  lon,lat=map(float,x[:2]);eps=1e-10
  if not (math.isfinite(lon) and math.isfinite(lat) and -180-eps<=lon<=180+eps and -90-eps<=lat<=90+eps):raise ValueError('invalid coordinates')
  yield max(-180.,min(180.,lon)),max(-90.,min(90.,lat))
 elif isinstance(x,(list,tuple)):
  for a in x:yield from _pairs(a)
 else:raise ValueError('invalid coordinates')

def wrapped_grid_bounds(feature,width,height,step):
 """Return a conservative unwrapped grid rectangle and canonical x windows."""
 if type(width) is not int or type(height) is not int or width<=0 or height<=0 or not math.isfinite(step) or step<=0 or abs(width*step-360)>1e-8:raise ValueError('invalid grid')
 g=feature.get('geometry',feature);typ=g.get('type');coords=g.get('coordinates')
 if typ=='Polygon':polys=[coords]
 elif typ=='MultiPolygon':polys=coords
 else:raise ValueError('expected Polygon or MultiPolygon')
 if not isinstance(polys,(tuple,list)) or not polys:raise ValueError('empty geometry')
 spans=[];minlat=90.;maxlat=-90.
 for poly in polys:
  p=list(_pairs(poly))
  if not p:raise ValueError('empty polygon')
  spans.append((min(z[0] for z in p)+180.,max(z[0] for z in p)+180.));minlat=min(minlat,min(z[1] for z in p));maxlat=max(maxlat,max(z[1] for z in p))
 spans.sort();merged=[]
 for a,b in spans:
  if not merged or a>merged[-1][1]:merged.append([a,b])
  else:merged[-1][1]=max(merged[-1][1],b)
 gaps=[]
 for i,(_,b) in enumerate(merged):
  a2=merged[(i+1)%len(merged)][0]+(360. if i==len(merged)-1 else 0.);gaps.append((a2-b,i))
 gap,i=max(gaps,key=lambda z:(z[0],-z[1]))
 if gap<=0:x0,x1=0,width
 else:
  start=merged[(i+1)%len(merged)][0];end=merged[i][1]
  if end<start:end+=360.
  x0=max(0,min(width-1,math.floor(start/step)));x1=math.ceil(end/step)
  if x1-x0>=width:x0,x1=0,width
 y0=max(0,math.floor((90-maxlat)/step));y1=min(height,math.ceil((90-minlat)/step))
 if not 0<x1-x0<=width or not 0<=y0<y1<=height:raise ValueError('empty grid intersection')
 windows=[(x0,x1)] if x1<=width else [(0,x1-width),(x0,width)]
 return (x0,x1,y0,y1),tuple(windows)

class StreamedWrappedClassifier:
 """Use certified WGS84 narrow results, scanning every full shore on fallback."""
 def __init__(self, classifier, stream_one, narrow_bounds, full_bounds, width, height, step, pairs, tolerance, narrow_indexes, full_blocks):
  self.classifier=classifier;self.stream_one=stream_one;self.narrow_bounds=narrow_bounds;self.full_bounds=full_bounds;self.width=width;self.height=height;self.step=step;self.pairs=pairs;self.tolerance=tolerance;self.narrow=narrow_indexes;self.full_blocks=full_blocks;self.narrow_cells=0;self.fallback_cells=0
 def classify(self,lat,lon):
  import numpy as np
  recoverable=('query lies outside crop','crop cannot certify nearest shore; increase halo','crop cannot certify coastal band; increase halo','crop cannot certify; increase halo','missing participant shore')
  if self.narrow:
   try:
    result=self.classifier(lat,lon,self.narrow_bounds,self.width,self.height,self.step,self.pairs,self.tolerance,self.narrow);self.narrow_cells+=len(lat);return result
   except ValueError as exc:
    if str(exc) not in recoverable:raise
  out=np.empty(len(lat),dtype='u1');certified=exact=0
  for i in range(len(lat)):
   try:
    if not self.narrow:raise ValueError('missing participant shore')
    z,nc,ne=self.classifier(lat[i:i+1],lon[i:i+1],self.narrow_bounds,self.width,self.height,self.step,self.pairs,self.tolerance,self.narrow);out[i]=z[0];certified+=nc;exact+=ne;self.narrow_cells+=1
   except ValueError as exc:
    if str(exc) not in recoverable:raise
    out[i]=self.stream_one(float(lat[i]),float(lon[i]),self.full_bounds,self.width,self.height,self.step,self.pairs,self.tolerance,self.full_blocks,self.narrow);exact+=1;self.fallback_cells+=1
  return out,certified,exact

def shore_blocks(shared,physical,land,bounds,width,height,step,code,rows_per_chunk=64):
 """Enumerate the complete full crop in row chunks with original neighbor halos."""
 if type(rows_per_chunk) is not int or rows_per_chunk<=0:raise ValueError('invalid row chunk')
 xa,xb,ya,yb=bounds
 for first in range(ya,yb,rows_per_chunk):
  try:
   yield shared.centers_for_crop(physical,land,(xa,xb,first,min(first+rows_per_chunk,yb)),width,height,step,[code])
  except ValueError as exc:
   if str(exc)!='no participant shorelines in crop':raise

def baseline_shore_order(centers,full_bounds,width,step):
 """Match full-crop row/column enumeration before constructing a wrapped tree."""
 import numpy as np
 lon=centers['lon'];lat=centers['lat']
 if lon.shape!=lat.shape or lat.ndim!=1 or width<=0 or not math.isfinite(step) or step<=0:raise ValueError('invalid shoreline centers')
 cols=np.rint((lon+180)/step-.5).astype(np.int64)%width
 offset=(cols-full_bounds[0])%width
 order=np.lexsort((offset,-lat))
 return {key:value[order] for key,value in centers.items()}
