from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from worldatlas.map_build.core.comparison import (
    comparable_codes,
    compare,
    reference_lookup,
)
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.shared.files import sha256_file


class ComparisonTests(unittest.TestCase):
    def test_category_translation_handles_identity_removed_and_unknown_codes(self):
        land = dict(code=3, entity_id=1, physical_class="land")
        water = dict(code=6, entity_id=1, physical_class="water")
        self.assertIsNone(reference_lookup([land], [land]))
        lookup = reference_lookup([land, water], [dict(land, code=2)])
        self.assertEqual(comparable_codes(np.array([0, 3, 6]), lookup).tolist(), [0, 2, -1])
        for unknown in (4, 9):
            with self.subTest(code=unknown), self.assertRaisesRegex(ValueError, "unknown"):
                comparable_codes(np.array([unknown]), lookup)

    def test_comparison_rejects_incomplete_and_changed_reference_pins(self):
        grid = Grid(4, 1, 90)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after = root / "before", root / "after"
            write_layer(before, grid, [(0, [(0, 4, 7)])])
            write_layer(after, grid, [(0, [(0, 4, 8)])])
            pins = {
                name: sha256_file(before / name)
                for name in ("rows.u32le", "runs.u32le")
            }
            candidate = {
                name: sha256_file(after / name) for name in ("rows.u32le", "runs.u32le")
            }
            cases = (
                ({}, {}, "both stream checksums"),
                (pins, {"reference_bindings": []}, "both category mappings"),
            )
            for expected, options, error in cases:
                with (
                    self.subTest(error=error),
                    self.assertRaisesRegex(ValueError, error),
                ):
                    compare(
                        after,
                        before,
                        grid,
                        root / "diff",
                        expected,
                        candidate_sha256=candidate,
                        **options,
                    )

            with self.assertRaisesRegex(ValueError, "input changed"):
                compare(
                    after,
                    before,
                    grid,
                    root / "bad-digest",
                    dict(pins, **{"runs.u32le": "bad"}),
                    candidate_sha256=candidate,
                )

            def hash_then_change(path):
                if (
                    path == before / "rows.u32le"
                    and (root / "diff/changes.u32le").exists()
                ):
                    with (after / "runs.u32le").open("ab") as stream:
                        stream.write(b"changed")
                return sha256_file(path)

            with patch(
                "worldatlas.map_build.core.comparison.sha256_file", hash_then_change
            ):
                with self.assertRaisesRegex(ValueError, "input changed"):
                    compare(
                        after,
                        before,
                        grid,
                        root / "diff",
                        pins,
                        candidate_sha256=candidate,
                    )
            self.assertFalse((root / "diff/report.json").exists())

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
                name: sha256_file(root / "before" / name)
                for name in ("rows.u32le", "runs.u32le")
            }
            for output, pairs in (
                ("recoded", {}),
                ("changed", {"17->17": 1, "2->17": 1}),
            ):
                with self.subTest(output=output):
                    report = compare(
                        root / output,
                        root / "before",
                        grid,
                        root / (output + "-diff"),
                        hashes,
                        candidate_sha256={
                            name: sha256_file(root / output / name) for name in hashes
                        },
                        reference_bindings=old,
                        candidate_bindings=new,
                    )
                    self.assertEqual(report["pair_counts"], pairs)
                    self.assertEqual(report["changed_cells"], sum(pairs.values()))
                    self.assertFalse(report["byte_identical"])

    def test_comparison_rejects_different_row_counts(self):
        tall, short = Grid(4, 2, 90), Grid(4, 1, 90)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_layer(root / "tall", tall, [(0, [(0, 4, 81)]), (1, [(0, 4, 11)])])
            write_layer(root / "short", short, [(0, [(0, 4, 81)])])
            for candidate, reference, grid in (
                ("short", "tall", short),
                ("tall", "short", tall),
            ):
                with self.subTest(candidate=candidate):
                    hashes = {
                        name: sha256_file(root / reference / name)
                        for name in ("rows.u32le", "runs.u32le")
                    }
                    with self.assertRaisesRegex(ValueError, "same row count"):
                        compare(
                            root / candidate,
                            root / reference,
                            grid,
                            root / "diff",
                            hashes,
                            candidate_sha256={
                                name: sha256_file(root / candidate / name)
                                for name in hashes
                            },
                        )
                    self.assertFalse((root / "diff").exists())

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
                name: sha256_file(root / "before" / name)
                for name in ("rows.u32le", "runs.u32le")
            }
            report = compare(
                root / "after",
                root / "before",
                grid,
                root / "diff",
                hashes,
                candidate_sha256={
                    name: sha256_file(root / "after" / name) for name in hashes
                },
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
                root / "before",
                root / "before",
                grid,
                root / "same",
                hashes,
                candidate_sha256=hashes,
            )
            self.assertTrue(same["byte_identical"])
            self.assertEqual(same["changed_cells"], 0)
            self.assertEqual((root / "same/changes.u32le").stat().st_size, 0)
