#!/usr/bin/env python3
"""Reproduce the scoped Dazhuxian/Dazhu/Dazu location discrepancy lead.

This is a bounded source-location comparison, not an administrative identity
or legal-boundary validator. Official extents are transcribed from the linked
government pages and are reported extents, not polygon geometries.
"""

from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OWNED = ROOT / "data/regional-review/southwest-china-adm2-lineage-449"
SOURCE = ROOT / "data/regional-review/regional-review-365cbd6478904888/source/geoBoundaries-CHN-ADM2.geojson"
ATLAS = ROOT / "data/geography/part-3.json"
OUTPUT_DIR = OWNED / "findings"
SUBJECT = "gb:CHN:ADM2:17275852B74051544695436"
SHAPE_ID = "17275852B74051544695436"
SOURCE_SHA256 = "2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34"
ATLAS_SHA256 = "e28e1ef867d6550ad65964125bd86a8f1d0919e4834e0d920af4046145a00617"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_unique(features: list[dict], predicate, label: str) -> dict:
    rows = [feature for feature in features if predicate(feature)]
    if len(rows) != 1:
        raise ValueError(f"Expected one {label}; found {len(rows)}")
    return rows[0]


def geometry_bbox(feature: dict) -> tuple[list[float], int]:
    points: list[list[float]] = []

    def visit(value):
        if isinstance(value, list) and len(value) >= 2 and all(
            isinstance(number, (int, float)) for number in value[:2]
        ):
            points.append(value[:2])
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(feature["geometry"]["coordinates"])
    if not points:
        raise ValueError("Feature geometry contains no coordinate pairs")
    return [
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    ], len(points)


def dms(degrees: int, minutes: int) -> float:
    return degrees + minutes / 60


