#!/usr/bin/env python3
"""Fresh, named full-run and non-vacuous provenance controls for issue #1396."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

import reproduce

ROOT, OWNED, EVIDENCE = reproduce.ROOT, reproduce.OWNED, reproduce.EVIDENCE


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_control_code() -> dict:
    head = reproduce.git('rev-parse', 'HEAD').decode().strip()
    relative = str(Path(__file__).resolve().relative_to(ROOT))
    committed = reproduce.git_file(head, relative)
    actual = Path(__file__).resolve().read_bytes()
    if actual != committed:
        raise ValueError('executed controls differ from their immutable HEAD blob')
    row = reproduce.git('ls-tree', head, '--', relative).decode().strip()
    return {'path': relative, 'commit': head, 'git_blob': row.split()[2],
            'sha256': sha(committed), 'bytes': len(committed)}


def write_exclusive(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()


def validate_run_record(record: dict, directory: Path, expected: dict) -> None:
    """Reject incomplete prior receipts before treating their reports as evidence."""
    if not isinstance(record, dict):
        raise ValueError('run receipt is not an object')
    if record.get('issue') != 1209 or record.get('subject_count') != 224:
        raise ValueError('run receipt has the wrong issue or exact subject count')
    if record.get('subject_ids_sha256') != expected['subject_ids_sha256']:
        raise ValueError('run receipt subject identity digest differs from the captured scope')
    if record.get('issue_pin_count') != 66 or record.get('historical_pin_count') != 62:
        raise ValueError('run receipt omits complete issue or historical pin coverage')
    if record.get('verified_source_count') != 80 or len(record.get('verified_sources', [])) != 80:
        raise ValueError('run receipt omits the complete 80-object source inventory')
    if record.get('verified_sources') != expected['verified_sources']:
        raise ValueError('run receipt source paths, vintages or exact hashes differ from the verified input map')
    if record.get('unique_original_bytes') != expected['unique_original_bytes']:
        raise ValueError('run receipt original-source budget differs from verified inputs')
    admission = record.get('execution_admission')
    if not isinstance(admission, dict) or admission.get('unique_original_bytes') != expected['unique_original_bytes'] or \
       admission.get('decoded_xlsx_member_bytes') != expected['planned_decoded_xlsx_bytes'] or \
       admission.get('additional_artifact_allowance_bytes') != reproduce.ADDITIONAL_ARTIFACT_ALLOWANCE or \
       admission.get('admitted_total_bytes') != admission.get('unique_original_bytes') + \
            admission.get('decoded_xlsx_member_bytes') + admission.get('additional_artifact_allowance_bytes') or \
       admission.get('admitted_total_bytes') > reproduce.MAX_PHASE_BYTES or \
       admission.get('limit_bytes') != reproduce.MAX_PHASE_BYTES:
        raise ValueError('run receipt does not prove complete pre-computation phase admission')
    if record.get('runner') != expected['runner']:
        raise ValueError('run receipt does not bind the exact executing runner')
    for field, expected_value in (
        ('pinned_commit', reproduce.PINNED_COMMIT),
        ('historical_baseline', reproduce.ORIGINAL_BASELINE),
    ):
        if record.get(field) != expected_value:
            raise ValueError(f'run receipt {field} is missing or changed')
    snapshot = record.get('issue_snapshot')
    retrieval = record.get('issue_snapshot_retrieval')
    if not isinstance(snapshot, dict) or not isinstance(retrieval, dict):
        raise ValueError('run receipt omits separate issue snapshot and retrieval evidence')
    if snapshot != expected['issue_snapshot'] or retrieval != expected['issue_snapshot_retrieval']:
        raise ValueError('run receipt issue snapshot/update time or retrieval receipt changed')
    if record.get('issue_updated_at') != snapshot.get('updated_at'):
        raise ValueError('run receipt mislabels issue update time')
    if record.get('issue_retrieved_at') != retrieval.get('retrieved_at'):
        raise ValueError('run receipt mislabels retrieval time')
    job_snapshot = record.get('job_snapshot')
    job_retrieval = record.get('job_snapshot_retrieval')
    if job_snapshot != expected['job_snapshot'] or job_retrieval != expected['job_snapshot_retrieval']:
        raise ValueError('run receipt issue #1396 contract provenance is incomplete')
    inputs = record.get('inputs')
    expected_inputs = {row['path']: row for row in expected['inputs']}
    if not isinstance(inputs, list) or len(inputs) != len(expected_inputs):
        raise ValueError('run receipt does not declare the complete consumed input list')
    actual_inputs = {row.get('path'): row for row in inputs if isinstance(row, dict)}
    if set(actual_inputs) != set(expected_inputs) or len(actual_inputs) != len(inputs):
        raise ValueError('run receipt consumed input coverage is incomplete or duplicated')
    if actual_inputs != expected_inputs:
        raise ValueError('run receipt consumed input pins do not match verified bytes')
    decoded = record.get('decoded_xlsx_members')
    if not isinstance(decoded, list) or not decoded or sum(row.get('bytes', -1) for row in decoded) != record.get('decoded_xlsx_bytes'):
        raise ValueError('run receipt omits actual decoded workbook member provenance')
    if any(not re.fullmatch(r'[a-f0-9]{64}', row.get('sha256', '')) or row.get('bytes', 0) < 0 or
           row.get('bytes', 0) > 32 * 1024 * 1024 for row in decoded):
        raise ValueError('run receipt has invalid decoded workbook member hashes or sizes')
    names = [row.get('member') for row in decoded]
    consumed = record.get('actually_consumed_xlsx_members')
    member_hashes = {row['member']: row['sha256'] for row in decoded}
    if len(names) != len(set(names)) or not isinstance(consumed, list) or not consumed or any(
        row.get('member') not in member_hashes or member_hashes[row['member']] != row.get('sha256') for row in consumed
    ):
        raise ValueError('run receipt lacks a complete unique decoded member set or actual-use binding')
    outputs = record.get('outputs')
    if not isinstance(outputs, dict) or set(outputs) != set(reproduce.FILES):
        raise ValueError('run receipt must bind the exact complete report output set')
    for name in reproduce.FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'run report output is missing or not an ordinary file: {name}')
        if outputs[name] != sha(path.read_bytes()):
            raise ValueError(f'run report output hash differs from receipt: {name}')


def altered_record_controls(record: dict, directory: Path, expected: dict) -> list[dict]:
    cases = []
    alterations = [
        ('empty-outputs', lambda row: row.update(outputs={})),
        ('empty-inputs', lambda row: row.update(inputs=[])),
        ('zero-subjects', lambda row: row.update(subject_count=0, subject_ids_sha256='0' * 64)),
        ('missing-pin-coverage', lambda row: row.update(issue_pin_count=0, historical_pin_count=0)),
        ('mislabelled-snapshot-time', lambda row: row.update(issue_updated_at='1900-01-01T00:00:00Z')),
        ('missing-source-inventory', lambda row: row.update(verified_sources=[], verified_source_count=0)),
    ]
    for label, alter in alterations:
        fixture = json.loads(json.dumps(record))
        alter(fixture)
        try:
            validate_run_record(fixture, directory, expected)
        except ValueError as error:
            cases.append({'id': label, 'outcome': 'passed', 'rejection': str(error),
                          'fixture_sha256': sha((json.dumps(fixture, sort_keys=True) + '\n').encode())})
        else:
            raise AssertionError(f'incomplete {label} run-record fixture was accepted')
    return cases


def snapshot_mutation_control(run_id: str) -> dict:
    original = reproduce.ISSUE_SNAPSHOT.read_bytes()
    changed = json.loads(original)
    changed['updated_at'] = '1900-01-01T00:00:00Z'
    fixture = json.dumps(changed, ensure_ascii=False, separators=(',', ':')).encode()
    seen = []

    def reader(path: Path) -> bytes:
        if path == reproduce.ISSUE_SNAPSHOT:
            seen.append(str(path))
            return fixture
        return path.read_bytes()

    target = f'evidence/runs/{run_id}/snapshot-mutation-must-not-publish'
    try:
        reproduce.run(target, read_input=reader)
    except ValueError as error:
        created = (OWNED / target).exists()
        if created or len(seen) != 1:
            raise AssertionError('mutated snapshot was read repeatedly or created output before rejection')
        return {'id': 'single-captured-snapshot-authentication', 'outcome': 'passed',
                'fixture_bytes': len(fixture), 'fixture_sha256': sha(fixture),
                'read_count': len(seen), 'rejection': str(error), 'output_created': False}
    raise AssertionError('complete changed issue snapshot unexpectedly passed authentication')


def path_and_writer_controls() -> dict:
    with tempfile.TemporaryDirectory(prefix='.controls-', dir=EVIDENCE) as temporary:
        root = Path(temporary)
        sentinel_dir = root / 'sentinel-run'
        sentinel_dir.mkdir()
        sentinel = sentinel_dir / 'sentinel.txt'
        sentinel.write_bytes(b'preserve this existing output')
        sentinel_hash = sha(sentinel.read_bytes())
        try:
            reproduce.run(sentinel_dir.relative_to(OWNED).as_posix())
        except FileExistsError:
            pass
        else:
            raise AssertionError('existing output directory was not rejected')
        if sha(sentinel.read_bytes()) != sentinel_hash:
            raise AssertionError('existing output sentinel changed')

        rejected = []
        for unsafe in ('evidence/../outside', 'evidence//empty', '/tmp/outside', 'evidence/a\\b'):
            try:
                reproduce.safe_destination(unsafe)
            except ValueError:
                rejected.append(unsafe)
        if len(rejected) != 4:
            raise AssertionError('traversal or malformed output path was accepted')
        ordinary = root / 'ordinary-file'
        ordinary.write_text('not a directory')
        link = OWNED / 'evidence' / f'.control-symlink-{root.name}'
        if link.exists() or link.is_symlink():
            raise FileExistsError('symlink control path already exists')
        link.symlink_to(root, target_is_directory=True)
        try:
            try:
                reproduce.safe_destination(f'evidence/{link.name}/escape')
            except ValueError:
                pass
            else:
                raise AssertionError('symlink parent path was accepted')
        finally:
            link.unlink()

        partial = root / 'partial-output'
        products = root / 'products'
        products.mkdir()
        for name in reproduce.FILES:
            (products / name).write_bytes(b'controlled output ' + name.encode())
        try:
            reproduce.publish_exclusive(products, partial, {'control': 'interrupted'}, interrupt_after=1)
        except RuntimeError:
            pass
        else:
            raise AssertionError('interruption control did not interrupt publication')
        first = partial / reproduce.FILES[0]
        partial_hash = sha(first.read_bytes())
        try:
            reproduce.publish_exclusive(products, partial, {'control': 'retry'})
        except FileExistsError:
            pass
        else:
            raise AssertionError('interrupted output name was overwritten')
        if sha(first.read_bytes()) != partial_hash:
            raise AssertionError('interrupted output bytes changed during retry')
    return {'outcome': 'passed', 'existing_output_preserved': True,
            'unsafe_paths_rejected': rejected, 'symlink_parent_rejected': True,
            'partial_failure_preserved': True, 'retry_refused': True,
            'sentinel_sha256': sentinel_hash, 'partial_output_sha256': partial_hash}


def prior_table_evidence(expected: dict, run_id: str) -> tuple[dict, dict]:
    """Load the exact pinned prior manifest/ledger and retarget only output names."""
    prefix = 'data/regional-review/croatia-batch4-read-boundary-guard/'
    manifest_path = prefix + 'evidence-quality.json'
    ledger_path = prefix + 'evidence/validation/2026-10-06-final/rendered-table-ledger.json'
    indexed = {(row['commit'], row['path']): row for row in expected['verified_sources']}
    for path in (manifest_path, ledger_path):
        matches = [row for row in indexed.values() if row['path'] == path]
        if len(matches) != 1:
            raise ValueError(f'prior generated-table provenance is not uniquely present in the complete input map: {path}')
    manifest_pin = next(row for row in indexed.values() if row['path'] == manifest_path)
    ledger_pin = next(row for row in indexed.values() if row['path'] == ledger_path)
    prior_manifest_raw = reproduce.git_file(manifest_pin['commit'], manifest_path)
    prior_ledger_raw = reproduce.git_file(ledger_pin['commit'], ledger_path)
    if sha(prior_manifest_raw) != manifest_pin['sha256'] or sha(prior_ledger_raw) != ledger_pin['sha256']:
        raise ValueError('prior metric/table evidence differs from the exact issue pin map')
    prior_manifest, prior_ledger = json.loads(prior_manifest_raw), json.loads(prior_ledger_raw)
    expected_ids = {metric['id'] for metric in prior_manifest.get('metrics', [])}
    if len(expected_ids) != 232 or len(prior_ledger.get('rows', [])) != 464:
        raise ValueError('prior result ledger no longer covers both complete retained report vintages')
    old_prefix = prefix + 'evidence/runs/2026-10-06/'
    new_prefix = str(OWNED.relative_to(ROOT)) + f'/evidence/runs/{run_id}/'
    for row in prior_ledger['rows']:
        if not row.get('path', '').startswith(old_prefix):
            raise ValueError('prior table ledger points outside the retained run vintages')
        row['path'] = new_prefix + row['path'][len(old_prefix):]
    prior_ledger['issue'] = 1396
    prior_ledger['method_id'] = 'croatia-run-provenance-controls'
    return prior_manifest, prior_ledger


def run_controls(run_id: str) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,62}', run_id):
        raise ValueError('run ID must use 1-63 ASCII letters, digits, underscores or hyphens')
    control_runner = verify_control_code()
    report_one = f'evidence/runs/{run_id}/run-1'
    report_two = f'evidence/runs/{run_id}/run-2'
    validation = EVIDENCE / 'validation' / run_id
    for relative in (report_one, report_two):
        reproduce.safe_destination(relative)
    if validation.exists() or validation.is_symlink():
        raise FileExistsError('control validation destination exists; use a fresh --run-id')

    # Two physical calls to the report runner create new outputs in this named vintage.
    snapshot_reads = []
    def track_snapshot(path: Path) -> bytes:
        if path == reproduce.ISSUE_SNAPSHOT:
            snapshot_reads.append(str(path))
        return path.read_bytes()
    one = reproduce.run(report_one, read_input=track_snapshot)
    two = reproduce.run(report_two)
    if len(snapshot_reads) != 1:
        raise AssertionError('actual first full report execution did not consume one captured issue snapshot')
    expected = reproduce.load_inputs()
    one_dir, two_dir = OWNED / report_one, OWNED / report_two
    validate_run_record(one, one_dir, expected)
    validate_run_record(two, two_dir, expected)
    historical = {}
    for name in reproduce.FILES:
        old_one_path = f'data/regional-review/croatia-batch4-reproduction-419-erratum/evidence/run-1/{name}'
        old_two_path = f'data/regional-review/croatia-batch4-reproduction-419-erratum/evidence/run-2/{name}'
        prior_one = reproduce.git_file(reproduce.PINNED_COMMIT, old_one_path)
        prior_two = reproduce.git_file(reproduce.PINNED_COMMIT, old_two_path)
        current_one, current_two = (one_dir / name).read_bytes(), (two_dir / name).read_bytes()
        if current_one != current_two or current_one != prior_one or current_two != prior_two:
            raise AssertionError(f'{name} differs from byte-identical fresh and historical results')
        historical[name] = {'bytes': len(prior_one), 'sha256': sha(prior_one),
                            'matches_fresh_run_1': True, 'matches_fresh_run_2': True,
                            'matches_retained_historical_run_1': True,
                            'matches_retained_historical_run_2': True}

    prior_manifest, rendered_ledger = prior_table_evidence(expected, run_id)

    single_read = snapshot_mutation_control(run_id)
    malformed = altered_record_controls(one, one_dir, expected)
    path_controls = path_and_writer_controls()
    combined_one = sha(b''.join((one_dir / name).read_bytes() for name in reproduce.FILES))
    combined_two = sha(b''.join((two_dir / name).read_bytes() for name in reproduce.FILES))
    if combined_one != combined_two:
        raise AssertionError('fresh full report output sets differ')
    result = {
        'version': 1, 'issue': 1396, 'method_id': 'croatia-run-provenance-controls',
        'kind': 'positive-control', 'outcome': 'passed',
        'run_id': run_id, 'runner_head': expected['runner']['commit'],
        'control_runner': control_runner,
        'manifest_scope': 'exactly the 224 Croatia #1199 subjects; mechanical provenance only',
        'first_fresh_run_snapshot_read_count': len(snapshot_reads),
        'prior_metric_inventory': {'metric_count': len(prior_manifest.get('metrics', [])),
                                   'rendered_table_rows': len(rendered_ledger.get('rows', [])),
                                   'evaluation_vintage': 'retained #1199/#1209 result values; baseline, not a new geographic finding'},
        'positive_runs': [one, two], 'historical_output_comparison': historical,
        'snapshot_mutation_control': single_read, 'malformed_receipt_controls': malformed,
        'path_and_writer_controls': path_controls,
        'validation_records': {
            'positive-control': {'method_id': 'croatia-run-provenance-controls', 'kind': 'positive-control',
                                 'outcome': 'passed', 'fresh_run_count': 2,
                                 'complete_report_receipts': True},
            'negative-control': {'method_id': 'croatia-run-provenance-controls', 'kind': 'negative-control',
                                 'outcome': 'passed', 'altered_record_case_count': len(malformed) + 1,
                                 'source_snapshot_mutation_rejected': True,
                                 'unsafe_and_interrupted_outputs_preserved': True},
            'reproducibility': {'method_id': 'croatia-run-provenance-controls', 'kind': 'reproducibility',
                                'outcome': 'passed', 'run_one_sha256': combined_one,
                                'run_two_sha256': combined_two}
        },
        'limits': [
            'The complete issue snapshot mutation is a synthetic integrity fixture, not a geographic correction.',
            'Fresh reports are mechanical reproductions of previously reviewed Croatia results; they add no independent territorial finding.',
            'DZS/DGU/legal authority, municipality-to-county parentage, census-date polygons, islands/coast completeness, four name candidates, seven roster gaps and geoBoundaries file-specific grant remain unresolved.'
        ]
    }
    validation.mkdir(parents=True, exist_ok=False)
    ledger_raw = (json.dumps(rendered_ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    ledger_path = validation / 'rendered-table-ledger.json'
    write_exclusive(ledger_path, ledger_raw)
    result['rendered_table_ledger'] = {'path': str(ledger_path.relative_to(ROOT)),
                                       'bytes': len(ledger_raw), 'sha256': sha(ledger_raw)}
    for kind, record in result['validation_records'].items():
        write_exclusive(validation / f'{kind}.json',
                        (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())
    result.pop('validation_records')
    # Install the full result last; its presence marks successful control completion.
    output = validation / 'controls.json'
    write_exclusive(output, (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())
    result['control_file'] = str(output.relative_to(ROOT))
    result['control_sha256'] = sha(output.read_bytes())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True,
                        help='fresh safe name for all report runs and control receipts')
    args = parser.parse_args()
    print(json.dumps(run_controls(args.run_id), ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
