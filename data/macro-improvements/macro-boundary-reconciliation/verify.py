#!/usr/bin/env python3
"""Read-only exhaustive replay of the independently sourced macro measurement ledger."""
import collections
import gzip
import hashlib
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import linemerge, transform

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from ellipsoidal_area import area


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def pinned_bytes(path, expected, release):
    """Replay original bytes, never substitute a new release for a pinned input."""
    original = ROOT / path
    if original.is_file() and digest(original.read_bytes()) == expected:
        return original.read_bytes()
    if path in ('data/hierarchy.json', 'data/world-index.json'):
        archived = (ROOT / 'data/macro-foundation/predecessor-inspections' /
                    release['hierarchy_sha256'] / (pathlib.Path(path).name + '.gz'))
    elif path.startswith('data/macro-foundation/'):
        archived = (ROOT / 'data/reference-migrations/macro-improvements-v4/prior-macro' /
                    (str(pathlib.Path(path).relative_to('data')) + '.archive.gz'))
    else:
        raise AssertionError(f'Changed pinned input without preserved archive: {path}')
    raw = gzip.decompress(archived.read_bytes())
    assert digest(raw) == expected, (path, 'archived input hash')
    return raw


def main():
    report = read(OWN / 'reconciliation.json')
    pinned = {}
    for path, expected in report['immutable_input_pins'].items():
        pinned[path] = pinned_bytes(path, expected, report['geographic_release'])
    for entry in ('measurement_archive', 'current_candidate_snapshot', 'larger_corridor_sensitivity'):
        item = report[entry]
        assert digest((ROOT / item['path']).read_bytes()) == item['sha256'], entry
    nodes, ways, relations = {}, {}, {}
    for source in report['sources']:
        archive = (ROOT / source['archive_path']).read_bytes()
        assert digest(archive) == source['archive_sha256']
        raw = gzip.decompress(archive)
        assert len(raw) == source['raw_bytes'] and digest(raw) == source['raw_sha256']
        parsed = ET.fromstring(raw)
        nodes.update({n.attrib['id']: (float(n.attrib['lon']), float(n.attrib['lat']))
                      for n in parsed.findall('node')})
        ways.update({w.attrib['id']: w for w in parsed.findall('way')})
        relations.update({r.attrib['id']: r for r in parsed.findall('relation')})
    relation = relations['214415']
    tagged_main = [m.attrib['ref'] for m in relation.findall('member')
                   if m.attrib['type'] == 'way' and m.attrib['role'] == 'main_stream']
    assert len(tagged_main) == 142

    def coordinates(identity):
        return [nodes[n.attrib['ref']] for n in ways[identity].findall('nd')]

    ural = linemerge([LineString(coordinates(i)) for i in tagged_main])
    assert ural.geom_type == 'LineString' and ural.is_simple
    upper, lower = coordinates('5038117'), coordinates('925360882')
    assert upper[-1] == lower[0], 'Suez source join'
    suez = LineString(upper + lower[1:])
    assert suez.is_simple
    rows = read(OWN / 'current-candidates.json.gz')
    measured = read(OWN / 'measurements.json.gz')
    sensitivity = read(OWN / 'sensitivity.json.gz')
    measured_by_id = {x['location_id']: x for x in measured['measurements']}
    old = read(ROOT / 'data/macro-boundary-decisions.json')
    old_rows = {x['location_id']: x for x in old['whole_location_measurements']}
    old_unknown = {x['location_id'] for x in old['unresolved_location_measurements']}
    hierarchy = {x['id']: x for x in read(ROOT / 'data/hierarchy.json')}
    assert len(rows) == len(old_rows) == 570
    assert {x['location_id'] for x in rows} == set(old_rows)
    snapshots = {x['location_id']: x for x in rows}
    approved = json.loads(pinned['data/macro-foundation/approved-boundary-decisions.json'])
    routes = [x for x in approved['named_land_routing'] if 'aegean-islands' in x.get('source_ids', [])]
    route_targets = {identity: x['region_id'] for x in routes for identity in x['existing_location_ids']}
    assert len(routes) == 19 and len(route_targets) == 19
    assert report['physical_segment_dispositions'][3]['named_routing_crosswalk'] == routes
    current, islands = {}, {}
    for path in read(ROOT / 'data/world-index.json')['parts']:
        for feature in read(ROOT / 'data' / path)['features']:
            if feature['properties']['id'] in route_targets:
                islands[feature['properties']['id']] = feature
            if feature['properties']['id'] in snapshots:
                current[feature['properties']['id']] = feature
    assert set(current) == set(snapshots)
    assert set(islands) == set(route_targets)
    for identity, feature in islands.items():
        parent = feature['properties']['parent_id']
        while hierarchy[parent]['level'] != 'region':
            parent = hierarchy[parent]['parent_id']
        assert parent == route_targets[identity], (identity, 'island routing')
    for identity, row in snapshots.items():
        feature = current[identity]
        footprint_hash = digest(json.dumps(feature['geometry'], sort_keys=True,
                                          separators=(',', ':')).encode())
        assert footprint_hash == row['geometry_sha256'] == old_rows[identity]['geometry_sha256']
        chain, parent = {}, feature['properties']['parent_id']
        while parent in hierarchy:
            unit = hierarchy[parent]
            chain[unit['level']] = {'id': parent, 'name': unit['name']}
            parent = unit.get('parent_id')
        assert chain == row['current_chain']
    count, resolved_old, opposite = collections.Counter(), 0, 0
    for label, line, continents, center in (
        ('Ural', ural, ('Europe', 'Asia'), (50.7, 55.4)),
        ('Suez Canal', suez, ('Africa', 'Asia'), (30.6, 32.4)),
    ):
        cs = list(line.coords)
        if cs[0][1] < cs[-1][1]:
            cs.reverse()
        first = Polygon(cs + [(-180, cs[-1][1]), (-180, cs[0][1]), cs[0]])
        assert first.is_valid
        domain = box(-180, cs[-1][1], 180, cs[0][1])
        second = domain.difference(first)
        proj = CRS.from_proj4(f'+proj=aeqd +lat_0={center[0]} +lon_0={center[1]} +datum=WGS84 +units=m')
        forward = Transformer.from_crs('EPSG:4326', proj, always_xy=True).transform
        inverse = Transformer.from_crs(proj, 'EPSG:4326', always_xy=True).transform
        band = transform(inverse, transform(forward, line).buffer(175, quad_segs=16 if label == 'Ural' else 32))
        for result in measured['measurements']:
            row = snapshots[result['location_id']]
            if row['divide'] != label:
                continue
            footprint = shape(row['geometry'])
            assert footprint.bounds[2] - footprint.bounds[0] < 180
            total = area(footprint)
            shares = [area(footprint.intersection(g)) / total for g in (first, second, band)]
            for field, value in zip(('first_share', 'second_share', 'corridor_share'), shares):
                assert abs(result[field] - value) < 2e-9, (result['location_id'], field)
            a, b = max(0, shares[0] - shares[2]), max(0, shares[1] - shares[2])
            winner = continents[0] if a > .5 and b <= .5 else continents[1] if b > .5 and a <= .5 else None
            assert winner == result['strict_majority_continent']
            count[winner or 'insufficient-river-reach'] += 1
            opposite += int(winner is not None and winner != row['current_chain']['continent']['name'])
            resolved_old += int(winner is not None and result['location_id'] in old_unknown)
        for extra in sensitivity['results']:
            if extra['divide'] != ('Ural' if label == 'Ural' else 'Suez'):
                continue
            meters = extra['corridor_meters']
            widened = transform(inverse, transform(forward, line).buffer(meters, quad_segs=16 if label == 'Ural' else 32))
            assert meters in (500, 1000)
            widened_count = collections.Counter()
            for row in extra['measurements']:
                identity = row['location_id']
                source_result = measured_by_id[identity]
                footprint = shape(snapshots[identity]['geometry'])
                corridor = area(footprint.intersection(widened)) / area(footprint)
                assert abs(row['corridor_share'] - corridor) < 2e-9
                a = max(0, source_result['first_share'] - corridor)
                b = max(0, source_result['second_share'] - corridor)
                winner = continents[0] if a > .5 and b <= .5 else continents[1] if b > .5 and a <= .5 else None
                assert winner == row['conditional_majority']
                assert winner is None or winner == snapshots[identity]['current_chain']['continent']['name']
                widened_count[winner or 'insufficient'] += 1
            assert dict(widened_count) == extra['summary']
    assert sum(count.values()) == 570 and count['insufficient-river-reach'] == 49
    assert opposite == 0 and resolved_old == 29
    assert len(report['original_uncertain_location_dispositions']) == 78
    assert len(report['physical_segment_dispositions']) == 4
    print(json.dumps({'verified': True, 'candidates': 570, 'conditional_majorities': 521,
                      'opposite_assignments': opposite, 'old_uncertainties_now_confirmed': resolved_old,
                      'remaining_physical_reach_insufficient': 49}))


if __name__ == '__main__':
    main()
