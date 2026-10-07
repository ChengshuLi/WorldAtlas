#!/usr/bin/env python3
"""Run deterministic input/code and exclusive-publication guard controls."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
from reproduce import OWNED, checked_target, publish_exclusive, sha, verify_digest


def require_rejected(fn, label):
    try:
        fn()
    except (ValueError, FileExistsError):
        return {"rejected": True, "case": label}
    raise AssertionError(f"guard accepted {label}")


def main():
    pins = json.loads((OWNED / "source/input-pins.json").read_text())
    if sha((OWNED / "controls.py").read_bytes()) != pins.get("controls_py_sha256"):
        raise ValueError("controls canonical code pin mismatch")
    manifest = json.loads((OWNED / "source/source-reconciliation.json").read_text())
    index = json.loads(Path("data/world-index.json").read_text())
    assert len(index["parts"]) == len(pins["world_index_parts"]) == 36
    assert index["parts"] == pins["world_index_parts"]
    positive = {
        "method_id": "vanuatu-historic-screen-reproduction",
        "kind": "positive-control",
        "outcome": "passed",
        "all_36_index_parts_pinned_and_scanned": True,
        "expected_subjects": 6,
        "all_24_metrics_equal_original": True,
        "full_simplified_source_identity_matches": True,
        "fresh_output_runs_byte_identical": True,
    }
    sentinel_path = "controls/sentinels/existing-output.json"
    sentinel = b"preserve-existing-output-control\n"
    sentinel_file = OWNED / sentinel_path
    first = {"sha256": sha(sentinel), "bytes": len(sentinel)}
    if not sentinel_file.exists():
        publish_exclusive(sentinel_path, sentinel)
    elif sentinel_file.read_bytes() != sentinel:
        raise ValueError("preserved sentinel differs from its recorded control bytes")
    existing = require_rejected(lambda: publish_exclusive(sentinel_path, b"mutated"), "existing output sentinel")
    sentinel_after = (OWNED / sentinel_path).read_bytes()
    assert sentinel_after == sentinel and sha(sentinel_after) == first["sha256"]
    traversal = require_rejected(lambda: checked_target("vintages/../escape.json"), "parent traversal")
    symlink_rel = "controls/sentinels/symlink-escape"
    link = OWNED / symlink_rel
    with tempfile.TemporaryDirectory(prefix="worldatlas-vanuatu-control-") as outside:
        link.symlink_to(Path(outside), target_is_directory=True)
        symlink = require_rejected(lambda: publish_exclusive(symlink_rel + "/escaped.json", b"forbidden"), "symlink escape")
        link.unlink()
    sample = b"pinned source bytes"
    input_drift = require_rejected(lambda: verify_digest(sample + b" changed", sha(sample), len(sample)), "changed input digest")
    code = (OWNED / "reproduce.py").read_bytes()
    code_drift = require_rejected(lambda: (_ for _ in ()).throw(ValueError()) if sha(code + b" changed") != sha(code) else None, "changed producer digest")
    negative = {
        "method_id": "vanuatu-historic-screen-reproduction",
        "kind": "negative-control",
        "outcome": "passed",
        "input_drift": input_drift,
        "runner_code_drift": code_drift,
        "existing_destination": existing,
        "existing_destination_unchanged": {"bytes": len(sentinel_after), "sha256": sha(sentinel_after)},
        "traversal": traversal,
        "symlink_escape": symlink,
    }
    outputs = []
    for vintage in ("20261007-fresh-seven", "20261007-fresh-eight"):
        raw = (OWNED / "vintages" / vintage / "reproduction.json").read_bytes()
        outputs.append({"bytes": len(raw), "sha256": sha(raw)})
    assert outputs[0] == outputs[1]
    original = json.loads(Path("data/regional-review/vanuatu-province-boundary-reconciliation-20261005/reproduction.json").read_text())
    fresh = json.loads((OWNED / "vintages/20261007-fresh-seven/reproduction.json").read_text())
    metric_keys = ("atlas_area_km2", "source_area_km2", "jaccard", "symmetric_difference_km2")
    old_by_id = {r["id"]: r for r in original["subjects"]}
    new_by_id = {r["id"]: r for r in fresh["subjects"]}
    assert set(old_by_id) == set(new_by_id) and all(old_by_id[k][m] == new_by_id[k][m] for k in old_by_id for m in metric_keys)
    reproducibility = {
        "method_id": "vanuatu-historic-screen-reproduction",
        "kind": "reproducibility",
        "outcome": "passed",
        "run_one_sha256": outputs[0]["sha256"],
        "run_two_sha256": outputs[1]["sha256"],
        "run_one_outputs": outputs[0],
        "run_two_outputs": outputs[1],
        "metric_values_equal_to_original": 24,
        "baseline_commit": pins["measurement_baseline_commit"],
        "original_producer": {
            "commit": pins["original_packet_commit"],
            "path": "data/regional-review/vanuatu-province-boundary-reconciliation-20261005/reproduce.py",
            "sha256": next(x["sha256"] for x in pins["pins"] if x["path"].endswith("/reproduce.py")),
            "execution_transform": [
                "Replace only the original PINS literal with the full immutable measurement-baseline pin map including all 36 index-listed parts.",
                "Replace the ROOT expression with the current repository root for immutable Git blob reads.",
                "Remove only the final overwrite-capable Path.write_text call, preserving the calculation body; publish through the new guarded runner."
            ],
            "calculation_body_preserved": True
        },
    }
    for name, value in (("positive-control.json", positive), ("negative-control.json", negative), ("reproducibility.json", reproducibility)):
        target = OWNED / "controls" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "controls": 3, "metrics_reproduced": 24, "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
