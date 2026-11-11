"""Experimental WGS84 terrain flow labels from supplied stream seed masks.

Mask boundaries and raster crop edges are artificial outlets. Seed labels do
not establish actual watercourses or validate source geography. The model is
not a boundary-selection tool.
"""
from collections import Counter
import numpy as np
from pyproj import Geod, CRS
from priority_flood import priority_flood

GEOD=Geod(ellps='WGS84')


def flow_graph(elevation,valid,transform,crs):
    try:
        crs_value=CRS.from_user_input(crs)
    except Exception as exc:
        raise ValueError('explicit EPSG:4326 raster CRS required') from exc
    if crs_value.to_epsg()!=4326:
        raise ValueError('explicit EPSG:4326 raster CRS required')
    if not hasattr(transform,'a') or not all(np.isfinite(v) for v in (transform.a,transform.b,transform.c,transform.d,transform.e,transform.f)) or transform.b or transform.d or transform.a<=0 or transform.e>=0:
        raise ValueError('finite north-up unrotated WGS84 raster transform required')
    z=np.asarray(elevation,dtype=float);valid=np.asarray(valid,dtype=bool)
    if z.ndim!=2 or not (-180<=transform.c<=180 and -180<=transform.c+z.shape[1]*transform.a<=180 and -90<=transform.f<=90 and -90<=transform.f+z.shape[0]*transform.e<=90):
        raise ValueError('WGS84 raster extent outside longitude/latitude bounds')
    filled,parent=priority_flood(z,valid);h,w=z.shape
    rows,cols=np.indices((h,w));lon=transform.c+(cols+.5)*transform.a;lat=transform.f+(rows+.5)*transform.e
    best=np.zeros((h,w));nxt=np.array(parent,copy=True)
    for dr in (-1,0,1):
        for dc in (-1,0,1):
            if not(dr or dc):continue
            src=(slice(max(0,-dr),min(h,h-dr)),slice(max(0,-dc),min(w,w-dc)))
            dst=(slice(max(0,dr),min(h,h+dr)),slice(max(0,dc),min(w,w+dc)))
            _,_,distance=GEOD.inv(lon[src],lat[src],lon[dst],lat[dst])
            if np.any(~np.isfinite(distance)) or np.any(distance<=0):raise ValueError('invalid WGS84 spacing')
            slope=np.divide(filled[src]-filled[dst],distance,out=np.zeros_like(distance),where=distance>0)
            eligible=valid[src]&valid[dst]&(slope>best[src]);best[src][eligible]=slope[eligible]
            nxt[src][eligible]=(rows[dst]*w+cols[dst])[eligible]
    return filled,nxt


def trace_to_seeds(next_index,valid,seeds):
    """Return 0 invalid, 1/2 seed destination, 3 unresolved; cycles unresolved."""
    valid=np.asarray(valid,dtype=bool);nxt=np.asarray(next_index);seed=np.asarray(seeds)
    if valid.ndim!=2 or nxt.shape!=valid.shape or seed.shape!=valid.shape:
        raise ValueError('matching two-dimensional arrays required')
    if np.any(~np.isin(seed,[0,1,2])) or np.any((seed>0)&~valid):
        raise ValueError('seed masks must be 0/1/2 and valid')
    labels=seed.ravel().astype('uint8').copy();vf=valid.ravel();nf=nxt.ravel();counts=Counter()
    for start in np.flatnonzero(vf):
        if labels[start]:continue
        path=[];seen=set();v=int(start)
        while 0<=v<len(vf) and vf[v] and labels[v]==0 and v not in seen:
            seen.add(v);path.append(v);v=int(nf[v])
        if 0<=v<len(vf) and vf[v] and labels[v] in (1,2):label=labels[v]
        else:
            label=3;counts['cycle' if v in seen else 'unresolved']+=1
        for i in path:labels[i]=label
    return labels.reshape(valid.shape),dict(counts)
