#!/usr/bin/env python3
"""Verify #526's second-part assessment against retained source reports/archives."""
import gzip
import hashlib
import json
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
DATA = ROOT / "data/macro-improvements/macro-coverage-oceania"
assessment = json.loads((PACKET / "remaining-assessment.json").read_text())
osm = json.loads((DATA / "osm-report.json").read_text())
gshhg = json.loads((DATA / "report.json").read_text())
assert len(assessment["locations"]) == 12
assert len({row["id"] for row in assessment["locations"]}) == 12
for key, source_path in (("osm_report_sha256", DATA / "osm-report.json"), ("gshhg_report_sha256", DATA / "report.json")):
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == assessment["sources"][key]
osm_routes = {row["name"]: row for row in osm["routes"]}
gshhg_routes = {row["name"]: row for row in gshhg["routes"]}
component_rows = [json.loads(line) for line in (PACKET / "component-inventory.jsonl").read_text().splitlines()]
for row in assessment["locations"]:
    name = row["name"]
    inventory = row["source_inventory"]
    o = inventory["osm"]
    source = osm_routes[name]
    assert o["route_name"] == name and o["source_url"] == source["source"]["url"], name
    assert o["raw_xml_sha256"] == source["source"]["sha256"], name
    assert o["coastline_way_count"] == source["coastline_way_count"], name
    osm_components = [c for c in component_rows if c["location_id"] == row["id"] and c["source_family"] == "osm"]
    assert o["closed_land_rings"] == source["closed_land_rings"] == o["component_inventory_count"] == len(osm_components), name
    assert o["open_chains"] == source["unclosed_chains"] == [] and o["missing_node_ways"] == source["missing_node_ways"] == [], name
    assert o["component_status"] == source["status"] and o["source_land_area_km2"] == source["source_land_area_km2"], name
    for compact, full in zip(osm_components, source["current_source_components"]):
        compact = {k:v for k,v in compact.items() if k not in ("location_id", "location_name", "source_family")}
        assert compact["way_ids"] == full["osm_way_ids"] and compact["versions"] == full["osm_source_versions"], name
        assert compact["area_km2"] == full["source_area_km2"] and compact["bbox"] == full["bbox"], name
    archive = DATA / o["retained_archive"]
    compressed = archive.read_bytes()
    assert len(compressed) == o["retained_archive_bytes"] and hashlib.sha256(compressed).hexdigest() == o["retained_archive_sha256"], name
    raw = gzip.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest() == o["raw_xml_sha256"], name
    assert raw.startswith(b"<?xml") or b"<osm" in raw[:1000], name
    g = inventory["gshhg"]
    full_g = gshhg_routes[name]
    g_components = [c for c in component_rows if c["location_id"] == row["id"] and c["source_family"] == "gshhg"]
    assert g["source_component_count"] == full_g["source_component_count"] == g["component_inventory_count"] == len(g_components), name
    assert g["source_domain_land_area_km2"] == full_g["source_domain_land_area_km2"], name
    for compact, full in zip(g_components, full_g["independent_land_components"]):
        compact = {k:v for k,v in compact.items() if k not in ("location_id", "location_name", "source_family")}
        assert compact == {'id':full['gshhg_id'],'level':full['source_level'],'area_km2':full['source_land_area_km2'],'bbox':full['source_bounds'],'vertex_count':full['source_vertex_count'],'status':full['status']}, name
print("verified 12 assigned locations, OSM/GSHHG component inventories, retained archives and pinned report hashes")
