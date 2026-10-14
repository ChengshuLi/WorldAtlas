"""Private Riau workload adaptation of the accepted Indonesia source probe.

This is source preparation, not a native authority or a selected repair writer.
Complete original sources are streamed, preserved, and checked at native centres.
"""
import collections, gc, gzip, hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import shape

BASE = 'f5898ab7a791e343e40dccf0e8f94b082b4049b2'
CURRENT_BASE = 'ecb837c599544ff8462b50f43a678d60c80fa5f6'
QUEUE = 'coordination/engineering/global-current-cell-work-queue-20261014/'
PREP = Path(__file__).resolve().parent
OUT = PREP / 'source-run-001'
assert OUT.is_dir() and not any(OUT.iterdir()), 'Require fresh pre-created output directory'
admission = json.loads((PREP / 'source-admission-001.json').read_bytes())
assert time.time()-admission['observed_unix_seconds'] < 60, 'Fresh admission expired'
WORKER = '01a1275a-c716-71e6-8917-50c14148900e'
PROVINCE = 'framework:province:riau-islands:4839c8831796'
FAMILIES = ['gb:IDN:ADM1', 'gb:IDN:ADM2', 'gb:MYS:ADM1', 'gb:MYS:ADM2',
            'gb:PNG:ADM1', 'gb:PNG:ADM2', 'gb:PNG:ADM3', 'gb:TLS:ADM1', 'gb:TLS:ADM2']
OWNERS = {22849, 22871, 22985, 23055}
EXPECTED = {
    22849: ('gb:IDN:ADM2:22746128B38340908247842', 'Karimun', 36402),
    22871: ('gb:IDN:ADM2:22746128B41866695352092', 'Lingga', 36561),
    22985: ('gb:IDN:ADM2:22746128B62804497316712', 'Bintan', 36316),
    23055: ('gb:IDN:ADM2:22746128B73074683492420', 'Kota Tanjung Pinang', 36522),
}
LIMIT = admission['allowance']['rssBytes']
PHASE_LIMIT = admission['allowance']['phaseBytes']
INPUT_LIMIT = 256 * 1024 * 1024
DEADLINE_SECONDS = 180
OUTPUT_LIMIT = 16 * 1024 * 1024
inputs = {}
start = time.monotonic()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
os.environ['GIT_NO_LAZY_FETCH'] = '1'

def peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024

def check_memory():
    assert peak() < LIMIT, 'Source qualification exceeded fresh RSS allowance at check boundary'
    assert time.monotonic()-start < DEADLINE_SECONDS, 'Source qualification exceeded finite deadline at check boundary'
    charged = sum(p['bytes']+p.get('decoded_bytes',0) for p in inputs.values())
    assert charged <= INPUT_LIMIT, 'Combined encoded/decoded input cap exceeded'
    assert charged+admission['runtime_inventory_bytes']+admission['execution_reserve_bytes'] < PHASE_LIMIT, 'Complete charged phase exceeded fresh allowance'

def read(path, commit=BASE, decode=True):
    current_oid = subprocess.check_output(['git','rev-parse',CURRENT_BASE+':'+path], text=True).strip()
    source_oid = subprocess.check_output(['git','rev-parse',commit+':'+path], text=True).strip()
    assert current_oid == source_oid, 'Scientific input differs from accepted current base: '+path
    raw = subprocess.check_output(['git','-c','protocol.allow=never','cat-file','blob',source_oid])
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
    assert len(raw) <= OUTPUT_LIMIT
    assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())+len(raw) <= OUTPUT_LIMIT
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
assert len(locations) == len(OWNERS) == 4
for owner, loc in locations.items():
    expected_id,expected_name,expected_source_index=EXPECTED[owner]
    assert loc['id']==expected_id and loc['name']==expected_name
    assert roster[expected_id]['source_index']==expected_source_index
    assert loc['province_id'] == PROVINCE and loc['source_atoms'] == [loc['id']]
    assert lineage['reverse'][loc['id']] == [owner] and roster[loc['id']]['owners'] == [owner]
del lineage
gc.collect()
target_ids = {r['id'] for r in locations.values()}
part = jread('data/geography/part-10.json')
selected = {f['id']: f for f in part['features'] if f['id'] in target_ids}
assert set(selected) == target_ids
for owner,loc in locations.items():
    feature=selected[loc['id']]
    props=feature['properties'];meta=props['metadata']
    assert props['name']==EXPECTED[owner][1] and props['reference_owner']=='Indonesia'
    assert meta['source_id']=='gb:IDN:ADM2' and meta['administrative_level']=='ADM2'
    assert meta['original_id']==EXPECTED[owner][0].split(':')[-1]
    assert meta['reference_year']=='2020' and meta['source_role']=='regency, city'
    assert props['parent_id']==PROVINCE
del part
gc.collect()

selector = private_read(PREP / 'exact-candidate-selectors.json.gz', {'bytes':42573,'sha256':'a67ebfff17627f09260c34e34d7c775ea637252dbbe106d5f26f1bc2a1717f45'})
assert selector['as_of_commit'] == BASE
segments=[]
counts=collections.Counter()
for category,y,a,z,owners,sids,physical in selector['rows']:
    assert category in ['repair','physical'] and 0<=y<262166 and 0<=a<z<=262166
    assert len(owners)==1 and owners[0] in OWNERS
    segments.append({'category':category,'y':y,'start':a,'end':z,'owners':owners,'sids':sids,'physical':physical})
    counts[category]+=z-a
