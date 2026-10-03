#!/usr/bin/env python3
"""Verify the complete eight-location Phoenix Islands evidence checkpoint."""
import gzip
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data/macro-improvements/macro-coverage-oceania"

def require(ok, why):
    if not ok:
        raise SystemExit("FAIL: " + why)

assessment = json.loads((PACKET / "phoenix-assessment.json").read_text())
rows = assessment["locations"]
require(len(rows) == 8, "all eight assigned Phoenix locations")
require(len({r["id"] for r in rows}) == 8, "unique assigned location IDs")
total_ways = total_land = total_gshhg = 0
for row in rows:
    source = row["source"]
    compressed = (ROOT / source["retained_archive"]).read_bytes()
    raw = gzip.decompress(compressed)
    require(len(compressed) == source["retained_archive_bytes"], row["name"] + " compressed size")
    require(hashlib.sha256(compressed).hexdigest() == source["retained_archive_sha256"], row["name"] + " archive hash")
    require(len(raw) == source["uncompressed_bytes"], row["name"] + " raw size")
    require(hashlib.sha256(raw).hexdigest() == source["uncompressed_sha256"] == source["source_profile_raw_sha256"], row["name"] + " raw/profile hash")
    xml = ET.fromstring(raw)
    nodes = {n.get("id") for n in xml.findall("node")}
    ways = {}
    for way in xml.findall("way"):
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        if tags.get("natural") == "coastline":
            refs = [n.get("ref") for n in way.findall("nd")]
            require(len(refs) >= 4 and refs[0] == refs[-1], row["name"] + " closed way " + way.get("id"))
            require(all(ref in nodes for ref in refs), row["name"] + " node references " + way.get("id"))
            ways[way.get("id")] = way
    inventory = row["osm_audit"]["source_way_inventory"]
    require({w["way_id"] for w in inventory} == set(ways), row["name"] + " complete coastline-way inventory")
    require(set(source["profile_way_ids"]) == set(ways), row["name"] + " issue-profile source-way inventory")
    component_ways = {wid for c in row["osm_audit"]["land_component_inventory"] for wid in c["osm_way_ids"]}
    require(component_ways == set(ways), row["name"] + " component topology covers all source ways")
    require(row["osm_audit"]["open_chains"] == [] and row["osm_audit"]["missing_node_ways"] == [], row["name"] + " complete reported ring reconstruction")
    require(len(row["gshhg_audit"]["components"]) == row["gshhg_audit"]["independent_polygon_count"], row["name"] + " GSHHG inventory")
    total_ways += len(ways)
    total_land += len(row["osm_audit"]["land_component_inventory"])
    total_gshhg += len(row["gshhg_audit"]["components"])
gshhg = DATA / "gshhg-selected-full-records.bin.gz"
packed = gshhg.read_bytes()
native = gzip.decompress(packed)
require(hashlib.sha256(packed).hexdigest() == "7e52c4c7c13ea3b2d35120cc0f1f6832007865750b98f42d5cd9c95162df1df4", "retained GSHHG compressed hash")
require(hashlib.sha256(native).hexdigest() == "a7c071d1e80655b7a929d9a0a3f694f915a224b59b449505560fd40433c71b51", "retained GSHHG native hash")
require(total_ways == 29 and total_land == 29 and total_gshhg == 33, "complete Phoenix component totals")
print(f"PASS: {len(rows)} locations, {total_ways} OSM coastline ways/land components, {total_gshhg} GSHHG polygons, retained archive hashes")
