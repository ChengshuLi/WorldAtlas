"""Complete bounded cold Python/native/data custody before scientific imports."""
import binascii
import ctypes
import gzip
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys

LIMIT = 33554432
PHASE = 268435456


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def image_paths():
    library = ctypes.CDLL(None)
    library._dyld_image_count.restype = ctypes.c_uint32
    library._dyld_get_image_name.argtypes = [ctypes.c_uint32]
    library._dyld_get_image_name.restype = ctypes.c_char_p
    return [library._dyld_get_image_name(i).decode()
            for i in range(library._dyld_image_count())]


def verify_index(raw, pin):
    require(len(raw) <= LIMIT and sha(raw) == pin['custody_index_sha256'],
            'Complete frozen runtime index differs')
    index = json.loads(raw)
    rows, shards = index['files'], index['shards']
    require(len(rows) == pin['whole_runtime_body_count'] and
            [row['ordinal'] for row in rows] == list(range(len(rows))) and
            len({row['path'] for row in rows}) == len(rows),
            'Complete unique runtime membership differs')
    require(len(shards) == pin['runtime_shard_count'] and
            len({row['path'] for row in shards}) == len(shards),
            'Complete unique runtime shard roster differs')
    for row in rows:
        path = Path(row['path'])
        require(path.is_absolute() and '..' not in path.parts and
                str(path.resolve()) == row['path'] and type(row['bytes']) is int and
                0 <= row['bytes'] <= LIMIT and type(row['mode']) is int and
                row['mode'] in (0o644, 0o755), 'Unsafe runtime member path/mode/bound')
    for row in shards:
        require(row['path'].startswith('runtime-custody/') and
                '\\' not in row['path'] and all(p not in ('', '.', '..')
                for p in row['path'].split('/')) and
                type(row['bytes']) is int and type(row['uncompressed_bytes']) is int and
                0 <= row['bytes'] <= LIMIT and 0 <= row['uncompressed_bytes'] <= LIMIT,
                'Unsafe runtime shard path/ordinary bound')
    require(sum(row['bytes'] for row in rows) == index['logical_raw_bytes'] and
            sum(row['bytes'] for row in shards) == index['encoded_transport_bytes'] and
            sum(row['uncompressed_bytes'] for row in shards) == index['decoded_transport_bytes'],
            'Complete runtime byte accounting differs')
    return index



