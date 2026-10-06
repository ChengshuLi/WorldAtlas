"""Authenticate an unchanged existing-world gap inventory and re-run connectivity.

This bounded producer refuses changed inputs: it cannot label a candidate repair
current or silently reuse changed tiles. Original products stay at their actual
measurement vintage; the new product is an identity lineage, not new land truth.
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import re
import subprocess
import sys

import shapely
from shapely.geometry import box
from evidence.immutable import canonical_json, deterministic_gzip
from geographic_components import components
from physical_gap_audit import Detector, load_inputs, decode
from physical_gap_crosswalk import membership

ORIGINAL = '548c5f89f00271050823076a84695bb41e1b8454'
ARTIFACT = 'a32ae163473a42ed28d7bedf7e9930414beb54f8'
WATER = 'ff566eab31ef072084c548f67dee8ee727ab3d47'
DETECTOR = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'
COMPONENT_ROOT = 'coordination/engineering/physical-gap-components-1005-20261005-local19/'
COMPONENT_REPORT = COMPONENT_ROOT + 'custody-v1/payloads/d3fb7670754c5689cdb991c0d0111105867c89196327adc2fceb582d61a58a94.bin'
WATER_ROOT = 'coordination/engineering/coverage-gaps-907-20261005-local01/sources'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(raw, row):
    if len(raw) != row['bytes'] or digest(raw) != row['sha256']:
        raise ValueError('Whole input byte mismatch: ' + row['path'])
    return raw


def require_equivalent(original, selected):
    equal = original == selected if isinstance(original, (bytes, str)) else canonical_json(original) == canonical_json(selected)
    if not equal:
        raise ValueError('Changed operand/order/status requires recomputation; identity reuse refused')


def query(detector, data, bounds):
    tile = box(*bounds)
    def invalid(rows):
        return [r['id'] for r in rows if box(*r['unchecked_bounds']).intersects(tile)]
    return {
        'land': [data['land_metadata'][int(i)]['id'] for i in detector.land_tree.query(tile, predicate='intersects')],
        'locations': [data['location_metadata'][int(i)]['id'] for i in detector.location_tree.query(tile, predicate='intersects')],
        'invalid_land': invalid(data['invalid_land']),
        'invalid_locations': invalid(data['invalid_locations']),
        'invalid_water': invalid(data['invalid_water']),
        'shorelines': [f'physical-shoreline:{int(i)}' for i in detector.shore_tree.query(tile, predicate='intersects')],
    }


def validate_selected(selected):
    if not isinstance(selected, str) or not re.fullmatch(r'[0-9a-f]{40}', selected):
        raise ValueError('Selected revision must be an exact lowercase forty-character commit SHA')
    return selected


def run(repo, selected, output):
    validate_selected(selected)
    if output.exists():
        raise ValueError('Refusing to overwrite prior run')
    def blob(commit, path):
        mode = subprocess.check_output(['git', 'ls-tree', commit, '--', path], cwd=repo).split()[0]
        if mode not in (b'100644', b'100755'):
            raise ValueError('Not an ordinary Git source: ' + path)
        return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=repo)
    subprocess.run(['git', 'merge-base', '--is-ancestor', selected, 'origin/main'], cwd=repo, check=True)
    execution = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    executed_files = []
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        source = pathlib.Path(filename).resolve()
        try:
            path = str(source.relative_to(repo / 'scripts'))
        except ValueError:
            continue
        path = 'scripts/' + path
        if source.is_symlink() or source.suffix != '.py':
            raise ValueError('Owned imported module is not an ordinary Python source')
        raw = blob(execution, path)
        require_equivalent(raw, source.read_bytes())
        executed_files.append({'path': path, 'bytes': len(raw), 'sha256': digest(raw), 'hash_kind': 'file-bytes'})
    executed_files = list({row['path']: row for row in executed_files}.values())
    if (sys.version.split()[0], shapely.__version__, shapely.geos_version_string) != ('3.12.14', '2.1.2', '3.13.1'):
        raise ValueError('Original measured software environment required')
    descriptors = {}
    def retained(commit, path, expected=None):
        raw = blob(commit, path)
        if expected:
            verify(raw, expected)
        selected_raw = blob(selected, path)
        require_equivalent(raw, selected_raw)
        descriptors[path] = {'path': path, 'bytes': len(raw), 'sha256': digest(raw), 'hash_kind': 'file-bytes'}
        return raw
    for row in executed_files:
        if row['path'] != 'scripts/worldwide_gap_inventory.py':
            retained(execution, row['path'], row)
    report = json.loads(retained(ARTIFACT, DETECTOR))
    require_equivalent(report['baseline_commit'], ORIGINAL)
    for row in report['inputs']:
        retained(ORIGINAL, row['path'], row)
    for row in report['water_inputs']:
        retained(WATER, row['path'], row)
    for row in report['code_inputs']:
        retained(report['executed_code_commit'], row['path'], row)
    old_data = load_inputs(repo, ORIGINAL, WATER_ROOT, WATER)
    new_data = load_inputs(repo, selected, WATER_ROOT, WATER)
    require_equivalent(old_data['inputs'], new_data['inputs'])
    require_equivalent(old_data['location_metadata'], new_data['location_metadata'])
    require_equivalent(old_data['release_ids'], new_data['release_ids'])
    old_detector, new_detector = Detector(old_data), Detector(new_data)
    queries = []
    for index, tile in enumerate(report['tiles']):
        before = query(old_detector, old_data, tile['bounds'])
        after = query(new_detector, new_data, tile['bounds'])
        require_equivalent(before, after)
        queries.append({'tile_id': index, 'bounds': tile['bounds'], 'query_order': after,
                        'status': tile['status'], 'blocked_sources': tile.get('blocked_sources', [])})
    print('Authenticated complete world source closure and all tile queries', flush=True)
    decoded_receipts = []
    def read_features(row, path=None):
        raw = retained(ARTIFACT, path or row['path'], {**row, 'path': path or row['path']})
        decoded = decode(raw)
        if len(decoded) != row['uncompressed_bytes'] or digest(decoded) != row['uncompressed_sha256']:
            raise ValueError('Decoded original shard mismatch')
        decoded_receipts.append({'path': path or row['path'], 'encoded_sha256': digest(raw),
                                 'decoded_bytes': len(decoded), 'decoded_sha256': digest(decoded)})
        value = json.loads(decoded)
        return value['features'] if isinstance(value, dict) else value
    fragments = [f for row in report['outputs'] for f in read_features(row)]
    residues = [f for row in report['residue_outputs'] for f in read_features(row)]
    index = json.loads(retained(ARTIFACT, COMPONENT_ROOT + 'custody-v1/index.json'))
    comp_report = json.loads(retained(ARTIFACT, COMPONENT_REPORT))
    aliases = {r['original']['path']: r['payload'] for r in index['aliases']}
    archived_components = [f for row in comp_report['outputs']['new_components']
                           for f in read_features(row, aliases[row['path']])]
    archived_contacts = [f for row in comp_report['outputs']['new_contacts']
                         for f in read_features(row, aliases[row['path']])]
    for row in comp_report['code_inputs']:
        retained(comp_report['executed_code_commit'], row['path'], row)
    blocked = [t for t in report['tiles'] if t['status'] != 'checked']
    fresh_components, fresh_contacts = components(fragments, blocked, report['bounds'])
    for component in fresh_components:
        component['id'] = 'physical-component:' + component['id'].split(':', 1)[1]
    members = membership(fragments, fresh_components)
    for contact in fresh_contacts:
        contact['components'] = [members[i] for i in contact['fragments']]
    require_equivalent(fresh_components, archived_components)
    require_equivalent(fresh_contacts, archived_contacts)
    require_equivalent(membership(fragments, archived_components), members)
    print('Recomputed worldwide connectivity and exact archived component/contact match', flush=True)
    output.mkdir(parents=True)
    def emit(name, value, compressed=False):
        raw = canonical_json(value)
        encoded = deterministic_gzip(raw) if compressed else raw
        (output / name).write_bytes(encoded)
        return {'path': name, 'bytes': len(encoded), 'sha256': digest(encoded),
                'decoded_bytes': len(raw), 'decoded_sha256': digest(raw)}
    products = [emit('tile-queries.json.gz', queries, True),
                emit('decoded-custody.json', decoded_receipts)]
    # Identity maps are exact bijections over authenticated complete rosters.
    # Components contain every fragment and original full-feature binding. No
    # duplicated geometry or artificial intersection/difference is necessary.
    lineage = {'kind': 'whole-byte-identity-bijection', 'original_input_commit': ORIGINAL,
               'selected_input_commit': selected, 'measurement_artifact_commit': ARTIFACT,
               'fragment_roster': {'count': len(fragments), 'sorted_ids_sha256': digest(canonical_json(sorted(f['id'] for f in fragments)))},
               'component_roster': {'count': len(fresh_components), 'sorted_ids_sha256': digest(canonical_json(sorted(f['id'] for f in fresh_components)))},
               'residue_roster': {'count': len(residues), 'sorted_ids_sha256': digest(canonical_json(sorted(f['id'] for f in residues)))},
               'mapping_rule': 'Every declared original ID maps to the identical selected ID; exact full record equality verified.',
               'removed': [], 'new': [], 'split': [], 'merged': [], 'unknown_lineage': []}
    products.append(emit('identity-lineage.json.gz', lineage, True))
    summary = {'version': 'worldatlas-existing-world-inventory-v1',
               'selected_main_commit': selected, 'executed_code_commit': execution, 'executed_code_files': executed_files,
               'original_input_commit': ORIGINAL, 'measurement_artifact_commit': ARTIFACT,
               'measurement_executed_code_commit': report['executed_code_commit'],
               'release_ids': new_data['release_ids'], 'release_index_sha256': new_data['release_index_sha256'],
               'domain': report['bounds'], 'software': report['software'],
               'tiles': len(queries), 'unchecked_tiles': len(blocked), 'reused_tiles': len(queries),
               'fragments': len(fragments), 'components': len(fresh_components), 'contacts': len(fresh_contacts),
               'residues': len(residues),
               'unmeasured_fragment_ids': sorted(f['id'] for f in fragments if f['properties'].get('area_m2') is None),
               'contact_kinds': {kind: sum(c['kind'] == kind for c in fresh_contacts) for kind in sorted({c['kind'] for c in fresh_contacts})},
               'dateline_contacts': sum(c['dateline'] for c in fresh_contacts),
               'source_descriptors': list(descriptors.values()), 'products': products,
               'complete_products': {'fragments': report['outputs'], 'residues': report['residue_outputs'],
                                     'components': comp_report['outputs']['new_components'],
                                     'contacts': comp_report['outputs']['new_contacts'], 'custody_aliases': aliases},
               'limits': report['limits'] + [
                   'Existing immutable main release only; later geography changes require a successor.',
                   'All original source, date, area, water and political limitations remain unchanged.',
                   'Identity reuse requires complete equal inputs and tile query order; changed input is refused.',
                   'Native classification, ranking and batch preparation belong to issue1184.',
                   'No water/land certification, political attribution, core repair, or deployment.']}
    emit('report.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--selected', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(pathlib.Path(__file__).resolve().parents[1], args.selected, pathlib.Path(args.output).resolve())
