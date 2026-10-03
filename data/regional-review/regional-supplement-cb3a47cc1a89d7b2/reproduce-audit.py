#!/usr/bin/env python3
"""Verify the retained Minamitorishima evidence and detect (not resolve) grouping conflict."""
import gzip
import hashlib
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[3]
PKG = ROOT / "data/macro-improvements/marcus-restoration"
HERE = pathlib.Path(__file__).resolve().parent
LOCATION = "atlas:named-land:location:825337016c35d6a8235a"
EXPECTED_CHAIN = [
    "atlas:named-land:province:8e2c400cda9a948c06bb",
    "atlas:named-land:area:812ad26d42ad1d6edb86",
    "framework:region:northwestern-pacific:2357073b3888",
    "framework:subcontinent:micronesia:44f839aaab87",
    "framework:continent:oceania:48580dd0c4b4",
]


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


manifest = json.loads((PKG / "manifest.json").read_text())
for name, row in manifest["files"].items():
    payload = (PKG / name).read_bytes()
    check(len(payload) == row["bytes"] and sha(payload) == row["sha256"], f"retained source package hash {name}")

hierarchy = json.loads((ROOT / "data/hierarchy.json").read_text())
by_id = {row["id"]: row for row in hierarchy}
chain = []
parent = LOCATION
for expected in EXPECTED_CHAIN:
    chain.append(expected)
    node = by_id[expected]
    check(node.get("parent_id") == (EXPECTED_CHAIN[chain.index(expected) + 1] if chain.index(expected) + 1 < len(EXPECTED_CHAIN) else None), f"hierarchy parent for {expected}")
    parent = node.get("parent_id")
feature = None
parts = json.loads((ROOT / "data/world-index.json").read_text())
index_doc = json.loads((ROOT / "data/world-index.json").read_text())
part_paths = [ROOT / "data" / p for p in index_doc["parts"]]
check(all(path.is_file() for path in part_paths), "all geography parts named by world index are present")
for path in part_paths:
    doc = json.loads(path.read_text())
    for f in doc.get("features", []):
        if f.get("id") == LOCATION:
            feature = f
check(feature is not None, "assigned location appears in geography parts")
props = feature["properties"]
check(props.get("parent_id") == EXPECTED_CHAIN[0], "location points to declared province")
check(props.get("reference_owner") is None, "location does not encode a political owner")
check(props["metadata"]["source_way_versions"] == [{"id":"130970566","version":"27","timestamp":"2025-12-20T23:39:26Z"}], "published source identity pins coastline way/version")

xml = ET.parse(gzip.open(PKG / "original-map.osm.xml.gz", "rb")).getroot()
ways = {w.get("id"): w for w in xml.findall("way")}
rels = {r.get("id"): r for r in xml.findall("relation")}
coast = ways["130970566"]
ctags = {t.get("k"): t.get("v") for t in coast.findall("tag")}
check(ctags.get("natural") == "coastline" and ctags.get("place") == "island", "source coastline is tagged island")
check(coast.find("nd").get("ref") == coast.findall("nd")[-1].get("ref"), "source coastline way is closed")
water = ways["534203444"]
check({t.get("k"):t.get("v") for t in water.findall("tag")}.get("natural") == "water", "one recorded closed water feature is present")
relation = rels["11775500"]
r_tags = {t.get("k"):t.get("v") for t in relation.findall("tag")}
check(r_tags.get("place") == "archipelago" and r_tags.get("name:en") == "Bonin Islands", "named Bonin/Ogasawara archipelago relation is present")
check(any(m.get("type") == "way" and m.get("ref") == "130970566" and m.get("role") == "outer" for m in relation.findall("member")), "archipelago relation directly includes Minamitorishima coastline")
check(relation.get("version") == "38" and relation.get("timestamp") == "2025-04-18T05:32:38Z", "archipelago relation version and timestamp match")
admin = rels["8004038"]
a_tags = {t.get("k"):t.get("v") for t in admin.findall("tag")}
check(a_tags.get("boundary") == "administrative" and a_tags.get("admin_level") == "8", "administrative boundary is separately tagged")
check(not (ROOT / "data/macro-foundation/new-location-source-profiles-v4.json.gz").exists(), "issue-cited source-profile file remains absent")
print("RESULT: source conflict detected; this check does not determine physical grouping, parent assignment, or boundary changes.")
