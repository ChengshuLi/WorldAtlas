#!/usr/bin/env python3
"""Bind the retained 30 source-rule-fit cases without rerunning geography."""

from __future__ import annotations

import gzip
import hashlib
import json
import pathlib
import subprocess
import types
import argparse


ROOT = pathlib.Path("research/geography/southeast-asia-gap-batch-0393f64c-20261009")
SOURCE_COMMIT = "b2b34087682b9a20e53c72c83f6d53054e09e8cf"
CANONICAL_SOURCE_COMMIT = "d07f64b2feab45f4eb2583743da74de91f8bbcce"
INDEX_PATH = ROOT / "inputs/geo3-next-full-batch-318.json"
STATE_PATH = ROOT / "vintages/roster-reconcile-001/component-state.json"
PHASE1_PATH = ROOT / "vintages/priority-source-target-001/priority-source-target.json"
CUSTODY_PATH = ROOT / "inputs/physical-custody-003"
OWNED_PREFIX = "research/geography/southeast-asia-gap-batch-0393f64c-20261009/"
OUTPUT_NAMES = [
    "administrative-source-rule-fit.json",
    "component-state-318.json",
    "family-roster-122.json",
]


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha(value: object) -> str:
    return sha(canonical_bytes(value))


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"])


def git_descriptor(revision: str, path: str, body: bytes | None = None) -> dict:
    mode, kind, blob = subprocess.check_output(
        ["git", "ls-tree", revision, "--", path], text=True
    ).strip().split("\t", 1)[0].split()
    assert mode == "100644" and kind == "blob", (revision, path, mode, kind)
    body = git_bytes(revision, path) if body is None else body
    assert subprocess.check_output(
        ["git", "hash-object", "--stdin"], input=body
    ).decode().strip() == blob
    return {
        "commit": revision,
        "path": path,
        "mode": mode,
        "blob": blob,
        "bytes": len(body),
        "sha256": sha(body),
    }


