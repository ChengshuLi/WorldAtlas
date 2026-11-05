"""Non-production exact WGS84 point/component prototype, with safe broad-phase.

The input points are geographic cell centers, no source selection or geography
policy is encoded here. Bounds use global principal curvature radii of WGS84.
"""
import math
import numpy as np
from pyproj import Geod
A=6378137.; F=1/298.257223563; E2=F*(2-F)
MIN_RADIUS=A*(1-E2); MAX_RADIUS=A/math.sqrt(1-E2)
GEOD=Geod(a=A,f=F)
# Numerical cushion for computed spherical angular bound and distance. This is
# an engineering fail-safe, not a formal floating-point proof.
CUSHION_M=1000.0

def validate_points(x):
 x=np.asarray(x,dtype=float)
 if x.ndim!=2 or x.shape[1]!=2 or not np.all(np.isfinite(x)) or np.any(np.abs(x[:,1])>90):raise ValueError('invalid lon,lat points')
 return x

def angular_to_many(q, donors):
 lon=np.radians(donors[:,0]-q[0]);lat=np.radians(donors[:,1]);latq=math.radians(q[1]);
 # atan2 of cross-norm and dot avoids ill-conditioned acos near zero/pi.
 x=np.cos(lat)*np.sin(lon); y=math.cos(latq)*np.sin(lat)-math.sin(latq)*np.cos(lat)*np.cos(lon)
 dot=math.sin(latq)*np.sin(lat)+math.cos(latq)*np.cos(lat)*np.cos(lon)
 return np.arctan2(np.hypot(x,y),dot)

def brute(queries, donors, codes):
 q=validate_points(queries);p=validate_points(donors);codes=np.asarray(codes);out={}
 if len(q)==0 or len(p)==0 or len(codes)!=len(p):raise ValueError('empty/malformed')
 for x in q:
  _,_,d=GEOD.inv(np.full(len(p),x[0]),np.full(len(p),x[1]),p[:,0],p[:,1])
  for c in np.unique(codes):out[int(c)]=min(out.get(int(c),math.inf),float(np.min(d[codes==c])))
 return out

def pruned(queries, donors, codes, tol=0, batch=65536):
 q=validate_points(queries);p=validate_points(donors);codes=np.asarray(codes)
 if len(q)==0 or len(p)==0 or len(codes)!=len(p) or tol<0 or not math.isfinite(tol) or batch<=0:raise ValueError('empty/malformed')
 best=math.inf; out={};checked=0;total=0
 for x in q:
  for lo in range(0,len(p),batch):
   a=p[lo:lo+batch];c=codes[lo:lo+batch];angle=angular_to_many(x,a);total+=len(a)
   if not math.isfinite(best):
    j=int(np.argmin(angle));_,_,best=GEOD.inv(x[0],x[1],float(a[j,0]),float(a[j,1]));best=float(best)
   keep=np.flatnonzero(angle*MIN_RADIUS<=best+tol+CUSHION_M)
   if not len(keep):continue
   _,_,d=GEOD.inv(np.full(len(keep),x[0]),np.full(len(keep),x[1]),a[keep,0],a[keep,1]);checked+=len(keep)
   for code in np.unique(c[keep]):out[int(code)]=min(out.get(int(code),math.inf),float(np.min(d[c[keep]==code])))
   best=min(best,float(np.min(d)))
 # Returning only codes that can affect the outcome avoids claiming exact
 # per-category minima for categories that were safely pruned.
 return {k:v for k,v in out.items() if v<=best+tol+CUSHION_M}, {'pairs':total,'exact_pairs':checked,'best_m':best}

def winners(ds,tol):
 z=min(ds.values());return {k for k,v in ds.items() if v<=z+tol}
