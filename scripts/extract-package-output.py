"""Extract exactly one authenticated original Cloudflare file inventory.

The trusted caller supplies the authenticated archive digest and manifest bytes.
No archive-selected path, symlink, duplicate, omitted or unlisted file is written.
"""
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


def digest_file(file):
    digest = hashlib.sha256()
    with open(file, 'rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            digest.update(chunk)
    return digest.hexdigest()


def extract(archive, manifest_file, target, expected_archive_digest):
    archive, manifest_file, target = Path(archive), Path(manifest_file), Path(target)
    need(not archive.is_symlink() and archive.is_file() and not manifest_file.is_symlink()
         and manifest_file.is_file() and manifest_file.stat().st_size <= MAX_METADATA, 'Ordinary bounded inputs required')
    need(len(expected_archive_digest) == 64 and digest_file(archive) == expected_archive_digest,
         'Archive digest differs from authenticated original upload')
    raw = manifest_file.read_bytes()
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
    need(not target.exists() and not target.is_symlink(), 'Fresh owned extraction destination required')
    parent = target.parent.resolve(strict=True)
    need(parent == target.parent.absolute() and not target.parent.is_symlink(), 'Ordinary extraction parent required')
    with zipfile.ZipFile(archive) as package:
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
        try:
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
        except BaseException:
            # Only this invocation's exclusively created destination is removed.
            shutil.rmtree(target)
            raise
    return {'files': len(expected), 'output_bytes': manifest['output']['bytes']}


def extract_manifest(archive, destination, expected_digest):
    archive, destination = Path(archive), Path(destination)
    need(not archive.is_symlink() and archive.is_file() and digest_file(archive) == expected_digest,
         'Original archive digest differs')
    need(not destination.exists() and not destination.is_symlink(), 'Fresh manifest destination required')
    with zipfile.ZipFile(archive) as package:
        matches = [row for row in package.infolist() if row.filename == '.cache/package-output-manifest.json']
        need(len(matches) == 1 and 0 < matches[0].file_size <= MAX_METADATA
             and stat.S_IFMT(matches[0].external_attr >> 16) in (0, stat.S_IFREG), 'Bounded unique original manifest required')
        with package.open(matches[0]) as stream:
            raw = stream.read(MAX_METADATA + 1)
            need(len(raw) == matches[0].file_size and len(raw) <= MAX_METADATA, 'Whole bounded manifest required')
        json.loads(raw)
        with destination.open('xb') as output:
            output.write(raw)
    return {'manifest_bytes': len(raw), 'manifest_sha256': hashlib.sha256(raw).hexdigest()}


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--manifest':
        print(json.dumps(extract_manifest(*sys.argv[2:])))
    else:
        need(len(sys.argv) == 5, 'Use extract-package-output.py ARCHIVE MANIFEST FRESH_TARGET EXPECTED_ARCHIVE_SHA256')
        print(json.dumps(extract(*sys.argv[1:])))
