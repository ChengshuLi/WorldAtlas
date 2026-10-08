#!/usr/bin/env python3
"""Substantive controls for the bounded #1356 producer correction."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKET = ROOT / "research/geography/east-siberia-assessment-integrity-1130-erratum"
CONTROLS = PACKET / "controls"
VINTAGES = PACKET / "vintages"
RUNNER_PATH = PACKET / "reproduction/reproduce_guarded.py"
BASELINE = "90d5309c6497073a039099241360ba807d0c3722"
ORIGINAL = Path("data/regional-review/regional-review-5cf69eed7fdff0b5")
ANALYZER = ORIGINAL / "reproduction/analyze-geography.py"
RENDERER = ORIGINAL / "reproduction/render-review-table.py"
INVENTORY = ORIGINAL / "reproduction/scope-inventory.run-1.json"
FINAL_VINTAGE = PACKET / "vintages/2026-10-08-integrity-v7"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


spec = importlib.util.spec_from_file_location("guarded", RUNNER_PATH)
guarded = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guarded)


def save_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != data:
            raise AssertionError(f"existing control fixture differs: {path}")
        return
    with path.open("xb") as output:
        output.write(data)


def capture_legacy_false_positive() -> dict:
    pins, pin_data, contract = guarded.git_hashes_and_contract()
    original = (ROOT / ANALYZER).read_bytes()
    if sha(original) != pins[str(ANALYZER)]["sha256"]:
        raise AssertionError("legacy analyzer no longer matches its issue pin")
    fixture_path = CONTROLS / "inventory-name-drift.json"
    inventory = guarded.git_blob(BASELINE, str(INVENTORY))
    old = b"Mukhorshibirsky Rayon"
    if inventory.count(old) != 1:
        raise AssertionError("name-drift fixture anchor is ambiguous")
    save_once(fixture_path, inventory.replace(old, b"AUDITOR WRONG PINNED NAME", 1))
    destination = CONTROLS / "legacy-false-positive-assessment.json"
    source = original.decode("utf-8")
    inventory_anchor = "inventory_path = OWNED / 'reproduction' / 'scope-inventory.run-1.json'"
    output_anchor = "OUT = OWNED / 'reproduction' / 'geography-assessment.json'"
    if source.count(inventory_anchor) != 1 or source.count(output_anchor) != 1:
        raise AssertionError("legacy analyzer redirection anchors changed")
    # Keep generated adapters relocatable across isolated author/reviewer checkouts.
    source = source.replace(inventory_anchor, f"inventory_path = Path({str(fixture_path.relative_to(ROOT))!r})")
    source = source.replace(output_anchor, f"OUT = Path({str(destination.relative_to(ROOT))!r})")
    adapter_path = CONTROLS / "legacy-false-positive-adapter.py"
    save_once(adapter_path, source.encode("utf-8"))
    if not destination.exists():
        run = subprocess.run([sys.executable, str(adapter_path)], cwd=ROOT, capture_output=True, text=True)
        if run.returncode != 0:
            raise AssertionError(f"pinned legacy producer failed its original false-positive control: {run.stderr[-2000:]}")
    output = json.loads(destination.read_text(encoding="utf-8"))
    identity = "gb:RUS:ADM2:50074027B10017540039169"
    row = next(item for item in output["subjects"] if item["id"] == identity)
    if row["current_name"] != "AUDITOR WRONG PINNED NAME" or row["current_name_matches_source"] is not True:
        raise AssertionError("legacy false-positive control was not reproduced")
    return {
        "control": "legacy-pinned-analyzer-accepts-unbound-inventory-name",
        "result": "reproduced",
        "input_sha256": sha(fixture_path.read_bytes()),
        "adapter_sha256": sha(adapter_path.read_bytes()),
        "output_sha256": sha(destination.read_bytes()),
        "subject_id": identity,
        "published_inventory_name": row["current_name"],
        "actual_pinned_feature_name_matches_source": row["current_name_matches_source"],
        "scope_note": "Only inventory read and output path were redirected; pinned science producer logic otherwise remained byte-identical.",
    }


def capture_legacy_writer_controls() -> dict:
    receipt_path = CONTROLS / "legacy-writer-controls.json"
    if receipt_path.exists():
        return json.loads(receipt_path.read_text(encoding="utf-8"))
    pins, _pin_data, _contract = guarded.git_hashes_and_contract()
    analyzer = (ROOT / ANALYZER).read_bytes()
    renderer = (ROOT / RENDERER).read_bytes()
    if sha(analyzer) != pins[str(ANALYZER)]["sha256"] or sha(renderer) != pins[str(RENDERER)]["sha256"]:
        raise AssertionError("legacy writer controls must start from the exact pinned producers")
    analyzer_destination = CONTROLS / "legacy-analyzer-overwrite.json"
    table_destination = CONTROLS / "legacy-renderer-overwrite.tsv"
    analyzer_sentinel = b"ANALYZER OUTPUT SENTINEL; preserve unless writer is unsafe\n"
    table_sentinel = b"RENDERER OUTPUT SENTINEL; preserve unless writer is unsafe\n"
    for destination, sentinel in ((analyzer_destination, analyzer_sentinel), (table_destination, table_sentinel)):
        if not destination.exists() and not destination.is_symlink():
            save_once(destination, sentinel)
    initial = {"analyzer": sha(analyzer_sentinel), "renderer": sha(table_sentinel)}

    analyzer_source = analyzer.decode("utf-8")
    analyzer_anchor = "OUT = OWNED / 'reproduction' / 'geography-assessment.json'"
    if analyzer_source.count(analyzer_anchor) != 1:
        raise AssertionError("pinned analyzer output anchor is not unique")
    analyzer_source = analyzer_source.replace(
        analyzer_anchor, f"OUT = Path({str(analyzer_destination.relative_to(ROOT))!r})")
    analyzer_adapter = CONTROLS / "legacy-analyzer-overwrite-adapter.py"
    save_once(analyzer_adapter, analyzer_source.encode("utf-8"))
    expected_analyzer = pins[str(ORIGINAL / "reproduction/geography-assessment.json")]["sha256"]
    if sha(analyzer_destination.read_bytes()) == initial["analyzer"]:
        analyzer_run = subprocess.run([sys.executable, str(analyzer_adapter)], cwd=ROOT, capture_output=True, text=True)
        if analyzer_run.returncode != 0:
            raise AssertionError(f"legacy analyzer sentinel run failed: {analyzer_run.stderr[-1500:]}")
    elif sha(analyzer_destination.read_bytes()) != expected_analyzer:
        raise AssertionError("existing analyzer control is neither the original sentinel nor the exact pinned output")

    renderer_source = renderer.decode("utf-8")
    renderer_anchor = "output = root / 'reproduction/subject-assessments.tsv'"
    if renderer_source.count(renderer_anchor) != 1:
        raise AssertionError("pinned renderer output anchor is not unique")
    renderer_source = renderer_source.replace(
        renderer_anchor, f"output = Path({str(table_destination.relative_to(ROOT))!r})")
    renderer_adapter = CONTROLS / "legacy-renderer-overwrite-adapter.py"
    save_once(renderer_adapter, renderer_source.encode("utf-8"))
    expected_table = pins[str(ORIGINAL / "reproduction/subject-assessments.tsv")]["sha256"]
    if sha(table_destination.read_bytes()) == initial["renderer"]:
        renderer_run = subprocess.run([sys.executable, str(renderer_adapter)], cwd=ROOT, capture_output=True, text=True)
        if renderer_run.returncode != 0:
            raise AssertionError(f"legacy renderer sentinel run failed: {renderer_run.stderr[-1500:]}")
    elif sha(table_destination.read_bytes()) != expected_table:
        raise AssertionError("existing table control is neither the original sentinel nor the exact pinned output")
    final = {"analyzer": sha(analyzer_destination.read_bytes()), "renderer": sha(table_destination.read_bytes())}
    if initial == final:
        raise AssertionError("the pinned legacy producers did not overwrite their private sentinels")
    receipt = {
        "control": "pinned-legacy-producer-overwrite-sentinel",
        "result": "both-original-writers-replaced-private-sentinels",
        "source_hashes": {"analyzer": sha(analyzer), "renderer": sha(renderer)},
        "adapter_hashes": {"analyzer": sha(analyzer_adapter.read_bytes()), "renderer": sha(renderer_adapter.read_bytes())},
        "sentinel_hashes_before": initial,
        "output_hashes_after": final,
        "output_bytes_after": {"analyzer": analyzer_destination.stat().st_size, "renderer": table_destination.stat().st_size},
        "outputs": [str(analyzer_destination.relative_to(ROOT)), str(table_destination.relative_to(ROOT))],
        "scope_note": "Only each final output path was redirected to an owned sentinel; original output paths were never opened by these controls.",
    }
    save_once(receipt_path, (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())
    return receipt


def compare_products() -> dict:
    pin_map, _pins, _contract = guarded.git_hashes_and_contract()
    old_assessment_path = ROOT / ORIGINAL / "reproduction/geography-assessment.json"
    old_table_path = ROOT / ORIGINAL / "reproduction/subject-assessments.tsv"
    old = json.loads(old_assessment_path.read_text(encoding="utf-8"))
    for path in (str(ORIGINAL / "reproduction/geography-assessment.json"),
                 str(ORIGINAL / "reproduction/subject-assessments.tsv")):
        if sha((ROOT / path).read_bytes()) != pin_map[path]["sha256"]:
            raise AssertionError(f"retained original output changed: {path}")
    new_path = FINAL_VINTAGE / "run-1/geography-assessment.json"
    new = json.loads(new_path.read_text(encoding="utf-8"))
    if {k: v for k, v in old.items() if k != "subjects"} != {k: v for k, v in new.items() if k != "subjects"}:
        raise AssertionError("non-subject assessment summaries, metrics, source pins or six parents changed")
    old_rows = {r["id"]: r for r in old["subjects"]}
    new_rows = {r["id"]: r for r in new["subjects"]}
    if len(old_rows) != 207 or set(old_rows) != set(new_rows):
        raise AssertionError("the assessment subject identities changed")
    for identity in old_rows:
        left = {k: v for k, v in old_rows[identity].items() if k != "current_source_level"}
        right = {k: v for k, v in new_rows[identity].items() if k != "current_source_level"}
        if left != right:
            raise AssertionError(f"non-provenance assessment values changed for {identity}")
    inventory = json.loads(guarded.git_blob(BASELINE, str(INVENTORY)))
    expected_levels = {r["id"]: r["source_level"] for r in inventory["subjects"]}
    if any(new_rows[identity].get("current_source_level") != expected_levels[identity] for identity in expected_levels):
        raise AssertionError("corrected source-level output differs from the pinned per-feature metadata join")
    if new["summaries"]["classifications"] != {"correction-needed": 22, "insufficient-evidence": 185}:
        raise AssertionError("original 185/22 dispositions changed")
    if len(new["provinces"]) != 6 or new["provinces"] != old["provinces"]:
        raise AssertionError("the six province-parent records changed")

    with old_table_path.open(encoding="utf-8", newline="") as stream:
        old_table = list(csv.DictReader(stream, delimiter="\t"))
    new_table_path = FINAL_VINTAGE / "run-1/subject-assessments.tsv"
    with new_table_path.open(encoding="utf-8", newline="") as stream:
        new_table = list(csv.DictReader(stream, delimiter="\t"))
    if len(old_table) != 213 or len(new_table) != 213:
        raise AssertionError("the review table must keep 207 subjects and six parents")
    table_changes = 0
    for before, after in zip(old_table, new_table):
        if {k: v for k, v in before.items() if k != "source_level_claim"} != {k: v for k, v in after.items() if k != "source_level_claim"}:
            raise AssertionError(f"table field other than source_level_claim changed for {before['record_id']}")
        if before["source_level_claim"] != after["source_level_claim"]:
            table_changes += 1
    if table_changes != 207:
        raise AssertionError(f"expected 207 provenance-only table corrections; observed {table_changes}")
    return {
        "control": "original-output-preservation-and-provenance-only-diff",
        "subjects": 207,
        "parents": 6,
        "assessment_non_provenance_fields_equal": True,
        "table_non_provenance_fields_equal": True,
        "table_provenance_cells_corrected": table_changes,
        "status_counts": {"insufficient-evidence": 185, "correction-needed": 22},
        "legacy_assessment_sha256": sha(old_assessment_path.read_bytes()),
        "legacy_table_sha256": sha(old_table_path.read_bytes()),
        "new_assessment_sha256": sha(new_path.read_bytes()),
        "new_table_sha256": sha(new_table_path.read_bytes()),
    }


class IntegrityControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pin_map, cls.pins, cls.contract = guarded.git_hashes_and_contract()
        cls.inventory_bytes = guarded.git_blob(BASELINE, str(INVENTORY))

    def invoke_preflight(self, vintage: str, arguments: list[str]) -> dict:
        target = VINTAGES / vintage
        self.assertFalse(target.exists() or target.is_symlink(), f"control vintage already exists: {target}")
        command = [sys.executable, str(RUNNER_PATH), "--vintage", vintage, *arguments]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0, "adverse input unexpectedly passed the actual entrypoint")
        self.assertFalse(target.exists() or target.is_symlink(), "failed preflight admitted an output directory")
        return {"returncode": run.returncode, "stderr_tail": run.stderr[-600:], "output_path_absent": True}

    def test_issue_inventory_and_every_feature_join(self) -> None:
        result = guarded.assert_inventory_matches_baseline(self.inventory_bytes, self.pins, self.contract)
        self.assertEqual(len(result["subjects"]), 207)

    def test_actual_legacy_false_positive(self) -> None:
        record = capture_legacy_false_positive()
        self.assertEqual(record["result"], "reproduced")
        self.assertTrue(record["actual_pinned_feature_name_matches_source"])
        for name in (
            "legacy-false-positive-adapter.py",
            "legacy-analyzer-overwrite-adapter.py",
            "legacy-renderer-overwrite-adapter.py",
        ):
            adapter = (CONTROLS / name).read_text(encoding="utf-8")
            self.assertNotIn("/Users/chengshuli/", adapter, f"checkout-specific path in {name}")

    def test_pinned_legacy_writers_replace_only_private_sentinels(self) -> None:
        record = capture_legacy_writer_controls()
        self.assertEqual(record["result"], "both-original-writers-replaced-private-sentinels")

    def test_original_assessment_and_table_are_preserved(self) -> None:
        result = compare_products()
        self.assertTrue(result["assessment_non_provenance_fields_equal"])
        self.assertEqual(result["table_provenance_cells_corrected"], 207)

    def test_actual_entrypoint_rejects_name_drift_before_any_output(self) -> None:
        fixture = CONTROLS / "inventory-name-drift.json"
        self.assertTrue(fixture.is_file())
        self.invoke_preflight("control-name-drift", ["--preflight-inventory", str(fixture.relative_to(ROOT))])

    def test_actual_entrypoint_rejects_code_and_source_byte_drift(self) -> None:
        analyzer_path = str(ANALYZER)
        analyzer = (ROOT / ANALYZER).read_bytes()
        code_fixture = CONTROLS / "analyze-geography-code-drift.py"
        save_once(code_fixture, analyzer.replace(b"source_level", b"source_levex", 1))
        self.invoke_preflight("control-code-drift", ["--preflight-byte-override",
            f"{analyzer_path}={code_fixture.relative_to(ROOT)}"])

        source_path = "data/regional-review/regional-review-5cf69eed7fdff0b5/source/geoboundaries-rus-adm2-2017-metadata.json"
        source = (ROOT / source_path).read_bytes()
        source_fixture = CONTROLS / "source-metadata-drift.json"
        save_once(source_fixture, source.replace(b"ADM2", b"ADMX", 1))
        self.invoke_preflight("control-source-drift", ["--preflight-byte-override",
            f"{source_path}={source_fixture.relative_to(ROOT)}"])

    def test_actual_entrypoint_rejects_identity_parent_member_and_roster_drift(self) -> None:
        original = json.loads(self.inventory_bytes)
        first = original["subjects"][0]["id"]
        overlay_index = next(i for i, r in enumerate(original["subjects"]) if r["source_id"].startswith("resolve:"))
        changes = {}
        duplicate = json.loads(self.inventory_bytes)
        duplicate["subjects"][1]["id"] = duplicate["subjects"][0]["id"]
        changes["duplicate-identity"] = duplicate
        missing = json.loads(self.inventory_bytes)
        missing["subjects"] = [r for r in missing["subjects"] if r["id"] != first]
        changes["missing-identity"] = missing
        parent = json.loads(self.inventory_bytes)
        parent["subjects"][0]["current_parent_id"] = "AUDITOR_WRONG_PARENT"
        changes["parent-drift"] = parent
        member = json.loads(self.inventory_bytes)
        member["subjects"][overlay_index]["source_member_ids"] = []
        changes["source-member-drift"] = member
        for name, fixture_data in changes.items():
            fixture = CONTROLS / f"inventory-{name}.json"
            save_once(fixture, (json.dumps(fixture_data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            self.invoke_preflight(f"control-{name}", ["--preflight-inventory", str(fixture.relative_to(ROOT))])

    def test_fresh_output_admission_preserves_existing_file_and_directory(self) -> None:
        record = VINTAGES / "control-existing-output"
        record.mkdir(parents=True, exist_ok=True)
        sentinel = record / "sentinel.txt"
        save_once(sentinel, b"existing sentinel: do not change\n")
        before = sha(sentinel.read_bytes())
        command = [sys.executable, str(RUNNER_PATH), "--vintage", record.name]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(sha(sentinel.read_bytes()), before)
        self.assertFalse((record / "run-1").exists())

    def test_safe_output_rejects_existing_directory_broken_symlink_and_escape(self) -> None:
        existing = VINTAGES / "control-existing-directory"
        existing.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(FileExistsError):
            guarded.safe_fresh_directory(existing.relative_to(ROOT))

        broken = VINTAGES / "control-broken-symlink"
        if not broken.exists() and not broken.is_symlink():
            broken.symlink_to(PACKET / "controls/no-such-target")
        with self.assertRaises(ValueError):
            guarded.safe_fresh_directory(broken.relative_to(ROOT))

        escape = VINTAGES / "control-path-escape"
        if not escape.exists() and not escape.is_symlink():
            escape.symlink_to(ROOT / "README.md")
        with self.assertRaises(ValueError):
            guarded.safe_fresh_directory(escape.relative_to(ROOT))

        partial = VINTAGES / "control-partial-conflict"
        (partial / "run-1").mkdir(parents=True, exist_ok=True)
        partial_sentinel = partial / "run-1/geography-assessment.json"
        save_once(partial_sentinel, b"partial output sentinel\n")
        partial_hash = sha(partial_sentinel.read_bytes())
        with self.assertRaises(FileExistsError):
            guarded.safe_fresh_directory(partial.relative_to(ROOT))
        self.assertEqual(sha(partial_sentinel.read_bytes()), partial_hash)
        broken.unlink(missing_ok=True)
        escape.unlink(missing_ok=True)
        existing.rmdir()

    def test_pairwise_fresh_run_outputs_and_receipt(self) -> None:
        receipt = json.loads((FINAL_VINTAGE / "reproducibility.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["pairwise_identical"])
        self.assertEqual(len(receipt["runs"]), 2)
        for name in ("geography-assessment.json", "subject-assessments.tsv"):
            self.assertEqual((FINAL_VINTAGE / "run-1" / name).read_bytes(), (FINAL_VINTAGE / "run-2" / name).read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
