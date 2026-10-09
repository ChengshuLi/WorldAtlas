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

VERSION = 'worldatlas-evidence-preparation-v1'
MAX_FILE_BYTES = 32 * 1024 * 1024


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
    def __init__(self, repo, commit, files):
        if not re.fullmatch('[a-f0-9]{40}', commit):
            raise ValueError('An immutable 40-character baseline commit is required')
        self.repo, self.commit = str(Path(repo).resolve()), commit
        self.pins = {}
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
        self._drift_probe_reads = getattr(self, '_drift_probe_reads', 0) + 1
        name = safe_path(name)
        row = self._git('ls-tree', '-z', self.commit, '--', name).decode().rstrip('\0')
        if not row.startswith(('100644 ', '100755 ')) or '\t' + name != row[row.find('\t'):]:
            raise ValueError('Baseline evidence must be an ordinary committed file: ' + name)
        blob = row.split()[2]
        if int(self._git('cat-file', '-s', blob)) > MAX_FILE_BYTES:
            raise ValueError('Baseline file exceeds byte budget')
        return self._git('cat-file', 'blob', blob)

    def subjects(self, ids, index='data/world-index.json'):
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate requested subjects')
        index = safe_path(index)
        if index not in self.pins:
            raise ValueError('World-index bytes must have a reviewed pin')
        parts = json.loads(self.read(index))['parts']
        root = str(Path(index).parent)
        found = {}
        containing = {}
        for part in parts:
            name = safe_path(root + '/' + part)
            raw = self.read(name)
            if name.endswith('.gz'):
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                    raw_json = stream.read(MAX_FILE_BYTES + 1)
                if len(raw_json) > MAX_FILE_BYTES:
                    raise ValueError('Uncompressed part exceeds byte budget')
            else:
                raw_json = raw
            for feature in json.loads(raw_json)['features']:
                identity = feature.get('id') or feature.get('properties', {}).get('id')
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


def write_new_vintage(baseline, owned_path, vintage, filename, value):
    if not re.fullmatch(r'(data/regional-review|research/geography|research/campaigns)/[a-z0-9][a-z0-9-]{0,63}/', owned_path):
        raise ValueError('Destination must be an explicitly owned research namespace')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', vintage) or not re.fullmatch(r'[a-zA-Z0-9_-]+\.json(?:\.gz)?', filename):
        raise ValueError('Use a named new vintage and a plain JSON filename')
    # Recheck every pin before even creating directories; changed working-tree
    # evidence is irrelevant, a caller cannot substitute a different baseline.
    for name, pin in baseline.pins.items():
        if sha256(baseline.read(name)) != pin['sha256']:
            raise ValueError('Immutable baseline input changed')
    target = Path(baseline.repo) / owned_path / 'vintages' / vintage / filename
    for ancestor in [target, *target.parents]:
        if ancestor == Path(baseline.repo).parent:
            break
        if ancestor.is_symlink():
            raise ValueError('Symlink in output path')
    if target.exists():
        raise FileExistsError('Original/new evidence already exists; preserve it and choose a new vintage')
    raw = canonical_json(value)
    encoded = deterministic_gzip(raw) if filename.endswith('.gz') else raw
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
