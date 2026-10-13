"""Versioned installed Python identity; cached code is verified, never ignored.

Usage: python3 -I -S -B scripts/package-python-runtime.py '[{"name":"numpy"}, ...]'
Only physical cache filenames and valid cache-header metadata can normalize.
Source, native libraries, package metadata and other installed bytes stay exact.
"""
import base64
from contextlib import contextmanager
import hashlib
import importlib
import importlib.metadata
import importlib.util
import io
import json
import marshal
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import sysconfig
import tempfile
import types

VERSION = 2
DEFAULT_ROOTS = ('numpy', 'shapely', 'pyproj', 'rasterio', 'scipy')
CHUNK = 1024 * 1024


def need(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def available_memory(read_text=None, sysconf=None):
    """Kernel available memory, intersected with each known cgroup ceiling."""
    read_text = read_text or (lambda path: Path(path).read_text())
    sysconf = sysconf or os.sysconf
    def optional(path):
        try:
            return read_text(path)
        except OSError:
            return None
    def counters(text):
        return {parts[0].rstrip(':'): int(parts[1]) for line in (text or '').splitlines()
                if len(parts := line.split()) >= 2 and parts[1].isdigit()}
    memory = counters(optional('/proc/meminfo'))
    if 'MemAvailable' in memory:
        host = {'kind': 'linux-MemAvailable', 'bytes': memory['MemAvailable'] * 1024}
    else:
        host = {'kind': 'available-physical-pages-fallback',
                'bytes': sysconf('SC_AVPHYS_PAGES') * sysconf('SC_PAGE_SIZE')}
    available, constraints = host['bytes'], []
    for base, limit_name, current_name, stat_name, prefix in (
        ('/sys/fs/cgroup', 'memory.max', 'memory.current', 'memory.stat', ''),
        ('/sys/fs/cgroup/memory', 'memory.limit_in_bytes', 'memory.usage_in_bytes', 'memory.stat', 'total_')):
        limit_raw = optional(base + '/' + limit_name)
        if limit_raw is None or limit_raw.strip() == 'max':
            continue
        current_raw = optional(base + '/' + current_name)
        need(limit_raw.strip().isdigit() and current_raw is not None and current_raw.strip().isdigit(),
             'Malformed cgroup memory ceiling/current usage')
        limit, current = int(limit_raw), int(current_raw)
        stats = counters(optional(base + '/' + stat_name))
        get = lambda name: stats.get(prefix + name, stats.get(name, 0))
        inactive = get('inactive_file')
        # Do not promise reclaim of anonymous/shared, dirty, or writeback pages.
        file_bytes = get('file') if not prefix else get('cache')
        reclaimable = max(0, min(inactive, max(0, file_bytes - get('shmem')), current)
                          - get('file_dirty') - get('file_writeback') - get('dirty') - get('writeback'))
        headroom = max(0, min(limit, limit - current + reclaimable))
        constraints.append({'path': base, 'limit_bytes': limit, 'current_bytes': current,
                            'clean_inactive_file_bytes': reclaimable, 'available_bytes': headroom})
        available = min(available, headroom)
    return {'host': host, 'cgroups': constraints, 'available_bytes': max(0, available)}


def object_nodes(value, excluded=lambda identity: False):
    """Owned Python object bytes; no traversal into unrelated module globals."""
    nodes, pending = {}, [value]
    while pending:
        item = pending.pop()
        identity = id(item)
        if identity in nodes or excluded(identity):
            continue
        nodes[identity] = sys.getsizeof(item)
        if isinstance(item, dict):
            pending.extend(item.keys()); pending.extend(item.values())
        elif isinstance(item, (list, tuple, set, frozenset)):
            pending.extend(item)
        elif isinstance(item, types.CodeType):
            pending.extend(getattr(item, field) for field in (*CODE_FIELDS, 'co_filename') if hasattr(item, field))
        elif isinstance(item, PurePosixPath):
            for cls in type(item).__mro__:
                for slot in getattr(cls, '__slots__', ()):
                    if slot not in ('__weakref__', '__dict__'):
                        try: pending.append(object.__getattribute__(item, slot))
                        except AttributeError: pass
    return nodes


class Budget:
    """One physical additional-allocation budget, with scoped peak accounting."""
    def __init__(self, maximum=None):
        self.source = available_memory() if maximum is None else {'kind': 'explicit-physical-bytes', 'bytes': maximum}
        if maximum is None:
            # Leave half of the kernel's available headroom for the caller and
            # concurrent work. Object expansion is charged below, not again here.
            maximum = self.source['available_bytes'] // 2
        self.maximum, self.used, self.scopes = maximum, 0, []
        self.retained_ids = set()
        self.operation, self.peak_charged = 'initialize budget', 0
        need(type(maximum) is int and maximum > 0, self.diagnostic(0, 'initialize budget'))
        self.admit(0, 'initialize budget')
        self.virtual_base = None
        if sys.platform == 'linux':
            self.virtual_base = int(Path('/proc/self/statm').read_text().split()[0]) * os.sysconf('SC_PAGE_SIZE')

    def bookkeeping(self):
        return sys.getsizeof(self.retained_ids) + len(self.retained_ids) * sys.getsizeof(id(self))

    def scoped_bytes(self):
        return sum(scope['bytes'] + sys.getsizeof(scope['nodes']) +
                   len(scope['nodes']) * (sys.getsizeof(id(self)) + sys.getsizeof(0)) for scope in self.scopes)

    def diagnostic(self, size, operation):
        return 'Installed Python physical-memory admission: ' + json.dumps({
            'operation': str(operation)[:320], 'capacity_bytes': self.maximum,
            'baseline_virtual_bytes': getattr(self, 'virtual_base', None),
            'allocation_ceiling_bytes': getattr(self, 'allocation_ceiling', None),
            'retained_bytes': self.used, 'scoped_bytes': self.scoped_bytes(),
            'bookkeeping_bytes': self.bookkeeping(), 'working_bytes': size,
            'capacity_source': self.source}, sort_keys=True, separators=(',', ':'))

    def admit(self, size, operation='metadata working set'):
        need(type(size) is int and size >= 0, 'Invalid physical-memory working-set charge')
        self.operation = operation
        total = self.used + self.scoped_bytes() + self.bookkeeping() + size
        self.peak_charged = max(self.peak_charged, total)
        if total > self.maximum:
            raise ValueError(self.diagnostic(size, operation))

    def retain(self, value):
        nodes = object_nodes(value, self.retained_ids.__contains__)
        # Ownership of shared members moves to the retained result; it is never
        # charged both as a live member-map object and as retained evidence.
        for scope in self.scopes:
            for identity in nodes:
                scope['bytes'] -= scope['nodes'].pop(identity, 0)
        self.used += sum(nodes.values())
        self.retained_ids.update(nodes)
        self.admit(0, 'retain evidence row/container')

    @contextmanager
    def scoped(self, value, operation):
        nodes = object_nodes(value, lambda identity: identity in self.retained_ids or
                             any(identity in scope['nodes'] for scope in self.scopes))
        scope = {'nodes': nodes, 'bytes': sum(nodes.values())}
        self.scopes.append(scope)
        try:
            self.admit(0, operation)
            yield
        finally:
            self.scopes.pop()


@contextmanager
def allocation_limit(budget):
    # The ceiling is fixed at budget creation, not reset from an ever-growing
    # per-file process size. It covers parser/import metadata, marshal/compile,
    # canonical encodings, final digests, validation and output serialization.
    if sys.platform != 'linux':
        yield
        return
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    allowed = budget.virtual_base + budget.maximum
    if soft != resource.RLIM_INFINITY:
        allowed = min(allowed, soft)
    if hard != resource.RLIM_INFINITY:
        allowed = min(allowed, hard)
    budget.allocation_ceiling = allowed
    failure = None
    resource.setrlimit(resource.RLIMIT_AS, (allowed, hard))
    try:
        yield
    except MemoryError as error:
        failure = error
    finally:
        resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
    if failure is not None:
        raise ValueError(budget.diagnostic(0, 'OS allocation limit during ' + budget.operation)) from failure


def ordinary(path):
    path = Path(path)
    need(path.absolute() == path.resolve(strict=True), 'Installed Python member has a linked ancestor')
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode), 'Installed Python member is not an ordinary file')
    return info


