#!/usr/bin/env python3
"""Reproduce the complete, frozen #1299 source and geometry comparison."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import types

import numpy
import pyproj
import shapely
from shapely import union_all
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, Point, shape, mapping

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
BASELINE = "fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7"
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope_guard import COMPONENTS, capture_tree, load_frozen_scope, validate_subject_parents

OWNED_PATH = "research/geography/portugal-spain-official-boundaries-audit-followup-20261008/"
SOURCE_ROOT = Path(os.environ.get("WORLDATLAS_SOURCE_ROOT", str(REPO / "research/geography/portugal-spain-official-boundaries-20261007"))).resolve()
SCOPE_PATH = Path(os.environ.get("WORLDATLAS_SCOPE_PATH", str(SOURCE_ROOT / "inputs" / "scope.json"))).resolve()
CAPTURE_INDEX_PATH = SOURCE_ROOT / "sources" / "official-capture-index.json"
INPUT_INDEX_PATH = "research/geography/portugal-spain-gap-source-families-20261007/inputs/complete-input-index.json"
SOURCE_REGISTRY_PATH = "data/administrative-sources.json"
PART_PATHS = ["data/geography/part-8.json", "data/geography/part-19.json", "data/geography/part-29.json"]
WORLD_INDEX_PATH = "data/world-index.json"
RAW_CAPTURE_DIR = SOURCE_ROOT / "sources" / "official"

ACTIVE_OUTPUTS = None
ACTIVE_EXPECTED = None
ACTIVE_RUN = None
wa_geometry = None
ImmutableBaseline = None
NewVintage = None

def packet_baseline():
    global wa_geometry, ImmutableBaseline, NewVintage
    helper_raw = git_blob("scripts/evidence/immutable.py", "c8df65e1d5c4d235c33e2f488c3e29d26223860f")
    if digest(helper_raw) != "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46":
        raise ValueError("Shared immutable evidence helper pin mismatch")
    immutable = types.ModuleType("worldatlas_immutable_pinned")
    immutable.__file__ = "scripts/evidence/immutable.py@c8df65e1"
    exec(compile(helper_raw, immutable.__file__, "exec"), immutable.__dict__)
    ImmutableBaseline, NewVintage = immutable.Baseline, immutable.NewVintage
    packet = capture_tree(REPO, SOURCE_ROOT)
    manifest_raw = (SOURCE_ROOT / "evidence-quality.json").read_bytes()
    manifest = json.loads(manifest_raw)
    files = {}
    original_files = list(manifest["outputs"]) + [file for source in manifest.get("sources", []) for file in source.get("files", [])]
    for row in original_files:
        files[row["path"]] = {k: row[k] for k in ("path", "bytes", "sha256", "hash_kind")}
    manifest_rel = str((SOURCE_ROOT / "evidence-quality.json").relative_to(REPO))
    files[manifest_rel] = {"path": manifest_rel, "bytes": len(manifest_raw), "sha256": digest(manifest_raw), "hash_kind": "file-bytes"}
    baseline = ImmutableBaseline(REPO, "cbae22cc877f6f8a70650069d91d2b34240582f7", list(files.values()))
    # Authenticate actual materialized packet inputs against the exact PR #1312 merge.
    for relative in files:
        baseline.materialized_bytes(relative)
    geometry_pin = {"path": "scripts/evidence/geometry.py", "bytes": 6573,
                    "sha256": "0b8e5b155c7a68b802b99a3597c63ac48293f276e682d34e9167cb5105b2a334", "hash_kind": "file-bytes"}
    area_pin = {"path": "scripts/ellipsoidal_area.py", "bytes": 1953,
                "sha256": "4ead1c5de909b257a7b300984e4d3dc56124e9a6c0d27240662024e44fd8ed12", "hash_kind": "file-bytes"}
    scientific = ImmutableBaseline(REPO, BASELINE, [geometry_pin, area_pin])
    wa_geometry = scientific.load_modules({"evidence.geometry": geometry_pin["path"], "ellipsoidal_area": area_pin["path"]})["evidence.geometry"]
    return baseline, packet

def planned_run_outputs():
    names = []
    load_frozen_scope(SCOPE_PATH)
    for ordinal, _cid in enumerate(COMPONENTS, 1):
        names.extend([f"component-{ordinal:02d}-coverage-summary.json", f"component-{ordinal:02d}-polygon-overlays.json"])
    names.extend(["boundary-line-overlays.json", "identity-and-vintage.json", "identity-geometry-comparisons.json",
                  "source-vintage-crs-and-terms-assessment.json", "summary.json", "execution-receipt.json"])
    if len(names) != 14 or len(set(names)) != len(names):
        raise ValueError("Unexpected complete producer output inventory")
    return names

def git_blob(path: str, commit: str = BASELINE) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=REPO)

def digest(data: bytes) -> str:
    return sha256(data).hexdigest()

def canonical_hash(value) -> str:
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return digest(raw)

def write_json(path: Path, value) -> bytes:
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if ACTIVE_OUTPUTS is None:
        raise RuntimeError("Producer output outside an admitted fresh vintage")
    parts = path.relative_to(ROOT).parts
    if parts[:2] == ("runs", ACTIVE_RUN):
        parts = parts[2:]
        if parts[:1] == ("components",) and len(parts) == 3:
            # Resolve from the authenticated component ID rather than trusting a candidate filename.
            matching = next((i for i, value in enumerate(COMPONENTS, 1) if value.replace(":", "_") == parts[1]), None)
            if matching is None:
                raise ValueError("Unexpected component output path")
            suffix = "coverage-summary.json" if parts[2] == "coverage-summary.json" else "polygon-overlays.json" if parts[2] == "polygon-overlays.json" else None
            if suffix is None:
                raise ValueError("Unexpected component output filename")
            parts = (f"component-{matching:02d}-{suffix}",)
    elif parts[:1] == ("controls",):
        parts = parts[1:]
    relative = "--".join(parts)
    if relative not in ACTIVE_EXPECTED or relative in ACTIVE_OUTPUTS:
        raise ValueError("Unexpected or duplicate producer output: " + relative)
    ACTIVE_OUTPUTS[relative] = raw
    return raw

def feature_id(feature):
    return feature.get("id") or (feature.get("properties") or {}).get("id")

def all_xy(geometry):
    """Return every coordinate and reject Z/M dimensions without coercion."""
    result = []
    def walk(value):
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(x, (int, float)) for x in value):
                if len(value) != 2:
                    raise ValueError("Only two-dimensional coordinates are supported")
                result.append((float(value[0]), float(value[1])))
            else:
                for child in value:
                    walk(child)
    walk(geometry.get("coordinates", []))
    return result

def bounds_and_extent(geometry, label):
    coords = all_xy(geometry)
    if not coords:
        raise ValueError(f"Empty coordinates: {label}")
    for lon, lat in coords:
        wa_geometry.point(lon, lat)
        if not (-9.8 <= lon <= -5.5 and 36.2 <= lat <= 39.2):
            raise ValueError(f"Coordinate outside scoped CRS84 envelope: {label}: {(lon, lat)}")
    return [min(x for x, _ in coords), min(y for _, y in coords), max(x for x, _ in coords), max(y for _, y in coords)]

def read_capture(capture_index, source_id):
    row = next((x for x in capture_index["captures"] if x["id"] == source_id), None)
    if row is None:
        raise ValueError(f"Missing official capture: {source_id}")
    body = (SOURCE_ROOT / row["body_path"]).read_bytes()
    if row["http_status"] != 200 or row["curl_exit"] != 0 or len(body) != row["body_bytes"] or digest(body) != row["body_sha256"]:
        raise ValueError(f"Official response receipt mismatch: {source_id}")
    headers = (SOURCE_ROOT / row["headers_path"]).read_text(encoding="utf-8", errors="replace")
    return row, body, headers

def geojson_feature(capture_index, source_id, expected_id, expected_name):
    row, raw, headers = read_capture(capture_index, source_id)
    obj = json.loads(raw)
    if obj.get("type") != "Feature" or str(feature_id(obj)) != str(expected_id):
        raise ValueError(f"Unexpected item identity: {source_id}")
    props = obj.get("properties") or {}
    name_keys = ("municipio", "nameunit", "name_boundary")
    if not any(props.get(name_key) == expected_name for name_key in name_keys):
        raise ValueError(f"Unexpected item name: {source_id}")
    if "Content-Crs: <http://www.opengis.net/def/crs/OGC/1.3/CRS84>" not in headers:
        raise ValueError(f"Returned coordinate reference not pinned as CRS84: {source_id}")
    bounds = bounds_and_extent(obj["geometry"], source_id)
    geom = shape(obj["geometry"])
    return {"id": source_id, "response": row, "feature": obj, "geometry": geom, "bounds": bounds}

def feature_from_collection(collection, expected_id):
    matches = [f for f in collection.get("features", []) if feature_id(f) == expected_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one source feature {expected_id}, found {len(matches)}")
    return matches[0]

def polygon_geometry(feature, label):
    geom_json = feature.get("geometry")
    if not geom_json:
        raise ValueError(f"Missing polygon geometry: {label}")
    bounds = bounds_and_extent(geom_json, label)
    geom = shape(geom_json)
    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError(f"Expected polygon feature: {label} ({geom.geom_type})")
    if not geom.is_valid:
        raise ValueError(f"Invalid input polygon (preserved, not repaired): {label}")
    # Existing reviewed helper validates longitude-first source edges and multipart topology.
    canonical = wa_geometry.canonical_land(geom)
    return geom, canonical, bounds

def geo_area(geom):
    return wa_geometry.area(geom)

def geom_json(geom):
    return mapping(geom) if geom is not None and not geom.is_empty else None

def count_geom(geom):
    if geom is None or geom.is_empty:
        return {"Polygon": 0, "LineString": 0, "Point": 0, "other": 0}
    out = Counter()
    def walk(g):
        if g.geom_type in ("Polygon", "MultiPolygon"):
            out["Polygon"] += sum(1 for x in ([g] if g.geom_type == "Polygon" else g.geoms))
        elif g.geom_type in ("LineString", "LinearRing", "MultiLineString"):
            out["LineString"] += sum(1 for x in ([g] if g.geom_type in ("LineString", "LinearRing") else g.geoms))
        elif g.geom_type in ("Point", "MultiPoint"):
            out["Point"] += sum(1 for x in ([g] if g.geom_type == "Point" else g.geoms))
        elif g.geom_type == "GeometryCollection":
            for child in g.geoms:
                walk(child)
        else:
            out["other"] += 1
    walk(geom)
    return {key: int(out.get(key, 0)) for key in ("Polygon", "LineString", "Point", "other")}

def line_length_m(geom):
    if geom.is_empty:
        return 0.0
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        return float(wa_geometry.GEOD.line_length([p[0] for p in coords], [p[1] for p in coords]))
    if geom.geom_type == "MultiLineString":
        return math.fsum(line_length_m(part) for part in geom.geoms)
    if geom.geom_type == "GeometryCollection":
        return math.fsum(line_length_m(part) for part in geom.geoms)
    return 0.0

def point_count(geom):
    if geom.is_empty:
        return 0
    if geom.geom_type == "Point":
        return 1
    if geom.geom_type == "MultiPoint":
        return len(geom.geoms)
    if geom.geom_type == "GeometryCollection":
        return sum(point_count(g) for g in geom.geoms)
    return 0

def polygon_pair(a, b, a_label, b_label):
    a_area, b_area = geo_area(a), geo_area(b)
    intersection = a.intersection(b)
    shared_boundary = a.boundary.intersection(b.boundary)
    residual = a.difference(b)
    return {
        "a": a_label,
        "b": b_label,
        "a_area_m2": a_area,
        "b_area_m2": b_area,
        "intersection_area_m2": geo_area(intersection),
        "a_coverage_fraction": geo_area(intersection) / a_area if a_area else None,
        "b_coverage_fraction": geo_area(intersection) / b_area if b_area else None,
        "a_minus_b_area_m2": geo_area(residual),
        "a_minus_b_geometry": geom_json(residual),
        "shared_boundary_length_m": line_length_m(shared_boundary),
        "shared_boundary_point_count": point_count(shared_boundary),
        "shared_boundary_geometry": geom_json(shared_boundary),
        "intersection_geometry_types": count_geom(intersection),
        "intersection_geometry": geom_json(intersection),
        "intersects": bool(a.intersects(b)),
        "covers": bool(a.covers(b)),
        "covered_by": bool(b.covers(a)),
    }

def line_pair(line, polygon, line_label, polygon_label):
    inside = line.intersection(polygon)
    boundary = line.intersection(polygon.boundary)
    return {
        "line": line_label,
        "polygon": polygon_label,
        "source_line_length_m": line_length_m(line),
        "line_inside_or_on_polygon_length_m": line_length_m(inside),
        "line_on_polygon_boundary_length_m": line_length_m(boundary),
        "line_inside_exclusive_length_m": line_length_m(inside.difference(boundary)),
        "line_polygon_contact_point_count": point_count(inside),
        "line_boundary_contact_point_count": point_count(boundary),
        "line_polygon_contact_types": count_geom(inside),
        "line_polygon_contact_geometry": geom_json(inside),
        "line_boundary_contact_geometry": geom_json(boundary),
    }

def verify_source_products(input_index, scope):
    products = {}
    records = {}
    for entry in input_index["source_product_payload_descriptors"]:
        key = entry["source_key"]
        part = entry["part"]
        payload = entry["descriptor"]
        compressed = git_blob(payload["path"], payload["commit"])
        if len(compressed) != part["bytes"] or digest(compressed) != part["sha256"]:
            raise ValueError(f"Pinned consumed source shard failed byte check: {key}")
        raw = gzip.decompress(compressed)
        if len(raw) != part["uncompressed_bytes"] or digest(raw) != part["uncompressed_sha256"]:
            raise ValueError(f"Consumed source product reconstruction failed: {key}")
        obj = json.loads(raw)
        expected_count = scope["original_consumed_source_products"][key]["full_native_feature_count"]
        if len(obj.get("features", [])) != expected_count:
            raise ValueError(f"Consumed source feature count mismatch: {key}")
        prefix = key + ":"
        products[key] = {"object": obj, "raw_sha256": digest(raw), "raw_bytes": len(raw), "compressed_sha256": digest(compressed), "compressed_bytes": len(compressed)}
        records[key] = {prefix + str((f.get("properties") or {}).get("shapeID")): f for f in obj["features"]}
    return products, records

def load_context():
    baseline, packet = packet_baseline()
    scope = load_frozen_scope(SCOPE_PATH)
    if scope["baseline_commit"] != BASELINE:
        raise ValueError("Scope/baseline commit mismatch")
    capture_index_raw = CAPTURE_INDEX_PATH.read_bytes()
    if digest(capture_index_raw) != "f63611c528ff85074b1e527e95d1647778d06473cb663b10fd1be5320f377f6d":
        raise ValueError("Frozen complete source-capture index hash mismatch")
    capture_index = json.loads(capture_index_raw)
    input_index = json.loads(git_blob(INPUT_INDEX_PATH))
    source_registry = json.loads(git_blob(SOURCE_REGISTRY_PATH))
    baseline_features = {}
    baseline_bytes = {}
    for path in PART_PATHS + [WORLD_INDEX_PATH, SOURCE_REGISTRY_PATH, INPUT_INDEX_PATH]:
        raw = git_blob(path)
        baseline_bytes[path] = raw
        if path.endswith(".json") and path != SOURCE_REGISTRY_PATH and path != INPUT_INDEX_PATH and path != WORLD_INDEX_PATH:
            obj = json.loads(raw)
            baseline_features[path] = obj
    for path in PART_PATHS:
        if path not in baseline_features:
            baseline_features[path] = json.loads(git_blob(path))
    parts_by_id = {}
    for path, collection in baseline_features.items():
        if path not in PART_PATHS:
            continue
        for ordinal, feature in enumerate(collection.get("features", [])):
            parts_by_id.setdefault(feature_id(feature), []).append((path, ordinal, feature))
    subjects = {}
    for subject_id, path in scope["pinned_baseline_subject_files"].items():
        rows = [(p, n, f) for p, n, f in parts_by_id.get(subject_id, []) if p == path]
        if len(rows) != 1:
            raise ValueError(f"Expected exact one baseline subject in pinned part: {subject_id}")
        subjects[subject_id] = rows[0]

    components = {}
    for row in input_index["current_lineage_rows"]:
        cid = row["id"]
        if cid not in {x for fam in scope["families"] for x in fam["component_ids"]}:
            continue
        matches = [x for x in input_index["component_v3_alias_resolution"] if cid in x["target_component_ids_in_payload"]]
        if len(matches) != 1:
            raise ValueError(f"Component not bound to one original containing shard: {cid}")
        alias = matches[0]
        descriptor = alias["virtual_original_descriptor"]
        payload = alias["ordinary_payload_descriptor"]
        if payload["bytes"] != descriptor["bytes"] or payload["sha256"] != descriptor["sha256"]:
            raise ValueError(f"Component custody payload differs from virtual original descriptor: {cid}")
        compressed = git_blob(payload["path"], payload["commit"])
        if len(compressed) != descriptor["bytes"] or digest(compressed) != descriptor["sha256"]:
            raise ValueError(f"Component shard byte pin mismatch: {cid}")
        unpacked = gzip.decompress(compressed)
        if len(unpacked) != descriptor["uncompressed_bytes"] or digest(unpacked) != descriptor["uncompressed_sha256"]:
            raise ValueError(f"Component shard reconstruction mismatch: {cid}")
        fc = json.loads(unpacked)
        feature = feature_from_collection(fc, cid)
        if canonical_hash(feature) != row["full_feature_sha256"]:
            raise ValueError(f"Whole component record hash mismatch: {cid}")
        geom, canonical, bounds = polygon_geometry(feature, cid)
        components[cid] = {"feature": feature, "geometry": geom, "canonical": canonical, "bounds": bounds,
                           "lineage": row, "shard": descriptor}

    native_products, native_records = verify_source_products(input_index, scope)
    official = {}
    item_specs = {
        "dgt-barrancos-0204": ("0204", "Barrancos"),
        "dgt-moura-0210": ("0210", "Moura"),
        "ign-encinasola-1166667": ("1166667", "Encinasola"),
        "ign-rosal-1166698": ("1166698", "Rosal de la Frontera"),
    }
    for source_id, (native_id, name) in item_specs.items():
        item = geojson_feature(capture_index, source_id, native_id, name)
        geom, canonical, bounds = polygon_geometry(item["feature"], source_id)
        item.update({"geometry": geom, "canonical": canonical, "bounds": bounds})
        official[source_id] = item
    lines = {}
    for source_id, native_id, name in [
        ("ign-encinasola-portugal-5679963", "5679963", "Encinasola#Portugal"),
        ("ign-rosal-portugal-5671403", "5671403", "Rosal de la Frontera#Portugal"),
    ]:
        item = geojson_feature(capture_index, source_id, native_id, name)
        if item["feature"]["geometry"].get("type") not in ("LineString", "MultiLineString"):
            raise ValueError(f"Expected complete boundary line: {source_id}")
        item["geometry"] = shape(item["feature"]["geometry"])
        if not item["geometry"].is_valid:
            raise ValueError(f"Invalid boundary line: {source_id}")
        lines[source_id] = item

    native = {}
    for source_id in [
        "gb:ESP:ADM3:28895703B56784737193540",
        "gb:ESP:ADM3:28895703B57935909975717",
        "gb:PRT:ADM2:2272694B13078000098594",
        "gb:PRT:ADM2:2272694B82300393258858",
    ]:
        product_key = "gb:ESP:ADM3" if ":ESP:" in source_id else "gb:PRT:ADM2"
        feat = native_records[product_key].get(source_id)
        if feat is None:
            raise ValueError(f"Native record not found in exact consumed product: {source_id}")
        geom, canonical, bounds = polygon_geometry(feat, source_id)
        native[source_id] = {"feature": feat, "geometry": geom, "canonical": canonical, "bounds": bounds,
                             "product": native_products[product_key]}

    # The Atlas district remains a 28-member aggregate; Encinasola is one exact source member.
    district = subjects["atlas:district:ESP-2101:def08fa9"][2]
    member_ids = district["properties"]["metadata"]["source_member_ids"]
    if len(member_ids) != 28 or len(set(member_ids)) != 28:
        raise ValueError("Atlas district source-member roster changed")
    missing_members = [mid for mid in member_ids if "gb:ESP:ADM3:" + mid.split(":")[-1] not in native_records["gb:ESP:ADM3"]]
    if missing_members:
        raise ValueError(f"Atlas district source members missing from 2018 whole source: {missing_members}")
    encinasola_member_id = "gb:ESP:ADM3:28895703B57935909975717"
    if encinasola_member_id not in member_ids:
        raise ValueError("Encinasola candidate is not a retained member of the Atlas district")
    district_members = [native_records["gb:ESP:ADM3"]["gb:ESP:ADM3:" + mid.split(":")[-1]] for mid in member_ids]
    district_member_geoms = [polygon_geometry(f, feature_id(f))[1] for f in district_members]

    # Original Atlas whole-feature geometries are also validated without correction.
    current_subjects = {}
    for subject_id, (path, ordinal, feature) in subjects.items():
        geom, canonical, bounds = polygon_geometry(feature, subject_id)
        current_subjects[subject_id] = {"feature": feature, "geometry": geom, "canonical": canonical,
                                        "bounds": bounds, "part": path, "ordinal": ordinal,
                                        "feature_sha256": canonical_hash(feature)}
    validate_subject_parents({key: value["feature"] for key, value in current_subjects.items()})

    for source_id, f in current_subjects.items():
        metadata = (f["feature"].get("properties") or {}).get("metadata") or {}
        if source_id.startswith("gb:") and metadata.get("original_id") != source_id.split(":")[-1]:
            raise ValueError(f"Current Atlas source ID does not preserve native ID: {source_id}")
    return {
        "packet_preservation": packet,
        "packet_baseline": baseline,
        "scope": scope,
        "capture_index": capture_index,
        "input_index": input_index,
        "source_registry": source_registry,
        "baseline_bytes": baseline_bytes,
        "subjects": current_subjects,
        "components": components,
        "native_products": native_products,
        "native_records": native,
        "district_member_ids": member_ids,
        "district_member_features": district_members,
        "district_member_geometries": district_member_geoms,
        "official": official,
        "lines": lines,
    }

def feature_identity_report(ctx):
    scope = ctx["scope"]
    member_feature_names = []
    for fid in ctx["district_member_features"]:
        p = fid["properties"]
        member_feature_names.append({"id": feature_id(fid), "name": p.get("shapeName"), "source_type": p.get("shapeType"),
                                     "feature_sha256": canonical_hash(fid), "geometry_type": fid["geometry"]["type"]})
    baseline_rows = []
    for subject_id, row in ctx["subjects"].items():
        feature = row["feature"]
        props = feature.get("properties") or {}
        meta = props.get("metadata") or {}
        baseline_rows.append({"id": subject_id, "name": props.get("name"), "part": row["part"], "ordinal": row["ordinal"],
                              "whole_feature_sha256": row["feature_sha256"], "geometry_type": feature["geometry"]["type"],
                              "source_id": meta.get("source_id"), "source_url": meta.get("source_url"),
                              "source_name": meta.get("source_name"), "source_role": meta.get("source_role"),
                              "source_member_count": len(meta.get("source_member_ids", [])),
                              "source_member_ids": meta.get("source_member_ids", [])})
    official_rows = []
    for source_id, value in ctx["official"].items():
        f = value["feature"]
        official_rows.append({"id": source_id, "native_id": f.get("id"), "properties": f.get("properties"),
                              "geometry_type": f["geometry"]["type"], "bounds_crs84": value["bounds"],
                              "response_bytes": value["response"]["body_bytes"], "response_sha256": value["response"]["body_sha256"],
                              "retrieved_at_local": value["response"]["retrieved_at_local"]})
    old_rows = []
    for source_id, value in ctx["native_records"].items():
        f = value["feature"]
        old_rows.append({"id": source_id, "shapeName": f["properties"].get("shapeName"), "shapeISO": f["properties"].get("shapeISO"),
                         "shapeType": f["properties"].get("shapeType"), "whole_feature_sha256": canonical_hash(f),
                         "geometry_type": f["geometry"]["type"], "bounds_crs84": value["bounds"]})
    return {
        "version": 1,
        "baseline_commit": BASELINE,
        "families": scope["families"],
        "baseline_contact_subjects": baseline_rows,
        "whole_consumed_source_products": {key: {k: v for k, v in val.items() if k != "object"} for key, val in ctx["native_products"].items()},
        "exact_original_native_records": old_rows,
        "atlas_esp_2101_source_members": {
            "aggregate_subject_id": "atlas:district:ESP-2101:def08fa9",
            "member_count": len(member_feature_names),
            "members": member_feature_names,
            "encinasola_member_id": "gb:ESP:ADM3:28895703B57935909975717",
            "limitation": "The 28-member Atlas district is not a municipality alias. Encinasola is one exact source member inside that aggregate.",
        },
        "official_whole_items": official_rows,
        "official_line_items": [
            {"id": source_id, "native_id": val["feature"].get("id"), "properties": val["feature"].get("properties"),
             "geometry_type": val["feature"]["geometry"]["type"], "whole_response_bytes": val["response"]["body_bytes"],
             "whole_response_sha256": val["response"]["body_sha256"], "retrieved_at_local": val["response"]["retrieved_at_local"]}
            for source_id, val in ctx["lines"].items()
        ],
        "identity_relations": [
            {"atlas_subject": "gb:ESP:ADM3:28895703B56784737193540", "old_native_record": "gb:ESP:ADM3:28895703B56784737193540", "candidate_official_item": "ign-administrativeunit-1166698", "basis": "Exact old source ID/name plus full polygon comparison; IGN nationalcode is a distinct scheme; no same-ID alias asserted."},
            {"atlas_subject": "gb:PRT:ADM2:2272694B13078000098594", "old_native_record": "gb:PRT:ADM2:2272694B13078000098594", "candidate_official_item": "dgt-caop2025-0204", "basis": "Exact old source ID/name plus full polygon comparison; DGT DTMN is a distinct scheme; no same-ID alias asserted."},
            {"atlas_subject": "gb:PRT:ADM2:2272694B82300393258858", "old_native_record": "gb:PRT:ADM2:2272694B82300393258858", "candidate_official_item": "dgt-caop2025-0210", "basis": "Exact old source ID/name plus full polygon comparison; DGT DTMN is a distinct scheme; no same-ID alias asserted."},
            {"atlas_subject": "atlas:district:ESP-2101:def08fa9", "old_native_record": "gb:ESP:ADM3:28895703B57935909975717", "candidate_official_item": "ign-administrativeunit-1166667", "basis": "Encinasola is a member of the 28-member district source roster; its name/nationalcode and whole polygon are checked separately. This is a member relation, not an alias of the Atlas district."}
        ],
        "classification": {"physical_class": "unknown", "cause": "unknown", "rightful_owner": "unknown", "water_or_ice": "unknown", "certification": "none"},
    }

def compare_identity_pairs(ctx):
    pairs = [
        ("gb:ESP:ADM3:28895703B56784737193540", "ign-rosal-1166698"),
        ("gb:ESP:ADM3:28895703B57935909975717", "ign-encinasola-1166667"),
        ("gb:PRT:ADM2:2272694B13078000098594", "dgt-barrancos-0204"),
        ("gb:PRT:ADM2:2272694B82300393258858", "dgt-moura-0210"),
    ]
    rows = []
    for old_id, official_id in pairs:
        old = ctx["native_records"][old_id]
        new = ctx["official"][official_id]
        row = polygon_pair(old["canonical"], new["canonical"], old_id, official_id)
        row.update({"comparison_role": "candidate unit correspondence; distinct native identifier schemes retained",
                    "old_geometry_sha256": canonical_hash(old["feature"]["geometry"]),
                    "official_response_sha256": new["response"]["body_sha256"],
                    "symmetric_difference_area_m2": geo_area(old["canonical"].symmetric_difference(new["canonical"])),
                    "symmetric_difference_geometry": geom_json(old["canonical"].symmetric_difference(new["canonical"]))})
        rows.append(row)
    district = ctx["subjects"]["atlas:district:ESP-2101:def08fa9"]
    members_union = union_all(ctx["district_member_geometries"])
    member_union_row = polygon_pair(district["canonical"], members_union, "atlas:district:ESP-2101:def08fa9", "union-of-28-exact-source-members")
    member_union_row["comparison_role"] = "aggregate lineage check; union is a derived overlay, not an identity replacement"
    member_union_row["member_count"] = len(ctx["district_member_geometries"])
    return {"version": 1, "baseline_commit": BASELINE, "old_native_to_official_candidates": rows,
            "atlas_aggregate_to_exact_source_member_union": member_union_row}

def run_component_outputs(ctx, run_dir: Path):
    subject_layers = [("atlas-current", key, value["canonical"]) for key, value in ctx["subjects"].items()]
    old_layers = [("consumed-source", key, value["canonical"]) for key, value in ctx["native_records"].items()]
    official_layers = [("official-item", key, value["canonical"]) for key, value in ctx["official"].items()]
    official_union = union_all([value["canonical"] for value in ctx["official"].values()])
    all_component_results = []
    for family in ctx["scope"]["families"]:
        for cid in family["component_ids"]:
            component = ctx["components"][cid]
            cgeom = component["canonical"]
            area = geo_area(cgeom)
            coverage = cgeom.intersection(official_union)
            uncovered = cgeom.difference(official_union)
            summary = {
                "component_id": cid, "family_id": family["id"],
                "source_shard_path": component["shard"]["path"],
                "source_shard_sha256": component["shard"]["sha256"],
                "whole_feature_sha256": canonical_hash(component["feature"]),
                "geometry_type": component["feature"]["geometry"]["type"],
                "component_area_m2": area,
                "four_official_municipal_union_area_m2": geo_area(official_union),
                "intersection_area_m2": geo_area(coverage),
                "component_coverage_fraction": geo_area(coverage) / area if area else None,
                "component_uncovered_area_m2": geo_area(uncovered),
                "uncovered_component_piece_count": len(uncovered.geoms) if hasattr(uncovered, "geoms") else (0 if uncovered.is_empty else 1),
                "uncovered_component_geometry": geom_json(uncovered),
                "whole_native_component_geometry_input": "Pinned full containing component shard; not reserialized into this output.",
                "limits": ["Administrative polygon overlap is not ownership, physical land/water, historical authority or processing cause."],
            }
            overlays = []
            for category, layers in [("atlas-current", subject_layers), ("consumed-source", old_layers), ("official-item", official_layers)]:
                for _, label, poly in layers:
                    row = polygon_pair(cgeom, poly, cid, label)
                    row["overlay_category"] = category
                    overlays.append(row)
            comp_dir = run_dir / "components" / cid.replace(":", "_")
            write_json(comp_dir / "coverage-summary.json", summary)
            write_json(comp_dir / "polygon-overlays.json", {"version": 1, "component_id": cid, "overlays": overlays})
            all_component_results.append(summary)
    return all_component_results

def run_boundary_outputs(ctx, run_dir: Path):
    polygons = []
    for source_id, value in ctx["subjects"].items():
        polygons.append(("atlas-current", source_id, value["canonical"]))
    for source_id, value in ctx["native_records"].items():
        polygons.append(("consumed-source", source_id, value["canonical"]))
    for source_id, value in ctx["official"].items():
        polygons.append(("official-item", source_id, value["canonical"]))
    for cid, value in ctx["components"].items():
        polygons.append(("gap-component", cid, value["canonical"]))
    rows = []
    for line_id, line in ctx["lines"].items():
        for category, label, poly in polygons:
            rows.append(line_pair(line["geometry"], poly, line_id, label) | {"polygon_category": category})
    write_json(run_dir / "boundary-line-overlays.json", {"version": 1, "line_item_count": len(ctx["lines"]), "comparisons": rows})
    return rows

def source_vintage_caveats(ctx):
    index = ctx["capture_index"]
    dgt = json.loads((RAW_CAPTURE_DIR / "dgt-caop2025-collection.body").read_bytes())
    ign_units = json.loads((RAW_CAPTURE_DIR / "ign-administrativeunit-collection.body").read_bytes())
    ign_lines = json.loads((RAW_CAPTURE_DIR / "ign-administrativeboundary-collection.body").read_bytes())
    return {
        "dgt_caop2025": {
            "official_product_page_claim": "CAOP2025; approved by DGT Director-General order dated 2026-01-28 and published in Diário da República Aviso 3502/2026/2 on 2026-02-18; official page says changes from 2025-03-16 through 2025-12-31.",
            "api_collection_title": dgt.get("title"),
            "api_temporal_extent": dgt.get("extent", {}).get("temporal"),
            "api_storage_crs": dgt.get("storageCrs"),
            "direct_item_return_crs": "OGC:CRS84 from each pinned Content-Crs header; longitude, latitude coordinates; already transformed by provider from storage CRS.",
            "vintage_assessment": "The official product page establishes a CAOP2025 release and change window. The API collection's declared interval 2000-10-30 through 2007-10-30 conflicts with the title; no per-item validity date is returned. Treat per-feature effective date as unresolved.",
        },
        "ign_administrativeunit": {
            "collection_title": ign_units.get("title"),
            "temporal_extent": ign_units.get("extent", {}).get("temporal"),
            "storage_crs": ign_units.get("storageCRS"),
            "direct_item_return_crs": "OGC:CRS84 from each pinned Content-Crs header; longitude, latitude coordinates.",
            "vintage_assessment": "The collection and selected polygons provide no validity date or dated polygon snapshot. Retrieval date is recorded; it is not a legal/effective date.",
        },
        "ign_administrativeboundary": {
            "collection_title": ign_lines.get("title"),
            "temporal_extent": ign_lines.get("extent", {}).get("temporal"),
            "storage_crs": ign_lines.get("storageCRS"),
            "direct_item_return_crs": "OGC:CRS84 from each pinned Content-Crs header; longitude, latitude coordinates.",
            "vintage_assessment": "Selected records return item-level date_boundary 2022-04-04 and legalstatus=agreed. The two linked resource URLs return the same generic CNIG landing page rather than item-specific record content. These Spanish item attributes do not alone prove bilateral authority or a matching Portuguese line.",
        },
        "coordinate_method": {
            "input_axis_order": "longitude-latitude",
            "area_crs": "EPSG:4326 / WGS84 with always-xy semantics, matching the existing WorldAtlas evidence helper",
            "coordinate_operation": "No extra projection was applied. The OGC API returned CRS84 longitude-latitude coordinates, which were passed as x/y to the existing WGS84 helper. DGT's storage CRS is EPSG:3763, but the item response header declares CRS84.",
            "geometry_policy": "Existing scripts/evidence/geometry.py worldatlas-evidence-geometry-v1 and scripts/ellipsoidal_area.py; direct overlay, no snap, rounding, buffer, MakeValid or proximity repair.",
        },
        "failed_source_attempts": index.get("failed_attempts", []),
    }

def _run_analysis(run_name: str):
    if not re.fullmatch(r"run-[0-9]{2}(?:-r[0-9]+)?", run_name):
        raise ValueError("Use a fresh run-NN or run-NN-rN vintage")
    started_at = datetime.now(ZoneInfo("America/Los_Angeles"))
    ctx = load_context()
    run_dir = ROOT / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    identity = feature_identity_report(ctx)
    identity_pairs = compare_identity_pairs(ctx)
    components = run_component_outputs(ctx, run_dir)
    boundary_rows = run_boundary_outputs(ctx, run_dir)
    write_json(run_dir / "identity-and-vintage.json", identity)
    write_json(run_dir / "identity-geometry-comparisons.json", identity_pairs)
    vintage = source_vintage_caveats(ctx)
    write_json(run_dir / "source-vintage-crs-and-terms-assessment.json", vintage)
    family_summaries = []
    for family in ctx["scope"]["families"]:
        rows = [x for x in components if x["family_id"] == family["id"]]
        total_area = math.fsum(row["component_area_m2"] for row in rows)
        total_covered = math.fsum(row["intersection_area_m2"] for row in rows)
        family_summaries.append({"family_id": family["id"], "component_count": len(rows),
                                 "contact_subjects": family["contact_subjects"],
                                 "component_area_sum_m2": total_area,
                                 "four_official_item_union_covered_area_sum_m2": total_covered,
                                 "coverage_fraction_of_component_area_sum": total_covered / total_area if total_area else None,
                                 "uncovered_area_sum_m2": math.fsum(row["component_uncovered_area_m2"] for row in rows),
                                 "physical_class": "unknown", "cause": "unknown", "rightful_owner": "unknown", "water_or_ice": "unknown"})
    summary = {
        "version": 1,
        "issue": 1299,
        "correction_issue": 1482,
        "corrected_runner_sha256": digest(Path(__file__).read_bytes()),
        "baseline_commit": BASELINE,
        "producer_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "scope": {"family_count": 2, "component_count": len(ctx["components"]), "distinct_contact_subject_count": len(ctx["subjects"]),
                  "family_contact_incidence_count": sum(len(f["contact_subjects"]) for f in ctx["scope"]["families"]),
                  "moura_occurrences": sum(f["contact_subjects"].count("gb:PRT:ADM2:2272694B82300393258858") for f in ctx["scope"]["families"])},
        "feature_counts": {"current_atlas_subjects": len(ctx["subjects"]), "complete_old_source_products": {key: val["object"]["features"] and len(val["object"]["features"]) for key, val in ctx["native_products"].items()},
                            "atlas_district_source_members": len(ctx["district_member_ids"]), "official_whole_municipal_items": len(ctx["official"]),
                            "official_whole_line_items": len(ctx["lines"]), "line_overlay_rows": len(boundary_rows)},
        "families": family_summaries,
        "component_results": components,
        "identity_and_vintage_path": "identity-and-vintage.json",
        "identity_geometry_comparison_path": "identity-geometry-comparisons.json",
        "source_assessment_path": "source-vintage-crs-and-terms-assessment.json",
        "boundary_overlay_path": "boundary-line-overlays.json",
        "non_assertions": {"physical_class": "unknown", "cause": "unknown", "rightful_owner": "unknown", "water_or_ice": "unknown", "approval": "none", "certification": "none", "core_data_changes": "none"},
        "limits": [
            "The four CAOP/IGN direct API items are complete whole features, not whole national datasets.",
            "CAOP2025 collection temporal metadata conflicts with the official product release date; selected CAOP items have no validity date.",
            "IGN administrativeunit polygons have no validity date; two IGN line records have item-level 2022-04-04 / agreed attributes only.",
            "The IGN line record links returned generic CNIG landing pages without item-specific metadata; line items do not establish a bilateral treaty, matching Portuguese line, or legal ownership by themselves.",
            "A full current/official overlap does not identify physical water, historic boundary authority, or old-pipeline cause.",
        ],
    }
    results_bytes = write_json(run_dir / "summary.json", summary)
    receipt = {
        "version": 1, "run_id": run_name,
        "started_at_local": started_at.isoformat(),
        "finished_at_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": f"PYTHONDONTWRITEBYTECODE=1 python3 -B {Path(__file__).relative_to(REPO).as_posix()} {run_name}",
        "exit_code": 0, "producer_commit": summary["producer_commit"],
        "summary_path": f"runs/{run_name}/summary.json", "summary_bytes": len(results_bytes), "summary_sha256": digest(results_bytes),
    }
    write_json(run_dir / "execution-receipt.json", receipt)
    return summary

def run_analysis(run_name: str):
    global ACTIVE_OUTPUTS, ACTIVE_EXPECTED, ACTIVE_RUN, ROOT
    if not re.fullmatch(r"run-[0-9]{2}(?:-r[0-9]+)?", run_name):
        raise ValueError("Use a fresh run-NN or run-NN-rN vintage")
    baseline, _packet = packet_baseline()
    filenames = planned_run_outputs()
    vintage = NewVintage(baseline, OWNED_PATH, run_name, filenames)
    failure_name = run_name + "-failed-" + digest(Path(__file__).read_bytes())[:12]
    scientific_files = [name for name in filenames if name != "execution-receipt.json"]
    failed = NewVintage(baseline, OWNED_PATH, failure_name, scientific_files + ["failure.json"])
    failed_partial = NewVintage(baseline, OWNED_PATH, failure_name + "-partial", ["failure.json"])
    prior_root = ROOT
    previous_outputs, previous_expected, previous_run = ACTIVE_OUTPUTS, ACTIVE_EXPECTED, ACTIVE_RUN
    with tempfile.TemporaryDirectory(prefix="worldatlas-1482-") as scratch:
        ROOT = Path(scratch)
        ACTIVE_OUTPUTS, ACTIVE_EXPECTED, ACTIVE_RUN = {}, set(filenames), run_name
        try:
            result = _run_analysis(run_name)
            if set(ACTIVE_OUTPUTS) != set(filenames):
                raise ValueError("Complete fresh run output inventory mismatch")
            if os.environ.get("WORLDATLAS_FAIL_AFTER_COMPUTE") == run_name:
                ACTIVE_OUTPUTS.pop("execution-receipt.json", None)
                raise RuntimeError("Injected post-computation failure control")
            vintage.publish_bytes(ACTIVE_OUTPUTS)
            return result
        except BaseException as exc:
            failure = {"version": 1, "issue": 1482, "run_id": run_name, "outcome": "failed",
                       "exception": type(exc).__name__, "reason": str(exc),
                       "corrected_runner_sha256": digest(Path(__file__).read_bytes()),
                       "computed_scientific_files": sorted(ACTIVE_OUTPUTS or {})}
            if set(ACTIVE_OUTPUTS or {}) == set(scientific_files):
                failure_bytes = (json.dumps(failure, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
                failed.publish_bytes({**ACTIVE_OUTPUTS, "failure.json": failure_bytes})
            else:
                failed_partial.publish({"failure.json": failure})
            raise
        finally:
            ROOT = prior_root
            ACTIVE_OUTPUTS, ACTIVE_EXPECTED, ACTIVE_RUN = previous_outputs, previous_expected, previous_run

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: run-analysis.py run-01|run-02")
    result = run_analysis(sys.argv[1])
    print(json.dumps({"run": sys.argv[1], "producer_commit": result["producer_commit"], "families": result["families"]}, indent=2))
