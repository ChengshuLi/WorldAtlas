"""Explicit, immutable code upgrades before downstream water checkpoints exist."""
import hashlib
import json
from pathlib import Path
import subprocess

from execution_state import journal_anchor, pin, verify_anchor, verify_pins, write

SUFFIXES = {'.py', '.cpp', '.c', '.h', '.hpp', '.sh'}
WATER = ('v7-replay/', 'v7-recovery/ocean/')
CONTROL = ('v7-pipeline/run_pipeline.py', 'v7-pipeline/execution_state.py',
           'v7-pipeline/code_versions.py')
UPSTREAM = ('v7-raw-mask/', 'v7-recovery/land/', 'v7-land/')


def committed_code(repo, revision):
    """Read source bytes from git objects, never a mutable historical checkout."""
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    commit = git('rev-parse', '--verify', '--end-of-options', revision + '^{commit}').decode().strip()
    entries = git('ls-tree', '-rz', '--full-tree', commit, '--', 'scripts').split(b'\0')
    selected = []
    for entry in filter(None, entries):
        metadata, raw = entry.split(b'\t', 1)
        mode, kind, blob = metadata.split()
        path = Path(raw.decode()).relative_to('scripts')
        if path.suffix not in SUFFIXES or '__pycache__' in path.parts:
            continue
        if mode not in (b'100644', b'100755') or kind != b'blob':
            raise ValueError('linked/nonregular committed source: ' + str(path))
        selected.append((str(path), blob))
    result = {}
    with subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as reader:
        for name, blob in selected:
            reader.stdin.write(blob + b'\n')
            reader.stdin.flush()
            _, kind, size = reader.stdout.readline().split()
            if kind != b'blob':
                raise ValueError('invalid committed source object')
            remaining, digest = int(size), hashlib.sha256()
            while remaining:
                block = reader.stdout.read(min(1 << 20, remaining))
                if not block:
                    raise ValueError('truncated committed source object')
                digest.update(block)
                remaining -= len(block)
            if reader.stdout.read(1) != b'\n':
                raise ValueError('invalid committed source boundary')
            result[name] = digest.hexdigest()
        reader.stdin.close()
        if reader.wait():
            raise ValueError('could not verify committed code')
    return commit, result


def noncode(identity):
    return {key: value for key, value in identity.items() if key != 'code'}


def changes(before, after):
    return {name: {'before': before.get(name), 'after': after.get(name)}
            for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)}


def validate_scope(delta, completed, scripts):
    """Conservative stage domains: shared/upstream code is never migrated."""
    water = any(name.startswith(WATER) for name in delta)
    for name in delta:
        test = name.startswith('v7-pipeline/test_') and '/' not in name[len('v7-pipeline/'):]
        if name not in CONTROL and not test and not name.startswith(WATER):
            raise ValueError('code upgrade changes upstream/shared producer code: ' + name)
    for path in completed:
        receipt = json.loads(Path(path).read_bytes())
        entry = Path(receipt['invocation']['code']['path']).relative_to(scripts).as_posix()
        if not entry.startswith(UPSTREAM + WATER):
            raise ValueError('code upgrade has an unsupported completed producer: ' + entry)
        if water and entry.startswith(WATER):
            raise ValueError('water code upgrade cannot reuse completed water checkpoints')
    return water


def load(root, original, repo):
    """Validate an unbroken append-only chain back to the original run identity."""
    root = Path(root)
    parent = pin(root / 'run-identity.json')
    identity = original
    stale = []
    paths = sorted((root / 'code-versions').glob('*.json'))
    for index, path in enumerate(paths, 1):
        if path.name != f'{index:06d}.json':
            raise ValueError('code-version chain is missing or unordered')
        record = json.loads(path.read_bytes())
        if (record.get('schema') != 'worldatlas-code-version-transition-v1'
                or record.get('parent') != parent
                or noncode(record['identity']) != noncode(original)
                or record['changes'] != changes(identity['code'], record['identity']['code'])):
            raise ValueError('code-version provenance chain changed')
        if committed_code(repo, record['from_commit'])[1] != identity['code']:
            raise ValueError('old committed code does not match run provenance')
        if committed_code(repo, record['to_commit'])[1] != record['identity']['code']:
            raise ValueError('new committed code does not match run provenance')
        verify_pins(record['completed_checkpoints'])
        validate_scope(record['changes'], [p['path'] for p in record['completed_checkpoints']],
                       Path(original['scripts_root']))
        verify_anchor(record['timing_anchor'], root / 'timing-events.jsonl')
        stale.extend(record['stale_coast_batches'])
        identity, parent = record['identity'], pin(path)
    return identity, parent, stale, len(paths)


def upgrade(root, previous, current, parent, revision, repo, count):
    if noncode(previous) != noncode(current):
        raise ValueError('code upgrade cannot change request, input, runtime or output identity')
    old_commit, old = committed_code(repo, revision)
    new_commit, new = committed_code(repo, 'HEAD')
    if old != previous['code'] or new != current['code']:
        raise ValueError('code upgrade requires exact old-run and clean committed new source identities')
    delta = changes(old, new)
    if not delta:
        raise ValueError('code upgrade has no source changes')
    completed = sorted((root / 'checkpoints').glob('*/complete.json'))
    water = validate_scope(delta, completed, Path(current['scripts_root']))
    stale = []
    if water:
        candidates = [root / 'coast/batch-start.json',
                      *(root / 'preserved').glob('coast-*/*/batch-start.json')]
        stale = [pin(path) for path in candidates if path.is_file()]
    # The caller must run Timing's normal recovery first. Reject an unnormalized
    # tail rather than publish an anchor that its next resume would invalidate.
    with (root / 'timing-events.jsonl').open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):
                raise ValueError('normalize torn timing journal before code upgrade')
            json.loads(line)
    directory = root / 'code-versions'
    directory.mkdir(exist_ok=True)
    record = {'schema': 'worldatlas-code-version-transition-v1', 'parent': parent,
              'from_commit': old_commit, 'to_commit': new_commit, 'identity': current,
              'changes': delta, 'completed_checkpoints': [pin(path) for path in completed],
              'timing_anchor': journal_anchor(root / 'timing-events.jsonl'),
              'stale_coast_batches': stale,
              'limitations': 'Unchanged upstream outputs retain their original producer provenance. '
                             'Partial coastal batches from older water code are preserved, not reused.'}
    path = write(directory / f'{count + 1:06d}.json', record)
    return pin(path), stale
