"""Check complete original identity/uncertainty accounting and whole-file custody.

This validates recorded numerical evidence, not geography or source authority.
An independent actual rerun is required for substantive scientific review.
"""
import argparse
from collections import defaultdict
import gzip
import json
import pathlib

from evidence.immutable import Baseline, canonical_json, descriptor, sha256, safe_path
from physical_component_custody import validate, describe, ordinary_read, OWNED
from physical_gap_crosswalk import membership, VERSION
from physical_component_contacts import component_contacts
from geographic_components import components
import shapely
from shapely.geometry import mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_REPO = ROOT
INDEX = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
OLD = 'coordination/engineering/coverage-gaps-907-20261005-local01/global-v3/report.json'
OLD_COMPONENTS = 'coordination/engineering/geographic-components-946-20261005-local06/components-v2/report.json'
NEW = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def structural_geometry(geometry):
    """Canonicalize representation order only; retain every coordinate token.

    This does not use point-set equality, overlay, rounding or GEOS repair.
    Type, dimensions, duplicate members/vertices and extra fields stay exact.
    """
    def ordered(values):
        return sorted(values, key=canonical_json)

    def line(points):
        return min([points, list(reversed(points))], key=canonical_json)

    def rotation(points):
        # Booth's linear-time minimal cyclic rotation on exact coordinate keys.
        if not points:
            return points
        keys = [canonical_json(p) for p in points]
        n, i, j, offset = len(keys), 0, 1, 0
        while i < n and j < n and offset < n:
            a, b = keys[(i + offset) % n], keys[(j + offset) % n]
            if a == b:
                offset += 1
                continue
            if a > b:
                i += offset + 1
                if i == j:
                    i += 1
            else:
                j += offset + 1
                if i == j:
                    j += 1
            offset = 0
        start = min(i, j)
        return points[start:] + points[:start]

    def ring(points):
        if not points:
            return points
        require(len(points) >= 4, 'Reconstructed nonempty ring has too few vertices')
        require(canonical_json(points[0]) == canonical_json(points[-1]),
                'Reconstructed ring lost exact closure')
        # Remove only the mandatory closing copy, never repeated vertices.
        cycle = points[:-1]
        result = min([rotation(cycle), rotation(list(reversed(cycle)))], key=canonical_json)
        return result + result[:1]

    def polygon(rings):
        return [ring(rings[0])] + ordered([ring(r) for r in rings[1:]]) if rings else []

    result = dict(geometry)
    kind = geometry['type']
    if kind == 'GeometryCollection':
        result['geometries'] = ordered([structural_geometry(g) for g in geometry['geometries']])
        return result
    points = geometry['coordinates']
    operations = {'Point': lambda x: x, 'MultiPoint': ordered,
                  'LineString': line, 'MultiLineString': lambda x: ordered([line(p) for p in x]),
                  'Polygon': polygon, 'MultiPolygon': lambda x: ordered([polygon(p) for p in x])}
    require(kind in operations, 'Unsupported reconstructed geometry type')
    result['coordinates'] = operations[kind](points)
    return result


def same_structural_row(a, b):
    if canonical_json(a) == canonical_json(b):
        return True
    if 'geometry' not in a or 'geometry' not in b:
        return False
    metadata_a = {k: v for k, v in a.items() if k != 'geometry'}
    metadata_b = {k: v for k, v in b.items() if k != 'geometry'}
    return (canonical_json(metadata_a) == canonical_json(metadata_b) and
            canonical_json(structural_geometry(a['geometry'])) ==
            canonical_json(structural_geometry(b['geometry'])))