def read_file(path, budget, body=False):
    path = Path(path)
    before = ordinary(path)
    block = min(CHUNK, max(1, before.st_size))
    if body:
        budget.admit(2 * before.st_size + block, 'read/join body: ' + str(path))
    else:
        budget.admit(2 * block, 'stream file hash: ' + str(path))
    checksum, chunks, size = hashlib.sha256(), [], 0
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        with os.fdopen(fd, 'rb') as stream:
            while True:
                chunk = stream.read(block)
                if not chunk:
                    break
                size += len(chunk)
                need(size <= before.st_size, 'Installed Python member grew while reading')
                checksum.update(chunk)
                if body:
                    chunks.append(chunk)
            held = os.fstat(stream.fileno())
        after = ordinary(path)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_mtime_ns', 'st_ctime_ns')
        need(size == before.st_size and all(getattr(before, key) == getattr(held, key) == getattr(after, key)
                                           for key in fields), 'Installed Python member changed while reading')
    except BaseException:
        # fdopen owns fd once constructed; callers never receive partial evidence.
        raise
    raw = {'bytes': size, 'sha256': checksum.hexdigest(),
           'mode': '100755' if before.st_mode & 0o111 else '100644'}
    return raw, b''.join(chunks) if body else None


CODE_FIELDS = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals',
               'co_stacksize', 'co_flags', 'co_code', 'co_consts', 'co_names', 'co_varnames',
               'co_freevars', 'co_cellvars', 'co_name', 'co_qualname', 'co_firstlineno',
               'co_linetable', 'co_exceptiontable')


def canonical_code(code, physical_source, logical_source):
    """Preserve every executable/code-position field, normalize one proven path."""
    def value(item):
        if isinstance(item, types.CodeType):
            need(item.co_filename == physical_source, 'Cached nested filename differs from actual source')
            result = {field: value(getattr(item, field)) for field in CODE_FIELDS if hasattr(item, field)}
            result['co_filename'] = ['str', logical_source]
            return ['code', result]
        if item is None:
            return ['none']
        if item is Ellipsis:
            return ['ellipsis']
        if type(item) is bool:
            return ['bool', item]
        if type(item) is int:
            return ['int', str(item)]
        if type(item) is float:
            return ['float', struct.pack('>d', item).hex()]
        if type(item) is complex:
            return ['complex', struct.pack('>dd', item.real, item.imag).hex()]
        if type(item) is str:
            return ['str', item]
        if type(item) is bytes:
            return ['bytes', base64.b64encode(item).decode('ascii')]
        if type(item) is tuple:
            return ['tuple', [value(child) for child in item]]
        if type(item) is frozenset:
            children = [value(child) for child in item]
            return ['frozenset', sorted(children, key=encoded)]
        raise ValueError('Unsupported executable cache constant')
    return encoded(value(code))


def cache_source(file, members):
    """Only an explicitly inventoried ordinary source can justify normalization."""
    if file.suffix != '.pyc':
        return None
    if file.parent.name == '__pycache__':
        match = re.fullmatch(r'(.+)\.' + re.escape(sys.implementation.cache_tag) + r'(?:\.opt-([012]))?\.pyc', file.name)
        if not match:
            return None
        source = file.parent.parent / (match[1] + '.py')
        optimization = int(match[2] or 0)
    else:
        source, optimization = file.with_suffix('.py'), sys.flags.optimize
    if source not in members:
        return None
    return source, optimization


