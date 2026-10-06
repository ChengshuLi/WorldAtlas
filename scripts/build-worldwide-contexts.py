"""Authenticate complete archived contexts and explicit successor applicability.

This stage produces no native-grid observations or physical interpretation.
"""
import argparse
import copy
import gzip
import importlib.util
import io
import json
import pathlib
import platform
import subprocess
import zlib

from evidence.immutable import Baseline, MAX_FILE_BYTES, canonical_json, descriptor, sha256
from physical_gap_priority import hierarchy_context

ROOT = pathlib.Path(__file__).resolve().parents[1]
FROZEN = 'cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
SELECTED = '79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'
OWNED = 'coordination/engineering/worldwide-contexts-1184-20261006/'
OLD_REPORT = 'coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/report.json'
INVENTORY = 'coordination/engineering/worldwide-inventory-1164-20261006/run-one/'
CANDIDATE = 'coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json'
CODE = ['scripts/build-worldwide-contexts.py', 'scripts/physical_gap_priority.py',
        'scripts/evidence/immutable.py', 'scripts/build-physical-gap-priorities.py']
DETECTOR = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'


class Inputs:
    """Reuse bounded ordinary Git reads; retain every full-file descriptor."""
    def __init__(self, commit, seed):
        raw = subprocess.check_output(['git', 'show', commit + ':' + seed], cwd=ROOT)
        self.reader = Baseline(ROOT, commit, [descriptor(seed, raw)])
        self.commit, self.pins = commit, {}

    def read(self, path, expected=None):
        raw = self.reader.read(path)
        pin = descriptor(path, raw)
        if expected and any(pin[k] != expected[k] for k in pin):
            raise ValueError('Original whole-file descriptor differs: ' + path)
        self.pins[path] = pin
        return raw

    def json(self, path, expected=None):
        raw = self.read(path, expected)
        if path.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError('Decoded whole file exceeds limit')
            pin = self.pins[path]
            pin.update(uncompressed_bytes=len(raw), uncompressed_sha256=sha256(raw))
            if expected and any(pin[k] != expected[k] for k in ('uncompressed_bytes', 'uncompressed_sha256')):
                raise ValueError('Original whole decoded descriptor differs: ' + path)
        return json.loads(raw)


def checked_context(feature, archived, nodes, owner):
    identity = feature['id']
    if archived['id'] != identity or owner['id'] != identity:
        raise ValueError('Context/source/owner identity differs')
    if sha256(canonical_json(feature)) != archived['original_feature_sha256']:
        raise ValueError('Complete original feature differs from archived context')
    computed = hierarchy_context(feature, nodes)
    if any(computed[k] != archived[k] for k in computed):
        raise ValueError('Recorded complete ancestry differs')
    if feature['properties'].get('parent_id') != owner['province_id']:
        raise ValueError('Owner registry recorded parent differs')
    if archived['original_metadata'] != feature['properties'].get('metadata', {}):
        raise ValueError('Complete original source metadata differs')
    if archived['original_name'] != feature['properties'].get('name'):
        raise ValueError('Original recorded name differs')
    return {**archived, 'frozen_owner_registry': owner,
            'native_observation_status': 'pending-pr2-complete-grid-measurement',
            'physical_interpretation': 'unknown', 'source_authority_status': 'not-independently-approved'}


def geometry_values(geometry):
    """Exact decoded binary64 coordinate values, retaining signed zero and structure."""
    def coordinates(value):
        if isinstance(value, list):
            return [coordinates(v) for v in value]
        if type(value) not in (float, int):
            raise ValueError('Unexpected nonnumeric source coordinate')
        return float(value).hex()
    return {'type': geometry['type'], 'coordinates': coordinates(geometry['coordinates'])}


def negative_controls(feature, archived, nodes, owner):
    """Reject corrupted actual input bindings, including self-consistent stale metadata."""
    trials = []
    def rejects(name, f=feature, a=archived, n=nodes, o=owner):
        try:
            checked_context(f, a, n, o)
        except (ValueError, KeyError) as error:
            trials.append({'control': name, 'rejected': True, 'error': str(error)})
        else:
            raise ValueError('Negative control accepted: ' + name)
    bad = copy.deepcopy(feature)
    bad['properties']['name'] = str(bad['properties'].get('name')) + '-altered'
    rejects('altered-whole-source-feature', f=bad)
    bad_archive = copy.deepcopy(archived)
    bad_archive['original_feature_sha256'] = '0' * 64
    rejects('stale-archived-feature-binding', a=bad_archive)
    bad_owner = dict(owner, id='missing-source-id')
    rejects('owner-identity-substitution', o=bad_owner)
    rejects('owner-recorded-parent-substitution', o=dict(owner, province_id='missing-parent'))
    bad_nodes = dict(nodes)
    parent = feature['properties']['parent_id']
    bad_nodes[parent] = dict(nodes[parent], name='altered-recorded-ancestor')
    rejects('altered-complete-hierarchy', n=bad_nodes)
    bad_archive = copy.deepcopy(archived)
    bad_archive['original_metadata'] = {'unsupported': 'substituted source metadata'}
    rejects('source-metadata-substitution-with-valid-feature-hash', a=bad_archive)
    bad_archive = copy.deepcopy(archived)
    bad_archive['status'] = 'invented-approval'
    rejects('ancestry-status-laundering', a=bad_archive)
    return {'method_id': 'complete-world-context-binding-v1', 'kind': 'negative',
            'outcome': 'passed', 'trials': trials}


