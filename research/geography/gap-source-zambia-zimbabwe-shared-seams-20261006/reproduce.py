#!/usr/bin/env python3
"""Reproduce issue #1234's bounded source and physical-water diagnostics.

All inputs are read from the issue's pinned Git baseline and original custody
payloads. Coordinates remain literal GeoJSON longitude/latitude. No geometry
repair, snapping, buffering, simplification, or ownership inference occurs.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import platform
import pathlib
import subprocess
import sys
import argparse

from shapely import STRtree, union_all
from shapely.geometry import box, mapping, shape
import shapely
import pyproj

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from evidence.geometry import land_area_m2, METHOD as AREA_METHOD
from evidence.immutable import Baseline, descriptor, canonical_json, deterministic_gzip, VERSION as PREPARATION_VERSION

ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE = "79ffb2ed04702e16f009e4675a8d74ef9bd09d4f"
OUT = pathlib.Path(__file__).parent
OWNED = "research/geography/gap-source-zambia-zimbabwe-shared-seams-20261006/"
COMPONENT_ROOT = "coordination/engineering/physical-gap-components-1005-20261005-local19/"
IDS = [
    "physical-component:087b8ed59af27e069111ed4388ae84383625b06dcaaf0a250c56b21b38a09412",
    "physical-component:1aaf0bcede4fa05f6a0e04291123eb68a618da7d181659dc81785f58f05ce624",
    "physical-component:339d343f62afdbb94f6352a45d41c17acf0d1df65fed834c1a5e86154f31102f",
    "physical-component:43d1a11315e3668e90ea91331a0857bbbe9d96984b212bf957653e616ee52cd8",
    "physical-component:447b38afd61e5dfa559b901ab149a059a711d9e99af2e204ab5f88ec30552275",
    "physical-component:4e35c8d9131282023f3efb77bc9c166be31ead102344e44e307aa964b66dfdf3",
    "physical-component:87a14332b9a62f4a42282cf8a415c0b94c15091654aa05b1ac293ee2d4758b3f",
    "physical-component:bb6382d696364f0b134a83c89a5fa36a479788538ec07a3696347056b63b7bae",
    "physical-component:e53af7b07bd3f726a90d31048953c13321f872340b2d7ab735d4bd4334faf782",
    "physical-component:ed72aa6057af62a735ca5b0b3ad6cf79f8f8e96ca7ab15b7aa2e4b4d8c981827",
]
SUBJECTS = [
    "gb:ZMB:ADM2:96606910B35256638811207",
    "gb:ZMB:ADM2:96606910B48730551364911",
    "gb:ZMB:ADM2:96606910B70191271227661",
    "gb:ZWE:ADM2:62879985B85730198836463",
]
SOURCE_PATHS = {
    "ZMB": "data/regional-review/regional-review-9203cb61c3883e07/source/geoboundaries/geoBoundaries-ZMB-ADM2_simplified.geojson",
    "ZWE": "data/regional-review/regional-review-9203cb61c3883e07/source/geoboundaries/geoBoundaries-ZWE-ADM2_simplified.geojson",
}
ATLAS_PATH = "data/geography/part-28.json"
CONTACT_PATH = COMPONENT_ROOT + "custody-v1/payloads/4a150385c4b026e55cd2faf756f8a3fc43eddac2d8a58c118c9fbcf8419777df.bin"
WATER_PATH = "coordination/engineering/coverage-gaps-907-20261005-local01/sources/natural-earth-lakes.geojson.gz"
BASELINE = None


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(value) -> bytes:
    return canonical_json(value)


def raw_git_blob(path: str, commit: str = BASE) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def git_blob(path: str) -> bytes:
    if BASELINE is None:
        return raw_git_blob(path)
    return BASELINE.read(path)


def geom_record(g):
    encoded = canon(mapping(g))
    def collect_polygons(geometry):
        if geometry.geom_type == "Polygon":
            return [geometry]
        if geometry.geom_type in ("MultiPolygon", "GeometryCollection"):
            return [part for child in geometry.geoms for part in collect_polygons(child)]
        return []
    polygon_parts = collect_polygons(g)
    area_m2 = None
    area_limit = None
    if polygon_parts:
        try:
            area_m2 = land_area_m2(union_all(polygon_parts))
        except ValueError as error:
            area_limit = str(error)
    return {"geometry": mapping(g), "geometry_sha256": sha(encoded),
            "geometry_type": g.geom_type, "empty": g.is_empty,
            "valid": g.is_valid, "planar_area_degrees_squared": g.area,
            "wgs84_area_m2": area_m2, "area_method_limit": area_limit,
            "planar_length_degrees": g.length}


def load_source(code):
    path = SOURCE_PATHS[code]
    raw = git_blob(path)
    data = json.loads(raw)
    assert data["type"] == "FeatureCollection"
    rows = []
    for index, feature in enumerate(data["features"]):
        props = feature["properties"]
        g = shape(feature["geometry"])
        rows.append({"index": index, "shapeID": props.get("shapeID"),
                     "name": props.get("shapeName"), "geometry": g,
                     "feature_sha256": sha(canon(feature))})
    expected = {
        "ZMB": (3574952, "58e9df3f95bb4c7539e5fb48839b246b2bfb12694cf5db3ed595240156016c60"),
        "ZWE": (1042500, "3486ef2803574e63db97e2a35b6688bb327cb8d6ff5e439691c1cc3068ddb424"),
    }[code]
    assert (len(raw), sha(raw)) == expected
    return {"path": path, "raw": raw, "features": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT))
    out_dir = pathlib.Path(parser.parse_args().output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assert subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", BASE]).decode().strip() == BASE
    index_path = COMPONENT_ROOT + "custody-v1/index.json"
    index = json.loads(raw_git_blob(index_path))
    alias_by_path = {a["original"]["path"]: a for a in index["aliases"]}
    component_payloads = [a["payload"] for name, a in alias_by_path.items()
                          if "/components-v3/components-" in name]
    initial_paths = [
        "data/hierarchy.json", "data/administrative-sources.json",
        "coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json",
        "data/canonical-grid/manifest.json", ATLAS_PATH,
        index_path, CONTACT_PATH, WATER_PATH,
        "scripts/evidence/geometry.py", "scripts/ellipsoidal_area.py",
        *SOURCE_PATHS.values(), *component_payloads,
        *(f"coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/candidates-{shard:03d}.geojson.gz" for shard in range(17)),
    ]
    pins = []
    for path in sorted(set(initial_paths)):
        raw = raw_git_blob(path)
        pin = descriptor(path, raw)
        if raw[:2] == b"\x1f\x8b":
            decoded = gzip.decompress(raw)
            pin.update(uncompressed_bytes=len(decoded), uncompressed_sha256=sha(decoded))
        pins.append(pin)
    global BASELINE
    BASELINE = Baseline(ROOT, BASE, pins)
    assert (platform.python_version(), shapely.__version__, shapely.geos_version_string,
            pyproj.__version__) == ("3.12.14", "2.1.2", "3.13.1", "3.7.2")
    for name in ("scripts/evidence/geometry.py", "scripts/ellipsoidal_area.py"):
        assert pathlib.Path(ROOT / name).read_bytes() == BASELINE.read(name)

    contact_bytes = git_blob(CONTACT_PATH)
    contact_rows = json.loads(gzip.decompress(contact_bytes))
    target_contacts = [r for r in contact_rows if set(r.get("components", [])) & set(IDS)]
    assert len(target_contacts) == 1 and target_contacts[0]["kind"] == "point-only-ambiguous"
    contact_fragment_ids = set(target_contacts[0]["fragments"])

    components = {}
    fragment_ids = set()
    for name, alias in alias_by_path.items():
        if "/components-v3/components-" not in name:
            continue
        compressed = git_blob(alias["payload"])
        assert sha(compressed) == alias["original"]["sha256"]
        rows = json.loads(gzip.decompress(compressed))["features"]
        for f in rows:
            if f["id"] in IDS:
                assert f["id"] not in components
                components[f["id"]] = f
                fragment_ids.update(binding["id"] for binding in f["properties"].get("fragment_bindings", []))
    assert set(components) == set(IDS)
    component_fragment_ids = set(fragment_ids)
    fragment_ids.update(contact_fragment_ids)
    fragments = {}
    fragment_input_receipts = []
    for shard in range(17):
        path = f"coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/candidates-{shard:03d}.geojson.gz"
        compressed = git_blob(path)
        decoded = gzip.decompress(compressed)
        fragment_input_receipts.append({"path": path, "bytes": len(compressed), "sha256": sha(compressed),
                                        "uncompressed_bytes": len(decoded), "uncompressed_sha256": sha(decoded)})
        rows = json.loads(decoded)["features"]
        for f in rows:
            if f["id"] in fragment_ids:
                assert f["id"] not in fragments
                fragments[f["id"]] = f
    assert set(fragments) == fragment_ids

    products = {code: load_source(code) for code in SOURCE_PATHS}
    assert len(products["ZMB"]["features"]) == 116
    assert len(products["ZWE"]["features"]) == 91
    atlas = json.loads(git_blob(ATLAS_PATH))["features"]
    atlas_by_country = {c: [] for c in SOURCE_PATHS}
    atlas_subjects = {}
    for f in atlas:
        subject = f["id"]
        if subject in SUBJECTS:
            atlas_subjects[subject] = f
        if subject.startswith("gb:ZMB:ADM2:"):
            atlas_by_country["ZMB"].append({"id": subject, "geometry": shape(f["geometry"]), "sha256": sha(canon(f))})
        elif subject.startswith("gb:ZWE:ADM2:"):
            atlas_by_country["ZWE"].append({"id": subject, "geometry": shape(f["geometry"]), "sha256": sha(canon(f))})
    assert set(atlas_subjects) == set(SUBJECTS)

    # Local comparison envelope includes all components plus 0.05 degrees on
    # every side. Whole-country sources are indexed; only intersecting features
    # enter the local union. This is not a country-wide accuracy certification.
    bounds = [shape(components[i]["geometry"]).bounds for i in IDS]
    local = box(min(b[0] for b in bounds) - .05, min(b[1] for b in bounds) - .05,
                max(b[2] for b in bounds) + .05, max(b[3] for b in bounds) + .05)
    source_unions = {}
    atlas_unions = {}
    union_receipts = {}
    for code, product in products.items():
        sg = [r["geometry"] for r in product["features"]]
        ag = [r["geometry"] for r in atlas_by_country[code]]
        source_tree, atlas_tree = STRtree(sg), STRtree(ag)
        si = sorted(int(i) for i in source_tree.query(local))
        ai = sorted(int(i) for i in atlas_tree.query(local))
        su = union_all([sg[i] for i in si]).intersection(local)
        au = union_all([ag[i] for i in ai]).intersection(local)
        source_unions[code], atlas_unions[code] = su, au
        union_receipts[code] = {
            "source_product_path": product["path"], "source_product_sha256": sha(product["raw"]),
            "source_feature_count": len(sg), "atlas_feature_count": len(ag),
            "source_bbox_candidate_indices": si,
            "source_bbox_candidate_shapeIDs": [product["features"][i]["shapeID"] for i in si],
            "atlas_bbox_candidate_ids": [atlas_by_country[code][i]["id"] for i in ai],
            "source_local_union": geom_record(su), "atlas_local_union": geom_record(au),
            "source_minus_atlas_local_union": geom_record(su.difference(au)),
            "atlas_minus_source_local_union": geom_record(au.difference(su)),
            "comparison_extent": list(local.bounds),
        }

    component_rows = []
    positive_witnesses = []
    negative_witnesses = []
    for component_id in IDS:
        f = components[component_id]
        g = shape(f["geometry"])
        sources = ["ZMB", "ZWE"]
        candidates = []
        valid_candidates = []
        for code in sources:
            rows = products[code]["features"]
            tree = STRtree([r["geometry"] for r in rows])
            indices = sorted(int(i) for i in tree.query(g))
            for i in indices:
                r = rows[i]
                ix = g.intersection(r["geometry"])
                candidates.append({"country": code, "source_feature_index": i,
                                   "shapeID": r["shapeID"], "name": r["name"],
                                   "source_feature_sha256": r["feature_sha256"],
                                   "covers_entire_component": r["geometry"].covers(g),
                                   "intersection": geom_record(ix),
                                   "positive_area": ix.area > 0})
                valid_candidates.append(r["geometry"])
                if ix.area > 0 and not positive_witnesses:
                    positive_witnesses.append({"component_id": component_id, "country": code,
                                               "source_feature_index": i, "shapeID": r["shapeID"],
                                               "intersection": geom_record(ix)})
        source_union = union_all(valid_candidates)
        intersection = g.intersection(source_union)
        residual = g.difference(source_union)
        local_atlas = union_all([atlas_unions[c] for c in sources])
        source_only = g.intersection(source_union).difference(local_atlas)
        contact = []
        # The original contact input is retained intact below; target rows are
        # joined by exact source component identity without changing the row.
        row = {
            "component_id": component_id,
            "component_feature_sha256": sha(canon(f)),
            "original_component_feature": f,
            "source_feature_intersections": candidates,
            "whole_relevant_source_union": geom_record(source_union),
            "source_union_intersection": geom_record(intersection),
            "component_minus_source_union": geom_record(residual),
            "source_covered_area_missing_from_local_atlas_union": geom_record(source_only),
            "classification": "mixed-evidence-source-intersection-and-outside-source-residual; executed cause and physical water unresolved",
            "water_status": f["properties"].get("water_status", "unverified"),
            "cause_status": "unknown",
            "administrative_assignment": None,
            "coordinate_scope": "literal longitude/latitude; no wrap, transform, snapping, repair, or normalization",
        }
        component_rows.append(row)
        assert intersection.area > 0 and not residual.is_empty

    # Stable source subject identity check: map the four roster IDs to exact
    # source shapeIDs and compare their full retained features to Atlas rows.
    subject_rows = []
    for subject_id in SUBJECTS:
        code, shape_id = subject_id.split(":")[1], subject_id.split(":")[-1]
        source_match = [r for r in products[code]["features"] if r["shapeID"] == shape_id]
        assert len(source_match) == 1
        sf, af = source_match[0], atlas_subjects[subject_id]
        sg, ag = sf["geometry"], shape(af["geometry"])
        subject_rows.append({"subject_id": subject_id, "source_feature_index": sf["index"],
                             "source_feature_sha256": sf["feature_sha256"],
                             "atlas_feature_sha256": sha(canon(af)),
                             "source_shapeID": sf["shapeID"], "source_name": sf["name"],
                             "source_minus_atlas": geom_record(sg.difference(ag)),
                             "atlas_minus_source": geom_record(ag.difference(sg)),
                             "source_intersection": geom_record(sg.intersection(ag)),
                             "source_covers_atlas": sg.covers(ag), "atlas_covers_source": ag.covers(sg)})

    # Negative control: a fixed far-away source feature must not overlap the
    # first issue component. This verifies that the overlay path detects an
    # empty result as well as the positive witness above.
    sentinel = products["ZMB"]["features"][0]
    first_component = shape(components[IDS[0]]["geometry"])
    negative = first_component.intersection(sentinel["geometry"])
    assert negative.is_empty
    negative_witnesses.append({"component_id": IDS[0], "country": "ZMB",
                               "source_feature_index": sentinel["index"],
                               "shapeID": sentinel["shapeID"],
                               "intersection": geom_record(negative), "expected_empty": True})

    assert set(fragments) == component_fragment_ids | contact_fragment_ids

    water_bytes = git_blob(WATER_PATH)
    assert sha(water_bytes) == "a57bd38b23b57d884853c3e8e6da1a4a24c9ca40dd1edb8e9b2de4db70c0656f"
    water_raw = gzip.decompress(water_bytes)
    water = json.loads(water_raw)
    water_features = [shape(f["geometry"]) for f in water["features"]]
    water_tree = STRtree(water_features)
    water_rows = []
    for component_id in IDS:
        g = shape(components[component_id]["geometry"])
        overlaps = []
        for i in sorted(int(i) for i in water_tree.query(g)):
            ix = g.intersection(water_features[i])
            if not ix.is_empty:
                overlaps.append({"lake_index": i, "intersection": geom_record(ix)})
        water_rows.append({"component_id": component_id, "major_lake_reference_overlays": overlaps,
                           "interpretation": "major-lakes-only diagnostic; no evidence of dry land or complete hydrology"})

    result = {
        "version": 1, "issue": 1234, "baseline": BASE,
        "immutable_input_pins": [BASELINE.pins[path] for path in sorted(BASELINE.pins)],
        "producer_versions": {"preparation_helper": PREPARATION_VERSION,
                              "geometry_helper": AREA_METHOD["version"],
                              "python": platform.python_version(), "shapely": shapely.__version__,
                              "geos": shapely.geos_version_string, "pyproj": pyproj.__version__},
        "component_ids": IDS, "subject_ids": SUBJECTS,
        "source_products": {c: {"path": p["path"], "bytes": len(p["raw"]), "sha256": sha(p["raw"]),
                                 "feature_count": len(p["features"])} for c, p in products.items()},
        "registered_subject_comparisons": subject_rows,
        "local_country_union_comparisons": union_receipts,
        "local_comparison_method": "union all whole-product bbox candidates within the issue batch extent expanded by 0.05 degrees; compare source and current Atlas country polygons in that local window",
        "components": component_rows,
        "original_fragment_features": [fragments[i] for i in sorted(component_fragment_ids)],
        "original_contact_fragment_features": [fragments[i] for i in sorted(contact_fragment_ids)],
        "original_fragment_inputs": fragment_input_receipts,
        "controls": {"positive": positive_witnesses, "negative": negative_witnesses,
                     "positive_count": len(positive_witnesses), "negative_count": len(negative_witnesses)},
        "original_source_contacts": {"input_path": CONTACT_PATH, "input_bytes": len(contact_bytes),
                                     "input_sha256": sha(contact_bytes), "matched_rows": target_contacts},
        "independent_water_diagnostics": {"source_path": WATER_PATH, "compressed_sha256": sha(water_bytes),
                                         "decoded_sha256": sha(water_raw), "feature_count": len(water_features),
                                         "components": water_rows},
        "limits": [
            "Source metadata represents boundaryYearRepresented 2020, not a legal effective date or registration accuracy statement.",
            "geoBoundaries contributor and license assertions are preserved from the source registry; underlying rights and survey accuracy were not independently authenticated.",
            "Natural Earth reference covers major lakes and reservoirs only, not complete river networks, small waters, or year-specific hydrology.",
            "Planar areas are reported only in square degrees as operation diagnostics; they are not physical area measurements.",
            "Source intersections, Atlas differences, and major-lake overlays do not assign territorial ownership, resolve seam cause, or justify geometry repair.",
            "Local union comparison uses a bounded expanded window, not whole-country union certification.",
        ],
        "area_helper": AREA_METHOD,
    }
    output_bytes = canon(result)
    output_path = out_dir / "source-geometry-results.json.gz"
    output_path.write_bytes(deterministic_gzip(output_bytes))
    print(json.dumps({"components": len(component_rows), "contacts": len(target_contacts),
                      "source_counts": {c: len(p["features"]) for c, p in products.items()},
                      "output": str(output_path), "decoded_bytes": len(output_bytes),
                      "decoded_sha256": sha(output_bytes)}, sort_keys=True))


if __name__ == "__main__":
    main()
