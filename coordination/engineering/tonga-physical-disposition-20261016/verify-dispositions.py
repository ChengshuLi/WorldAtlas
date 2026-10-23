#!/usr/bin/env python3
"""Read-only exact-cell audit using original retained Tonga source/physical products.
No physical producer, native constructor, geometry repair or ownership write runs.
Usage: python verify-dispositions.py READ_ONLY_REPO PACKET_DIRECTORY
"""
import collections
import gzip
import hashlib
import json
import os
import pathlib
import re
import struct
import subprocess
import sys
import tempfile

from shapely.geometry import Point, shape

repo, packet = map(pathlib.Path, sys.argv[1:])
bindings = json.loads((packet / 'input-bindings.json').read_bytes())

def read_pin(pin):
    assert re.fullmatch('[0-9a-f]{40}', pin['commit'])
    assert not pin['path'].startswith('/') and all(p not in ('', '.', '..') for p in pin['path'].split('/'))
    assert pin['mode'] == '100644' and 0 <= pin['bytes'] <= 32 * 1024 * 1024
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1')
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', pin['commit'] + ':' + pin['path']], env=env)
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == pin['git_blob_oid']
    if 'decoded_bytes' in pin:
        raw = gzip.decompress(raw)
        assert len(raw) == pin['decoded_bytes'] and hashlib.sha256(raw).hexdigest() == pin['decoded_sha256']
    return raw

# Authenticate the complete original stock image, then compare its actual extracted
# output. Temporary work never touches the checkout or the original products.
queue = bindings['stock_extraction']
assert len(queue['files']) == 19
queue_bodies = {}
for pin in queue['files']:
    assert pin['commit'] == queue['commit']
    name = pathlib.PurePosixPath(pin['path']).name
    assert name not in queue_bodies
    queue_bodies[name] = read_pin(pin)
with tempfile.TemporaryDirectory(prefix='worldatlas-tonga-review-') as directory:
    temporary = pathlib.Path(directory)
    image = temporary / 'queue'
    image.mkdir()
    for name, raw in queue_bodies.items():
        (image / name).write_bytes(raw)
    environment = {key: value for key, value in os.environ.items() if key not in ('NODE_OPTIONS', 'NODE_PATH')}
    extracted = temporary / 'extracted'
    subprocess.run(['node', str(image / 'source-batch-intervals.mjs'),
                    'gb-TON-ADM1--physical-interpretation', str(extracted)],
                   env=environment, check=True, capture_output=True, text=True)
    assert {file.name for file in extracted.iterdir()} == {'package.json', 'block-034.json.gz', 'block-035.json.gz', 'block-036.json.gz'}
    assert (extracted / 'package.json').read_bytes() == (packet / 'package.json').read_bytes()
    for block in (34, 35, 36):
        assert (extracted / f'block-{block:03d}.json.gz').read_bytes() == (packet / f'frozen-block-{block:03d}.json.gz').read_bytes()

inputs = {name: read_pin(pin) for name, pin in bindings['inputs'].items()}
source = json.loads(inputs['original_source'])
source_features = {'gb:TON:ADM1:' + f['properties']['shapeID']: f for f in source['features']}
stage = json.loads(inputs['original_stage'])
assert len(stage) == len(source_features) == 5
current_features = {f['id']: f for f in json.loads(inputs['current_geometry'])['features'] if f['id'] in source_features}
assert len(current_features) == 5
for row in stage:
    assert row['consumed'] == source_features[row['target']]
    assert row['selected'] == current_features[row['target']]
original_shapes = {key: shape(value['geometry']) for key, value in source_features.items()}
current_shapes = {key: shape(value['geometry']) for key, value in current_features.items()}
physical = json.loads(inputs['original_physical'])
support = {row['target']: {key: shape(geom if geom.get('type') else {'type': 'GeometryCollection', 'geometries': []}) for key, geom in row['support'].items()} for row in physical['results']}
assert set(support) == set(source_features)
latitudes = struct.unpack('<262166d', inputs['native_latitudes'])
owners = {row['index']: row for row in json.loads(inputs['owner_roster'])}
source_roster = {row['source_index']: row for row in json.loads(inputs['source_roster'])}

