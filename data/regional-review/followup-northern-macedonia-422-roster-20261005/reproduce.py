#!/usr/bin/env python3
"""Reproduce the scoped MKD 84-to-80 roster and official-layer overlap screen.

The current AKN geometry is not retained: its service supplies no reuse terms.
This script restores it in memory, checks the exact observed response SHA-256,
and writes only the owned crosswalk output. Python requirements: Shapely 2 and
pyproj. Source attributes are transcribed from the official NTES 2019 roster in
official-roster.json; response hashes and restoration URLs are in SOURCES.md.
"""
from __future__ import annotations

import hashlib
import io
import json
import statistics
import struct
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/followup-northern-macedonia-422-roster-20261005"
BASELINE = ROOT / "data/regional-review/regional-review-3c4fe25a21fa428d"
SOURCE_FILE = BASELINE / "source/gb/gb-MKD-ADM2.geojson"
ASSESSMENTS_FILE = BASELINE / "source/subject-assessments.json"
ROSTER_FILE = PACKET / "official-roster.json"
OUTPUT_FILE = PACKET / "crosswalk-results.json"
HDX_ZIP = PACKET / "source/hdx-rimwge/mkd_admn_adm_py_eurogeographics-ntes_pp.zip"

SOURCE_SHA256 = "0a0d7340810fb353c3faa37ab9afea20830ce6124083ffe6321182277da61d01"
AKN_URL = (
    "https://portal.app.gov.mk/arcgis/rest/services/"
    "Servis_za_opsti_podatoci_od_AKN_2022/MapServer/4/query"
)
AKN_PARAMS = {
    "where": "1=1",
    "outFields": "NAME,NAMEMK,MaticenBro,Code_TU",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "geojson",
}
AKN_SHA256 = "2f5832c11ffdf4a22a4825db399cf40d31645d6340353ce4fe166e433a27efea"
AKN_ATTRIBUTE_SHA256 = "ffb4c27c6b08291b0fa1798c911f0108c42c0aad49b4ccf2588a32520e51d6ce"
HDX_SHA256 = "dabdc4f606584f9df0410fd3faaaa1a0b932a944d0a9b3015078fc4e1a54d7fb"

sys.path.insert(0, str(ROOT / "scripts"))
from evidence.geometry import METHOD as GEOMETRY_METHOD
from evidence.geometry import VERSION as GEOMETRY_VERSION
from evidence.geometry import land_area_m2

