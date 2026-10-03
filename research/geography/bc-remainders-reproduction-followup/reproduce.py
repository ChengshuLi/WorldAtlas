#!/usr/bin/env python3
"""Read-only check or explicit, exclusive reproduction of issue #609 outputs."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types

OWNED = Path(__file__).resolve().parent
REPO = OWNED.parents[2]
ORIGINAL_COMMIT = "24629e5918a144a1979db80ba7012baea42036e7"
INPUT_BASELINE_SHA256 = "e05d2aab2cd465bc3e3dcb0e47cc2a3a994f81d75cb38a3f2b1c69c6e37a3cb9"
ORIGINAL = "data/regional-review/bc-administrative-remainders-followup-2026"
PARENT = "data/regional-review/regional-review-4254da254d94f450"
TARGETS = ("5901", "5933", "5939", "5941", "5949", "5951", "5953", "5955", "5957", "5959")
MAX_FILE_BYTES = 32 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def hash_path(path: Path) -> tuple[int, str]:
    h, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return size, h.hexdigest()


def hash_git_blob(commit: str, repo_path: str) -> tuple[int, str]:
    row = subprocess.check_output(["git", "-C", str(REPO), "ls-tree", "-z", commit, "--", repo_path]).decode().rstrip("\0")
    if not row.startswith(("100644 ", "100755 ")) or row.split("\t", 1)[-1] != repo_path:
        raise ValueError(f"Expected an ordinary pinned Git input: {repo_path}")
    oid = row.split()[2]
    proc = subprocess.Popen(["git", "-C", str(REPO), "cat-file", "blob", oid], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    h, size = hashlib.sha256(), 0
    assert proc.stdout is not None
    for block in iter(lambda: proc.stdout.read(1024 * 1024), b""):
        h.update(block)
        size += len(block)
    error = proc.stderr.read() if proc.stderr else b""
    if proc.wait() != 0:
        raise RuntimeError(error.decode(errors="replace"))
    return size, h.hexdigest()


def verify_file(root: Path, entry: dict, commit: str | None = None, *, decompress: bool = True) -> None:
    path = root / entry["path"]
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Missing or non-ordinary input: {entry['path']}")
    size, actual = hash_path(path)
    if size != entry["bytes"] or actual != entry["sha256"]:
        raise ValueError(f"Input bytes changed: {entry['path']}")
    if commit:
        blob_size, blob_sha = hash_git_blob(commit, entry["path"])
        if blob_size != size or blob_sha != actual:
            raise ValueError(f"Immutable Git blob mismatch: {entry['path']}")
    if decompress and "uncompressed_sha256" in entry:
        h, raw_size = hashlib.sha256(), 0
        with gzip.open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
                raw_size += len(block)
        if raw_size != entry["uncompressed_bytes"] or h.hexdigest() != entry["uncompressed_sha256"]:
            raise ValueError(f"Uncompressed input bytes changed: {entry['path']}")


def load_input_baseline() -> dict:
    path = OWNED / "input-baseline.json"
    raw = path.read_bytes()
    if sha(raw) != INPUT_BASELINE_SHA256:
        raise ValueError("The input-baseline file changed; do not silently repin this evidence")
    record = json.loads(raw)
    if record.get("baseline_commit") != ORIGINAL_COMMIT:
        raise ValueError("Unexpected original input baseline commit")
    return record


def derived_baseline_commit() -> str:
    # The immutable derivative baseline is the first issue-packet commit. Read
    # its identifier from the evidence manifest so rebasing the packet does not
    # leave a dangling pre-rebase commit SHA in this reproduction tool.
    manifest = json.loads((OWNED / "evidence-quality.json").read_text(encoding="utf-8"))
    commit = manifest.get("baseline", {}).get("commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("Evidence manifest has no valid immutable derivative baseline commit")
    return commit


def verify_original_inputs(record: dict) -> None:
    for entry in record["files"]:
        verify_file(REPO, entry, ORIGINAL_COMMIT)
    by_path = {row["path"]: row for row in record["files"]}
    receipt_path = f"{ORIGINAL}/sources/acquisition-receipt.json"
    receipt = json.loads((REPO / receipt_path).read_text(encoding="utf-8"))
    for name, source in receipt["responses"].items():
        path = f"{ORIGINAL}/{source['retained_path']}"
        entry = by_path.get(path)
        if not entry:
            raise ValueError(f"Acquired source missing from original whole-file inventory: {name}")
        if entry["bytes"] != source["retained_bytes"] or entry["sha256"] != source["retained_sha256"]:
            raise ValueError(f"Acquisition retained-byte receipt mismatch: {name}")
        if source["retained_encoding"].startswith("gzip"):
            if entry.get("uncompressed_bytes") != source["bytes"] or entry.get("uncompressed_sha256") != source["sha256"]:
                raise ValueError(f"Acquisition source-response receipt mismatch: {name}")
        elif entry["bytes"] != source["bytes"] or entry["sha256"] != source["sha256"]:
            raise ValueError(f"Acquisition source-response receipt mismatch: {name}")
    if len(receipt["responses"]) != 32:
        raise ValueError("Unexpected acquired-source response inventory")


def derived_descriptors(record: dict) -> list[dict]:
    prefix = OWNED.relative_to(REPO).as_posix() + "/"
    return [{**row, "path": prefix + row["path"]} for row in record["bounded_derived_inputs"]]


def verify_derived_inputs(record: dict) -> None:
    # Shared immutable preparation helper validates every bounded derivative
    # against commit A; custom streaming pins above cover the >32 MiB originals.
    sys.path.insert(0, str(REPO / "scripts"))
    from evidence.immutable import Baseline
    derived_commit = derived_baseline_commit()
    Baseline(REPO, derived_commit, derived_descriptors(record))
    for row in record["bounded_derived_inputs"]:
        verify_file(REPO, {**row, "path": OWNED.relative_to(REPO).as_posix() + "/" + row["path"]}, derived_commit)


def verify_complete_geoboundaries() -> dict:
    receipt_path = OWNED / "complete-geoboundaries-extraction-receipt.json"
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    if receipt.get("source_baseline_commit") != ORIGINAL_COMMIT:
        raise ValueError("Complete-source extract is linked to the wrong original baseline")
    original_path = receipt["source_path"]
    input_record = load_input_baseline()
    source_pin = next((row for row in input_record["files"] if row["path"] == original_path), None)
    if not source_pin or source_pin["sha256"] != receipt["source_sha256"] or source_pin["bytes"] != receipt["source_bytes"]:
        raise ValueError("Full geoBoundaries extraction receipt disagrees with the immutable input inventory")
    root = OWNED.relative_to(REPO).as_posix()
    features, next_start = [], 0
    for item in receipt["files"]:
        entry = {**item, "path": root + "/" + item["path"]}
        verify_file(REPO, entry, decompress=True)
        part = json.loads(gzip.decompress((REPO / entry["path"]).read_bytes()))["features"]
        if item["source_feature_start"] != next_start or len(part) != item["source_feature_count"]:
            raise ValueError("Complete geoBoundaries partition is missing, duplicated, or reordered")
        next_start += len(part)
        features.extend(part)
    if next_start != receipt["source_feature_count"]:
        raise ValueError("Complete geoBoundaries partition count mismatch")
    source = json.loads((REPO / original_path).read_text(encoding="utf-8"))
    if features != source.get("features"):
        raise ValueError("Complete geoBoundaries chunks do not exactly preserve every original feature and its order")
    return {"feature_count": len(features), "feature_order_and_contents": "exactly match the pinned full original source"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_member_id_map(assessment: dict, *, strict: bool = False) -> tuple[dict[str, str], dict]:
    assigned: dict[str, set[str]] = {}
    for row in assessment["locations"]:
        location_id = row.get("location_id", "")
        for part in row.get("full_parent_chain", []):
            for source_id in part.get("metadata", {}).get("source_member_ids", []):
                if source_id:
                    assigned.setdefault(source_id, set()).add(location_id)
    conflicts = {sid: sorted(ids) for sid, ids in assigned.items() if len(ids) > 1}
    if strict and conflicts:
        raise ValueError("Conflicting source-member assignments: " + json.dumps(conflicts, sort_keys=True))
    mapping = {sid: next(iter(ids)) for sid, ids in assigned.items() if len(ids) == 1}
    return mapping, {"unique_source_member_ids": len(mapping), "repeated_same_location_assignments": sum(len(ids) - 1 for ids in assigned.values() if len(ids) == 1), "conflicts": conflicts}


def verify_mapping(summary: dict, crosswalk_path: Path, assessment: dict, parent_chains: dict, *, historical_last_write: bool = False) -> dict:
    mapping, map_stats = build_member_id_map(assessment)
    legacy_mapping = {}
    for location in assessment["locations"]:
        for part in location.get("full_parent_chain", []):
            for source_id in part.get("metadata", {}).get("source_member_ids", []):
                if source_id:
                    legacy_mapping[source_id] = location.get("location_id", "")
    expected_mapping = legacy_mapping if historical_last_write else mapping
    chains = {row["id"]: json.dumps([
        {"id": tier.get("id"), "name": tier.get("name"), "reference_owner": tier.get("reference_owner")}
        for tier in row["parent_chain"]
    ], ensure_ascii=False, separators=(",", ":")) for row in parent_chains}
    roster_rows = 0
    missing_parent_chains = []
    conflict_roster_rows = []
    for cd, result in summary["cd_assessments"].items():
        for row in result["2016_geoboundaries_cd_intersection_roster"]:
            sid = "gb:CAN:ADM3:" + row["shape_id"]
            expected_id = expected_mapping.get(sid)
            expected_chain = chains.get(expected_id) if expected_id else None
            if expected_id and expected_chain is None:
                missing_parent_chains.append({"cd": cd, "source_id": sid, "location_id": expected_id})
            if row["atlas_source_member_location_id"] != expected_id or row["current_atlas_parent_chain"] != expected_chain:
                raise ValueError(f"Roster source-member/parent-chain mismatch for {sid} in CD {cd}")
            if sid in map_stats["conflicts"]:
                conflict_roster_rows.append({"cd": cd, "shape_id": row["shape_id"], "source_id": sid, "recorded_historical_winner": row["atlas_source_member_location_id"], "rejected_location_ids": map_stats["conflicts"][sid]})
            roster_rows += 1
    csv_rows = 0
    with crosswalk_path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            for candidate in json.loads(row["2016_geoboundaries_candidates"]):
                sid = candidate["source_id"]
                if candidate["already_a_member_of_location_id"] != expected_mapping.get(sid):
                    raise ValueError(f"CSD crosswalk source-member mismatch for {sid} in {row['csd_uid']}")
                if sid in map_stats["conflicts"]:
                    conflict_roster_rows.append({"csd_uid": row["csd_uid"], "source_id": sid, "recorded_historical_winner": candidate["already_a_member_of_location_id"], "rejected_location_ids": map_stats["conflicts"][sid]})
                csv_rows += 1
    if missing_parent_chains:
        raise ValueError("Mapped source members lack a parent chain: " + json.dumps(missing_parent_chains, sort_keys=True))
    return {"assignment_map": map_stats, "mapping_policy": "historical last-write values are checked only in the historical comparison; new reproduction leaves conflicting source-member IDs unassigned and records all affected rows", "historical_last_write_comparison": historical_last_write, "current_parent_chain_count": len(chains), "CD_source_roster_rows_checked": roster_rows, "CSD_source_candidate_rows_checked": csv_rows, "ambiguous_source_rows": conflict_roster_rows, "ambiguous_CD_roster_row_count": sum(1 for row in conflict_roster_rows if "cd" in row), "ambiguous_CSD_candidate_row_count": sum(1 for row in conflict_roster_rows if "csd_uid" in row), "missing_parent_chains": []}


def source_features(path: Path) -> list[dict]:
    return json.loads(gzip.decompress(path.read_bytes()))["features"]


def load_cd_parts() -> list[dict]:
    out: dict[str, dict] = {}
    root = OWNED / "inputs/parent/census-divisions"
    for path in sorted(root.glob("*.geojson.gz")):
        for feature in source_features(path):
            cd = str(feature["properties"]["CDUID"])
            current = out.get(cd)
            if current is None:
                out[cd] = feature
            else:
                if current["geometry"].get("type") != "MultiPolygon" or feature["geometry"].get("type") != "MultiPolygon":
                    raise ValueError(f"Unexpected divided non-MultiPolygon Census Division: {cd}")
                current["geometry"]["coordinates"].extend(feature["geometry"]["coordinates"])
    return [out[key] for key in sorted(out)]


def load_csd_parts() -> list[dict]:
    out = []
    for path in sorted((OWNED / "inputs/parent/census-subdivisions").glob("*.geojson.gz")):
        out.extend(source_features(path))
    return sorted(out, key=lambda feature: feature["properties"]["CSDUID"])


def load_complete_gb() -> dict:
    features = []
    for path in sorted((OWNED / "inputs/parent/geoboundaries-complete").glob("*.geojson.gz")):
        features.extend(source_features(path))
    return {"type": "FeatureCollection", "features": features}


def compose_electoral_area_source(audit) -> list[dict]:
    receipt = load_json(REPO / ORIGINAL / "sources/acquisition-receipt.json")
    features: dict[int, dict] = {}
    for cd in TARGETS:
        path = REPO / ORIGINAL / "sources" / f"bc-electoral-areas-cd-{cd}.geojson.gz"
        for feature in audit.feature_file(path):
            features[int(feature["properties"]["OBJECTID"])] = feature
    raw = json.dumps({"type": "FeatureCollection", "features": list(features.values())}, separators=(",", ":")).encode()
    pin = receipt["responses"]["bc-electoral-areas.geojson.gz"]
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("Per-CD electoral-area layers do not reconstruct the pinned deduplicated union")
    original = gzip.decompress((REPO / ORIGINAL / "sources/bc-electoral-areas.geojson.gz").read_bytes())
    if original != raw:
        raise ValueError("Composed electoral-area source differs from the retained full-union response")
    return list(features.values())


def load_audit_module(output_dir: Path):
    method_path = f"{ORIGINAL}/audit_remainders.py"
    raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{ORIGINAL_COMMIT}:{method_path}"])
    input_record = load_input_baseline()
    pin = next(row for row in input_record["files"] if row["path"] == method_path)
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("Original #609 audit algorithm does not match the pinned Git blob")
    module = types.ModuleType("pinned_issue609_audit")
    module.__file__ = str(REPO / method_path)
    exec(compile(raw.decode("utf-8"), module.__file__, "exec"), module.__dict__)
    module.PACKET = output_dir
    module.SOURCES = REPO / ORIGINAL / "sources"
    module.PARENT_DIR = OWNED / "inputs/parent"
    source_manifest = load_json(module.PARENT_DIR / "sources-manifest.json")
    module.EXPECTED_PARENT_FILES = {row["path"]: row["sha256"] for row in source_manifest["files"]}
    orig_read_json = module.read_json
    orig_read_gzip_json = module.read_gzip_json
    orig_feature_file = module.feature_file
    complete_gb = load_complete_gb()
    cds = load_cd_parts()
    csds = load_csd_parts()
    ea = compose_electoral_area_source(module)

    def read_json(path: Path):
        if path.name == "geoboundaries-CAN-ADM3-2016.geojson":
            return complete_gb
        return orig_read_json(path)

    def read_gzip_json(path: Path):
        if path.name == "statistics-canada-bc-census-divisions-2021.geojson.gz":
            return {"type": "FeatureCollection", "features": cds}
        if path.name == "statistics-canada-bc-census-subdivisions-2021.geojson.gz":
            return {"type": "FeatureCollection", "features": csds}
        return orig_read_gzip_json(path)

    def feature_file(path: Path):
        if path.name == "bc-electoral-areas.geojson.gz":
            return ea
        return orig_feature_file(path)

    def member_id_map():
        mapping, _ = build_member_id_map(orig_read_json(module.PARENT_DIR / "assessment.json"))
        return mapping

    module.read_json = read_json
    module.read_gzip_json = read_gzip_json
    module.feature_file = feature_file
    module.member_id_map = member_id_map
    return module


def verify_original_outputs() -> None:
    record = load_input_baseline()
    paths = [f"{ORIGINAL}/cd-assessments.json", f"{ORIGINAL}/csd-crosswalk.csv"]
    entries = {row["path"]: row for row in record["files"]}
    for name in paths:
        verify_file(REPO, entries[name], ORIGINAL_COMMIT, decompress=False)


def check_only() -> dict:
    record = load_input_baseline()
    verify_original_inputs(record)
    verify_derived_inputs(record)
    complete = verify_complete_geoboundaries()
    verify_original_outputs()
    parent_assessment = load_json(OWNED / "inputs/parent/assessment.json")
    parent_chains = json.loads(gzip.decompress((OWNED / "inputs/parent/sources/current-parent-chains.json.gz").read_bytes()))
    original_summary = load_json(REPO / ORIGINAL / "cd-assessments.json")
    mapping = verify_mapping(original_summary, REPO / ORIGINAL / "csd-crosswalk.csv", parent_assessment, parent_chains, historical_last_write=True)
    return {"mode": "read-only-check", "original_inputs": len(record["files"]), "bounded_derived_inputs": len(record["bounded_derived_inputs"]), "complete_geoboundaries_features": complete["feature_count"], "original_outputs": "whole-file pins match", "source_mapping": mapping}


def require_new_output(path_arg: str) -> Path:
    target = (REPO / path_arg).resolve()
    if not target.is_relative_to(OWNED.resolve()):
        raise ValueError("Output must remain under the issue-owned directory")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Output path already exists; choose a fresh issue-owned destination")
    return target


def write_new_output(path_arg: str) -> dict:
    record = load_input_baseline()
    verify_original_inputs(record)
    verify_derived_inputs(record)
    verify_complete_geoboundaries()
    verify_original_outputs()
    target = require_new_output(path_arg)
    target.mkdir(parents=True, exist_ok=False)
    module = load_audit_module(target)
    module.main()
    summary = load_json(target / "cd-assessments.json")
    if summary["exact_subjects"] != list(TARGETS) or summary["subject_count"] != 10 or summary["current_statistics_canada_csd_count"] != 335:
        raise ValueError("Reproduction output lost or expanded assigned subjects")
    if set(summary["cd_assessments"]) != set(TARGETS):
        raise ValueError("Reproduction output does not contain every assigned CD")
    parent_assessment = load_json(OWNED / "inputs/parent/assessment.json")
    parent_chains = json.loads(gzip.decompress((OWNED / "inputs/parent/sources/current-parent-chains.json.gz").read_bytes()))
    mapping = verify_mapping(summary, target / "csd-crosswalk.csv", parent_assessment, parent_chains)
    (target / "source-mapping-validation.json").write_text(json.dumps(mapping, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {"mode": "new-exclusive-output", "output": target.relative_to(REPO).as_posix(), "subject_count": 10, "csd_rows": 335, "source_mapping": mapping}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="generate into a required new issue-owned output directory")
    parser.add_argument("--out-dir", help="new directory inside this packet; required with --write")
    args = parser.parse_args()
    if args.write:
        if not args.out_dir:
            parser.error("--write requires --out-dir")
        result = write_new_output(args.out_dir)
    else:
        if args.out_dir:
            parser.error("--out-dir is only valid with --write")
        result = check_only()
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
