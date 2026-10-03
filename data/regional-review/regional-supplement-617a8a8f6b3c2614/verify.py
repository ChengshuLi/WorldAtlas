#!/usr/bin/env python3
"""Read-only reproduction checks for issue #543 source and scope accounting."""
import gzip
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
packet = json.loads((HERE / "assessment.json").read_text())
source = ROOT / "data/macro-improvements/macro-coverage-oceania/osm-e3de5671fd1c.xml.gz"
raw = source.read_bytes()
assert len(raw) == 9577
assert hashlib.sha256(raw).hexdigest() == "ac5e565a083b08ce1fb4d83d64cd3e5b522d1766defadbbc082093e200e01b94"
xml = gzip.decompress(raw)
assert len(xml) == 73911
assert hashlib.sha256(xml).hexdigest() == "4042db2e1fff71d26c3b01e12c49d49e18aace181866d4af7bb83ba9f28e94c3"
root = ET.fromstring(xml)
ways = {w.attrib["id"]: w for w in root.findall("way")}
ids = ["42063621", "42063620", "42063619"]
assert all(i in ways for i in ids)
for i in ids:
    tags = {t.attrib["k"]: t.attrib["v"] for t in ways[i].findall("tag")}
    assert tags == {"natural": "coastline", "place": "islet", "source": "NOAA U.S. Vector Shoreline"}
    nodes = ways[i].findall("nd")
    assert nodes and nodes[0].attrib["ref"] == nodes[-1].attrib["ref"]
assert sum(len(ways[i].findall("nd")) for i in ids) == 50
assert len({nd.attrib["ref"] for i in ids for nd in ways[i].findall("nd")}) == 47
node_coordinates = {n.attrib["id"]: (float(n.attrib["lon"]), float(n.attrib["lat"])) for n in root.findall("node")}
geo = json.loads((ROOT / "data/macro-improvements/loose-ends-v5/grid/held-islands.geojson").read_text())
feature = next(f for f in geo["features"] if f["properties"]["id"] == packet["scope"]["member_location_ids"][0])
assert feature["properties"]["name"] == "Gardner Pinnacles"
assert feature["properties"]["parent_chain"] == [p["id"] for p in packet["parent_chain_assessment"]["chain"]]
assert len(feature["geometry"]["coordinates"]) == 3
rings = feature["geometry"]["coordinates"]
assert all(poly[0][0] == poly[0][-1] for poly in rings)
for way_id in ids:
    source_points = {node_coordinates[nd.attrib["ref"]] for nd in ways[way_id].findall("nd")}
    assert sum(source_points == set(map(tuple, poly[0][:-1])) for poly in rings) == 1
assert packet["scope"]["owned_member_count"] == packet["subject_assessments"][0]["accounting"]["assessed_subjects"] == 1
print("PASS: original OSM bytes/hashes, three target ways/rings, 50 references/47 unique nodes, exact pinned location and parent chain, and 1/1 issue accounting")
