import argparse, heapq, json, math
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
from shapely.geometry import LineString

def run(src, mask, bounds, off, a, b, crs, line=None):
    tx=Transformer.from_crs(4326,crs,always_xy=True)
    inv=Transformer.from_crs(crs,4326,always_xy=True)
    A=tx.transform(*a); B=tx.transform(*b)
    if line and (tuple(line[0])!=tuple(a) or tuple(line[-1])!=tuple(b)): raise ValueError('line endpoints differ from anchors')
    route=LineString([tx.transform(*p) for p in line]) if line else LineString([A,B])
    if not route.is_simple or route.length<=2: raise ValueError('invalid route')
    with rasterio.open(src) as ds, rasterio.open(mask) as ms:
        if ds.crs != ms.crs or ds.transform != ms.transform or ds.shape != ms.shape or str(ds.crs) != 'EPSG:4326':
            raise ValueError('DSM and mask must have identical EPSG:4326 grids')
        w=from_bounds(*bounds,transform=ds.transform).round_offsets().round_lengths()
        z=ds.read(1,window=w).astype(float); m=ms.read(1,window=w); trans=ds.window_transform(w)
        valid=(m==0)&np.isfinite(z)&(z!=ds.nodata)
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
    flow=parent.copy(); dx=abs(trans.a)*111320*math.cos(math.radians((bounds[1]+bounds[3])/2)); dy=abs(trans.e)*111320
    for r,c in order:
        i=r*w+c
        if parent[i]<0: continue
        best=0.
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                nr,nc=r+dr,c+dc
                if (dr or dc) and 0<=nr<h and 0<=nc<w and np.isfinite(flood[nr,nc]):
                    slope=(flood[r,c]-flood[nr,nc])/math.hypot(dx*dc,dy*dr)
                    if slope>best: best=slope; flow[i]=nr*w+nc
    def outlet(i):
        trail=[]
        while flow[i]>=0 and flow[i]!=i:
            trail.append(i); i=int(flow[i])
            if len(trail)>h*w: raise ValueError('cycle')
        for j in trail: flow[j]=i
        return i
    pairs=[]; outlets=[]; excluded=0
    for f in np.linspace(.05,.95,19):
        pos=route.length*f; mid=route.interpolate(pos); prev=route.interpolate(max(0,pos-1)); nxt=route.interpolate(min(route.length,pos+1))
        vx=nxt.x-prev.x;vy=nxt.y-prev.y;length=math.hypot(vx,vy)
        if not length: raise ValueError('undefined route normal')
        nx=-vy/length;ny=vx/length;x=mid.x;y=mid.y;inds=[]
        for sign in (-1,1):
            lon,lat=inv.transform(x+sign*off*nx,y+sign*off*ny)
            rr,cc=rasterio.transform.rowcol(trans,lon,lat)
            if rr<0 or cc<0 or rr>=h or cc>=w or not valid[rr,cc] or not np.isfinite(flood[rr,cc]): break
            inds.append(outlet(rr*w+cc))
        if len(inds)!=2: excluded+=1; continue
        r1,c1=divmod(inds[0],w);r2,c2=divmod(inds[1],w)
        pairs.append(math.hypot((c1-c2)*dx,(r1-r2)*dy))
        outlets.append([list(rasterio.transform.xy(trans,r1,c1)),list(rasterio.transform.xy(trans,r2,c2))])
    return {'bounds':bounds,'offset_m':off,'shape':[h,w], 'valid_fraction':round(float(valid.mean()),4),'excluded':excluded,'same_outlet':sum(x==0 for x in pairs),'within_500m':sum(x<=500 for x in pairs),'outlet_separation_m':[round(x) for x in pairs], 'outlet_pairs_lonlat':outlets}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description='Experimental local D8 outlet comparison; not a watershed proof')
    p.add_argument('--dsm',required=True); p.add_argument('--mask',required=True)
    p.add_argument('--bounds',nargs=4,type=float,required=True,metavar=('W','S','E','N'))
    p.add_argument('--start',nargs=2,type=float,required=True,metavar=('LON','LAT'))
    p.add_argument('--end',nargs=2,type=float,required=True,metavar=('LON','LAT'))
    p.add_argument('--line',help='optional JSON coordinate array; overrides the straight chord')
    p.add_argument('--crs',required=True,help='local metric projected CRS, e.g. EPSG code')
    p.add_argument('--offset',type=float,required=True,help='perpendicular distance in metres')
    a=p.parse_args()
    if a.offset <= 0: p.error('offset must be positive')
    route=json.load(open(a.line)) if a.line else None
    print(json.dumps(run(a.dsm,a.mask,a.bounds,a.offset,a.start,a.end,a.crs,route)))
