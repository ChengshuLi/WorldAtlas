#!/usr/bin/python3
"""Private post-merge custody handoff. Preparation only until explicitly invoked.

Supply independently obtained bot merge-result JSON and GitHub pull-request API
state JSON, each pinned by the verifier's SHA256. No network access is performed.
Run from outside the author checkout after all author-local processes stop.
This preserves files only: it never removes build artifacts or releases slots.
"""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import sys

AUTHOR = '/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/3d62cf18b0b42e3ae3cd26d42f5e7ac90b65e45ead741649cedd79762724f9e7/work'
PRIVATE = '/Users/chengshuli/world-atlas-workspace/.cache/integration-dependencies-991-sqlite-20261006'
DEST = '/Users/chengshuli/world-atlas-workspace/.cache/991-author-slot-preserved-20261006-44ed0b44'
HEAD = '405f75ce2280dc44172ba596b9ee08513abe437c'
TOKEN = '[workspace-ownership-token-omitted]'
NODE = '/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
INVENTORY_SHA = 'fb49571a2fc521cdbcc0c9f013ee9f1829d037b78f733a99ee97479fc93933c9'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def ordinary_parents(path):
    current = os.path.abspath(path)
    while True:
        if os.path.lexists(current):
            require(not os.path.islink(current), 'Symlink path component: ' + current)
        parent = os.path.dirname(current)
        if parent == current:
            return
        current = parent


def signature(path):
    s = os.lstat(path)
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode)


def file_pin(path):
    ordinary_parents(path)
    before = signature(path)
    require(stat.S_ISREG(before[4]), 'Not an ordinary file: ' + path)
    digest = hashlib.sha256()
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as source:
        require(os.fstat(source.fileno()).st_ino == before[1], 'File substituted: ' + path)
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    require(signature(path) == before, 'File changed while hashing: ' + path)
    return {'bytes': before[2], 'sha256': digest.hexdigest()}


def pinned_json(path, expected):
    require(re.fullmatch('[a-f0-9]{64}', expected) is not None, 'Invalid JSON hash pin')
    pin = file_pin(path)
    require(pin['bytes'] <= 1024 * 1024, 'JSON exceeds bounded size')
    require(pin['sha256'] == expected, 'JSON hash mismatch: ' + path)
    with open(path, 'rb') as source:
        content = source.read(1024 * 1024 + 1)
    require(hashlib.sha256(content).hexdigest() == expected, 'JSON changed during read')
    return json.loads(content), {'path': os.path.abspath(path), **pin}


def no_writers():
    # Conservatively reject *all* open author-local files/cwds, not only write FDs.
    # lsof must run as this user; ambiguous diagnostics block rather than waive.
    result = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', AUTHOR, '-F', 'pfn'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    require(result.returncode in (0, 1) and not result.stderr.strip(),
            'Unable to establish author process quiescence: ' + result.stderr[:2000])
    require(not result.stdout.strip(), 'Live author-local process/open file: ' + result.stdout[:2000])
    processes = subprocess.check_output(['/bin/ps', '-axo', 'pid=,command='], text=True)
    for line in processes.splitlines():
        require(AUTHOR not in line, 'Process command references author checkout: ' + line[:2000])


def database_pins(inventory):
    paths = sorted(os.path.join(AUTHOR, 'data', n) for n in os.listdir(AUTHOR + '/data')
                   if n.startswith('atlas.sqlite'))
    expected = sorted(row['path'] for row in inventory['files'])
    require(paths == expected and len(paths) == 7, 'Database inventory changed or sidecar exists')
    rows = []
    for row in inventory['files']:
        pin = file_pin(row['path'])
        require(pin == {'bytes': row['bytes'], 'sha256': row['sha256']},
                'Changed database pin: ' + row['path'])
        rows.append({'source': row['path'], 'destination': DEST + '/databases/' + pin['sha256'] + '.sqlite', **pin})
    require(len({row['destination'] for row in rows}) == 7, 'Expected seven distinct DB vintages')
    return rows


def cache_snapshot(root):
    ordinary_parents(root)
    require(os.path.isdir(root), 'Cache directory missing')
    rows = []

    def walk(directory, relative):
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            path = entry.path
            rel = relative + '/' + entry.name if relative else entry.name
            s = os.lstat(path)
            if stat.S_ISLNK(s.st_mode):
                target = os.readlink(path)
                require(signature(path) == (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode),
                        'Link changed during snapshot')
                rows.append({'path': rel, 'kind': 'symlink', 'link_text': target})
            elif stat.S_ISDIR(s.st_mode):
                rows.append({'path': rel, 'kind': 'directory'})
                walk(path, rel)
            else:
                require(stat.S_ISREG(s.st_mode), 'Unsupported cache file type: ' + path)
                rows.append({'path': rel, 'kind': 'file', **file_pin(path)})
            require(len(rows) <= 100000, 'Cache descriptor budget exceeded')
    walk(root, '')
    return rows


def allocator():
    program = "import {workspaceManager} from './scripts/local-workspace.mjs'; console.log(JSON.stringify(workspaceManager(process.cwd()).check()));"
    report = json.loads(subprocess.check_output([NODE, '--input-type=module', '-e', program], cwd=AUTHOR))
    require(report['registry'] == '/Users/chengshuli/world-atlas-workspace/WorldAtlas/.git/worldatlas-local-workspaces',
            'Allocator belongs to a different Git common store')
    matches = [row for row in report['entries'] if row['path'] == AUTHOR and row['token'] == TOKEN
               and row['slot'] == 'work' and row['status'] == 'ready']
    require(len(matches) == 1, 'Exact author ownership token not confirmed')
    return report


