#!/usr/bin/env python3
"""Verify #605's immutable reproduction, saved controls and evidence manifest."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import build_packet as bp

MANIFEST_PATH = bp.OUT / "evidence-quality.json"

def main() -> None:
    scope = json.loads((bp.ROOT / bp.SCOPE_PATH).read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest["issue"] != 605 or manifest["lane"] != "geography" or manifest["subject_ids"] != scope["subject_ids"]:
        raise ValueError("Evidence manifest differs from exact issue scope")
    if manifest["worker_id"] != scope["worker_id"]:
        raise ValueError("Evidence worker identity differs from reservation")
    if manifest["baseline"]["commit"] != bp.BASELINE_COMMIT:
        raise ValueError("Manifest baseline differs from the preserved #486 evaluation baseline")
    if manifest["baseline"]["subject_files"] != {
        row["id"]: row["actual_containing_file"] for row in json.loads(
            (bp.ROOT / (bp.OWNED + "vintages/" + bp.VINTAGE + "/baseline-source-crosswalk.json")).read_text()
        )["subject_inventory"]
    }:
        raise ValueError("Manifest subject-to-containing-file crosswalk changed")
    for row in manifest["outputs"]:
        raw = (bp.ROOT / row["path"]).read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("Output descriptor mismatch: " + row["path"])
    controls = json.loads((bp.OUT / "negative-control-results.json").read_text())
    if controls.get("result") != "PASS" or len(controls.get("cases", [])) < 10:
        raise ValueError("Negative-control record incomplete")
    if not controls.get("changed_pin_created_no_output") or not controls.get("existing_output_preserved"):
        raise ValueError("Required failed-pin/overwrite guarantees are not recorded")
    subprocess.run([sys.executable, str(bp.OUT / "build_packet.py"), "--check", "--vintage", bp.VINTAGE],
                   cwd=bp.ROOT, check=True, stdout=subprocess.DEVNULL)
    checked = subprocess.check_output(["node", "scripts/evidence-quality.mjs", str(MANIFEST_PATH.relative_to(bp.ROOT))],
                                      cwd=bp.ROOT, text=True)
    evidence = json.loads(checked)
    if evidence.get("status") not in {"limited", "bytes-verified"}:
        raise ValueError("Evidence-quality validator did not accept the packet")
    print(json.dumps({"result": "PASS", "subjects": len(scope["subject_ids"]),
                      "baseline_files": len(manifest["baseline"]["files"]),
                      "outputs": len(manifest["outputs"]), "negative_controls": len(controls["cases"]),
                      "source_snapshot_commit": bp.SOURCE_SNAPSHOT_COMMIT,
                      "evidence_status": evidence["status"]}, indent=2))


if __name__ == "__main__":
    main()
