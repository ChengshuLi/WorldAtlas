"""Lossless #1423 custody of exactly the 39 pre-final files at immutable 83d."""
import argparse, base64, gzip, hashlib, io, json, os, pathlib, re, resource, shutil, subprocess, sys, types

N = 'coordination/engineering/angola-original-envelope-20261007/'
R = pathlib.Path(__file__).resolve().parents[3]
OLD = '83d280e36d3cf5849e27411adf51edce0968b5e2'
PACK = N + 'vintages/pre-final-custody/'
CAP = 32 * 1024 * 1024
sha = lambda b: hashlib.sha256(b).hexdigest()
canon = lambda x: (json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def git(commit, name):
    row = subprocess.check_output(['git', '-C', str(R), 'ls-tree', commit, '--', name]).decode().split()
    if len(row) != 4 or row[:2] != ['100644', 'blob']:
        raise ValueError('Ordinary immutable Git file required')
    raw = subprocess.check_output(['git', '-C', str(R), 'cat-file', 'blob', row[2]])
    if len(raw) > CAP:
        raise ValueError('Whole file cap')
    return raw


def safe(name):
    parts = pathlib.PurePosixPath(name).parts
    if not name.startswith(N + 'vintages/') or any(p in ('', '.', '..') or not re.fullmatch('[a-zA-Z0-9_.-]+', p) for p in parts) or str(pathlib.PurePosixPath(name)) != name:
        raise ValueError('Unsafe custody member path')
    if parts[4].startswith('final-'):
        raise ValueError('Final files must remain flat')
    return name


def read_body(encoded, index, expected):
    # Whole transport/body identities precede parsing or returning any member.
    if len(encoded) > CAP or len(encoded) != expected['bytes'] or sha(encoded) != expected['sha256']:
        raise ValueError('Whole encoded custody drift')
    with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
        raw = stream.read(CAP + 1)
    if len(raw) > CAP or len(raw) != expected['uncompressed_bytes'] or sha(raw) != expected['uncompressed_sha256']:
        raise ValueError('Whole decoded custody drift')
    if not raw.endswith(b'\n'):
        raise ValueError('Trailing custody body')
    rows = [json.loads(line) for line in raw.splitlines()]
    if len(rows) != 39:
        raise ValueError('Exact39 custody membership')
    found = {}
    for row in rows:
        name = safe(row['path'])
        if name in found:
            raise ValueError('Duplicate custody member')
        if set(row) != {'path', 'mode', 'bytes', 'sha256', 'raw_base64'} or row['mode'] != '100644':
            raise ValueError('Custody member fields/mode')
        body = base64.b64decode(row['raw_base64'], validate=True)
        if len(body) > CAP or len(body) != row['bytes'] or sha(body) != row['sha256']:
            raise ValueError('Custody member body drift')
        found[name] = (row, body)
    expected_rows = index['members']
    if index['source_commit'] != OLD or len(expected_rows) != 39 or len({r['path'] for r in expected_rows}) != 39 or set(found) != {r['path'] for r in expected_rows}:
        raise ValueError('Independent39 roster drift')
    for row in expected_rows:
        safe(row['path'])
        actual, body = found[row['path']]
        if {k: actual[k] for k in ('path', 'mode', 'bytes', 'sha256')} != row:
            raise ValueError('Independent immutable member binding drift')
        original = git(OLD, row['path'])
        if body != original:
            raise ValueError('Immutable83d inverse byte mismatch')
    return {name: body for name, (_, body) in found.items()}


def restore(members, destination):
    # Entire safe roster and destination are admitted before allocating any output.
    destination = pathlib.Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Fresh ordinary restoration directory required')
    for ancestor in [destination, *destination.parents]:
        if ancestor.is_symlink() or ancestor.exists() and not ancestor.is_dir():
            raise ValueError('Restoration symlink/nonordinary ancestor')
    targets = {name: destination / safe(name) for name in members}
    destination.mkdir()
    for name, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(members[name]); stream.flush(); os.fsync(stream.fileno())
        os.chmod(target, 0o644)
    return targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--proof-vintage')
    parser.add_argument('--restore')
    args = parser.parse_args()
    if not re.fullmatch('[a-f0-9]{40}', args.commit):
        raise ValueError('Exact custody execution freeze')
    names = [N + 'custody.py', PACK + 'members.jsonl.gz', PACK + 'index.json', 'scripts/evidence/immutable.py']
    captured = {name: git(args.commit, name) for name in names}
    for name, raw in captured.items():
        target = R / name
        if any(a.is_symlink() for a in [target, *target.parents]) or target.read_bytes() != raw:
            raise ValueError('Actual custody entry/helper/input drift')
    helper = types.ModuleType('immutable'); helper.__file__ = str(R / names[-1])
    exec(compile(captured[names[-1]], helper.__file__, 'exec'), helper.__dict__)
    baseline = helper.Baseline(R, args.commit, [helper.descriptor(n, b) for n, b in captured.items()])
    index = json.loads(baseline.pinned_bytes(PACK + 'index.json'))
    encoded = baseline.pinned_bytes(PACK + 'members.jsonl.gz')
    members = read_body(encoded, index, index['archive'])
    if not args.controls:
        if args.restore:
            restore(members, args.restore)
        print(json.dumps({'status': 'complete39-authenticated-before-access', 'members': 39, 'archive': index['archive'], 'execution_commit': args.commit}))
        return
    if not args.proof_vintage or args.restore:
        raise ValueError('Controls need a fresh proof vintage and owned scratch destination')
    publication = helper.NewVintage(baseline, N, args.proof_vintage, ['controls.json'])
    scratch = R / N / 'vintages' / (args.proof_vintage + '-roundtrip')
    # Admission is dry before the true roundtrip and all controls.
    if scratch.exists() or scratch.is_symlink():
        raise ValueError('Fresh control scratch required')
    targets = restore(members, scratch)
    checks = []
    for name, target in targets.items():
        original = git(OLD, name)
        if target.read_bytes() != original or oct(target.stat().st_mode & 0o777) != '0o644':
            raise ValueError('Actual inverse roundtrip failed')
        checks.append({'path': name, 'mode': '100644', 'bytes': len(original), 'sha256': sha(original), 'inverse_equal': True})
    rows = [json.loads(line) for line in gzip.decompress(encoded).splitlines()]
    controls = []
    def adverse(label, changed):
        raw = b''.join(canon(row) for row in changed) if isinstance(changed, list) else changed
        transport = helper.deterministic_gzip(raw)
        expected = helper.descriptor('coherent-fixture.jsonl.gz', transport)
        try:
            read_body(transport, index, expected)
        except (ValueError, json.JSONDecodeError) as error:
            controls.append({'name': label, 'actual_reader_rejected': True, 'error': str(error), 'coherent_whole_transport': expected})
        else:
            raise ValueError('Nonvacuous custody adverse input accepted')
    adverse('missing-member', rows[:-1])
    adverse('duplicate-member', rows[:-1] + [rows[0]])
    adverse('trailing-body', gzip.decompress(encoded) + b'{}\n')
    changed = json.loads(json.dumps(rows)); changed[0]['raw_base64'] = base64.b64encode(b'changed').decode()
    adverse('member-body-drift', changed)
    changed = json.loads(json.dumps(rows)); changed[0]['path'] = N + 'vintages/../escape'
    adverse('unsafe-member-path', changed)
    changed = json.loads(json.dumps(rows)); changed[0]['mode'] = '100755'
    adverse('member-mode-drift', changed)
    try:
        read_body(encoded + b'x', index, index['archive'])
    except ValueError as error:
        controls.append({'name': 'whole-transport-drift', 'actual_reader_rejected': True, 'error': str(error)})
    else:
        raise ValueError('Whole transport drift accepted')
    index_path = R / PACK / 'index.json'
    original_index = index_path.read_bytes()
    try:
        index_path.write_bytes(original_index + b' ')
        result = subprocess.run([sys.executable, '-I', '-B', str(R / N / 'custody.py'), '--commit', args.commit], capture_output=True)
        if result.returncode == 0 or b'Actual custody entry/helper/input drift' not in result.stderr:
            raise ValueError('Actual whole-index entry guard not exercised')
        controls.append({'name': 'whole-index-actual-entry-drift', 'actual_reader_rejected': True, 'returncode': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()})
    finally:
        index_path.write_bytes(original_index)
    try:
        restore(members, scratch)
    except ValueError as error:
        controls.append({'name': 'existing-restoration-destination', 'actual_reader_rejected': True, 'error': str(error)})
    else:
        raise ValueError('Existing restoration accepted')
    link = scratch.parent / (scratch.name + '-symlink')
    if link.exists() or link.is_symlink():
        raise ValueError('Fresh symlink fixture required')
    link.symlink_to(scratch, target_is_directory=True)
    try:
        try:
            restore(members, link)
        except ValueError as error:
            controls.append({'name': 'symlink-restoration-destination', 'actual_reader_rejected': True, 'error': str(error)})
        else:
            raise ValueError('Symlink restoration accepted')
    finally:
        link.unlink()
    # Only verified exact regenerated own scratch copies are removed; originals
    # remain in immutable83d and whole authenticated lossless custody.
    for name, target in targets.items():
        if target.read_bytes() != members[name]:
            raise ValueError('Scratch drift before safe removal')
    shutil.rmtree(scratch)
    proof = {'status': 'complete39-lossless-inverse-and10-actual-reader-controls', 'execution_commit': args.commit, 'original_commit': OLD,
             'original_records': checks, 'controls': controls, 'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'scratch': '39 exact regenerated own copies verified against immutable83d and custody before removal; no unique evidence removed',
             'archive': index['archive']}
    publication.publish({'controls.json': proof})
    print(json.dumps({'status': proof['status'], 'members': len(checks), 'controls': len(controls), 'peak_rss_bytes': proof['peak_rss_bytes']}))


if __name__ == '__main__':
    main()
