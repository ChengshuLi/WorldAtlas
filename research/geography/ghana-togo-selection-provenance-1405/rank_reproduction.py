#!/usr/bin/env python3
"""Reproduce the retained Ghana–Togo family selection from pinned records."""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ISSUE = 1553
WORKER = '01a10947-b3d7-7812-8b2f-c5a47e88ccb2'
OWNED = 'research/geography/ghana-togo-selection-provenance-1405/'
ISSUE_BASE = '4a78e95a96a3a12f3baca85f948eb67a5f924b1f'
ROUTING_BASE = 'd51c43e878c797d215ba5bd8285571fa14add443'
NATIVE_CODE = 'cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
NATIVE_EXECUTION_REPORTED = 'c9be3365bec68b553e1c003f5efc44d945dab2b6'
HELPER_CODE = '7110932cd2bcab7c2e03cadcda8eb02aa118eb9b'
HELPER_PATH = 'scripts/evidence/immutable.py'
RANKER_PATH = 'scripts/physical_gap_priority.py'
NATIVE_REPORT = 'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json'
NATIVE_MANIFEST = 'coordination/engineering/worldwide-native-batches-1184-20261006/evidence-quality.json'
ROUTING_MANIFEST = 'research/geography/ghana-togo-complete-family-source-fitness-20261007/evidence-quality.json'
LAND_PATH = 'coordination/engineering/global-actionability-routing-20261007/results/land-source-fitness-000.bin.gz'
RANK_ROOT = 'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/'
FAMILY_ROOT = 'coordination/engineering/global-actionability-routing-20261007/results/'
SELECTION_AUDIT = 'research/geography/ghana-togo-complete-family-source-fitness-20261007/selection-audit.json'
FAMILY_HANDOFF = 'research/geography/ghana-togo-complete-family-source-fitness-20261007/family-handoff.json'
DATA_COMMIT_FILES = {
    'research/geography/ghana-togo-complete-family-source-fitness-20261007/README.md': 'ea54758f2272a7d7836dce8ba191c996694bca8e4af8eb0604eee72bc31c7710',
    'research/geography/ghana-togo-complete-family-source-fitness-20261007/claim-receipt.json': '8733a89e5579437cb98ff70cb04fdc9ea762a589af77cb7538179835eb249934',
    ROUTING_MANIFEST: '07643c6f699e343c707b9b9a5738f9c9998c75e3bdbc39d39193ee6e7ec5b8c7',
    FAMILY_HANDOFF: 'b95293cd0a6b2afd062fc0fda8121f6098c0e7e10250af563b35d840c91c373e',
    SELECTION_AUDIT: '200c18840963a6cabfd81c96b085dccf80b721902c65764fe2471a3c1cfe3787',
    RANK_ROOT + 'current-rank-positions-000.json.gz': 'da5ea9cb223174c090947785f5ec1c84ba2f72fa3bcad85bdaa9f3409640ec54',
    RANK_ROOT + 'current-rank-positions-001.json.gz': 'af3d28d483b9eb01d1c7c4db51e699ae32bba03bad2938ff6d723f419335e2a4',
    RANK_ROOT + 'current-rank-positions-002.json.gz': '5e45d4924be44c9d0ab5d619db94a8a65940967554f4d809de6deb034d1ea81a',
    RANK_ROOT + 'current-rank-positions-003.json.gz': '6d6b5dec8b4650a67ab8abbff80619d14023278a42ba98fce01e8ac0f76c6b3a',
    RANK_ROOT + 'current-rank-positions-004.json.gz': 'bcf7bde1699392d69dc4b6e4dc92de5043312773be05d065f36f4d38d151ac98',
    NATIVE_MANIFEST: 'b1069d432b21146451a560dd75c152968274af683cf551e2f65ae03395096384',
    LAND_PATH: '98382c95655a927c4075e7de5c8aa5204980340d001cfb28d9993823cc3d8476',
    'data/geography/part-9.json': '9a3bd8c8846cad2cd4ff681cf1f9341b876fdba4041214c52dcefecb5918aba6',
    'data/geography/part-23.json': 'd61082ccd69b319723fadc4cad582b8d5c8a8ced3e50b4f90f00b4eb17e6a9c2',
}
SUBJECTS = [
    'gb:GHA:ADM2:2480657B35240131522033',
    'gb:GHA:ADM2:2480657B47242267083805',
    'gb:TGO:ADM2:56601680B4042875560778',
    'gb:TGO:ADM2:56601680B98633254865748',
]
COMPONENTS = [
    'physical-component:01c3bef8e5c4dceec102c248a9f7db86d7a6bcfbdb322d493704dcd3903912c3',
    'physical-component:06dc16bf3ee20625d3efb70f8f94afa061a476eb1d83eb3ddbd7bcf9495a28fc',
    'physical-component:0a149a1adf1f22badf1c73d3ff5d1960f7dd5a6be8dbed0f6e68d20e1cea7cdd',
    'physical-component:100033d5f179136790f2bc870beca47f18b0dd6459018b7d5db1916cdc21030a',
    'physical-component:9124722a82606c8db57df20583a15739055eab7f62eda2346640080bc7137b7f',
    'physical-component:dbd76c808ddc0bf725ad6085fce94ba4fe23beb60eef0deeb6509d6c0a334f87',
]
FAMILY = 'gap-source-batch:836f0998d0d7b82bd3486750'
SELECTED_COMPONENT = 'physical-component:06dc16bf3ee20625d3efb70f8f94afa061a476eb1d83eb3ddbd7bcf9495a28fc'
RANK_FIELDS = ('source_locator_readiness', 'measured_impact', 'coordination_complexity')
RUNTIME_RESERVE = 33_554_432
MAX_FILE = 32 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_size(repo: Path, commit: str, path: str) -> int:
    return int(subprocess.check_output(['git', '-C', str(repo), 'cat-file', '-s', f'{commit}:{path}']))


