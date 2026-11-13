"""Index complete seed runs and select real sample cells for distance bounds."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from map_build.core.rle import open_grid, row
from map_build.core.layers import file_hash


def build_seed_index(grid, seeds, directory, *, tile_cells=1024, samples_per_category=32):
    """Write complete spatial tiles; sampled cells provide upper bounds only."""
    if (
        type(tile_cells) is not int
        or tile_cells <= 0
        or type(samples_per_category) is not int
        or samples_per_category <= 0
    ):
        raise ValueError('seed index needs positive tile and sample sizes')
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir()
    tiles, representatives = [], []
    with open_grid(seeds, grid) as source:
        for first in range(0, grid.height, tile_cells):
            buffers = defaultdict(list)
            for y in range(first, min(grid.height, first + tile_cells)):
                ends, codes = row(source, y, grid.width)
                left = 0
                for right, code in zip(map(int, ends), map(int, codes)):
                    if code:
                        a = left
                        while a < right:
                            tx = a // tile_cells
                            b = min(right, (tx + 1) * tile_cells)
                            buffers[tx].append((y, a, b, code))
                            a = b
                    left = right
            ty = first // tile_cells
            for tx, records in sorted(buffers.items()):
                values = np.asarray(records, dtype='<u4')
                data = values.tobytes()
                (directory / f'{ty:05d}-{tx:05d}.bin').write_bytes(data)
                codes = sorted(set(map(int, values[:, 3])))
                tiles.append((ty, tx, codes, len(records), hashlib.sha256(data).hexdigest()))
                for code in codes:
                    selected = np.flatnonzero(values[:, 3] == code)
                    picked = selected[
                        np.unique(
                            np.linspace(
                                0,
                                len(selected) - 1,
                                min(samples_per_category, len(selected)),
                                dtype=int,
                            )
                        )
                    ]
                    for y, a, b, _ in values[picked]:
                        representatives.append((int(y), (int(a) + int(b) - 1) // 2, code))
    if not tiles:
        raise ValueError('cannot index an empty mainland seed')
    np.asarray(representatives, dtype='<u4').tofile(directory / 'representatives.u32le')
    result = dict(
        grid=vars(grid),
        tile_cells=tile_cells,
        tiles=tiles,
        representatives=len(representatives),
        representatives_sha256=file_hash(directory / 'representatives.u32le'),
        processing_seconds=time.monotonic() - started,
    )
    (directory / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
