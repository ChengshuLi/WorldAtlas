#!/usr/bin/env python3
"""Reproduce issue #786's bounded source/summary consistency receipt."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent.relative_to(ROOT).as_posix() + "/"
VINTAGE = "20261004-reviewed-2"
MANIFEST_PATH = ROOT / OWNED / "evidence-quality.json"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / OWNED))

from evidence.immutable import Baseline, canonical_json, sha256, write_new_vintage
from evidence.geometry import METHOD, land_area_m2, transform_point
import shapefile
from pyproj import Transformer
from shapely.geometry import Polygon, shape, mapping
from shapely.ops import transform

EXPECTED_CONTEXTS = ("Tristan vicinity", "Gough vicinity", "Bouvet vicinity")
SUBJECTS = {
    "SHN-4865": {"iso_3166_2": "SH-TA", "source_id": "SHN-4865"},
    "atlas:coverage:BVT+00?": {"iso_3166_2": "NO-X01~", "source_id": "BVT+00?"},
}
OLD_PIN = "7a5940df57e7fe521e7714f195385f3eb6901a71e0102b43b571d5fa90ddeee"
OLD_AUDIT_COMMIT = "c32de3f062369494cabe455e36556db258977cd4"


def canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def pinned_baseline(manifest):
    return Baseline(ROOT, manifest["baseline"]["commit"], manifest["baseline"]["files"])


def require(ok, message):
    if not ok:
        raise ValueError(message)


def derive_contexts(inventory):
    records = inventory.get("records")
    require(isinstance(records, list), "records must be an array")
    require(inventory.get("record_count") == len(records), "declared record total disagrees with rows")
    ids = [row.get("gshhg_id") for row in records]
    require(all(isinstance(value, str) and value for value in ids), "every row needs a source ID")
    require(len(ids) == len(set(ids)), "duplicate source IDs")
    contexts = [row.get("context") for row in records]
    require(all(value in EXPECTED_CONTEXTS for value in contexts), "missing or unexpected context")
    counts = collections.Counter(contexts)
    require(tuple(sorted(counts)) == tuple(sorted(EXPECTED_CONTEXTS)), "missing context category")
    return {"record_count": len(records), "unique_id_count": len(set(ids)),
            "context_counts": {name: counts[name] for name in EXPECTED_CONTEXTS}}


def hierarchy_chain(subject_id, feature, hierarchy):
    rows = {row["id"]: row for row in hierarchy}
    chain = [{"id": subject_id, "name": feature["properties"].get("name"),
              "level": "location", "parent_id": feature["properties"].get("parent_id")}]
    parent = feature["properties"].get("parent_id")
    seen = {subject_id}
    while parent:
        require(parent not in seen and parent in rows, f"missing or cyclic parent for {subject_id}: {parent}")
        row = rows[parent]
        chain.append({"id": row["id"], "name": row.get("name"), "level": row.get("level"),
                      "parent_id": row.get("parent_id")})
        seen.add(parent)
        parent = row.get("parent_id")
    require([row["level"] for row in chain] == ["location", "province", "area", "region", "subcontinent", "continent"],
            f"unexpected six-tier parent chain for {subject_id}")
    return chain


def find_region_members(value, region_id):
    found = []
    def walk(node):
        if isinstance(node, dict):
            if node.get("id") == region_id and isinstance(node.get("member_location_ids"), list):
                found.append(node["member_location_ids"])
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)
    require(len(found) == 1, "expected one current frozen-region membership row")
    return found[0]


def coordinate_count(geometry):
    def count(value):
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
                return 1
            return sum(count(child) for child in value)
        return 0
    return count(geometry["coordinates"])


def canonical_shape_hash(geometry):
    return canonical_hash(geometry)


def source_sidecars(manifest):
    source = next(row for row in manifest["sources"] if row["id"] == "natural-earth-admin1-5.1.1")
    rows = {}
    for descriptor in source["files"]:
        path = ROOT / descriptor["path"]
        raw = path.read_bytes()
        require(len(raw) == descriptor["bytes"] and sha256(raw) == descriptor["sha256"],
                f"retained source bytes mismatch: {descriptor['path']}")
        rows[Path(descriptor["path"]).name] = path
    return source, rows


def compute():
    manifest = load_manifest()
    baseline = pinned_baseline(manifest)
    source, sidecars = source_sidecars(manifest)
    source_receipt = json.loads((ROOT / OWNED / "sources/natural-earth-5.1.1/retrieval.json").read_text())
    require(source_receipt["commit"] == "ca96624a56bd078437bca8184e78163e5039ad19", "Natural Earth commit changed")
    for row in source_receipt["files"]:
        file = sidecars[Path(row["path"]).name]
        require(file.stat().st_size == row["bytes"] and sha256(file.read_bytes()) == row["sha256"],
                f"Natural Earth restoration receipt mismatch: {file.name}")

    issue_dir = "data/regional-review/regional-review-dbe207dead8603ae/"
    original_readme = baseline.read(issue_dir + "README.md")
    shoreline_raw = baseline.read(issue_dir + "shoreline-screen.json")
    part_raw = baseline.read("data/geography/part-28.json")
    index = json.loads(baseline.read("data/world-index.json"))
    part_names = {"data/" + item for item in index["parts"]}
    require("data/geography/part-28.json" in part_names, "subject containing file is not in the pinned world index")
    part = json.loads(part_raw)
    features = {}
    for feature in part["features"]:
        identity = feature.get("id") or feature.get("properties", {}).get("id")
        if identity in SUBJECTS:
            features.setdefault(identity, []).append(feature)
    require(set(features) == set(SUBJECTS) and all(len(rows) == 1 for rows in features.values()),
            "requested subject missing or duplicated in actual containing file")
    hierarchy = json.loads(baseline.read("data/hierarchy.json"))

    inventory = json.loads(shoreline_raw)
    contexts = derive_contexts(inventory)
    require(sha256(original_readme) == "248b82ff43ae53727928711c4f91317b2022d1330c1289dd1d17961c646936d2",
            "original summary pin changed")
    require(sha256(shoreline_raw) == "44847f5c043d78c9349f623cdb063e9b26d459ed73a0a56c21cb5231999747fd",
            "original shoreline inventory pin changed")
    require(len(OLD_PIN) == 63 and re.fullmatch(r"[a-f0-9]{64}", OLD_PIN) is None,
            "old settlement response digest must remain explicitly malformed")

    region_id = "framework:region:south-atlantic-islands:242a7633c849"
    membership = json.loads(gzip.decompress(baseline.read("data/macro-foundation/current-membership-inventory.json.gz")))
    region_members = find_region_members(membership, region_id)
    require(set(region_members) == {"SHN-4865", "atlas:coverage:BVT+00?", "atlas:island:geonames:3370905"},
            "current neighboring location inventory changed")
    gate = json.loads(baseline.read("data/research-geography-gate.json"))
    gate_state = gate["macro_boundaries"]

    shp_path = next(path for name, path in sidecars.items() if name.endswith(".shp"))
    reader = shapefile.Reader(str(shp_path.with_suffix("")), encoding="utf-8", encodingErrors="strict")
    fields = [entry[0] for entry in reader.fields[1:]]
    selected = {}
    for row in reader.iterShapeRecords():
        attrs = dict(zip(fields, row.record))
        if attrs.get("iso_3166_2") in {item["iso_3166_2"] for item in SUBJECTS.values()}:
            subject_id = next(identity for identity, spec in SUBJECTS.items()
                              if spec["iso_3166_2"] == attrs["iso_3166_2"])
            require(subject_id not in selected, f"Natural Earth source row duplicated: {subject_id}")
            selected[subject_id] = {"attributes": attrs, "geometry": mapping(shape(row.shape.__geo_interface__))}
    require(set(selected) == set(SUBJECTS), "Natural Earth 5.1.1 source subject coverage incomplete")

    project = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
    measurements = {}
    for subject_id in SUBJECTS:
        atlas_feature = features[subject_id][0]
        atlas_geom = atlas_feature["geometry"]
        source_row = selected[subject_id]
        source_geom = source_row["geometry"]
        source_shape, atlas_shape = shape(source_geom), shape(atlas_geom)
        source_ea = transform(project.transform, source_shape).area / 1_000_000
        atlas_ea = transform(project.transform, atlas_shape).area / 1_000_000
        source_helper = land_area_m2(source_shape)
        atlas_helper = land_area_m2(atlas_shape)
        props = source_row["attributes"]
        measurements[subject_id] = {
            "source": {
                "featurecla": props.get("featurecla"), "adm1_code": props.get("adm1_code"),
                "iso_3166_2": props.get("iso_3166_2"), "name": props.get("name"),
                "admin": props.get("admin"), "geonunit": props.get("geonunit"),
                "gu_a3": props.get("gu_a3"), "adm0_a3": props.get("adm0_a3"),
                "sov_a3": props.get("sov_a3"), "type": props.get("type"),
                "geometry_type": source_geom["type"], "geometry_hash_sha256": canonical_shape_hash(source_geom),
                "coordinate_count": coordinate_count(source_geom), "bounds": list(source_shape.bounds),
                "epsg6933_area_km2": source_ea, "shared_helper_area_m2": source_helper,
            },
            "atlas": {
                "name": atlas_feature["properties"].get("name"),
                "parent_id": atlas_feature["properties"].get("parent_id"),
                "reference_owner": atlas_feature["properties"].get("reference_owner"),
                "geometry_type": atlas_geom["type"], "geometry_hash_sha256": canonical_shape_hash(atlas_geom),
                "coordinate_count": coordinate_count(atlas_geom), "bounds": list(atlas_shape.bounds),
                "epsg6933_area_km2": atlas_ea, "shared_helper_area_m2": atlas_helper,
            },
            "area_difference_source_minus_atlas_km2": source_ea - atlas_ea,
            "hashes_equal": canonical_shape_hash(source_geom) == canonical_shape_hash(atlas_geom),
            "parent_chain": hierarchy_chain(subject_id, atlas_feature, hierarchy),
        }
        require(not measurements[subject_id]["hashes_equal"],
                f"unexpected source/atlas geometry equality: {subject_id}")

    retrieval = json.loads((ROOT / OWNED / "source-retrieval.json").read_text())
    require(retrieval["url"] == "https://www.tristandc.com/settlement.php" and retrieval["http_status"] == 200,
            "current settlement page observation changed")
    require(re.fullmatch(r"[a-f0-9]{64}", retrieval["sha256"]), "current response digest must be complete SHA-256")
    require(retrieval["original_response_bytes_retained"] is False, "do not retain HTML with unverified reuse terms")

    metric_values = {
        "shoreline-total": (contexts["record_count"], "rows"),
        "shoreline-unique-ids": (contexts["unique_id_count"], "unique source IDs"),
        "tristan-vicinity-count": (contexts["context_counts"]["Tristan vicinity"], "rows"),
        "gough-vicinity-count": (contexts["context_counts"]["Gough vicinity"], "rows"),
        "bouvet-vicinity-count": (contexts["context_counts"]["Bouvet vicinity"], "rows"),
        "settlement-current-response-bytes": (retrieval["bytes"], "response bytes"),
    }
    for subject_id, slug in (("SHN-4865", "shn"), ("atlas:coverage:BVT+00?", "bouvet")):
        row = measurements[subject_id]
        metric_values[slug + "-source-epsg6933-area"] = (row["source"]["epsg6933_area_km2"], "km²")
        metric_values[slug + "-atlas-epsg6933-area"] = (row["atlas"]["epsg6933_area_km2"], "km²")
        metric_values[slug + "-difference-epsg6933-area"] = (row["area_difference_source_minus_atlas_km2"], "km²")
        metric_values[slug + "-source-shared-helper-area"] = (row["source"]["shared_helper_area_m2"], "m²")
        metric_values[slug + "-atlas-shared-helper-area"] = (row["atlas"]["shared_helper_area_m2"], "m²")
    findings = {
        "version": 1,
        "issue": 786,
        "baseline_commit": manifest["baseline"]["commit"],
        "historical_audit_commit": OLD_AUDIT_COMMIT,
        "original_issue_pins_verified_on_current_main": {
            "original_summary_sha256": sha256(original_readme),
            "original_shoreline_inventory_sha256": sha256(shoreline_raw),
            "actual_subject_containing_file_sha256": sha256(part_raw),
        },
        "original_settlement_digest": {"value": OLD_PIN, "characters": len(OLD_PIN), "valid_sha256": False},
        "settlement_current_response": retrieval,
        "shoreline_inventory": contexts,
        "subjects": measurements,
        "current_regional_membership": {"region_id": region_id, "member_location_ids": sorted(region_members)},
        "current_macro_publication_gate": {
            "macro_partition_approved": gate_state.get("approved"),
            "approved_release": gate_state.get("approved_release"),
            "publication_verified": gate_state.get("publication_verified"),
            "publication_status": gate_state.get("publication_status"),
            "ready_for_location_attributes": gate.get("ready_for_location_attributes"),
            "complete_region_certificates": len(gate.get("regions", [])),
        },
        "metric_values": {key: {"value": value, "unit": unit} for key, (value, unit) in metric_values.items()},
        "interpretation": [
            "The pinned 17-row shoreline JSON inventory has unique IDs and context counts 6/9/2; those row counts are not a proof of coastline or island-group completeness.",
            "Natural Earth 5.1.1 source geometry hashes and equal-area measurements differ from both current atlas geometries. This rejects the old equality statement only; it does not determine whether the atlas generalization is suitable.",
            "Natural Earth Admin-1 labels are source classification, not independent proof of statutory status or the purpose of WorldAtlas province/area wrappers.",
            "The four Tristan group islands, separate Inaccessible neighbor, fixed parent chains, source vintages and open tier/source questions remain explicit; no region, boundary, settlement absence, or historical claim is certified.",
        ],
        "limits": [
            "GSHHG 2.3.7 original archive is not independently re-extracted in this packet; the count reproduction uses only the pinned prior whole-file shoreline-screen.json inventory.",
            "Tristan source HTML and Norsk Polar Institute HTML are not retained because reuse terms were not verified; canonical restoration instructions are in README.md.",
            "The newly observed settlement response is distinct from the unavailable original response; its digest cannot repair or identify that original vintage.",
            "No core geography, hierarchy, region certificate, live data, deployment or historical import changed.",
        ],
    }
    return findings, metric_values, measurements, retrieval, contexts, inventory


def control_results(findings, metrics, measurements, retrieval, contexts, inventory):
    # The exact shared helper control rejects swapped coordinate axes.
    x, y = transform_point(10, 45, "EPSG:3857")
    require(math.isclose(x, 1113194.9079327357, abs_tol=0.02) and
            math.isclose(y, 5621521.486192066, abs_tol=0.02), "positive CRS control failed")
    swapped = transform_point(45, 10, "EPSG:3857")
    require(not (math.isclose(swapped[0], x, abs_tol=0.02) and math.isclose(swapped[1], y, abs_tol=0.02)),
            "swapped-axis negative control was not detected")
    generator_positive = {"method_id": "pinned-shoreline-ledger", "kind": "positive-control", "outcome": "passed",
                          "checks": {"total": contexts["record_count"], "unique_ids": contexts["unique_id_count"],
                                     "contexts": contexts["context_counts"]}}
    negative_cases = []
    def rejected(name, mutator):
        changed = json.loads(json.dumps(inventory))
        mutator(changed)
        try:
            derive_contexts(changed)
        except ValueError as exc:
            negative_cases.append({"case": name, "outcome": "rejected", "reason": str(exc)})
            return
        raise AssertionError("negative control passed invalid data: " + name)
    rejected("wrong-total", lambda x: x.update(record_count=x["record_count"] - 1))
    rejected("duplicate-source-id", lambda x: x["records"][1].update(gshhg_id=x["records"][0]["gshhg_id"]))
    rejected("missing-context", lambda x: x["records"][0].update(context=None))
    wrong_render = {"Tristan vicinity": 5, "Gough vicinity": 9, "Bouvet vicinity": 2}
    require(wrong_render != contexts["context_counts"], "wrong-count narrative control was not mutated")
    negative_cases.append({"case": "prose-generated-count-disagreement", "outcome": "rejected",
                           "expected": contexts["context_counts"], "mutated": wrong_render})
    generator_negative = {"method_id": "pinned-shoreline-ledger", "kind": "negative-control", "outcome": "passed",
                          "rejected_cases": negative_cases}
    result_bytes = canonical_json(findings)
    generator_repro = {"method_id": "pinned-shoreline-ledger", "kind": "reproducibility", "outcome": "passed",
                       "run_one_sha256": sha256(result_bytes), "run_two_sha256": sha256(canonical_json(compute()[0]))}
    require(generator_repro["run_one_sha256"] == generator_repro["run_two_sha256"], "two-run result bytes differ")
    geometry_positive = {"method_id": "subject-geometry-comparison", "kind": "positive-control", "outcome": "passed",
                         "axis_control_expected": [1113194.9079327357, 5621521.486192066],
                         "axis_control_actual": [x, y], "source_atlas_hashes_differ": True,
                         "helper_version": METHOD["version"]}
    geometry_negative = {"method_id": "subject-geometry-comparison", "kind": "negative-control", "outcome": "passed",
                         "swapped_axis_result": list(swapped), "correct_axis_result": [x, y],
                         "swapped_axis_claim_rejected": True}
    measurement_positive = {"method_id": "epsg6933-area-comparison", "kind": "positive-control", "outcome": "passed",
                            "reproduced_source_area_km2": {key: row["source"]["epsg6933_area_km2"] for key, row in measurements.items()},
                            "reproduced_atlas_area_km2": {key: row["atlas"]["epsg6933_area_km2"] for key, row in measurements.items()}}
    false_equalities = [key for key, row in measurements.items() if row["source"]["geometry_hash_sha256"] == row["atlas"]["geometry_hash_sha256"]]
    require(false_equalities == [], "deliberately false equality claim unexpectedly passed")
    measurement_negative = {"method_id": "epsg6933-area-comparison", "kind": "negative-control", "outcome": "passed",
                            "deliberately_claimed_equal_subjects": sorted(measurements),
                            "actual_equal_subjects": false_equalities, "false_equality_claim_rejected": True}
    pin_positive = {"method_id": "historical-pin-validation", "kind": "positive-control", "outcome": "passed",
                    "current_sha256_characters": len(retrieval["sha256"]),
                    "current_sha256_valid": bool(re.fullmatch(r"[a-f0-9]{64}", retrieval["sha256"]))}
    pin_negative = {"method_id": "historical-pin-validation", "kind": "negative-control", "outcome": "passed",
                    "historical_value_characters": len(findings["original_settlement_digest"]["value"]),
                    "historical_sha256_valid": bool(re.fullmatch(r"[a-f0-9]{64}", findings["original_settlement_digest"]["value"])),
                    "malformed_historical_digest_rejected": True}
    return {"generator-positive-control.json": generator_positive,
            "generator-negative-control.json": generator_negative,
            "generator-reproducibility-control.json": generator_repro,
            "geometry-positive-control.json": geometry_positive,
            "geometry-negative-control.json": geometry_negative,
            "measurement-positive-control.json": measurement_positive,
            "measurement-negative-control.json": measurement_negative,
            "pin-positive-control.json": pin_positive,
            "pin-negative-control.json": pin_negative}


def write_exclusive(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(path, flags, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def render_tables(readme, contexts, metrics):
    for context, actual in contexts["context_counts"].items():
        if f"| {context} | {actual} |" not in readme:
            raise ValueError(f"README generated count differs from ledger: {context}")
    if f"| Total source rows | {contexts['record_count']} |" not in readme:
        raise ValueError("README total differs from ledger")
    if f"| Unique source IDs | {contexts['unique_id_count']} |" not in readme:
        raise ValueError("README unique-ID count differs from ledger")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="create a fresh immutable evidence vintage")
    parser.add_argument("--check", action="store_true", help="recompute and compare all retained outputs")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    manifest = load_manifest()
    findings, metrics, measurements, retrieval, contexts, inventory = compute()
    controls = control_results(findings, metrics, measurements, retrieval, contexts, inventory)
    vintage_dir = ROOT / OWNED / "vintages" / VINTAGE
    rows = {"findings.json": findings, **controls}
    if args.write:
        baseline = pinned_baseline(manifest)
        for name, value in rows.items():
            if name == "findings.json":
                write_new_vintage(baseline, OWNED, VINTAGE, name, value)
            else:
                write_exclusive(vintage_dir / name, canonical_json(value))
    else:
        for name, value in rows.items():
            actual = (vintage_dir / name).read_bytes()
            require(actual == canonical_json(value), f"reproduced bytes differ: {name}")
        readme = (ROOT / OWNED / "README.md").read_text(encoding="utf-8")
        render_tables(readme, contexts, metrics)
    print(json.dumps({"status": "passed", "mode": "write" if args.write else "check",
                      "baseline_commit": manifest["baseline"]["commit"],
                      "outputs": sorted(rows), "source_context_counts": contexts["context_counts"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
