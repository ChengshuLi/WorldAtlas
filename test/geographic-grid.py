import math
import pathlib
import sys
import unittest

import numpy as np
from shapely.geometry import box, mapping, Polygon, MultiPolygon, Point

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import deterministic_gzip, sha256
from geographic_grid import CanonicalGrid, project, cell_centre, component_sample, owner_shape_check


class Source:
    def __init__(self):
        self.pins, self.blobs = {}, {}
    def read(self, path):
        return self.blobs[path]


def fixture(rows=None, split=False):
    rows = rows or [[], [], [], [(0, 2, 1), (4, 6, 2)], [], [], [], []]
    source = Source()
    table, words, at = [], [], 0
    for row in rows:
        table.extend([at, len(row)])
        for start, end, identity in row:
            words.extend([identity * 8 + start, end - 1])
        at += len(row)
    parts = []
    def add(kind, offset, values):
        raw = np.asarray(values, dtype='<u4').tobytes()
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 4).T.copy().tobytes()
        encoded = deterministic_gzip(a)
        name = f'{kind}-{offset}.bin.gz'
        source.blobs['data/canonical-grid/' + name] = encoded
        source.pins['data/canonical-grid/' + name] = {}
        parts.append({'kind': kind, 'offset': offset, 'words': len(values), 'path': name,
                      'encoding': 'byte-shuffle', 'sha256': sha256(encoded),
                      'decoded_sha256': sha256(raw), 'compressed_bytes': len(encoded)})
    add('rows', 0, table)
    if split:
        for offset in range(0, len(words), 2):
            add('runs', offset, words[offset:offset + 2])
    else:
        add('runs', 0, words)
    return source, {'version': 2, 'size': 8, 'coordinateBits': 3,
                    'runWords': len(words), 'parts': parts}


def feature(g, identity='gap:fixture'):
    return {'type': 'Feature', 'id': identity, 'geometry': mapping(g), 'properties': {}}


class GridTests(unittest.TestCase):
    def test_real_compact_layout_and_half_open_runs(self):
        s, m = fixture();g = CanonicalGrid(s, m)
        self.assertEqual([g.pick(x, 3) for x in range(8)], [1, 1, 0, 0, 2, 2, 0, 0])
        self.assertEqual(g.pick(1.99, 3.99), 1)
        self.assertEqual(g.pick(2, 3), 0)
        self.assertEqual(g.pick(-1, 3), 0)
        self.assertEqual(g.pick(8, 3), 0)
        self.assertEqual(g.pick(1, 2), 0)

    def test_split_native_run_partitions(self):
        s, m = fixture(split=True);g = CanonicalGrid(s, m, cache_parts=1)
        self.assertEqual(g.pick(5, 3), 2)
        self.assertEqual(len(g.verified), 3)
        self.assertLessEqual(len(g.cache), 1)

    def test_actual_grid_width_not_rounded(self):
        x, y = project(63.207727681, 26.8032, 262166)
        self.assertEqual((math.floor(x), math.floor(y)), (177113, 110810))
        self.assertNotEqual(math.floor(project(63.207727681, 26.8032, 262144)[0]), 177113)

    def test_inverse_centre_axes(self):
        lon, lat = cell_centre(126031, 99379, 262166)
        x, y = project(lon, lat, 262166)
        self.assertAlmostEqual(x, 126031.5)
        self.assertAlmostEqual(y, 99379.5)

    def test_original_encoded_hash_failure(self):
        s, m = fixture();s.blobs['data/canonical-grid/runs-0.bin.gz'] += b'x'
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_decoded_hash_failure(self):
        s, m = fixture();m['parts'][1]['decoded_sha256'] = '0' * 64
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_missing_partition(self):
        s, m = fixture();m['parts'].pop()
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_unlisted_original_rejected(self):
        s, m = fixture();s.pins.pop('data/canonical-grid/runs-0.bin.gz')
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_corrupt_row_accounting(self):
        s, m = fixture();m['runWords'] += 2
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_within_row_overlap_rejected(self):
        s, m = fixture([[], [], [], [(0, 5, 1), (4, 6, 2)], [], [], [], []])
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_cross_partition_overlap_rejected(self):
        s, m = fixture([[], [], [], [(0, 5, 1), (4, 6, 2)], [], [], [], []], True)
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_run_start_reset_per_native_row(self):
        s, m = fixture([[(4, 8, 1)], [(0, 2, 2)], [], [], [], [], [], []], True)
        g = CanonicalGrid(s, m)
        self.assertEqual(g.pick(0, 1), 2)

    def test_native_unassigned_component(self):
        s, m = fixture();g = CanonicalGrid(s, m);lon, lat = cell_centre(3, 3, 8)
        r = component_sample(feature(box(lon - 1, lat - 1, lon + 1, lat + 1)), g)
        self.assertEqual(r['status'], 'centre-in-gap-unassigned')
        self.assertIsNone(r['administrative_assignment'])

    def test_subpixel_component_not_silently_discarded(self):
        s, m = fixture();g = CanonicalGrid(s, m);lon, lat = cell_centre(4.15 - .5, 3.15 - .5, 8)
        r = component_sample(feature(box(lon - .01, lat - .01, lon + .01, lat + .01)), g)
        self.assertEqual(r['status'], 'representative-cell-centre-outside-gap-owned')
        self.assertEqual(r['component_id'], 'gap:fixture')

    def test_hole_does_not_receive_representative_sample(self):
        s, m = fixture();g = CanonicalGrid(s, m)
        poly = Polygon([(-20, 0), (20, 0), (20, 40), (-20, 40)],
                       [[(-10, 10), (10, 10), (10, 30), (-10, 30)]])
        r = component_sample(feature(poly), g)
        self.assertTrue(poly.contains(Point(*r['representative_lonlat'])))

    def test_dateline_component_keeps_original_disconnected_positions(self):
        s, m = fixture();g = CanonicalGrid(s, m)
        polygon = MultiPolygon([box(-179.9, 0, -179, 2), box(179, 0, 179.9, 2)])
        r = component_sample(feature(polygon), g)
        self.assertTrue(polygon.contains(Point(*r['representative_lonlat'])))
        self.assertIn(r['cell'][0], (0, 7))
        self.assertIsNone(r['administrative_assignment'])

    def test_source_partition_boolean_offset_rejected(self):
        s, m = fixture();m['parts'][0]['offset'] = False
        with self.assertRaises(ValueError): CanonicalGrid(s, m)

    def test_unmapped_native_owner_rejected_even_if_not_sampled(self):
        s, m = fixture()
        with self.assertRaises(ValueError): CanonicalGrid(s, m, max_owner_id=1)

    def test_true_grid_only_control_is_flagged(self):
        sample = {'cell': [3, 3], 'cell_centre_lonlat': list(cell_centre(3, 3, 8)), 'owner_integer': 0}
        lon, lat = sample['cell_centre_lonlat']
        r = owner_shape_check(sample, feature(box(lon - 5, lat - 5, lon + 5, lat + 5), 'owner'), 8)
        self.assertEqual(r['interpretation'], 'grid-unassigned-but-current-shape-covers-centre')

    def test_invalid_polygon_never_fixed(self):
        s, m = fixture();g = CanonicalGrid(s, m)
        with self.assertRaises(ValueError):
            component_sample(feature(Polygon([(0, 0), (3, 3), (0, 3), (3, 0), (0, 0)])), g)

    def test_nonfinite_coordinates_rejected(self):
        with self.assertRaises(ValueError): project(float('nan'), 3, 8)


if __name__ == '__main__':
    unittest.main()
