"""Cold actual module/file/callable checks before restoration and operators."""
import gzip
import hashlib
import io
import importlib
from pathlib import Path
import sys
import numpy
import shapely
import pyproj


def cold(pin, guard, baseline, custody, owned):
    versions = {'numpy': numpy.__version__, 'shapely': shapely.__version__,
                'GEOS': shapely.geos_version_string, 'pyproj': pyproj.__version__}
    if sys.version != pin['python'] or versions != pin['versions'] or \
            str(Path(sys.executable).resolve()) != pin['executable']:
        raise ValueError('Actual scientific runtime identity differs')
    receipts, aliases = [], []
    if [row['original_whole_runtime_body'] for row in custody['files']] != pin['whole_runtime_files']:
        raise ValueError('Complete runtime alias roster differs')
    if len(custody['files']) != 25 or len({row['path'] for row in custody['files']}) != 25:
        raise ValueError('Complete unique runtime alias roster required')
    for alias in custody['files']:
        name = alias['path']
        if not name or '/' in name or '\\' in name or name in ('.', '..'):
            raise ValueError('Unsafe whole runtime alias path')
        encoded = baseline.read(owned + 'runtime-bodies/' + name)
        if len(encoded) != alias['bytes'] or len(encoded) > 33554432 or hashlib.sha256(encoded).hexdigest() != alias['sha256']:
            raise ValueError('Whole encoded runtime alias differs')
        with gzip.GzipFile(fileobj=io.BytesIO(encoded), mode='rb') as stream:
            decoded = stream.read(33554433)
        if len(decoded) != alias['uncompressed_bytes'] or len(decoded) > 33554432 or hashlib.sha256(decoded).hexdigest() != alias['uncompressed_sha256']:
            raise ValueError('Whole decoded runtime alias differs')
        row = alias['original_whole_runtime_body']
        path = Path(row['path'])
        with path.open('rb') as stream:
            raw = stream.read(row['bytes'] + 1)
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Actual whole runtime body differs: ' + str(path))
        if decoded != raw:
            raise ValueError('Complete reconstructed alias differs from actual installed runtime')
        receipts.append(dict(row))
        aliases.append({'commit': baseline.commit, 'path': owned + 'runtime-bodies/' + name,
                        'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest(),
                        'uncompressed_bytes': len(decoded), 'uncompressed_sha256': hashlib.sha256(decoded).hexdigest(),
                        'hash_kind': 'file-bytes', 'original_whole_runtime_body': dict(row)})
    callables = []
    for name, expected in pin['module_paths'].items():
        module = importlib.import_module(name)
        if expected == 'built-in':
            if getattr(module, '__file__', None) is not None or module.__spec__.origin != 'built-in':
                raise ValueError('Loaded built-in runtime binding differs: ' + name)
            continue
        if str(Path(module.__file__).resolve()) != expected:
            raise ValueError('Actual loaded runtime module escaped its binding: ' + name)
        if name in pin.get('critical_callables', {}):
            callables.extend(guard.callable_guard(module, Path(expected).read_bytes(), pin['critical_callables'][name]))
        if name in pin['stdlib_callable_modules']:
            callables.extend(guard.all_callables(module, Path(expected).read_bytes()))
    return {'identity': versions, 'python': sys.version, 'whole_runtime_files': receipts,
            'whole_runtime_aliases': aliases, 'actual_module_paths': pin['module_paths'], 'actual_stdlib_callables': callables,
            'limits': pin['limits']}