def patch_cells(body):
    cells = {(row['y'], x): owner for row in json.loads(body)['rows'] for start, end, owner in row['runs'] for x in range(start, end)}
    assert len(cells) == sum(end - start for row in json.loads(body)['rows'] for start, end, _ in row['runs'])
    return cells

accepted, repair = map(patch_cells, (inputs['accepted_patch'], inputs['repair_patch']))
frozen = []
for block in (34, 35, 36):
    frozen.extend(json.loads(gzip.decompress((packet / f'frozen-block-{block:03d}.json.gz').read_bytes())))
interval_product = json.loads((packet / 'interval-dispositions.json').read_bytes())
intervals = interval_product['intervals']
literals = json.loads((packet / 'literal-cell-dispositions.json').read_bytes())['records']
summary = json.loads((packet / 'review-summary.json').read_bytes())
assert len(frozen) == len(intervals) == 754
assert len(interval_product['questions']) == 1 and interval_product['questions'][0]['question']
literal_map = {(row['y'], row['x']): row for row in literals}
assert len(literals) == len(literal_map) == 1984
seen = set()
per_owner = collections.Counter()
for raw, interval in zip(frozen, intervals):
    y, start, end, owner_list, source_list, category = raw
    assert len(owner_list) == len(source_list) == 1 and category == 'source-relative'
    owner, source_index = owner_list[0], source_list[0]
    source_id = owners[owner]['id']
    assert source_roster[source_index]['source_id'] == source_id
    assert source_roster[source_index]['owners'] == [owner]
    assert [interval[k] for k in ('y', 'start', 'end', 'owner', 'source_feature_index')] == [y, start, end, owner, source_index]
    assert interval['source_id'] == source_id and interval['native_cells'] == end - start
    assert interval['disposition'] == 'unresolved-physical-interpretation'
    assert interval['observed_context'] == 'outside_mapped_L1_context'
    assert interval['repair_cells'] == 0 and interval['land_or_water_classification'] is None
    assert interval['question_id'] == interval_product['questions'][0]['id']
    for x in range(start, end):
        key = (y, x)
        assert key not in seen and key not in accepted and key not in repair
        seen.add(key)
        cell = literal_map[key]
        longitude, latitude = (x + .5) / 262166 * 360 - 180, latitudes[y]
        point = Point(longitude, latitude)
        assert [sid for sid, geom in original_shapes.items() if geom.covers(point)] == [source_id]
        assert not [sid for sid, geom in current_shapes.items() if sid != source_id and geom.covers(point)]
        categories = [name for name, geom in support[source_id].items() if geom.covers(point)]
        assert categories == ['outside_mapped_L1_context']
        assert cell['source_id'] == source_id and cell['owner'] == owner and cell['source_unique'] is True
        assert cell['longitude'] == longitude and cell['latitude'] == latitude
        assert cell['support_categories'] == categories and cell['current_owner_covers_center'] == current_shapes[source_id].covers(point)
        assert cell['disposition'] == interval['disposition'] and cell['question_id'] == interval['question_id']
        assert cell['land_or_water_classification'] is None
        per_owner[owner] += 1
assert seen == set(literal_map)
assert summary['accepted_baseline'] == bindings['accepted_baseline']
for field in ('scope_cells', 'reviewed_cells', 'unresolved_cells', 'unique_source_center_matches'):
    assert summary[field] == len(seen)
for field in ('accepted_intersection', 'repair_cohort_intersection', 'current_sibling_center_hits', 'repaired_cells', 'approved_land_cells', 'approved_water_cells'):
    assert summary[field] == 0
assert summary['segments'] == len(frozen)
assert summary['whole_physical_center_classification'] == {'outside_mapped_L1_context': 1984}
assert summary['per_owner'] == {str(owner): {'outside_mapped_L1_context': count} for owner, count in per_owner.items()}
assert summary['current_owner_zero_verified'] is False and summary['native_qualification_executed'] is False and summary['original_physical_rerun'] is False
print(json.dumps({'passed': True, 'reviewed_cells': len(seen), 'unresolved_cells': len(seen), 'intervals': len(frozen), 'repair_cells': 0, 'land_or_water_approvals': 0, 'physical_producer_rerun': False, 'native_constructor_run': False, 'accepted_baseline': bindings['accepted_baseline']}, sort_keys=True))
