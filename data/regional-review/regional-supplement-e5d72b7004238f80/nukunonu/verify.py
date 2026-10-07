#!/usr/bin/env python3
"""Reproduce the bounded Nukunonu source-inventory integrity checks."""
import gzip
import hashlib
import json
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / "data/macro-improvements/macro-coverage-oceania/osm-2af0d96ae4f6.xml.gz"
EXPECTED_RAW = "0b150bc8b2675fceeca0fca17661d5c373cc1381c4c7667b92b0e8cb4e0dbad4"
EXPECTED_GZIP = "ade053ac91d0f2f4b6d7a033bba95c3fd39c2468b55b58ab14b2120e8420fb07"
BASELINE = "3e22e5a2562526e5c9dc3d1aa87c5cc2c3e2e5bc"

def source_bytes(path):
    if path.exists():
        return path.read_bytes()
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(["git", "show", f"{BASELINE}:{relative}"], cwd=ROOT)

def require(test, message):
    if not test:
        raise SystemExit("FAIL: " + message)

compressed = source_bytes(SOURCE)
raw = gzip.decompress(compressed)
require(hashlib.sha256(compressed).hexdigest() == EXPECTED_GZIP, "retained gzip SHA-256")
require(len(raw) == 1_487_407, "decompressed byte count")
require(hashlib.sha256(raw).hexdigest() == EXPECTED_RAW, "decompressed SHA-256")
root = ET.fromstring(raw)
nodes = {n.get("id") for n in root.findall("node")}
coast = {}
for way in root.findall("way"):
    tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
    if tags.get("natural") != "coastline":
        continue
    refs = [n.get("ref") for n in way.findall("nd")]
    require(len(refs) >= 4 and refs[0] == refs[-1], f"closed coastline ring {way.get('id')}")
    require(all(ref in nodes for ref in refs), f"all nodes present for {way.get('id')}")
    coast[way.get("id")] = way
assessment = json.loads((PACKET / "assessment.json").read_text())
rings = assessment["audit"]["ring_inventory"]
require(len(coast) == 97, "all 97 coastline ways present")
require({c["osm_way_ids"][0] for c in rings} == set(coast), "ring inventory covers source exactly")
require(all(c["valid_source_ring"] and c["whole_source_polygon_inside_query_domain"] for c in rings), "all inventoried rings valid and in query envelope")
require(len(assessment["audit"]["gshhg_components"]) == 21, "21 independent comparison polygons inventoried")
require(assessment["audit"]["unclosed_chains"] == [] and assessment["audit"]["missing_node_ways"] == [], "reported source reconstruction has no open chains/missing ways")
print("PASS source integrity: hashes, 97/97 closed coastline rings and nodes, exact ring inventory, 21 GSHHG comparison components")
print("Current coverage is reproduced separately by reproduce_current_coverage.py --check.")
