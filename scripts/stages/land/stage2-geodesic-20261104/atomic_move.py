"""Crash-safe, no-overwrite directory publication using Python's filesystem API.

POSIX os.rename may overwrite an existing empty directory. Instead, copy the
sealed tree to a private durable sibling payload, then publish one exclusive
symlink. Readers see either no destination or the complete tree. The payload
is independent of the work tree, so preserving or removing work cannot break
published output. Interrupted/unpublished payloads are retained for inspection.
"""
import errno
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

SCHEMA = 'worldatlas-directory-publication-v1'


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _copy_tree(source_fd, destination):
    """Copy only regular files/directories, without following source symlinks."""
    destination.mkdir(mode=0o700)
    for name in sorted(os.listdir(source_fd)):
        info = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
        target = destination / name
        if stat.S_ISDIR(info.st_mode):
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
            try:
                _copy_tree(fd, target)
            finally:
                os.close(fd)
        elif stat.S_ISREG(info.st_mode):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=source_fd)
            with os.fdopen(fd, 'rb') as source:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ValueError('non-regular publication source')
                with target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1 << 20)
                    output.flush()
                    os.fsync(output.fileno())
        else:
            raise ValueError('linked or non-regular publication source')
    _sync_directory(destination)


def published_directory(path):
    """Validate our exact sibling-payload protocol, rejecting arbitrary links.

    The returned receipt is sealed by checkpoint inventories along with every
    output file. Relative links, escaping payloads, linked receipts and nested
    links are not permitted.
    """
    path = output_path(path)
    if not path.is_symlink():
        raise ValueError('not a published directory link')
    target = Path(os.readlink(path))
    if (not target.is_absolute() or target.name != 'data' or
            target.parent.parent != path.parent.resolve() or
            not target.parent.name.startswith('.' + path.name + '.payload-') or
            target.parent.is_symlink() or target.is_symlink() or not target.is_dir()):
        raise ValueError('invalid publication payload path')
    receipt = target.parent / 'publication.json'
    if receipt.is_symlink() or not receipt.is_file():
        raise ValueError('missing publication receipt')
    value = json.loads(receipt.read_bytes())
    if value != {'schema': SCHEMA, 'destination': str(path), 'payload': str(target)}:
        raise ValueError('publication receipt mismatch')
    return target, receipt


def output_path(path):
    """Canonicalize parents while preserving an occupied destination leaf."""
    path = Path(os.path.abspath(path))
    return path.parent.resolve(strict=True) / path.name


def move_noreplace(source, destination):
    """Publish an independent complete directory, then remove the source.

    No check-then-rename and no replacement are used. Concurrent publishers
    compete at os.symlink, which fails atomically for *any* existing name,
    including empty directories and dangling symlinks. If a durability or
    cleanup error occurs after publication, keep the output and report an
    uncertain result rather than rolling it back or retrying blindly.
    """
    source = output_path(source)
    destination = output_path(destination)
    if os.path.lexists(destination):
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(destination))
    if source.is_symlink() or not source.is_dir():
        raise ValueError('publication source must be a real directory')
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('publication source and destination overlap')
    if source.stat().st_dev != destination.parent.stat().st_dev:
        raise OSError(errno.EXDEV, 'publication requires the same filesystem')
    payload = Path(tempfile.mkdtemp(prefix='.' + destination.name + '.payload-', dir=destination.parent))
    data = payload / 'data'
    fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _copy_tree(fd, data)
    finally:
        os.close(fd)
    with (payload / 'publication.json').open('x') as stream:
        json.dump({'schema': SCHEMA, 'destination': str(destination), 'payload': str(data)}, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    _sync_directory(payload)
    _sync_directory(destination.parent)
    os.symlink(str(data), destination, target_is_directory=True)
    try:
        _sync_directory(destination.parent)
        shutil.rmtree(source)
        _sync_directory(source.parent)
    except OSError as exc:
        raise RuntimeError('published output may exist; durability or source cleanup uncertain, inspect before retry') from exc
