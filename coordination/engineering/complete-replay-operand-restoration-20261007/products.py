"""Flat ordinary output admission; no scientific record may be omitted to fit.

This is the encoded ordinary-descriptor budget, with a separate unchanged
32MiB bound on every decoded body. Caller supplies the complete source/code
roster, not a nested method summary. It is not Baseline/NewVintage's distinct
encoded-plus-decoded aggregate accounting policy.
"""
import gzip
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path

FILE_LIMIT = 33554432
PHASE_LIMIT = 268435456
DESCRIPTOR_LIMIT = 512
SHARD = 8388608


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


class Products:
    def __init__(self, directory, complete_inputs, *, repo):
        repo, directory = Path(repo), Path(directory)
        if not repo.is_absolute() or not directory.is_absolute() or '..' in directory.parts:
            raise ValueError('Absolute owned repository/cache output required')
        if any(p.is_symlink() for p in (repo, *repo.parents, directory, *directory.parents)):
            raise ValueError('Symlink in output or repository ancestor')
        if not repo.is_dir() or not directory.resolve().is_relative_to(repo.resolve() / '.cache'):
            raise ValueError('Output escaped the actual owned cache')
        identities = {(p['commit'], p['path']) for p in complete_inputs}
        if len(identities) != len(complete_inputs):
            raise ValueError('Flat phase contains duplicate source/code descriptors')
        for pin in complete_inputs:
            if type(pin['bytes']) is not int or not 0 <= pin['bytes'] <= FILE_LIMIT:
                raise ValueError('Ordinary encoded input bound')
            if 'uncompressed_bytes' in pin and (type(pin['uncompressed_bytes']) is not int or
                                               not 0 <= pin['uncompressed_bytes'] <= FILE_LIMIT):
                raise ValueError('Ordinary decoded input bound')
        self.input_bytes = sum(p['bytes'] for p in complete_inputs)
        self.input_count = len(complete_inputs)
        if self.input_bytes > PHASE_LIMIT or self.input_count > DESCRIPTOR_LIMIT:
            raise ValueError('Complete flat phase already exceeds admission')
        self.directory = directory
        if directory.exists() or directory.is_symlink():
            raise ValueError('Output destination must be fresh')
        directory.mkdir(parents=True, exist_ok=False)
        self.buffers = defaultdict(bytearray)
        self.ordinals = defaultdict(int)
        self.outputs = []

    def write(self, name, body, compress=False):
        if '/' in name or '\\' in name or name in ('', '.', '..'):
            raise ValueError('Unsafe ordinary output name')
        if len(body) > FILE_LIMIT:
            raise ValueError('One complete decoded output exceeds ordinary bound')
        if compress:
            buffer = io.BytesIO()
            with gzip.GzipFile(filename='', mode='wb', fileobj=buffer,
                               mtime=0, compresslevel=9) as stream:
                stream.write(body)
            encoded = buffer.getvalue()
        else:
            encoded = body
        if len(encoded) > FILE_LIMIT:
            raise ValueError('One complete encoded output exceeds ordinary bound')
        if self.input_bytes + sum(p['bytes'] for p in self.outputs) + len(encoded) > PHASE_LIMIT:
            raise ValueError('Complete flat phase exceeds encoded aggregate; retain failure')
        if self.input_count + len(self.outputs) + 1 > DESCRIPTOR_LIMIT:
            raise ValueError('Complete flat phase exceeds descriptor count')
        path = self.directory / name
        with path.open('xb') as stream:
            stream.write(encoded)
        with path.open('rb') as stream:
            actual = stream.read(len(encoded) + 1)
        if actual != encoded:
            raise ValueError('Whole exclusive output readback differs')
        pin = {'path': name, 'bytes': len(encoded), 'sha256': sha(encoded),
               'hash_kind': 'file-bytes'}
        if compress:
            pin.update(uncompressed_bytes=len(body), uncompressed_sha256=sha(body))
        self.outputs.append(pin)
        return pin

    def emit(self, kind, row):
        if not kind or not all(c.isascii() and (c.isalnum() or c == '-') for c in kind):
            raise ValueError('Unsafe scientific output kind')
        raw = canonical(row)
        if len(raw) > FILE_LIMIT:
            raise ValueError('One complete scientific row exceeds decoded bound')
        if self.buffers[kind] and len(self.buffers[kind]) + len(raw) > SHARD:
            self.flush(kind)
        self.buffers[kind].extend(raw)

    def flush(self, kind):
        if not self.buffers[kind]:
            return
        raw = bytes(self.buffers[kind])
        self.write(f'{kind}-{self.ordinals[kind]:03}.jsonl.gz', raw, compress=True)
        self.ordinals[kind] += 1
        del self.buffers[kind]

    def finish(self):
        for kind in sorted(self.buffers):
            self.flush(kind)
        return sorted(self.outputs, key=lambda pin: pin['path'])
