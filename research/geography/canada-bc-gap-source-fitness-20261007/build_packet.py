#!/usr/bin/env python3
"""Build an evidence-only, complete-scope source-fitness packet for issue #1362."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import subprocess
import sys
from collections import Counter

ROUTING = "0198938719a5666b6726fb6a1e45779926eefeb2"
DIAGNOSIS = "bec82842ad5d9cf07e38a78395df8d5e7a6f4591"
FAMILY = "gap-source-batch:63d748f318d7dfeb738447ea"
CONTACT = "atlas:district:CAN-5917:BRC"
EXPECTED_FAMILY_HASH = "2b61c6f59d5192b124f88822ab11279a85ae1764d773f76266a8b40b0140a38e"
ROUTING_REPORT_PATH = "coordination/engineering/global-actionability-routing-20261007/results/report.json"
DIAGNOSIS_ROOT = "coordination/engineering/complete-numeric-closure-diagnosis-20261007"
ROUTING_ROOT = "coordination/engineering/global-actionability-routing-20261007/results"
CONTACT_PATH = "data/geography/part-29.json"
BC_PACKET = "data/regional-review/regional-review-4254da254d94f450"
OWNED_PATH = "research/geography/canada-bc-gap-source-fitness-20261007/"
DIAGNOSIS_REPORT = f"{DIAGNOSIS_ROOT}/r1/report.json"
GENERATOR_OUTPUTS = ["family-row.json", "component-review.jsonl", "source-input-pins.json",
                     "source-assessment.json", "scope-summary.json", "run-receipt.json"]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                        allow_nan=False) + "\n").encode("utf-8")


def write_json(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def tracked_pin(commit: str, path: str) -> dict:
    body = git("show", f"{commit}:{path}")
    tree = git("ls-tree", commit, "--", path).decode().strip().split()
    if len(tree) < 4 or tree[0] not in {"100644", "100755"}:
        raise ValueError(f"Expected one ordinary tracked file: {commit}:{path}")
    return {"commit": commit, "path": path, "mode": tree[0], "oid": tree[2],
            "bytes": len(body), "sha256": sha(body)}


def verify_part(repo: pathlib.Path, commit: str, root_path: str, descriptor: dict) -> bytes:
    path = f"{root_path}/{descriptor['path']}"
    if descriptor["bytes"] > 32 * 1024 * 1024 or descriptor["uncompressed_bytes"] > 32 * 1024 * 1024:
        raise ValueError(f"Routing/diagnosis partition exceeds the 32 MiB per-file limit: {path}")
    tree = git("ls-tree", commit, "--", path).decode().strip().split()
    if len(tree) < 4 or tree[0] not in {"100644", "100755"}:
        raise ValueError(f"Expected an ordinary immutable routing/diagnosis partition: {path}")
    encoded = git("show", f"{commit}:{path}")
    if len(encoded) != descriptor["bytes"] or sha(encoded) != descriptor["sha256"]:
        raise ValueError(f"Encoded routing/diagnosis part mismatch: {path}")
    decoded = gzip.decompress(encoded)
    if (len(decoded) != descriptor["uncompressed_bytes"] or
            sha(decoded) != descriptor["uncompressed_sha256"]):
        raise ValueError(f"Decoded routing/diagnosis part mismatch: {path}")
    return decoded


def parse_target_rows(raw: bytes, id_field: str, wanted: set[str]) -> dict:
    found = {}
    for line in raw.splitlines():
        if not line:
            continue
        if not any(value.encode("ascii") in line for value in wanted):
            continue
        row = json.loads(line)
        key = row.get(id_field)
        if key in wanted:
            if key in found:
                raise ValueError(f"Duplicate {id_field}: {key}")
            found[key] = row
    return found


def all_lines(raw: bytes):
    for line in raw.splitlines():
        if line:
            yield json.loads(line)


def geometry_counts(geometry: dict) -> dict:
    kind, coordinates = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        polygons = [coordinates]
    elif kind == "MultiPolygon":
        polygons = coordinates
    else:
        return {"type": kind, "parts": None, "exterior_vertices": None,
                "interior_rings": None}
    return {"type": kind, "parts": len(polygons),
            "exterior_vertices": sum(len(polygon[0]) for polygon in polygons),
            "interior_rings": sum(max(0, len(polygon) - 1) for polygon in polygons)}


def compact_query(q: dict) -> dict:
    fields = ("source_id", "source_level", "source_container", "periodic_offset", "status",
              "witness", "intersects", "disjoint", "candidate_covers_source",
              "source_covers_candidate", "source_record_sha256", "source_pointset_sha256",
              "container_chain_issues")
    return {key: q[key] for key in fields if key in q}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit(f"Refusing to replace existing output: {out}")
    # Pin the fetched current main explicitly, not HEAD (which may already
    # contain earlier commits from this same PR).
    main_sha = git("rev-parse", "origin/main").decode().strip()
    helper_path = repo / "scripts/evidence/immutable.py"
    helper_bytes = git("show", f"{main_sha}:scripts/evidence/immutable.py")
    if helper_path.read_bytes() != helper_bytes:
        raise ValueError("Shared immutable preparation helper differs from pinned baseline")
    sys.path.insert(0, str(repo / "scripts"))
    from evidence.immutable import Baseline, NewVintage
    baseline_paths = [ROUTING_REPORT_PATH, DIAGNOSIS_REPORT, "scripts/evidence/immutable.py",
                      f"{DIAGNOSIS_ROOT}/input-index.json", CONTACT_PATH,
                      "data/semantic-report.json", "data/administrative-sources.json",
                      "scripts/administrative.py", f"{BC_PACKET}/README.md",
                      f"{BC_PACKET}/evidence-artifacts-manifest.json",
                      f"{BC_PACKET}/sources-manifest.json", f"{BC_PACKET}/assessment.json",
                      f"{BC_PACKET}/gshhg-scope-screen.json",
                      f"{BC_PACKET}/sources/statistics-canada-census-divisions-item-metadata.json",
                      f"{BC_PACKET}/sources/statistics-canada-census-divisions-layer-metadata.json",
                      f"{BC_PACKET}/sources/gshhg-scope-land-candidates.bin.gz",
                      f"{BC_PACKET}/sources/gshhg-COPYING.LESSERv3.txt",
                      f"{BC_PACKET}/sources/gshhg-LICENSE-notice.txt"]
    baseline_descriptors = []
    for path in baseline_paths:
        pin = tracked_pin(main_sha, path)
        baseline_descriptors.append({"path": path, "bytes": pin["bytes"],
                                     "sha256": pin["sha256"], "hash_kind": "file-bytes"})
    baseline = Baseline(repo, main_sha, baseline_descriptors)
    destination = NewVintage(baseline, OWNED_PATH, out.name, GENERATOR_OUTPUTS)
    if destination.root.resolve() != out:
        raise ValueError("Output must be a fresh named vintage under the issue-owned path")

    # Authenticate the complete accepted routing tables by their recorded chunk receipts.
    route_report_bytes = baseline.pinned_bytes(ROUTING_REPORT_PATH)
    if sha(route_report_bytes) != "2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265":
        raise ValueError("Accepted routing report changed")
    route_report = json.loads(route_report_bytes)
    family_parts = [p for p in route_report["outputs"] if p["path"].startswith("families-")]
    component_parts = [p for p in route_report["outputs"] if p["path"].startswith("components-")]
    family_rows = {}
    for descriptor in sorted(family_parts, key=lambda x: x["path"]):
        rows = parse_target_rows(verify_part(repo, main_sha, ROUTING_ROOT, descriptor), "id", {FAMILY})
        if any(key in family_rows for key in rows):
            raise ValueError("Accepted routing family row is duplicated across source partitions")
        family_rows.update(rows)
    if len(family_rows) != 1:
        raise ValueError("Accepted routing family row is missing or duplicated")
    family = family_rows[FAMILY]
    if sha(canonical(family)) != EXPECTED_FAMILY_HASH:
        raise ValueError("Complete accepted family row hash mismatch")
    component_ids = family["complete_component_ids"]
    component_set = set(component_ids)
    if len(component_ids) != 43 or len(component_set) != 43:
        raise ValueError("Complete family roster is not 43 unique members")
    route_components = {}
    for descriptor in sorted(component_parts, key=lambda x: x["path"]):
        rows = parse_target_rows(verify_part(repo, main_sha, ROUTING_ROOT, descriptor), "component", component_set)
        if any(key in route_components for key in rows):
            raise ValueError("Accepted component row is duplicated across source partitions")
        route_components.update(rows)
    if set(route_components) != component_set:
        raise ValueError("Accepted routing does not yield all and only 43 family component rows")
    if any(row.get("family") != FAMILY for row in route_components.values()):
        raise ValueError("Component-to-family binding mismatch")

    # Verify the complete diagnostic output chunks, then retain all 28 target numeric rows.
    input_index_path = f"{DIAGNOSIS_ROOT}/input-index.json"
    input_index = json.loads(baseline.materialized_bytes(input_index_path))
    if input_index.get("actual_merge") != ROUTING:
        raise ValueError("Diagnosis input index does not bind the accepted routing merge")
    diagnosis_report_bytes = baseline.pinned_bytes(DIAGNOSIS_REPORT)
    if sha(diagnosis_report_bytes) != "e47379a74c053b57781fec04aaedc702ecba24adb773b42bb8c75d142326647a":
        raise ValueError("Accepted numeric diagnosis report changed")
    diagnosis_report = json.loads(diagnosis_report_bytes)
    numeric_ids = {cid for cid, row in route_components.items()
                   if row.get("next_prerequisite") == "engineering-numeric-closure-first"}
    if len(numeric_ids) != 28:
        raise ValueError("Expected complete 28-member numerical closure")
    diagnosis_rows = {}
    diagnosis_parts = [p for p in diagnosis_report["outputs"] if p["path"].startswith("diagnoses-")]
    diagnosis_root = repo / DIAGNOSIS_ROOT / "r1"
    for descriptor in sorted(diagnosis_parts, key=lambda x: x["path"]):
        decoded = verify_part(repo, main_sha, f"{DIAGNOSIS_ROOT}/r1", descriptor)
        for line in decoded.splitlines():
            if not line or not any(cid.encode("ascii") in line for cid in numeric_ids):
                continue
            row = json.loads(line)
            cid = row.get("component_id")
            if cid in numeric_ids:
                if cid in diagnosis_rows:
                    raise ValueError(f"Duplicate numerical diagnosis: {cid}")
                diagnosis_rows[cid] = row
    if set(diagnosis_rows) != numeric_ids:
        raise ValueError("Numeric diagnosis output is missing or adds family members")
    if any(row.get("family") != FAMILY for row in diagnosis_rows.values()):
        raise ValueError("Numeric diagnosis family binding mismatch")
    category_counts = Counter(row["conservative_class"] for row in diagnosis_rows.values())
    expected_categories = {"local-construction-contradiction-demonstrated": 9,
                           "retained-unresolved-numerical-or-context-prerequisite": 18,
                           "retained-unresolved-original-replay-mismatch": 1}
    if dict(category_counts) != expected_categories:
        raise ValueError(f"Numeric diagnosis categories changed: {dict(category_counts)}")

    # Restore each complete original physical row from the accepted immutable merge.
    entries = {f["original_path"]: f for f in input_index["files"] if "original_path" in f}
    source_paths = sorted({row["whole_physical_containing_file"] for row in route_components.values()})
    physical_rows = {}
    physical_pins = []
    for path in source_paths:
        entry = entries.get(path)
        if not entry or entry.get("original_commit") != ROUTING:
            raise ValueError(f"Physical row source missing from complete input index: {path}")
        body = git("show", f"{ROUTING}:{path}")
        tree = git("ls-tree", ROUTING, "--", path).decode().strip().split()
        if (len(body) != entry["bytes"] or sha(body) != entry["sha256"] or
                tree[0] != entry["original_mode"] or tree[2] != entry["original_oid"]):
            raise ValueError(f"Whole physical source pin mismatch: {path}")
        physical_pins.append({"commit": ROUTING, "path": path, "bytes": len(body),
                              "sha256": sha(body), "mode": tree[0], "oid": tree[2],
                              "input_index_role": entry["role"]})
        for line in gzip.decompress(body).splitlines():
            if not line or not any(cid.encode("ascii") in line for cid in component_set):
                continue
            row = json.loads(line)
            cid = row.get("component_id")
            if cid in component_set:
                if cid in physical_rows:
                    raise ValueError(f"Duplicate original physical row: {cid}")
                expected = route_components[cid]["whole_physical_row_sha256"]
                if sha(canonical(row)) != expected:
                    raise ValueError(f"Whole original physical row hash mismatch: {cid}")
                physical_rows[cid] = row
    if set(physical_rows) != component_set:
        raise ValueError("Original physical input closure does not include all 43 records")

    # Authenticate current whole contact and the independent retained 2021 statistical source.
    contact_pin = tracked_pin(main_sha, CONTACT_PATH)
    contact_db = json.loads(baseline.materialized_bytes(CONTACT_PATH))
    contact_feature = next(f for f in contact_db["features"] if f["id"] == CONTACT)
    contact_hash = sha(canonical(contact_feature))
    current_metadata = contact_feature["properties"]["metadata"]
    if current_metadata.get("source_id") != CONTACT:
        raise ValueError("Current contact source identity mismatch")
    if contact_feature["geometry"]["type"] != "MultiPolygon":
        raise ValueError("Current contact geometry type changed")

    bc_root = repo / BC_PACKET
    stats_rel = f"{BC_PACKET}/sources/statistics-canada-bc-census-divisions-2021.geojson.gz"
    stats_pin = tracked_pin(main_sha, stats_rel)
    stats_encoded = (repo / stats_rel).read_bytes()
    if len(stats_encoded) != stats_pin["bytes"] or sha(stats_encoded) != stats_pin["sha256"]:
        raise ValueError("Oversized retained Statistics Canada source bytes differ from the pinned Git blob")
    stats_doc = json.loads(gzip.decompress(stats_encoded))
    stats_features = [f for f in stats_doc["features"] if f.get("properties", {}).get("CDUID") == "5917"]
    if len(stats_features) != 1:
        raise ValueError("Retained 2021 Statistics Canada CDUID 5917 row is missing or duplicated")
    stats_feature = stats_features[0]
    if stats_feature["properties"].get("CDNAME") != "Capital" or stats_feature["properties"].get("CDTYPE") != "RD":
        raise ValueError("Retained Statistics Canada identity fields changed")
    # A bounded representation/identity screen only. This is not a legal or physical boundary test.
    try:
        from shapely.geometry import shape
        current_geom = shape(contact_feature["geometry"])
        stats_geom = shape(stats_feature["geometry"])
        topology_equal = bool(current_geom.equals(stats_geom))
        current_valid, stats_valid = bool(current_geom.is_valid), bool(stats_geom.is_valid)
    except Exception as exc:
        raise ValueError(f"Required retained geometry identity screen unavailable: {exc}") from exc

    assessment_path = bc_root / "assessment.json"
    prior_assessment = json.loads(baseline.materialized_bytes(f"{BC_PACKET}/assessment.json"))
    screen_path = bc_root / "gshhg-scope-screen.json"
    gshhg_screen = json.loads(baseline.materialized_bytes(f"{BC_PACKET}/gshhg-scope-screen.json"))
    contact_screen = gshhg_screen["per_location"][CONTACT]
    source_meta_path = bc_root / "sources/statistics-canada-census-divisions-item-metadata.json"
    layer_meta_path = bc_root / "sources/statistics-canada-census-divisions-layer-metadata.json"
    query_receipt_path = bc_root / "sources/statistics-canada-census-divisions-query-receipt.json"
    if not query_receipt_path.exists():
        query_receipt_path = bc_root / "sources/statistics-canada-census-divisions-acquisition-receipt.json"

    # Build a complete 43-row source/diagnosis matrix without changing any input geography.
    review_rows = []
    for cid in component_ids:
        routed = route_components[cid]
        original = physical_rows[cid]
        diagnosis = diagnosis_rows.get(cid)
        relations = original.get("query_relations", [])
        review_rows.append({
            "component_id": cid,
            "family_id": FAMILY,
            "operational_batch_id": routed["operational_batch"],
            "full_current_candidate": {
                "feature_sha256": routed["current_feature_sha256"],
                "geometry_sha256": routed["current_geometry_sha256"],
                "context_alias": routed["whole_current_context_alias"]},
            "original_physical_record": {
                "path": routed["whole_physical_containing_file"],
                "row_sha256": routed["whole_physical_row_sha256"],
                "query_relation_count": len(relations),
                "query_relations": [compact_query(q) for q in relations],
                "contact_ids": original.get("complete_contact_ids", []),
                "source_vintage": original.get("source_vintage"),
                "physical_limits": original.get("physical_limits", [])},
            "routing": {
                "physical_status": routed["physical_status"],
                "physical_authority": routed["physical_authority"],
                "physical_source_vintage": routed["physical_source_vintage"],
                "source_fitness_prerequisite": routed["source_fitness_prerequisite"],
                "next_prerequisite": routed["next_prerequisite"],
                "support_areas_m2": routed["existing_support_areas"],
                "unresolved": routed["unresolved"]},
            "numeric_diagnosis": (None if diagnosis is None else {
                "replay_status": diagnosis["status"],
                "conservative_class": diagnosis["conservative_class"],
                "row_sha256": sha(canonical(diagnosis)),
                "query_count": diagnosis.get("query_count"),
                "geometry_mapping_refs": diagnosis.get("complete_geometry_mappings"),
                "original_unknowns": diagnosis.get("original_unknowns"),
                "original_unresolved": diagnosis.get("original_unresolved"),
                "demonstrated_local_contradictions": diagnosis.get("demonstrated_local_contradictions"),
                "next_action": diagnosis.get("next_action")}),
            "source_fitness_disposition": "unapproved; preserve source-relative evidence and open physical/registration/date uncertainty"
        })
    if len(review_rows) != 43 or {x["component_id"] for x in review_rows} != component_set:
        raise ValueError("Source-fitness matrix does not cover exactly all 43 components")

    # Bind primary whole-file inputs and the actual original physical records.
    source_paths_to_pin = [
        ROUTING_REPORT_PATH,
        f"{DIAGNOSIS_ROOT}/input-index.json",
        f"{DIAGNOSIS_ROOT}/evidence-quality.json",
        CONTACT_PATH,
        "data/semantic-report.json",
        "data/administrative-sources.json",
        "scripts/administrative.py",
        f"{BC_PACKET}/README.md",
        f"{BC_PACKET}/evidence-artifacts-manifest.json",
        f"{BC_PACKET}/sources-manifest.json",
        f"{BC_PACKET}/assessment.json",
        f"{BC_PACKET}/gshhg-scope-screen.json",
        f"{BC_PACKET}/sources/statistics-canada-census-divisions-item-metadata.json",
        f"{BC_PACKET}/sources/statistics-canada-census-divisions-layer-metadata.json",
        f"{BC_PACKET}/sources/statistics-canada-bc-census-divisions-2021.geojson.gz",
        f"{BC_PACKET}/sources/gshhg-scope-land-candidates.bin.gz",
        f"{BC_PACKET}/sources/gshhg-COPYING.LESSERv3.txt",
        f"{BC_PACKET}/sources/gshhg-LICENSE-notice.txt",
    ]
    source_pins = [tracked_pin(main_sha, path) for path in source_paths_to_pin]
    runtime = {"python": sys.version.split()[0]}
    try:
        import shapely
        runtime["shapely"] = shapely.__version__
    except Exception:
        pass

    review_jsonl = b"".join(canonical(row) for row in review_rows)
    source_input_pins = {
        "accepted_routing_commit": ROUTING,
        "accepted_diagnosis_commit": DIAGNOSIS,
        "current_main_baseline": main_sha,
        "routing_report": tracked_pin(ROUTING, ROUTING_REPORT_PATH),
        "diagnosis_input_index": tracked_pin(DIAGNOSIS, f"{DIAGNOSIS_ROOT}/input-index.json"),
        "diagnosis_execution_report": tracked_pin(DIAGNOSIS, f"{DIAGNOSIS_ROOT}/r1/report.json"),
        "complete_original_physical_row_files": physical_pins,
        "current_and_retained_source_files": source_pins,
        "family_row_sha256": EXPECTED_FAMILY_HASH,
        "family_id": FAMILY,
        "component_ids_sha256": family["original_fine_family"]["component_ids_sha256"],
        "complete_contact_ids": [CONTACT],
        "numeric_component_ids": sorted(numeric_ids),
        "numeric_diagnosis_status_counts": dict(category_counts),
        "runtime": runtime,
        "whole_source_closure_note": "Original physical gzip rows were read from accepted routing merge, whole blobs were checked against the diagnosis input-index path/mode/OID/byte/hash receipts, and each selected row was checked against the delivered route row SHA. Query relationships remain individually listed in component-review.jsonl. No original operator or external source service was run."
    }

    source_assessment = {
        "accepted_routing_family": {
            "family_id": FAMILY,
            "family_row_sha256": EXPECTED_FAMILY_HASH,
            "operational_batch_id": family["operational_batch"],
            "complete_component_count": len(component_ids),
            "source_fitness": family["source_fitness"],
            "physical_authority": family["physical_authority"],
            "original_fine_family": family["original_fine_family"],
            "inherited_impact_m2": family["measured_fragment_area_sum_m2"],
            "support_area_sums_m2": family["support_area_sums_m2"],
            "interpretation": "These are accepted routing diagnostics and source-family metadata. They do not constitute source fitness approval, legal authority, dry-land proof, or a new impact measurement."
        },
        "contact": {
            "id": CONTACT, "current_full_feature_sha256": contact_hash,
            "geometry_sha256": sha(canonical(contact_feature["geometry"])),
            "geometry_counts": geometry_counts(contact_feature["geometry"]),
            "source_id": current_metadata.get("source_id"),
            "recorded_source_url": current_metadata.get("source_url"),
            "recorded_reference_year": current_metadata.get("reference_year"),
            "recorded_license": current_metadata.get("license"),
            "source_member_count": len(current_metadata.get("source_member_ids", [])),
            "source_member_ids": current_metadata.get("source_member_ids", [])},
        "statistics_canada_2021_census_division": {
            "source_file_pin": stats_pin,
            "product_identity": {k: stats_feature["properties"].get(k) for k in
                                 ("CDUID", "DGUID", "CDNAME", "CDTYPE", "LANDAREA", "PRUID")},
            "geometry_sha256": sha(canonical(stats_feature["geometry"])),
            "geometry_counts": geometry_counts(stats_feature["geometry"]),
            "current_contact_valid": current_valid,
            "official_feature_valid": stats_valid,
            "current_contact_topologically_equal": topology_equal,
            "assessment": "Suitable to identify the retained 2021 statistical Census Division record. The current Atlas aggregation is not topologically equal to this dated source feature and has a much smaller retained coordinate/part representation. This is a cartographic comparison, not a legal-boundary, currentness, physical-land, or source-accuracy approval."},
        "gshhg_physical_screen": {
            "retained_source": gshhg_screen["source"],
            "method": gshhg_screen["method"],
            "contact_level1_screen": contact_screen,
            "family_routing_physical_status_counts": dict(Counter(r["routing"]["physical_status"] for r in review_rows)),
            "family_source_fitness": family["source_fitness"],
            "family_physical_authority": family["physical_authority"],
            "family_existing_support_area_sums_m2": family["support_area_sums_m2"],
            "assessment": "Suitable only as a 2017 generalized mapped-land/coastline screen. Contact representative-point and level-1 centroid hits do not cover the 43 component geometries as a whole; 15 component rows remain mixed-source-support and 28 remain physically unknown. No dry-land inference is made."},
        "source_role_limits": [
            "The accepted contact metadata describes an undated modern aggregation, with the complete 22-member source roster and an ArcGIS item locator. The retained 2021 Statistics Canada row provides a dated cross-check, but exact topological inequality means it cannot be treated as a byte/geometry substitute for the current contact.",
            "Statistics Canada Census Division is statistical geography, not a physical land/water or shoreline product; a CD/RD code does not establish legal authority for every fragment or resident/local-government coverage.",
            "GSHHG is a global 2017 shoreline/land product with heterogeneous source observation dates and resolution/registration limits. Its absence of a matching mapped water feature does not demonstrate dry land.",
            "The nine construction contradictions remain the accepted numeric diagnosis; they are not independent physical-source validation. Eighteen numeric prerequisites, one replay mismatch, all fifteen nonnumeric siblings, and all original query records remain attached and unapproved.",
            "Whole-family emitted impact 116441477.74262899 m² is inherited diagnostic accounting only; it is not a new area computation, confirmed land, a legal area, or a correction proposal."
        ]}
    scope_summary = {
        "family_id": FAMILY, "operational_batch_id": family["operational_batch"],
        "complete_component_count": 43, "complete_component_ids": component_ids,
        "complete_contact_ids": [CONTACT], "numeric_component_count": 28,
        "numeric_diagnosis_status_counts": dict(category_counts),
        "nonnumeric_sibling_count": 15,
        "nonnumeric_component_ids": sorted(component_set - numeric_ids),
        "complete_query_relation_count": sum(r["original_physical_record"]["query_relation_count"] for r in review_rows),
        "family_row_sha256": EXPECTED_FAMILY_HASH,
        "family_impact_m2_inherited": family["measured_fragment_area_sum_m2"],
        "physical_status_counts": dict(Counter(r["routing"]["physical_status"] for r in review_rows)),
        "source_fitness": family["source_fitness"], "physical_authority": family["physical_authority"],
        "source_fitness_dispositions": Counter(r["source_fitness_disposition"] for r in review_rows)}

    payloads = {
        "family-row.json": canonical(family),
        "component-review.jsonl": review_jsonl,
        "source-input-pins.json": canonical(source_input_pins),
        "source-assessment.json": canonical(source_assessment),
        "scope-summary.json": canonical(scope_summary),
    }
    run_outputs = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                   for name, raw in sorted(payloads.items())]
    payloads["run-receipt.json"] = canonical({
        "version": 1, "issue": 1362, "lane": "geography",
        "worker_id": "01a11522-1da9-75a1-8ecb-765bae224f1c",
        "baseline_commit": main_sha,
        "source_record_members": component_ids,
        "active_geographic_subject_ids": [CONTACT],
        "pins": {
            "accepted_routing_report": sha(route_report_bytes),
            "accepted_numeric_diagnosis_report": sha(diagnosis_report_bytes),
            "complete_family_row": EXPECTED_FAMILY_HASH,
            "current_contact_feature": contact_hash,
            "2021_statistics_canada_Capital_feature": sha(canonical(stats_feature)),
            "complete_component_review_jsonl": sha(review_jsonl)},
        "outputs": run_outputs,
        "metrics": {
            "complete_physical_components": 43,
            "full_contacts": 1,
            "complete_numeric_siblings": 28,
            "local_construction_contradictions": 9,
            "retained_unresolved_numeric_or_context": 18,
            "retained_original_replay_mismatches": 1,
            "nonnumeric_siblings": 15,
            "complete_original_query_relations": sum(r["original_physical_record"]["query_relation_count"] for r in review_rows)},
        "limits": source_assessment["source_role_limits"],
        "validation": {"authenticated_complete_routing_parts": len(family_parts) + len(component_parts),
                       "authenticated_numeric_diagnosis_parts": len(diagnosis_parts),
                       "authenticated_original_physical_containing_files": len(physical_pins),
                       "selected_original_physical_rows": len(physical_rows),
                       "selected_component_route_rows": len(route_components),
                       "selected_numeric_diagnosis_rows": len(diagnosis_rows),
                       "exact_route_diagnosis_component_membership": True,
                       "complete_contact_identity": True,
                       "source_contact_topological_comparison_recorded": True},
        "change_receipts": [], "review_kind": "source"})
    destination.publish_bytes(payloads)
    print(json.dumps({"result": "PASS", "output": str(out), "components": len(review_rows),
                      "contacts": 1, "queries": sum(r["original_physical_record"]["query_relation_count"] for r in review_rows),
                      "numeric_status_counts": dict(category_counts),
                      "physical_status_counts": dict(Counter(r["routing"]["physical_status"] for r in review_rows)),
                      "contact_vs_2021_topologically_equal": topology_equal}, sort_keys=True))


if __name__ == "__main__":
    main()
