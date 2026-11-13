"""Exact WGS84 minimum between two discrete horizontal grid runs.

No land policy. Enumerate attainable *longitude gaps*, not all cell pairs.
"""
import math,numpy as np
from map_build.core.geodesy import GEOD, MIN_RADIUS, CUSHION_M

def inverse(lat1,lat2,gaps,step):
 gaps=np.asarray(gaps,dtype=np.float64);lon=gaps*step
 if len(gaps)==1:
  return np.asarray([GEOD.inv(0,float(lat1),float(lon[0]),float(lat2))[2]])
 return np.asarray(GEOD.inv(np.zeros(len(gaps)),np.full(len(gaps),lat1),lon,np.full(len(gaps),lat2))[2])

def run_pair(y,a,b,yy,c,d,width,north=90.,incumbent=math.inf,tol=0.):
 if not (type(width) is int and width>=2 and all(type(x) is int for x in (y,a,b,yy,c,d)) and 0<=a<b<=width and 0<=c<d<=width and y>=0 and yy>=0 and 0<=tol and math.isfinite(tol) and incumbent>=0):raise ValueError('invalid runs')
 step=360/width;lat1=north-(y+.5)*step;lat2=north-(yy+.5)*step
 if abs(lat1)>90 or abs(lat2)>90:raise ValueError('invalid latitude')
 diffs=np.arange(c-(b-1), (d-1)-a+1,dtype=np.int64);mod=diffs%width;gaps=np.unique(np.minimum(mod,width-mod));dl=np.deg2rad(gaps*step);p1=math.radians(lat1);p2=math.radians(lat2)
 xx=math.cos(p2)*np.sin(dl);yy0=math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*np.cos(dl);dot=math.sin(p1)*math.sin(p2)+math.cos(p1)*math.cos(p2)*np.cos(dl);angles=np.arctan2(np.hypot(xx,yy0),dot)
 if not math.isfinite(incumbent):
  j=int(np.argmin(angles));incumbent=float(inverse(lat1,lat2,[gaps[j]],step)[0])
 keep=np.flatnonzero(angles*MIN_RADIUS<=incumbent+tol+CUSHION_M)
 if not len(keep):return None,{'attainable_gaps':len(gaps),'exact_gaps':0}
 ds=inverse(lat1,lat2,gaps[keep],step)
 return float(ds.min()),{'attainable_gaps':len(gaps),'exact_gaps':len(keep)}

def run_pairs_batch(y,a,b,records,width,north=90.,incumbent=math.inf,tol=0.):
 """Evaluate each seed run at its smallest attainable wrapped longitude gap.

 On an ellipsoid of revolution the surface metric is E(lat)dlat² +
 G(lat)dlon². Scale the unwrapped longitude excursion of any pole-avoiding
 path to a smaller endpoint separation; its length cannot increase. Winding
 paths have absolute unwrapped separation at least the wrapped separation;
 pole-touching paths are limits of pole-avoiding paths. Taking shortest-path
 infima proves that distance is nondecreasing with wrapped separation. The
 smallest attainable integer gap therefore suffices, including seam wraps.
 The original spherical lower bound and numerical cushion are unchanged.
 """
 if not (type(width) is int and width>=2 and all(type(x) is int for x in (y,a,b)) and 0<=a<b<=width and y>=0 and math.isfinite(incumbent) and incumbent>=0 and math.isfinite(tol) and tol>=0):raise ValueError('invalid runs')
 r=np.asarray(records)
 if not len(r):return {},0
 if r.ndim!=2 or r.shape[1]!=4:raise ValueError('invalid records')
 yy=r[:,0].astype(np.int64);left=r[:,1].astype(np.int64);right=r[:,2].astype(np.int64);codes=r[:,3].astype(np.int64)
 if np.any(yy<0) or np.any(left<0) or np.any(left>=right) or np.any(right>width) or np.any((codes<=0)|(codes>=2**32)):raise ValueError('invalid runs')
 step=360/width;lat1=north-(y+.5)*step;lat2=north-(yy.astype(float)+.5)*step
 if abs(lat1)>90 or np.any(np.abs(lat2)>90):raise ValueError('invalid latitude')
 gap=np.full(len(r),width,dtype=np.int64)
 for shift in (-width,0,width):gap=np.minimum(gap,np.maximum(0,np.maximum(left+shift-(b-1),a-(right-1+shift))))
 dl=np.deg2rad(gap*step);p1=math.radians(lat1);p2=np.deg2rad(lat2);x=np.cos(p2)*np.sin(dl);z=math.cos(p1)*np.sin(p2)-math.sin(p1)*np.cos(p2)*np.cos(dl);dot=math.sin(p1)*np.sin(p2)+math.cos(p1)*np.cos(p2)*np.cos(dl);angles=np.arctan2(np.hypot(x,z),dot)
 keep=np.flatnonzero(angles*MIN_RADIUS<=incumbent+tol+CUSHION_M)
 if not len(keep):return {},len(r)
 gg=gap[keep]*step;ll=lat2[keep]
 if len(keep)==1:ds=np.asarray([GEOD.inv(0.,lat1,float(gg[0]),float(ll[0]))[2]])
 else:ds=np.asarray(GEOD.inv(np.zeros(len(keep)),np.full(len(keep),lat1),gg,ll)[2])
 selected_codes=codes[keep];result={}
 for code in np.unique(selected_codes):result[int(code)]=float(np.min(ds[selected_codes==code]))
 return result,len(r)