def file_identity(distribution, logical, file, members, budget):
    binding = cache_source(file, members)
    if binding:
        budget.admit(2 * (ordinary(file).st_size + ordinary(binding[0]).st_size) + CHUNK,
                     'read source/cache pair: ' + str(file))
    raw, body = read_file(file, budget, body=binding is not None)
    effective = dict(raw, kind='exact')
    row = {'distribution': distribution, 'path': logical, 'raw': raw, 'effective': effective}
    if binding:
        source, optimization = binding
        source_logical = members[source]
        source_raw, source_body = read_file(source, budget, body=True)
        need(len(body) >= 16 and body[:4] == importlib.util.MAGIC_NUMBER, 'Invalid source-backed cache magic/header')
        flags = int.from_bytes(body[4:8], 'little')
        need(flags in (0, 1, 3), 'Invalid source-backed cache invalidation flags')
        # Header validity is explicit evidence. A stale timestamp/hash is allowed
        # only because fresh compilation independently establishes identical code.
        if flags & 1:
            header = {'kind': 'checked-hash' if flags & 2 else 'unchecked-hash',
                      'source_hash': body[8:16].hex(),
                      'matches_source': body[8:16] == importlib.util.source_hash(source_body)}
        else:
            timestamp, source_bytes = struct.unpack('<II', body[8:16])
            header = {'kind': 'timestamp', 'timestamp': timestamp, 'source_bytes': source_bytes,
                      'matches_source': timestamp == int(source.stat().st_mtime) & 0xffffffff and
                      source_bytes == len(source_body) & 0xffffffff}
        with budget.scoped((source_body, body), 'source/cache buffers: ' + str(file)):
            stream = io.BytesIO(body[16:])
            cached = marshal.load(stream)
            need(stream.read(1) == b'' and isinstance(cached, types.CodeType), 'Incomplete or non-code source-backed cache')
            physical = str(source)
            need(cached.co_filename == physical, 'Cached filename differs from actual source')
            current = compile(source_body, physical, 'exec', dont_inherit=True, optimize=optimization)
            with budget.scoped((cached, current, stream), 'decoded/fresh code: ' + str(file)):
                budget.admit(0, 'canonical cached code: ' + str(file))
                observed = canonical_code(cached, physical, source_logical)
                with budget.scoped(observed, 'retained cached canonical bytes: ' + str(file)):
                    budget.admit(0, 'canonical fresh code: ' + str(file))
                    expected = canonical_code(current, physical, source_logical)
                    budget.admit(sys.getsizeof(expected), 'canonical comparison: ' + str(file))
                    need(observed == expected, 'Cached executable code differs from fresh source compilation')
        del cached, current, stream, observed
        effective = {'kind': 'verified-source-backed-pyc-v1', 'bytes': len(expected),
                     'sha256': digest(expected), 'mode': raw['mode'], 'source': source_logical,
                     'source_sha256': source_raw['sha256'], 'optimization': optimization}
        row.update(effective=effective, normalization={'physical_filename': physical,
                   'header_hex': body[:16].hex(), 'header': header})
        del expected, source_body, body
    budget.retain(row)
    return row


def effective_rows(inventory):
    return [{'distribution': row['distribution'], 'path': row['path'], **row['effective']} for row in inventory]


def explicit_site_paths():
    """Discover install roots without site, .pth, or sitecustomize execution."""
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
         'Runtime identity requires Python -I -S -B startup')
    executable = Path(sys.executable).absolute()
    environment = executable.parent.parent
    configuration = environment / 'pyvenv.cfg'
    prefixes = [Path(sys.prefix).absolute()]
    if configuration.is_file():
        _, configuration_bytes = read_file(configuration, Budget(), body=True)
        settings = {}
        for line in configuration_bytes.decode('utf-8').splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                settings[key.strip().lower()] = value.strip()
        include = settings.get('include-system-site-packages', 'false').lower()
        need(include in ('true', 'false'), 'Malformed virtual-environment site policy')
        prefixes = [environment]
        if include == 'true':
            prefixes.append(Path(sys.base_prefix).absolute())
    paths = []
    for prefix in prefixes:
        for kind in ('purelib', 'platlib'):
            path = Path(sysconfig.get_path(kind, vars={'base': str(prefix), 'platbase': str(prefix)})).absolute()
            if path.is_dir():
                need(path == path.resolve(strict=True), 'Installed site root has a linked ancestor')
                if str(path) not in paths:
                    paths.append(str(path))
    return paths


@contextmanager
def source_only_parser():
    """A private empty cache prefix proves normal parser caches cannot execute."""
    prefixes = ('packaging', 'pip')
    def relevant(name):
        return any(name == prefix or name.startswith(prefix + '.') for prefix in prefixes)
    need(not any(relevant(name) for name in sys.modules), 'Preloaded requirement parser cannot prove source-only execution')
    old_prefix, old_write, old_path = sys.pycache_prefix, sys.dont_write_bytecode, sys.path[:]
    sites = explicit_site_paths()
    with tempfile.TemporaryDirectory(prefix='worldatlas-parser-source-') as directory:
        prefix = Path(directory).resolve()
        need(prefix == Path(directory).absolute() and not any(prefix.iterdir()), 'Ordinary empty parser cache prefix required')
        sys.pycache_prefix, sys.dont_write_bytecode = str(prefix), True
        sys.path.extend(path for path in sites if path not in sys.path)
        try:
            yield prefix
            need(not any(prefix.rglob('*')), 'Source-only parser unexpectedly wrote bytecode')
        finally:
            for name in list(sys.modules):
                if relevant(name):
                    del sys.modules[name]
            sys.pycache_prefix, sys.dont_write_bytecode = old_prefix, old_write
            sys.path[:] = old_path


def parser_effective_rows(inventory):
    # Only the invocation's proven-unread source caches disappear from execution
    # identity. Their complete raw descriptors remain bound by raw_sha256.
    return effective_rows([row for row in inventory if row['effective']['kind'] != 'unread-source-cache-v1'])


