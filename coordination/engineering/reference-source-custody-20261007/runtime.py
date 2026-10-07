"""Authenticate the literal manually imported reference helper objects."""
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def code_value(value):
    # Same canonical CodeType representation as accepted #1386; no marshal
    # interning or address-dependent repr is used as callable identity.
    if isinstance(value, types.CodeType):
        return {'code': value.co_code.hex(),
                'constants': [code_value(x) for x in value.co_consts],
                'names': value.co_names, 'varnames': value.co_varnames,
                'freevars': value.co_freevars, 'cellvars': value.co_cellvars,
                'flags': value.co_flags,
                'args': [value.co_argcount, value.co_posonlyargcount,
                         value.co_kwonlyargcount],
                'exceptiontable': value.co_exceptiontable.hex()}
    if isinstance(value, frozenset):
        return {'frozenset': sorted((code_value(x) for x in value),
                key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(value, tuple):
        return [code_value(x) for x in value]
    if isinstance(value, bytes):
        return {'bytes': value.hex()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError('Unsupported literal callable constant')


def callable_pin(fn):
    if inspect.ismethod(fn):
        fn = fn.__func__
    if hasattr(fn, '__code__'):
        raw = json.dumps(code_value(fn.__code__), sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode()
        return {'kind': 'python-code', 'sha256': hashlib.sha256(raw).hexdigest()}
    return {'kind': type(fn).__name__, 'module': fn.__module__,
            'name': fn.__qualname__}


def file_pin(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def load_original():
    # The authentic ZIP has legacy flag_bits=0 headers; Python lazily loads this
    # exact standard codec when ZipFile reads its central directory. Admit it
    # before freezing runtime bodies, rather than after source reconstruction.
    import encodings.cp437
    plan = json.loads((ROOT / 'input-plan.json').read_bytes())
    for pin in plan['literal_helpers']:
        name = Path(pin['path']).relative_to(
            'coordination/engineering/reference-source-custody-20261007')
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Literal helper must be an ordinary file')
        original = pin['original']
        if (path.stat().st_size != original['bytes'] or
                sha(path) != original['sha256']):
            raise ValueError('Actual literal helper byte drift')
    spec = importlib.util.spec_from_file_location(
        'literal_reference_custody', ROOT / 'literal/scripts/prepare-reference-incremental.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # OWN/VEG/TOPO are deliberately absent from sys.modules in the original
    # recipe, so authenticate these actual executed objects directly.
    objects = {'reference': module, 'OWN': module.OWN, 'VEG': module.VEG,
               'TOPO': module.TOPO, 'majority': sys.modules['majority'],
               'ellipsoidal_area': sys.modules['ellipsoidal_area']}
    expected = {str((ROOT / Path(p['path']).relative_to(
        'coordination/engineering/reference-source-custody-20261007')).resolve()):
        p['original']['sha256'] for p in plan['literal_helpers']}
    for obj in objects.values():
        actual = str(Path(obj.__file__).resolve(strict=True))
        if actual not in expected or sha(actual) != expected[actual]:
            raise ValueError('Actual manual import is outside literal closure')
    return module, objects


def snapshot(objects):
    import numpy
    import rasterio
    import shapely
    versions = {'python': sys.version, 'numpy': numpy.__version__,
                'rasterio': rasterio.__version__, 'gdal': rasterio.__gdal_version__,
                'shapely': shapely.__version__, 'geos': shapely.geos_version_string}
    if not sys.version.startswith('3.12.14') or versions != {
            **versions, 'numpy': '2.3.5', 'rasterio': '1.4.3', 'gdal': '3.9.3',
            'shapely': '2.1.2', 'geos': '3.13.1'}:
        raise ValueError('Actual original reference runtime version drift')
    modules = {}
    for name, obj in sorted(sys.modules.items()):
        path = getattr(obj, '__file__', None)
        if name != '__main__' and path and not Path(path).resolve().is_relative_to(ROOT):
            modules[name] = file_pin(path)
    manual = {name: file_pin(obj.__file__) for name, obj in objects.items()}
    functions = {'Path.open': Path.open, 'Path.read_bytes': Path.read_bytes,
                 'hashlib.sha256': hashlib.sha256, 'json.loads': json.loads}
    reference = objects['reference']
    functions.update({'reference.source_proof': reference.source_proof,
                      'reference.sha': reference.sha,
                      'reference.zipfile.ZipFile': reference.zipfile.ZipFile,
                      'reference.zipfile.ZipFile.getinfo': reference.zipfile.ZipFile.getinfo,
                      'reference.zlib.crc32': reference.zlib.crc32})
    # Constructor/context/reader code is an actual operator, not merely a class name.
    import gzip
    for label, cls in [('ZipFile', reference.zipfile.ZipFile),
                       ('ZipExtFile', reference.zipfile.ZipExtFile),
                       ('GzipFile', gzip.GzipFile)]:
        for method_name, value in vars(cls).items():
            if inspect.isfunction(value):
                functions[label + '.' + method_name] = value
    functions.update({'gzip.compress': gzip.compress, 'gzip.open': gzip.open})
    for name, obj in objects.items():
        for key, value in vars(obj).items():
            if inspect.isfunction(value) and value.__module__ == obj.__name__:
                functions[name + '.' + key] = value
    return {'python': file_pin(sys.executable), 'versions': versions,
            'loaded_module_files': modules, 'actual_manual_objects': manual,
            'callables': {k: callable_pin(v) for k, v in sorted(functions.items())}}


def authenticate(objects, expected):
    actual = snapshot(objects)
    if actual != expected:
        raise ValueError('Actual reference runtime/import/callable drift')
    return actual
