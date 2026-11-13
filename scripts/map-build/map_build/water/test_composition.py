from pathlib import Path
import tempfile
import unittest


from map_build.core.grid import Grid
from map_build.core.rle import open_grid
from map_build.water.composition import compose
from map_build.water.shared_nearest import crop
from map_build.water.test_basins import rle


class CompositionTests(unittest.TestCase):
    def test_coastal_precedence_preserves_land_and_complete_coverage(self):
        grid = Grid(4, 2, 90.0)
        physical = rle([[17, 1, 1, 17], [1, 1, 1, 1]])
        land = rle([[901, 0, 0, 302], [0, 0, 0, 0]])
        coast = rle([[0, 75, 87, 0], [0, 0, 0, 0]])
        basin = rle([[0, 87, 87, 0], [75, 75, 75, 75]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'final'
            result = compose(
                physical, land, [[coast], [basin]], grid, path, [901, 302], [75, 87], complete=True
            )
            with open_grid(path, grid) as data:
                self.assertEqual(crop(*data, 0, 0, 4, 4).tolist(), [901, 75, 87, 302])
                self.assertEqual(crop(*data, 1, 0, 4, 4).tolist(), [75, 75, 75, 75])
            self.assertEqual(sum(result['counts'].values()), 8)

    def test_water_on_land_conflicts_and_incomplete_outputs_are_rejected(self):
        grid = Grid(4, 2, 90.0)
        physical = rle([[17, 1, 1, 1], [1, 1, 1, 1]])
        land = rle([[901, 0, 0, 0], [0, 0, 0, 0]])
        cases = [
            ([[rle([[75, 0, 0, 0], [0, 0, 0, 0]])]], False, 'physical land'),
            (
                [[rle([[0, 75, 0, 0], [0, 0, 0, 0]]), rle([[0, 87, 0, 0], [0, 0, 0, 0]])]],
                False,
                'conflicting',
            ),
            ([], True, 'unassigned'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for i, (groups, complete, message) in enumerate(cases):
                with self.subTest(case=i), self.assertRaisesRegex(ValueError, message):
                    compose(
                        physical,
                        land,
                        groups,
                        grid,
                        Path(directory) / str(i),
                        [901],
                        [75, 87],
                        complete=complete,
                    )
