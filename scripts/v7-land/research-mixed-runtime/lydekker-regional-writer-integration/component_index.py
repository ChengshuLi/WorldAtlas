"""Run-scoped, authenticated component queries without repeated global scans.

The reviewed component_scan implementation remains unchanged. This index checks
the same complete stream and supplies identical integer counts, root order and
whole-component runs. Inputs are authenticated at construction and verification;
every query also rejects a changed file identity. No geographic policy is added.
"""
from bisect import bisect_left, bisect_right
import math
import numpy as np

from component_scan import _pin, _offsets, sha256_file
from regional_rule import BOUNDARY_EPSILON_DEGREES, _require


def identity(path):
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


class ComponentIndex:
    def __init__(self, row_spec, run_spec, grid):
        _require(isinstance(grid, dict) and set(grid) == {'width', 'height', 'west', 'north', 'step'}, 'invalid grid')
        w, h, west, north, step = (grid[x] for x in ('width', 'height', 'west', 'north', 'step'))
        _require(type(w) is int and type(h) is int and 1 < w <= 1000000 and 0 < h <= 1000000 and
                 type(step) in (int, float) and math.isfinite(step) and step > 0 and
                 type(west) in (int, float) and type(north) in (int, float) and
                 math.isfinite(west) and math.isfinite(north) and west >= -180 and north <= 90 and
                 west + w*step <= 180 + 1e-8 and north - h*step >= -90 - 1e-8, 'invalid grid bounds')
        self.row_spec, self.run_spec, self.grid = dict(row_spec), dict(run_spec), dict(grid)
        self.row_path, self.run_path = _pin(row_spec), _pin(run_spec)
        offsets = _offsets(self.row_path, self.run_path, h)
        self.offsets = np.asarray(offsets, dtype=np.uint32)
        count = int(offsets[-1])
        self.runs = (np.memmap(self.run_path, mode='r', dtype='<u4', shape=(count, 3))
                     if count else np.empty((0, 3), dtype=np.uint32))
        lo, hi, roots = self.runs.T
        _require(bool(np.all(lo < hi) and np.all(hi <= w) and np.all(roots < 0xffffffff)), 'invalid component run')
        overlap = hi[:-1] > lo[1:]
        starts = self.offsets[:-1][self.offsets[1:] > self.offsets[:-1]]
        starts = starts[starts > 0]
        overlap[starts.astype(np.int64) - 1] = False
        _require(not bool(np.any(overlap)), 'invalid component run')
        self.roots, inverse = np.unique(roots, return_inverse=True)
        # Grid validation bounds every total by 10**12, so float64 integer
        # accumulation is exact (well below 2**53), including every partial sum.
        self.totals = np.bincount(inverse, weights=hi.astype(np.int64) - lo).astype(np.uint64)
        self.identities = identity(self.row_path), identity(self.run_path)
        self._collected = {}
        self.verify()

    def check(self, row_spec, run_spec, grid):
        _require(row_spec == self.row_spec and run_spec == self.run_spec and grid == self.grid,
                 'component index generation mismatch')
        _require((identity(self.row_path), identity(self.run_path)) == self.identities,
                 'component input changed')

    def verify(self):
        _require(sha256_file(self.row_path) == self.row_spec['sha256'] and
                 sha256_file(self.run_path) == self.run_spec['sha256'], 'component input changed')

    def scan(self, row_spec, run_spec, grid, bounds, line):
        self.check(row_spec, run_spec, grid)
        _require(isinstance(bounds, (list, tuple)) and len(bounds) == 4 and
                 all(type(v) in (int, float) and math.isfinite(v) for v in bounds), 'invalid region')
        bw, bs, be, bn = bounds
        _require(-180 <= bw < be <= 180 and -90 <= bs < bn <= 90, 'invalid region bounds')
        w, h, west, north, step = (grid[x] for x in ('width', 'height', 'west', 'north', 'step'))
        xs = range(w)
        lon = lambda x: west + (x + 0.5)*step
        x0, x1 = bisect_left(xs, bw, key=lon), bisect_right(xs, be, key=lon)
        ys = [y for y in range(h) if bs <= north - (y + 0.5)*step <= bn]
        if not ys or x0 == x1:
            return {}
        first, last = ys[0], ys[-1] + 1
        start, end = int(self.offsets[first]), int(self.offsets[last])
        raw = self.runs[start:end]
        lo, hi = np.maximum(raw[:, 0], x0), np.minimum(raw[:, 1], x1)
        selected = np.flatnonzero(lo < hi)
        lo, hi, labels = lo[selected].astype(np.int64), hi[selected].astype(np.int64), raw[selected, 2]
        if not len(selected):
            return {}
        rows = np.searchsorted(self.offsets, selected + start, side='right') - 1
        left, right, outside = np.zeros(h, dtype=np.int64), np.zeros(h, dtype=np.int64), np.zeros(h, dtype=bool)
        for y in ys:
            cut = line.longitude(north - (y + 0.5)*step)
            if cut is None:
                outside[y] = True
            else:
                left[y] = bisect_left(xs, cut - BOUNDARY_EPSILON_DEGREES, key=lon)
                right[y] = bisect_right(xs, cut + BOUNDARY_EPSILON_DEGREES, key=lon)
        unique, first_seen, inverse = np.unique(labels, return_index=True, return_inverse=True)
        sizes = hi - lo
        active = ~outside[rows]
        values = {'in_scope': sizes, 'west': np.where(active, np.maximum(0, np.minimum(hi, left[rows]) - lo), 0),
                  'boundary': np.where(active, np.maximum(0, np.minimum(hi, right[rows]) - np.maximum(lo, left[rows])), 0),
                  'east': np.where(active, np.maximum(0, hi - np.maximum(lo, right[rows])), 0),
                  'outside_latitude': np.where(active, 0, sizes)}
        counts = {key: np.bincount(inverse, weights=value).astype(np.uint64) for key, value in values.items()}
        totals = self.totals[np.searchsorted(self.roots, unique)]
        records = {int(unique[i]): {'total': int(totals[i]), **{key: int(value[i]) for key, value in counts.items()}}
                   for i in np.argsort(first_seen)}
        _require(all(r['total'] >= r['in_scope'] > 0 and
                     sum(r[k] for k in ('west', 'east', 'boundary', 'outside_latitude')) == r['in_scope']
                     for r in records.values()), 'inconsistent scan')
        self.check(row_spec, run_spec, grid)
        return records

    def collect_runs(self, row_spec, run_spec, grid, expected_counts):
        self.check(row_spec, run_spec, grid)
        _require(isinstance(expected_counts, dict) and all(type(r) is int and type(n) is int and n > 0
                                                          for r, n in expected_counts.items()), 'invalid root request')
        key = tuple(sorted(expected_counts.items()))
        if key in self._collected:
            return self._collected[key]
        result = {root: [] for root in expected_counts}
        indices = np.flatnonzero(np.isin(self.runs[:, 2], list(expected_counts)))
        rows = np.searchsorted(self.offsets, indices, side='right') - 1
        for y, (lo, hi, root) in zip(rows.tolist(), self.runs[indices].tolist()):
            result[root].append((y, lo, hi))
        _require(all(sum(hi - lo for _, lo, hi in result[r]) == n for r, n in expected_counts.items()),
                 'incomplete root runs')
        self.check(row_spec, run_spec, grid)
        self._collected[key] = result
        return result

    def component_at(self, row_spec, run_spec, grid, lon, lat):
        self.check(row_spec, run_spec, grid)
        _require(all(type(v) in (int, float) and math.isfinite(v) for v in (lon, lat)), 'invalid witness')
        w, h, west, north, step = (grid[x] for x in ('width', 'height', 'west', 'north', 'step'))
        x, y = math.floor((lon - west)/step), math.floor((north - lat)/step)
        _require(0 <= x < w and 0 <= y < h, 'witness outside grid')
        runs = self.runs[int(self.offsets[y]):int(self.offsets[y + 1])]
        index = int(np.searchsorted(runs[:, 0], x, side='right')) - 1
        _require(index >= 0 and x < runs[index, 1], 'witness does not resolve to exactly one physical component')
        return int(runs[index, 2])