def drift_plan(pin, baseline, owned):
    declared = pin['current_runtime_delta']
    require(declared['path'].startswith('runtime-custody/') and
            '\\' not in declared['path'] and all(part not in ('', '.', '..')
            for part in declared['path'].split('/')), 'Unsafe current runtime delta path')
    raw = baseline.pinned_bytes(owned + declared['path'])
    require(len(raw) == declared['bytes'] <= LIMIT and sha(raw) == declared['sha256'],
            'Whole current runtime delta transport differs')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        decoded = stream.read(LIMIT + 1)
    require(len(decoded) == declared['uncompressed_bytes'] <= LIMIT and
            sha(decoded) == declared['uncompressed_sha256'], 'Whole current runtime delta decoded differs')
    baseline.admit('current-runtime-delta:decoded', len(decoded))
    value = json.loads(decoded)
    changes = value['changes']
    require(value['version'] == 1 and
            value['original_custody_index_sha256'] == pin['custody_index_sha256'] and
            [{k: v for k, v in row.items() if k != 'commands'} for row in changes] == declared['changes'] and
            len(changes) == 3 and len({r['ordinal'] for r in changes}) == 3,
            'Complete current runtime delta/source roster differs')
    return {row['ordinal']: row for row in changes}, dict(
        commit=baseline.commit, **{k: declared[k] for k in
        ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256')},
        path=owned + declared['path'], hash_kind='file-bytes')


def apply_delta(original, row, delta):
    require(delta['path'] == row['path'] and delta['original_bytes'] == len(original) and
            delta['original_sha256'] == sha(original) and delta['original_mode'] == row['mode'] and
            type(delta['current_bytes']) is int and 0 <= delta['current_bytes'] <= LIMIT and
            delta['current_mode'] in (0o644, 0o755), 'Current runtime delta original/bound differs')
    output = bytearray()
    require(type(delta['commands']) is list and delta['commands'], 'Empty runtime delta inverse')
    for command in delta['commands']:
        require(type(command) is dict and len(command) == 1, 'Ambiguous runtime delta command')
        if 'copy' in command:
            pair = command['copy']
            require(type(pair) is list and len(pair) == 2 and
                    all(type(v) is int for v in pair) and pair[0] >= 0 and pair[1] > 0 and
                    pair[0] + pair[1] <= len(original), 'Escaped runtime delta copy range')
            chunk = original[pair[0]:pair[0] + pair[1]]
        else:
            require('literal' in command and type(command['literal']) is str,
                    'Unknown runtime delta command')
            chunk = binascii.a2b_base64(command['literal'], strict_mode=True)
        require(len(output) + len(chunk) <= delta['current_bytes'], 'Runtime delta decoded output overflow')
        output.extend(chunk)
    body = bytes(output)
    require(len(body) == delta['current_bytes'] and sha(body) == delta['current_sha256'],
            'Complete current runtime delta raw body differs')
    return body, dict(row, bytes=len(body), sha256=sha(body), mode=delta['current_mode'])


def current_index(index, pin):
    rows = [dict(row) for row in index['files']]
    for delta in pin['current_runtime_delta']['changes']:
        row = rows[delta['ordinal']]
        require(row['path'] == delta['path'] and row['sha256'] == delta['original_sha256'],
                'Current runtime origin roster source differs')
        row.update(bytes=delta['current_bytes'], sha256=delta['current_sha256'], mode=delta['current_mode'])
    return dict(index, files=rows)


def prepare(pin, index_raw, baseline, owned):
    """Validate all groups and members before exposing package paths or bodies."""
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            'Cold isolated no-site/no-bytecode startup required')
    cache = Path(baseline.repo) / '.cache' / '1394-never-materialized-bytecode'
    require(sys.pycache_prefix == str(cache) and not cache.exists() and
            not cache.is_symlink(), 'Fixed absent bytecode prefix required')
    require(sys.version == pin['python'] and
            str(Path(sys.executable).resolve()) == pin['executable'],
            'Actual interpreter identity differs')
    require(not any(name == package or name.startswith(package + '.')
                    for name in sys.modules for package in ('numpy', 'shapely', 'pyproj')),
            'Scientific package was imported before complete runtime authentication')
    index = verify_index(index_raw, pin)
    changes, delta_alias = drift_plan(pin, baseline, owned)
    rows, seen, aliases, previous = index['files'], set(), [], []
    current_rows = []
    old = {row['group_logical_ordinal']: row for row in index['previous25_inverse']['rows']}
    require(len(old) == len(index['previous25_inverse']['rows']) == 25 and
            index['previous25_inverse']['all_inverse_equal'] is True,
            'Original25 custody inverse roster differs')
    for number, declared in enumerate(index['shards']):
        encoded = baseline.pinned_bytes(owned + declared['path'])
        require(len(encoded) == declared['bytes'] and len(encoded) <= LIMIT and
                sha(encoded) == declared['sha256'], 'Whole encoded runtime shard differs')
        digest, total, actual = hashlib.sha256(), 0, []
        with gzip.GzipFile(fileobj=io.BytesIO(encoded), mode='rb') as stream:
            while True:
                line = stream.readline(LIMIT + 1)
                if not line:
                    break
                offset = total
                total += len(line)
                require(len(line) <= LIMIT and total <= LIMIT and
                        total <= declared['uncompressed_bytes'], 'Actual decoded runtime shard bound')
                digest.update(line)
                member = json.loads(line)
                ordinal = member.pop('ordinal')
                text = member.pop('raw_base64')
                require(type(ordinal) is int and 0 <= ordinal < len(rows) and
                        ordinal not in seen, 'Missing/duplicate runtime member')
                row = rows[ordinal]
                fields = {k: v for k, v in row.items() if k not in
                          ('ordinal', 'shard', 'decoded_offset', 'decoded_line_bytes', 'decoded_line_sha256')}
                require(member == fields and row['shard'] == number and
                        row['decoded_offset'] == offset and row['decoded_line_bytes'] == len(line) and
                        row['decoded_line_sha256'] == sha(line), 'Runtime member/index envelope differs')
                body = binascii.a2b_base64(text, strict_mode=True)
                require(len(body) == row['bytes'] and len(body) <= LIMIT and sha(body) == row['sha256'],
                        'Complete logical runtime raw body differs')
                baseline.admit('logical-runtime-' + str(ordinal), len(body))
                if ordinal in old:
                    original = old[ordinal]
                    require(original['group_raw_bytes'] == len(body) and
                            original['group_raw_sha256'] == sha(body),
                            'Original25 inverse raw member differs')
                    inverse = gzip.compress(body, compresslevel=9, mtime=0)
                    require(len(inverse) == original['original_bytes'] and
                            sha(inverse) == original['original_sha256'],
                            'Original25 whole encoded inverse differs')
                    previous.append(dict(original, actual_inverse_bytes=len(inverse),
                                         actual_inverse_sha256=sha(inverse)))
                current_row = row
                if ordinal in changes:
                    body, current_row = apply_delta(body, row, changes[ordinal])
                    baseline.admit('logical-current-runtime-' + str(ordinal), len(body))
                path = Path(current_row['path'])
                require(not path.is_symlink() and path.is_file() and
                        (path.stat().st_mode & 0o777) == current_row['mode'], 'Installed runtime mode/path differs')
                with path.open('rb') as installed:
                    require(installed.read(len(body) + 1) == body, 'Actual installed runtime body differs')
                current_rows.append(current_row)
                seen.add(ordinal)
                actual.append(ordinal)
        require(total == declared['uncompressed_bytes'] and
                digest.hexdigest() == declared['uncompressed_sha256'] and actual == declared['members'],
                'Complete decoded runtime shard/membership differs')
        baseline.admit('runtime-shard-decoded-' + str(number), total)
        aliases.append({'commit': baseline.commit, 'path': owned + declared['path'],
                        **{k: declared[k] for k in ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256')},
                        'hash_kind': 'file-bytes'})
    require(seen == set(range(len(rows))) and len(previous) == 25,
            'Complete runtime custody/inverse membership differs')
    require(sum(baseline.consumed.values()) <= PHASE,
            'Runtime code/encoded/decoded/logical admission exceeds phase')
    aliases.append(delta_alias)
    require({r['ordinal'] for r in current_rows} == set(range(len(rows))),
            'Complete current runtime installed roster differs')
    sites = pin['site_paths']
    require(len(sites) == len(set(sites)) == 2 and
            all(Path(p).is_absolute() and Path(p).is_dir() for p in sites),
            'Exact scientific package roots required')
    # -S prevents site/.pth execution. No scientific import occurs before this point.
    sys.path[:0] = sites
    return {'whole_runtime_files': [{k: row[k] for k in ('path', 'bytes', 'sha256', 'mode')}
                                   for row in sorted(current_rows, key=lambda row: row['ordinal'])], 'whole_runtime_aliases': aliases,
            'original_logical_runtime_raw_bytes': index['logical_raw_bytes'],
            'logical_runtime_raw_bytes': sum(row['bytes'] for row in current_rows),
            'runtime_encoded_bytes': index['encoded_transport_bytes'] + delta_alias['bytes'],
            'runtime_decoded_bytes': index['decoded_transport_bytes'] + delta_alias['uncompressed_bytes'],
            'runtime_code_encoded_decoded_logical_phase_bytes': sum(baseline.consumed.values()),
            'original25_actual_inverse': previous, 'custody_index_sha256': sha(index_raw),
            'startup': {'isolated': sys.flags.isolated, 'no_site': sys.flags.no_site,
                        'dont_write_bytecode': sys.dont_write_bytecode,
                        'pycache_prefix': sys.pycache_prefix, 'site_paths': sites},
            'limits': pin['limits']}


def loaded(pin, index, *, repo, owned, project_pins):
    """Reject every unlisted actual origin/image, including later lazy imports."""
    # Load scientific packages before scanning their actual lazy origins/images.
    import numpy
    import shapely
    import pyproj
    index = current_index(index, pin)
    known = {row['path']: row for row in index['files']}
    origins = {row['module']: row for row in index['module_origins']}
    project = {str((Path(repo) / row['path']).resolve()): row for row in project_pins
               if row['path'].endswith('.py')}
    receipts = []
    for name, module in sorted(sys.modules.items()):
        origin = getattr(getattr(module, '__spec__', None), 'origin', None)
        path = getattr(module, '__file__', None)
        if origin == 'built-in':
            require(name in index['builtin_modules'], 'Unknown loaded built-in origin: ' + name)
        if origin == 'frozen':
            require(name in index['frozen_modules'], 'Unknown loaded frozen origin: ' + name)
        if not path:
            require(origin in ('built-in', 'frozen', None), 'Unbound no-file module origin: ' + name)
            continue
        path = Path(path).resolve()
        require(path.suffix != '.pyc', 'Actual bytecode-cache origin forbidden: ' + name)
        row = project.get(str(path)) or known.get(str(path))
        if str(path) not in project:
            expected_origin = origins.get(name)
            require(expected_origin is not None and
                    expected_origin['path'] == str(path) and
                    expected_origin['origin'] == origin,
                    'Actual module name/origin binding differs: ' + name)
        require(row is not None, 'Loaded origin lacks complete whole-body pin: ' + name + ':' + str(path))
        with path.open('rb') as stream:
            body = stream.read(row['bytes'] + 1)
        require(len(body) == row['bytes'] and sha(body) == row['sha256'],
                'Actual loaded origin body differs: ' + name)
        if row.get('mode') is not None:
            require((path.stat().st_mode & 0o777) == row['mode'], 'Actual loaded origin mode differs')
        receipts.append({'module': name, 'origin': origin, 'path': str(path),
                         'bytes': len(body), 'sha256': row['sha256']})
    native, platform = [], []
    for path in image_paths():
        if path.startswith('/Users/chengshuli/'):
            path = str(Path(path).resolve())
            row = known.get(path)
            require(row is not None, 'Unlisted installed native image: ' + path)
            with Path(path).open('rb') as stream:
                body = stream.read(row['bytes'] + 1)
            require(len(body) == row['bytes'] and sha(body) == row['sha256'] and
                    (Path(path).stat().st_mode & 0o777) == row['mode'], 'Native image body/mode differs')
            native.append({'path': path, 'bytes': len(body), 'sha256': row['sha256']})
        else:
            require(path in index['system_image_paths'], 'Unrecorded platform native image: ' + path)
            platform.append(path)
    versions = {'numpy': numpy.__version__, 'shapely': shapely.__version__,
                'GEOS': shapely.geos_version_string, 'pyproj': pyproj.__version__}
    require(versions == pin['versions'], 'Actual scientific version identity differs')
    require(str(Path(pyproj.datadir.get_data_dir()).resolve()) == index['PROJ_data_dir'] and
            pyproj.network.is_network_enabled() is False, 'Actual PROJ data/network binding differs')
    for row in index['files']:
        if 'pinned-PROJ-data' in row['roles']:
            body = Path(row['path']).read_bytes()
            require(len(body) == row['bytes'] and sha(body) == row['sha256'] and
                    (Path(row['path']).stat().st_mode & 0o777) == row['mode'],
                    'Actual PROJ data body/mode differs')
    return {'actual_module_origins': receipts, 'actual_installed_native_images': native,
            'actual_named_platform_images': platform, 'versions': versions,
            'PROJ_data_dir': index['PROJ_data_dir'], 'PROJ_network_enabled': False}


def callables(pin, guard):
    receipts = []
    for name in pin['stdlib_callable_modules']:
        module = importlib.import_module(name)
        receipts.extend(guard.all_callables(module, Path(module.__file__).read_bytes()))
    for name, required in pin['critical_callables'].items():
        module = importlib.import_module(name)
        receipts.extend(guard.callable_guard(module, Path(module.__file__).read_bytes(), required))
    return receipts


def scientific_bindings(methods):
    import numpy
    import shapely
    import shapely.geometry
    import shapely.geometry.base
    import shapely.strtree
    functions = {name: getattr(numpy, name) for name in
                 ('sin', 'cos', 'arctanh', 'dot', 'asarray', 'deg2rad')}
    functions.update({name: getattr(shapely, name) for name in
                      ('prepare', 'union_all', 'make_valid', 'intersection', 'difference',
                       'intersects', 'covers', 'contains')})
    functions.update(shape=shapely.geometry.shape, mapping=shapely.geometry.mapping,
                     Polygon=shapely.geometry.Polygon, STRtree=shapely.strtree.STRtree,
                     tree_query=shapely.strtree.STRtree.query,
                     method_intersection=shapely.geometry.base.BaseGeometry.intersection,
                     method_intersects=shapely.geometry.base.BaseGeometry.intersects)
    for module_name in ('comparison', 'kernel', 'trace'):
        for name, value in vars(methods[module_name]).items():
            if callable(value) and getattr(value, '__module__', '').split('.')[0] in ('numpy', 'shapely'):
                functions[module_name + '.' + name] = value
    ellipsoid = methods['ellipsoidal_area']
    constants = {name: getattr(ellipsoid, name).tobytes() for name in ('NODES', 'WEIGHTS')}
    return {name: (value, getattr(value, '__code__', None)) for name, value in functions.items()}, constants


def require_scientific_bindings(methods, expected):
    actual = scientific_bindings(methods)
    require(actual[0].keys() == expected[0].keys() and actual[1] == expected[1] and
            all(actual[0][name][0] is value and actual[0][name][1] is code
                for name, (value, code) in expected[0].items()),
            'Actual scientific callable/quadrature binding changed')