def discover_parser():
    """PathFinder traverses package paths without executing ancestor packages."""
    direct = importlib.machinery.PathFinder.find_spec('packaging', sys.path)
    provider = 'packaging' if direct is not None else 'pip._vendor.packaging'
    search, ancestors, pieces = sys.path, [], provider.split('.')
    for index in range(1, len(pieces) + 1):
        name = '.'.join(pieces[:index])
        spec = importlib.machinery.PathFinder.find_spec(name, search)
        need(spec is not None and isinstance(spec.loader, importlib.machinery.SourceFileLoader) and
             spec.origin and spec.submodule_search_locations is not None and len(spec.submodule_search_locations) == 1,
             'Requirement parser needs an ordinary source package')
        source = Path(spec.origin).absolute()
        ordinary(source)
        need(source.name == '__init__.py', 'Requirement parser package initializer is not ordinary source')
        ancestors.append(source)
        search = list(spec.submodule_search_locations)
    base, members = ancestors[-1].parent, {}
    for file in sorted(base.rglob('*')):
        if file.is_dir() and not file.is_symlink():
            continue
        ordinary(file)
        members[file] = provider.replace('.', '/') + '/' + file.relative_to(base).as_posix()
    for index, file in enumerate(ancestors[:-1], 1):
        members[file] = '/'.join(pieces[:index]) + '/__init__.py'
        cached = file.parent / '__pycache__' / (file.stem + '.' + sys.implementation.cache_tag + '.pyc')
        if cached.is_file():
            members[cached] = '/'.join(pieces[:index]) + '/__pycache__/' + cached.name
    return provider, members


def parser_inventory(members, budget):
    inventory = []
    for file, logical in sorted(members.items(), key=lambda item: item[1]):
        raw, _ = read_file(file, budget)
        row = {'distribution': 'identity-parser', 'path': logical,
               'raw': raw, 'effective': dict(raw, kind='exact')}
        binding = cache_source(file, members) if file.parent.name == '__pycache__' else None
        if binding:
            source, _ = binding
            source_raw, _ = read_file(source, budget)
            row['effective'] = {'kind': 'unread-source-cache-v1', 'source': members[source], 'source_sha256': source_raw['sha256']}
        budget.retain(row)
        inventory.append(row)
    return inventory


def validate_expected_parser(expected):
    """Strict builtin-only validation before any installed parser may execute."""
    need(isinstance(expected, dict) and set(expected) == {'provider', 'version', 'files', 'sha256', 'raw_sha256', 'inventory'},
         'Complete authenticated expected parser roster required')
    need(expected['provider'] in ('packaging', 'pip._vendor.packaging') and
         isinstance(expected['version'], str) and expected['version'], 'Invalid expected parser implementation')
    rows = expected['inventory']
    need(isinstance(rows, list) and rows and type(expected['files']) is int and expected['files'] == len(rows),
         'Invalid expected parser inventory count')
    found = {}
    for row in rows:
        need(isinstance(row, dict) and set(row) == {'distribution', 'path', 'raw', 'effective'} and
             row['distribution'] == 'identity-parser', 'Invalid expected parser member')
        name = row['path']
        need(isinstance(name, str) and name and str(PurePosixPath(name)) == name and
             not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and
             '\\' not in name and not any(ord(char) < 32 for char in name) and name not in found,
             'Invalid or duplicate expected parser path')
        found[name] = row
        raw, effective = row['raw'], row['effective']
        need(isinstance(raw, dict) and set(raw) == {'bytes', 'sha256', 'mode'} and type(raw['bytes']) is int and raw['bytes'] >= 0 and
             isinstance(raw['sha256'], str) and re.fullmatch('[a-f0-9]{64}', raw['sha256']) and raw['mode'] in ('100644', '100755'),
             'Invalid expected parser raw descriptor')
        need(isinstance(effective, dict), 'Invalid expected parser effective descriptor')
        if effective.get('kind') == 'exact':
            need(effective == dict(raw, kind='exact'), 'Expected exact parser member was normalized')
        else:
            need(set(effective) == {'kind', 'source', 'source_sha256'} and effective['kind'] == 'unread-source-cache-v1' and
                 isinstance(effective['source'], str) and isinstance(effective['source_sha256'], str),
                 'Unknown expected parser normalization')
    need(list(found) == sorted(found), 'Expected parser inventory is not ordered')
    for row in rows:
        effective = row['effective']
        if effective['kind'] == 'exact':
            continue
        source = found.get(effective['source'])
        file = PurePosixPath(row['path'])
        match = re.fullmatch(r'(.+)\.' + re.escape(sys.implementation.cache_tag) + r'(?:\.opt-([012]))?\.pyc', file.name)
        need(source is not None and source['effective']['kind'] == 'exact' and source['raw']['sha256'] == effective['source_sha256'] and
             file.parent.name == '__pycache__' and match is not None and
             str(file.parent.parent / (match[1] + '.py')) == effective['source'], 'Expected unread parser cache binding differs')
    need(expected['sha256'] == digest(encoded(parser_effective_rows(rows))) and
         expected['raw_sha256'] == digest(encoded(raw_rows(rows))), 'Expected parser roster digest differs')


def require_expected_parser(provider, inventory, expected):
    # The caller supplies the authenticated original roster, not an identifier
    # printed by the currently installed executable parser implementation.
    need(expected['provider'] == provider, 'Expected parser provider differs')
    rows = expected['inventory']
    need(parser_effective_rows(inventory) == parser_effective_rows(rows),
         'Requirement parser differs from authenticated original before import')


def implementation_parser(budget, expected_parser=None):
    # Nothing from packaging or pip has executed when this roster is collected
    # and compared. A modified parser cannot forge stdout and exit before checks.
    if expected_parser is not None:
        validate_expected_parser(expected_parser)
    provider, members = discover_parser()
    with budget.scoped(members, 'parser member map'):
        inventory = parser_inventory(members, budget)
        if expected_parser is not None:
            require_expected_parser(provider, inventory, expected_parser)
        package = importlib.import_module(provider)
        requirements = importlib.import_module(provider + '.requirements')
        markers = importlib.import_module(provider + '.markers')
        utils = importlib.import_module(provider + '.utils')
        # SourceFileLoader consults only the private empty prefix, never installed
        # source caches. Verify every actually loaded parser source was inventoried.
        for name, module in list(sys.modules.items()):
            if name in ('packaging', 'pip') or name.startswith(('packaging.', 'pip.')):
                file = Path(module.__file__)
                ordinary(file)
                need(file.suffix == '.py' and isinstance(module.__loader__, importlib.machinery.SourceFileLoader) and
                     Path(module.__cached__).is_relative_to(Path(sys.pycache_prefix)), 'Requirement parser did not execute ordinary source')
                need(file in members, 'Executed requirement parser module is outside the hashed implementation')
        identity = {'provider': provider, 'version': getattr(package, '__version__', None),
                    'files': len(inventory), 'sha256': digest(encoded(parser_effective_rows(inventory))),
                    'raw_sha256': digest(encoded(raw_rows(inventory))), 'inventory': inventory}
        if expected_parser is not None:
            need(identity['version'] == expected_parser['version'], 'Expected parser implementation version differs')
        budget.retain(identity)
        return requirements.Requirement, markers.default_environment(), utils.canonicalize_name, identity