def git_descriptor(repo: Path, commit: str, path: str, digest: str, **extra) -> dict:
    return {'path': path, 'bytes': git_size(repo, commit, path), 'sha256': digest,
            'hash_kind': 'file-bytes', **extra}


def capped_gunzip(raw: bytes, expected_bytes: int, expected_sha: str) -> bytes:
    if expected_bytes > MAX_FILE:
        raise ValueError('Declared decoded input exceeds the single-file cap')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        decoded = stream.read(MAX_FILE + 1)
    if len(decoded) != expected_bytes or sha(decoded) != expected_sha:
        raise ValueError('Decoded gzip bytes disagree with their authenticated descriptor')
    return decoded


def load_array(raw: bytes, count: int, label: str) -> list:
    value = json.loads(raw)
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f'{label}: array/record-count mismatch')
    return value


def rank_tuple(record: dict) -> tuple[int, int, int]:
    positions = record.get('rank_positions')
    if not isinstance(positions, dict) or any(type(positions.get(key)) is not int for key in RANK_FIELDS):
        raise ValueError('Incomplete native rank tuple')
    return tuple(positions[key] for key in RANK_FIELDS)


def derive(eligible_rows: list[dict], native_rows: list[dict]) -> dict:
    # Check raw identities before making either index.
    eligible_components = [row.get('component') for row in eligible_rows]
    native_components = [row.get('component') for row in native_rows]
    if any(not isinstance(value, str) or not value for value in eligible_components + native_components):
        raise ValueError('Missing component identity')
    if len(eligible_components) != len(set(eligible_components)):
        raise ValueError('Duplicate eligible component identity')
    if len(native_components) != len(set(native_components)):
        raise ValueError('Duplicate native component identity')
    native = {row['component']: row for row in native_rows}
    grouped: dict[str, list[tuple[tuple[int, int, int], str]]] = {}
    for row in eligible_rows:
        family = row.get('family')
        candidate = native.get(row['component'])
        if not isinstance(family, str) or not family.startswith('gap-source-batch:'):
            raise ValueError('Invalid eligible family identity')
        if candidate is None:
            raise ValueError('Missing native rank for eligible component')
        if candidate.get('actionable_batch_id') != family:
            raise ValueError('Native actionable family does not match eligibility row')
        grouped.setdefault(family, []).append((rank_tuple(candidate), row['component']))
    minima = {family: min(rows, key=lambda item: (item[0], item[1]))
              for family, rows in grouped.items()}
    ordered = sorted(minima.items(), key=lambda item: (item[1][0], item[0]))
    matches = [(position, family, tuple_value, component)
               for position, (family, (tuple_value, component)) in enumerate(ordered, 1)
               if family == FAMILY]
    if len(matches) != 1:
        raise ValueError('Target family is missing or duplicated in eligible ranking')
    position, family, selected_tuple, selected_component = matches[0]
    return {
        'eligible_row_count': len(eligible_rows),
        'eligible_family_count': len(grouped),
        'family_tie_count': len(ordered) - len({value[1][0] for value in ordered}),
        'within_family_tie_count': sum(len(rows) - len({value[0] for value in rows}) for rows in grouped.values()),
        'selected': {
            'family_id': family,
            'eligible_component_id': selected_component,
            'rank_tuple_order': list(RANK_FIELDS),
            'rank_tuple': list(selected_tuple),
            'family_position_one_based': position,
            'ranked_family_count': len(ordered),
        },
    }


