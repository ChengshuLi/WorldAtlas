"""Job-local whole-byte transport; no scientific algorithms or geometry changes."""
import gzip
import hashlib
import os
import stat
import sys
import zipfile
import zlib
from pathlib import Path

CAP = 32 * 1024 * 1024
FRAME = 8 * 1024 * 1024
TOTAL = 256 * 1024 * 1024
PREFIX = 'coordination/engineering/reference-source-custody-20261007/'


def ordinary(root, relative):
    if not isinstance(relative, str):
        raise ValueError('Relative ordinary path required')
    if '\\' in relative or '\0' in relative or any(x in ('', '.', '..') for x in relative.split('/')):
        raise ValueError('Unsafe ordinary path')
    p = Path(relative)
    if p.is_absolute() or not p.parts or any(x in ('..', '.') for x in p.parts):
        raise ValueError('Unsafe ordinary path')
    base = Path(root).absolute()
    if '..' in base.parts or any(parent.is_symlink() for parent in (base, *base.parents)):
        raise ValueError('Symlink or traversal in ordinary root')
    if not base.is_dir():
        raise ValueError('Ordinary root must exist')
    target = base.resolve(strict=True)
    for part in p.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError('Symlink in ordinary path')
    return target


def digest(path, size, expected, *, cap=None):
    if type(size) is not int or size < 0 or (cap is not None and size > cap):
        raise ValueError('Declared whole-byte bound')
    # Open without following a replaced leaf; check the opened file itself.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        s = os.fstat(stream.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_size != size:
            raise ValueError('Actual whole-file size/type drift')
        h = hashlib.sha256(); n = 0
        while True:
            block = stream.read(min(1024 * 1024, size - n + 1))
            if not block:
                break
            n += len(block)
            if n > size:
                raise ValueError('Opened whole-file growth')
            h.update(block)
        if n != size or h.hexdigest() != expected:
            raise ValueError('Whole-file byte drift')
    return h.hexdigest()


def budget(pins, reserve=0):
    if type(reserve) is not int or reserve < 0:
        raise ValueError('Invalid reserved output bytes')
    paths = set(); total = reserve
    for p in pins:
        if p['path'] in paths:
            raise ValueError('Duplicate ordinary descriptor')
        paths.add(p['path'])
        if (type(p['bytes']) is not int or not 0 <= p['bytes'] <= CAP or
                type(p.get('decoded_bytes', p['bytes'])) is not int or
                not 0 <= p.get('decoded_bytes', p['bytes']) <= CAP):
            raise ValueError('Ordinary encoded/decoded cap')
        total += p['bytes']
    if len(paths) > 512 or total > TOTAL:
        raise ValueError('Complete ordinary phase budget')
    return {'ordinary_files': len(paths), 'encoded_bytes_with_reserve': total,
            'reserved_output_bytes': reserve}


def publish(root, pin, raw):
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Generated ordinary byte drift')
    if len(raw) > CAP:
        raise ValueError('Generated ordinary cap')
    path = ordinary(root, pin['path']); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out:
        out.write(raw)
    return pin


def split_original(source, obj, pins, root):
    digest(source, obj['whole_bytes'], obj['whole_sha256'])
    offset = 0
    with Path(source).open('rb') as stream:
        for ordinal, pin in enumerate(pins):
            if pin['offset'] != offset or pin['ordinal'] != ordinal:
                raise ValueError('Fragment continuity')
            raw = stream.read(pin['decoded_bytes'])
            if len(raw) != pin['decoded_bytes'] or hashlib.sha256(raw).hexdigest() != pin['decoded_sha256']:
                raise ValueError('Original decoded fragment drift')
            publish(root, pin, gzip.compress(raw, mtime=0))
            offset += len(raw)
        if stream.read(1) or offset != obj['whole_bytes']:
            raise ValueError('Whole original fragment closure')


def restore_original(root, obj, pins, destination):
    offset = 0; full = hashlib.sha256()
    with Path(destination).open('xb') as out:
        for ordinal, pin in enumerate(pins):
            if pin['offset'] != offset or pin['ordinal'] != ordinal:
                raise ValueError('Fragment continuity')
            path = ordinary(root, pin['path'])
            digest(path, pin['bytes'], pin['sha256'], cap=CAP)
            h = hashlib.sha256(); n = 0
            with gzip.open(path, 'rb') as stream:
                while True:
                    block = stream.read(min(1024 * 1024, pin['decoded_bytes'] - n + 1))
                    if not block:
                        break
                    n += len(block)
                    if n > pin['decoded_bytes'] or n > CAP:
                        raise ValueError('Decoded fragment growth')
                    h.update(block); full.update(block); out.write(block)
            if n != pin['decoded_bytes'] or h.hexdigest() != pin['decoded_sha256']:
                raise ValueError('Decoded fragment drift')
            offset += n
    if offset != obj['whole_bytes'] or full.hexdigest() != obj['whole_sha256']:
        raise ValueError('Whole reconstructed original drift')


def extract_members(archive_path, members, root):
    names = [p['archive_entry'] for p in members]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate declared native member')
    with zipfile.ZipFile(archive_path) as archive:
        # Unselected archive entries stay retained in the whole archive; never extractall.
        for pin in members:
            matches = [x for x in archive.infolist() if x.filename == pin['archive_entry']]
            if len(matches) != 1:
                raise ValueError('Missing/duplicate selected ZIP member')
            info = matches[0]
            if (info.is_dir() or info.flag_bits & 1 or info.file_size != pin['bytes'] or
                    info.compress_size != pin['ZIP_compressed_bytes'] or info.CRC != pin['ZIP_CRC32'] or
                    info.file_size > CAP or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError('Selected ZIP header/type/bound drift')
            path = ordinary(root, pin['path']); path.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256(); n = 0; crc = 0
            with archive.open(info) as stream, path.open('xb') as out:
                while True:
                    block = stream.read(min(1024 * 1024, pin['bytes'] - n + 1))
                    if not block:
                        break
                    n += len(block)
                    if n > pin['bytes']:
                        raise ValueError('Selected member decoded growth')
                    h.update(block); crc = zlib.crc32(block, crc); out.write(block)
            if n != pin['bytes'] or h.hexdigest() != pin['sha256'] or crc != pin['ZIP_CRC32']:
                raise ValueError('Complete selected native member drift')


class ReadGate:
    """Actual Python open audit events, active only for literal stock source_proof."""
    def __init__(self, allowed):
        self.allowed = {str(Path(p).resolve(strict=True)) for p in allowed}
        self.seen = set(); self.events = []; self.active = False
        sys.addaudithook(self.observe)

    def observe(self, event, args):
        if not self.active or event != 'open':
            return
        path, mode, flags = args
        if not isinstance(path, (str, bytes, Path)):
            raise ValueError('Stock proof undeclared descriptor read')
        name = str(Path(os.fsdecode(path)).resolve(strict=True))
        if name not in self.allowed or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise ValueError('Stock proof undeclared read/write')
        self.seen.add(name); self.events.append({'path': name, 'flags': flags, 'mode': mode})

    def call(self, fn, *args):
        if self.active:
            raise ValueError('Nested stock read gate')
        self.active = True
        try:
            result = fn(*args)
        finally:
            self.active = False
        if self.seen != self.allowed:
            raise ValueError('Stock proof incomplete actual read closure')
        return result
