#!/usr/bin/env python3
"""Recreate bounded boundary comparisons for regional-review-3e9f1d51da6b0a22.

Requires pyshp and Shapely. Chile's DPA 2023 archive and the original
geoBoundaries country sources are intentionally restored by the reader from
the exact URLs and SHA-256 values in SOURCES.md; do not commit them here.
The Argentina IGN query extract is restored under source-cache/ and checked by hash.
"""
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import shapefile
from shapely import make_valid
from shapely.geometry import shape

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
SCOPE = json.loads((PACKET / "scope.json").read_text())
SOURCE_DIR = PACKET / "source-cache" / "DPA_2023"
ARG_GEOJSON = PACKET / "source-cache" / "ign-argentina-south-generalized.geojson"
OUT = PACKET / "geometry-summary.json"
RECORDS_OUT = PACKET / "geometry-comparisons.jsonl"
SIMPLIFY_DEGREES = 0.001


def norm(value):
    folded = unicodedata.normalize("NFKD", value or "")
    ascii_value = folded.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", ascii_value)


def simplified_iou(left, right):
    if not left.is_valid:
        left = make_valid(left)
    if not right.is_valid:
        right = make_valid(right)
    left = left.simplify(SIMPLIFY_DEGREES, preserve_topology=True)
    right = right.simplify(SIMPLIFY_DEGREES, preserve_topology=True)
    intersection = left.intersection(right).area
    union = left.area + right.area - intersection
    return intersection / union if union else 0.0


def baseline_features():
    expected = {
        "data/geography/part-0.json": "bcad5408720e0f50165e794636fd44e02913e5e4649d73c8aa422b94562d32f3",
        "data/geography/part-2.json": "93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf",
    }
    for relative, digest in expected.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"baseline file is not the pinned v5 snapshot: {relative}")
    wanted = set(SCOPE["member_location_ids"])
    found = {}
    for part in (ROOT / "data/geography/part-0.json", ROOT / "data/geography/part-2.json"):
        for feature in json.loads(part.read_text())["features"]:
            location_id = feature["properties"]["id"]
            if location_id in wanted:
                if location_id in found:
                    raise ValueError(f"duplicate baseline ID: {location_id}")
                found[location_id] = feature
    if set(found) != wanted:
        raise ValueError(f"baseline coverage mismatch: found {len(found)} of {len(wanted)}")
    return found


def chile_index():
    shp = SOURCE_DIR / "COMUNAS" / "COMUNAS_v1.shp"
    reader = shapefile.Reader(str(shp), encoding="utf-8")
    fields = [field[0] for field in reader.fields[1:]]
    index = collections.defaultdict(list)
    for record, geometry in zip(reader.records(), reader.shapes()):
        attributes = dict(zip(fields, record))
        province = re.sub(r"^Provincia de\s+", "", attributes["PROVINCIA"], flags=re.I)
        key = (norm(province), norm(attributes["COMUNA"]))
        index[key].append((attributes, shape(geometry.__geo_interface__)))
    return index, len(reader)


def argentina_index():
    raw = ARG_GEOJSON.read_bytes()
    expected = "3f2b63b4499b01a67274142ec66814997207591090e402ca7bf208b1ac3fc2f3"
    if __import__("hashlib").sha256(raw).hexdigest() != expected:
        raise ValueError("IGN restored query response does not match the inspected source vintage")
    payload = json.loads(raw)
    province_codes = {"26": "chubut", "58": "neuquen", "62": "rionegro", "78": "santacruz", "94": "tierradelfuego"}
    index = collections.defaultdict(list)
    for feature in payload["features"]:
        properties = feature["properties"]
        key = (province_codes.get(str(properties.get("CODPROV"))), norm(properties.get("NAM")))
        index[key].append((properties, shape(feature["geometry"])))
    return index, len(payload["features"])


