"""Job-local cold runtime and actual callable authentication before decoding."""
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import types
import shutil
import bz2
import lzma

PREFIX = Path(__file__).resolve().parent


def file_pin(path):
    path = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def code_value(value):
    if isinstance(value, types.CodeType):
        return {'code': value.co_code.hex(), 'constants': [code_value(x) for x in value.co_consts],
                'names': value.co_names, 'varnames': value.co_varnames, 'freevars': value.co_freevars,
                'cellvars': value.co_cellvars, 'flags': value.co_flags,
                'args': [value.co_argcount, value.co_posonlyargcount, value.co_kwonlyargcount],
                'exceptiontable': value.co_exceptiontable.hex()}
    if isinstance(value, frozenset):
        return {'frozenset': sorted((code_value(x) for x in value), key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(value, tuple):
        return [code_value(x) for x in value]
    if isinstance(value, bytes):
        return {'bytes': value.hex()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {'type': type(value).__name__, 'repr': repr(value)}


def callable_pin(fn):
    if inspect.ismethod(fn):
        fn = fn.__func__
    if hasattr(fn, '__code__'):
        raw = json.dumps(code_value(fn.__code__), sort_keys=True, separators=(',', ':')).encode()
        return {'kind': 'python-code', 'sha256': hashlib.sha256(raw).hexdigest()}
    return {'kind': type(fn).__name__, 'module': fn.__module__, 'name': fn.__qualname__}


def callables():
    import restore
    import verify
    values = {'hashlib.sha256': hashlib.sha256, 'subprocess.run': subprocess.run,
              'subprocess.check_output': subprocess.check_output,
              'Path.open': Path.open, 'Path.read_bytes': Path.read_bytes,
              'Path.stat': Path.stat, 'Path.is_file': Path.is_file,
              'json.loads': json.loads, 'json.dumps': json.dumps}
    for mod in list(sys.modules.values()):
        if mod is None or mod.__name__ == '__main__':
            continue
        for name, value in vars(mod).items():
            if (inspect.isfunction(value) or inspect.isbuiltin(value)) and value.__module__ == mod.__name__:
                values[mod.__name__ + '.' + name] = value
    return {name: callable_pin(value) for name, value in sorted(values.items())}


def snapshot(node):
    # Import the same consumer dependencies before pinning cold runtime state.
    import restore
    import verify
    import shutil, bz2, lzma
    python = file_pin(sys.executable)
    node_pin = file_pin(node)
    versions = {'python': sys.version, 'node': subprocess.check_output([node_pin['path'], '--version'], text=True).strip()}
    module_pins = {}
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if name != '__main__' and path and not str(Path(path).resolve()).startswith(str(PREFIX)):
            module_pins[name] = file_pin(path)
    return {'python': python, 'node': node_pin, 'versions': versions,
            'modules': module_pins, 'callables': callables()}


def authenticate_runtime(node):
    expected = json.loads((PREFIX / 'runtime-guard.json').read_bytes())
    if str(Path(sys.executable).resolve()) != expected['python']['path'] or str(Path(node).resolve()) != expected['node']['path']:
        raise ValueError('Actual cold runtime/import/callable identity differs: executable path')
    if callables() != expected['callables']:
        raise ValueError('Actual cold runtime/import/callable identity differs: callables')
    actual = snapshot(node)
    if actual != expected:
        changed = [k for k in expected if actual.get(k) != expected[k]]
        raise ValueError('Actual cold runtime/import/callable identity differs: ' + ','.join(changed))
    return actual


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', required=True)
    args = parser.parse_args()
    # Import by canonical module identity, as production verify.run does.
    import execution
    raw = json.dumps(execution.snapshot(args.node), sort_keys=True, separators=(',', ':')) + '\n'
    (PREFIX / 'runtime-guard.json').write_text(raw)
