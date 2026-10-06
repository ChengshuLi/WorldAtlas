"""Whole-output reproducibility and real producer/overwrite guard controls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PREFIX = Path(__file__).resolve().parent
ROOT = PREFIX.parents[2]
relative = PREFIX.relative_to(ROOT).as_posix()
hash_bytes = lambda data: hashlib.sha256(data).hexdigest()
commit = sys.argv[1]
results = []
for first, second, names in [('results-v3', 'results-v4', ['report.json', 'partition.json', 'candidates.json']),
                             ('native-v1', 'native-v2', ['native-cells.json', 'latitude-bytes.f64le']),
                             ('exact-native-v1', 'exact-native-v2', ['exact-native.json'])]:
    for name in names:
        a, b = (PREFIX / first / name).read_bytes(), (PREFIX / second / name).read_bytes()
        if a != b:
            raise ValueError('Two complete runs differ: ' + name)
        results.append({'one': relative + '/' + first + '/' + name,
                        'two': relative + '/' + second + '/' + name, 'sha256': hash_bytes(a), 'bytes': len(a)})
for name in ['candidates.json', 'partition.json']:
    if (PREFIX / 'results-v1' / name).read_bytes() != (PREFIX / 'results-v3' / name).read_bytes():
        raise ValueError('Dependency-pin amendment changed scientific output')
aggregate = hash_bytes(('\n'.join(row['sha256'] for row in results) + '\n').encode())
receipt = {'method_id': 'joint-exact-native-partition', 'kind': 'reproducibility', 'outcome': 'passed',
           'run_one_sha256': aggregate, 'run_two_sha256': aggregate, 'files': results,
           'limits': ['All complete generated products compared; no source factual or installation approval.']}
with (PREFIX / 'reproducibility.json').open('x') as stream:
    json.dump(receipt, stream, sort_keys=True, indent=2)
    stream.write('\n')
command = [sys.executable, '-B', str(PREFIX / 'reproduce.py'), '--evaluation-commit', commit, '--out']
guards = []
process = subprocess.run(command + [relative + '/results-v3'], capture_output=True, text=True)
if process.returncode == 0 or 'Fresh owned output directory required' not in process.stderr:
    raise ValueError('Existing-output guard did not reject the actual generator')
guards.append({'case': 'existing-complete-output', 'exit_code': process.returncode, 'stderr': process.stderr})
helper = PREFIX / 'exact_arrangement.py'
original = helper.read_bytes()
target = relative + '/rejected-code-mutation'
try:
    helper.write_bytes(original + b'\n# synthetic guard mutation\n')
    process = subprocess.run(command + [target], capture_output=True, text=True)
    if process.returncode == 0 or 'Producer differs from execution pin' not in process.stderr or (ROOT / target).exists():
        raise ValueError('Mutated actual producer did not fail before output creation')
    guards.append({'case': 'actual-helper-byte-mutation', 'exit_code': process.returncode, 'stderr': process.stderr})
finally:
    helper.write_bytes(original)
with (PREFIX / 'generator-guards.json').open('x') as stream:
    json.dump({'method_id': 'joint-exact-native-partition', 'kind': 'negative-control',
               'outcome': 'passed', 'evaluation_commit': commit, 'cases': guards}, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'complete_equal_products': len(results), 'guards_rejected': len(guards), 'aggregate': aggregate}))
