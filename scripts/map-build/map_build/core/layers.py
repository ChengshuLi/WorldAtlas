"""Read checksum-verified assignment tiles and write ordinary row-run layers."""

from collections import Counter
import gzip
import hashlib
import heapq
import itertools
import json
from pathlib import Path

import numpy as np


def file_hash(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def tile_rows(path, tile, grid, codes):
    first, last = tile['core_rows']
    left, right = tile['core_cols']
    if not (0 <= first < last <= grid.height and 0 <= left < right <= grid.width):
        raise ValueError('assignment tile escapes the grid')
    info = tile['span_file']
    source = (path.parent / info['path']).resolve(strict=True)
    if file_hash(source) != info['sha256']:
        raise ValueError('assignment file checksum differs')
    opener = gzip.open if source.suffix == '.gz' else open
    previous = first - 1
    with opener(source, 'rt') as stream:
        for line in stream:
            record = json.loads(line)
            y = record['row']
            if type(y) is not int or not first <= y < last or y <= previous:
                raise ValueError('assignment rows must be ordered and unique within a tile')
            previous = y
            spans, stop = [], left
            for item in record['spans']:
                a, b, code = (item[key] for key in ('start', 'end', 'code'))
                if (
                    any(type(v) is not int for v in (a, b, code))
                    or not stop <= a < b <= right
                    or code not in codes
                ):
                    raise ValueError('invalid assignment span or unbound category code')
                spans.append((a, b, code))
                stop = b
            if spans:
                yield y, spans


def layer_rows(path, grid, codes):
    path = Path(path)
    manifest = json.loads(path.read_text())
    if (manifest['grid']['width'], manifest['grid']['height']) != (grid.width, grid.height):
        raise ValueError('assignment layer uses a different grid')
    streams = [tile_rows(path, tile, grid, codes) for tile in manifest['tiles']]
    merged = heapq.merge(*streams, key=lambda item: item[0])
    for y, records in itertools.groupby(merged, key=lambda item: item[0]):
        spans = sorted(span for _, values in records for span in values)
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            raise ValueError('assignment tiles overlap')
        yield y, spans


def write_layer(directory, grid, rows):
    """Write sparse assigned spans as a complete layer, using zero elsewhere."""
    directory = Path(directory)
    directory.mkdir()
    iterator = iter(rows)
    current = next(iterator, None)
    offsets = [0]
    counts = Counter()
    with (directory / 'runs.u32le').open('xb') as output:
        for y in range(grid.height):
            if current is not None and (type(current[0]) is not int or current[0] < y):
                raise ValueError('layer rows must be ordered and unique')
            spans = current[1] if current is not None and current[0] == y else ()
            pairs = []
            stop = 0

            def append(end, code):
                if pairs and pairs[-1][1] == code:
                    pairs[-1] = (end, code)
                else:
                    pairs.append((end, code))

            for a, b, code in spans:
                if (
                    any(type(v) is not int for v in (a, b, code))
                    or not stop <= a < b <= grid.width
                    or not 0 < code < 2**32
                ):
                    raise ValueError('invalid output span')
                if a > stop:
                    append(a, 0)
                append(b, code)
                counts[str(code)] += b - a
                stop = b
            if stop < grid.width:
                append(grid.width, 0)
            np.asarray(pairs, dtype='<u4').tofile(output)
            offsets.append(offsets[-1] + len(pairs))
            if offsets[-1] >= 2**32:
                raise ValueError('run offsets exceed the u32 representation')
            if current is not None and current[0] == y:
                current = next(iterator, None)
        if current is not None:
            raise ValueError('assignment row outside the grid')
    np.asarray(offsets, dtype='<u4').tofile(directory / 'rows.u32le')
    report = {
        'grid': {'width': grid.width, 'height': grid.height, 'step': grid.step},
        'counts': dict(counts),
        'run_count': offsets[-1],
    }
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def patch_rows(values, bounds, grid):
    """Emit a possibly wrapped rectangular assignment without expanding the globe."""
    x0, x1, y0, y1 = bounds
    if values.shape != (y1 - y0, x1 - x0):
        raise ValueError('assignment dimensions differ from its bounds')
    for y, row in enumerate(values, y0):
        spans = []
        for a, b in ((x0, min(x1, grid.width)), (0, max(0, x1 - grid.width))):
            if a == b:
                continue
            offset = (a - x0) % grid.width
            part = row[offset : offset + b - a]
            stops = np.r_[0, np.flatnonzero(part[1:] != part[:-1]) + 1, len(part)]
            for first, last in zip(stops, stops[1:]):
                code = int(part[first])
                if code:
                    spans.append((a + int(first), a + int(last), code))
        if spans:
            yield y, sorted(spans)
