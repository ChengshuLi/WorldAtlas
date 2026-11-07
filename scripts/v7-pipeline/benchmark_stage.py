#!/usr/bin/env python3
"""Time one complete admitted stage on pinned local inputs, without downloads.

The original interpreter and arguments are retained, except for the checkout,
fresh output and explicitly requested extra arguments. No resource limits or
watchdogs are installed. Run benchmarks sequentially for comparable timings.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_directory_exclusive, create_text_exclusive, write_json_exclusive


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def environment():
    cpu_max = Path('/sys/fs/cgroup/cpu.max')
    return {'platform': platform.platform(), 'logical_cpu_count': os.cpu_count(),
            'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
            'cpu_quota': cpu_max.read_text().strip() if cpu_max.exists() else None,
            **{key: os.environ.get(key) for key in ('PROJ_NETWORK', 'PYTHONPATH', 'TMPDIR')}}


def stage_command(admitted, code_root, candidate, extra_arguments=(), *, drop_boolean_options=()):
    command = list(admitted['invocation']['command'])
    if len(command) < 2 or command.count('--out') != 1:
        raise ValueError('stage must use one explicit --out')
    parts = Path(command[1]).parts
    if 'scripts' not in parts:
        raise ValueError('stage script must be inside the repository scripts directory')
    relative = Path(*parts[parts.index('scripts'):])
    builder = code_root / relative
    if not builder.is_file():
        raise ValueError(f'missing stage script: {relative}')
    command[1] = str(builder)
    command[command.index('--out') + 1] = str(candidate)
    if any(v == '--out' or v.startswith('--out=') for v in extra_arguments):
        raise ValueError('extra arguments cannot replace the fresh output')
    if any(not flag.startswith('--') or '=' in flag or flag in ('--out', '--input-root') for flag in drop_boolean_options):
        raise ValueError('only explicit classifier boolean options can be removed')
    command = [arg for arg in command if arg not in drop_boolean_options]
    return command + list(extra_arguments)


def run_stage(admission, code_root, out, extra_arguments=(), *, drop_boolean_options=()):
    admitted = json.loads(admission.read_text())
    out = out.absolute()
    if out.exists() or not out.parent.is_dir():
        raise ValueError('benchmark output must be new with an existing parent')
    command = stage_command(admitted, code_root.resolve(), out / 'candidate', extra_arguments, drop_boolean_options=drop_boolean_options)
    create_directory_exclusive(out)
    invocation = {'command': command, 'environment': environment(), 'admission_sha256': digest(admission),
                  'builder_sha256': digest(Path(command[1]))}
    write_json_exclusive(out / 'invocation.json', invocation, indent=2)
    started = time.perf_counter()
    with create_text_exclusive(out / 'builder.log') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    report = {**invocation, 'process_wall_seconds': time.perf_counter() - started,
              'scope': 'complete stage on already-local inputs, including interpreter startup; no comparison checks'}
    write_json_exclusive(out / 'stage-timing.json', report, indent=2)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--admitted', type=Path, required=True)
    ap.add_argument('--code-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--extra-argument', action='append', default=[])
    args = ap.parse_args()
    print(json.dumps(run_stage(args.admitted, args.code_root, args.out, args.extra_argument)))


if __name__ == '__main__':
    main()
