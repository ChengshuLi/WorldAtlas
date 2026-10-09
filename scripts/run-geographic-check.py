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
import tempfile
import gzip

MAX_BYTES = 32 * 1024 * 1024
TRUSTED_PATHS = ['scripts/run-geographic-check.py', 'scripts/check-geographic-regression.py',
                 'scripts/check-effective-geographic-regression.mjs', 'src/ownership-codec.js',
                 'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
                 'scripts/ellipsoidal_area.py', 'requirements.txt',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs']
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
    for row in git(repo, 'ls-tree', '-r', '-z', baseline, '--', 'scripts', 'src').decode().split('\0'):
        if not row:
            continue
        fields, name = row.split('\t', 1)
        if fields.split()[0] not in ['100644', '100755']:
            raise ValueError('Trusted scripts must be ordinary committed files')
        expected[name] = fields.split()[2]
    actual = {}
    for namespace in ['scripts', 'src']:
        if (repo / namespace).is_symlink():
            raise ValueError('Trusted scripts namespace cannot contain symlinks')
        for target in (repo / namespace).rglob('*'):
            if target.is_symlink():
                raise ValueError('Trusted scripts namespace cannot contain symlinks')
            if target.is_file():
                actual[str(target.relative_to(repo))] = target
    if set(actual) != set(expected):
        raise ValueError('Untracked or missing file in trusted scripts namespace')
    for name, target in actual.items():
        if target.read_bytes() != git(repo, 'cat-file', 'blob', expected[name]):
            raise ValueError('Checker differs from immutable trusted baseline: ' + name)
    for name in ['requirements.txt', 'package.json', '.github/evidence-policy.json', *[p for p in TRUSTED_PATHS if p.startswith('coordination/')]]:
        target = repo / name
        if any(path.is_symlink() for path in [target, *target.parents]) or not target.is_file() or target.read_bytes() != read(repo, baseline, name):
            raise ValueError('Trusted dependency metadata or evidence policy differs from baseline')
        expected[name] = entry(repo, baseline, name)['git_blob_oid']
    return hashlib.sha256((json.dumps(expected, sort_keys=True, separators=(',', ':')) + '\n').encode()).hexdigest()


def selected_continuous(repo, baseline, candidate, detector):
    import sys
    env = dict(os.environ)
    for name in ['NODE_OPTIONS', 'NODE_PATH']:
        env.pop(name, None)
    executable = os.environ.get('NODE', 'node')
    entrypoint = repo / 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'
    with tempfile.TemporaryDirectory(prefix='trusted-selected-footprints-') as temporary:
        destination = pathlib.Path(temporary).resolve() / 'complete'
        raw = subprocess.check_output([executable, str(entrypoint), 'continuous', str(repo), baseline,
                                      baseline, candidate, str(destination), sys.executable], env=env, stderr=subprocess.PIPE)
        if len(raw) > MAX_BYTES:
            raise ValueError('Cold selected acknowledgement exceeds output cap')
        issued = json.loads(raw)
        if issued.get('candidate_code_executed') is not False or issued.get('kind') != 'trusted-selected-continuous-comparison-v1':
            raise ValueError('Unsupported selected continuous acknowledgement')
        if issued.get('status') == 'selected-sources-unchanged':
            return issued
        publication = issued.get('publication')
        if not isinstance(publication, dict) or publication.get('complete') is not True:
            raise ValueError('Selected continuous source operands lack complete issued publication')
        names = ['publication.json', publication['facts']['path'], publication['operands']['path']]
        pins = [None, publication['facts'], publication['operands']]
        total = 0
        for name, pin in zip(names, pins):
            if safe_path(name) != pathlib.Path(name).name:
                raise ValueError('Foreign selected output path')
            target = destination / name
            stat = target.lstat()
            if target.is_symlink() or not target.is_file() or stat.st_mode & 0o777 != 0o644 or stat.st_size > MAX_BYTES:
                raise ValueError('Nonordinary whole selected output')
            if pin is not None and (stat.st_size != pin['bytes'] or pin.get('decoded_bytes', 0) > MAX_BYTES):
                raise ValueError('Whole selected output size exceeds original bound')
            total += stat.st_size + (pin.get('decoded_bytes', 0) if pin else 0)
        # Node has terminated. This is the actual Python consumer phase, with
        # complete encoded+decoded operands and retained output/code allowance.
        runtime_bytes = pathlib.Path(sys.executable).resolve().stat().st_size
        code_bytes = sum((repo / name).stat().st_size for name in TRUSTED_PATHS)
        if total + runtime_bytes + code_bytes + 2 * MAX_BYTES > 256 * 1024 * 1024:
            raise ValueError('Complete selected polygon consumer phase exceeds prospective cap')
        bodies = []
        for name, pin in zip(names, pins):
            body = (destination / name).read_bytes()
            if pin is not None and (len(body) != pin['bytes'] or hashlib.sha256(body).hexdigest() != pin['sha256']):
                raise ValueError('Whole selected output differs from issued trusted child')
            bodies.append(body)
        if json.loads(bodies[0]) != publication:
            raise ValueError('Cold selected publication differs from live issued acknowledgement')
        facts = json.loads(bodies[1])
        if facts.get('executing_commit') != baseline or facts.get('baseline_commit') != baseline or facts.get('candidate_commit') != candidate or facts.get('candidate_code_executed') is not False:
            raise ValueError('Foreign selected execution/input vintage')
        pin = publication['operands']
        decoded = gzip.decompress(bodies[2])
        if len(decoded) != pin['decoded_bytes'] or hashlib.sha256(decoded).hexdigest() != pin['decoded_sha256']:
            raise ValueError('Whole selected operand decoded inverse differs')
        operands = json.loads(decoded)
        plan = operands.get('plan')
        if operands.get('kind') != 'complete-selected-continuous-operands-v1' or not isinstance(plan, dict):
            raise ValueError('Unsupported complete selected operand domain')
        ids = plan['required_ids']
        if ids != sorted(set(ids)) or sorted(operands['baseline']) != ids or sorted(operands['candidate']) != ids or plan['changed_ids'] != issued['changed_ids']:
            raise ValueError('Selected affected operand closure omitted/reordered owners')
        result = detector.compare(operands['baseline'], operands['candidate'])
        if result['changed_location_ids'] != plan['changed_ids']:
            raise ValueError('Original polygon operator changed-ID closure differs from complete certificate')
        return {'version': 1, 'kind': 'trusted-selected-continuous-comparison-v1',
                'candidate_code_executed': False, 'issued_publication': publication,
                'source_binding': plan['source_bindings'], 'complete_owners': issued['complete_owners'],
                'required_ids': ids, 'original_strict_polygon_result': result,
                'status': result['status'], 'regressions': result['regressions'],
                'limits': ['Complete coordinate-derived exclusion and full affected source pointsets; original coverage/overlap predicates are unchanged.',
                           'No physical water/admin/history approval, repair assignment, release activation or deployment.']}


def inspect(repo, baseline, candidate):
    immutable_sha(baseline)
    immutable_sha(candidate)
    trusted_inventory = verify_trusted_checkout(repo, baseline)
    before, after = inventory(repo, baseline), inventory(repo, candidate)
    report = {'version': 1, 'method_id': 'worldatlas-trusted-geography-check-v1',
              'baseline_commit': baseline, 'candidate_commit': candidate,
              'trusted_code_commit': baseline, 'trusted_code_inventory_sha256': trusted_inventory,
              'candidate_code_executed': False,
              'baseline_input_inventory': before, 'candidate_input_inventory': after,
              'published': False, 'source_approval': False}
    selected = any(git(repo, 'ls-tree', '-z', version, '--', 'data/ownership-selection.json')
                   for version in [baseline, candidate])
    if selected:
        import sys
        env = dict(os.environ)
        for name in ['NODE_OPTIONS', 'NODE_PATH']:
            env.pop(name, None)
        native_raw = subprocess.check_output([
            os.environ.get('NODE', 'node'), str(repo / 'scripts/check-effective-geographic-regression.mjs'),
            str(repo), baseline, candidate, sys.executable], stderr=subprocess.PIPE, env=env)
        if len(native_raw) > MAX_BYTES:
            raise ValueError('Selected native report exceeds bounded output')
        native = json.loads(native_raw)
        report['selected_native_report'] = native
        if native['status'] == 'native-regressions-found':
            return {**report, 'status': 'native-regressions-found',
                    'regressions': len(native['intervals']),
                    'limits': ['Existing owner loss/reassignment has no automatic water or political exception. The raw polygon gate is preserved.']}
    import sys
    sys.path.insert(0, str(repo / 'scripts'))
    spec = importlib.util.spec_from_file_location('trusted_geographic_detector', repo / 'scripts/check-geographic-regression.py')
    detector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detector)
    if selected:
        continuous = selected_continuous(repo, baseline, candidate, detector)
        report['selected_continuous_report'] = continuous
        if continuous.get('regressions') not in [None, 0] or str(continuous.get('status', '')).startswith('blocked-'):
            return {**report, 'status': continuous['status'], 'regressions': continuous['regressions'],
                    'differential_report': continuous['original_strict_polygon_result'],
                    'limits': ['Selected complete footprint loss/overlap is enforced with original predicates; no automatic source exception.']}
    if before == after:
        return {**report, 'status': 'not-applicable', 'regressions': None,
                'limits': ['Live geography input blobs are unchanged; this is applicability evidence, not fresh polygon validation or a global gap clearance.']}
    # Import only after verifying the checked-out implementation against trusted
    # baseline bytes. Candidate scripts, hooks and reproduction commands never run.
    result = detector.inspect(repo, baseline, candidate)
    return {**report, 'status': result['status'], 'regressions': result['regressions'],
            'differential_report': result,
            'limits': ['No automatic repair. Water-loss acceptance requires retained original physical sources, full-shape support and separate exact-head independent review.',
                       'Existing release, identity, regional certificate and historical import checks remain required.']}