OLD_KICHEVO_UNITS = {"Drugovo", "Vraneshtitsa", "Zajas", "Oslomej"}
FORMER_UNITS = {"Drugovo", "Vraneshtitsa", "Zajas", "Oslomej", "Kichevo"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_code(value: str) -> str:
    return value.strip().translate(str.maketrans({"М": "M", "К": "K"}))


def land_area_or_zero(geometry) -> float:
    if geometry.is_empty or geometry.geom_type not in ("Polygon", "MultiPolygon"):
        return 0.0
    return land_area_m2(geometry)


def read_hdx_adm4(raw_zip: bytes):
    """Read only the standard Polygon SHP/DBF record layout from retained source."""
    with ZipFile(io.BytesIO(raw_zip)) as archive:
        shp_name = next(name for name in archive.namelist()
                        if "_adm4_" in name and name.endswith(".shp"))
        shp = archive.read(shp_name)
        dbf = archive.read(shp_name[:-3] + "dbf")
        encoding = archive.read(shp_name[:-3] + "CPG").decode("ascii").strip()
    if struct.unpack("<i", shp[32:36])[0] != 5:
        raise SystemExit("HDX ADM4 source is not Polygon shape type")
    header_length = struct.unpack("<H", dbf[8:10])[0]
    record_length = struct.unpack("<H", dbf[10:12])[0]
    fields, offset = [], 32
    while dbf[offset] != 0x0D:
        descriptor = dbf[offset:offset + 32]
        fields.append((descriptor[:11].split(b"\0")[0].decode("ascii"), descriptor[16]))
        offset += 32
    rows = []
    row_count = struct.unpack("<I", dbf[4:8])[0]
    for index in range(row_count):
        record = dbf[header_length + index * record_length:header_length + (index + 1) * record_length]
        cursor, attributes = 1, {}
        for name, width in fields:
            raw_value = record[cursor:cursor + width]
            cursor += width
            value = raw_value.decode(encoding).strip()
            if value:
                attributes[name] = value
        rows.append(attributes)
    geometries, cursor = {}, 100
    for index in range(row_count):
        word_count = struct.unpack(">i", shp[cursor + 4:cursor + 8])[0]
        content = shp[cursor + 8:cursor + 8 + word_count * 2]
        shape_type = struct.unpack("<i", content[:4])[0]
        part_count = struct.unpack("<i", content[36:40])[0]
        point_count = struct.unpack("<i", content[40:44])[0]
        if shape_type != 5 or part_count != 1:
            raise SystemExit("Unexpected multipart/non-polygon HDX source geometry")
        point_start = 44 + 4 * part_count
        points = [struct.unpack("<dd", content[point_start + i * 16:point_start + (i + 1) * 16])
                  for i in range(point_count)]
        geometries[rows[index]["Name4_E"]] = shape({"type": "Polygon", "coordinates": [points]})
        cursor += 8 + word_count * 2
    if cursor != len(shp) or len(rows) != row_count or len(geometries) != row_count:
        raise SystemExit("HDX ADM4 shapefile records are incomplete or duplicated")
    return rows, geometries


def main() -> None:
    raw_source = SOURCE_FILE.read_bytes()
    if sha256(raw_source) != SOURCE_SHA256:
        raise SystemExit("Pinned geoBoundaries source hash changed")
    source = json.loads(raw_source)
    source_features = source["features"]
    hdx_raw = HDX_ZIP.read_bytes()
    if sha256(hdx_raw) != HDX_SHA256:
        raise SystemExit("Pinned CC-BY HDX source archive hash changed")
    hdx_rows, hdx_geometries = read_hdx_adm4(hdx_raw)
    hdx_by_name = {row["Name4_E"]: row for row in hdx_rows}
    source_by_name = {feature["properties"]["shapeName"]: feature for feature in source_features}
    if len(source_features) != 84 or set(source_by_name) != set(hdx_by_name):
        raise SystemExit("GeoBoundaries source names/count differ from retained HDX ADM4 source")
    assessments = read_json(ASSESSMENTS_FILE)
    assessment_by_id = {
        x["location_id"]: x for x in assessments["subjects"]
        if x["location_id"].startswith("gb:MKD:ADM2:")
    }
    roster = read_json(ROSTER_FILE)
    roster_units = {x["code"]: x for x in roster["municipalities"]}
    roster_regions = {x["code"]: x for x in roster["regions"]}
    hierarchy = {x["id"]: x for x in read_json(ROOT / "data/hierarchy.json")}
    expected_ids = sorted(assessment_by_id)
    if len(expected_ids) != 84 or len(source_features) != 84:
        raise SystemExit("Expected exact 84-subject issue scope and source features")

    url = AKN_URL + "?" + urllib.parse.urlencode(AKN_PARAMS)
    with urllib.request.urlopen(url, timeout=60) as response:
        raw_akn = response.read()
    if sha256(raw_akn) != AKN_SHA256:
        raise SystemExit("AKN geometry response differs from the reviewed response hash")
    akn = json.loads(raw_akn)
    coded_features = [
        feature for feature in akn["features"]
        if canonical_code(feature["properties"].get("Code_TU", ""))
    ]
    code_by_feature = {
        feature["properties"]["Code_TU"]: feature for feature in coded_features
    }
    code_by_feature = {
        canonical_code(code): feature for code, feature in code_by_feature.items()
    }
    if len(akn["features"]) != 82 or len(coded_features) != 80:
        raise SystemExit("AKN service feature / municipality-coded counts changed")
    if len(code_by_feature) != 80 or set(code_by_feature) != set(roster_units):
        raise SystemExit("AKN municipality codes do not equal the official NTES roster")

    source_to_wgs84 = Transformer.from_crs("EPSG:4258", "EPSG:4326", always_xy=True).transform
    hdx_vs_geoboundaries = []
    for name, hdx_geometry in hdx_geometries.items():
        original = transform(source_to_wgs84, hdx_geometry)
        published = shape(source_by_name[name]["geometry"])
        delta = land_area_or_zero(original.symmetric_difference(published)) / land_area_m2(original)
        hdx_vs_geoboundaries.append(delta)
    exact_geometry_count = sum(delta < 1e-8 for delta in hdx_vs_geoboundaries)
    if exact_geometry_count != 84:
        raise SystemExit("geoBoundaries geometries differ materially from retained HDX source")
    current_geometries = [
        shape(code_by_feature[code]["geometry"])
        for code in sorted(code_by_feature)
    ]
    current_codes = sorted(code_by_feature)
    tree = STRtree(current_geometries)
    rows = []
    for feature in source_features:
        props = feature["properties"]
        shape_id = props["shapeID"]
        subject_id = f"gb:MKD:ADM2:{shape_id}"
        if subject_id not in assessment_by_id:
            raise SystemExit(f"Source shape is outside exact reviewed scope: {shape_id}")
        record = assessment_by_id[subject_id]
        hdx = hdx_by_name[props["shapeName"]]
        geometry = shape(feature["geometry"])
        geometry_area = land_area_m2(geometry)
        intersections = []
        for index in tree.query(geometry):
            current_index = int(index)
            intersection_area = land_area_or_zero(geometry.intersection(
                current_geometries[current_index]
            ))
            if intersection_area > 0:
                code = current_codes[current_index]
                intersections.append((intersection_area, code))
        if not intersections:
            raise SystemExit(f"No current official overlap for {subject_id}")
        intersections.sort(reverse=True)
        winning_area, winning_code = intersections[0]
        if props["shapeName"] in FORMER_UNITS:
            expected_code = "MK00307"
            outcome = (
                "former_municipality_merged_into_current_kichevo"
                if props["shapeName"] in OLD_KICHEVO_UNITS
                else "historic_kichevo_component_of_current_municipality"
            )
        else:
            expected_code = winning_code
            outcome = "current_roster_unit_spatially_corresponds"
        if winning_code != expected_code:
            raise SystemExit(
                f"Unexpected official spatial match for {subject_id}: "
                f"{winning_code} != {expected_code}"
            )
        if winning_code not in roster_units:
            raise SystemExit(f"No official NTES 2019 roster code: {winning_code}")
        target = roster_units[winning_code]
        parent = hierarchy[record["parent_id"]]
        region_code = winning_code[:5]
        region = roster_regions[region_code]
        if parent["name"].casefold() != region["name"].casefold():
            raise SystemExit(f"Atlas parent differs from current NTES region: {record['parent_id']} / {region_code}")
        if hdx["Name3_E"].casefold() != region["name"].casefold():
            raise SystemExit(f"Source statistical-region name differs from the current roster: {subject_id}")
        if props["shapeName"] in FORMER_UNITS:
            native_label_relation = "historical source label; current target is a merger crosswalk"
        elif hdx.get("Name4_L", "") == target.get("native_name", ""):
            native_label_relation = "exact native-script label match"
        elif hdx.get("Name4_E", "") == target.get("name", ""):
            native_label_relation = "English label matches; source native-script label differs"
        else:
            native_label_relation = "official-name spelling variant; code and spatial crosswalk inspected"
        rows.append({
            "location_id": subject_id,
            "source_shape_id": shape_id,
            "source_name": props["shapeName"],
            "source_native_name": hdx.get("Name4_L", ""),
            "hdx_source_code": canonical_code(hdx.get("SHN4", "")),
            "hdx_source_statistical_region": hdx["Name3_E"],
            "atlas_parent_id": record["parent_id"],
            "current_ntes_code": winning_code,
            "current_ntes_name": target["name"],
            "current_ntes_native_name": target["native_name"],
            "native_label_relation": native_label_relation,
            "current_ntes_region_code": region_code,
            "current_ntes_region_name": region["name"],
            "atlas_parent_name": parent["name"],
            "outcome": outcome,
            "source_polygon_share_overlapping_target": winning_area / geometry_area,
            "target_overlap_ranked_codes": [
                {"code": code, "name": roster_units[code]["name"],
                 "source_area_share": area / geometry_area}
                for area, code in intersections[:3]
            ],
        })

    rows.sort(key=lambda row: row["location_id"])
    if {row["location_id"] for row in rows} != set(expected_ids):
        raise SystemExit("Crosswalk subject IDs differ from the pinned issue scope")
    counts = {}
    for row in rows:
        counts[row["current_ntes_code"]] = counts.get(row["current_ntes_code"], 0) + 1
    if counts.get("MK00307") != 5 or len(counts) != 80:
        raise SystemExit("Expected 5 source shapes to current Kichevo and 80 target codes")
    if sum(row["outcome"] == "current_roster_unit_spatially_corresponds" for row in rows) != 79:
        raise SystemExit("Expected 79 direct current roster matches")
    hdx_code_counts = Counter(canonical_code(row.get("SHN4", "")) for row in hdx_rows)
    repeated_hdx_codes = {code: count for code, count in hdx_code_counts.items() if count > 1}
    if repeated_hdx_codes != {"MK00307": 5, "MK00809": 10}:
        raise SystemExit("Unexpected non-unique source SHN4 codes; do not use SHN4 as feature identity")

    # Coverage is a descriptive diagnostic only. A mismatch may be source vintage,
    # scale/generalization or boundary change; it cannot certify legal boundaries.
    source_geometries = [shape(f["geometry"]) for f in source_features]
    source_union = unary_union(source_geometries)
    target_coverages = []
    target_coverage_rows = []
    for code in current_codes:
        target_geometry = current_geometries[current_codes.index(code)]
        covered_area = land_area_m2(source_union.intersection(target_geometry))
        coverage = covered_area / land_area_m2(target_geometry)
        target_coverages.append(coverage)
        target_coverage_rows.append({
            "code": code,
            "name": roster_units[code]["name"],
            "source_union_coverage_share": coverage,
            "source_shapes_with_positive_overlap": sum(
                source_geometries[i].intersection(target_geometry).area > 0
                for i in range(len(source_geometries))
            ),
        })
    target_coverage_rows.sort(key=lambda x: x["source_union_coverage_share"])
    kichevo_geometry = current_geometries[current_codes.index("MK00307")]
    old_kichevo_features = [
        shape(f["geometry"])
        for f in source_features if f["properties"]["shapeName"] in FORMER_UNITS
    ]
    kichevo_union_coverage = unary_union(old_kichevo_features).intersection(
        kichevo_geometry
    )
    kichevo_union_coverage = land_area_m2(kichevo_union_coverage) / land_area_m2(kichevo_geometry)

    result = {
        "issue": 995,
        "retrieved_at_utc": "2026-10-05",
        "source_geojson_sha256": SOURCE_SHA256,
        "retained_hdx_source_archive": {
            "bytes": len(hdx_raw),
            "sha256": sha256(hdx_raw),
            "adm4_shape_records": len(hdx_geometries),
            "unique_source_codes": len(hdx_code_counts),
            "repeated_codes": repeated_hdx_codes,
            "geoBoundaries_geometry_equivalence_count": exact_geometry_count,
            "maximum_ellipsoidal_symmetric_difference_fraction": max(hdx_vs_geoboundaries),
        },
        "official_akn_response": {
            "url": url,
            "bytes": len(raw_akn),
            "sha256": sha256(raw_akn),
            "service_layer": "Servis_za_opsti_podatoci_od_AKN_2022 / layer 4",
            "returned_features": len(akn["features"]),
            "municipality_coded_features": len(coded_features),
            "unique_municipality_codes": len(code_by_feature),
            "attribute_only_response_sha256": AKN_ATTRIBUTE_SHA256,
            "license_status": "unknown; no layer reuse terms or copyright text",
            "geometry_retained": False,
        },
        "method": {
            "software": "Python 3.12; Shapely 2.1.2; pyproj 3.7.2",
            "coordinate_order": "longitude-latitude",
            "input_crs": "EPSG:4326",
            "area_method": GEOMETRY_METHOD,
            "area_helper_version": GEOMETRY_VERSION,
            "method": "source polygon area intersected with current AKN municipality polygons; maximum-area target, with official current NTES code roster as target registry",
            "warning": "Area overlap supports a spatial crosswalk and flags geometry differences; it does not certify legal boundaries, epochs or correct source geometry.",
        },
        "summary": {
            "source_shapes": len(rows),
            "current_official_municipalities": len(roster_units),
            "direct_current_roster_matches": 79,
            "historic_kichevo_source_rows": 5,
            "direct_native_label_exact_matches": sum(row["native_label_relation"] == "exact native-script label match" for row in rows),
            "direct_native_label_variants_or_omissions": sum(row["native_label_relation"] in {"English label matches; source native-script label differs", "official-name spelling variant; code and spatial crosswalk inspected"} for row in rows),
            "four_historical_units_to_kichevo": 4,
            "old_kichevo_component_to_kichevo": 1,
            "distinct_current_target_codes_covered": len(counts),
            "parent_region_assignments_matching_ntes": 1,
            "unique_hdx_source_code_values": len(hdx_code_counts),
            "nonunique_hdx_source_code_groups": repeated_hdx_codes,
            "min_source_overlap_share": min(row["source_polygon_share_overlapping_target"] for row in rows),
            "median_source_overlap_share": statistics.median(row["source_polygon_share_overlapping_target"] for row in rows),
            "min_current_municipality_area_covered_by_source_union": min(target_coverages),
            "minimum_dojran_target_area_covered_by_source_union": next(
                row["source_union_coverage_share"] for row in target_coverage_rows if row["code"] == "MK00406"
            ),
            "median_current_municipality_area_covered_by_source_union": statistics.median(target_coverages),
            "kichevo_area_covered_by_union_of_five_legacy_shapes": kichevo_union_coverage,
            "source_geometry_valid_features": sum(g.is_valid for g in source_geometries),
            "current_geometry_valid_features": sum(g.is_valid for g in current_geometries),
        },
        "current_target_coverage": target_coverage_rows,
        "rows": rows,
    }
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    print(f"wrote {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
