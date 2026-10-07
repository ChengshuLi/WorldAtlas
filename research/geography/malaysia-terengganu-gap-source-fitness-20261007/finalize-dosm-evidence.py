#!/usr/bin/env python3
"""Bind completed DOSM comparison runs to premerge control receipts.

This small finalizer does no geometry work. It accepts only the two expected
fresh run outputs and their execution receipts, checks their byte bindings,
source/runtime/producer identities and controls, then writes deterministic
method-specific positive, negative and reproducibility evidence.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OWNED = 'research/geography/malaysia-terengganu-gap-source-fitness-20261007'
VINTAGE = OWNED + '/vintages/20261007-dosm-r7/'
METHOD = 'terengganu-dosm-source-generator-r7'
PRODUCER = OWNED + '/reproduce-dosm.py'
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
EXPECTED_CONTACTS = [
    'gb:MYS:ADM2:92858781B15989569853600',
    'gb:MYS:ADM2:92858781B44112931825428',
    'gb:MYS:ADM2:92858781B50781472629025',
    'gb:MYS:ADM2:92858781B66748088999576',
    'gb:MYS:ADM2:92858781B69735571651191',
    'gb:MYS:ADM2:92858781B78340444844195',
    'gb:MYS:ADM2:92858781B85628090125570',
]
EXPECTED_NUMERIC_CLOSURE = [
    EXPECTED_COMPONENTS[1], EXPECTED_COMPONENTS[5], EXPECTED_COMPONENTS[7],
]
EXPECTED_SOURCE = {
    'id': 'dosm-open-data-malaysia-adm2',
    'repository_commit': 'b057365ccbf26cbe3db1c043668f6a0efe811cb2',
    'repository_path': 'datasets/geodata/administrative_2_district.geojson',
    'repository_blob': '5dc846b26ca0fb5fc2f9c1fb33abf1c800ee0f88',
    'retained_path': OWNED + '/sources/dosm-data-open-b057365/administrative_2_district.geojson',
    'bytes': 947755,
    'sha256': '3edb1022b2de371bba6b7afb9802b6fc6d747c86dbcc40abf2374a9134f3c561',
    'license_path': OWNED + '/sources/dosm-data-open-b057365/LICENSE.md',
    'license_sha256': '9633cc27c1cd18bed2f088aeb637a048e3688aeafdf85d70b72c38c2a1c16d02',
    'feature_count': 160,
    'crs': 'urn:ogc:def:crs:OGC:1.3:CRS84',
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


MAX_FILE_BYTES = 32 * 1024 * 1024


def bounded_read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Evidence input must be an ordinary non-symlink file')
    try:
        relative = path.absolute().relative_to(ROOT.absolute())
    except ValueError:
        relative = None
    if relative is not None:
        for ancestor in (ROOT / relative, *(ROOT / relative).parents):
            if ancestor == ROOT.parent:
                break
            if ancestor.is_symlink():
                raise ValueError('Symlink in evidence input path')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise ValueError('Evidence input is not an ordinary bounded file')
        chunks, remaining = [], MAX_FILE_BYTES + 1
        while remaining:
            block = os.read(fd, min(1024 * 1024, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        raw = b''.join(chunks)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('Evidence input exceeds byte budget')
        return raw
    finally:
        os.close(fd)


def exclusive_write(path, raw):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o644)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            view = view[count:]
    finally:
        os.close(fd)


def atomic_replace_regular(path, raw):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Evidence manifest must be an ordinary file')
    fd, temp_name = tempfile.mkstemp(prefix='.evidence-quality-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode()


def read_json(relative):
    return json.loads(bounded_read(ROOT / relative))


def finalize():
    run_paths = [VINTAGE + 'run-one.json', VINTAGE + 'run-two.json']
    receipt_paths = [VINTAGE + 'execution-one.json', VINTAGE + 'execution-two.json']
    runs, receipts, run_hashes = [], [], []
    for run_path, receipt_path in zip(run_paths, receipt_paths):
        run_raw = bounded_read(ROOT / run_path)
        receipt = read_json(receipt_path)
        run = json.loads(run_raw)
        if receipt.get('status') != 'completed' or receipt.get('issue') != 1408:
            raise ValueError('An execution receipt is missing or incomplete')
        if receipt.get('output_path') != run_path or receipt.get('output_bytes') != len(run_raw) or receipt.get('output_sha256') != sha256(run_raw):
            raise ValueError('Execution receipt does not bind the exact run output bytes')
        if receipt.get('producer_path') != PRODUCER or run.get('code_bindings', {}).get('producer_path') != PRODUCER:
            raise ValueError('Run and receipt do not name the exact DOSM producer')
        if receipt.get('producer_sha256') != run.get('code_bindings', {}).get('producer_sha256'):
            raise ValueError('Run and receipt producer hashes differ')
        if receipt.get('runtime') != run.get('runtime'):
            raise ValueError('Execution receipt runtime differs from generated result')
        if run.get('issue') != 1408 or run.get('family_id') != 'gap-source-batch:bfb3cabaf651a97ffcfa1a76':
            raise ValueError('Unexpected issue or family in generated result')
        if run.get('evidence_manifest_sha256') != receipt.get('evidence_manifest_sha256'):
            raise ValueError('Run and receipt evidence-manifest bindings differ')
        try:
            manifest_raw = base64.b64decode(run['evidence_manifest_snapshot_base64'], validate=True)
        except Exception as error:
            raise ValueError('Run lacks a decodable exact evidence-manifest snapshot') from error
        if sha256(manifest_raw) != run['evidence_manifest_sha256']:
            raise ValueError('Embedded evidence-manifest snapshot does not match its SHA-256')
        manifest = json.loads(manifest_raw)
        producer = next((row for row in manifest.get('outputs', []) if row.get('path') == PRODUCER), None)
        producer_raw = bounded_read(ROOT / PRODUCER)
        if (not producer or producer.get('sha256') != run.get('code_bindings', {}).get('producer_sha256') or
                sha256(producer_raw) != producer.get('sha256')):
            raise ValueError('Execution manifest does not pin the exact producer bytes')
        finalizer_path = Path(__file__).resolve().relative_to(ROOT).as_posix()
        finalizer_pin = next((row for row in manifest.get('outputs', []) if row.get('path') == finalizer_path), None)
        if not finalizer_pin or sha256(bounded_read(Path(__file__))) != finalizer_pin.get('sha256'):
            raise ValueError('Execution manifest does not pin the exact finalizer bytes')
        expected_subjects = set(EXPECTED_COMPONENTS + EXPECTED_CONTACTS)
        subject_hash = sha256(json.dumps(sorted(expected_subjects), separators=(',', ':')).encode())
        if (manifest.get('issue') != 1408 or len(manifest.get('subject_ids', [])) != 15 or
                set(manifest.get('subject_ids', [])) != expected_subjects or manifest.get('subject_ids_sha256') != subject_hash):
            raise ValueError('Execution manifest does not bind the exact 8-component/7-contact subject cohort')
        method = next((row for row in manifest.get('methods', []) if row.get('id') == METHOD), None)
        if not method or method.get('kind') != 'generator' or method.get('helper_version') != 'worldatlas-evidence-preparation-v1':
            raise ValueError('Execution manifest lacks the supported method/helper binding')
        if run.get('baseline_commit') != manifest.get('baseline', {}).get('commit'):
            raise ValueError('Generated result baseline commit differs from execution manifest')
        pinned_baseline = {row.get('path'): row for row in manifest.get('baseline', {}).get('files', [])}
        for helper in run.get('code_bindings', {}).get('baseline_helpers', []):
            baseline_file = pinned_baseline.get(helper.get('path'))
            if not baseline_file or baseline_file.get('sha256') != helper.get('sha256') or baseline_file.get('bytes') != helper.get('bytes'):
                raise ValueError('Generated result baseline helper differs from frozen manifest: ' + str(helper.get('path')))
        if {row.get('path') for row in run.get('code_bindings', {}).get('baseline_helpers', [])} != {
            'scripts/evidence/immutable.py', 'scripts/physical_component_custody.py'
        }:
            raise ValueError('Generated result does not bind both required baseline helpers')
        source_record = next((row for row in manifest.get('sources', []) if row.get('id') == EXPECTED_SOURCE['id']), None)
        if not source_record or source_record.get('retention') != 'retained':
            raise ValueError('Execution manifest does not retain the exact DOSM comparator')
        retained_file = next(iter(source_record.get('files', [])), {})
        license_file = source_record.get('license_file', {})
        if (retained_file.get('path') != EXPECTED_SOURCE['retained_path'] or
                retained_file.get('bytes') != EXPECTED_SOURCE['bytes'] or
                retained_file.get('sha256') != EXPECTED_SOURCE['sha256'] or
                license_file.get('path') != EXPECTED_SOURCE['license_path'] or
                license_file.get('bytes') != 3503 or
                license_file.get('sha256') != EXPECTED_SOURCE['license_sha256']):
            raise ValueError('Execution manifest DOSM source/license file-byte pins differ')
        config_path = OWNED + '/input-config.json'
        config_descriptor = next((row for row in manifest.get('outputs', []) if row.get('path') == config_path), None)
        config_raw = bounded_read(ROOT / config_path)
        if not config_descriptor or config_descriptor.get('bytes') != len(config_raw) or config_descriptor.get('sha256') != sha256(config_raw):
            raise ValueError('Current input-config bytes differ from the execution manifest pin')
        config = json.loads(config_raw)
        configured_source = next((row for row in config.get('retained_sources', []) if row.get('id') == EXPECTED_SOURCE['id']), None)
        if not configured_source:
            raise ValueError('Exact DOSM source is missing from input-config')
        config_source_bindings = {
            'id': 'id',
            'repository_commit': 'repository_commit',
            'repository_path': 'source_path',
            'repository_blob': 'repository_blob',
            'retained_path': 'path',
            'bytes': 'bytes',
            'sha256': 'sha256',
            'license_path': 'license_path',
            'license_sha256': 'license_sha256',
            'feature_count': 'expected_feature_count',
            'crs': 'crs',
        }
        for expected_key, config_key in config_source_bindings.items():
            if configured_source.get(config_key) != EXPECTED_SOURCE[expected_key]:
                raise ValueError('Pinned input-config DOSM source binding differs: ' + config_key)
        if configured_source.get('license_bytes') != 3503:
            raise ValueError('Pinned input-config DOSM license byte count differs')
        for relative, expected_size, expected_hash in (
            (EXPECTED_SOURCE['retained_path'], EXPECTED_SOURCE['bytes'], EXPECTED_SOURCE['sha256']),
            (EXPECTED_SOURCE['license_path'], 3503, EXPECTED_SOURCE['license_sha256']),
        ):
            raw = bounded_read(ROOT / relative)
            if len(raw) != expected_size or sha256(raw) != expected_hash:
                raise ValueError('Retained source/license bytes changed after execution: ' + relative)
        if run.get('source', {}).get('id') != EXPECTED_SOURCE['id']:
            raise ValueError('Generated result names an unexpected comparison source')
        for key in ('repository_commit', 'repository_path', 'repository_blob', 'retained_path', 'bytes', 'sha256', 'license_path', 'license_sha256', 'feature_count', 'crs'):
            if run['source'].get(key) != EXPECTED_SOURCE[key]:
                raise ValueError('Generated result DOSM source binding differs: ' + key)
        rosters = run.get('rosters', {})
        if rosters.get('component_ids') != EXPECTED_COMPONENTS or rosters.get('contact_ids') != EXPECTED_CONTACTS or rosters.get('numeric_closure_component_ids') != EXPECTED_NUMERIC_CLOSURE:
            raise ValueError('Generated result does not preserve the exact 8/7/3 family roster')
        for key in ('baseline_commit', 'evidence_manifest_sha256', 'evidence_manifest_snapshot_base64', 'source', 'rosters', 'code_bindings', 'runtime', 'controls'):
            if runs and run.get(key) != runs[0].get(key):
                raise ValueError('Two runs differ in bound ' + key)
        for kind in ('positive', 'negative'):
            rows = run.get('controls', {}).get(kind)
            if not isinstance(rows, list) or not rows or any(row.get('passed') is not True for row in rows):
                raise ValueError('Missing or failed ' + kind + ' production-loader controls')
        runs.append(run)
        receipts.append(receipt)
        run_hashes.append(sha256(run_raw))
    if run_hashes[0] != run_hashes[1]:
        raise ValueError('Two-run result bytes differ; reproducibility is not established')
    if receipts[0].get('git_head_at_execution') != receipts[1].get('git_head_at_execution'):
        raise ValueError('The two executions used different Git HEAD values')

    outdir = ROOT / (VINTAGE + 'verification')
    if outdir.is_symlink():
        raise ValueError('Verification output directory must not be a symlink')
    outdir.mkdir(parents=True, exist_ok=True)
    common = {
        'version': 1,
        'method_id': METHOD,
        'outcome': 'passed',
        'evidence_manifest_sha256_at_execution': runs[0]['evidence_manifest_sha256'],
        'producer_path': PRODUCER,
        'producer_sha256': runs[0]['code_bindings']['producer_sha256'],
        'baseline_commit': runs[0]['baseline_commit'],
        'source': runs[0]['source'],
        'runtime': runs[0]['runtime'],
        'run_one_sha256': run_hashes[0],
        'run_two_sha256': run_hashes[1],
    }
    artifacts = {
        'positive-control.json': {**common, 'kind': 'positive-control', 'controls': runs[0]['controls']['positive']},
        'negative-control.json': {**common, 'kind': 'negative-control', 'controls': runs[0]['controls']['negative']},
        'reproducibility.json': {**common, 'kind': 'reproducibility'},
    }
    for name, payload in artifacts.items():
        exclusive_write(outdir / name, canonical(payload))
    evidence_path = ROOT / (OWNED + '/evidence-quality.json')
    evidence = json.loads(bounded_read(evidence_path))
    validation_paths = {
        'positive-control': VINTAGE + 'verification/positive-control.json',
        'negative-control': VINTAGE + 'verification/negative-control.json',
        'reproducibility': VINTAGE + 'verification/reproducibility.json',
    }
    registered_paths = run_paths + receipt_paths + list(validation_paths.values())
    dynamic_paths = set(registered_paths)
    execution_manifest = json.loads(base64.b64decode(runs[0]['evidence_manifest_snapshot_base64'], validate=True))
    for key in ('outputs', 'change_receipts'):
        if any(row.get('path') in dynamic_paths for row in execution_manifest.get(key, [])):
            raise ValueError('Execution manifest already contains this fresh DOSM vintage')
        evidence[key] = [row for row in evidence.get(key, []) if row.get('path') not in dynamic_paths]
        evidence[key].sort(key=lambda row: row['path'])
        execution_manifest[key] = sorted(execution_manifest.get(key, []), key=lambda row: row['path'])
    if any(row.get('method_id') == METHOD for row in execution_manifest.get('validation', [])):
        raise ValueError('Execution manifest already contains DOSM validation receipts')
    evidence['validation'] = [row for row in evidence.get('validation', []) if row.get('method_id') != METHOD]
    if canonical(evidence) != canonical(execution_manifest):
        raise ValueError('Evidence manifest changed after the two runs; rerun against the current exact manifest')
    output_rows = {row['path']: row for row in evidence.get('outputs', [])}
    for relative in registered_paths:
        raw = bounded_read(ROOT / relative)
        output_rows[relative] = {
            'path': relative,
            'bytes': len(raw),
            'hash_kind': 'file-bytes',
            'sha256': sha256(raw),
        }
    evidence['outputs'] = sorted(output_rows.values(), key=lambda row: row['path'])
    receipt_rows = {row['path']: row for row in evidence.get('change_receipts', [])}
    for relative in registered_paths:
        receipt_rows.setdefault(relative, {'path': relative, 'status': 'added'})
    evidence['change_receipts'] = sorted(receipt_rows.values(), key=lambda row: row['path'])
    evidence['validation'] = [
        row for row in evidence.get('validation', [])
        if row.get('method_id') != METHOD
    ] + [
        {'method_id': METHOD, 'kind': kind, 'outcome': 'passed', 'evidence_path': path}
        for kind, path in validation_paths.items()
    ]
    run = runs[0]
    summary = run['predicate_summary']
    metric_rows = [
        ('dosm_product_features', 'features', run['source']['feature_count'], '/source/feature_count'),
        ('dosm_invalid_product_features', 'features', run['source']['full_product_invalid_feature_count'], '/source/full_product_invalid_feature_count'),
        ('components_intersecting_any_valid_dosm_feature', 'components', summary['components_intersecting_any_valid_dosm_feature'], '/predicate_summary/components_intersecting_any_valid_dosm_feature'),
        ('component_valid_dosm_feature_intersections', 'intersections', summary['total_component_feature_intersections'], '/predicate_summary/total_component_feature_intersections'),
        ('components_with_dosm_union_coverage_unassessed', 'components', summary['components_with_union_coverage_unassessed_due_invalid_source'], '/predicate_summary/components_with_union_coverage_unassessed_due_invalid_source'),
    ]
    existing_metrics = {row['id']: row for row in evidence.get('metrics', [])}
    existing_bindings = {row['metric_id']: row for row in evidence.get('metric_bindings', [])}
    evidence['metrics'] = [row for row in evidence.get('metrics', []) if row.get('id') not in {x[0] for x in metric_rows}]
    evidence['metric_bindings'] = [row for row in evidence.get('metric_bindings', []) if row.get('metric_id') not in {x[0] for x in metric_rows}]
    evidence['summaries'] = [row for row in evidence.get('summaries', []) if row.get('metric_id') not in {x[0] for x in metric_rows}]
    for metric_id, unit, value, pointer in metric_rows:
        evidence['metrics'].append({'id': metric_id, 'unit': unit, 'value': value,
                                    'input_sha256': run['source']['sha256'],
                                    'evaluation_commit': receipts[0]['git_head_at_execution'],
                                    'vintage': '20261007-dosm-r2'})
        evidence['metric_bindings'].append({'metric_id': metric_id, 'path': run_paths[0], 'json_pointer': pointer})
        evidence['summaries'].append({'metric_id': metric_id, 'value': value, 'unit': unit})
    evidence['metrics'].sort(key=lambda row: row['id'])
    evidence['metric_bindings'].sort(key=lambda row: row['metric_id'])
    evidence['summaries'].sort(key=lambda row: row['metric_id'])
    atomic_replace_regular(evidence_path, canonical(evidence))
    return {name: sha256(canonical(payload)) for name, payload in artifacts.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(json.dumps({'status': 'completed', 'outputs': finalize()}, sort_keys=True))
