"""Exact immutable canonical-grid reads and explicitly scoped shape diagnostics."""
import bisect
import collections
import gzip
import io
import math

import numpy as np
from shapely.geometry import Point, shape
from shapely.ops import transform

from evidence.immutable import MAX_FILE_BYTES, sha256

VERSION = 'worldatlas-geographic-grid-diagnostics-v1'
MERCATOR_LIMIT = 85.05112878


def project(lon, lat, size):
    if not all(math.isfinite(v) for v in (lon, lat)):
        raise ValueError('Finite longitude/latitude required')
    s = math.sin(math.radians(max(-MERCATOR_LIMIT, min(MERCATOR_LIMIT, lat))))
    return ((lon + 180) / 360 * size,
            (.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * size)


def cell_centre(x, y, size):
    return ((x + .5) / size * 360 - 180,
            math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + .5) / size)))))


def projected_polygon(g, size):
    """Project source vertices, then connect them as the app does; no densification."""
    def coordinates(x, y, z=None):
        if hasattr(x, '__iter__'):
            pairs = [project(a, b, size) for a, b in zip(x, y)]
            return tuple(a for a, b in pairs), tuple(b for a, b in pairs)
        return project(x, y, size)
    return transform(coordinates, g)


class CanonicalGrid:
    """Whole-file pins, full row/run accounting and bounded decoded-part cache."""
    def __init__(self, source, manifest, root='data/canonical-grid', cache_parts=8, max_owner_id=2 ** 32 - 1):
        self.source, self.manifest, self.root = source, manifest, root
        self.size, self.bits = manifest['size'], manifest['coordinateBits']
        if (manifest.get('version') != 2 or type(self.size) is not int
                or not 2 <= self.size <= MAX_FILE_BYTES // 8
                or self.bits != math.ceil(math.log2(self.size))):
            raise ValueError('Unsupported canonical size/packing')
        self.mask = 2 ** self.bits - 1
        if type(max_owner_id) is not int or not 1 <= max_owner_id <= 2 ** 32 - 1:
            raise ValueError('Finite native owner inventory required')
        if (not 1 <= cache_parts <= 16 or any(p['kind'] not in ('rows', 'runs') for p in manifest['parts'])
                or len({p['path'] for p in manifest['parts']}) != len(manifest['parts'])):
            raise ValueError('Unknown/duplicate partitions or unbounded cache')
        self.cache, self.cache_parts = collections.OrderedDict(), cache_parts
        self.verified = set()
        self.parts = {}
        for kind, total in (('rows', self.size * 2), ('runs', manifest['runWords'])):
            parts = sorted((p for p in manifest['parts'] if p['kind'] == kind),
                           key=lambda p: p['offset'])
            cursor = 0
            for p in parts:
                if (type(p['words']) is not int or p['words'] <= 0 or p['words'] % 2
                        or type(p['offset']) is not int or p['offset'] != cursor or p['encoding'] != 'byte-shuffle'
                        or p['words'] * 4 > MAX_FILE_BYTES):
                    raise ValueError('Incomplete/oversized immutable grid partition')
                cursor += p['words']
            if not parts or cursor != total:
                raise ValueError('Grid partition coverage differs from declared total')
            self.parts[kind] = parts
        self.offsets = [p['offset'] for p in self.parts['runs']]
        self.rows = np.empty(self.size * 2, dtype=np.uint32)
        for p in self.parts['rows']:
            self.rows[p['offset']:p['offset'] + p['words']] = self._words(p)
        starts = self.rows[::2].astype(np.uint64)
        counts = self.rows[1::2].astype(np.uint64)
        if (starts[0] != 0 or np.any(starts[1:] != starts[:-1] + counts[:-1])
                or starts[-1] + counts[-1] != manifest['runWords'] // 2):
            raise ValueError('Rows do not account for every declared run exactly once')
        # Verify every original part, including partitions not reached by samples.
        previous_end = None
        for p in self.parts['runs']:
            words = self._words(p)
            a, b = words[::2], words[1::2]
            start, end = a & self.mask, (b & self.mask) + 1
            ids = ((a.astype(np.uint64) >> self.bits)
                   + (b.astype(np.uint64) >> self.bits) * 2 ** (32 - self.bits))
            if np.any((end <= start) | (end > self.size) | (ids == 0) | (ids > max_owner_id)):
                raise ValueError('Invalid native packed run')
            first_run = p['offset'] // 2
            comparisons = np.ones(max(0, len(start) - 1), dtype=bool)
            lo = np.searchsorted(starts, first_run + 1)
            hi = np.searchsorted(starts, first_run + len(start))
            comparisons[(starts[lo:hi] - first_run - 1).astype(np.int64)] = False
            if np.any((start[1:] < end[:-1]) & comparisons):
                raise ValueError('Overlapping/unsorted runs within a native row')
            at = np.searchsorted(starts, first_run)
            is_row_start = at < len(starts) and starts[at] == first_run
            if previous_end is not None and not is_row_start and start[0] < previous_end:
                raise ValueError('Cross-partition native row overlap')
            previous_end = int(end[-1])

    def _words(self, p):
        name = self.root + '/' + p['path']
        if name in self.cache:
            self.cache.move_to_end(name)
            return self.cache[name]
        if name not in self.source.pins:
            raise ValueError('Grid part lacks a declared ordinary whole-file pin')
        encoded = self.source.read(name)
        if len(encoded) != p['compressed_bytes'] or sha256(encoded) != p['sha256']:
            raise ValueError('Encoded native grid hash/size mismatch')
        with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) != p['words'] * 4:
            raise ValueError('Decoded native word count mismatch')
        planes = np.frombuffer(raw, dtype=np.uint8).reshape(4, p['words'])
        words = (planes[0].astype(np.uint32) + (planes[1].astype(np.uint32) << 8)
                 + (planes[2].astype(np.uint32) << 16)
                 + (planes[3].astype(np.uint32) << 24))
        if sha256(words.astype('<u4').tobytes()) != p['decoded_sha256']:
            raise ValueError('Decoded native word hash mismatch')
        self.verified.add(name)
        self.cache[name] = words
        if len(self.cache) > self.cache_parts:
            self.cache.popitem(last=False)
        return words

    def _word(self, index):
        p = self.parts['runs'][bisect.bisect_right(self.offsets, index) - 1]
        if not p['offset'] <= index < p['offset'] + p['words']:
            raise ValueError('Word outside declared partition')
        return int(self._words(p)[index - p['offset']])

    def run(self, index):
        a, b = self._word(index * 2), self._word(index * 2 + 1)
        return a & self.mask, (b & self.mask) + 1, (a >> self.bits) + (b >> self.bits) * 2 ** (32 - self.bits)

    def pick(self, x, y):
        x, y = math.floor(x), math.floor(y)
        if x < 0 or y < 0 or x >= self.size or y >= self.size:
            return 0
        lo = int(self.rows[y * 2])
        stop = hi = lo + int(self.rows[y * 2 + 1])
        while lo < hi:
            mid = (lo + hi) // 2
            if self.run(mid)[1] <= x:
                lo = mid + 1
            else:
                hi = mid
        if lo == stop:
            return 0
        start, end, identity = self.run(lo)
        return identity if start <= x else 0