def expect_rejected(name: str, eligible: list, native: list, phrase: str) -> dict:
    try:
        derive(eligible, native)
    except ValueError as error:
        if phrase not in str(error):
            raise AssertionError(f'{name}: wrong rejection: {error}') from error
        return {'id': name, 'status': 'rejected-as-required', 'reason': str(error)}
    raise AssertionError(f'{name}: invalid records were accepted')


def family_stream(repo: Path, helper, routing_manifest: dict, main_baseline, eligible_count: int) -> tuple[dict, list]:
    commit = routing_manifest['baseline']['commit']
    descriptors = [item for item in routing_manifest['baseline']['files']
                   if re.fullmatch(re.escape(FAMILY_ROOT) + r'families-\d{3}\.bin\.gz', item['path'])]
    descriptors.sort(key=lambda item: item['path'])
    if len(descriptors) != 14 or [item['path'] for item in descriptors] != [FAMILY_ROOT + f'families-{n:03d}.bin.gz' for n in range(14)]:
        raise ValueError('Complete original family record stream is not pinned')
    if commit != ROUTING_BASE:
        raise ValueError('Original family source manifest vintage changed')
    # Admit raw and decoded bytes into the same phase before secondary reads/decompression.
    for item in descriptors:
        main_baseline.admit(f'versioned/{commit}/{item["path"]}', item['bytes'])
        main_baseline.admit(f'decoded/{commit}/{item["path"]}', item['uncompressed_bytes'])
    auxiliary = helper.Baseline(repo, commit, descriptors)
    seen = set()
    found = None
    carry = b''
    total = 0
    part_starts = []
    for item in descriptors:
        raw = auxiliary.pinned_bytes(item['path'])
        decoded = capped_gunzip(raw, item['uncompressed_bytes'], item['uncompressed_sha256'])
        part_starts.append((item['path'], total, total + len(decoded)))
        combined = carry + decoded
        base_offset = total - len(carry)
        lines = combined.splitlines(keepends=True)
        carry = b''
        cursor = base_offset
        for line in lines:
            if not line.endswith(b'\n'):
                carry = line
                break
            record_bytes = line[:-1]
            if record_bytes:
                record = json.loads(record_bytes)
                identity = record.get('id')
                if not isinstance(identity, str) or not identity.startswith('gap-source-batch:'):
                    raise ValueError('Malformed original fine-family record identity')
                if identity in seen:
                    raise ValueError('Duplicate original fine-family identity')
                seen.add(identity)
                if identity == FAMILY:
                    found = {'record': record, 'global_offset': cursor, 'record_bytes': len(line),
                             'record_sha256': sha(line)}
            cursor += len(line)
        total += len(decoded)
    if carry:
        raise ValueError('Original concatenated family stream ends in a partial record')
    if len(seen) != 15_610:
        raise ValueError('Unexpected original family stream record count')
    if found is None:
        raise ValueError('Target original fine-family row is absent')
    offset, end = found['global_offset'], found['global_offset'] + found['record_bytes']
    spans = []
    for path, start, stop in part_starts:
        left, right = max(offset, start), min(end, stop)
        if left < right:
            spans.append({'path': path, 'decoded_start_byte': left - start, 'bytes': right - left})
    found['record_source_spans'] = spans
    found['whole_stream_decoded_bytes'] = total
    return found, descriptors