def main(vintage_name: str) -> None:
    # Discover the complete bounded input inventory before calculations, then
    # authenticate every input and helper against the immutable source commit.
    # Materialized custody files are checked against those same pinned bytes.
    manifest_path = CUSTODY_PATH / "manifest.json"
    discovery_manifest = json.loads(git_bytes(SOURCE_COMMIT, str(manifest_path)))
    state_path = STATE_PATH
    index_raw = git_bytes(SOURCE_COMMIT, str(INDEX_PATH))
    index = json.loads(index_raw)
    state_raw = git_bytes(SOURCE_COMMIT, str(STATE_PATH))
    state = json.loads(state_raw)
    phase_raw = git_bytes(SOURCE_COMMIT, str(PHASE1_PATH))
    phase = json.loads(phase_raw)
    custody_manifest_raw = git_bytes(SOURCE_COMMIT, str(manifest_path))
    custody_manifest = json.loads(custody_manifest_raw)
    custody_index_path = CUSTODY_PATH / "index.json.gz"
    custody_index_raw = git_bytes(SOURCE_COMMIT, str(custody_index_path))
    custody_index_decoded = None
    expected_ids = index["original_batch"]["complete_component_ids"]
    state_rows = state["rows"]
    assert len(expected_ids) == 318 and len(set(expected_ids)) == 318
    assert {row["component_id"] for row in state_rows} == set(expected_ids)
    assert state["component_count"] == 318 and state["family_count"] == 122

    families: dict[str, list[str]] = {}
    for row in state_rows:
        for family in row["family_locators"]:
            families.setdefault(family, []).append(row["component_id"])
    family_rows = [
        {"family_id": family, "component_ids": ids, "component_count": len(ids)}
        for family, ids in sorted(families.items())
    ]
    assert len(family_rows) == 122
    expected_priority = set(phase["cases"][i]["component_id"] for i in range(30))
    assert len(expected_priority) == 30
    assert {row["component_id"] for row in phase["cases"]} == expected_priority

    # Enumerate only the exact retained case and pointset payloads used below.
    selected_case_paths = sorted(
        item["path"] for item in discovery_manifest["payloads"]
        if "/cases/" in item["path"] and item["path"].endswith(".json.gz")
    )
    source_paths = sorted(
        item["path"] for item in discovery_manifest["payloads"]
        if "/sources/" in item["path"] and item["path"].endswith(".json.gz")
    )
    target_paths = sorted({
        row["target_record"]["path"] for row in phase["cases"]
    })
    static_paths = [
        str(INDEX_PATH), str(STATE_PATH), str(PHASE1_PATH),
        str(manifest_path), str(custody_index_path),
        "scripts/evidence/immutable.py", "scripts/evidence/contracts.py",
        "data/hierarchy.json", "data/administrative-sources.json",
        "scripts/administrative.py", "data/administrative-sources.json",
    ]
    # Keep the separately historical recipe and registry as explicit admitted
    # inputs. Their original commit identities remain recorded in the outputs.
    historical_paths = [
        (CANONICAL_SOURCE_COMMIT, "scripts/administrative.py"),
        ("79ffb2ed04702e16f009e4675a8d74ef9bd09d4f", "data/administrative-sources.json"),
    ]
    materialized_paths = sorted(set(
        selected_case_paths + source_paths + [str(custody_index_path)] + [
            str(ROOT / "inputs/source-products" / (p["product_id"].replace(":", "-") + ".bin"))
            for p in phase["source_products"]
        ]
    ))
    pin_inputs = {}
    for path in static_paths + target_paths:
        pin_inputs[(SOURCE_COMMIT, path)] = git_bytes(SOURCE_COMMIT, path)
    for revision, path in historical_paths:
        pin_inputs[(revision, path)] = git_bytes(revision, path)
    for path in materialized_paths:
        pin_inputs[(SOURCE_COMMIT, path)] = git_bytes(SOURCE_COMMIT, path)
    pin_files = []
    for (revision, path), raw in sorted(pin_inputs.items()):
        # Baseline is intentionally one immutable commit. Historical inputs are
        # accounted separately below and remain explicitly revision-bound.
        if revision == SOURCE_COMMIT:
            pin_files.append({"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
    helper_raw = pin_inputs[(SOURCE_COMMIT, "scripts/evidence/immutable.py")]
    # Load pinned helper source from authenticated bytes under its real package
    # names, without importing mutable checkout code or writing helper files.
    immutable_helpers = types.ModuleType("immutable")
    exec(compile(helper_raw, "scripts/evidence/immutable.py", "exec"), immutable_helpers.__dict__)
    contract_helpers = types.ModuleType("contracts")
    exec(
        compile(pin_inputs[(SOURCE_COMMIT, "scripts/evidence/contracts.py")], "scripts/evidence/contracts.py", "exec"),
        contract_helpers.__dict__,
    )
    repo_root = pathlib.Path.cwd()
    baseline = immutable_helpers.Baseline(repo_root, SOURCE_COMMIT, pin_files)
    # Historical revisions and materialized representations share the same
    # complete phase budget even though they are authenticated separately.
    for (revision, path), raw in pin_inputs.items():
        if revision != SOURCE_COMMIT:
            baseline.admit(f"{revision}:{path}", len(raw))
    vintage = immutable_helpers.NewVintage(baseline, OWNED_PREFIX, vintage_name, OUTPUT_NAMES)
    exact_rows = contract_helpers.exact_rows
    join_rows = contract_helpers.join_rows

    # Authenticate local custody bytes before using them.
    materialized_bytes = {
        relative: baseline.materialized_bytes(relative)
        for relative in materialized_paths
    }
    # From this point onward, calculations consume only returned authenticated
    # baseline/materialized bytes, never a second read of a checked input.
    index_raw = baseline.pinned_bytes(str(INDEX_PATH))
    index = json.loads(index_raw)
    state_raw = baseline.pinned_bytes(str(STATE_PATH))
    state = json.loads(state_raw)
    state_path = STATE_PATH
    state_rows = state["rows"]
    expected_ids = index["original_batch"]["complete_component_ids"]
    assert len(expected_ids) == 318 and len(set(expected_ids)) == 318
    assert len(state_rows) == 318 and {row["component_id"] for row in state_rows} == set(expected_ids)
    assert state["component_count"] == 318 and state["family_count"] == 122
    phase_raw = baseline.pinned_bytes(str(PHASE1_PATH))
    phase = json.loads(phase_raw)
    assert sorted({row["target_record"]["path"] for row in phase["cases"]}) == target_paths
    custody_manifest_raw = baseline.pinned_bytes(str(manifest_path))
    custody_manifest = json.loads(custody_manifest_raw)
    custody_index_raw = materialized_bytes[str(custody_index_path)]
    custody_index_decoded = gzip.decompress(custody_index_raw)
    custody_index = json.loads(custody_index_decoded)
    baseline.admit(f"decoded:{custody_index_path}", len(custody_index_decoded))
    assert exact_rows(state_rows, expected_ids, key="component_id")

    families: dict[str, list[str]] = {}
    for row in state_rows:
        for family in row["family_locators"]:
            families.setdefault(family, []).append(row["component_id"])
    family_rows = [
        {"family_id": family, "component_ids": ids, "component_count": len(ids)}
        for family, ids in sorted(families.items())
    ]
    assert len(family_rows) == 122
    expected_priority = {row["component_id"] for row in phase["cases"]}
    assert len(phase["cases"]) == 30 and len(expected_priority) == 30

    current_hierarchy_path = "data/hierarchy.json"
    current_admin_registry_path = "data/administrative-sources.json"
    hierarchy_raw = baseline.pinned_bytes(current_hierarchy_path)
    admin_registry_raw = baseline.pinned_bytes(current_admin_registry_path)
    hierarchy_desc = git_descriptor(SOURCE_COMMIT, current_hierarchy_path, hierarchy_raw)
    admin_registry_desc = git_descriptor(SOURCE_COMMIT, current_admin_registry_path, admin_registry_raw)
    hierarchy = json.loads(hierarchy_raw)
    hierarchy_by_id = {row["id"]: (i, row) for i, row in enumerate(hierarchy)}
    current_registry = json.loads(admin_registry_raw)
    recipe_desc = git_descriptor(CANONICAL_SOURCE_COMMIT, "scripts/administrative.py", pin_inputs[(CANONICAL_SOURCE_COMMIT, "scripts/administrative.py")])
    historical_registry_desc = git_descriptor(
        "79ffb2ed04702e16f009e4675a8d74ef9bd09d4f", "data/administrative-sources.json",
        pin_inputs[("79ffb2ed04702e16f009e4675a8d74ef9bd09d4f", "data/administrative-sources.json")],
    )

    phase_products = {row["product_id"]: row for row in phase["source_products"]}
    phase_cases = {row["component_id"]: row for row in phase["cases"]}
    target_containers = {}
    product_capture = {}
    for product_id, product in sorted(phase_products.items()):
        captured = product["captured_file"]
        local_path = ROOT / "inputs/source-products" / (product_id.replace(":", "-") + ".bin")
        captured_bytes = materialized_bytes[str(local_path)]
        decoded = gzip.decompress(captured_bytes)
        baseline.admit(f"decoded:{local_path}", len(decoded))
        assert len(captured_bytes) == captured["bytes"]
        assert sha(captured_bytes) == captured["sha256"]
        assert len(decoded) == captured["uncompressed_bytes"]
        assert sha(decoded) == captured["uncompressed_sha256"]
        assert sha(decoded) == product["original_atlas_registry"]["sha256"]
        assert product["url"].endswith("_simplified.geojson")
        product_capture[product_id] = {
            "metadata": product,
            "retained_capture_path": str(local_path),
            "retained_capture_bytes": len(captured_bytes),
            "retained_capture_sha256": sha(captured_bytes),
            "decoded_source_bytes": len(decoded),
            "decoded_source_sha256": sha(decoded),
            "raw_simplified_geojson": json.loads(decoded),
            "current_registry_entry": current_registry.get(product_id),
        }
        current_entry = current_registry.get(product_id)
        assert current_entry is not None
        assert current_entry["sha256"] == product["original_atlas_registry"]["sha256"]
        assert current_entry["simplifiedGeometryGeoJSON"] == product["url"]
        assert current_entry["boundaryYearRepresented"] == product["original_atlas_registry"]["boundaryYearRepresented"]

    custody_files = {
        item["path"]: item for item in custody_manifest["payloads"]
    }
    query_source_payloads = {}
    for source_id in sorted(
        {
            int(name.name[:-8])
            for name in (CUSTODY_PATH / "sources").glob("*.json.gz").__iter__()
        }
    ):
        rel = f"{ROOT}/inputs/physical-custody-003/sources/{source_id}.json.gz"
        source_path = f"{CUSTODY_PATH}/sources/{source_id}.json.gz"
        payload = materialized_bytes[source_path]
        source_decoded = gzip.decompress(payload)
        baseline.admit(f"decoded:{source_path}", len(source_decoded))
        source_bundle = json.loads(source_decoded)
        descriptor = custody_files[rel]
        assert sha(payload) == descriptor["sha256"] and len(payload) == descriptor["bytes"]
        query_source_payloads[source_id] = {
            "source_file": rel,
            "bytes": len(payload),
            "sha256": sha(payload),
            "uncompressed_bytes": descriptor["uncompressed_bytes"],
            "uncompressed_sha256": descriptor["uncompressed_sha256"],
            "binary64_pointset_sha256": source_bundle["source"]["decoded_pointset_binary64_sha256"],
            "coordinate_bytes_sha256": source_bundle["source"]["coordinate_bytes_sha256"],
            "geometry_status": source_bundle["source"]["geometry_status"],
            "source_record_pointer": "/source",
        }
    assert len(query_source_payloads) == 35
    rows = []
    case_paths = sorted((CUSTODY_PATH / "cases").glob("*.json.gz"))
    for case_path in case_paths:
        case_file_rel = str(case_path)
        packed = materialized_bytes[case_file_rel]
        case_decoded = gzip.decompress(packed)
        baseline.admit(f"decoded:{case_file_rel}", len(case_decoded))
        case_bundle = json.loads(case_decoded)
        case = case_bundle["case"]
        component_id = case["component_id"]
        if component_id not in expected_priority:
            continue
        assert case_bundle["batch_id"] == index["original_batch"]["batch_id"]
        assert str(case_path).replace(str(pathlib.Path.cwd()) + "/", "") in custody_files
        case_meta = custody_files[case_file_rel]
        assert len(packed) == case_meta["bytes"] and sha(packed) == case_meta["sha256"]
        assert case_meta["uncompressed_sha256"] == sha(gzip.decompress(packed))

        binding = case["administrative_source_target"]
        comp = case["existing_full_admin_comparison"]
        assert binding is not None and comp is not None
        record = comp["record"]
        source_product_id = binding["source_product"]
        source_capture = product_capture[source_product_id]
        source_gj = source_capture["raw_simplified_geojson"]
        source_ordinal = binding["source_record_ordinal"]
        source_feature = binding["source_feature"]
        assert source_gj["features"][source_ordinal - 1] == source_feature
        assert canonical_sha(source_feature) == binding["source_feature_sha256"]
        assert canonical_sha(source_feature["geometry"]) == binding["source_geometry_sha256"]
        assert source_feature["properties"]["shapeID"] == binding["source_subject_id"].split(":")[-1]
        assert binding["source_subject_id"].startswith(source_product_id + ":")

        target_feature = binding["target_record_feature"]
        assert canonical_sha(target_feature) == binding["target_record_feature_sha256"]
        assert canonical_sha(target_feature["geometry"]) == binding["target_record_geometry_sha256"]
        target_feature_id = binding["target_feature_id"]
        assert target_feature["id"] == target_feature_id == component_id
        assert record["component"] == component_id
        assert record["full_component_feature_sha256"] == binding["target_record_feature_sha256"]
        assert record["component_geometry_sha256"] == binding["target_record_geometry_sha256"]
        assert record["current_component_source_successor"]

        target_path = binding["target_record_path"]
        if target_path not in target_containers:
            target_blob_bytes = baseline.pinned_bytes(target_path)
            target_descriptor = git_descriptor(SOURCE_COMMIT, target_path, target_blob_bytes)
            target_containers[target_path] = (
                target_blob_bytes,
                target_descriptor,
                json.loads(target_blob_bytes),
            )
        target_blob_bytes, target_descriptor, target_container = target_containers[target_path]
        target_reference = phase_cases[component_id]["target_record"]
        assert len(target_blob_bytes) == target_reference["bytes"]
        assert target_descriptor["sha256"] == target_reference["sha256"]
        assert target_descriptor["path"] == target_reference["path"]
        target_features = target_container["features"]
        target_ordinal = target_reference["record_ordinal"]
        assert target_features[target_ordinal - 1] == target_feature
        assert canonical_sha(target_feature) == target_reference["feature_sha256"]
        assert canonical_sha(target_feature["geometry"]) == target_reference["geometry_sha256"]

        unique = record.get("uniquely_covering_compatible_recorded_subject")
        assert unique is not None and unique["id"] == binding["source_subject_id"]
        assert unique["original_parent_id"]
        hierarchy_idx, parent_row = hierarchy_by_id[unique["original_parent_id"]]
        assert parent_row["metadata"]["framework_status"] == "retained-reference"
        assert parent_row["metadata"]["semantic_review"]["action"] == "open"

        residual = record["component_minus_source_union"]
        assert residual["geometry_type"] and residual["geometry_sha256"]
        assert residual["is_valid"] in (True, False)
        is_union_full = residual["is_empty"] is True
        if is_union_full:
            assert residual["planar_area_coordinate_units_squared"] == 0.0
            assert residual["planar_length_coordinate_units"] == 0.0
        intersects = record["feature_intersections"]
        assert intersects
        covering = [x for x in intersects if x["source_feature_covers_entire_component"] is True]
        assert len(covering) == 1 and covering[0]["binding"]["recorded_stable_subjects"][0]["id"] == unique["id"]
        assert record["source_union_intersection"]["is_valid"] in (True, False)
        assert record["whole_relevant_source_union"]
        source_refs = []
        for source_id in case["physical_query_source_ids"]:
            source_ref = query_source_payloads[int(source_id)]
            related = [
                relation
                for relation in case["physical_query_relations"]
                if int(relation["source_id"]) == int(source_id)
            ]
            assert related
            assert all(
                relation["source_pointset_sha256"] == source_ref["binary64_pointset_sha256"]
                for relation in related
            )
            source_refs.append(source_ref)

        relation_status = "established" if is_union_full else "partial"
        required_exceptions = []
        if not is_union_full:
            required_exceptions.append("original-source-union-residual-is-nonempty")
        required_exceptions.extend(
            [
                "selected-current-owner-and-owner-parent-binding-remains-engineering-owned",
                "selected-native-cell-and-uncovered-cell-binding-remains-engineering-owned",
                "contemporary-physical-class-and-land-water-status-are-unverified",
                "source-observation-date-and-registration-accuracy-remain-unresolved",
                "cause-and-repair-authority-remain-unknown",
            ]
        )

        rows.append(
            {
                "component_id": component_id,
                "family_id": case["family_id"],
                "country_codes": phase_cases[component_id]["country_codes"],
                "source_rule_fit_state": relation_status,
                "whole_gap_completion": False,
                "source_product": source_capture["metadata"],
                "source_product_capture": {
                    "retained_capture_path": source_capture["retained_capture_path"],
                    "retained_capture_bytes": source_capture["retained_capture_bytes"],
                    "retained_capture_sha256": source_capture["retained_capture_sha256"],
                    "decoded_source_bytes": source_capture["decoded_source_bytes"],
                    "decoded_source_sha256": source_capture["decoded_source_sha256"],
                    "advertised_original_registry_sha256": source_capture["metadata"]["original_atlas_registry"]["sha256"],
                    "current_registry_entry": source_capture["current_registry_entry"],
                },
                "original_atlas_recipe_descriptor": recipe_desc,
                "original_atlas_registry_descriptor": historical_registry_desc,
                "source_feature": {
                    "feature": source_feature,
                    "canonical_feature_sha256": binding["source_feature_sha256"],
                    "canonical_geometry_sha256": binding["source_geometry_sha256"],
                    "source_id": source_product_id,
                    "source_subject_id": binding["source_subject_id"],
                    "source_record_ordinal_one_based": source_ordinal,
                },
                "compatible_recorded_subject": {
                    "record": unique,
                    "current_hierarchy_row": parent_row,
                    "hierarchy_array_record_ordinal_zero_based": hierarchy_idx,
                    "current_hierarchy_descriptor": hierarchy_desc,
                    "parent_geometry_in_hierarchy": False,
                    "semantic_review_status": parent_row["metadata"]["semantic_review"]["action"],
                },
                "current_component_candidate": {
                    "feature": target_feature,
                    "component_id": target_feature_id,
                    "feature_sha256": binding["target_record_feature_sha256"],
                    "geometry_sha256": binding["target_record_geometry_sha256"],
                    "source_path": target_path,
                    "containing_source_descriptor": target_descriptor,
                    "record_ordinal_one_based": target_ordinal,
                    "current_component_source_successor": record["current_component_source_successor"],
                    "selected_effective_owner_binding": "not-present; engineering-owned",
                    "candidate_administrative_assignment": target_feature.get("properties", {}).get("administrative_assignment"),
                    "candidate_parent_id": target_feature.get("properties", {}).get("parent_id"),
                    "current_effective_owner_parent_binding": {
                        "status": "unavailable-from-retained-component-candidate",
                        "reason": "The full component candidate does not carry a selected current effective-owner or parent binding; Engineering owns selection and native qualification.",
                    },
                },
                "original_administrative_comparison": {
                    "descriptor": comp["descriptor"],
                    "record_ordinal_one_based": comp["record_ordinal_one_based"],
                    "record": record,
                    "record_canonical_sha256": canonical_sha(record),
                    "component_minus_source_union": residual,
                    "feature_intersections": intersects,
                    "uniquely_covering_compatible_recorded_subject": unique,
                    "source_union_intersection": record["source_union_intersection"],
                    "whole_relevant_source_union": record["whole_relevant_source_union"],
                },
                "original_physical_query_custody": {
                    "case_file": case_file_rel,
                    "case_file_bytes": len(packed),
                    "case_file_sha256": sha(packed),
                    "case_file_uncompressed_sha256": case_meta["uncompressed_sha256"],
                    "complete_original_case_pointer": "/case",
                    "complete_candidate_pointer": "/case/complete_current_component_candidate",
                    "physical_comparison_pointer": "/case/physical_comparison_packed_row",
                    "physical_query_relations_pointer": "/case/physical_query_relations",
                    "physical_query_source_ids_pointer": "/case/physical_query_source_ids",
                    "complete_original_query_relations": case["physical_query_relations"],
                    "complete_original_packed_comparison_row": case["physical_comparison_packed_row"],
                    "complete_original_query_source_ids": case["physical_query_source_ids"],
                    "complete_query_source_pointsets": source_refs,
                },
                "source_date_and_authority_limits": [
                    "The advertised represented year is source metadata, not an authenticated per-feature observation date.",
                    "Historical retrieval time is unknown; exact source/feature registration accuracy has not been established.",
                    "Source-relative mapped-land overlap does not establish contemporary land/water, legal ownership, cause, repair authority, or approval.",
                ],
                "missing_required_premises": required_exceptions,
            }
        )

    assert len(rows) == 30 and {r["component_id"] for r in rows} == expected_priority
    rows.sort(key=lambda r: r["component_id"])
    counts = {
        "priority_components": len(rows),
        "source_products": len(product_capture),
        "established_full_source_union": sum(r["source_rule_fit_state"] == "established" for r in rows),
        "partial_nonempty_original_source_union_residual": sum(r["source_rule_fit_state"] == "partial" for r in rows),
        "missing_original_required_source_relation": sum(r["source_rule_fit_state"] == "missing-required-premise" for r in rows),
        "whole_gap_completion": 0,
        "approved_repairs": 0,
        "accepted_physical_classes": 0,
    }
    state_output = {
        "batch_id": index["original_batch"]["batch_id"],
        "component_count": 318,
        "family_count": 122,
        "priority_component_count": 30,
        "other_component_count": 288,
        "batch_index": {"path": str(INDEX_PATH), "bytes": len(index_raw), "sha256": sha(index_raw)},
        "prior_component_state": {"path": str(state_path), "bytes": len(state_raw), "sha256": sha(state_raw)},
        "rows": state_rows,
        "family_rows": family_rows,
    }
    fit_output = {
        "version": 1,
        "batch_id": index["original_batch"]["batch_id"],
        "scope": "Same complete 318-ID / 122-family batch; exact 30 priority cases; no subbatch.",
        "current_source_bank_commit": SOURCE_COMMIT,
        "canonical_existing_comparison_commit": CANONICAL_SOURCE_COMMIT,
        "current_source_bank_descriptors": {
            "hierarchy": hierarchy_desc,
            "administrative_sources": admin_registry_desc,
            "current_hierarchy_note": "Parent rows are retained-reference records with open semantic review; they are not selected effective-owner geometry.",
        },
        "historical_source_recipe": recipe_desc,
        "historical_registry": historical_registry_desc,
        "custody_manifest": {
            "path": str(CUSTODY_PATH / "manifest.json"),
            "bytes": len(custody_manifest_raw),
            "sha256": sha(custody_manifest_raw),
            "counts": custody_manifest["counts"],
        },
        "original_query_pointsets": {
            "custody_index_path": str(CUSTODY_PATH / "index.json.gz"),
            "custody_index_bytes": len(custody_index_raw),
            "custody_index_sha256": sha(custody_index_raw),
            "pointset_count": len(query_source_payloads),
            "selected_pointsets": sorted(query_source_payloads.values(), key=lambda x: x["source_file"]),
            "complete_coordinates_are_in_the_bound_source_payloads": True,
        },
        "counts": counts,
        "limitations": [
            "All source and target features and relations below are retained original records. No overlay, GIS, source or native operator was run.",
            "The target is the complete current physical component candidate; no selected effective current administrative owner/parent or native cell binding is asserted.",
            "Compatible subject parents are separately bound to current hierarchy rows. Their semantic review is open and those rows contain no geometry.",
            "All 318 component states and all 122 family mappings are copied from the prior accepted ledger unchanged; this continuation changes no decisions or repair state.",
            "Recorded source coverage is not contemporary physical truth, water/ice qualification, authority, cause, source policy approval, or repair eligibility.",
        ],
        "cases": rows,
    }
    family_output = {
        "batch_id": index["original_batch"]["batch_id"],
        "family_count": len(family_rows),
        "component_count": 318,
        "families": family_rows,
    }
    # Revalidate cross-phase identities and publish the complete run atomically.
    exact_rows(rows, sorted(expected_priority), key="component_id")
    join_rows(
        [{"component_id": row["component_id"], "family_id": row["family_id"], "country_codes": row["country_codes"]} for row in rows],
        [{"component_id": row["component_id"], "family_id": row["family_id"], "country_codes": row["country_codes"]} for row in phase["cases"]],
        {"family_id": "family_id", "country_codes": "country_codes"},
        key="component_id", reference_key="component_id",
    )
    vintage.publish({
        "administrative-source-rule-fit.json": fit_output,
        "component-state-318.json": state_output,
        "family-roster-122.json": family_output,
    })
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintage", required=True, help="unused fresh source-rule-fit vintage name")
    main(parser.parse_args().vintage)
