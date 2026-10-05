"""Retain exact self-crossing diagnostics; never reinterpret as physical area."""
exec(open('.cache/shared-edge-991/exact-world-case.py').read().split('arrangement=arrange')[0])
from exact_arrangement import crossings
from shapely.strtree import STRtree
from shapely.validation import explain_validity
findings = []
for owner, g in all_before.items():
    raw = mapping(g)
    polygons = [raw['coordinates']] if raw['type'] == 'Polygon' else raw['coordinates']
    owner_records = []
    for polygon_n, polygon in enumerate(polygons):
        for ring_n, ring in enumerate(polygon):
            exact = [point(p) for p in ring[:-1]]
            edges = list(zip(exact, exact[1:] + exact[:1]))
            lines = [LineString([[float(v) for v in a], [float(v) for v in b]]) for a, b in edges]
            tree = STRtree(lines)
            for n, edge in enumerate(edges):
                for other in tree.query(lines[n]):
                    k = int(other)
                    if k <= n or k == n + 1 or (n == 0 and k == len(edges) - 1):
                        continue
                    points = crossings(*edge, *edges[k])
                    if not points:
                        continue
                    proper = [p for p in points if p not in edge and p not in edges[k]]
                    owner_records.append({'polygon': polygon_n, 'ring': ring_n,
                                          'edge_indices': [n, k], 'proper_crossing': bool(proper),
                                          'intersection_points': [[str(x), str(y)] for x, y in points]})
    findings.append({'owner': owner, 'geos_valid': g.is_valid,
                     'geos_validity_reason': explain_validity(g), 'exact_ring_findings': owner_records})
result = {'experimental': True, 'subjects': findings,
          'limits': ['Original-ring self-intersection diagnostic only; inter-ring intersections, spherical topology and source authority are not assessed.',
                     'Rational diagnostics do not measure physical errors and must not justify filling or editing geography.']}
payload = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
pathlib.Path('.cache/shared-edge-991/exact-baseline-validity-v1.json').write_bytes(payload)
import hashlib
print(json.dumps({'sha256': hashlib.sha256(payload).hexdigest(),
                  'subjects': [{'owner': r['owner'], 'geos_valid': r['geos_valid'],
                                'exact_ring_findings': len(r['exact_ring_findings']),
                                'proper_crossings': sum(f['proper_crossing'] for f in r['exact_ring_findings'])}
                               for r in findings]}))
