"""Reusable, source-only Indonesia cohort probe.

The immutable Riau/Indonesia programs remain historical evidence. This shared
implementation retains their complete-family covers, lineage/identity checks,
competitor withholding and physical/native/semantic holds. It is not a writer of
native authority. Inputs are explicit immutable whole-file pins, never a cache.
"""
import argparse
import collections
import gc
import gzip
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

MAX_FILE = 32 * 1024 * 1024
MAX_INPUT = 256 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024
GRID = 262166
FAMILY_INDICES = dict(zip(
    ['gb:IDN:ADM1', 'gb:IDN:ADM2', 'gb:MYS:ADM1', 'gb:MYS:ADM2',
     'gb:PNG:ADM1', 'gb:PNG:ADM2', 'gb:PNG:ADM3', 'gb:TLS:ADM1', 'gb:TLS:ADM2'],
    [152, 153, 230, 231, 263, 264, 265, 327, 328]))
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def exact_map(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        need(value not in result, 'Duplicate identity: ' + str(value))
        result[value] = row
    need(result, 'Empty required identity inventory')
    return result


def positive_int(value, limit=None):
    return type(value) is int and value > 0 and (limit is None or value <= limit)


def safe_path(value):
    need(isinstance(value, str) and value and not value.startswith('/')
         and '\\' not in value and all(p not in ('', '.', '..') for p in value.split('/'))
         and re.fullmatch(r'[A-Za-z0-9_./-]+', value), 'Unsafe repository input path')
    return value


def validate_config(config):
    need(config.get('version') == 1, 'Unsupported source config')
    for key in ('scientific_input_commit', 'accepted_head'):
        need(re.fullmatch('[a-f0-9]{40}', config.get(key, '')), 'Exact commit required: ' + key)
    need(positive_int(config.get('issue')) and isinstance(config.get('worker_id'), str)
         and config['worker_id'].strip(), 'Explicit issue/worker required')
    pins = exact_map(config['inputs'], 'path')
    for name, pin in pins.items():
        safe_path(name)
        need(re.fullmatch('[a-f0-9]{40}', pin.get('commit', '')) and
             re.fullmatch('[a-f0-9]{40}', pin.get('git_blob_oid', '')) and
             re.fullmatch('[a-f0-9]{64}', pin.get('sha256', '')) and
             positive_int(pin.get('bytes'), MAX_FILE), 'Invalid whole input pin')
        if name.endswith('.gz'):
            need(positive_int(pin.get('decoded_bytes'), MAX_FILE) and
                 re.fullmatch('[a-f0-9]{64}', pin.get('decoded_sha256', '')), 'Decoded pin required')
    roles = config['roles']
    for role in ('catalogue', 'roster', 'lineage', 'selector', 'latitudes', 'countries', 'country_registry', 'decisions'):
        need(roles.get(role) in pins, 'Missing pinned role: ' + role)
    for role in ('geography', 'method_code'):
        need(isinstance(roles.get(role), list) and roles[role] and
             len(set(roles[role])) == len(roles[role]) and all(p in pins for p in roles[role]), 'Missing role inventory: ' + role)
    need(set(roles['method_code']) == {'scripts/reconcile-topology.py', 'scripts/prepare.mjs'}, 'Complete accepted method inventory required')
    family_map = exact_map(config['families'], 'id')
    need({k: v['family_index'] for k, v in family_map.items()} == FAMILY_INDICES and
         list(family_map) == list(FAMILY_INDICES),
         'Complete accepted Indonesia and neighboring source families required')
    targets = exact_map(config['targets'], 'owner')
    need(len({t['id'] for t in targets.values()}) == len(targets) and
         len({t['source_index'] for t in targets.values()}) == len(targets), 'Duplicate target identity/source index')
    for owner, target in targets.items():
        need(positive_int(owner) and positive_int(target['source_index']), 'Invalid target owner/source index')
        for key in ('id', 'name', 'parent_id'):
            need(isinstance(target.get(key), str) and target[key], 'Missing target identity expectation')
        need(target['id'].startswith('gb:IDN:ADM2:') and target['reference_owner'] == 'Indonesia'
             and target['source_id'] == 'gb:IDN:ADM2' and target['administrative_level'] == 'ADM2'
             and target['reference_year'] == '2020' and target['source_role'] == 'regency, city'
             and target['shape_group'] == 'IDN' and target['shape_type'] == 'ADM2',
             'Unsupported target source method; reviewed method expansion required')
    need(config['country'] == {'code': 'IDN', 'source_prefix': 'gb:IDN:',
         'registry_hash_key': 'ne_10m_admin_0_countries'}, 'Unsupported country-reference method')
    need(config['selector_format'] in ('cohort-intervals-v1', 'candidate-rows-v1'), 'Unknown selector format')
    need(set(config['expected_counts']) == {'repair', 'physical'} and
         all(type(n) is int and n >= 0 for n in config['expected_counts'].values()) and
         sum(config['expected_counts'].values()) > 0 and positive_int(config['expected_segments']), 'Nonempty exact selector counts required')
    resources = config['resources']
    for name, limit in [('input_bytes', MAX_INPUT), ('output_bytes', MAX_OUTPUT), ('deadline_seconds', 180)]:
        need(positive_int(resources.get(name), limit), 'Invalid finite resource limit: ' + name)
    need(sum(p['bytes'] + p.get('decoded_bytes', 0) for p in pins.values()) <= resources['input_bytes'], 'Declared complete input budget exceeded')
    physical = config['physical_reproducer']
    need(physical.get('path') in pins and physical == pins[physical['path']], 'Pinned physical reproducer required')
    need(set(config['runtime']) == {'python', 'numpy', 'shapely', 'geos'} and
         all(isinstance(v, str) and v for v in config['runtime'].values()), 'Exact runtime versions required')
    return pins


def selector_segments(selector, config):
    owners = {t['owner'] for t in config['targets']}
    if config['selector_format'] == 'candidate-rows-v1':
        need(selector['as_of_commit'] == config['scientific_input_commit'], 'Selector scientific vintage differs')
        need(isinstance(selector['rows'], list) and selector['rows'] and
             all(isinstance(r, list) and len(r) == 7 for r in selector['rows']), 'Exact candidate row shape required')
        rows = [dict(zip(('category', 'y', 'start', 'end', 'owners', 'sids', 'physical'), r)) for r in selector['rows']]
    else:
        need(selector['scientific_input_commit'] == config['scientific_input_commit'], 'Selector scientific vintage differs')
        need(not selector['source_conflict_segments'], 'Unqualified source-conflict selector rows')
        rows = selector['repair_segments'] + selector['physical_segments']
        need(all(r['category'] == 'repair' for r in selector['repair_segments']) and
             all(r['category'] == 'physical' for r in selector['physical_segments']), 'Selector category differs')
    counts = collections.Counter()
    intervals = collections.defaultdict(list)
    for row in rows:
        need(set(row) == {'category', 'y', 'start', 'end', 'owners', 'sids', 'physical'}, 'Exact selector fields required')
        category, y, a, z = (row[k] for k in ('category', 'y', 'start', 'end'))
        need(category in ('repair', 'physical') and all(type(n) is int for n in (y, a, z))
             and 0 <= y < GRID and 0 <= a < z <= GRID, 'Invalid native selector interval')
        need(len(row['owners']) == 1 and row['owners'][0] in owners, 'Unknown or ambiguous selector owner')
        need(row['sids'] and len(set(row['sids'])) == len(row['sids']) and
             all(positive_int(s) for s in row['sids']), 'Invalid selector source identities')
        intervals[y].append((a, z))
        counts[category] += z - a
    for ranges in intervals.values():
        ranges.sort()
        need(all(a >= previous_z for (_, previous_z), (a, _) in zip(ranges, ranges[1:])), 'Overlapping selector cells')
    need(dict(counts) == {k: v for k, v in config['expected_counts'].items() if v} and
         len(rows) == config['expected_segments'], 'Exact selector counts differ')
    need({r['owners'][0] for r in rows} == owners, 'Target lacks candidate selector cells')
    return rows, counts


def peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024


def ordinary_bytes(filename, limit=MAX_FILE):
    filename = Path(filename).absolute()
    need(all(not p.is_symlink() for p in [filename, *filename.parents]), 'Symlink in input path')
    need(filename.is_file() and filename.stat().st_size <= limit, 'Bounded ordinary file required')
    with filename.open('rb') as handle:
        raw = handle.read(limit + 1)
    need(len(raw) <= limit, 'File exceeded bounded read')
    return raw


def runtime_paths():
    """Loaded Python/extension bodies plus bundled NumPy/GEOS shared libraries.

    This inventories file-backed modules, executable and package-bundled native
    libraries. The operating system loader/libc and process-tree allocations are
    not a hermetic or fully contained runtime and are not claimed as such.
    """
    result = {str(Path(sys.executable).resolve())}
    venv = Path(sys.prefix) / 'pyvenv.cfg'
    if venv.is_file():
        result.add(str(venv.resolve()))
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename)
        if path.suffix == '.pyc':
            source = Path(importlib.util.source_from_cache(str(path)))
            if source.is_file():
                path = source
        if path.is_file() and path.resolve() != Path(__file__).resolve():
            result.add(str(path.resolve()))
    for name in ('numpy', 'shapely'):
        module = sys.modules.get(name)
        if module:
            directory = Path(module.__file__).resolve().parent.parent / (name + '.libs')
            if directory.is_dir():
                result.update(str(p.resolve()) for p in directory.iterdir() if p.is_file())
    return sorted(result)


