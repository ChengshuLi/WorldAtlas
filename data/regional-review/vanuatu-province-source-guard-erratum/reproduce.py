#!/usr/bin/env python3
"""Fresh-output Vanuatu source reconciliation and frozen-screen reproduction."""
from __future__ import annotations

import ast
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OWNED = ROOT / "data/regional-review/vanuatu-province-source-guard-erratum"
PINS_PATH = OWNED / "source/input-pins.json"
SIMPLIFIED = OWNED / "source/geoBoundaries-VUT-ADM1_simplified.geojson"
FULL_PATH = "data/regional-review/regional-review-1aa97b490604ea4e/sources/vanuatu-2017-adm1.geojson"
PACKET = "data/regional-review/vanuatu-province-boundary-reconciliation-20261005/"
IDS = [
    "gb:VUT:ADM1:32282491B17169683382430",
    "gb:VUT:ADM1:32282491B5439526076152",
    "gb:VUT:ADM1:32282491B61228346728599",
    "gb:VUT:ADM1:32282491B7486560380604",
    "gb:VUT:ADM1:32282491B78905986242135",
    "gb:VUT:ADM1:32282491B8417950609019",
]
SIMPLIFIED_SHA256 = "63e1878b1a484787aafa029e3f2a8cb063d9d720b38e9d17884a999d28cd10f8"
FULL_SHA256 = "69f44b96d0690310c67a4a430488fb7a02d028bdec8bbc755436cdfb90962c8d"
SOURCE_COMMIT = "9469f09592ced973a3448cf66b6100b741b64c0d"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_digest(raw: bytes, expected_sha: str, expected_bytes: int) -> None:
    if len(raw) != expected_bytes or sha(raw) != expected_sha:
        raise ValueError("whole-file input pin mismatch")


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def safe_relative(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or "\\" in value or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("unsafe output path")
    return candidate


def checked_target(relative: str) -> Path:
    rel = safe_relative(relative)
    target = OWNED / rel
    if not target.resolve(strict=False).is_relative_to(OWNED.resolve()):
        raise ValueError("output escapes owned path")
    cursor = OWNED
    for part in rel.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("symlink in output path")
    if target.is_symlink():
        raise ValueError("symlink output target")
    return target


def publish_exclusive(relative: str, raw: bytes) -> dict:
    target = checked_target(relative)
    if target.exists():
        raise FileExistsError(f"output already exists; preserved: {relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".vanuatu-evidence-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    finally:
        os.unlink(temporary)
    return {"path": str(target.relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-one", default="20261007-fresh-seven")
    parser.add_argument("--run-two", default="20261007-fresh-eight")
    args = parser.parse_args()
    for value in (args.run_one, args.run_two):
        if not value or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in value) or value[0] == "-":
            raise ValueError("vintage names may contain lowercase letters, digits and hyphens only")
    if args.run_one == args.run_two:
        raise ValueError("two unique fresh vintage names are required")
    pins_doc = json.loads(PINS_PATH.read_text())
    pins = pins_doc["pins"]
    runner_pin = pins_doc.get("reproduce_py_sha256")
    if not runner_pin or sha(Path(__file__).read_bytes()) != runner_pin:
        raise ValueError("runner canonical code pin mismatch")
    by_key = {(x["commit"], x["path"]): x for x in pins}
    # Verify exact source, original producer, original output, and shared helper bytes
    # before importing or executing any pinned code.
    for row in pins:
        raw = git_blob(row["commit"], row["path"])
        try:
            verify_digest(raw, row["sha256"], row["bytes"])
        except ValueError as error:
            raise ValueError(f"pinned Git object mismatch: {row['path']} at {row['commit']}")
    source_raw = SIMPLIFIED.read_bytes()
    verify_digest(source_raw, SIMPLIFIED_SHA256, 133712)

    measurement = pins_doc["measurement_baseline_commit"]
    packet = pins_doc["original_packet_commit"]
    # The index and every indexed world part are pinned at the historical metric vintage.
    spatial_rows = [x for x in pins if x["commit"] == measurement]
    if len([x for x in spatial_rows if x["path"].startswith("data/geography/")]) != 36:
        raise ValueError("expected all 36 indexed world parts")
    sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts/evidence")]
    from immutable import Baseline, canonical_json

    baseline_files = [
        {"path": x["path"], "sha256": x["sha256"], "bytes": x["bytes"], "hash_kind": "file-bytes"}
        for x in spatial_rows
    ]
    baseline = Baseline(ROOT, measurement, baseline_files)

    # Execute the exact pinned original producer's calculations with the complete
    # historical baseline pin set, removing only its final overwrite-capable write.
    original_path = PACKET + "reproduce.py"
    original_bytes = git_blob(packet, original_path)
    tree = ast.parse(original_bytes, filename=original_path)
    write_nodes = [
        n for n in tree.body
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "write_text"
    ]
    if len(write_nodes) != 1:
        raise ValueError("original producer write boundary changed")
    tree.body.remove(write_nodes[0])
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PINS" for t in node.targets):
            node.value = ast.parse(repr({x["path"]: (x["sha256"], x["bytes"]) for x in spatial_rows})).body[0].value
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ROOT" for t in node.targets):
            node.value = ast.parse("Path(__file__).resolve().parents[3]").body[0].value
    namespace = {"__file__": str(OWNED / "reproduce.py"), "__name__": "__vanuatu_frozen_original__"}
    exec(compile(tree, original_path, "exec"), namespace)
    result = namespace["result"]

    full = json.loads(baseline.read(FULL_PATH))
    simplified = json.loads(source_raw)
    full_by_id = {f["properties"]["shapeID"]: f for f in full["features"]}
    simple_by_id = {f["properties"]["shapeID"]: f for f in simplified["features"]}
    expected = [identity.rsplit(":", 1)[1] for identity in IDS]
    if len(full_by_id) != 6 or len(simple_by_id) != 6 or set(full_by_id) != set(expected) or set(simple_by_id) != set(expected):
        raise ValueError("full or simplified source roster differs from the exact six subjects")
    for shape_id in expected:
        a, b = full_by_id[shape_id], simple_by_id[shape_id]
        for field in ("shapeID", "shapeName", "shapeType"):
            if a["properties"].get(field) != b["properties"].get(field):
                raise ValueError(f"full/simplified native identity mismatch: {shape_id} {field}")
    meta = json.loads((OWNED / "source/geoBoundaries-VUT-ADM1-metaData.json").read_text())
    result["source_digest_reconciliation"] = {
        "status": "reconciled_distinct_full_and_simplified_products",
        "upstream_repository": "wmgeolab/geoBoundaries",
        "upstream_commit": SOURCE_COMMIT,
        "registry_digest_matches_simplified_lfs_oid": SIMPLIFIED_SHA256,
        "simplified": {"path": "source/geoBoundaries-VUT-ADM1_simplified.geojson", "bytes": len(source_raw), "sha256": sha(source_raw)},
        "full": {"path": FULL_PATH, "bytes": len(baseline.read(FULL_PATH)), "sha256": sha(baseline.read(FULL_PATH))},
        "metadata": {"boundaryID": meta.get("boundaryID"), "boundaryYear": meta.get("boundaryYear"), "boundaryType": meta.get("boundaryType"), "sourceDataUpdateDate": meta.get("sourceDataUpdateDate"), "license": "ODbL-1.0"},
        "native_feature_count": 6,
        "matching_native_shape_ids": expected,
        "matching_fields": ["shapeID", "shapeName", "shapeType"],
        "interpretation": "The registry SHA is the upstream simplified LFS payload, while the retained historical screen consumes the distinct full payload. Matching IDs/names/types establishes product identity only; it does not establish current legal boundary correctness or justify substituting simplified geometry into the historic screen.",
    }
    result["baseline_commit"] = measurement
    result["original_packet_commit"] = packet
    encoded = canonical_json(result)
    for vintage in (args.run_one, args.run_two):
        publish_exclusive(f"vintages/{vintage}/reproduction.json", encoded)
    print(json.dumps({"status": "passed", "subjects": len(result["subjects"]), "metrics": len(result["subjects"]) * 4, "sha256": sha(encoded)}, indent=2))


if __name__ == "__main__":
    main()
