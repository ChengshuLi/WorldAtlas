"""Research-only exact WGS84 minimum between two discrete horizontal grid runs.

No land policy. Enumerate attainable *longitude gaps*, not all cell pairs.
"""
import math,numpy as np
from point_prototype import GEOD, MIN_RADIUS, CUSHION_M

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