assert dict(counts)=={'repair':14054,'physical':4760} and len(segments)==7825
# Interval subtraction is retained separately; actual current-owner zero remains pending.
accounting_path = str(PREP / 'accepted-overlap-check.json')

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
            expected_name=next(v[1] for v in EXPECTED.values() if v[0]==ident)
            assert feature['properties']['shapeName']==expected_name
            assert feature['properties']['shapeGroup']=='IDN' and feature['properties']['shapeType']=='ADM2'
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
# Preserve any competitor witnesses for withholding; do not erase successful source observations.
foreign_hits = np.zeros(len(cells), dtype=bool)
for rival in competing:
    witness = {(p['x'],p['y']) for p in rival['interval_witnesses']}
    foreign_hits |= np.array([(c[0],c[1]) in witness for c in cells],dtype=bool)

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
outputs.append(publish('cohort-intervals.json', {'version': 1, 'issue': 1884, 'scientific_input_commit': BASE, 'accepted_head': CURRENT_BASE,
    'repair_segments': repair_segments, 'physical_segments': physical_segments,
    'source_conflict_segments': [], 'cells': dict(counts), 'accepted_interval_subtraction_only': accounting_path,
    'current_owner_zero_proof': 'Pending actual accepted-selection owner-zero/consumer phase'}))
outputs.append(publish('cohort-config.json', {'version': 1, 'issue': 1884, 'worker_id': WORKER,
    'scientific_input_commit': BASE, 'accepted_head': CURRENT_BASE, 'source_family': 'gb:IDN:ADM2', 'source_products': FAMILIES,
    'target_ids': sorted(target_ids), 'owner_indices': sorted(OWNERS), 'native_blocks': sorted(set(r['y']//4096 for r in segments)),
    'constructor': {'module': 'scripts/delivery-handoff-advance.mjs', 'export': 'constructOriginalAuthority',
                    'reader': 'ImmutableReader', 'immutable_locators': 'Pending committed source_evidence and native_patch'},
    'operator': {'module': 'src/native-grid.js', 'export': 'deriveSourceTargetNativeDelta',
                 'maximum_rows_per_frame': 4096},
    'physical_reproducer': 'coordination/engineering/source-target-native-delivery-20261014/evidence/physical-reproduction.py',
    'physical_stage_inputs': str(OUT / 'original-stage-inputs.json'),
    'physical_source_status': 'Not executed; complete original GSHHG hierarchy required',
    'territorial_exclusions': 'No target holes or recorded topology/display repair; all complete-source/country competitor witnesses are retained and foreign/reference cases withheld. This is not global territorial adjudication.',
    'native_patch_status': 'Not produced', 'cumulative_write_status': 'Not authorized', 'repaired_credit': 0}))
check_memory()
outputs.append(publish('source-qualification.json', {'version': 1, 'issue': 1884, 'worker_id': WORKER,
    'scientific_input_commit': BASE, 'base_commit': CURRENT_BASE, 'method': 'Riau cohort adaptation of accepted Indonesia check-sources.py: complete original-family custody, exact raw source identities, independent Shapely covers at authenticated native centres, all retained reference-country coverage, original/current geometry and lineage checks.',
    'runtime': {'python': sys.version, 'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
                'numpy': np.__version__}, 'candidate_cells': len(cells), 'counts': dict(counts),
    'source_membership_mismatch_cells': 0, 'complete_families': complete_families,
    'covering_source_members': source_members, 'reference_country_counts': dict(country_hits),
    'outside_retained_IDN_reference_cells': int(np.count_nonzero(~indonesia_hits)),
    'competing_reference_country_cells': int(np.count_nonzero(foreign_hits)), 'competing_reference_countries': competing,
    'competing_foreign_source_cells': int(np.count_nonzero(foreign_source_hits)),
    'targets': target_results, 'existing_location_review': review,
    'source_prerequisite_repair_candidates': sum(r['source_reference_eligible_repair_cells'] for r in target_results), 'physical_interpretation_held_cells': 4760,
    'native_authority_qualified_cells': 0, 'repaired_credit': 0,
    'limits': ['Source qualifications alone do not prove current physical support or grant territorial/semantic/historical approval.',
               'Exact accepted-patch interval subtraction is preparation only; actual current-owner zero and selected-reader conservation remain pending.',
               'Absence from a coarse country coastline does not establish competing-country ownership; the accepted reconciler preserved non-overlapping coastline coverage.',
               'Complete GSHHG hierarchy interpretation, admitted native constructor/operator and actual selected-reader conservation remain pending.',
               'All four direct target identities preserve their semantically open framework parent; no official-parent or territorial adjudication claim is made. Foreign/reference witnesses and all physical holds remain separate.'],
    'inputs': list(inputs.values()), 'preparation_outputs': outputs,
    'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(), 'fresh_admission': admission, 'boundary_rss_limit_bytes': LIMIT, 'boundary_deadline_seconds': DEADLINE_SECONDS, 'operating_limits': ['Checks occur at code/feature boundaries; no live RSS supervisor, hard timeout, process-tree containment or enforced output/log stream cap is claimed.', 'Complete raw/decoded input cap is 256 MiB; output writers cap cumulative JSON products at 16 MiB; parsed/native expansion remains data-dependent.']}))
publish('execution-receipt.json', {'version': 1, 'issue': 1884, 'worker_id': WORKER,
    'complete': True, 'program': {'path': str(PREP / 'check-riau-sources.py'), 'sha256': sha((PREP / 'check-riau-sources.py').read_bytes())},
    'outputs': outputs, 'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(),
    'source_prerequisite_repair_candidates': sum(r['source_reference_eligible_repair_cells'] for r in target_results), 'physical_interpretation_held_cells': 4760,
    'native_authority_qualified_cells': 0, 'repaired_credit': 0})
print(json.dumps({'complete': True, 'outputs': outputs, 'candidate_cells': len(cells),
                  'elapsed_seconds': time.monotonic()-start, 'peak_rss_bytes': peak(), 'repaired_credit': 0}))
