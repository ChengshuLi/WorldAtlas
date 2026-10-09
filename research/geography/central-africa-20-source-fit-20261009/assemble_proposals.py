#!/usr/bin/env python3
"""Build the exact-ID decision table and additive-only proposal payload."""
import csv
import gzip
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/central-africa-20-source-fit-20261009"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_gz_json(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def main():
    result_path = PACKET / "results/simplified-source-fit.json"
    fit = json.loads(result_path.read_bytes())
    component_path = PACKET / "inputs/components/selected-20-components.json.gz"
    components = {f["id"]: f for f in load_gz_json(component_path)["features"]}
    comparisons = {r["component_id"]: r["source_comparison_row"]
                   for r in load_gz_json(PACKET / "inputs/source-comparisons/selected-20-source-comparison-rows.json.gz")["rows"]}
    gshhg = json.loads((PACKET / "gshhg-custody.json").read_bytes())
    gshhg_by_id = {cid: [] for cid in components}
    for record in gshhg["selected_records"]:
        for cid in record["bbox_candidate_ids_only"]:
            gshhg_by_id[cid].append(str(record["id"]))
    fit_rows = {r["component_id"]: r for r in fit["fit_rows"]}
    proposal_rows = [r for r in fit["fit_rows"] if r["proposal_eligible"]]
    assert len(components) == len(comparisons) == len(fit["roster"]) == 20
    assert len(proposal_rows) == 9

    # Per-ID decisions are the union of exact source-comparison and fit ledgers.
    table_path = PACKET / "results/per-id-decisions.csv"
    with table_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["component_id", "source_status", "fit_status", "source_subject_id", "target_id",
                    "failed_predicates", "gshhg_record_ids_bbox_only", "physical_class", "decision_limit"])
        for row in fit["roster"]:
            cid = row["component_id"]
            prev = comparisons[cid]
            subject = prev.get("uniquely_covering_compatible_recorded_subject") or {}
            fitrow = fit_rows.get(cid)
            fail = ";".join(row.get("failed_predicates", []))
            if row["fit_status"] == "unknown":
                fail = row.get("reason", "")
            w.writerow([cid, prev["status"], row["fit_status"], subject.get("id", ""), row.get("target_id", ""),
                        fail, ";".join(sorted(gshhg_by_id[cid])), "unknown",
                        "source-relative reference-map fit only; physical land/water/ice, cause, authority and legal status unknown"])

    proposals = []
    for row in proposal_rows:
        cid = row["component_id"]
        original = components[cid]
        source = row["source_target"]
        props = original.get("properties", {})
        proposals.append({
            "type": "Feature",
            "id": cid,
            "geometry": original["geometry"],
            "properties": {
                "component_id": cid,
                "proposal_kind": "additive-reference-map-fit",
                "proposal_status": "research proposal; not implemented or approved",
                "target_id": row["current_target"]["id"],
                "target_feature_sha256_before": row["current_target"]["feature_sha256"],
                "target_geometry_sha256_before": row["current_target"]["geometry_sha256"],
                "component_feature_sha256": row["component_full_feature_sha256"],
                "component_geometry_sha256": row["component_geometry_sha256"],
                "source_feature_id": source["id"],
                "source_shapeID": source["shapeID"],
                "source_feature_sha256": source["feature_sha256"],
                "source_geometry_sha256": source["geometry_sha256"],
                "source_product": row["source_product"],
                "overlay_predicates": row["conditions"],
                "source_relative_only": True,
                "physical_class": "unknown",
                "cause": "unknown",
                "legal_or_current_authority": "not assessed or implied",
                "limits": row["limits"],
                "original_component_properties": {k: props.get(k) for k in (
                    "water_status", "administrative_assignment", "dateline_connected", "fragment_bindings")},
            },
        })
    proposal_doc = {"type": "FeatureCollection", "features": proposals}
    proposal_path = PACKET / "proposals/additive-proposals.geojson"
    proposal_path.parent.mkdir(exist_ok=True)
    proposal_raw = json.dumps(proposal_doc, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    proposal_path.write_bytes(proposal_raw)

    result_raw = result_path.read_bytes()
    table_raw = table_path.read_bytes()
    gshhg_raw = (PACKET / "gshhg-custody.json").read_bytes()
    manifest = {
        "schema": "central-africa-additive-proposal-v1",
        "issue": 1629,
        "batch_id": fit["batch_id"],
        "baseline_commit": fit["baseline_commit"],
        "proposal_count": len(proposals),
        "proposal_geojson": {"path": str(proposal_path.relative_to(ROOT)), "bytes": len(proposal_raw), "sha256": sha(proposal_raw)},
        "decision_table": {"path": str(table_path.relative_to(ROOT)), "bytes": len(table_raw), "sha256": sha(table_raw)},
        "fit_result": {"path": str(result_path.relative_to(ROOT)), "bytes": len(result_raw), "sha256": sha(result_raw)},
        "gshhg_custody": {"path": str((PACKET / "gshhg-custody.json").relative_to(ROOT)), "bytes": len(gshhg_raw), "sha256": sha(gshhg_raw)},
        "proposal_ids": [f["id"] for f in proposals],
        "exclusions": {"source-unique-water-support": 1, "mixed-or-partial": 7, "contact-only": 2,
                       "unique-land-source-but-exact-fit-refused": 1},
        "physical_class": "unknown for every candidate",
        "integration_status": "not implemented; no core geography files changed",
        "limitations": ["GeoBoundaries source-relative fit is not legal/current authority or historical truth",
                        "GSHHG byte records were chosen by bounding-box overlap only; geometry validity was not evaluated",
                        "No present land/water/ice, causal class, or publication approval is asserted"],
    }
    manifest_path = PACKET / "proposals/additive-proposals-manifest.json"
    manifest_raw = json.dumps(manifest, indent=2).encode() + b"\n"
    manifest_path.write_bytes(manifest_raw)
    print(json.dumps({"table": {"path": str(table_path), "sha256": sha(table_raw)},
                      "proposal": {"path": str(proposal_path), "bytes": len(proposal_raw), "sha256": sha(proposal_raw)},
                      "manifest": {"path": str(manifest_path), "sha256": sha(manifest_raw)},
                      "proposal_ids": manifest["proposal_ids"]}, indent=2))


if __name__ == "__main__":
    main()
