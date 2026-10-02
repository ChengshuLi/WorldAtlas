"""Globally recover candidates that coarse area cancellation may have omitted."""
import collections
import hashlib
import importlib.util
import json
import multiprocessing
import pathlib
import sqlite3
import subprocess

from shapely import STRtree, from_wkb, prepare, destroy_prepared
from shapely.geometry import shape
from majority import canonical, area

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = DATA / 'ownership-history'
DIR = ROOT / '.cache/ownership-overlaps'
read = lambda p: json.loads(p.read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
footprints = subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip()
index = read(OUT / 'index.json')
assert index['footprints_sha256'] == footprints
hashes = {p: h for p, h in index['inputs'].items() if p.startswith('cliopatria/')}
for p, expected in hashes.items():
    assert digest(DATA / p) == expected
paths = list(DIR.glob('*.sqlite'))
assert len(paths) == 1
cache = paths[0]
algorithm_hash = ''.join(digest(ROOT / 'scripts' / p) for p in ['majority.py', 'prepare-ownership.py', 'ellipsoidal_area.py'])
new_key = hashlib.sha256((footprints + ''.join(hashes[p] for p in sorted(hashes)) + algorithm_hash).encode()).hexdigest()
destination = DIR / f'{new_key}.sqlite'
receipt = OUT / 'candidate-recovery.json'
if receipt.exists() and read(receipt).get('algorithm_sha256') == algorithm_hash and read(receipt).get('footprints_sha256') == footprints:
    print('Numerical candidate recovery is current')
    raise SystemExit
world = read(DATA / 'world-index.json')
features = sorted([f for p in world['parts'] for f in read(DATA / p)['features']], key=lambda f: f['id'])
locations = [canonical(shape(f['geometry'])) for f in features]
totals = [area(g) for g in locations]
spec = importlib.util.spec_from_file_location('initial_coarse_math', OUT / 'algorithms/majority.py')
coarse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coarse)


def initialize():
    global lookup
    lookup = sqlite3.connect('file:' + str(cache) + '?mode=ro', uri=True)


def risks(task):
    start, end = task
    flagged = []
    old_invalid = 0
    for i in range(start, end):
        previous_total = coarse.area(locations[i])
        relative = abs(previous_total / totals[i] - 1)
        reasons = []
        if totals[i] < 1e6:
            reasons.append('land-footprint-under-1-km2')
        if relative > 1e-8:
            reasons.append('whole-footprint-coarse-area-drift')
        interned = {}
        for j, share, raw in lookup.execute('SELECT record,share,geometry FROM overlaps WHERE location=? ORDER BY record', (i,)):
            if raw is None:
                continue
            if raw not in interned:
                previous_area = coarse.area(from_wkb(raw))
                exact_area = share * totals[i]
                interned[raw] = (previous_area, exact_area)
            previous_area, exact_area = interned[raw]
            if exact_area <= 0 or abs(previous_area / exact_area - 1) > 1e-6:
                if 'partial-footprint-coarse-area-drift' not in reasons:
                    reasons.append('partial-footprint-coarse-area-drift')
            if previous_total <= 0 or previous_area / previous_total > 1.000001:
                old_invalid += 1
        if reasons:
            flagged.append((i, reasons, relative))
    return flagged, old_invalid


flagged = []
old_invalid = 0
done = 0
with multiprocessing.get_context('fork').Pool(3, initializer=initialize) as pool:
    for rows, invalid in pool.imap_unordered(risks, [(i, min(i+150, len(features))) for i in range(0, len(features), 150)]):
        flagged.extend(rows);old_invalid += invalid;done += 150
        if done % 3000 == 0:
            print(f'Numerical risk audit: {min(done,len(features))}/{len(features)}', flush=True)
flagged.sort()
selected = [i for i, _, _ in flagged]
tree = STRtree([locations[i] for i in selected])
connection = sqlite3.connect(cache)
existing = set()
for offset in range(0, len(selected), 500):
    batch = selected[offset:offset+500]
    existing.update(connection.execute('SELECT location,record FROM overlaps WHERE location IN (' + ','.join('?' for _ in batch) + ')', batch))
new = []
checked = 0
source_count = connection.execute('SELECT count(*) FROM source_geometry').fetchone()[0]
for j, raw in connection.execute('SELECT record,geometry FROM source_geometry ORDER BY record'):
    geometry = from_wkb(raw)
    prepare(geometry)
    updates = []
    for k in tree.query(geometry, predicate='intersects'):
        i = selected[int(k)]
        checked += 1
        if (i, j) in existing:
            continue
        full = geometry.covers(locations[i])
        clip = None if full else locations[i].intersection(geometry)
        share = 1.0 if full else area(clip) / totals[i]
        assert 0 <= share <= 1.00000001
        if share > 1e-8:
            updates.append((i, j, min(1, share), None if full else clip.wkb))
            new.append({'location_id': features[i]['id'], 'source_record_index': j, 'share': min(1, share)})
    if updates:
        connection.executemany('INSERT INTO overlaps VALUES(?,?,?,?)', updates)
        connection.commit()
    destroy_prepared(geometry)
    if j % 1000 == 0:
        print(f'Candidate recovery: {j+1}/{source_count} source geometries; {len(new)} recovered pairs', flush=True)
connection.close()
if cache != destination:
    cache.rename(destination)
report = {'method': 'Every numerically flagged location queried against every cached original source geometry; only previously absent positive intersections added. Footprints and existing intersections preserved.', 'algorithm_sha256': algorithm_hash, 'recovery_script_sha256': digest(pathlib.Path(__file__)), 'footprints_sha256': footprints, 'source_hashes': hashes, 'locations_audited': len(features), 'locations_requeried': len(selected), 'source_geometries': source_count, 'intersecting_pairs_checked': checked, 'recovered_pairs': len(new), 'reconstructed_old_invalid_share_rows': old_invalid, 'screening': {'tiny_land_area_m2': 1e6, 'whole_area_relative_drift': 1e-8, 'partial_area_relative_drift': 1e-6}, 'flagged_locations': [{'location_id': features[i]['id'], 'reasons': reasons, 'whole_area_relative_drift': drift} for i, reasons, drift in flagged], 'records': new}
receipt.write_text(json.dumps(report, separators=(',', ':')))
print(json.dumps({k: v for k, v in report.items() if k not in ('source_hashes','flagged_locations','records')}))
