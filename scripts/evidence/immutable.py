"""Immutable baseline reads and exclusive deterministic new-vintage writes, v1."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import builtins
import importlib.util
import types
from evidence.contracts import exact_rows

VERSION = 'worldatlas-evidence-preparation-v1'
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PHASE_BYTES = 256 * 1024 * 1024


def safe_path(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('Unsafe repository path')
    return value


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def descriptor(path, raw):
    return {'path': safe_path(path), 'bytes': len(raw), 'sha256': sha256(raw), 'hash_kind': 'file-bytes'}


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def deterministic_gzip(raw):
    output = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0, compresslevel=9) as stream:
        stream.write(raw)
    return output.getvalue()


class Baseline:
    """A commit plus reviewed whole-file pins; never the mutable working tree."""
    def __init__(self, repo, commit, files, *, max_phase_bytes=MAX_PHASE_BYTES):
        if not re.fullmatch('[a-f0-9]{40}', commit):
            raise ValueError('An immutable 40-character baseline commit is required')
        self.repo, self.commit = str(Path(repo).resolve()), commit
        self.pins = {}
        if not isinstance(max_phase_bytes, int) or not 0 < max_phase_bytes <= MAX_PHASE_BYTES:
            raise ValueError('Invalid bounded phase budget')
        self.max_phase_bytes = max_phase_bytes
        self.consumed = {}
        resolved = self._git('rev-parse', '--verify', '--end-of-options', commit + '^{commit}').decode().strip()
        if resolved != commit:
            raise ValueError('Baseline commit mismatch')
        for f in files:
            name = safe_path(f['path'])
            if name in self.pins or f.get('hash_kind') != 'file-bytes' or not re.fullmatch('[a-f0-9]{64}', f.get('sha256', '')):
                raise ValueError('Require unique whole-file SHA-256 pins')
            raw = self.read(name)
            if len(raw) != f.get('bytes') or sha256(raw) != f['sha256']:
                raise ValueError('Baseline input hash/size mismatch: ' + name)
            self.pins[name] = f
        if not self.pins:
            raise ValueError('No reviewed baseline/source pins')

    def _git(self, *args):
        return subprocess.check_output(['git', '-C', self.repo, *args], stderr=subprocess.PIPE)

    def read(self, name):
        name = safe_path(name)
        row = self._git('ls-tree', '-z', self.commit, '--', name).decode().rstrip('\0')
        if not row.startswith(('100644 ', '100755 ')) or '\t' + name != row[row.find('\t'):]:
            raise ValueError('Baseline evidence must be an ordinary committed file: ' + name)
        blob = row.split()[2]
        size = int(self._git('cat-file', '-s', blob))
        if size > MAX_FILE_BYTES:
            raise ValueError('Baseline file exceeds byte budget')
        self.admit(name, size)
        return self._git('cat-file', 'blob', blob)

    def admit(self, name, size):
        """Account unique actual raw/decoded inputs, including index discoveries."""
        if size < 0 or size > MAX_FILE_BYTES:
            raise ValueError('Input exceeds file byte budget')
        previous = self.consumed.get(name)
        if previous is not None and previous != size:
            raise ValueError('Consumed input size changed')
        if previous is None:
            if sum(self.consumed.values()) + size > self.max_phase_bytes:
                raise ValueError('Complete execution phase exceeds byte budget')
            self.consumed[name] = size

    def pinned_bytes(self, name):
        name = safe_path(name)
        pin = self.pins.get(name)
        if pin is None:
            raise ValueError('Consumed input/code lacks reviewed whole-file pin: ' + name)
        raw = self.read(name)
        if len(raw) != pin['bytes'] or sha256(raw) != pin['sha256']:
            raise ValueError('Consumed immutable bytes disagree with pin')
        return raw

    def materialized_bytes(self, name):
        """Authenticate the captured bytes actually supplied to a legacy reader."""
        expected = self.pinned_bytes(name)
        target = Path(self.repo) / safe_path(name)
        for ancestor in [target, *target.parents]:
            if ancestor == Path(self.repo).parent:
                break
            if ancestor.is_symlink():
                raise ValueError('Symlink in consumed input/code path')
        with target.open('rb') as stream:
            actual = stream.read(MAX_FILE_BYTES + 1)
        if actual != expected:
            raise ValueError('Actually consumed materialized input/code drift: ' + name)
        return actual

    def load_modules(self, project_modules):
        """Execute captured pinned code, including explicitly named local imports.

        This is cooperative provenance tooling, not a sandbox. Dynamic file reads
        must use pinned_bytes/materialized_bytes; installed dependencies require
        a recorded runtime. Undeclared imports resolving inside the checkout fail.
        """
        if not project_modules or any(not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', n) for n in project_modules):
            raise ValueError('Require named project module inventory')
        sources = {name: self.pinned_bytes(path) for name, path in project_modules.items()}
        modules = {}
        def load(name):
            if name in modules:
                return modules[name]
            module = types.ModuleType(name)
            module.__file__ = self.repo + '/' + project_modules[name]
            module.__package__ = name.rpartition('.')[0]
            module.__dict__['__builtins__'] = {**vars(builtins), '__import__': import_pinned}
            modules[name] = module
            exec(compile(sources[name], module.__file__, 'exec'), module.__dict__)
            return module
        def import_pinned(name, globals=None, locals=None, fromlist=(), level=0):
            if level:
                raise ValueError('Use explicit absolute project imports in pinned execution')
            if name in sources:
                if not fromlist and '.' in name:
                    raise ValueError('Use from-import for a dotted pinned project module')
                return load(name)
            # Looking up a dotted name can execute its parent package. Admit the
            # top-level location first rather than importing an unverified parent.
            spec = importlib.util.find_spec(name.split('.')[0])
            locations = list(spec.submodule_search_locations or []) if spec else []
            if spec and spec.origin and spec.origin not in ('built-in', 'frozen'):
                locations.append(spec.origin)
            if any(Path(location).resolve().is_relative_to(self.repo) for location in locations):
                raise ValueError('Undeclared executed project code: ' + name)
            return builtins.__import__(name, globals, locals, fromlist, level)
        return {name: load(name) for name in sources}

    def subjects(self, ids, index='data/world-index.json'):
        exact_rows([{'id': identity} for identity in ids], ids)
        index = safe_path(index)
        if index not in self.pins:
            raise ValueError('World-index bytes must have a reviewed pin')
        parts = json.loads(self.read(index))['parts']
        if not isinstance(parts, list) or not parts or len(parts) != len(set(parts)):
            raise ValueError('Require a complete unique indexed part inventory')
        root = str(Path(index).parent)
        found = {}
        containing = {}
        all_ids = set()
        for part in parts:
            name = safe_path(root + '/' + part)
            raw = self.read(name)
            if name.endswith('.gz'):
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                    raw_json = stream.read(MAX_FILE_BYTES + 1)
                if len(raw_json) > MAX_FILE_BYTES:
                    raise ValueError('Uncompressed part exceeds byte budget')
                self.admit(name + ':decoded', len(raw_json))
            else:
                raw_json = raw
            for feature in json.loads(raw_json)['features']:
                identity = feature.get('id') or feature.get('properties', {}).get('id')
                property_id = feature.get('properties', {}).get('id')
                if not isinstance(identity, str) or not identity or identity in all_ids or property_id not in (None, identity):
                    raise ValueError('Missing, conflicting or duplicate indexed identity')
                all_ids.add(identity)
                if identity in ids:
                    if identity in found:
                        raise ValueError('Subject occurs in multiple containing files: ' + identity)
                    found[identity] = feature
                    containing[identity] = descriptor(name, raw)
        if set(found) != set(ids):
            raise ValueError('Subjects absent from immutable index: ' + str(sorted(set(ids) - set(found))))
        return found, containing


def validate_source_receipts(registry, receipts, baseline):
    entries = {x['id']: x for x in registry}
    if len({x['id'] for x in receipts}) != len(receipts):
        raise ValueError('Duplicate source receipts')
    if len(entries) != len(registry):
        raise ValueError('Duplicate source IDs')
    for receipt in receipts:
        source = entries.get(receipt['id'])
        pin = baseline.pins.get(receipt['path'])
        if not source or not pin or source.get('sha256') != receipt.get('sha256') or pin['sha256'] != receipt.get('sha256'):
            raise ValueError('Source registry/receipt/baseline disagree')


def admit_destination(baseline, owned_path, vintage, filenames):
    if not re.fullmatch(r'(data/regional-review|research/geography|research/campaigns|coordination/engineering)/[a-z0-9][a-z0-9-]{0,63}/', owned_path):
        raise ValueError('Destination must be an explicitly owned evidence namespace')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', vintage):
        raise ValueError('Use a safe named fresh vintage')
    if not filenames or len(filenames) != len(set(filenames)) or any(
        not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}', name) for name in filenames
    ):
        raise ValueError('Use a complete unique plain output filename inventory')
    root = Path(baseline.repo) / owned_path / 'vintages' / vintage
    for target in [root, *(root / name for name in filenames)]:
        for ancestor in [target, *target.parents]:
            if ancestor == Path(baseline.repo).parent:
                break
            if ancestor.is_symlink():
                raise ValueError('Symlink in output path')
        if target != root and target.exists():
            raise FileExistsError('Evidence already exists; choose a new vintage')
    return root


class NewVintage:
    """Admit an entire fresh run before compute; completion is published last."""
    def __init__(self, baseline, owned_path, vintage, filenames):
        self.baseline, self.owned_path, self.vintage = baseline, owned_path, vintage
        self.filenames = list(filenames)
        if 'publication.json' in self.filenames:
            raise ValueError('publication.json is reserved for the final completion receipt')
        self.root = admit_destination(baseline, owned_path, vintage, self.filenames)
        if self.root.exists():
            raise FileExistsError('Fresh run directory already exists')

    def publish(self, values):
        if any(not re.fullmatch(r'[a-zA-Z0-9_-]+\.json(?:\.gz)?', name) for name in values):
            raise ValueError('Use publish_bytes for non-JSON products')
        payloads = {}
        for name, value in values.items():
            raw = canonical_json(value)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError('Output exceeds file byte budget')
            payloads[name] = deterministic_gzip(raw) if name.endswith('.gz') else raw
        return self.publish_bytes(payloads)

    def publish_bytes(self, values):
        """Publish complete CSV/JSONL/GeoJSON/etc. bytes with the same safeguards."""
        if set(values) != set(self.filenames):
            raise ValueError('Incomplete or unexpected output set')
        payloads = {}
        decoded_output_bytes = 0
        for name, value in values.items():
            if not isinstance(value, bytes) or len(value) > MAX_FILE_BYTES:
                raise ValueError('Require bounded complete output bytes')
            payloads[name] = value
            if name.endswith('.gz'):
                with gzip.GzipFile(fileobj=io.BytesIO(value)) as stream:
                    raw = stream.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES:
                    raise ValueError('Decoded output exceeds file byte budget')
                decoded_output_bytes += len(raw)
        if sum(self.baseline.consumed.values()) + sum(len(raw) for raw in payloads.values()) + decoded_output_bytes + 4096 > self.baseline.max_phase_bytes:
            raise ValueError('Complete phase including output exceeds byte budget')
        records = [descriptor(str((self.root / name).relative_to(self.baseline.repo)), raw) for name, raw in payloads.items()]
        receipt = canonical_json({'version': 1, 'status': 'complete', 'outputs': records})
        if len(receipt) > 4096:
            raise ValueError('Completion receipt exceeds admitted reserve')
        # Check the entire set and all pins again immediately before first mutation.
        NewVintage(self.baseline, self.owned_path, self.vintage, self.filenames)
        for name in self.baseline.pins:
            self.baseline.pinned_bytes(name)
        self.root.parent.mkdir(parents=True, exist_ok=True)
        self.root.mkdir()  # Exclusive run reservation; never reuse a retained run.
        try:
            for name, raw in payloads.items():
                target = self.root / name
                with target.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            # Install only a fully flushed complete receipt. A failed write/fsync
            # cannot leave a parseable success record at its accepted pathname.
            temporary = self.root / '.publication-incomplete'
            with temporary.open('xb') as stream:
                stream.write(receipt)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, self.root / 'publication.json')
            temporary.unlink()
        except Exception:
            # A partial new run is not accepted evidence. Do not overwrite/retry it.
            # No complete receipt is installed until all planned files have succeeded.
            raise
        return records


def write_new_vintage(baseline, owned_path, vintage, filename, value):
    target = admit_destination(baseline, owned_path, vintage, [filename]) / filename
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', vintage) or not re.fullmatch(r'[a-zA-Z0-9_-]+\.json(?:\.gz)?', filename):
        raise ValueError('Use a named new vintage and a plain JSON filename')
    # Recheck every pin before even creating directories; changed working-tree
    # evidence is irrelevant, a caller cannot substitute a different baseline.
    for name, pin in baseline.pins.items():
        if sha256(baseline.read(name)) != pin['sha256']:
            raise ValueError('Immutable baseline input changed')
    raw = canonical_json(value)
    encoded = deterministic_gzip(raw) if filename.endswith('.gz') else raw
    output_bytes = len(encoded) + (len(raw) if filename.endswith('.gz') else 0)
    if len(raw) > MAX_FILE_BYTES or len(encoded) > MAX_FILE_BYTES or sum(baseline.consumed.values()) + output_bytes > baseline.max_phase_bytes:
        raise ValueError('Output exceeds complete byte budget')
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix='.evidence-', dir=target.parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link creation is atomic and exclusive, unlike overwrite-capable rename.
        os.link(temporary, target)
    finally:
        if temporary:
            os.unlink(temporary)
    record = descriptor(str(target.relative_to(baseline.repo)), encoded)
    if filename.endswith('.gz'):
        record.update(uncompressed_sha256=sha256(raw), uncompressed_bytes=len(raw))
    return record