def require_exact_reconstruction(original, rebuilt, message):
    require(len(original) == len(rebuilt), message + ': different complete row count')
    for number, (a, b) in enumerate(zip(original, rebuilt)):
        if same_structural_row(a, b):
            continue
        diagnostic = {'row': number, 'software': {'shapely': shapely.__version__,
                      'geos': shapely.geos_version_string},
                      'original': a, 'rebuilt': b,
                      'metadata_equal': canonical_json({k: v for k, v in a.items() if k != 'geometry'}) ==
                                        canonical_json({k: v for k, v in b.items() if k != 'geometry'})}
        if 'geometry' in a and 'geometry' in b:
            ga, gb = shape(a['geometry']), shape(b['geometry'])
            diagnostic.update(exact_point_sets_equal=ga.equals(gb),
                              normalized_coordinate_bytes_equal=canonical_json(mapping(ga.normalize())) ==
                                                                canonical_json(mapping(gb.normalize())),
                              original_area=ga.area, rebuilt_area=gb.area)
        raise ValueError(message + ': ' + canonical_json(diagnostic).decode()[:16000])


def validate_science(index_path=INDEX):
    index = json.loads(ordinary_read(ROOT, index_path))
    require({g['prefix'] for g in index['generations']} == {OWNED + 'components-v' + str(i) for i in (1, 2, 3)}, 'Original execution vintage roster differs')
    result = validate(ROOT, index)
    aliases = {a['original']['path']: a for a in index['aliases']}

    def original(path):
        return ordinary_read(ROOT, aliases[path]['payload'])

    complete = [g for g in index['generations'] if g['status'] == 'complete']
    report_path = complete[0]['prefix'] + '/report.json'
    report_raw = original(report_path)
    require(describe(report_path, report_raw) == aliases[report_path]['original'],
            'Whole original scientific report changed')
    report = json.loads(report_raw)
    require(report['version'] == VERSION, 'Unexpected full scientific report')
    pins = {r['path']: r for r in report['inputs']}
    require(len(pins) == len(report['inputs']), 'Duplicate original input')
    consumed = set()
    baseline = Baseline(SOURCE_REPO, report['input_commit'], report['inputs'])

    def read(path):
        safe_path(path)
        require(path in pins, 'Unpinned whole original input')
        raw = ordinary_read(ROOT, path)
        require(descriptor(path, raw) == pins[path], 'Complete original input changed')
        require(raw == baseline.read(path), 'Whole original differs from immutable science commit')
        consumed.add(path)
        return raw

    def bundle(entry, transported=False):
        raw = original(entry['path']) if transported else read(entry['path'])
        require(describe(entry['path'], raw) == entry, 'Whole decoded scientific bundle changed')
        return json.loads(gzip.decompress(raw))

    def features(entries, transported=False):
        out = []
        for entry in entries:
            body = bundle(entry, transported)
            if isinstance(body, dict):
                require(body.get('type') == 'FeatureCollection', 'Full FeatureCollection required')
                out.extend(body['features'])
            else:
                require(isinstance(body, list), 'Full row bundle required')
                out.extend(body)
        return out

    old_report, component_report, new_report = [json.loads(read(p)) for p in (OLD, OLD_COMPONENTS, NEW)]
    old, new = features(old_report['outputs']), features(new_report['outputs'])
    remnants = features(new_report['residue_outputs'])
    old_records = []
    for entry in component_report['outputs']:
        body = bundle(entry)
        if isinstance(body, dict) and body.get('type') == 'FeatureCollection':
            old_records.extend(body['features'])
    require(consumed == set(pins), 'Full original scientific input roster differs')
    require(old_report['bounds'] == new_report['bounds'] == component_report['bounds'] == report['bounds'], 'Original domains differ')
    native = {r['path']: r for r in new_report['inputs']}
    require(all(native.get(r['path']) == r for r in old_report['inputs']), 'Original native science inputs differ')
    require(set(report['outputs']) == {'new_components', 'new_contacts', 'fragment_pairs', 'old_fragments',
                                     'new_fragments', 'component_links', 'components'}, 'Incomplete output families')
    rows = {k: features(v, True) for k, v in report['outputs'].items()}
    new_records = rows['new_components']
    old_members, new_members = membership(old, old_records), membership(new, new_records)
    require(set(r['id'] for r in old_records).isdisjoint(r['id'] for r in new_records), 'Old/new component identities collide')
    require(all(r['id'].startswith('physical-component:') for r in new_records), 'Missing distinct physical namespace')
    for name, value in [('old_fragments', len(old)), ('new_fragments', len(new)), ('old_components', len(old_records)),
                        ('new_components', len(new_records)), ('fragment_pairs', len(rows['fragment_pairs'])),
                        ('component_links', len(rows['component_links'])), ('new_remnants_preserved_in_original_bundles', len(remnants))]:
        require(report[name] == value, 'Complete reported count differs: ' + name)
    require(len(old) == old_report['candidate_fragments'] and len(new) == new_report['candidate_fragments']
            and len(old_records) == component_report['component_count'] and len(remnants) == new_report['residues'], 'Original full product count differs')
    old_by = {f['id']: f for f in old}
    new_by = {f['id']: f for f in new}
    pair_refs = {'old': defaultdict(list), 'new': defaultdict(list)}
    link_refs = defaultdict(list)
    identities = set()
    for number, pair in enumerate(rows['fragment_pairs']):
        a, b = pair['old_fragment'], pair['new_fragment']
        require(a in old_members and b in new_members, 'Pair refers to absent original fragment')
        require(pair['old_component'] == old_members[a] and pair['new_component'] == new_members[b], 'Pair membership differs')
        key = (a, b, pair['new_shift_degrees'])
        require(key not in identities, 'Duplicate exact fragment pair')
        identities.add(key)
        require(pair['new_shift_degrees'] in (-360, 0, 360) and pair['dateline'] == (pair['new_shift_degrees'] != 0), 'Invalid original comparison shift')
        require(pair['status'] in ('checked', 'unknown-original-operation-failed'), 'Unknown comparison status')
        if pair['status'] == 'checked':
            require(pair['kind'] in ('identical-coordinates', 'equal-point-set', 'positive-area-overlap', 'positive-length-contact', 'point-only-contact'), 'Invalid checked comparison kind')
            require('original_intersection' in pair and pair['intersection_planar_area'] >= 0, 'Original intersection missing')
            if pair['kind'] == 'positive-area-overlap':
                require(pair['intersection_planar_area'] > 0, 'Positive area erased')
        else:
            require(pair['kind'] == 'unknown-overlay' and pair.get('error'), 'Overlay uncertainty erased')
        pair_refs['old'][a].append(number)
        pair_refs['new'][b].append(number)
        link_refs[(old_members[a], new_members[b])].append(number)
    differences = []
    for side, original_features, members in [('old', old_by, old_members), ('new', new_by, new_members)]:
        ledgers = rows[side + '_fragments']
        require(len(ledgers) == len(original_features) and {r['fragment'] for r in ledgers} == set(original_features), 'Missing/duplicate original fragment accounting')
        unknowns = sorted(k for k, f in original_features.items() if f['properties'].get('area_m2') is None)
        require(unknowns == report['unmeasured_original_ids' if side == 'old' else 'unmeasured_new_ids'], 'Original unmeasured IDs changed')
        for row in ledgers:
            f = original_features[row['fragment']]
            require(row['side'] == side and row['component'] == members[f['id']], 'Fragment accounting membership changed')
            require(row['feature_sha256'] == sha256(canonical_json(f)) and row['geometry_sha256'] == sha256(canonical_json(f['geometry'])), 'Whole original shape binding changed')
            area = f['properties'].get('area_m2')
            require(row['original_area_m2'] == area and row['unmeasured_original'] == (area is None), 'Original measurement uncertainty changed')
            require(row['pair_numbers'] == pair_refs[side][f['id']], 'Fragment pair ledger incomplete')
            d = row['difference']
            require(d['status'] in ('checked', 'unknown-original-operation-failed', 'unknown-related-overlay-failed'), 'Invalid difference status')
            if d['status'] == 'checked':
                require(isinstance(d['atoms'], list) and d['remaining_planar_area'] >= 0, 'Original residual atoms missing')
            else:
                differences.append({'fragment': row['fragment'], 'side': side, 'difference': d})
    links = rows['component_links']
    require(len(links) == len(link_refs), 'Incomplete component relationships')
    component_refs = {'old': defaultdict(list), 'new': defaultdict(list)}
    seen_links = set()
    for number, row in enumerate(links):
        key = (row['old_component'], row['new_component'])
        require(key not in seen_links and row['pair_numbers'] == link_refs.get(key), 'Component relationship omitted/duplicated')
        seen_links.add(key)
        require(row['kinds'] == sorted({rows['fragment_pairs'][i]['kind'] for i in row['pair_numbers']}), 'Contact kinds conflated')
        component_refs['old'][key[0]].append(number)
        component_refs['new'][key[1]].append(number)
    records = {'old': {r['id']: r for r in old_records}, 'new': {r['id']: r for r in new_records}}
    seen = set()
    for row in rows['components']:
        key = (row['side'], row['component'])
        require(key not in seen and row['component'] in records.get(row['side'], {}), 'Duplicate/unknown complete component accounting')
        seen.add(key)
        record = records[row['side']][row['component']]
        require(row['original_feature_sha256'] == sha256(canonical_json(record)), 'Whole component binding changed')
        require(row['fragment_ids'] == [b['id'] for b in record['properties']['fragment_bindings']], 'Complete component fragments omitted')
        require(row['unmeasured_fragment_ids'] == record['properties']['unmeasured_fragment_ids'], 'Component measurement uncertainty changed')
        require(row['component_link_numbers'] == component_refs[row['side']][row['component']], 'Complete component links omitted')
    require(seen == {(side, identity) for side, group in records.items() for identity in group}, 'Original unlinked components erased')
    errors = [p for p in rows['fragment_pairs'] if p['status'] != 'checked']
    require(report['overlay_unknowns'] == errors and report['difference_unknowns'] == differences, 'Operation unknown roster differs')
    require(report['status'] == ('complete-accounting-with-explicit-unknowns' if errors or differences else 'complete-exact-correspondence-accounting'), 'Completion status overclaims')
    require(len(report['original_blocked_domains']) == len(old_report['tiles_blocked']), 'Old blocked domains erased')
    for binding, tile in zip(report['original_blocked_domains'], old_report['tiles_blocked']):
        same = [t for t in new_report['tiles'] if t['bounds'] == tile['bounds']]
        require(len(same) == 1 and binding == {'original': tile, 'new': same[0]}, 'Old blocked domain binding changed')
    # These parsed accounting rows and lookup tables have been checked in full.
    # Retire them before reconstruction, rather than growing its working set.
    # Original custody bytes and files remain unchanged and independently bound.
    fragment_pair_count = len(rows['fragment_pairs'])
    for family in set(rows) - {'new_components', 'new_contacts'}:
        del rows[family]
    del pair_refs, link_refs, component_refs, old_by, new_by, old_members, new_members
    del identities, seen_links, seen, records, ledgers, links, errors, differences
    del old, old_records, remnants
    # Reject invalid accounting before expensive reconstruction. Every successful
    # execution still reconstructs the complete world and checks exact shapes.
    # Independently reconstruct complete connected sets and their edge/point/
    # dateline contact roster; counts alone cannot detect a rehashed omission.
    rebuilt, contacts = components(new, [t for t in new_report['tiles'] if t['status'] != 'checked'], new_report['bounds'])
    for record in rebuilt:
        record['id'] = 'physical-component:' + record['id'].split(':', 1)[1]
    rebuilt_members = membership(new, rebuilt)
    for contact in contacts:
        contact['components'] = [rebuilt_members[i] for i in contact['fragments']]
    require_exact_reconstruction(rows['new_contacts'], contacts,
                                 'Complete original edge/point/dateline contact roster changed')
    require_exact_reconstruction(new_records, rebuilt,
                                 'Complete exact connected component shapes changed')
    resolved = component_contacts(new, new_records)
    result.update(fragment_pairs=fragment_pair_count, new_components=len(new_records),
                  source_contact_components=len(resolved), source_contact_unknowns=sum(r['status'] != 'complete-recorded-contacts' for r in resolved))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', default=INDEX)
    args = parser.parse_args()
    print(json.dumps(validate_science(args.index)))
