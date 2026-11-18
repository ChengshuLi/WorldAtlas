from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.comparison import compare
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import file_hash, write_layer


class ComparisonTests(unittest.TestCase):
    def test_release_comparison_uses_category_meaning_and_reports_original_codes(self):
        grid = Grid(6, 1, 60)
        old = [
            dict(code=17, entity_id=1, physical_class="land"),
            dict(code=18, entity_id=2, physical_class="land"),
            dict(code=2, entity_id=2, physical_class="water"),
        ]
        new = [dict(old[0], code=11), dict(old[1], code=17), dict(old[2], code=12)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, runs in (
                ("before", [(0, 2, 17), (2, 4, 18), (4, 6, 2)]),
                ("recoded", [(0, 2, 11), (2, 4, 17), (4, 6, 12)]),
                ("changed", [(0, 1, 11), (1, 4, 17), (4, 5, 12), (5, 6, 17)]),
            ):
                write_layer(root / name, grid, [(0, runs)])
            hashes = {
                name: file_hash(root / "before" / name)
                for name in ("rows.u32le", "runs.u32le")
            }
            for output, pairs in (("recoded", {}), ("changed", {"17->17": 1, "2->17": 1})):
                with self.subTest(output=output):
                    report = compare(
                        root / output,
                        root / "before",
                        grid,
                        root / (output + "-diff"),
                        hashes,
                        reference_bindings=old,
                        candidate_bindings=new,
                    )
                    self.assertEqual(report["pair_counts"], pairs)
                    self.assertEqual(report["changed_cells"], sum(pairs.values()))
                    self.assertFalse(report["byte_identical"])

    def test_removed_southern_rows_are_reported_separately(self):
        original, cropped = Grid(4, 2, 90), Grid(4, 1, 90)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_layer(
                root / "before", original, [(0, [(0, 4, 81)]), (1, [(0, 4, 11)])]
            )
            write_layer(root / "after", cropped, [(0, [(0, 4, 81)])])
            hashes = {
                name: file_hash(root / "before" / name)
                for name in ("rows.u32le", "runs.u32le")
            }
            report = compare(
                root / "after", root / "before", cropped, root / "diff", hashes
            )
            self.assertEqual(report["changed_cells"], 0)
            self.assertEqual(report["removed_cells_by_code"], {"11": 4})
            self.assertTrue(report["assignments_identical_on_retained_grid"])
            self.assertFalse(report["byte_identical"])

    def test_exact_changed_spans_and_row_offsets(self):
        grid = Grid(4, 2, 90.0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_layer(root / "before", grid, [(0, [(0, 4, 81)]), (1, [(0, 4, 81)])])
            write_layer(
                root / "after",
                grid,
                [(0, [(0, 1, 81), (1, 3, 70000), (3, 4, 81)]), (1, [(0, 4, 81)])],
            )
            hashes = {
                name: file_hash(root / "before" / name)
                for name in ("rows.u32le", "runs.u32le")
            }
            report = compare(
                root / "after", root / "before", grid, root / "diff", hashes
            )
            self.assertEqual(report["changed_cells"], 2)
            self.assertEqual(report["pair_counts"], {"81->70000": 2})
            self.assertEqual(
                np.fromfile(root / "diff/changes.u32le", dtype="<u4").tolist(),
                [0, 1, 3, 81, 70000],
            )
            self.assertEqual(
                np.fromfile(root / "diff/change-rows.u64le", dtype="<u8").tolist(),
                [0, 1, 1],
            )
            same = compare(
                root / "before", root / "before", grid, root / "same", hashes
            )
            self.assertTrue(same["byte_identical"])
            self.assertEqual(same["changed_cells"], 0)
            self.assertEqual((root / "same/changes.u32le").stat().st_size, 0)