def require_import_ownership(names, root, members):
    """Bind declared physical modules to Python's ordered import resolution."""
    importlib.machinery.PathFinder.invalidate_caches()
    for name in sorted(names):
        loaded = sys.modules.get(name)
        if loaded is not None:
            filename = getattr(loaded, '__file__', None)
            locations = getattr(loaded, '__path__', ())
            need((filename is not None and Path(filename).absolute().is_relative_to(root)) or
                 (filename is None and locations and all(Path(item).absolute().is_relative_to(root) for item in locations)),
                 'Declared Python import is already loaded outside its distribution root: ' + name)
        need(importlib.machinery.BuiltinImporter.find_spec(name) is None and
             importlib.machinery.FrozenImporter.find_spec(name) is None,
             'Declared Python import is shadowed by interpreter modules: ' + name)
        spec = importlib.machinery.PathFinder.find_spec(name, sys.path)
        need(spec is not None, 'Declared Python import is absent from active import roots: ' + name)
        if spec.origin is not None:
            file = Path(spec.origin).absolute()
            need(file.is_relative_to(root) and file in members,
                 'Declared Python import resolves outside its inventoried distribution root: ' + name)
            ordinary(file)
        else:
            locations = spec.submodule_search_locations
            need(locations and all(Path(item).absolute().is_relative_to(root) and
                                   Path(item).absolute() == Path(item).resolve(strict=True) for item in locations),
                 'Declared Python namespace merges an unowned import root: ' + name)


def distribution_members(distribution, budget):
    root = Path(distribution.locate_file('')).absolute()
    need(root == root.resolve(strict=True) and root.is_dir(), 'Ordinary installed distribution root required')
    records = distribution.files
    need(records is not None and len(records) > 0, 'Complete installed distribution RECORD required')
    members, directories, imports = {}, set(), set()
    suffixes = sorted(importlib.machinery.EXTENSION_SUFFIXES + importlib.machinery.SOURCE_SUFFIXES +
                      importlib.machinery.BYTECODE_SUFFIXES, key=len, reverse=True)
    scripts = Path(sys.executable).absolute().parent
    for member in records:
        name = str(member)
        need(name and '\\' not in name and '\x00' not in name and not PurePosixPath(name).is_absolute(), 'Unsafe installed distribution member')
        file = Path(os.path.abspath(distribution.locate_file(member)))
        need(file.is_relative_to(root) or file.parent == scripts, 'Distribution RECORD escapes package/script installation')
        ordinary(file)
        need(file not in members, 'Duplicate installed distribution member')
        members[file] = name
        if file.is_relative_to(root):
            relative = file.relative_to(root)
            first = relative.parts[0]
            if first == '__pycache__':
                # A flat module's cache does not grant ownership over every
                # unrelated cache sharing this site-level directory.
                match = re.fullmatch(r'(.+)\.' + re.escape(sys.implementation.cache_tag) + r'(?:\.opt-[012])?\.pyc', file.name)
                if match and match[1].isidentifier():
                    imports.add(match[1])
            elif (root / first).is_dir():
                directories.add(root / first)
                if first.isidentifier():
                    imports.add(first)
            elif len(relative.parts) == 1:
                suffix = next((item for item in suffixes if first.endswith(item)), None)
                if suffix and first[:-len(suffix)].isidentifier():
                    imports.add(first[:-len(suffix)])
    # FileFinder can choose a package before a recorded flat module, an
    # extension before source, or a sourceless/cache sibling. Enumerate the
    # entire physical name family, including unknown companion bytes, rather
    # than trusting RECORD to describe future import resolution.
    for name in sorted(imports):
        candidates = [root / name, *root.glob(name + '.*'), *(root / '__pycache__').glob(name + '.*.pyc')]
        for file in candidates:
            if not file.exists() and not file.is_symlink():
                continue
            if file.is_dir() and not file.is_symlink():
                directories.add(file)
            else:
                ordinary(file)
                members.setdefault(file, file.relative_to(root).as_posix())
    for directory in sorted(directories):
        for file in sorted(directory.rglob('*')):
            if file.is_dir() and not file.is_symlink():
                continue
            ordinary(file)
            members.setdefault(file, file.relative_to(root).as_posix())
    require_import_ownership(imports, root, members)
    return members


def installed_identity(roots=None, *, distribution_finder=importlib.metadata.distribution, metadata_bytes=None, expected_parser=None):
    with source_only_parser():
        return _installed_identity(roots, distribution_finder=distribution_finder, metadata_bytes=metadata_bytes, expected_parser=expected_parser)


def _installed_identity(roots=None, *, distribution_finder=importlib.metadata.distribution, metadata_bytes=None, expected_parser=None):
    budget = Budget(metadata_bytes)
    with allocation_limit(budget):
        return _measure_identity(roots, distribution_finder, expected_parser, budget)


