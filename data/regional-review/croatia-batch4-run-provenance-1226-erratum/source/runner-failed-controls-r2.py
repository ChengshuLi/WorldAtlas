#!/usr/bin/env python3
"""Reproduce the preserved Croatia #1199 reports from authenticated inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
EVIDENCE = OWNED / 'evidence'
ISSUE_SNAPSHOT = ROOT / 'data/regional-review/croatia-batch4-read-boundary-guard/source/issue-1209-api-snapshot.json'
ISSUE_RETRIEVAL = ROOT / 'data/regional-review/croatia-batch4-read-boundary-guard/source/issue-snapshot-retrieval.json'
ISSUE_SNAPSHOT_SHA256 = 'f694f98d653042bffe067c698dd6ec20f8673416dc94d8370937b83e2977694b'
ISSUE_RETRIEVAL_SHA256 = 'ed3aa34354e53b6b74ff227569e64fd684a9060b8ad8fc0a268ac5dfe7267c8b'
JOB_SNAPSHOT = OWNED / 'source/issue-1396-api-snapshot.json'
JOB_SNAPSHOT_SHA256 = '0cd76e4014929f705b025bcfd32571541ee11581994577de05aba8c5c5a173a1'
JOB_RETRIEVAL = OWNED / 'source/issue-1396-snapshot-retrieval.json'
JOB_RETRIEVAL_SHA256 = 'd15b3c30c392e046b63ff472c92b26adffefe881bc1651733ca2b1a9634fed60'
PINNED_COMMIT = 'dd096da1b7a8c28f4f824d178a16e59ecdc2ac7e'
ORIGINAL_BASELINE = '7646e0962afab6cc4f566439bb2f96890ae4b91e'
HISTORICAL_PIN_COMMITS = {
    ORIGINAL_BASELINE,
    'ab655fbbaf5c0091f24653e66e8e1a40b8fdfeeb',
    '96f2a6d201236ba62f471535db240b123de60c09',
}
OLD_PACKET = Path('data/regional-review/regional-review-ce7798317652c0c2')
OLD_SCOPE = OLD_PACKET / 'scope.json'
OLD_ISSUE_SNAPSHOT = OLD_PACKET / 'source/issue-419-api-snapshot.json'
BUILDER = OLD_PACKET / 'build_assessment.py'
GEOMETRY = Path('data/regional-review/regional-review-c64d17e99f61d668/source/geoboundaries-9469f09/HRV/ADM2/geoBoundaries-HRV-ADM2.geojson')
DETAIL = OLD_PACKET / 'source/dzs-census-2021-detail-extract.csv'
SUMMARY = OLD_PACKET / 'source/dzs-census-2021-summary-tables.xlsx'
HELPER = Path('scripts/evidence/immutable.py')
FILES = ('assessment-summary.json', 'province-completeness.csv', 'scoped-location-assessments.csv')
ISSUE_SCOPE_RE = re.compile(r'Machine-readable exact workload scope \(JSON;.*?\):\s*```json\s*(.*?)\s*```', re.S)
WORK_RE = re.compile(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->')
INPUT_RE = re.compile(r'- `(?P<alias>input_\d{3})`: `(?P<path>[^`]+)` at `(?P<commit>[a-f0-9]{40})`; (?P<bytes>\d+) bytes; SHA-256 `(?P<sha>[a-f0-9]{64})`\.')
MAX_PHASE_BYTES = 256 * 1024 * 1024
ADDITIONAL_ARTIFACT_ALLOWANCE = 27 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.PIPE)


def git_file(commit: str, path: str) -> bytes:
    """Read one ordinary Git blob and reject symlink/submodule entries."""
    listing = git('ls-tree', '-z', commit, '--', path).decode('utf-8')
    row = listing.rstrip('\0')
    if not row or '\t' not in row:
        raise ValueError(f'missing pinned Git object: {commit}:{path}')
    metadata, actual_path = row.split('\t', 1)
    mode, kind, oid = metadata.split()
    if actual_path != path or kind != 'blob' or mode not in ('100644', '100755'):
        raise ValueError(f'input is not an ordinary Git file: {commit}:{path}')
    return git('cat-file', 'blob', oid)


def contract_snapshot(raw: bytes) -> tuple[dict, dict, dict[str, str]]:
    if sha(raw) != ISSUE_SNAPSHOT_SHA256:
        raise ValueError('captured issue #1209 API snapshot hash mismatch')
    issue = json.loads(raw)
    if issue.get('number') != 1209 or issue.get('state') != 'open':
        raise ValueError('captured issue is not the claimed open work item')
    labels = {label.get('name') for label in issue.get('labels', [])}
    if not {'kind:work-item', 'status:ready', 'type:geography'}.issubset(labels):
        raise ValueError('captured issue is outside the reviewed ready geography lane')
    work = WORK_RE.findall(issue.get('body') or '')
    if len(work) != 1:
        raise ValueError('captured issue has no unique reviewed work contract')
    spec = json.loads(work[0])
    quality = spec.get('evidence_quality') or {}
    if spec.get('mode') != 'geography' or spec.get('owned_paths') != [
        'data/regional-review/croatia-batch4-read-boundary-guard/'
    ]:
        raise ValueError('captured issue ownership or geography mode changed')
    if spec.get('max_prs') != 1 or spec.get('depends_on') != [1194]:
        raise ValueError('captured issue PR budget or completed prerequisite changed')
    if quality.get('manifest_path') != str(ISSUE_SNAPSHOT.relative_to(ROOT).parents[1] / 'evidence-quality.json'):
        raise ValueError('captured issue evidence manifest path changed')
    pins = quality.get('pins')
    if not isinstance(pins, dict) or len(pins) != 66:
        raise ValueError('captured issue no longer declares the exact 66 immutable pins')
    parsed = {}
    for key, value in pins.items():
        commit, separator, path = key.partition(':')
        if not separator or commit != PINNED_COMMIT or not re.fullmatch(r'[a-f0-9]{64}', value):
            raise ValueError(f'malformed or retargeted issue pin: {key}')
        parsed[path] = value
    if len(parsed) != 66:
        raise ValueError('duplicate issue pin paths')
    subjects = quality.get('subject_ids')
    if not isinstance(subjects, list) or len(subjects) != 224 or len(set(subjects)) != 224:
        raise ValueError('captured issue no longer scopes exactly 224 unique IDs')
    return issue, spec, parsed


def verify_runner_code() -> dict:
    """Bind the currently executing runner to its committed Git tree bytes."""
    head = git('rev-parse', 'HEAD').decode().strip()
    relative = str(Path(__file__).resolve().relative_to(ROOT))
    committed = git_file(head, relative)
    actual = Path(__file__).resolve().read_bytes()
    if actual != committed:
        raise ValueError('executed new runner differs from its immutable HEAD blob')
    row = git('ls-tree', head, '--', relative).decode().strip()
    oid = row.split()[2]
    return {'path': relative, 'commit': head, 'git_blob': oid, 'sha256': sha(committed), 'bytes': len(committed)}


def load_inputs(read_input=None) -> dict:
    """Read, bind and freeze every path later passed to the historical builder."""
    runner = verify_runner_code()
    reader = read_input or (lambda path: path.read_bytes())
    snapshot_raw = bytes(reader(ISSUE_SNAPSHOT))
    retrieval_raw = ISSUE_RETRIEVAL.read_bytes()
    if sha(retrieval_raw) != ISSUE_RETRIEVAL_SHA256:
        raise ValueError('captured issue #1209 retrieval receipt hash mismatch')
    issue, spec, pins = contract_snapshot(snapshot_raw)
    retrieval = json.loads(retrieval_raw)
    if (retrieval.get('api_url') != 'https://api.github.com/repos/ChengshuLi/WorldAtlas/issues/1209' or
        retrieval.get('sha256') != sha(snapshot_raw) or retrieval.get('bytes') != len(snapshot_raw) or
        retrieval.get('retrieved_at') != '2026-10-06T20:57:57Z' or
        issue.get('updated_at') != '2026-10-06T20:55:33Z'):
        raise ValueError('issue snapshot and retrieval receipt disagree')
    job_raw = JOB_SNAPSHOT.read_bytes()
    if sha(job_raw) != JOB_SNAPSHOT_SHA256:
        raise ValueError('captured issue #1396 API snapshot hash mismatch')
    job_issue = json.loads(job_raw)
    work_blocks = WORK_RE.findall(job_issue.get('body') or '')
    if job_issue.get('number') != 1396 or job_issue.get('state') != 'open' or len(work_blocks) != 1:
        raise ValueError('captured issue #1396 contract is missing or ambiguous')
    job_spec = json.loads(work_blocks[0])
    job_quality = job_spec.get('evidence_quality') or {}
    job_labels = {label.get('name') for label in job_issue.get('labels', [])}
    if not {'kind:work-item', 'type:geography', 'mode:geography', 'status:ready', 'status:claimed'}.issubset(job_labels):
        raise ValueError('captured issue #1396 is not the claimed geography work item')
    subjects = job_quality.get('subject_ids', [])
    if (job_spec.get('mode') != 'geography' or job_spec.get('max_prs') != 1 or
        job_spec.get('depends_on') != [1209] or job_quality.get('review_kind') != 'source' or
        job_quality.get('manifest_path') != str(OWNED.relative_to(ROOT) / 'evidence-quality.json') or
        job_spec.get('owned_paths') != [
        str(OWNED.relative_to(ROOT)) + '/'
    ] or len(job_quality.get('pins', {})) != 80 or len(subjects) != 224 or len(set(subjects)) != 224):
        raise ValueError('captured issue #1396 scope, pins, subjects or PR budget changed')
    descriptors = {row['alias']: {'path': row['path'], 'commit': row['commit'],
                    'bytes': int(row['bytes']), 'sha256': row['sha']}
                   for row in (match.groupdict() for match in INPUT_RE.finditer(job_issue.get('body') or ''))}
    if len(descriptors) != 80 or set(descriptors) != set(job_quality['pins']):
        raise ValueError('captured issue #1396 whole-file input map is incomplete or ambiguous')
    if any(job_quality['pins'][alias] != row['sha256'] for alias, row in descriptors.items()):
        raise ValueError('captured issue #1396 input aliases disagree with exact hashes')
    job_receipt_raw = JOB_RETRIEVAL.read_bytes()
    if sha(job_receipt_raw) != JOB_RETRIEVAL_SHA256:
        raise ValueError('captured issue #1396 retrieval receipt hash mismatch')
    job_retrieval = json.loads(job_receipt_raw)
    if (job_retrieval.get('api_url') != job_issue.get('url') or
        job_retrieval.get('sha256') != sha(job_raw) or job_retrieval.get('bytes') != len(job_raw) or
        not isinstance(job_retrieval.get('retrieved_at'), str)):
        raise ValueError('issue #1396 snapshot and retrieval receipt disagree')

    # Check the immutable #1199 issue snapshot and all 66 complete Git blobs.
    saved_scope_path = 'data/regional-review/croatia-batch4-reproduction-419-erratum/source/issue-evidence-scope.json'
    if saved_scope_path not in pins:
        raise ValueError('issue snapshot omits the preserved #1194 evidence scope')
    saved_scope = git_file(PINNED_COMMIT, saved_scope_path)
    if sha(saved_scope) != pins[saved_scope_path]:
        raise ValueError('preserved #1199 issue evidence-scope blob changed')
    prior_scope = json.loads(saved_scope)
    prior_pins = prior_scope.get('pins')
    if not isinstance(prior_pins, dict) or len(prior_pins) != 62:
        raise ValueError('preserved #1194 scope does not contain all 62 historical pins')
    verified_sources = {}
    for key, expected in prior_pins.items():
        commit, separator, path = key.partition(':')
        if not separator or commit not in HISTORICAL_PIN_COMMITS or not re.fullmatch(r'[a-f0-9]{64}', expected):
            raise ValueError(f'malformed historical source pin: {key}')
        raw = git_file(commit, path)
        if sha(raw) != expected:
            raise ValueError(f'historical source pin changed: {key}')
        verified_sources[(commit, path)] = {'commit': commit, 'path': path,
            'sha256': expected, 'bytes': len(raw), 'role': 'historical-source-or-result'}
    for alias, row in descriptors.items():
        raw = git_file(row['commit'], row['path'])
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError(f'issue input pin changed: {alias} {row["commit"]}:{row["path"]}')
        verified_sources[(row['commit'], row['path'])] = {**row, 'role': 'issue-pinned-input'}
    unique_source_bytes = {}
    for row in verified_sources.values():
        previous = unique_source_bytes.setdefault(row['sha256'], row['bytes'])
        if previous != row['bytes']:
            raise ValueError('same source digest declared with inconsistent byte counts')
        if row['bytes'] > 32 * 1024 * 1024:
            raise ValueError('pinned source exceeds the per-file limit')
    original_phase_bytes = sum(unique_source_bytes.values())
    if original_phase_bytes != 238_024_039:
        raise ValueError('unique original source byte total differs from the complete descriptor map')
    for path, expected in pins.items():
        raw = git_file(PINNED_COMMIT, path)
        if sha(raw) != expected:
            raise ValueError(f'issue pin differs from immutable Git bytes: {PINNED_COMMIT}:{path}')

    # Bind actual filesystem bytes once, then give only those frozen bytes to
    # a private working packet. The old builder never reopens mutable originals.
    actual_paths = [OLD_SCOPE, OLD_ISSUE_SNAPSHOT, BUILDER, GEOMETRY, DETAIL, SUMMARY]
    frozen = {}
    captured = {str(path): bytes(reader(ROOT / str(path))) for path in actual_paths}
    input_records = []
    for relative_path in actual_paths:
        path = str(relative_path)
        actual = captured[path]
        if len(actual) > 32 * 1024 * 1024:
            raise ValueError(f'actually consumed input exceeds the ordinary-file limit: {path}')
        expected = pins.get(path)
        if expected is None:
            raise ValueError(f'actually consumed input has no issue-contract pin: {path}')
        trusted = git_file(PINNED_COMMIT, path)
        if sha(trusted) != expected or sha(actual) != expected:
            raise ValueError(f'actually consumed filesystem bytes differ from the declared immutable pin: {path}')
        frozen[path] = trusted
        input_records.append({'path': path, 'commit': PINNED_COMMIT, 'sha256': expected,
                              'bytes': len(trusted), 'read_boundary': 'verified bytes copied into private build packet'})

    helper_bytes = git_file(PINNED_COMMIT, str(HELPER))
    frozen[str(HELPER)] = helper_bytes
    input_records.append({'path': str(HELPER), 'commit': PINNED_COMMIT, 'sha256': sha(helper_bytes),
                          'bytes': len(helper_bytes), 'read_boundary': 'compiled from immutable Git blob'})

    # Admit the complete phase before parsing/decompressing workbook members or
    # running the historical generator. The 27 MiB reserve covers all candidate
    # code, captures, controls, receipts, generated reports and other retained
    # artifacts; it is deliberately conservative and never partitions the inputs.
    with zipfile.ZipFile(io.BytesIO(frozen[str(SUMMARY)])) as workbook:
        planned_members = [{'member': item.filename, 'bytes': item.file_size}
                           for item in workbook.infolist()]
    if any(row['bytes'] > 32 * 1024 * 1024 for row in planned_members):
        raise ValueError('planned decoded XLSX member exceeds the per-file limit')
    planned_decoded_bytes = sum(row['bytes'] for row in planned_members)
    if original_phase_bytes + planned_decoded_bytes + ADDITIONAL_ARTIFACT_ALLOWANCE > MAX_PHASE_BYTES:
        raise ValueError('complete raw, decoded and additional-artifact phase exceeds 256 MiB')

    # These two original inputs also occur in the 62-file #1194 source map.
    for path in (str(OLD_SCOPE), str(OLD_ISSUE_SNAPSHOT), str(DETAIL), str(SUMMARY), str(GEOMETRY)):
        key = f'{ORIGINAL_BASELINE}:{path}'
        expected = prior_pins.get(key)
        if expected is not None and sha(frozen[path]) != expected:
            raise ValueError(f'issue #1194 source pin disagrees with the #1199 file pin: {path}')

    # Confirm the pinned old issue snapshot embeds the same exact complete scope.
    original_issue = json.loads(frozen[str(OLD_ISSUE_SNAPSHOT)])
    match = ISSUE_SCOPE_RE.search(original_issue.get('body') or '')
    if not match:
        raise ValueError('pinned #1194 issue snapshot has no machine-readable scope')
    embedded_scope = json.loads(match.group(1))
    disk_scope = json.loads(frozen[str(OLD_SCOPE)])
    if embedded_scope != disk_scope:
        raise ValueError('pinned #1194 issue body and scope bytes disagree')
    quality = job_spec['evidence_quality']
    subjects = quality['subject_ids']
    if sorted(embedded_scope.get('member_location_ids', [])) != sorted(subjects):
        raise ValueError('pinned historical scope differs from the exact 224 scoped subjects')

    # The helper is executed from the verified Git blob; verify its on-disk copy
    # only to ensure the checkout still represents the recorded source bytes.
    return {'runner': runner, 'issue_snapshot': {'path': str(ISSUE_SNAPSHOT.relative_to(ROOT)),
            'sha256': sha(snapshot_raw), 'bytes': len(snapshot_raw), 'updated_at': issue.get('updated_at')},
            'issue_snapshot_retrieval': {'path': str(ISSUE_RETRIEVAL.relative_to(ROOT)),
            'sha256': sha(retrieval_raw), 'bytes': len(retrieval_raw), 'retrieved_at': retrieval.get('retrieved_at')},
            'job_snapshot': {'path': str(JOB_SNAPSHOT.relative_to(ROOT)), 'sha256': sha(job_raw),
            'bytes': len(job_raw), 'updated_at': job_issue.get('updated_at')},
            'job_snapshot_retrieval': {'path': str(JOB_RETRIEVAL.relative_to(ROOT)),
            'sha256': sha(job_receipt_raw), 'bytes': len(job_receipt_raw), 'retrieved_at': job_retrieval.get('retrieved_at')},
            'issue_spec': job_spec, 'issue_pins': pins, 'historical_pins': prior_pins,
            'verified_sources': sorted(verified_sources.values(), key=lambda row: (row['commit'], row['path'])),
            'unique_original_bytes': original_phase_bytes,
            'planned_decoded_xlsx_bytes': planned_decoded_bytes,
            'additional_artifact_allowance_bytes': ADDITIONAL_ARTIFACT_ALLOWANCE,
            'phase_limit_bytes': MAX_PHASE_BYTES,
            'frozen': frozen, 'inputs': input_records,
            'subjects': subjects, 'subject_count': len(subjects),
            'subject_ids_sha256': hashlib.sha256('\n'.join(sorted(subjects)).encode()).hexdigest(),
            'issue_updated_at': issue.get('updated_at'),
            'issue_retrieved_at': retrieval.get('retrieved_at'),
            'pinned_commit': PINNED_COMMIT, 'historical_baseline': ORIGINAL_BASELINE}


def safe_destination(output: str | Path) -> Path:
    raw = str(output)
    lexical = PurePosixPath(raw)
    parts = raw.split('/')
    if '\\' in raw or '\0' in raw or lexical.is_absolute() or any(part in ('', '.', '..') for part in parts):
        raise ValueError('output path must be relative and contain no empty, dot or traversal component')
    if not parts or parts[0] != 'evidence' or len(parts) < 2:
        raise ValueError('output must stay below this packet evidence directory')
    evidence = EVIDENCE.resolve(strict=False)
    target = OWNED.joinpath(*parts)
    cursor = OWNED
    for component in parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ValueError('output path contains a symlink')
        if cursor.exists() and cursor != target and not cursor.is_dir():
            raise ValueError('output parent is not an ordinary directory')
    if target.exists():
        raise FileExistsError('output destination already exists; preserve it and choose a new run ID')
    resolved_parent = target.parent.resolve(strict=False)
    if not resolved_parent.is_relative_to(evidence):
        raise ValueError('resolved output parent escapes the owned evidence directory')
    return target


def install_verified_helper(source: bytes) -> None:
    """Load the pinned helper bytes rather than importing a mutable checkout file."""
    helper = types.ModuleType('evidence.immutable')
    helper.__file__ = str(ROOT / HELPER)
    helper.__package__ = 'evidence'
    package = sys.modules.get('evidence')
    if package is None:
        package = types.ModuleType('evidence')
        sys.modules['evidence'] = package
    package.__path__ = [str(ROOT / 'scripts/evidence')]
    sys.modules['evidence.immutable'] = helper
    package.immutable = helper
    exec(compile(source, helper.__file__, 'exec'), helper.__dict__)


def build_private(frozen: dict, scratch: Path, subjects: list[str]) -> tuple[Path, list[dict]]:
    private_packet = scratch / 'packet'
    (private_packet / 'source').mkdir(parents=True)
    copies = {
        str(OLD_SCOPE): private_packet / 'scope.json',
        str(OLD_ISSUE_SNAPSHOT): private_packet / 'source/issue-419-api-snapshot.json',
        str(DETAIL): private_packet / 'source/dzs-census-2021-detail-extract.csv',
        str(SUMMARY): private_packet / 'source/dzs-census-2021-summary-tables.xlsx',
    }
    for source, target in copies.items():
        target.write_bytes(frozen[source])
    geometry = scratch / 'verified-geometry.geojson'
    geometry.write_bytes(frozen[str(GEOMETRY)])
    install_verified_helper(frozen[str(HELPER)])
    module = types.ModuleType('_worldatlas_verified_croatia_builder')
    module.__file__ = str(ROOT / BUILDER)
    exec(compile(frozen[str(BUILDER)], module.__file__, 'exec'), module.__dict__)
    module.PACKET = private_packet
    output = scratch / 'products'
    summary_path = copies[str(SUMMARY)]
    decoded_members = {}
    original_read = zipfile.ZipFile.read
    def observed_read(archive, name, *args, **kwargs):
        raw = original_read(archive, name, *args, **kwargs)
        if Path(archive.filename) == summary_path:
            member = str(name)
            if member in decoded_members and decoded_members[member]['bytes'] != len(raw):
                raise ValueError('XLSX decoded member changed between reads')
            decoded_members[member] = {'path': str(SUMMARY), 'member': member,
                'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'decoded-member-bytes'}
        return raw
    zipfile.ZipFile.read = observed_read
    try:
        module.build(ORIGINAL_BASELINE, output, geometry)
    finally:
        zipfile.ZipFile.read = original_read
    consumed_members = sorted(decoded_members.values(), key=lambda row: row['member'])
    archive_members = []
    with zipfile.ZipFile(summary_path) as archive:
        for info in archive.infolist():
            raw = original_read(archive, info.filename)
            if len(raw) != info.file_size:
                raise ValueError('XLSX member size differs from its central directory')
            archive_members.append({'path': str(SUMMARY), 'member': info.filename,
                'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'decoded-member-bytes'})
    archive_names = {row['member'] for row in archive_members}
    if any(row['member'] not in archive_names for row in consumed_members):
        raise ValueError('actual XLSX reader consumed a member absent from the complete archive inventory')
    decoded_total = sum(row['bytes'] for row in archive_members)
    if decoded_total > 32 * 1024 * 1024:
        raise ValueError('decoded workbook members exceed the per-file limit')
    produced = {path.name for path in output.iterdir() if path.is_file()}
    if produced != set(FILES):
        raise ValueError(f'historical builder produced an unexpected file set: {sorted(produced)}')
    for name in FILES:
        if (output / name).is_symlink() or not (output / name).is_file():
            raise ValueError(f'historical builder output is not an ordinary file: {name}')
    summary_doc = json.loads((output / FILES[0]).read_bytes())
    rows = list(csv.DictReader((output / FILES[2]).open(encoding='utf-8', newline='')))
    ids = [row['id'] for row in rows]
    if len(ids) != 224 or len(set(ids)) != 224 or sorted(ids) != sorted(subjects):
        raise ValueError('generated output no longer has the exact 224 unique issue subjects')
    if summary_doc.get('metrics', {}).get('scoped_subject_count') != 224:
        raise ValueError('historical report subject count differs from the exact issue scope')
    return output, archive_members, consumed_members


def write_exclusive(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def publish_exclusive(products: Path, destination: Path, record: dict, interrupt_after: int | None = None) -> dict:
    destination.mkdir(parents=False, exist_ok=False)
    written = 0
    for name in FILES:
        raw = (products / name).read_bytes()
        write_exclusive(destination / name, raw)
        written += 1
        if interrupt_after == written:
            raise RuntimeError('injected interruption after exclusive output write')
    record = {**record, 'outputs': {name: sha((destination / name).read_bytes()) for name in FILES}}
    write_exclusive(destination / 'run-record.json', (json.dumps(record, sort_keys=True, indent=2) + '\n').encode())
    return record


def run(output: str | Path, read_input=None, interrupt_after: int | None = None) -> dict:
    destination = safe_destination(output)
    verified = load_inputs(read_input)
    # Validation and computation happen before creating the public destination.
    with tempfile.TemporaryDirectory(prefix='.read-boundary-', dir=OWNED) as temporary:
        products, decoded_members, consumed_members = build_private(verified['frozen'], Path(temporary), verified['subjects'])
        actual_decoded_bytes = sum(row['bytes'] for row in decoded_members)
        if actual_decoded_bytes != verified['planned_decoded_xlsx_bytes']:
            raise ValueError('decoded XLSX member inventory differs from its admitted central directory')
        destination = safe_destination(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination = safe_destination(output)
        record = {
            'issue': 1209,
            'runner': verified['runner'],
            'pinned_commit': verified['pinned_commit'],
            'historical_baseline': verified['historical_baseline'],
            'issue_snapshot': verified['issue_snapshot'],
            'issue_updated_at': verified['issue_snapshot']['updated_at'],
            'issue_retrieved_at': verified['issue_snapshot_retrieval']['retrieved_at'],
            'issue_snapshot_retrieval': verified['issue_snapshot_retrieval'],
            'job_snapshot': verified['job_snapshot'],
            'job_snapshot_retrieval': verified['job_snapshot_retrieval'],
            'subject_count': verified['subject_count'],
            'subject_ids_sha256': verified['subject_ids_sha256'],
            'issue_pin_count': len(verified['issue_pins']),
            'historical_pin_count': len(verified['historical_pins']),
            'verified_source_count': len(verified['verified_sources']),
            'unique_original_bytes': verified['unique_original_bytes'],
            'verified_sources': verified['verified_sources'],
            'decoded_xlsx_members': decoded_members,
            'decoded_xlsx_bytes': sum(row['bytes'] for row in decoded_members),
            'actually_consumed_xlsx_members': consumed_members,
            'execution_admission': {'unique_original_bytes': verified['unique_original_bytes'],
                'decoded_xlsx_member_bytes': actual_decoded_bytes,
                'additional_artifact_allowance_bytes': verified['additional_artifact_allowance_bytes'],
                'admitted_total_bytes': verified['unique_original_bytes'] + actual_decoded_bytes +
                    verified['additional_artifact_allowance_bytes'],
                'limit_bytes': verified['phase_limit_bytes']},
            'inputs': verified['inputs'],
            'factual_limit': 'This is a byte/read-boundary reproduction correction; it establishes no new territorial, parent, boundary, completeness, legal or licensing finding.'
        }
        return publish_exclusive(products, destination, record, interrupt_after)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True, help='A fresh safe run ID; never overwrite retained evidence')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,62}', args.run_id):
        raise SystemExit('run ID must use 1-63 ASCII letters, digits, underscores or hyphens')
    record = run(f'evidence/runs/{args.run_id}')
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