def intersects(left: list[float], right: list[float]) -> bool:
    return left[0] <= right[2] and right[0] <= left[2] and left[1] <= right[3] and right[1] <= left[3]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", required=True,
                        help="new JSON filename created exclusively inside this packet's findings directory")
    args = parser.parse_args()
    if (not args.output_name or Path(args.output_name).name != args.output_name
            or args.output_name in {".", ".."} or not args.output_name.endswith(".json")):
        raise ValueError("--output-name must be a simple .json filename")
    if OWNED.is_symlink() or OUTPUT_DIR.is_symlink() or not OUTPUT_DIR.is_dir():
        raise ValueError("Owned findings directory must be a real directory, not a symlink")
    output = OUTPUT_DIR / args.output_name
    source_bytes = SOURCE.read_bytes()
    atlas_bytes = ATLAS.read_bytes()
    if sha256(source_bytes) != SOURCE_SHA256:
        raise ValueError("Pinned geoBoundaries source bytes differ from the recorded baseline")
    if sha256(atlas_bytes) != ATLAS_SHA256:
        raise ValueError("Pinned Atlas part-3 bytes differ from the recorded baseline")

    source = json.loads(source_bytes)
    atlas = json.loads(atlas_bytes)
    source_feature = find_unique(
        source["features"],
        lambda feature: feature.get("properties", {}).get("shapeID") == SHAPE_ID,
        "source shapeID",
    )
    atlas_feature = find_unique(
        atlas["features"],
        lambda feature: feature.get("properties", {}).get("id") == SUBJECT,
        "Atlas subject ID",
    )
    if source_feature["properties"].get("shapeName") != "Dazhuxian":
        raise ValueError("Pinned source name changed")
    if atlas_feature["properties"].get("name") != "Dazhuxian":
        raise ValueError("Atlas subject name changed")
    if atlas_feature["properties"].get("parent_id") != "framework:province:chongqing-municipality:840dd0059ac9":
        raise ValueError("Atlas parent changed")

    source_bbox, source_vertices = geometry_bbox(source_feature)
    atlas_bbox, atlas_vertices = geometry_bbox(atlas_feature)
    source_geometry_sha256 = sha256(json.dumps(source_feature["geometry"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    atlas_geometry_sha256 = sha256(json.dumps(atlas_feature["geometry"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    # Officially stated bounding extents, converted from degrees/minutes.
    # Dazhu County, Dazhou, Sichuan: 106°59′–107°32′ E, 30°20′–31°00′ N.
    dazhu_extent = [dms(106, 59), dms(30, 20), dms(107, 32), 31.0]
    # Dazu District, Chongqing: 105°28′–106°02′ E, 29°23′–29°52′ N.
    dazu_extent = [dms(105, 28), dms(29, 23), dms(106, 2), dms(29, 52)]
    dazhu_intersection = intersects(source_bbox, dazhu_extent)
    dazu_intersection = intersects(source_bbox, dazu_extent)
    if dazhu_intersection or not dazu_intersection:
        raise ValueError("Reported-source extent comparison no longer matches the recorded discrepancy")

    result = {
        "issue": 917,
        "assessment": "candidate-name-location-discrepancy; not a verified identity or boundary correction",
        "subject_id": SUBJECT,
        "source_shape_id": SHAPE_ID,
        "source_name": source_feature["properties"]["shapeName"],
        "atlas_name": atlas_feature["properties"]["name"],
        "atlas_parent_id": atlas_feature["properties"]["parent_id"],
        "historical_geometry": {
            "source": "retained #449 geoBoundaries CHN ADM2 original",
            "source_sha256": SOURCE_SHA256,
            "source_feature_geometry_sha256_canonical_json": source_geometry_sha256,
            "atlas_part": "data/geography/part-3.json at pinned baseline",
            "atlas_part_sha256": ATLAS_SHA256,
            "atlas_feature_geometry_sha256_canonical_json": atlas_geometry_sha256,
        "source_bbox_lon_lat": source_bbox,
            "source_coordinate_pair_count": source_vertices,
        "atlas_bbox_lon_lat": atlas_bbox,
            "atlas_coordinate_pair_count": atlas_vertices,
        },
        "official_reported_extents_lon_lat": {
            "dazhu_county_dazhou_sichuan": {
                "degrees_minutes": "106°59′–107°32′ E, 30°20′–31°00′ N",
                "decimal_bbox": dazhu_extent,
                "publisher": "Dazhu County People's Government",
                "url": "https://www.dazhu.gov.cn/uploadfile/1/Attachment/b28c3b3063.pdf",
                "source_role": "official reported location extent; not boundary geometry",
                "direct_original_retrieval": "connection timeout after three attempts; HTTP 000, zero body bytes, no source hash",
                "reuse_terms": "not retrieved; no source redistribution or extraction permission asserted",
            },
            "dazu_district_chongqing": {
                "degrees_minutes": "105°28′–106°02′ E, 29°23′–29°52′ N",
                "decimal_bbox": dazu_extent,
                "publisher": "Dazu District People's Government",
                "url": "https://www.dazu.gov.cn/qzfbm/qjjxxw/zwxx_53317/gzdt_53319/202211/t20221130_11345280.html",
                "source_role": "official reported location extent; not boundary geometry",
                "direct_original_retrieval": "connection timeout after three attempts; HTTP 000, zero body bytes, no source hash",
                "reuse_terms": "not retrieved; no source redistribution or extraction permission asserted",
            },
        },
        "reproduced_comparisons": {
            "source_bbox_intersects_officially_reported_dazhu_county_extent": dazhu_intersection,
            "source_bbox_intersects_officially_reported_dazu_district_extent": dazu_intersection,
            "overlapping_extent_control_detected": intersects(source_bbox, source_bbox),
            "interpretation": "The source geometry footprint is spatially incompatible with the official reported extent of Dazhu County and overlaps the reported location extent of Dazu District. Extent rectangles are not polygons; overlap is not boundary identity proof.",
        },
        "summary_metrics": {
            "dazhu_reported_extent_disjoint_scoped_features": int(not dazhu_intersection),
            "dazu_reported_extent_overlapping_scoped_features": int(dazu_intersection),
        },
        "engineering_handoff": "Check the original-language name/code attached to the retained geoBoundaries shapeID and Atlas history. Determine whether Dazhuxian is a source-label/transliteration defect for Chongqing Dazu or another documented identity. Preserve the native ID and original source; make no rename, parent, geometry or release change from this lead alone.",
        "uncertainty": [
            "Both government location extents were obtained from indexed official-page text; the original pages/PDFs were not retained or hashed.",
            "Bounding rectangles do not test polygon boundaries, neighboring topology, completeness, components, coastline or legal boundary role.",
            "The indexed official sources do not provide a Chinese source name/code for this geoBoundaries shapeID; candidate identity remains unresolved.",
        ],
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    # Exclusive creation refuses existing files and dangling symlinks rather
    # than overwriting retained evidence or following a link.
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)
    print(json.dumps({"output": str(output.relative_to(ROOT)), "source_bbox_intersects_dazhu": dazhu_intersection, "source_bbox_intersects_dazu": dazu_intersection, "result": result["assessment"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
