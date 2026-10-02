"""Recheck near-half ownership with finer ellipsoidal area, retaining execution proof."""
import collections
import gzip
import hashlib
import json
import pathlib
import shutil
import sqlite3
import subprocess

from shapely import from_wkb
from shapely.geometry import shape
from majority import canonical, decide

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = DATA / 'ownership-history'
SCRIPT = pathlib.Path(__file__).resolve()


def read(file):
    return json.loads(gzip.decompress(file.read_bytes()) if file.suffix == '.gz' else file.read_text())


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def write_part(file, value):
    file.write_bytes(gzip.compress(json.dumps(value, separators=(',', ':')).encode(), mtime=0))
    return digest(file)


index = read(OUT / 'index.json')
assert index['version'] == 2
proof = {'script_sha256': digest(SCRIPT), 'area_algorithm_sha256': digest(ROOT / 'scripts/majority.py')}
if any(r.get('kind') == 'adaptive-majority-area' and all(r.get(k) == v for k, v in proof.items()) for r in index.get('refinements', [])):
    print('Adaptive majority refinement is current')
    raise SystemExit
footprints = subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip()
assert footprints == index['footprints_sha256'], 'Location footprints changed after ownership preparation'
for name, expected in index['inputs'].items():
    if name.startswith('cliopatria/'):
        assert digest(DATA / name) == expected, f'Changed historical source: {name}'

critical = {}
offset = 0
for part in index['evidence_parts']:
    rows = read(OUT / part['path'])
    for n, evidence in enumerate(rows):
        if abs(evidence[1] - .5) <= 1e-5:
            critical[offset + n] = evidence
    offset += len(rows)
assert offset == index['evidence_records']

# Reuse the validated full source geometries, never the approximate area as the
# final near-threshold result. Each selected geometry is checked against its
# pinned raw source before reuse.
source_index = read(DATA / 'cliopatria/index.json')
sources = {}
source_positions = {}
source_owners = {}
j = 0
for chunk in dict.fromkeys(r['chunk'] for r in source_index['records']):
    for f in read(DATA / 'cliopatria' / chunk)['features']:
        sources[f['id']] = f
        source_positions[f['id']] = j
        p = f['properties']
        source_owners[f['id']] = 'owner:' + p['wikidata'] if p.get('wikidata') else 'owner:cliopatria:' + hashlib.sha256((p.get('seshat_id') or p['name']).encode()).hexdigest()[:16]
        j += 1
caches = list((ROOT / '.cache/ownership-overlaps').glob('*.sqlite'))
assert len(caches) == 1, 'Select one validated overlap cache before refinement'
measurements = sqlite3.connect('file:' + str(caches[0]) + '?mode=ro', uri=True)
assert measurements.execute('SELECT last_record FROM progress WHERE singleton=1').fetchone()[0] == j - 1
geometries = {}
for evidence in critical.values():
    for n in evidence[4]:
        source_id = index['source_ids'][n]
        if source_id in geometries:
            continue
        stored = measurements.execute('SELECT geometry FROM source_geometry WHERE record=?', (source_positions[source_id],)).fetchone()
        assert stored, f'Missing source geometry: {source_id}'
        geometries[source_id] = from_wkb(stored[0])
        assert geometries[source_id].equals(canonical(shape(sources[source_id]['geometry']))), f'Cached source differs: {source_id}'

locations = {}
location_ids = []
world = read(DATA / 'world-index.json')
for part in index['parts']:
    for location_id, rows in read(OUT / part['path']):
        if any(row[4] in critical for row in rows):
            locations[location_id] = None
for part in world['parts']:
    for f in read(DATA / part)['features']:
        location_ids.append(f['id'])
        if f['id'] in locations:
            locations[f['id']] = canonical(shape(f['geometry']))
location_indices = {location_id: n for n, location_id in enumerate(sorted(location_ids))}
assert all(g is not None for g in locations.values())
db = sqlite3.connect('file:' + str(DATA / 'atlas.sqlite') + '?mode=ro', uri=True)
overrides = collections.defaultdict(list)
for location_id, start, end, raw in db.execute('SELECT location_id,valid_from,valid_to,geometry FROM boundaries WHERE is_example=0'):
    if location_id in locations:
        overrides[location_id].append((start, end, canonical(shape(json.loads(raw)))))
db.close()

