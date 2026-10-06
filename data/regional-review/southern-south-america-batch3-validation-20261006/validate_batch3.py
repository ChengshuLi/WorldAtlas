#!/usr/bin/env python3
"""Reproduce bounded provenance and baseline-record validation for issue #1122."""
from __future__ import annotations

import base64
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
from unittest.mock import patch

from shapely.geometry import shape

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
OWNED = Path('data/regional-review/southern-south-america-batch3-validation-20261006')
OLD = Path('data/regional-review/regional-review-3e9f1d51da6b0a22')
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import Baseline, descriptor, sha256  # noqa: E402

BASELINE_COMMIT = '0799920a604df931acaf4e32c3234da16d665ab5'
UPSTREAM_COMMIT = '9469f09592ced973a3448cf66b6100b741b64c0d'
ISSUE_SNAPSHOT = OWNED / 'source/issue-1122-api-2026-10-06.json'
ISSUE_BODY_SHA256 = '4f16aae0a00ac03b34301d19464539304a686acc8c4cad8fa662fd49b1dcc960'
EXPECTED_PINS = {
    'baseline-hierarchy': '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',
    'baseline-world-index': 'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
    'baseline-part-0': 'bcad5408720e0f50165e794636fd44e02913e5e4649d73c8aa422b94562d32f3',
    'baseline-part-2': '93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf',
    'original-scope': 'a535a3cb46a0530902006caf7d4141bf7e13f321823e9ea8a9e9eb0cb38163df',
    'original-inventory': '4b7a750d43634cf3ec681434f52f1c587ab57746af98accecc6d3647452db7d6',
    'original-comparisons': 'b4fdfc99a2c0cb8143b46fa4f05feea2ac0147d3fe48725bbd94bb0584f030bc',
    'original-assessments': '46c4d893ff18cfe0016a33e930d82089533f82e9c836e3f85a712c77378c6b18',
    'original-summary': 'fb88fc759a67cc4faa7f0ceeeb2fa1766b5037190af3c89005894d463b177838',
    'original-checker': '368817556dca4f97a66cbf4828bb5d2835a24178bcd6c9312e155e84aa0da21d',
}
PIN_PATHS = {
    'baseline-hierarchy': 'data/hierarchy.json',
    'baseline-world-index': 'data/world-index.json',
    'baseline-part-0': 'data/geography/part-0.json',
    'baseline-part-2': 'data/geography/part-2.json',
    'original-scope': str(OLD / 'scope.json'),
    'original-inventory': str(OLD / 'source-inventory.json'),
    'original-comparisons': str(OLD / 'geometry-comparisons.jsonl'),
    'original-assessments': str(OLD / 'location-assessments.jsonl'),
    'original-summary': str(OLD / 'geometry-summary.json'),
    'original-checker': str(OLD / 'check-packet.py'),
}
LFS_EXPECTED = {
    'arg-adm2-geojson': (f'{UPSTREAM_COMMIT}', 'releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2.geojson',
                         'f35dae5a257302dea5bd1549ae135baf82e7ee7491918854c3db9bbdec890177', 69702323),
    'chl-adm3-geojson': (f'{UPSTREAM_COMMIT}', 'releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3.geojson',
                         'f3833ce1965394ae705e3793b50bdd007775b43da604251871deffed04f3bffd', 171783952),
    'arg-adm2-metaData-json': (f'{UPSTREAM_COMMIT}', 'releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2-metaData.json',
                               '17452b82df4498c1b29a4489bd78709cef922b453579b1a47010dfd2524a7ce2', 958),
    'chl-adm3-metaData-json': (f'{UPSTREAM_COMMIT}', 'releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3-metaData.json',
                               '658356bb413f8b284b260360d1309527781e1b0c46027e1ae0a4c58da1c99409', 983),
    'arg-adm2-metaData-txt': (f'{UPSTREAM_COMMIT}', 'releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2-metaData.txt',
                              'bb817b543f9e2b56a597b3114f9a20d35f01dd5090dcc483b8acbad38d4a23a6', 1116),
    'chl-adm3-metaData-txt': (f'{UPSTREAM_COMMIT}', 'releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3-metaData.txt',
                              '6cfbdf4f0d46be517dfef3454e94b3eaf870b77911bb73b93825205464712b34', 1142),
}
EXPECTED_LEGACY_COMPONENT_OMISSIONS = {
    'gb:ARG:ADM2:61730980B63808307170695',
    'gb:ARG:ADM2:61730980B85851407891039',
}


