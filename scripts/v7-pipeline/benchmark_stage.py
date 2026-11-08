#!/usr/bin/env python3
"""Time one complete admitted stage on pinned local inputs, without downloads.

The admitted arguments are retained, except for the checkout, fresh output and
explicitly requested extra arguments. Stages use main(argv, emit=...) in the
current interpreter. Run benchmarks sequentially for comparable timings.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.util
import inspect
import json
import os
import platform
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

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
            'python_version': sys.version,
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
    builder = (code_root / relative).resolve()
    if not builder.is_relative_to((code_root / 'scripts').resolve()) or not builder.is_file():
        raise ValueError(f'missing stage script: {relative}')
    command[1] = str(builder)
    command[command.index('--out') + 1] = str(candidate)
    if any(v == '--out' or v.startswith('--out=') for v in extra_arguments):
        raise ValueError('extra arguments cannot replace the fresh output')
    if any(not flag.startswith('--') or '=' in flag or flag in ('--out', '--input-root') for flag in drop_boolean_options):
        raise ValueError('only explicit classifier boolean options can be removed')
    command = [arg for arg in command if arg not in drop_boolean_options]
    return command + list(extra_arguments)


def check_module_origins(directories):
    """Refuse sibling imports cached from a different checkout."""
    expected = {}
    for directory in directories:
        for path in directory.glob('*.py'):
            expected.setdefault(path.stem, path.resolve())
    for name, path in expected.items():
        module = sys.modules.get(name)
        if module is not None and Path(getattr(module, '__file__', '')).resolve() != path:
            raise ImportError(f'benchmark module {name} resolved outside the selected checkout')


def invoke_stage(builder, arguments, log):
    """Call a stage's ordinary Python API without changing argv or starting a CLI."""
    scripts = next(parent for parent in builder.parents if parent.name == 'scripts')
    directories = tuple(dict.fromkeys((builder.parent, scripts,
                                       scripts / 'v7-replay', scripts / 'v7-recovery/ocean')))
    check_module_origins(directories)
    previous = sys.path[:]
    name = '_worldatlas_benchmark_' + hashlib.sha256(str(builder).encode()).hexdigest()
    if name in sys.modules:
        raise ImportError('benchmark stage is already active in this interpreter')
    try:
        sys.path[:0] = [str(path) for path in directories]
        spec = importlib.util.spec_from_file_location(name, builder)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            spec.loader.exec_module(module)
            check_module_origins(directories)
            api = getattr(module, 'main', None)
            emit = lambda *values, **options: print(*values, **{**options, 'file': log})
            if api is None:
                raise TypeError('benchmark stage must provide main(argv, *, emit)')
            inspect.signature(api).bind(arguments, emit=emit)
            try:
                api(arguments, emit=emit)
            except SystemExit as exc:
                if exc.code not in (0, None):
                    raise RuntimeError(f'benchmark stage failed ({exc.code})') from exc
            check_module_origins(directories)
    finally:
        sys.path[:] = previous
        sys.modules.pop(name, None)


def run_stage(admission, code_root, out, extra_arguments=(), *, drop_boolean_options=()):
    admitted = json.loads(admission.read_text())
    out = out.absolute()
    if out.exists() or not out.parent.is_dir():
        raise ValueError('benchmark output must be new with an existing parent')
    command = stage_command(admitted, code_root.resolve(), out / 'candidate', extra_arguments, drop_boolean_options=drop_boolean_options)
    create_directory_exclusive(out)
    invocation = {'command': command, 'environment': environment(), 'admission_sha256': digest(admission),
                  'builder_sha256': digest(Path(command[1])),
                  'execution_mode': 'in-process-python-api', 'actual_interpreter': sys.executable}
    write_json_exclusive(out / 'invocation.json', invocation, indent=2)
    started_utc = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    with create_text_exclusive(out / 'builder.log') as log:
        invoke_stage(Path(command[1]), command[2:], log)
    elapsed = time.perf_counter() - started
    completed_utc = datetime.now(timezone.utc).isoformat()
    if digest(Path(command[1])) != invocation['builder_sha256']:
        raise ValueError('stage entrypoint changed during execution')
    report = {**invocation, 'process_wall_seconds': elapsed, 'stage_wall_seconds': elapsed,
              'started_utc': started_utc, 'completed_utc': completed_utc,
              'scope': 'complete in-process stage on already-local inputs, including module loading; no interpreter startup or comparison checks'}
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