def component_sample(feature, grid):
    g = shape(feature['geometry'])
    if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Unchanged valid component polygon required')
    point = g.representative_point()
    if not g.contains(point):
        return {'component_id': feature['id'], 'representative_lonlat': [point.x, point.y],
                'cell': None, 'cell_centre_lonlat': None, 'cell_centre_strictly_inside': False,
                'owner_integer': None, 'status': 'unknown-no-strict-representative-point',
                'sample_scope': 'No strictly interior floating-point sample; original geometry retained',
                'administrative_assignment': None}
    px, py = project(point.x, point.y, grid.size)
    x, y = math.floor(px), math.floor(py)
    if not (0 <= x < grid.size and 0 <= y < grid.size):
        raise ValueError('Retained component sample outside canonical domain')
    centre = cell_centre(x, y, grid.size)
    inside, owner = g.contains(Point(*centre)), grid.pick(x, y)
    status = (('centre-in-gap-unassigned' if owner == 0 else 'centre-in-gap-owned-discrepancy')
              if inside else ('representative-cell-centre-outside-gap-unassigned' if owner == 0
                              else 'representative-cell-centre-outside-gap-owned'))
    return {'component_id': feature['id'], 'representative_lonlat': [point.x, point.y],
            'cell': [x, y], 'cell_centre_lonlat': list(centre),
            'cell_centre_strictly_inside': inside, 'owner_integer': owner, 'status': status,
            'sample_scope': 'one representative native cell; other cells remain unchecked',
            'administrative_assignment': None}


def owner_shape_check(sample, owner_feature, size):
    g = shape(owner_feature['geometry'])
    if not g.is_valid or g.is_empty:
        raise ValueError('Invalid current owner footprint; never MakeValid')
    native = g.contains(Point(*sample['cell_centre_lonlat']))
    x, y = sample['cell']
    pg = projected_polygon(g, size)
    pixel_point = Point(x + .5, y + .5)
    projected = pg.contains(pixel_point)
    boundary = pg.boundary.covers(pixel_point)
    interpretation = ('projection-interpolation-explains-owned-cell' if projected and not native
                      else 'grid-unassigned-but-current-shape-covers-centre' if native and projected
                      and sample['owner_integer'] == 0
                      else 'native-owner-shape-covers-centre' if native and projected
                      else 'projection-interpolation-explains-unassigned-cell' if native and not projected
                      and sample['owner_integer'] == 0 and not boundary
                      else 'grid-edge-tie-rule-review-required' if boundary
                      else 'unresolved-grid-shape-discrepancy')
    return {'owner_location_id': owner_feature['id'],
            'native_lonlat_straight_edges_contain_centre': native,
            'app_projected_straight_edges_contain_centre': projected,
            'projected_boundary_contact': boundary,
            'interpretation': interpretation}
