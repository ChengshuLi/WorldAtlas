"""Research-only interval certificates for WGS84 nearest-center classification.

A class distance is 1-Lipschitz in geodesic distance. At each interval's
midpoint, prove the selected class beats each other and every omitted center by
2*the maximum distance to a center of the interval. Otherwise split or use
point classifier. Experimental floating point guard is NOT independently proven.
"""
import math
import numpy as np
import shared_nearest as s
MAX_RADIUS=s.A/(1-s.F)

def classify_row(y,intervals,bounds,width,height,step,pairs,tol,indexes,*,leaf=16,point_classifier=None):
 if any(type(z) is not int for z in (y,width,height,leaf)) or width<=0 or height<=0 or not 0<=y<height or leaf<1:raise ValueError('invalid grid, row, or leaf')
 if isinstance(step,(bool,np.bool_)) or isinstance(tol,(bool,np.bool_)) or not math.isfinite(step) or step<=0 or abs(step*width-360)>1e-8 or not math.isfinite(tol) or tol<0:raise ValueError('invalid step or tolerance')
 if not isinstance(bounds,(tuple,list)) or len(bounds)!=4 or any(type(z) is not int for z in bounds):raise ValueError('invalid crop bounds')
 x0,x1,y0,y1=bounds
 if not (0<x1-x0<=width and 0<=y0<y1<=height):raise ValueError('invalid crop bounds')
 if not isinstance(intervals,(tuple,list)) or any(not isinstance(z,(tuple,list)) or len(z)!=2 or any(type(x) is not int for x in z) for z in intervals):raise ValueError('spans require integer boundaries')
 intervals=sorted(intervals)
 if any(a<0 or b>width or a>=b for a,b in intervals) or any(a[1]>b[0] for a,b in zip(intervals,intervals[1:])):raise ValueError('invalid spans')
 if not isinstance(pairs,(tuple,list)) or len(pairs)<2 or any(not isinstance(p,(tuple,list)) or len(p)!=3 or type(p[1]) is not int or type(p[2]) is not int for p in pairs):raise ValueError('invalid participant classes')
 if len({p[1] for p in pairs})!=len(pairs) or len({p[2] for p in pairs})!=len(pairs):raise ValueError('duplicate participant classes')
 if point_classifier is not None and not callable(point_classifier):raise ValueError('invalid point classifier')
 lat=90-(y+.5)*step
 if not -90<=lat<=90:raise ValueError('invalid latitude')
 missing=any(code not in indexes for _,code,_ in pairs)
 if missing and point_classifier is None:raise ValueError('missing participant shore; full-shore classifier required')
 # Each canonical span must fit the crop as one translated interval.
 outside=False
 for a,b in intervals:
  k=math.ceil((x0-a-.5)/width)
  outside |= (y<y0 or y>=y1 or a+.5+k*width<x0 or b-.5+k*width>x1)
 needs_full=missing or outside
 if needs_full and point_classifier is None:raise ValueError('full-shore classifier required')
 def query(latitudes,longitudes):
  result=(point_classifier(latitudes,longitudes) if point_classifier is not None else s.classify(latitudes,longitudes,bounds,width,height,step,pairs,tol,indexes))
  if not isinstance(result,(tuple,list)) or len(result)!=3:raise ValueError('invalid point result')
  bounded,exact=result[1:]
  if any(not isinstance(v,(int,np.integer)) or isinstance(v,(bool,np.bool_)) or v<0 for v in (bounded,exact)) or bounded+exact!=len(latitudes):raise ValueError('invalid point accounting')
  z=np.asarray(result[0])
  if z.ndim!=1 or len(z)!=len(latitudes) or not np.issubdtype(z.dtype,np.integer) or np.any(~np.isin(z,[p[2] for p in pairs])):raise ValueError('invalid point codes')
  return z,int(bounded),int(exact)
 active=np.array(intervals,dtype=np.int64).reshape(-1,2);done=[];certified=split=leafcells=leafbounded=leafexact=0
 if needs_full:
  for a,b in intervals:
   for st in range(a,b,5000):
    en=min(st+5000,b);xs=np.arange(st,en,dtype=float);codes,nb,ne=query(np.full(len(xs),lat),-180+(xs+.5)*step);leafbounded+=nb;leafexact+=ne
    cuts=np.r_[0,np.flatnonzero(np.diff(codes)!=0)+1,len(codes)]
    done.extend((st+int(i),st+int(j),int(codes[i])) for i,j in zip(cuts[:-1],cuts[1:]));leafcells+=en-st
  active=np.empty((0,2),dtype=np.int64)
 while len(active):
  middle=(active[:,0]+active[:,1]-1)//2
  lon=-180+(middle+.5)*step;lats=np.full(len(middle),lat); points=s.unit(lats,lon)
  extent=MAX_RADIUS*math.cos(math.radians(lat))*np.deg2rad(step)*np.maximum(middle-active[:,0],active[:,1]-1-middle)+.01
  lowers,best,upper=s.nearest_class_bounds(lats,lon,points,pairs,indexes)
  lowers[np.arange(len(active)),best]=np.inf
  boundary=s.boundary_lower(lats,lon,bounds,width,height,step)
  good=(upper+2*extent+tol<lowers.min(axis=1))&(upper+2*extent+tol<boundary)
  for i in np.flatnonzero(good):
   a,b=map(int,active[i]);done.append((a,b,pairs[int(best[i])][2]));certified+=b-a
  todo=active[~good];small=todo[:,1]-todo[:,0]<=leaf
  leaves=todo[small]
  if len(leaves):
   leaves=leaves[np.argsort(leaves[:,0])]
   sizes=leaves[:,1]-leaves[:,0]
   offsets=np.repeat(np.cumsum(sizes)-sizes,sizes)
   xs=np.repeat(leaves[:,0],sizes)+np.arange(int(sizes.sum()))-offsets
   codes,nb,ne=query(np.full(len(xs),lat),-180+(xs+.5)*step)
   leafbounded+=nb;leafexact+=ne;leafcells+=len(xs)
   cuts=np.r_[0,np.flatnonzero((np.diff(xs)>1)|(codes[1:]!=codes[:-1]))+1,len(xs)]
   done.extend((int(xs[i]),int(xs[j-1])+1,int(codes[i])) for i,j in zip(cuts[:-1],cuts[1:]))
  parts=todo[~small];split+=len(parts)
  mid=(parts[:,0]+parts[:,1])//2
  active=np.concatenate((np.column_stack((parts[:,0],mid)),np.column_stack((mid,parts[:,1]))),axis=0)
 done.sort();merged=[]
 for a,b,c in done:
  if merged and merged[-1][1]==a and merged[-1][2]==c:merged[-1]=(merged[-1][0],b,c)
  else:merged.append((a,b,c))
 if leafbounded+leafexact!=leafcells or certified+leafcells!=sum(b-a for a,b in intervals):raise RuntimeError('assignment accounting mismatch')
 return merged,{'certified_cells':certified,'leaf_cells':leafcells,'split_nodes':split,'bounded_cells':certified+leafbounded,'exact_cells':leafexact}
