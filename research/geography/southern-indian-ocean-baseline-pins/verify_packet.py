#!/usr/bin/env python3
"""Verify the retained #654 reproduction packet without mutating its sources."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/southern-indian-ocean-baseline-pins/"
sys.path.insert(0, str(ROOT))
from scripts.evidence.immutable import Baseline  # noqa: E402
from build_packet import (  # noqa: E402
    BASELINE_COMMIT, IDS, OUT, SOURCE_SNAPSHOT_COMMIT, SCOPE_PATH,
    sha256, validate_request_pins,
)

manifest_path = ROOT / OWNED / "evidence-quality.json"
manifest = json.loads(manifest_path.read_text())
scope = json.loads((ROOT / SCOPE_PATH).read_text())
validate_request_pins(scope)
if manifest["issue"] != 654 or manifest["lane"] != "geography" or manifest["subject_ids"] != IDS:
    raise ValueError("Manifest differs from the exact issue #654 subject scope")
if manifest["baseline"]["commit"] != BASELINE_COMMIT:
    raise ValueError("Manifest baseline is not the preserved #439 evaluation commit")
if manifest["baseline"]["subject_files"] != {
    "atlas:coverage:ATF-5916": "data/geography/part-28.json",
    "atlas:coverage:ATF-5917": "data/geography/part-28.json",
    "atlas:coverage:ATF-5918": "data/geography/part-28.json",
    "atlas:coverage:HMD+00?": "data/geography/part-28.json",
}:
    raise ValueError("Manifest actual containing-file map differs from the verified baseline crosswalk")

baseline = Baseline(ROOT, manifest["baseline"]["commit"], manifest["baseline"]["files"])
for row in manifest["outputs"]:
    raw = (ROOT / row["path"]).read_bytes()
    if len(raw) != row["bytes"] or sha256(raw) != row["sha256"]:
        raise ValueError("Output descriptor mismatch: " + row["path"])
crosswalk_path = ROOT / (OWNED + "vintages/20261004-pinned-geography-inputs/baseline-source-crosswalk.json")
crosswalk = json.loads(crosswalk_path.read_text())
if crosswalk["baseline_commit"] != BASELINE_COMMIT or crosswalk["source_snapshot_commit"] != SOURCE_SNAPSHOT_COMMIT:
    raise ValueError("Crosswalk baseline/source snapshot identity mismatch")
if [row["id"] for row in crosswalk["subjects"]] != IDS:
    raise ValueError("Crosswalk subject inventory mismatch")
checks = crosswalk["checks"]
for key, value in checks.items():
    if key in {"canonical_grid_counts_recomputed", "geographic_conclusions_recomputed"}:
        if value is not False:
            raise ValueError("Packet must keep inherited grid/geographic conclusions archived")
    elif key == "world_index_part_count":
        if value != 36:
            raise ValueError("Unexpected frozen world-index part inventory")
    elif value is not True:
        raise ValueError("Missing exact baseline verification result: " + key)
reproduction = ROOT / (OWNED + "vintages/20261004-pinned-geography-inputs/reproducibility-control.json")
control = json.loads(reproduction.read_text())
if control["run_one_sha256"] != control["run_two_sha256"]:
    raise ValueError("Recorded independent rebuild hashes differ")
subprocess.run([sys.executable, str(OUT / "build_packet.py"), "--check", "--vintage", "20261004-pinned-geography-inputs"],
               cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
print(json.dumps({"result": "PASS", "baseline_files": len(manifest["baseline"]["files"]),
                  "outputs": len(manifest["outputs"]), "subjects": len(IDS),
                  "source_snapshot_commit": SOURCE_SNAPSHOT_COMMIT}, indent=2))
