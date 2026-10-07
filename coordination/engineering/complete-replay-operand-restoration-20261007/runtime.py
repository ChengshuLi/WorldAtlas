"""Cold actual module/file/callable checks before restoration and operators."""
import hashlib
import importlib
from pathlib import Path
import sys
import numpy
import shapely
import pyproj


def cold(pin, guard):
    versions = {'numpy': numpy.__version__, 'shapely': shapely.__version__,
                'GEOS': shapely.geos_version_string, 'pyproj': pyproj.__version__}
    if sys.version != pin['python'] or versions != pin['versions'] or \
            str(Path(sys.executable).resolve()) != pin['executable']:
        raise ValueError('Actual scientific runtime identity differs')
    receipts = []
    for row in pin['whole_runtime_files']:
        path = Path(row['path'])
        with path.open('rb') as stream:
            raw = stream.read(row['bytes'] + 1)
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Actual whole runtime body differs: ' + str(path))
        receipts.append(dict(row))
    callables = []
    for name, expected in pin['module_paths'].items():
        module = importlib.import_module(name)
        if expected == 'built-in':
            if getattr(module, '__file__', None) is not None or module.__spec__.origin != 'built-in':
                raise ValueError('Loaded built-in runtime binding differs: ' + name)
            continue
        if str(Path(module.__file__).resolve()) != expected:
            raise ValueError('Actual loaded runtime module escaped its binding: ' + name)
        if name in pin['stdlib_callable_modules']:
            callables.extend(guard.all_callables(module, Path(expected).read_bytes()))
    return {'identity': versions, 'python': sys.version, 'whole_runtime_files': receipts,
            'actual_module_paths': pin['module_paths'], 'actual_stdlib_callables': callables,
            'limits': pin['limits']}
