"""Basin discovery uses complete physical water and current shoreline ownership."""

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from pyproj import Geod

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.division.policies import nearest_basin_water
from worldatlas.map_build.water.test_helpers import rle
from worldatlas.map_build.division.intervals import Eligibility, combine


class BasinTests(unittest.TestCase):
    def test_shore_span_splits_at_an_ownership_boundary(self):
        physical = np.ones_like(self.physical)
        physical[8, 5:13] = 17
        ownership = np.zeros_like(self.land)
        ownership[8, 5:8] = 81
        ownership[8, 8:13] = 42
        refs = ShoreGeometry(rle(physical), self.grid).attach(rle(ownership), [81, 42])
        self.assertEqual(
            [(y, spans.tolist()) for y, spans in refs.layer_rows()],
            [(8, [[5, 8, 81], [8, 13, 42]])],
        )

    def setUp(self):
        self.grid = Grid(36, 18, 10)
        self.physical = np.ones((18, 36), dtype=np.uint32)
        self.land = np.zeros_like(self.physical)
        self.physical[7:11, [10, 16]] = 17
        self.land[7:11, 10] = 81
        self.land[7:11, 16] = 42
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)

    def calculate(
        self,
        *,
        bounds=(11, 16, 7, 11),
        snapshot=None,
        remaining=False,
        eligible=None,
    ):
        p, l = rle(self.physical), rle(self.land)
        parent = rle(np.ones_like(self.physical))
        x0, x1, y0, y1 = bounds
        west, east = -180 + x0 * 10, -180 + x1 * 10
        north, south = 90 - y0 * 10, 90 - y1 * 10
        polygon = dict(
            type="Polygon",
            coordinates=[
                [
                    [west, south],
                    [east, south],
                    [east, north],
                    [west, north],
                    [west, south],
                ]
            ],
        )
        rule = dict(
            id="basin",
            operation="nearest_basin_water",
            physical_class="water",
            unit="cell",
            unassigned_only=remaining,
            features=dict(scope_area=[dict(id="area", geometry=polygon)]),
        )
        scope = Scope(
            rule,
            self.grid,
            p,
            parent,
            rle(self.land if snapshot is None else snapshot),
            lambda kind: None,
        )
        shores = ShoreGeometry(p, self.grid).attach(
            l, [81, 42], reference_owners=eligible
        )
        context = SimpleNamespace(
            grid=self.grid,
            parent_physical=p,
            land_ownership=l,
            shore_order=[81, 42],
            water_shores=lambda: shores,
        )
        directory = self.path / str(len(list(self.path.iterdir())))
        result = nearest_basin_water(context, scope, directory)
        with open_grid(result["directory"], self.grid) as values:
            dense = np.stack(
                [
                    codes[np.searchsorted(ends, np.arange(36), side="right")]
                    for ends, codes in (row(values, y, 36) for y in range(18))
                ]
            )
        return result, dense

    def test_full_claim_includes_coastal_cells_and_discovery_precedes_filtering(self):
        snapshot = self.land.copy()
        snapshot[7:11, 11] = 81
        snapshot[7:11, 15] = 42
        full, values = self.calculate(snapshot=snapshot)
        remaining, left = self.calculate(snapshot=snapshot, remaining=True)
        self.assertEqual(full["participant_shore_edges"], {81: 4, 42: 4})
        self.assertEqual(
            remaining["participant_shore_edges"], full["participant_shore_edges"]
        )
        self.assertTrue(np.all(values[7:11, 11] == 81))
        self.assertTrue(np.all(values[7:11, 15] == 42))
        self.assertFalse(left[7:11, [11, 15]].any())

    def test_land_edit_changes_the_participant_set(self):
        self.land[7:11, 16] = 81
        result, values = self.calculate()
        self.assertEqual(result["participant_shore_edges"], {81: 8})
        self.assertTrue(np.all(values[7:11, 11:16] == 81))

    def test_land_only_child_is_not_a_water_assignment_candidate(self):
        result, values = self.calculate(eligible={81})
        self.assertEqual(result["participant_shore_edges"], {81: 4})
        self.assertTrue(np.all(values[7:11, 11:16] == 81))

    def test_no_participant_with_eligible_water_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "no eligible reference shores"):
            self.calculate(bounds=(12, 15, 7, 11))

    def test_independent_coastal_and_basin_claims_must_agree(self):
        with self.assertRaisesRegex(ValueError, "ownership conflict"):
            combine(
                (np.array([1]), np.array([1])),
                (np.array([1]), np.array([1])),
                (np.array([1]), np.array([0])),
                [(np.array([1]), np.array([99])), (np.array([1]), np.array([81]))],
                y=0,
                rules=["coastal", "basin"],
                allowed=Eligibility({99: "mixed", 81: "mixed"}),
            )

    def test_assignment_matches_complete_independent_distances(self):
        _, values = self.calculate()
        geod = Geod(ellps="WGS84")
        for y in range(7, 11):
            for x in range(11, 16):
                minima = []
                for owner in (81, 42):
                    yy, xx = np.nonzero(self.land == owner)
                    minima.append(
                        np.min(
                            geod.inv(
                                np.full(len(xx), float(self.grid.longitude(x))),
                                np.full(len(yy), float(self.grid.latitude(y))),
                                self.grid.longitude(xx),
                                self.grid.latitude(yy),
                            )[2]
                        )
                    )
                self.assertEqual(values[y, x], (81, 42)[int(np.argmin(minima))])
