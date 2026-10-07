#!/usr/bin/env python3
"""Bounded DOSM comparator for the exact Terengganu 8/7/3 family.

This prepares a new result vintage. It never overwrites the original runs,
repairs geometry, classifies land/water, or assigns legal/source authority.
"""
import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import shapely
import shapely.lib as shapely_lib
from shapely.geometry import box, shape
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = 'research/geography/malaysia-terengganu-gap-source-fitness-20261007'
CONFIG_PATH = OWNED + '/input-config.json'
EVIDENCE_PATH = OWNED + '/evidence-quality.json'
CUSTODY = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
COMPONENT_PREFIX = 'coordination/engineering/physical-gap-components-1005-20261005-local19/components-v3/components-'
GEObOUNDARIES = 'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-MYS-ADM2-000.bin.gz'
ATLAS = 'data/geography/part-16.json'
ROUTE = 'coordination/engineering/global-actionability-routing-20261007/results/'
FAMILY_ID = 'gap-source-batch:bfb3cabaf651a97ffcfa1a76'
EXPECTED_COMPONENTS = [
    'physical-component:46a2537871d6055d90416c1508d40805648567d8dfc37696192a8a23d778922b',
    'physical-component:4dbe3afea3880fac1e82de705149e196aa6ad6930a0e0d4b740059fa75d401b2',
    'physical-component:6233f6efda804999c5d871acf8fca60daf4742a13f5001a69fba6f15b375f9b6',
    'physical-component:8bb9857dc07c70b27c9b4ed6a55fe70af5b322a293423aa1879d1d4e994c8c3f',
    'physical-component:96632d82d1eb09e9410028d0259535bf712f6005d821777f3b3d65e3941eb9ff',
    'physical-component:a5dbeb12c0625bb589edcafb5bc44d9953f36980565865e2032c4888221733e9',
    'physical-component:e9dd7858cb946a4779d6c2079ddd9876cb953d0406101094a428b10d602c70d5',
    'physical-component:f181e43671a67d0313075212a5b10c5c9d086541a044284eb3d7ff70f097fb62',
]
CONTACT_NAME_TO_ID = {
    'Dungun': 'gb:MYS:ADM2:92858781B15989569853600',
    'Setiu': 'gb:MYS:ADM2:92858781B44112931825428',
    'Marang': 'gb:MYS:ADM2:92858781B50781472629025',
    'Besut': 'gb:MYS:ADM2:92858781B66748088999576',
    'Kuala Terengganu': 'gb:MYS:ADM2:92858781B69735571651191',
    'Kuala Nerus': 'gb:MYS:ADM2:92858781B78340444844195',
    'Kemaman': 'gb:MYS:ADM2:92858781B85628090125570',
}
DISTRICT_CODES = {
    'Besut': '11_1', 'Dungun': '11_2', 'Kemaman': '11_3',
    'Kuala Terengganu': '11_4', 'Marang': '11_5',
    'Hulu Terengganu': '11_6', 'Setiu': '11_7', 'Kuala Nerus': '11_8',
}
NUMERIC_CLOSURE_IDS = [
    'physical-component:4dbe3afea3880fac1e82de705149e196aa6ad6930a0e0d4b740059fa75d401b2',
    'physical-component:a5dbeb12c0625bb589edcafb5bc44d9953f36980565865e2032c4888221733e9',
    'physical-component:f181e43671a67d0313075212a5b10c5c9d086541a044284eb3d7ff70f097fb62',
]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


MAX_PACKET_FILE_BYTES = 32 * 1024 * 1024
ALLOWED_RUN_FILES = {'run-one.json', 'run-two.json', 'execution-one.json', 'execution-two.json'}
METHOD_ID = 'terengganu-dosm-source-generator-r7'


