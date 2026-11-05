"""WGS84 polyline distances with bounded one-dimensional closest-point search.

Edges are shortest WGS84 geodesics. Long edges are split to <=10 km before
bounded minimization. This numerical search is not a formal global proof; do
not make an exact-threshold decision without accounting for 0.02 m tolerance.
"""
import math
from pyproj import Geod
from scipy.optimize import minimize_scalar

GEOD=Geod(ellps='WGS84')
SEARCH_TOLERANCE_M=0.02
MAX_SEARCH_SEGMENT_M=10000.0


def distance(a,b):
    d=GEOD.inv(a[0],a[1],b[0],b[1])[2]
    if not math.isfinite(d):raise ValueError('non-finite WGS84 coordinates')
    return d


class GeodesicLine:
    def __init__(self,coords):
        self.segments=[];station=0.0
        if len(coords)<2:raise ValueError('line needs two points')
        for a,b in zip(coords,coords[1:]):
            azi,_,length=GEOD.inv(a[0],a[1],b[0],b[1])
            if not math.isfinite(length):raise ValueError('invalid coordinates')
            if length==0:continue
            n=max(1,math.ceil(length/MAX_SEARCH_SEGMENT_M))
            for i in range(n):
                start=GEOD.fwd(a[0],a[1],azi,length*i/n)[:2] if i else tuple(a)
                end=GEOD.fwd(a[0],a[1],azi,length*(i+1)/n)[:2] if i+1<n else tuple(b)
                segazi,_,seglen=GEOD.inv(*start,*end)
                self.segments.append((start,segazi,seglen,station))
                station+=seglen
        if not self.segments:raise ValueError('zero-length line')
        self.length=station

    def point(self,station):
        station=max(0,min(self.length,station))
        for a,azi,length,base in self.segments:
            if station<=base+length:
                return GEOD.fwd(*a,azi,max(0,station-base))[:2]
        a,azi,length,base=self.segments[-1]
        return GEOD.fwd(*a,azi,length)[:2]

    def closest(self,point):
        best=None
        for a,azi,length,base in self.segments:
            def evaluate(offset):
                q=GEOD.fwd(*a,azi,offset)[:2]
                return distance(q,point)
            opt=minimize_scalar(evaluate,bounds=(0,length),method='bounded',options={'xatol':0.002})
            for offset,d in ((0,evaluate(0)),(length,evaluate(length)),(float(opt.x),float(opt.fun))):
                candidate=(d,base+offset)
                if best is None or candidate<best:best=candidate
        return {'distance_m':best[0],'station_m':best[1],'point':self.point(best[1])}

    def side(self,point,station,radius=5):
        if radius<=0:raise ValueError('positive tangent radius required')
        p=self.point(station);a=self.point(max(0,station-radius));b=self.point(min(self.length,station+radius))
        forward=GEOD.inv(*a,*b)[0];toward=GEOD.inv(*p,*point)[0]
        signed=math.sin(math.radians(toward-forward))
        if distance(p,point)<=SEARCH_TOLERANCE_M or abs(signed)<1e-12:return 'on'
        return 'right' if signed>0 else 'left'
