#!/usr/bin/python3
"""Experimental physical land mask builder. Not a reconstruction claim."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()
ogr.UseExceptions()


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def checked_files(spec):
    """All dataset files explicitly pinned; require mandatory shapefile parts."""
    files = {str(Path(f['path']).resolve()): f['sha256'] for f in spec['files']}
    dataset = str(Path(spec['dataset']).resolve())
    if dataset not in files:
        raise ValueError('dataset must be among hash-pinned files')
    if dataset.lower().endswith('.shp'):
        stem = Path(dataset).with_suffix('')
        for ext in ('.shp', '.shx', '.dbf', '.prj'):
            if str(stem.with_suffix(ext)) not in files:
                raise ValueError('shapefile needs pinned .shp, .shx, .dbf and .prj')
        # Sidecars may change interpretation; no untracked companion permitted.
        for p in stem.parent.glob(stem.name + '.*'):
            if p.is_file() and str(p.resolve()) not in files:
                raise ValueError(f'unpinned shapefile companion: {p}')
    for p, expected in files.items():
        if len(expected) != 64 or sha(p) != expected.lower():
            raise ValueError(f'input digest mismatch: {p}')
    return files


def open_layer(spec):
    ds = ogr.Open(spec['dataset'], 0)
    if ds is None:
        raise ValueError(f"cannot open dataset: {spec['dataset']}")
    layer = ds.GetLayerByName(spec['layer']) if spec.get('layer') else ds.GetLayer(0)
    if layer is None:
        raise ValueError('layer not found')
    srs = layer.GetSpatialRef()
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(4326)
    if srs is not None:
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if srs is None or not srs.IsSame(expected):
        raise ValueError('layer must explicitly declare EPSG:4326; reprojection is not implicit')
    if 'where' not in spec:
        raise ValueError('selection predicate must be explicit; null means all features')
    if spec['where'] is not None:
        layer.SetAttributeFilter(spec['where'])
    count = 0
    for feat in layer:
        geom = feat.GetGeometryRef()
        if geom is None or geom.IsEmpty():
            raise ValueError(f'empty geometry at feature {feat.GetFID()}')
        if ogr.GT_Flatten(geom.GetGeometryType()) not in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
            raise ValueError(f'nonpolygon geometry at feature {feat.GetFID()}')
        if not geom.IsValid():
            raise ValueError(f'invalid geometry at feature {feat.GetFID()} (no repair performed)')
        count += 1
    layer.ResetReading()
    if not count:
        raise ValueError('selection yielded no features')
    return ds, layer, count


def validate_reference(ref, width, height):
    for key in ('rows', 'runs'):
        if sha(ref[key]['path']) != ref[key]['sha256']:
            raise ValueError(f'reference {key} digest mismatch')
    rows = np.memmap(ref['rows']['path'], dtype='<u4', mode='r')
    runs = np.memmap(ref['runs']['path'], dtype='<u4', mode='r')
    if len(rows) != height + 1 or len(runs) % 2 or rows[0] != 0 or rows[-1] != len(runs)//2:
        raise ValueError('invalid reference stream lengths/offsets')
    if np.any(rows[1:] < rows[:-1]):
        raise ValueError('reference offsets not monotone')
    return rows, runs.reshape(-1, 2)


def compare_row(values, ref_runs, width):
    ends = ref_runs[:, 0]
    codes = ref_runs[:, 1]
    if not len(ends) or ends[-1] != width or np.any(ends[1:] <= ends[:-1]) or np.any(~np.isin(codes, [1, 17])):
        raise ValueError('invalid reference row')
    actual_ends = np.flatnonzero(np.r_[values[1:] != values[:-1], True]) + 1
    cuts = np.unique(np.r_[0, ends, actual_ends])
    x = cuts[:-1]
    old = codes[np.searchsorted(ends, x, side='right')]
    new = values[x]
    bad = old != new
    return int(np.diff(cuts)[bad].sum()), [(int(a), int(b), int(c), int(d)) for a, b, c, d in zip(x[bad], cuts[1:][bad], old[bad], new[bad])]


def build(config_path, output):
    config_bytes = Path(config_path).read_bytes()
    cfg = json.loads(config_bytes)
    if cfg.get('schema') != 'raw-physical-mask-prototype-v1':
        raise ValueError('unknown configuration schema')
    grid = cfg['grid']
    width, height, step = grid['width'], grid['height'], grid['step']
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0 or not 0 < step <= 360:
        raise ValueError('invalid grid')
    west, north = grid['west'], grid['north']
    if not all(math.isfinite(v) for v in (west, north, step)) or west < -180 or west+width*step > 180.0000001 or north > 90 or north-height*step < -90.0000001:
        raise ValueError('grid must stay within geographic bounds')
    if not cfg.get('selection_notes'):
        raise ValueError('selection_notes must explain provenance and unresolved assumptions')
    all_files = {}
    opened = {}
    for key in ('land', 'water'):
        if not isinstance(cfg[key], list) or not cfg[key]:
            raise ValueError(f'{key} must be a nonempty list of selected datasets')
        opened[key] = []
        for spec in cfg[key]:
            for path, digest in checked_files(spec).items():
                if path in all_files and all_files[path] != digest:
                    raise ValueError(f'conflicting digests for {path}')
                all_files[path] = digest
            opened[key].append(open_layer(spec))
    ref = validate_reference(cfg['reference'], width, height) if cfg.get('reference') else None
    # Must create a new output directory; never overwrite an existing checkpoint.
    os.mkdir(output)
    out = Path(output)
    rows_path, runs_path = out/'rows.u32le', out/'runs.u32le'
    offsets = [0]
    mismatch = 0
    samples = []
    strip = cfg.get('strip_rows', 128)
    if not isinstance(strip, int) or not 1 <= strip <= 1024:
        raise ValueError('strip_rows must be an integer from 1 to 1024')
    diff_path = out/'mismatch-spans.jsonl'
    mismatch_intervals = 0
    with runs_path.open('xb') as runs_out, diff_path.open('x') as diff_out:
        for y in range(0, height, strip):
            n = min(strip, height-y)
            raster = gdal.GetDriverByName('MEM').Create('', width, n, 1, gdal.GDT_Byte)
            x0, north = grid['west'], grid['north'] - y*step
            raster.SetGeoTransform((x0, step, 0, north, 0, -step))
            raster.GetRasterBand(1).Fill(1)
            for key, burn in (('land', 17), ('water', 1)):
                for _, layer, _ in opened[key]:
                    layer.SetSpatialFilterRect(x0, north-n*step, x0+width*step, north)
                    layer.ResetReading()
                    # ALL_TOUCHED is omitted: GDAL polygon default is center-based.
                    gdal.RasterizeLayer(raster, [1], layer, burn_values=[burn])
                    layer.SetSpatialFilter(None)
            band = raster.ReadAsArray()
            for row_index, values in enumerate(band, y):
                changes = np.flatnonzero(np.r_[values[1:] != values[:-1], True])
                pairs = np.column_stack((changes+1, values[changes])).astype('<u4')
                pairs.tofile(runs_out)
                offsets.append(offsets[-1] + len(pairs))
                if offsets[-1] > np.iinfo(np.uint32).max:
                    raise ValueError('too many runs for u32 offsets')
                if ref:
                    rr, rv = ref
                    count, spans = compare_row(values, rv[int(rr[row_index]):int(rr[row_index+1])], width)
                    mismatch += count
                    mismatch_intervals += len(spans)
                    for a,b,c,d in spans:
                        span = {'row':row_index,'start':a,'end':b,'reference':c,'candidate':d}
                        diff_out.write(json.dumps(span, separators=(',', ':'))+'\n')
                        if len(samples) < 20:
                            samples.append(span)
    np.asarray(offsets, dtype='<u4').tofile(rows_path)
    for key in ('land', 'water'):
        for spec in cfg[key]:
            checked_files(spec)
    if ref:
        validate_reference(cfg['reference'], width, height)
    (out/'config.json').write_bytes(config_bytes)
    report = {'status':'candidate-only', 'configuration_sha256':hashlib.sha256(config_bytes).hexdigest(),
              'runtime':{'gdal':gdal.VersionInfo('--version'), 'python':sys.version, 'numpy':np.__version__, 'geos':'.'.join(str(v()) for v in (ogr.GetGEOSVersionMajor, ogr.GetGEOSVersionMinor, ogr.GetGEOSVersionMicro)), 'proj':'.'.join(str(v()) for v in (osr.GetPROJVersionMajor, osr.GetPROJVersionMinor, osr.GetPROJVersionMicro))}, 'feature_counts':{key:[part[2] for part in opened[key]] for key in opened},
              'output_sha256':{'rows':sha(rows_path), 'runs':sha(runs_path)},
              'comparison':{'mismatched_cells':mismatch, 'mismatched_intervals':mismatch_intervals, 'all_spans_file':'mismatch-spans.jsonl', 'spans_sha256':sha(diff_path), 'sample_spans':samples} if ref else None,
              'limitations':'Selection and historical source equivalence are not established; inspect all mismatches before use.'}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config')
    ap.add_argument('new_output_directory')
    args = ap.parse_args()
    try:
        build(args.config, args.new_output_directory)
    except Exception as e:
        print(f'build failed: {e}', file=sys.stderr)
        sys.exit(1)
