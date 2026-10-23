"""Isolated execution of actual package Python work, without startup hooks."""
from contextlib import contextmanager
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import sysconfig
import tempfile

CHUNK = 1024 * 1024


def need(ok, message):
    if not ok:
        raise ValueError(message)


def ordinary(path):
    path = Path(path)
    need(path.absolute() == path.resolve(strict=True), 'Installed Python member has a linked ancestor')
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode), 'Installed Python member is not an ordinary file')
    return info


def read_configuration(path):
    path = Path(path)
    before = ordinary(path)
    chunks, size = [], 0
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        while chunk := stream.read(CHUNK):
            size += len(chunk)
            need(size <= before.st_size, 'Python configuration grew while reading')
            chunks.append(chunk)
        held = os.fstat(stream.fileno())
    after = ordinary(path)
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_mtime_ns', 'st_ctime_ns')
    need(size == before.st_size and all(getattr(before, key) == getattr(held, key) == getattr(after, key)
                                       for key in fields), 'Python configuration changed while reading')
    return b''.join(chunks).decode('utf-8')


def explicit_site_paths():
    """Discover install roots without site, .pth, or sitecustomize execution."""
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
         'Package execution requires Python -I -S -B startup')
    executable = Path(sys.executable).absolute()
    environment = executable.parent.parent
    configuration = environment / 'pyvenv.cfg'
    prefixes = [Path(sys.prefix).absolute()]
    if configuration.is_file():
        settings = {}
        for line in read_configuration(configuration).splitlines():
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
def isolated_imports():
    """Use installed sources without site hooks or existing bytecode caches."""
    old_prefix, old_write, old_path = sys.pycache_prefix, sys.dont_write_bytecode, sys.path[:]
    sites = explicit_site_paths()
    with tempfile.TemporaryDirectory(prefix='worldatlas-python-source-') as directory:
        prefix = Path(directory).resolve()
        need(prefix == Path(directory).absolute() and not any(prefix.iterdir()), 'Ordinary empty Python cache prefix required')
        sys.pycache_prefix, sys.dont_write_bytecode = str(prefix), True
        sys.path.extend(path for path in sites if path not in sys.path)
        try:
            yield prefix
            need(not any(prefix.rglob('*')), 'Source-only execution unexpectedly wrote bytecode')
        finally:
            sys.pycache_prefix, sys.dont_write_bytecode = old_prefix, old_write
            sys.path[:] = old_path


def probe_imports(rows):
    """Execute only after caller admission, with no site-startup hooks."""
    need(isinstance(rows, list), 'Python import probe needs declared rows')
    for row in rows:
        need(isinstance(row, dict) and set(row) == {'name', 'version'} and
             isinstance(row['name'], str) and re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', row['name']) and
             isinstance(row['version'], str) and row['version'], 'Malformed Python import probe row')
    imports = []
    with isolated_imports():
        for row in rows:
            try:
                module = importlib.import_module(row['name'])
                imports.append({**row, 'actual': module.__version__})
            except Exception as error:
                imports.append({**row, 'error': str(error)})
    return {'version': sys.version.split()[0], 'executable': sys.executable, 'imports': imports}


def namespace_portion_has_code(directory):
    """Data/cache-only namespace portions add no executable import candidates."""
    pending, seen = [Path(directory)], set()
    suffixes = sorted(importlib.machinery.all_suffixes(), key=len, reverse=True)
    while pending:
        directory = pending.pop()
        physical = directory.resolve(strict=True)
        if physical in seen:
            continue
        seen.add(physical)
        for item in directory.iterdir():
            name = item.name if item.is_dir() else next((item.name[:-len(suffix)] for suffix in suffixes
                                                       if item.name.endswith(suffix)), '')
            # Dynamic imports allow nonidentifiers; dots still delimit segments.
            if not name or '.' in name:
                continue
            spec = importlib.machinery.PathFinder.find_spec(name, [str(directory)])
            if spec is None:
                continue
            if spec.loader is not None or spec.origin is not None:
                return True
            pending.extend(Path(location) for location in spec.submodule_search_locations or ())
    return False


def append_authored_script_path(parent):
    """Local helpers cannot replace or extend admitted executable imports."""
    parent = Path(parent)
    need(parent.absolute() == parent.resolve(strict=True) and parent.is_dir(),
         'Ordinary authored script directory required')
    names = set()
    suffixes = sorted(importlib.machinery.all_suffixes(), key=len, reverse=True)
    for item in parent.iterdir():
        name = item.name if item.is_dir() else next((item.name[:-len(suffix)] for suffix in suffixes
                                                   if item.name.endswith(suffix)), '')
        if name and '.' not in name:
            names.add(name)
    def identity(spec):
        return None if spec is None else (spec.origin, tuple(spec.submodule_search_locations or ()))
    before = sys.path[:]
    for name in sorted(names):
        original = importlib.machinery.PathFinder.find_spec(name, before)
        if original is not None:
            updated = importlib.machinery.PathFinder.find_spec(name, [*before, str(parent)])
            unchanged = identity(original) == identity(updated)
            if not unchanged and updated is not None and original.loader is None and updated.loader is None:
                old_parts = tuple(original.submodule_search_locations or ())
                new_parts = tuple(updated.submodule_search_locations or ())
                # Namespace search paths are observable, but adding an empty or
                # data-only portion cannot supply executable Python code. Tagged
                # cache filenames are handled by the actual importer, not a
                # special-case directory-name exemption.
                unchanged = (new_parts[:len(old_parts)] == old_parts and
                             not any(namespace_portion_has_code(part) for part in new_parts[len(old_parts):]))
            need(unchanged, 'Authored script directory changes admitted import resolution: ' + name)
    if str(parent) not in sys.path:
        sys.path.append(str(parent))


def execute_package_source(mode, arguments):
    """The same no-hook/source-cache policy governs real work and probes."""
    need(mode in ('--run-script', '--run-code') and arguments,
         'Explicit package Python source required')
    import runpy
    old_argv = sys.argv[:]
    with isolated_imports():
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


def main():
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'Package execution requires Python -I -S -B startup')
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
    raise ValueError('Use --run-cli, --run-script, --run-code or --probe-imports')


if __name__ == '__main__':
    main()
