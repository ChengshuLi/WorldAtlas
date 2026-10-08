from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import admission
import freeze_safe
import run_safe
import write_control_receipts


REPO = run_safe.REPO_ROOT
OWNED = REPO / "research/geography/saudi-source-capture-1357-admission-20261008"
OLD = REPO / run_safe.PREDECESSOR


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fake_lock(*, phase: int, per_file: int = 32,
              duplicate: bool = False, decoded: bytes | None = None) -> dict:
    body = b"same"
    rows = []
    for i in range(2 if duplicate else 1):
        row = {"commit": f"{i + 1:040x}", "path": f"coordination/source-{i}.json",
               "mode": "100644", "oid": f"{i + 11:040x}",
               "bytes": len(body), "sha256": digest(body)}
        if decoded is not None:
            row.update(uncompressed_bytes=len(decoded), uncompressed_sha256=digest(decoded))
        rows.append(row)
    code_paths = ["source_extract.py", "run_final.py", "compat/inputs.py", "compat/immutable.py"]
    input_paths = ["issue-1336-api.json", "inputs/legacy-input-config.json"]
    code = [{"path": p, "bytes": 1, "sha256": digest(p.encode())} for p in code_paths]
    local = [{"path": p, "bytes": 1, "sha256": digest(p.encode())} for p in input_paths]
    return {"version": 1, "source_blobs": rows, "source_blob_count": len(rows),
            "source_blob_encoded_bytes": len(rows) * len(body), "code": code,
            "local_inputs": local,
            "limits": {"per_encoded_or_decoded_input_bytes": per_file,
                       "maximum_total_declared_bytes": phase}}


def plan(lock: dict, *, output: int = 0, runtime: int = 0, receipt: int = 0,
         phase: int = 256, per_file: int = 32, supplemental_files: list[dict] | None = None) -> dict:
    lock = json.loads(json.dumps(lock))
    lock["limits"]["per_encoded_or_decoded_input_bytes"] = per_file
    lock["limits"]["maximum_total_declared_bytes"] = phase
    return admission.plan_from_lock(
        lock, lock_sha256=digest(b"lock"), lock_bytes=4,
        output_reserve_bytes=output, runtime_reserve_bytes=runtime,
        receipt_reserve_bytes=receipt, per_file_bytes=per_file,
        phase_bytes=phase, required_source_bytes=None, supplemental_files=supplemental_files,
    )


