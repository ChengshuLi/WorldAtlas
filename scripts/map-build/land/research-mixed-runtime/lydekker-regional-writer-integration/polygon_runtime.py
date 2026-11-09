"""Pinned equivalent polygon queries over one authenticated stream generation.

Reviewed source extraction, rasterization, containment and Bering policy remain
unchanged. Immutable mapped run views avoid repeated decoding; each queried row's
physical/component coverage is checked once. Exact integer boundary arithmetic
uses the original coordinate values, never rounded geometry or cell patches.
"""
import hashlib
import math
import os
from pathlib import Path
import struct
from types import FunctionType, SimpleNamespace
import weakref

import numpy as np
from fractions import Fraction


def need(ok, message):
    if not ok:
        raise ValueError(message)


def bind(function, **dependencies):
    result = FunctionType(function.__code__, {**function.__globals__, **dependencies},
                          function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


def facade(module, **dependencies):
    return SimpleNamespace(**{**vars(module), **dependencies})


def _ceil(n, d):
    return -((-n)//d)


def reject_boundary_centers(geometry, grid, max_visits=5000000):
    """Solve exact segment/center incidence with integer congruences.

    Fraction in the reviewed algorithm denotes each supplied binary64 coordinate
    exactly. as_integer_ratio gives that same value. One conversion per vertex
    and a common integer denominator per edge avoid repeated Fraction arithmetic.
    """
    step = Fraction(str(grid['step']))
    w, h = grid['width'], grid['height']
    need(type(w) is int and type(h) is int and w > 0 and h > 0 and
         Fraction(str(grid['west'])) == -180 and Fraction(str(grid['north'])) == 90 and
         step == Fraction(360, w) and Fraction(float(step)) == step and h*step <= 180,
         'unsupported non-dyadic global grid')
    sn, sd = step.numerator, step.denominator

    def pixel(point):
        values = []
        for value, origin, sign in ((point[0], 180, 1), (point[1], 90, -1)):
            n, d = value.as_integer_ratio() if hasattr(value, 'as_integer_ratio') else Fraction(value).as_integer_ratio()
            numerator, denominator = 2*(sign*n + origin*d)*sd - sn*d, 2*d*sn
            g = math.gcd(numerator, denominator)
            values.extend((numerator//g, denominator//g))
        return values

    visits = 0
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    for polygon in polygons:
        for ring in polygon:
            if len(ring) < 2:
                continue
            previous = pixel(ring[0])
            for point in ring[1:]:
                current = pixel(point)
                d = math.lcm(previous[1], previous[3], current[1], current[3])
                x0, y0 = previous[0]*(d//previous[1]), previous[2]*(d//previous[3])
                x1, y1 = current[0]*(d//current[1]), current[2]*(d//current[3])
                previous = current
                if y0 == y1:
                    if y0 % d == 0 and 0 <= y0//d < h and max(0, _ceil(min(x0, x1), d)) <= min(w-1, max(x0, x1)//d):
                        raise ValueError('polygon boundary crosses grid cell center')
                    continue
                lo, hi = max(0, _ceil(min(y0, y1), d)), min(h-1, max(y0, y1)//d)
                visits += max(0, hi-lo+1)
                need(visits <= max_visits, 'boundary visit limit exceeded')
                if lo > hi:
                    continue
                dx, dy = x1-x0, y1-y0
                a, b, denominator = dx*d, x0*dy-dx*y0, d*dy
                if denominator < 0:
                    a, b, denominator = -a, -b, -denominator
                if a > 0:
                    lo, hi = max(lo, _ceil(-b, a)), min(hi, (denominator*w-1-b)//a)
                elif a < 0:
                    lo, hi = max(lo, _ceil(b-(denominator*w-1), -a)), min(hi, b//(-a))
                elif not 0 <= b < denominator*w:
                    continue
                if lo > hi:
                    continue
                g = math.gcd(a, denominator)
                if b % g:
                    continue
                period = denominator//g
                residue = (-b//g*pow(a//g, -1, period)) % period
                hit = residue + _ceil(lo-residue, period)*period
                need(hit > hi, 'polygon boundary crosses grid cell center')
    return visits


def _identity(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


class Row:
    __slots__ = ('index', 'kind', 'y', 'data')

    def __init__(self, index, kind, y, data):
        self.index, self.kind, self.y, self.data = index, kind, y, data

    def __iter__(self):
        return struct.iter_unpack('<III' if self.kind == 'component' else '<II', self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, item):
        return tuple(int(value) for value in self.data[item])


class CoverageRows:
    """Run-scoped views; the caller still rehashes the complete inputs at exit."""
    def __init__(self, inputs, grid, reviewed):
        self.inputs, self.grid, self.reviewed = {name: dict(spec) for name, spec in inputs.items()}, dict(grid), reviewed
        self.w, self.h = grid['width'], grid['height']
        self.paths = {name: Path(spec['path']).resolve(strict=True) for name, spec in inputs.items()}
        self.identities = {name: _identity(path.stat()) for name, path in self.paths.items()}
        self.known_handles = weakref.WeakKeyDictionary()
        self.validated = np.zeros(self.h, dtype=bool)
        self.offsets, self.runs = {}, {}
        for kind, columns in (('physical', 2), ('component', 3)):
            row_path, run_path = self.paths[kind+'_rows'], self.paths[kind+'_runs']
            need(row_path.stat().st_size >= (self.h+1)*4, 'truncated row index')
            need(run_path.stat().st_size % (columns*4) == 0, 'truncated row')
            self.offsets[kind] = np.memmap(row_path, mode='r', dtype='<u4', shape=(self.h+1,))
            count = run_path.stat().st_size//(columns*4)
            self.runs[kind] = (np.memmap(run_path, mode='r', dtype='<u4', shape=(count, columns))
                               if count else np.empty((0, columns), dtype=np.uint32))
        self._totals = None
        self.verify()

    def check(self):
        need(all(_identity(path.stat()) == self.identities[name] for name, path in self.paths.items()),
             'polygon coverage streams changed')

    def verify(self):
        self.check()
        need(all(_sha(path) == self.inputs[name]['sha256'] for name, path in self.paths.items()),
             'polygon coverage stream pin mismatch')
        self.check()

    def _known(self, stream, name):
        if stream not in self.known_handles:
            if not isinstance(getattr(stream, 'name', None), (str, bytes, os.PathLike)) or Path(stream.name).resolve() != self.paths[name]:
                return False
            need(_identity(os.fstat(stream.fileno())) == self.identities[name], 'polygon coverage streams changed')
            self.known_handles[stream] = name
        return self.known_handles[stream] == name

    def readrow(self, rows, runs, y, width, kind):
        if width != self.w or kind not in self.offsets or not (self._known(rows, kind+'_rows') and self._known(runs, kind+'_runs')):
            return self.reviewed.readrow(rows, runs, y, width, kind)
        need(0 <= y < self.h, 'truncated row index')
        a, z = map(int, self.offsets[kind][y:y+2])
        need(a <= z and z-a <= width, 'invalid row index')
        need(z <= len(self.runs[kind]), 'truncated row')
        return Row(self, kind, y, self.runs[kind][a:z])

    def equal_coverage(self, physical, components, width):
        if not (isinstance(physical, Row) and isinstance(components, Row) and
                physical.index is components.index is self and physical.kind == 'physical' and
                components.kind == 'component' and physical.y == components.y and width == self.w):
            return self.reviewed.equal_coverage(physical, components, width)
        if self.validated[physical.y]:
            return
        p, c = physical.data, components.data
        ends, codes = p.T
        need(len(ends) > 0, 'incomplete physical row')
        starts = np.r_[np.uint32(0), ends[:-1]]
        need(bool(np.all(starts < ends) and np.all(ends <= width) and np.all((codes == 1) | (codes == 17))), 'invalid physical row')
        need(len(ends) > 0 and ends[-1] == width, 'incomplete physical row')
        lo, hi, roots = c.T
        need(bool(np.all(lo < hi) and np.all(hi <= width) and np.all(roots < 0xffffffff) and
                  np.all(hi[:-1] <= lo[1:])), 'invalid component row')
        land = codes == 17
        p_lo, p_hi = starts[land], ends[land]
        def union(a, b):
            if not len(a):
                return a, b
            return a[np.r_[True, a[1:] != b[:-1]]], b[np.r_[b[:-1] != a[1:], True]]
        p_lo, p_hi = union(p_lo, p_hi)
        c_lo, c_hi = union(lo, hi)
        need(np.array_equal(p_lo, c_lo) and np.array_equal(p_hi, c_hi), 'component/physical mismatch')
        self.validated[physical.y] = True

    def totals(self):
        self.check()
        if self._totals is None:
            with self.paths['physical_rows'].open('rb') as pr, self.paths['physical_runs'].open('rb') as pv, self.paths['component_rows'].open('rb') as cr, self.paths['component_runs'].open('rb') as cv:
                for y in range(self.h):
                    self.equal_coverage(self.readrow(pr, pv, y, self.w, 'physical'),
                                        self.readrow(cr, cv, y, self.w, 'component'), self.w)
            # Only indexed records belong to the grid; do not count trailing bytes.
            start, end = int(self.offsets['component'][0]), int(self.offsets['component'][-1])
            runs = self.runs['component'][start:end]
            roots, inverse = np.unique(runs[:, 2], return_inverse=True)
            # Every population is <= width*height <= 10**12, exactly represented
            # by float64, including all intermediate bincount sums.
            totals = np.bincount(inverse, weights=runs[:, 1].astype(np.int64)-runs[:, 0]).astype(np.uint64)
            self._totals = {int(root): int(total) for root, total in zip(roots, totals)}
        self.check()
        return self._totals


def prepare(modules, inputs, grid):
    """Return private function bindings; do not replace process-global modules."""
    pi, cp = modules['polygon_intersection'], modules['full_coverage_policy']
    index = CoverageRows(inputs, grid, pi)
    query = {'readrow': index.readrow, 'equal_coverage': index.equal_coverage,
             'reject_boundary_centers': reject_boundary_centers}
    def intersection_module(module):
        witness = bind(module.witness_root, **query)
        return facade(module, **query, witness_root=witness,
                      intersect=bind(module.intersect, **query, witness_root=witness))
    polygon, bering = intersection_module(pi), intersection_module(modules['bering_intersection'])
    def build_coverage_index(request_grid, *paths):
        need(request_grid == grid and tuple(Path(path).resolve() for path in paths) == tuple(index.paths[name] for name in ('physical_rows','physical_runs','component_rows','component_runs')),
             'coverage index generation mismatch')
        key = cp._stream_key(request_grid, paths)
        result = cp.CoverageIndex(key, index.totals(), cp._COVERAGE_INDEX_TOKEN)
        need(key == cp._stream_key(request_grid, paths), 'coverage streams changed during indexing')
        return result
    coverage = facade(cp, build_coverage_index=build_coverage_index)
    resolver = bind(modules['polygon_resolution'].resolve, polygon_intersection=polygon, full_coverage_policy=coverage)
    profile = bind(modules['bering_profiler'].profile, **query)
    return {'resolve': resolver, 'intersect': polygon.intersect, 'profile': profile, 'reader': bering, 'verify': index.verify,
            'provenance': {'schema': 'polygon-equivalent-runtime-v1', 'numpy_version': np.__version__,
                           'substitutions': ['immutable-mapped-row-views', 'validated-row-coverage-reuse',
                                             'exact-integer-boundary-congruences', 'vectorized-root-populations'],
                           'geographic_policy_changed': False, 'rasterization_changed': False}}
