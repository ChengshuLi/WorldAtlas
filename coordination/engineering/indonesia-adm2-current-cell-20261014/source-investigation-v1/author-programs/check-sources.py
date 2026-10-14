"""Private issue 1884 workload adaptation of the accepted Myeik source probe.

This is source preparation, not a native authority or a selected repair writer.
Complete original sources are streamed, preserved, and checked at native centres.
"""
import collections, gc, gzip, hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import shape

BASE = 'f7c358326d776398bc1cffe84df81eac7033091c'
QUEUE = 'coordination/engineering/global-current-cell-work-queue-20261014/'
OUT = Path('.cache/idn-source-qualification-1884-v1')
WORKER = '/root/idn_sources_61'
PROVINCE = 'framework:province:north-maluku:9e8f13182212'
FAMILIES = ['gb:IDN:ADM1', 'gb:IDN:ADM2', 'gb:MYS:ADM1', 'gb:MYS:ADM2',
            'gb:PNG:ADM1', 'gb:PNG:ADM2', 'gb:PNG:ADM3', 'gb:TLS:ADM1', 'gb:TLS:ADM2']
OWNERS = {22769, 22796, 22837, 22866, 22898, 22930, 23018, 23033, 23108, 23198}
LIMIT = 500 * 1024 * 1024
inputs = {}
start = time.monotonic()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
os.environ['GIT_NO_LAZY_FETCH'] = '1'

def peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024

def check_memory():
    assert peak() < LIMIT, 'Source qualification exceeded coordinated 500 MiB RSS'

def read(path, commit=BASE, decode=True):
    raw = subprocess.check_output(['git', 'show', commit + ':' + path])
    assert len(raw) <= 32 * 1024 * 1024
    pin = {'commit': commit, 'path': path, 'bytes': len(raw), 'sha256': sha(raw),
           'git_blob_oid': subprocess.check_output(['git', 'rev-parse', commit + ':' + path], text=True).strip()}
    if decode and path.endswith('.gz'):
        body = gzip.decompress(raw)
        assert len(body) <= 32 * 1024 * 1024
        pin.update(decoded_bytes=len(body), decoded_sha256=sha(body))
    else:
        body = raw
    inputs[commit + ':' + path] = pin
    check_memory()
    return body

def jread(path, commit=BASE):
    return json.loads(read(path, commit))

def private_read(path, expected=None):
    raw = Path(path).read_bytes()
    if expected:
        assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
    pin = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw), 'kind': 'private-retained-execution-input'}
    if str(path).endswith('.gz'):
        raw = gzip.decompress(raw)
        pin.update(decoded_bytes=len(raw), decoded_sha256=sha(raw))
    assert len(raw) <= 32 * 1024 * 1024
    inputs[str(path)] = pin
    return json.loads(raw)

