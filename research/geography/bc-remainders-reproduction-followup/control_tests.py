#!/usr/bin/env python3
"""Negative controls for issue #667. Writes one receipt only after all pass."""
from __future__ import annotations
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("bc_remainder_reproduction", HERE / "reproduce.py")
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def descriptor(path: str) -> dict:
    data = json.loads((HERE / "input-baseline.json").read_text(encoding="utf-8"))
    return next(row for row in data["files"] if row["path"] == path)


def original_outputs() -> dict[str, str]:
    result = {}
    for rel in (f"{audit.ORIGINAL}/cd-assessments.json", f"{audit.ORIGINAL}/csd-crosswalk.csv"):
        size, digest = audit.hash_path(audit.REPO / rel)
        result[rel] = f"{size}:{digest}"
    return result


class ReproductionControls(unittest.TestCase):
    def test_changed_parent_assessment_fails_before_output(self):
        rel = f"{audit.PARENT}/assessment.json"
        before = original_outputs()
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp)
            target = root / rel
            target.parent.mkdir(parents=True)
            target.write_bytes((audit.REPO / rel).read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Input bytes changed"):
                audit.verify_file(root, descriptor(rel))
        self.assertEqual(before, original_outputs())

    def test_changed_acquired_layer_fails_before_output(self):
        rel = f"{audit.ORIGINAL}/sources/bc-regional-districts-and-stikine.geojson.gz"
        before = original_outputs()
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp)
            target = root / rel
            target.parent.mkdir(parents=True)
            target.write_bytes((audit.REPO / rel).read_bytes() + b"x")
            with self.assertRaisesRegex(ValueError, "Input bytes changed"):
                audit.verify_file(root, descriptor(rel))
        self.assertEqual(before, original_outputs())

    def test_missing_input_fails_before_output(self):
        rel = f"{audit.ORIGINAL}/sources/bc-regional-districts-and-stikine.geojson.gz"
        before = original_outputs()
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            with self.assertRaisesRegex(ValueError, "Missing or non-ordinary input"):
                audit.verify_file(Path(tmp), descriptor(rel))
        self.assertEqual(before, original_outputs())

    def test_source_member_conflict_is_rejected(self):
        conflicting = {"locations": [
            {"location_id": "atlas:location:one", "full_parent_chain": [{"metadata": {"source_member_ids": ["gb:CAN:ADM3:duplicate"]}}]},
            {"location_id": "atlas:location:two", "full_parent_chain": [{"metadata": {"source_member_ids": ["gb:CAN:ADM3:duplicate"]}}]},
        ]}
        with self.assertRaisesRegex(ValueError, "Conflicting source-member assignments"):
            audit.build_member_id_map(conflicting, strict=True)

    def test_existing_output_cannot_be_overwritten(self):
        before = original_outputs()
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            out = Path(tmp) / "existing"
            out.mkdir()
            sentinel = out / "kept.json"
            sentinel.write_text('{"preserve":true}\n', encoding="utf-8")
            old = sentinel.read_bytes()
            arg = out.relative_to(audit.REPO).as_posix()
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                audit.require_new_output(arg)
            self.assertEqual(old, sentinel.read_bytes())
        self.assertEqual(before, original_outputs())


def main() -> None:
    before = original_outputs()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReproductionControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    after = original_outputs()
    if before != after:
        raise SystemExit("Original #609 output bytes changed during controls")
    receipt = {
        "version": 1,
        "method_id": "negative-controls",
        "kind": "measurement",
        "outcome": "passed",
        "controls": [
            {"id": "changed-parent-assessment", "expected": "rejected before output", "outcome": "passed"},
            {"id": "changed-acquired-layer", "expected": "rejected before output", "outcome": "passed"},
            {"id": "missing-input", "expected": "rejected before output", "outcome": "passed"},
            {"id": "conflicting-source-member-map", "expected": "rejected without last-write-wins", "outcome": "passed"},
            {"id": "attempted-overwrite", "expected": "rejected without changing sentinel or original outputs", "outcome": "passed"},
        ],
        "original_outputs_before": before,
        "original_outputs_after": after,
        "retained_originals_changed": False,
    }
    target = HERE / "negative-controls.json"
    if target.exists():
        raise SystemExit("Refusing to overwrite a controls receipt; choose a new issue vintage")
    target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(audit.REPO)}")


if __name__ == "__main__":
    main()
