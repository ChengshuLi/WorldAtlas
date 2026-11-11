"""WGS84 distances to a coordinate-linear WGS84 GeoJSON LineString.

Input edges retain coordinate-linear geometry; they are NOT replaced by geodesic
arcs. Distances use WGS84 inverse geodesics. Edges are split into at most 1 km
chords for numerical stationing and bounded closest-point search. This is not a
formal global proof; treat distances within 0.02 m of a threshold as uncertain.
Uncut antimeridian-spanning input is rejected: split it before use.
"""
import math
from pyproj import Geod
from scipy.optimize import minimize_scalar

GEOD=Geod(ellps='WGS84')
SEARCH_TOLERANCE_M=0.02
MAX_SEARCH_SEGMENT_M=1000.0


def distance(a,b):
    d=GEOD.inv(a[0],a[1],b[0],b[1])[2]
    if not math.isfinite(d):raise ValueError('non-finite WGS84 coordinates')
    return d


def interpolate(a,b,t):
    return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)


def coordinate_fraction(a,b,point):
    """Recover the coordinate-linear parameter of a point on one source edge."""
    dx=b[0]-a[0];dy=b[1]-a[1]
    if dx==0 and dy==0:raise ValueError('zero-length coordinate edge')
    t=(point[0]-a[0])/dx if abs(dx)>=abs(dy) else (point[1]-a[1])/dy
    return max(0.0,min(1.0,t))


def closest_segment(coords,point):
    """Return an exact WGS84 minimum and coordinate-linear fraction on one edge."""
    if len(coords)!=2:raise ValueError('one source edge required')
    line=GeodesicLine(coords)
    result=line.closest(point)
    result['coordinate_fraction']=coordinate_fraction(coords[0],coords[1],result['point'])
    return result


class GeodesicLine:
    def __init__(self,coords):
        self.segments=[];station=0.0
        if len(coords)<2:raise ValueError('line needs two points')
        for a,b in zip(coords,coords[1:]):
            if abs(b[0]-a[0])>180:raise ValueError('split antimeridian-spanning edges before use')
            length=distance(a,b)
            if length==0:continue
            n=max(1,math.ceil(length/MAX_SEARCH_SEGMENT_M))
            for i in range(n):
                start=interpolate(a,b,i/n);end=interpolate(a,b,(i+1)/n)
                seglen=distance(start,end);midpoint=interpolate(start,end,.5)
                self.segments.append((start,end,seglen,station,midpoint))
                station+=seglen
        if not self.segments:raise ValueError('zero-length line')
        self.length=station

    def point(self,station):
        station=max(0,min(self.length,station))
        for a,b,length,base,midpoint in self.segments:
            if station<=base+length:
                return interpolate(a,b,max(0,min(1,(station-base)/length)))
        return self.segments[-1][1]

    def closest(self,point):
        best=None;candidates=[]
        # A meridian-plus-parallel route bounds geodesic distance to every
        # point on each coordinate-linear subsegment, including near poles.
        ranked=sorted((max(0,distance(midpoint,point)-111700*(abs(b[0]-a[0])+abs(b[1]-a[1]))/2),base,(a,b,length)) for a,b,length,base,midpoint in self.segments)
        for lower,base,(a,b,length) in ranked:
            if best is not None and lower>best[0]+SEARCH_TOLERANCE_M:break
            def evaluate(t):return distance(interpolate(a,b,t),point)
            opt=minimize_scalar(evaluate,bounds=(0,1),method='bounded',options={'xatol':min(.001/length,.0001)})
            for t,d in ((0,evaluate(0)),(1,evaluate(1)),(float(opt.x),float(opt.fun))):
                candidate=(d,base+t*length);candidates.append(candidate)
                if best is None or candidate<best:best=candidate
        ambiguous=any(d<=best[0]+SEARCH_TOLERANCE_M and abs(s-best[1])>1 for d,s in candidates)
        return {'distance_m':best[0],'station_m':best[1],'point':self.point(best[1]),'ambiguous':ambiguous}

    def side(self,point,station,radius=5):
        if radius<=0:raise ValueError('positive tangent radius required')
        p=self.point(station);a=self.point(max(0,station-radius));b=self.point(min(self.length,station+radius))
        forward=GEOD.inv(*a,*b)[0];toward=GEOD.inv(*p,*point)[0]
        signed=math.sin(math.radians(toward-forward))
        if distance(p,point)<=SEARCH_TOLERANCE_M or abs(signed)<1e-12:return 'on'
        return 'right' if signed>0 else 'left'


def closest_line(lines,point):
    """Find the closest coordinate-linear source line by WGS84 distance.

    Ties within the line solver's tolerance are marked ambiguous when the
    candidate nearest points are more than one metre apart.
    """
    candidates=[]
    for index,line in enumerate(lines):
        result=line.closest(point)
        candidates.append((result['distance_m'],index,result))
    if not candidates:raise ValueError('no source lines')
    candidates.sort(key=lambda item:(item[0],item[1]))
    best=candidates[0]
    bx,by=best[2]['point']
    ambiguous=best[2]['ambiguous']
    for distance_m,index,result in candidates[1:]:
        if distance_m>best[0]+SEARCH_TOLERANCE_M:break
        x,y=result['point']
        if distance((bx,by),(x,y))>1.0:
            ambiguous=True
            break
    return {'distance_m':best[0],'source_index':best[1],
            'point':best[2]['point'],'ambiguous':ambiguous}
