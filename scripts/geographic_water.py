"""Bounded native monthly-water diagnostics, never administrative assignment.

Counts concern exact polygon-contained pixel centres at the native source grid.
They do not certify an entire polygon, subpixel water, or a historical boundary.
"""
import math
import re

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import Window
from shapely import contains_xy, prepare
from shapely.geometry import shape

VERSION = 'worldatlas-native-monthly-water-diagnostics-v1'
MAX_WINDOW_PIXELS = 8_000_000


def monthly_diagnostics(raw, feature, month, anchor):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        raise ValueError('Explicit source month required')
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError('Whole original exceeds ordinary-file budget')
    g = shape(feature['geometry'])
    if g.geom_type not in ('Polygon', 'MultiPolygon') or not g.is_valid or g.is_empty:
        raise ValueError('Valid unchanged component geometry required')
    if len(anchor) != 2 or not all(math.isfinite(v) for v in anchor):
        raise ValueError('Finite longitude/latitude anchor required')
    prepare(g)
    with MemoryFile(raw) as mem, mem.open() as source:
        t = source.transform
        if (source.crs != rasterio.crs.CRS.from_epsg(4326) or source.count != 1
                or source.dtypes != ('uint8',) or t.b != 0 or t.d != 0
                or t.a <= 0 or t.e >= 0):
            raise ValueError('Require native north-up EPSG:4326 single-byte monthly raster')
        if source.nodata not in (None, 0):
            raise ValueError('Unexpected monthly nodata encoding')
        if any(rows * columns > 1_000_000 for rows, columns in source.block_shapes):
            raise ValueError('Native decoder block exceeds bounded working-memory scope')
        xmin, ymin, xmax, ymax = g.bounds
        left = math.floor((xmin - t.c) / t.a)
        right = math.ceil((xmax - t.c) / t.a)
        top = math.floor((ymax - t.f) / t.e)
        bottom = math.ceil((ymin - t.f) / t.e)
        # A clipped source window would silently omit part of the component.
        if left < 0 or top < 0 or right > source.width or bottom > source.height:
            raise ValueError('Component extends outside original raster coverage')
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0 or width * height > MAX_WINDOW_PIXELS:
            raise ValueError('Native window exceeds declared bounded pilot scope')
        counts = {str(i): 0 for i in (0, 1, 2)}
        xs = t.c + (np.arange(left, right) + .5) * t.a
        # Chunk rows, avoiding full-tile decoding and per-cell geometry copies.
        for row in range(top, bottom, 128):
            n = min(128, bottom - row)
            values = source.read(1, window=Window(left, row, width, n))
            mask = source.read_masks(1, window=Window(left, row, width, n))
            if np.any((values > 2) | ((mask == 0) & (values != 0))):
                raise ValueError('Unexpected raw class/mask; do not guess TIFF encoding')
            ys = t.f + (np.arange(row, row + n) + .5) * t.e
            inside = contains_xy(g, xs[None, :], ys[:, None])
            for i in (0, 1, 2):
                counts[str(i)] += int(np.count_nonzero(inside & (values == i)))
        ar, ac = source.index(*anchor)
        if not (0 <= ar < source.height and 0 <= ac < source.width):
            raise ValueError('Anchor outside native coverage')
        value = int(source.read(1, window=Window(ac, ar, 1, 1))[0, 0])
        if value not in (0, 1, 2):
            raise ValueError('Unexpected anchor class')
        if not contains_xy(g, *anchor):
            raise ValueError('Anchor must lie strictly inside retained component')
        centre = source.xy(ar, ac)
        signal = ('mixed-water-and-not-water' if counts['1'] and counts['2'] else
                  'sampled-water-support' if counts['2'] else
                  'sampled-not-water-contradiction' if counts['1'] else
                  'unknown-no-observed-centres')
        return {
            'source_month': month,
            'native_raster': {'crs': str(source.crs), 'transform': list(t),
                              'width': source.width, 'height': source.height,
                              'bounds': list(source.bounds), 'dtype': source.dtypes[0],
                              'nodata': source.nodata, 'tags': source.tags(),
                              'nominal_resolution_m': 30},
            'window': {'row_start': top, 'column_start': left,
                       'rows': height, 'columns': width},
            'centre_counts': {'no_observations': counts['0'], 'not_water': counts['1'],
                              'water_detected': counts['2'],
                              'total': sum(counts.values())},
            'raw_class_counts': counts,
            'semantic_mapping_status': 'conditional-on-reviewed-monthly-schema',
            'signal': signal,
            'anchor': {'lonlat': list(anchor), 'native_row': ar, 'native_column': ac,
                       'native_pixel_centre': list(centre), 'raw_value': value,
                       'pixel_centre_inside_component': bool(contains_xy(g, *centre))},
            'component_water_status': 'unknown', 'administrative_assignment': None,
            'registration_error_bound_m': None,
            'limits': [
                'Raw 0/1/2 counts are exact; semantic labels are conditional on the reviewed monthly schema.',
                'Counts cover strictly interior native pixel centres, not continuous polygon area.',
                'No-observation cells are unknown, never dry land.',
                'A detected-water pixel may mix water and land; narrower seams remain unresolved.',
                'One monthly observation is not permanence, seasonality or a valid-observation scene count.',
                'Local source registration accuracy is unverified; no hard offset bound is assumed.',
                'No full-shape water waiver, province assignment, geometry repair or release approval.']}


def compare_months(records):
    """Describe sampled months without inventing an annual/seasonal classification."""
    dates = [r['source_month'] for r in records]
    if len(dates) != len(set(dates)) or not records:
        raise ValueError('Distinct explicit months required')
    grids = [r['native_raster'] for r in records]
    keys = ('crs', 'transform', 'width', 'height', 'dtype')
    if any(any(g[k] != grids[0][k] for k in keys) for g in grids):
        raise ValueError('Native grids differ; coordinated registration review required')
    signals = {r['signal'] for r in records}
    return {'sampled_months': sorted(dates),
            'signals_differ': len(signals) > 1,
            'sampled_water_present': any(r['centre_counts']['water_detected'] for r in records),
            'sampled_not_water_present': any(r['centre_counts']['not_water'] for r in records),
            'unsampled_months_unknown': True, 'seasonality': 'unknown',
            'component_water_status': 'unknown'}
