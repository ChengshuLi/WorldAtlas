#!/usr/bin/env python3
"""Run positive, changed-input, deterministic, and overwrite controls locally."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'build_immutable_extract.py'
OUTPUT = HERE / 'corrected-baseline-extract.json'
SPEC = json.loads((HERE / 'correction-spec.json').read_text())
BASE = SPEC['baseline']['commit']
SCOPE = SPEC['scope_snapshot']['commit']


def run(*args, expect=0):
    result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=HERE.parents[2],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != expect:
        raise RuntimeError(f"Expected exit {expect}, got {result.returncode}: {result.stdout}")
    return result.stdout.strip()


# Positive exact-output check, plus a second extraction to a previously absent owned file.
check = run('--check')
second_name = 'control-second-extract.json'
second = HERE / second_name
try:
    write = run('--output', second_name)
    original_bytes = OUTPUT.read_bytes()
    second_bytes = second.read_bytes()
    if original_bytes != second_bytes:
        raise RuntimeError('Repeated immutable extraction differs byte-for-byte')

    # The other pinned repository commit is a deliberate mismatched baseline; it must fail
    # before even a new output file is opened.
    changed_name = 'control-mismatched-baseline.json'
    mismatch = run('--baseline-commit', SCOPE, '--output', changed_name, expect=1)
    if (HERE / changed_name).exists():
        raise RuntimeError('Mismatched baseline created an output')

    # Alter an existing reproduction target and require --check to detect changed input/output.
    corrupt_name = 'control-corrupt-check.json'
    corrupt = HERE / corrupt_name
    corrupt.write_bytes(original_bytes + b'changed-input-control\n')
    changed_check = run('--check', '--output', corrupt_name, expect=1)

    # Default regeneration cannot overwrite the evidence packet.
    overwrite = run(expect=1)
    if OUTPUT.read_bytes() != original_bytes:
        raise RuntimeError('Overwrite refusal modified the canonical output')
finally:
    second.unlink(missing_ok=True)
    (HERE / 'control-mismatched-baseline.json').unlink(missing_ok=True)
    (HERE / 'control-corrupt-check.json').unlink(missing_ok=True)

report = {
    'result': 'passed',
    'positive_existing_output_check': {'status': 'passed', 'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
    'repeat_generation': {'status': 'passed', 'byte_identical': True, 'output_sha256': hashlib.sha256(second_bytes).hexdigest()},
    'mismatched_baseline': {'status': 'passed', 'rejected_before_output_creation': True, 'diagnostic': mismatch.splitlines()[-1]},
    'changed_output_input_check': {'status': 'passed', 'corrupted_candidate_rejected': True, 'diagnostic': changed_check.splitlines()[-1]},
    'overwrite_protection': {'status': 'passed', 'existing_output_unchanged': True, 'diagnostic': overwrite.splitlines()[-1]},
    'commands': ['python build_immutable_extract.py', 'python build_immutable_extract.py --check', 'python verify_controls.py'],
    'baseline_commit': BASE,
    'scope_snapshot_commit': SCOPE,
}
(HERE / 'control-results.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
