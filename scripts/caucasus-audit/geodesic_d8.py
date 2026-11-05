"""Strict downhill raster tracing with WGS84 neighbor distances.

This is a research diagnostic. Pixel pits, DSM artifacts, and an unconditioned
surface can prevent reaching the actual outlet. A traced path is not a stream.
"""
import argparse
import json
import math
import numpy as np
import rasterio
from pyproj import Geod

GEOD = Geod(ellps='WGS84')


def trace(values, valid, affine, start, max_steps=1500):
    if values.ndim != 2 or valid.shape != values.shape or max_steps < 1:
        raise ValueError('invalid raster dimensions or step limit')
    if affine.b or affine.d:
        raise ValueError('north-up, unrotated raster required')
    row, col = (int(v) for v in start)
    height, width = values.shape
    coords = []
    for _ in range(max_steps):
        if row < 1 or col < 1 or row >= height-1 or col >= width-1:
            return coords, 'tile_edge'
        if not valid[row-1:row+2, col-1:col+2].all():
            return coords, 'invalid_neighbor'
        lon, lat = affine * (col+.5, row+.5)
        coords.append((lon, lat))
        best, target = 0.0, None
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if not (dr or dc): continue
                lon2, lat2 = affine * (col+dc+.5, row+dr+.5)
                _, _, distance = GEOD.inv(lon, lat, lon2, lat2)
                if not math.isfinite(distance) or distance <= 0:
                    raise ValueError('invalid geodesic pixel spacing')
                slope = (float(values[row,col])-float(values[row+dr,col+dc]))/distance
                if slope > best:
                    best, target = slope, (row+dr, col+dc)
        if target is None:
            return coords, 'pit_or_flat'
        row, col = target
    return coords, 'step_cap'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dsm',required=True);p.add_argument('--mask',required=True)
    p.add_argument('--stack',required=True);p.add_argument('--starts',required=True)
    p.add_argument('--output',required=True);p.add_argument('--max-steps',type=int,default=1500)
    a=p.parse_args()
    with rasterio.open(a.dsm) as ds, rasterio.open(a.mask) as ms, rasterio.open(a.stack) as st:
        if ds.crs is None or ds.crs.to_epsg()!=4326 or ds.crs!=ms.crs or ds.crs!=st.crs or ds.shape!=ms.shape or ds.shape!=st.shape or ds.transform!=ms.transform or ds.transform!=st.transform:
            raise ValueError('aligned WGS84 DSM/MSK/STK required')
        if ds.nodata is None:raise ValueError('DSM nodata value required')
        values=ds.read(1);mask=ms.read(1);stack=st.read(1)
        valid=(mask==0)&(stack>0)&(values!=ds.nodata)&np.isfinite(values)
        results=[]
        for lon,lat in json.load(open(a.starts)):
            row,col=ds.index(lon,lat);coords,status=trace(values,valid,ds.transform,(row,col),a.max_steps)
            results.append({'start':[lon,lat],'status':status,'coordinates':coords})
    with open(a.output,'x') as out:json.dump(results,out)

if __name__=='__main__':main()
