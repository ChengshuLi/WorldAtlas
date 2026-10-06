"""Committed immutable producer of analytic controls and reproducibility evidence."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
from evidence.exact_predicates import diagnose, segment_certificate, VERSION


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def write_new(path, value):
    with path.open('xb') as stream:
        stream.write(encode(value))


def main(output):
    fixtures = Path(__file__).parent / 'fixtures'
    request = json.loads((fixtures / 'request.json').read_bytes())
    context = request['context']
    def seg(id, endpoints): return {'id': id, 'endpoints': endpoints, 'context': context}
    triangle = segment_certificate(seg('analytic-diagonal', [[0, 0], [1, 1]]), seg('analytic-gap-edge', [[0, 1], [1, -1]]))
    dyadic = segment_certificate(seg('analytic-diagonal', [[0, 0], [1, 1]]), seg('analytic-dyadic', [[0, 1], [1, 0]]))
    one, two = diagnose(fixtures, request), diagnose(fixtures, request)
    expected = {'first': ['first-only'], 'second': ['second-only'], 'both': ['both'], 'neither': ['neither']}
    actual = {p['point_id']: p['classes'] for p in one['points']}
    assert all(actual[key] == value for key, value in expected.items())
    assert triangle['status'] == 'export-incidence-failure' and triangle['exact_node'] == [{'numerator': '1', 'denominator': '3'}] * 2
    assert dyadic['status'] == 'exact-incidence'
    positive = {'method_id': 'exact-original-source', 'kind': 'positive-control', 'outcome': 'passed',
                'actual_classes': actual, 'nonrepresentable_crossing': triangle, 'dyadic_crossing': dyadic}
    failures = []
    for change in ('roster', 'crs', 'vintage', 'bytes'):
        changed = copy.deepcopy(request)
        if change == 'roster': changed['collections']['first']['member_ids'].pop()
        elif change in ('crs', 'vintage'): changed['files'][0]['context']['crs' if change == 'crs' else 'numeric_vintage'] = 'altered'
        else: changed['files'][0]['sha256'] = '0' * 64
        failure = diagnose(fixtures, changed)
        assert failure['status'] in ('unknown', 'invalid')
        failures.append({'control': change, 'actual_failure': failure})
    tests = subprocess.run([sys.executable, '-B', str(REPO / 'test/exact-source-predicates.py')], capture_output=True, text=True)
    assert tests.returncode == 0, tests.stdout + tests.stderr
    negative = {'method_id': 'exact-original-source', 'kind': 'negative-control', 'outcome': 'passed',
                'retained_failures': failures, 'focused_test_status': tests.returncode}
    first_hash, second_hash = (hashlib.sha256(encode(value)).hexdigest() for value in (one, two))
    assert first_hash == second_hash
    reproducibility = {'method_id': 'exact-original-source', 'kind': 'reproducibility', 'outcome': 'passed',
                       'run_one_sha256': first_hash, 'run_two_sha256': second_hash,
                       'producer_commit': subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
                       'helper_version': VERSION, 'python': sys.version}
    output.mkdir(parents=True, exist_ok=False)
    for name, result in [('run-one.json', one), ('run-two.json', two), ('positive-control.json', positive),
                         ('negative-control.json', negative), ('reproducibility.json', reproducibility)]:
        write_new(output / name, result)
    print(json.dumps({'output': str(output), 'run_one_sha256': first_hash, 'run_two_sha256': second_hash}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