def apply_adjudications(repo, candidate, report):
    # No proposed local envelope is accepted. Only baseline Node code can read
    # actual GitHub authority, using a read-only workflow token and exact head.
    if report['status'] != 'regressions-found':
        return report
    report['adjudication'] = {'status': 'blocked'}
    try:
        number, head = os.environ.get('GEOGRAPHY_PR_NUMBER'), os.environ.get('GEOGRAPHY_REVIEWED_HEAD')
        if not isinstance(number, str) or not re.fullmatch('[1-9][0-9]*', number):
            raise ValueError('Missing trusted PR context for source-backed adjudication')
        immutable_sha(head)
        env = dict(os.environ)
        for name in ['NODE_OPTIONS', 'NODE_PATH']:
            env.pop(name, None)
        # stdout contains bounded base64 original dossier bytes, never executable
        # candidate code. The child enforces 48 MiB transport; timeout is finite.
        result = subprocess.run(['node', str(repo / 'scripts/check-geographic-adjudications.mjs'),
                                 '--pr', number, '--head', head], cwd=repo, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode or len(result.stdout) > 48 * 1024 * 1024:
            raise ValueError('Trusted GitHub source-decision validation failed; rerun after exact-head independent review')
        envelope = json.loads(result.stdout)
        from geographic_adjudication import adjudicate
        report['adjudication'] = adjudicate(report, envelope, lambda name: read(repo, candidate, name))
    except Exception as error:  # Preserve raw findings on every failed adjudication.
        report['adjudication'] = {'status': 'blocked', 'reason': str(error)[:1024]}
        if getattr(error, 'unsupported_geometry', None) is not None:
            report['adjudication']['unsupported_geometry'] = error.unsupported_geometry
    return report


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
    # Refuse collisions and symlink/dangling ancestors before any code or data
    # reads; the final exclusive open still handles a later destination race.
    if any(p.is_symlink() for p in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink report path forbidden')
    if args.out.exists():
        raise ValueError('Report destination already exists')
    if not args.out.absolute().parent.is_dir():
        raise ValueError('Report parent must be an existing ordinary directory')
    repo = args.repo.resolve()
    verify_trusted_checkout(repo, args.baseline)
    if args.fetch:
        fetch_candidate(repo, args.candidate)
    result = apply_adjudications(repo, args.candidate, inspect(repo, args.baseline, args.candidate))
    passed = result['status'] in ['not-applicable', 'no-footprint-change', 'no-new-regression'] or (
        result.get('adjudication', {}).get('status') == 'all-findings-supported-and-reviewed')
    result['gate_status'] = 'passed' if passed else 'blocked'
    raw = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(raw) > MAX_BYTES:
        raise ValueError('Geography check output exceeds bounded report size')
    if any(p.is_symlink() for p in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink report path forbidden')
    with args.out.open('xb') as stream:
        stream.write(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('report_sha256=' + digest + '\n')
    print(json.dumps({'status': result['status'], 'regressions': result['regressions'],
                      'report_bytes': len(raw), 'report_sha256': hashlib.sha256(raw).hexdigest()}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
