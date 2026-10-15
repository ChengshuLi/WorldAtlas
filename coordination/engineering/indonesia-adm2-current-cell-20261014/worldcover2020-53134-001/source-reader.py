"""Cohort adaptation of Vietnam WorldCover read_points.py; native source values only.

Same Rasterio index/read/read_masks kernels, now official remote COG blocks.
Completed block JSON+NPZ are retained atomically; a later invocation reuses them.
No classification, source geometry, native authority or application memory policy.
"""
import collections
import datetime
import hashlib
import json
import os
import pathlib
import resource
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import rasterio
from rasterio.windows import Window

ROOT = pathlib.Path(__file__).resolve().parent
PLAN = ROOT / 'point-plan.json'
PLAN_SHA = 'c290b53ddc43b3bf7289445a4f50fa9f5e7805be65b989d8bddd753631128ef9'
started = time.monotonic()
started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
raw = PLAN.read_bytes()
assert hashlib.sha256(raw).hexdigest() == PLAN_SHA
plan = json.loads(raw)
assert plan['count'] == len(plan['points']) == 53134
for pin in plan['input_files'].values():
    b = pathlib.Path(pin['path']).read_bytes()
    assert len(b) == pin['bytes'] and hashlib.sha256(b).hexdigest() == pin['sha256']
CODE_SHA = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()