def main():
    hierarchy = {item["id"]: item["name"] for item in json.loads((ROOT / "data/hierarchy.json").read_text())}
    baseline = baseline_features()
    ch_index, ch_count = chile_index()
    ar_index, ar_count = argentina_index()
    arg_province_key = {
        "framework:province:rio-negro:1609a338a963": "rionegro",
        "framework:province:neuquen:836e7698a123": "neuquen",
        "framework:province:chubut:d2131f4e9ce6": "chubut",
        "framework:province:santa-cruz:45532d6f729d": "santacruz",
        "framework:province:tierra-del-fuego:7cb3e4d5a95a": "tierradelfuego",
        "framework:province:tierra-del-fuego:92e8b3536793": "tierradelfuego",
    }
    chile_aliases = {"marchigue": "marchihue"}
    records = []
    for location_id, feature in baseline.items():
        props = feature["properties"]
        source_id = props["metadata"]["source_id"]
        name = props["name"]
        parent_name = hierarchy[props["parent_id"]]
        old_geometry = shape(feature["geometry"])
        if source_id == "gb:CHL:ADM3":
            province = re.sub(r"^Provincia de\s+", "", parent_name, flags=re.I)
            member_name = chile_aliases.get(norm(name), norm(name))
            matches = ch_index.get((norm(province), member_name), [])
            current_source = "SUBDERE DPA 2023"
        elif source_id == "gb:ARG:ADM2":
            province = arg_province_key[props["parent_id"]]
            matches = ar_index.get((province, norm(name)), [])
            current_source = "IGN ANIDA Departamentos service query"
        else:
            raise ValueError(f"unexpected source for scoped member: {source_id}")
        if len(matches) > 1:
            raise ValueError(f"multiple current source matches for {location_id}")
        record = {
            "id": location_id,
            "name": name,
            "parent_id": props["parent_id"],
            "source_id": source_id,
            "baseline_geometry_type": old_geometry.geom_type,
            "baseline_geometry_valid": old_geometry.is_valid,
            "current_source": current_source,
            "current_match_count": len(matches),
        }
        if matches:
            attributes, current_geometry = matches[0]
            record["current_name"] = attributes.get("COMUNA") or attributes.get("NAM")
            record["current_parent_name"] = attributes.get("PROVINCIA") or {
                "26": "Chubut", "58": "Neuquén", "62": "Río Negro", "78": "Santa Cruz", "94": "Tierra del Fuego"
            }.get(str(attributes.get("CODPROV")))
            record["current_region_name"] = attributes.get("REGION")
            if attributes.get("CODPROV") is not None:
                record["current_parent_code"] = attributes.get("CODPROV")
            record["current_geometry_type"] = current_geometry.geom_type
            record["current_geometry_valid"] = current_geometry.is_valid
            record["baseline_multipart_count"] = len(old_geometry.geoms) if hasattr(old_geometry, "geoms") else 1
            record["current_multipart_count"] = len(current_geometry.geoms) if hasattr(current_geometry, "geoms") else 1
            record["simplified_iou_0_001_degrees"] = round(simplified_iou(old_geometry, current_geometry), 6)
            record["geometry_type_changed"] = old_geometry.geom_type != current_geometry.geom_type
        records.append(record)
    records.sort(key=lambda item: item["id"])
    summary = {
        "method": "Join on exact source unit name (with the documented Marchigüe/Marchihue alias) and parent; repair invalid geometry for overlay with Shapely make_valid; simplify both planar longitude/latitude geometries at 0.001 degrees preserving topology; compute area intersection-over-union. This is a triage measure, not a geodetic or legal boundary test.",
        "simplify_degrees": SIMPLIFY_DEGREES,
        "argentina_current_feature_count": ar_count,
        "chile_current_commune_feature_count": ch_count,
        "scoped_location_count": len(records),
        "matched_current_feature_count": sum(row["current_match_count"] == 1 for row in records),
        "unmatched_location_ids": [row["id"] for row in records if row["current_match_count"] == 0],
        "type_change_location_ids": [row["id"] for row in records if row.get("geometry_type_changed")],
        "iou_below_0_95_location_ids": [row["id"] for row in records if row.get("simplified_iou_0_001_degrees", 1) < 0.95],
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    RECORDS_OUT.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in records))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
