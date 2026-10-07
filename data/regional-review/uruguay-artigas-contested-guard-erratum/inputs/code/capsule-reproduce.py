#!/usr/bin/env python3
"""Offline equivalent of original-reproduce.py, using only pinned capsule bytes."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[2]
BASELINE = HERE / "inputs/baseline"
SOURCES = HERE / "inputs/sources"
OUT = Path(sys.argv[1])
PINS = {
    "data-world-index.json": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "data-hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "data-administrative-sources.json": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "data-macro-publication-v5.json": "aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674",
    "data-geography-part-25.json": "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394",
}
SOURCE_PINS = {
    "ury-gb-2017.geojson": "9f4887205e7b359af2ef1e4f484ad071d2dc0d12d068f1d7b6c1cc6c2624d1cf",
    "ury-igm-current.geojson": "3cfa19c6be9d12bd159b236e15839f958656fdbe66ef19e38379cb54c141b3a7",
}


def read(path):
    return path.read_bytes()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(raw, expected):
    if sha(raw) != expected:
        raise ValueError("whole-file pin mismatch")


def unique_subjects(features, target):
    rows = [f for f in features if f.get("id") == target]
    if len(rows) != 1:
        raise ValueError("subject must occur exactly once")
    return rows[0]


baseline = {name: read(BASELINE / name) for name in PINS}
for name, expected in PINS.items():
    verify(baseline[name], expected)
source_bytes = {name: read(SOURCES / name) for name in SOURCE_PINS}
for name, expected in SOURCE_PINS.items():
    verify(source_bytes[name], expected)
part = json.loads(baseline["data-geography-part-25.json"])
subject_id = "gb:URY:ADM1:27058087B22084813565519"
subject = unique_subjects(part["features"], subject_id)
positive_control = {"method_id":"source-review","kind":"positive-control","outcome":"passed","evidence":"the pinned input contains the exact subject once"}
try:
    unique_subjects(part["features"] + [subject], subject_id)
    raise AssertionError("duplicate control unexpectedly accepted")
except ValueError:
    pass
negative_control = {"method_id":"source-review","kind":"negative-control","outcome":"passed","evidence":"a duplicated subject is rejected"}
try:
    verify(baseline["data-world-index.json"], "0" * 64)
    raise AssertionError("wrong-pin control unexpectedly accepted")
except ValueError:
    pass
pin_control = {"method_id":"source-review","kind":"negative-control","outcome":"passed","evidence":"an altered whole-file pin is rejected"}
assert subject["properties"]["name"] == "Artigas"
assert subject["properties"]["parent_id"] == "framework:province:artigas:dc4b2e0fed20"
assert subject["properties"]["metadata"].get("semantic_review", {}).get("status") == "open"
old = json.loads(source_bytes["ury-gb-2017.geojson"])
igm = json.loads(source_bytes["ury-igm-current.geojson"])
assert len(old["features"]) == 19 and len(igm["features"]) == 21
old_art = [f for f in old["features"] if f["properties"].get("shapeName") == "Artigas"]
assert len(old_art) == 1
contested = []
for feature in igm["features"]:
    prop = feature.get("properties", {})
    if prop.get("nam") in ("Rincón de Maneco", "Isla Brasileña"):
        contested.append({"id":feature.get("id"),"name":prop.get("nam"),"department":prop.get("DEPTO"),"definition":prop.get("DEF"),"text":prop.get("TXT"),"observation":prop.get("OBS"),"geometry_type":feature.get("geometry",{}).get("type"),"coordinate_member_count":len(feature.get("geometry",{}).get("coordinates",[]))})
assert len(contested) == 2
byname = {item["name"]: item for item in contested}
assert byname["Rincón de Maneco"]["id"] == 15 and byname["Rincón de Maneco"]["department"] == "ARTIGAS"
assert byname["Rincón de Maneco"]["definition"] == "Rincón de Maneco (Contestado)"
assert byname["Isla Brasileña"]["id"] == 16 and byname["Isla Brasileña"]["department"] == "ARTIGAS"
assert byname["Isla Brasileña"]["definition"] == "Isla Brasileña (Contestada)"
assert all(item["text"] == "Contestado." for item in contested)
assert all(item["geometry_type"] == "Polygon" and item["coordinate_member_count"] > 0 for item in contested)
result = {
    "version":1,"issue":927,"baseline_commit":"72029cd16057199be441058c69dd783604541100","subject_id":subject_id,"subject_name":subject["properties"]["name"],
    "parent_id":subject["properties"]["parent_id"],"semantic_review":subject["properties"]["metadata"]["semantic_review"]["status"],
    "source_features":{"geoBoundaries_2017_adm1_count":len(old["features"]),"igm_current_count":len(igm["features"]),"igm_regular_department_count":19,"igm_contested_feature_count":2,"igm_contested_features":sorted(contested,key=lambda x:x["id"])},
    "interpretation_limits":["IGM DEPTO assignment and contested attributes document that source map representation; they do not establish mutually agreed sovereignty, a normal second administrative tier, or whether either polygon belongs inside the ordinary Artigas department boundary.","This reproduction reads geometry type and coordinate-member presence only; it does not test topology, overlap, containment, area or legal boundaries.","The 2017 geoBoundaries ADM1 feature represents Artigas as a single ordinary ADM1 unit and does not encode these two separate contested records."],
    "controls":[positive_control,negative_control,pin_control],
    "source_hashes":{"2017_geoBoundaries":sha(source_bytes["ury-gb-2017.geojson"]),"igm_current":sha(source_bytes["ury-igm-current.geojson"]),"part25":sha(baseline["data-geography-part-25.json"])}}
raw = (json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
(OUT / "reproduction-results.json").write_bytes(raw)
print(json.dumps({"result_sha256":sha(raw),"features_checked":2,"old_adm1":len(old["features"]),"igm_features":len(igm["features"]),"pins_checked":len(PINS)},sort_keys=True))