def atomic_json(p, value):
    b = (json.dumps(value, separators=(',', ':')) + '\n').encode()
    temp = p.with_suffix(p.suffix + '.partial')
    with temp.open('wb') as f:
        f.write(b)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, p)
    return {'file': str(p.relative_to(ROOT)), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


by_tile = collections.defaultdict(list)
for point in plan['points']:
    by_tile[point['tile']].append(point)
sources = []
results = []
block_inventory = []
errors = []
new_blocks = reused_blocks = 0

# Standard GDAL HTTP/COG range access, not whole-tile acquisition. Cache/runtime
# defaults remain normal; no application memory allowance, RSS guard or heap flag.
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                  CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',
                  GDAL_HTTP_CONNECTTIMEOUT='30', GDAL_HTTP_TIMEOUT='120'):
    for tile, points in sorted(by_tile.items()):
        folder = ROOT / 'tiles' / tile
        folder.mkdir(parents=True, exist_ok=True)
        url = plan['source_url_template'].format(tile=tile)
        print(json.dumps({'event': 'tile-start', 'tile': tile, 'points': len(points)}), flush=True)
        try:
            # HEAD authenticates the remote object identity/size, not a whole-body hash.
            try:
                req = urllib.request.Request(url, method='HEAD')
                with urllib.request.urlopen(req, timeout=60) as response:
                    http = {'status': response.status, 'headers': dict(response.headers.items())}
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                http = {'status': 404, 'headers': dict(error.headers.items())}
                source = {'tile': tile, 'url': url, 'http': http, 'status': 'missing-tile', 'points': len(points)}
                atomic_json(folder / 'source.json', source)
                sources.append(source)
                results.extend({**p, 'coverage_status': 'missing-tile', 'class_code': None,
                                'valid_mask': None, 'nodata_match': None} for p in points)
                continue
            assert http['status'] == 200
            source_identity = {k.lower(): v for k, v in http['headers'].items()
                               if k.lower() in ('etag', 'content-length', 'last-modified', 'accept-ranges')}
            assert source_identity.get('accept-ranges', '').lower() == 'bytes', 'No advertised byte-range access'
            with rasterio.open(url) as ds:
                assert ds.crs.to_epsg() == 4326 and ds.width == ds.height == 36000
                assert ds.count == 1 and ds.dtypes == ('uint8',)
                assert ds.transform.a == 1 / 12000 and ds.transform.e == -1 / 12000
                assert ds.transform.b == ds.transform.d == 0
                south = (1 if tile[0] == 'N' else -1) * int(tile[1:3])
                west = (1 if tile[3] == 'E' else -1) * int(tile[4:7])
                assert ds.transform.c == west and ds.transform.f == south + 3
                assert ds.block_shapes == [(1024, 1024)]
                source = {'tile': tile, 'url': url, 'http': http, 'source_identity': source_identity,
                          'status': 'opened-native-cog', 'points': len(points),
                          'crs': str(ds.crs), 'transform': list(ds.transform),
                          'shape': [ds.height, ds.width], 'block_shapes': ds.block_shapes,
                          'nodata': ds.nodata, 'tags': ds.tags(), 'mask_flags': str(ds.mask_flag_enums),
                          'compression': str(ds.compression), 'full_source_hash_claimed': False}
                atomic_json(folder / 'source.json', source)
                sources.append(source)
                grouped = collections.defaultdict(list)
                for p in points:
                    row, col = ds.index(p['longitude'], p['latitude'])
                    item = {**p, 'native_row': int(row), 'native_col': int(col)}
                    if not (0 <= row < ds.height and 0 <= col < ds.width):
                        results.append({**item, 'coverage_status': 'outside-native-frame',
                                        'class_code': None, 'valid_mask': None, 'nodata_match': None})
                    else:
                        grouped[(row // 1024, col // 1024)].append(item)
                for (br, bc), members in sorted(grouped.items()):
                    key = f'block-{br:02d}-{bc:02d}'
                    json_path, array_path = folder / (key + '.json'), folder / (key + '.npz')
                    if json_path.exists():
                        saved = json.loads(json_path.read_text())
                        assert saved['plan_sha256'] == PLAN_SHA and saved['reader_sha256'] == CODE_SHA
                        assert saved['source_identity'] == source_identity
                        assert saved['point_indices'] == [p['point_index'] for p in members]
                        b = array_path.read_bytes()
                        assert len(b) == saved['array']['bytes'] and hashlib.sha256(b).hexdigest() == saved['array']['sha256']
                        results.extend(saved['observations'])
                        block_inventory.append({'tile': tile, 'block': [br, bc],
                                                'json': str(json_path.relative_to(ROOT)), 'array': saved['array']})
                        reused_blocks += 1
                        continue
                    # One native block plus one native pixel border for literal3x3 context.
                    r0, c0 = max(0, br * 1024 - 1), max(0, bc * 1024 - 1)
                    r1, c1 = min(ds.height, (br + 1) * 1024 + 1), min(ds.width, (bc + 1) * 1024 + 1)
                    window = Window(c0, r0, c1 - c0, r1 - r0)
                    codes = ds.read(1, window=window)
                    masks = ds.read_masks(1, window=window)
                    assert codes.shape == masks.shape == (r1 - r0, c1 - c0)
                    temp = array_path.with_suffix('.npz.partial')
                    with temp.open('wb') as f:
                        np.savez_compressed(f, codes=codes, masks=masks)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(temp, array_path)
                    array_raw = array_path.read_bytes()
                    array_pin = {'file': str(array_path.relative_to(ROOT)), 'bytes': len(array_raw),
                                 'sha256': hashlib.sha256(array_raw).hexdigest()}
                    observations = []
                    for p in members:
                        r, c = p['native_row'] - r0, p['native_col'] - c0
                        value, mask = int(codes[r, c]), int(masks[r, c])
                        nodata = ds.nodata is not None and value == ds.nodata
                        complete = 0 < p['native_row'] < ds.height - 1 and 0 < p['native_col'] < ds.width - 1
                        observations.append({**p, 'coverage_status': 'nodata' if nodata else ('mask-invalid' if mask == 0 else 'valid-native-value'),
                                             'class_code': value, 'valid_mask': mask, 'nodata_match': nodata,
                                             'neighbourhood_complete': complete,
                                             'neighbourhood_codes': codes[r-1:r+2, c-1:c+2].tolist() if complete else None,
                                             'neighbourhood_masks': masks[r-1:r+2, c-1:c+2].tolist() if complete else None,
                                             'block_context': str(array_path.relative_to(ROOT))})
                    body = {'kind': 'worldcover-native-block-observation', 'plan_sha256': PLAN_SHA,
                            'reader_sha256': CODE_SHA, 'tile': tile, 'source_identity': source_identity,
                            'window': {'row_off': r0, 'col_off': c0, 'height': r1-r0, 'width': c1-c0},
                            'point_indices': [p['point_index'] for p in members], 'array': array_pin,
                            'observations': observations}
                    atomic_json(json_path, body)
                    results.extend(observations)
                    block_inventory.append({'tile': tile, 'block': [br, bc],
                                            'json': str(json_path.relative_to(ROOT)), 'array': array_pin})
                    new_blocks += 1
                    print(json.dumps({'event': 'block-complete', 'tile': tile, 'block': [br, bc],
                                      'points': len(members), 'completed_points': len(results)}), flush=True)
            print(json.dumps({'event': 'tile-complete', 'tile': tile, 'completed_points': len(results)}), flush=True)
        except Exception as error:
            failure = {'tile': tile, 'error_type': type(error).__name__, 'error': str(error),
                       'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            atomic_json(folder / 'attempt-failure.json', failure)
            errors.append(failure)
            print(json.dumps({'event': 'tile-failed', **failure}), flush=True)
            break

observed_indices = {p['point_index'] for p in results}
assert len(observed_indices) == len(results)
unobserved = [p['point_index'] for p in plan['points'] if p['point_index'] not in observed_indices]
report = {'kind': 'worldcover2020-native-source-observations-not-dispositions',
          'source_year': 2020, 'source_version': 'v100', 'license': plan['license'],
          'attribution': plan['attribution'], 'plan_sha256': PLAN_SHA, 'reader_sha256': CODE_SHA,
          'started_utc': started_utc, 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'elapsed_seconds': time.monotonic() - started,
          'observed_process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'runtime': {'python': sys.version, 'rasterio': rasterio.__version__, 'gdal': rasterio.__gdal_version__, 'numpy': np.__version__},
          'complete': not errors and not unobserved, 'count': len(results), 'requested_count': 53134,
          'status_counts': dict(collections.Counter(p['coverage_status'] for p in results)),
          'literal_value_counts': dict(collections.Counter(str(p['class_code']) for p in results)),
          'sources': sources, 'block_inventory': block_inventory, 'new_blocks': new_blocks,
          'reused_blocks': reused_blocks, 'errors': errors, 'unobserved_point_indices': unobserved,
          'observations': sorted(results, key=lambda p: p['point_index']),
          'limits': ['Native product predictions and masks only; not geographic answers, authority or acceptance.',
                     'No absent tile, invalid value or nodata interpreted as ocean.',
                     'Annual2020 model class is not instantaneous stage or territorial ownership.',
                     'No whole remote source hash, InputQuality layer, image interpretation or new classification claimed.'],
          'answered_review_credit': 0, 'repair_credit': 0}
pin = atomic_json(ROOT / 'source-observations.json', report)
print(json.dumps({'event': 'complete' if report['complete'] else 'incomplete', 'output': pin,
                  'count': len(results), 'status_counts': report['status_counts'],
                  'new_blocks': new_blocks, 'reused_blocks': reused_blocks, 'errors': errors}), flush=True)
sys.exit(0 if report['complete'] else 1)
