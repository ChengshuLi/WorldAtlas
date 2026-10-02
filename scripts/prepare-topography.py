"""EarthEnv published geomorphon references; no inferred historical terrain classes."""
import collections
import gc
import gzip
import hashlib
import json
import math
import pathlib
import subprocess
import urllib.request

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
CACHE = ROOT / '.cache/research'
OUT = DATA / 'topography-reference'
URL = 'https://data.earthenv.org/topography/geom_1KMmaj_GMTEDmd.tif'
SOURCE_SHA = 'acbb0254a6ecc5464abbdaff63c6e8af42a085ada4eba1c8feb8d40c4fc6414b'
CLASSES = ['unknown', 'flat', 'peak', 'ridge', 'shoulder', 'spur', 'slope', 'hollow', 'footslope', 'valley', 'pit']
CLASS_URL = 'https://grass.osgeo.org/grass-stable/manuals/r.geomorphon.html'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def footprint_hash():
    return subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip()


def summarize(geometry, grid, transform):
    """Native cell-centre area proxy includes cells beyond the source latitude extent."""
    weights = np.zeros(11, dtype=float)
    total = 0.0
    pieces = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
    for piece in pieces:
        w = from_bounds(*piece.bounds, transform)
        col = max(0, math.floor(w.col_off))
        stop_col = min(grid.shape[1], math.ceil(w.col_off + w.width))
        start_row = math.floor(w.row_off)
        stop_row = math.ceil(w.row_off + w.height)
        if stop_col <= col:
            continue
        # Bounded strips prevent oversized polar/local territories allocating huge masks.
        for row in range(start_row, stop_row, 128):
            height = min(128, stop_row - row)
            width = stop_col - col
            win = Window(col, row, width, height)
            win_transform = rasterio.windows.transform(win, transform)
            mask = ~geometry_mask([mapping(piece)], out_shape=(height, width), transform=win_transform)
            if not mask.any():
                continue
            latitudes = transform.f + (np.arange(row, row + height) + .5) * transform.e
            latitude_weights = np.cos(np.deg2rad(latitudes))[:, None]
            total += float((mask * latitude_weights).sum())
            cells = np.zeros((height, width), dtype=np.uint8)
            first = max(0, row)
            last = min(grid.shape[0], row + height)
            if last > first:
                cells[first-row:last-row] = grid[first:last, col:stop_col]
            weights += np.bincount(cells[mask], weights=np.broadcast_to(latitude_weights, cells.shape)[mask], minlength=11)
    supported = float(weights[1:].sum())
    if total <= 0:
        return None, 'no_native_cell_centre', None
    coverage = supported / total
    if coverage < .5:
        return None, 'less_than_half_supported_native_land_cells', round(coverage, 6)
    code = int(np.argmax(weights[1:]) + 1)
    return (code, round(float(weights[code] / supported), 6), round(coverage, 6)), None, None


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    expected = footprint_hash()
    source = CACHE / 'terrain-geom_1KMmaj_GMTEDmd.tif'
    if not source.exists():
        partial = source.with_suffix('.partial')
        request = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.earthenv.org/topography'})
        with urllib.request.urlopen(request, timeout=25) as response, partial.open('wb') as out:
            count = 0
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
                count += len(chunk)
                if count % (10 * 1024 * 1024) == 0:
                    print('Terrain download bytes', count, flush=True)
        partial.rename(source)
    if digest(source) != SOURCE_SHA:
        raise ValueError('Terrain source hash differs from inspected licensed release')
    native = CACHE / 'terrain-geom_1KMmaj_GMTEDmd.npy'
    histogram = np.zeros(256, dtype=np.int64)
    with rasterio.open(source) as raster:
        if (raster.crs.to_epsg(), raster.width, raster.height, raster.dtypes[0]) != (4326, 43200, 16800, 'uint8'):
            raise ValueError('Unexpected native topography format')
        if not np.allclose(tuple(raster.transform)[:6], [1/120, 0, -180, 0, -1/120, 84]):
            raise ValueError('Unexpected native topography alignment')
        transform = raster.transform
        source_tags = raster.tags()
        # Native memory map stays on disk; no worldwide vector collection is held in memory.
        native_grid = np.lib.format.open_memmap(native, mode='w+', dtype=np.uint8, shape=(raster.height, raster.width))
        for row in range(0, raster.height, 128):
            cells = raster.read(1, window=Window(0, row, raster.width, min(128, raster.height-row)))
            histogram += np.bincount(cells.ravel(), minlength=256)
            native_grid[row:row+cells.shape[0]] = cells
        native_grid.flush()
    if histogram[11:].sum():
        raise ValueError('Source contains classes outside the verified GRASS 0–10 crosswalk')
    if not histogram[1:11].all():
        raise ValueError('Verified terrain classes missing from the global native raster')
    parts = []
    rows = []
    part_hashes = {}
    locations = 0
    known = 0
    missing = []
    value_counts = collections.Counter()
    def save_part():
        if not rows:
            return
        name = f'part-{len(parts)}.json.gz'
        payload = gzip.compress(json.dumps(rows, separators=(',', ':')).encode(), mtime=0)
        (OUT / name).write_bytes(payload)
        parts.append(name)
        part_hashes[name] = hashlib.sha256(payload).hexdigest()
        rows.clear()
    world = json.loads((DATA / 'world-index.json').read_text())
    for path in world['parts']:
        features = json.loads((DATA / path).read_text())['features']
        for feature in features:
            result, reason, coverage = summarize(shape(feature['geometry']), native_grid, transform)
            locations += 1
            if result is None:
                missing.append({'location_id': feature['id'], 'reason': reason, 'coverage': coverage})
            else:
                code, share, coverage = result
                rows.append([feature['id'], [[0, code-1, share, coverage]]])
                known += 1
                value_counts[CLASSES[code]] += 1
            if len(rows) == 1500:
                save_part()
            if locations % 5000 == 0:
                print(f'Topography {locations}: {known} supported', flush=True)
        del features
    save_part()
    native_grid._mmap.close()
    del native_grid
    gc.collect()
    if footprint_hash() != expected:
        raise ValueError('Location footprints changed during topography preparation')
    metadata = {'source_url': URL, 'publication_url': 'https://doi.org/10.1038/sdata.2018.40', 'source_sha256': SOURCE_SHA,
                'source_year': 2016, 'publication_year': 2018, 'base_product': 'GMTED2010 median 7.5 arc-second elevation',
                'resolution': '1/120 degree (approximately 1 km at equator)', 'source_extent': [-180, -56, 180, 84],
                'aggregation': 'Dominant published geomorphon class by latitude-weighted native cell centres; at least 50% of all sampled location land cells must be supported, including cells outside source latitude extent',
                'interpretation': 'Published geomorphological landform, not an inferred hills/mountains game classification',
                'note': 'Modern physical reference; relatively stable terrain, not a historical observation. Source native-cell centres may miss sub-cell islands.', 'class_crosswalk_url': CLASS_URL}
    index = {'version': 2, 'parts': parts, 'part_hashes': part_hashes, 'records': known, 'locations': locations, 'represented_locations': known,
             'footprints_sha256': expected, 'values': CLASSES[1:], 'types': [{'attribute': 'topography', 'valid_from': 2026, 'valid_to': 2027,
             'method': 'reference', 'status': 'reference', 'source': 'Amatulli et al. (2018), EarthEnv global topographic variables; CC BY 4.0', 'metadata': metadata}],
             'inputs': {'terrain': SOURCE_SHA, 'algorithm': digest(pathlib.Path(__file__))}, 'source_tags': source_tags,
             'source_class_counts': {str(i): int(v) for i, v in enumerate(histogram) if v}, 'location_class_counts': dict(value_counts),
             'class_crosswalk': {str(i): CLASSES[i] for i in range(1, 11)}, 'missing': missing}
    (OUT / 'index.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps({'locations': locations, 'records': known, 'missing': len(missing), 'classes': dict(value_counts)}), flush=True)


if __name__ == '__main__':
    main()
