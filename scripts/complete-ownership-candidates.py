"""Confirm candidate completeness for locations outside the numerical risk set."""
import hashlib
import json
import pathlib
import sqlite3
from shapely import STRtree, from_wkb, prepare, destroy_prepared
from shapely.geometry import shape
from majority import canonical, area

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = DATA / 'ownership-history'
read = lambda p: json.loads(p.read_text())
receipt = OUT / 'candidate-recovery.json'
report = read(receipt)
if report.get('locations_confirmed') == report['locations_audited']:
    print('All ownership location/source candidates have been confirmed')
    raise SystemExit
excluded = {r['location_id'] for r in report['flagged_locations']}
world = read(DATA / 'world-index.json')
ids = []
geometries = {}
for p in world['parts']:
    for f in read(DATA / p)['features']:
        ids.append(f['id'])
        if f['id'] not in excluded:
            geometries[f['id']] = canonical(shape(f['geometry']))
indices = {id: n for n, id in enumerate(sorted(ids))}
locations = sorted(geometries)
totals = {id: area(g) for id, g in geometries.items()}
tree = STRtree([geometries[id] for id in locations])
paths = list((ROOT / '.cache/ownership-overlaps').glob('*.sqlite'))
assert len(paths) == 1
connection = sqlite3.connect(paths[0])
selected = [indices[id] for id in locations]
existing = set(connection.execute('SELECT location,record FROM overlaps WHERE location IN (' + ','.join('?' for _ in selected) + ')', selected))
checked = 0
new = []
for j, raw in connection.execute('SELECT record,geometry FROM source_geometry ORDER BY record'):
    g = from_wkb(raw)
    prepare(g)
    updates = []
    for k in tree.query(g, predicate='intersects'):
        id = locations[int(k)]
        i = indices[id]
        checked += 1
        if (i, j) in existing:
            continue
        full = g.covers(geometries[id])
        clip = None if full else geometries[id].intersection(g)
        share = 1.0 if full else area(clip) / totals[id]
        assert 0 <= share <= 1.00000001
        if share > 1e-8:
            updates.append((i, j, min(1, share), None if full else clip.wkb))
            new.append({'location_id': id, 'source_record_index': j, 'share': min(1, share)})
    if updates:
        connection.executemany('INSERT INTO overlaps VALUES(?,?,?,?)', updates)
        connection.commit()
    destroy_prepared(g)
connection.close()
report.update(locations_confirmed=report['locations_requeried']+len(locations), normal_locations_confirmed=len(locations), confirmation_script_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
report['intersecting_pairs_checked'] += checked
report['recovered_pairs'] += len(new)
report['records'] += new
report['method'] = 'Every location queried against all original source geometries using STRtree; all positive-area candidates confirmed with the precise WGS84 surface integral. Original and newly recovered intersections distinguished; location footprints unchanged.'
receipt.write_text(json.dumps(report, separators=(',', ':')))
print(json.dumps({'locations_confirmed': report['locations_confirmed'], 'additional_normal_locations': len(locations), 'additional_intersecting_pairs': checked, 'recovered_pairs': report['recovered_pairs']}))
