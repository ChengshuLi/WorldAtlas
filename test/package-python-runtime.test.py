"""Focused controls against real temporary installed-distribution metadata."""
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import marshal
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'scripts/package-python-runtime.py'
spec = importlib.util.spec_from_file_location('package_python_runtime', HELPER)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class Installation:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True)
        self.distributions = {}
        self.lookups = []

    def add(self, name, *, version='1.0', source='def answer(x):\n    return x + 1\n',
            requirements=(), extras=(), cache=True, optimization=0, flags=0, stamp=1, flat=False):
        package = self.root / name.replace('-', '_')
        if not flat:
            package.mkdir()
        source_file = package.with_suffix('.py') if flat else package / '__init__.py'
        source_file.write_bytes(source.encode())
        files = [source_file]
        if cache:
            file = Path(importlib.util.cache_from_source(str(source_file), optimization=str(optimization) if optimization else ''))
            file.parent.mkdir()
            code = compile(source.encode(), str(source_file), 'exec', dont_inherit=True, optimize=optimization)
            header = importlib.util.MAGIC_NUMBER + struct.pack('<I', flags)
            header += (bytes([stamp]) * 8 if flags & 1 else struct.pack('<II', stamp, len(source)))
            file.write_bytes(header + marshal.dumps(code))
            files.append(file)
        metadata = self.root / (name.replace('-', '_') + '-' + version + '.dist-info')
        metadata.mkdir()
        lines = ['Metadata-Version: 2.3', 'Name: ' + name, 'Version: ' + version]
        lines += ['Requires-Dist: ' + item for item in requirements]
        lines += ['Provides-Extra: ' + item for item in extras]
        (metadata / 'METADATA').write_text('\n'.join(lines) + '\n')
        files += [metadata / 'METADATA', metadata / 'RECORD']
        # Empty RECORD digests are valid installer metadata; the helper hashes
        # every actual member independently and includes unrecorded additions.
        (metadata / 'RECORD').write_text(''.join(file.relative_to(self.root).as_posix() + ',,\n' for file in files))
        self.distributions[name] = importlib.metadata.PathDistribution(metadata)
        return source_file, next((file for file in files if file.suffix == '.pyc'), None)

    def finder(self, name):
        self.lookups.append(name)
        if name not in self.distributions:
            raise importlib.metadata.PackageNotFoundError(name)
        return self.distributions[name]

    def identity(self, roots=None, **kwargs):
        original = sys.path[:]
        sys.path.insert(0, str(self.root))
        try:
            return runtime.installed_identity(roots or ['example'], distribution_finder=self.finder, **kwargs)
        finally:
            sys.path[:] = original


class PythonRuntimeIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='atlas-python-identity-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def installation(self, name='one'):
        return Installation(self.base / name)

    def test_fresh_relocated_source_cache_has_equal_effective_identity_and_distinct_raw_evidence(self):
        a, b = self.installation('short'), self.installation('longer-new-installation')
        a.add('example', stamp=1)
        b.add('example', stamp=2)
        first, second = a.identity(), b.identity()
        self.assertEqual(first['version'], 2)
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertNotEqual(first['raw_sha256'], second['raw_sha256'])
        cache_a = next(row for row in first['inventory'] if row['path'].endswith('.pyc'))
        cache_b = next(row for row in second['inventory'] if row['path'].endswith('.pyc'))
        self.assertEqual(cache_a['effective'], cache_b['effective'])
        self.assertNotEqual(cache_a['normalization']['physical_filename'], cache_b['normalization']['physical_filename'])
        self.assertNotEqual(cache_a['normalization']['header_hex'], cache_b['normalization']['header_hex'])
        self.assertTrue(first['parser']['inventory'])
        self.assertEqual(first['executable_sha256'], first['interpreter']['executable']['sha256'])

    def test_root_versions_are_required_before_scientific_inventory(self):
        install = self.installation(); source, _ = install.add('example', version='1.2')
        source.unlink()  # Wrong version must be rejected before this missing member.
        with self.assertRaisesRegex(ValueError, 'version does not satisfy'):
            install.identity([{'name': 'example', 'version': '1.3'}])

    def test_unchanged_version_does_not_hide_modified_source_native_or_unknown_bytes(self):
        install = self.installation(); source, cache = install.add('example')
        native = source.parent / 'native.so'; native.write_bytes(b'\x7fELFactual-native-code')
        data = source.parent / 'runtime.dat'; data.write_bytes(b'original')
        original = install.identity()
        # Source comments are still byte-exact even when executable cache agrees.
        source.write_bytes(source.read_bytes() + b'# actual source edit\n')
        changed = install.identity(); self.assertNotEqual(original['sha256'], changed['sha256'])
        source.write_bytes(source.read_bytes().replace(b'# actual source edit\n', b''))
        for file in (native, data):
            previous = file.read_bytes(); file.write_bytes(previous[:-1] + b'X')
            self.assertNotEqual(original['sha256'], install.identity()['sha256'])
            file.write_bytes(previous)
        self.assertEqual(original['sha256'], install.identity()['sha256'])

    def test_stale_executable_cache_is_rejected_even_when_header_would_make_python_recompile(self):
        install = self.installation(); source, _ = install.add('example', stamp=0)
        source.write_text('def answer(x):\n    return x + 2\n')
        with self.assertRaisesRegex(ValueError, 'Cached executable code differs'):
            install.identity()

    def test_edited_executable_bytecode_nested_filename_and_line_table_are_rejected(self):
        install = self.installation(); _, cache = install.add('example')
        raw = cache.read_bytes(); code = marshal.loads(raw[16:])
        nested = next(value for value in code.co_consts if isinstance(value, type(code)))
        changed = [
            code.replace(co_consts=tuple(nested.replace(co_consts=(None, 2)) if value is nested else value for value in code.co_consts)),
            code.replace(co_consts=tuple(nested.replace(co_filename='/other/source.py') if value is nested else value for value in code.co_consts)),
            code.replace(co_linetable=b''), code.replace(co_filename='/different/install/example/__init__.py')]
        for candidate in changed:
            cache.write_bytes(raw[:16] + marshal.dumps(candidate))
            with self.assertRaises(ValueError): install.identity()
        cache.write_bytes(raw)
        install.identity()

    def test_valid_hash_and_timestamp_invalidation_headers_normalize_only_after_code_verification(self):
        hashes = []
        for index, flags in enumerate((0, 1, 3)):
            install = self.installation(str(index)); install.add('example', flags=flags, stamp=index + 1)
            hashes.append(install.identity()['sha256'])
        self.assertEqual(len(set(hashes)), 1)

    def test_malformed_magic_flags_truncation_and_trailing_marshal_data_are_rejected(self):
        install = self.installation(); _, cache = install.add('example')
        raw = cache.read_bytes()
        for corrupted in (b'xxxx' + raw[4:], raw[:4] + struct.pack('<I', 4) + raw[8:],
                          raw[:4] + struct.pack('<I', 2) + raw[8:], raw[:12], raw + b'extra'):
            cache.write_bytes(corrupted)
            with self.assertRaises((ValueError, EOFError)): install.identity()

    def test_cache_optimization_is_bound_and_wrong_optimization_cannot_normalize(self):
        install = self.installation(); source, cache = install.add('example', source='"doc"\nassert False\nanswer = 3\n', optimization=2)
        observed = install.identity()
        row = next(row for row in observed['inventory'] if row['path'].endswith('.pyc'))
        self.assertEqual(row['effective']['optimization'], 2)
        raw = cache.read_bytes()
        code = compile(source.read_bytes(), str(source), 'exec', dont_inherit=True, optimize=0)
        cache.write_bytes(raw[:16] + marshal.dumps(code))
        with self.assertRaisesRegex(ValueError, 'Cached executable code differs'): install.identity()

    def test_sourceless_bytecode_remains_exact(self):
        install = self.installation(); source, _ = install.add('example', cache=False)
        file = source.parent / 'standalone.pyc'
        first = importlib.util.MAGIC_NUMBER + b'\0' * 12 + marshal.dumps(compile('answer=1', '/original.py', 'exec'))
        file.write_bytes(first)
        original = install.identity()
        row = next(row for row in original['inventory'] if row['path'].endswith('standalone.pyc'))
        self.assertEqual(row['effective']['kind'], 'exact')
        self.assertEqual(row['raw']['sha256'], hashlib.sha256(first).hexdigest())
        file.write_bytes(first[:-1] + bytes([first[-1] ^ 1]))
        self.assertNotEqual(original['sha256'], install.identity()['sha256'])

    def test_markers_extras_versions_and_missing_applicable_dependencies(self):
        install = self.installation()
        install.add('example', requirements=('base>=1', 'missing; python_version < "1"',
            'docs; extra == "docs"', 'optional; extra == "other"'), extras=('docs', 'other'))
        install.add('base'); install.add('docs'); install.add('optional')
        first = install.identity()
        self.assertEqual([row['name'] for row in first['distributions']], ['base', 'example'])
        self.assertNotIn('missing', install.lookups); self.assertNotIn('docs', install.lookups)
        observed = install.identity(['example[docs]'])
        self.assertEqual([row['name'] for row in observed['distributions']], ['base', 'docs', 'example'])
        with self.assertRaisesRegex(ValueError, 'extra is not declared'): install.identity(['example[typo]'])
        with self.assertRaisesRegex(ValueError, 'version does not satisfy'): install.identity(['example>=2'])
        del install.distributions['base']
        with self.assertRaises(importlib.metadata.PackageNotFoundError): install.identity()

    def test_late_extras_propagate_through_cycles_to_fixed_point(self):
        install = self.installation()
        install.add('example', requirements=('middle[first]', 'later'))
        install.add('later', requirements=('middle[second]',))
        install.add('middle', requirements=('first; extra == "first"', 'second; extra == "second"', 'example'), extras=('first', 'second'))
        install.add('first'); install.add('second')
        observed = install.identity()
        self.assertEqual([row['name'] for row in observed['distributions']], ['example', 'first', 'later', 'middle', 'second'])
        self.assertEqual(next(row['extras'] for row in observed['distributions'] if row['name'] == 'middle'), ['first', 'second'])

    def test_unrecorded_injected_modules_are_included_and_links_are_rejected(self):
        install = self.installation(); source, _ = install.add('example')
        original = install.identity(); injected = source.parent / 'injected.py'; injected.write_text('danger=True\n')
        changed = install.identity()
        self.assertNotEqual(original['sha256'], changed['sha256'])
        self.assertTrue(any(row['path'] == 'example/injected.py' for row in changed['inventory']))
        injected.unlink(); injected.symlink_to(source)
        with self.assertRaisesRegex(ValueError, 'linked ancestor|ordinary file'): install.identity()

    def test_flat_module_package_shadow_changes_complete_identity(self):
        install = self.installation()
        install.add('example', flat=True, cache=False, source='__version__="1.0"\ndef answer(): return 1\n')
        original = install.identity()
        package = install.root / 'example'
        package.mkdir()
        (package / '__init__.py').write_text('__version__="1.0"\ndef answer(): return 2\n')
        changed = install.identity(expected_parser=original['parser'])
        self.assertNotEqual(original['sha256'], changed['sha256'])
        self.assertNotEqual(original['raw_sha256'], changed['raw_sha256'])
        self.assertEqual(runtime.validate_identity(changed), {'valid': True})
        self.assertTrue(any(row['path'] == 'example/__init__.py' for row in changed['inventory']))
        spec = importlib.machinery.PathFinder.find_spec('example', [str(install.root)])
        self.assertEqual(Path(spec.origin), package / '__init__.py')

    def test_flat_module_native_sourceless_unknown_and_cache_siblings_are_bound(self):
        install = self.installation(); source, _ = install.add('example', flat=True, cache=False)
        original = install.identity()
        native = source.with_name('example' + importlib.machinery.EXTENSION_SUFFIXES[0])
        native.write_bytes(b'Unexecuted native candidate')
        changed = install.identity()
        self.assertNotEqual(original['sha256'], changed['sha256'])
        self.assertEqual(next(row['effective']['kind'] for row in changed['inventory'] if row['path'] == native.name), 'exact')
        native.unlink()
        unknown = source.with_suffix('.data'); unknown.write_bytes(b'unknown exact companion')
        self.assertNotEqual(original['sha256'], install.identity()['sha256'])
        unknown.unlink()
        cache = source.parent / '__pycache__' / ('example.' + sys.implementation.cache_tag + '.pyc')
        cache.parent.mkdir()
        header = importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, 0, source.stat().st_size)
        cache.write_bytes(header + marshal.dumps(compile(source.read_bytes(), str(source), 'exec', dont_inherit=True)))
        observed = install.identity()
        self.assertTrue(any(row['path'] == '__pycache__/' + cache.name for row in observed['inventory']))
        cache.write_bytes(header + marshal.dumps(compile('changed=True', str(source), 'exec', dont_inherit=True)))
        with self.assertRaisesRegex(ValueError, 'Cached executable code differs'):
            install.identity()
        cache.unlink()
        legacy = source.with_suffix('.pyc')
        legacy.write_bytes(header + marshal.dumps(compile(source.read_bytes(), str(source), 'exec', dont_inherit=True)))
        self.assertNotEqual(original['sha256'], install.identity()['sha256'])

    def test_sourceless_recorded_module_package_shadow_is_inventoried(self):
        install = self.installation(); source, _ = install.add('example', flat=True, cache=False)
        bytecode = source.with_suffix('.pyc')
        bytecode.write_bytes(importlib.util.MAGIC_NUMBER + b'\0' * 12 + marshal.dumps(compile(source.read_bytes(), '/original/example.py', 'exec')))
        source.unlink()
        record = install.root / 'example-1.0.dist-info/RECORD'
        record.write_text(record.read_text().replace('example.py,,', 'example.pyc,,'))
        original = install.identity()
        package = install.root / 'example'; package.mkdir()
        (package / '__init__.py').write_text('changed=True\n')
        changed = install.identity()
        self.assertNotEqual(original['sha256'], changed['sha256'])
        row = next(row for row in changed['inventory'] if row['path'] == 'example.pyc')
        self.assertEqual(row['effective']['kind'], 'exact')

    def test_ordered_roots_reject_shadowing_but_ignore_unreachable_later_module(self):
        install = self.installation(); install.add('example', flat=True, cache=False)
        original = install.identity()
        other = self.base / 'other-site'; other.mkdir()
        (other / 'example.py').write_text('changed=True\n')
        old_path = sys.path[:]
        try:
            sys.path[:] = [str(other), str(install.root), *old_path]
            with self.assertRaisesRegex(ValueError, 'outside its inventoried distribution root'):
                runtime.installed_identity(['example'], distribution_finder=install.finder)
            sys.path[:] = [str(install.root), str(other), *old_path]
            self.assertEqual(runtime.installed_identity(['example'], distribution_finder=install.finder)['sha256'], original['sha256'])
        finally:
            sys.path[:] = old_path

    def test_unowned_namespace_portions_are_rejected_even_in_later_roots(self):
        install = self.installation(); source, _ = install.add('example', cache=False)
        member = source.with_name('member.py'); source.rename(member)
        record = install.root / 'example-1.0.dist-info/RECORD'
        record.write_text(record.read_text().replace('example/__init__.py,,', 'example/member.py,,'))
        install.identity()
        other = self.base / 'other-site'; (other / 'example').mkdir(parents=True)
        (other / 'example/second.py').write_text('changed=True\n')
        old_path = sys.path[:]
        try:
            sys.path[:] = [str(install.root), str(other), *old_path]
            with self.assertRaisesRegex(ValueError, 'namespace merges an unowned import root'):
                runtime.installed_identity(['example'], distribution_finder=install.finder)
        finally:
            sys.path[:] = old_path

    def test_metadata_memory_admission_is_resource_based_and_fails_closed(self):
        install = self.installation(); install.add('example')
        with self.assertRaisesRegex(ValueError, 'memory admission'): install.identity(metadata_bytes=1)
        with self.assertRaises(ValueError): runtime.installed_identity([], distribution_finder=install.finder)

    def test_full_serialized_inventory_validation_and_cli_do_not_read_embedded_paths(self):
        install = self.installation(); install.add('example')
        observed = install.identity()
        self.assertEqual(runtime.validate_identity(observed), {'valid': True})
        raw = json.dumps(observed).encode()
        # All referenced source paths are now absent; pure evidence validation
        # must still work without inspecting any embedded path.
        import shutil
        shutil.rmtree(install.root)
        self.assertEqual(runtime.validate_identity(observed), {'valid': True})
        output = subprocess.check_output([sys.executable, '-I', '-S', '-B', str(HELPER), '--validate'], input=raw)
        self.assertEqual(json.loads(output), {'valid': True})

    def test_aggregate_only_and_modified_or_ambiguous_serialized_inventory_fail(self):
        install = self.installation(); install.add('example'); original = install.identity()
        with self.assertRaises(ValueError):
            runtime.validate_identity({'version': 2, 'files': original['files'], 'sha256': original['sha256']})
        def change_hash(value): value['inventory'][0]['effective']['sha256'] = 'f' * 64
        def duplicate(value): value['inventory'].append(copy.deepcopy(value['inventory'][0]))
        def change_parser(value): value['parser']['inventory'][0]['raw']['sha256'] = 'f' * 64
        def change_unread_parser_cache(value):
            next(row for row in value['parser']['inventory'] if row['effective']['kind'] == 'unread-source-cache-v1')['raw']['bytes'] += 1
        def change_verified_cache_raw(value):
            next(row for row in value['inventory'] if 'normalization' in row)['raw']['bytes'] += 1
        def change_count(value): value['files'] += 1
        def change_source(value):
            next(row for row in value['inventory'] if 'normalization' in row)['effective']['source_sha256'] = 'e' * 64
        def change_header(value):
            next(row for row in value['inventory'] if 'normalization' in row)['normalization']['header_hex'] = '0' * 32
        def change_raw(value): value['inventory'][0]['raw']['bytes'] += 1
        def change_roots(value): value['roots'].append('other')
        def change_binary(value): value['executable_sha256'] = 'd' * 64
        mutations = [change_hash, duplicate, change_parser, change_verified_cache_raw, change_count, change_source, change_header, change_raw, change_roots, change_binary]
        if any(row['effective']['kind'] == 'unread-source-cache-v1' for row in original['parser']['inventory']):
            mutations.append(change_unread_parser_cache)
        for mutate in mutations:
            altered = copy.deepcopy(original); mutate(altered)
            with self.assertRaises(ValueError): runtime.validate_identity(altered)

    def test_source_only_parser_relocation_and_changed_execution_source(self):
        import shutil
        with runtime.source_only_parser():
            parser = runtime.implementation_parser(runtime.Budget())[3]
            package = sys.modules[parser['provider']]
            original_source = Path(package.__file__).parent
        roots = []
        for index in range(2):
            root = Path(self.temporary.name) / ('parser-' + str(index))
            target = root / 'packaging'
            shutil.copytree(original_source, target, ignore=shutil.ignore_patterns('__pycache__'))
            for source in target.rglob('*.py'):
                cache = source.parent / '__pycache__' / (source.stem + '.' + sys.implementation.cache_tag + '.pyc')
                cache.parent.mkdir(exist_ok=True)
                code = compile(source.read_bytes(), str(source), 'exec', dont_inherit=True)
                cache.write_bytes(importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, index + 1, source.stat().st_size) + marshal.dumps(code))
            roots.append(root)
        script = """import importlib.util,json,sys
sys.path.insert(0,sys.argv[2])
spec=importlib.util.spec_from_file_location('runtime',sys.argv[1]);runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
with runtime.source_only_parser():
    expected=json.load(sys.stdin) if len(sys.argv)>3 else None
    parser=runtime.implementation_parser(runtime.Budget(), expected_parser=expected)[3]
print(json.dumps(parser))
"""
        def measure(root):
            return json.loads(subprocess.check_output([sys.executable, '-I', '-S', '-B', '-c', script, str(HELPER), str(root)]))
        left, right = [measure(root) for root in roots]
        self.assertEqual(left['sha256'], right['sha256'])
        self.assertNotEqual(left['raw_sha256'], right['raw_sha256'])
        self.assertTrue(any(row['effective']['kind'] == 'unread-source-cache-v1' for row in left['inventory']))
        # An independent installed root with a different physical cache path is
        # accepted against the original parser before executing its sources.
        admitted = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', script, str(HELPER), str(roots[1]), '--expected-parser'],
                                  input=json.dumps(left).encode(), capture_output=True)
        self.assertEqual(admitted.returncode, 0, admitted.stderr.decode())
        source = roots[1] / 'packaging' / '__init__.py'
        source.write_bytes(source.read_bytes() + b'\nparser_execution_changed = True\n')
        self.assertNotEqual(left['sha256'], measure(roots[1])['sha256'])
        # Source-only execution never grants a sourceless/unknown file exemption.
        standalone = roots[0] / 'packaging' / 'unknown.pyc'
        standalone.write_bytes(b'unknown executable bytes')
        unknown = measure(roots[0])
        self.assertEqual(next(row['effective']['kind'] for row in unknown['inventory'] if row['path'].endswith('unknown.pyc')), 'exact')
        self.assertNotEqual(left['sha256'], unknown['sha256'])
        standalone.unlink()
        sentinel = self.base / 'untrusted-parser-executed'
        malicious = ('import os\nfrom pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("executed")\n'
                     + 'os.write(1,b"forged original identity\\n")\nos._exit(0)\n')
        compile(malicious, '<malicious-parser-fixture>', 'exec')
        (roots[0] / 'packaging' / '__init__.py').write_text(malicious)
        rejected = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', script, str(HELPER), str(roots[0]), '--expected-parser'],
                                  input=json.dumps(left).encode(), capture_output=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(b'before import', rejected.stderr)
        self.assertEqual(rejected.stdout, b'')
        self.assertFalse(sentinel.exists(), 'Untrusted parser executed before authentication')

    def test_no_site_startup_blocks_pth_and_sitecustomize_in_real_venv(self):
        import shutil
        import venv
        environment = self.base / 'startup-environment'
        venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
        executable = environment / 'bin/python'
        import sysconfig
        site = Path(sysconfig.get_path('purelib', vars={'base': str(environment), 'platbase': str(environment)}))
        sentinel = self.base / 'startup-hook-executed'
        payload = 'import pathlib; pathlib.Path(' + repr(str(sentinel)) + ').write_text("executed")\n'
        (site / 'hostile.pth').write_text(payload)
        (site / 'sitecustomize.py').write_text(payload)
        with runtime.source_only_parser():
            provider, members = runtime.discover_parser()
            source = next(file.parent for file, logical in members.items() if logical == provider.replace('.', '/') + '/__init__.py')
        shutil.copytree(source, site / 'packaging', ignore=shutil.ignore_patterns('__pycache__'))
        # The test distribution shares the actual interpreter's site directory.
        installation = Installation.__new__(Installation)
        installation.root, installation.distributions, installation.lookups = site, {}, []
        installation.add('example', source="__version__ = '1.0'\n")
        process = subprocess.run([str(executable), '-I', '-S', '-B', str(HELPER), '[{"name":"example","version":"1.0"}]'], capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(json.loads(process.stdout)['distributions'], [{'name': 'example', 'version': '1.0', 'extras': []}])
        self.assertFalse(sentinel.exists(), 'Python startup hooks executed before the identity helper')
        # Probe mode needs no requirement parser and preserves the caller's
        # existing per-module actual/error contract.
        (site / 'packaging' / '__init__.py').write_text('raise AssertionError("Parser must not execute for probe")\n')
        probe = subprocess.run([str(executable), '-I', '-S', '-B', str(HELPER), '--probe-imports',
                                '[{"name":"example","version":"1.0"},{"name":"absent_module","version":"1"}]'], capture_output=True)
        self.assertEqual(probe.returncode, 0, probe.stderr.decode())
        result = json.loads(probe.stdout)
        self.assertEqual(result['version'], sys.version.split()[0])
        self.assertEqual(result['executable'], str(executable))
        self.assertEqual(result['imports'][0], {'name': 'example', 'version': '1.0', 'actual': '1.0'})
        self.assertIn('error', result['imports'][1])
        self.assertFalse(sentinel.exists(), 'Python startup hooks executed before the admitted import probe')

    def test_expected_parser_schema_is_validated_before_import(self):
        install = self.installation(); install.add('example')
        original = install.identity()
        parser = original['parser']
        runtime.validate_expected_parser(parser)
        self.assertEqual(install.identity(expected_parser=parser)['sha256'], original['sha256'])
        for altered in ({'sha256': parser['sha256']}, dict(parser, files=parser['files'] + 1),
                        dict(parser, sha256='f' * 64)):
            with self.assertRaises(ValueError): install.identity(expected_parser=altered)

    def test_preloaded_parser_is_rejected_and_source_only_state_restores(self):
        old_prefix, old_write = sys.pycache_prefix, sys.dont_write_bytecode
        with runtime.source_only_parser():
            parser = runtime.implementation_parser(runtime.Budget())[3]
            with self.assertRaisesRegex(ValueError, 'Preloaded requirement parser'):
                with runtime.source_only_parser(): pass
        self.assertEqual((sys.pycache_prefix, sys.dont_write_bytecode), (old_prefix, old_write))
        self.assertNotIn(parser['provider'], sys.modules)

    def test_hostile_marshal_declared_allocation_is_bounded(self):
        if sys.platform != 'linux': self.skipTest('Linux production allocation boundary')
        install = self.installation(); source, cache = install.add('example')
        raw = cache.read_bytes()
        # A small encoded tuple header must not allocate a billion references.
        cache.write_bytes(raw[:16] + b'(' + struct.pack('<i', 1000000000))
        with self.assertRaises((ValueError, EOFError, MemoryError)):
            install.identity(metadata_bytes=8 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