def _measure_identity(roots, distribution_finder, expected_parser, budget):
    if expected_parser is not None:
        budget.retain(expected_parser)
    Requirement, environment, normalize, parser = implementation_parser(budget, expected_parser)
    roots = list(DEFAULT_ROOTS) if roots is None else roots
    need(isinstance(roots, list) and roots, 'At least one declared Python root required')
    requirements = []
    for root in roots:
        if isinstance(root, str):
            requirement = root
        else:
            need(isinstance(root, dict) and isinstance(root.get('name'), str), 'Invalid declared Python root')
            extras = root.get('extras', [])
            need(isinstance(extras, list) and all(isinstance(extra, str) for extra in extras), 'Invalid declared root extras')
            requirement = root['name'] + ('[' + ','.join(extras) + ']' if extras else '')
            if 'version' in root:
                need(isinstance(root['version'], str), 'Invalid declared root version')
                requirement += '==' + root['version']
        requirements.append(Requirement(requirement))
    declared = sorted(set(str(item) for item in requirements))
    distributions, active, processed, pending = {}, {}, {}, []

    def include(requirement):
        name = normalize(requirement.name)
        need(not requirement.url, 'Installed direct-URL dependency needs an explicit immutable distribution contract')
        if name not in distributions:
            distribution = distribution_finder(name)
            need(normalize(distribution.metadata['Name']) == name, 'Installed distribution name differs')
            distributions[name] = distribution
        distribution = distributions[name]
        need(requirement.specifier.contains(distribution.version, prereleases=True), 'Installed dependency version does not satisfy declared requirement')
        extras = {normalize(extra) for extra in requirement.extras}
        provided = {normalize(extra) for extra in distribution.metadata.get_all('Provides-Extra', [])}
        need(extras <= provided, 'Requested installed dependency extra is not declared')
        updated = active.get(name, set()) | extras
        if name not in active or updated != active[name]:
            active[name] = updated
            pending.append(name)

    for requirement in requirements:
        if requirement.marker is None or requirement.marker.evaluate({**environment, 'extra': ''}):
            include(requirement)
    need(distributions, 'No declared Python roots apply to this interpreter')
    while pending:
        name = pending.pop()
        contexts = frozenset(active[name])
        if processed.get(name) == contexts:
            continue
        processed[name] = contexts
        for raw in distributions[name].requires or []:
            requirement = Requirement(raw)
            if requirement.marker is None or any(requirement.marker.evaluate({**environment, 'extra': extra})
                                                 for extra in ('', *sorted(contexts))):
                include(requirement)
    inventory, resolved = [], []
    for name, distribution in sorted(distributions.items()):
        members = distribution_members(distribution, budget)
        resolved.append({'name': name, 'version': distribution.version, 'extras': sorted(active[name])})
        with budget.scoped(members, 'distribution member map: ' + name):
            for file, logical in sorted(members.items(), key=lambda item: item[1]):
                inventory.append(file_identity(name, logical, file, members, budget))
        del members
    executable, _ = read_file(Path(sys.executable).resolve(), budget)
    interpreter = {'implementation': sys.implementation.name, 'version': sys.version, 'cache_tag': sys.implementation.cache_tag,
                   'optimization': sys.flags.optimize, 'magic_number': importlib.util.MAGIC_NUMBER.hex(), 'executable': executable}
    for value in (inventory, resolved, declared, interpreter):
        budget.retain(value)
    budget.admit(0, 'final effective/raw identity serialization')
    semantic = {'version': VERSION, 'interpreter': interpreter, 'roots': declared, 'distributions': resolved,
                'parser': {key: parser[key] for key in ('provider', 'version', 'sha256')}, 'inventory': effective_rows(inventory)}
    return {'version': VERSION, 'executable_sha256': executable['sha256'], 'interpreter': interpreter,
            'roots': declared, 'distributions': resolved, 'files': len(inventory), 'sha256': digest(encoded(semantic)),
            'raw_sha256': digest(encoded(raw_rows(inventory))),
            'inventory': inventory, 'parser': parser}



def raw_rows(inventory):
    return [{'distribution': row['distribution'], 'path': row['path'], **row['raw'],
             **({'normalization': row['normalization']} if 'normalization' in row else {})} for row in inventory]


