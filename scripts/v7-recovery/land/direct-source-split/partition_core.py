"""Generic grid-edge barrier rasterization and interval graph primitives."""
from array import array
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path
import math, struct

class CutEdges:
    """Blocked four-neighbor graph edges. H: (row,x)-(row,x+1); V: (row,x)-(row+1,x)."""
    def __init__(self):
        self.horizontal=defaultdict(set)
        self.vertical=defaultdict(set)
        self.wrap=set()  # blocks (x=W-1) <-> (x=0) on this row
    def add_h(self,y,x):self.horizontal[int(y)].add(int(x))
    def add_v(self,y,x):self.vertical[int(y)].add(int(x))
    def add_wrap(self,y):self.wrap.add(int(y))
    def as_dict(self):
        return {'horizontal':{str(y):sorted(xs) for y,xs in sorted(self.horizontal.items()) if xs},
                'vertical':{str(y):sorted(xs) for y,xs in sorted(self.vertical.items()) if xs},
                'wrap':sorted(self.wrap)}

    def write_u32le(self,path):
        """Serialize unique cut edges as (kind,row,x) uint32 triples."""
        records=[]
        for y,xs in self.horizontal.items():records.extend((0,y,x) for x in xs)
        for y,xs in self.vertical.items():records.extend((1,y,x) for x in xs)
        records.extend((2,y,0) for y in self.wrap)
        records.sort()
        with Path(path).open('wb') as f:
            for k,y,x in records:f.write(struct.pack('<III',k,y,x))
        return len(records)
    @classmethod
    def read_u32le(cls,path):
        cuts=cls();data=Path(path).read_bytes()
        if len(data)%12:raise ValueError('cut edge file length is not a multiple of 12 bytes')
        for k,y,x in struct.iter_unpack('<III',data):
            if k==0:cuts.add_h(y,x)
            elif k==1:cuts.add_v(y,x)
            elif k==2:cuts.add_wrap(y)
            else:raise ValueError(f'unknown cut edge kind {k}')
        return cuts

def _cross(ax,ay,bx,by):return ax*by-ay*bx

def _point_on_segment(p,a,b,eps=1e-10):
    px,py=p;ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay
    if abs(_cross(dx,dy,px-ax,py-ay))>eps*max(1.0,abs(dx)+abs(dy)):return False
    dot=(px-ax)*dx+(py-ay)*dy;ll=dx*dx+dy*dy
    return -eps<=dot<=ll+eps

def _intersection_nonvertex(p,q,a,b,eps=1e-10):
    """True iff line segment pq intersects edge ab away from a/b graph vertices.

    Intersections at cell-center graph vertices are handled by the deterministic
    tie rule in rasterize_barriers. A source edge overlapping an entire graph
    edge is also assigned by those endpoint ties, so it is not cut here.
    """
    px,py=p;qx,qy=q;ax,ay=a;bx,by=b
    rx,ry=qx-px,qy-py;sx,sy=bx-ax,by-ay
    den=_cross(rx,ry,sx,sy);apx,apy=ax-px,ay-py
    if abs(den)<=eps:
        if abs(_cross(apx,apy,rx,ry))>eps*max(1.0,abs(rx)+abs(ry)):return False
        rr=rx*rx+ry*ry
        if rr==0:return False
        t0=(apx*rx+apy*ry)/rr;t1=((bx-px)*rx+(by-py)*ry)/rr
        lo=max(0.0,min(t0,t1));hi=min(1.0,max(t0,t1))
        if hi<lo-eps:return False
        # If both edge endpoints are on the source route, use the vertex tie.
        if _point_on_segment(a,p,q,eps) and _point_on_segment(b,p,q,eps):return False
        # Any positive-length partial overlap or a touch of edge interior is a cut.
        return hi-lo>eps or (lo>=-eps and lo<=1+eps and
          (eps < min(abs(lo),abs(1-lo)) or _point_on_segment(p,a,b,eps) or _point_on_segment(q,a,b,eps)))
    t=_cross(apx,apy,sx,sy)/den;u=_cross(apx,apy,rx,ry)/den
    if t < -eps or t > 1+eps or u < -eps or u > 1+eps:return False
    ix=px+t*rx;iy=py+t*ry
    # A graph-center endpoint hit is deferred to the tie handler.
    if (math.hypot(ix-ax,iy-ay)<=eps or math.hypot(ix-bx,iy-by)<=eps):return False
    return True