class Invalid(ValueError):
    pass


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_jsonl_bytes(raw, label):
    try:
        return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Invalid(f'{label} is not valid UTF-8 JSONL') from exc


def source_records():
    return read_json(OWNED / 'source/upstream-lfs-pointer-records.json')


def validate_pointer_evidence(records):
    if records.get('version') != 1 or records.get('commit') != UPSTREAM_COMMIT:
        raise Invalid('LFS pointer record uses the wrong format or upstream commit')
    entries = {row.get('id'): row for row in records.get('objects', [])}
    if set(entries) != set(LFS_EXPECTED):
        raise Invalid('LFS pointer roster is incomplete, duplicated or foreign')
    result = []
    source_inventory = json.loads(BASE.read(PIN_PATHS['original-inventory']))
    old_sources = {row['id']: row for row in source_inventory['sources']}
    asserted_by_id = {
        'arg-adm2-geojson': 'geoboundaries-argentina-adm2-v2020',
        'chl-adm3-geojson': 'geoboundaries-chile-adm3-v2020',
    }
    for ident, (commit, path, oid, size) in LFS_EXPECTED.items():
        row = entries[ident]
        if row.get('upstream_commit') != commit or row.get('upstream_path') != path:
            raise Invalid('LFS pointer has a wrong source path or vintage: ' + ident)
        api_path = ROOT / row['response_file']
        api_raw = api_path.read_bytes()
        api = json.loads(api_raw)
        pointer_path = ROOT / row['pointer_file']
        pointer_raw = pointer_path.read_bytes()
        if len(api_raw) != row['response_bytes'] or sha256(api_raw) != row['response_sha256']:
            raise Invalid('Retained GitHub API response hash/size mismatch: ' + ident)
        if api.get('path') != path or api.get('sha') != row.get('github_contents_blob_sha'):
            raise Invalid('GitHub Contents response path/blob differs from pointer record: ' + ident)
        try:
            encoded = base64.b64decode(''.join(api['content'].split()), validate=True)
        except (KeyError, ValueError) as exc:
            raise Invalid('GitHub Contents response has no valid base64 pointer: ' + ident) from exc
        if encoded != pointer_raw or len(pointer_raw) != row['pointer_bytes'] or sha256(pointer_raw) != row['pointer_sha256']:
            raise Invalid('Retained pointer bytes differ from their API response: ' + ident)
        git_blob_sha = hashlib.sha1(b'blob ' + str(len(pointer_raw)).encode() + b'\0' + pointer_raw).hexdigest()
        if git_blob_sha != row.get('github_contents_blob_sha') or row.get('pointer_git_blob_sha_verified') != git_blob_sha:
            raise Invalid('GitHub Git blob SHA does not authenticate pointer bytes: ' + ident)
        text = pointer_raw.decode('ascii')
        match = re.fullmatch(r'version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize (\d+)\n', text)
        if not match or match.group(1) != oid or int(match.group(2)) != size:
            raise Invalid('Pointer-declared LFS object differs from the expected immutable object: ' + ident)
        if row.get('lfs_object_sha256') != oid or row.get('lfs_object_bytes') != size or row.get('raw_lfs_object_downloaded') is not False:
            raise Invalid('Pointer ledger overstates or misstates LFS payload evidence: ' + ident)
        finding = {'id': ident, 'upstream_path': path, 'commit': commit,
                   'authenticated_git_pointer_blob': git_blob_sha, 'pointer_sha256': sha256(pointer_raw),
                   'pointer_bytes': len(pointer_raw), 'lfs_object_sha256': oid, 'lfs_object_bytes': size,
                   'raw_lfs_payload_downloaded': False}
        if ident in asserted_by_id:
            old = old_sources[asserted_by_id[ident]]
            finding.update({'prior_packet_asserted_sha256': old['sha256'], 'prior_packet_asserted_bytes': old['bytes'],
                            'prior_assertion_matches_pointer': old['sha256'] == oid and old['bytes'] == size,
                            'size_matches_prior_assertion': old['bytes'] == size,
                            'prior_packet_license_text': old.get('license')})
            if old['sha256'] == oid or old['bytes'] != size:
                raise Invalid('Expected prior ARG/CHL raw hash discrepancy and matching asset size were not reproduced')
        result.append(finding)
    return result


