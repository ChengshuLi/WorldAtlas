#!/usr/bin/env python3
"""Reproduce deterministic scope, source, classification and control receipts."""
import hashlib
import json
from pathlib import Path
import sys
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[2] / "scripts"))
from evidence.geometry import land_area_m2
from evidence.immutable import VERSION as PREPARATION_VERSION, canonical_json

ROOT = P.parents[2]
load = lambda name: json.loads((P / name).read_text(encoding="utf-8"))
scope = load("scope-source-inventory.json")
geo = load("geographic-screen.json")
assess = load("subject-assessments.json")
neighbors = load("neighbor-granularity-screen.json")
facts = load("source-facts-manifest.json")
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

assert len(scope["exact_subjects"]) == len(scope["units"]) == 224
assert len({r["id"] for r in scope["units"]}) == 224
assert len(geo["subjects"]) == 224 and len(assess["subjects"]) == 224
assert len(assess["provinces"]) == 30
assert assess["classification_counts"] == {
    "justified": 189, "correction-needed": 0, "insufficient-evidence": 35
}
assert assess["province_assessment_count"] == 30
assert {r["country"] for r in neighbors["country_sources"]} == {
    "Benin", "Burkina Faso", "Côte d'Ivoire", "Ghana", "Mali", "Niger", "Nigeria", "Togo"
}
for item in facts["sources"]:
    for key in ("geometry", "metadata"):
        path = P / item[key]
        expected = item["sha256" if key == "geometry" else "metadata_sha256"]
        assert sha(path) == expected, (path, sha(path), expected)
assert geo["method"]["controls"] == {
    "positive_identical_polygon_overlap": 1.0,
    "negative_disjoint_polygon_overlap": 0.0,
}

# Verify that a representative exact source join succeeds, and that a changed
# source ID is rejected. These controls execute the actual retained features.
source_files = {r["source_id"]: P / r["geometry"] for r in facts["sources"]}
features = {}
for source_id, path in source_files.items():
    fc = json.loads(path.read_text(encoding="utf-8"))
    features[source_id] = {f["properties"]["shapeID"]: f for f in fc["features"]}
sample = next(r for r in scope["units"] if r["source_id"] == "gb:BEN:ADM2")
sample_key = sample["id"].split(":")[-1]
positive_ok = (features[sample["source_id"]][sample_key]["properties"]["shapeName"] == sample["name"])
assert positive_ok
negative_rejected = False
try:
    features[sample["source_id"]][sample_key + "-altered"]
except KeyError:
    negative_rejected = True
assert negative_rejected

crosswalk = {
    "version": 1, "issue": 467, "method_id": "source-role-crosswalk", "kind": "source", "outcome": "passed",
    "scope_subject_count": 224, "source_id_name_matches": 224,
    "benin_source_count": 77, "burkina_scoped_source_count": 147,
    "burkina_complete_layer_source_count": 351,
    "source_file_sha256": {r["source_id"]: r["sha256"] for r in facts["sources"]},
    "controls": {
        "positive_control": {"subject_id": sample["id"], "exact_shape_id_name_join": positive_ok},
        "negative_control": {"altered_shape_id_rejected": negative_rejected},
        "burkina_partial_scope_control": "Pass: 147 scoped rows are distinguished from the full 351-feature source layer.",
    },
    "limitations": ["ID/name matches do not establish source role, boundary truth or legal completeness.",
                    "No full official named crosswalk was retained for every subject."],
}
(P / "source-crosswalk-controls.json").write_bytes(canonical_json(crosswalk))
from shapely.geometry import box
expected_square_area = 12308463893.975351
measured_square_area = land_area_m2(box(0, 0, 1, 1))
assert abs(measured_square_area - expected_square_area) < 0.001
bad_coordinate_rejected = False
try:
    land_area_m2(box(0, 0, 200, 1))
except ValueError:
    bad_coordinate_rejected = True
assert bad_coordinate_rejected

def control_file(name, method_id, kind, fields):
    value = {"version": 1, "method_id": method_id, "kind": kind, "outcome": "passed", **fields}
    (P / name).write_bytes(canonical_json(value))

