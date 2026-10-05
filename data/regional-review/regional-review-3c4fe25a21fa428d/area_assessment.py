#!/usr/bin/env python3
"""Reproduce source-feature area observations with the repository's shared helper.

Run from repository root after installing requirements.txt:
PYTHONPATH=scripts/evidence python3 data/regional-review/regional-review-3c4fe25a21fa428d/area_assessment.py
"""
import collections
import hashlib
import json
import pathlib
import platform
import statistics
import sys

sys.path.insert(0, 'scripts')
from geometry import land_area_m2, METHOD, VERSION
from shapely.geometry import shape
from shapely import __version__ as shapely_version
import pyproj

ROOT = pathlib.Path('data/regional-review/regional-review-3c4fe25a21fa428d')
with (ROOT / 'source' / 'subject-assessments.json').open() as f:
    packet = json.load(f)
with (ROOT / 'source' / 'source-manifest.json').open() as f:
    source_manifest = json.load(f)
sources = {x['source_id']: x for x in source_manifest['sources']}
source_data = {}
for source_id, desc in sources.items():
    data = json.loads(pathlib.Path(desc['path']).read_bytes())
    source_data[source_id] = data
    assert hashlib.sha256(pathlib.Path(desc['path']).read_bytes()).hexdigest() == desc['sha256']
    assert len(data['features']) == desc['features']

measurements = []
by_source = collections.defaultdict(list)
for item in packet['subjects']:
    source_id = item['source_id']
    desc = sources[source_id]
    prefix = desc['boundary_id'].rsplit('-', 1)[-1]
    matches = [f for f in source_data[source_id]['features']
               if f['properties'].get('shapeID') == item['source_shape_id']
               and f['properties'].get('shapeID', '').startswith(prefix)]
    assert len(matches) == 1, (item['location_id'], len(matches))
    geometry = matches[0]['geometry']
    try:
        area_m2 = land_area_m2(shape(geometry))
        record = {
            'location_id': item['location_id'], 'name': item['name'],
            'source_id': source_id, 'source_feature_name': item['source_feature_name'],
            'source_shape_id': item['source_shape_id'], 'geometry_type': geometry['type'],
            'area_m2': round(area_m2, 3), 'area_km2': round(area_m2 / 1_000_000, 6),
            'measurement_status': 'measured'
        }
        by_source[source_id].append(area_m2 / 1_000_000)
    except Exception as error:
        record = {
            'location_id': item['location_id'], 'name': item['name'],
            'source_id': source_id, 'source_feature_name': item['source_feature_name'],
            'source_shape_id': item['source_shape_id'], 'geometry_type': geometry['type'],
            'measurement_status': 'unresolved', 'error_type': type(error).__name__,
            'error': str(error)
        }
    record['source_sha256'] = desc['sha256']
    measurements.append(record)

summaries = []
for source_id, values in sorted(by_source.items()):
    ordered = sorted(values)
    median = statistics.median(ordered)
    scoped = [r for r in measurements if r['source_id'] == source_id and r['measurement_status'] == 'measured']
    large = [r['location_id'] for r in scoped if r['area_km2'] > 3 * median]
    small = [r['location_id'] for r in scoped if r['area_km2'] < median / 10]
    summaries.append({
        'source_id': source_id, 'source_sha256': sources[source_id]['sha256'],
        'measured_count': len(values), 'unresolved_count': sum(
            r['source_id'] == source_id and r['measurement_status'] == 'unresolved' for r in measurements),
        'minimum_area_km2': round(min(ordered), 6),
        'median_area_km2': round(median, 6),
        'maximum_area_km2': round(max(ordered), 6),
        'screen_large_gt_3x_median_ids': sorted(large),
        'screen_small_lt_0_1x_median_ids': sorted(small),
        'screen_interpretation': 'Descriptive within-source scale screen only; thresholds do not define acceptable admin-unit size.'
    })
result = {
    'version': 1, 'baseline_commit': '5391a5a2cc5bc3386d30e8c816de3f9388e70d99',
    'retrieved_source_date_utc': '2026-10-05',
    'evaluation_vintage': 'source', 'scope_count': len(measurements),
    'method': METHOD, 'helper_version': VERSION,
    'helper_source_sha256': hashlib.sha256(pathlib.Path('scripts/evidence/geometry.py').read_bytes()).hexdigest(),
    'ellipsoidal_area_source_sha256': hashlib.sha256(pathlib.Path('scripts/ellipsoidal_area.py').read_bytes()).hexdigest(),
    'software': {'python': platform.python_version(), 'shapely': shapely_version, 'pyproj': pyproj.__version__},
    'summary': summaries, 'subjects': measurements,
    'limits': ['Areas measure retained polygons, not legal territory.',
               'No official-source overlay, topology repair, or area-based semantic approval was performed.',
               'Large/small thresholds are triage flags, not correctness thresholds.']
}
(ROOT / 'source' / 'area-assessments.json').write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
for row in summaries:
    print(row['source_id'], 'n', row['measured_count'], 'unresolved', row['unresolved_count'],
          'min/median/max km2', row['minimum_area_km2'], row['median_area_km2'], row['maximum_area_km2'],
          'large', len(row['screen_large_gt_3x_median_ids']), 'small', len(row['screen_small_lt_0_1x_median_ids']))
print('measurements', len(measurements), 'unresolved', sum(r['measurement_status'] == 'unresolved' for r in measurements))