owner_indices = {owner: n for n, owner in enumerate(index['owner_ids'])}
labels = {label: n for n, label in enumerate(index['labels'])}
new_evidence = []
intern = {}
reports = []
status_delta = collections.Counter()
result_cache = {}
for part in index['parts']:
    rows = read(OUT / part['path'])
    changed = False
    for location_id, intervals in rows:
        for row in intervals:
            start, end, old_owner, old_status, old_evidence = row
            if old_evidence not in critical:
                continue
            key = (location_id, old_evidence, start if critical[old_evidence][5] else None)
            if key not in result_cache:
                old = critical[old_evidence]
                footprint = next((g for a, b, g in overrides[location_id] if a <= start < b), locations[location_id])
                claims = collections.defaultdict(list)
                source_ids = [index['source_ids'][n] for n in old[4]]
                for source_id in source_ids:
                    claims[source_owners[source_id]].append(geometries[source_id])
                memo = {}
                result = decide(footprint, claims, cache=memo)
                # Screening evidence was near half. Require the adaptive path to
                # actually have used the finer denominator before publication.
                assert 'fine_total' in memo, 'Adaptive area denominator was not used'
                winner = None
                if result['owner']:
                    eligible = [s for s in source_ids if source_owners[s] == result['owner']]
                    # Preserve the original deterministic dated-label rule.
                    ranked = []
                    for source_id in eligible:
                        measured = measurements.execute('SELECT share FROM overlaps WHERE location=? AND record=?', (location_indices[location_id], source_positions[source_id])).fetchone()
                        share = measured[0] if measured else 0
                        ranked.append((-share, source_id))
                    winner = sources[min(ranked)[1]]['properties']['name']
                    if winner not in labels:
                        labels[winner] = len(index['labels'])
                        index['labels'].append(winner)
                evidence = [labels[winner] if winner else None, result['share'], result['coverage'], [[owner_indices[o], share] for o, share in result['candidates']], old[4], old[5]]
                serialized = json.dumps(evidence, separators=(',', ':'))
                if serialized not in intern:
                    intern[serialized] = index['evidence_records'] + len(new_evidence)
                    new_evidence.append(evidence)
                result_cache[key] = (owner_indices[result['owner']] if result['owner'] else None, index['statuses_order'].index(result['status']), intern[serialized], result)
            owner, status, evidence, result = result_cache[key]
            row[2:] = [owner, status, evidence]
            changed = True
            status_delta[index['statuses_order'][old_status]] -= 1
            status_delta[index['statuses_order'][status]] += 1
            reports.append({'location_id': location_id, 'valid_from': start, 'valid_to': end, 'old_share': critical[old_evidence][1], 'share': result['share'], 'old_status': index['statuses_order'][old_status], 'status': result['status'], 'old_owner': index['owner_ids'][old_owner] if old_owner is not None else None, 'owner': result['owner'], 'source_record_ids': [index['source_ids'][n] for n in critical[old_evidence][4]]})
    if changed:
        part['sha256'] = write_part(OUT / part['path'], rows)
measurements.close()

# Fill the existing final evidence chunk before adding another one, preserving
# the original 20,000-record chunk layout for consumers.
if new_evidence:
    last = index['evidence_parts'][-1]
    tail = read(OUT / last['path'])
    capacity = 20000 - len(tail)
    tail += new_evidence[:capacity]
    last['sha256'] = write_part(OUT / last['path'], tail)
    for offset in range(capacity, len(new_evidence), 20000):
        name = f'evidence-{len(index["evidence_parts"])}.json.gz'
        index['evidence_parts'].append({'path': name, 'sha256': write_part(OUT / name, new_evidence[offset:offset+20000])})
    index['evidence_records'] += len(new_evidence)
for status, delta in status_delta.items():
    index['statuses'][status] = index['statuses'].get(status, 0) + delta
algorithms = OUT / 'algorithms'
algorithms.mkdir(exist_ok=True)
shutil.copyfile(SCRIPT, algorithms / 'refine-ownership-threshold.py')
shutil.copyfile(ROOT / 'scripts/majority.py', algorithms / 'majority-refinement.py')
report = {'kind': 'adaptive-majority-area', **proof, 'screening_share_band': 1e-5, 'edge_densification_degrees': .01, 'footprints_sha256': footprints, 'checked_intervals': len(reports), 'checked_locations': len(locations), 'ownership_changes': sum(r['old_owner'] != r['owner'] for r in reports), 'status_changes': sum(r['old_status'] != r['status'] for r in reports), 'records': reports}
(OUT / 'threshold-refinement.json').write_text(json.dumps(report, separators=(',', ':')))
index.setdefault('refinements', []).append({k: v for k, v in report.items() if k != 'records'})
index['numerical_tolerances']['near_majority_screening_band'] = 1e-5
index['numerical_tolerances']['near_majority_edge_densification_degrees'] = .01
(OUT / 'index.json').write_text(json.dumps(index, separators=(',', ':')))
print(json.dumps({k: v for k, v in report.items() if k != 'records'}))
