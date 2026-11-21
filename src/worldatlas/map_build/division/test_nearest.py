"""Compare the common distance kernels with complete independent WGS84 searches."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
from pyproj import Geod

from worldatlas.map_build.water import shared_nearest as nearest
from worldatlas.map_build.water.rectangle_nearest import classify
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.division.nearest import nearest as assign_nearest
from worldatlas.map_build.division.policies import nearest_land
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.division.shores import ReferenceCells


class StrictNearest(unittest.TestCase):
    bounds = (0, 360, 0, 180)

    def references(self, latitude, longitude, owners):
        centers = dict(
            lat=np.asarray(latitude, dtype=float),
            lon=np.asarray(longitude, dtype=float),
            category=np.asarray(owners, dtype=np.uint32),
        )
        centers["mids"] = nearest.unit(centers["lat"], centers["lon"])
        pairs = [(owner, owner, owner) for owner in dict.fromkeys(owners)]
        return centers, pairs, nearest.make_indexes(centers, pairs)

    def query(self, latitude, longitude, pairs, indexes, **kwargs):
        return nearest.classify_wgs84(
            latitude, longitude, self.bounds, 360, 180, 1, pairs, indexes, **kwargs
        )

    def test_random_queries_match_all_reference_distances(self):
        rng = np.random.default_rng(1927)
        centers, pairs, indexes = self.references(
            rng.uniform(-70, 70, 72), rng.uniform(-180, 180, 72), [101, 807, 99] * 24
        )
        lat, lon = rng.uniform(-75, 75, 160), rng.uniform(-180, 180, 160)
        actual, stats = self.query(lat, lon, pairs, indexes)
        expected = []
        geod = Geod(ellps="WGS84")
        for y, x in zip(lat, lon):
            distance = np.asarray(
                geod.inv(
                    np.full(72, x), np.full(72, y), centers["lon"], centers["lat"]
                )[2]
            )
            minima = [
                distance[centers["category"] == owner].min() for owner, _, _ in pairs
            ]
            expected.append(pairs[int(np.argmin(minima))][0])
        self.assertEqual(actual.tolist(), expected)
        self.assertEqual(stats["bounded"] + stats["exact"], len(lat))

    def test_exact_equality_uses_supplied_order(self):
        _, pairs, indexes = self.references([0, 0], [-1, 1], [807, 101])
        self.assertEqual(self.query([0], [0], pairs, indexes)[0].tolist(), [807])
        with patch.object(nearest, "exact_minima_by_ordered_chord", return_value=np.array([np.inf])):
            with self.assertRaisesRegex(RuntimeError, "no provable candidate shore"):
                self.query([0], [0], pairs, indexes)

    def test_a_smaller_distance_wins_even_when_difference_is_tiny(self):
        _, pairs, indexes = self.references([0, 0], [-1, 1], [807, 101])
        answer, _ = self.query([0], [1e-11], pairs, indexes)
        self.assertEqual(answer.tolist(), [101])

    def test_coastal_limit_includes_exact_threshold(self):
        _, pairs, indexes = self.references([0], [1], [101])
        limit = Geod(ellps="WGS84").inv(0, 0, 1, 0)[2]
        self.assertEqual(
            self.query([0], [0], pairs, indexes, band=limit)[0].tolist(), [101]
        )
        self.assertEqual(
            self.query([0], [0], pairs, indexes, band=limit - 1e-6)[0].tolist(), [0]
        )

    def test_index_must_contain_all_unrestricted_participants(self):
        centers, pairs, indexes = self.references([0], [0], [101])
        missing = (807, 807, 807)
        with self.assertRaisesRegex(ValueError, "missing participant shore"):
            self.query([0], [0], [*pairs, missing], indexes)
        with self.assertRaisesRegex(ValueError, "no shore"):
            nearest.make_indexes(centers, [missing])

    def test_small_crop_cannot_rule_out_shore_just_outside_it(self):
        self.assertEqual(
            self.query([0], [0], [], {}, band=100)[0].tolist(), [0]
        )
        with self.assertRaisesRegex(ValueError, "crop cannot certify"):
            nearest.classify_wgs84(
                [0], [0], (180, 181, 90, 91), 360, 180, 1, [], {}, band=100
            )
        _, pairs, indexes = self.references([0], [1], [101])
        with self.assertRaisesRegex(ValueError, "cannot certify coastal band"):
            nearest.classify_wgs84(
                [0], [0], (180, 360, 0, 180), 360, 180, 1, pairs, indexes, band=100,
            )

    def test_point_classifier_checks_coordinates_and_grid(self):
        pairs, indexes = [], {}
        for lat, lon, bounds, step, band, message in (
            ([91], [0], self.bounds, 1, None, "invalid query coordinates"),
            ([0], [0], self.bounds, 1, -1, "invalid coastal distance limit"),
            ([0], [0], (0, 361, 0, 180), 1, None, "invalid crop or grid"),
            ([0], [0], self.bounds, 2, None, "step does not match"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    nearest.classify_wgs84(
                        lat, lon, bounds, 360, 180, step, pairs, indexes, band=band
                    )
        owners, stats = self.query([], [], pairs, indexes)
        self.assertEqual(owners.tolist(), [])
        self.assertEqual(stats, {"bounded": 0, "exact": 0})

    def test_empty_component_rule_returns_no_assignments(self):
        grid = Grid(8, 4, 45)
        # An empty parent has no eligible land, even with unassigned water.
        offsets = np.arange(grid.height + 1, dtype=np.uint32)
        empty_owner = offsets, np.tile(np.array([grid.width, 0], dtype=np.uint32), grid.height)
        physical = offsets, np.tile(np.array([grid.width, 1], dtype=np.uint32), grid.height)
        points = np.empty(0, dtype=np.uint32)
        references = ReferenceCells(grid, np.zeros_like(offsets), points, points, points, [])
        scope = Scope(
            dict(features={}, physical_class="land", unit="component", unassigned_only=True),
            grid, physical, empty_owner, empty_owner, lambda kind: None,
        )
        with TemporaryDirectory() as folder:
            path = Path(folder) / "assignments"
            self.assertEqual(assign_nearest(scope, references, "component", directory=path)["counts"], {})
            self.assertEqual(nearest_land(None, scope, Path(folder) / "policy")["counts"], {})
            with self.assertRaisesRegex(ValueError, "requires a cell or component"):
                assign_nearest(scope, references, "row", directory=path)
            with self.assertRaisesRegex(ValueError, "does not support a coastal distance limit"):
                assign_nearest(scope, references, "component", 100, directory=path)

    def test_reference_index_rejects_unknown_or_missing_shore_owners(self):
        grid = Grid(8, 4, 45)
        empty = np.empty(0, dtype=np.uint32)
        offsets = np.zeros(grid.height + 1, dtype=np.uint32)
        references = ReferenceCells(grid, offsets, empty, empty, empty, [])
        with self.assertRaisesRegex(ValueError, "no eligible physical shores"):
            references.indexes
        with self.assertRaisesRegex(ValueError, "lacks an eligible physical shore"):
            references.filtered([17])
        with self.assertRaisesRegex(ValueError, "shore owner is not a selected child"):
            ReferenceCells(grid, np.array([0, 1, 1, 1, 1]), np.array([0]), np.array([1]), np.array([17]), [])

    def test_rectangle_acceleration_preserves_point_results(self):
        _, pairs, indexes = self.references(
            [12, -13, 20], [-30, 60, 170], [101, 807, 99]
        )
        mask = np.ones((10, 15), dtype=bool)
        mask[::2, ::3] = False

        def points(lat, lon):
            codes, stats = self.query(lat, lon, pairs, indexes)
            return codes, stats["bounded"], stats["exact"]

        actual, stats = classify(
            mask, 170, 80, self.bounds, 360, 180, 1, pairs, indexes, points
        )
        y, x = np.nonzero(mask)
        expected, _ = self.query(
            90 - (80 + y + 0.5), -180 + (170 + x + 0.5), pairs, indexes
        )
        self.assertEqual(actual[mask].tolist(), expected.tolist())
        self.assertTrue(np.all(actual[~mask] == 0))
        self.assertEqual(stats["bounded_cells"] + stats["exact_cells"], int(mask.sum()))
