"""Recompute every cached overlap area without changing source intersections."""
import hashlib
import json
import multiprocessing
import pathlib
import sqlite3
import subprocess

from shapely import from_wkb
from shapely.geometry import shape
from majority import canonical, area

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DIR = ROOT / '.cache/ownership-overlaps'


def read(file):
    return json.loads(file.read_text())


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def geometry_hash(connection):
    result = hashlib.sha256()
    for i, j, geometry in connection.execute('SELECT location,record,geometry FROM overlaps ORDER BY location,record'):
        result.update(f'{i}:{j}:'.encode())
        result.update(geometry if geometry is not None else b'FULL')
        result.update(b'\n')
    return result.hexdigest()


old_index = read(DATA / 'ownership-history/index.json')
source_hashes = {p: h for p, h in old_index['inputs'].items() if p.startswith('cliopatria/')}
for path, expected in source_hashes.items():
    assert digest(DATA / path) == expected, f'Historical source changed: {path}'
footprints = subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip()
assert footprints == old_index['footprints_sha256']
algorithm_hash = ''.join(digest(ROOT / 'scripts' / p) for p in ['majority.py', 'prepare-ownership.py', 'ellipsoidal_area.py'])
key = hashlib.sha256((footprints + ''.join(source_hashes[p] for p in sorted(source_hashes)) + algorithm_hash).encode()).hexdigest()
files = list(DIR.glob('*.sqlite'))
assert len(files) == 1, 'Expected one validated overlap cache'
old_cache = files[0]
new_cache = DIR / f'{key}.sqlite'
receipt = DIR / 'exact-area-migration.json'
if receipt.exists() and read(receipt).get('to') == new_cache.name and old_cache == new_cache:
    print('Exact cached overlap areas are current')
    raise SystemExit
connection = sqlite3.connect(old_cache)
source_index = read(DATA / 'cliopatria/index.json')
assert connection.execute('SELECT last_record FROM progress WHERE singleton=1').fetchone()[0] == len(source_index['records']) - 1
source_geometry_hash = hashlib.sha256()
for n, geometry in connection.execute('SELECT record,geometry FROM source_geometry ORDER BY record'):
    source_geometry_hash.update(str(n).encode());source_geometry_hash.update(geometry)
before = geometry_hash(connection)
world = read(DATA / 'world-index.json')
features = sorted([f for p in world['parts'] for f in read(DATA / p)['features']], key=lambda f: f['id'])
locations = [canonical(shape(f['geometry'])) for f in features]
totals = [area(g) for g in locations]
assert all(t > 0 for t in totals), 'A location has no supported ellipsoidal land area'


def initialize():
    global lookup
    lookup = sqlite3.connect('file:' + str(old_cache) + '?mode=ro', uri=True)


def measure(task):
    start, end = task
    updates = []
    maximum_share_delta = 0.0
    maximum_area_drift = 0.0
    for i in range(start, end):
        interned = {}
        for j, previous, raw in lookup.execute('SELECT record,share,geometry FROM overlaps WHERE location=? ORDER BY record', (i,)):
            if raw is None:
                value = 1.0
            else:
                if raw not in interned:
                    interned[raw] = area(from_wkb(raw)) / totals[i]
                value = interned[raw]
            maximum_share_delta = max(maximum_share_delta, abs(value - previous))
            if value:
                maximum_area_drift = max(maximum_area_drift, abs(previous / value - 1))
            updates.append((value, i, j))
    return updates, maximum_share_delta, maximum_area_drift, end - start


connection.commit()
done = 0
measured = 0
share_delta = 0
drift = 0
with multiprocessing.get_context('fork').Pool(3, initializer=initialize) as pool:
    for updates, maximum_share_delta, maximum_area_drift, size in pool.imap_unordered(measure, [(i, min(i+150, len(features))) for i in range(0, len(features), 150)]):
        connection.executemany('UPDATE overlaps SET share=? WHERE location=? AND record=?', updates)
        connection.commit()
        done += size;measured += len(updates)
        share_delta = max(share_delta, maximum_share_delta);drift = max(drift, maximum_area_drift)
        if done % 3000 == 0 or done == len(features):
            print(f'Exact cached areas: {done}/{len(features)} locations', flush=True)
after = geometry_hash(connection)
assert before == after, 'Cached geographic intersections changed during area recomputation'
connection.close()
old_cache.rename(new_cache)
report = {'from': old_cache.name, 'to': new_cache.name, 'footprints_sha256': footprints, 'source_hashes': source_hashes, 'source_geometry_sha256': source_geometry_hash.hexdigest(), 'overlap_geometry_sha256': after, 'algorithm_sha256': algorithm_hash, 'locations': len(features), 'overlaps_remeasured': measured, 'maximum_share_delta': share_delta, 'maximum_relative_area_drift': drift, 'method': 'Every cached source intersection remeasured using the WGS84 latitude-strip surface integral; no geographic intersections changed'}
receipt.write_text(json.dumps(report, separators=(',', ':')))
print(json.dumps({k: v for k, v in report.items() if k != 'source_hashes'}))
