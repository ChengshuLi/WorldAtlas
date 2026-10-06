"""Bounded controls and whole-product readback for the two context executions."""
import argparse
import gzip
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import MAX_FILE_BYTES, canonical_json, descriptor, sha256

spec = importlib.util.spec_from_file_location('contexts', ROOT / 'scripts/build-worldwide-contexts.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
OWNED = 'coordination/engineering/worldwide-contexts-1184-20261006/'


def check_numeric_representation():
    integer = {'type': 'Polygon', 'coordinates': [[[1, 1], [2, 1], [1, 2], [1, 1]]]}
    floating = {'type': 'Polygon', 'coordinates': [[[1.0, 1.0], [2.0, 1.0], [1.0, 2.0], [1.0, 1.0]]]}
    assert canonical_json(integer) != canonical_json(floating)
    assert module.geometry_values(integer) == module.geometry_values(floating)
    positive_zero = {'type': 'Point', 'coordinates': [0.0, 1.0]}
    negative_zero = {'type': 'Point', 'coordinates': [-0.0, 1.0]}
    assert canonical_json(positive_zero) != canonical_json(negative_zero)
    assert module.geometry_values(positive_zero) != module.geometry_values(negative_zero)
    altered = {'type': 'Point', 'coordinates': [0.0, 1.0000000000000002]}
    assert module.geometry_values(positive_zero) != module.geometry_values(altered)
    return {'method_id': 'context-representation-control-v1', 'kind': 'positive-control',
            'outcome': 'passed', 'integer_float_byte_identity_rejected': True,
            'integer_float_binary64_values_equal': True, 'signed_zero_preserved': True,
            'one_ulp_coordinate_change_detected': True}


def load_run(name):
    folder = ROOT / OWNED / name
    raw_report = (folder / 'report.json').read_bytes()
    report = json.loads(raw_report)
    rows, payloads = [], []
    for pin in report['outputs']:
        raw = (ROOT / pin['path']).read_bytes()
        assert descriptor(pin['path'], raw) == {k: pin[k] for k in ('path', 'bytes', 'sha256', 'hash_kind')}
        decoded = gzip.decompress(raw)
        assert len(decoded) <= MAX_FILE_BYTES
        assert len(decoded) == pin['uncompressed_bytes'] and sha256(decoded) == pin['uncompressed_sha256']
        rows.extend(json.loads(decoded))
        payloads.append({'name': pathlib.PurePosixPath(pin['path']).name,
                         'bytes': len(raw), 'sha256': sha256(raw),
                         'decoded_bytes': len(decoded), 'decoded_sha256': sha256(decoded)})
    assert len(rows) == 49625 and len({r['id'] for r in rows}) == 49625
    assert all(r['native_observation_status'] == 'pending-pr2-complete-grid-measurement' for r in rows)
    assert all(r['physical_interpretation'] == 'unknown' for r in rows)
    statuses = {status: sum(r['selected_successor_applicability'] == status for r in rows)
                for status in ('changed-coordinate-values', 'changed-json-representation-exact-binary64-values',
                               'identical-canonical-feature-bytes')}
    assert statuses['changed-coordinate-values'] == len(report['selected_coordinate_value_changed_ids']) == 2
    assert statuses['changed-json-representation-exact-binary64-values'] == len(report['selected_representation_only_changed_ids'])
    assert sum(statuses.values()) == 49625
    for filename in ('positive-controls.json', 'negative-controls.json'):
        raw = (folder / filename).read_bytes()
        assert json.loads(raw)['outcome'] == 'passed'
        payloads.append({'name': filename, 'bytes': len(raw), 'sha256': sha256(raw)})
    return report, raw_report, rows, payloads


def run():
    a, raw_a, rows_a, payload_a = load_run('run-one')
    b, raw_b, rows_b, payload_b = load_run('run-two')
    assert a['executed_code_commit'] == b['executed_code_commit']
    assert a['code_inputs'] == b['code_inputs'] and a['frozen_inputs'] == b['frozen_inputs']
    assert a['selected_inputs'] == b['selected_inputs'] and rows_a == rows_b and payload_a == payload_b
    # Manifest path differences are completely reconstructed; no other bytes may differ.
    translated = raw_a.replace((OWNED + 'run-one/').encode(), (OWNED + 'run-two/').encode())
    assert translated == raw_b
    signature = sha256(canonical_json(payload_a))
    receipt = {'method_id': 'complete-world-context-binding-v1', 'kind': 'reproducibility',
               'outcome': 'passed', 'run_one_sha256': signature, 'run_two_sha256': signature,
               'complete_payloads': payload_a, 'complete_rows_verified_each_run': len(rows_a),
               'report_one_sha256': sha256(raw_a), 'report_two_sha256': sha256(raw_b),
               'report_reconstruction': {'operation': 'replace-exact-output-directory-prefix',
                                         'from': OWNED + 'run-one/', 'to': OWNED + 'run-two/',
                                         'whole_result_equals_run_two': True}}
    destination = ROOT / OWNED / 'verification'
    destination.mkdir(exist_ok=False)
    (destination / 'two-run-reproducibility.json').write_bytes(canonical_json(receipt))
    (destination / 'numeric-representation-controls.json').write_bytes(canonical_json(check_numeric_representation()))
    for source_name, expected_kind, kind in [('positive-controls.json', 'positive', 'positive-control'),
                                             ('negative-controls.json', 'negative', 'negative-control')]:
        sources = []
        for name in ('run-one', 'run-two'):
            path = OWNED + name + '/' + source_name
            raw = (ROOT / path).read_bytes()
            record = json.loads(raw)
            assert record['kind'] == expected_kind and record['outcome'] == 'passed'
            if kind == 'negative-control':
                assert len(record['trials']) == 7 and all(t['rejected'] and t['error'] for t in record['trials'])
            else:
                assert record['context_count'] == 49625 and record['native_statistics_produced'] is False
            sources.append(descriptor(path, raw))
        wrapped = {'method_id': 'complete-world-context-binding-v1', 'kind': kind,
                   'outcome': 'passed', 'whole_actual_execution_control_files': sources,
                   'verification': 'Both complete producer executions contain matching passed actual control results; original bytes preserved.'}
        (destination / source_name).write_bytes(canonical_json(wrapped))
    print(json.dumps({'whole_context_rows_each_run': len(rows_a), 'payload_files_each_run': len(payload_a),
                      'reproducibility': 'passed', 'numeric_representation_controls': 'passed'}))


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    run()
