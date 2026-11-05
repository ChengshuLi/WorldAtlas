import argparse, bisect, heapq, json, math
from functools import lru_cache
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from pyproj import CRS, Geod, Transformer

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

def route_stations(points, forward, reverse):
    """Sample projected-linear geometry using bounded WGS84 chord lengths.

    This numerically approximates path length; no exact error bound is asserted.
    """
    if len(points)<2 or len(points)>10000:raise ValueError('invalid source route')
    projected=[]
    for point in points:
        if len(point)!=2 or not all(math.isfinite(v) for v in point) or not (-180<=point[0]<=180 and -90<=point[1]<=90):raise ValueError('invalid route coordinate')
        projected.append(forward.transform(*point))
    if len(projected)>2:
        from shapely.geometry import LineString
        shape=LineString(projected)
        if not shape.is_simple or shape.is_empty:raise ValueError('invalid route topology')
    parts=[];total=0.
    for i,(a,b) in enumerate(zip(projected,projected[1:])):
        if not all(math.isfinite(v) for v in (*a,*b)) or a==b:raise ValueError('degenerate projected route segment')
        def at(t):return reverse.transform(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
        _,_,length=GEOD.inv(*at(0),*at(1))
        if not math.isfinite(length) or length<=0:raise ValueError('invalid geodesic route edge')
        count=max(1,math.ceil(length/99.));
        if count>1000000 or len(parts)+count>1000000:raise ValueError('route subdivision limit exceeded')
        prev=at(0)
        for j in range(1,count+1):
            current=at(j/count);_,_,d=GEOD.inv(*prev,*current)
            if not math.isfinite(d) or d<=0 or d>100.01:raise ValueError('route subdivision exceeds WGS84 chord limit')
            parts.append((total,total+d,i,(j-1)/count,j/count));total+=d;prev=current
    if total<=2:raise ValueError('route too short')
    ends=[part[1] for part in parts];out=[]
    for fraction in np.linspace(.05,.95,19):
        target=total*float(fraction);lo,hi,i,t0,t1=parts[min(bisect.bisect_left(ends,target),len(parts)-1)];a,b=projected[i:i+2]
        def at(t):return reverse.transform(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
        origin=at(t0);left,right=t0,t1;wanted=target-lo
        for _ in range(48):
            t=(left+right)/2;point=at(t);_,_,d=GEOD.inv(*origin,*point)
            if not math.isfinite(d):raise ValueError('invalid route sample')
            if abs(d-wanted)<=1e-5:break
            if d<wanted:left=t
            else:right=t
        else:raise ValueError('route sample did not converge')
        q=min(1.,t+1e-6);reverse_tangent=q==t
        if reverse_tangent:q=max(0.,t-1e-6)
        other=at(q);azi,_,tangent=GEOD.inv(*point,*other)
        if not math.isfinite(tangent) or tangent<=0:raise ValueError('invalid route tangent')
        if reverse_tangent:azi+=180
        out.append((*point,azi))
    return out

def run(src, mask, bounds, off, a, b, crs, line=None, diagnostic=None, basin_outlets=None):
    selected_crs=CRS.from_user_input(crs)
    if not selected_crs.is_projected or any(abs(axis.unit_conversion_factor-1)>1e-9 for axis in selected_crs.axis_info):raise ValueError('source-line CRS must be projected in metres')
    tx=Transformer.from_crs(4326,crs,always_xy=True)
    inv=Transformer.from_crs(crs,4326,always_xy=True)
    if line is not None and (not line or tuple(line[0])!=tuple(a) or tuple(line[-1])!=tuple(b)):raise ValueError('line endpoints differ from anchors')
    if not math.isfinite(off) or off<=0:raise ValueError('invalid offset')
    stations=route_stations(line if line is not None else [a,b],tx,inv)
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
    pairs=[];outlets=[];excluded=0
    for lon,lat,azi in stations:
        inds=[]
        for sign in (-1,1):
            lon2,lat2,_=GEOD.fwd(lon,lat,azi-90,sign*off)
            rr,cc=rasterio.transform.rowcol(trans,lon2,lat2)
            if rr<0 or cc<0 or rr>=h or cc>=w or not valid[rr,cc] or not np.isfinite(flood[rr,cc]):break
            inds.append(outlet(rr*w+cc))
        if len(inds)!=2:excluded+=1;continue
        r1,c1=divmod(inds[0],w);r2,c2=divmod(inds[1],w)
        pairs.append(cell_distance(trans,(r1,c1),(r2,c2)))
        outlets.append([list(cell_center(trans,r1,c1)),list(cell_center(trans,r2,c2))])
    result={'distance_method':METHOD,'source_geometry_method':'projected-linear','source_geometry_crs':str(crs),'route_length_approximation':'sum of WGS84 geodesic chords <=100.01m','bounds':bounds,'offset_m':off,'shape':[h,w], 'valid_fraction':round(float(valid.mean()),4),'excluded':excluded,'same_outlet':sum(x==0 for x in pairs),'within_500m':sum(x<=500 for x in pairs),'outlet_separation_m':[round(x) for x in pairs],'outlet_pairs_lonlat':outlets}
    if diagnostic is not None:
        if basin_outlets is None or len(basin_outlets)!=2:raise ValueError('two basin outlets required')
        targets=[]
        for p in basin_outlets:
            rr,cc=rasterio.transform.rowcol(trans,*p)
            if not (0<=rr<h and 0<=cc<w and valid[rr,cc] and np.isfinite(flood[rr,cc])):raise ValueError('invalid basin outlet')
            targets.append(outlet(rr*w+cc))
        if targets[0]==targets[1]:raise ValueError('basin outlets must be distinct')
        roots=np.zeros((h,w),dtype=np.uint8)
        for rr,cc in order:
            root=outlet(rr*w+cc)
            if root==targets[0]:roots[rr,cc]=1
            elif root==targets[1]:roots[rr,cc]=2
        edges=np.zeros_like(roots,dtype=bool)
        v=(roots[1:,:]+roots[:-1,:]==3)&(roots[1:,:]*roots[:-1,:]==2);edges[1:,:]|=v;edges[:-1,:]|=v
        v=(roots[:,1:]+roots[:,:-1]==3)&(roots[:,1:]*roots[:,:-1]==2);edges[:,1:]|=v;edges[:,:-1]|=v
        rr,cc=rasterio.transform.rowcol(trans,*diagnostic)
        if not (0<=rr<h and 0<=cc<w and valid[rr,cc]):raise ValueError('invalid diagnostic point')
        ys,xs=np.where(edges)
        if not len(xs):raise ValueError('no transition between selected outlets')
        lon0,lat0=cell_center(trans,rr,cc);lons=trans.c+(xs+.5)*trans.a;lats=trans.f+(ys+.5)*trans.e
        _,_,distances=GEOD.inv(np.full(len(xs),lon0),np.full(len(xs),lat0),lons,lats)
        if not np.isfinite(distances).all():raise ValueError('invalid transition-center geodesic')
        i=int(np.argmin(distances));lon,lat=cell_center(trans,int(ys[i]),int(xs[i]))
        result['diagnostic']={'point':diagnostic,'root_class':int(roots[rr,cc]),'class_cell_counts':[int(np.count_nonzero(roots==i)) for i in (1,2)],'other_or_unrouted_cells':int(np.count_nonzero(valid&(roots==0))),'nearest_transition_center_m':float(distances[i]),'nearest_transition_center_lonlat':[lon,lat],'note':'WGS84 geodesic between grid centers at a four-neighbor modeled outlet transition, not a surveyed divide.'}
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser(description='Experimental local D8 outlet comparison; not a watershed proof')
    p.add_argument('--dsm',required=True); p.add_argument('--mask',required=True)
    p.add_argument('--bounds',nargs=4,type=float,required=True,metavar=('W','S','E','N'))
    p.add_argument('--start',nargs=2,type=float,required=True,metavar=('LON','LAT'))
    p.add_argument('--end',nargs=2,type=float,required=True,metavar=('LON','LAT'))
    p.add_argument('--line',help='optional JSON coordinate array; overrides the straight chord')
    p.add_argument('--crs',required=True,help='local metric projected CRS, e.g. EPSG code')
    p.add_argument('--offset',type=float,required=True,help='perpendicular distance in metres')
    p.add_argument('--diagnostic-point',type=float,nargs=2,metavar=('LON','LAT'))
    p.add_argument('--basin-outlets',type=float,nargs=4,metavar=('LON1','LAT1','LON2','LAT2'))
    a=p.parse_args()
    if a.offset <= 0: p.error('offset must be positive')
    route=json.load(open(a.line)) if a.line else None
    basin=[a.basin_outlets[:2],a.basin_outlets[2:]] if a.basin_outlets else None
    print(json.dumps(run(a.dsm,a.mask,a.bounds,a.offset,a.start,a.end,a.crs,route,a.diagnostic_point,basin)))
