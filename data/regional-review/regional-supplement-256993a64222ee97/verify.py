#!/usr/bin/env python3
"""Reproduce the seven-location NWHI source and parent checks.

For the official county test, first download the Census TIGER archive listed in
README.md and pass --census-zip PATH. Requires GDAL/OGR command-line utilities.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, re, subprocess, tempfile, xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "data"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ogr(command):
    return subprocess.run(command, check=True, text=True, capture_output=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census-zip", type=Path, help="Exact TIGER/Line 2024 county ZIP")
    args = ap.parse_args()
    assessment = read_json(HERE / "assessment.json")
    issue = read_json(HERE / "issue-metadata.json")
    assert issue["issue_number"] == 523
    assert sha(DATA / "hierarchy.json") == assessment["provenance_pins"]["hierarchy_sha256"]
    assert assessment["audit_status"] == "in_progress_checkpoint"

    scope = issue["scope_metadata"]
    expected_ids = set(assessment["scope"]["assigned_ids"])
    assert set(scope["member_location_ids"]) == expected_ids
    assert scope["owned_evidence_path"] == assessment["scope"]["owned_path"]
    assert scope["region_id"] == assessment["scope"]["region_id"]
    assert len(expected_ids) == assessment["scope"]["assigned_location_count"] == 7
    assert {x["id"] for x in assessment["locations"]} == expected_ids
    assert sum(x["individual_classification"] == "justified" for x in assessment["locations"]) == 2
    assert sum(x["individual_classification"] == "insufficient-evidence" for x in assessment["locations"]) == 4
    assert sum(x["individual_classification"] == "correction-needed" for x in assessment["locations"]) == 1

    profile_path = DATA / "reference-migrations/macro-improvements-v4/queue-checkpoint/new-location-source-profiles-v4.json.gz"
    profiles = {x["location_id"]: x for x in json.loads(gzip.open(profile_path, "rt", encoding="utf-8").read())}
    candidates_doc = json.loads(gzip.open(DATA / "macro-improvements/oceania-restoration/candidate-report.json.gz", "rt", encoding="utf-8").read())
    candidates = {x["id"]: x for x in candidates_doc["candidates"]}
    osm_report = read_json(DATA / "macro-improvements/macro-coverage-oceania/osm-report.json")
    osm_routes = {x["name"]: x for x in osm_report["routes"]}
    osm_sources = read_json(DATA / "macro-improvements/macro-coverage-oceania/osm-sources.json")
    source_by_hash = {x["sha256"]: x for x in osm_sources}
    input_manifest = read_json(DATA / "macro-improvements/oceania-restoration/inputs.json")
    pinned_inputs = {x["path"]: x["sha256"] for x in input_manifest["files"]}

    part_ids = {}
    world_index = read_json(DATA / "world-index.json")
    for part in world_index["parts"]:
        doc = read_json(DATA / part)
        for feature in doc["features"]:
            fid = feature.get("id") or feature.get("properties", {}).get("id")
            if fid in expected_ids or fid == assessment["neighbor_and_parent_audit"]["administrative_completeness_finding"]["affected_neighbor_id"]:
                part_ids[fid] = feature
    projection = json.loads(gzip.open(DATA / "macro-foundation/current-membership-projection.json.gz", "rt", encoding="utf-8").read())
    projected = {x["id"]: x for x in projection["locations"]}
    groups = {x["id"]: x for x in projection["groups"]}
    assert groups[assessment["scope"]["area_id"]]["descendant_location_count"] == 14
    assert groups[assessment["scope"]["province_id"]]["descendant_location_count"] == 13
    assert len([x for x in projection["locations"] if x.get("region_id") == assessment["scope"]["region_id"]]) == 15

    features = []
    per_location = []
    for item in assessment["locations"]:
        ident = item["id"]
        assert ident in profiles and ident in candidates and ident in part_ids and ident in projected
        candidate = candidates[ident]
        assert candidate["parent_chain"] == item["parent_chain"] == projected[ident]["parent_chain"]
        assert candidate["source_identity"] == item["candidate_source_identity"]
        assert part_ids[ident]["geometry"] == candidate["geometry"], f"current index geometry mismatch: {ident}"
        src = source_by_hash[item["coastline_evidence"]["uncompressed_xml_sha256"]]
        assert src["name"] == item["name"]
        source_path = ROOT / item["coastline_evidence"]["retained_path"]
        assert sha(source_path) == item["coastline_evidence"]["gzip_sha256"]
        assert pinned_inputs[item["coastline_evidence"]["retained_path"]] == item["coastline_evidence"]["gzip_sha256"]
        with gzip.open(source_path, "rb") as f:
            raw = f.read()
        assert hashlib.sha256(raw).hexdigest() == item["coastline_evidence"]["uncompressed_xml_sha256"]
        assert len(raw) == item["coastline_evidence"]["uncompressed_xml_bytes"]
        root = ET.fromstring(raw)
        all_place_values = {"island", "islet", "atoll", "archipelago"}
        inhabited_values = {"city", "town", "village", "hamlet", "isolated_dwelling", "locality"}
        place_features, inhabited_features, population_objects = [], [], []
        infra_counts = {}
        for element in root:
            tags = {x.get("k"): x.get("v") for x in element.findall("tag")}
            for key in ("building", "man_made", "aeroway", "tourism", "place"):
                if key in tags:
                    label = key + ":" + tags[key]
                    infra_counts[label] = infra_counts.get(label, 0) + 1
            obj = {"osm_" + element.tag + "_id": element.get("id"), "name": tags.get("name")}
            if element.tag in {"node", "way", "relation"} and tags.get("place") in all_place_values:
                place_features.append({**obj, "place": tags["place"]})
            if element.tag in {"node", "way", "relation"} and tags.get("place") in inhabited_values:
                inhabited_features.append({**obj, "place": tags["place"]})
            if "population" in tags:
                population_objects.append({"element_type": element.tag, "element_id": element.get("id"), "name": tags.get("name"), "population": tags["population"], "population_date": tags.get("population:date"), "scope": "enclosing Hawaiian state or Honolulu County; not location population"})
        settlement = item["settlement_and_infrastructure"]
        assert place_features == settlement["osm_place_features"]
        assert inhabited_features == settlement["mapped_inhabited_place_features"] == []
        assert dict(sorted(infra_counts.items())) == settlement["osm_infrastructure_tag_counts"]
        assert population_objects == settlement["population_tagged_objects"]
        coast = []
        for way in root.findall("way"):
            tags = {x.get("k"): x.get("v") for x in way.findall("tag")}
            if tags.get("natural") == "coastline":
                coast.append(way)
        assert len(coast) == len(item["coastline_evidence"]["coastline_ways"])
        assert all({x.get("k"): x.get("v") for x in w.findall("tag")}.get("source") in {"NOAA U.S. Vector Shoreline", "NOAA U.S. Vector Shoreline;Mapbox", "Mapbox", None} for w in coast)
        route = osm_routes[item["name"]]
        assert route["complete_ring_reconstruction"] and not route["missing_node_ways"] and not route["unclosed_chains"]
        assert route["closed_land_rings"] == item["coastline_evidence"]["reconstruction"]["land_rings"]
        feature = {"type": "Feature", "id": ident, "properties": {"name": item["name"], "id": ident}, "geometry": candidate["geometry"]}
        features.append(feature)
        per_location.append({"name": item["name"], "coastline_ways": len(coast), "land_rings": route["closed_land_rings"], "area_km2": route["source_land_area_km2"]})

    # Reconstruct and test Laysan's mapped inland-water ring against the accepted outer land polygon.
    laysan_id = next(x["id"] for x in assessment["locations"] if x["name"] == "Laysan")
    laysan_path = ROOT / next(x["coastline_evidence"]["retained_path"] for x in assessment["locations"] if x["id"] == laysan_id)
    root = ET.parse(gzip.open(laysan_path, "rb")).getroot()
    nodes = {x.get("id"): [float(x.get("lon")), float(x.get("lat"))] for x in root.findall("node")}
    lake = next(w for w in root.findall("way") if w.get("id") == "170022053")
    lake_tags = {x.get("k"): x.get("v") for x in lake.findall("tag")}
    lake_refs = [x.get("ref") for x in lake.findall("nd")]
    assert lake_tags.get("natural") == "water" and lake_tags.get("water") == "lagoon" and lake_tags.get("salt") == "yes"
    assert len(lake_refs) == 57 and lake_refs[0] == lake_refs[-1] and all(n in nodes for n in lake_refs)
    lake_feature = {"type": "Feature", "properties": {"id": "laysan-lagoon"}, "geometry": {"type": "Polygon", "coordinates": [[nodes[n] for n in lake_refs]]}}

    with tempfile.TemporaryDirectory(prefix="worldatlas-nwhi-") as temp:
        temp = Path(temp)
        (temp / "islands.json").write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
        (temp / "lake.json").write_text(json.dumps({"type": "FeatureCollection", "features": [lake_feature]}), encoding="utf-8")
        admin_id = assessment["neighbor_and_parent_audit"]["administrative_completeness_finding"]["affected_neighbor_id"]
        assert admin_id in part_ids
        (temp / "honolulu-core.json").write_text(json.dumps({"type": "FeatureCollection", "features": [part_ids[admin_id]]}), encoding="utf-8")
        gpkg = temp / "check.gpkg"
        ogr(["ogr2ogr", "-f", "GPKG", str(gpkg), str(temp / "islands.json"), "-nlt", "PROMOTE_TO_MULTI"])
        ogr(["ogr2ogr", "-update", str(gpkg), str(temp / "lake.json"), "-nln", "lake", "-nlt", "PROMOTE_TO_MULTI"])
        result = ogr(["ogrinfo", "-q", "-dialect", "SQLite", str(gpkg), "-sql", "SELECT ST_Contains(i.geom,l.geom) AS lake_inside, ST_Intersects(i.geom,l.geom) AS lake_intersects FROM islands i JOIN lake l ON i.name='Laysan'"])
        assert "lake_inside (Integer) = 1" in result and "lake_intersects (Integer) = 1" in result
        ogr(["ogr2ogr", "-update", str(gpkg), str(temp / "honolulu-core.json"), "-nln", "honolulu_core", "-nlt", "PROMOTE_TO_MULTI"])
        overlap = ogr(["ogrinfo", "-q", "-dialect", "SQLite", str(gpkg), "-sql", "SELECT i.name, ST_Intersects(h.geom,i.geom) AS intersects FROM islands i CROSS JOIN honolulu_core h"])
        assert overlap.count("intersects (Integer) = 0") == 7, overlap

        admin = assessment["neighbor_and_parent_audit"]["administrative_completeness_finding"]
        county_zip = args.census_zip
        if county_zip:
            expected_hash = "04e668d3502757c837c13444730547cd967f28a2c49aeffb873d1792ab2cb97b"
            assert sha(county_zip) == expected_hash, "wrong TIGER 2024 county archive"
            county_gpkg = temp / "county.gpkg"
            ogr(["ogr2ogr", "-f", "GPKG", str(county_gpkg), f"/vsizip/{county_zip.resolve()}/tl_2024_us_county.shp", "-where", "GEOID = '15003'", "-nlt", "PROMOTE_TO_MULTI"])
            ogr(["ogr2ogr", "-update", str(county_gpkg), str(temp / "islands.json"), "-nln", "islands", "-nlt", "PROMOTE_TO_MULTI"])
            result = ogr(["ogrinfo", "-q", "-dialect", "SQLite", str(county_gpkg), "-sql", "SELECT i.name, ST_Contains(c.geom,i.geom) AS contained, ST_Area(ST_Intersection(c.geom,i.geom))/ST_Area(i.geom) AS ratio FROM islands i CROSS JOIN tl_2024_us_county c WHERE c.GEOID='15003' ORDER BY i.name"])
            assert result.count("contained (Integer) = 1") == 7, result
            ratios = [float(x) for x in re.findall(r"ratio \(Real\) = ([0-9.eE+-]+)", result)]
            assert len(ratios) == 7 and all(math.isclose(x, 1.0, rel_tol=1e-9, abs_tol=1e-9) for x in ratios), result
            per_location.append({"administrative_test":"all seven wholly contained by 2024 Census Honolulu County GEOID 15003"})
        else:
            print("NOTE: Census TIGER polygon containment not rerun; pass --census-zip to verify the recorded official boundary test.")

    print("PASS: exact 7/7 issue identities; current v5 hierarchy/index geometries and complete parent chains; pinned source and OSM archive hashes; all 7 complete coastline reconstructions; Laysan lagoon ring lies inside candidate dry-land polygon; current 13/14/15 parent counts")
    if args.census_zip:
        print("PASS: verified TIGER archive hash and ST_Contains for all seven locations against Honolulu County GEOID 15003")
    print(json.dumps(per_location, ensure_ascii=False, separators=(",", ":")))

if __name__ == "__main__":
    main()
