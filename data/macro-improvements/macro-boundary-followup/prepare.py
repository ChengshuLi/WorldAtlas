#!/usr/bin/env python3
"""Reproduce the current-release applicability diagnosis; never change geography."""
import argparse
import collections
import gzip
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import linemerge, transform

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = pathlib.Path(__file__).resolve().parent
OLD = ROOT / 'data/macro-improvements/macro-boundary-reconciliation'
sys.path.insert(0, str(ROOT / 'scripts'))
from ellipsoidal_area import area


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def produce(archived_pins=None):
    pins = {}

    def pinned_raw(path):
        raw = path.read_bytes()
        expected = (archived_pins or {}).get(str(path.relative_to(ROOT)))
        if expected and sha(raw) != expected:
            index = json.loads(gzip.decompress((ROOT / 'data/macro-improvements/loose-ends-v5/publication/installation-source-proof-index.json.gz').read_bytes()))
            raw = subprocess.check_output(['git', 'show', f"{index['baseline_commit']}:{path.relative_to(ROOT)}"], cwd=ROOT)
        assert not expected or sha(raw) == expected, (str(path), 'Archived input hash differs')
        return raw

    def read(path):
        raw = pinned_raw(path)
        pins[str(path.relative_to(ROOT))] = sha(raw)
        return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)

    pins[str(pathlib.Path(__file__).resolve().relative_to(ROOT))] = sha(pinned_raw(pathlib.Path(__file__).resolve()))
    pins['scripts/ellipsoidal_area.py'] = sha(pinned_raw(ROOT / 'scripts/ellipsoidal_area.py'))
    reconciliation = read(OLD / 'reconciliation.json')
    archived = read(OLD / 'measurements.json.gz')
    snapshots = {row['location_id']: row for row in read(OLD / 'current-candidates.json.gz')}
    for key in ('measurement_archive', 'current_candidate_snapshot'):
        item = reconciliation[key]
        assert pins[item['path']] == item['sha256']
    certificate = read(ROOT / 'data/macro-foundation/macro-certificate.json')
    decisions = read(ROOT / 'data/macro-foundation/approved-boundary-decisions.json')
    hierarchy = {row['id']: row for row in read(ROOT / 'data/hierarchy.json')}
    release = certificate['release']
    assert certificate['status'] == 'approved' and release['version'] == 4
    assert release == decisions['release']
    assert release['hierarchy_sha256'] == pins['data/hierarchy.json']
    conventions = {row['id']: row for row in decisions['groups']}
    unresolved = {row['location_id']: row for row in archived['measurements']
                  if row['strict_majority_continent'] is None}
    assert len(unresolved) == 49
    current = {}
    for part in read(ROOT / 'data/world-index.json')['parts']:
        for feature in read(ROOT / 'data' / part)['features']:
            identity = feature['properties']['id']
            if identity in snapshots:
                assert identity not in current
                current[identity] = feature
    assert len(snapshots) == 570 and set(current) == set(snapshots)

    def current_chain(feature):
        chain, parent = {}, feature['properties']['parent_id']
        for tier in ('province', 'area', 'region', 'subcontinent', 'continent'):
            unit = hierarchy[parent]
            assert unit['level'] == tier
            chain[tier] = {'id': parent, 'name': unit['name']}
            parent = unit.get('parent_id')
        assert parent is None
        return chain

    for identity, feature in current.items():
        geometry_sha = sha(json.dumps(feature['geometry'], sort_keys=True, separators=(',', ':')).encode())
        assert geometry_sha == snapshots[identity]['geometry_sha256']
        assert current_chain(feature) == snapshots[identity]['current_chain']

    nodes, ways, relations = {}, {}, {}
    for source in reconciliation['sources']:
        filename = ROOT / source['archive_path']
        packed = filename.read_bytes()
        pins[source['archive_path']] = sha(packed)
        assert sha(packed) == source['archive_sha256']
        raw = gzip.decompress(packed)
        assert len(raw) == source['raw_bytes'] and sha(raw) == source['raw_sha256']
        document = ET.fromstring(raw)
        for node in document.findall('node'):
            identity = node.attrib['id']
            xy = (float(node.attrib['lon']), float(node.attrib['lat']))
            assert identity not in nodes or nodes[identity] == xy
            nodes[identity] = xy
        ways.update({way.attrib['id']: way for way in document.findall('way')})
        relations.update({relation.attrib['id']: relation for relation in document.findall('relation')})

    def coordinates(identity):
        return [nodes[node.attrib['ref']] for node in ways[identity].findall('nd')]

    river_ways = [member.attrib['ref'] for member in relations['214415'].findall('member')
                  if member.attrib['type'] == 'way' and member.attrib.get('role') == 'main_stream']
    assert len(river_ways) == 142
    ural = linemerge([LineString(coordinates(identity)) for identity in river_ways])
    assert ural.geom_type == 'LineString' and ural.is_simple
    upper, lower = coordinates('5038117'), coordinates('925360882')
    assert upper[-1] == lower[0]
    suez = LineString(upper + lower[1:])
    assert suez.is_simple
    assert ural.equals_exact(shape(archived['Ural']['line']), 0)
    assert suez.equals_exact(shape(archived['Suez']['line']), 0)

    contexts = {}
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
        projection = CRS.from_proj4(f'+proj=aeqd +lat_0={center[0]} +lon_0={center[1]} +datum=WGS84 +units=m')
        forward = Transformer.from_crs('EPSG:4326', projection, always_xy=True).transform
        inverse = Transformer.from_crs(projection, 'EPSG:4326', always_xy=True).transform
        corridor = transform(inverse, transform(forward, line).buffer(175, quad_segs=16 if label == 'Ural' else 32))
        contexts[label] = (line, continents, first, second, domain, corridor)

    cases = []
    for identity in sorted(unresolved):
        feature, snapshot, old = current[identity], snapshots[identity], unresolved[identity]
        geometry = feature['geometry']
        geometry_sha = sha(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode())
        assert geometry_sha == snapshot['geometry_sha256']
        chain = current_chain(feature)
        footprint = shape(geometry)
        assert footprint.is_valid and not footprint.is_empty
        assert footprint.bounds[2] - footprint.bounds[0] < 180
        line, continents, first, second, domain, corridor = contexts[snapshot['divide']]
        total = area(footprint)
        assert total > 0
        a, b, uncertainty, supported = [area(footprint.intersection(part)) / total
                                         for part in (first, second, corridor, domain)]
        for key, value in [('first_share', a), ('second_share', b), ('corridor_share', uncertainty)]:
            assert abs(old[key] - value) < 2e-9, (identity, key)
        assert abs(a + b - supported) < 2e-9
        guaranteed = (max(0, a - uncertainty), max(0, b - uncertainty))
        assert not any(value > .5 for value in guaranteed)
        intersects = footprint.intersects(line)
        north = area(footprint.intersection(box(-180, domain.bounds[3], 180, 90))) / total
        south = area(footprint.intersection(box(-180, -90, 180, domain.bounds[1]))) / total
        assert abs(supported + north + south - 1) < 2e-9
        convention_snapshots = []
        for tier in ('region', 'subcontinent', 'continent'):
            convention = conventions[chain[tier]['id']]
            assert convention['status'] == 'approved' and convention['level'] == tier
            assert convention['parent_id'] == hierarchy[convention['id']]['parent_id']
            convention_snapshots.append({key: convention[key] for key in ('id', 'name', 'convention', 'source_ids')})
        cases.append({
            'location_id': identity, 'name': feature['properties']['name'],
            'present_day_reference_owner': feature['properties'].get('reference_owner'),
            'source_identity_country_code': identity.split(':')[1] if identity.startswith('gb:') else None,
            'divide': snapshot['divide'], 'geometry_sha256': geometry_sha,
            'current_chain': chain, 'whole_footprint_area_m2': total,
            'intersects_supported_channel': intersects,
            'supported_domain_status': 'entirely-outside' if supported <= 1e-12 else 'partially-inside',
            'supported_domain_share': supported, 'north_of_domain_share': north,
            'south_of_domain_share': south,
            'measured_side_shares': {continents[0]: a, continents[1]: b},
            'corridor_share': uncertainty,
            'conservative_side_shares': dict(zip(continents, guaranteed)),
            'river_majority_result': 'unresolved',
            'diagnosis': 'actual-crossing-unresolved-by-river' if intersects else 'measure-domain-limited-not-physical-confirmation',
            'accepted_reporting_conventions': convention_snapshots,
            'reporting_membership_verified_against_current_certificate': True,
            'independent_physical_assignment_confirmed': False,
            'footprint_land_mask_verified': False,
            'assignment_changed': False,
        })
    summary = {
        'original_candidate_ids_geometries_and_chains_verified_current': len(current),
        'cases': len(cases),
        'actual_channel_intersections': sum(row['intersects_supported_channel'] for row in cases),
        'nonintersections': sum(not row['intersects_supported_channel'] for row in cases),
        'zero_corridor_coverage': sum(row['corridor_share'] == 0 for row in cases),
        'domain_status': dict(collections.Counter(row['supported_domain_status'] for row in cases)),
        'divide': dict(collections.Counter(row['divide'] for row in cases)),
        'region': dict(collections.Counter(row['current_chain']['region']['name'] for row in cases)),
        'present_day_reference_owner': dict(collections.Counter(row['present_day_reference_owner'] for row in cases)),
        'source_identity_country_code': dict(collections.Counter(row['source_identity_country_code'] or 'derived-identity' for row in cases)),
    }
    assert summary['actual_channel_intersections'] == 1 and summary['nonintersections'] == 48
    assert summary['zero_corridor_coverage'] == 48
    assert summary['domain_status'] == {'partially-inside': 47, 'entirely-outside': 2}
    return {
        'version': 1, 'issue': 538, 'recorded_date_utc': '2026-10-03',
        'recorded_date_pacific': '2026-10-02', 'date_timezone': 'America/Los_Angeles',
        'scope': 'Current-release applicability diagnosis of all 49 archived unresolved river measurements',
        'current_release': release, 'input_sha256': dict(sorted(pins.items())),
        'method': 'Exact archived OSM XML joins; WGS84 whole source-footprint area, holes excluded; supported sides clipped to channel endpoint latitude band; 175m local AEQD corridor subtracted without shrinking denominator.',
        'interpretation': 'Partial source-domain coverage is not proof of an uncertain continental boundary. Nonintersection is not independent proof of continental assignment. Retained membership follows the separately documented approved reporting convention, not a manufactured river majority.',
        'certified_scope': 'Unchanged 49 IDs/geometries/chains match the current approved convention; source-based domain and intersection measurements replay exactly.',
        'physical_precision_certified': False, 'geography_changed': False,
        'worldwide_shoreline_completeness_certified': False, 'regional_interiors_approved': False,
        'summary': summary, 'cases': cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Recompute and require byte-identical saved report')
    args = parser.parse_args()
    destination = OWN / 'domain-diagnosis.json.gz'
    old_report = json.loads(gzip.decompress(destination.read_bytes())) if args.check else None
    report = produce(old_report['input_sha256'] if old_report else None)
    raw = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()
    output = io.BytesIO()
    with gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=0) as stream:
        stream.write(raw)
    packed = output.getvalue()
    if args.check:
        assert destination.read_bytes() == packed, 'Saved diagnosis does not match current pinned inputs'
    else:
        destination.write_bytes(packed)
    # Current publication context is checked separately from the archived v4 result.
    certificate_raw = (ROOT / 'data/macro-foundation/macro-certificate.json').read_bytes()
    current = json.loads(certificate_raw)
    current_hierarchy = sha((ROOT / 'data/hierarchy.json').read_bytes())
    assert current_hierarchy == current['release']['hierarchy_sha256']
    if current['release'] != report['current_release']:
        receipt_raw = gzip.decompress((ROOT / 'data/macro-improvements/loose-ends-v5/publication/aggregate-source-receipt.json.gz').read_bytes())
        receipt = json.loads(receipt_raw)
        installed = json.loads((ROOT / 'data/publication-geography-receipt.json').read_bytes())
        assert sha(receipt_raw) == installed['sources']['sourceReceipt']['sha256']
        assert receipt['before_footprints_sha256'] == report['current_release']['footprints_sha256']
        assert receipt['after_footprints_sha256'] == installed['after_footprints_sha256'] == current['release']['footprints_sha256']
        candidates = {row['location_id'] for row in json.loads(gzip.decompress((OLD / 'current-candidates.json.gz').read_bytes()))}
        assert receipt['historical_claims_transferred'] is False and not receipt['removed_ids']
        assert not candidates.intersection(receipt['changed_ids'] + receipt['added_ids'])
    context = {'release': current['release'], 'status': current['status'],
               'certificate_sha256': sha(certificate_raw), 'hierarchy_sha256': current_hierarchy,
               'world_index_sha256': sha((ROOT / 'data/world-index.json').read_bytes())}
    print(json.dumps({'checked': args.check, 'archived_report_release': report['current_release'],
                      'current_context': context, 'report_sha256': sha(packed), **report['summary']}))


if __name__ == '__main__':
    main()