def publish(name, body):
    raw = (json.dumps(body, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    assert len(raw) <= 32 * 1024 * 1024
    with (OUT / name).open('xb') as handle:
        handle.write(raw)
    return {'path': str(OUT / name), 'bytes': len(raw), 'sha256': sha(raw)}

def holes(geometry):
    return sum(len(poly.interiors) for poly in ([geometry] if geometry.geom_type == 'Polygon' else geometry.geoms))

catalogue = jread(QUEUE + 'retained-source-catalogue.json')
full_roster = jread(QUEUE + 'source-feature-roster.json.gz')
family_indices = {152, 153, 230, 231, 263, 264, 265, 327, 328}
roster = {r['source_id']: r for r in full_roster if r['family_index'] in family_indices}
del full_roster
gc.collect()
lineage = jread(QUEUE + 'lineage.json.gz')
locations = {r['index']: r for r in lineage['locations'] if r['index'] in OWNERS}
assert len(locations) == len(OWNERS) == 10
for owner, loc in locations.items():
    assert loc['province_id'] == PROVINCE and loc['source_atoms'] == [loc['id']]
    assert lineage['reverse'][loc['id']] == [owner] and roster[loc['id']]['owners'] == [owner]
del lineage
gc.collect()
target_ids = {r['id'] for r in locations.values()}
part = jread('data/geography/part-10.json')
selected = {f['id']: f for f in part['features'] if f['id'] in target_ids}
assert set(selected) == target_ids
del part
gc.collect()

accounting_path = '.cache/idn-adm2-current-accounting-v1/receipt.json'
accounting = private_read(accounting_path)
assert accounting['accepted_head'] == BASE
extract_root = Path('.cache/idn-adm2-extraction-20261014-v1')
segments = []
counts = collections.Counter()
for category in ['repair', 'physical', 'conflict']:
    package_path = extract_root / category / 'package.json'
    package = private_read(package_path, accounting['input_files'][str(package_path)])
    for block in package['native_blocks']:
        p = extract_root / category / f'block-{block:03}.json.gz'
        for row in private_read(p, accounting['input_files'][str(p)]):
            y, a, z, owners, sids, physical = row
            if not OWNERS.intersection(owners):
                continue
            assert len(owners) == 1 and owners[0] in OWNERS
            segments.append({'category': category, 'y': y, 'start': a, 'end': z,
                             'owners': owners, 'sids': sids, 'physical': physical})
            counts[category] += z-a
assert dict(counts) == {'repair': 12424, 'physical': 11080}
assert accounting['categories']['repair']['by_locality'][PROVINCE]['already_owned'] == 0
assert accounting['categories']['physical']['by_locality'][PROVINCE]['already_owned'] == 0

latpath = 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'
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
    record = next(r for r in catalogue['products'] if r['key'] == family)
    pieces = []
    for pin in record['parts']:
        raw = read(pin['path'])
        observed = inputs[BASE + ':' + pin['path']]
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
mismatches = [{'x': c[0], 'y': c[1], 'stored': sorted(c[3]), 'actual': sorted(a)}
              for c, a in zip(cells, actual) if a != c[3]]
assert not mismatches, 'Source memberships disagree with frozen native queue'

country_path = 'data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz'
country_raw = read(country_path)
country_pins = jread('data/sources.json')
assert sha(country_raw) == country_pins['hashes']['ne_10m_admin_0_countries']
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
assert not competing, 'Competing retained reference-country coverage requires withholding'

read('scripts/reconcile-topology.py')
read('scripts/prepare.mjs')
decisions = jread('data/geographic-decisions/asia.json')
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
    assert feature['properties']['parent_id'] == PROVINCE and metadata['original_id'] == ident.split(':')[-1]
    assert not any(metadata.get(key) for key in ['topology_reconciled', 'residual_overlap_repair', 'display_geometry_repaired'])
    inds = [i for i, c in enumerate(cells) if c[2] == owner]
    by_category = collections.Counter(cells[i][4] for i in inds)
    outside = sum(not indonesia_hits[i] for i in inds)
    target_results.append({'id': ident, 'pixelIndex': owner, 'name': loc['name'],
                           'current_parent_id': PROVINCE, 'raw_valid': True, 'current_valid': True,
                           'raw_holes': 0, 'current_holes': 0,
                           'topology_reconciled': False, 'display_geometry_repaired': False,
                           'candidate_cells': dict(by_category), 'outside_retained_IDN_reference': outside,
                           'competing_reference_country_cells': 0,
                           'base_geometry_sha256': sha(json.dumps(feature['geometry'], separators=(',', ':')).encode()),
                           'status': 'source-prerequisites-supported; physical/native-authority-pending'})
    stages.append({'target': ident, 'consumed': source_targets[ident], 'selected': feature})

repair_segments = [r for r in segments if r['category'] == 'repair']
physical_segments = [r for r in segments if r['category'] == 'physical']
outputs = []
outputs.append(publish('original-stage-inputs.json', stages))
outputs.append(publish('cohort-intervals.json', {'version': 1, 'issue': 1884, 'accepted_head': BASE,
    'repair_segments': repair_segments, 'physical_segments': physical_segments,
    'source_conflict_segments': [], 'cells': dict(counts), 'current_owner_zero_basis': accounting_path}))
outputs.append(publish('cohort-config.json', {'version': 1, 'issue': 1884, 'worker_id': WORKER,
    'accepted_head': BASE, 'source_family': 'gb:IDN:ADM2', 'source_products': FAMILIES,
    'target_ids': sorted(target_ids), 'owner_indices': sorted(OWNERS), 'native_blocks': [31, 32],
    'constructor': {'module': 'scripts/delivery-handoff-advance.mjs', 'export': 'constructOriginalAuthority',
                    'reader': 'ImmutableReader', 'immutable_locators': 'Pending committed source_evidence and native_patch'},
    'operator': {'module': 'src/native-grid.js', 'export': 'deriveSourceTargetNativeDelta',
                 'maximum_rows_per_frame': 4096},
    'physical_reproducer': 'coordination/engineering/source-target-native-delivery-20261014/evidence/physical-reproduction.py',
    'physical_stage_inputs': str(OUT / 'original-stage-inputs.json'),
    'physical_source_status': 'Not executed; complete original GSHHG hierarchy required',
    'territorial_exclusions': 'No target holes or recorded topology/display repair; complete competing-source/country probe had no competing coverage. This is not global territorial adjudication.',
    'native_patch_status': 'Not produced', 'cumulative_write_status': 'Not authorized', 'repaired_credit': 0}))
check_memory()
outputs.append(publish('source-qualification.json', {'version': 1, 'issue': 1884, 'worker_id': WORKER,
    'base_commit': BASE, 'method': 'Workload adaptation of accepted Myeik check-sources.py: complete original-family custody, exact raw source identities, independent Shapely covers at authenticated native centres, all retained reference-country coverage, original/current geometry and lineage checks.',
    'runtime': {'python': sys.version, 'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
                'numpy': np.__version__}, 'candidate_cells': len(cells), 'counts': dict(counts),
    'source_membership_mismatch_cells': 0, 'complete_families': complete_families,
    'covering_source_members': source_members, 'reference_country_counts': dict(country_hits),
    'outside_retained_IDN_reference_cells': int(np.count_nonzero(~indonesia_hits)),
    'competing_reference_country_cells': 0, 'competing_reference_countries': competing,
    'targets': target_results, 'existing_location_review': review,
    'source_prerequisite_repair_candidates': 12424, 'physical_interpretation_held_cells': 11080,
    'native_authority_qualified_cells': 0, 'repaired_credit': 0,
    'limits': ['Source qualifications alone do not prove current physical support or grant territorial/semantic/historical approval.',
               'Current owner-zero evidence is reused from the distinct current-ownership worker receipt; no independent full native-owner rebuild was run here.',
               'Absence from a coarse country coastline does not establish competing-country ownership; the accepted reconciler preserved non-overlapping coastline coverage.',
               'Complete GSHHG hierarchy interpretation, admitted native constructor/operator and actual selected-reader conservation remain pending.',
               'All ten targets lack current/original holes and recorded topology/display repair; no country reference or complete nine-family source competitor covers these native candidate centres.'],
    'inputs': list(inputs.values()), 'preparation_outputs': outputs,
    'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(), 'coordinated_rss_limit_bytes': LIMIT}))
publish('execution-receipt.json', {'version': 1, 'issue': 1884, 'worker_id': WORKER,
    'complete': True, 'program': {'path': str(OUT / 'check-sources.py'), 'sha256': sha((OUT / 'check-sources.py').read_bytes())},
    'outputs': outputs, 'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(),
    'source_prerequisite_repair_candidates': 12424, 'physical_interpretation_held_cells': 11080,
    'native_authority_qualified_cells': 0, 'repaired_credit': 0})
print(json.dumps({'complete': True, 'outputs': outputs, 'candidate_cells': len(cells),
                  'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(), 'repaired_credit': 0}))
