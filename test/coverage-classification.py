import array
import importlib.util
import pathlib
import unittest
from shapely.geometry import Polygon, box

root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('coverage_preparation',root/'scripts/prepare-coverage-classification.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ClassificationControls(unittest.TestCase):
    def test_interval_priority_holes_and_repeatability(self):
        def compile_once():
            spans=[array.array('I',[0,8,1,2,4,2,5,6,3]) for _ in range(8)]
            return module.compile_runs(spans,8)
        rows,runs,cells,bits=compile_once()
        self.assertEqual(bits,3)
        self.assertEqual(list(runs[:8]),[8,1,18,3,12,4,14,7])
        self.assertEqual(cells,[0,40,16])
        self.assertEqual((rows.tobytes(),runs.tobytes()),tuple(x.tobytes() for x in compile_once()[:2]))

    def test_center_sampling_preserves_a_hole_and_shared_edge(self):
        # Invert grid cells to lon/lat to construct a known 8x8 physical polygon.
        import math
        def ll(x,y):
            return (x/8*360-180,math.degrees(math.atan(math.sinh(math.pi*(1-2*y/8)))))
        outer=[ll(x,y) for x,y in [(1,1),(7,1),(7,7),(1,7),(1,1)]]
        hole=[ll(x,y) for x,y in [(3,3),(5,3),(5,5),(3,5),(3,3)]]
        spans=[array.array('I') for _ in range(8)]
        module.add_polygon(spans,Polygon(outer,[hole]),1,8)
        rows,runs,cells,bits=module.compile_runs(spans,8)
        self.assertEqual(cells[1],32)
        self.assertEqual(list(rows[6:8]),[2,2])
        offset=rows[6]
        self.assertEqual(list(runs[offset*2:offset*2+4]),[9,2,13,6])

    def test_corrupt_source_and_excessive_decode_fail_closed(self):
        with self.assertRaises(ValueError):module.verify(b'changed','a'*64)
        old=module.MAX_DECODED
        module.MAX_DECODED=8
        try:
            with self.assertRaises(ValueError):module.decode_gzip(module.deterministic_gzip(b'x'*9))
        finally:module.MAX_DECODED=old

if __name__=='__main__':unittest.main()
