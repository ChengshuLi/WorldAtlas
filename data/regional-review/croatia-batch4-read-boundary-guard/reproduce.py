#!/usr/bin/env python3
"""Reproduce the preserved Croatia #1199 reports from authenticated inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
EVIDENCE = OWNED / 'evidence'
ISSUE_SNAPSHOT = OWNED / 'source/issue-1209-api-snapshot.json'
ISSUE_SNAPSHOT_SHA256 = 'f694f98d653042bffe067c698dd6ec20f8673416dc94d8370937b83e2977694b'
PINNED_COMMIT = 'dd096da1b7a8c28f4f824d178a16e59ecdc2ac7e'
ORIGINAL_BASELINE = '7646e0962afab6cc4f566439bb2f96890ae4b91e'
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


def contract_snapshot() -> tuple[dict, dict, dict[str, str]]:
    raw = ISSUE_SNAPSHOT.read_bytes()
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
    if quality.get('manifest_path') != str(OWNED.relative_to(ROOT) / 'evidence-quality.json'):
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
    _, spec, pins = contract_snapshot()

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
    for key, expected in prior_pins.items():
        commit, separator, path = key.partition(':')
        if not separator or commit != ORIGINAL_BASELINE or not re.fullmatch(r'[a-f0-9]{64}', expected):
            raise ValueError(f'malformed historical source pin: {key}')
        if sha(git_file(commit, path)) != expected:
            raise ValueError(f'historical source pin changed: {key}')
    for path, expected in pins.items():
        raw = git_file(PINNED_COMMIT, path)
        if sha(raw) != expected:
            raise ValueError(f'issue pin differs from immutable Git bytes: {PINNED_COMMIT}:{path}')

    # Bind actual filesystem bytes once, then give only those frozen bytes to
    # a private working packet. The old builder never reopens mutable originals.
    actual_paths = [OLD_SCOPE, OLD_ISSUE_SNAPSHOT, BUILDER, GEOMETRY, DETAIL, SUMMARY]
    frozen = {}
    reader = read_input or (lambda path: path.read_bytes())
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
    current_issue = json.loads(ISSUE_SNAPSHOT.read_bytes())
    body_match = WORK_RE.findall(current_issue.get('body') or '')
    current_spec = json.loads(body_match[0])
    quality = current_spec['evidence_quality']
    subjects = quality['subject_ids']
    if sorted(embedded_scope.get('member_location_ids', [])) != sorted(subjects):
        raise ValueError('pinned historical scope differs from the exact 224 scoped subjects')

    # The helper is executed from the verified Git blob; verify its on-disk copy
    # only to ensure the checkout still represents the recorded source bytes.
    return {'runner': runner, 'issue_snapshot': {'path': str(ISSUE_SNAPSHOT.relative_to(ROOT)),
            'sha256': ISSUE_SNAPSHOT_SHA256, 'bytes': ISSUE_SNAPSHOT.stat().st_size},
            'issue_spec': current_spec, 'issue_pins': pins, 'historical_pins': prior_pins,
            'frozen': frozen, 'inputs': input_records,
            'subjects': subjects, 'subject_count': len(subjects),
            'subject_ids_sha256': hashlib.sha256('\n'.join(sorted(subjects)).encode()).hexdigest(),
            'issue_snapshot_retrieved_at': current_issue.get('updated_at'),
            'pinned_commit': PINNED_COMMIT, 'historical_baseline': ORIGINAL_BASELINE}


def safe_destination(output: str | Path) -> Path:
    raw = str(output)
    lexical = PurePosixPath(raw)
    parts = raw.split('/')
    if '\\' in raw or '\0' in raw or lexical.is_absolute() or any(part in ('', '.', '..') for part in parts):
        raise ValueError('output path must be relative and contain no empty, dot or traversal component')
    if not parts or parts[0] != 'evidence' or len(parts) < 2:
        raise ValueError('output must stay below this packet evidence directory')
    evidence = EVIDENCE.resolve(strict=True)
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


def build_private(frozen: dict, scratch: Path) -> Path:
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
    module.build(ORIGINAL_BASELINE, output, geometry)
    produced = {path.name for path in output.iterdir() if path.is_file()}
    if produced != set(FILES):
        raise ValueError(f'historical builder produced an unexpected file set: {sorted(produced)}')
    for name in FILES:
        if (output / name).is_symlink() or not (output / name).is_file():
            raise ValueError(f'historical builder output is not an ordinary file: {name}')
    summary_doc = json.loads((output / FILES[0]).read_bytes())
    rows = list(csv.DictReader((output / FILES[2]).open(encoding='utf-8', newline='')))
    ids = [row['id'] for row in rows]
    if len(ids) != 224 or len(set(ids)) != 224 or sorted(ids) != sorted(load_subjects()):
        raise ValueError('generated output no longer has the exact 224 unique issue subjects')
    if summary_doc.get('metrics', {}).get('scoped_subject_count') != 224:
        raise ValueError('historical report subject count differs from the exact issue scope')
    return output


def load_subjects() -> list[str]:
    _, spec, _ = contract_snapshot()
    return spec['evidence_quality']['subject_ids']


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
        products = build_private(verified['frozen'], Path(temporary))
        destination = safe_destination(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination = safe_destination(output)
        record = {
            'issue': 1209,
            'runner': verified['runner'],
            'pinned_commit': verified['pinned_commit'],
            'historical_baseline': verified['historical_baseline'],
            'issue_snapshot': verified['issue_snapshot'],
            'issue_snapshot_retrieved_at': verified['issue_snapshot_retrieved_at'],
            'subject_count': verified['subject_count'],
            'subject_ids_sha256': verified['subject_ids_sha256'],
            'issue_pin_count': len(verified['issue_pins']),
            'historical_pin_count': len(verified['historical_pins']),
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
    record = run(f'evidence/runs/2026-10-06/{args.run_id}')
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
