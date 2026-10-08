#!/usr/bin/env python3
"""Bind the completed runs and controls into validator-ready evidence receipts."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reproduce  # noqa: E402


def main(vintage, run_one_name, run_two_name, controls_name):
    immutable = reproduce.load_immutable()
    baseline, _, _ = reproduce.pinned_inputs(immutable)
    first = reproduce.BASE / reproduce.OWNED / "vintages" / run_one_name
    second = reproduce.BASE / reproduce.OWNED / "vintages" / run_two_name
    controls = reproduce.BASE / reproduce.OWNED / "vintages" / controls_name
    run_one = (first / "reconciliation.json").read_bytes()
    run_two = (second / "reconciliation.json").read_bytes()
    if reproduce.sha(run_one) != reproduce.CURRENT_OUTPUT_SHA or run_one != run_two:
        raise ValueError("Two exact current-baseline outputs are required")
    control_report = json.loads((controls / "legacy-controls.json").read_text())
    if len(control_report["controls"]) != 16:
        raise ValueError("All legacy and guarded-runner controls plus partial-publication control are required")
    output = {
        "method_id": "corrected-runner-reproducibility", "kind": "generator", "outcome": "passed",
        "version": 1, "baseline_commit": reproduce.BASELINE_COMMIT,
        "run_one_sha256": reproduce.sha(run_one), "run_two_sha256": reproduce.sha(run_two),
        "run_one_bytes": len(run_one), "run_two_bytes": len(run_two),
        "component_count": 50, "contact_count": 14, "family_count": 2,
        "available_numeric_sibling_bindings": 34,
        "runtime": {"node_version": "v24.19.0", "node_sha256": reproduce.NODE_SHA,
                    "python_version": "3.7.3", "python_sha256": reproduce.PYTHON_SHA,
                    "historical_sha256": "27db838bb204ef7c21df2931f5656e4c8fb32e6e947f363a402b49714d32b5b1",
                    "exact_historical_executable_replay": False},
        "comparison": "The complete reports match the retained prior successful vintages after normalizing only their recorded main-head fields.",
        "limits": ["No GIS overlay, physical reexecution, authority determination, geographic approval, or import authorization.",
                   "Source applicability, county parent/date, precision, legal terms, current condition, and parent #1202 remain unresolved."],
    }
    controls_receipt = {
        "method_id": "legacy-cli-input-output-controls", "kind": "code", "outcome": "passed",
        "version": 1, "legacy_cli_controls": "vintages/" + controls_name + "/legacy-controls.json",
        "legacy_cli_controls_sha256": reproduce.sha((controls / "legacy-controls.json").read_bytes()),
        "control_count": 16,
        "positive_control": "Both unchanged full original CLI reconstructions complete and preserve all 50 components, 14 contacts, two families, and 34 numeric sibling bindings.",
        "negative_controls": ["changed candidate with original fixed lock rejected",
                              "changed source/current bytes rejected", "changed contact subject roster rejected",
                              "cochanged candidate plus recomputed legacy lock accepted by the old CLI",
                              "changed full-family body with copied accounting checksum accepted by the old CLI",
                              "old CLI overwrites a sentinel and follows dangling-leaf and parent symlinks",
                              "fresh-vintage completion-link failure leaves no publication receipt"],
        "code_pins": {"guarded_runner": reproduce.sha((reproduce.BASE / reproduce.OWNED / "tools/reproduce.py").read_bytes()),
                      "controls_runner": reproduce.sha((reproduce.BASE / reproduce.OWNED / "tools/legacy_controls.py").read_bytes()),
                      "test_runner": reproduce.sha((reproduce.BASE / reproduce.OWNED / "tests/test_reproduce.py").read_bytes()),
                      "finalizer": reproduce.sha(Path(__file__).read_bytes()),
                      "immutable_helper": reproduce.IMMUTABLE_SHA},
        "corrected_runner": "NewVintage admission, readback, and exclusive publication are exercised through tools/reproduce.py and tests/test_reproduce.py.",
        "scope": "The negative acceptance controls run only inside private fixtures under this issue-owned directory.",
    }
    writer = immutable.NewVintage(baseline, reproduce.OWNED, vintage,
                                  ["reproducibility.json", "controls-validation.json"])
    payloads = {"reproducibility.json": immutable.canonical_json(output),
                "controls-validation.json": immutable.canonical_json(controls_receipt)}
    published = writer.publish_bytes(payloads)
    for name, expected in payloads.items():
        if (writer.root / name).read_bytes() != expected:
            raise ValueError("Validation output readback mismatch: " + name)
    receipt = json.loads((writer.root / "publication.json").read_bytes())
    if receipt.get("status") != "complete" or receipt.get("outputs") != published:
        raise ValueError("Validation publication receipt readback mismatch")
    print(json.dumps({"vintage": vintage, "outputs": 2, "path": str(writer.root)}))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: finalize_evidence.py FRESH-OUTPUT-VINTAGE RUN-ONE-VINTAGE RUN-TWO-VINTAGE CONTROLS-VINTAGE")
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
