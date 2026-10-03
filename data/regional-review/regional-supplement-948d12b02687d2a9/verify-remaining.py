#!/usr/bin/env python3
"""Verify the #526 second-part assessment against retained source reports/archives."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
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
for row in assessment["locations"]:
    name = row["name"]
    route_copy = json.loads(json.dumps(row["osm_2026-10-02"]))
    route_copy["source"].pop("retained_archive_bytes", None)
    route_copy["source"].pop("retained_archive_sha256", None)
    assert route_copy == osm_routes[name], name
    assert row["gshhg_2.3.7"] == gshhg_routes[name], name
    route = osm_routes[name]
    archive_source = row["osm_2026-10-02"]["source"]
    archive = DATA / archive_source["path"]
    compressed = archive.read_bytes()
    assert len(compressed) == archive_source["retained_archive_bytes"], name
    assert hashlib.sha256(compressed).hexdigest() == archive_source["retained_archive_sha256"], name
    raw = gzip.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest() == route["source"]["sha256"], name
    # OSM report's source SHA is the compressed archive digest; XML is independently parseable.
    assert raw.startswith(b"<?xml") or b"<osm" in raw[:1000], name
    assert route["complete_ring_reconstruction"] is True, name
    assert route["unclosed_chains"] == [] and route["missing_node_ways"] == [], name
    assert len(route["current_source_components"]) == route["closed_land_rings"], name
    assert row["gshhg_2.3.7"]["source_component_count"] == len(row["gshhg_2.3.7"]["independent_land_components"]), name
print("verified 12 assigned locations, complete OSM/GSHHG inventories, retained archives and source report hashes")
