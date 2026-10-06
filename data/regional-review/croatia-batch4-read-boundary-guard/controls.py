#!/usr/bin/env python3
"""Run exact-positive and in-memory read-boundary rejection controls."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

import reproduce

ROOT = reproduce.ROOT
OWNED = reproduce.OWNED
EVIDENCE = reproduce.EVIDENCE


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def compact_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def injected_run(label: str, overrides: dict[str, bytes], required_reads: set[str]) -> dict:
    marker = f'evidence/.controls-{label}/must-not-exist'
    seen = []

    def reader(path: Path) -> bytes:
        name = str(path)
        seen.append(name)
        if name in overrides:
            return overrides[name]
        return path.read_bytes()

    parent = OWNED / f'evidence/.controls-{label}'
    target = parent / 'must-not-exist'
    if parent.exists():
        raise FileExistsError(f'control scratch path already exists: {parent}')
    try:
        reproduce.run(marker, read_input=reader)
    except ValueError as error:
        rejected = str(error)
    else:
        raise AssertionError(f'{label} mutated-input control unexpectedly succeeded')
    if target.exists() or parent.exists():
        raise AssertionError(f'{label} rejection created an output path')
    expected = {str(ROOT / path) for path in required_reads}
    if not expected.issubset(seen):
        raise AssertionError(f'{label} did not reach all intended input boundaries: {expected - set(seen)}')
    return {'id': label, 'outcome': 'passed', 'rejection': rejected,
            'fixture_hashes': {name: sha(raw) for name, raw in overrides.items()},
            'input_boundaries_read': sorted(Path(name).relative_to(ROOT).as_posix() for name in seen),
            'output_path_created': False}


def coherent_parent_fixture() -> tuple[bytes, bytes]:
    scope_raw = (ROOT / reproduce.OLD_SCOPE).read_bytes()
    snapshot_raw = (ROOT / reproduce.OLD_ISSUE_SNAPSHOT).read_bytes()
    old = b'"name": "Zagreb County"'
    new = b'"name": "AUDITOR_SYNTHETIC_PARENT_LABEL"'
    if scope_raw.count(old) != 1:
        raise AssertionError('expected exactly one first-province name field in saved scope')
    scope_fixture = scope_raw.replace(old, new, 1)

    snapshot = json.loads(snapshot_raw)
    match = reproduce.ISSUE_SCOPE_RE.search(snapshot.get('body') or '')
    if not match:
        raise AssertionError('saved #1194 issue snapshot has no exact scope block')
    embedded = match.group(1)
    if embedded.count('"name":"Zagreb County"') != 1:
        raise AssertionError('expected one first-province name in embedded compact scope')
    altered = embedded.replace('"name":"Zagreb County"',
                               '"name":"AUDITOR_SYNTHETIC_PARENT_LABEL"', 1)
    altered_scope = json.loads(altered)
    if altered_scope != json.loads(scope_fixture):
        raise AssertionError('synthetic scope and issue snapshot fixture are not coherent')

    # Replace the exact escaped embedded JSON in the original API bytes. This
    # leaves every other API response byte intact and creates no disk mutation.
    escaped_old = json.dumps(embedded, ensure_ascii=False)[1:-1].encode('utf-8')
    escaped_new = json.dumps(altered, ensure_ascii=False)[1:-1].encode('utf-8')
    if snapshot_raw.count(escaped_old) != 1:
        raise AssertionError('cannot bind the exact embedded API scope bytes')
    snapshot_fixture = snapshot_raw.replace(escaped_old, escaped_new, 1)
    check = json.loads(snapshot_fixture)
    check_match = reproduce.ISSUE_SCOPE_RE.search(check.get('body') or '')
    if not check_match or json.loads(check_match.group(1)) != json.loads(scope_fixture):
        raise AssertionError('captured coherent API fixture no longer matches the scope bytes')
    return scope_fixture, snapshot_fixture


def run_controls() -> dict:
    issue_inputs = reproduce.load_inputs()
    original = issue_inputs['frozen']
    old_scope_key = str(reproduce.OLD_SCOPE)
    old_snapshot_key = str(reproduce.OLD_ISSUE_SNAPSHOT)
    builder_key = str(reproduce.BUILDER)
    detail_key = str(reproduce.DETAIL)

    pair_scope, pair_snapshot = coherent_parent_fixture()
    pair = injected_run('coherent-parent-label-drift', {
        str(ROOT / old_scope_key): pair_scope,
        str(ROOT / old_snapshot_key): pair_snapshot,
    }, {old_scope_key, old_snapshot_key})
    scope_only = injected_run('scope-only-drift', {
        str(ROOT / old_scope_key): pair_scope,
    }, {old_scope_key, old_snapshot_key})
    request_doc = json.loads(original[old_snapshot_key])
    request_doc['title'] = request_doc['title'] + ' [synthetic snapshot drift]'
    request_fixture = (json.dumps(request_doc, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    snapshot_only = injected_run('issue-snapshot-only-drift', {
        str(ROOT / old_snapshot_key): bytes(request_fixture),
    }, {old_scope_key, old_snapshot_key})
    code_fixture = bytearray(original[builder_key])
    code_fixture[0] ^= 1
    code_only = injected_run('builder-code-drift', {
        str(ROOT / builder_key): bytes(code_fixture),
    }, {old_scope_key, old_snapshot_key, builder_key})
    data_fixture = bytearray(original[detail_key])
    data_fixture[0] ^= 1
    source_only = injected_run('source-extract-drift', {
        str(ROOT / detail_key): bytes(data_fixture),
    }, {old_scope_key, old_snapshot_key, detail_key})

    run_one = reproduce.run('evidence/runs/2026-10-06/run-1')
    run_two = reproduce.run('evidence/runs/2026-10-06/run-2')
    historical = {}
    for name in reproduce.FILES:
        prior_one = reproduce.git_file(reproduce.PINNED_COMMIT,
            f'data/regional-review/croatia-batch4-reproduction-419-erratum/evidence/run-1/{name}')
        prior_two = reproduce.git_file(reproduce.PINNED_COMMIT,
            f'data/regional-review/croatia-batch4-reproduction-419-erratum/evidence/run-2/{name}')
        current_one = (OWNED / 'evidence/runs/2026-10-06/run-1' / name).read_bytes()
        current_two = (OWNED / 'evidence/runs/2026-10-06/run-2' / name).read_bytes()
        if current_one != current_two or current_one != prior_one or current_two != prior_two:
            raise AssertionError(f'{name} differs from original byte-identical reports')
        historical[name] = {'sha256': sha(current_one), 'bytes': len(current_one),
                            'matches_retained_run_1': True, 'matches_retained_run_2': True}

    with tempfile.TemporaryDirectory(prefix='.controls-', dir=OWNED) as temp:
        sentinel_dir = Path(temp) / 'sentinel-run'
        sentinel_dir.mkdir()
        sentinel = sentinel_dir / 'sentinel.txt'
        sentinel.write_bytes(b'preserve this existing output')
        sentinel_hash = sha(sentinel.read_bytes())
        try:
            reproduce.run(str(sentinel_dir.relative_to(OWNED)))
        except FileExistsError:
            pass
        else:
            raise AssertionError('existing output directory was not rejected')
        if sha(sentinel.read_bytes()) != sentinel_hash:
            raise AssertionError('existing output sentinel changed')
        existing_output = {'outcome': 'passed', 'sentinel_sha256': sentinel_hash,
                           'preserved': True}

        unsafe_rejected = False
        try:
            reproduce.safe_destination('evidence/../outside')
        except ValueError:
            unsafe_rejected = True
        if not unsafe_rejected:
            raise AssertionError('traversal destination was accepted')

        partial = Path(temp) / 'partial-output'
        products = Path(temp) / 'products'
        products.mkdir()
        for name in reproduce.FILES:
            (products / name).write_bytes(b'controlled output ' + name.encode())
        try:
            reproduce.publish_exclusive(products, partial, {'control': 'interrupted'}, interrupt_after=1)
        except RuntimeError:
            pass
        else:
            raise AssertionError('interruption control did not interrupt publication')
        partial_bytes = (partial / reproduce.FILES[0]).read_bytes()
        partial_hash = sha(partial_bytes)
        try:
            reproduce.publish_exclusive(products, partial, {'control': 'retry'})
        except FileExistsError:
            pass
        else:
            raise AssertionError('interrupted output name was overwritten')
        if sha((partial / reproduce.FILES[0]).read_bytes()) != partial_hash:
            raise AssertionError('interrupted output bytes changed during retry')
        interrupted_output = {'outcome': 'passed', 'preserved_files': [reproduce.FILES[0]],
                              'preserved_sha256': partial_hash, 'retry_refused': True}

    return {
        'version': 1,
        'issue': 1209,
        'runner_head': issue_inputs['runner']['commit'],
        'manifest_scope': 'exactly 224 Croatia #1199 subjects; read-boundary integrity only',
        'positive_runs': [run_one, run_two],
        'historical_output_comparison': historical,
        'negative_controls': [pair, scope_only, snapshot_only, code_only, source_only],
        'existing_output_control': existing_output,
        'unsafe_path_control': {'outcome': 'passed', 'traversal_rejected_before_reads': True},
        'interrupted_output_control': interrupted_output,
        'limits': [
            'The coherent synthetic parent-name fixture is a byte-integrity trigger, not evidence that any original Croatia parent label is wrong.',
            'These runs do not establish legal municipal boundaries, census-date geometry, official parentage, coast/island completeness or countrywide roster completeness.',
            'The source/license and factual limits recorded by the preserved #1199 packet remain in force; this correction adds no new source finding.'
        ]
    }


if __name__ == '__main__':
    result = run_controls()
    output = EVIDENCE / 'validation/controls.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())
    print(json.dumps({'control_file': str(output.relative_to(ROOT)), 'sha256': sha(output.read_bytes()),
                      'positive_runs': len(result['positive_runs']),
                      'negative_controls': len(result['negative_controls'])}, sort_keys=True))
