#!/usr/bin/env python3
"""Reproduce current indexed overlap for the two #569 island packets.

This is a read-only geometry comparison. Inputs are fetched from the exact
baseline Git tree so sparse checkouts need not materialize source archives.
"""
import gzip
import hashlib
import json
import math
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True

from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[4]
PACKET = Path(__file__).resolve().parent
BOUNTY = ROOT / "data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands"
BASELINE = "3e22e5a2562526e5c9dc3d1aa87c5cc2c3e2e5bc"
ARCHIVE_COMMIT = "4afe1cb250fe68f5c63022d9583b3b89b9e607a2"
SUBJECTS = [
    {
        "name": "Nukunonu",
        "packet": PACKET,
        "id": "atlas:macro-coverage:location:a0457f0d44c94b71f00d",
        "source_path": "data/macro-improvements/macro-coverage-oceania/osm-2af0d96ae4f6.xml.gz",
        "source_sha256": "ade053ac91d0f2f4b6d7a033bba95c3fd39c2468b55b58ab14b2120e8420fb07",
        "raw_sha256": "0b150bc8b2675fceeca0fca17661d5c373cc1381c4c7667b92b0e8cb4e0dbad4",
        "gshhg_ids_key": "gshhg_components",
        "osm_rows_key": "ring_inventory",
    },
    {
        "name": "Bounty Islands",
        "packet": BOUNTY,
        "id": "atlas:macro-coverage:location:73281d3672f84a47a770",
        "source_path": "data/macro-improvements/macro-coverage-oceania/osm-28c1ddf724e1.xml.gz",
        "source_sha256": "45545b5d4cdf82c3bcab305a437cdf0c388a515df9b6d20857a51ba04de7af18",
        "raw_sha256": "9bb048bfe6efb335bffbe08bda484a0283571eb7b6f839e9e0e99268ca8f177c",
        "gshhg_ids_key": "gshhg_components",
        "osm_rows_key": "osm_ring_inventory",
    },
]


def require(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)


