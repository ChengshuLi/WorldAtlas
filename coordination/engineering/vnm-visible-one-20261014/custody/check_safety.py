"""Bounded real-entrypoint refusals with exclusive fixtures and restoration.

Run only while no other producer is consuming this owned checkout's control file.
"""
import hashlib
import os
import pathlib
import subprocess

root = pathlib.Path.cwd()
own = root / 'coordination/engineering/vnm-visible-one-20261014'
code = own / 'custody'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
python = __import__('sys').executable
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1',
       'PYTHONPYCACHEPREFIX': str(root / '.cache/phl-custody-20261011/pycache')}
fixture = own / 'vintages/safety-symlink-control'
if fixture.exists() or fixture.is_symlink():
    raise FileExistsError('Occupied safety fixture; preserve it and stop')
control = code / 'inputs.json'
assert not control.is_symlink() and control.is_file()


def snapshot():
    return {str(p.relative_to(own)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in own.rglob('*') if p.is_file()}


def rejected(label, command, expected):
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    assert result.returncode != 0 and expected in result.stderr, (label, result.stdout, result.stderr)
    print('ok - ' + label + '; ' + expected)


before = snapshot()
cases = [
    ('build_handoff.py', [python, str(code / 'build_handoff.py'), head], 'source-handoff-001'),
    ('bind_current_neighbors.mjs', ['node', str(code / 'bind_current_neighbors.mjs'), head], 'vnm-current-neighbors-001'),
]
for label, command, occupied in cases:
    expected = 'exists' if label.endswith('.py') else 'Occupied output destination'
    rejected(label + ' occupied output', command + [occupied], expected)
    fixture.symlink_to('/tmp', target_is_directory=True)
    try:
        rejected(label + ' symlink output', command + ['safety-symlink-control'], 'Symlink')
    finally:
        fixture.unlink()

assert snapshot() == before
print('All 4 real-entrypoint output refusals passed; original owned bytes unchanged and no publication produced.')
