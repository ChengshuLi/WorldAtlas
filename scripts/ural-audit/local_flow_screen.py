import argparse, heapq, json, math
from functools import lru_cache
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from pyproj import Geod, Transformer

GEOD=Geod(ellps="WGS84")
METHOD="wgs84-ellipsoidal-geodesic-v1"

def cell_center(trans,row,col):
    lon=trans.c+(col+.5)*trans.a;lat=trans.f+(row+.5)*trans.e
    if not (math.isfinite(lon) and math.isfinite(lat) and -180<=lon<=180 and -90<=lat<=90):raise ValueError("cell center outside WGS84")
    return lon,lat

def cell_distance(trans,a,b):
    p=cell_center(trans,*a);q=cell_center(trans,*b);_,_,d=GEOD.inv(*p,*q)
    if not math.isfinite(d) or d<0:raise ValueError("invalid WGS84 distance")
    return d

def neighbor_distance(trans,row,dr,dc):
    lat=trans.f+(row+.5)*trans.e;other=trans.f+(row+dr+.5)*trans.e
    if not (-90<=lat<=90 and -90<=other<=90):raise ValueError('neighbor latitude outside WGS84')
    _,_,distance=GEOD.inv(0,lat,dc*trans.a,other)
    if not math.isfinite(distance) or distance<=0:raise ValueError('invalid geodesic neighbor distance')
    return distance

def run(src, mask, bounds, off, a, b, crs):
    tx=Transformer.from_crs(4326,crs,always_xy=True)
    inv=Transformer.from_crs(crs,4326,always_xy=True)
    A=tx.transform(*a); B=tx.transform(*b)
    with rasterio.open(src) as ds, rasterio.open(mask) as ms:
        if ds.crs != ms.crs or ds.transform != ms.transform or ds.shape != ms.shape or str(ds.crs) != 'EPSG:4326':
            raise ValueError('DSM and mask must have identical EPSG:4326 grids')
        w=from_bounds(*bounds,transform=ds.transform).round_offsets().round_lengths()
        if (not all(math.isfinite(v) for v in (w.col_off,w.row_off,w.width,w.height))
                or any(v!=int(v) for v in (w.col_off,w.row_off,w.width,w.height))
                or w.col_off<0 or w.row_off<0 or w.width<=0 or w.height<=0
                or w.col_off+w.width>ds.shape[1] or w.row_off+w.height>ds.shape[0]):
            raise ValueError('requested raster window is outside source grid')
        z=ds.read(1,window=w).astype(float); m=ms.read(1,window=w); trans=ds.window_transform(w)
        if z.shape!=(int(w.height),int(w.width)) or m.shape!=z.shape:raise ValueError('raster read does not match requested window')
        valid=(m==0)&np.isfinite(z)&(z!=ds.nodata)
    if trans.b!=0 or trans.d!=0 or trans.a<=0 or trans.e>=0:raise ValueError('north-up WGS84 raster required')
    h,w=z.shape; seen=~valid; flood=np.full(z.shape,np.inf); parent=np.full(h*w,-1,np.int64); heap=[]
    # Invalid cells are barriers, not artificial outlets. Only valid exterior cells seed the fill.
    for r,c in [(r,c) for r in range(h) for c in (0,w-1)]+[(r,c) for c in range(w) for r in (0,h-1)]:
        if valid[r,c] and not seen[r,c]: seen[r,c]=True; flood[r,c]=z[r,c]; heapq.heappush(heap,(z[r,c],r,c))
    order=[]
    while heap:
        v,r,c=heapq.heappop(heap); order.append((r,c))
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                nr,nc=r+dr,c+dc
                if (dr or dc) and 0<=nr<h and 0<=nc<w and not seen[nr,nc]:
                    seen[nr,nc]=True; flood[nr,nc]=max(v,z[nr,nc]); parent[nr*w+nc]=r*w+c; heapq.heappush(heap,(flood[nr,nc],nr,nc))
    # Boundary outlet following steepest D8 drop on filled surface; flats follow flood parent.
    flow=parent.copy()
    @lru_cache(maxsize=8192)
    def cached_neighbor_distance(row,dr,dc):
        return neighbor_distance(trans,row,dr,dc)
    for r,c in order:
        i=r*w+c
        if parent[i]<0: continue
        best=0.
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                nr,nc=r+dr,c+dc
                if (dr or dc) and 0<=nr<h and 0<=nc<w and np.isfinite(flood[nr,nc]):
                    slope=(flood[r,c]-flood[nr,nc])/cached_neighbor_distance(r,dr,dc)
                    if slope>best: best=slope; flow[i]=nr*w+nc
    def outlet(i):
        trail=[]
        while flow[i]>=0 and flow[i]!=i:
            trail.append(i); i=int(flow[i])
            if len(trail)>h*w: raise ValueError('cycle')
        for j in trail: flow[j]=i
        return i
    vx=B[0]-A[0];vy=B[1]-A[1]
    if not all(math.isfinite(x) for x in (*A,*B,off)) or (vx==0 and vy==0) or off<=0:raise ValueError('invalid source line or offset')
    pairs=[];excluded=0
    for f in np.linspace(.05,.95,19):
        x=A[0]+f*vx;y=A[1]+f*vy
        lon,lat=inv.transform(x,y);qx,qy=inv.transform(x+vx*1e-6,y+vy*1e-6)
        azi,_,tangent_distance=GEOD.inv(lon,lat,qx,qy)
        if not math.isfinite(tangent_distance) or tangent_distance<=0:raise ValueError('invalid source-line tangent')
        inds=[]
        for sign in (-1,1):
            lon2,lat2,_=GEOD.fwd(lon,lat,azi-90,sign*off)
            rr,cc=rasterio.transform.rowcol(trans,lon2,lat2)
            if rr<0 or cc<0 or rr>=h or cc>=w or not valid[rr,cc] or not np.isfinite(flood[rr,cc]):break
            inds.append(outlet(rr*w+cc))
        if len(inds)!=2:excluded+=1;continue
        r1,c1=divmod(inds[0],w);r2,c2=divmod(inds[1],w)
        pairs.append(cell_distance(trans,(r1,c1),(r2,c2)))
    return {'distance_method':METHOD,'source_geometry_method':'projected-linear','source_geometry_crs':str(crs),'bounds':bounds,'offset_m':off,'shape':[h,w], 'valid_fraction':round(float(valid.mean()),4),'excluded':excluded,'same_outlet':sum(x==0 for x in pairs),'within_500m':sum(x<=500 for x in pairs),'outlet_separation_m':[round(x) for x in pairs]}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description='Experimental local D8 outlet comparison; not a watershed proof')
    p.add_argument('--dsm',required=True); p.add_argument('--mask',required=True)
    p.add_argument('--bounds',nargs=4,type=float,required=True,metavar=('W','S','E','N'))
    p.add_argument('--start',nargs=2,type=float,required=True,metavar=('LON','LAT'))
    p.add_argument('--end',nargs=2,type=float,required=True,metavar=('LON','LAT'))
    p.add_argument('--crs',required=True,help='local metric projected CRS, e.g. EPSG code')
    p.add_argument('--offset',type=float,required=True,help='perpendicular distance in metres')
    a=p.parse_args()
    if a.offset <= 0: p.error('offset must be positive')
    print(json.dumps(run(a.dsm,a.mask,a.bounds,a.offset,a.start,a.end,a.crs)))
