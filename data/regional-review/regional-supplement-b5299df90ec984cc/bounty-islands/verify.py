#!/usr/bin/env python3
"""Verify retained Bounty Islands source identities and exhaustive component inventories."""
import gzip
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / "data/macro-improvements/macro-coverage-oceania/osm-28c1ddf724e1.xml.gz"
EXPECTED_GZIP = "45545b5d4cdf82c3bcab305a437cdf0c388a515df9b6d20857a51ba04de7af18"
EXPECTED_RAW = "9bb048bfe6efb335bffbe08bda484a0283571eb7b6f839e9e0e99268ca8f177c"
GSHHG = ROOT / "data/macro-improvements/macro-coverage-oceania/gshhg-selected-full-records.bin.gz"
GSHHG_GZIP = "7e52c4c7c13ea3b2d35120cc0f1f6832007865750b98f42d5cd9c95162df1df4"
GSHHG_NATIVE = "a7c071d1e80655b7a929d9a0a3f694f915a224b59b449505560fd40433c71b51"

def require(ok, message):
    if not ok:
        raise SystemExit("FAIL: " + message)

compressed = SOURCE.read_bytes()
raw = gzip.decompress(compressed)
require(hashlib.sha256(compressed).hexdigest() == EXPECTED_GZIP, "retained compressed SHA-256")
require(len(raw) == 341174 and hashlib.sha256(raw).hexdigest() == EXPECTED_RAW, "retained source bytes/hash")
root = ET.fromstring(raw)
nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in root.findall("node")}
ways = {}
for way in root.findall("way"):
    tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
    if tags.get("natural") != "coastline":
        continue
    refs = [n.get("ref") for n in way.findall("nd")]
    require(len(refs) >= 4 and refs[0] == refs[-1], f"closed ring {way.get('id')}")
    require(all(ref in nodes for ref in refs), f"complete node references {way.get('id')}")
    require(all(178.97 <= nodes[ref][0] <= 179.13 and -47.83 <= nodes[ref][1] <= -47.67 for ref in refs), f"ring inside retrieval bbox {way.get('id')}")
    ways[way.get("id")] = way
assessment = json.loads((PACKET / "assessment.json").read_text())
audit = assessment["audit"]
rings = audit["osm_ring_inventory"]
require(len(ways) == 27 and len(rings) == 27, "all 27 coastline rings inventoried")
require({c["osm_way_ids"][0] for c in rings} == set(ways), "ring inventory exactly matches source")
require(all(c["valid_source_ring"] and c["whole_source_polygon_inside_query_domain"] for c in rings), "all rings valid and within retrieval envelope")
require(all(c["name"] is None and c["place"] is None for c in rings), "all 27 source ways are explicitly unnamed")
require(abs(sum(c["source_area_km2"] for c in rings) - audit["ring_land_area_km2"]) < 1e-8, "OSM ring area sum")
polygons = audit["gshhg_components"]
require(len(polygons) == 14 and len({p["gshhg_id"] for p in polygons}) == 14, "all 14 GSHHG polygons inventoried")
require(abs(sum(c["source_land_area_km2"] for c in polygons) - audit["gshhg_land_area_km2"]) < 1e-8, "GSHHG polygon area sum")
source_dir = ROOT / "data/macro-improvements/macro-coverage-oceania"
source_osm = next(r for r in json.loads((source_dir / "osm-report.json").read_text())["routes"] if r["name"] == "Bounty Islands")
require({c["osm_way_ids"][0] for c in source_osm["current_source_components"]} == set(ways), "matches retained OSM analysis inventory")
source_gshhg = next(r for r in json.loads((source_dir / "report.json").read_text())["routes"] if r["name"] == "Bounty Islands")
require(polygons == source_gshhg["independent_land_components"], "matches retained GSHHG comparison inventory")
gshhg_compressed = GSHHG.read_bytes()
gshhg_native = gzip.decompress(gshhg_compressed)
require(hashlib.sha256(gshhg_compressed).hexdigest() == GSHHG_GZIP, "retained GSHHG records compressed SHA-256")
require(len(gshhg_native) == 8081872 and hashlib.sha256(gshhg_native).hexdigest() == GSHHG_NATIVE, "retained GSHHG records native SHA-256")
require(audit["unclosed_chains"] == [] and audit["missing_node_ways"] == [], "reported complete OSM reconstruction")
print("PASS: OSM and GSHHG source hashes; all 27 closed, unnamed OSM rings and nodes; exact OSM/GSHHG inventories")