def validate_identity(value):
    """Validate serialized evidence only; never read any embedded filesystem path."""
    def keys(item, expected):
        need(isinstance(item, dict) and set(item) == set(expected), 'Malformed Python identity fields')

    def sha(item):
        return isinstance(item, str) and re.fullmatch('[a-f0-9]{64}', item) is not None

    def logical(item):
        if not isinstance(item, str) or item in ('', '.', '..') or '\\' in item or any(ord(char) < 32 for char in item):
            return False
        pure = PurePosixPath(item)
        return not pure.is_absolute() and str(pure) == item and not any(part == '..' for part in pure.parts[len(tuple(p for p in pure.parts if p == '..')):])

    def descriptor(item):
        keys(item, ('bytes', 'sha256', 'mode'))
        need(type(item['bytes']) is int and item['bytes'] >= 0 and sha(item['sha256']) and
             item['mode'] in ('100644', '100755'), 'Invalid Python file descriptor')

    def sorted_unique(items):
        return isinstance(items, list) and all(isinstance(item, str) and item for item in items) and items == sorted(set(items))

    keys(value, ('version', 'executable_sha256', 'interpreter', 'roots', 'distributions', 'files', 'sha256', 'raw_sha256', 'inventory', 'parser'))
    need(value['version'] == VERSION and type(value['version']) is int, 'Unsupported Python identity version')
    interpreter = value['interpreter']
    keys(interpreter, ('implementation', 'version', 'cache_tag', 'optimization', 'magic_number', 'executable'))
    descriptor(interpreter['executable'])
    need(all(isinstance(interpreter[key], str) and interpreter[key] for key in ('implementation', 'version', 'cache_tag')) and
         type(interpreter['optimization']) is int and interpreter['optimization'] in (0, 1, 2) and
         isinstance(interpreter['magic_number'], str) and re.fullmatch('[a-f0-9]{8}', interpreter['magic_number']) and
         value['executable_sha256'] == interpreter['executable']['sha256'], 'Python executable identity differs')
    need(sorted_unique(value['roots']) and value['roots'], 'Declared Python roots missing or ambiguous')
    distributions = value['distributions']
    need(isinstance(distributions, list) and distributions, 'Python distribution closure missing')
    names = []
    for distribution in distributions:
        keys(distribution, ('name', 'version', 'extras'))
        name = distribution['name']
        need(isinstance(name, str) and re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', name) and
             isinstance(distribution['version'], str) and distribution['version'] and sorted_unique(distribution['extras']),
             'Invalid Python distribution closure')
        names.append(name)
    need(names == sorted(set(names)), 'Duplicate or unordered Python distributions')

    def inventory(rows, allowed, parser=False):
        need(isinstance(rows, list) and rows, 'Complete Python file inventory missing')
        found = {}
        for row in rows:
            keys(row, ('distribution', 'path', 'raw', 'effective', *(['normalization'] if 'normalization' in row else [])))
            need(row['distribution'] in allowed and logical(row['path']), 'Invalid Python inventory member')
            key = (row['distribution'], row['path'])
            need(key not in found, 'Duplicate Python inventory member')
            found[key] = row
            descriptor(row['raw'])
            effective = row['effective']
            need(isinstance(effective, dict), 'Missing Python effective descriptor')
            if effective.get('kind') == 'exact':
                keys(effective, ('kind', 'bytes', 'sha256', 'mode'))
                need(effective == dict(row['raw'], kind='exact') and 'normalization' not in row,
                     'Exact Python member was normalized')
            elif parser and effective.get('kind') == 'unread-source-cache-v1':
                keys(effective, ('kind', 'source', 'source_sha256'))
                need('normalization' not in row and logical(effective['source']) and effective['source'].endswith('.py') and
                     sha(effective['source_sha256']), 'Invalid unread parser cache binding')
            else:
                need(not parser and effective.get('kind') == 'verified-source-backed-pyc-v1', 'Unknown Python semantic normalization')
                keys(effective, ('kind', 'bytes', 'sha256', 'mode', 'source', 'source_sha256', 'optimization'))
                descriptor({key: effective[key] for key in ('bytes', 'sha256', 'mode')})
                need(effective['bytes'] > 0 and effective['mode'] == row['raw']['mode'] and logical(effective['source']) and
                     effective['source'].endswith('.py') and sha(effective['source_sha256']) and
                     type(effective['optimization']) is int and effective['optimization'] in (0, 1, 2), 'Invalid verified cache descriptor')
                keys(row.get('normalization'), ('physical_filename', 'header_hex', 'header'))
                normalization = row['normalization']
                need(isinstance(normalization['physical_filename'], str) and PurePosixPath(normalization['physical_filename']).is_absolute() and
                     normalization['physical_filename'].endswith('/' + effective['source']) and
                     isinstance(normalization['header_hex'], str) and re.fullmatch('[a-f0-9]{32}', normalization['header_hex']),
                     'Invalid cache provenance')
                header = bytes.fromhex(normalization['header_hex'])
                flags = int.from_bytes(header[4:8], 'little')
                need(header[:4].hex() == interpreter['magic_number'] and flags in (0, 1, 3), 'Malformed normalized cache header')
                details = normalization['header']
                if flags & 1:
                    keys(details, ('kind', 'source_hash', 'matches_source'))
                    need(details['kind'] == ('checked-hash' if flags & 2 else 'unchecked-hash') and details['source_hash'] == header[8:16].hex(),
                         'Cache hash header evidence differs')
                else:
                    keys(details, ('kind', 'timestamp', 'source_bytes', 'matches_source'))
                    need(details['kind'] == 'timestamp' and type(details['timestamp']) is int and type(details['source_bytes']) is int and
                         (details['timestamp'], details['source_bytes']) == struct.unpack('<II', header[8:16]), 'Cache timestamp evidence differs')
                need(type(details['matches_source']) is bool, 'Missing cache invalidation observation')
        need(list(found) == sorted(found), 'Python inventory is not canonically ordered')
        need(set(row['distribution'] for row in rows) == set(allowed), 'Python distribution inventory is incomplete')
        for row in rows:
            effective = row['effective']
            if effective['kind'] == 'exact':
                continue
            source = found.get((row['distribution'], effective['source']))
            need(source is not None and source['effective']['kind'] == 'exact' and source['raw']['sha256'] == effective['source_sha256'],
                 'Cache source descriptor binding differs')
            file = PurePosixPath(row['path'])
            if effective['kind'] == 'unread-source-cache-v1':
                match = re.fullmatch(r'(.+)\.' + re.escape(interpreter['cache_tag']) + r'(?:\.opt-([012]))?\.pyc', file.name)
                need(file.parent.name == '__pycache__' and match is not None and
                     str(file.parent.parent / (match[1] + '.py')) == effective['source'], 'Unread parser cache path differs')
                continue
            if file.parent.name == '__pycache__':
                match = re.fullmatch(r'(.+)\.' + re.escape(interpreter['cache_tag']) + r'(?:\.opt-([012]))?\.pyc', file.name)
                need(match is not None and str(file.parent.parent / (match[1] + '.py')) == effective['source'] and
                     int(match[2] or 0) == effective['optimization'], 'Cache path/optimization binding differs')
            else:
                need(file.suffix == '.pyc' and str(file.with_suffix('.py')) == effective['source'] and
                     effective['optimization'] == interpreter['optimization'], 'Legacy cache source binding differs')
        return rows

    parser = value['parser']
    keys(parser, ('provider', 'version', 'files', 'sha256', 'raw_sha256', 'inventory'))
    need(parser['provider'] in ('packaging', 'pip._vendor.packaging') and isinstance(parser['version'], str) and parser['version'],
         'Unidentified Python requirement parser')
    parser_rows = inventory(parser['inventory'], ['identity-parser'], parser=True)
    need(type(parser['files']) is int and parser['files'] == len(parser_rows) and parser['sha256'] == digest(encoded(parser_effective_rows(parser_rows))) and
         parser['raw_sha256'] == digest(encoded(raw_rows(parser_rows))),
         'Python parser implementation digest differs')
    rows = inventory(value['inventory'], names)
    need(type(value['files']) is int and value['files'] == len(rows) and sha(value['sha256']) and sha(value['raw_sha256']),
         'Python inventory count or summary missing')
    semantic = {'version': VERSION, 'interpreter': interpreter, 'roots': value['roots'], 'distributions': distributions,
                'parser': {key: parser[key] for key in ('provider', 'version', 'sha256')}, 'inventory': effective_rows(rows)}
    need(value['sha256'] == digest(encoded(semantic)) and value['raw_sha256'] == digest(encoded(raw_rows(rows))),
         'Python inventory raw/effective summary differs')
    return {'valid': True}


