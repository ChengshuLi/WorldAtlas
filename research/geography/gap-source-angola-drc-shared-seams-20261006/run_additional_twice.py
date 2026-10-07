#!/usr/bin/env python3
"""Run the frozen candidate-scale producer twice and record process observations."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, subprocess

PACKET = Path(__file__).resolve().parent
WORKSPACE = PACKET.parents[2]
FREEZE_PATH = PACKET / 'inputs/additional-freeze.json'
FREEZE = json.loads(FREEZE_PATH.read_text())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
if sha(Path(__file__).read_bytes()) != FREEZE['runner_sha256']:
    raise ValueError('Execution runner differs from frozen code bytes')
producer = PACKET / 'reproduce_additional.py'
if sha(producer.read_bytes()) != FREEZE['producer_sha256']:
    raise ValueError('Producer differs from frozen code bytes')
python = WORKSPACE / '.venv312/bin/python'
results = []
observations = []
for number in (1, 2):
    output_dir = WORKSPACE / f'.scratch/additional-run-{number}'
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['OUTPUT_DIR'] = str(output_dir)
    started = datetime.now(timezone.utc).isoformat()
    process = subprocess.run([str(python), str(producer)], cwd=WORKSPACE, env=env,
                             capture_output=True, text=True)
    finished = datetime.now(timezone.utc).isoformat()
    log = {'run': number, 'started_utc': started, 'finished_utc': finished,
           'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr}
    observations.append(log)
    if process.returncode:
        unique = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (PACKET / f'outputs/additional-failed-run-{number}-{unique}.json').write_text(
            json.dumps({'attempt': number, **log, 'producer_sha256': FREEZE['producer_sha256'],
                        'runner_sha256': FREEZE['runner_sha256'],
                        'input_freeze_sha256': sha(FREEZE_PATH.read_bytes())},
                       sort_keys=True, indent=2) + '\n')
        raise SystemExit(f'producer run {number} failed with exit code {process.returncode}')
    files = {path.name: sha(path.read_bytes()) for path in sorted(output_dir.iterdir()) if path.is_file()}
    results.append({'producer_path': str(producer.relative_to(WORKSPACE)),
                    'producer_sha256': FREEZE['producer_sha256'],
                    'runner_path': str(Path(__file__).relative_to(WORKSPACE)),
                    'runner_sha256': FREEZE['runner_sha256'],
                    'input_freeze_sha256': sha(FREEZE_PATH.read_bytes()),
                    'files': files})
if results[0] != results[1]:
    raise SystemExit('Frozen final producer outputs differ')
for number, result in enumerate(results, 1):
    (PACKET / f'outputs/additional-run-{number}-digests.json').write_text(
        json.dumps(result, sort_keys=True, indent=2) + '\n')
(PACKET / 'outputs/additional-run-observations.json').write_text(
    json.dumps({'runs': observations, 'byte_identical_outputs': True,
                'producer_sha256': FREEZE['producer_sha256'],
                'runner_sha256': FREEZE['runner_sha256'],
                'input_freeze_sha256': sha(FREEZE_PATH.read_bytes())},
               sort_keys=True, indent=2) + '\n')
print(json.dumps({'runs': [{'run': row['run'], 'started_utc': row['started_utc'],
                            'finished_utc': row['finished_utc'], 'exit_code': row['exit_code']}
                           for row in observations],
                  'byte_identical_outputs': True, 'files': results[0]['files']}, indent=2))
