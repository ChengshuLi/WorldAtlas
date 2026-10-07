"""Bounded reads of the accepted reference custody and original whole world."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[3]
CAP = 32 * 1024 * 1024


def exact_commit(commit):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Exact immutable commit required before Git')
    return commit


def safe(root, relative):
    if (not isinstance(relative, str) or '\\' in relative or '\0' in relative or
            any(x in ('', '.', '..') for x in relative.split('/')) or
            Path(relative).is_absolute()):
        raise ValueError('Safe relative ordinary path required')
    root = Path(root).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)) or not root.is_dir():
        raise ValueError('Ordinary root and ancestors required')
    p = root
    for part in relative.split('/'):
        p /= part
        if p.is_symlink():
            raise ValueError('Ordinary path contains symlink')
    return p


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded(path, size=None):
    if size is not None and (type(size) is not int or not 0 <= size <= CAP):
        raise ValueError('Declared ordinary cap')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or not 0 <= s.st_size <= CAP or size is not None and s.st_size != size:
            raise ValueError('Opened ordinary size/type')
        raw = f.read(s.st_size + 1)
        if len(raw) != s.st_size or f.read(1):
            raise ValueError('Opened ordinary growth or truncation')
    return raw


def gunzip(raw, size):
    import io
    if type(size) is not int or not 0 <= size <= CAP:
        raise ValueError('Decoded ordinary cap')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:
        decoded = f.read(size + 1)
        if len(decoded) != size or f.read(1):
            raise ValueError('Decoded ordinary growth or truncation')
    return decoded


class Inputs:
    def __init__(self, commit):
        self.commit = exact_commit(commit)
        self.pins = {}

    def read(self, relative):
        path = safe(ROOT, relative)
        # Check size before whole immutable/materialized reads.
        raw = bounded(path)
        item = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-l', self.commit, '--', relative], text=True).strip()
        if not item or '\t' not in item:
            raise ValueError('Missing committed input')
        fields, name = item.split('\t'); mode, kind, oid, size = fields.split()
        if name != relative or mode != '100644' or kind != 'blob' or int(size) != len(raw):
            raise ValueError('Immutable ordinary metadata drift')
        actual_oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if actual_oid != oid:
            raise ValueError('Actual immutable Git blob drift')
        self.pins[relative] = {'commit': self.commit, 'path': relative, 'mode': mode,
                'blob': oid, 'bytes': len(raw), 'sha256': sha(raw)}
        return raw

    def json(self, relative):
        return json.loads(self.read(relative))

    def alias(self, prefix, row):
        p = row['ordinary']; o = row['original']
        raw = self.read(prefix + p['path'])
        if len(raw) != p['bytes'] or sha(raw) != p['sha256']:
            raise ValueError('Whole alias byte drift')
        result = gunzip(raw, p['decoded_bytes'])
        if (sha(result) != p['decoded_sha256'] or len(result) != o['bytes'] or
                sha(result) != o['sha256'] or o['mode'] != '100644' or
                hashlib.sha1(b'blob ' + str(len(result)).encode() + b'\0' + result).hexdigest() != o['git_blob_oid']):
            raise ValueError('Original whole byte/OID relation drift')
        exact_commit(o['commit'])
        old = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-l', o['commit'], '--', o['path']], text=True).strip()
        if not old or old.split('\t')[0].split() != ['100644', 'blob', o['git_blob_oid'], str(o['bytes'])]:
            raise ValueError('Original containing-file binding drift')
        return result