def probe_imports(rows):
    """Execute only after caller admission, with no site-startup hooks."""
    need(isinstance(rows, list), 'Python import probe needs declared rows')
    for row in rows:
        need(isinstance(row, dict) and set(row) == {'name', 'version'} and
             isinstance(row['name'], str) and re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', row['name']) and
             isinstance(row['version'], str) and row['version'], 'Malformed Python import probe row')
    imports = []
    # The same fresh cache prefix also keeps measuring-parser caches unread if
    # an admitted scientific module happens to import that parser itself.
    with source_only_parser():
        for row in rows:
            try:
                module = importlib.import_module(row['name'])
                imports.append({**row, 'actual': module.__version__})
            except Exception as error:
                imports.append({**row, 'error': str(error)})
    return {'version': sys.version.split()[0], 'executable': sys.executable, 'imports': imports}


def append_authored_script_path(parent):
    """Local helpers cannot replace or extend any admitted import root."""
    parent = Path(parent)
    need(parent.absolute() == parent.resolve(strict=True) and parent.is_dir(),
         'Ordinary authored script directory required')
    names = set()
    suffixes = sorted(importlib.machinery.all_suffixes(), key=len, reverse=True)
    for item in parent.iterdir():
        name = item.name if item.is_dir() else next((item.name[:-len(suffix)] for suffix in suffixes
                                                   if item.name.endswith(suffix)), '')
        if name.isidentifier():
            names.add(name)
    def identity(spec):
        return None if spec is None else (spec.origin, tuple(spec.submodule_search_locations or ()))
    before = sys.path[:]
    for name in sorted(names):
        original = importlib.machinery.PathFinder.find_spec(name, before)
        if original is not None:
            need(identity(original) == identity(importlib.machinery.PathFinder.find_spec(name, [*before, str(parent)])),
                 'Authored script directory changes admitted import resolution: ' + name)
    if str(parent) not in sys.path:
        sys.path.append(str(parent))


def execute_package_source(mode, arguments):
    """The same no-hook/source-cache policy governs real work and probes."""
    need(mode in ('--run-script', '--run-code') and arguments,
         'Explicit package Python source required')
    import runpy
    old_argv = sys.argv[:]
    with source_only_parser():
        try:
            if mode == '--run-script':
                script = Path(arguments[0]).absolute()
                ordinary(script)
                # Installed/runtime roots win over local names. The explicit
                # script directory supplies authored sibling helpers only.
                append_authored_script_path(script.parent)
                sys.argv = [str(script), *arguments[1:]]
                runpy.run_path(str(script), run_name='__main__')
            else:
                sys.argv = ['-c', *arguments[1:]]
                exec(compile(arguments[0], '<string>', 'exec'),
                     {'__name__': '__main__', '__package__': None, '__builtins__': __builtins__})
        finally:
            sys.argv = old_argv


def read_json_input(budget):
    chunks, size = [], 0
    while chunk := sys.stdin.buffer.read(CHUNK):
        size += len(chunk)
        budget.admit(2 * size + CHUNK, 'read/join JSON input')
        chunks.append(chunk)
    raw = b''.join(chunks)
    del chunks
    budget.admit(len(raw), 'decode JSON input bytes/text')
    text = raw.decode('utf-8')
    budget.admit(sys.getsizeof(raw) + sys.getsizeof(text), 'parse JSON input bytes/text')
    return json.loads(text)


def write_json(value, budget):
    budget.admit(0, 'serialize JSON output')
    for fragment in json.JSONEncoder(ensure_ascii=True, separators=(',', ':')).iterencode(value):
        sys.stdout.write(fragment)
    sys.stdout.write('\n')


def main():
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'Runtime identity requires Python -I -S -B startup')
    if len(sys.argv) >= 3 and sys.argv[1] == '--run-cli':
        arguments=sys.argv[2:]
        need(arguments[0] == '-c' and len(arguments)>1 or not arguments[0].startswith('-'), 'Unsupported current Python child invocation')
        execute_package_source('--run-code' if arguments[0]=='-c' else '--run-script',arguments[1:] if arguments[0]=='-c' else arguments)
        return
    if len(sys.argv) >= 3 and sys.argv[1] in ('--run-script', '--run-code'):
        execute_package_source(sys.argv[1], sys.argv[2:])
        return
    if len(sys.argv) == 3 and sys.argv[1] == '--probe-imports':
        print(json.dumps(probe_imports(json.loads(sys.argv[2])), separators=(',', ':')))
        return
    if sys.argv[1:] == ['--validate']:
        budget = Budget()
        with allocation_limit(budget):
            value = read_json_input(budget)
            budget.retain(value)
            budget.admit(0, 'validate serialized identity')
            result = validate_identity(value)
            write_json(result, budget)
        return
    arguments = sys.argv[1:]
    has_expected_parser = '--expected-parser' in arguments
    if has_expected_parser:
        arguments.remove('--expected-parser')
    need(len(arguments) <= 1, 'Use package-python-runtime.py [JSON_ROOTS] [--expected-parser] or --validate')
    budget = Budget()
    with allocation_limit(budget), source_only_parser():
        expected_parser = read_json_input(budget) if has_expected_parser else None
        if has_expected_parser:
            need(isinstance(expected_parser, dict), 'Authenticated expected parser object required')
        roots = json.loads(arguments[0]) if arguments else None
        result = _measure_identity(roots, importlib.metadata.distribution, expected_parser, budget)
        budget.retain(result)
        budget.admit(0, 'validate completed identity')
        validate_identity(result)
        write_json(result, budget)



if __name__ == '__main__':
    main()