def read_bounded_packet_file(path):
    """Read a bounded ordinary packet file without following symlinks."""
    path = pathlib.Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Packet input must be an ordinary non-symlink file')
    try:
        relative = path.absolute().relative_to(ROOT.absolute())
    except ValueError:
        relative = None
    if relative is not None:
        for parent in (ROOT / relative, *(ROOT / relative).parents):
            if parent == ROOT.parent:
                break
            if parent.is_symlink():
                raise ValueError('Packet input path contains a symlink')
    fd = None
    try:
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Packet input must be an ordinary non-symlink file')
        if info.st_size > MAX_PACKET_FILE_BYTES:
            raise ValueError('Packet input exceeds 32 MiB byte budget')
        chunks = []
        remaining = MAX_PACKET_FILE_BYTES + 1
        while remaining:
            block = os.read(fd, min(1024 * 1024, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        raw = b''.join(chunks)
        if len(raw) > MAX_PACKET_FILE_BYTES:
            raise ValueError('Packet input exceeds 32 MiB byte budget')
        return raw
    finally:
        if fd is not None:
            os.close(fd)


def safe_output_relative_path(value):
    if not isinstance(value, str) or '\\' in value or '\0' in value:
        raise ValueError('Unsafe output path')
    parsed = pathlib.PurePosixPath(value)
    parts = parsed.parts
    if parsed.is_absolute() or '..' in parts or '.' in parts or parsed.as_posix() != value:
        raise ValueError('Unsafe output path')
    if (len(parts) != 6 or parts[:3] != tuple(OWNED.split('/')) or parts[3] != 'vintages' or
            not re.fullmatch(r'20261007-dosm-r[0-9]+', parts[4])):
        raise ValueError('Output must use a unique named DOSM vintage')
    if parts[5] not in ALLOWED_RUN_FILES:
        raise ValueError('Unexpected output filename')
    return value


def validate_output_admission(relative):
    relative = safe_output_relative_path(relative)
    target = ROOT / relative
    vintage = target.parent
    for ancestor in (target, vintage, *vintage.parents):
        if ancestor == ROOT.parent:
            break
        if ancestor.is_symlink():
            raise ValueError('Symlink in output path')
    if target.exists() or target.is_symlink():
        raise FileExistsError('Evidence already exists; choose a fresh vintage')
    if vintage.exists() and not vintage.is_dir():
        raise ValueError('Vintage output parent is not an ordinary directory')
    return target


def safe_fresh_output_path(relative):
    target = validate_output_admission(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Recheck after directory creation to guard a raced path substitution.
    return validate_output_admission(relative)


def exclusive_write(path, raw):
    fd = None
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o644)
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            view = view[written:]
    finally:
        if fd is not None:
            os.close(fd)


def run_output_path_controls():
    traversal_rejected = symlink_rejected = overwrite_rejected = parent_symlink_rejected = False
    entry_rejected_before_calculation = False
    try:
        safe_output_relative_path(OWNED + '/vintages/20261007-dosm-r999999/../escape/run-one.json')
    except ValueError:
        traversal_rejected = True
    vintages = ROOT / OWNED / 'vintages'
    vintages.mkdir(parents=True, exist_ok=True)
    nonce = f'{os.getpid()}'
    real_vintage = vintages / ('20261007-dosm-r' + nonce)
    linked_vintage = vintages / ('20261007-dosm-r' + str(os.getpid() + 1000000000))
    external = pathlib.Path(tempfile.mkdtemp(prefix='dosm-output-control-'))
    try:
        real_vintage.mkdir()
        link_target = real_vintage / 'run-one.json'
        link_target.symlink_to(external / 'sentinel')
        try:
            safe_fresh_output_path(OWNED + '/vintages/' + real_vintage.name + '/run-one.json')
        except (FileExistsError, ValueError):
            symlink_rejected = True
        link_target.unlink()
        sentinel = b'preserve-existing-output'
        link_target.write_bytes(sentinel)
        try:
            safe_fresh_output_path(OWNED + '/vintages/' + real_vintage.name + '/run-one.json')
        except FileExistsError:
            overwrite_rejected = link_target.read_bytes() == sentinel
        real_vintage.rmdir() if not any(real_vintage.iterdir()) else shutil.rmtree(real_vintage)
        linked_vintage.symlink_to(external, target_is_directory=True)
        try:
            validate_output_admission(OWNED + '/vintages/' + linked_vintage.name + '/run-one.json')
        except ValueError:
            parent_symlink_rejected = True
        previous_argv = sys.argv
        previous_reproduce = globals()['reproduce']
        calculation_called = False
        def calculation_canary(_):
            nonlocal calculation_called
            calculation_called = True
            raise RuntimeError('calculation reached before output admission')
        try:
            sys.argv = [str(ROOT / (OWNED + '/reproduce-dosm.py')),
                        '--output', OWNED + '/vintages/' + linked_vintage.name + '/run-one.json',
                        '--receipt', OWNED + '/vintages/' + linked_vintage.name + '/execution-one.json']
            globals()['reproduce'] = calculation_canary
            try:
                main()
            except ValueError:
                entry_rejected_before_calculation = not calculation_called
        finally:
            sys.argv = previous_argv
            globals()['reproduce'] = previous_reproduce
    finally:
        if real_vintage.exists() and not real_vintage.is_symlink():
            shutil.rmtree(real_vintage)
        if linked_vintage.is_symlink():
            linked_vintage.unlink()
        shutil.rmtree(external, ignore_errors=True)
    checks = [
        {'control': 'path traversal rejected by production output path validator', 'passed': traversal_rejected},
        {'control': 'symlink output target rejected without following it', 'passed': symlink_rejected},
        {'control': 'existing output rejected and original bytes preserved', 'passed': overwrite_rejected},
        {'control': 'symlink vintage directory rejected by production output path guard', 'passed': parent_symlink_rejected},
        {'control': 'CLI rejects symlinked vintage before calculation is invoked', 'passed': entry_rejected_before_calculation},
    ]
    if not all(row['passed'] for row in checks):
        raise ValueError('Safe fresh output path controls failed')
    return checks


def loaded_shapely_module_fingerprints():
    rows = {}
    total = 0
    package_root = pathlib.Path(shapely.__file__).resolve().parent
    for name, module in sorted(sys.modules.items()):
        if name != 'shapely' and not name.startswith('shapely.'):
            continue
        origin = getattr(module, '__file__', None)
        if not origin:
            continue
        path = pathlib.Path(origin).resolve(strict=True)
        try:
            path.relative_to(package_root)
        except ValueError:
            continue
        raw = read_bounded_packet_file(path)
        total += len(raw)
        if total > 256 * 1024 * 1024:
            raise ValueError('Loaded Shapely module fingerprint set exceeds byte budget')
        rows[name] = {'path': str(path), 'bytes': len(raw), 'sha256': sha256(raw)}
    return [{'module': name, **row} for name, row in rows.items()]


def file_fingerprint(path):
    path = pathlib.Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Runtime fingerprint path is not an ordinary file')
    if path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('Runtime fingerprint exceeds the 256 MiB bound')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            digest.update(block)
    return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode()


def read_packet_config():
    """Bind the current config, producer, source, and license to the review manifest."""
    manifest_raw = read_bounded_packet_file(ROOT / EVIDENCE_PATH)
    manifest = json.loads(manifest_raw)
    if manifest.get('issue') != 1408 or manifest.get('subject_ids_sha256') is None:
        raise ValueError('Wrong or incomplete issue evidence manifest')
    outputs = {row['path']: row for row in manifest.get('outputs', [])}
    script_path = pathlib.Path(__file__).resolve().relative_to(ROOT).as_posix()
    for path in (CONFIG_PATH, script_path):
        descriptor = outputs.get(path)
        if descriptor is None:
            raise ValueError('Review manifest lacks a whole-file packet/producer descriptor: ' + path)
        raw = read_bounded_packet_file(ROOT / path)
        if len(raw) != descriptor.get('bytes') or sha256(raw) != descriptor.get('sha256'):
            raise ValueError('Packet/producer bytes differ from review manifest: ' + path)
    config = json.loads(read_bounded_packet_file(ROOT / CONFIG_PATH))
    retained = config['retained_sources'][0]
    source = next((row for row in manifest.get('sources', []) if row.get('id') == retained['id']), None)
    if source is None or source.get('retention') != 'retained' or not source.get('files'):
        raise ValueError('DOSM retained source is absent from review manifest')
    data_pin = source['files'][0]
    license_pin = source.get('license_file')
    if (data_pin.get('path') != retained['path'] or data_pin.get('bytes') != retained['bytes'] or
            data_pin.get('sha256') != retained['sha256']):
        raise ValueError('DOSM source hash/size disagree between config and review manifest')
    if (not license_pin or license_pin.get('path') != retained['license_path'] or
            license_pin.get('bytes') != retained['license_bytes'] or
            license_pin.get('sha256') != retained['license_sha256']):
        raise ValueError('DOSM license hash/size disagree between config and review manifest')
    return manifest, config, sha256(manifest_raw), manifest_raw


def read_json(raw, compressed=False):
    return json.loads(gzip.decompress(raw) if compressed else raw)


def bootstrap_pinned_modules(config):
    """Authenticate helper bootstrap bytes before executing them, then load
    the exact baseline-pinned helper graph through Baseline.load_modules.
    """
    pins = {row['path']: row for row in config['baseline']['files']}
    immutable_path = 'scripts/evidence/immutable.py'
    custody_path = 'scripts/physical_component_custody.py'
    immutable_pin = pins.get(immutable_path)
    custody_pin = pins.get(custody_path)
    if not immutable_pin or not custody_pin:
        raise ValueError('Baseline is missing exact helper source descriptors')
    immutable_raw = read_bounded_packet_file(ROOT / immutable_path)
    if len(immutable_raw) != immutable_pin['bytes'] or sha256(immutable_raw) != immutable_pin['sha256']:
        raise ValueError('Immutable helper bootstrap differs from its exact source pin')
    spec = importlib.util.spec_from_file_location('worldatlas_immutable_bootstrap', ROOT / immutable_path)
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    baseline = bootstrap.Baseline(ROOT, config['baseline']['commit'], config['baseline']['files'])
    modules = baseline.load_modules({
        'evidence.immutable': immutable_path,
        'physical_component_custody': custody_path,
    })
    for path in (immutable_path, custody_path):
        baseline.materialized_bytes(path)
    pinned_immutable = modules['evidence.immutable']
    pinned_baseline = pinned_immutable.Baseline(ROOT, config['baseline']['commit'], config['baseline']['files'])
    if pinned_immutable.VERSION != 'worldatlas-evidence-preparation-v1':
        raise ValueError('Unexpected pinned immutable helper version')
    modules['_helper_mutation_control'] = run_actual_helper_mutation_control(pinned_immutable)
    return pinned_baseline, modules, pins


def run_actual_helper_mutation_control(immutable_module):
    """Load a helper from a real temporary Git baseline, mutate its bytes, and
    verify the actual imported-helper reader rejects workspace drift.
    """
    with tempfile.TemporaryDirectory(prefix='dosm-helper-drift-') as temp:
        repo = pathlib.Path(temp) / 'repo'
        helper = repo / 'scripts' / 'physical_component_custody.py'
        helper.parent.mkdir(parents=True)
        original = b"VALUE = 'pinned-helper-body'\n"
        helper.write_bytes(original)
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'review-control@invalid'], check=True)
        subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Review Control'], check=True)
        subprocess.run(['git', '-C', str(repo), 'add', 'scripts/physical_component_custody.py'], check=True)
        subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'Pin helper fixture'], check=True)
        commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        descriptor = {'path': 'scripts/physical_component_custody.py', 'bytes': len(original),
                      'sha256': sha256(original), 'hash_kind': 'file-bytes'}
        baseline = immutable_module.Baseline(repo, commit, [descriptor])
        loaded = baseline.load_modules({'physical_component_custody': descriptor['path']})
        if loaded['physical_component_custody'].VALUE != 'pinned-helper-body':
            raise ValueError('Actual helper mutation control failed to load pinned helper')
        helper.write_bytes(b"VALUE = 'mutated-helper-body'\n")
        try:
            baseline.materialized_bytes(descriptor['path'])
        except ValueError as error:
            passed = str(error) == 'Actually consumed materialized input/code drift: ' + descriptor['path']
        else:
            passed = False
        if not passed:
            raise ValueError('Actual imported-helper byte mutation was not rejected')
        return {'passed': True, 'tested_helper_path': descriptor['path'],
                'pinned_sha256': descriptor['sha256'], 'mutated_sha256': sha256(helper.read_bytes())}


