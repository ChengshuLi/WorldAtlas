#!/usr/bin/env python3
"""Crosswalk local D8 outlets to three basin roots; research diagnostic only."""
import argparse, json
import numpy as np
import rasterio
from rasterio.transform import from_origin, rowcol, xy
from rasterio.warp import reproject, transform_bounds, Resampling
from shapely.geometry import Point
from shapely.strtree import STRtree
from pyproj import Transformer
from priority_d8 import drainage
from terrain_basin_screen import checked_shapes, digest_file


def nearest_transitions(labels, roots, left, top, resolution, sx, sy, to_geo):
    height,width=labels.shape; boundaries={}
    for i in range(1,len(roots)+1):
        for j in range(i+1,len(roots)+1):
            candidates=[]
            for dr,dc in ((1,0),(0,1)):
                a=labels[:height-dr,:width-dc];b=labels[dr:,dc:]; y,x=np.where(((a==i)&(b==j))|((a==j)&(b==i)))
                if len(x):
                    mx=left+(x+.5+dc/2)*resolution;my=top-(y+.5+dr/2)*resolution; distances=np.hypot(mx-sx,my-sy);q=int(np.argmin(distances));candidates.append((float(distances[q]),float(mx[q]),float(my[q])))
            if candidates:
                d,x,y=min(candidates);boundaries[f'{roots[i-1]}:{roots[j-1]}']={'distance_m':d,'point_lonlat':list(to_geo.transform(x,y))}
    return boundaries


def run(source, source_sha, source_mask, mask_sha, basins, bounds, route_point, roots, resolution):
    if digest_file(open(source,'rb')) != source_sha: raise ValueError('DSM checksum mismatch')
    if source_mask and digest_file(open(source_mask,'rb')) != mask_sha: raise ValueError('mask checksum mismatch')
    crs='EPSG:32640'; to_grid=Transformer.from_crs(4326,crs,always_xy=True); to_geo=Transformer.from_crs(crs,4326,always_xy=True)
    west,south,east,north=transform_bounds('EPSG:4326',crs,*bounds,densify_pts=21)
    left=np.floor(west/resolution)*resolution; top=np.ceil(north/resolution)*resolution
    width=int(np.ceil((east-left)/resolution)); height=int(np.ceil((top-south)/resolution))
    transform=from_origin(left,top,resolution,resolution)
    z=np.full((height,width),np.nan,dtype=np.float32)
    with rasterio.open(source) as ds:
        reproject(rasterio.band(ds,1),z,src_transform=ds.transform,src_crs=ds.crs,src_nodata=ds.nodata,dst_transform=transform,dst_crs=crs,dst_nodata=np.nan,resampling=Resampling.nearest)
    valid=np.isfinite(z)
    if source_mask:
        m=np.full((height,width),255,dtype=np.uint8)
        with rasterio.open(source_mask) as ds:
            reproject(rasterio.band(ds,1),m,src_transform=ds.transform,src_crs=ds.crs,dst_transform=transform,dst_crs=crs,dst_nodata=255,resampling=Resampling.nearest)
        valid &= m==0
    features=[]
    for archive,expected,shp in basins: features.extend(checked_shapes(archive,expected,shp,bounds))
    geoms=[f[0] for f in features]; ids=[f[1] for f in features]; tree=STRtree(geoms)
    flow,_,_=drainage(z.astype('float64'),valid,resolution); outlets=np.unique(flow[flow>=0]); classes=np.zeros(height*width,dtype=np.uint8); status={'unmatched':0,'conflict':0}
    for k in outlets:
        row,col=divmod(int(k),width); x,y=xy(transform,row,col); point=Point(*to_geo.transform(x,y))
        hit={ids[i] for i in tree.query(point) if geoms[i].covers(point)}; matches={index+1 for index,root in enumerate(roots) if root in hit}
        if len(matches)==1: classes[k]=matches.pop()
        elif len(matches)>1: status['conflict']+=1
        else: status['unmatched']+=1
    labels=np.zeros((height,width),dtype=np.uint8); ok=flow>=0;labels[ok]=classes[flow[ok]]
    sx,sy=to_grid.transform(*route_point);r,c=rowcol(transform,sx,sy)
    if not (0<=r<height and 0<=c<width and valid[r,c]):raise ValueError('target outside valid grid')
    boundaries=nearest_transitions(labels,roots,left,top,resolution,sx,sy,to_geo)
    return {'bounds':bounds,'crs':crs,'resolution_m':resolution,'shape':[height,width], 'source_sha256':source_sha,'mask_sha256':mask_sha,'valid_cells':int(valid.sum()),'unrouted_valid':int(np.count_nonzero(valid&(flow<0))),'classes':{str(root):int((labels==i+1).sum()) for i,root in enumerate(roots)},'unclassified_valid':int(np.count_nonzero(valid&(labels==0))),'outlet_unmatched_or_conflict':status,'point':route_point,'point_class':int(labels[r,c]),'root_order':roots,'nearest_group_transitions':boundaries,'caveat':'Local source-relative DSM D8 routing and HydroBASINS outlet classes; unknown cells, window edges, masks and DSM artifacts prevent treating modeled transitions as surveyed divides.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--basin',nargs=3,action='append',required=True);p.add_argument('--bounds',nargs=4,type=float,required=True);p.add_argument('--point',nargs=2,type=float,required=True);p.add_argument('--root',type=int,action='append',required=True);p.add_argument('--resolution',type=float,default=30);p.add_argument('--output',required=True);a=p.parse_args()
    if len(a.root)!=3 or len(set(a.root))!=3 or a.resolution<=0 or bool(a.mask)!=bool(a.mask_sha):raise ValueError('three distinct roots, positive resolution, paired mask and hash required')
    result=run(a.source,a.source_sha,a.mask,a.mask_sha,a.basin,a.bounds,a.point,a.root,a.resolution)
    with open(a.output,'x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
