"""Compare complete grids and retain the exact locations of changed cells."""

from collections import Counter
import json
from pathlib import Path
import time

import numpy as np

from map_build.core.layers import file_hash
from map_build.core.rle import open_grid, row


def compare(candidate, reference, grid, directory, reference_sha256):
    candidate, reference, directory = map(Path, (candidate, reference, directory))
    names = ('rows.u32le', 'runs.u32le')
    if set(reference_sha256) != set(names):
        raise ValueError('both reference stream checksums are required')
    start = time.monotonic()
    before = {
        label: {name: file_hash(root / name) for name in names}
        for label, root in (('reference', reference), ('candidate', candidate))
    }
    if before['reference'] != reference_sha256:
        raise ValueError('reference stream checksum differs')
    directory.mkdir()
    changed, transitions, offsets = 0, Counter(), [0]
    bounds = None
    with open_grid(candidate, grid) as new, open_grid(reference, grid) as old, (
        directory / 'changes.u32le'
    ).open('xb') as stream:
        for y in range(grid.height):
            a, b = row(old, y, grid.width), row(new, y, grid.width)
            records = []
            if not (np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])):
                ends = np.union1d(a[0], b[0])
                starts = np.r_[np.uint32(0), ends[:-1]]
                av = a[1][np.searchsorted(a[0], starts, side='right')]
                bv = b[1][np.searchsorted(b[0], starts, side='right')]
                for i in np.flatnonzero(av != bv):
                    left, right, prior, after = map(int, (starts[i], ends[i], av[i], bv[i]))
                    count = right - left
                    changed += count
                    transitions[f'{prior}->{after}'] += count
                    records.append((y, left, right, prior, after))
                    if bounds is None:
                        bounds = [left, right, y, y + 1]
                    else:
                        bounds = [min(bounds[0], left), max(bounds[1], right), bounds[2], y + 1]
            np.asarray(records, dtype='<u4').tofile(stream)
            offsets.append(offsets[-1] + len(records))
    np.asarray(offsets, dtype='<u8').tofile(directory / 'change-rows.u64le')
    after = {
        label: {name: file_hash(root / name) for name in names}
        for label, root in (('reference', reference), ('candidate', candidate))
    }
    if after != before:
        raise ValueError('grid input changed during comparison')
    result = {
        'grid': {'width': grid.width, 'height': grid.height, 'step': grid.step},
        'changed_cells': changed,
        'pair_counts': dict(sorted(transitions.items())),
        'changed_bounds': bounds,
        'byte_identical': before['reference'] == before['candidate'],
        'input_sha256': before,
        'elapsed_seconds': time.monotonic() - start,
        'change_record_fields': ['row', 'start', 'end', 'before_code', 'after_code'],
    }
    (directory / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