def blob(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def exists_in_tree(commit, path):
    return subprocess.run(["git", "cat-file", "-e", f"{commit}:{path}"], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render_json(value, level=0):
    """Stable readable JSON with one-line objects for long component inventories."""
    pad = "  " * level
    child_pad = "  " * (level + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        rows = [f"{child_pad}{json.dumps(key, ensure_ascii=False)}: {render_json(item, level + 1)}"
                for key, item in value.items()]
        return "{\n" + ",\n".join(rows) + f"\n{pad}}}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if len(value) > 8 and all(isinstance(item, dict) for item in value):
            rows = [child_pad + json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                    for item in value]
        else:
            rows = [child_pad + render_json(item, level + 1) for item in value]
        return "[\n" + ",\n".join(rows) + f"\n{pad}]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def read_area_helper():
    sys.path.insert(0, str(ROOT / "scripts"))
    from ellipsoidal_area import area
    return area


def parse_osm(gzip_bytes):
    raw = gzip.decompress(gzip_bytes)
    xml = ET.fromstring(raw)
    nodes = {node.get("id"): (float(node.get("lon")), float(node.get("lat")))
             for node in xml.findall("node")}
    rings = {}
    for way in xml.findall("way"):
        tags = {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
        if tags.get("natural") != "coastline":
            continue
        refs = [nd.get("ref") for nd in way.findall("nd")]
        require(len(refs) >= 4 and refs[0] == refs[-1], f"closed OSM coastline ring {way.get('id')}")
        require(all(ref in nodes for ref in refs), f"complete OSM nodes for way {way.get('id')}")
        geometry = Polygon([nodes[ref] for ref in refs])
        require(geometry.is_valid and geometry.area > 0, f"valid OSM ring {way.get('id')}")
        rings[way.get("id")] = geometry
    return raw, rings


def parse_gshhg(gzip_bytes, wanted_ids):
    native = gzip.decompress(gzip_bytes)
    records = {}
    offset = 0
    while offset < len(native):
        start = offset
        fields = struct.unpack_from(">IIIiiiiIIii", native, offset)
        lid, count, flag, west, east, south, north, _area, _area_full, container, ancestor = fields
        offset += 44
        require(count >= 4 and offset + count * 8 <= len(native), f"GSHHG record bounds for {lid}")
        coords = []
        for x, y in struct.iter_unpack(">ii", native[offset:offset + count * 8]):
            lon = x / 1_000_000
            if lon > 180:
                lon -= 360
            coords.append((lon, y / 1_000_000))
        polygon = Polygon(coords)
        offset += count * 8
        records[lid] = {
            "geometry": polygon,
            "level": flag & 255,
            "container": container,
            "ancestor": ancestor,
            "count": count,
            "header_bounds": [west / 1e6, south / 1e6, east / 1e6, north / 1e6],
            "record_sha256": digest(native[start:offset]),
        }
    require(offset == len(native), "complete GSHHG record stream")
    require(wanted_ids <= set(records), "all referenced GSHHG source records are retained")
    return native, records


def gshhg_land(lid, records):
    item = records[lid]
    geometry = item["geometry"]
    require(geometry.is_valid and not geometry.is_empty, f"valid original GSHHG source record {lid}")
    child_level = item["level"] + 1
    holes = [r["geometry"] for r in records.values()
             if r["level"] == child_level and r["container"] == lid]
    if holes:
        geometry = geometry.difference(unary_union(holes))
    require(geometry.is_valid and not geometry.is_empty, f"valid GSHHG land polygon {lid}")
    return geometry


def current_components(feature):
    return [shape({"type": "Polygon", "coordinates": coordinates})
            for coordinates in feature["geometry"]["coordinates"]]


def geometry_rows(rows, source_geometries, components, area):
    source_union = unary_union(list(source_geometries.values()))
    component_summaries = []
    for source_id, source_geometry in sorted(source_geometries.items(), key=lambda pair: str(pair[0])):
        source_area = area(source_geometry)
        overlaps = []
        for component_index, component in enumerate(components):
            intersection_area = area(source_geometry.intersection(component))
            if intersection_area > max(source_area * 1e-12, 1e-8):
                overlaps.append({
                    "indexed_component": component_index,
                    "intersection_area_km2": intersection_area / 1e6,
                    "source_component_covered_fraction": intersection_area / source_area,
                })
        total_intersection = area(source_geometry.intersection(unary_union(components)))
        component_summaries.append({
            "source_component_id": str(source_id),
            "source_area_km2": source_area / 1e6,
            "covered_area_km2": total_intersection / 1e6,
            "source_component_covered_fraction": total_intersection / source_area if source_area else None,
            "intersecting_indexed_components": overlaps,
        })
    source_area_sum = math.fsum(area(g) for g in source_geometries.values())
    union_area = area(source_union)
    covered_union_area = area(source_union.intersection(unary_union(components)))
    return {
        "source_component_count": len(source_geometries),
        "component_summed_source_area_km2": source_area_sum / 1e6,
        "source_union_area_km2": union_area / 1e6,
        "source_union_covered_area_km2": covered_union_area / 1e6,
        "source_union_covered_fraction": covered_union_area / union_area if union_area else None,
        "components": component_summaries,
    }


def main(check_only=False):
    area = read_area_helper()
    index_bytes = blob(BASELINE, "data/world-index.json")
    additions_bytes = blob(BASELINE, "data/geography/source-restoration-additions.json")
    hierarchy_bytes = blob(BASELINE, "data/hierarchy.json")
    manifest_bytes = blob(BASELINE, "data/geographic-releases/current-manifest.json")
    manifest = json.loads(manifest_bytes)
    release_path = "data/geographic-releases/" + manifest["path"]
    release_bytes = blob(BASELINE, release_path)
    require(digest(release_bytes) == manifest["sha256"], "current release matches its manifest SHA-256")
    index = json.loads(index_bytes)
    indexed_paths = index["parts"]
    require("geography/source-restoration-additions.json" in indexed_paths,
            "restoration additions are a current world-index part")
    additions = json.loads(additions_bytes)
    hierarchy = json.loads(hierarchy_bytes)
    hierarchy_by_id = {entity.get("id"): entity for entity in hierarchy}
    by_id = {feature.get("properties", {}).get("id"): feature
             for feature in additions.get("features", [])}

    osm_pins = {}
    gshhg_wanted = set()
    assessments = {}
    osm_geometries = {}
    gshhg_ids = {}
    for item in SUBJECTS:
        assessment_path = item["packet"] / "assessment.json"
        assessment = json.loads(assessment_path.read_text())
        assessments[item["name"]] = assessment
        audit = assessment["audit"]
        archive_context = audit.get("historical_comparison_context", {})
        require(archive_context.get("comparison_commit") == ARCHIVE_COMMIT,
                f"{item['name']} assessment labels its old comparison as archived")
        require(all("archived_pre_restoration_comparison" in row
                    for row in audit[item["osm_rows_key"]]),
                f"{item['name']} per-ring old comparisons are explicitly archived")
        require(all("all_location_overlap_fraction" not in row and
                    "intended_region_overlap_fraction" not in row
                    for row in audit[item["osm_rows_key"]]),
                f"{item['name']} archived overlap fields are not presented as current")
        osm_bytes = blob(BASELINE, item["source_path"])
        require(digest(osm_bytes) == item["source_sha256"], f"{item['name']} OSM compressed hash")
        raw, geometries = parse_osm(osm_bytes)
        require(digest(raw) == item["raw_sha256"], f"{item['name']} OSM decompressed hash")
        pinned_ids = {row["osm_way_ids"][0] for row in audit[item["osm_rows_key"]]}
        require(pinned_ids == set(geometries), f"{item['name']} OSM assessment/source ID parity")
        osm_geometries[item["name"]] = geometries
        osm_pins[item["name"]] = {
            "path": item["source_path"],
            "retrieved": assessment.get("source", {}).get("retrieved")
                or assessment.get("source", {}).get("retrieved_on") or "2026-10-02",
            "license": "Open Database License 1.0; © OpenStreetMap contributors",
            "compressed_sha256": digest(osm_bytes),
            "decompressed_sha256": digest(raw),
            "coastline_ring_count": len(geometries),
        }
        gshhg_ids[item["name"]] = {int(row["gshhg_id"]) for row in audit[item["gshhg_ids_key"]]}
        gshhg_wanted |= gshhg_ids[item["name"]]

    gshhg_path = "data/macro-improvements/macro-coverage-oceania/gshhg-selected-full-records.bin.gz"
    gshhg_bytes = blob(BASELINE, gshhg_path)
    extraction_bytes = blob(BASELINE, "data/macro-improvements/macro-coverage-oceania/gshhg-extraction.json")
    extraction = json.loads(extraction_bytes)
    require(digest(gshhg_bytes) == "7e52c4c7c13ea3b2d35120cc0f1f6832007865750b98f42d5cd9c95162df1df4",
            "GSHHG selected compressed record hash")
    native, records = parse_gshhg(gshhg_bytes, gshhg_wanted)
    require(digest(native) == extraction["selected_native_sha256"], "GSHHG selected native hash")
    require(len(native) == extraction["selected_native_bytes"], "GSHHG selected native byte count")

    archive_osm_bytes = blob(ARCHIVE_COMMIT,
                             "data/macro-improvements/macro-coverage-oceania/osm-report.json")
    archive_gshhg_bytes = blob(ARCHIVE_COMMIT,
                               "data/macro-improvements/macro-coverage-oceania/report.json")
    archive_index_bytes = blob(ARCHIVE_COMMIT, "data/world-index.json")
    archive_osm = json.loads(archive_osm_bytes)
    archive_gshhg = json.loads(archive_gshhg_bytes)
    archive_additions_present = exists_in_tree(ARCHIVE_COMMIT,
                                               "data/geography/source-restoration-additions.json")
    archive_manifest_present = exists_in_tree(ARCHIVE_COMMIT,
                                              "data/geographic-releases/current-manifest.json")
    archive_index = json.loads(archive_index_bytes)
    archive_subject_ids = set()
    for part_path in archive_index["parts"]:
        part = json.loads(blob(ARCHIVE_COMMIT, "data/" + part_path))
        archive_subject_ids.update(feature.get("properties", {}).get("id")
                                   for feature in part.get("features", []))
    require(not archive_additions_present and not archive_manifest_present,
            "archived report predates current manifest and restoration additions")
    require(all(subject["id"] not in archive_subject_ids for subject in SUBJECTS),
            "both restoration feature IDs are absent from the archived comparison index")
    archived_rows = {"osm": {}, "gshhg": {}}
    for subject in SUBJECTS:
        name = subject["name"]
        osm_row = next(route for route in archive_osm["routes"] if route["name"] == name)
        gshhg_row = next(route for route in archive_gshhg["routes"] if route["name"] == name)
        require(osm_row["any_existing_location_covered_fraction"] == 0,
                f"archived OSM report has zero overlap for {name}")
        require(gshhg_row["same_region_covered_fraction"] == 0,
                f"archived GSHHG report has zero same-region overlap for {name}")
        require(not osm_row.get("absent_current_land_components", 0) == 0,
                f"archived OSM report has absent components for {name}")
        archived_rows["osm"][name] = osm_row
        archived_rows["gshhg"][name] = gshhg_row

    output = {
        "schema": "worldatlas-569-current-coverage-v1",
        "recorded_date": "2026-10-07",
        "status": "indexed-overlap-recomputed; geography and hierarchy approval remain open",
        "historical_comparison": {
            "archive_report_commit": ARCHIVE_COMMIT,
            "archive_report_commit_utc": "2026-10-02T22:03:05Z",
            "archive_world_index_sha256": digest(archive_index_bytes),
            "archived_osm_report_sha256": digest(archive_osm_bytes),
            "archived_gshhg_report_sha256": digest(archive_gshhg_bytes),
            "release_manifest_present_at_archive_report_commit": archive_manifest_present,
            "source_restoration_additions_present_at_archive_report_commit": archive_additions_present,
            "interpretation": "The zero-overlap outputs are preserved measurements from this pre-restoration main-index snapshot. They do not describe current indexed coverage.",
        },
        "current_snapshot": {
            "baseline_commit": BASELINE,
            "world_index_sha256": digest(index_bytes),
            "source_restoration_additions_sha256": digest(additions_bytes),
            "hierarchy_sha256": digest(hierarchy_bytes),
            "current_manifest_sha256": digest(manifest_bytes),
            "current_release_path": release_path,
            "current_release_sha256": digest(release_bytes),
            "indexed_part_path": "geography/source-restoration-additions.json",
        },
        "method": {
            "crs": "EPSG:4326; longitude,latitude coordinate order",
            "topology": "Shapely polygon intersection using shortest straight longitude/latitude edges; no snapping, buffering, repair, or source clipping",
            "area": "WGS84 ellipsoid integral for straight source edges (scripts/ellipsoidal_area.py)",
            "coverage_denominator": "union area of one named source family (OSM rings or GSHHG land polygons); each source component is also reported individually",
            "limits": [
                "OSM and GSHHG describe different source vintages, generalization and shoreline conventions.",
                "Geometry overlap measures indexed representation only; it does not establish present-day coastline completeness, a legal boundary, or approval for imports.",
                "The indexed restoration feature is not itself a hierarchy node. Its parent pointer and open semantic review are retained as unresolved engineering/integration work.",
            ],
        },
        "source_pins": {
            "osm": osm_pins,
            "gshhg": {
                "path": gshhg_path,
                "release_date": "2017-06-15",
                "license": "LGPLv3 or later",
                "selected_records_compressed_sha256": digest(gshhg_bytes),
                "selected_records_native_sha256": digest(native),
                "extraction_manifest_sha256": digest(extraction_bytes),
                "selection_method": extraction["method"],
            },
        },
        "subjects": [],
    }

    for subject in SUBJECTS:
        name = subject["name"]
        feature = by_id.get(subject["id"])
        require(feature is not None, f"{name} source-restoration indexed feature is present")
        properties = feature["properties"]
        source_metadata = properties.get("metadata", {})
        require(source_metadata.get("source_raw_sha256") == osm_pins[name]["decompressed_sha256"],
                f"{name} indexed source hash matches the archived OSM extract")
        require(set(source_metadata.get("source_way_ids", [])) == set(osm_geometries[name]),
                f"{name} indexed OSM source-way inventory matches exactly")
        components = current_components(feature)
        require(len(components) == len(osm_geometries[name]), f"{name} indexed component count")
        require(all(component.is_valid and not component.is_empty for component in components),
                f"{name} current indexed component validity")
        parent_id = properties.get("parent_id")
        # The feature has a parent pointer, but the location itself is an indexed source feature,
        # not currently an entity in hierarchy.json. Preserve that distinction in the result.
        parent = hierarchy_by_id.get(parent_id)
        osm_comparison = geometry_rows([], osm_geometries[name], components, area)
        gshhg_geometries = {lid: gshhg_land(lid, records) for lid in gshhg_ids[name]}
        gshhg_comparison = geometry_rows([], gshhg_geometries, components, area)
        require(all(row["source_component_covered_fraction"] >= 1 - 1e-10
                    for row in osm_comparison["components"]),
                f"{name} positive control: each OSM ring is fully found in its indexed component")
        control_way_id = sorted(osm_geometries[name], key=int)[0]
        control_row = next(row for row in osm_comparison["components"]
                           if row["source_component_id"] == control_way_id)
        matched_indexes = {entry["indexed_component"]
                           for entry in control_row["intersecting_indexed_components"]}
        reduced_components = [component for i, component in enumerate(components)
                              if i not in matched_indexes]
        omitted_area = (area(osm_geometries[name][control_way_id].intersection(
            unary_union(reduced_components))) if reduced_components else 0.0)
        omission_fraction = omitted_area / area(osm_geometries[name][control_way_id])
        require(omission_fraction < 1e-10,
                f"{name} negative control: omitting its indexed component removes source-ring coverage")
        all_indexed_area = area(unary_union(components))
        output["subjects"].append({
            "name": name,
            "indexed_feature_id": subject["id"],
            "indexed_feature_name": properties.get("name"),
            "parent_pointer": parent_id,
            "parent_node_present_in_hierarchy": parent is not None,
            "hierarchy_node_present_for_indexed_feature": subject["id"] in hierarchy_by_id,
            "semantic_review_status": (source_metadata.get("semantic_review") or {}).get("status"),
            "indexed_component_count": len(components),
            "indexed_feature_area_km2": all_indexed_area / 1e6,
            "osm_current_indexed_coverage": osm_comparison,
            "gshhg_current_indexed_coverage": gshhg_comparison,
            "archived_comparison_values": {
                "osm_pre_restoration_covered_fraction": archived_rows["osm"][name]["any_existing_location_covered_fraction"],
                "osm_pre_restoration_absent_component_count": archived_rows["osm"][name]["absent_current_land_components"],
                "gshhg_pre_restoration_same_region_covered_fraction": archived_rows["gshhg"][name]["same_region_covered_fraction"],
            },
            "coverage_controls": {
                "positive_osm_ring_way_id": control_way_id,
                "positive_osm_ring_covered_fraction": control_row["source_component_covered_fraction"],
                "negative_control_omitted_component_indices": sorted(matched_indexes),
                "negative_control_covered_fraction_after_omission": omission_fraction,
            },
        })

    output["scope_control"] = {
        "issue_owned_paths": [
            "data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/",
            "data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands/",
        ],
        "generated_files": [
            "data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/current-coverage.json",
            "data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands/current-coverage.json",
        ],
        "outside_owned_path_writes": False,
    }
    nuku_output = dict(output)
    nuku_output["subjects"] = [s for s in output["subjects"] if s["name"] == "Nukunonu"]
    bounty_output = dict(output)
    bounty_output["subjects"] = [s for s in output["subjects"] if s["name"] == "Bounty Islands"]
    expected_outputs = {
        PACKET / "current-coverage.json":
            (render_json(nuku_output) + "\n").encode(),
        BOUNTY / "current-coverage.json":
            (render_json(bounty_output) + "\n").encode(),
    }
    if check_only:
        require(all(path.exists() and path.read_bytes() == payload
                    for path, payload in expected_outputs.items()),
                "both current-coverage.json files match an exact fresh reproduction")
        print("PASS: current #569 coverage reproduces from pinned OSM/GSHHG inputs and baseline index")
    else:
        for path, payload in expected_outputs.items():
            path.write_bytes(payload)
        print("WROTE: Nukunonu and Bounty Islands current-coverage.json")
        for item in output["subjects"]:
            print(item["name"],
                  "OSM", round(item["osm_current_indexed_coverage"]["source_union_covered_fraction"], 12),
                  "GSHHG", round(item["gshhg_current_indexed_coverage"]["source_union_covered_fraction"], 8),
                  "indexed components", item["indexed_component_count"],
                  "hierarchy node", item["hierarchy_node_present_for_indexed_feature"])


if __name__ == "__main__":
    main("--check" in sys.argv)
