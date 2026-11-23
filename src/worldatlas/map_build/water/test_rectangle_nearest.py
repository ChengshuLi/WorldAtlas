from worldatlas.map_build.water.test_helpers import classify_points
import unittest
from unittest.mock import patch
import numpy as np
from worldatlas.geodesy.wgs84 import unit_sphere
from worldatlas.map_build.water import rectangle_nearest as r
from worldatlas.map_build.water import shared_nearest as s


class RectangleNearest(unittest.TestCase):
    def test_empty_selection_needs_no_point_calculations(self):
        def unused(*_):
            self.fail("empty selection called the point classifier")

        result, totals = r.classify(
            np.zeros((2, 3), dtype=bool), 0, 0, (0, 360, 0, 180),
            360, 180, 1, [], {}, unused, band=22224,
        )
        self.assertFalse(result.any())
        self.assertFalse(any(totals.values()))

    def test_rejects_inconsistent_rectangle_inputs(self):
        valid = dict(
            water=np.ones((2, 3), dtype=bool), x0=0, y0=0,
            bounds=(0, 360, 0, 180), width=360, height=180,
            step=1, owners=[1, 2], indexes={},
            point_classifier=lambda *_: self.fail("validation was skipped"),
        )
        for definitions, error in (
            (dict(water=np.ones((2, 3))), "boolean selection grid required"),
            (dict(owners=[1, 1]), "invalid participant classes"),
            (dict(x0=359), "invalid grid or classifier"),
            (dict(band=-1), "invalid coastal band"),
            (dict(bounds=(0, 360)), "invalid crop"),
            (dict(bounds=(0, 361, 0, 180)), "invalid crop"),
            (dict(y0=181, height=184), "query latitude outside globe"),
        ):
            with self.subTest(definitions=definitions):
                with self.assertRaisesRegex(ValueError, error):
                    r.classify(**(valid | definitions))

    def test_rectangle_requires_one_valid_point_result_per_uncertain_cell(self):
        with self.assertRaisesRegex(ValueError, "invalid point classifier result"):
            r.classify(
                np.ones((1, 1), dtype=bool), 180, 89, (180, 360, 0, 180),
                360, 180, 1, [17], {}, lambda *_: ([99], 1, 0),
                band=100000,
            )

    def test_unbounded_cells_use_point_search_if_rectangle_index_is_incomplete(self):
        result, stats = r.classify(
            np.ones((1, 2), dtype=bool), 180, 89, (180, 360, 0, 180),
            360, 180, 1, [17, 18], {},
            lambda lat, lon: (np.full(lat.shape, 18), 0, len(lat)),
        )
        self.assertEqual(result.tolist(), [[18, 18]])
        self.assertEqual(stats["exact_cells"], 2)

    def test_incomplete_rectangle_search_never_publishes_codes(self):
        owners = [17, 18]
        lat, lon = np.array([0, 0]), np.array([-5, 5])
        indexes = s.make_indexes(
            dict(lat=lat, lon=lon, category=np.array([17, 18]), mids=unit_sphere(lat, lon)),
            owners,
        )
        settings = (
            np.ones((4, 4), dtype=bool), 179, 85, (0, 360, 0, 180),
            360, 180, 1, owners, indexes,
            lambda *_: self.fail("should fail before classifying individual cells"),
        )
        with patch.object(s, "exact_minima_by_ordered_chord", return_value=np.array([np.inf])):
            with self.assertRaisesRegex(RuntimeError, "invalid exact rectangle distances"):
                r.classify(*settings, block=4)
        with patch.object(r, "rectangle_counts", return_value=lambda a, *_: np.zeros_like(a)):
            with self.assertRaisesRegex(RuntimeError, "rectangle classification accounting mismatch"):
                r.classify(*settings, block=4)

    def test_block_counts_match_direct_sums_including_partial_edges(self):
        rng = np.random.default_rng(1729)
        for shape, block in (
            ((95, 197), 64),
            ((1, 137), 64),
            ((37, 1), 9),
            ((3, 7), 100),
        ):
            water = rng.random(shape) > 0.4
            if shape == (95, 197):
                water[:64, :64] = True
                water[:64, 64:128] = False
            count = r.rectangle_counts(water, block)
            rectangles = []
            for y in range(0, shape[0], block):
                for x in range(0, shape[1], block):
                    for _ in range(20):
                        a = int(rng.integers(y, min(y + block, shape[0])))
                        b = int(rng.integers(a + 1, min(y + block, shape[0]) + 1))
                        c = int(rng.integers(x, min(x + block, shape[1])))
                        d = int(rng.integers(c + 1, min(x + block, shape[1]) + 1))
                        rectangles.append((a, b, c, d))
            coordinates = np.array(rectangles).T
            expected = [water[a:b, c:d].sum() for a, b, c, d in rectangles]
            np.testing.assert_array_equal(count(*coordinates), expected)
            a, b, c, d = rectangles[0]
            self.assertEqual(count(a, b, c, d), water[a:b, c:d].sum())

    def test_optional_coastal_band_and_missing_classes(self):
        owners = [17, 18, 19]
        (lat, lon) = (np.array([0.5, 0.5]), np.array([-0.5, 5.5]))
        indexes = s.make_indexes(
            {
                "lat": lat,
                "lon": lon,
                "mids": unit_sphere(lat, lon),
                "category": np.array([17, 18], dtype="u1"),
            },
            owners[:2],
        )
        bounds = (0, 360, 0, 180)

        def point(lat, lon):
            (codes, stats) = s.classify_wgs84(
                lat, lon, bounds, 360, 180, 1.0, owners, indexes, band=100000.0
            )
            return (codes, stats["bounded"], stats["exact"])

        water = np.ones((7, 40), dtype=bool)
        (actual, stats) = r.classify(
            water, 160, 86, bounds, 360, 180, 1.0, owners, indexes, point, band=100000.0
        )
        (yy, xx) = np.indices(water.shape)
        expected = point(
            (90 - (86 + yy + 0.5)).ravel(), (-180 + (160 + xx + 0.5)).ravel()
        )[0].reshape(water.shape)
        np.testing.assert_array_equal(actual, expected)
        self.assertTrue(np.any(actual == 0))
        self.assertTrue(np.any(actual != 0))
        self.assertEqual(
            stats["bounded_cells"] + stats["exact_cells"], int(water.sum())
        )

    def test_global_masks_and_seams_against_complete_point_classifier(self):
        rng = np.random.default_rng(29485)
        owners = [18, 17, 19]
        lat = rng.uniform(-85, 85, 120)
        lon = rng.uniform(-180, 180, 120)
        categories = np.tile([17, 18, 19], 40).astype("u1")
        indexes = s.make_indexes(
            {"lat": lat, "lon": lon, "mids": unit_sphere(lat, lon), "category": categories},
            owners,
        )
        bounds = (0, 360, 0, 180)
        point = lambda lat, lon: classify_points(
            lat, lon, bounds, 360, 180, 1.0, owners, indexes
        )
        for x0, y0, nr, nc in (
            (0, 0, 5, 30),
            (350, 20, 11, 10),
            (0, 150, 13, 10),
            (160, 80, 9, 30),
        ):
            water = rng.random((nr, nc)) > 0.2
            (actual, stats) = r.classify(
                water, x0, y0, bounds, 360, 180, 1.0, owners, indexes, point, block=8
            )
            (yy, xx) = np.nonzero(water)
            expected = point(90 - (y0 + yy + 0.5), -180 + (x0 + xx + 0.5))[0]
            np.testing.assert_array_equal(actual[water], expected)
            self.assertTrue(np.all(actual[~water] == 0))
            self.assertEqual(
                stats["bounded_cells"] + stats["exact_cells"], int(water.sum())
            )

    def test_coastal_band_accepts_one_or_no_participant(self):
        bounds = (0, 360, 0, 180)
        data = {
            "lat": np.array([0.5]),
            "lon": np.array([0.5]),
            "mids": unit_sphere(np.array([0.5]), np.array([0.5])),
            "category": np.array([17], dtype="u1"),
        }
        for owners in ([17], []):
            indexes = s.make_indexes(data, owners)

            def point(lat, lon):
                (codes, stats) = s.classify_wgs84(
                    lat, lon, bounds, 360, 180, 1.0, owners, indexes, band=100000.0
                )
                return (codes, stats["bounded"], stats["exact"])

            water = np.ones((5, 8), dtype=bool)
            (actual, stats) = r.classify(
                water,
                177,
                87,
                bounds,
                360,
                180,
                1.0,
                owners,
                indexes,
                point,
                band=100000.0,
            )
            (yy, xx) = np.indices(water.shape)
            expected = point(
                (90 - (87 + yy + 0.5)).ravel(), (-180 + (177 + xx + 0.5)).ravel()
            )[0].reshape(water.shape)
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(
                stats["bounded_cells"] + stats["exact_cells"], int(water.sum())
            )

    def test_tie_priority_matches_point_reference(self):
        owners = [18, 17]
        (lat, lon) = (np.array([0.5, 0.5]), np.array([-0.5, 1.5]))
        indexes = s.make_indexes(
            {
                "lat": lat,
                "lon": lon,
                "mids": unit_sphere(lat, lon),
                "category": np.array([17, 18], dtype="u1"),
            },
            owners,
        )
        bounds = (0, 360, 0, 180)
        point = lambda lat, lon: classify_points(
            lat, lon, bounds, 360, 180, 1.0, owners, indexes
        )
        (actual, _) = r.classify(
            np.ones((3, 12), dtype=bool),
            175,
            88,
            bounds,
            360,
            180,
            1.0,
            owners,
            indexes,
            point,
        )
        self.assertEqual(actual[1, 5], 18)


if __name__ == "__main__":
    unittest.main()
