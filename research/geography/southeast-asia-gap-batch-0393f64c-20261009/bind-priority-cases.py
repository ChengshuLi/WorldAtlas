#!/usr/bin/env python3
"""Bind the 30 preselected cases to exact Atlas source products and retained target pointsets."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from scripts.evidence.immutable import Baseline, NewVintage, descriptor, sha256  # noqa: E402

OWNED = "research/geography/southeast-asia-gap-batch-0393f64c-20261009/"
INDEX_PATH = Path(REPO, OWNED, "inputs/geo3-next-full-batch-318.json")
INDEX_SHA = "9857d3c03f94799b4e7e22c9afce68259dc4e2747d2864d6eb580030222f3430"
REFRESH_MANIFEST = "coordination/engineering/global-gap-candidate-refresh-20261009/evidence-quality.json"
TARGET_MANIFEST = "research/geography/indonesia-borneo-source-fitness-20261007/evidence-quality.json"
ADMIN_REGISTRY_COMMIT = "79ffb2ed04702e16f009e4675a8d74ef9bd09d4f"
ADMIN_SCRIPT_COMMIT = "cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1"


def git_bytes(commit, path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{path}"])


def manifest_at(head, path):
    return json.loads(git_bytes(head, path))


def digest_json(value):
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    return sha256(raw)


def main():
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    index_raw = INDEX_PATH.read_bytes()
    if sha256(index_raw) != INDEX_SHA:
        raise ValueError("the retained original batch index differs from its raw custody hash")
    index = json.loads(index_raw)
    batch = index["original_batch"]
    contract_doc = json.loads(Path(REPO, OWNED, "inputs/issue-contract-readback.json").read_bytes())
    contract = contract_doc["contract"]["evidence_quality"]
    subjects = contract["subject_ids"]
    if len(subjects) != 30 or len(subjects) != len(set(subjects)):
        raise ValueError("issue contract no longer binds exactly 30 unique source-geometry subjects")
    selected_by_id = {}
    for family in index["existing_priority_families"]:
        for component in family["research_component_ids"]:
            if component in selected_by_id:
                raise ValueError("duplicate priority ID in retained family index: " + component)
            selected_by_id[component] = family
    if set(selected_by_id) != set(subjects):
        raise ValueError("retained original priority roster and current issue subjects disagree")

    state_path = Path(REPO, OWNED, "vintages/roster-reconcile-001/component-state.json")
    state = json.loads(state_path.read_bytes())
    state_by_id = {row["component_id"]: row for row in state["rows"]}
    if len(state_by_id) != 318 or set(state_by_id) != set(batch["complete_component_ids"]):
        raise ValueError("the whole-batch state ledger is incomplete or has fabricated IDs")

    helper_raw = Path(REPO, "scripts/evidence/immutable.py").read_bytes()
    helper_desc = descriptor("scripts/evidence/immutable.py", helper_raw)
    refresh = manifest_at(head, REFRESH_MANIFEST)
    target_manifest = manifest_at(head, TARGET_MANIFEST)
    refresh_outputs = {x["path"]: x for x in refresh["outputs"]}
    target_outputs = {x["path"]: x for x in target_manifest["outputs"]}

    # The issue's 63 immutable pins are exact original membership, complete catalog,
    # and full target-geometry bytes. Reconstruct their path inventory from manifests.
    membership_outputs = sorted((x for x in refresh["outputs"] if "/corrected-run-1-leaf-" in x["path"]
                                  and x["path"].endswith("/membership-metrics.jsonl.gz")), key=lambda x: x["path"])
    catalog_outputs = sorted((x for x in refresh["outputs"] if "/corrected-run-1-leaf-" in x["path"]
                              and "/catalog-" in x["path"] and x["path"].endswith(".jsonl.gz")), key=lambda x: x["path"])
    target_outputs_list = sorted((x for x in target_manifest["outputs"] if "/restore-450126d0/components-" in x["path"]
                                  and x["path"].endswith(".json")), key=lambda x: x["path"])
    if (len(membership_outputs), len(catalog_outputs), len(target_outputs_list)) != (7, 45, 11):
        raise ValueError("current retained membership/catalog/target input inventory changed")

    pin_files = {}
    for i, desc in enumerate(membership_outputs, 1):
        pin_files[f"membership_leaf_{i:02d}"] = desc["path"]
    for desc in catalog_outputs:
        leaf = int(desc["path"].split("corrected-run-1-leaf-")[1][:2])
        shard = int(desc["path"].rsplit("catalog-", 1)[1].split(".", 1)[0])
        pin_files[f"catalog_leaf_{leaf:02d}_shard_{shard:02d}"] = desc["path"]
    for i, desc in enumerate(target_outputs_list):
        pin_files[f"prior_component_shard_{i:03d}"] = desc["path"]
    if set(pin_files) != set(contract["pins"]):
        raise ValueError("exact issue pin aliases differ from verified source-output paths")
    pins = {alias: refresh_outputs.get(path, target_outputs.get(path, {})).get("sha256")
            for alias, path in pin_files.items()}
    if pins != contract["pins"]:
        raise ValueError("one or more current baseline bytes no longer match the issue's exact pin")

    # Stream only the 30 exact priority rows from complete catalog leaves. Each
    # independent leaf phase stays under the shared 256 MiB input+decoded budget.
    catalog_by_id = {}
    catalog_rows = {}
    catalog_phase_receipts = []
    for leaf in range(1, 8):
        leaf_outputs = [x for x in catalog_outputs if f"corrected-run-1-leaf-{leaf:02d}/" in x["path"]]
        phase_files = leaf_outputs + [helper_desc]
        baseline = Baseline(str(REPO), head, phase_files)
        leaf_records = 0
        for desc in leaf_outputs:
            raw = baseline.pinned_bytes(desc["path"])
            decoded = gzip.decompress(raw)
            baseline.admit(desc["path"] + ":decoded", len(decoded))
            for ordinal, line in enumerate(decoded.splitlines(), 1):
                if not line:
                    continue
                leaf_records += 1
                row = json.loads(line)
                identity = row.get("component_id")
                if identity in subjects:
                    if identity in catalog_by_id:
                        raise ValueError("priority ID appears more than once in catalog: " + identity)
                    catalog_by_id[identity] = row
                    catalog_rows[identity] = {"path": desc["path"], "bytes": desc["bytes"],
                                              "sha256": desc["sha256"], "record_ordinal": ordinal}
        catalog_phase_receipts.append({"leaf": leaf, "files": [x["path"] for x in leaf_outputs],
                                       "encoded_bytes": sum(x["bytes"] for x in leaf_outputs),
                                       "decoded_bytes": sum(x["uncompressed_bytes"] for x in leaf_outputs),
                                       "catalog_rows_scanned": leaf_records})
    if set(catalog_by_id) != set(subjects):
        raise ValueError("latest corrected full catalog is missing priority identities: " + str(sorted(set(subjects)-set(catalog_by_id))))

    # Bind exact current target pointsets from the retained full component features.
    targets = {}
    target_baseline = Baseline(str(REPO), head, target_outputs_list + [helper_desc])
    for desc in target_outputs_list:
        raw = target_baseline.pinned_bytes(desc["path"])
        doc = json.loads(raw)
        if doc.get("type") != "FeatureCollection" or not isinstance(doc.get("features"), list):
            raise ValueError("retained target component source is not a complete FeatureCollection")
        for ordinal, feature in enumerate(doc["features"], 1):
            identity = feature.get("id")
            if identity in subjects:
                if identity in targets:
                    raise ValueError("priority target feature occurs in more than one retained shard: " + identity)
                targets[identity] = {"feature": feature, "pin": desc, "record_ordinal": ordinal,
                                     "feature_sha256": digest_json(feature),
                                     "geometry_sha256": digest_json(feature["geometry"])}
    if set(targets) != set(subjects):
        raise ValueError("retained full target component features do not cover all 30 priority IDs")

    # Retain the exact first-pass source rows. This is read-only reuse of previous
    # source overlays, not a new geometry calculation.
    packets = sorted({catalog_by_id[x]["source_evidence"]["source_comparison_packet"] for x in subjects})
    packet_manifests = {}
    packet_component_outputs = {}
    for packet in packets:
        manifest_path = f"coordination/engineering/{packet}/evidence-quality.json"
        manifest = manifest_at(head, manifest_path)
        packet_manifests[packet] = {"path": manifest_path, "document": manifest}
        files = [x for x in manifest["outputs"] if "/scientific/components-" in x["path"] and x["path"].endswith(".json.gz")]
        if not files:
            raise ValueError("source-comparison packet lacks retained whole-case output descriptors: " + packet)
        packet_component_outputs[packet] = sorted(files, key=lambda x: x["path"])
    comparisons = {}
    comparison_pins = {}
    for packet in packets:
        packet_ids = {x for x in subjects if catalog_by_id[x]["source_evidence"]["source_comparison_packet"] == packet}
        remaining = set(packet_ids)
        for desc in packet_component_outputs[packet]:
            if not remaining:
                break
            baseline = Baseline(str(REPO), head, [desc, helper_desc])
            compressed = baseline.pinned_bytes(desc["path"])
            decoded = gzip.decompress(compressed)
            baseline.admit(desc["path"] + ":decoded", len(decoded))
            records = json.loads(decoded)
            for ordinal, record in enumerate(records, 1):
                identity = record.get("component")
                if identity in remaining:
                    comparisons[identity] = {"record": record, "path": desc["path"],
                                             "bytes": desc["bytes"], "sha256": desc["sha256"],
                                             "uncompressed_sha256": desc["uncompressed_sha256"],
                                             "record_ordinal": ordinal}
                    comparison_pins[desc["path"]] = desc
                    remaining.remove(identity)
        if remaining:
            raise ValueError("existing source comparison output lacks exact priority IDs: " + str(sorted(remaining)))

    # Pin the original administrative metadata registry and recipe used by the
    # original Atlas source preparation, then validate actual simplified products.
    registry_path = "data/administrative-sources.json"
    registry_raw = git_bytes(ADMIN_REGISTRY_COMMIT, registry_path)
    registry_desc = descriptor(registry_path, registry_raw) | {"commit": ADMIN_REGISTRY_COMMIT}
    registry = json.loads(registry_raw)
    admin_script_path = "scripts/administrative.py"
    admin_script = git_bytes(ADMIN_SCRIPT_COMMIT, admin_script_path)
    admin_script_desc = descriptor(admin_script_path, admin_script) | {"commit": ADMIN_SCRIPT_COMMIT}
    if b"replace('.geojson','_simplified.geojson')" not in admin_script and b"replace(\".geojson\",\"_simplified.geojson\")" not in admin_script:
        raise ValueError("selected original administrative recipe does not bind the simplified product")

    source_registry = {}
    source_features = {}
    source_input_descriptors = {}
    source_packet_manifest_descriptors = {}
    for packet in packets:
        mpath = packet_manifests[packet]["path"]
        source_packet_manifest_descriptors[mpath] = descriptor(mpath, git_bytes(head, mpath))
        manifest = packet_manifests[packet]["document"]
        for source in manifest.get("sources", []):
            source_registry.setdefault(source["id"], []).append((packet, source))
    products = sorted({catalog_by_id[x]["source_evidence"]["source_products"] for x in subjects})
    for product in products:
        usages = []
        for packet, source in source_registry.get(product, []):
            # Keep the per-case citation to the packet named in the exact catalog row.
            if any(catalog_by_id[x]["source_evidence"]["source_comparison_packet"] == packet and
                   catalog_by_id[x]["source_evidence"]["source_products"] == product for x in subjects):
                usages.append((packet, source))
        if not usages:
            raise ValueError("priority product is not retained by its cited comparison packet: " + product)
        packet, source = usages[0]
        files = source.get("files", [])
        if len(files) != 1:
            raise ValueError("expected a whole single-file source product capture for " + product)
        product_desc = files[0]
        input_path = product_desc["path"]
        phase = Baseline(str(REPO), head, [product_desc, helper_desc])
        compressed = phase.pinned_bytes(input_path)
        source_raw = gzip.decompress(compressed) if compressed[:2] == b"\x1f\x8b" else compressed
        phase.admit(input_path + ":decoded", len(source_raw))
        if (product_desc.get("uncompressed_bytes") != len(source_raw) or
            product_desc.get("uncompressed_sha256") != sha256(source_raw)):
            raise ValueError("retained source-product content differs from its whole-product descriptor: " + product)
        registry_row = registry.get(product)
        if not registry_row:
            raise ValueError("original administrative registry lacks exact source product " + product)
        if registry_row.get("sha256") != sha256(source_raw):
            raise ValueError("original administrative registry product hash differs from captured source bytes: " + product)
        if registry_row.get("simplifiedGeometryGeoJSON") != source.get("url"):
            raise ValueError("original Atlas simplified product URL and retained source packet disagree: " + product)
        product_doc = json.loads(source_raw)
        features = product_doc.get("features")
        if not isinstance(features, list):
            raise ValueError("retained Atlas source product is not a complete GeoJSON FeatureCollection: " + product)
        wanted = {catalog_by_id[x]["source_evidence"]["unique_source_subject_id"].split(":")[-1]
                  for x in subjects if catalog_by_id[x]["source_evidence"]["source_products"] == product}
        selected = {}
        for ordinal, feature in enumerate(features, 1):
            shape_id = feature.get("properties", {}).get("shapeID")
            if shape_id in wanted:
                if shape_id in selected:
                    raise ValueError("retained source product has duplicate selected shapeID: " + product + "/" + shape_id)
                selected[shape_id] = {"feature": feature, "record_ordinal": ordinal,
                                      "feature_sha256": digest_json(feature),
                                      "geometry_sha256": digest_json(feature["geometry"])}
        if set(selected) != wanted:
            raise ValueError("whole Atlas source product lacks expected selected stable subject IDs: " + product)
        source_features[product] = selected
        source_registry[product] = {"packet": packet, "product_id": product, "url": source["url"],
                                    "role": source["role"], "vintage": source["vintage"],
                                    "retrieved_at": source["retrieved_at"], "license": source["license"],
                                    "retention": source["retention"], "verification": source["verification"],
                                    "temporal_status": source["temporal_status"], "limit": source["limit"],
                                    "captured_file": product_desc, "original_atlas_registry": registry_row,
                                    "original_atlas_recipe": {"commit": ADMIN_SCRIPT_COMMIT,
                                                               "path": admin_script_path,
                                                               "bytes": len(admin_script),
                                                               "sha256": sha256(admin_script)}}
        source_input_descriptors[input_path] = product_desc

    # Close exact source/current-target joins and retain the entire feature pointsets
    # plus the already-computed comparison row for each priority identity.
    cases = []
    for identity in sorted(subjects):
        catalog = catalog_by_id[identity]
        source_info = catalog["source_evidence"]
        product = source_info["source_products"]
        source_id = source_info["unique_source_subject_id"]
        shape_id = source_id.split(":")[-1]
        source_entry = source_features[product][shape_id]
        target_entry = targets[identity]
        comparison = comparisons[identity]
        cmp = comparison["record"]
        if state_by_id[identity]["membership"].get("class") != "unresolved":
            raise ValueError("priority component state changed from unresolved; reconcile accepted decision explicitly: " + identity)
        if (target_entry["feature_sha256"] != catalog["current_feature_sha256"] or
            target_entry["geometry_sha256"] != catalog["current_geometry_sha256"]):
            raise ValueError("target feature hashes do not resolve the current catalog record: " + identity)
        if (cmp.get("component_geometry_sha256") != catalog["current_geometry_sha256"] or
            cmp.get("full_component_feature_sha256") != catalog["current_feature_sha256"]):
            raise ValueError("retained source-comparison target differs from current catalog/whole target pointset: " + identity + " " + json.dumps({"cmp_geometry": cmp.get("component_geometry_sha256"), "catalog_geometry": catalog.get("current_geometry_sha256"), "cmp_component_digest": digest_json(cmp.get("component")), "cmp_feature": cmp.get("full_component_feature_sha256"), "catalog_feature": catalog.get("current_feature_sha256"), "target_geometry": target_entry.get("geometry_sha256"), "target_feature": target_entry.get("feature_sha256")}, sort_keys=True))
        if cmp.get("status") != source_info.get("source_comparison_status"):
            raise ValueError("retained source-comparison outcome differs from current catalog evidence: " + identity)
        if product not in cmp.get("source_products", []):
            raise ValueError("retained comparison row does not bind catalog source product: " + identity)
        match = [f for f in cmp.get("feature_intersections", [])
                 if f.get("binding", {}).get("source_id") == product and f.get("binding", {}).get("shapeID") == shape_id]
        if len(match) != 1:
            raise ValueError("comparison row does not uniquely bind the selected source feature: " + identity)
        binding = match[0]["binding"]
        if (binding.get("recorded_stable_subjects", [{}])[0].get("id") != source_id or
            binding.get("feature_sha256") != source_entry["feature_sha256"] or
            binding.get("geometry_sha256") != source_entry["geometry_sha256"]):
            raise ValueError("exact simplified source pointset does not match retained comparison feature binding: " + identity)
        original_subject = next((x for x in binding.get("recorded_stable_subjects", []) if x.get("id") == source_id), None)
        if not original_subject:
            raise ValueError("source comparison row omits the stable original subject binding: " + identity)
        if source_info.get("source_geometry_sha256") != original_subject.get("original_feature_sha256"):
            raise ValueError("original stable-subject geometry hash differs from retained catalog provenance: " + identity)
        family = selected_by_id[identity]
        cases.append({"component_id": identity, "family_id": family["family_id"],
                      "country_codes": family["countries"], "decision_state": state_by_id[identity]["reconciled_state"],
                      "decision": catalog.get("decision"), "class": catalog.get("class"),
                      "repair_ready": catalog.get("repair_ready"), "implemented": catalog.get("implemented"),
                      "fully_integrated": catalog.get("fully_integrated"), "delivered": catalog.get("delivered"),
                      "exact_unresolved_facts": state_by_id[identity]["exact_id_reason"],
                      "next_action": state_by_id[identity]["next_action"],
                      "catalog_record": catalog,
                      "target_record": {"kind": "retained full Atlas component feature pointset",
                                        "path": target_entry["pin"]["path"], "bytes": target_entry["pin"]["bytes"],
                                        "sha256": target_entry["pin"]["sha256"],
                                        "record_ordinal": target_entry["record_ordinal"],
                                        "feature_sha256": target_entry["feature_sha256"],
                                        "geometry_sha256": target_entry["geometry_sha256"],
                                        "feature": target_entry["feature"]},
                      "source_record": {"product_id": product, "subject_id": source_id,
                                        "record_ordinal": source_entry["record_ordinal"],
                                        "feature_sha256": source_entry["feature_sha256"],
                                        "geometry_sha256": source_entry["geometry_sha256"],
                                        "original_stable_subject_geometry_sha256": source_info["source_geometry_sha256"],
                                        "feature": source_entry["feature"]},
                      "existing_comparison": {"path": comparison["path"], "bytes": comparison["bytes"],
                                               "sha256": comparison["sha256"],
                                               "uncompressed_sha256": comparison["uncompressed_sha256"],
                                               "record_ordinal": comparison["record_ordinal"],
                                               "record": cmp},
                      "established": ["Atlas administrative recipe selects the explicitly pinned simplified geoBoundaries product.",
                                      "Whole product bytes match the historical administrative registry SHA and selected stable subject ID.",
                                      "The selected simplified source feature and exact current full target component feature are preserved and hash-joined.",
                                      "The previously retained source overlay row binds the same target and source feature pointsets."],
                      "unresolved": ["The physical class, contemporary land/water state, causal mechanism, and repair authority remain unknown.",
                                     "A source feature is an administrative reference, not proof of current physical truth or authorization."]})

    if len(cases) != 30:
        raise ValueError("deep exact source/target packet is not complete")
    root_pins = [refresh_outputs[path] for alias, path in pin_files.items() if alias.startswith(("membership_", "catalog_"))]
    root_pins += [target_outputs[path] for alias, path in pin_files.items() if alias.startswith("prior_component_")]
    extras = [helper_desc, descriptor(REFRESH_MANIFEST, git_bytes(head, REFRESH_MANIFEST)),
              descriptor(TARGET_MANIFEST, git_bytes(head, TARGET_MANIFEST)),
              registry_desc, admin_script_desc]
    extras += list(source_packet_manifest_descriptors.values())
    extras += list(source_input_descriptors.values())
    extras += list(comparison_pins.values())
    unique = {}
    for desc in root_pins + extras:
        current = dict(desc)
        if "commit" not in current:
            current["commit"] = head
        if current["path"] in unique and (unique[current["path"]]["sha256"] != current["sha256"] or
                                          unique[current["path"]].get("commit") != current.get("commit")):
            raise ValueError("same baseline path bound to different commit/hash identities")
        unique[current["path"]] = current

    # The final publication phase reauthenticates every referenced whole input and
    # emits the one complete 30-case packet. It does not rerun any overlay.
    write_baseline = Baseline(str(REPO), head, [d for d in unique.values() if d.get("commit") == head])
    vintage = NewVintage(write_baseline, OWNED, "priority-source-target-001", ["priority-source-target.json"])
    output = {"version": 1, "batch_id": batch["batch_id"], "batch_index_sha256": INDEX_SHA,
              "current_head": head, "catalog_refresh_execution_baseline": refresh["baseline"]["commit"],
              "issue_contract_body_sha256": contract_doc["body_sha256"], "component_count": 30,
              "priority_family_count": 24, "country_codes": batch["countries"],
              "source_products": [source_registry[p] for p in products],
              "source_comparison_packets": [{"packet": p, "manifest_path": packet_manifests[p]["path"],
                                               "component_output_count": len(packet_component_outputs[p])}
                                              for p in packets],
              "catalog_phase_receipts": catalog_phase_receipts,
              "processing": "Source and target pointsets are selected from complete retained products and existing result rows. No source overlays, administrative replay, core geography changes or decision approvals were generated.",
              "summary": {"priority_cases": len(cases), "distinct_source_products": len(products),
                          "distinct_source_comparison_packets": len(packets),
                          "source_current_target_bindings": len(cases),
                          "unresolved_decisions": sum(x["decision_state"] == "unresolved" for x in cases),
                          "approved_repairs": 0, "fully_integrated": 0, "delivered": 0},
              "limitations": ["Source feature hashes from the exact consumed simplified products are kept distinct from historical stable-subject geometry hashes; simplification can change coordinates.",
                              "The currently retained whole target pointsets establish record identity/location only, not accepted physical class or current authoritative territory.",
                              "Existing comparison overlays are cited and reused, not recalculated.",
                              "Water/ice status, cause, legal/administrative repair authority and permission to modify Atlas geography remain unknown."],
              "cases": cases,
              "baseline_files": sorted(unique.values(), key=lambda x: (x.get("commit", head), x["path"])),
              "issue_pin_files": pin_files}
    vintage.publish({"priority-source-target.json": output})
    print(json.dumps({"cases": len(cases), "source_products": products, "comparison_packets": packets,
                      "baseline_file_count": len(unique), "decoded_bytes_per_catalog_leaf": [x["decoded_bytes"] for x in catalog_phase_receipts],
                      "result_path": f"{OWNED}vintages/priority-source-target-001/priority-source-target.json"}, indent=2))


if __name__ == "__main__":
    main()
