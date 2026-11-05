"""Screen provisional historical summit and OSM points in original JAXA DSM.

The historic coordinate comes from an unverified frame fit and visual symbol
position. These samples do not identify a summit or validate a georeference.
"""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window

SHA = {'DSM': '1ae023541b8849a45139b7e9bc250a8327a0a177169d9bdeb2bb54bae01f4f9e',
       'MSK': '2d32d2720f24b96cc7d0e100db47ed725c0e7cfd9d48a1d3ebc769dc29e6ff89',
       'STK': 'ef13b39466563e48d5092e6c4eabf12a800740a2ad79c67a8ec2401b2cc76b0b'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main(folder):
    paths = {k: Path(folder) / ('ALPSMLC30_N044E038_' + k + '.tif') for k in SHA}
    if any(sha(paths[k]) != SHA[k] for k in SHA):
        raise ValueError('source TIFF hash mismatch')
    points = [('historic_frame_estimate', 38 + (6532 - 670.5) * .5 / 9391.5,
               44 + 40/60 - (2840 - 902.9) * (20/60) / 8903.1),
              ('osm_13276920139', 38.3115831, 44.5966511),
              ('osm_785474093', 38.3303118, 44.5944707)]
    with rasterio.open(paths['DSM']) as d, rasterio.open(paths['MSK']) as m, rasterio.open(paths['STK']) as s:
        if any((ds.transform, ds.crs, ds.shape) != (d.transform, d.crs, d.shape) for ds in (m, s)):
            raise ValueError('source rasters are not aligned')
        for name, lon, lat in points:
            row, col = d.index(lon, lat)
            if row < 3 or col < 3 or row + 3 >= d.height or col + 3 >= d.width:
                raise ValueError('sample window outside raster')
            w = Window(col-3, row-3, 7, 7)
            z, mask, stack = (ds.read(1, window=w) for ds in (d, m, s))
            valid = (mask == 0) & (stack > 0) & (z != d.nodata)
            print(json.dumps({'point': name, 'lon': lon, 'lat': lat,
                              'center_dsm_m': int(z[3, 3]), 'center_mask': int(mask[3, 3]),
                              'center_stack': int(stack[3, 3]), 'valid_7x7_count': int(valid.sum()),
                              'valid_7x7_min_m': int(z[valid].min()) if valid.any() else None,
                              'valid_7x7_max_m': int(z[valid].max()) if valid.any() else None}, sort_keys=True))


if __name__ == '__main__':
    main(sys.argv[1])
