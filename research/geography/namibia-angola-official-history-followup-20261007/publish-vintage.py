"""Invoke the repository-pinned evidence reader and exclusive NewVintage writer."""
import base64
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main(request):
    repo = str(Path(request['repo']).resolve())
    commit = request['baseline_commit']
    files = request['baseline_files']
    helper_path = 'scripts/evidence/immutable.py'
    helper_pin = next((row for row in files if row.get('path') == helper_path), None)
    if not helper_pin:
        raise ValueError('Immutable evidence helper must be pinned at the selected base')
    helper_bytes = subprocess.check_output(['git', '-C', repo, 'show', f'{commit}:{helper_path}'])
    if len(helper_bytes) != helper_pin.get('bytes') or sha256(helper_bytes) != helper_pin.get('sha256'):
        raise ValueError('Pinned helper source differs from its immutable descriptor')
    module = types.ModuleType('worldatlas_pinned_immutable')
    exec(compile(helper_bytes, f'{commit}:{helper_path}', 'exec'), module.__dict__)
    baseline = module.Baseline(repo, commit, files)
    helper = baseline.pinned_bytes(helper_path)
    if helper != helper_bytes:
        raise ValueError('Captured helper bytes differ from code executed by publisher')

    mode = request['mode']
    if mode == 'inputs':
        values = {path: base64.b64encode(baseline.pinned_bytes(path)).decode('ascii')
                  for path in request['input_paths']}
        print(json.dumps(values, sort_keys=True))
        return

    for path, size in request.get('candidate_input_bytes', {}).items():
        baseline.admit('candidate-input:' + path, size)
    vintage = request['vintage']
    writer = module.NewVintage(baseline, request['owned_path'], vintage, request['filenames'])
    if mode == 'admit':
        print(json.dumps({'admitted': True, 'vintage': vintage}, sort_keys=True))
        return
    if mode != 'publish':
        raise ValueError('Unknown publication mode')
    outputs = {name: base64.b64decode(value, validate=True)
               for name, value in request['outputs'].items()}
    records = writer.publish_bytes(outputs)
    print(json.dumps({'version': 1, 'status': 'complete', 'outputs': records}, sort_keys=True))


if __name__ == '__main__':
    try:
        main(json.load(sys.stdin))
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        raise
