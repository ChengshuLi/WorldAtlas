"""Compare fixture setup at the exact original commit and this candidate.

No geographic computation, input copy, credential, or change to retained evidence.
Temporary hard-linked fixtures live under the caller's managed TMPDIR.
"""
import hashlib
import json
import pathlib
import subprocess
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
PATH = 'test/physical-component-evidence-controls.py'
BASELINE = 'ad2d418f298031c83afd30d2147c1a4e8ec546b8'
original = subprocess.check_output(['git', 'show', BASELINE + ':' + PATH], cwd=ROOT)
candidate = (ROOT / PATH).read_bytes()


def load(raw, name):
    namespace = {'__name__': name, '__file__': str(ROOT / PATH)}
    exec(compile(raw, str(ROOT / PATH), 'exec'), namespace)
    return namespace


versions = {'baseline': load(original, 'baseline_fixture'), 'candidate': load(candidate, 'candidate_fixture')}
measurements, signatures = [], []
for trial in range(3):
    for version in ('baseline', 'candidate'):
        namespace = versions[version]
        with tempfile.TemporaryDirectory(prefix='component-fixture-profile-') as directory:
            f = namespace['Fixture'](pathlib.Path(directory))
            f.alter_rows('new_contacts', lambda rows: rows.clear())
            retained = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in f.changed}
            started = time.monotonic()
            f.finalize()
            seconds = time.monotonic() - started
            for p, digest in retained.items():
                assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest
            signature = hashlib.sha256((f.root / namespace['validator'].INDEX).read_bytes()).hexdigest()
            signatures.append(signature)
            measurements.append({'trial': trial, 'version': version, 'finalize_seconds': seconds,
                                 'complete_fixture_index_sha256': signature})
            print(json.dumps(measurements[-1]), flush=True)
assert len(set(signatures)) == 1, 'Optimization changed the fully rebound fixture'
print(json.dumps({'baseline_commit': BASELINE, 'baseline_code_sha256': hashlib.sha256(original).hexdigest(),
                  'candidate_code_sha256': hashlib.sha256(candidate).hexdigest(),
                  'fixture_whole_bytes_equal': True,
                  'limit': 'Preparation only. Candidate validate_science still executes full custody before every semantic control.'}), flush=True)