class PlanTests(unittest.TestCase):
    def test_phase_limit_below_at_and_above(self):
        template = fake_lock(phase=100)
        at = plan(template, output=3, runtime=2, receipt=1, phase=100, per_file=32)
        exact = at["complete_phase_bytes"]
        self.assertTrue(plan(template, output=3, runtime=2, receipt=1,
                             phase=exact, per_file=32)["admitted"])
        self.assertFalse(plan(template, output=3, runtime=2, receipt=1,
                              phase=exact - 1, per_file=32)["admitted"])
        self.assertTrue(plan(template, output=3, runtime=2, receipt=1,
                             phase=exact + 1, per_file=32)["admitted"])

    def test_identical_hashes_deduplicate_but_distinct_hashes_do_not(self):
        duplicate = fake_lock(phase=256, duplicate=True)
        value = plan(duplicate, phase=256, per_file=32)
        self.assertEqual(value["encoded_descriptor_sum_bytes"], 8)
        self.assertEqual(value["source_body_minimum_bytes"], 4)
        self.assertEqual(value["unique_source_body_identities"], 1)

        distinct = fake_lock(phase=256)
        distinct["source_blobs"].append({
            "commit": f"{99:040x}", "path": "coordination/other.json", "mode": "100644",
            "oid": f"{100:040x}", "bytes": 4, "sha256": digest(b"diff"),
        })
        distinct["source_blob_count"] = 2
        distinct["source_blob_encoded_bytes"] = 8
        value = plan(distinct, phase=256, per_file=32)
        self.assertEqual(value["source_body_minimum_bytes"], 8)
        self.assertEqual(value["unique_source_body_identities"], 2)

    def test_conflicting_identity_size_and_missing_bindings_reject(self):
        lock = fake_lock(phase=256, duplicate=True)
        lock["source_blobs"][1]["bytes"] = 5
        lock["source_blob_encoded_bytes"] = 9
        with self.assertRaises(admission.AdmissionError):
            plan(lock, phase=256, per_file=32)
        lock = fake_lock(phase=256)
        lock["code"].pop()
        with self.assertRaises(admission.AdmissionError):
            plan(lock, phase=256, per_file=32)

    def test_compressed_small_but_decoded_large_is_rejected_boundedly(self):
        payload = b"x" * 64
        compressed = gzip.compress(payload)
        self.assertLess(len(compressed), len(payload))
        with self.assertRaisesRegex(admission.AdmissionError, "Declared decoded"):
            admission.bounded_gzip(compressed, declared_bytes=len(payload),
                                   declared_sha256=digest(payload), per_file_bytes=32)
        with self.assertRaisesRegex(admission.AdmissionError, "Actual decoded"):
            admission.bounded_gzip(compressed, declared_bytes=32,
                                   declared_sha256=digest(payload[:32]), per_file_bytes=32)

    def test_independent_reader_inputs_aggregate_into_complete_phase(self):
        lock = fake_lock(phase=512)
        base = plan(lock, phase=512, per_file=256)["complete_phase_bytes"]
        extras = [{"path": "reader-a/ast.json", "bytes": 80, "sha256": digest(b"a" * 80)},
                  {"path": "reader-b/decoded.json", "bytes": 80, "sha256": digest(b"b" * 80)}]
        result = plan(lock, phase=base + 100, per_file=256, supplemental_files=extras)
        self.assertEqual(result["supplemental_input_count"], 2)
        self.assertEqual(result["complete_phase_bytes"], base + 160)
        self.assertFalse(result["admitted"])

    def test_output_and_receipt_reserves_are_in_complete_phase(self):
        lock = fake_lock(phase=256)
        base = plan(lock, phase=256, per_file=32)["complete_phase_bytes"]
        self.assertTrue(plan(lock, phase=base, per_file=32)["admitted"])
        self.assertFalse(plan(lock, output=1, phase=base, per_file=32)["admitted"])
        reserved = plan(lock, output=10, runtime=8, receipt=4,
                        phase=256, per_file=32)["complete_phase_bytes"]
        self.assertEqual(reserved - base, 22)