def validate_source_bytes(raw, descriptor):
    """The production loader and controls use this same byte gate."""
    if len(raw) != descriptor['bytes'] or sha256(raw) != descriptor['sha256']:
        raise ValueError('Retained source byte identity mismatch')
    product = json.loads(raw)
    if product.get('type') != 'FeatureCollection' or not isinstance(product.get('features'), list):
        raise ValueError('Retained source is not a GeoJSON FeatureCollection')
    if len(product['features']) != descriptor['expected_feature_count']:
        raise ValueError('Retained source feature count changed')
    crs = (product.get('crs') or {}).get('properties', {}).get('name')
    if crs != descriptor['crs']:
        raise ValueError('Retained source CRS metadata changed')
    return product


def index_product(features):
    found = {}
    for feature in features:
        props = feature.get('properties') or {}
        code = props.get('code_state_district')
        state = props.get('state')
        name = props.get('district')
        if not all(isinstance(value, str) and value for value in (code, state, name)):
            raise ValueError('National source feature lacks stable state/district/code identity')
        if code in found:
            raise ValueError('Duplicate national source feature identity')
        found[code] = (state, name, feature)
    return found


def index_districts(features):
    national = index_product(features)
    found = {}
    for state, name, feature in national.values():
        props = feature['properties']
        code = props['code_state_district']
        if state != 'Terengganu':
            continue
        if code != DISTRICT_CODES.get(name):
            raise ValueError('Unexpected Terengganu district identity/code')
        found[name] = feature
    if set(found) != set(DISTRICT_CODES):
        raise ValueError('Complete eight-district DOSM source roster is missing or changed')
    return found