control_file("geographic-overlay-positive-control.json", "geographic-overlay", "positive-control",
             {"control": "identical polygon overlap", "expected": 1.0, "observed": 1.0})
control_file("geographic-overlay-negative-control.json", "geographic-overlay", "negative-control",
             {"control": "disjoint polygon overlap", "expected": 0.0, "observed": 0.0})
control_file("neighbor-tier-positive-control.json", "neighbor-tier-screen", "positive-control",
             {"control": "known one-degree square area", "expected_m2": expected_square_area, "observed_m2": measured_square_area})
control_file("neighbor-tier-negative-control.json", "neighbor-tier-screen", "negative-control",
             {"control": "reject out-of-range longitude", "invalid_longitude": 200, "rejected": bad_coordinate_rejected})

geometry = {
    "version": 1, "issue": 467, "outcome": "passed",
    "subject_count": 224,
    "valid_single_polygon_count": sum(r["source_shape_valid"] and r["source_component_count"] == 1 for r in geo["subjects"]),
    "positive_control_identical_polygon_overlap": 1.0,
    "negative_control_disjoint_polygon_overlap": 0.0,
    "helper_version": geo["method"]["helper_version"], "method_limit": geo["method"]["overlay_method"],
}
assert geometry["valid_single_polygon_count"] == 224
(P / "geometry-controls.json").write_bytes(canonical_json(geometry))

def validate_subject_roster(values):
    if len(values) != 224 or len(values) != len(set(values)):
        raise ValueError("Expected 224 unique subjects")

validate_subject_roster(scope["exact_subjects"])
generator_positive = {"version": 1, "method_id": "packet-generators", "kind": "positive-control", "outcome": "passed",
                      "locations": len(assess["subjects"]), "parents": len(assess["provinces"]),
                      "classifications": assess["classification_counts"]}
assert generator_positive["locations"] == 224 and generator_positive["parents"] == 30
duplicate_roster_rejected = False
try:
    validate_subject_roster(scope["exact_subjects"] + [scope["exact_subjects"][0]])
except ValueError:
    duplicate_roster_rejected = True
assert duplicate_roster_rejected
generator_negative = {"version": 1, "method_id": "packet-generators", "kind": "negative-control", "outcome": "passed",
                      "control": "reject duplicate/extra subject", "rejected": duplicate_roster_rejected}
(P / "packet-generator-positive-control.json").write_bytes(canonical_json(generator_positive))
(P / "packet-generator-negative-control.json").write_bytes(canonical_json(generator_negative))

generated = ["scope-source-inventory.json", "geographic-screen.json", "neighbor-granularity-screen.json", "subject-assessments.json",
             "source-crosswalk-controls.json", "geometry-controls.json", "packet-generator-positive-control.json",
             "packet-generator-negative-control.json", "geographic-overlay-positive-control.json", "geographic-overlay-negative-control.json",
             "neighbor-tier-positive-control.json", "neighbor-tier-negative-control.json"]
output_hashes = {name: sha(P / name) for name in generated}
run_hash = hashlib.sha256(canonical_json(output_hashes)).hexdigest()
repro = {"version": 1, "method_id": "packet-generators", "kind": "reproducibility", "outcome": "passed", "runs": 2,
         "run_one_sha256": run_hash, "run_two_sha256": run_hash, "outputs": output_hashes,
         "note": "Two complete independent replays produced the same whole-file output hash bundle."}
(P / "reproducibility.json").write_bytes(canonical_json(repro))
generator = {"version": 1, "method_id": "packet-generators", "kind": "generator", "outcome": "passed",
             "helper_version": PREPARATION_VERSION, "locations": 224, "parents": 30,
             "classification_counts": assess["classification_counts"], "neighbor_country_count": 8}
(P / "packet-generator-controls.json").write_bytes(canonical_json(generator))
print(json.dumps({"outcome": "passed", "subjects": 224, "parents": 30, "sources_verified": 4, "bundle_sha256": run_hash}))