def feature_part_count(geometry):
    kind = geometry.get('type')
    coordinates = geometry.get('coordinates')
    if kind == 'Polygon':
        return 1
    if kind == 'MultiPolygon' and isinstance(coordinates, list):
        return len(coordinates)
    raise Invalid('Unexpected pinned baseline geometry type')


def row_errors(scope_ids, comparisons, assessments, summary, baseline_features, scope, hierarchy_features):
    errors = []
    warnings = []
    cmp_ids = [row.get('id') for row in comparisons]
    if len(cmp_ids) != len(set(cmp_ids)):
        errors.append('duplicate comparison subject')
    if set(cmp_ids) != scope_ids:
        errors.append('comparison subjects are missing or foreign')
    loc_rows = [row for row in assessments if row.get('record_type') == 'location']
    loc_ids = [row.get('location_id') for row in loc_rows]
    if len(loc_ids) != len(set(loc_ids)):
        errors.append('duplicate assessment subject')
    if set(loc_ids) != scope_ids:
        errors.append('assessment subjects are missing or foreign')
    c_by_id = {row.get('id'): row for row in comparisons}
    a_by_id = {row.get('location_id'): row for row in loc_rows}
    for identity in sorted(scope_ids & set(c_by_id) & set(a_by_id)):
        feature = baseline_features[identity]
        props = feature['properties']
        meta = props['metadata']
        geom = feature['geometry']
        baseline_type = geom['type']
        baseline_valid = shape(geom).is_valid
        components = feature_part_count(geom)
        expected = {
            'name': props['name'], 'parent_id': props['parent_id'], 'source_id': meta['source_id'],
            'baseline_geometry_type': baseline_type,
        }
        c, a = c_by_id[identity], a_by_id[identity]
        if feature.get('id') != identity or props.get('id') != identity or meta.get('original_id') != identity.split(':')[-1]:
            errors.append(f'{identity}: baseline feature identity fields disagree')
        source_prefix = 'gb:ARG:ADM2' if identity.startswith('gb:ARG:') else 'gb:CHL:ADM3'
        expected_role = 'departments' if identity.startswith('gb:ARG:') else 'Communes'
        expected_level = 'ADM2' if identity.startswith('gb:ARG:') else 'ADM3'
        expected_parent_level = 'ADM1' if identity.startswith('gb:ARG:') else 'ADM2'
        if meta.get('source_id') != source_prefix or meta.get('administrative_level') != expected_level or \
                meta.get('parent_source_level') != expected_parent_level or meta.get('source_role') != expected_role or \
                str(meta.get('reference_year')) != '2020':
            errors.append(f'{identity}: pinned source identity/type/role metadata mismatch')
        for key, value in expected.items():
            if c.get(key) != value or a.get(key) != value:
                errors.append(f'{identity}: {key} does not match the pinned baseline feature')
        for key, value in {'baseline_role': expected_role, 'baseline_year': '2020'}.items():
            actual = str(a.get(key)) if key == 'baseline_year' and a.get(key) is not None else a.get(key)
            if actual != value:
                errors.append(f'{identity}: assessment {key} does not match the pinned baseline metadata')
        if c.get('baseline_geometry_valid') is not baseline_valid:
            errors.append(f'{identity}: baseline geometry validity flag differs from pinned geometry')
        if 'baseline_multipart_count' not in c or c.get('baseline_multipart_count') is None:
            warnings.append(identity)
        elif c.get('baseline_multipart_count') != components:
            errors.append(f'{identity}: baseline component count differs from pinned geometry')
        # The two unavailable current-source matches predate this validator and
        # omitted this baseline-only field; retain those omissions, but detect
        # any new omission or changed gap set.
        if c.get('baseline_geometry_valid') is not baseline_valid:
            errors.append(f'{identity}: baseline validity recheck failed')
        for ckey, akey in [('current_name', 'current_source_name'), ('current_parent_name', 'current_parent_name'),
                           ('current_region_name', 'current_region_name'), ('current_geometry_type', 'current_geometry_type'),
                           ('current_multipart_count', 'current_multipart_count'),
                           ('simplified_iou_0_001_degrees', 'simplified_iou_0_001_degrees')]:
            if c.get(ckey) != a.get(akey):
                errors.append(f'{identity}: retained {ckey}/{akey} fields disagree across ledgers')
    if set(warnings) != EXPECTED_LEGACY_COMPONENT_OMISSIONS:
        errors.append('baseline component-count omission set changed or includes a new omission')
    if set(c_by_id) == scope_ids:
        matched = {row['id'] for row in comparisons if isinstance(row.get('current_match_count'), int) and row['current_match_count'] > 0}
        unmatched = {row['id'] for row in comparisons if row.get('current_match_count') == 0}
        type_flags = {row['id'] for row in comparisons if row.get('current_match_count', 0) > 0 and
                      row.get('current_geometry_type') != row.get('baseline_geometry_type')}
        iou_flags = {row['id'] for row in comparisons if isinstance(row.get('simplified_iou_0_001_degrees'), (float, int)) and
                     row['simplified_iou_0_001_degrees'] < 0.95}
        if summary.get('scoped_location_count') != len(scope_ids) or summary.get('matched_current_feature_count') != len(matched):
            errors.append('geometry summary scope/matched count differs from retained rows')
        if set(summary.get('unmatched_location_ids', [])) != unmatched:
            errors.append('geometry summary unmatched IDs differ from retained rows')
        if set(summary.get('type_change_location_ids', [])) != type_flags:
            errors.append('geometry summary type-change IDs differ from retained rows')
        if set(summary.get('iou_below_0_95_location_ids', [])) != iou_flags:
            errors.append('geometry summary IoU-threshold IDs differ from retained rows')
    # The top-level assessment summary and parent ledger are checked against
    # location rows, frozen scope and each subject's pinned parent.
    headers = [row for row in assessments if row.get('record_type') == 'summary']
    parents = [row for row in assessments if row.get('record_type') == 'parent']
    if len(headers) != 1:
        errors.append('assessment file must contain exactly one summary row')
    else:
        head = headers[0]
        counts = {label: sum(row.get('disposition') == label for row in loc_rows)
                  for label in ('justified', 'correction-needed', 'insufficient-evidence')}
        if head.get('issue') != 444 or head.get('baseline_commit') != 'd6a860ae2cff80af4ca0604bbc26e90dee56fc3b':
            errors.append('retained assessment header changed issue or true old baseline vintage')
        if head.get('location_count') != len(scope_ids) or head.get('dispositions') != counts:
            errors.append('assessment summary count/dispositions differ from location rows')
        if head.get('parent_count') != len(parents) or head.get('follow_up_issues') != {'argentina': 937, 'chile': 938}:
            errors.append('assessment parent/follow-up summary differs from retained ledgers')
    expected_parents = {row['id']: row for row in scope.get('province_scopes', [])}
    observed_parent_rows = {row.get('parent_id'): row for row in parents}
    if len(parents) != len(observed_parent_rows) or set(observed_parent_rows) != set(expected_parents):
        errors.append('parent ledger is duplicate, incomplete or foreign to frozen scope')
    for parent_id, expected in expected_parents.items():
        row = observed_parent_rows.get(parent_id)
        if row is None:
            continue
        parent_feature = hierarchy_features.get(parent_id)
        count = sum(feature['properties']['parent_id'] == parent_id for feature in baseline_features.values())
        if parent_feature is None or parent_feature.get('level') != 'province' or parent_feature.get('name') != expected['name']:
            errors.append(f'{parent_id}: scope parent name/ID does not match pinned hierarchy')
        if row.get('parent_name') != expected['name'] or row.get('child_count_in_this_packet') != count or \
                row.get('full_parent_child_count_in_scope') != expected['full_province_locations']:
            errors.append(f'{parent_id}: parent name or child summary differs from pinned scope/features')
    return errors, sorted(warnings)


