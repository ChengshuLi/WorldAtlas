"""Numerical WGS84 stationing along an existing projected-linear route.

Geometric edges remain straight in the supplied projected CRS.  Chord sums
at <=100.01 m approximate their WGS84 surface length; this is not a formally
bounded estimate. Tangents at a vertex use the preceding edge.
"""
import bisect, math
import numpy as np
from pyproj import CRS, Geod, Transformer

GEOD=Geod(ellps='WGS84')

class ProjectedRoute:
    def __init__(self,points,crs):
        crs=CRS.from_user_input(crs)
        if not crs.is_projected or any(abs(a.unit_conversion_factor-1)>1e-9 for a in crs.axis_info):
            raise ValueError('projected metre CRS required')
        if not 2<=len(points)<=10000:raise ValueError('invalid route')
        self.forward=Transformer.from_crs(4326,crs,always_xy=True)
        self.reverse=Transformer.from_crs(crs,4326,always_xy=True)
        self.vertices=[]
        for p in points:
            if len(p)!=2 or not all(math.isfinite(v) for v in p) or not (-180<=p[0]<=180 and -90<=p[1]<=90):raise ValueError('invalid route coordinate')
            projected=self.forward.transform(*p)
            if not self.vertices or projected!=self.vertices[-1]:self.vertices.append(projected)
        if len(self.vertices)<2:raise ValueError('degenerate route')
        self.parts=[];self.length=0.
        for i,(a,b) in enumerate(zip(self.vertices,self.vertices[1:])):
            if not all(math.isfinite(v) for v in (*a,*b)) or a==b:raise ValueError('degenerate route edge')
            _,_,length=GEOD.inv(*self._at(i,0),*self._at(i,1))
            if not math.isfinite(length) or length<=0:raise ValueError('invalid WGS84 route edge')
            count=max(1,math.ceil(length/99))
            if count>1000000 or len(self.parts)+count>1000000:raise ValueError('route subdivision limit exceeded')
            prev=self._at(i,0)
            for j in range(1,count+1):
                cur=self._at(i,j/count);_,_,d=GEOD.inv(*prev,*cur)
                if not math.isfinite(d) or not 0<d<=100.01:raise ValueError('route chord limit exceeded')
                self.parts.append((self.length,self.length+d,i,(j-1)/count,j/count));self.length+=d;prev=cur
        self.ends=[p[1] for p in self.parts]
    def _at(self,i,t):
        a,b=self.vertices[i:i+2]
        return self.reverse.transform(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
    def point(self,distance):
        if not math.isfinite(distance) or not 0<=distance<=self.length:raise ValueError('station outside route')
        lo,hi,i,t0,t1=self.parts[min(bisect.bisect_left(self.ends,distance),len(self.parts)-1)]
        origin=self._at(i,t0);left,right=t0,t1;want=distance-lo
        if want<=0:t=t0
        elif want>=hi-lo:t=t1
        else:
            for _ in range(48):
                t=(left+right)/2;_,_,d=GEOD.inv(*origin,*self._at(i,t))
                if not math.isfinite(d):raise ValueError('invalid station')
                if abs(d-want)<=1e-5:break
                if d<want:left=t
                else:right=t
            else:raise ValueError('station did not converge')
        point=self._at(i,t);q=min(1.,t+1e-6);back=q==t
        if back:q=max(0.,t-1e-6)
        azi,_,d=GEOD.inv(*point,*self._at(i,q))
        if not math.isfinite(d) or d<=0:raise ValueError('invalid route tangent')
        return (*point,azi+(180 if back else 0))
    def nearest(self,lon,lat):
        """Numerically minimize WGS84 distance to the projected-linear route.

        Each <=100.01 m chord interval is independently searched, including
        its endpoints. A numerical optimum is returned, not a certified global
        minimum; callers must not treat it as a formal error bound.
        """
        if not all(math.isfinite(x) for x in (lon,lat)) or not -180<=lon<=180 or not -90<=lat<=90:raise ValueError('invalid query coordinate')
        indices=np.array([p[2] for p in self.parts],dtype=np.int64)
        lower=np.array([p[3] for p in self.parts],dtype=float)
        upper=np.array([p[4] for p in self.parts],dtype=float)
        vertices=np.asarray(self.vertices,dtype=float);a=vertices[indices];b=vertices[indices+1]
        def distance(t):
            x=a[:,0]+t*(b[:,0]-a[:,0]);y=a[:,1]+t*(b[:,1]-a[:,1]);xs,ys=self.reverse.transform(x,y)
            _,_,d=GEOD.inv(np.full(len(t),lon),np.full(len(t),lat),xs,ys)
            d=np.asarray(d)
            if not np.isfinite(d).all():raise ValueError('invalid WGS84 query distance')
            return d
        # Golden-section search over every interval in parallel. Each starts at
        # <=100.01 m chord length; 36 rounds shrink its parameter span by
        # >30 million. Unimodality is an engineering assumption, not a proof.
        original_lower=lower.copy();original_upper=upper.copy();ratio=(math.sqrt(5)-1)/2
        x1=upper-ratio*(upper-lower);x2=lower+ratio*(upper-lower)
        for _ in range(36):
            d1=distance(x1);d2=distance(x2);first=d1<=d2
            upper=np.where(first,x2,upper);lower=np.where(first,lower,x1)
            x1=upper-ratio*(upper-lower);x2=lower+ratio*(upper-lower)
        candidates=np.stack((original_lower,(lower+upper)/2,original_upper))
        distances=np.stack([distance(t) for t in candidates]);which,j=np.unravel_index(np.argmin(distances),distances.shape)
        d=float(distances[which,j]);i=int(indices[j]);t=float(candidates[which,j])
        a,b=self.vertices[i:i+2];x=a[0]+t*(b[0]-a[0]);y=a[1]+t*(b[1]-a[1])
        return d,(x,y),self._at(i,t)
