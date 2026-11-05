#!/usr/bin/env python3
"""Build a reproducible research crop from checksum-pinned DEM tiles."""
import argparse,hashlib,json,math,os
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject,Resampling

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def crop(inputs,bounds,resolution,crs,resampling,out):
    w,s,e,n=bounds;width=round((e-w)/resolution);height=round((n-s)/resolution)
    if width<1 or height<1 or width*height>16000000 or not math.isclose(w+width*resolution,e) or not math.isclose(s+height*resolution,n):raise ValueError('invalid crop dimensions')
    trans=from_origin(w,n,resolution,resolution);dest=np.full((height,width),np.nan,dtype='float32');source_meta=[]
    for path,expected in inputs:
        actual=digest(path)
        if actual!=expected:raise ValueError('DEM source checksum mismatch')
        with rasterio.open(path) as src:
            if src.crs is None:raise ValueError('source CRS missing')
            data=np.full((height,width),np.nan,dtype='float32')
            reproject(source=rasterio.band(src,1),destination=data,src_transform=src.transform,src_crs=src.crs,src_nodata=src.nodata,dst_transform=trans,dst_crs=crs,dst_nodata=np.nan,resampling=getattr(Resampling,resampling),num_threads=1)
            select=np.isnan(dest)&np.isfinite(data);dest[select]=data[select]
            source_meta.append({'sha256':actual,'shape':[src.height,src.width],'crs':str(src.crs),'nodata':src.nodata,'filled_pixels':int(np.count_nonzero(select))})
    fd=os.open(out,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    with rasterio.open(out,'w',driver='GTiff',width=width,height=height,count=1,dtype='float32',crs=crs,transform=trans,nodata=np.nan,compress='deflate') as f:f.write(dest,1)
    return {'bounds':bounds,'crs':crs,'resolution':resolution,'resampling':resampling,'shape':[height,width],'valid_fraction':float(np.isfinite(dest).mean()),'output_sha256':digest(out),'sources':source_meta,'method':'first-valid-source mosaic of reprojected pixels'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',nargs=2,action='append',required=True,metavar=('PATH','SHA256'));p.add_argument('--bounds',type=float,nargs=4,required=True);p.add_argument('--resolution',type=float,required=True);p.add_argument('--crs',required=True);p.add_argument('--resampling',choices=['nearest','bilinear'],default='nearest');p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(crop(a.input,a.bounds,a.resolution,a.crs,a.resampling,a.output)))
