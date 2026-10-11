"""Bounded real-entrypoint refusals with exclusive fixtures and restoration.

Run only while no other producer is consuming this owned checkout's control file.
"""
import hashlib
import os
import pathlib
import subprocess

root = pathlib.Path.cwd()
own = root / 'coordination/engineering/shared-country-delivery-phl-20261010'
code = own / 'custody-20261011'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
python = '/workspace/scratch/127991fc8b8e/cloud-tools/trusted-geography-cp312-np235-sh212-pr372/venv/bin/python'
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1',
       'PYTHONPYCACHEPREFIX': str(root / '.cache/phl-custody-20261011/pycache')}
fixture = own / 'vintages/safety-symlink-control'
if fixture.exists() or fixture.is_symlink():
    raise FileExistsError('Occupied safety fixture; preserve it and stop')
control = code / 'physical-inputs.json'
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
    ('restore_physical.py', [python, str(code / 'restore_physical.py'), head, '1'], 'physical-custody-phase1-001'),
    ('build_handoff.py', [python, str(code / 'build_handoff.py'), head], 'phl-source-handoff-003'),
    ('bind_current_neighbors.mjs', ['node', str(code / 'bind_current_neighbors.mjs'), head], 'phl-current-neighbors-001'),
]
for label, command, occupied in cases:
    expected = 'exists' if label.endswith('.py') else 'Occupied output destination'
    rejected(label + ' occupied output', command + [occupied], expected)
    fixture.symlink_to('/tmp', target_is_directory=True)
    try:
        rejected(label + ' symlink output', command + ['safety-symlink-control'], 'Symlink')
    finally:
        fixture.unlink()

raw = control.read_bytes()
try:
    control.write_bytes(raw + b' ')
    rejected('restore physical input drift',
             [python, str(code / 'restore_physical.py'), head, '1', 'safety-no-output'],
             'Unfrozen execution input')
finally:
    control.write_bytes(raw)
assert snapshot() == before
assert not (own / 'vintages/safety-no-output').exists()
print('All 7 real-entrypoint refusals passed; original owned bytes unchanged and no publication produced.')