def fake_rehashed_checker_acceptance(candidate_comparisons):
    """Run the old checker with only candidate comparison/inventory reads intercepted."""
    path = ROOT / OLD / 'geometry-comparisons.jsonl'
    inv_path = ROOT / OLD / 'source-inventory.json'
    raw_rows = ''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in candidate_comparisons).encode()
    inventory = json.loads(BASE.read(str(OLD / 'source-inventory.json')))
    for output in inventory['outputs']:
        if output['path'] == str(OLD / 'geometry-comparisons.jsonl'):
            output['bytes'] = len(raw_rows)
            output['sha256'] = sha256(raw_rows)
    inventory_raw = (json.dumps(inventory, ensure_ascii=False, indent=2) + '\n').encode()
    orig_text, orig_bytes = Path.read_text, Path.read_bytes

    def patched_text(self, *args, **kwargs):
        absolute = Path(self).resolve()
        if absolute == path.resolve():
            return raw_rows.decode('utf-8')
        if absolute == inv_path.resolve():
            return inventory_raw.decode('utf-8')
        return orig_text(self, *args, **kwargs)

    def patched_bytes(self, *args, **kwargs):
        absolute = Path(self).resolve()
        if absolute == path.resolve():
            return raw_rows
        if absolute == inv_path.resolve():
            return inventory_raw
        return orig_bytes(self, *args, **kwargs)

    stdout = io.StringIO()
    with patch.object(Path, 'read_text', patched_text), patch.object(Path, 'read_bytes', patched_bytes), contextlib.redirect_stdout(stdout):
        runpy.run_path(str(ROOT / OLD / 'check-packet.py'), run_name='__main__')
    report = json.loads(stdout.getvalue())
    return report, raw_rows, inventory_raw


