#!/usr/bin/env python3
"""Reproduce bounded India–Pakistan seam source and geometry comparisons.

Run only after committing this script. All output stays in this owned packet.
The script never edits source geometry, infers ownership, or classifies water.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from collections import defaultdict

from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import unary_union
import shapely
import pyproj

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from evidence import immutable  # noqa: E402
from evidence.geometry import METHOD, land_area_m2, distance_m  # noqa: E402

if immutable.VERSION != "worldatlas-evidence-preparation-v1":
    raise RuntimeError("Unsupported immutable evidence preparation helper")

SOURCE_COMMIT = "9469f09592ced973a3448cf66b6100b741b64c0d"
BASELINE_COMMIT = "c603befd3aaf4da90d59b12378e1e0739331efba"
SUBJECTS = {
    "atlas:local:IND:7132399B1507487316620": ("ind-adm3-simplified", "7132399B1507487316620"),
    "atlas:local:IND:7132399B19493089186258": ("ind-adm3-simplified", "7132399B19493089186258"),
    "atlas:local:IND:7132399B23352295489123": ("ind-adm3-simplified", "7132399B23352295489123"),
    "atlas:local:IND:7132399B25679382819073": ("ind-adm3-simplified", "7132399B25679382819073"),
    "atlas:local:IND:7132399B27106528401514": ("ind-adm3-simplified", "7132399B27106528401514"),
    "atlas:local:IND:7132399B38242062299143": ("ind-adm3-simplified", "7132399B38242062299143"),
    "atlas:local:IND:7132399B49490689811564": ("ind-adm3-simplified", "7132399B49490689811564"),
    "atlas:local:IND:7132399B516102083904": ("ind-adm3-simplified", "7132399B516102083904"),
    "atlas:local:IND:7132399B78390472834442": ("ind-adm3-simplified", "7132399B78390472834442"),
    "atlas:local:IND:7132399B91194549462935": ("ind-adm3-simplified", "7132399B91194549462935"),
    "gb:IND:ADM2:76128533B7291413308870": ("ind-adm2", "76128533B7291413308870"),
    "gb:PAK:ADM2:60131773B1682888309057": ("pak-adm2", "60131773B1682888309057"),
    "gb:PAK:ADM2:60131773B44072502651200": ("pak-adm2", "60131773B44072502651200"),
    "gb:PAK:ADM2:60131773B44161758981040": ("pak-adm2", "60131773B44161758981040"),
    "gb:PAK:ADM2:60131773B62209958986210": ("pak-adm2", "60131773B62209958986210"),
    "gb:PAK:ADM2:60131773B87869837926518": ("pak-adm2", "60131773B87869837926518"),
}
FRAGMENTS = {
    "physical-gap:1274:1:bc2dfd4d6bfe071a9bea0d15adc0e4cc62e9962f2c6418395802962a579cade1": "370a3a380760f6dd02c5c588e69385d65b3afd4cd9703cbc578596989302a730",
    "physical-gap:1346:2:eb4771cfae78b61aea03e2285006660025febfe0051a97abc63e812e210bd64f": "d16ac5ffccab3c818261a7835797831b87a1fba5115332a651eda7eb9c54c273",
}
SOURCE_FILES = {
    "ind-adm3-simplified": "geoBoundaries-IND-ADM3_simplified.geojson",
    "ind-adm2": "geoBoundaries-IND-ADM2.geojson",
    "pak-adm2": "geoBoundaries-PAK-ADM2.geojson",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable(obj) -> bytes:
    return immutable.canonical_json(obj)


def fragment_sha(feature) -> str:
    # This is the established detector's full-feature digest convention.
    return hashlib.sha256((json.dumps(feature, ensure_ascii=False, sort_keys=False,
                                      separators=(",", ":")) + "\n").encode()).hexdigest()


def verify_fragment(feature, expected):
    actual = fragment_sha(feature)
    if actual != expected:
        raise ValueError(f"full fragment identity mismatch: expected {expected}, got {actual}")


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable(obj))


def load_original_sources():
    packet_sources = PACKET / "sources"
    custody = json.loads((packet_sources / "source-custody.json").read_text())
    original_dir = PACKET / ".cache" / "geo4-sources"
    objects = {}
    for key, filename in SOURCE_FILES.items():
        raw = (original_dir / filename).read_bytes()
        record = next(x for x in custody["sources"] if x["id"] == {
            "ind-adm3-simplified": "gb:IND:ADM3:simplified:2018",
            "ind-adm2": "gb:IND:ADM2:2021", "pak-adm2": "gb:PAK:ADM2:2019"}[key])
        if len(raw) != record["bytes"] or sha(raw) != record["sha256"]:
            raise ValueError(f"whole original source custody mismatch: {key}")
        parts = sorted((packet_sources / "original-byte-parts").glob(f"{key}-*.source-bytes"))
        restored = b"".join(p.read_bytes() for p in parts)
        if restored != raw:
            raise ValueError(f"lossless source partition restoration mismatch: {key}")
        collection = json.loads(raw)
        by_id = {}
        for feature in collection["features"]:
            sid = feature.get("properties", {}).get("shapeID")
            if sid in by_id:
                raise ValueError(f"nonunique original shapeID in {key}: {sid}")
            by_id[sid] = feature
        objects[key] = {"raw": raw, "features": by_id, "feature_count": len(collection["features"]), "custody": record}
    return objects


def restore_gap_envelope():
    base = ROOT / "coordination/engineering/physical-gap-audit-1005-20261005-local18"
    env = base / "input-envelope-v1"
    manifest = json.loads((env / "manifest.json").read_text())
    restored_root = PACKET / ".cache" / "restored-input-envelope"
    receipts = []
    for entry in manifest["entries"]:
        encoded_path = ROOT / entry["encoded"]["path"]
        encoded = encoded_path.read_bytes()
        if len(encoded) != entry["encoded"]["bytes"] or sha(encoded) != entry["encoded"]["sha256"]:
            raise ValueError(f"encoded original envelope hash mismatch: {entry['encoded']['path']}")
        original = gzip.decompress(encoded)
        if len(original) != entry["original"]["bytes"] or sha(original) != entry["original"]["sha256"]:
            raise ValueError(f"decoded original envelope hash mismatch: {entry['original']['path']}")
        dest = restored_root / entry["original"]["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(original)
        receipts.append({"encoded": entry["encoded"], "original": entry["original"],
                         "source_commit": entry["source_commit"], "restored_path": str(dest.relative_to(PACKET))})
    write_json(PACKET / "inputs" / "original-input-envelope-readback.json",
               {"status": "complete", "manifest_sha256": sha((env / "manifest.json").read_bytes()),
                "entry_count": len(receipts), "entries": receipts})
    report_path = base / "detection-v4" / "report.json"
    report = json.loads(report_path.read_text())
    if sha(report_path.read_bytes()) != "230a49dbb3feab482d2946a7a4c75b9b8069acd841fc2609f2251cf6d2d58330":
        raise ValueError("pinned physical-gap report hash changed")
    shard = base / "detection-v4" / "candidates-008.geojson.gz"
    if sha(shard.read_bytes()) != "20ecf84ad85b3fb74514e4633c5b0c0d94d59b20e0a4ef2829348fb1e9f75f77":
        raise ValueError("pinned physical-gap candidate shard hash changed")
    candidates = json.loads(gzip.decompress(shard.read_bytes()))["features"]
    found = {}
    for f in candidates:
        fid = f.get("id")
        if fid in FRAGMENTS:
            verify_fragment(f, FRAGMENTS[fid])
            found[fid] = f
    if set(found) != set(FRAGMENTS):
        raise ValueError("the two issue-pinned complete fragments were not both restored")
    for fid, feature in found.items():
        write_json(PACKET / "sources" / "physical-gap-fragments" / (fid.split(":")[1] + "-" + fid.split(":")[2] + ".geojson"), feature)
    return report, found


def geometry_of(feature):
    return shape(feature["geometry"])


def flatten_components(geom):
    if geom.geom_type == "GeometryCollection" or geom.geom_type.startswith("Multi"):
        for child in geom.geoms:
            yield from flatten_components(child)
    else:
        yield geom


def measure_area(geom, errors, label, component_ledger):
    if geom is None:
        component_ledger.append({"operation": label, "kind": "failed-operation-result"})
        return None
    if geom.is_empty:
        component_ledger.append({"operation": label, "kind": "empty", "geometry_type": geom.geom_type})
        return 0.0
    components = list(flatten_components(geom))
    polygons = [part for part in components if part.geom_type == "Polygon"]
    nonpolygons = [part for part in components if part.geom_type != "Polygon"]
    for part in polygons:
        encoded = stable(mapping(part))
        try:
            component_area = land_area_m2(part)
            component_ledger.append({"operation": label, "kind": "polygon-component",
                                     "geometry_type": part.geom_type, "area_m2": component_area,
                                     "geometry_sha256": sha(encoded), "geometry": mapping(part)})
        except Exception as exc:
            errors.append({"operation": label, "geometry_type": part.geom_type,
                           "error_type": type(exc).__name__, "error": str(exc)})
            component_ledger.append({"operation": label, "kind": "failed-polygon-component",
                                     "geometry_type": part.geom_type, "geometry_sha256": sha(encoded),
                                     "geometry": mapping(part), "error": str(exc)})
    for part in nonpolygons:
        encoded = stable(mapping(part))
        component_ledger.append({"operation": label, "kind": "nonpolygon-remnant",
                                 "geometry_type": part.geom_type, "geometry_sha256": sha(encoded),
                                 "geometry": mapping(part)})
    if not polygons:
        return 0.0
    try:
        # GeometryCollections from overlays may contain area-bearing polygons
        # and coincident line remnants. Measure the union of polygon members
        # while retaining every original component and line in the ledger.
        polygon_union = unary_union(polygons) if geom.geom_type == "GeometryCollection" else geom
        return land_area_m2(polygon_union)
    except Exception as exc:
        errors.append({"operation": label, "geometry_type": geom.geom_type,
                       "error_type": type(exc).__name__, "error": str(exc)})
        return None


def safe_overlay(left, right, operation, errors, label):
    try:
        return getattr(left, operation)(right)
    except Exception as exc:
        errors.append({"operation": label, "geometry_type": left.geom_type,
                       "error_type": type(exc).__name__, "error": str(exc),
                       "status": "failed; result unknown"})
        return None


def atlas_index():
    index = {}
    parts = []
    for path in sorted((ROOT / "data/geography").glob("part-*.json")):
        if path.name.startswith("part-0") and path.name not in {f"part-{i}.json" for i in range(10)}:
            continue
        doc = json.loads(path.read_text())
        parts.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())})
        for feature in doc["features"]:
            p = feature.get("properties", {})
            meta = p.get("metadata", {})
            if p.get("id"):
                index.setdefault(p["id"], []).append((feature, path))
            if meta.get("original_id"):
                index.setdefault(meta["original_id"], []).append((feature, path))
            for source_id in meta.get("source_member_ids", []):
                index.setdefault(source_id, []).append((feature, path))
    return index, parts


def geodesic_line_length(geom):
    if geom.is_empty:
        return 0.0
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        return sum(distance_m(a[:2], b[:2]) for a, b in zip(coords, coords[1:]))
    if geom.geom_type == "MultiLineString" or geom.geom_type == "GeometryCollection":
        return sum(geodesic_line_length(g) for g in geom.geoms)
    return 0.0


def run_geometry_controls():
    ledger, failures = [], []
    shell = Polygon([(73, 28), (73.01, 28), (73.01, 28.01), (73, 28.01), (73, 28)])
    hole = Polygon([(73, 28), (73.01, 28), (73.01, 28.01), (73, 28.01), (73, 28)],
                   [[(73.002, 28.002), (73.008, 28.002), (73.008, 28.008), (73.002, 28.008), (73.002, 28.002)]])
    second = Polygon([(73.02, 28), (73.021, 28), (73.021, 28.001), (73.02, 28.001), (73.02, 28)])
    tiny = Polygon([(73, 28), (73.000001, 28), (73.000001, 28.000001), (73, 28.000001), (73, 28)])
    line = LineString([(73.03, 28), (73.031, 28)])
    point = Point(73.04, 28)
    geom_collection = GeometryCollection([shell, line, point])
    multi = MultiPolygon([shell, second])
    invalid = Polygon([(73, 28), (73.01, 28.01), (73, 28.01), (73.01, 28), (73, 28)])

    gc_area = measure_area(geom_collection, failures, "control:geometry-collection", ledger)
    shell_area = land_area_m2(shell)
    multi_area = measure_area(multi, failures, "control:disconnected-multipolygon", ledger)
    expected_multi = land_area_m2(shell) + land_area_m2(second)
    hole_area = measure_area(hole, failures, "control:polygon-hole", ledger)
    line_area = measure_area(line, failures, "control:line-zero-area", ledger)
    point_area = measure_area(point, failures, "control:point-zero-area", ledger)
    tiny_area = measure_area(tiny, failures, "control:tiny-positive-polygon", ledger)
    invalid_area = measure_area(invalid, failures, "control:invalid-polygon", ledger)
    tiny_length = geodesic_line_length(line)
    expected_length = distance_m((73.03, 28), (73.031, 28))
    remnant_types = sorted({entry["geometry_type"] for entry in ledger if entry["kind"] == "nonpolygon-remnant"})
    checks = {
        "geometry_collection_retains_polygon_and_measures_its_positive_area": gc_area is not None and gc_area > 0 and abs(gc_area - shell_area) <= shell_area * 1e-12,
        "geometry_collection_retains_line_and_point_remnants": "LineString" in remnant_types and "Point" in remnant_types,
        "disconnected_multipolygon_measures_both_components": multi_area is not None and abs(multi_area - expected_multi) <= expected_multi * 1e-12,
        "polygon_hole_reduces_area_without_repair": hole_area is not None and 0 < hole_area < shell_area,
        "true_line_and_point_have_zero_area_and_are_retained": line_area == 0 and point_area == 0 and remnant_types.count("LineString") >= 1 and remnant_types.count("Point") >= 1,
        "tiny_positive_polygon_is_not_cut_off": tiny_area is not None and tiny_area > 0,
        "invalid_polygon_is_explicit_unknown_not_zero": invalid_area is None and any(e["operation"] == "control:invalid-polygon" for e in failures),
        "line_length_uses_wgs84_inverse_geodesic": abs(tiny_length - expected_length) <= expected_length * 1e-12,
    }
    if not all(checks.values()):
        raise ValueError(f"analytic geometry control failed: {checks}; failures={failures}")
    positive_names = {"geometry_collection_retains_polygon_and_measures_its_positive_area",
                      "disconnected_multipolygon_measures_both_components", "polygon_hole_reduces_area_without_repair",
                      "tiny_positive_polygon_is_not_cut_off", "line_length_uses_wgs84_inverse_geodesic"}
    negative_names = {"geometry_collection_retains_line_and_point_remnants",
                      "true_line_and_point_have_zero_area_and_are_retained",
                      "invalid_polygon_is_explicit_unknown_not_zero"}
    write_json(PACKET / "geometry-positive-control.json", {
        "method_id": "seam-geometry-measurement", "kind": "positive-control", "outcome": "passed",
        "checks": {name: value for name, value in checks.items() if name in positive_names},
        "geometry_controls_sha256": sha(stable({"checks": checks, "measured": {"shell_area_m2": shell_area,
            "geometry_collection_area_m2": gc_area, "multipolygon_area_m2": multi_area,
            "hole_area_m2": hole_area, "tiny_polygon_area_m2": tiny_area, "line_length_m": tiny_length}}))})
    write_json(PACKET / "geometry-negative-control.json", {
        "method_id": "seam-geometry-measurement", "kind": "negative-control", "outcome": "passed",
        "checks": {name: value for name, value in checks.items() if name in negative_names},
        "expected_invalid_geometry_errors": failures})
    receipt = {"method_id": "seam-geometry-measurement", "kind": "geography", "outcome": "passed",
               "schema": "geo4-shared-seam-geometry-controls-v1", "status": "passed",
               "method": METHOD, "checks": checks,
               "measured": {"shell_area_m2": shell_area, "geometry_collection_area_m2": gc_area,
                            "disconnected_multipolygon_area_m2": multi_area,
                            "disconnected_component_sum_m2": expected_multi,
                            "hole_polygon_area_m2": hole_area, "line_area_m2": line_area,
                            "point_area_m2": point_area, "tiny_polygon_area_m2": tiny_area,
                            "line_length_m": tiny_length, "line_inverse_geodesic_m": expected_length,
                            "invalid_polygon_area": invalid_area},
               "retained_component_ledger_sha256": sha(stable(ledger)),
               "expected_invalid_geometry_errors": failures}
    write_json(PACKET / "geometry-controls.json", receipt)
    return receipt


def compare(geometry_controls):
    originals = load_original_sources()
    report, gaps = restore_gap_envelope()
    atlas, current_part_receipts = atlas_index()
    crosswalk, comparison_rows = [], []
    source_by_subject = {}
    current_by_subject = {}
    failures = []
    component_ledger = []
    for subject, (source_key, shape_id) in SUBJECTS.items():
        source_record = originals[source_key]
        original = source_record["features"].get(shape_id)
        matches = atlas.get(shape_id, [])
        # PAK/ADM2 appears in source_member_ids. IND ADM3 local IDs match shapeID.
        target_matches = [m for m in matches if m[0].get("properties", {}).get("id") == subject]
        if source_key == "ind-adm3-simplified" and not target_matches:
            target_matches = [(f, p) for f, p in atlas.get(shape_id, []) if f.get("properties", {}).get("id") == subject]
        if original is None or len(target_matches) != 1:
            failures.append({"subject_id": subject, "original_member_found": original is not None,
                             "matching_atlas_features": len(target_matches)})
            continue
        current, current_path = target_matches[0]
        source_by_subject[subject] = original
        current_by_subject[subject] = current
        original_digest, atlas_digest = sha(stable(original)), sha(stable(current))
        original_geom, current_geom = geometry_of(original), geometry_of(current)
        overlay = safe_overlay(original_geom, current_geom, "intersection", failures, subject + ":source-current-intersection")
        union = safe_overlay(original_geom, current_geom, "union", failures, subject + ":source-current-union")
        inter_area = measure_area(overlay, failures, subject + ":source-current-intersection", component_ledger)
        union_area = measure_area(union, failures, subject + ":source-current-union", component_ledger)
        symmetric = safe_overlay(original_geom, current_geom, "symmetric_difference", failures, subject + ":symmetric-difference")
        symmetric_area = measure_area(symmetric, failures, subject + ":symmetric-difference", component_ledger)
        a_area = measure_area(original_geom, failures, subject + ":original-source-area", component_ledger)
        b_area = measure_area(current_geom, failures, subject + ":current-atlas-area", component_ledger)
        props = current.get("properties", {})
        metadata = props.get("metadata", {})
        crosswalk.append({"subject_id": subject, "source_layer": source_key, "shapeID": shape_id,
                          "shapeName": original.get("properties", {}).get("shapeName"),
                          "source_type": original.get("properties", {}).get("shapeType"),
                          "source_feature_sha256_canonical_json": original_digest,
                          "atlas_feature_id": props.get("id"), "atlas_source_member_ids": metadata.get("source_member_ids", []),
                          "atlas_original_id": metadata.get("original_id"),
                          "atlas_source_geography_sha256": metadata.get("source_geography_sha256"),
                          "atlas_feature_sha256_canonical_json": atlas_digest,
                          "atlas_feature_path": str(current_path.relative_to(ROOT)),
                          "atlas_feature_part_sha256": sha(current_path.read_bytes())})
        comparison_rows.append({"subject_id": subject, "source_layer": source_key,
                                "original_source_member_area_m2": a_area, "current_atlas_area_m2": b_area,
                                "positive_overlap_area_m2": inter_area,
                                "positive_overlap_share_of_source": inter_area / a_area if inter_area is not None and a_area else None,
                                "positive_overlap_share_of_atlas": inter_area / b_area if inter_area is not None and b_area else None,
                                "union_area_m2": union_area, "symmetric_difference_area_m2": symmetric_area,
                                "source_minus_atlas_area_m2": a_area - inter_area if a_area is not None and inter_area is not None else None,
                                "atlas_minus_source_area_m2": b_area - inter_area if b_area is not None and inter_area is not None else None,
                                "method": METHOD, "overlay_status": "measured-with-errors" if failures else "measured"})
        write_json(PACKET / "sources" / "original-features" / f"{shape_id}.geojson", original)
        write_json(PACKET / "sources" / "current-features" / f"{shape_id}.geojson", current)

    if failures or len(crosswalk) != 16:
        raise ValueError(f"subject membership/crosswalk incomplete: {failures}")
    source_layers = []
    for key, obj in originals.items():
        cust = obj["custody"]
        metadata_record = next(m for m in json.loads((PACKET / "sources/source-custody.json").read_text())["metadata_files"]
                              if m["metadata"].get("boundaryISO") == cust["country"]
                              and m["metadata"].get("boundaryType") == cust["tier"])
        metadata = metadata_record["metadata"]
        source_layers.append({"source_id": cust["id"], "upstream_path": cust["upstream_path"],
                              "country": cust["country"], "administrative_tier": cust["tier"],
                              "boundary_year": cust["boundary_year"], "native_feature_count": obj["feature_count"],
                              "metadata_declared_admUnitCount": metadata.get("admUnitCount"),
                              "source_data_update_date": metadata.get("sourceDataUpdateDate"),
                              "source_build_date": metadata.get("buildDate"),
                              "source_name": metadata.get("boundarySource"),
                              "license": metadata.get("boundaryLicense"),
                              "whole_original_encoded_bytes": cust["encoded_bytes"],
                              "whole_original_decoded_bytes": cust["decoded_bytes"],
                              "source_content_encoding": cust["source_content_encoding"],
                              "whole_original_sha256": cust["sha256"]})
    write_json(PACKET / "source-crosswalk.json", {"source_commit": SOURCE_COMMIT,
               "atlas_baseline_commit": BASELINE_COMMIT, "subjects": crosswalk,
               "source_layers": source_layers,
               "counts": {"requested": 16, "matched_original_members": len(crosswalk), "matched_atlas_features": len(comparison_rows)}})

    # Preserve and measure complete original gap fragments against the 16 named
    # source/current features. Contact lengths use geodesic segments; areas use
    # the shared, pinned WGS84 straight-source-edge method.
    seam_rows = []
    all_geoms = {s: geometry_of(f) for s, f in source_by_subject.items()}
    all_current_geoms = {s: geometry_of(f) for s, f in current_by_subject.items()}
    for fid, fragment in gaps.items():
        g = geometry_of(fragment)
        p = fragment.get("properties", {})
        source_contacts, current_contacts, intersections = [], [], []
        for sid, subj_geom in all_geoms.items():
            shared = safe_overlay(g.boundary, subj_geom.boundary, "intersection", failures, fid + ":" + sid + ":source-contact")
            if shared is None:
                continue
            length = geodesic_line_length(shared)
            if length > 0:
                source_contacts.append({"subject_id": sid, "shared_boundary_m": length,
                                        "shared_boundary_geometry": mapping(shared)})
            overlap = safe_overlay(g, subj_geom, "intersection", failures, fid + ":" + sid + ":source-intersection")
            if overlap is None:
                continue
            if not overlap.is_empty:
                ar = measure_area(overlap, failures, fid + ":" + sid + ":fragment-intersection", component_ledger)
                if ar is not None and ar > 0:
                    intersections.append({"subject_id": sid, "positive_area_intersection_m2": ar})
        for sid, subj_geom in all_current_geoms.items():
            shared = safe_overlay(g.boundary, subj_geom.boundary, "intersection", failures, fid + ":" + sid + ":atlas-contact")
            if shared is None:
                continue
            length = geodesic_line_length(shared)
            if length > 0:
                current_contacts.append({"subject_id": sid, "shared_boundary_m": length,
                                         "shared_boundary_geometry": mapping(shared)})
        fragment_area = measure_area(g, failures, fid + ":fragment-area", component_ledger)
        seam_rows.append({"fragment_id": fid, "full_feature_sha256": FRAGMENTS[fid],
                          "fragment_area_m2": fragment_area, "source_contacts": source_contacts,
                          "current_atlas_contacts": current_contacts, "positive_area_intersections": intersections,
                          "administrative_assignment": p.get("administrative_assignment"),
                          "water_status": p.get("water_status"), "water_diagnostics": p.get("water_diagnostics"),
                          "method": METHOD})
    combined = unary_union([geometry_of(x) for x in gaps.values()])
    combined_area = measure_area(combined, failures, "combined-fragment-area", component_ledger)
    seam = {"status": "complete-with-unresolved-surface-and-affiliation", "fragment_count": len(seam_rows),
            "fragments": seam_rows, "combined_fragment_area_m2": combined_area,
            "source_subject_comparisons": comparison_rows,
            "source_contact_count": sum(len(x["source_contacts"]) for x in seam_rows),
            "atlas_contact_count": sum(len(x["current_atlas_contacts"]) for x in seam_rows),
            "retained_zero_contacts": True, "retained_positive_tiny_intersections": True,
            "water_interpretation": "unknown; Natural Earth lake reference is incomplete and not year-specific",
            "boundary_affiliation": "unknown; no sovereign or administrative assignment inferred",
            "method": METHOD, "measurement_errors": failures}
    write_json(PACKET / "comparisons" / "original-vs-current.json", seam)
    tamper_rejected = False
    sample_id = next(iter(FRAGMENTS))
    tampered = json.loads(json.dumps(gaps[sample_id]))
    tampered["properties"]["water_status"] = "tampered-control"
    try:
        verify_fragment(tampered, FRAGMENTS[sample_id])
    except ValueError:
        tamper_rejected = True
    controls = {
        "positive": {"all_16_original_members_uniquely_found": len(crosswalk) == 16,
                     "all_16_atlas_features_uniquely_crosswalked": len(comparison_rows) == 16,
                     "both_full_fragments_identity_verified": len(seam_rows) == 2,
                     "original_and_current_geometry_intersections_computed": len(comparison_rows) == 16},
        "negative": {"nonexistent_member_absent": "GEO4-NEGATIVE-NONEXISTENT-SHAPE-ID" not in originals["ind-adm3-simplified"]["features"],
                     "tampered_fragment_digest_rejected_by_exact_expected_digest": tamper_rejected,
                     "no_owner_or_water_label_generated": all(x["administrative_assignment"] is None and x["water_status"] == "unverified" for x in seam_rows)},
        "geometry_controls_sha256": sha((PACKET / "geometry-controls.json").read_bytes()),
        "status": "passed"}
    if not all(controls["positive"].values()) or not all(controls["negative"].values()):
        raise ValueError("one or more scientific positive/negative controls failed")
    source_controls = {"method_id": "seam-source-crosswalk", "kind": "source", "outcome": "passed",
                       "positive": controls["positive"], "negative": controls["negative"],
                       "source_crosswalk_sha256": sha((PACKET / "source-crosswalk.json").read_bytes()),
                       "gap_readback_sha256": sha((PACKET / "inputs/original-input-envelope-readback.json").read_bytes()),
                       "fragment_identities": FRAGMENTS}
    write_json(PACKET / "source-controls.json", source_controls)
    write_json(PACKET / "source-positive-control.json", {
        "method_id": "seam-source-crosswalk", "kind": "positive-control", "outcome": "passed",
        "checks": controls["positive"], "source_crosswalk_sha256": source_controls["source_crosswalk_sha256"]})
    write_json(PACKET / "source-negative-control.json", {
        "method_id": "seam-source-crosswalk", "kind": "negative-control", "outcome": "passed",
        "checks": controls["negative"], "source_controls_sha256": sha(stable(source_controls))})
    write_json(PACKET / "generator-positive-control.json", {
        "method_id": "seam-evidence-generator", "kind": "positive-control", "outcome": "passed",
        "complete_subject_count": len(crosswalk), "full_fragment_count": len(seam_rows),
        "source_controls_sha256": sha(stable(source_controls))})
    write_json(PACKET / "generator-negative-control.json", {
        "method_id": "seam-evidence-generator", "kind": "negative-control", "outcome": "passed",
        "tampered_fragment_rejected": controls["negative"]["tampered_fragment_digest_rejected_by_exact_expected_digest"],
        "invalid_geometry_remains_unknown": json.loads((PACKET / "geometry-controls.json").read_text())[
            "checks"]["invalid_polygon_is_explicit_unknown_not_zero"]})
    write_json(PACKET / "controls.json", controls)
    return seam, crosswalk, comparison_rows, current_part_receipts, component_ledger


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"--run-final", "--verify-two-run"}:
        raise SystemExit("usage: reproduce.py --run-final | --verify-two-run")
    head = os.popen("git rev-parse HEAD").read().strip()
    tracked_dirty = os.popen("git status --porcelain --untracked-files=no").read().strip()
    if tracked_dirty:
        raise SystemExit("refusing final numerical run with tracked changes after code commit")
    if sys.argv[1] == "--verify-two-run":
        run_one = (PACKET / "runs/run-1.json").read_bytes()
        run_two = (PACKET / "runs/run-2.json").read_bytes()
        one, two = json.loads(run_one), json.loads(run_two)
        if run_one != run_two or one != two or one.get("actual_execution_sha") != head:
            raise SystemExit("two-run byte/field/execution-commit reproducibility check failed")
        write_json(PACKET / "two-run-reproducibility.json", {
            "method_id": "seam-evidence-generator", "kind": "reproducibility", "outcome": "passed",
            "schema": "geo4-two-run-reproducibility-v1", "actual_execution_sha": head,
            "run_one_sha256": sha(run_one), "run_two_sha256": sha(run_two),
            "complete_file_bytes_equal": True, "all_fields_equal": True,
            "run_one_bytes": len(run_one), "run_two_bytes": len(run_two),
            "reproduction_code_sha256": one["reproduction_code_sha256"],
        })
        return
    geometry_controls = run_geometry_controls()
    seam, crosswalk, rows, parts, component_ledger = compare(geometry_controls)
    code_hash = sha(Path(__file__).read_bytes())
    code_inputs = []
    for rel in ("research/geography/shared-seam-ind-pak-20261006/reproduce.py",
                "scripts/evidence/geometry.py", "scripts/evidence/immutable.py", "scripts/ellipsoidal_area.py"):
        raw = (ROOT / rel).read_bytes()
        code_inputs.append({"path": rel, "bytes": len(raw), "sha256": sha(raw)})
    pinned_inputs = {}
    for rel in ("data/world-index.json", "data/hierarchy.json", "data/canonical-grid/manifest.json"):
        raw = (ROOT / rel).read_bytes()
        pinned_inputs[rel] = {"bytes": len(raw), "sha256": sha(raw)}
    # Only run_id and actual_execution_sha are allowed to vary between runs.
    result = {"schema": "geo4-shared-seam-final-run-v1",
              "actual_execution_sha": head, "reproduction_code_sha256": code_hash,
              "exact_code_inputs": code_inputs, "pinned_atlas_inputs": pinned_inputs,
              "source_commit": SOURCE_COMMIT, "atlas_baseline_commit": BASELINE_COMMIT,
              "subject_count": len(crosswalk), "fragment_count": len(seam["fragments"]),
              "software": {"python": sys.version.split()[0], "shapely": shapely.__version__, "pyproj": pyproj.__version__},
              "geometry_method": METHOD, "comparisons": rows,
              "seam": seam, "geometry_component_ledger": component_ledger,
              "validation_evidence": {
                  "aggregate_controls_sha256": sha((PACKET / "controls.json").read_bytes()),
                  "geometry_controls_sha256": sha((PACKET / "geometry-controls.json").read_bytes()),
                  "source_controls_sha256": sha((PACKET / "source-controls.json").read_bytes()),
                  "geometry_positive_control_sha256": sha((PACKET / "geometry-positive-control.json").read_bytes()),
                  "geometry_negative_control_sha256": sha((PACKET / "geometry-negative-control.json").read_bytes()),
                  "source_positive_control_sha256": sha((PACKET / "source-positive-control.json").read_bytes()),
                  "source_negative_control_sha256": sha((PACKET / "source-negative-control.json").read_bytes()),
                  "generator_positive_control_sha256": sha((PACKET / "generator-positive-control.json").read_bytes()),
                  "generator_negative_control_sha256": sha((PACKET / "generator-negative-control.json").read_bytes())},
              "current_source_parts": parts,
              "inputs": {"original_source_custody_sha256": sha((PACKET / "sources/source-custody.json").read_bytes()),
                         "gap_readback_sha256": sha((PACKET / "inputs/original-input-envelope-readback.json").read_bytes())}}
    run_label = os.environ.get("GEO4_RUN_ID", "run-1")
    if run_label not in {"run-1", "run-2"}:
        raise SystemExit("GEO4_RUN_ID must be run-1 or run-2")
    write_json(PACKET / "runs" / f"{run_label}.json", result)


if __name__ == "__main__":
    main()
