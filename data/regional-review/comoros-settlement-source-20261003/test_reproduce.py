import hashlib
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import reproduce


class CrosswalkReproductionTests(unittest.TestCase):
    def test_positive_source_and_output_control(self):
        rows = reproduce.rows_from_source()
        counts = {}
        for row in rows:
            counts[row["crosswalk_level"]] = counts.get(row["crosswalk_level"], 0) + 1
        self.assertEqual(counts, {"ADM1_island": 3, "ADM2_prefecture": 17, "ADM3_commune": 55})
        self.assertEqual(reproduce.OUTPUT.read_bytes(), reproduce.render(rows))

    def test_negative_source_hash_control(self):
        original = reproduce.SOURCE.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            altered = pathlib.Path(directory) / "altered.zip"
            altered.write_bytes(original + b"\n")
            with patch.object(reproduce, "SOURCE", altered):
                with self.assertRaisesRegex(SystemExit, "source hash mismatch"):
                    reproduce.rows_from_source()

    def test_write_refuses_dangling_symlink_without_creating_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            target = root / "outside.csv"
            link = root / "crosswalk.csv"
            link.symlink_to(target)
            with patch.object(reproduce, "OUTPUT", link), patch.object(
                sys, "argv", ["reproduce.py", "--write"]
            ):
                with self.assertRaisesRegex(SystemExit, "Refusing to overwrite"):
                    reproduce.main()
            self.assertTrue(link.is_symlink())
            self.assertFalse(target.exists())

    def test_two_renderings_are_byte_identical(self):
        first = reproduce.render(reproduce.rows_from_source())
        second = reproduce.render(reproduce.rows_from_source())
        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(),
            hashlib.sha256(reproduce.OUTPUT.read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
