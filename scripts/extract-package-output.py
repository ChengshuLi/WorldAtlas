"""Extract exactly one authenticated original Cloudflare file inventory.

The archive is authenticated and consumed through one held descriptor. No
archive-selected path, symlink, duplicate, omitted or unlisted file is written.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile

MAX_METADATA = 8 * 1024 * 1024
MAX_SAFE_INTEGER = 2**53 - 1
CHUNK = 1024 * 1024


def need(ok, message):
    if not ok:
        raise ValueError(message)


def safe(name):
    return (isinstance(name, str) and name and not name.startswith('/') and '\\' not in name
            and '\x00' not in name and all(part and part not in ('.', '..') for part in name.split('/')))


@contextmanager
def authenticated_archive(archive, expected_digest):
    archive = Path(archive)
    before = archive.lstat()
    need(stat.S_ISREG(before.st_mode) and isinstance(expected_digest, str)
         and len(expected_digest) == 64, 'Ordinary archive and exact digest required')
    identity = lambda value: tuple(getattr(value, key) for key in
        ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_mtime_ns', 'st_ctime_ns'))
    with os.fdopen(os.open(archive, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        need(identity(os.fstat(stream.fileno())) == identity(before), 'Archive identity changed before consumption')
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            digest.update(chunk)
        need(digest.hexdigest() == expected_digest, 'Archive digest differs from authenticated original upload')
        need(identity(os.fstat(stream.fileno())) == identity(before)
             and identity(archive.lstat()) == identity(before), 'Archive identity changed during authentication')
        stream.seek(0)
        with zipfile.ZipFile(stream) as package:
            yield package
        need(identity(os.fstat(stream.fileno())) == identity(before)
             and identity(archive.lstat()) == identity(before), 'Archive identity changed during consumption')


def manifest_bytes(package):
    matches = [row for row in package.infolist() if row.filename == '.cache/package-output-manifest.json']
    need(len(matches) == 1 and 0 < matches[0].file_size <= MAX_METADATA
         and not matches[0].flag_bits & 1
         and stat.S_IFMT(matches[0].external_attr >> 16) in (0, stat.S_IFREG), 'Bounded unique original manifest required')
    with package.open(matches[0]) as stream:
        raw = stream.read(MAX_METADATA + 1)
        need(len(raw) == matches[0].file_size and len(raw) <= MAX_METADATA, 'Whole bounded manifest required')
    return raw


def extract(archive, target, expected_archive_digest, expected_manifest_digest, expected_manifest_bytes):
    expected_manifest_bytes = int(expected_manifest_bytes)
    need(isinstance(expected_manifest_digest, str) and len(expected_manifest_digest) == 64
         and 0 < expected_manifest_bytes <= MAX_METADATA, 'Exact authenticated original manifest required')
    target = Path(target)
    need(not target.exists() and not target.is_symlink(), 'Fresh owned extraction destination required')
    parent = target.parent.resolve(strict=True)
    need(parent == target.parent.absolute() and not target.parent.is_symlink(), 'Ordinary extraction parent required')
    created = False
    try:
        with authenticated_archive(archive, expected_archive_digest) as package:
            raw = manifest_bytes(package)
            need(len(raw) == expected_manifest_bytes and hashlib.sha256(raw).hexdigest() == expected_manifest_digest,
                 'Manifest differs from authenticated original producer')
            manifest = json.loads(raw)
            need(manifest.get('version') == 1 and manifest.get('kind') == 'original-cloudflare-package-output', 'Unknown output manifest')
            rows = manifest['output']['files']
            need(isinstance(rows, list) and 0 < len(rows) <= 20000, 'Bounded complete output roster required')
            expected = {}
            for row in rows:
                name, size, digest = row['path'], row['bytes'], row['sha256']
                need(safe(name) and name.startswith(('dist/client/', 'dist/cloudflare/')) and name not in expected
                     and type(size) is int and 0 <= size <= MAX_SAFE_INTEGER and isinstance(digest, str) and len(digest) == 64,
                     'Unsafe, duplicate or oversized output member')
                expected[name] = (size, digest)
            need(sum(size for size, _ in expected.values()) == manifest['output']['bytes'] <= MAX_SAFE_INTEGER,
                 'Output aggregate differs or exceeds transport admission')
            expected['.cache/package-output-manifest.json'] = (len(raw), hashlib.sha256(raw).hexdigest())
            receipt = manifest['original_build_receipt']
            need(receipt['path'] == '.cache/package-input-build.json' and type(receipt['bytes']) is int
                 and 0 < receipt['bytes'] <= MAX_METADATA, 'Exact original build receipt required')
            expected[receipt['path']] = (receipt['bytes'], receipt['sha256'])
            allowed_directories = set()
            for name in expected:
                parts = name.split('/')
                allowed_directories.update('/'.join(parts[:i]) for i in range(1, len(parts)))
            members = package.infolist()
            need(len(members) <= len(expected) + len(allowed_directories), 'Unexpected archive members')
            found, directories = set(), set()
            for member in members:
                name = member.filename
                kind = stat.S_IFMT(member.external_attr >> 16)
                need(not member.flag_bits & 1, 'Encrypted package member')
                if member.is_dir():
                    name = name[:-1]
                    need(safe(name) and name in allowed_directories and name not in directories
                         and kind in (0, stat.S_IFDIR), 'Unsafe or duplicate archive directory')
                    directories.add(name)
                else:
                    need(safe(name) and name in expected and name not in found and kind in (0, stat.S_IFREG)
                         and member.file_size == expected[name][0], 'Unsafe, duplicate, unlisted or wrong-size archive member')
                    found.add(name)
            need(found == set(expected), 'Incomplete archive inventory')
            required = sum(size for size, _ in expected.values()) + 4096 * (len(expected) + len(allowed_directories))
            need(shutil.disk_usage(parent).free >= required, 'Insufficient admitted extraction disk')
            target.mkdir(mode=0o700)
            created = True
            for member in members:
                if member.is_dir():
                    continue
                name = member.filename
                destination = target.joinpath(*PurePosixPath(name).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                digest, size = hashlib.sha256(), 0
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                with package.open(member) as source, os.fdopen(os.open(destination, flags, 0o644), 'wb') as output:
                    for chunk in iter(lambda: source.read(CHUNK), b''):
                        size += len(chunk)
                        need(size <= expected[name][0], 'Expanded output exceeds declared bytes')
                        digest.update(chunk)
                        output.write(chunk)
                need((size, digest.hexdigest()) == expected[name], 'Extracted original output digest differs')
        return {'files': len(expected), 'output_bytes': manifest['output']['bytes']}
    except BaseException:
        # Include a failed final archive-identity check in owned-output cleanup.
        if created:
            shutil.rmtree(target)
        raise


def extract_manifest(archive, destination, expected_digest):
    destination = Path(destination)
    need(not destination.exists() and not destination.is_symlink(), 'Fresh manifest destination required')
    with authenticated_archive(archive, expected_digest) as package:
        raw = manifest_bytes(package)
        json.loads(raw)
    with destination.open('xb') as output:
        output.write(raw)
    return {'manifest_bytes': len(raw), 'manifest_sha256': hashlib.sha256(raw).hexdigest()}


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--manifest':
        print(json.dumps(extract_manifest(*sys.argv[2:])))
    else:
        need(len(sys.argv) == 6, 'Use extract-package-output.py ARCHIVE FRESH_TARGET EXPECTED_ARCHIVE_SHA256 EXPECTED_MANIFEST_SHA256 EXPECTED_MANIFEST_BYTES')
        print(json.dumps(extract(*sys.argv[1:])))
