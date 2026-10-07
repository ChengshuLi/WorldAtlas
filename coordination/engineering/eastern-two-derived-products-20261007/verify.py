"""Complete source relations and unchanged stock semantic runtime consumers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
import sys

from restore import PREFIX, ROOT, checked, gunzip, restore, sha

TARGETS = {'atlas:physical:CAN-103:QUE', 'atlas:physical:CAN-114:NFL'}
BEFORE = '6ea7c3613759d7b747c800c399b70c1be24e1f6aea21fc81c389cfdcc78d3eb1'
AFTER = 'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433'


def read(p):
    raw = p.read_bytes()
    return json.loads(gunzip(raw) if p.name.endswith('.gz') else raw)


def same_values(a, b):
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return struct.pack('>d', float(a)) == struct.pack('>d', float(b))
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same_values(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same_values(x, y) for x, y in zip(a, b))
    return a == b


def world_relation(root, index):
    original = root / 'complete_original_world_source_relation'
    staged = root / 'full_world_inputs'
    proof = index['snapshot_original_relation']
    changed = []
    ids = []
    for row in proof['rows']:
        ordinal = row['ordinal']
        raw = checked(original, row['original']['path']).read_bytes()
        before_path = 'before/part-' + str(ordinal) + '.json'
        before = checked(staged, before_path).read_bytes()
        if before != raw:
            raise ValueError('Complete original before pointset differs')
        after_path = 'after/part-29.json' if ordinal == 29 else before_path
        after = checked(staged, after_path).read_bytes()
        if ordinal != 29 and after != raw:
            raise ValueError('Unchanged whole source pointset differs')
        if ordinal == 29:
            proposal = proof['proposal']
            source = next(b for b in index['bindings'] if (b.get('original_binding') or {}).get('blob') == proposal['blob'])
            proposed = gunzip(checked(root, source['group'] + '/' + source['path']).read_bytes())
            if not proposed.endswith(b'\n') or after != proposed[:-1]:
                raise ValueError('Exact proposed final-LF derivation differs')
        a = json.loads(before)['features']
        b = json.loads(after)['features']
        if len(a) != len(b):
            raise ValueError('Full feature roster differs')
        for old, new in zip(a, b):
            if old['id'] != new['id'] or not same_values(old['properties'], new['properties']):
                raise ValueError('Identity/metadata/parent transfer')
            ids.append(old['id'])
            if not same_values(old, new):
                changed.append(old['id'])
    if len(ids) != 49625 or len(set(ids)) != 49625 or set(changed) != TARGETS or len(changed) != 2:
        raise ValueError('Full original/proposed geographic closure differs')
    return {'complete_features': len(ids), 'changed_ids': changed, 'unchanged_features': len(ids) - 2,
            'part29_derivation': 'whole proposed decoded body minus exactly one final LF',
            'historical_constructor_not_relabelled': True}


def ownership_relation(root):
    original = root / 'original_ownership_cliopatria244/data/ownership-history'
    proposed = root / 'full_ownership_products180'
    old_index, new_index = read(original / 'index.json'), read(proposed / 'index.json')
    if old_index['footprints_sha256'] != BEFORE or new_index['footprints_sha256'] != AFTER:
        raise ValueError('Ownership full source/proposal vintage differs')
    for key in ('owner_ids', 'labels', 'source_ids', 'statuses_order', 'valid_from', 'valid_to'):
        if old_index[key] != new_index[key]:
            raise ValueError('Original ownership dictionary/date domain differs')
    old_targets = {}
    unchanged = intervals = 0
    new_parts = {}
    for part in new_index['parts']:
        for identifier, rows in read(proposed / part['path']):
            if identifier in TARGETS:
                new_parts[identifier] = rows
    for part in old_index['parts']:
        old_rows = read(original / part['path'])
        reused = next((p for p in new_index['parts'] if p.get('reused_original_sha256') == part['sha256']), None)
        if reused is None:
            # The complete part containing the two targets is rewritten after
            # removing just those rows; its whole checksum correctly changes.
            reused = next((p for p in new_index['parts'] if p['path'] == part['path']), None)
        if reused is None:
            raise ValueError('Original whole location part reuse missing')
        new_rows = read(proposed / reused['path'])
        expected = []
        for identifier, rows in old_rows:
            if identifier in TARGETS:
                old_targets[identifier] = rows
            else:
                expected.append([identifier, rows])
                unchanged += 1
                intervals += len(rows)
        if expected != new_rows:
            raise ValueError('Unchanged complete ownership rows differ')
    if set(old_targets) != TARGETS or set(new_parts) != TARGETS:
        raise ValueError('Complete target interval roster omitted')
    for identifier in TARGETS:
        if [r[:4] for r in old_targets[identifier]] != [r[:4] for r in new_parts[identifier]]:
            raise ValueError('Target dates/owner/status changed')
    target_intervals = sum(len(v) for v in old_targets.values())
    if (unchanged, intervals, target_intervals) != (49623, 6833690, 165):
        raise ValueError('Ownership full retained scope differs')
    return {'unchanged_locations': unchanged, 'unchanged_intervals': intervals,
            'target_intervals': target_intervals, 'target_dates_owner_status_preserved': True}


def pixel_relation(root):
    old = read(root / 'pixel_original_inputs/data/pixel-audit.json')
    new = read(root / 'full_pixel_products2/pixel-audit.json')
    if old['footprints_sha256'] != BEFORE or new['footprints_sha256'] != AFTER:
        raise ValueError('Pixel/source footprint differs')
    if len(old['records']) != 49625 or len(new['records']) != 49625:
        raise ValueError('Pixel full roster omitted')
    changed = []
    for a, b in zip(old['records'], new['records']):
        if a['id'] != b['id']:
            raise ValueError('Pixel identity/order changed')
        if a != b:
            changed.append(a['id'])
    if set(changed) != TARGETS or len(changed) != 2:
        raise ValueError('Pixel untouched records changed')
    if new['covered_cells'] - old['covered_cells'] != 3:
        raise ValueError('Pixel three added cells differ')
    return {'unchanged_full_records': 49623, 'changed_records': changed,
            'added_owned_cells': 3, 'native_pixel_method_reused_at_original_b7': True}


def code_image(root, index):
    image = root / 'executed-consumer-image'
    image.mkdir()
    for group in ('existing_caller_and_helper_code', 'actual_selector_transitive_closure'):
        for row in (b for b in index['bindings'] if b['group'] == group):
            src = checked(root, group + '/' + row['path'])
            dst = checked(image, row['path'])
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if dst.read_bytes() != src.read_bytes():
                    raise ValueError('Executed import duplicate differs')
            else:
                os.link(src, dst)
    return image


def run(commit, destination, node, identical_prior=None):
    destination = Path(os.path.abspath(destination))
    index, restored = restore(commit, destination, identical_prior)
    result = {'world': world_relation(destination, index), 'ownership': ownership_relation(destination),
              'pixel': pixel_relation(destination)}
    image = code_image(destination, index)
    old_namespace = image / 'coordination/engineering/eastern-two-gap-repair-native-20261007'
    runtime = destination / 'full_runtime_products55'
    ownership = destination / 'full_ownership_products180'
    selector = destination / 'production-selector-map.json'
    subprocess.run([node, str(old_namespace / 'runtime-selector-proof.mjs'), str(runtime), str(selector)], check=True, cwd=image)
    subprocess.run([sys.executable, str(old_namespace / 'runtime-complete-equivalence.py'),
                    '--source', str(ownership), '--runtime', str(runtime), '--selector-map', str(selector),
                    '--receipt', str(destination / 'complete-runtime-semantic-proof.json')], check=True, cwd=image)
    result['runtime'] = read(destination / 'complete-runtime-semantic-proof.json')
    result['restoration'] = restored
    result['scientific_stage_reuse'] = {'ownership': 'b7b45a6c686c3dff9063185829ec0e2f66d7932d',
                                      'pixel': 'b7b45a6c686c3dff9063185829ec0e2f66d7932d',
                                      'runtime': '55e77780fad75fe38af40e1cc05cbd72c7f193d2'}
    result['artifact_only_no_activation_or_authority_approval'] = True
    (destination / 'complete-product-verification.json').write_text(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
    print(json.dumps({'status': 'PASS', 'complete_locations': 49625,
                      'runtime_source_intervals': result['runtime']['source_intervals'],
                      'runtime_endpoint_checks': result['runtime']['endpoint_selector_checks']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--node', required=True)
    parser.add_argument('--identical-prior', type=Path)
    args = parser.parse_args()
    run(args.commit, args.destination, args.node, args.identical_prior)
