#!/usr/bin/env python3
"""Positive, repeat, changed-baseline, changed-output, overwrite and preservation checks."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
ROOT = HERE.parents[3]
SCRIPT = HERE / 'reproduce.py'
SPEC = json.loads((HERE / 'correction-spec.json').read_text())
DEFAULT_FILES = [SPEC['new_artifacts'][k] for k in ('feature_path', 'chain_path', 'manifest_path')]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(*args, expect=0):
    result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != expect:
        raise RuntimeError(f'Expected exit {expect}, got {result.returncode}: {result.stdout}')
    return result.stdout.strip()


def local_original_hashes():
    descriptors = {}
    for item in SPEC['original_artifact_snapshot']['files']:
        descriptors[item['path']] = item
    for item in SPEC['original_artifact_snapshot']['source_files']:
        path = str((PACKET / item['path']).relative_to(ROOT))
        desc = {'path': path, 'bytes': item['bytes'], 'sha256': item['sha256']}
        prior = descriptors.get(path)
        if prior and (prior['bytes'], prior['sha256']) != (desc['bytes'], desc['sha256']):
            raise RuntimeError(f'Conflicting original artifact descriptors: {path}')
        descriptors[path] = desc
    rows = []
    updated_readme = str((PACKET / 'README.md').relative_to(ROOT))
    for relpath, item in descriptors.items():
        # The parent README is intentionally amended by #614; its original bytes are
        # independently checked by reproduce.py at the immutable artifact snapshot.
        if relpath == updated_readme:
            continue
        path = ROOT / relpath
        data = path.read_bytes()
        if len(data) != item['bytes'] or sha(data) != item['sha256']:
            raise RuntimeError(f'Original packet artifact/source changed: {relpath}')
        rows.append(relpath)
    return sorted(rows)

original_before = local_original_hashes()
positive = run('--check')
repeat_dir = HERE / 'control-repeat'
changed_dir = HERE / 'control-changed'
mismatch_dir = HERE / 'control-mismatched-baseline'
try:
    repeat = run('--output-dir', 'control-repeat')
    for name in DEFAULT_FILES:
        if (HERE / name).read_bytes() != (repeat_dir / name).read_bytes():
            raise RuntimeError(f'Repeated output differs: {name}')

    # A different valid repository commit must be rejected before its output directory exists.
    mismatch = run('--baseline-commit', SPEC['current_main_at_correction_start'],
                   '--output-dir', 'control-mismatched-baseline', expect=1)
    if mismatch_dir.exists():
        raise RuntimeError('Mismatched baseline created its output directory')

    # Changed existing candidate bytes are rejected by --check.
    for name in DEFAULT_FILES:
        target = changed_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((HERE / name).read_bytes())
    with (changed_dir / DEFAULT_FILES[0]).open('ab') as stream:
        stream.write(b'changed-output-control\n')
    changed = run('--check', '--output-dir', 'control-changed', expect=1)

    # Normal generation is immutable after first creation and cannot replace evidence.
    before = {name: (HERE / name).read_bytes() for name in DEFAULT_FILES}
    overwrite = run(expect=1)
    if any((HERE / name).read_bytes() != before[name] for name in DEFAULT_FILES):
        raise RuntimeError('Overwrite refusal changed generated output')
finally:
    shutil.rmtree(repeat_dir, ignore_errors=True)
    shutil.rmtree(changed_dir, ignore_errors=True)
    shutil.rmtree(mismatch_dir, ignore_errors=True)

original_after = local_original_hashes()
if original_before != original_after:
    raise RuntimeError('Original packet/source inventory changed during controls')

result = {
    'result': 'passed',
    'source_baseline_commit': SPEC['source_baseline']['commit'],
    'artifact_snapshot_commit': SPEC['original_artifact_snapshot']['commit'],
    'assigned_subjects': SPEC['scope_snapshot']['member_count'],
    'original_packet_files_hash_checked': len(original_after),
    'checks': {
        'positive_existing_output': {'status': 'passed', 'diagnostic': 'exact pinned output bytes matched'},
        'two_run_determinism': {'status': 'passed', 'byte_identical': True},
        'changed_baseline': {'status': 'passed', 'rejected_before_output_directory_creation': True,
                             'diagnostic': mismatch.splitlines()[-1]},
        'changed_output_candidate': {'status': 'passed', 'rejected_by_check_mode': True,
                                     'diagnostic': changed.splitlines()[-1]},
        'overwrite_protection': {'status': 'passed', 'existing_correction_outputs_unchanged': True,
                                 'diagnostic': overwrite.splitlines()[-1]},
        'original_preservation': {'status': 'passed', 'original_hashes_unchanged': True,
                                  'files_checked': len(original_after)},
    },
    'outputs_sha256': {name: sha((HERE / name).read_bytes()) for name in DEFAULT_FILES},
    'commands': ['python reproduce.py', 'python reproduce.py --check', 'python verify_controls.py'],
}
(HERE / 'control-results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
