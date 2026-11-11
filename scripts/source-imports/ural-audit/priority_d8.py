"""Experimental D8 roots with WGS84 center-to-center slope distances."""
import heapq, math
import numpy as np
from numba import njit
from pyproj import CRS, Geod, Transformer

GEOD=Geod(ellps='WGS84')

def neighbor_distances(valid,transform,crs,chunk_rows=128):
    """Cache each undirected neighboring grid edge exactly once in meters.

    The four planes store E, S, SE and SW distances. Coordinates are
    transformed in row chunks; the returned cache uses 32 bytes per cell.
    """
    valid=np.asarray(valid,dtype=bool)
    if valid.ndim!=2:raise ValueError('two-dimensional raster required')
    h,w=valid.shape
    if h*w>np.iinfo(np.int32).max:raise ValueError('raster exceeds int32 index capacity')
    if h<2 or w<2 or chunk_rows<1 or not all(math.isfinite(v) for v in (transform.a,transform.b,transform.c,transform.d,transform.e,transform.f)) or transform.b!=0 or transform.d!=0 or transform.a<=0 or transform.e>=0:raise ValueError('north-up projected raster required')
    if not CRS.from_user_input(crs).is_projected:raise ValueError('projected raster CRS required')
    out=np.zeros((4,h,w),dtype=np.float64);to_geo=Transformer.from_crs(crs,4326,always_xy=True)
    xv=transform.c+(np.arange(w)+.5)*transform.a
    for start in range(0,h,chunk_rows):
        end=min(h,start+chunk_rows);stop=min(h,end+1)
        yv=transform.f+(np.arange(start,stop)+.5)*transform.e
        xx,yy=np.meshgrid(xv,yv);lon,lat=to_geo.transform(xx,yy)
        checked=valid[start:stop,:]
        if np.any(checked & (~np.isfinite(lon) | ~np.isfinite(lat) | (np.abs(lat)>90))):raise ValueError('invalid WGS84 cell center')
        count=end-start
        def fill(plane,rows,cols,a,b,c,d,mask):
            _,_,distance=GEOD.inv(a,b,c,d);distance=np.asarray(distance)
            if np.any(mask & (~np.isfinite(distance) | (distance<=0))):raise ValueError('invalid WGS84 neighbor distance')
            out[plane,rows,cols]=np.where(mask,distance,0.)
        fill(0,slice(start,end),slice(0,w-1),lon[:count,:-1],lat[:count,:-1],lon[:count,1:],lat[:count,1:],valid[start:end,:-1]&valid[start:end,1:])
        n=min(count,h-1-start)
        if n:
            fill(1,slice(start,start+n),slice(None),lon[:n,:],lat[:n,:],lon[1:n+1,:],lat[1:n+1,:],valid[start:start+n,:]&valid[start+1:start+n+1,:])
            fill(2,slice(start,start+n),slice(0,w-1),lon[:n,:-1],lat[:n,:-1],lon[1:n+1,1:],lat[1:n+1,1:],valid[start:start+n,:-1]&valid[start+1:start+n+1,1:])
            fill(3,slice(start,start+n),slice(1,w),lon[:n,1:],lat[:n,1:],lon[1:n+1,:-1],lat[1:n+1,:-1],valid[start:start+n,1:]&valid[start+1:start+n+1,:-1])
    return out

@njit
def _drainage(elevation, valid, edges):
    h,w=elevation.shape;size=h*w
    flood=np.full((h,w),np.inf,np.float64);parent=np.full(size,-2,np.int32)
    order=np.empty(size,np.int32);count=0
    heap=[(0.0,0)];heap.pop()
    for r in range(h):
        for c in range(w):
            i=r*w+c
            if not valid[r,c]:parent[i]=-3
            elif r==0 or c==0 or r==h-1 or c==w-1:
                flood[r,c]=elevation[r,c];parent[i]=-1;heapq.heappush(heap,(float(flood[r,c]),i))
    while heap:
        v,i=heapq.heappop(heap);order[count]=i;count+=1;r=i//w;c=i%w
        for dr in range(-1,2):
            for dc in range(-1,2):
                rr=r+dr;cc=c+dc
                if (dr!=0 or dc!=0) and 0<=rr<h and 0<=cc<w:
                    j=rr*w+cc
                    if parent[j]==-2:
                        parent[j]=i;flood[rr,cc]=max(v,elevation[rr,cc]);heapq.heappush(heap,(float(flood[rr,cc]),j))
    flow=parent.copy()
    for k in range(count):
        i=order[k];r=i//w;c=i%w
        if parent[i]<0:continue
        best=0.0
        for dr in range(-1,2):
            for dc in range(-1,2):
                rr=r+dr;cc=c+dc
                if (dr!=0 or dc!=0) and 0<=rr<h and 0<=cc<w and math.isfinite(flood[rr,cc]):
                    if dr==0: distance=edges[0,r,c if dc>0 else c-1]
                    elif dc==0: distance=edges[1,r if dr>0 else r-1,c]
                    elif dr==dc: distance=edges[2,r if dr>0 else r-1,c if dc>0 else c-1]
                    else: distance=edges[3,r if dr>0 else r-1,c if dr>0 else c+1]
                    if distance<=0:raise ValueError('missing geodesic neighbor edge')
                    slope=(flood[r,c]-flood[rr,cc])/distance
                    if slope>best:best=slope;flow[i]=rr*w+cc
    roots=np.full(size,-1,np.int32)
    for i in range(size):
        if flow[i]==-3 or flow[i]==-2:roots[i]=-2
        elif flow[i]==-1:roots[i]=i
    for i in range(size):
        if roots[i]!=-1:continue
        j=i;steps=0
        while roots[j]==-1:
            j=flow[j];steps+=1
            if j<0 or steps>size:raise ValueError('flow cycle or unconnected cell')
        target=roots[j];j=i
        while roots[j]==-1:
            nxt=flow[j];roots[j]=target;j=nxt
    return roots.reshape((h,w)),flood,flow.reshape((h,w))

def drainage(elevation,valid,transform,crs):
    if elevation.shape!=valid.shape:raise ValueError('elevation/mask shape mismatch')
    if len(elevation.shape)!=2 or math.prod(elevation.shape)>np.iinfo(np.int32).max:raise ValueError('raster exceeds int32 index capacity')
    if np.any(valid & ~np.isfinite(elevation)):raise ValueError('valid cells require finite elevation')
    return _drainage(elevation,valid,neighbor_distances(valid,transform,crs))

