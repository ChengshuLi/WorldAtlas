#!/usr/bin/env python3
"""Bind the five exact Greenland candidate pointsets from retained whole files.

This performs exact ID lookup and JSON passthrough only. It does not calculate
spatial intersections, source coverage, native cells, or geography changes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMMIT = "59acfabec9a22acebdb312010d37a43c8956ba8f"
RESTORED_ROOT = "research/geography/indonesia-borneo-source-fitness-20261007/vintages/restore-450126d0"
IDS = {
    "physical-component:0441b8d2c49152a8ad4e5c8a0426eba450eb7298957b46eceadcac5c59c904ad": "components-000.json",
    "physical-component:074e4f2fbdd5d53d94cd654c9737406325cfc851b36abb17940b3609187a2cc2": "components-000.json",
    "physical-component:26f7658cfe2bed03c9cca108e8c2d08277f9efdd0a8143c308a7d6d0357662ee": "components-001.json",
    "physical-component:f840c42d9967e89c74e47e4693392c474df5bfd4014d7c04acee9d04f58ed2f5": "components-010.json",
    "physical-component:ff63cb9b104fd5baada0f18a8426c9d0e11ddb99ceed1392c7f6f715e4b27064": "components-010.json",
}
EXPECTED_SHA256 = {
    "components-000.json": "eac8b87294e31722939ff834289c00be512312ab83e81720d4fabd577cd5da36",
    "components-001.json": "10d2e853604b368fb9f0dbeb29919bec472640c98b457019865ff02e266a883a",
    "components-010.json": "6a432ffbe3d9a8d4412140438c960b0113f752cb70c2db20b76c7467e9575025",
}
EXPECTED_BYTES = {
    "components-000.json": 8387182,
    "components-001.json": 8388214,
    "components-010.json": 6909917,
}
OUT = Path(__file__).with_name("greenland-five-pointset-bindings.json")


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    restoration_path = f"{RESTORED_ROOT}/custody-restoration.json"
    restoration_raw = git_bytes(COMMIT, restoration_path)
    restoration = json.loads(restoration_raw)
    assert restoration["source_commit"] == "450126d04c7e6bf85c8763c9bb6949c1fac68000"
    assert restoration["authenticated_candidate_commit"] == "efa2e50fa6a40a7be5004d55bca3ff1653ca0dfe"
    assert restoration["method"] == (
        "Exact gzip decompression of each entire custody-v3 components-v3 payload; "
        "no filtering, recoding, geometry rewrite, or repair."
    )

    source_files = {}
    rows = []
    for component_id, filename in IDS.items():
        if filename not in source_files:
            path = f"{RESTORED_ROOT}/{filename}"
            raw = git_bytes(COMMIT, path)
            assert len(raw) == EXPECTED_BYTES[filename]
            assert sha(raw) == EXPECTED_SHA256[filename]
            document = json.loads(raw)
            assert document.get("type") == "FeatureCollection"
            source_files[filename] = {
                "path": path,
                "bytes": len(raw),
                "sha256": sha(raw),
                "feature_count": len(document["features"]),
                "features": document["features"],
            }
        features = source_files[filename]["features"]
        matches = [(ordinal, feature) for ordinal, feature in enumerate(features)
                   if feature.get("id") == component_id]
        assert len(matches) == 1, f"Expected exactly one original feature for {component_id}"
        ordinal, feature = matches[0]
        assert feature.get("geometry") and feature["geometry"].get("type") == "Polygon"
        rows.append({
            "component_id": component_id,
            "source_file": filename,
            "feature_ordinal_zero_based": ordinal,
            "original_feature": feature,
        })

    assert len(rows) == len(IDS) and len({row["component_id"] for row in rows}) == len(IDS)
    output = {
        "version": 1,
        "status": "exact-original-pointsets-bound",
        "scope": "five Greenland candidate features; exact whole-file ID lookup only",
        "commit": COMMIT,
        "restoration_receipt": {
            "path": restoration_path,
            "bytes": len(restoration_raw),
            "sha256": sha(restoration_raw),
            "source_commit": restoration["source_commit"],
            "authenticated_candidate_commit": restoration["authenticated_candidate_commit"],
            "custody_index": restoration["custody_index"],
            "method": restoration["method"],
        },
        "source_files": {
            name: {key: value for key, value in record.items() if key != "features"}
            for name, record in source_files.items()
        },
        "candidates": rows,
        "limits": [
            "The original candidate features above are authoritative pointset inputs for engineering measurement.",
            "The existing target-overlay report used retained GSHHG mapped-land support geometry, not these original candidate pointsets.",
            "No spatial operation was performed by this binding step.",
            "Original water_status is unverified; physical authority, cause, and repair readiness remain unresolved.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "candidates": len(rows),
                      "source_files": len(source_files), "output": str(OUT)}))


if __name__ == "__main__":
    main()
