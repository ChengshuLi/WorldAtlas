"""Capture input bytes in a private, unlinked file with a read-only handle."""
import os
from pathlib import Path
import tempfile


def open_snapshot(write, *, directory=None):
    with tempfile.TemporaryDirectory(prefix='worldatlas-input-', dir=directory) as temporary:
        path = Path(temporary) / 'snapshot'
        with path.open('xb') as output:
            write(output)
        fd = os.open(path, os.O_RDONLY)
        try:
            path.unlink()
        except BaseException:
            os.close(fd)
            raise
        return fd
