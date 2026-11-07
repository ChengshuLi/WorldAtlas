#!/usr/bin/env python3
"""WGS84 geodesic terrain cross-sections along a proposed connector join."""
import argparse, json
import numpy as np
import rasterio
from pyproj import Geod
from terrain_basin_screen import digest_file

GEOD=Geod(ellps='WGS84')


def station_points(a,b,n,offset):
    if n<=0 or offset<=0:raise ValueError('positive station count and offset required')
    bearing,_,length=GEOD.inv(*a,*b)
    if length<=0:raise ValueError('identical endpoints')
    centers=[];left=[];right=[]
    for i in range(1,n+1):
        x,y,back=GEOD.fwd(a[0],a[1],bearing,length*i/(n+1));forward=(back+180)%360
        centers.append((x,y));left.append(GEOD.fwd(x,y,forward-90,offset)[:2]);right.append(GEOD.fwd(x,y,forward+90,offset)[:2])
    return length,centers,left,right


def profile(source,expected,mask,mask_sha,a,b,n,offsets):
    with open(source,'rb') as f:
        if digest_file(f)!=expected:raise ValueError('source checksum mismatch')
    if mask:
        with open(mask,'rb') as f:
            if digest_file(f)!=mask_sha:raise ValueError('mask checksum mismatch')
    result={}
    with rasterio.open(source) as ds:
        ms=rasterio.open(mask) if mask else None
        try:
            if ms and (ms.crs!=ds.crs or ms.transform!=ds.transform or ms.shape!=ds.shape):raise ValueError('mask grid mismatch')
            for offset in offsets:
                length,c,l,r=station_points(a,b,n,offset);coords=c+l+r;v=np.array([x[0] for x in ds.sample(coords)],dtype=float);ok=np.isfinite(v)
                ok &= np.array([ds.bounds.left<=x<ds.bounds.right and ds.bounds.bottom<y<=ds.bounds.top for x,y in coords])
                if ds.nodata is not None:ok &= v!=ds.nodata
                if ms:ok &= np.array([x[0] for x in ms.sample(coords)])==0
                mids,ls,rs=v[:n],v[n:2*n],v[2*n:];good=ok[:n]&ok[n:2*n]&ok[2*n:]
                result[str(offset)]={'valid':int(good.sum()),'excluded':int((~good).sum()),'center_higher_than_both':int(np.sum(good&(mids>ls)&(mids>rs))),'center_range_m':[float(np.min(mids[good])),float(np.max(mids[good]))] if good.any() else None}
        finally:
            if ms:ms.close()
    return {'start':a,'end':b,'length_wgs84_m':length,'n_stations':n,'offsets_m':result,'source_sha256':expected,'mask_sha256':mask_sha,'method':'WGS84 geodesic stationing and perpendicular offsets; nearest raster pixel','caveat':'DSM elevation cross-sections are a local sensitivity screen, not proof of drainage separation or a surveyed ridge.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--start',nargs=2,type=float,required=True);p.add_argument('--end',nargs=2,type=float,required=True);p.add_argument('--stations',type=int,default=19);p.add_argument('--offset',type=float,action='append',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if bool(a.mask)!=bool(a.mask_sha):raise ValueError('mask and mask hash required together')
    r=profile(a.source,a.source_sha,a.mask,a.mask_sha,a.start,a.end,a.stations,a.offset)
    with open(a.output,'x') as f:json.dump(r,f,indent=2)
    print(json.dumps(r))