def verify_subjects(parts: dict[str, bytes]) -> list[dict]:
    found = []
    for path, raw in parts.items():
        data = json.loads(raw)
        features = data.get('features')
        if not isinstance(features, list):
            raise ValueError('Subject part is not a feature collection')
        ids = [(feature.get('id') or feature.get('properties', {}).get('id')) for feature in features]
        if any(not isinstance(value, str) for value in ids) or len(ids) != len(set(ids)):
            raise ValueError('Subject part contains missing/duplicate native identities')
        by_id = {identity: feature for identity, feature in zip(ids, features)}
        for identity in SUBJECTS:
            if identity not in by_id:
                continue
            properties = by_id[identity].get('properties', {})
            found.append({'id': identity, 'name': properties.get('name'),
                          'parent_id': properties.get('parent_id'), 'containing_file': path})
    if sorted(row['id'] for row in found) != sorted(SUBJECTS):
        raise ValueError('Pinned geography parts do not contain exactly the declared four contact subjects')
    return sorted(found, key=lambda item: item['id'])


def run(repo: Path, vintage: str) -> list[dict]:
    # The project helper is loaded from exact current-base bytes, then its pinned copy
    # is used for every immutable reader and exclusive output publication.
    helper_file = repo / HELPER_PATH
    code_commit = HELPER_CODE
    code_bytes = subprocess.check_output(['git', '-C', str(repo), 'show', f'{code_commit}:{HELPER_PATH}'])
    working_helper = helper_file.read_bytes()
    if working_helper != code_bytes or sha(code_bytes) != 'a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46':
        raise ValueError('Working execution helper differs from the exact pinned base helper bytes')
    sys.path.insert(0, str(repo))
    bootstrap = importlib.import_module('scripts.evidence.immutable')
    helper_descriptor = {'path': HELPER_PATH, 'bytes': len(code_bytes), 'sha256': sha(code_bytes), 'hash_kind': 'file-bytes'}
    bootstrap_baseline = bootstrap.Baseline(repo, code_commit, [helper_descriptor])
    helper = bootstrap_baseline.load_modules({'immutable': HELPER_PATH})['immutable']

    inputs = [git_descriptor(repo, ISSUE_BASE, path, digest)
              for path, digest in DATA_COMMIT_FILES.items()]
    baseline = helper.Baseline(repo, ISSUE_BASE, inputs)
    original_manifest = json.loads(baseline.pinned_bytes(ROUTING_MANIFEST))
    native_manifest = json.loads(baseline.pinned_bytes(NATIVE_MANIFEST))
    selection_audit = json.loads(baseline.pinned_bytes(SELECTION_AUDIT))
    handoff = json.loads(baseline.pinned_bytes(FAMILY_HANDOFF))
    if original_manifest.get('baseline', {}).get('commit') != ROUTING_BASE:
        raise ValueError('Original routing evidence manifest does not bind the declared snapshot')
    if sorted(handoff['scope']['contact_ids']) != sorted(SUBJECTS) or sorted(handoff['scope']['component_ids']) != sorted(COMPONENTS):
        raise ValueError('Original six-component/four-contact scope changed')

    family_descriptors = [item for item in original_manifest['baseline']['files']
                          if re.fullmatch(re.escape(FAMILY_ROOT) + r'families-\d{3}\.bin\.gz', item['path'])]
    land_descriptor = next((item for item in original_manifest['baseline']['files'] if item['path'] == LAND_PATH), None)
    native_report_descriptor = next((item for item in native_manifest.get('outputs', []) if item['path'] == NATIVE_REPORT), None)
    rank_descriptors = [item for item in native_manifest.get('outputs', [])
                        if item['path'].startswith(RANK_ROOT + 'current-rank-positions-')]
    rank_descriptors.sort(key=lambda item: item['path'])
    if land_descriptor is None or land_descriptor['sha256'] != DATA_COMMIT_FILES[LAND_PATH]:
        raise ValueError('Land-source eligibility record is not bound to the original routing manifest')
    expected_rank_paths = [RANK_ROOT + f'current-rank-positions-{n:03d}.json.gz' for n in range(5)]
    if [item['path'] for item in rank_descriptors] != expected_rank_paths:
        raise ValueError('Complete five-file native rank inventory is not bound')
    for item in rank_descriptors:
        if item['sha256'] != DATA_COMMIT_FILES[item['path']]:
            raise ValueError('Native rank output descriptor differs from the exact issue pin')
    if native_report_descriptor is None:
        raise ValueError('Exact native rank execution report is absent from its evidence manifest')

    # Aggregate every source, code, decoded input and runtime reserve in one byte phase.
    for item in family_descriptors:
        baseline.admit(f'versioned/{ROUTING_BASE}/{item["path"]}', item['bytes'])
        baseline.admit(f'decoded/{ROUTING_BASE}/{item["path"]}', item['uncompressed_bytes'])
    baseline.admit(f'versioned/{ROUTING_BASE}/{LAND_PATH}', land_descriptor['bytes'])
    baseline.admit(f'decoded/{ROUTING_BASE}/{LAND_PATH}', land_descriptor['uncompressed_bytes'])
    for item in rank_descriptors:
        baseline.admit(f'decoded/{ISSUE_BASE}/{item["path"]}', item['uncompressed_bytes'])
    baseline.admit(f'versioned/{ISSUE_BASE}/{NATIVE_REPORT}', native_report_descriptor['bytes'])
    baseline.admit(f'code/{code_commit}/{HELPER_PATH}', len(code_bytes))
    ranker_descriptor = git_descriptor(repo, NATIVE_CODE, RANKER_PATH,
        '26ff1467cef85a0a30c21334ad9c2a6be4a0d635bae50ca4940086853773ab28')
    native_helper_descriptor = git_descriptor(repo, NATIVE_CODE, HELPER_PATH,
        'b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd')
    for descriptor in (ranker_descriptor, native_helper_descriptor):
        baseline.admit(f'code/{NATIVE_CODE}/{descriptor["path"]}', descriptor['bytes'])
    script_bytes = Path(__file__).read_bytes()
    baseline.admit('code/candidate/rank_reproduction.py', len(script_bytes))
    baseline.admit('runtime/python-object-and-result-reserve', RUNTIME_RESERVE)

    # Destination is admitted before decompression, computation, or control probes.
    destination = helper.NewVintage(baseline, OWNED, vintage,
                                    ['selection-reproduction.json', 'adverse-controls.json'])
    auxiliary = helper.Baseline(repo, ROUTING_BASE, family_descriptors + [land_descriptor])
    ranker_source = helper.Baseline(repo, NATIVE_CODE, [ranker_descriptor, native_helper_descriptor])
    ranker_bytes = ranker_source.pinned_bytes(RANKER_PATH)
    native_helper_bytes = ranker_source.pinned_bytes(HELPER_PATH)
    if b'for rank, record in enumerate(sorted(records' not in ranker_bytes or b'ORDER_NAMES' not in ranker_bytes:
        raise ValueError('Pinned native rank generator does not expose its total-order enumeration')
    if b'class Baseline:' not in native_helper_bytes:
        raise ValueError('Pinned native-rank helper is unexpected')
    report_bytes = helper.Baseline(repo, ISSUE_BASE, [native_report_descriptor]).pinned_bytes(NATIVE_REPORT)
    native_report = json.loads(report_bytes)
    if native_report.get('executed_code_commit') != NATIVE_EXECUTION_REPORTED or RANKER_PATH not in native_report.get('executed_project_modules', []):
        raise ValueError('Native rank execution report does not bind the rank producer vintage')

    # Verify all issue-declared raw input pins, then reserve exact decoded lengths before inflate.
    raw_by_path = {path: baseline.pinned_bytes(path) for path in DATA_COMMIT_FILES}
    for path in (LAND_PATH, *expected_rank_paths):
        item = land_descriptor if path == LAND_PATH else next(x for x in rank_descriptors if x['path'] == path)
        baseline.admit(f'decoded/{ISSUE_BASE}/{path}', item['uncompressed_bytes'])
    land_bytes = capped_gunzip(raw_by_path[LAND_PATH], land_descriptor['uncompressed_bytes'], land_descriptor['uncompressed_sha256'])
    land_rows = load_array(land_bytes, 1005, 'land-source-fitness roster')
    native_rows = []
    rank_raw = {}
    for item in rank_descriptors:
        raw = raw_by_path[item['path']]
        decoded = capped_gunzip(raw, item['uncompressed_bytes'], item['uncompressed_sha256'])
        rank_raw[item['path']] = decoded
        shard = json.loads(decoded)
        if not isinstance(shard, list):
            raise ValueError('Native rank shard is not an array')
        native_rows.extend(shard)
    if len(native_rows) != 95_173:
        raise ValueError('Complete native rank row count differs from the retained total')
    for field in RANK_FIELDS:
        positions = [rank_tuple(row)[RANK_FIELDS.index(field)] for row in native_rows]
        if set(positions) != set(range(len(native_rows))):
            raise ValueError(f'Native {field} positions are not a complete unique total order')
    result = derive(land_rows, native_rows)
    result['native_rank_component_count'] = len(native_rows)
    selected = result['selected']
    if result['eligible_row_count'] != 1005 or result['eligible_family_count'] != 711:
        raise ValueError('Eligible roster or family count differs from the exact routing snapshot')
    if (selected['family_position_one_based'], selected['ranked_family_count'], selected['eligible_component_id'], selected['rank_tuple']) != (30, 711, SELECTED_COMPONENT, [2457, 94832, 52630]):
        raise ValueError('Derived current eligible ranking differs from the issue’s observed expected tuple')
    if result['family_tie_count'] != 0:
        raise ValueError('Unexpected cross-family rank-tuple tie requires a reviewed tie policy')

    original = selection_audit['selected']
    original_tuple = original['eligible_row_rank_positions']
    broader = original['family_best_rank']
    if original['family_id'] != FAMILY or original['family_rank_position'] != selected['family_position_one_based'] or original['total_ranked_families'] != selected['ranked_family_count']:
        raise ValueError('Original family identity/position/count does not reconcile')
    family_record, family_files = family_stream(repo, helper, original_manifest, baseline, result['eligible_family_count'])
    original_family = family_record['record'].get('original_fine_family', {})
    best = original_family.get('best_rank')
    if best != broader:
        raise ValueError('Broader original-family best tuple differs from the immutable complete family record')
    if sorted(original_family.get('component_ids', [])) != sorted(COMPONENTS) or sorted(original_family.get('contact_ids', [])) != sorted(SUBJECTS):
        raise ValueError('Immutable original family record changed its complete subject roster')
    subjects = verify_subjects({
        'data/geography/part-9.json': raw_by_path['data/geography/part-9.json'],
        'data/geography/part-23.json': raw_by_path['data/geography/part-23.json'],
    })

    # Negative controls: exercise the same consumed-record derivation and whole-byte pin boundary.
    missing_native = [row for row in native_rows if row['component'] != SELECTED_COMPONENT]
    duplicate_native = native_rows + [copy.deepcopy(next(row for row in native_rows if row['component'] == SELECTED_COMPONENT))]
    duplicate_eligible = land_rows + [copy.deepcopy(land_rows[0])]
    controls = [
        expect_rejected('missing-native-rank', land_rows, missing_native, 'Missing native rank'),
        expect_rejected('duplicate-native-component', land_rows, duplicate_native, 'Duplicate native component'),
        expect_rejected('duplicate-eligible-component', duplicate_eligible, native_rows, 'Duplicate eligible component'),
    ]
    peer = next(row for row in native_rows if row['rank_positions']['measured_impact'] == 94833)
    changed_native = [dict(row) for row in native_rows]
    by_component = {row['component']: row for row in changed_native}
    for component, new_rank in ((SELECTED_COMPONENT, 94833), (peer['component'], 94832)):
        changed = dict(by_component[component])
        changed['rank_positions'] = dict(changed['rank_positions'])
        changed['rank_positions']['measured_impact'] = new_rank
        by_component[component] = changed
    changed_native = list(by_component.values())
    changed_result = derive(land_rows, changed_native)
    if changed_result['selected']['rank_tuple'] == selected['rank_tuple']:
        raise AssertionError('Coherent ordinal-swap control did not change the selected native tuple')
    for path, raw in rank_raw.items():
        changed = raw
        for component in (SELECTED_COMPONENT, peer['component']):
            if re.search(rb'"component":"' + re.escape(component.encode()) + rb'"', changed):
                pattern = re.compile(rb'(\{"actionable_batch_id":"[^"]+","component":"' +
                    re.escape(component.encode()) + rb'"[^\{]*"rank_positions":\{"coordination_complexity":\d+,"measured_impact":)(\d+)(,"source_locator_readiness":\d+\}\})')
                match = pattern.search(changed)
                if not match:
                    raise AssertionError('Could not construct coherent source-row ordinal control')
                replacement = match.group(1) + (b'94833' if component == SELECTED_COMPONENT else b'94832') + match.group(3)
                changed = changed[:match.start()] + replacement + changed[match.end():]
        rank_desc = next(item for item in rank_descriptors if item['path'] == path)
        if changed != raw and sha(changed) == rank_desc['uncompressed_sha256']:
            raise AssertionError('Changed impact values unexpectedly retained the immutable decoded hash')
    controls.append({
        'id': 'coherently-swapped-impact-ordinals',
        'status': 'changed-result-and-pin-refusal-demonstrated',
        'affected_components': [SELECTED_COMPONENT, peer['component']],
        'original_ordinals': [94832, 94833],
        'mutated_ordinals': [94833, 94832],
        'complete_impact_total_order_retained': True,
        'mutated_selected_tuple': changed_result['selected']['rank_tuple'],
        'immutable_decoded_input_hashes_reject_mutation': True,
        'candidate_outputs_unchanged': True,
    })

    source_pin_records = []
    for item in inputs:
        detail = dict(item)
        detail['commit'] = ISSUE_BASE
        if item['path'] in expected_rank_paths:
            native_descriptor = next(row for row in rank_descriptors if row['path'] == item['path'])
            detail.update(uncompressed_bytes=native_descriptor['uncompressed_bytes'],
                          uncompressed_sha256=native_descriptor['uncompressed_sha256'])
        elif item['path'] == LAND_PATH:
            detail.update(uncompressed_bytes=land_descriptor['uncompressed_bytes'],
                          uncompressed_sha256=land_descriptor['uncompressed_sha256'])
        source_pin_records.append(detail)
    versioned = []
    for item in family_descriptors:
        versioned.append({**{key: item[key] for key in ('path', 'bytes', 'sha256', 'hash_kind', 'uncompressed_bytes', 'uncompressed_sha256')}, 'commit': ROUTING_BASE})
    versioned.append({**{key: land_descriptor[key] for key in ('path', 'bytes', 'sha256', 'hash_kind', 'uncompressed_bytes', 'uncompressed_sha256')}, 'commit': ROUTING_BASE})
    versioned.extend([
        {**ranker_descriptor, 'commit': NATIVE_CODE},
        {**native_helper_descriptor, 'commit': NATIVE_CODE},
        {**helper_descriptor, 'commit': code_commit},
        {**native_report_descriptor, 'commit': ISSUE_BASE},
    ])

    selection_output = {
        'version': 1,
        'status': 'reproduced-limited-ranking-provenance',
        'issue': ISSUE,
        'source_selection_snapshot_commit': ROUTING_BASE,
        'evaluation_commit': ISSUE_BASE,
        'native_rank_execution_commit_reported_by_run': NATIVE_EXECUTION_REPORTED,
        'native_ranker_source_commit_with_matching_pinned_bytes': NATIVE_CODE,
        'ranking': result,
        'stored_native_rank_convention': 'zero-based total-order positions assigned by enumerate in the authenticated native rank producer',
        'family_position_convention': 'one-based family list position; sorted lexicographically by the per-family minimum rank tuple, then family ID',
        'within_family_tie_break': 'rank tuple, then component ID',
        'eligible_row_definition': 'All 1,005 records in the exact land-source-fitness roster; dispatch_ready is a separate source/readiness state and is false for these rows.',
        'original_selection_audit': {
            'previous_eligible_tuple': original_tuple,
            'previous_family_position_one_based': original['family_rank_position'],
            'current_tuple_reproduced_from_native_records': selected['rank_tuple'],
            'impact_position_delta': selected['rank_tuple'][1] - original_tuple[1],
            'broader_original_family_best_rank': broader,
            'broader_tuple_source': 'original complete fine-family record, not the eligible-component tuple used for family selection',
        },
        'original_family_record': {
            'family_id': FAMILY,
            'row_sha256': family_record['record_sha256'],
            'concatenated_uncompressed_offset': family_record['global_offset'],
            'row_bytes_including_newline': family_record['record_bytes'],
            'source_spans': family_record['record_source_spans'],
            'component_ids': COMPONENTS,
            'contact_ids': SUBJECTS,
            'original_best_rank': best,
        },
        'contact_feature_identity': subjects,
        'authenticated_input_files': source_pin_records,
        'versioned_original_family_files': versioned[:len(family_descriptors)],
        'execution': {
            'producer_path': str(Path(__file__).resolve().relative_to(repo)),
            'producer_sha256': sha(script_bytes),
            'evidence_helper_path': HELPER_PATH,
            'evidence_helper_commit': code_commit,
            'evidence_helper_sha256': sha(code_bytes),
            'native_ranker_path': RANKER_PATH,
            'native_ranker_commit': NATIVE_CODE,
            'native_ranker_sha256': sha(ranker_bytes),
            'complete_input_phase_reserved_bytes': sum(baseline.consumed.values()),
            'runtime_result_reserve_bytes': RUNTIME_RESERVE,
        },
        'limits': [
            'The reproduced tuple and position establish retained-data arithmetic only; they do not establish geographic accuracy, boundary authority, source completeness, legal reuse, physical surface, or cause.',
            f'The native run report names execution commit {NATIVE_EXECUTION_REPORTED}, which is not an ancestor of this checkout. The ranker and helper whole-file hashes are independently pinned at ancestor {NATIVE_CODE}; that confirms matching source bytes but does not independently establish the report commit ancestry.',
            'The original 94833 tuple is preserved as historical reporting; no retained historical rank source was found that authenticates 94833 as an alternate vintage.',
            'The original family best-rank tuple is a separate broader statistic and does not select the eligible component tuple.',
        ],
    }
    controls_output = {
        'version': 1,
        'status': 'adverse-controls-passed',
        'issue': ISSUE,
        'controls': controls,
        'control_limits': ['Mutation probes use bounded in-memory copies and do not change any pinned original file.'],
    }
    records = destination.publish({'selection-reproduction.json': selection_output,
                                   'adverse-controls.json': controls_output})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--vintage', required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path(args.repo).resolve(), args.vintage), sort_keys=True))


if __name__ == '__main__':
    main()
