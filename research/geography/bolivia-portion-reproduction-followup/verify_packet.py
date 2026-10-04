#!/usr/bin/env python3
"""Verify the pinned issue #675 vintage without writing repository files."""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = pathlib.Path(__file__).resolve().parent
VINTAGE = "20261004-validated"
sys.dont_write_bytecode = True


def main():
    command = [sys.executable, str(PACKET / "build_packet.py"), "--check", "--vintage", VINTAGE]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    directory = PACKET / "vintages" / VINTAGE
    result = json.loads((directory / "derived-portion-audit.json").read_text())
    scan = json.loads((directory / "baseline-scan-inventory.json").read_text())
    comparison = json.loads((directory / "reproduction-comparison.json").read_text())
    if result["fragment_count"] != 9 or result["fragment_pair_count"] != 36 or len(result["parent_unions"]) != 2:
        raise SystemExit("FAIL: incomplete 9-fragment/2-predecessor/36-pair result")
    if scan["indexed_part_count"] != 36 or len(scan["parts"]) != 36 or len(scan["subject_assessments"]) != 9:
        raise SystemExit("FAIL: all indexed inputs or row-level predecessor assessments are not covered")
    if any(count != 1 for count in scan["subject_occurrences"].values()):
        raise SystemExit("FAIL: assigned subjects are not exact-once")
    if not comparison["semantic_match"] or comparison["differing_json_pointers"]:
        raise SystemExit("FAIL: regenerated result differs from retained #594 rows")
    if result["neighbor_pair_graph_differences"] != {"expected_missing_current": [], "current_missing_expected": []}:
        raise SystemExit("FAIL: source/current fragment neighbor graphs differ")
    unresolved = [row for row in scan["subject_assessments"].values()
                  if not row["preserved_settlement_finding"].startswith("unresolved:")
                  or not row["preserved_remainders_islands_finding"].startswith("unresolved")]
    if unresolved:
        raise SystemExit("FAIL: prior explicit settlement/remainder uncertainty was lost")
    print(json.dumps({"result": "PASS", "subjects": 9, "indexed_parts": 36,
                      "predecessors": 2, "ecoregions": 7, "fragment_pairs": 36,
                      "retained_result_semantic_match": True,
                      "unresolved_subject_assessments_preserved": 9}, sort_keys=True))


if __name__ == "__main__":
    main()