class DestinationTests(unittest.TestCase):
    def setUp(self):
        OWNED.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="test-safety-", dir=OWNED)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_existing_file_dangling_and_live_symlinks_and_escape_reject(self):
        (self.root / "parent").mkdir()
        target = self.root / "target.json"
        target.write_bytes(b"sentinel")
        with self.assertRaises(FileExistsError):
            admission.admit_destinations(self.root, ["target.json"])
        link = self.root / "broken.json"
        link.symlink_to("absent.json")
        with self.assertRaises(admission.AdmissionError):
            admission.admit_destinations(self.root, ["broken.json"])
        live = self.root / "live"
        live.symlink_to(target)
        with self.assertRaises(admission.AdmissionError):
            admission.admit_destinations(self.root, ["live/child.json"])
        with self.assertRaises(admission.AdmissionError):
            admission.admit_destinations(self.root, ["../escape.json"])
        self.assertEqual(target.read_bytes(), b"sentinel")

    def test_new_vintage_paths_can_be_admitted_as_one_set(self):
        paths = ["runs/run-a/output/one.json", "runs/run-a/receipt.json"]
        dirs = ["runs/run-a", "runs/run-a/output"]
        self.assertEqual(admission.admit_destinations(self.root, paths, directory_paths=dirs), paths)

    def test_exclusive_writer_refuses_existing_and_dangling_targets(self):
        target = self.root / "out.json"
        target.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            admission.write_exclusive(self.root, "out.json", b"replacement")
        self.assertEqual(target.read_bytes(), b"original")
        (self.root / "broken.json").symlink_to("absent.json")
        with self.assertRaises((admission.AdmissionError, FileExistsError)):
            admission.write_exclusive(self.root, "broken.json", b"data")
        self.assertTrue((self.root / "broken.json").is_symlink())

    def test_freeze_writer_preadmits_before_derivation_and_never_overwrites(self):
        old_here = run_safe.HERE
        harness = self.root / "research/geography/saudi-source-capture-1357-admission-20261008"
        harness.mkdir(parents=True)
        run_safe.HERE = harness
        plan = {"admitted": True, "runtime": {"version": "fixture"}}
        called = []
        def derive(root):
            run_dir = harness / "execution/freezes/success"
            self.assertFalse((run_dir / "frozen-execution.json").exists())
            self.assertFalse((run_dir / "execution.json").exists())
            called.append(True)
            return {"version": 1}
        try:
            with patch.object(run_safe, "load_plan", return_value=({}, plan, {}, [])):
                result = freeze_safe.run_freeze(self.root, "success", derive)
            run_dir = harness / "execution/freezes/success"
            raw = (run_dir / "frozen-execution.json").read_bytes()
            receipt = json.loads((run_dir / "execution.json").read_text())
            self.assertEqual(result["lock"]["sha256"], digest(raw))
            self.assertEqual(called, [True])
            self.assertEqual(receipt["status"], "complete")
            self.assertTrue(receipt["complete_source_pass"])

            called[:] = []
            collision_dir = harness / "execution/freezes/existing"
            collision_dir.mkdir(parents=True)
            collision = collision_dir / "stale-partial.json"
            collision.write_bytes(b"preserve")
            with patch.object(run_safe, "load_plan", return_value=({}, plan, {}, [])):
                with self.assertRaises(FileExistsError):
                    freeze_safe.run_freeze(self.root, "existing", derive)
            self.assertEqual(called, [])
            self.assertEqual(collision.read_bytes(), b"preserve")
        finally:
            run_safe.HERE = old_here

    def test_freeze_derivation_failure_gets_a_failed_receipt(self):
        old_here = run_safe.HERE
        harness = self.root / "research/geography/saudi-source-capture-1357-admission-20261008"
        harness.mkdir(parents=True)
        run_safe.HERE = harness
        try:
            with patch.object(run_safe, "load_plan", return_value=({}, {"admitted": True, "runtime": {"version": "fixture"}}, {}, [])):
                with self.assertRaisesRegex(admission.AdmissionError, "failure receipt was retained"):
                    freeze_safe.run_freeze(self.root, "late-failure", lambda _root: (_ for _ in ()).throw(ValueError("controlled derive failure")))
            run_dir = harness / "execution/freezes/late-failure"
            self.assertFalse((run_dir / "frozen-execution.json").exists())
            receipt = json.loads((run_dir / "execution.json").read_text())
            self.assertEqual(receipt["status"], "failed-attempt")
            self.assertFalse(receipt["complete_source_pass"])
            self.assertIn("controlled derive failure", receipt["error"])
        finally:
            run_safe.HERE = old_here

    def test_freeze_refusal_does_not_derive_or_admit_writer(self):
        old_here = run_safe.HERE
        harness = self.root / "research/geography/saudi-source-capture-1357-admission-20261008"
        harness.mkdir(parents=True)
        run_safe.HERE = harness
        called = []
        try:
            with patch.object(run_safe, "load_plan", return_value=({}, {"admitted": False}, {}, [])):
                with self.assertRaisesRegex(freeze_safe.FreezeRefused, "refused before freeze"):
                    freeze_safe.run_freeze(self.root, "refused", lambda _root: called.append(True))
            self.assertEqual(called, [])
            self.assertFalse((harness / "execution/freezes/refused/frozen-execution.json").exists())
        finally:
            run_safe.HERE = old_here

    def test_control_receipt_entrypoint_preadmits_complete_output_set_before_tests(self):
        old_root, old_here, old_argv = run_safe.REPO_ROOT, run_safe.HERE, sys.argv[:]
        harness = self.root / "research/geography/saudi-source-capture-1357-admission-20261008"
        execution = harness / "execution"
        execution.mkdir(parents=True)
        run_safe.REPO_ROOT, run_safe.HERE = self.root, harness
        try:
            (execution / "positive-control-occupied.json").write_bytes(b"preserve")
            sys.argv = ["write_control_receipts.py", "--suffix", "occupied"]
            with patch.object(run_safe, "load_plan", side_effect=AssertionError("plan ran before destination admission")):
                with patch.object(write_control_receipts.subprocess, "run", side_effect=AssertionError("tests ran before destination admission")):
                    with self.assertRaises(FileExistsError):
                        write_control_receipts.main()
            self.assertEqual((execution / "positive-control-occupied.json").read_bytes(), b"preserve")
            self.assertFalse((execution / "test-run-occupied.json").exists())
            self.assertFalse((execution / "negative-control-occupied.json").exists())

            outside = self.root / "outside-control-receipts"
            outside.mkdir()
            (execution / "negative-control-parent").symlink_to(outside, target_is_directory=True)
            # Point the real entrypoint at a fresh owned-prefix-shaped fixture with a symlinked execution parent.
            linked = self.root / "research/geography/saudi-source-capture-1357-admission-20261008-linked"
            linked.mkdir()
            (linked / "execution").symlink_to(outside, target_is_directory=True)
            run_safe.HERE = linked
            sys.argv = ["write_control_receipts.py", "--suffix", "parent"]
            with patch.object(run_safe, "load_plan", side_effect=AssertionError("plan ran before destination admission")):
                with patch.object(write_control_receipts.subprocess, "run", side_effect=AssertionError("tests ran before destination admission")):
                    with self.assertRaises(admission.AdmissionError):
                        write_control_receipts.main()
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            run_safe.REPO_ROOT, run_safe.HERE, sys.argv = old_root, old_here, old_argv

    def test_new_wrapper_records_partial_failure_after_child_write(self):
        harness = OWNED / "test-harness"
        harness.mkdir(parents=True, exist_ok=True)
        old_here = run_safe.HERE
        expected = {"one.json": {"bytes": 32, "sha256": "0" * 64}}
        run_id = "control-partial-failure"
        output = harness / "execution/runs" / run_id / "output"
        code = "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(parents=True); (p/'one.json').write_bytes(b'partial'); sys.exit(23)"
        try:
            run_safe.HERE = harness
            result = run_safe.run_admitted_child(
                REPO, run_id, [sys.executable, "-c", code, str(output)], expected,
                {"admitted": True, "complete_phase_bytes": 1, "phase_limit_bytes": 2},
            )
            self.assertEqual(result["exit_code"], 23)
            receipt = json.loads((harness / "execution/runs" / run_id / "execution.json").read_text())
            self.assertEqual(receipt["status"], "failed-attempt")
            self.assertFalse(receipt["complete_source_pass"])
            self.assertEqual(receipt["products"][0]["bytes"], 7)
            self.assertTrue((output / "one.json").is_file())
        finally:
            run_safe.HERE = old_here
            shutil.rmtree(harness / "execution/runs" / run_id, ignore_errors=True)

    def test_new_wrapper_rejects_late_success_with_wrong_product_bytes(self):
        harness = OWNED / "test-harness"
        harness.mkdir(parents=True, exist_ok=True)
        old_here = run_safe.HERE
        run_id = "control-late-wrong-output"
        output = harness / "execution/runs" / run_id / "output"
        expected = {"one.json": {"bytes": 8, "sha256": digest(b"expected")}}
        code = "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(parents=True); (p/'one.json').write_bytes(b'wrong!!!')"
        try:
            run_safe.HERE = harness
            result = run_safe.run_admitted_child(
                REPO, run_id, [sys.executable, "-c", code, str(output)], expected,
                {"admitted": True, "complete_phase_bytes": 1, "phase_limit_bytes": 2},
            )
            receipt = json.loads((harness / "execution/runs" / run_id / "execution.json").read_text())
            self.assertEqual(result["child_exit_code"], 0)
            self.assertEqual(result["exit_code"], 1)
            self.assertFalse(receipt["complete_source_pass"])
            self.assertEqual(receipt["status"], "failed-attempt")
            self.assertIn("authenticated expected bytes", receipt["output_validation_error"])
        finally:
            run_safe.HERE = old_here
            shutil.rmtree(harness / "execution/runs" / run_id, ignore_errors=True)

    def test_new_wrapper_rejects_linked_receipt_and_parent_before_child(self):
        harness = OWNED / "test-harness"
        harness.mkdir(parents=True, exist_ok=True)
        old_here = run_safe.HERE
        expected = {"one.json": {"bytes": 32, "sha256": "0" * 64}}
        marker = harness / "child-started.txt"
        code = "from pathlib import Path; Path(__import__('sys').argv[1]).write_text('started')"
        try:
            run_safe.HERE = harness
            run_dir = harness / "execution/runs/existing-receipt"
            run_dir.mkdir(parents=True)
            link = run_dir / "execution.json"
            link_text = "../../../../outside-receipt.json"
            link.symlink_to(link_text)
            with self.assertRaises(admission.AdmissionError):
                run_safe.run_admitted_child(REPO, "existing-receipt",
                    [sys.executable, "-c", code, str(marker)], expected,
                    {"admitted": True})
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), link_text)
            self.assertFalse(marker.exists())

            run_dir = harness / "execution/runs/live-parent"
            outside = harness / "outside-runs"
            outside.mkdir()
            (harness / "execution/runs").mkdir(parents=True, exist_ok=True)
            run_dir.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(admission.AdmissionError):
                run_safe.run_admitted_child(REPO, "live-parent",
                    [sys.executable, "-c", code, str(marker)], expected,
                    {"admitted": True})
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse(marker.exists())
        finally:
            run_safe.HERE = old_here
            shutil.rmtree(harness / "execution/runs", ignore_errors=True)
            shutil.rmtree(harness / "outside-runs", ignore_errors=True)

    def _copy_early_failure_fixture(self, fixture_name: str) -> Path:
        root = self.root / fixture_name / "repo"
        packet = root / "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007"
        (packet / "compat").mkdir(parents=True)
        (packet / "inputs").mkdir()
        files = [
            "source_extract.py", "run_final.py", "frozen-execution.json", "issue-1336-api.json",
            "compat/inputs.py", "compat/immutable.py", "inputs/legacy-input-config.json",
        ]
        for name in files:
            shutil.copy2(OLD / name, packet / name)
        (packet / "issue-1336-api.json").write_text('{"auditor_deliberate_drift":true}\n')
        return root

    def _run_legacy_final(self, root: Path) -> subprocess.CompletedProcess:
        wrapper = root / "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007/run_final.py"
        return subprocess.run([sys.executable, str(wrapper), "--run-id", "run-1", "--repo", str(root)],
                              text=True, capture_output=True, check=False)

    def test_actual_legacy_wrapper_writes_through_dangling_receipt_link(self):
        root = self._copy_early_failure_fixture("legacy-dangling")
        packet = root / "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007"
        runs = packet / "runs"
        runs.mkdir()
        link = runs / "run-1-execution.json"
        target = root / "outside-dangling-receipt.json"
        link.symlink_to("../../../../outside-dangling-receipt.json")
        result = self._run_legacy_final(root)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(link.is_symlink())
        self.assertTrue(target.exists())
        receipt = json.loads(target.read_text())
        self.assertEqual(receipt["exit_code"], 1)
        self.assertFalse(receipt["complete_source_pass"])

    def test_actual_legacy_wrapper_writes_through_live_runs_parent_link(self):
        root = self._copy_early_failure_fixture("legacy-parent-link")
        packet = root / "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007"
        outside = root / "outside-runs"
        outside.mkdir()
        (packet / "runs").symlink_to(outside, target_is_directory=True)
        result = self._run_legacy_final(root)
        self.assertEqual(result.returncode, 1)
        escaped = outside / "run-1-execution.json"
        self.assertTrue(escaped.exists())
        self.assertFalse(json.loads(escaped.read_text())["complete_source_pass"])

    def test_actual_legacy_wrapper_preserves_existing_receipt_and_partial_output_controls(self):
        for case in ("existing-receipt", "partial-output"):
            root = self._copy_early_failure_fixture(case)
            packet = root / "research/geography/saudi-fortynine-numeric-gap-family-source-fitness-20261007"
            runs = packet / "runs"
            runs.mkdir()
            if case == "existing-receipt":
                target = runs / "run-1-execution.json"
                target.write_bytes(b"receipt-sentinel")
            else:
                target = runs / "run-1" / "output" / "partial.json"
                target.parent.mkdir(parents=True)
                target.write_bytes(b"output-sentinel")
            before = target.read_bytes()
            result = self._run_legacy_final(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
