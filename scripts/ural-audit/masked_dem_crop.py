#!/usr/bin/env python3
"""Mosaic checksum-pinned DEM/mask pairs onto one projected research grid."""
import argparse
import hashlib
import json
import math
import os
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling


def checksum(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def crop(pairs, bounds, resolution, crs, resampling, output):
    west, south, east, north = bounds
    if resolution <= 0:
        raise ValueError('resolution must be positive')
    width, height = round((east - west) / resolution), round((north - south) / resolution)
    if width < 1 or height < 1 or width * height > 16000000 or not math.isclose(west + width * resolution, east) or not math.isclose(south + height * resolution, north):
        raise ValueError('invalid grid dimensions')
    transform = from_origin(west, north, resolution, resolution)
    dest = np.full((height, width), np.nan, dtype=np.float32)
    sources = []
    for dem, dem_sha, mask, mask_sha in pairs:
        if checksum(dem) != dem_sha or checksum(mask) != mask_sha:
            raise ValueError('source hash mismatch')
        with rasterio.open(dem) as ds, rasterio.open(mask) as ms:
            if ds.crs is None or ds.crs != ms.crs or ds.transform != ms.transform or ds.shape != ms.shape:
                raise ValueError('DEM and mask grids do not align')
            z = ds.read(1).astype('float32')
            valid = np.isfinite(z) & (ds.read_masks(1) != 0) & (ms.read(1) == 0)
            if ds.nodata is not None and np.isfinite(ds.nodata):
                valid &= z != ds.nodata
            z[~valid] = np.nan
            data = np.full_like(dest, np.nan)
            reproject(z, data, src_transform=ds.transform, src_crs=ds.crs, src_nodata=np.nan,
                      dst_transform=transform, dst_crs=crs, dst_nodata=np.nan,
                      resampling=getattr(Resampling, resampling), num_threads=1)
            select = np.isnan(dest) & np.isfinite(data)
            dest[select] = data[select]
            sources.append({'dem_sha256': dem_sha, 'mask_sha256': mask_sha, 'filled_pixels': int(select.sum())})
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with rasterio.open(output, 'w', driver='GTiff', width=width, height=height, count=1, dtype='float32', crs=crs, transform=transform, nodata=np.nan, compress='deflate') as ds:
        ds.write(dest, 1)
    return {'bounds': bounds, 'crs': crs, 'resolution': resolution, 'resampling': resampling,
            'mask_rule': 'accept code 0 only', 'valid_fraction': float(np.isfinite(dest).mean()),
            'sources': sources, 'output_sha256': checksum(output)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pair', nargs=4, action='append', required=True, metavar=('DEM', 'DEM_SHA', 'MASK', 'MASK_SHA'))
    p.add_argument('--bounds', nargs=4, type=float, required=True)
    p.add_argument('--resolution', type=float, required=True)
    p.add_argument('--crs', required=True)
    p.add_argument('--resampling', choices=['nearest', 'bilinear'], default='nearest')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(crop(a.pair, a.bounds, a.resolution, a.crs, a.resampling, a.output)))
