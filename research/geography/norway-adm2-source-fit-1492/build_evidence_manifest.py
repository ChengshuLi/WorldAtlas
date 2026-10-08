#!/usr/bin/env python3
"""Build the issue #1492 manifest after accounting for its full source inventory."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/norway-adm2-source-fit-1492/"
COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
FINAL_STAGE = "exact-overlay-acceptance-20261008"
SOURCES_STAGE = "official-source-capture-20261008"
OUTPUT = OWNED + "evidence-quality.json"
SOURCE_PATHS = {
    OWNED + f"vintages/{SOURCES_STAGE}/adm1-api.json",
    OWNED + f"vintages/{SOURCES_STAGE}/adm1-simplified.geojson",
    OWNED + f"vintages/{SOURCES_STAGE}/adm2-api.json",
    OWNED + f"vintages/{SOURCES_STAGE}/adm2-simplified.geojson",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def subjects_hash(ids):
    return sha(json.dumps(sorted(ids), separators=(",", ":")).encode())


def file_desc(path):
    raw = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def source_product(path):
    return file_desc(OWNED + f"vintages/{SOURCES_STAGE}/{path}")


def main():
    if (ROOT / OUTPUT).exists():
        raise SystemExit("evidence-quality.json already exists; refusing overwrite")
    admission_raw = (ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json").read_bytes()
    if sha(admission_raw) != BASELINE_SHA:
        raise SystemExit("Initial baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, canonical_json

    baseline = Baseline(ROOT, COMMIT, admission["baseline_files"])
    # Pin the exact delivery shard inventory through the baseline's trusted physical evidence manifest.
    physical_manifest_path = "coordination/engineering/global-physical-comparison-20261006/evidence-quality.json"
    physical_manifest = json.loads(baseline.pinned_bytes(physical_manifest_path))
    cfg_entry = next(x for x in physical_manifest["outputs"]
                     if x.get("path") == "coordination/engineering/global-physical-comparison-20261006/input-config.json")
    baseline.pins[cfg_entry["path"]] = {k: cfg_entry[k] for k in ("path", "bytes", "sha256", "hash_kind")}
    input_config = json.loads(baseline.pinned_bytes(cfg_entry["path"]))
    shards = [x for x in input_config["inputs"] if x.get("kind") == "components"]
    if len(shards) != 11:
        raise SystemExit("Unexpected physical component delivery shard count")

    source_capture_path = ROOT / OWNED / f"vintages/{SOURCES_STAGE}/selected-source-rows.json"
    component_capture_path = ROOT / OWNED / "vintages/component-geometries-20261008/selected-components.json"
    overlay_path = ROOT / OWNED / f"vintages/{FINAL_STAGE}/overlay-v1.json"
    source_capture = json.loads(source_capture_path.read_bytes())
    component_capture = json.loads(component_capture_path.read_bytes())
    overlay = json.loads(overlay_path.read_bytes())
    selected_ids = overlay["scope"]["selected_ids"]
    if len(selected_ids) != 15 or len(set(selected_ids)) != 15:
        raise SystemExit("Final overlay subject roster differs from issue scope")

    # Account for every candidate packet output, retained public source product, decoded shard,
    # and manifest reserve before scanning any original candidate delivery feature collection.
    packet_files = []
    for path in sorted((ROOT / OWNED).rglob("*")):
        if not path.is_file() or path.relative_to(ROOT).as_posix() == OUTPUT:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in SOURCE_PATHS:
            continue
        packet_files.append(rel)
    all_candidate_bytes = sum((ROOT / p).stat().st_size for p in packet_files)
    source_bytes = sum((ROOT / p).stat().st_size for p in SOURCE_PATHS)
    baseline.admit("reserved-output:evidence-quality.json", 4 * 1024 * 1024)
    baseline.admit("existing-candidate-artifacts", all_candidate_bytes)
    baseline.admit("retained-official-source-products", source_bytes)
    for d in shards:
        baseline.pins[d["path"]] = {k: d[k] for k in ("path", "bytes", "sha256", "hash_kind")}
    id_to_path = {}
    delivery_ids = set()
    duplicate_ids = []
    for d in shards:
        raw = baseline.pinned_bytes(d["path"])
        baseline.admit("decoded:" + d["path"], d["uncompressed_bytes"])
        decoded = gzip.decompress(raw)
        if len(decoded) != d["uncompressed_bytes"] or sha(decoded) != d["uncompressed_sha256"]:
            raise SystemExit("Original physical component delivery decoded bytes changed")
        collection = json.loads(decoded)
        for feature in collection["features"]:
            identity = feature.get("id")
            if identity in delivery_ids:
                duplicate_ids.append(identity)
            delivery_ids.add(identity)
            if identity in selected_ids:
                if identity in id_to_path:
                    raise SystemExit("Selected subject appears in more than one original delivery shard")
                id_to_path[identity] = d["path"]
    if set(id_to_path) != set(selected_ids) or duplicate_ids:
        raise SystemExit("Subject-to-delivery-source binding is incomplete or duplicate")
    if len(delivery_ids) != input_config["current_components"] + 1:
        raise SystemExit("Expected source inventory discrepancy changed")

    # Add the exact source manifest/config/code bytes used to authenticate the original delivery.
    baseline_descriptors = list(admission["baseline_files"])
    by_path = {d["path"]: d for d in baseline_descriptors}
    for d in shards:
        by_path[d["path"]] = {"path": d["path"], "bytes": d["bytes"], "sha256": d["sha256"],
                               "hash_kind": "file-bytes", "uncompressed_bytes": d["uncompressed_bytes"],
                               "uncompressed_sha256": d["uncompressed_sha256"]}
    for path, entry in [(cfg_entry["path"], cfg_entry)]:
        by_path[path] = {k: entry[k] for k in ("path", "bytes", "sha256", "hash_kind")}
    for entry in physical_manifest["outputs"]:
        path = entry.get("path", "")
        if path.endswith(("/producer.py", "/comparison.py", "/inputs.py", "/immutable.py", "/ellipsoidal_area.py")):
            by_path[path] = {k: entry[k] for k in ("path", "bytes", "sha256", "hash_kind")}

    source_adm1 = source_capture["source_metadata"]["adm1"]
    source_adm2 = source_capture["source_metadata"]["adm2"]
    retrieved_at = source_capture["retrieval_started_at"]
    sources = [
        {"id": "nor-adm2-simplified-2013", "url": source_adm2["product_capture"]["requested_url"],
         "role": "Official simplified geoBoundaries NOR ADM2 source product used in exact source overlay",
         "vintage": "geoBoundaries commit 9469f09592ced973a3448cf66b6100b741b64c0d; represented year 2013",
         "retrieved_at": retrieved_at, "license": {"status": "redistributable", "terms": source_adm2["license"]},
         "retention": "retained", "verification": "verified", "temporal_status": "reference",
         "files": [source_product("adm2-api.json"), source_product("adm2-simplified.geojson")]},
        {"id": "nor-adm1-simplified-2022", "url": source_adm1["product_capture"]["requested_url"],
         "role": "Official simplified geoBoundaries NOR ADM1 parent product used in exact source overlay",
         "vintage": "geoBoundaries commit 9469f09592ced973a3448cf66b6100b741b64c0d; represented year 2022",
         "retrieved_at": retrieved_at, "license": {"status": "redistributable", "terms": source_adm1["license"]},
         "retention": "retained", "verification": "verified", "temporal_status": "reference",
         "files": [source_product("adm1-api.json"), source_product("adm1-simplified.geojson")]},
        {"id": "original-physical-component-delivery", "url": "https://github.com/ChengshuLi/WorldAtlas/tree/c6a26e1caba54e1b81a89fbda3a64fff56da323d/coordination/engineering/physical-gap-components-1005-20261005-local19/components-v3",
         "role": "Original project candidate-component delivery; identity/geometry input only",
         "vintage": "candidate delivery commit c6a26e1caba54e1b81a89fbda3a64fff56da323d; baseline byte snapshot 088ab05aeb16ddfa8f0c43e596533f3f11d5fcec",
         "retrieved_at": retrieved_at, "license": {"status": "unknown", "terms": "Internal project evidence; redistribution terms not assessed"},
         "retention": "restoration-only", "restoration": "Use the 11 original components-v3 payload paths pinned in baseline.files in the evidence manifest.",
         "verification": "verified", "temporal_status": "unknown",
         "limit": "This diagnostic delivery is not a physical classification or approved geography."},
        {"id": "current-atlas-part-17-targets", "url": "https://github.com/ChengshuLi/WorldAtlas/blob/088ab05aeb16ddfa8f0c43e596533f3f11d5fcec/data/geography/part-17.json",
         "role": "Pinned current Atlas ADM2 target members for target/no-loss comparison",
         "vintage": "baseline commit 088ab05aeb16ddfa8f0c43e596533f3f11d5fcec",
         "retrieved_at": retrieved_at, "license": {"status": "unknown", "terms": "Project data reuse terms were not separately assessed"},
         "retention": "restoration-only", "restoration": "Read data/geography/part-17.json at the pinned baseline commit.",
         "verification": "verified", "temporal_status": "reference",
         "limit": "The current Atlas target comparison does not establish real-world accuracy or physical status."},
        {"id": "historical-source-contact-ledger", "url": "https://github.com/ChengshuLi/WorldAtlas/tree/088ab05aeb16ddfa8f0c43e596533f3f11d5fcec/coordination/engineering/global-source-comparisons-a-001-20261006",
         "role": "Prior source-comparison component intersections/contact rows preserved for exact contact-drift comparison",
         "vintage": "project comparison vintage 2026-10-06; baseline commit 088ab05aeb16ddfa8f0c43e596533f3f11d5fcec",
         "retrieved_at": retrieved_at, "license": {"status": "unknown", "terms": "Project evidence; upstream per-product reuse terms are recorded separately"},
         "retention": "restoration-only", "restoration": "Use the pinned global-source-comparisons-a-001-20261006 scientific component shards and their manifest.",
         "verification": "verified", "temporal_status": "unknown",
         "limit": "Historical feature_intersections include empty bounding-box candidates; only nonempty historical intersections are contacts. After that distinction, all 15 contact sets match the byte-identical current simplified product."}
    ]
    out_descriptors = []
    for path in packet_files:
        out_descriptors.append(file_desc(path))
    overlay_desc = file_desc(OWNED + f"vintages/{FINAL_STAGE}/overlay-v1.json")
    if overlay_desc not in out_descriptors:
        raise SystemExit("Final overlay missing from output inventory")
    metrics_data = [
        ("selected-components", 15, "components", "Selected physical component scope"),
        ("complete-family-members", 400, "components", "Complete preserved gap-source family members"),
        ("positive-length-neighbors", 36, "ADM2 IDs", "Complete preserved positive-length neighboring source IDs"),
        ("exact-source-subject-coverage", sum(x["exact_subject_covers_component"] for x in overlay["components"]), "components", "Component covered by its unique-compatible recorded ADM2 source subject"),
        ("exact-parent-coverage", sum(x["exact_recorded_parent_covers_component"] for x in overlay["components"]), "components", "Component covered by the recorded Nordland ADM1 parent"),
        ("strict-no-loss-pass", sum(x["strict_no_loss_under_T_union_C"] for x in overlay["components"]), "components", "Strict current-target T difference union(T,C) empty"),
        ("strict-no-loss-fail", sum(not x["strict_no_loss_under_T_union_C"] for x in overlay["components"]), "components", "Strict current-target no-loss residual is nonempty"),
        ("candidate-adds-area-to-current-target", sum(x["candidate_adds_area_beyond_current_atlas_target"] for x in overlay["components"]), "components", "Candidate component adds area beyond pinned Atlas ADM2 target"),
        ("historical-current-contact-equality", sum(x["recorded_vs_recomputed_contact_ids_equal"] for x in overlay["adverse_controls"]), "components", "Prior contact IDs exactly equal recomputed current simplified product contacts"),
        ("historical-current-contact-differences", sum(not x["recorded_vs_recomputed_contact_ids_equal"] for x in overlay["adverse_controls"]), "components", "Prior and current simplified contact-ID sets differ"),
        ("historical-bbox-candidate-rows", overlay["contact_reconciliation"]["historical_bbox_candidate_rows"], "rows", "All historical source feature bounding-box candidates, including empty intersections"),
        ("historical-empty-bbox-rows", overlay["contact_reconciliation"]["historical_empty_bbox_rows_not_contacts"], "rows", "Empty historical bounding-box candidates, correctly excluded from contact counts"),
        ("historical-nonempty-contact-rows", overlay["contact_reconciliation"]["historical_nonempty_contact_rows"], "contacts", "Historical nonempty source intersections"),
        ("recomputed-nonempty-source-intersections", len(overlay["all_nonempty_intersections_and_contacts"]), "contacts", "Recomputed nonempty ADM2 feature intersections, including zero-area contacts"),
        ("recomputed-zero-area-contacts", sum(len(x["zero_area_contacts"]) for x in overlay["components"]), "contacts", "Recomputed zero-area contacts in the retained simplified product"),
        ("measured-acceptance-gate-passes", sum(x["measured_acceptance_gate_passes"] for x in overlay["adverse_controls"]), "components", "Components satisfying the complete measured fail-closed conjunction"),
        ("adverse-control-sets-rejected", sum(x["all_adverse_controls_rejected"] for x in overlay["adverse_controls"]), "component control sets", "Components whose ten adverse controls all reject"),
        ("original-delivery-unique-IDs", component_capture["component_delivery_inventory"]["unique_component_ids"], "IDs", "Unique component IDs found in all 11 original delivery shards"),
        ("delivery-config-declared-IDs", component_capture["component_delivery_inventory"]["declared_current_components"], "IDs", "Component count declared in pinned input-config"),
        ("delivery-unique-count-excess", component_capture["component_delivery_inventory"]["declared_vs_captured_unique_difference"], "IDs", "Actual unique delivery IDs minus input-config declaration"),
        ("deterministic-overlay-runs", overlay["runs"]["run_count"], "runs", "Equal canonical exact overlay runs")
    ]
    metrics = [{"id": key, "value": value, "unit": unit, "vintage": "current",
                "input_sha256": overlay_desc["sha256"], "evaluation_commit": COMMIT}
               for key, value, unit, _ in metrics_data]
    summaries = [{"metric_id": key, "value": value, "unit": unit, "text": text}
                 for (key, value, unit, text) in metrics_data]
    subject_map = {identity: id_to_path[identity] for identity in selected_ids}
    manifest = {
        "version": 1, "issue": 1492, "lane": "geography", "worker_id": "01a112b9-e2b7-7d03-8000-eb2890649612",
        "subject_ids": selected_ids, "subject_ids_sha256": subjects_hash(selected_ids),
        "component_ids": selected_ids, "component_ids_sha256": subjects_hash(selected_ids),
        "baseline": {"commit": COMMIT, "files": list(by_path.values()), "subject_files": subject_map},
        "sources": sources, "outputs": out_descriptors,
        "methods": [{"id": "norway-exact-component-source-overlay", "kind": "geography",
                     "description": "Exact source-subject, parent, current Atlas target, strict no-loss, and contact overlays for exactly 15 components. Full 400-member family and 36-neighbor IDs are preserved; no repair or tolerance is used.",
                     "software": overlay["runtime"]["python"].splitlines()[0] + "; Shapely " + overlay["runtime"]["shapely_version"] + "; GEOS " + overlay["runtime"]["geos_version"],
                     "units": "Planar square degrees in source longitude/latitude coordinates; no physical area interpretation",
                     "axis_order": "longitude-latitude", "crs": "Source GeoJSON longitude/latitude, interpreted as OGC:CRS84",
                     "area_method": "Shapely/GEOS planar area and exact topology predicates; no tolerance, snapping, buffering, normalization, or repair",
                     "distance_method": "No distance calculations"}],
        "metrics": metrics, "summaries": summaries,
        "conclusions": [
            {"status": "supported", "text": "All 15 exact component delivery geometries match their pinned prior component geometry hashes and are covered by their unique-compatible retained 2013 ADM2 source subject. Each has one positive-area current simplified-product contact and no additional positive-area source overlap.", "source_ids": ["original-physical-component-delivery", "nor-adm2-simplified-2013"]},
            {"status": "unresolved", "text": "Only 13 of 15 candidate components are covered by the recorded Nordland ADM1 parent; the two Rødøy components fail the strict parent predicate. No candidate satisfies the complete acceptance conjunction.", "source_ids": ["current-atlas-part-17-targets", "nor-adm1-simplified-2022"]},
            {"status": "unresolved", "text": "The exact current-target no-loss predicate passes 8 of 15 and leaves nonempty residuals for 7. This differs by one pass from the earlier issue observation; the exact current run is preserved and the discrepancy is not waived.", "source_ids": ["current-atlas-part-17-targets", "original-physical-component-delivery"]},
            {"status": "supported", "text": "The prior source-comparison ledger contains 31 bbox candidate rows, including 16 empty intersections. Filtering those empty rows and comparing actual contacts yields exact set equality for all 15 selected components against the byte-identical current simplified product; there are no zero-area contacts in either result.", "source_ids": ["historical-source-contact-ledger", "nor-adm2-simplified-2013"]},
            {"status": "supported", "text": "Seven components satisfy the complete measured source-fit/no-loss conjunction: 1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b, 764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384, 7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35, 8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9, a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803, b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a, eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40. This is a source-only proposal result and does not constitute physical or geographic approval.", "source_ids": ["original-physical-component-delivery", "nor-adm1-simplified-2022", "nor-adm2-simplified-2013", "current-atlas-part-17-targets"]},
            {"status": "unresolved", "text": "The 11 pinned delivery shards contain 95,174 unique IDs while the pinned input-config declares 95,173. All selected IDs are individually present exactly once; complete delivery count closure remains unresolved.", "source_ids": ["original-physical-component-delivery"]},
            {"status": "unresolved", "text": "Source-relative geometry does not classify physical land/water or establish history, authority, registration accuracy, ownership, rights, or cause. These remain unknown and geographic approval remains unapproved.", "source_ids": ["nor-adm2-simplified-2013", "nor-adm1-simplified-2022", "original-physical-component-delivery"]}
        ],
        "stages": {"research": "complete", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "python3.12 research/geography/norway-adm2-source-fit-1492/capture_component_geometries.py (use a fresh VINTAGE name for a new run)",
            "python3.12 research/geography/norway-adm2-source-fit-1492/run_bounded_overlay.py (use a fresh VINTAGE name for a new run)",
            "node scripts/evidence-quality.mjs research/geography/norway-adm2-source-fit-1492/evidence-quality.json"
        ],
        "change_receipts": [{"path": OWNED + "vintages/issue-scope-correction-20261008/correction.json",
                             "sha256": sha((ROOT / OWNED / "vintages/issue-scope-correction-20261008/correction.json").read_bytes()),
                             "text": "The corrected Vevelstad component hash is preserved; selected count and full family scope are unchanged."}],
        "limits": [
            "Physical classification, geographic approval, and all core map/database/publisher writes are outside this source-only proposal.",
            "Two Rødøy candidates fail strict ADM1 parent coverage; seven candidates fail exact current-target no-loss. The prior strict no-loss summary reported one fewer pass than this exact run; per-component results are retained.",
            "The exact no-loss result is 8/15 pass, one more than the earlier issue observation of 7/15; this packet preserves the per-component discrepancy.",
            "The complete source delivery has one more unique component ID than its pinned input-config declaration.",
            "The official ADM2 simplified product contains no parent property. Parent feature identity is linked via the recorded framework parent and unique ADM1 shapeName Nordland.",
            "Complete ECO_ID0 geometry, registration accuracy, and Atlas feature-generation lineage remain unavailable.",
            "Unknown remains the classification for physical cause, land/water/ice status, authority, history, rights, and ownership."
        ],
        "retained_artifacts": [{"path": OWNED + f"vintages/{FINAL_STAGE}/overlay-v1.json",
                               "sha256": overlay_desc["sha256"], "status": "exact-head bounded result; zero cases accepted"}]
    }
    raw_manifest = canonical_json(manifest)
    if len(raw_manifest) > 4 * 1024 * 1024:
        raise SystemExit("Manifest exceeds the pre-admitted 4 MiB reserve")
    if sum(baseline.consumed.values()) > baseline.max_phase_bytes:
        raise SystemExit("Complete manifest phase exceeded 256 MiB")
    with (ROOT / OUTPUT).open("xb") as stream:
        stream.write(raw_manifest)
        stream.flush()
        import os
        os.fsync(stream.fileno())
    print(json.dumps({"path": OUTPUT, "sha256": sha(raw_manifest), "bytes": len(raw_manifest),
                      "baseline_files": len(manifest["baseline"]["files"]),
                      "outputs": len(out_descriptors), "source_files": sum(len(s.get("files", [])) for s in sources),
                      "subjects": len(subject_map), "delivery_unique_ids": len(delivery_ids),
                      "phase_bytes": sum(baseline.consumed.values())}, indent=2))


if __name__ == "__main__":
    main()
