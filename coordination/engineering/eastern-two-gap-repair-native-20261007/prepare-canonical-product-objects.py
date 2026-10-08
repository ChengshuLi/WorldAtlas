"""Bounded parent custody preparation; no scientific producer is invoked."""
import argparse
import hashlib
import importlib.util
import json
import marshal
import types
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
UPSTREAM = ROOT / 'coordination/engineering/eastern-two-derived-products-20261007'
GROUPS = {'full_ownership_products180': 'data/ownership-history',
          'full_runtime_products55': 'data/ownership-runtime',
          'full_pixel_products2': 'data'}
MAX = 32 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ordinary(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative or '\0' in relative or any(z in ('', '.', '..') for z in relative.split('/')):
        raise ValueError('Unsafe complete ordinary path')
    if not root.is_absolute() or root.is_symlink() or root.resolve() != root:
        raise ValueError('Ordinary root required')
    p = root
    for z in relative.split('/'):
        p /= z
        if p.is_symlink():
            raise ValueError('Symlink ordinary ancestor rejected')
    return p


def git_body(commit, relative):
    if not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Immutable commit required before Git')
    ordinary(ROOT, relative)
    entry = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-z', commit, '--', relative])
    match = re.fullmatch(rb'(100644|100755) blob ([a-f0-9]{40})\t' + re.escape(relative.encode()) + b'\0', entry)
    if not match:
        raise ValueError('Exact ordinary immutable tree entry required')
    mode, oid = (x.decode() for x in match.groups())
    size = int(subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-s', oid]))
    if not 0 <= size <= MAX:
        raise ValueError('Immutable declared body exceeds cap before allocation')
    with subprocess.Popen(['git', '-C', str(ROOT), 'cat-file', 'blob', oid], stdout=subprocess.PIPE) as process:
        raw = process.stdout.read(size + 1)
        extra = process.stdout.read(1)
        exit_code = process.wait()
    if len(raw) != size or extra or exit_code:
        raise ValueError('Immutable bounded EOF differs')
    if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != oid:
        raise ValueError('Actual immutable Git blob differs')
    return raw, {'commit': commit, 'path': relative, 'mode': mode, 'blob': oid, 'bytes': size, 'sha256': sha(raw)}


def immutable(commit, relative):
    expected, pin = git_body(commit, relative)
    p = ordinary(ROOT, relative)
    if not p.is_file() or p.stat().st_size != len(expected):
        raise ValueError('Complete immutable body bounds differ')
    with p.open('rb') as h:
        raw = h.read(len(expected) + 1)
        if raw != expected or h.read(1):
            raise ValueError('Executed/input whole body differs')
    return raw, pin


def authenticate_helper(helper, source, guard):
    if str(Path(sys.executable).resolve()) != guard['python']['path']:
        raise ValueError('Actual pinned Python executable path differs')
    def file_sha(path):
        h = hashlib.sha256()
        with Path(path).open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        return h.hexdigest()
    if file_sha(sys.executable) != guard['python']['sha256'] or sys.version != guard['versions']['python']:
        raise ValueError('Actual pinned Python body/version differs')
    compiled = compile(source, str(UPSTREAM / 'restore.py'), 'exec')
    expected = {value.co_name: value for value in compiled.co_consts if isinstance(value, types.CodeType)}
    for name in ('member_bytes', 'raw_file', 'gunzip', 'validate_index', 'original_guard', 'checked', 'safe', 'sha'):
        if marshal.dumps(getattr(helper, name).__code__) != marshal.dumps(expected[name]):
            raise ValueError('Actual imported restoration callable differs')
    for name, module in list(sys.modules.items()):
        actual = getattr(module, '__file__', None)
        if name in guard['modules'] and actual:
            pin = guard['modules'][name]
            if str(Path(actual).resolve()) != pin['path'] or file_sha(actual) != pin['sha256']:
                raise ValueError('Actual loaded runtime module differs: ' + name)
    return {'python': guard['python'], 'version': sys.version,
            'helper_callables': sorted(expected), 'runtime_modules': sorted(name for name in sys.modules if name in guard['modules'])}


def prepare(commit, destination):
    immutable(commit, str(Path(__file__).relative_to(ROOT)))
    output = ordinary(ROOT, destination)
    if output.parent != ROOT / '.cache' or not output.name.startswith('1295-canonical-objects-') or output.exists():
        raise ValueError('Fresh exclusively owned object preparation required')
    helper_path = str((UPSTREAM / 'restore.py').relative_to(ROOT))
    helper_raw, helper_pin = immutable(commit, helper_path)
    index_path = str((UPSTREAM / 'source-index.json').relative_to(ROOT))
    index_raw, index_pin = immutable(commit, index_path)
    guard_raw, guard_pin = immutable(commit, str((UPSTREAM / 'runtime-guard.json').relative_to(ROOT)))
    accepted, _ = git_body('15025282de755d631024211687f036751fba963d', index_path)
    if index_raw != accepted:
        raise ValueError('Accepted upstream complete index differs')
    spec = importlib.util.spec_from_file_location('accepted_product_restore', UPSTREAM / 'restore.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    if (UPSTREAM / 'restore.py').read_bytes() != helper_raw:
        raise ValueError('Actual helper source changed')
    runtime = authenticate_helper(helper, helper_raw, json.loads(guard_raw))
    index = json.loads(index_raw)
    helper.validate_index(index)
    rows = []
    objects = {}
    read_parts = set()
    output.mkdir(parents=True)
    (output / 'objects').mkdir()

    def keep(target, raw, mode, origin):
        if len(raw) > MAX:
            raise ValueError('Complete restored member exceeds cap')
        ordinary(ROOT, target)
        key = mode + '-' + sha(raw)
        if key not in objects:
            q = output / 'objects' / key
            with q.open('xb') as h:
                h.write(raw)
            q.chmod(0o755 if mode == '100755' else 0o644)
            objects[key] = {'path': 'objects/' + key, 'bytes': len(raw), 'sha256': sha(raw), 'mode': mode}
        rows.append({'target': target, 'object': objects[key]['path'], 'bytes': len(raw), 'sha256': sha(raw), 'mode': mode, 'origin': origin})

    for binding in index['bindings']:
        if binding['group'] not in GROUPS:
            continue
        member = index['members'][binding['member_id']]
        a, b = member['offset'], member['offset'] + member['encoded_bytes']
        for pin in index['parts']:
            if pin['offset'] < b and pin['offset'] + pin['bytes'] > a and pin['path'] not in read_parts:
                immutable(commit, str((UPSTREAM / pin['path']).relative_to(ROOT)))
                read_parts.add(pin['path'])
        raw = helper.member_bytes(index, member)
        helper.original_guard(binding, raw)
        target = GROUPS[binding['group']] + '/' + binding['path']
        if binding['group'] == 'full_pixel_products2' and binding['path'] == 'verification.json':
            target = str(HERE.relative_to(ROOT)) + '/accepted-pixel-verification.json'
        keep(target, raw, binding['mode'],
             {'kind': 'accepted-upstream-complete-generated-member', 'index': index_pin,
              'accepted_commit': '15025282de755d631024211687f036751fba963d',
              'group': binding['group'], 'member_id': member['id'], 'binding': binding})
    if len(rows) != 237:
        raise ValueError('Complete accepted product roster differs')
    native = ROOT / 'data/canonical-grid/eastern-v8'
    native_paths = sorted(str(q.relative_to(ROOT)) for q in native.rglob('*') if q.is_file())
    original_paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'c5ebd677a0ba3a376eb12ebb97c47cc0343b48d4', '--', 'data/canonical-grid/eastern-v8']).decode().splitlines()
    if native_paths != sorted(original_paths) or any(q.is_symlink() for q in native.rglob('*')):
        raise ValueError('Exact original native path roster differs')
    if len(native_paths) != 63:
        raise ValueError('Complete reviewed native repository roster differs')
    for name in native_paths:
        raw, pin = immutable(commit, name)
        old, _ = git_body('c5ebd677a0ba3a376eb12ebb97c47cc0343b48d4', name)
        if raw != old:
            raise ValueError('Complete original native body differs')
        keep(name, raw, pin['mode'], {'kind': 'accepted-original-native-body', 'original': pin,
             'scientific_execution_commit': '5b32388df0501b013ac9a3ba97864932db493d59',
             'source_publication_commit': 'c5ebd677a0ba3a376eb12ebb97c47cc0343b48d4'})
    if len({x['target'] for x in rows}) != 300:
        raise ValueError('Duplicate or omitted canonical target')
    result = {'version': 1, 'issue': 1295, 'kind': 'complete-accepted-canonical-product-byte-map',
              'execution_commit': commit, 'helper': helper_pin, 'upstream_index': index_pin,
              'runtime_guard': guard_pin, 'actual_runtime': runtime,
              'logical_targets': rows, 'distinct_objects': list(objects.values()),
              'actually_read_whole_upstream_parts': sorted(read_parts),
              'scientific_producers_invoked': False, 'original_unknowns_and_vintages_preserved': True}
    (output / 'canonical-path-map.json').write_text(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
    print(json.dumps({'status': 'PASS', 'logical_targets': len(rows), 'distinct_objects': len(objects),
                      'object_bytes': sum(x['bytes'] for x in objects.values()),
                      'source_parts': len(read_parts), 'scientific_producers_invoked': False}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    prepare(args.commit, args.destination)