def run(output):
    if not output.startswith(OWNED) or output == OWNED.rstrip('/'):
        raise ValueError('Use exact owned new output vintage')
    target = ROOT / output
    if target.exists() or any(p.is_symlink() for p in [target, *target.parents]):
        raise ValueError('Never overwrite previous evidence')
    executed = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    code = []
    for path in CODE:
        raw = subprocess.check_output(['git', 'show', executed + ':' + path], cwd=ROOT)
        if (ROOT / path).is_symlink() or (ROOT / path).read_bytes() != raw:
            raise ValueError('Commit exact executed code before generation')
        code.append(descriptor(path, raw))
    frozen, selected = Inputs(FROZEN, OLD_REPORT), Inputs(SELECTED, INVENTORY + 'report.json')
    original = frozen.json(OLD_REPORT)
    frozen.json(DETECTOR)
    archived = {}
    for pin in original['outputs']['native_contexts']:
        for row in frozen.json(pin['path'], pin):
            if row['id'] in archived:
                raise ValueError('Duplicate archived context')
            archived[row['id']] = row
    hierarchy = frozen.json('data/hierarchy.json')
    nodes = {row['id']: row for row in hierarchy}
    if len(nodes) != len(hierarchy):
        raise ValueError('Duplicate hierarchy identity')
    bounds = frozen.json('data/canonical-grid/bounds.json.gz')
    owners = {row['id']: row for row in bounds}
    if len(owners) != len(bounds) or sorted(row['index'] for row in bounds) != list(range(1, len(bounds) + 1)):
        raise ValueError('Incomplete or duplicate ordered owner registry')
    candidate = frozen.json(CANDIDATE)
    grid = frozen.json('data/canonical-grid/manifest.json')
    pointer = frozen.json('data/geographic-releases/current-manifest.json')
    release = frozen.json('data/geographic-releases/' + pointer['path'])
    current_pointer = selected.json('data/geographic-releases/current-manifest.json')
    current_release_path = 'data/geographic-releases/' + current_pointer['path']
    current_release = selected.json(current_release_path)
    if sha256(selected.read(current_release_path)) != current_pointer['sha256']:
        raise ValueError('Selected release pointer differs from whole release bytes')
    inventory = selected.json(INVENTORY + 'report.json')
    selected.json(INVENTORY + 'decoded-custody.json')
    selected.json(INVENTORY + 'identity-lineage.json.gz')
    world = frozen.json('data/world-index.json')
    if selected.reader.read('data/world-index.json') != frozen.read('data/world-index.json'):
        raise ValueError('Successor world-index changed; complete new world closure required')
    if selected.reader.read('data/hierarchy.json') != frozen.read('data/hierarchy.json'):
        raise ValueError('Successor hierarchy changed; complete new hierarchy closure required')
    contexts, changed, geometry_changed, representation_changed, aliases = [], [], [], [], []
    control_input = None
    seen = set()
    for part in world['parts']:
        path = 'data/' + part
        features = frozen.json(path)['features']
        current_raw = selected.reader.read(path)
        old_pin = frozen.pins[path]
        if sha256(current_raw) == old_pin['sha256']:
            current = None
            aliases.append({'selected_commit': SELECTED, 'baseline_commit': FROZEN, **old_pin,
                            'basis': 'whole-selected-ordinary-file-bytes-read-and-equal'})
        else:
            current_rows = selected.json(path)['features']
            current = {f['id']: f for f in current_rows}
            if len(current) != len(current_rows) or set(current) != {f['id'] for f in features}:
                raise ValueError('Successor part membership changed; explicit new/retired closure required')
        for feature in features:
            identity = feature['id']
            if identity in seen or identity not in archived or identity not in owners:
                raise ValueError('Incomplete or duplicate exact worldwide subject closure')
            seen.add(identity)
            row = checked_context(feature, archived[identity], nodes, owners[identity])
            if control_input is None:
                control_input = (feature, archived[identity], nodes, owners[identity])
            current_feature = current[identity] if current is not None else feature
            current_hash = sha256(canonical_json(current_feature))
            is_changed = current_hash != row['original_feature_sha256']
            geometry_changed_here = geometry_values(feature['geometry']) != geometry_values(current_feature['geometry'])
            if geometry_changed_here:
                geometry_changed.append(identity)
            if is_changed and not geometry_changed_here:
                representation_changed.append(identity)
            if {k: v for k, v in feature.items() if k != 'geometry'} != {k: v for k, v in current_feature.items() if k != 'geometry'}:
                raise ValueError('Unexpected successor identity/source/hierarchy metadata change')
            row['selected_successor_applicability'] = (
                'changed-coordinate-values' if geometry_changed_here else
                'changed-json-representation-exact-binary64-values' if is_changed else
                'identical-canonical-feature-bytes')
            if is_changed:
                changed.append(identity)
                row['selected_successor_context'] = {
                    **hierarchy_context(current_feature, nodes), 'feature_sha256': current_hash,
                    'input_path': path, 'metadata': current_feature['properties'].get('metadata', {}),
                    'name': current_feature['properties'].get('name'),
                    'native_observation_status': 'requires-separately-pinned-successor-measurement'}
            contexts.append(row)
    if seen != set(archived) or seen != set(owners) or len(seen) != 49625:
        raise ValueError('Missing archived/current/owner contexts')
    declared_changed = current_release['successor_geometry']['changed_ids']
    if sorted(geometry_changed) != sorted(declared_changed):
        raise ValueError('Whole-source current changes differ from release declared roster')
    # Reuse the existing deterministic shard producer, rather than introduce another format.
    spec = importlib.util.spec_from_file_location('original_priorities', ROOT / 'scripts/build-physical-gap-priorities.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target.mkdir(parents=True, exist_ok=False)
    outputs = module.write_parts(target, 'contexts', sorted(contexts, key=lambda r: r['id']))
    controls = negative_controls(*control_input)
    (target / 'negative-controls.json').write_bytes(canonical_json(controls))
    positive = {'method_id': 'complete-world-context-binding-v1', 'kind': 'positive',
                'outcome': 'passed', 'context_count': len(contexts),
                'complete_original_feature_bijection': True, 'complete_owner_bijection': True,
                'complete_current_source_bijection': True, 'changed_ids': sorted(changed),
                'changed_coordinate_value_ids': sorted(geometry_changed),
                'representation_only_changed_ids': sorted(representation_changed),
                'native_statistics_produced': False}
    (target / 'positive-controls.json').write_bytes(canonical_json(positive))
    report = {
        'version': 'worldatlas-worldwide-contexts-v1', 'executed_code_commit': executed,
        'frozen_measurement_commit': FROZEN, 'selected_successor_commit': SELECTED,
        'code_inputs': code, 'frozen_inputs': list(frozen.pins.values()),
        'selected_inputs': list(selected.pins.values()), 'outputs': outputs,
        'context_count': len(contexts), 'archived_context_count': len(archived),
        'ordered_owner_count': len(owners), 'selected_changed_ids': sorted(changed),
        'selected_coordinate_value_changed_ids': sorted(geometry_changed),
        'selected_representation_only_changed_ids': sorted(representation_changed),
        'selected_unchanged_count': len(contexts) - len(changed),
        'frozen_native_candidate': {k: candidate[k] for k in ('method', 'size', 'geographic_release', 'footprints_sha256', 'hierarchy_sha256')},
        'frozen_canonical_grid': {k: grid[k] for k in ('size', 'footprints_sha256', 'hierarchy_sha256')},
        'selected_release': current_release['releases'][-1],
        'inventory_component_count': inventory['components'],
        'selected_lossless_input_aliases': aliases + [
            {'selected_commit': SELECTED, 'baseline_commit': FROZEN, **frozen.pins[path],
             'basis': 'whole-selected-ordinary-file-bytes-read-and-equal'}
            for path in ('data/world-index.json', 'data/hierarchy.json')],
        'software': {'python': platform.python_version(), 'zlib': zlib.ZLIB_RUNTIME_VERSION},
        'limits': ['Reviewed native candidate is not the installed runtime grid.',
                   'No native observations/counts are produced by manifest or context inspection.',
                   'Archived source metadata is retained verbatim; processing records are not proved causes.',
                   'Current geography changes require separately pinned successor component/native measurements.',
                   'Identity, source locator and ancestry agreement does not approve source authority or water/land interpretation.']}
    (target / 'report.json').write_bytes(canonical_json(report))
    print(json.dumps({'contexts': len(contexts), 'changed_ids': sorted(changed), 'output': output}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    run(parser.parse_args().output)
