#!/usr/bin/env python3
"""Reproduce country-bound license provenance and run genuine negative controls."""
from __future__ import annotations
import gzip, hashlib, importlib.util, json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GENERATOR = HERE / "reproduce.py"
OUTPUT = HERE / "license-provenance.json"
CONTRACT = json.loads((HERE / "issue-contract.json").read_text())

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def run_isolated() -> bytes:
    with tempfile.TemporaryDirectory(prefix="worldatlas-sle-provenance-") as tmp:
        result = subprocess.check_output([sys.executable, str(GENERATOR)], cwd=tmp)
        json.loads(result)
        return result

def main() -> None:
    first, second = run_isolated(), run_isolated()
    if first != second:
        raise SystemExit("Independent temporary-directory reproductions differ")
    committed = OUTPUT.read_bytes()
    if first.rstrip(b"\n") != committed.rstrip(b"\n"):
        raise SystemExit("Reproduction does not match retained license-provenance.json")
    packet = json.loads(first)
    if packet["counts"] != {
        "sierra_leone_subjects": 12,
        "sierra_leone_original_license_mismatches": 12,
        "togo_context_rows": 37,
        "togo_context_license_matches": 37,
    }:
        raise SystemExit("Unexpected exact-scope result counts")
    spec = importlib.util.spec_from_file_location("sle_provenance", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    baseline = CONTRACT["baseline_commit"]
    sle_meta = json.loads(gzip.decompress(subprocess.check_output([
        "git", "show", f"{baseline}:{CONTRACT['baseline_paths']['sle_metadata']}"], cwd=ROOT)))
    tgo_meta = json.loads(gzip.decompress(subprocess.check_output([
        "git", "show", f"{baseline}:{CONTRACT['baseline_paths']['tgo_metadata']}"], cwd=ROOT)))
    # Negative control 1: a SLE feature cannot be paired with TGO country metadata.
    row = packet["sierra_leone_rows"][0]
    member = {"id": row["id"], "country": "Sierra Leone", "pinned_source_id": "gb:SLE:ADM2"}
    try:
        module.assert_country_binding(member, "SLE", tgo_meta)
    except ValueError:
        pass
    else:
        raise SystemExit("Cross-country metadata negative control was not rejected")
    # Negative control 2: changing a corrected SLE license to TGO's label is rejected.
    mutated = dict(row, corrected_license=tgo_meta["boundaryLicense"])
    try:
        module.validate_sle_record(mutated, sle_meta)
    except ValueError:
        pass
    else:
        raise SystemExit("Injected wrong-license negative control was not rejected")
    # The packet preserves the exact historical identity fields for each subject;
    # verify each is also represented by the pinned canonical partition.
    part_path = CONTRACT["baseline_paths"]["atlas_part"]
    features = json.loads(subprocess.check_output(["git", "show", f"{baseline}:{part_path}"], cwd=ROOT))["features"]
    by_id = {f.get("id", f.get("properties", {}).get("id")): f for f in features}
    if len(by_id) != len(features):
        raise SystemExit("Pinned canonical partition has duplicate feature IDs")
    for record in packet["sierra_leone_rows"]:
        feature = by_id.get(record["id"])
        if feature is None:
            raise SystemExit(f"Subject absent from pinned canonical partition: {record['id']}")
        props = feature["properties"]
        if props.get("name") != record["name"] or props.get("parent_id") != record["parent_id"]:
            raise SystemExit(f"Historical name/parent changed in provenance receipt: {record['id']}")
    result = {
        "version": 1,
        "method_id": "country-license-provenance",
        "kind": "source",
        "outcome": "passed",
        "scope": {"sierra_leone_subjects": 12, "togo_context_rows": 37},
        "run_one_sha256": sha(first),
        "run_two_sha256": sha(second),
        "equal_runs": True,
        "negative_controls": {
            "foreign_country_metadata_rejected": True,
            "injected_togo_license_rejected_for_sle": True,
        },
        "identity_preservation": "all 12 subject IDs, names, and direct parent IDs match the pinned canonical partition",
        "limits": ["Metadata-declared licensing is not independently adjudicated.", "No boundary or regional approval is established."],
    }
    (HERE / "verification-results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True, indent=2))

if __name__ == "__main__":
    main()
