"""Verify selected vector inputs and read physical comparison streams."""

import hashlib
from pathlib import Path
import numpy as np
from osgeo import ogr, osr


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


def open_layer(spec, *, feature_callback=None):
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
        if feature_callback is not None:
            feature_callback(feat, geom)
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
    if len(rows) != height + 1 or len(runs) % 2 or rows[0] != 0 or rows[-1] != len(runs) // 2:
        raise ValueError('invalid reference stream lengths/offsets')
    if np.any(rows[1:] < rows[:-1]):
        raise ValueError('reference offsets not monotone')
    return rows, runs.reshape(-1, 2)


def compare_row(values, ref_runs, width):
    ends = ref_runs[:, 0]
    codes = ref_runs[:, 1]
    if (
        not len(ends)
        or ends[0] == 0
        or ends[-1] != width
        or np.any(ends[1:] <= ends[:-1])
        or np.any(~np.isin(codes, [1, 17]))
    ):
        raise ValueError('invalid reference row')
    actual_ends = np.flatnonzero(np.r_[values[1:] != values[:-1], True]) + 1
    cuts = np.unique(np.r_[0, ends, actual_ends])
    x = cuts[:-1]
    old = codes[np.searchsorted(ends, x, side='right')]
    new = values[x]
    bad = old != new
    return int(np.diff(cuts)[bad].sum()), [
        (int(a), int(b), int(c), int(d))
        for a, b, c, d in zip(x[bad], cuts[1:][bad], old[bad], new[bad])
    ]
