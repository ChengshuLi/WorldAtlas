"""Read-only trusted geography check; proposed commits are data, never code."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess

MAX_BYTES = 32 * 1024 * 1024
TRUSTED_PATHS = ['scripts/run-geographic-check.py', 'scripts/check-geographic-regression.py',
                 'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
                 'scripts/ellipsoidal_area.py', 'requirements.txt']
PIN_PATHS = ['data/hierarchy.json', 'data/canonical-grid/manifest.json',
             'data/geographic-releases/index.json', 'data/geographic-releases/current-manifest.json']


def immutable_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{40}', value):
        raise ValueError('Require exact immutable baseline and candidate commits')
    return value


def safe_path(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value or any(p in ['', '.', '..'] for p in value.split('/')):
        raise ValueError('Unsafe geography input path')
    return value


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args], stderr=subprocess.PIPE)


def entry(repo, commit, name):
    name = safe_path(name)
    row = git(repo, 'ls-tree', '-z', commit, '--', name).decode().rstrip('\0')
    if not row.startswith(('100644 ', '100755 ')) or row[row.find('\t'):] != '\t' + name:
        raise ValueError('Geography input must be an ordinary Git file: ' + name)
    blob = row.split()[2]
    return {'path': name, 'mode': row.split()[0], 'git_blob_oid': blob}


def read(repo, commit, name):
    blob = entry(repo, commit, name)['git_blob_oid']
    if int(git(repo, 'cat-file', '-s', blob)) > MAX_BYTES:
        raise ValueError('Geography input exceeds bounded file size: ' + name)
    return git(repo, 'cat-file', 'blob', blob)


def inventory(repo, commit):
    index = json.loads(read(repo, commit, 'data/world-index.json'))
    parts = index.get('parts')
    if not isinstance(parts, list) or not 1 <= len(parts) <= 512 or len(set(parts)) != len(parts):
        raise ValueError('Invalid or incomplete live geography part inventory')
    names = ['data/world-index.json', *PIN_PATHS, *['data/' + safe_path(p) for p in parts]]
    pointer = json.loads(read(repo, commit, PIN_PATHS[-1]))
    if not isinstance(pointer, dict) or not re.fullmatch('[a-f0-9]{64}', pointer.get('sha256', '')):
        raise ValueError('Invalid geographic release pointer')
    pointed = safe_path(pointer.get('path'))
    if not pointed.startswith('data/'):
        pointed = 'data/geographic-releases/' + pointed
    if hashlib.sha256(read(repo, commit, pointed)).hexdigest() != pointer['sha256']:
        raise ValueError('Geographic release pointer hash mismatch')
    names.append(pointed)
    return [entry(repo, commit, name) for name in sorted(set(names))]


def verify_trusted_checkout(repo, baseline):
    if git(repo, 'rev-parse', 'HEAD').decode().strip() != baseline:
        raise ValueError('Checker checkout must be the exact trusted baseline commit')
    # Verify the complete local scripts namespace, including package absence.
    # A byte-correct geometry.py is insufficient if an untracked evidence.py,
    # package initializer, extension module or cached bytecode can shadow it.
    expected = {}
    for row in git(repo, 'ls-tree', '-r', '-z', baseline, '--', 'scripts').decode().split('\0'):
        if not row:
            continue
        fields, name = row.split('\t', 1)
        if fields.split()[0] not in ['100644', '100755']:
            raise ValueError('Trusted scripts must be ordinary committed files')
        expected[name] = fields.split()[2]
    actual = {}
    for target in (repo / 'scripts').rglob('*'):
        if target.is_symlink():
            raise ValueError('Trusted scripts namespace cannot contain symlinks')
        if target.is_file():
            actual[str(target.relative_to(repo))] = target
    if set(actual) != set(expected):
        raise ValueError('Untracked or missing file in trusted scripts namespace')
    for name, target in actual.items():
        if target.read_bytes() != git(repo, 'cat-file', 'blob', expected[name]):
            raise ValueError('Checker differs from immutable trusted baseline: ' + name)
    if (repo / 'requirements.txt').is_symlink() or (repo / 'requirements.txt').read_bytes() != read(repo, baseline, 'requirements.txt'):
        raise ValueError('Trusted dependency requirements differ from baseline')


def inspect(repo, baseline, candidate):
    immutable_sha(baseline)
    immutable_sha(candidate)
    verify_trusted_checkout(repo, baseline)
    before, after = inventory(repo, baseline), inventory(repo, candidate)
    report = {'version': 1, 'method_id': 'worldatlas-trusted-geography-check-v1',
              'baseline_commit': baseline, 'candidate_commit': candidate,
              'trusted_code_commit': baseline, 'candidate_code_executed': False,
              'baseline_input_inventory': before, 'candidate_input_inventory': after,
              'published': False, 'source_approval': False}
    if before == after:
        return {**report, 'status': 'not-applicable', 'regressions': None,
                'limits': ['Live geography input blobs are unchanged; this is applicability evidence, not fresh polygon validation or a global gap clearance.']}
    # Import only after verifying the checked-out implementation against trusted
    # baseline bytes. Candidate scripts, hooks and reproduction commands never run.
    import sys
    sys.path.insert(0, str(repo / 'scripts'))
    spec = importlib.util.spec_from_file_location('trusted_geographic_detector', repo / 'scripts/check-geographic-regression.py')
    detector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detector)
    result = detector.inspect(repo, baseline, candidate)
    return {**report, 'status': result['status'], 'regressions': result['regressions'],
            'differential_report': result,
            'limits': ['No automatic water exception or repair. Source-backed intentional loss needs separate exact-geometry adjudication.',
                       'Existing release, identity, regional certificate and historical import checks remain required.']}


def fetch_candidate(repo, candidate):
    immutable_sha(candidate)
    # Read token stays in process environment, not arguments, logs or Git config.
    token = os.environ.get('GH_TOKEN')
    if token:
        for key in list(os.environ):
            if key.startswith('GIT_CONFIG_KEY_') or key.startswith('GIT_CONFIG_VALUE_'):
                del os.environ[key]
        os.environ['GIT_CONFIG_COUNT'] = '1'
        os.environ['GIT_CONFIG_KEY_0'] = 'http.https://github.com/.extraheader'
        os.environ['GIT_CONFIG_VALUE_0'] = 'AUTHORIZATION: basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode()
    git(repo, 'fetch', '--quiet', '--no-tags', '--no-write-fetch-head', '--filter=blob:none', 'origin', candidate)


def main():
    import sys
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError('Invoke the trusted checker with python -I -B')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument('--baseline', default=os.environ.get('GEOGRAPHY_BASELINE'))
    parser.add_argument('--candidate', default=os.environ.get('GEOGRAPHY_CANDIDATE'))
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--out', type=pathlib.Path, required=True)
    args = parser.parse_args()
    immutable_sha(args.baseline)
    immutable_sha(args.candidate)
    repo = args.repo.resolve()
    verify_trusted_checkout(repo, args.baseline)
    if args.fetch:
        fetch_candidate(repo, args.candidate)
    result = inspect(repo, args.baseline, args.candidate)
    raw = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(raw) > MAX_BYTES:
        raise ValueError('Geography check output exceeds bounded report size')
    if any(p.is_symlink() for p in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink report path forbidden')
    with args.out.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'status': result['status'], 'regressions': result['regressions'],
                      'report_bytes': len(raw), 'report_sha256': hashlib.sha256(raw).hexdigest()}))
    return 0 if result['status'] in ['not-applicable', 'no-footprint-change', 'no-new-regression'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
