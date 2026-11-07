#!/usr/bin/env python3
"""Construct an exploratory connected D8 basin interface with WGS84 lengths.

This is a sensitivity candidate, not a selected continental boundary. The
straight endpoint joins and the outlet-root model require independent support.
"""
import argparse, heapq, json
import numpy as np
import rasterio
from rasterio.transform import from_origin, xy
from rasterio.warp import reproject, transform_bounds, Resampling
from shapely.geometry import Point
from shapely.strtree import STRtree
from pyproj import Transformer, Geod
from priority_d8 import drainage
from terrain_basin_screen import checked_shapes, digest_file


def basin_labels(source, source_sha, mask, mask_sha, basins, bounds, roots, resolution):
    with open(source,'rb') as f:
        if digest_file(f)!=source_sha:raise ValueError('source hash mismatch')
    if mask:
        with open(mask,'rb') as f:
            if digest_file(f)!=mask_sha:raise ValueError('mask hash mismatch')
    crs='EPSG:32640'; tgeo=Transformer.from_crs(crs,4326,always_xy=True)
    west,south,east,north=transform_bounds('EPSG:4326',crs,*bounds,densify_pts=21)
    left=np.floor(west/resolution)*resolution;top=np.ceil(north/resolution)*resolution
    width=int(np.ceil((east-left)/resolution));height=int(np.ceil((top-south)/resolution));t=from_origin(left,top,resolution,resolution)
    z=np.full((height,width),np.nan,dtype=np.float32)
    with rasterio.open(source) as ds:reproject(rasterio.band(ds,1),z,src_transform=ds.transform,src_crs=ds.crs,src_nodata=ds.nodata,dst_transform=t,dst_crs=crs,dst_nodata=np.nan,resampling=Resampling.nearest)
    valid=np.isfinite(z)
    if mask:
        m=np.full((height,width),255,dtype=np.uint8)
        with rasterio.open(mask) as ds:reproject(rasterio.band(ds,1),m,src_transform=ds.transform,src_crs=ds.crs,dst_transform=t,dst_crs=crs,dst_nodata=255,resampling=Resampling.nearest)
        valid &= m==0
    features=[]
    for archive,expected,shp in basins:features.extend(checked_shapes(archive,expected,shp,bounds))
    geoms=[f[0] for f in features];basin_ids=[f[1] for f in features];tree=STRtree(geoms)
    flow,_,_=drainage(z.astype('float64'),valid,t,crs);outlets=np.unique(flow[flow>=0]);classes=np.zeros(width*height,dtype=np.uint8)
    for k in outlets:
        r,c=divmod(int(k),width);x,y=xy(t,r,c);point=Point(*tgeo.transform(x,y));hit={basin_ids[i] for i in tree.query(point) if geoms[i].covers(point)}
        matches={index+1 for index,root in enumerate(roots) if root in hit}
        if len(matches)==1:classes[k]=matches.pop()
    labels=np.zeros((height,width),dtype=np.uint8);ok=flow>=0;labels[ok]=classes[flow[ok]]
    return labels,t,tgeo,int(np.count_nonzero(valid&(labels==0)))


def graph_route(labels,transform,to_geo,anchor_a,anchor_b):
    """Trace 1–2 cell-edge interfaces; rank components by WGS84 route+joins."""
    h,w=labels.shape;adj={}
    def edge(u,v):adj.setdefault(u,set()).add(v);adj.setdefault(v,set()).add(u)
    a,b=labels[:,:-1],labels[:,1:]; rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
    for r,c in zip(rr,cc):edge((int(r),int(c+1)),(int(r+1),int(c+1)))
    a,b=labels[:-1,:],labels[1:,:];rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
    for r,c in zip(rr,cc):edge((int(r+1),int(c)),(int(r+1),int(c+1)))
    if not adj:raise ValueError('no shared interface for requested basin pair')
    coords={v:to_geo.transform(*(transform*(v[1],v[0]))) for v in adj};geod=Geod(ellps='WGS84');remaining=set(adj);best=None;component_count=0
    def distance(p,q):return geod.inv(p[0],p[1],q[0],q[1])[2]
    while remaining:
        seed=next(iter(remaining));stack=[seed];remaining.remove(seed);nodes=[]
        while stack:
            u=stack.pop();nodes.append(u)
            for v in adj[u]:
                if v in remaining:remaining.remove(v);stack.append(v)
        component_count+=1
        start=min(nodes,key=lambda v:distance(anchor_a,coords[v]));end=min(nodes,key=lambda v:distance(anchor_b,coords[v]));ja=distance(anchor_a,coords[start]);jb=distance(anchor_b,coords[end]);dist={start:0.};previous={};queue=[(0.,start)]
        while queue:
            length,u=heapq.heappop(queue)
            if length!=dist[u]:continue
            if u==end:break
            for v in adj[u]:
                d=length+distance(coords[u],coords[v])
                if d<dist.get(v,float('inf')):dist[v]=d;previous[v]=u;heapq.heappush(queue,(d,v))
        cost=ja+dist[end]+jb
        if best is None or cost<best[0]:
            path=[end]
            while path[-1]!=start:path.append(previous[path[-1]])
            path.reverse();best=(cost,ja,jb,dist[end],path,len(nodes))
    cost,ja,jb,length,path,size=best
    return {'method':'WGS84 geodesic shortest graph path for each 4-neighbor basin interface component, with nearest-vertex straight joins; rank components by total length',
            'component_count':component_count,'selected_component_nodes':size,'start_join_m':ja,'end_join_m':jb,'divide_length_m':length,'total_length_m':cost,
            'start_interface_lonlat':list(coords[path[0]]),'end_interface_lonlat':list(coords[path[-1]]),
            'coordinates':[list(anchor_a)]+[list(coords[v]) for v in path]+[list(anchor_b)]}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--basin',nargs=3,action='append',required=True);p.add_argument('--bounds',nargs=4,type=float,required=True);p.add_argument('--start',nargs=2,type=float,required=True);p.add_argument('--end',nargs=2,type=float,required=True);p.add_argument('--root',type=int,action='append',required=True);p.add_argument('--resolution',type=float,default=30);p.add_argument('--output',required=True);a=p.parse_args()
    if len(a.root)!=3 or len(set(a.root))!=3 or a.resolution<=0 or bool(a.mask)!=bool(a.mask_sha):raise ValueError('three distinct roots, positive resolution, paired mask and hash required')
    labels,t,geo,unknown=basin_labels(a.source,a.source_sha,a.mask,a.mask_sha,a.basin,a.bounds,a.root,a.resolution);result=graph_route(labels,t,geo,a.start,a.end)
    result.update({'source_sha256':a.source_sha,'mask_sha256':a.mask_sha,'bounds':a.bounds,'root_order':a.root,'resolution_m':a.resolution,'unclassified_valid':unknown,'status':'exploratory, not approved','caveats':['4-neighbor interfaces can meet at a grid corner; not a surveyed divide.','Nearest-node straight joins are not terrain- or source-validated.','Not a global optimum over all endpoint pairs within a component.','HydroBASINS outlet crosswalk and D8 depend on source and model.']})
    with open(a.output,'x') as f:json.dump(result,f)
    print(json.dumps({k:v for k,v in result.items() if k!='coordinates'}))