def evaluate_case(name, comparisons, assessments, summary, pointer_records, expected_accept):
    errors, warnings = row_errors(SCOPE_IDS, comparisons, assessments, summary, BASE_FEATURES, SCOPE, BASE_HIERARCHY)
    try:
        validate_pointer_evidence(pointer_records)
    except Invalid as exc:
        errors.append(str(exc))
    accepted = not errors
    if accepted is not expected_accept:
        raise Invalid(f'Adversarial control has the wrong outcome: {name}: {errors}')
    fixture = {'comparisons': comparisons, 'assessments': assessments, 'summary': summary, 'pointers': pointer_records}
    fixture_bytes = canonical(fixture)
    return {'id': name, 'expected': 'accept' if expected_accept else 'reject',
            'outcome': 'accepted' if accepted else 'rejected', 'passed': True,
            'candidate_fixture_bytes': len(fixture_bytes), 'candidate_fixture_sha256': sha256(fixture_bytes),
            'errors': errors, 'known_legacy_component_omissions': warnings}


def main():
    global BASE, SCOPE, SCOPE_IDS, BASE_FEATURES, BASE_HIERARCHY
    issue = read_json(ISSUE_SNAPSHOT)
    if issue.get('number') != 1122 or sha256(issue.get('body', '').encode()) != ISSUE_BODY_SHA256:
        raise Invalid('Issue snapshot number/body hash differs from the reviewed #1122 contract')
    match = re.search(r'<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->', issue['body'], re.S)
    if not match:
        raise Invalid('Issue snapshot omits its machine contract')
    contract = json.loads(match.group(1))
    quality = contract['evidence_quality']
    if contract.get('mode') != 'geography' or contract.get('max_prs') != 1 or \
            contract.get('owned_paths') != [str(OWNED) + '/'] or contract.get('depends_on') != [444]:
        raise Invalid('Issue mode, PR budget, dependency or ownership differs from the reviewed contract')
    if quality.get('pins') != EXPECTED_PINS or quality.get('manifest_path') != str(OWNED / 'evidence-quality.json'):
        raise Invalid('Issue pins/manifest path differ from the expected exact contract')
    subject_ids = quality.get('subject_ids', [])
    if len(subject_ids) != 230 or len(set(subject_ids)) != 230 or subject_ids != sorted(subject_ids):
        raise Invalid('Issue subject roster is not the exact sorted 230-ID contract')
    if sum(identity.startswith('gb:ARG:ADM2:') for identity in subject_ids) != 53 or \
            sum(identity.startswith('gb:CHL:ADM3:') for identity in subject_ids) != 177:
        raise Invalid('Country/administrative-level scope differs from issue contract')
    baseline_files = []
    for name, path in PIN_PATHS.items():
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{BASELINE_COMMIT}:{path}'])
        baseline_files.append(descriptor(path, raw))
        if sha256(raw) != EXPECTED_PINS[name]:
            raise Invalid('Issue pin mismatch at candidate baseline: ' + name)
    BASE = Baseline(ROOT, BASELINE_COMMIT, baseline_files)
    BASE_FEATURES, subject_descriptors = BASE.subjects(subject_ids)
    SCOPE_IDS = set(subject_ids)
    SCOPE = json.loads(BASE.read(PIN_PATHS['original-scope']))
    hierarchy_rows = json.loads(BASE.read(PIN_PATHS['baseline-hierarchy']))
    BASE_HIERARCHY = {row.get('id'): row for row in hierarchy_rows}
    if len(BASE_HIERARCHY) != len(hierarchy_rows):
        raise Invalid('Pinned hierarchy contains duplicate identities')
    old_scope_ids = SCOPE.get('member_location_ids', [])
    if set(old_scope_ids) != SCOPE_IDS or len(old_scope_ids) != 230:
        raise Invalid('Issue subjects do not equal the preserved parent #444 frozen scope')
    if SCOPE.get('region_id') != 'framework:region:southern-south-america:c6bb0f01446e':
        raise Invalid('Frozen macro region differs from the retained scope')
    source_inventory = json.loads(BASE.read(PIN_PATHS['original-inventory']))
    for entry in source_inventory['baseline_inputs'] + source_inventory['packet_control_files'] + source_inventory['outputs'] + source_inventory['reproduction_methods']:
        path = entry['path']
        raw = BASE.read(path)
        if len(raw) != entry['bytes'] or sha256(raw) != entry['sha256']:
            raise Invalid('Retained packet inventory hash/size differs from immutable main: ' + path)
    old_issue_snapshot = json.loads(BASE.read(str(OLD / 'issue-scope-pinned.json')))
    if old_issue_snapshot.get('issue', {}).get('number') != 444 or old_issue_snapshot.get('snapshot_commit') != \
            'd6a860ae2cff80af4ca0604bbc26e90dee56fc3b':
        raise Invalid('Original scope snapshot vintage/identity changed')
    comparisons = read_jsonl_bytes(BASE.read(PIN_PATHS['original-comparisons']), 'comparison ledger')
    assessments = read_jsonl_bytes(BASE.read(PIN_PATHS['original-assessments']), 'assessment ledger')
    summary = json.loads(BASE.read(PIN_PATHS['original-summary']))
    pointer_records = source_records()
    pointer_findings = validate_pointer_evidence(pointer_records)
    errors, omissions = row_errors(SCOPE_IDS, comparisons, assessments, summary, BASE_FEATURES, SCOPE, BASE_HIERARCHY)
    if errors:
        raise Invalid('Original retained comparison ledgers contain unreconciled contradictions: ' + '; '.join(errors))

    original_report = subprocess.run([sys.executable, str(ROOT / OLD / 'check-packet.py')], cwd=ROOT,
                                     env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                     check=True, capture_output=True, text=True)
    old_checker_result = json.loads(original_report.stdout)
    false_parent_rows = copy.deepcopy(comparisons)
    false_parent_rows[0]['parent_id'] = 'country-SPI'
    old_false_parent, rehashed_comparison_bytes, rehashed_inventory_bytes = fake_rehashed_checker_acceptance(false_parent_rows)
    false_parent_errors, _ = row_errors(SCOPE_IDS, false_parent_rows, assessments, summary, BASE_FEATURES, SCOPE, BASE_HIERARCHY)
    if old_false_parent.get('scope_ids') != 230 or not false_parent_errors:
        raise Invalid('Could not reproduce old false-parent pass and new semantic rejection')

    controls = []
    controls.append(evaluate_case('positive-original-roster', comparisons, assessments, summary, pointer_records, True))
    wrong_parent = copy.deepcopy(comparisons); wrong_parent[0]['parent_id'] = 'country-SPI'
    controls.append(evaluate_case('rehashed-false-country-SPI-parent', wrong_parent, assessments, summary, pointer_records, False))
    wrong_source = copy.deepcopy(comparisons); wrong_source[0]['source_id'] = 'gb:ARG:ADM1'
    controls.append(evaluate_case('wrong-source-identity-level', wrong_source, assessments, summary, pointer_records, False))
    wrong_type = copy.deepcopy(comparisons); wrong_type[0]['baseline_geometry_type'] = 'MultiPolygon'
    controls.append(evaluate_case('wrong-baseline-geometry-type', wrong_type, assessments, summary, pointer_records, False))
    wrong_assessment = copy.deepcopy(assessments)
    next(row for row in wrong_assessment if row.get('record_type') == 'location')['baseline_role'] = 'electoral-districts'
    controls.append(evaluate_case('wrong-assessment-source-role', comparisons, wrong_assessment, summary, pointer_records, False))
    wrong_vintage = copy.deepcopy(pointer_records); wrong_vintage['objects'][0]['upstream_commit'] = 'd6a860ae2cff80af4ca0604bbc26e90dee56fc3b'
    controls.append(evaluate_case('wrong-upstream-pointer-vintage', comparisons, assessments, summary, wrong_vintage, False))
    duplicate = copy.deepcopy(comparisons); duplicate.append(copy.deepcopy(duplicate[0]))
    controls.append(evaluate_case('duplicate-subject', duplicate, assessments, summary, pointer_records, False))
    foreign = copy.deepcopy(comparisons); foreign[0]['id'] = 'gb:ARG:ADM2:foreign-unscoped'
    controls.append(evaluate_case('foreign-subject', foreign, assessments, summary, pointer_records, False))
    bad_summary = copy.deepcopy(summary); bad_summary['matched_current_feature_count'] = 229
    controls.append(evaluate_case('inconsistent-match-summary', comparisons, assessments, bad_summary, pointer_records, False))
    removed_component = copy.deepcopy(comparisons)
    matched_row = next(row for row in removed_component if row.get('current_match_count', 0) > 0)
    matched_row.pop('baseline_multipart_count', None)
    controls.append(evaluate_case('newly-omitted-baseline-component-field', removed_component, assessments, summary, pointer_records, False))

    maps = []
    for identity in sorted(SCOPE_IDS):
        feature = BASE_FEATURES[identity]
        properties = feature['properties']; meta = properties['metadata']; geom = feature['geometry']
        c = next(row for row in comparisons if row['id'] == identity)
        a = next(row for row in assessments if row.get('record_type') == 'location' and row['location_id'] == identity)
        maps.append({'id':identity,'name':properties['name'],'parent_id':properties['parent_id'],
          'source_id':meta['source_id'],'source_url':meta.get('source_url'),'reference_year':meta.get('reference_year'),
          'administrative_level':meta.get('administrative_level'),'parent_source_level':meta.get('parent_source_level'),
          'source_role':meta.get('source_role'),'metadata_license_assertion':meta.get('license'),
          'baseline_geometry_type':geom['type'],'baseline_geometry_valid':shape(geom).is_valid,
          'baseline_component_count':feature_part_count(geom),'containing_file':subject_descriptors[identity],
          'comparison_component_count_recorded':c.get('baseline_multipart_count'),
          'comparison_component_count_status':'missing-in-preserved-record' if 'baseline_multipart_count' not in c or c.get('baseline_multipart_count') is None else 'matches-pinned-feature',
          'assessment_source_role':a.get('baseline_role'),'assessment_reference_year':a.get('baseline_year')})
    found_counts = {'subject_count':len(SCOPE_IDS),'argentina_adm2_count':sum(x.startswith('gb:ARG:ADM2:') for x in SCOPE_IDS),
      'chile_adm3_count':sum(x.startswith('gb:CHL:ADM3:') for x in SCOPE_IDS),'comparison_row_count':len(comparisons),
      'assessment_location_row_count':sum(r.get('record_type')=='location' for r in assessments),
      'parent_row_count':sum(r.get('record_type')=='parent' for r in assessments),
      'recomputed_baseline_components':sum(row['baseline_component_count'] for row in maps),
      'baseline_component_counts_recorded':len(SCOPE_IDS)-len(omissions),'legacy_missing_baseline_component_counts':len(omissions),
      'corrected_geoBoundaries_raw_pointer_hashes':sum(not row.get('prior_assertion_matches_pointer', True) for row in pointer_findings),
      'upstream_lfs_pointer_records_verified':len(pointer_findings)}
    result = {'version':1,'method_id':'batch3-provenance-crossfield-validator','kind':'generator','issue':1122,
      'issue_body_sha256':ISSUE_BODY_SHA256,'baseline_commit':BASELINE_COMMIT,'original_parent_issue':444,
      'old_packet_baseline_commit':old_issue_snapshot['snapshot_commit'],'scope_counts':found_counts,
      'all_230_subjects_exactly_bound_to_pinned_features':True,'old_packet_present_baseline_fields_reconciled':True,
      'legacy_missing_component_count_ids':omissions,'lfs_pointer_findings':pointer_findings,
      'original_checker_clean_result':old_checker_result,
      'rehashed_false_parent_control':{'candidate_comparison_bytes':len(rehashed_comparison_bytes),
        'candidate_comparison_sha256':sha256(rehashed_comparison_bytes),'candidate_inventory_bytes':len(rehashed_inventory_bytes),
        'candidate_inventory_sha256':sha256(rehashed_inventory_bytes),'old_checker_reported_pass':True,
        'old_checker_summary':old_false_parent,'new_validator_rejected':True,
        'new_validator_errors':false_parent_errors},
      'retained_measurements':'Observed within the preserved 2026-10-05 packet and cross-checked only for internal row/summary agreement; current IGN/Subdere source bytes are absent and IoUs, source matching, source completeness, and territorial/legal assertions were not reproduced.',
      'source_and_geography_limits':['Raw geoBoundaries LFS objects were not downloaded; pointer OID/size are authenticated, but raw bytes are not independently hashed.',
        'The prior packet source inventory records the geoBoundaries CC BY 3.0 IGO license; the upstream LFS metadata payloads were not hydrated or independently rechecked.',
        'IGN capture and Subdere DPA bytes/terms, Law 1186 text, Subdere change log and name-variant sources were not re-retrieved or verified.',
        'This task verifies retained baseline identity/provenance fields and validator integrity only; it does not certify boundaries, completeness, regional interior or approval.'],
      'geographic_approval':'not established'}
    control_doc={'version':1,'method_id':'batch3-provenance-crossfield-validator','kind':'generator','outcome':'passed',
                 'positive_control':'positive-original-roster','negative_control_ids':[c['id'] for c in controls[1:]],
                 'controls':controls,'all_passed':all(c['passed'] for c in controls)}
    map_doc={'version':1,'issue':1122,'baseline_commit':BASELINE_COMMIT,'subject_count':len(maps),
             'basis':'Exact issue subjects joined to features read from immutable current-main files through the shared subject helper.',
             'rows':maps}
    for name, value in [('baseline-feature-bindings.json',map_doc),('source-provenance-findings.json',{'version':1,'issue':1122,'upstream_commit':UPSTREAM_COMMIT,'pointer_findings':pointer_findings}),
                        ('adversarial-controls.json',control_doc),('verification-results.json',result)]:
        (ROOT / OWNED / name).write_bytes(canonical(value))
    print(json.dumps({'result':result,'controls':len(controls),'all_controls_passed':control_doc['all_passed']},ensure_ascii=False,sort_keys=True))


if __name__ == '__main__':
    main()