def exclusive_json(path, value):
    content = (json.dumps(value, indent=2) + '\n').encode()
    require(len(content) <= 32 * 1024 * 1024, 'Receipt descriptor budget exceeded')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    return file_pin(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--merge-receipt', required=True)
    parser.add_argument('--merge-receipt-sha256', required=True)
    parser.add_argument('--pr-state', required=True)
    parser.add_argument('--pr-state-sha256', required=True)
    args = parser.parse_args()
    require(sys.platform == 'darwin', 'Requires macOS renamex_np(RENAME_EXCL)')
    require(not os.path.realpath(os.getcwd()).startswith(AUTHOR + '/')
            and os.path.realpath(os.getcwd()) != AUTHOR, 'Run outside author checkout')
    for path in [args.merge_receipt, args.pr_state]:
        require(not os.path.realpath(path).startswith(AUTHOR + '/'), 'Merge proof must already be outside author')
    receipt, receipt_pin = pinned_json(args.merge_receipt, args.merge_receipt_sha256)
    state, state_pin = pinned_json(args.pr_state, args.pr_state_sha256)
    require(receipt.get('accepted') is True and receipt.get('status') == 'merged'
            and receipt.get('phase') == 'merge' and receipt.get('pr_number') == 1150
            and receipt.get('reviewed_head') == HEAD
            and receipt.get('result_source') == 'github-comment'
            and isinstance(receipt.get('result_comment_id'), int), 'Not an independently confirmed bot merge receipt')
    require(state.get('number') == 1150 and state.get('merged') is True
            and state.get('state') == 'closed' and state.get('head', {}).get('sha') == HEAD
            and state.get('html_url') == 'https://github.com/ChengshuLi/WorldAtlas/pull/1150'
            and re.fullmatch('[a-f0-9]{40}', state.get('merge_commit_sha', '')) is not None
            and state.get('merge_commit_sha') == receipt.get('merge_commit'), 'Receipt disagrees with actual merged PR state')
    require(subprocess.check_output(['git', '-C', AUTHOR, 'rev-parse', 'HEAD'], text=True).strip() == HEAD,
            'Author head advanced; preserve new work separately')
    ordinary_parents(DEST)
    require(not os.path.lexists(DEST), 'Destination collision; never overwrite or resume blindly')
    require(os.stat(AUTHOR).st_dev == os.stat(os.path.dirname(DEST)).st_dev,
            'Same-filesystem rename required; no copy fallback')
    inventory, inventory_pin = pinned_json(PRIVATE + '/sqlite-inventory-v1.json', INVENTORY_SHA)
    no_writers()
    before = allocator()
    databases = database_pins(inventory)
    cache = cache_snapshot(AUTHOR + '/.cache')
    # Repeat the complete snapshot immediately before mutation, not just counts.
    require(cache_snapshot(AUTHOR + '/.cache') == cache, 'Cache changed during preflight')
    require(database_pins(inventory) == databases, 'Database changed during preflight')
    no_writers()
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    rename = library.renamex_np
    rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    os.mkdir(DEST, 0o700)
    os.mkdir(DEST + '/databases', 0o700)
    preflight = {'version': 1, 'head': HEAD, 'pr_number': 1150, 'merge_receipt': receipt_pin,
                 'actual_pr_state': state_pin, 'database_inventory': inventory_pin,
                 'helper': {'path': os.path.abspath(__file__), **file_pin(__file__)},
                 'allocator_before': before, 'databases': databases, 'cache': cache,
                 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    exclusive_json(DEST + '/preflight.json', preflight)
    moves = [(row['source'], row['destination']) for row in databases]
    moves.append((AUTHOR + '/.cache', DEST + '/ignored-cache'))
    for index, (source, destination) in enumerate(moves):
        no_writers()
        original_names = {os.path.basename(row['source']) for row in databases}
        require(all(name in original_names for name in os.listdir(AUTHOR + '/data')
                    if name.startswith('atlas.sqlite')), 'New database/sidecar appeared before rename')
        if index < 7:
            require(file_pin(source) == {key: databases[index][key] for key in ['bytes', 'sha256']},
                    'Database changed immediately before rename')
        else:
            require(cache_snapshot(source) == cache, 'Cache changed immediately before rename')
        require(os.lstat(source).st_dev == os.stat(os.path.dirname(destination)).st_dev,
                'Cross-device move refused')
        if rename(os.fsencode(source), os.fsencode(destination), 0x00000004) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), destination)
        exclusive_json(DEST + '/move-%02d.json' % index, {'source': source, 'destination': destination})
    for row in databases:
        require(file_pin(row['destination']) == {key: row[key] for key in ['bytes', 'sha256']},
                'Destination database readback mismatch')
    require(cache_snapshot(DEST + '/ignored-cache') == cache, 'Complete destination cache inventory/hash mismatch')
    require(all(not os.path.lexists(source) for source, _ in moves), 'Source remains after rename')
    result = {'version': 1, 'operation': 'private exclusive same-filesystem preservation moves',
              'preflight': {'path': DEST + '/preflight.json', **file_pin(DEST + '/preflight.json')},
              'database_count': 7, 'all_database_whole_hashes_verified': True,
              'complete_cache_paths_hashes_link_texts_verified': True,
              'allocator_after': allocator(), 'deleted_artifacts': False,
              'slot_or_claim_released': False, 'external_publication': False,
              'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    final_path = DEST + '/preservation-receipt-v1.json'
    pin = exclusive_json(final_path, result)
    print(json.dumps({'receipt_path': final_path, **pin}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Interrupted/partial handoffs retain preflight and per-move journals.
        # Never roll back, delete destinations, or silently resume a collision.
        print('PRESERVATION STOPPED: ' + str(error), file=sys.stderr)
        sys.exit(1)
