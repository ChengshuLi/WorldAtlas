"""Check that map codes preserve ownership and physical class."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.encoding import encode


class MapEncodingTests(unittest.TestCase):
    def test_land_and_water_need_distinct_codes_for_the_same_owner(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            grid = Grid(4, 2, 90)
            physical = root / "physical"
            owners = root / "owners"
            write_layer(physical, grid, [
                (0, [(0, 2, 17), (2, 4, 1)]),
                (1, [(0, 4, 1)]),
            ])
            write_layer(owners, grid, [(0, [(0, 4, 17)])])
            land = dict(entity_id=17, physical_class="land", code=80)
            water = dict(entity_id=17, physical_class="water", code=320)
            for invalid, message in (
                ([], "ambiguous map category bindings"),
                ([land, dict(land, code=81)], "ambiguous map category bindings"),
                ([land], "missing entity/physical-class map binding"),
            ):
                with self.subTest(invalid=invalid):
                    output = root / ("invalid-" + str(len(invalid)))
                    with self.assertRaisesRegex(ValueError, message):
                        encode(grid, physical, owners, invalid, output)
            output = root / "final"
            self.assertEqual(
                encode(grid, physical, owners, [land, water], output)["counts"],
                {"80": 2, "320": 2},
            )
            with open_grid(output, grid) as encoded:
                np.testing.assert_array_equal(row(encoded, 0, 4)[1], [80, 320])
                np.testing.assert_array_equal(row(encoded, 1, 4)[1], [0])
