"""Independent row scans for checking streamed enclosed-water calculations."""

from collections import Counter, defaultdict

import numpy as np
from map_build.water import shared_nearest as shore


def validate_spans(by_row, width, height):
    components = defaultdict(list)
    for y, spans in sorted(by_row.items()):
        if type(y) is not int or not 0 <= y < height:
            raise ValueError('component row out of bounds')
        prev = 0
        for a, b, root in spans:
            if (
                any(type(v) is not int for v in (a, b, root))
                or not (0 <= a < b <= width)
                or a < prev
            ):
                raise ValueError('invalid or overlapping component span')
            components[root].append((y, a, b))
            prev = b
    return components


def adjacency(by_row, physical, prefill, width, height, pairs):
    """Count boundary codes and unknown external-zero edges independently."""
    components = validate_spans(by_row, width, height)
    results = {
        r: {'codes': Counter(), 'unknown_zero_edges': 0, 'crop_edge': False} for r in components
    }
    water_to_entity = {w: e for e, _, w in pairs}
    land_to_entity = {l: e for e, l, _ in pairs}
    arrays = {}
    row_index = {
        y: (
            np.asarray([v[0] for v in spans], dtype=np.int64),
            np.asarray([v[1] for v in spans], dtype=np.int64),
            np.asarray([v[2] for v in spans], dtype=np.int64),
        )
        for y, spans in by_row.items()
    }

    def row(y):
        if y not in arrays:
            p = shore.crop(*physical, y, 0, width, width)
            q = shore.crop(*prefill, y, 0, width, width)
            if (
                np.any(~np.isin(p, [1, 17]))
                or np.any((p == 17) & ~np.isin(q, list(land_to_entity)))
                or np.any((p == 1) & ~np.isin(q, [0, *water_to_entity]))
            ):
                raise ValueError(f'invalid physical/prefill relation at row {y}')
            arrays[y] = (p, q)
        return arrays[y]

    def owners(y, x):
        data = row_index.get(y)
        if data is None:
            return np.full(len(x), -1, dtype=np.int64)
        starts, ends, ids = data
        ix = np.searchsorted(starts, x, side='right') - 1
        found = (ix >= 0) & (x < ends[np.maximum(ix, 0)])
        return np.where(found, ids[np.maximum(ix, 0)], -1)

    for y, spans in sorted(by_row.items()):
        arrays.clear()
        p, q = row(y)
        for a, b, root in spans:
            if np.any(p[a:b] != 1) or np.any(q[a:b] != 0):
                raise ValueError('component does not consist solely of residual physical water')
            if y == 0 or y == height - 1:
                results[root]['crop_edge'] = True
            xs = np.arange(a, b, dtype=np.int64)
            for ny, nx in ((y, (xs - 1) % width), (y, (xs + 1) % width), (y - 1, xs), (y + 1, xs)):
                if ny < 0 or ny >= height:
                    continue
                own = owners(ny, nx)
                external = own != root
                if not np.any(external):
                    continue
                v = row(ny)[1][nx[external]]
                results[root]['unknown_zero_edges'] += int(np.count_nonzero(v == 0))
                for code, n in zip(*np.unique(v[v != 0], return_counts=True)):
                    code = int(code)
                    entity = water_to_entity.get(code, land_to_entity.get(code))
                    if entity is None:
                        raise ValueError('boundary contains unsupported code')
                    results[root]['codes'][entity] += int(n)
    return components, results


def component_method(summary, cut_edges):
    if type(cut_edges) is not int or cut_edges < 0:
        raise ValueError('invalid source cut count')
    if cut_edges:
        return 'pending-source-cut-contact'
    if summary['crop_edge']:
        return 'pending-grid-crop-edge'
    if summary['unknown_zero_edges']:
        return 'pending-unknown-zero-boundary'
    count = len(summary['codes'])
    return (
        'pending-no-boundary-continent'
        if count == 0
        else ('direct-single-boundary-continent' if count == 1 else 'nearest-participant-shore')
    )


def cut_contacts(by_row, records, width, height):
    """Conservatively count every source cut incident to an unseeded cell.

    This includes internal cuts whose two sides reconnect into the same root;
    the upstream partition summary omits those. No full-grid expansion is used.
    """
    from bisect import bisect_right

    indexed = {y: ([a for a, _, _ in spans], spans) for y, spans in by_row.items()}

    def owner(y, x):
        data = indexed.get(y)
        if data is None:
            return None
        starts, spans = data
        i = bisect_right(starts, x) - 1
        return spans[i][2] if i >= 0 and x < spans[i][1] else None

    counts = Counter()
    prev = None
    for record in records:
        if (
            not isinstance(record, tuple)
            or len(record) != 3
            or any(type(v) is not int for v in record)
        ):
            raise ValueError('invalid cut edge')
        kind, y, x = record
        if prev is not None and record <= prev:
            raise ValueError('cut edges must be unique and sorted')
        prev = record
        if kind == 0 and 0 <= y < height and 0 <= x < width - 1:
            endpoints = ((y, x), (y, x + 1))
        elif kind == 1 and 0 <= y < height - 1 and 0 <= x < width:
            endpoints = ((y, x), (y + 1, x))
        elif kind == 2 and 0 <= y < height and x == 0:
            endpoints = ((y, width - 1), (y, 0))
        else:
            raise ValueError('cut edge outside grid')
        for root in {owner(*point) for point in endpoints} - {None}:
            counts[root] += 1
    return counts
