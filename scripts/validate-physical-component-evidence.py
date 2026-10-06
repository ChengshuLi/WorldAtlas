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

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_REPO = ROOT
INDEX = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
OLD = 'coordination/engineering/coverage-gaps-907-20261005-local01/global-v3/report.json'
OLD_COMPONENTS = 'coordination/engineering/geographic-components-946-20261005-local06/components-v2/report.json'
NEW = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_science(index_path=INDEX):
    index = json.loads(ordinary_read(ROOT, index_path))
    require({g['prefix'] for g in index['generations']} == {OWNED + 'components-v' + str(i) for i in (1, 2, 3)}, 'Original execution vintage roster differs')
    result = validate(ROOT, index)
    aliases = {a['original']['path']: a for a in index['aliases']}

    def original(path):
        return ordinary_read(ROOT, aliases[path]['payload'])

    complete = [g for g in index['generations'] if g['status'] == 'complete']
    report = json.loads(original(complete[0]['prefix'] + '/report.json'))
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
    # Independently reconstruct complete connected sets and their edge/point/
    # dateline contact roster; counts alone cannot detect a rehashed omission.
    rebuilt, contacts = components(new, [t for t in new_report['tiles'] if t['status'] != 'checked'], new_report['bounds'])
    for record in rebuilt:
        record['id'] = 'physical-component:' + record['id'].split(':', 1)[1]
    rebuilt_members = membership(new, rebuilt)
    for contact in contacts:
        contact['components'] = [rebuilt_members[i] for i in contact['fragments']]
    require(len(rows['new_contacts']) == len(contacts) and
            all(canonical_json(a) == canonical_json(b) for a, b in zip(rows['new_contacts'], contacts)),
            'Complete original edge/point/dateline contact roster changed')
    require(len(new_records) == len(rebuilt) and
            all(canonical_json(a) == canonical_json(b) for a, b in zip(new_records, rebuilt)),
            'Complete exact connected component shapes changed')
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
    resolved = component_contacts(new, new_records)
    result.update(fragment_pairs=len(rows['fragment_pairs']), new_components=len(new_records),
                  source_contact_components=len(resolved), source_contact_unknowns=sum(r['status'] != 'complete-recorded-contacts' for r in resolved))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', default=INDEX)
    args = parser.parse_args()
    print(json.dumps(validate_science(args.index)))