def run_loader_controls(source_raw, descriptor, features):
    # Positive: actual production byte and identity loaders on the retained file.
    decoded = validate_source_bytes(source_raw, descriptor)
    indexed = index_districts(decoded['features'])
    positive = len(indexed) == 8

    # Negative: the actual production byte gate rejects one changed byte.
    altered = bytearray(source_raw)
    altered[-1] ^= 1
    try:
        validate_source_bytes(bytes(altered), descriptor)
    except ValueError as error:
        mutated_source_rejected = str(error) == 'Retained source byte identity mismatch'
    else:
        mutated_source_rejected = False

    # Negative: the actual production identity gate rejects a missing family district.
    omitted_features = [f for f in features if not (
        (f.get('properties') or {}).get('state') == 'Terengganu' and
        (f.get('properties') or {}).get('district') == 'Setiu')]
    try:
        index_districts(omitted_features)
    except ValueError as error:
        roster_omission_rejected = str(error) == 'Complete eight-district DOSM source roster is missing or changed'
    else:
        roster_omission_rejected = False
    # Exercise the real bounded filesystem reader on oversize and symlink paths.
    oversize_rejected = symlink_rejected = parent_symlink_rejected = False
    with tempfile.TemporaryDirectory(prefix='dosm-reader-control-') as temp:
        large = pathlib.Path(temp) / 'oversize.bin'
        with large.open('wb') as stream:
            stream.truncate(MAX_PACKET_FILE_BYTES + 1)
        try:
            read_bounded_packet_file(large)
        except ValueError as error:
            oversize_rejected = str(error) == 'Packet input exceeds 32 MiB byte budget'
        link = pathlib.Path(temp) / 'linked.bin'
        link.symlink_to(large)
        try:
            read_bounded_packet_file(link)
        except ValueError as error:
            symlink_rejected = str(error) == 'Packet input must be an ordinary non-symlink file'
    with tempfile.TemporaryDirectory(prefix='dosm-parent-reader-control-', dir=ROOT) as temp:
        base = pathlib.Path(temp)
        real_dir = base / 'real'
        real_dir.mkdir()
        (real_dir / 'input.bin').write_bytes(b'bounded-parent-symlink-check')
        linked_dir = base / 'linked'
        linked_dir.symlink_to(real_dir, target_is_directory=True)
        try:
            read_bounded_packet_file(linked_dir / 'input.bin')
        except ValueError as error:
            parent_symlink_rejected = str(error) == 'Packet input path contains a symlink'
    if not all((positive, mutated_source_rejected, roster_omission_rejected,
                oversize_rejected, symlink_rejected, parent_symlink_rejected)):
        raise ValueError('Actual source-loader positive/negative controls failed')
    return {
        'method_id': METHOD_ID,
        'positive': [{'control': 'retained complete source decodes and indexes all eight Terengganu districts', 'passed': positive}],
        'negative': [
            {'control': 'single-byte source mutation rejected by production byte gate', 'passed': mutated_source_rejected},
            {'control': 'missing Setiu identity rejected by production roster gate', 'passed': roster_omission_rejected},
            {'control': 'oversize packet file rejected before reading beyond byte budget', 'passed': oversize_rejected},
            {'control': 'symlink packet input rejected by production bounded reader', 'passed': symlink_rejected},
            {'control': 'symlink parent directory rejected by production bounded reader', 'passed': parent_symlink_rejected},
        ],
    }


