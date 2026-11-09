#!/usr/bin/env python3
"""Reproduce the two Ural northern-gap rasters from pinned raw ArcticDEM tiles.

Place the three R2-reassembled provider tiles in --source-dir with the names
below. Outputs are temporary derived inputs, not new raw source assets.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

INPUTS = {'ural-arctic-gap00.tif': '0207e55aec04678895aa73ead434ff189eb0c0a3a8badf553a831821a13eabbd',
          'ural-arctic-gap02a.tif': 'dab46d70f16e3c6ee397f342167458513e2d6697898b86a5a2c1e447a437987a',
          'ural-arctic-gap02b.tif': '7a02a4d2ad464323c56bd953c7841369ff2183be243c0931e39b3894031549c3'}
CASES = [('ural-gap00-12km-nearest.tif', ['ural-arctic-gap00.tif'],
          (2750336, 731372, 10, 10), (1200, 1200),
          '3dbc4da15948791a70b78346eaba7174ccb464226bf9adf292184757f7c6af6b'),
         ('ural-gap02-16km-nearest.tif', ['ural-arctic-gap02a.tif', 'ural-arctic-gap02b.tif'],
          (2992420, 782560, 10, 10), (1600, 1600),
          'dc04a55cdc1b742a21dfdb1f050f493c621a6ae0f3f66f7cdd0042c2cb893635')]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def build_crops(source_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, expected in INPUTS.items():
        if sha(source_dir / name) != expected:
            raise ValueError('raw source hash mismatch: ' + name)
    results = []
    for name, sources, origin, shape, expected in CASES:
        output = output_dir / name
        if output.exists():
            raise FileExistsError(output)
        transform = from_origin(*origin)
        data = np.full(shape, np.nan, dtype='float32')
        for source in sources:
            with rasterio.open(source_dir / source) as ds:
                reproject(rasterio.band(ds, 1), data, src_transform=ds.transform,
                          src_crs=ds.crs, src_nodata=ds.nodata,
                          dst_transform=transform, dst_crs='EPSG:3413',
                          dst_nodata=np.nan, resampling=Resampling.nearest,
                          init_dest_nodata=False)
        with rasterio.open(output, 'w', driver='GTiff', dtype='float32',
                           nodata=np.nan, width=shape[1], height=shape[0], count=1,
                           crs='EPSG:3413', transform=transform, compress='deflate') as dst:
            dst.write(data, 1)
        actual = sha(output)
        if actual != expected:
            raise ValueError('derived raster differs from pinned result: ' + name)
        results.append({'file': name, 'sha256': actual,
                        'nodata_cells': int(np.count_nonzero(np.isnan(data)))})
    for name, expected in INPUTS.items():
        if sha(source_dir / name) != expected:
            raise ValueError('source changed during reproduction: ' + name)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    results = build_crops(args.source_dir, args.output_dir)
    print(json.dumps({'outputs': results, 'resampling': 'nearest',
                      'note': 'Source order is significant in overlapping valid pixels.'}, sort_keys=True))


if __name__ == '__main__':
    main()
