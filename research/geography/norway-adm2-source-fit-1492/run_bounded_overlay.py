#!/usr/bin/env python3
"""Run exact 15-component Norway source overlay after bounded whole-phase admission."""
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/norway-adm2-source-fit-1492/"
BASELINE_COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
CAPTURE = "component-geometries-20261008"
SOURCES = "official-source-capture-20261008"
VINTAGE = "exact-overlay-acceptance-20261008"
OUTPUTS = ["overlay-v1.json"]
PHYSICAL = "coordination/engineering/global-physical-comparison-20261006/"
SOURCE = "coordination/engineering/global-source-comparisons-a-001-20261006/"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def stage_file(root, stage, leaf, base, reserve):
    stage_dir = root / OWNED / "vintages" / stage
    pub_path = stage_dir / "publication.json"
    pub_raw = pub_path.read_bytes()
    base.admit("stage:" + stage + "/publication.json", len(pub_raw))
    pub = json.loads(pub_raw)
    if pub.get("status") != "complete":
        raise SystemExit("Stage publication is incomplete or changed: " + stage)
    entry = next((x for x in pub["outputs"] if x["path"].endswith("/" + leaf)), None)
    if not entry:
        raise SystemExit("Expected staged output missing: " + leaf)
    path = root / entry["path"]
    raw = path.read_bytes()
    base.admit("stage:" + stage + "/" + leaf, len(raw))
    if len(raw) != entry["bytes"] or sha(raw) != entry["sha256"]:
        raise SystemExit("Staged output bytes disagree with publication: " + leaf)
    return raw, entry


def encode_geom(geom, mapping):
    return mapping(geom) if not geom.is_empty else {"type": "GeometryCollection", "geometries": []}