def rasterize_barriers(paths,width,height,eps=1e-10,*,guard=lambda:None,max_work=100000000):
    """Convert polyline paths in grid-edge (x,y) coordinates into blocked graph edges.

    At a source-line hit on a cell-center graph vertex, the tie cell is assigned
    to the left side of the oriented route; only edges to its right-side
    neighbors are blocked. This prevents diagonal leakage without dropping any
    cell. Shared boundary-aligned cell-center edges stay connected on that same
    tie side. Paths are expected to be longitude-unwrapped and may not cross the
    antimeridian.
    """
    if not callable(guard) or type(max_work) is not int or max_work <= 0: raise ValueError('invalid raster work guard')
    guard(); work=0
    cuts=CutEdges();tie_vectors=defaultdict(lambda:[0.0,0.0])
    for path in paths:
        pts=[(float(x),float(y)) for x,y in path]
        for p,q in zip(pts,pts[1:]):
            guard()
            x0,y0=p;x1,y1=q;dx=x1-x0;dy=y1-y0
            work += 3*(math.ceil(abs(dx))+3)*(math.ceil(abs(dy))+3)
            if work>max_work: raise ValueError('boundary raster work limit reached')
            if abs(dx)+abs(dy)<=eps:continue
            # Collect graph-center vertices on the route; store oriented tangents.
            ix0=math.ceil(min(x0,x1)-.5-eps);ix1=math.floor(max(x0,x1)-.5+eps)
            iy0=math.ceil(min(y0,y1)-.5-eps);iy1=math.floor(max(y0,y1)-.5+eps)
            for iy in range(iy0,iy1+1):
                cy=iy+.5
                for ix in range(ix0,ix1+1):
                    cx=ix+.5
                    if _point_on_segment((cx,cy),p,q,eps):
                        v=tie_vectors[(ix,iy)];v[0]+=dx;v[1]+=dy
            # Candidate east/west graph edges, endpoints at cell centers.
            j0=max(0,math.ceil(min(y0,y1)-.5-eps));j1=min(height-1,math.floor(max(y0,y1)-.5+eps))
            i0=max(0,math.floor(min(x0,x1)-1.5));i1=min(width-2,math.ceil(max(x0,x1)-.5))
            for j in range(j0,j1+1):
                yy=j+.5
                for i in range(i0,i1+1):
                    a=(i+.5,yy);b=(i+1.5,yy)
                    if _intersection_nonvertex(p,q,a,b,eps):cuts.add_h(j,i)
            # Candidate north/south graph edges.
            i0=max(0,math.ceil(min(x0,x1)-.5-eps));i1=min(width-1,math.floor(max(x0,x1)-.5+eps))
            j0=max(0,math.floor(min(y0,y1)-1.5));j1=min(height-2,math.ceil(max(y0,y1)-.5))
            for i in range(i0,i1+1):
                xx=i+.5
                for j in range(j0,j1+1):
                    a=(xx,j+.5);b=(xx,j+1.5)
                    if _intersection_nonvertex(p,q,a,b,eps):cuts.add_v(j,i)
    # Deterministic graph-vertex tie handling after tangents have been combined.
    for (ix,iy),(dx,dy) in tie_vectors.items():
        if abs(dx)+abs(dy)<=eps:continue
        cx,cy=ix+.5,iy+.5
        for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):
            nx,ny=cx+ox,cy+oy
            side=_cross(dx,dy,nx-cx,ny-cy)
            if side>=-eps:continue  # keep left/on-line neighbors in same tie class
            if ox==1 and 0<=ix<width-1:cuts.add_h(iy,ix)
            elif ox==-1 and 0<=ix-1<width-1:cuts.add_h(iy,ix-1)
            elif oy==1 and 0<=iy<height-1:cuts.add_v(iy,ix)
            elif oy==-1 and 0<=iy-1<height-1:cuts.add_v(iy-1,ix)
    return cuts

def split_eligible(intervals,blocked_edges,width):
    """Split [x0,x1) eligible intervals wherever a horizontal neighbor is cut."""
    out=[]
    for a,b in intervals:
        if not (0<=a<b<=width):raise ValueError(f'invalid eligible interval {(a,b)}')
        i=bisect_left(blocked_edges,a);j=bisect_left(blocked_edges,b-1)
        start=a
        for edge in blocked_edges[i:j]:
            out.append((start,edge+1));start=edge+1
        if start<b:out.append((start,b))
    return out

class _DSU:
    def __init__(self):self.parent=array('I');self.size=array('I')
    def add(self):
        i=len(self.parent)
        if i>=0xffffffff:raise OverflowError('run-node count exceeds uint32 DSU capacity')
        self.parent.append(i);self.size.append(1);return i
    def find(self,x):
        p=self.parent
        while p[x]!=x:
            p[x]=p[p[x]];x=p[x]
        return x
    def union(self,a,b):
        ra=self.find(a);rb=self.find(b)
        if ra==rb:return
        if self.size[ra]<self.size[rb]:ra,rb=rb,ra
        self.parent[rb]=ra;self.size[ra]+=self.size[rb]
