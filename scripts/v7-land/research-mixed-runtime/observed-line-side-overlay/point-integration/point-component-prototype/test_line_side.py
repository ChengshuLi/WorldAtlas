import hashlib
import json
import unittest

import line_side


def observed():
    geometry = {'type': 'MultiLineString', 'coordinates': [
        [[10.0, 4.0], [10.5, 3.0], [11.0, 2.0]],
        [[11.5, 0.0], [12.0, -1.0]]
    ]}
    encoded = json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode()
    return {'line_id': 'fictional-line', 'geometry': geometry,
            'geometry_sha256': hashlib.sha256(encoded).hexdigest()}


class LineSideTest(unittest.TestCase):
    def test_west_and_east(self):
        self.assertEqual(line_side.check(observed(), [9, 3.5], 'west', 10000)['side'], 'west')
        self.assertEqual(line_side.check(observed(), [12, 2.5], 'east', 10000)['side'], 'east')

    def test_shared_vertex_only_once(self):
        self.assertEqual(line_side.check(observed(), [9, 3], 'west', 10000)['side'], 'west')

    def test_gap_and_endpoints_fail_closed(self):
        for p in ([9, 1], [9, 4], [9, -1], [9, 5]):
            with self.subTest(p=p), self.assertRaises(ValueError):
                line_side.check(observed(), p, 'west', 10000)

    def test_too_close_or_wrong_side(self):
        for p, side in (([10.26, 3.5], 'east'), ([9, 3.5], 'east')):
            with self.assertRaises(ValueError):
                line_side.check(observed(), p, side, 10000)

    def test_tampered_geometry_and_bad_points(self):
        o = observed(); o['geometry']['coordinates'][0][0][0] = 9
        with self.assertRaises(ValueError): line_side.check(o, [9, 3.5], 'west', 10000)
        for p in ([float('nan'), 3], [True, 3], [200, 3]):
            with self.assertRaises(ValueError): line_side.check(observed(), p, 'west', 10000)

    def test_nonmonotonic_and_overlapping_segments_fail(self):
        for coords in ([[[10, 4], [10, 2], [11, 3]]],
                       [[[10, 4], [10, 2]], [[11, 4], [11, 2]]]):
            o = observed(); o['geometry']['coordinates'] = coords
            o['geometry_sha256'] = hashlib.sha256(json.dumps(o['geometry'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            with self.assertRaises(ValueError): line_side.check(o, [9, 3], 'west', 10000)

    def test_endpoint_overlap_is_ambiguous(self):
        o = observed(); o['geometry']['coordinates'] = [
            [[10, 4], [10, 3]], [[11, 5], [11, 2]]]
        o['geometry_sha256'] = hashlib.sha256(json.dumps(o['geometry'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            line_side.check(o, [9, 3], 'west', 10000)

    def test_geodesic_margin_depends_on_latitude(self):
        for latitude, passes in ((0, True), (80, False)):
            o = observed(); o['geometry']['coordinates'] = [[[10, latitude + 1], [10, latitude - 1]]]
            o['geometry_sha256'] = hashlib.sha256(json.dumps(o['geometry'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            if passes:
                self.assertEqual(line_side.check(o, [9, latitude], 'west', 50000)['side'], 'west')
            else:
                with self.assertRaisesRegex(ValueError, 'below review screen'):
                    line_side.check(o, [9, latitude], 'west', 50000)

    def test_antimeridian_and_exact_line_fail_closed(self):
        o = observed(); o['geometry']['coordinates'] = [[[179, 1], [179, -1]]]
        o['geometry_sha256'] = hashlib.sha256(json.dumps(o['geometry'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        for longitude in (-179, 179):
            with self.subTest(longitude=longitude), self.assertRaisesRegex(ValueError, 'ambiguous point-to-line longitude'):
                line_side.check(o, [longitude, 0], 'west', 10000)


if __name__ == '__main__':
    unittest.main()