def validate_scope_rosters(component_ids, contact_ids, numeric_closure_ids):
    if len(component_ids) != 8 or set(component_ids) != set(EXPECTED_COMPONENTS):
        raise ValueError('Exact eight-component family roster mismatch')
    expected_contacts = [CONTACT_NAME_TO_ID[name] for name in CONTACT_NAME_TO_ID]
    if len(contact_ids) != 7 or set(contact_ids) != set(expected_contacts):
        raise ValueError('Exact seven-contact family roster mismatch')
    if len(numeric_closure_ids) != 3 or set(numeric_closure_ids) != set(NUMERIC_CLOSURE_IDS):
        raise ValueError('Exact three numeric-closure roster mismatch')


def run_scope_loader_controls(component_ids, contact_ids, numeric_closure_ids):
    validate_scope_rosters(component_ids, contact_ids, numeric_closure_ids)
    negatives = []
    for label, components, contacts, numeric in (
        ('component omission', component_ids[:-1], contact_ids, numeric_closure_ids),
        ('contact omission', component_ids, contact_ids[:-1], numeric_closure_ids),
        ('numeric-closure omission', component_ids, contact_ids, numeric_closure_ids[:-1]),
    ):
        try:
            validate_scope_rosters(components, contacts, numeric)
        except ValueError:
            negatives.append({'control': label + ' rejected by production exact-scope gate', 'passed': True})
        else:
            negatives.append({'control': label + ' rejected by production exact-scope gate', 'passed': False})
    if not all(row['passed'] for row in negatives):
        raise ValueError('Exact family-scope roster controls failed')
    return {
        'method_id': METHOD_ID,
        'positive': {'control': 'exact 8-component/7-contact/3-numeric-closure cohort passes production roster gate', 'passed': True},
        'negative': negatives,
    }


def validate_contact_crosswalk(contact_map, atlas_features, districts, gb_name_by_id):
    expected_names = set(CONTACT_NAME_TO_ID)
    if set(contact_map) != expected_names or len(set(contact_map.values())) != len(expected_names):
        raise ValueError('Independent contact name/ID roster mismatch')
    for district_name, identity in contact_map.items():
        feature = atlas_features.get(identity)
        if feature is None or (feature.get('properties') or {}).get('name') != district_name:
            raise ValueError('Contact ID does not independently join to the expected Atlas feature name')
        raw_shape_id = identity.rsplit(':', 1)[-1]
        if gb_name_by_id.get(raw_shape_id) != district_name:
            raise ValueError('Contact ID does not independently join to pinned geoBoundaries shapeID/shapeName')
        if district_name not in districts:
            raise ValueError('Contact name is absent from retained DOSM district roster')


def run_contact_crosswalk_controls(atlas_features, districts, gb_name_by_id):
    validate_contact_crosswalk(CONTACT_NAME_TO_ID, atlas_features, districts, gb_name_by_id)
    swapped = dict(CONTACT_NAME_TO_ID)
    first, second = list(swapped)[:2]
    swapped[first], swapped[second] = swapped[second], swapped[first]
    try:
        validate_contact_crosswalk(swapped, atlas_features, districts, gb_name_by_id)
    except ValueError as error:
        rejected = str(error) == 'Contact ID does not independently join to the expected Atlas feature name'
    else:
        rejected = False
    if not rejected:
        raise ValueError('Swapped contact identity control was not rejected')
    return {'positive': {'control': 'each DOSM district name independently joins to the current Atlas contact feature name', 'passed': True},
            'negative': {'control': 'swapped contact name/ID pairs rejected by independent feature-name join', 'passed': rejected}}


def component_source_predicates(component_geom, source_geom):
    """Shared production predicates for comparison rows and geometry controls."""
    intersects = bool(component_geom.intersects(source_geom))
    positive = bool(intersects and component_geom.intersection(source_geom).area > 0)
    covered = bool(source_geom.covers(component_geom))
    return {'intersects': intersects, 'positive_coordinate_plane_area': positive,
            'source_covers_component': covered}


def run_geometry_predicate_controls():
    source = box(0, 0, 2, 2)
    contained = box(0.5, 0.5, 1, 1)
    disjoint = box(3, 3, 4, 4)
    positive_result = component_source_predicates(contained, source)
    negative_result = component_source_predicates(disjoint, source)
    positive_passed = positive_result == {
        'intersects': True, 'positive_coordinate_plane_area': True,
        'source_covers_component': True,
    }
    negative_passed = negative_result == {
        'intersects': False, 'positive_coordinate_plane_area': False,
        'source_covers_component': False,
    }
    if not positive_passed or not negative_passed:
        raise ValueError('Production geometry-predicate controls failed')
    return {
        'positive': {'control': 'contained synthetic polygon exercises the production intersects/positive-area-sign/covers predicates',
                     'passed': positive_passed, 'observed': positive_result},
        'negative': {'control': 'disjoint synthetic polygon exercises the production intersects/positive-area-sign/covers predicates',
                     'passed': negative_passed, 'observed': negative_result},
    }


