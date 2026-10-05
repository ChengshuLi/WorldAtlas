"""Independent controls for the geographic gap inventory, no production writes."""
import importlib.util
import pathlib
import sys
import gzip
import json
import tempfile
import unittest

from shapely.geometry import Polygon, box
from shapely import union_all

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('gaps', ROOT / 'scripts/audit-geographic-gaps.py')
gaps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gaps)


class GapControls(unittest.TestCase):
    def test_matching_neighbors_have_no_gap(self):
        self.assertTrue(gaps.difference_tile(box(0, 0, 2, 1), [box(0, 0, 2, 1)],
                                            [box(0, 0, 1, 1), box(1, 0, 2, 1)]).is_empty)

    def test_narrow_missing_seam_is_retained(self):
        land = box(0, 0, 2, 1)
        result = gaps.difference_tile(land, [land], [box(0, 0, 1, 1), box(1.00000001, 0, 2, 1)])
        self.assertAlmostEqual(result.area, 1e-8, places=14)
        self.assertEqual(len(list(gaps.polygons(result))), 1)

    def test_ocean_and_reference_lake_holes_are_not_candidates(self):
        land = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)],
                       [[(1, 1), (2, 1), (2, 2), (1, 2)]])
        result = gaps.difference_tile(box(-1, -1, 4, 4), [land], [land])
        self.assertTrue(result.is_empty)
        # A land layer may include a lake. A separate water reference must exclude it.
        lake = box(1, 1, 2, 2)
        self.assertTrue(gaps.difference_tile(box(0, 0, 3, 3), [box(0, 0, 3, 3)], [land], [lake]).is_empty)

    def test_missing_small_island_is_retained(self):
        mainland, island = box(0, 0, 1, 1), box(2, 2, 2.0001, 2.0001)
        result = gaps.difference_tile(box(0, 0, 3, 3), [mainland, island], [mainland])
        self.assertTrue(result.equals(island))

    def test_tiling_preserves_cross_tile_gap_without_double_area(self):
        land = box(0, 0, 2, 2)
        occupied = [box(0, 0, .9, 2), box(1.1, 0, 2, 2)]
        fragments = [gaps.difference_tile(box(*b), [land], occupied)
                     for b in gaps.tiles([0, 0, 2, 2], 1)]
        whole = gaps.difference_tile(land, [land], occupied)
        self.assertTrue(union_all(fragments).equals(whole))
        self.assertAlmostEqual(sum(f.area for f in fragments), whole.area)

    def test_bundling_preserves_every_fragment_and_tile_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            out = pathlib.Path(directory)
            rows = [{'type': 'Feature', 'id': f'{i}:0', 'properties': {'tile': [i, 0, i+1, 1]},
                     'geometry': {'type': 'Polygon', 'coordinates': [[[i, 0], [i+1, 0], [i+1, 1], [i, 0]]]}}
                    for i in range(2)]
            report = {'outputs': []}
            for i, row in enumerate(rows):
                path = out / f'tile-{i}.geojson.gz'
                path.write_bytes(gzip.compress(json.dumps({'features': [row]}).encode()))
                report['outputs'].append({'path': str(path.relative_to(ROOT))})
            gaps.bundle_outputs(report, out)
            self.assertEqual(len(report['outputs']), 1)
            self.assertEqual(json.loads(gzip.decompress((ROOT / report['outputs'][0]['path']).read_bytes()))['features'], rows)
            self.assertEqual(list(out.glob('tile-*')), [])


if __name__ == '__main__':
    unittest.main()
