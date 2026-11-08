"""One immutable, SHA-verified grid generation for in-process water producers.

Copies are private and unlinked, opened read-only, and never obtained by trusting
pathname/stat cache hits. Original streams are rehashed before successful exit.
Standalone producers can retain their independent verification path.
"""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import stat
from types import MappingProxyType

import numpy as np

from coastal_shore_index import CoastalShoreIndex
import coastal_shore_index
import snapshot_input


NAMES = ('physical_rows', 'physical_runs', 'land_rows', 'land_runs')


def input_path(path):
    """Normalize relative parents without following the final source symlink."""
    path = Path(os.path.abspath(path))
    return path.parent.resolve(strict=True) / path.name


def visit_pinned(path, expected, consume=lambda block: None):
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('invalid grid SHA-256 pin')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('grid input is not a regular file')
        digest = hashlib.sha256(); total = 0
        for block in iter(lambda: source.read(1 << 20), b''):
            total += len(block)
            if total > before.st_size:
                raise ValueError('grid input grew during verification')
            digest.update(block); consume(block)
        after = os.fstat(source.fileno())
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (total != before.st_size or digest.hexdigest() != expected
                or any(getattr(before, key) != getattr(after, key) for key in fields)):
            raise ValueError('grid input changed or SHA-256 mismatch')
        return total


class VerifiedWaterInputs:
    """A context-owned snapshot; match all caller pins before sharing its arrays."""
    def __init__(self, specifications, width, height, *, work_root):
        if set(specifications) != set(NAMES):
            raise ValueError('exactly four grid input pins are required')
        if any(type(value) is not int or value <= 0 for value in (width, height)):
            raise ValueError('invalid shared grid dimensions')
        self.width, self.height = width, height
        self.work_root = Path(work_root).resolve(strict=True)
        if not self.work_root.is_dir():raise ValueError('shared input workspace scratch directory must exist')
        self.paths = MappingProxyType({key: input_path(specifications[key]['path']) for key in NAMES})
        self.pins = MappingProxyType({key: specifications[key]['sha256'] for key in NAMES})
        self._state = 'new'; self._arrays = {}; self._stack = ExitStack()
        self.shore_index = None
        self._sources = {'verified_water_inputs': Path(__file__),
                         'coastal_shore_index': Path(coastal_shore_index.__file__),
                         'shared_nearest': Path(coastal_shore_index.shore.__file__),
                         'snapshot_input': Path(snapshot_input.__file__)}
        self._code_pins = {}

    def provenance(self):
        if self._state != 'active':
            raise RuntimeError('shared water inputs are not active')
        return {'schema': 'worldatlas-verified-shared-water-inputs-v1',
                'grid': {'width': self.width, 'height': self.height},
                'input_sha256': dict(self.pins), 'code_sha256': dict(self._code_pins),
                'storage': 'unlinked-read-only-SHA-verified-snapshots'}

    def __enter__(self):
        if self._state != 'new':
            raise RuntimeError('shared water input context cannot be reused')
        try:
            here = Path(__file__).resolve().parent
            for name,path in self._sources.items():
                expected = (here.parent if name == 'snapshot_input' else here) / (name + '.py')
                if path.resolve() != expected:
                    raise ImportError('shared water input helper resolved outside the selected checkout: ' + name)
            self._code_pins = {key: hashlib.sha256(path.read_bytes()).hexdigest()
                               for key,path in self._sources.items()}
            for name in NAMES:
                def copy(output, name=name):
                    visit_pinned(self.paths[name], self.pins[name], output.write)
                fd = snapshot_input.open_snapshot(copy, directory=self.work_root)
                handle = self._stack.enter_context(os.fdopen(fd, 'rb'))
                values = np.memmap(handle, dtype='<u4', mode='r')
                self._arrays[name] = values
                self._stack.callback(values._mmap.close)
            for role in ('physical', 'land'):
                rows, runs = (self._arrays[role + '_' + kind] for kind in ('rows', 'runs'))
                if (len(rows) != self.height + 1 or len(runs) % 2 or int(rows[0]) != 0
                        or int(rows[-1]) != len(runs) // 2 or np.any(rows[1:] <= rows[:-1])):
                    raise ValueError(f'invalid shared {role} RLE offsets')
            self.shore_index = CoastalShoreIndex(
                (self._arrays['physical_rows'], self._arrays['physical_runs']),
                (self._arrays['land_rows'], self._arrays['land_runs']), self.width, self.height)
            for values in (self.shore_index.offsets, self.shore_index.starts,
                           self.shore_index.ends, self.shore_index.codes):
                values.flags.writeable = False
            self._state = 'active'
            return self
        except BaseException:
            self._state = 'closed'; self._stack.close()
            raise

    def grid(self, role, rows_path, rows_sha, runs_path, runs_sha, width, height):
        if self._state != 'active':
            raise RuntimeError('shared water inputs are not active')
        if role not in ('physical', 'land') or (width, height) != (self.width, self.height):
            raise ValueError('shared grid role or dimensions mismatch')
        for kind, path, pin in (('rows', rows_path, rows_sha), ('runs', runs_path, runs_sha)):
            name = role + '_' + kind
            if input_path(path) != self.paths[name] or pin != self.pins[name]:
                raise ValueError('shared grid path or SHA-256 pin mismatch')
        return self._arrays[role + '_rows'], self._arrays[role + '_runs']

    def __exit__(self, error_type, error, traceback):
        try:
            if error_type is None:
                for name in NAMES:
                    visit_pinned(self.paths[name], self.pins[name])
                if any(hashlib.sha256(path.read_bytes()).hexdigest() != self._code_pins[key]
                       for key,path in self._sources.items()):
                    raise ValueError('shared water input helper changed')
        finally:
            self._state = 'closed'; self.shore_index = None
            self._stack.close(); self._arrays.clear()