def verify_runtime(admission):
    files = admission['runtime_files']
    need(isinstance(files, list) and 0 < len(files) <= 512, 'Bounded runtime file inventory required')
    pins = exact_map(files, 'path')
    resolved = {str(Path(name).resolve()) for name in pins}
    need(len(resolved) == len(pins), 'Duplicate resolved runtime file')
    missing = sorted(set(runtime_paths()) - resolved)
    need(not missing, 'Loaded runtime file omitted from admission inventory: ' + ', '.join(missing))
    total = 0
    for name, pin in pins.items():
        need(Path(name).is_absolute(), 'Absolute runtime file path required')
        raw = ordinary_bytes(Path(name).resolve())
        need(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Loaded runtime file drift: ' + name)
        total += len(raw)
    need(total == admission['runtime_inventory_bytes'], 'Runtime inventory total differs')


def run(repo, config_path, admission_path, output, publication_prefix):
    safe_path(publication_prefix)
    need(__debug__, 'Optimized Python would disable scientific predicates')
    start = time.monotonic()
    config_raw = ordinary_bytes(config_path)
    config = json.loads(config_raw)
    pins = validate_config(config)
    admission = json.loads(ordinary_bytes(admission_path))
    need(0 <= time.time() - admission['observed_unix_seconds'] < 60, 'Fresh admission expired or future dated')
    need(admission['program_sha256'] == sha(ordinary_bytes(__file__)) and
         admission['config_sha256'] == sha(config_raw), 'Admitted source program/config drift')
    for field in ('runtime_inventory_bytes', 'execution_reserve_bytes'):
        need(type(admission[field]) is int and admission[field] >= 0, 'Invalid admission resource inventory')
    for field in ('rssBytes', 'phaseBytes'):
        need(positive_int(admission['allowance'][field]), 'Invalid admission allowance')
    OUT = Path(output).absolute()
    need(all(not p.is_symlink() for p in [OUT, *OUT.parents]), 'Symlink in output path')
    need(not OUT.exists() and OUT.parent.is_dir(), 'Require fresh output directory and existing ordinary parent')
    BASE, CURRENT_BASE = config['scientific_input_commit'], config['accepted_head']
    WORKER = config['worker_id']
    FAMILIES = [f['id'] for f in config['families']]
    EXPECTED = {t['owner']: t for t in config['targets']}
    OWNERS = set(EXPECTED)
    roles = config['roles']
    LIMIT, PHASE_LIMIT = admission['allowance']['rssBytes'], admission['allowance']['phaseBytes']
    INPUT_LIMIT = config['resources']['input_bytes']
    DEADLINE_SECONDS = config['resources']['deadline_seconds']
    OUTPUT_LIMIT = config['resources']['output_bytes']
    inputs, products = {}, {}
    env = {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
    def git(*args):
        return subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', str(repo), *args], env=env)
    def check_memory():
        need(peak() < LIMIT, 'Source qualification exceeded fresh RSS allowance at check boundary')
        need(time.monotonic() - start < DEADLINE_SECONDS, 'Source qualification exceeded finite deadline at check boundary')
        charged = sum(p['bytes'] + p.get('decoded_bytes', 0) for p in inputs.values())
        need(charged <= INPUT_LIMIT, 'Combined encoded/decoded input cap exceeded')
        need(charged + admission['runtime_inventory_bytes'] + admission['execution_reserve_bytes'] < PHASE_LIMIT,
             'Complete charged phase exceeded fresh allowance')
    check_memory()
    declared = sum(p['bytes'] + p.get('decoded_bytes', 0) for p in pins.values())
    need(declared + admission['runtime_inventory_bytes'] + admission['execution_reserve_bytes'] < PHASE_LIMIT,
         'Declared complete phase exceeds fresh allowance')
    import numpy as np
    import shapely
    from shapely.geometry import shape
    runtime = {'python': sys.version, 'numpy': np.__version__, 'shapely': shapely.__version__, 'geos': shapely.geos_version_string}
    need(runtime == config['runtime'], 'Installed scientific runtime versions differ')
    verify_runtime(admission)
    def read(name, scientific=True):
        need(name in pins, 'Unpinned consumed source input: ' + name)
        pin = pins[name]
        row = git('ls-tree', '-z', pin['commit'], '--', name).decode()
        need(row == '100644 blob ' + pin['git_blob_oid'] + '\t' + name + '\0', 'Pinned ordinary Git input differs')
        need(int(git('cat-file', '-s', pin['git_blob_oid'])) == pin['bytes'], 'Pinned Git input size differs')
        if scientific:
            need(pin['commit'] == BASE and git('rev-parse', CURRENT_BASE + ':' + name).decode().strip() == pin['git_blob_oid'],
                 'Scientific input differs from accepted current base: ' + name)
        raw = git('cat-file', 'blob', pin['git_blob_oid'])
        need(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Pinned input byte identity differs')
        body = raw
        if name.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                body = stream.read(MAX_FILE + 1)
            need(len(body) == pin['decoded_bytes'] <= MAX_FILE and sha(body) == pin['decoded_sha256'], 'Pinned decoded input differs')
        inputs[name] = dict(pin)
        check_memory()
        return body
    def jread(name, scientific=True):
        return json.loads(read(name, scientific))
    def publish(name, body):
        raw = (json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
        need(name not in products and len(raw) + sum(len(r) for r in products.values()) <= OUTPUT_LIMIT, 'Cumulative source output cap exceeded')
        products[name] = raw
        return {'path': publication_prefix + '/' + name, 'bytes': len(raw), 'sha256': sha(raw)}
    def holes(geometry):
        return sum(len(poly.interiors) for poly in ([geometry] if geometry.geom_type == 'Polygon' else geometry.geoms))

    catalogue = jread(roles['catalogue'])
    catalogue_by_family = exact_map(catalogue['products'], 'key')
    full_roster = jread(roles['roster'])
    family_indices = {r['family_index'] for r in config['families']}
    roster = exact_map([r for r in full_roster if r['family_index'] in family_indices], 'source_id')
    need(len({r['source_index'] for r in roster.values()}) == len(roster), 'Duplicate source index')
    del full_roster
    gc.collect()
    lineage = jread(roles['lineage'])
    locations = exact_map([r for r in lineage['locations'] if r['index'] in OWNERS], 'index')
    assert len(locations) == len(OWNERS)
    for owner, loc in locations.items():
        expectation=EXPECTED[owner]
        expected_id,expected_name,expected_source_index=(expectation[k] for k in ('id','name','source_index'))
        assert loc['id']==expected_id and loc['name']==expected_name
        assert roster[expected_id]['source_index']==expected_source_index
        assert loc['province_id'] == EXPECTED[owner]['parent_id'] and loc['source_atoms'] == [loc['id']]
        assert lineage['reverse'][loc['id']] == [owner] and roster[loc['id']]['owners'] == [owner]
    del lineage
    gc.collect()
    target_ids = {r['id'] for r in locations.values()}
    selected = {}
    for part_path in roles['geography']:
        part = jread(part_path)
        for ident, feature in exact_map(part['features'], 'id').items():
            if ident in target_ids:
                need(ident not in selected, 'Duplicate target in geographic parts')
                selected[ident] = feature
    assert set(selected) == target_ids
    for owner,loc in locations.items():
        feature=selected[loc['id']]
        props=feature['properties'];meta=props['metadata']
        assert props['name']==EXPECTED[owner]['name'] and props['reference_owner']==EXPECTED[owner]['reference_owner']
        assert meta['source_id']==EXPECTED[owner]['source_id'] and meta['administrative_level']==EXPECTED[owner]['administrative_level']
        assert meta['original_id']==EXPECTED[owner]['id'].split(':')[-1]
        assert meta['reference_year']==EXPECTED[owner]['reference_year'] and meta['source_role']==EXPECTED[owner]['source_role']
        assert props['parent_id']==EXPECTED[owner]['parent_id']
    del part
    gc.collect()

    selector = jread(roles['selector'], scientific=False)
    segments, counts = selector_segments(selector, config)
    accounting_path = selector.get('accepted_interval_subtraction_only')

    latpath = roles['latitudes']
    latitudes = np.frombuffer(read(latpath), dtype='<f8')
    assert len(latitudes) == 262166
    cells = []
    for segment in segments:
        for x in range(segment['start'], segment['end']):
            cells.append((x, segment['y'], segment['owners'][0], set(segment['sids']), segment['category']))
    points = shapely.points([[(x+.5)/262166*360-180, latitudes[y]] for x, y, *_ in cells])
    actual = [set() for _ in cells]
    complete_families = []
    source_members = []
    source_targets = {}
    source_target_geometries = {}
    for family in FAMILIES:
        record = catalogue_by_family[family]
        pieces = []
        for pin in record['parts']:
            raw = read(pin['path'])
            observed = inputs[pin['path']]
            assert observed['sha256'] == pin['sha256'] and observed['bytes'] == pin['bytes']
            assert len(raw) == pin['uncompressed_bytes'] and sha(raw) == pin['uncompressed_sha256']
            pieces.append(raw)
        body = b''.join(pieces)
        assert len(body) == record['original_bytes'] and sha(body) == record['original_sha256']
        product = json.loads(body)
        assert product['crs']['properties']['name'] == 'urn:ogc:def:crs:OGC:1.3:CRS84'
        ids = [family + ':' + f['properties']['shapeID'] for f in product['features']]
        expected = [r['source_id'] for r in sorted(roster.values(), key=lambda r: r['source_index'])
                    if r['source_id'].startswith(family + ':')]
        assert ids == expected and len(ids) == record['feature_count']
        invalid = []
        for ident, feature in zip(ids, product['features']):
            geometry = shape(feature['geometry'])
            if not geometry.is_valid:
                invalid.append({'id': ident, 'reason': shapely.is_valid_reason(geometry)})
            hits = shapely.covers(geometry, points)
            if any(hits):
                assert geometry.is_valid, 'Relevant raw source geometry is invalid'
                source_members.append({'id': ident, 'name': feature['properties']['shapeName'],
                                       'candidate_cells': int(np.count_nonzero(hits)), 'valid': True})
                for i in np.flatnonzero(hits):
                    actual[i].add(roster[ident]['source_index'])
            if ident in target_ids:
                target=next(v for v in EXPECTED.values() if v['id']==ident)
                expected_name=target['name']
                assert feature['properties']['shapeName']==expected_name
                assert feature['properties']['shapeGroup']==target['shape_group'] and feature['properties']['shapeType']==target['shape_type']
                source_targets[ident] = feature
                source_target_geometries[ident] = geometry
            check_memory()
        complete_families.append({'source_family': family, 'features': len(ids), 'original_bytes': len(body),
                                 'original_sha256': sha(body), 'ordered_ids_match': True,
                                 'represented_year': record['source_represented_year_claim'],
                                 'recorded_license': record['recorded_license'], 'invalid_features': invalid})
        del body, pieces, product, geometry
        gc.collect()
        print('complete source', family, len(ids), flush=True)
    assert set(source_targets) == target_ids
    assert all(roster[locations[c[2]]['id']]['source_index'] in a for c,a in zip(cells,actual)), 'Candidate lacks direct target source membership'
    source_id_by_index = {r['source_index']:ident for ident,r in roster.items()}
    foreign_source_hits = np.array([any(not source_id_by_index[sid].startswith('gb:IDN:') for sid in a) for a in actual], dtype=bool)
    mismatches = [{'x': c[0], 'y': c[1], 'stored': sorted(c[3]), 'actual': sorted(a)}
                  for c, a in zip(cells, actual) if a != c[3]]
    assert not mismatches, 'Source memberships disagree with frozen native queue'

    country_path = roles['countries']
    country_raw = read(country_path)
    country_pins = jread(roles['country_registry'])
    assert sha(country_raw) == country_pins['hashes'][config['country']['registry_hash_key']]
    country_product = json.loads(country_raw)
    del country_raw
    country_hits = collections.Counter()
    competing = []
    indonesia_hits = np.zeros(len(cells), dtype=bool)
    for feature in country_product['features']:
        geometry = shape(feature['geometry'])
        hits = shapely.covers(geometry, points)
        n = int(np.count_nonzero(hits))
        if n:
            properties = feature['properties']
            code = properties['ADM0_A3']
            country_hits[code] += n
            if code == 'IDN':
                indonesia_hits |= hits
            else:
                competing.append({'code': code, 'name': properties.get('ADMIN'), 'cells': n,
                                  'interval_witnesses': [{'x': cells[i][0], 'y': cells[i][1]} for i in np.flatnonzero(hits)]})
    del country_product, geometry
    gc.collect()
    # Preserve any competitor witnesses for withholding; do not erase successful source observations.
    foreign_hits = np.zeros(len(cells), dtype=bool)
    for rival in competing:
        witness = {(p['x'],p['y']) for p in rival['interval_witnesses']}
        foreign_hits |= np.array([(c[0],c[1]) in witness for c in cells],dtype=bool)

    for method_path in roles['method_code']:
        read(method_path)
    read(config['physical_reproducer']['path'], scientific=False)
    decisions = jread(roles['decisions'])
    review = [r for r in decisions['location_review'] if target_ids.intersection(r.get('ids', []))]
    del decisions
    gc.collect()
    target_results = []
    stages = []
    for owner, loc in sorted(locations.items()):
        ident = loc['id']
        feature = selected[ident]
        metadata = feature['properties']['metadata']
        original = source_target_geometries[ident]
        current = shape(feature['geometry'])
        assert current.is_valid and original.is_valid and holes(current) == holes(original) == 0
        assert feature['properties']['parent_id'] == EXPECTED[owner]['parent_id'] and metadata['original_id'] == ident.split(':')[-1]
        assert not any(metadata.get(key) for key in ['topology_reconciled', 'residual_overlap_repair', 'display_geometry_repaired'])
        inds = [i for i, c in enumerate(cells) if c[2] == owner]
        by_category = collections.Counter(cells[i][4] for i in inds)
        outside = sum(not indonesia_hits[i] for i in inds)
        target_results.append({'id': ident, 'pixelIndex': owner, 'name': loc['name'],
                               'current_parent_id': EXPECTED[owner]['parent_id'], 'raw_valid': True, 'current_valid': True,
                               'raw_holes': 0, 'current_holes': 0,
                               'topology_reconciled': False, 'display_geometry_repaired': False,
                               'candidate_cells': dict(by_category), 'outside_retained_IDN_reference': outside,
                               'competing_reference_country_cells': int(np.count_nonzero(foreign_hits[inds])),
                               'competing_foreign_source_cells': int(np.count_nonzero(foreign_source_hits[inds])),
                               'source_reference_eligible_repair_cells': sum(cells[i][4]=='repair' and not bool(foreign_hits[i]) and not bool(foreign_source_hits[i]) for i in inds),
                               'base_geometry_sha256': sha(json.dumps(feature['geometry'], separators=(',', ':')).encode()),
                               'status': 'source-prerequisites-supported; physical/native-authority-pending'})
        stages.append({'target': ident, 'consumed': source_targets[ident], 'selected': feature})

    repair_segments = [r for r in segments if r['category'] == 'repair']
    physical_segments = [r for r in segments if r['category'] == 'physical']
    outputs = []
    outputs.append(publish('original-stage-inputs.json', stages))
    outputs.append(publish('cohort-intervals.json', {'version': 1, 'issue': config['issue'], 'scientific_input_commit': BASE, 'accepted_head': CURRENT_BASE,
        'repair_segments': repair_segments, 'physical_segments': physical_segments,
        'source_conflict_segments': [], 'cells': dict(counts), 'accepted_interval_subtraction_only': accounting_path,
        'current_owner_zero_proof': 'Pending actual accepted-selection owner-zero/consumer phase'}))
    outputs.append(publish('cohort-config.json', {'version': 1, 'issue': config['issue'], 'worker_id': WORKER,
        'scientific_input_commit': BASE, 'accepted_head': CURRENT_BASE, 'source_family': 'gb:IDN:ADM2', 'source_products': FAMILIES,
        'target_ids': sorted(target_ids), 'owner_indices': sorted(OWNERS), 'native_blocks': sorted(set(r['y']//4096 for r in segments)),
        'constructor': {'module': 'scripts/delivery-handoff-advance.mjs', 'export': 'constructOriginalAuthority',
                        'reader': 'ImmutableReader', 'immutable_locators': 'Pending committed source_evidence and native_patch'},
        'operator': {'module': 'src/native-grid.js', 'export': 'deriveSourceTargetNativeDelta',
                     'maximum_rows_per_frame': 4096},
        'physical_reproducer': config['physical_reproducer'],
        'physical_stage_inputs': publication_prefix + '/original-stage-inputs.json',
        'physical_source_status': 'Not executed; complete original GSHHG hierarchy required',
        'territorial_exclusions': 'No target holes or recorded topology/display repair; all complete-source/country competitor witnesses are retained and foreign/reference cases withheld. This is not global territorial adjudication.',
        'native_patch_status': 'Not produced', 'cumulative_write_status': 'Not authorized', 'repaired_credit': 0}))
    check_memory()
    outputs.append(publish('source-qualification.json', {'version': 1, 'issue': config['issue'], 'worker_id': WORKER,
        'scientific_input_commit': BASE, 'base_commit': CURRENT_BASE, 'method': 'Shared Indonesia source-cohort qualification: complete original-family custody, exact raw source identities, independent Shapely covers at authenticated native centres, all retained reference-country coverage, original/current geometry and lineage checks.',
        'runtime': {'python': sys.version, 'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
                    'numpy': np.__version__}, 'candidate_cells': len(cells), 'counts': dict(counts),
        'source_membership_mismatch_cells': 0, 'complete_families': complete_families,
        'covering_source_members': source_members, 'reference_country_counts': dict(country_hits),
        'outside_retained_IDN_reference_cells': int(np.count_nonzero(~indonesia_hits)),
        'competing_reference_country_cells': int(np.count_nonzero(foreign_hits)), 'competing_reference_countries': competing,
        'competing_foreign_source_cells': int(np.count_nonzero(foreign_source_hits)),
        'targets': target_results, 'existing_location_review': review,
        'source_prerequisite_repair_candidates': sum(r['source_reference_eligible_repair_cells'] for r in target_results), 'physical_interpretation_held_cells': counts['physical'],
        'native_authority_qualified_cells': 0, 'repaired_credit': 0,
        'limits': ['Source qualifications alone do not prove current physical support or grant territorial/semantic/historical approval.',
                   'Exact accepted-patch interval subtraction is preparation only; actual current-owner zero and selected-reader conservation remain pending.',
                   'Absence from a coarse country coastline does not establish competing-country ownership; the accepted reconciler preserved non-overlapping coastline coverage.',
                   'Complete GSHHG hierarchy interpretation, admitted native constructor/operator and actual selected-reader conservation remain pending.',
                   'All direct target identities preserve their semantically open framework parent; no official-parent or territorial adjudication claim is made. Foreign/reference witnesses and all physical holds remain separate.'],
        'inputs': list(inputs.values()), 'preparation_outputs': outputs,
        'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(), 'fresh_admission': admission, 'boundary_rss_limit_bytes': LIMIT, 'boundary_deadline_seconds': DEADLINE_SECONDS, 'operating_limits': ['Checks occur at code/feature boundaries; no live RSS supervisor, hard timeout, process-tree containment or enforced output/log stream cap is claimed.', 'Complete raw/decoded input cap is 256 MiB; output writers cap cumulative JSON products at 16 MiB; parsed/native expansion remains data-dependent.', 'Runtime inventory covers executable, loaded file-backed Python/extension modules and package-bundled NumPy/GEOS libraries; OS loader/system libraries are not a hermetic runtime closure.']}))
    publish('execution-receipt.json', {'version': 1, 'issue': config['issue'], 'worker_id': WORKER,
        'complete': True, 'program': {'path': 'scripts/qualify-source-cohort.py', 'sha256': sha(Path(__file__).read_bytes())},
        'outputs': outputs, 'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(),
        'source_prerequisite_repair_candidates': sum(r['source_reference_eligible_repair_cells'] for r in target_results), 'physical_interpretation_held_cells': counts['physical'],
        'native_authority_qualified_cells': 0, 'repaired_credit': 0})
    check_memory()
    need(set(inputs) == set(pins), 'Declared input inventory contains unconsumed files')
    verify_runtime(admission)
    need(all(not p.is_symlink() for p in [OUT, *OUT.parents]) and not OUT.exists(), 'Output destination changed during computation')
    OUT.mkdir()
    # Products stay in memory until all computation/admission succeeds. Receipt is
    # written last; interrupted publication cannot look like a complete run.
    for name, raw in products.items():
        with (OUT / name).open('xb') as handle:
            handle.write(raw)
    return {'complete': True, 'output': str(OUT), 'products': list(products), 'repaired_credit': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--admission', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--publication-prefix', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.repo, args.config, args.admission, args.output, args.publication_prefix)))
