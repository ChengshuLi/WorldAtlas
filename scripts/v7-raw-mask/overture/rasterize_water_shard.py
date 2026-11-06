#!/usr/bin/python3
"""Rasterize one Overture water GeoParquet shard to a sparse grid mask.

Experimental candidate, not a recovered historic build. Set PYTHONPATH to a
local PyArrow install. The new output directory must not already exist.
"""
import argparse
import gc
import ctypes
from collections import Counter
import hashlib
import json
import math
import os
import shutil
from pathlib import Path
import sys

import numpy as np

import pyarrow
import pyarrow.parquet as pq
from osgeo import gdal, ogr, osr

gdal.UseExceptions()
ogr.UseExceptions()

POLYGON = (ogr.wkbPolygon, ogr.wkbMultiPolygon)

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def selected(subtype):
    """Use Overture's inland-water subtype classification, not source tags."""
    if not isinstance(subtype,str) or not subtype.strip():
        return 'missing_classification'
    if subtype in ('ocean','physical'):
        return 'excluded_classification'
    return None


def run(source, expected, output, config_path, batch_size=8192):
    source = Path(source).resolve()
    config_path = Path(config_path).resolve()
    output = Path(output).resolve()
    if (source == config_path or source.is_relative_to(output) or config_path.is_relative_to(output)
            or output.is_relative_to(source.parent) or output.is_relative_to(config_path.parent)):
        raise ValueError('output must be outside input directories and must not contain inputs')
    config_bytes = config_path.read_bytes()
    cfg = json.loads(config_bytes)
    if cfg.get('schema') != 'water-shard-candidate-v2' or not cfg.get('selection_notes'):
        raise ValueError('explicit supported configuration and selection notes required')
    grid = cfg['grid']; policy = cfg['policy']
    width, height, west, north, step = (grid[k] for k in ('width','height','west','north','step'))
    tile = cfg.get('tile_size', 1024)
    reserve = cfg.get('minimum_free_bytes', 2 * (1 << 30))
    if not isinstance(reserve, int) or isinstance(reserve, bool) or reserve < 0:
        raise ValueError('invalid free-space reserve')
    if (not isinstance(width,int) or isinstance(width,bool) or width <= 0 or
        not isinstance(height,int) or isinstance(height,bool) or height <= 0 or
        not isinstance(tile,int) or isinstance(tile,bool) or not 1 <= tile <= 4096 or
        not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (west,north,step)) or
        step <= 0 or west < -180 or west+width*step > 180.0000001 or
        north > 90 or north-height*step < -90.0000001):
        raise ValueError('invalid grid or tile size')
    if policy != {'method':'overture-inland-subtype-v1'}:
        raise ValueError('explicit Overture inland subtype policy required')
    if not 1 <= batch_size <= 100000:
        raise ValueError('batch size out of range')
    if len(expected) != 64 or sha256(source) != expected.lower():
        raise ValueError('source SHA-256 does not match expected digest')
    pf = pq.ParquetFile(source, pre_buffer=False)
    md = pf.schema_arrow.metadata or {}
    geo = json.loads(md[b'geo'])
    if geo['primary_column'] != 'geometry' or geo['columns']['geometry'].get('encoding') != 'WKB':
        raise ValueError('unexpected GeoParquet geometry encoding or column')
    # GeoParquet specifies OGC:CRS84 when crs is absent. Refuse a different or
    # explicitly null CRS rather than silently assume longitude/latitude.
    if 'crs' in geo['columns']['geometry']:
        raise ValueError('explicit CRS requires independent review; expected GeoParquet default OGC:CRS84')
    if shutil.disk_usage(output.parent).free < reserve:
        raise ValueError('free disk below configured reserve')
    os.mkdir(output)
    out = Path(output)
    raster = gdal.GetDriverByName('GTiff').Create(str(out/'water.tif'), width, height, 1,
        gdal.GDT_Byte, options=['TILED=YES', 'BLOCKXSIZE=512', 'BLOCKYSIZE=512',
                               'NBITS=1', 'COMPRESS=DEFLATE', 'SPARSE_OK=YES', 'BIGTIFF=YES'])
    raster.SetGeoTransform((west, step, 0, north, 0, -step))
    srs = osr.SpatialReference(); srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    raster.SetSpatialRef(srs)
    counts = Counter(); invalid = []
    driver = ogr.GetDriverByName('Memory')
    # A feature's raster burn is identical across batches because the operation
    # is a monotone union (the mask is initialized to zero and burns only 1).
    for batch_no, batch in enumerate(pf.iter_batches(batch_size=batch_size,
            columns=['id', 'subtype', 'geometry'], use_threads=False)):
        if shutil.disk_usage(out).free < reserve:
            raise ValueError('free disk below configured reserve; partial output preserved')
        tiles = {}
        for item in batch.to_pylist():
            counts['rows'] += 1
            reason = selected(item['subtype'])
            if reason:
                counts[reason] += 1
                continue
            if item['geometry'] is None:
                raise ValueError(f"missing geometry: {item['id']}")
            geom = ogr.CreateGeometryFromWkb(item['geometry'])
            if geom is None or geom.IsEmpty():
                raise ValueError(f"invalid or empty WKB geometry: {item['id']}")
            if ogr.GT_Flatten(geom.GetGeometryType()) not in POLYGON:
                counts['non_polygon'] += 1
                continue
            if not geom.IsValid():
                invalid.append(item['id'])
                counts['invalid_polygon'] += 1
                # Do not burn invalid geometry, repair it, or silently omit it.
                continue
            xmin, xmax, ymin, ymax = geom.GetEnvelope()
            x0 = max(0, math.floor((xmin - west) / step)); x1 = min(width-1, math.floor((xmax - west) / step))
            y0 = max(0, math.floor((north - ymax) / step)); y1 = min(height-1, math.floor((north - ymin) / step))
            if x0 <= x1 and y0 <= y1:
                for ty in range(y0 // tile, y1 // tile + 1):
                    for tx in range(x0 // tile, x1 // tile + 1):
                        tiles.setdefault((tx,ty), []).append(item['geometry'])
            counts['polygons'] += 1
        for (tx, ty), geometries in tiles.items():
            x, y = tx*tile, ty*tile
            w, h = min(tile, width-x), min(tile, height-y)
            target = gdal.GetDriverByName('MEM').Create('', w, h, 1, gdal.GDT_Byte)
            target.SetGeoTransform((west+x*step, step, 0, north-y*step, 0, -step))
            target.GetRasterBand(1).WriteArray(raster.GetRasterBand(1).ReadAsArray(x,y,w,h))
            ds = driver.CreateDataSource(''); layer = ds.CreateLayer('water', srs, ogr.wkbUnknown)
            definition = layer.GetLayerDefn()
            for wkb in geometries:
                feat = ogr.Feature(definition); feat.SetGeometry(ogr.CreateGeometryFromWkb(wkb)); layer.CreateFeature(feat)
            gdal.RasterizeLayer(target, [1], layer, burn_values=[1])
            raster.GetRasterBand(1).WriteArray(target.ReadAsArray(), x, y)
            layer = None; ds = None; target = None
        # Release temporary Arrow, OGR, and allocator buffers between batches.
        tiles = None; batch = None; item = None; geom = None; feat = None; definition = None
        gc.collect()
        pyarrow.default_memory_pool().release_unused()
        try:
            trim = getattr(ctypes.CDLL(None), 'malloc_trim', None)
            if trim: trim(0)
        except (AttributeError, OSError):
            pass
        rss = 'unavailable'
        try:
            rss = next((line for line in Path('/proc/self/status').read_text().splitlines()
                        if line.startswith('VmRSS:')), 'unavailable')
        except OSError:
            pass
        print(json.dumps({'rows': counts['rows'], 'polygons': counts['polygons'],
                          'invalid_polygon': counts['invalid_polygon'], 'rss':rss,
                          'gdal_cache_used_bytes':gdal.GetCacheUsed()}), flush=True)
    raster.FlushCache(); raster = None
    if sha256(source) != expected.lower():
        raise ValueError('source changed during processing')
    if config_path.read_bytes() != config_bytes:
        raise ValueError('configuration changed during processing')
    if invalid:
        with (out/'invalid-feature-ids.json').open('x') as f: f.write(json.dumps(invalid, indent=2)+'\n')
    report = {'status': 'incomplete-input-issues' if invalid or counts['missing_classification'] else 'candidate-only',
       'source':str(source), 'source_sha256':expected.lower(), 'rows_in_source':pf.metadata.num_rows,
       'script_sha256':sha256(Path(__file__).resolve()),
       'counts':dict(counts), 'invalid_feature_ids': 'invalid-feature-ids.json' if invalid else None,
       'policy': policy, 'selection_notes':cfg['selection_notes'],
       'configuration_sha256':hashlib.sha256(config_bytes).hexdigest(),
       'geometry_policy':'GEOS validity checked; invalid geometries excluded and IDs reported; no repair',
       'grid': {'width':width, 'height':height, 'west':west, 'north':north, 'step':step},
       'rasterization':f'GDAL default polygon rasterization, ALL_TOUCHED off; values unioned per batch on {tile}-cell tiles',
       'runtime':{'python':sys.version, 'pyarrow':pyarrow.__version__, 'gdal':gdal.VersionInfo('--version'),
                  'geos':'.'.join(str(f()) for f in (ogr.GetGEOSVersionMajor, ogr.GetGEOSVersionMinor, ogr.GetGEOSVersionMicro))},
       'output_sha256':sha256(out/'water.tif'),
       'limitations':'Candidate water mask only, not a historical or complete physical mask. Review invalid features and compare against preserved references before use.'}
    with (out/'report.json').open('x') as f: f.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source'); p.add_argument('sha256'); p.add_argument('config'); p.add_argument('new_output_directory')
    p.add_argument('--batch-size', type=int, default=8192)
    a = p.parse_args()
    if not 1 <= a.batch_size <= 100000:
        p.error('batch size must be between 1 and 100000')
    try: run(a.source, a.sha256, a.new_output_directory, a.config, a.batch_size)
    except Exception as e:
        print(f'failed: {e}', file=sys.stderr); sys.exit(1)