def main():
    started = time.monotonic()
    script_raw = Path(__file__).read_bytes()
    script_hash = sha(script_raw)
    admission_raw = (ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json").read_bytes()
    if sha(admission_raw) != BASELINE_SHA:
        raise SystemExit("Pinned baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage

    base = Baseline(ROOT, BASELINE_COMMIT, admission["baseline_files"])
    writer = NewVintage(base, OWNED, VINTAGE, OUTPUTS)
    output_reserve = 12 * 1024 * 1024
    base.admit("reserved-output:overlay-v1.json", output_reserve)
    base.admit("reserved-output:publication.json", 4096)

    # Admit every exact staged input before parsing any geometry or importing Shapely.
    component_raw, component_desc = stage_file(ROOT, CAPTURE, "selected-components.json", base, output_reserve)
    selected_raw, selected_desc = stage_file(ROOT, SOURCES, "selected-source-rows.json", base, output_reserve)
    adm2_raw, adm2_desc = stage_file(ROOT, SOURCES, "adm2-simplified.geojson", base, output_reserve)
    adm1_raw, adm1_desc = stage_file(ROOT, SOURCES, "adm1-simplified.geojson", base, output_reserve)
    adm2_api_raw, adm2_api_desc = stage_file(ROOT, SOURCES, "adm2-api.json", base, output_reserve)
    adm1_api_raw, adm1_api_desc = stage_file(ROOT, SOURCES, "adm1-api.json", base, output_reserve)
    family_raw, family_desc = stage_file(ROOT, "family-scope-20261008", "family-scope.json", base, output_reserve)
    correction_raw, correction_desc = stage_file(ROOT, "issue-scope-correction-20261008", "correction.json", base, output_reserve)
    prior_overlay_raw, prior_overlay_desc = stage_file(ROOT, "exact-overlay-contact-reconciled-20261008", "overlay-v1.json", base, output_reserve)
    # Retained original comparison shard identities and exact producer/method bytes.
    physical_manifest = json.loads(base.pinned_bytes(PHYSICAL + "evidence-quality.json"))
    input_cfg = next(x for x in physical_manifest["outputs"] if x.get("path") == PHYSICAL + "input-config.json")
    base.pins[input_cfg["path"]] = {k: input_cfg[k] for k in ("path", "bytes", "sha256", "hash_kind")}
    config = json.loads(base.pinned_bytes(input_cfg["path"]))
    pinned_method = {}
    for entry in physical_manifest["outputs"]:
        path = entry.get("path", "")
        if path.endswith(("/producer.py", "/comparison.py", "/inputs.py", "/immutable.py")):
            pinned_method[path] = entry
    for entry in pinned_method.values():
        if entry["path"] not in base.pins:
            base.pins[entry["path"]] = {k: entry[k] for k in ("path", "bytes", "sha256", "hash_kind")}
        base.pinned_bytes(entry["path"])

    # Exact source-comparison rows for the selected IDs are part of the baseline and cross-check.
    source_manifest = json.loads(base.pinned_bytes(SOURCE + "evidence-quality.json"))
    comparison_files = [x for x in source_manifest["outputs"] if "/scientific/components-" in x.get("path", "")]
    for entry in comparison_files:
        if entry["path"] in base.pins:
            base.pinned_bytes(entry["path"])

    # Freeze installed numerical implementation bytes without executing the geometry library.
    dist = importlib.metadata.distribution("shapely")
    if dist.version != "2.1.2":
        raise SystemExit("Unexpected Shapely runtime version")
    runtime_files = []
    for file in dist.files or []:
        full = Path(dist.locate_file(file)).resolve()
        if full.is_file():
            raw = full.read_bytes()
            base.admit("runtime:" + str(full), len(raw))
            runtime_files.append({"path": str(full), "bytes": len(raw), "sha256": sha(raw)})
    python_bin = Path(sys.executable).resolve()
    python_raw = python_bin.read_bytes()
    base.admit("runtime:" + str(python_bin), len(python_raw))
    runtime_files.append({"path": str(python_bin), "bytes": len(python_raw), "sha256": sha(python_raw)})

    # Check live local-workspace and OS admission immediately before source decode / GIS.
    free_disk = shutil.disk_usage(ROOT).free
    if free_disk < 10 * 1024**3:
        raise SystemExit("GIS admission denied: less than 10 GiB free storage")
    if base.max_phase_bytes < sum(base.consumed.values()) + output_reserve:
        raise SystemExit("GIS admission denied: complete input/output phase exceeds byte cap")

    # Re-read all exact bytes after accounting, then import the frozen geometry runtime.
    if sha(Path(__file__).read_bytes()) != script_hash:
        raise SystemExit("Overlay producer changed before run")
    for item in runtime_files:
        if sha(Path(item["path"]).read_bytes()) != item["sha256"]:
            raise SystemExit("Numerical runtime bytes drifted before import")
    import shapely
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union
    if shapely.__version__ != "2.1.2" or shapely.geos_version_string != "3.13.1":
        raise SystemExit("Loaded Shapely/GEOS versions differ from frozen runtime")
    for item in runtime_files:
        if sha(Path(item["path"]).read_bytes()) != item["sha256"]:
            raise SystemExit("Numerical runtime bytes changed on import")

    components_capture = json.loads(component_raw)
    components = components_capture["selected_components"]
    source_capture = json.loads(selected_raw)
    selected_ids = source_capture["family_context"]["selected_component_ids"]
    family = json.loads(family_raw)["scope"]
    family_ids = family["complete_component_ids"]
    neighbor_ids = family["complete_positive_length_neighbor_ids"]
    correction = json.loads(correction_raw)
    if len(components) != 15 or len(selected_ids) != 15 or len(family_ids) != 400 or len(neighbor_ids) != 36:
        raise SystemExit("Selected scope / full family / neighbor inventory changed")
    if [x["id"] for x in components] != selected_ids or not set(selected_ids) <= set(family_ids):
        raise SystemExit("Component geometry roster does not equal corrected selected route roster")

    adm2_doc, adm1_doc = json.loads(adm2_raw), json.loads(adm1_raw)
    atlas_doc = json.loads(base.pinned_bytes("data/geography/part-17.json"))
    if len(adm2_doc.get("features", [])) != 431 or len(adm1_doc.get("features", [])) != 11:
        raise SystemExit("Official simplified source feature count changed")
    adm2_features = adm2_doc["features"]
    adm1_features = adm1_doc["features"]
    by_shapeid = {f.get("properties", {}).get("shapeID"): (i, f) for i, f in enumerate(adm2_features)}
    if len(by_shapeid) != 431 or None in by_shapeid:
        raise SystemExit("ADM2 feature stable identifiers are incomplete or duplicate")
    adm2_geoms = [shape(f["geometry"]) for f in adm2_features]
    adm1_geoms = [shape(f["geometry"]) for f in adm1_features]
    if any(not g.is_valid for g in adm2_geoms + adm1_geoms):
        raise SystemExit("Invalid official source geometry; no repair is permitted")
    nordland_candidates = [(i, f, adm1_geoms[i]) for i, f in enumerate(adm1_features)
                           if f.get("properties", {}).get("shapeName", "").casefold() == "nordland"]
    if len(nordland_candidates) != 1:
        raise SystemExit("ADM1 source product does not identify one Nordland feature")
    nordland_index, nordland_feature, nordland_geom = nordland_candidates[0]
    nordland_shapeid = nordland_feature["properties"]["shapeID"]
    atlas_by_id = {f.get("properties", {}).get("id"): f for f in atlas_doc.get("features", [])}

    row_records = {x["record"]["component"]: x["record"] for x in source_capture["source_component_rows"]}
    feature_bindings = source_capture["source_feature_bindings"]
    targets = []
    for comp in components:
        identity = comp["id"]
        record = row_records.get(identity)
        if not record:
            raise SystemExit("Selected baseline source comparison row missing")
        geometry_raw = canonical(comp["geometry"])
        if sha(geometry_raw) != record["component_geometry_sha256"]:
            raise SystemExit("Original component delivery geometry does not match source comparison geometry hash")
        subject = record["uniquely_covering_compatible_recorded_subject"]
        if not subject or subject["reference_year"] != "2013" or subject["id"].split(":")[-1] not in by_shapeid:
            raise SystemExit("Recorded unique-compatible ADM2 source binding is missing or wrong edition")
        child_shapeid = subject["id"].split(":")[-1]
        child_index, child_feature = by_shapeid[child_shapeid]
        binding = feature_bindings.get(child_shapeid)
        if not binding or binding["feature_index"] != child_index:
            raise SystemExit("Selected subject feature index differs from pinned full simplified product")
        atlas_target = atlas_by_id.get(subject["id"])
        if atlas_target is None:
            raise SystemExit("Exact current Atlas target member is absent from pinned part-17")
        atlas_props = atlas_target.get("properties", {})
        if (atlas_props.get("parent_id") != "framework:province:nordland:03c9b4c95d9e"
                or atlas_props.get("metadata", {}).get("reference_year") != "2013"):
            raise SystemExit("Current Atlas target metadata does not match recorded source/parent lineage")
        # The retained ADM2 product carries no parent property. Bind the recorded
        # Atlas parent lineage to the unique 2022 ADM1 feature whose official
        # shapeName is Nordland, and keep that name-based linkage explicit.
        parent_shapeid, parent_index, parent_geom = nordland_shapeid, nordland_index, nordland_geom
        if subject.get("original_parent_id") != "framework:province:nordland:03c9b4c95d9e":
            raise SystemExit("Recorded source lineage parent differs from pinned issue binding")
        targets.append((comp, record, shape(comp["geometry"]), child_shapeid, child_index,
                        shape(child_feature["geometry"]), parent_shapeid, parent_index, parent_geom,
                        subject["id"], shape(atlas_target["geometry"]), sha(canonical(atlas_target["geometry"]))))
    if len({x[6] for x in targets}) != 1:
        raise SystemExit("Selected recorded source subjects do not resolve to one ADM1 parent")

    def run_once():
        result_rows = []
        all_contacts = []
        control_evidence = []
        for comp, record, candidate, child_id, child_ix, child_geom, parent_id, parent_ix, parent_geom, target_id, current_target, target_geom_sha in targets:
            if not candidate.is_valid or candidate.is_empty or not current_target.is_valid or current_target.is_empty:
                raise SystemExit("Invalid or empty selected component geometry")
            intersections = []
            positive_ids = []
            for ix, feature in enumerate(adm2_features):
                other = adm2_geoms[ix]
                if not candidate.intersects(other):
                    continue
                piece = candidate.intersection(other)
                f_id = feature["properties"]["shapeID"]
                positive_area = piece.area > 0
                if positive_area:
                    positive_ids.append(f_id)
                row = {"feature_index": ix, "shapeID": f_id,
                       "recorded_stable_subject_ids": ["gb:NOR:ADM2:" + f_id],
                       "is_empty": piece.is_empty, "geometry_type": piece.geom_type,
                       "planar_area_coordinate_units_squared": piece.area,
                       "geometry": encode_geom(piece, mapping)}
                intersections.append(row)
                all_contacts.append({"component_id": comp["id"], **row})
            if positive_ids != [child_id]:
                raise SystemExit("Selected component has positive-area contacts outside its unique source subject")
            expected_contact_ids = sorted({
                *[x["binding"]["shapeID"] for x in record["feature_intersections"]
                  if not x["intersection"]["is_empty"]],
                *[x["shapeID"] if isinstance(x, dict) else str(x).split(":")[-1]
                  for x in record["zero_area_feature_ids"]]
            })
            actual_contact_ids = sorted(r["shapeID"] for r in intersections)
            source_covered = candidate.difference(child_geom).is_empty
            parent_covered = candidate.difference(parent_geom).is_empty
            source_union = unary_union(adm2_geoms)
            source_union_covered = candidate.difference(source_union).is_empty
            source_union_intersection = candidate.intersection(source_union)
            candidate_target_intersection = candidate.intersection(current_target)
            candidate_target_addition = candidate.difference(current_target)
            no_loss_residual = current_target.difference(current_target.union(candidate))
            no_loss = no_loss_residual.is_empty
            current_relation = record["current_component_relation"]
            result_rows.append({
                "component_id": comp["id"], "recorded_current_component_relation": current_relation,
                "component_geometry_sha256": record["component_geometry_sha256"],
                "unique_compatible_recorded_subject": subject_id(record),
                "current_atlas_target_id": target_id, "current_atlas_target_geometry_sha256": target_geom_sha,
                "candidate_intersects_current_atlas_target": not candidate_target_intersection.is_empty,
                "candidate_adds_area_beyond_current_atlas_target": not candidate_target_addition.is_empty,
                "candidate_target_intersection": encode_geom(candidate_target_intersection, mapping),
                "candidate_minus_current_target": encode_geom(candidate_target_addition, mapping),
                "source_product_feature_index": child_ix, "source_product_feature_shapeID": child_id,
                "recorded_source_comparison_intersections": record["feature_intersections"],
                "recorded_source_comparison_zero_area_feature_ids": record["zero_area_feature_ids"],
                "recorded_source_comparison_contact_ids": expected_contact_ids,
                "recomputed_source_contact_ids": actual_contact_ids,
                "historical_contact_ids_missing_from_current_simplified_product": sorted(set(expected_contact_ids) - set(actual_contact_ids)),
                "current_simplified_contacts_absent_from_historical_comparison": sorted(set(actual_contact_ids) - set(expected_contact_ids)),
                "source_year": "2013", "exact_subject_covers_component": source_covered,
                "exact_subject_coverage_residual": encode_geom(candidate.difference(child_geom), mapping),
                "parent_framework_id": "framework:province:nordland:03c9b4c95d9e",
                "parent_product_feature_index": parent_ix, "parent_product_feature_shapeID": parent_id,
                "parent_product_match_basis": "unique ADM1 shapeName=Nordland; ADM2 product has no parent property",
                "exact_recorded_parent_covers_component": parent_covered,
                "exact_parent_coverage_residual": encode_geom(candidate.difference(parent_geom), mapping),
                "exact_complete_source_union_covers_component": source_union_covered,
                "exact_source_union_residual": encode_geom(candidate.difference(source_union), mapping),
                "exact_source_union_intersection": encode_geom(source_union_intersection, mapping),
                "strict_no_loss_under_T_union_C": no_loss,
                "strict_no_loss_residual": encode_geom(no_loss_residual, mapping),
                "source_intersections": intersections,
                "positive_area_source_feature_ids": positive_ids,
                "zero_area_contacts": [r for r in intersections if r["planar_area_coordinate_units_squared"] == 0]
            })
            # Fail-closed adverse controls: identity, edition, parent, scope/contact, bytes, loss, overlap.
            def accepted(state):
                return bool(
                    state["component_id"] in selected_ids
                    and state["target_id"] == state["expected_target_id"]
                    and state["source_id"] == "gb:NOR:ADM2:" + child_id
                    and state["edition"] == "2013"
                    and state["parent_id"] == parent_id
                    and state["parent_covered"]
                    and state["family_ids"] == set(family_ids)
                    and state["neighbor_ids"] == set(neighbor_ids)
                    and state["actual_contact_ids"] == state["expected_contact_ids"]
                    and state["source_bytes_sha256"] == adm2_desc["sha256"]
                    and state["source_covered"]
                    and state["candidate_adds_area"]
                    and state["no_loss"]
                    and state["positive_ids"] == [child_id]
                )
            gate_state = {"component_id": comp["id"], "target_id": target_id, "expected_target_id": target_id,
                          "source_id": "gb:NOR:ADM2:" + child_id, "edition": "2013",
                          "parent_id": parent_id, "parent_covered": parent_covered,
                          "family_ids": set(family_ids), "neighbor_ids": set(neighbor_ids),
                          "actual_contact_ids": actual_contact_ids, "expected_contact_ids": expected_contact_ids,
                          "source_bytes_sha256": sha(adm2_raw), "source_covered": source_covered,
                          "candidate_adds_area": not candidate_target_addition.is_empty,
                          "no_loss": no_loss, "positive_ids": positive_ids}
            actual_gate_passes = accepted(gate_state)
            # Each adverse control starts from a complete synthetic affirmative control state,
            # so unrelated measured failures cannot make a negative control pass trivially.
            control_anchor = dict(gate_state)
            control_anchor.update({"parent_covered": True, "family_ids": set(family_ids),
                                   "neighbor_ids": set(neighbor_ids),
                                   "actual_contact_ids": expected_contact_ids,
                                   "source_bytes_sha256": adm2_desc["sha256"],
                                   "source_covered": True, "candidate_adds_area": True, "no_loss": True,
                                   "positive_ids": [child_id]})
            if not accepted(control_anchor):
                raise SystemExit("Positive-control acceptance gate does not accept complete valid control state")
            negative_checks = {}
            for label, field, bad in [
                ("wrong_source_id", "source_id", "gb:NOR:ADM2:WRONG"),
                ("wrong_source_edition", "edition", "2012"),
                ("wrong_target_id", "target_id", "gb:NOR:ADM2:WRONG"),
                ("wrong_parent", "parent_id", "WRONG"),
                ("missing_family_member", "family_ids", set(family_ids) - {next(iter(family_ids))}),
                ("missing_neighbor", "neighbor_ids", set(neighbor_ids) - {next(iter(neighbor_ids))}),
                ("missing_contact", "actual_contact_ids", actual_contact_ids[:-1]),
                ("altered_source_bytes", "source_bytes_sha256", sha(adm2_raw + b"\\0")),
                ("forced_target_loss", "no_loss", False),
                ("forced_new_positive_overlap", "positive_ids", [child_id, "FORCED-OVERLAP"])
            ]:
                mutated = dict(control_anchor)
                mutated[field] = bad
                negative_checks[label + "_rejected"] = not accepted(mutated)
            control_evidence.append({"component_id": comp["id"],
                                     "measured_acceptance_gate_passes": actual_gate_passes,
                                     "positive_control_acceptance": accepted(control_anchor),
                                     "measured_parent_covered": parent_covered,
                                     "measured_strict_no_loss": no_loss,
                                     "measured_source_covered": source_covered,
                                     **negative_checks,
                                     "all_adverse_controls_rejected": all(negative_checks.values()),
                                     "recorded_vs_recomputed_contact_ids_equal": actual_contact_ids == expected_contact_ids})
        return {"components": result_rows, "contacts": all_contacts, "adverse_controls": control_evidence}

    def subject_id(record):
        return record["uniquely_covering_compatible_recorded_subject"]["id"]

    first = run_once()
    second = run_once()
    first_hash, second_hash = sha(canonical(first)), sha(canonical(second))
    if first_hash != second_hash or first != second:
        raise SystemExit("Two exact runs differ")
    controls = first["adverse_controls"]
    if len(controls) != 15 or any(not row["all_adverse_controls_rejected"] for row in controls):
        raise SystemExit("A required fail-closed adverse control did not trigger")
    for row in first["components"]:
        if not row["exact_subject_covers_component"] or not row["exact_complete_source_union_covers_component"]:
            row["source_fit_status"] = "not-qualified"
        else:
            row["source_fit_status"] = "recorded-source-covered"
        row["parent_status"] = "covered" if row["exact_recorded_parent_covers_component"] else "not-covered"
        row["no_loss_status"] = "strict-pass" if row["strict_no_loss_under_T_union_C"] else "strict-fail"
    historical_bbox_rows = [item for record in row_records.values()
                            for item in record["feature_intersections"]]
    historical_empty_bbox_rows = sum(item["intersection"]["is_empty"] for item in historical_bbox_rows)
    historical_nonempty_contacts = sum(not item["intersection"]["is_empty"] for item in historical_bbox_rows)
    historical_zero_area_contacts = sum(len(record["zero_area_feature_ids"]) for record in row_records.values())
    result = {
        "version": 1, "status": "bounded-exact-source-overlay-complete", "issue": 1492,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": script_hash},
        "supersedes": {"prior_overlay_sha256": prior_overlay_desc["sha256"],
                       "reason": "This capture adds the issue's current-target area-addition predicate to the measured fail-closed acceptance gate. Historical bbox candidates are reconciled only after excluding empty intersections; each adverse mutation is independently tested from a positive passing control state."},
        "scope": {"selected_component_count": 15, "complete_family_member_count": len(family_ids),
                  "complete_positive_length_neighbor_count": len(neighbor_ids),
                  "selected_ids": selected_ids, "complete_family_member_ids": family_ids,
                  "complete_positive_length_neighbor_ids": neighbor_ids,
                  "family_sha256": family_desc["sha256"],
                  "issue_scope_correction_sha256": correction_desc["sha256"],
                  "issue_correction_receipt": correction},
        "sources": {"adm2": {"api_sha256": sha(adm2_api_raw), "api_bytes": len(adm2_api_raw),
                     "api_url": "https://www.geoboundaries.org/api/current/gbOpen/NOR/ADM2/",
                     "product_url": json.loads(adm2_api_raw)["simplifiedGeometryGeoJSON"],
                     "product_bytes": len(adm2_raw), "product_sha256": sha(adm2_raw),
                     "feature_count": len(adm2_features), "represented_year": json.loads(adm2_api_raw)["boundaryYearRepresented"],
                     "license": json.loads(adm2_api_raw)["boundaryLicense"]},
                    "adm1": {"api_sha256": sha(adm1_api_raw), "api_bytes": len(adm1_api_raw),
                     "api_url": "https://www.geoboundaries.org/api/current/gbOpen/NOR/ADM1/",
                     "product_url": json.loads(adm1_api_raw)["simplifiedGeometryGeoJSON"],
                     "product_bytes": len(adm1_raw), "product_sha256": sha(adm1_raw),
                     "feature_count": len(adm1_features), "represented_year": json.loads(adm1_api_raw)["boundaryYearRepresented"],
                     "license": json.loads(adm1_api_raw)["boundaryLicense"]}},
        "input_component_delivery": {"source_capture_sha256": component_desc["sha256"],
                                     "declared_count": components_capture["component_delivery_inventory"]["declared_current_components"],
                                     "actual_unique_count": components_capture["component_delivery_inventory"]["unique_component_ids"],
                                     "mismatch": components_capture["component_delivery_inventory"]["declared_vs_captured_unique_difference"]},
        "runtime": {"python": sys.version, "platform": platform.platform(), "executable_sha256": sha(python_raw),
                    "shapely_version": shapely.__version__, "geos_version": shapely.geos_version_string,
                    "distribution_files": runtime_files},
        "runs": {"first_canonical_sha256": first_hash, "second_canonical_sha256": second_hash,
                 "deterministic_equal": True, "run_count": 2},
        "contact_reconciliation": {"historical_bbox_candidate_rows": len(historical_bbox_rows),
                                   "historical_empty_bbox_rows_not_contacts": historical_empty_bbox_rows,
                                   "historical_nonempty_contact_rows": historical_nonempty_contacts,
                                   "historical_zero_area_contacts": historical_zero_area_contacts,
                                   "recomputed_current_contacts": len(first["contacts"]),
                                   "components_with_exact_contact_set_equality": sum(x["recorded_vs_recomputed_contact_ids_equal"] for x in first["adverse_controls"]),
                                   "source_product_hash_equal_to_historical_consumed_product": sha(adm2_raw) == "ab294b0b1dadfb937daa07963aa5995544fd8a16a6c9eb6261a82bb66401d90e",
                                   "basis": "Historical feature_intersections include all bbox candidates, including empty intersections. Contacts are only nonempty intersections plus explicit zero_area_feature_ids."},
        "components": first["components"], "all_nonempty_intersections_and_contacts": first["contacts"],
        "adverse_controls": first["adverse_controls"],
        "admission": {"baseline_commit": BASELINE_COMMIT, "baseline_sha256": BASELINE_SHA,
                      "phase_input_bytes_including_outputs_reserve": sum(base.consumed.values()),
                      "phase_cap_bytes": base.max_phase_bytes, "output_reserve_bytes": output_reserve,
                      "disk_free_bytes_at_run": free_disk,
                      "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
                      "process_max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "elapsed_seconds": time.monotonic() - started},
        "interpretation": {"authority": "unknown", "physical_classification": "unknown", "cause": "unknown",
                           "water_ice_status": "unknown", "history": "unknown", "rights": "unknown", "ownership": "unknown",
                           "no_blanket_acceptance": True},
        "limits": ["Strict lon/lat planar topology predicates describe source-relative geometry only; they do not establish physical land/water, historical truth, accuracy, authority, ownership, rights, or cause.",
                   "The issue's strict T.difference(T.union(C)) predicate uses C as the source-union intersection; this is a floating-topology diagnostic and not an independent measure of source coverage.",
                   "A whole-delivery mismatch remains: 95,174 unique source IDs were found although input-config declares 95,173; all selected 15 IDs matched exactly once.",
                   "The source capture is the official retained simplified geoBoundaries product. No unpinned or full-resolution product was substituted."]
    }
    output_raw = canonical(result)
    if len(output_raw) > output_reserve:
        raise SystemExit("Complete overlay output exceeds pre-admitted reserve")
    if sha(Path(__file__).read_bytes()) != script_hash:
        raise SystemExit("Overlay producer code changed during run")
    for item in runtime_files:
        if sha(Path(item["path"]).read_bytes()) != item["sha256"]:
            raise SystemExit("Numerical runtime changed during run")
    published = writer.publish({"overlay-v1.json": result})
    print(json.dumps({"status": result["status"], "components": len(result["components"]),
                      "contacts": len(result["all_nonempty_intersections_and_contacts"]),
                      "parent_passes": sum(x["exact_recorded_parent_covers_component"] for x in result["components"]),
                      "strict_no_loss_passes": sum(x["strict_no_loss_under_T_union_C"] for x in result["components"]),
                      "phase_bytes": result["admission"]["phase_input_bytes_including_outputs_reserve"],
                      "max_rss": result["admission"]["process_max_rss_bytes"], "outputs": published}, indent=2))


if __name__ == "__main__":
    main()
