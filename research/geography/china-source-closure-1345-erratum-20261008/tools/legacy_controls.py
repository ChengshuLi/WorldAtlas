#!/usr/bin/env python3
"""Reproduce the original CLI's input-binding and output-path gaps in fixtures."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reproduce  # noqa: E402


def main(vintage: str):
    immutable = reproduce.load_immutable()
    baseline, _, _ = reproduce.pinned_inputs(immutable)
    handoff_path, contract_path = reproduce.INPUT_FILES["handoff"][0], reproduce.INPUT_FILES["contract"][0]
    handoff_raw = baseline.pinned_bytes(handoff_path)
    contract_raw = baseline.pinned_bytes(contract_path)
    lock_raw = baseline.pinned_bytes(reproduce.INPUT_FILES["lock"][0])
    cli_raw = baseline.pinned_bytes(reproduce.INPUT_FILES["assembler"][0])
    node = reproduce.node_runtime()
    packet_rel = reproduce.PREDECESSOR
    all_records = []

    with tempfile.TemporaryDirectory(prefix="legacy-controls-", dir=reproduce.BASE / reproduce.OWNED) as temp:
        root = Path(temp) / "fixture"
        root.mkdir()
        reproduce.fixture(root, baseline, handoff_raw, contract_raw, lock_raw, cli_raw)
        packet = root / packet_rel
        hand_file = packet / "inputs/complete-source-ready-handoff.json"
        contract_file = packet / "inputs/candidate-contract.json"
        lock_file = packet / "inputs/frozen-input-lock.json"
        cli = packet / "tools/assemble-source-closure.mjs"
        guarded = root / reproduce.OWNED / "tools/reproduce.py"
        guarded.parent.mkdir(parents=True, exist_ok=True)
        guarded.write_bytes((reproduce.BASE / reproduce.OWNED / "tools/reproduce.py").read_bytes())

        def call(*args):
            return subprocess.run([str(node), str(cli), *map(str, args)], cwd=root, text=True,
                                  capture_output=True, timeout=180)

        def write_hand(value):
            hand_file.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")))

        def wrapper_rejection(control_name):
            attempted = subprocess.run([sys.executable, str(guarded), control_name], cwd=root, text=True,
                                       capture_output=True, timeout=180)
            output_dir = root / reproduce.OWNED / "vintages" / control_name
            record = {"control": "guarded-runner-rejects-" + control_name, "expected": "reject before compute/publication",
                      "exit_code": attempted.returncode, "failure": attempted.stderr[-1200:],
                      "output_vintage_created": output_dir.exists()}
            if attempted.returncode == 0 or output_dir.exists():
                raise AssertionError("Guarded runner accepted altered fixture: " + control_name)
            all_records.append(record)

        def lock_and_run(output_name):
            lock_file.unlink() if lock_file.exists() else None
            lock_cmd = call("--write-lock")
            if lock_cmd.returncode:
                raise RuntimeError("Legacy --write-lock control failed: " + lock_cmd.stderr[-1200:])
            output = root / output_name
            result = call(output)
            return result, output

        original_hand = json.loads(handoff_raw)
        # Changed candidate with a fixed accepted lock must fail before output.
        candidate_case = json.loads(json.dumps(original_hand))
        component_id = candidate_case["complete_family_scope_and_diagnostics"]["whole_families"][0]["accounting"]["complete_component_ids"][0]
        candidate_case["complete_candidate_pointsets"][component_id]["geometry"]["coordinates"][0][0][0] += 0.00001
        write_hand(candidate_case)
        fixed = call(root / "fixed-lock-rejected.json")
        fixed_output_exists = (root / "fixed-lock-rejected.json").exists()
        wrapper_rejection("guard-fixed-candidate")
        all_records.append({"control": "candidate-change-fixed-lock", "expected": "reject", "exit_code": fixed.returncode,
                            "failure": fixed.stderr[-1200:], "output_created": fixed_output_exists,
                            "mutated_handoff_sha256": reproduce.sha(hand_file.read_bytes()),
                            "accepted_handoff_sha256": reproduce.HANDOFF_SHA})
        if fixed.returncode == 0 or fixed_output_exists:
            raise AssertionError("Fixed original lock unexpectedly accepted changed candidate")

        # Legacy escape: recomputing its lock from the same changed handoff admits it.
        changed_candidate, candidate_output = lock_and_run("candidate-rebound.json")
        if changed_candidate.returncode or not candidate_output.exists():
            raise AssertionError("Could not reproduce legacy cochanged-lock candidate acceptance")
        wrapper_rejection("guard-cochanged-candidate")
        candidate_report = json.loads(candidate_output.read_text())
        changed_geometry = candidate_report["families"][candidate_case["complete_family_scope_and_diagnostics"]["whole_families"][0]["accounting"]["family"]]["complete_component_pointsets"][component_id]["geometry"]
        all_records.append({"control": "candidate-change-cochanged-lock", "expected": "legacy accepts; wrapper anchor rejects",
                            "lock_write_exit": 0, "cli_exit_code": changed_candidate.returncode,
                            "output": immutable.descriptor("candidate-rebound.json", candidate_output.read_bytes()),
                            "changed_geometry_matches_input": changed_geometry == candidate_case["complete_candidate_pointsets"][component_id]["geometry"],
                            "fixed_anchor_rejection": "hand-off whole-body SHA differs from accepted #1337 input"})
        if changed_geometry != candidate_case["complete_candidate_pointsets"][component_id]["geometry"]:
            raise AssertionError("Legacy candidate rebound did not reach published report")

        # Whole-family body is not bound by the old lock's copied accounting hash.
        family_case = json.loads(handoff_raw)
        family = family_case["complete_family_scope_and_diagnostics"]["whole_families"][0]
        family["whole_family"]["complete_positive_length_neighbor_ids"].append("physical-component:control-only-foreign")
        copied_checksum = family["accounting"]["family_row_sha256"]
        write_hand(family_case)
        family_result, family_output = lock_and_run("family-body-rebound.json")
        if family_result.returncode or not family_output.exists():
            raise AssertionError("Could not reproduce unbound whole-family body")
        wrapper_rejection("guard-cochanged-family")
        family_report = json.loads(family_output.read_text())
        family_id = family["accounting"]["family"]
        accepted_body = family_report["families"][family_id]["whole_family"]
        all_records.append({"control": "family-body-copied-checksum", "expected": "legacy accepts; wrapper anchor rejects",
                            "exit_code": family_result.returncode, "copied_accounting_checksum": copied_checksum,
                            "foreign_neighbor_survived": "physical-component:control-only-foreign" in accepted_body["complete_positive_length_neighbor_ids"],
                            "output": immutable.descriptor("family-body-rebound.json", family_output.read_bytes())})
        if "physical-component:control-only-foreign" not in accepted_body["complete_positive_length_neighbor_ids"]:
            raise AssertionError("Legacy family-body mutation did not survive full CLI")

        # Restore the accepted original inputs before testing legacy output writes.
        hand_file.write_bytes(handoff_raw)
        contract_file.write_bytes(contract_raw)
        lock_file.write_bytes(lock_raw)

        # Ordinary fixed-lock controls for source, current geography, and subject roster.
        for control_name, rel in [
            ("source-byte-mutation", original_hand["source_encoded_ordinary_pins"][0]["path"]),
            ("current-contact-byte-mutation", "data/geography/part-3.json"),
        ]:
            target = root / rel
            original = baseline.pinned_bytes(rel)
            changed = bytearray(original)
            changed[len(changed) // 2] ^= 1
            target.write_bytes(changed)
            attempted = call(root / (control_name + ".json"))
            output_created = (root / (control_name + ".json")).exists()
            wrapper_rejection("guard-" + control_name)
            all_records.append({"control": control_name, "expected": "reject", "exit_code": attempted.returncode,
                                "failure": attempted.stderr[-1200:], "output_created": output_created,
                                "changed_input_sha256": reproduce.sha(bytes(changed)), "accepted_input_sha256": reproduce.sha(original)})
            if attempted.returncode == 0 or output_created:
                raise AssertionError("Legacy fixed-lock source/current mutation unexpectedly accepted: " + control_name)
            target.write_bytes(original)

        changed_contract = json.loads(contract_raw)
        changed_contract["evidence_quality"]["subject_ids"][0] = "gb:CHN:ADM2:control-foreign"
        contract_file.write_text(json.dumps(changed_contract, ensure_ascii=False, separators=(",", ":")))
        subject_attempt = call(root / "subject-roster-mutation.json")
        subject_output = (root / "subject-roster-mutation.json").exists()
        wrapper_rejection("guard-subject-roster")
        all_records.append({"control": "subject-roster-mutation", "expected": "reject", "exit_code": subject_attempt.returncode,
                            "failure": subject_attempt.stderr[-1200:], "output_created": subject_output,
                            "mutated_contract_sha256": reproduce.sha(contract_file.read_bytes()), "accepted_contract_sha256": reproduce.CONTRACT_SHA})
        if subject_attempt.returncode == 0 or subject_output:
            raise AssertionError("Legacy fixed lock unexpectedly accepted changed subject roster")
        contract_file.write_bytes(contract_raw)

        sentinel = root / "sentinel.json"
        sentinel.write_bytes(b"ORIGINAL-VINTAGE\n")
        before = sentinel.read_bytes()
        overwritten = call(sentinel)
        all_records.append({"control": "sentinel-overwrite", "expected": "legacy overwrites", "exit_code": overwritten.returncode,
                            "before_sha256": reproduce.sha(before), "after": immutable.descriptor("sentinel.json", sentinel.read_bytes()),
                            "overwritten": sentinel.read_bytes() != before})
        if overwritten.returncode or sentinel.read_bytes() == before:
            raise AssertionError("Could not reproduce legacy sentinel overwrite")

        dangling = root / "dangling-output.json"
        dangling_target = root / "dangling-target.json"
        dangling.symlink_to(dangling_target)
        dangling_run = call(dangling)
        all_records.append({"control": "dangling-output-symlink", "expected": "legacy follows symlink", "exit_code": dangling_run.returncode,
                            "link_remains": dangling.is_symlink(), "target_created": dangling_target.exists(),
                            "target": immutable.descriptor("dangling-target.json", dangling_target.read_bytes()) if dangling_target.exists() else None})
        if dangling_run.returncode or not dangling.is_symlink() or not dangling_target.exists():
            raise AssertionError("Could not reproduce legacy dangling symlink write")

        real_dir = root / "symlink-destination"
        real_dir.mkdir()
        redirected = root / "redirected-parent"
        redirected.symlink_to(real_dir, target_is_directory=True)
        redirected_path = redirected / "parent-output.json"
        parent_run = call(redirected_path)
        real_output = real_dir / "parent-output.json"
        all_records.append({"control": "symlink-parent", "expected": "legacy follows symlink parent", "exit_code": parent_run.returncode,
                            "link_remains": redirected.is_symlink(), "target_created": real_output.exists(),
                            "target": immutable.descriptor("symlink-destination/parent-output.json", real_output.read_bytes()) if real_output.exists() else None})
        if parent_run.returncode or not redirected.is_symlink() or not real_output.exists():
            raise AssertionError("Could not reproduce legacy symlink-parent write")

    failed_vintage = vintage + "-partial-failure"
    failed_writer = immutable.NewVintage(baseline, reproduce.OWNED, failed_vintage,
                                         ["first.json", "second.json"])
    original_link = immutable.os.link

    def fail_completion(source, destination):
        if Path(destination).name == "publication.json":
            raise OSError("fixture completion-link failure")
        return original_link(source, destination)

    try:
        with mock.patch.object(immutable.os, "link", side_effect=fail_completion):
            failed_writer.publish_bytes({"first.json": b"first\n", "second.json": b"second\n"})
        raise AssertionError("Completion failure injection did not fail")
    except OSError as error:
        if str(error) != "fixture completion-link failure":
            raise
    partial = {"control": "completion-receipt-last-failure", "expected": "partial outputs remain unaccepted",
               "failure": "fixture completion-link failure", "publication_exists": (failed_writer.root / "publication.json").exists(),
               "outputs": [immutable.descriptor(str((failed_writer.root / name).relative_to(reproduce.BASE)), (failed_writer.root / name).read_bytes())
                           for name in ("first.json", "second.json")],
               "incomplete_receipt_exists": (failed_writer.root / ".publication-incomplete").exists()}
    if partial["publication_exists"] or not partial["incomplete_receipt_exists"]:
        raise AssertionError("Expected incomplete failed-vintage receipt state")

    output = {"version": 1, "status": "complete", "baseline": reproduce.BASELINE_COMMIT,
              "scope": "Private fixture only; no output or source outside owned packet was touched.",
              "legacy_cli_sha256": reproduce.ASSEMBLER_SHA,
              "code_pins": {"guarded_runner": reproduce.sha((reproduce.BASE / reproduce.OWNED / "tools/reproduce.py").read_bytes()),
                            "controls_runner": reproduce.sha(Path(__file__).read_bytes()),
                            "immutable_helper": reproduce.IMMUTABLE_SHA},
              "runtime": {"node": subprocess.check_output([str(node), "--version"], text=True).strip(), "node_sha256": reproduce.NODE_SHA,
                          "python_version": sys.version, "python_sha256": reproduce.PYTHON_SHA},
              "controls": all_records + [partial],
              "interpretation": ["Legacy write-lock can rebind a changed candidate to itself; fixed accepted handoff bytes prevent that in reproduce.py.",
                                 "Legacy lock omits a full whole-family body binding; immutable accepted handoff hash protects it in reproduce.py.",
                                 "Legacy CLI overwrites files and follows leaf and parent symlinks; NewVintage admits every output path before compute and publishes exclusively."]}
    writer = immutable.NewVintage(baseline, reproduce.OWNED, vintage, ["legacy-controls.json"])
    payload = immutable.canonical_json(output)
    published = writer.publish_bytes({"legacy-controls.json": payload})
    if (writer.root / "legacy-controls.json").read_bytes() != payload:
        raise ValueError("Control report readback mismatch")
    receipt = json.loads((writer.root / "publication.json").read_bytes())
    if receipt.get("status") != "complete" or receipt.get("outputs") != published:
        raise ValueError("Control publication receipt readback mismatch")
    print(json.dumps({"vintage": vintage, "controls": len(output["controls"]), "path": str(writer.root / "legacy-controls.json")}))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: legacy_controls.py FRESH-VINTAGE")
    main(sys.argv[1])