def family_record(pin):
    family = None
    for index in range(14):
        path = f'{ROUTE}families-{index:03d}.bin.gz'
        for line in gzip.decompress(pin.pinned_bytes(path)).splitlines():
            if FAMILY_ID.encode() in line:
                if family is not None:
                    raise ValueError('Duplicate complete routing family')
                family = json.loads(line)
    if family is None:
        raise ValueError('Complete pinned routing family is absent')
    validate_scope_rosters(family['complete_component_ids'],
                           family['original_fine_family']['contact_ids'],
                           family['numeric_closure_component_ids'])
    if family['numeric_closure_component_count'] != 3 or set(family['numeric_closure_component_ids']) != set(NUMERIC_CLOSURE_IDS):
        raise ValueError('The three numeric-closure unknowns changed')
    return family


def reproduce(output_path):
    manifest, config, evidence_manifest_sha256, manifest_raw = read_packet_config()
    pin, modules, pins = bootstrap_pinned_modules(config)
    if len(config['subject_ids']) != 15:
        raise ValueError('Exact 8-component/7-contact subject scope changed')
    expected_subjects = set(EXPECTED_COMPONENTS) | set(CONTACT_NAME_TO_ID.values())
    config_subjects = config['subject_ids']
    expected_subject_hash = sha256(json.dumps(sorted(expected_subjects), separators=(',', ':')).encode())
    if set(config_subjects) != expected_subjects or config['subject_ids_sha256'] != expected_subject_hash:
        raise ValueError('Input-config 8/7 subject identities or canonical hash changed')
    custody = read_json(pin.pinned_bytes(CUSTODY))
    custody_validation = modules['physical_component_custody'].validate(ROOT, custody)
    aliases = {row['original']['path']: row for row in custody['aliases']}
    components = {}
    for path in sorted(p for p in aliases if p.startswith(COMPONENT_PREFIX)):
        alias = aliases[path]
        raw = pin.pinned_bytes(alias['payload'])
        if sha256(raw) != alias['original']['sha256']:
            raise ValueError('Custodied complete-component payload hash mismatch')
        for feature in read_json(raw, compressed=True).get('features', []):
            identity = feature.get('id')
            if identity in EXPECTED_COMPONENTS:
                if identity in components:
                    raise ValueError('Duplicate target component identity')
                components[identity] = feature
    if set(components) != set(EXPECTED_COMPONENTS):
        raise ValueError('Complete component roster is not present in pinned custody')

    source_descriptor = config['retained_sources'][0]
    source_raw = read_bounded_packet_file(ROOT / source_descriptor['path'])
    if len(source_raw) != source_descriptor['bytes'] or sha256(source_raw) != source_descriptor['sha256']:
        raise ValueError('Retained DOSM source bytes differ from input-config pin')
    license_raw = read_bounded_packet_file(ROOT / source_descriptor['license_path'])
    if len(license_raw) != source_descriptor['license_bytes'] or sha256(license_raw) != source_descriptor['license_sha256']:
        raise ValueError('Retained DOSM license bytes differ from input-config pin')
    product = validate_source_bytes(source_raw, source_descriptor)
    districts = index_districts(product['features'])
    controls = run_loader_controls(source_raw, source_descriptor, product['features'])
    controls['negative'].extend(run_output_path_controls())
    controls['negative'].append({
        'control': 'mutated pinned imported helper rejected by immutable baseline loader',
        'passed': modules['_helper_mutation_control']['passed'],
    })
    family = family_record(pin)
    scope_controls = run_scope_loader_controls(list(components), family['original_fine_family']['contact_ids'],
                                               family['numeric_closure_component_ids'])
    controls['positive'].extend(scope_controls['positive'] if isinstance(scope_controls['positive'], list)
                                else [scope_controls['positive']])
    controls['negative'].extend(scope_controls['negative'])
    geometry_controls = run_geometry_predicate_controls()
    controls['positive'].append(geometry_controls['positive'])
    controls['negative'].append(geometry_controls['negative'])
    atlas = read_json(pin.pinned_bytes(ATLAS))
    atlas_features = {f.get('id') or (f.get('properties') or {}).get('id'): f for f in atlas['features']}
    gb_product = read_json(pin.pinned_bytes(GEObOUNDARIES), compressed=True)
    gb_name_by_id = {}
    for feature in gb_product.get('features', []):
        props = feature.get('properties') or {}
        shape_id, shape_name = props.get('shapeID'), props.get('shapeName')
        if isinstance(shape_id, str) and shape_id:
            if shape_id in gb_name_by_id:
                raise ValueError('Duplicate pinned geoBoundaries shapeID')
            gb_name_by_id[shape_id] = shape_name
    crosswalk_controls = run_contact_crosswalk_controls(atlas_features, districts, gb_name_by_id)
    controls['positive'].append(crosswalk_controls['positive'])
    controls['negative'].append(crosswalk_controls['negative'])
    national_index = index_product(product['features'])
    all_source_geometries = {
        code: (state, name, shape(feature['geometry']))
        for code, (state, name, feature) in national_index.items()
    }
    all_source_validity = {code: bool(row[2].is_valid) for code, row in all_source_geometries.items()}
    all_source_valid = all(all_source_validity.values())
    source_union = unary_union([row[2] for row in all_source_geometries.values()]) if all_source_valid else None
    district_geometries = {name: shape(feature['geometry']) for name, feature in districts.items()}
    district_validity = {name: bool(geom.is_valid) for name, geom in district_geometries.items()}

    contacts = []
    for name, identity in CONTACT_NAME_TO_ID.items():
        source_feature = districts[name]
        current = atlas_features.get(identity)
        if current is None:
            raise ValueError('A scoped current Atlas contact is absent')
        source_geom = district_geometries[name]
        atlas_geom = shape(current['geometry'])
        contacts.append({
            'district_name': name,
            'source_code': DISTRICT_CODES[name],
            'current_contact_id': identity,
            'source_feature_sha256': sha256(canonical(source_feature)),
            'source_geometry_sha256': sha256(canonical(source_feature['geometry'])),
            'current_atlas_geometry_sha256': sha256(canonical(current['geometry'])),
            'source_geometry_valid': district_validity[name],
            'atlas_geometry_valid': bool(atlas_geom.is_valid),
            'topologically_equal': bool(source_geom.equals(atlas_geom)) if district_validity[name] and atlas_geom.is_valid else None,
            'coordinate_order_equal': source_feature['geometry'] == current['geometry'],
        })

    component_rows = []
    for identity in EXPECTED_COMPONENTS:
        feature = components[identity]
        component_geom = shape(feature['geometry'])
        if not component_geom.is_valid:
            raise ValueError('Invalid preserved component geometry; no repair is performed')
        intersects, positive = [], []
        for source_code, (state, district_name, district_geom) in all_source_geometries.items():
            if not all_source_validity[source_code]:
                continue
            predicates = component_source_predicates(component_geom, district_geom)
            if predicates['intersects']:
                intersects.append({'state': state, 'district': district_name, 'code': source_code})
                if predicates['positive_coordinate_plane_area']:
                    positive.append({'state': state, 'district': district_name, 'code': source_code})
        component_rows.append({
            'id': identity,
            'geometry_sha256': sha256(canonical(feature['geometry'])),
            'fragment_binding_count': len(feature['properties']['fragment_bindings']),
            'intersecting_valid_dosm_feature_keys': intersects,
            'positive_coordinate_plane_intersection_area_sign_feature_keys': positive,
            'covered_by_complete_valid_dosm_union': bool(source_union.covers(component_geom)) if source_union is not None else None,
            'dosm_union_coverage_assessed': source_union is not None,
        })

    code_paths = ('scripts/evidence/immutable.py', 'scripts/physical_component_custody.py')
    script_path = pathlib.Path(__file__).resolve().relative_to(ROOT).as_posix()
    result = {
        'version': 2,
        'issue': 1408,
        'family_id': FAMILY_ID,
        'baseline_commit': config['baseline']['commit'],
        'evidence_manifest_sha256': evidence_manifest_sha256,
        'evidence_manifest_snapshot_base64': base64.b64encode(manifest_raw).decode('ascii'),
        'operational_batch': family['operational_batch'],
        'source': {
            'id': source_descriptor['id'],
            'repository_commit': source_descriptor['repository_commit'],
            'repository_path': source_descriptor['source_path'],
            'repository_blob': source_descriptor['repository_blob'],
            'retained_path': source_descriptor['path'],
            'bytes': len(source_raw),
            'sha256': sha256(source_raw),
            'license_path': source_descriptor['license_path'],
            'license_sha256': sha256(license_raw),
            'feature_count': len(product['features']),
            'crs': source_descriptor['crs'],
            'scope_districts': [{'name': name, 'code': DISTRICT_CODES[name], 'geometry_valid': district_validity[name]}
                                for name in DISTRICT_CODES],
            'full_product_invalid_feature_count': sum(not valid for valid in all_source_validity.values()),
            'role': source_descriptor['role'],
        },
        'rosters': {
            'component_ids': EXPECTED_COMPONENTS,
            'contact_ids': [CONTACT_NAME_TO_ID[n] for n in CONTACT_NAME_TO_ID],
            'numeric_closure_component_ids': NUMERIC_CLOSURE_IDS,
        },
        'whole_file_custody_validation': custody_validation,
        'contacts': contacts,
        'components': component_rows,
        'predicate_summary': {
            'components_intersecting_any_valid_dosm_feature': sum(bool(row['intersecting_valid_dosm_feature_keys']) for row in component_rows),
            'total_component_feature_intersections': sum(len(row['intersecting_valid_dosm_feature_keys']) for row in component_rows),
            'components_covered_by_complete_valid_dosm_union': sum(row['covered_by_complete_valid_dosm_union'] is True for row in component_rows),
            'components_not_covered_by_complete_valid_dosm_union': sum(row['covered_by_complete_valid_dosm_union'] is False for row in component_rows),
            'components_with_union_coverage_unassessed_due_invalid_source': sum(row['covered_by_complete_valid_dosm_union'] is None for row in component_rows),
            'coordinate_plane_intersection_area_sign_predicate_used': True,
            'numeric_area_values_or_dry_land_area_reported': False,
            'classification_or_ownership_inferred': False,
        },
        'controls': controls,
        'code_bindings': {
            'producer_path': script_path,
            'producer_sha256': sha256(read_bounded_packet_file(ROOT / script_path)),
            'baseline_helpers': [{'path': path, 'sha256': pins[path]['sha256'], 'bytes': pins[path]['bytes']} for path in code_paths],
            'helper_loading': 'Authenticated baseline immutable helper bootstrap; executed helper graph loaded via Baseline.load_modules.',
        },
        'runtime': {
            'python_executable': sys.executable,
            'python_version': sys.version,
            'shapely_version': shapely.__version__,
            'geos_version': shapely.geos_version_string,
            'runtime_files': [
                {'role': 'python-executable', **file_fingerprint(sys.executable)},
                {'role': 'shapely-geos-extension', **file_fingerprint(shapely_lib.__file__)},
            ],
            'loaded_shapely_modules': loaded_shapely_module_fingerprints(),
        },
        'limits': [
            'DOSM file is a separate published comparator; its name geo_2_district_simp2 signals a simplified product, but source lineage, geometry vintage, accuracy, and third-party-rights details are not documented.',
            'DOSM Open Data License permits reuse subject to its exclusions; this run does not imply official endorsement or settle third-party rights.',
            'The historical MyGOS response is absent; its Besut validity and overlays remain preliminary and are not restored by this source.',
            'The positive-intersection diagnostic uses intersection(...).area > 0 as a Boolean in CRS84 coordinates. No numeric area/distance or physical-area claim is reported.',
            'Physical land/water class, legal authority/effective date, registration accuracy, cause, and rightful ownership remain unknown.',
            'All three numeric-closure components remain in the frozen cohort with their original unknown status.',
        ],
    }
    out = safe_fresh_output_path(output_path)
    exclusive_write(out, canonical(result))
    return result


