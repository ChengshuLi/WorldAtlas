import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
import unittest
import uuid
from unittest import mock

OWNED_DIR = Path(__file__).resolve().parents[1]
WORK = OWNED_DIR.parents[2]
sys.path.insert(0, str(OWNED_DIR / "tools"))
import reproduce


class ReproductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.immutable = reproduce.load_immutable()
        cls.baseline, _, _ = reproduce.pinned_inputs(cls.immutable)

    def fresh(self):
        return "test-" + uuid.uuid4().hex[:16]

    def run_driver(self, vintage):
        return subprocess.run([sys.executable, str(OWNED_DIR / "tools/reproduce.py"), vintage],
                              cwd=WORK, text=True, capture_output=True, timeout=240)

    def test_two_full_runs_have_complete_receipts_and_identical_reports(self):
        reports = []
        for vintage in ("correction-5", "correction-6"):
            root = OWNED_DIR / "vintages" / vintage
            receipt = json.loads((root / "publication.json").read_text())
            self.assertEqual(receipt["status"], "complete")
            names = {row["path"].rsplit("/", 1)[-1] for row in receipt["outputs"]}
            self.assertEqual(names, {"reconciliation.json", "execution.json"})
            report = (root / "reconciliation.json").read_bytes()
            execution = json.loads((root / "execution.json").read_text())
            self.assertEqual(reproduce.sha(report), reproduce.CURRENT_OUTPUT_SHA)
            self.assertEqual(execution["runtime"]["historical_replay"], False)
            self.assertEqual(execution["roster"], {"components": 50, "contacts": 14,
                                                     "families": 2, "available_numeric_sibling_bindings": 34})
            reports.append(report)
        self.assertEqual(reports[0], reports[1])

    def test_real_runner_refuses_existing_sentinel_and_later_output_collision(self):
        for collided_name in ("reconciliation.json", "execution.json"):
            vintage = self.fresh()
            root = OWNED_DIR / "vintages" / vintage
            root.mkdir(parents=True)
            sentinel = root / collided_name
            sentinel.write_bytes(b"ORIGINAL-VINTAGE\n")
            before = sentinel.read_bytes()
            result = self.run_driver(vintage)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_bytes(), before)
            self.assertFalse((root / "publication.json").exists())
            for item in root.iterdir():
                item.unlink()
            root.rmdir()

    def test_real_runner_refuses_dangling_output_and_symlink_parent(self):
        vintage = self.fresh()
        root = OWNED_DIR / "vintages" / vintage
        root.mkdir(parents=True)
        leaf = root / "reconciliation.json"
        target = root / "leaf-target.json"
        leaf.symlink_to(target)
        result = self.run_driver(vintage)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(leaf.is_symlink())
        self.assertFalse(target.exists())
        leaf.unlink()
        root.rmdir()

        vintage = self.fresh()
        vintages = OWNED_DIR / "vintages"
        target_dir = vintages / (vintage + "-target")
        target_dir.mkdir(parents=True)
        root = vintages / vintage
        root.symlink_to(target_dir, target_is_directory=True)
        before = list(target_dir.iterdir())
        result = self.run_driver(vintage)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(target_dir.iterdir()), before)
        self.assertTrue(root.is_symlink())
        root.unlink()
        target_dir.rmdir()

    def test_completed_run_cannot_be_replaced_on_rerun(self):
        root = OWNED_DIR / "vintages/correction-5"
        before = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}
        result = self.run_driver("correction-5")
        self.assertNotEqual(result.returncode, 0)
        after = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}
        self.assertEqual(after, before)

    def test_input_and_output_overflow_rejected_before_products(self):
        with self.assertRaises(ValueError):
            self.baseline.admit("over-limit-control", self.immutable.MAX_FILE_BYTES + 1)
        vintage = self.fresh()
        writer = self.immutable.NewVintage(self.baseline, reproduce.OWNED, vintage, ["large.bin"])
        with self.assertRaises(ValueError):
            writer.publish_bytes({"large.bin": b"x" * (self.immutable.MAX_FILE_BYTES + 1)})
        self.assertFalse(writer.root.exists())

    def test_failed_completion_link_leaves_no_success_receipt(self):
        failed = OWNED_DIR / "vintages/legacy-controls-v4-partial-failure"
        self.assertTrue((failed / "first.json").exists())
        self.assertTrue((failed / "second.json").exists())
        self.assertTrue((failed / ".publication-incomplete").exists())
        self.assertFalse((failed / "publication.json").exists())
        record = json.loads((OWNED_DIR / "vintages/legacy-controls-v4/legacy-controls.json").read_text())
        receipt = next(row for row in record["controls"] if row["control"] == "completion-receipt-last-failure")
        self.assertFalse(receipt["publication_exists"])
        self.assertTrue(receipt["incomplete_receipt_exists"])
        self.assertEqual([row["sha256"] for row in receipt["outputs"]],
                         [reproduce.sha(b"first\n"), reproduce.sha(b"second\n")])

    def test_validation_receipts_bind_exact_two_runs_and_controls(self):
        root = OWNED_DIR / "vintages/validation-v3"
        run = json.loads((root / "reproducibility.json").read_text())
        controls = json.loads((root / "controls-validation.json").read_text())
        self.assertEqual((run["method_id"], run["kind"], run["outcome"]),
                         ("corrected-runner-reproducibility", "generator", "passed"))
        self.assertEqual(run["run_one_sha256"], run["run_two_sha256"])
        self.assertEqual((controls["method_id"], controls["kind"], controls["outcome"]),
                         ("legacy-cli-input-output-controls", "code", "passed"))

    def test_preserves_original_packet_paths_modes_and_exact_metrics(self):
        manifest_path = OWNED_DIR / "evidence-quality.json"
        manifest = json.loads(manifest_path.read_text())
        original = [row for row in manifest["baseline"]["files"]
                    if row["path"].startswith(reproduce.PREDECESSOR)]
        tree = subprocess.check_output(["git", "-C", str(WORK), "ls-tree", "-r", "-l",
                                        reproduce.BASELINE_COMMIT, "--", reproduce.PREDECESSOR], text=True)
        actual = {}
        for line in tree.splitlines():
            metadata, path = line.split("\t", 1)
            mode, object_type, oid, byte_count = metadata.split()
            self.assertEqual(object_type, "blob")
            actual[path] = (mode, oid, int(byte_count))
        self.assertEqual(len(actual), 28)
        self.assertEqual({row["path"] for row in original}, set(actual))
        for row in original:
            self.assertEqual((row["mode"], row["git_oid"], row["bytes"]), actual[row["path"]])

        output_paths = {row["path"] for row in manifest["outputs"]}
        ledger_paths = {row["path"] for row in manifest["change_receipts"]}
        self.assertEqual(ledger_paths, output_paths | {str(manifest_path.relative_to(WORK))})
        for binding in manifest["metric_bindings"]:
            metric = next(row for row in manifest["metrics"] if row["id"] == binding["metric_id"])
            value = json.loads((WORK / binding["path"]).read_text())
            for segment in binding["json_pointer"].split("/")[1:]:
                segment = segment.replace("~1", "/").replace("~0", "~")
                value = value[int(segment)] if isinstance(value, list) else value[segment]
            self.assertEqual(value, metric["value"])

    def test_actual_legacy_cli_controls_record_expected_gaps(self):
        root = OWNED_DIR / "vintages/legacy-controls-v4/legacy-controls.json"
        packet = json.loads(root.read_text())
        controls = {row["control"]: row for row in packet["controls"]}
        self.assertEqual(len(controls), 16)
        self.assertEqual(controls["candidate-change-fixed-lock"]["expected"], "reject")
        self.assertEqual(controls["candidate-change-cochanged-lock"]["cli_exit_code"], 0)
        self.assertTrue(controls["family-body-copied-checksum"]["foreign_neighbor_survived"])
        self.assertTrue(controls["sentinel-overwrite"]["overwritten"])
        self.assertTrue(controls["dangling-output-symlink"]["target_created"])
        self.assertTrue(controls["symlink-parent"]["target_created"])
        self.assertNotEqual(controls["source-byte-mutation"]["exit_code"], 0)
        self.assertNotEqual(controls["current-contact-byte-mutation"]["exit_code"], 0)
        self.assertNotEqual(controls["subject-roster-mutation"]["exit_code"], 0)
        for name in ("guard-fixed-candidate", "guard-cochanged-candidate", "guard-cochanged-family",
                     "guard-source-byte-mutation", "guard-current-contact-byte-mutation", "guard-subject-roster"):
            row = controls["guarded-runner-rejects-" + name]
            self.assertNotEqual(row["exit_code"], 0)
            self.assertFalse(row["output_vintage_created"])


if __name__ == "__main__":
    unittest.main()
