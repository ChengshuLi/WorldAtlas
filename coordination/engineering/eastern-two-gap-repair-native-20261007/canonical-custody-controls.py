"""Directed controls for exact accepted-byte custody; no scientific calculation."""
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run():
    module = load('parent_custody', HERE / 'prepare-canonical-product-objects.py')
    helper = load('accepted_restore', module.UPSTREAM / 'restore.py')
    raw = (module.UPSTREAM / 'restore.py').read_bytes()
    guard = json.loads((module.UPSTREAM / 'runtime-guard.json').read_bytes())
    runtime = module.authenticate_helper(helper, raw, guard)
    results = ['authentic-helper-runtime-positive']
    def rejects(name, action, reason):
        try:
            action()
        except ValueError as error:
            assert reason in str(error), str(error)
            results.append(name)
        else:
            raise AssertionError(name)
    rejects('git-option-before-operation', lambda: module.git_body('--output=/tmp/forbidden', 'AGENTS.md'), 'Immutable commit')
    rejects('traversal', lambda: module.ordinary(module.ROOT, '../outside'), 'Unsafe')
    original = helper.member_bytes
    try:
        helper.member_bytes = lambda *args: b'forged'
        rejects('actual-imported-helper-mutation', lambda: module.authenticate_helper(helper, raw, guard), 'callable')
    finally:
        helper.member_bytes = original
    with tempfile.TemporaryDirectory(dir=module.ROOT / '.cache', prefix='1295-custody-controls-') as temporary:
        root = Path(temporary)
        (root / 'real').mkdir()
        (root / 'linked').symlink_to(root / 'real', target_is_directory=True)
        rejects('symlink-root-before-write', lambda: module.ordinary(root / 'linked', 'file'), 'root')
        rejects('symlink-ancestor-before-write', lambda: module.ordinary(root, 'linked/file'), 'ancestor')
        assert not (root / 'real/file').exists()
    return {'status': 'PASS', 'controls': results, 'actual_python': runtime['python'],
            'scientific_producers_invoked': False}

if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
