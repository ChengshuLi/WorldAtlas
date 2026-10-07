#!/usr/bin/env python3
"""Execute issue #1385 in complete raw/decoded/code bounded semantic phases."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import pathlib
import platform
import re
import subprocess
import sys

import pyproj
import shapely
from shapely import STRtree, union_all
from shapely.geometry import box, mapping, shape

from evidence_core import BASE, HERE, OWNED, Phase, canonical, deterministic_gzip, sha, source_lock, verify_code, verify_source_contract, secure_publish, finalize_phase_output

COMPONENT_ROOT = "coordination/engineering/physical-gap-components-1005-20261005-local19/"
COMPONENT_INDEX = COMPONENT_ROOT + "custody-v1/index.json"
CONTACT_PATH = COMPONENT_ROOT + "custody-v1/payloads/4a150385c4b026e55cd2faf756f8a3fc43eddac2d8a58c118c9fbcf8419777df.bin"
FRAGMENT_ROOT = "coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/"
WATER_PATH = "coordination/engineering/coverage-gaps-907-20261005-local01/sources/natural-earth-lakes.geojson.gz"
SOURCE_PATHS = {
    "ZMB": "data/regional-review/regional-review-9203cb61c3883e07/source/geoboundaries/geoBoundaries-ZMB-ADM2_simplified.geojson",
    "ZWE": "data/regional-review/regional-review-9203cb61c3883e07/source/geoboundaries/geoBoundaries-ZWE-ADM2_simplified.geojson",
}
ATLAS_PATH = "data/geography/part-28.json"
HIERARCHY_PATH = "data/hierarchy.json"
REGISTRY_PATH = "data/administrative-sources.json"
EXPECTED_SUBJECTS = {
    "gb:ZMB:ADM2:96606910B35256638811207": {"country": "ZMB", "shapeID": "96606910B35256638811207", "name": "Chirundu", "parent_id": "framework:province:lusaka:0a81a8111ef8"},
    "gb:ZMB:ADM2:96606910B48730551364911": {"country": "ZMB", "shapeID": "96606910B48730551364911", "name": "Luangwa", "parent_id": "framework:province:lusaka:0a81a8111ef8"},
    "gb:ZMB:ADM2:96606910B70191271227661": {"country": "ZMB", "shapeID": "96606910B70191271227661", "name": "Kafue", "parent_id": "framework:province:lusaka:0a81a8111ef8"},
    "gb:ZWE:ADM2:62879985B85730198836463": {"country": "ZWE", "shapeID": "62879985B85730198836463", "name": "Hurungwe", "parent_id": "framework:province:mashonaland-west:8faaeddc2c75"},
}


def pinmap():
    lock = source_lock()
    return {p["path"]: p for p in lock["pins"] if p["commit"] == BASE}


def ids():
    lock = source_lock()
    return lock["component_ids"], lock["subject_ids"]


def geom_record(geometry, area_fn):
    polygon_parts = []
    def collect(g):
        if g.geom_type == "Polygon":
            polygon_parts.append(g)
        elif g.geom_type in ("MultiPolygon", "GeometryCollection"):
            for part in g.geoms:
                collect(part)
    collect(geometry)
    area = None
    limit = None
    if polygon_parts:
        try:
            area = area_fn(union_all(polygon_parts))
        except ValueError as error:
            limit = str(error)
    return {"geometry": mapping(geometry), "geometry_sha256": sha(canonical(mapping(geometry))),
            "geometry_type": geometry.geom_type, "empty": geometry.is_empty, "valid": geometry.is_valid,
            "planar_area_degrees_squared": geometry.area, "wgs84_area_m2": area,
            "area_method_limit": limit, "planar_length_degrees": geometry.length}


def verify_inventory():
    code = verify_code()
    phase = Phase("source-pin-inventory", [], pin_map=pinmap())
    inventory = verify_source_contract(phase)
    inventory["phase_bytes"] = sum(phase.baseline.consumed.values())
    inventory["phase_consumed"] = list(phase.records)
    return code, inventory


def custody_phase(component_ids, pin_map):
    # The index identifies exactly eleven component-v3 payloads. Together with
    # the separately pinned contact payload, this is the complete 12-payload
    # custody family; discovery never widens the issue's ten-member roster.
    phase = Phase("custody", [COMPONENT_INDEX, CONTACT_PATH], pin_map=pin_map)
    index_raw = phase.raw(COMPONENT_INDEX)
    index = json.loads(index_raw)
    aliases = index.get("aliases")
    if not isinstance(aliases, list):
        raise ValueError("Malformed immutable custody index")
    component_aliases = [a for a in aliases if "/components-v3/components-" in a.get("original", {}).get("path", "")]
    if len(component_aliases) != 11 or len({a["payload"] for a in component_aliases}) != 11:
        raise ValueError("Expected the complete unique eleven-payload component-v3 family")
    components = {}
    fragment_ids = set()
    component_input_receipts = []
    for alias in sorted(component_aliases, key=lambda x: x["original"]["path"]):
        path = alias["payload"]
        phase.baseline.pins[path] = phase.baseline.pins.get(path) or __import__("evidence_core").pin_at(__import__("evidence_core").ROOT, BASE, path, (pin_map.get(path) or {}).get("sha256"), (pin_map.get(path) or {}).get("bytes"))
        raw = phase.raw(path)
        if sha(raw) != alias["original"].get("sha256"):
            raise ValueError("Component payload does not match its authenticated alias")
        decoded = phase.decoded(path, raw)
        rows = json.loads(decoded).get("features")
        if not isinstance(rows, list):
            raise ValueError("Malformed component payload")
        component_input_receipts.append({"source_path": alias["original"]["path"], "payload_path": path,
                                         "raw_sha256": sha(raw), "decoded_sha256": sha(decoded),
                                         "raw_bytes": len(raw), "decoded_bytes": len(decoded)})
        for feature in rows:
            identity = feature.get("id")
            if identity in component_ids:
                if identity in components:
                    raise ValueError("Duplicate immutable component identity: " + str(identity))
                components[identity] = feature
                bindings = feature.get("properties", {}).get("fragment_bindings", [])
                if not isinstance(bindings, list) or any(not isinstance(b.get("id"), str) for b in bindings):
                    raise ValueError("Malformed fragment membership bindings")
                fragment_ids.update(b["id"] for b in bindings)
    if set(components) != set(component_ids):
        raise ValueError("Exact ten-component identity roster is incomplete")
    contact_raw = phase.raw(CONTACT_PATH)
    contact_decoded = phase.decoded(CONTACT_PATH, contact_raw)
    contacts = json.loads(contact_decoded)
    targets = [row for row in contacts if set(row.get("components", [])) & set(component_ids)]
    if (len(targets) != 1 or not (set(targets[0].get("components", [])) & set(component_ids))
            or targets[0].get("kind") != "point-only-ambiguous"
            or targets[0].get("geometry", {}).get("type") != "Point"):
        raise ValueError("Original full ten-member contact contract is not unique and point-only")
    if len(targets[0].get("fragments", [])) != len(set(targets[0]["fragments"])):
        raise ValueError("Duplicate fragment membership in immutable source contact")
    contact_fragment_ids = set(targets[0]["fragments"])
    all_fragment_ids = fragment_ids | contact_fragment_ids
    if len(all_fragment_ids) != 11 or not fragment_ids or not contact_fragment_ids:
        raise ValueError("Exact eleven original component/contact fragment IDs are required")
    stage = {"version": 1, "phase": "custody", "baseline_commit": BASE,
             "component_ids": component_ids, "component_features": components,
             "component_fragment_ids": sorted(fragment_ids), "contact_fragment_ids": sorted(contact_fragment_ids),
             "fragment_ids": sorted(all_fragment_ids), "original_contact_rows": targets,
             "component_payloads": component_input_receipts,
             "contact_input": {"path": CONTACT_PATH, "raw_bytes": len(contact_raw), "raw_sha256": sha(contact_raw),
                               "decoded_bytes": len(contact_decoded), "decoded_sha256": sha(contact_decoded)},
             "phase_inputs": phase.records, "phase_consumed_bytes": sum(phase.baseline.consumed.values())}
    stage["phase_inputs"] = phase.records
    _, stage = finalize_phase_output(phase, stage, "custody-stage.json.gz")
    return stage


def fragment_phase(custody, pin_map):
    paths = [FRAGMENT_ROOT + f"candidates-{i:03d}.geojson.gz" for i in range(17)]
    stage_raw = canonical(custody)
    phase = Phase("fragments", paths, extra=[("custody-stage.json", stage_raw)], pin_map=pin_map)
    target_ids = set(custody["fragment_ids"])
    fragments = {}
    receipts = []
    candidate_feature_count = 0
    for path in paths:
        raw = phase.raw(path)
        decoded = phase.decoded(path, raw)
        rows = json.loads(decoded).get("features")
        if not isinstance(rows, list):
            raise ValueError("Malformed complete candidate shard: " + path)
        candidate_feature_count += len(rows)
        matches = 0
        for feature in rows:
            identity = feature.get("id")
            if identity in target_ids:
                if identity in fragments:
                    raise ValueError("Duplicate original fragment membership across candidate shards")
                fragments[identity] = feature
                matches += 1
        receipts.append({"path": path, "bytes": len(raw), "sha256": sha(raw),
                         "uncompressed_bytes": len(decoded), "uncompressed_sha256": sha(decoded),
                         "feature_count": len(rows),
                         "matching_fragment_count": matches})
    if set(fragments) != target_ids or len(fragments) != 11 or candidate_feature_count != 96963:
        raise ValueError("Complete original candidate shard family did not yield exact fragment roster")
    result = {"version": 1, "phase": "fragments", "baseline_commit": BASE,
              "expected_fragment_ids": sorted(target_ids), "features": fragments, "shards": receipts,
              "candidate_feature_count": candidate_feature_count,
              "custody_stage_sha256": sha(stage_raw), "phase_inputs": phase.records,
              "phase_consumed_bytes": sum(phase.baseline.consumed.values())}
    result["custody_stage_sha256"] = sha(stage_raw)
    result["phase_inputs"] = phase.records
    _, result = finalize_phase_output(phase, result, "fragment-stage.json.gz")
    return result


def source_geometry_phase(custody, fragment_stage, subject_ids, pin_map, source_contract, executed_code):
    paths = [*SOURCE_PATHS.values(), ATLAS_PATH, HIERARCHY_PATH, REGISTRY_PATH, WATER_PATH]
    custody_raw, fragment_raw = canonical(custody), canonical(fragment_stage)
    phase = Phase("source-and-geometry", paths,
                  extra=[("custody-stage.json", custody_raw), ("fragment-stage.json", fragment_raw),
                         ("source-contract.json", canonical(source_contract)), ("executed-code.json", canonical(executed_code))], pin_map=pin_map)
    modules = phase.modules
    geometry_module = modules["evidence.geometry"]
    area_fn = geometry_module.land_area_m2
    if (platform.python_version(), shapely.__version__, shapely.geos_version_string, pyproj.__version__) != ("3.12.14", "2.1.2", "3.13.1", "3.7.2"):
        raise ValueError("Unreviewed geometry runtime; stop before output")

    component_ids = custody["component_ids"]
    component_features = custody["component_features"]
    products = {}
    for code, path in SOURCE_PATHS.items():
        raw = phase.raw(path)
        data = json.loads(raw)
        if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
            raise ValueError("Malformed registered administrative source: " + code)
        rows = []
        identities = set()
        for index, feature in enumerate(data["features"]):
            props = feature.get("properties", {})
            shape_id = props.get("shapeID")
            if not isinstance(shape_id, str) or shape_id in identities or props.get("shapeGroup") != code or props.get("shapeType") != "ADM2":
                raise ValueError("Duplicate or wrong-country/level source feature identity")
            identities.add(shape_id)
            rows.append({"index": index, "shapeID": shape_id, "name": props.get("shapeName"),
                         "geometry": shape(feature["geometry"]), "feature_sha256": sha(canonical(feature))})
        expected = {"ZMB": (3574952, "58e9df3f95bb4c7539e5fb48839b246b2bfb12694cf5db3ed595240156016c60", 116),
                    "ZWE": (1042500, "3486ef2803574e63db97e2a35b6688bb327cb8d6ff5e439691c1cc3068ddb424", 91)}[code]
        if (len(raw), sha(raw), len(rows)) != expected:
            raise ValueError("Exact whole-source vintage/feature roster changed for " + code)
        products[code] = {"path": path, "raw": raw, "features": rows}

    atlas_raw = phase.raw(ATLAS_PATH)
    atlas_features = json.loads(atlas_raw).get("features")
    if not isinstance(atlas_features, list):
        raise ValueError("Malformed native part-28 source")
    atlas_subjects, atlas_by_country = {}, {code: [] for code in SOURCE_PATHS}
    seen_atlas = set()
    for feature in atlas_features:
        identity = feature.get("id")
        if identity in seen_atlas:
            raise ValueError("Duplicate native part-28 feature identity")
        seen_atlas.add(identity)
        if identity in subject_ids:
            atlas_subjects[identity] = feature
        if isinstance(identity, str) and identity.startswith("gb:ZMB:ADM2:"):
            atlas_by_country["ZMB"].append({"id": identity, "geometry": shape(feature["geometry"]), "sha256": sha(canonical(feature))})
        elif isinstance(identity, str) and identity.startswith("gb:ZWE:ADM2:"):
            atlas_by_country["ZWE"].append({"id": identity, "geometry": shape(feature["geometry"]), "sha256": sha(canonical(feature))})
    if set(atlas_subjects) != set(subject_ids):
        raise ValueError("Exact four unique native Atlas subjects absent")

    hierarchy_raw = phase.raw(HIERARCHY_PATH)
    hierarchy = json.loads(hierarchy_raw)
    hierarchy_rows = {row.get("id"): row for row in hierarchy if isinstance(row, dict)}
    registry_raw = phase.raw(REGISTRY_PATH)
    registry = json.loads(registry_raw)
    for subject_id in subject_ids:
        expected = EXPECTED_SUBJECTS.get(subject_id)
        if not expected or subject_id not in atlas_subjects:
            raise ValueError("Unrecognized exact native subject identity")
        code, shape_id = expected["country"], expected["shapeID"]
        matches = [r for r in products[code]["features"] if r["shapeID"] == shape_id]
        if len(matches) != 1 or matches[0]["name"] != expected["name"]:
            raise ValueError("Native source identity is absent or nonunique: " + subject_id)
        atlas = atlas_subjects[subject_id]
        properties = atlas.get("properties", {})
        if properties.get("id") != subject_id or properties.get("parent_id") != expected["parent_id"]:
            raise ValueError("Native source subject has false Atlas identity or parent: " + subject_id)
        if expected["parent_id"] not in hierarchy_rows or hierarchy_rows[expected["parent_id"]].get("level") != "province":
            raise ValueError("Pinned hierarchy does not contain the independently checked province parent")
        source_registry = registry.get("gb:" + code + ":ADM2")
        if not source_registry or source_registry.get("sha256") != sha(products[code]["raw"]):
            raise ValueError("Pinned administrative source registry and full source bytes disagree")

    component_bounds = [shape(component_features[i]["geometry"]).bounds for i in component_ids]
    local = box(min(b[0] for b in component_bounds) - .05, min(b[1] for b in component_bounds) - .05,
                max(b[2] for b in component_bounds) + .05, max(b[3] for b in component_bounds) + .05)
    atlas_unions, union_receipts = {}, {}
    for code, product in products.items():
        source_geometries = [r["geometry"] for r in product["features"]]
        atlas_geometries = [r["geometry"] for r in atlas_by_country[code]]
        source_tree, atlas_tree = STRtree(source_geometries), STRtree(atlas_geometries)
        si = sorted(int(i) for i in source_tree.query(local))
        ai = sorted(int(i) for i in atlas_tree.query(local))
        source_union = union_all([source_geometries[i] for i in si]).intersection(local)
        atlas_union = union_all([atlas_geometries[i] for i in ai]).intersection(local)
        atlas_unions[code] = atlas_union
        union_receipts[code] = {"source_path": product["path"], "source_sha256": sha(product["raw"]),
            "source_feature_count": len(source_geometries), "atlas_feature_count": len(atlas_geometries),
            "source_candidate_indices": si, "source_candidate_shapeIDs": [product["features"][i]["shapeID"] for i in si],
            "atlas_candidate_ids": [atlas_by_country[code][i]["id"] for i in ai],
            "source_local_union": geom_record(source_union, area_fn), "atlas_local_union": geom_record(atlas_union, area_fn),
            "source_minus_atlas": geom_record(source_union.difference(atlas_union), area_fn),
            "atlas_minus_source": geom_record(atlas_union.difference(source_union), area_fn), "extent": list(local.bounds)}

    component_rows, positive_witnesses, negative_witnesses = [], [], []
    for component_id in component_ids:
        feature = component_features[component_id]
        geometry = shape(feature["geometry"])
        candidates, contributing = [], []
        for code in ("ZMB", "ZWE"):
            source_rows = products[code]["features"]
            geoms = [r["geometry"] for r in source_rows]
            tree = STRtree(geoms)
            for idx in sorted(int(i) for i in tree.query(geometry)):
                row = source_rows[idx]
                intersection = geometry.intersection(row["geometry"])
                candidates.append({"country": code, "source_feature_index": idx, "shapeID": row["shapeID"],
                    "name": row["name"], "source_feature_sha256": row["feature_sha256"],
                    "covers_entire_component": row["geometry"].covers(geometry),
                    "intersection": geom_record(intersection, area_fn), "positive_area": intersection.area > 0})
                contributing.append(row["geometry"])
                if intersection.area > 0 and not positive_witnesses:
                    positive_witnesses.append({"component_id": component_id, "country": code, "source_feature_index": idx,
                                               "shapeID": row["shapeID"], "intersection": geom_record(intersection, area_fn)})
        source_union = union_all(contributing)
        intersection = geometry.intersection(source_union)
        residual = geometry.difference(source_union)
        current_union = union_all([atlas_unions["ZMB"], atlas_unions["ZWE"]])
        source_only = intersection.difference(current_union)
        if intersection.is_empty or residual.is_empty:
            raise ValueError("Expected actual overlap and source residual controls for each component")
        component_rows.append({"component_id": component_id, "component_feature_sha256": sha(canonical(feature)),
            "original_component_feature": feature, "source_feature_intersections": candidates,
            "whole_relevant_source_union": geom_record(source_union, area_fn),
            "source_union_intersection": geom_record(intersection, area_fn),
            "component_minus_source_union": geom_record(residual, area_fn),
            "source_covered_area_missing_from_local_atlas_union": geom_record(source_only, area_fn),
            "classification": "mixed-evidence-source-intersection-and-outside-source-residual; executed cause and physical water unresolved",
            "water_status": feature.get("properties", {}).get("water_status", "unverified"),
            "cause_status": "unknown", "administrative_assignment": None,
            "coordinate_scope": "literal longitude/latitude; no wrap, transform, snapping, repair, or normalization"})
    if len(component_rows) != 10 or {r["component_id"] for r in component_rows} != set(component_ids) or len(positive_witnesses) != 1:
        raise ValueError("Exact component roster or nonvacuous actual overlay witness failed")
    sentinel = products["ZMB"]["features"][0]
    negative = shape(component_features[component_ids[0]]["geometry"]).intersection(sentinel["geometry"])
    if not negative.is_empty:
        raise ValueError("Fixed far-away source feature unexpectedly overlaps the first component")
    negative_witnesses.append({"component_id": component_ids[0], "country": "ZMB", "source_feature_index": sentinel["index"],
                               "shapeID": sentinel["shapeID"], "intersection": geom_record(negative, area_fn), "expected_empty": True})

    subject_rows = []
    for subject_id in subject_ids:
        spec = EXPECTED_SUBJECTS[subject_id]
        match = [r for r in products[spec["country"]]["features"] if r["shapeID"] == spec["shapeID"]]
        atlas = atlas_subjects[subject_id]
        source_geometry, atlas_geometry = match[0]["geometry"], shape(atlas["geometry"])
        subject_rows.append({"subject_id": subject_id, "country": spec["country"], "source_shapeID": spec["shapeID"],
            "source_name": spec["name"], "atlas_parent_id": spec["parent_id"],
            "source_feature_index": match[0]["index"], "source_feature_sha256": match[0]["feature_sha256"],
            "atlas_feature_sha256": sha(canonical(atlas)),
            "source_minus_atlas": geom_record(source_geometry.difference(atlas_geometry), area_fn),
            "atlas_minus_source": geom_record(atlas_geometry.difference(source_geometry), area_fn),
            "source_intersection": geom_record(source_geometry.intersection(atlas_geometry), area_fn),
            "source_covers_atlas": source_geometry.covers(atlas_geometry), "atlas_covers_source": atlas_geometry.covers(source_geometry)})
    if len(subject_rows) != 4 or {r["subject_id"] for r in subject_rows} != set(subject_ids):
        raise ValueError("Exact four-subject source/Atlas contract failed")

    fragment_ids = set(fragment_stage["expected_fragment_ids"])
    if set(fragment_stage["features"]) != fragment_ids or fragment_ids != set(custody["fragment_ids"]):
        raise ValueError("Fragment semantic output is missing or expanded beyond exact original membership")
    water_raw = phase.raw(WATER_PATH)
    if sha(water_raw) != "a57bd38b23b57d884853c3e8e6da1a4a24c9ca40dd1edb8e9b2de4db70c0656f":
        raise ValueError("Natural Earth original source pin differs")
    water_decoded = phase.decoded(WATER_PATH, water_raw)
    water = json.loads(water_decoded)
    if len(water.get("features", [])) != 1355:
        raise ValueError("Major-lakes-only whole source count changed")
    water_geometries = [shape(f["geometry"]) for f in water["features"]]
    water_tree, water_rows = STRtree(water_geometries), []
    for component_id in component_ids:
        geometry = shape(component_features[component_id]["geometry"])
        overlaps = []
        for idx in sorted(int(i) for i in water_tree.query(geometry)):
            crossing = geometry.intersection(water_geometries[idx])
            if not crossing.is_empty:
                overlaps.append({"lake_index": idx, "intersection": geom_record(crossing, area_fn)})
        water_rows.append({"component_id": component_id, "major_lake_reference_overlays": overlaps,
                           "interpretation": "major-lakes-only diagnostic; no evidence of dry land or complete hydrology"})
    result = {"version": 1, "issue": 1385, "affected_issue": 1244, "baseline": BASE,
        "component_ids": component_ids, "subject_ids": subject_ids,
        "source_products": {code: {"path": p["path"], "bytes": len(p["raw"]), "sha256": sha(p["raw"]), "feature_count": len(p["features"]),
            "registry": registry.get("gb:" + code + ":ADM2")} for code, p in products.items()},
        "registered_subject_comparisons": subject_rows, "local_country_union_comparisons": union_receipts,
        "local_comparison_method": "union complete whole-source bbox candidates within the issue-component extent expanded by 0.05 degrees; compare source and current Atlas country polygons only in that local window",
        "components": component_rows,
        "original_fragment_features": [fragment_stage["features"][i] for i in sorted(custody["component_fragment_ids"])],
        "original_contact_fragment_features": [fragment_stage["features"][i] for i in sorted(custody["contact_fragment_ids"])],
        "original_fragment_inputs": fragment_stage["shards"],
        "controls": {"positive": positive_witnesses, "negative": negative_witnesses,
                     "positive_count": len(positive_witnesses), "negative_count": len(negative_witnesses)},
        "original_source_contacts": {"input_path": CONTACT_PATH, "input_bytes": custody["contact_input"]["raw_bytes"],
            "input_sha256": custody["contact_input"]["raw_sha256"], "matched_rows": custody["original_contact_rows"]},
        "independent_water_diagnostics": {"source_path": WATER_PATH, "compressed_sha256": sha(water_raw),
            "decoded_sha256": sha(water_decoded), "feature_count": len(water_geometries), "components": water_rows},
        "source_and_scope_limits": [
            "Source metadata represents boundaryYearRepresented 2020, not a legal effective date or registration accuracy statement.",
            "geoBoundaries contributor and license assertions are preserved from the source registry; underlying rights and survey accuracy were not independently authenticated.",
            "Natural Earth reference covers major lakes and reservoirs only, not complete river networks, small waters, or year-specific hydrology.",
            "Planar areas are reported only in square degrees as operation diagnostics; they are not physical area measurements.",
            "Source intersections, Atlas differences, and major-lake overlays do not assign territorial ownership, resolve seam cause, or justify geometry repair.",
            "Local union comparison uses a bounded expanded window, not whole-country union certification.",
            "Atlas row parent IDs are exact current structural references only; semantic status remains open and is not geographically certified here.",
            "Original four regional citations remain restoration-only; UK Order 1963 provides no candidate-scale registered maps or current bilateral boundary/water status.",
            "The source split and original stored geometries are retained without repair, snapping, reassignment or repinning."] ,
        "area_helper": geometry_module.METHOD,
        "runtime": {"python": platform.python_version(), "shapely": shapely.__version__, "geos": shapely.geos_version_string, "pyproj": pyproj.__version__},
        "source_contract": source_contract, "executed_code": executed_code,
        "input_phase_links": {"custody_stage_sha256": sha(custody_raw), "fragment_stage_sha256": sha(fragment_raw)},
        "phase_inputs": phase.records}
    _, result = finalize_phase_output(phase, result, "source-geometry-results.json.gz")
    return result


def run_once(vintage: str, *, input_overrides=None):
    code, inventory = verify_inventory()
    pmap = pinmap()
    custody = custody_phase(ids()[0], pmap)
    fragments = fragment_phase(custody, pmap)
    result = source_geometry_phase(custody, fragments, ids()[1], pmap, inventory, code)
    outputs = {"custody-phase.json.gz": deterministic_gzip(canonical(custody)),
               "fragment-phase.json.gz": deterministic_gzip(canonical(fragments)),
               "source-geometry-results.json.gz": deterministic_gzip(canonical(result))}
    def output_phase_bytes(value, filename, raw):
        decoded_bytes = len(gzip.decompress(raw)) if filename.endswith(".gz") else 0
        return value["phase_accounting"]["input_bytes"] + len(raw) + decoded_bytes
    phase_bytes = {"source-contract": inventory["phase_bytes"],
                   "custody": output_phase_bytes(custody, "custody-phase.json.gz", outputs["custody-phase.json.gz"]),
                   "fragments": output_phase_bytes(fragments, "fragment-phase.json.gz", outputs["fragment-phase.json.gz"]),
                   "source-and-geometry": output_phase_bytes(result, "source-geometry-results.json.gz", outputs["source-geometry-results.json.gz"])}
    if any(value > 256 * 1024 * 1024 for value in phase_bytes.values()):
        raise ValueError("A complete semantic phase including its output exceeds 256 MiB")
    summary = {"version": 1, "issue": 1385, "baseline_commit": BASE, "source_lock_sha256": sha((HERE / "source-lock.json").read_bytes()),
               "issue_contract_sha256": inventory["issue_contract_sha256"], "executed_code": code,
               "phase_bytes": phase_bytes, "phase_limits": {"max_file_bytes": 32 * 1024 * 1024, "max_phase_bytes": 256 * 1024 * 1024},
               "outputs": [{"name": name, "bytes": len(raw), "sha256": sha(raw),
                            "decoded_bytes": len(gzip.decompress(raw)), "decoded_sha256": sha(gzip.decompress(raw))}
                           for name, raw in sorted(outputs.items())]}
    outputs["run-summary.json"] = canonical(summary)
    phase = Phase("whole-run-publication", [], pin_map=pmap)
    for name, raw in outputs.items():
        phase.account_output(name, raw)
    receipt = secure_publish(vintage, list(outputs), outputs, phase)
    return {"vintage": vintage, "publication_sha256": sha(receipt),
            "outputs": [{"name": n, "bytes": len(b), "sha256": sha(b),
                         "decoded_sha256": sha(gzip.decompress(b)) if n.endswith(".gz") else sha(b)} for n, b in outputs.items()],
            "phase_bytes": {**phase_bytes,
                            "publication": sum(phase.baseline.consumed.values())}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True)
    parser.add_argument("--input-override", action="append", default=[], metavar="REPO_PATH=OWNED_FIXTURE")
    args = parser.parse_args()
    overrides = {}
    for item in args.input_override:
        path, fixture = item.split("=", 1)
        fixture_path = (HERE / fixture).resolve()
        if not fixture_path.is_relative_to(HERE) or fixture_path.is_symlink():
            raise ValueError("Input drift fixtures must stay in the owned evidence tree")
        raw = fixture_path.read_bytes()
        if path in overrides:
            raise ValueError("Duplicate input override")
        overrides[path] = raw
    if overrides:
        # Control path: offer altered bytes to the real pinned reader, which must
        # reject them before parsing or creating an output vintage.
        code = verify_code()
        candidate = next(iter(overrides.items()))
        phase = Phase("input-drift-control", [candidate[0]], pin_map=pinmap(), overrides=overrides)
        phase.raw(candidate[0])
        raise AssertionError("Altered immutable input unexpectedly reached publication")
    print(json.dumps(run_once(args.vintage), sort_keys=True))


if __name__ == "__main__":
    main()