def write_execution_receipt(output_path, receipt_path, argv, start_time):
    output_raw = (ROOT / output_path).read_bytes()
    output_data = json.loads(output_raw)
    try:
        head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    except Exception:
        head = None
    receipt = {
        'version': 1,
        'issue': 1408,
        'run_kind': 'fresh-source-comparison',
        'run_id': sha256((start_time + '\0' + output_path + '\0' + sha256(output_raw)).encode())[:24],
        'argv': argv,
        'git_head_at_execution': head,
        'evidence_manifest_sha256': output_data['evidence_manifest_sha256'],
        'started_at_utc': start_time,
        'ended_at_utc': datetime.now(timezone.utc).isoformat(),
        'python_executable': sys.executable,
        'python_version': sys.version,
        'runtime': output_data['runtime'],
        'output_path': output_path,
        'output_bytes': len(output_raw),
        'output_sha256': sha256(output_raw),
        'producer_path': pathlib.Path(__file__).resolve().relative_to(ROOT).as_posix(),
        'producer_sha256': sha256(read_bounded_packet_file(pathlib.Path(__file__))),
        'status': 'completed',
    }
    target = safe_fresh_output_path(receipt_path)
    exclusive_write(target, canonical(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    output_path = safe_output_relative_path(args.output)
    receipt_path = safe_output_relative_path(args.receipt)
    if pathlib.PurePosixPath(output_path).parent != pathlib.PurePosixPath(receipt_path).parent:
        raise SystemExit('Run and receipt must share one fresh DOSM vintage directory')
    output_name = pathlib.PurePosixPath(output_path).name
    receipt_name = pathlib.PurePosixPath(receipt_path).name
    expected_receipt = {'run-one.json': 'execution-one.json', 'run-two.json': 'execution-two.json'}
    if expected_receipt.get(output_name) != receipt_name:
        raise SystemExit('Run and execution receipt filenames must correspond')
    # Admit both destinations before any packet/source read or geometry work.
    validate_output_admission(output_path)
    validate_output_admission(receipt_path)
    vintage_dir = ROOT / pathlib.PurePosixPath(output_path).parent
    if vintage_dir.exists() and (vintage_dir.is_symlink() or not vintage_dir.is_dir()):
        raise SystemExit('Vintage parent must be an ordinary non-symlink directory')
    existing = set(x.name for x in vintage_dir.iterdir()) if vintage_dir.exists() else set()
    allowed_progress = {'run-one.json', 'execution-one.json'}
    if existing and (existing != allowed_progress or output_name != 'run-two.json'):
        raise SystemExit('Vintage is not fresh or the first run is incomplete')
    started = datetime.now(timezone.utc).isoformat()
    result = reproduce(output_path)
    receipt = write_execution_receipt(output_path, receipt_path, sys.argv, started)
    print(json.dumps({'status': 'completed', 'result_sha256': sha256(canonical(result)),
                      'receipt_sha256': sha256(canonical(receipt))}, sort_keys=True))


if __name__ == '__main__':
    main()
