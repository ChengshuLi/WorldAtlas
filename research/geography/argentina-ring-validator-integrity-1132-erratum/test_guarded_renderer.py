"""Adverse-entry-point and partial-publication checks for the additive guard."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OWN = "research/geography/argentina-ring-validator-integrity-1132-erratum"
SCRIPT = HERE / "guarded-renderer.py"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("guarded_renderer", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GuardedRendererTests(unittest.TestCase):
    def invoke(self, vintage, *extra):
        return subprocess.run([sys.executable, str(SCRIPT), "--vintage", vintage, *extra],
                              cwd=REPO, text=True, capture_output=True, check=False)

    def owned_run(self, vintage):
        return REPO / OWN / "vintages" / vintage

    def test_unpinned_changed_inputs_are_rejected_before_output(self):
        expected = {
            "--scope": "data/regional-review/argentina-ring-classification-953-20261006/scope.json",
            "--source": "data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020-scoped-214.geojson",
            "--table": "data/regional-review/argentina-adm2-source-revalidation-443/findings/scoped-2020-to-current-georef-overlay.csv",
            "--baseline-renderer": "data/regional-review/argentina-adm2-source-revalidation-443/categorize-tabular-findings.py",
        }
        for option, original in expected.items():
            with self.subTest(option=option), tempfile.NamedTemporaryFile() as altered:
                altered.write(b"changed complete input fixture\n")
                altered.flush()
                vintage = "test-drift-" + option.lstrip("-").replace("-", "")
                result = self.invoke(vintage, option, altered.name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Unpinned caller-selected input rejected", result.stderr)
                self.assertFalse(self.owned_run(vintage).exists())

    def test_complete_source_with_only_itati_holes_removed_is_rejected(self):
        source_path = REPO / guard.REQUIRED_INPUTS["source"]
        source = json.loads(source_path.read_text(encoding="utf-8"))
        features = source["features"]
        by_id = {feature["properties"]["shapeID"]: feature for feature in features}
        self.assertEqual(len(features), 214)
        self.assertEqual(len(by_id), 214)
        itati_id = "61730980B76052784863315"
        itati = by_id[itati_id]

        def ring_count(feature):
            geometry = feature["geometry"]
            polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
            return sum(len(polygon) - 1 for polygon in polygons)

        self.assertEqual(ring_count(itati), 5)
        before_features = {identity: json.dumps(feature, sort_keys=True) for identity, feature in by_id.items()}
        geometry = itati["geometry"]
        if geometry["type"] == "Polygon":
            geometry["coordinates"] = geometry["coordinates"][:1]
        else:
            geometry["coordinates"] = [polygon[:1] for polygon in geometry["coordinates"]]
        self.assertEqual(ring_count(itati), 0)
        self.assertEqual(itati["properties"], json.loads(before_features[itati_id])["properties"])
        for identity, feature in by_id.items():
            if identity != itati_id:
                self.assertEqual(json.dumps(feature, sort_keys=True), before_features[identity])

        vintage = "test-complete-source-drift"
        with tempfile.TemporaryDirectory(prefix=".test-source-drift-", dir=REPO / OWN) as temp:
            altered_path = Path(temp) / "complete-214-source-drift.geojson"
            altered_path.write_text(json.dumps(source, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            altered = json.loads(altered_path.read_text(encoding="utf-8"))
            self.assertEqual(len(altered["features"]), 214)
            self.assertEqual(len({x["properties"]["shapeID"] for x in altered["features"]}), 214)
            result = self.invoke(vintage, "--source", str(altered_path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unpinned caller-selected input rejected", result.stderr)
        self.assertFalse(self.owned_run(vintage).exists())

    def test_escaped_output_path_is_rejected(self):
        vintage = "test-escaped-output"
        result = self.invoke(vintage, "--out-dir", str(REPO.parent / "escaped-output"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Output path must equal", result.stderr)
        self.assertFalse((REPO.parent / "escaped-output").exists())

    def test_existing_product_file_or_directory_is_preserved(self):
        base = REPO / OWN / "vintages"
        base.mkdir(parents=True, exist_ok=True)
        for kind in ("file", "directory"):
            vintage = "test-existing-" + kind
            root = self.owned_run(vintage)
            root.mkdir()
            sentinel = root / "corrected-findings.csv"
            if kind == "file":
                sentinel.write_bytes(b"keep this prior sentinel")
            else:
                sentinel.mkdir()
            before = sentinel.lstat()
            try:
                result = self.invoke(vintage)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(sentinel.lstat().st_ino, before.st_ino)
                if kind == "file":
                    self.assertEqual(sentinel.read_bytes(), b"keep this prior sentinel")
            finally:
                shutil.rmtree(root)

    def test_broken_symlink_product_is_rejected_and_preserved(self):
        vintage = "test-broken-symlink"
        root = self.owned_run(vintage)
        root.mkdir(parents=True)
        link = root / "corrected-findings.csv"
        link.symlink_to(root / "missing-target")
        try:
            result = self.invoke(vintage)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(link.is_symlink())
            self.assertFalse(link.exists())
        finally:
            shutil.rmtree(root)

    def test_actual_entry_point_failure_after_first_product_has_no_success_receipt(self):
        vintage = "test-partial-publication"
        root = self.owned_run(vintage)
        argv = [str(SCRIPT), "--vintage", vintage]
        original_open = Path.open
        created = 0

        def fail_second_output(path, mode="r", *args, **kwargs):
            nonlocal created
            if path.parent == root and mode == "xb":
                created += 1
                if created == 2:
                    raise OSError("injected write failure after one complete output")
            return original_open(path, mode, *args, **kwargs)

        try:
            with patch.object(Path, "open", fail_second_output), patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(OSError, "injected write failure"):
                    guard.main()
            self.assertEqual(created, 2)
            self.assertTrue(root.is_dir())
            self.assertEqual(len([p for p in root.iterdir() if p.is_file()]), 1)
            self.assertFalse((root / "publication.json").exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
