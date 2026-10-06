#!/usr/bin/env python3
"""Compare pinned source members, current subjects, official API line items and one full gap.

All operations are read-only geometric measurements. Invalid operations are
reported; no make-valid, snap, buffer, nearest-owner assignment, or filling is
performed. Run twice from the committed source revision and compare report bytes.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import sys
import subprocess
import tempfile
import unicodedata
from pathlib import Path

import pyproj
import shapely
from shapely.geometry import mapping, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[4]
OWNED = ROOT / "research/geography/shared-seam-prt-esp-20261006"
SOURCES = OWNED / "sources"
API = SOURCES / "official-api-responses"
GAP_ID = "gap:ad2052defbeba8e89287bcc4344e641225c6579f9afd584497b381fe8fd8eedc"
SUBJECTS = {
    "atlas:district:ESP-1003:a5622946": "Brozas",
    "atlas:district:ESP-1004:a5622946": "Valencia De Alcantara",
    "atlas:district:ESP-1010:a5622946": "Coria",
    "gb:PRT:ADM2:2272694B24025236019409": "Nisa",
    "gb:PRT:ADM2:2272694B40601521893357": "Idanha-a-Nova",
    "gb:PRT:ADM2:2272694B64876814145037": "Castelo Branco",
    "gb:PRT:ADM2:2272694B74999887486897": "Vila Velha de Rodao",
}
IGN_BORDER_IDS = ["5665057", "5666602", "5674903", "5680275", "5684705", "5686837", "5688358", "5690193"]
IGN_COUNTRY_ID = "5702440"
IGN_NEGATIVE_CONTROL_ID = "5673087"
DGT_BY_PRT_ID = {
    "gb:PRT:ADM2:2272694B24025236019409": ("1212", "Nisa"),
    "gb:PRT:ADM2:2272694B40601521893357": ("0505", "Idanha-a-Nova"),
    "gb:PRT:ADM2:2272694B64876814145037": ("0502", "Castelo Branco"),
    "gb:PRT:ADM2:2272694B74999887486897": ("0511", "Vila Velha de Ródão"),
}
EXPECTED_HASHES = {
    "baseline_release_manifest": "85075dd4eceebf5bc8e7b554fb4e1573aed2c5baae546ca21746643852c55b81",
    "baseline_grid_manifest": "73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6",
    "baseline_hierarchy": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "gap_shard": "c8726499e2d34c89b45fcf5d4c725b9583d2cb14319736580c032d460c04cb54",
    "gap_report": "69aa2c4cc0a949d66938344cb80e526fe77b68661b93fd0b3be7830e2e18e478",
    "triage_report": "ba7a4b190683f8436109b6159359727a2300053ac42a96dcdd53ebef7f092b20",
    "triage_inputs": "ae609d1312be34a15d34f2c5b7915292a568465acab729f44036f8d4400d338d",
    "esp_raw": "ccce612ee6275d91e2d2fcccf7912087dcc72377abec6c8e20c65089ecb48564",
    "esp_simplified": "e5bfa1c3889ea763ca2bb82c7f1e8ff9eff715dcb99ce405293a03de7ac85862",
    "prt_raw": "a02fd52278e5e300a19949450e793812fe76d78664c0a896bb3c5ebda7f79f9e",
    "prt_simplified": "f7a9143190715b85812b03617adc4879898b8c6a6789b9c9732c9705ea6c21ac",
    "baseline_admin_sources": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "baseline_semantic_report": "266c4f0f6e91381a26bfa6868d3c0df22b30140fa7f8551977be10b423295831",
    "baseline_part19": "baeade0e3ad11cdd65beb101e7b79284ae2b6ee8794f9b08e86631c7f20e6269",
    "baseline_part28": "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d",
    "baseline_admin_importer": "d9df8285f1c270856a8e79b95636cf4b8d8496f48b30348a1e4d6d20619b2f22",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_file(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def feature_list(document):
    if isinstance(document, dict) and document.get("type") == "FeatureCollection":
        return document.get("features", [])
    if isinstance(document, dict) and document.get("type") == "Feature":
        return [document]
    return []


def feature_id(feature):
    return feature.get("properties", {}).get("id", feature.get("id"))


def find_feature(document, wanted_id):
    for feature in feature_list(document):
        if feature_id(feature) == wanted_id:
            return feature
    return None


def joined_part_file(source_dir: Path, destination: Path, expected_sha: str, expected_bytes: int):
    receipt_path = source_dir / "verified-partition-receipt.json"
    if not receipt_path.exists():
        receipt_path = source_dir / "partition-receipt.json"
    receipt = json_file(receipt_path)
    if receipt.get("actual_sha256") != expected_sha or receipt.get("actual_bytes") != expected_bytes:
        raise RuntimeError(f"source partition receipt mismatch: {source_dir}")
    digest = hashlib.sha256()
    written = 0
    with destination.open("xb") as output:
        for part in receipt["parts"]:
            path = source_dir / part["filename"]
            local_hash = hashlib.sha256()
            local_bytes = 0
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    output.write(block)
                    digest.update(block)
                    local_hash.update(block)
                    written += len(block)
                    local_bytes += len(block)
            if local_bytes != part["bytes"] or local_hash.hexdigest() != part["sha256"]:
                raise RuntimeError(f"partition changed after receipt: {path}")
    if written != expected_bytes or digest.hexdigest() != expected_sha:
        raise RuntimeError(f"whole source reconstruction mismatch: {source_dir}")
    return destination


def stream_feature_collection(path: Path, wanted_ids: set[str], prefix: str):
    """Read one GeoJSON feature at a time; only retain the requested source members."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r'"features"\s*:\s*\[', text)
    if not match:
        raise RuntimeError(f"not a GeoJSON FeatureCollection: {path}")
    decoder = json.JSONDecoder()
    position = match.end()
    count = 0
    found = {}
    while True:
        while position < len(text) and (text[position].isspace() or text[position] == ","):
            position += 1
        if position >= len(text) or text[position] == "]":
            break
        feature, position = decoder.raw_decode(text, position)
        count += 1
        properties = feature.get("properties") or {}
        shape_id = properties.get("shapeID")
        if shape_id is None:
            continue
        atlas_id = prefix + str(shape_id)
        if atlas_id in wanted_ids:
            if atlas_id in found:
                raise RuntimeError(f"duplicate source member id: {atlas_id}")
            found[atlas_id] = {
                "shape_id": str(shape_id),
                "shape_name": properties.get("shapeName"),
                "shape_iso": properties.get("shapeISO"),
                "shape_group": properties.get("shapeGroup"),
                "shape_type": properties.get("shapeType"),
                "geometry": shape(feature["geometry"]) if feature.get("geometry") else None,
            }
    return count, found


def geometry_record(geom):
    if geom is None:
        return {"geometry_type": None, "coordinate_count": 0, "bounds": None}
    def count_coords(value):
        if isinstance(value, (tuple, list)):
            if value and isinstance(value[0], (int, float)):
                return 1
            return sum(count_coords(child) for child in value)
        return 0
    return {
        "geometry_type": geom.geom_type,
        "coordinate_count": count_coords(geom.__geo_interface__.get("coordinates", [])),
        "bounds": [round(float(value), 9) for value in geom.bounds],
        "is_valid": bool(geom.is_valid),
        "validity_reason": shapely.is_valid_reason(geom),
    }


def projected(geom):
    if geom is None:
        return None
    transformer = pyproj.Transformer.from_crs("OGC:CRS84", "EPSG:25829", always_xy=True)
    return transform(transformer.transform, geom)


def metric(value):
    if value is None:
        return None
    value = float(value)
    return round(value, 6) if math.isfinite(value) else None


def safe_geometry_metrics(left, right):
    result = {"intersection_length_m": None, "distance_m": None, "hausdorff_m": None, "operation_errors": []}
    if left is None or right is None:
        result["operation_errors"].append("missing geometry")
        return result
    try:
        result["intersection_length_m"] = metric(left.intersection(right).length)
    except Exception as error:  # preserve failed topology operations
        result["operation_errors"].append(f"intersection: {type(error).__name__}: {error}")
    try:
        result["distance_m"] = metric(left.distance(right))
    except Exception as error:
        result["operation_errors"].append(f"distance: {type(error).__name__}: {error}")
    try:
        result["hausdorff_m"] = metric(left.hausdorff_distance(right))
    except Exception as error:
        result["operation_errors"].append(f"hausdorff: {type(error).__name__}: {error}")
    return result


def polygon_difference_metrics(left, right):
    result = {"topologically_equal": None, "symmetric_difference_area_m2": None, "operation_errors": []}
    if left is None or right is None:
        result["operation_errors"].append("missing geometry")
        return result
    try:
        result["topologically_equal"] = bool(left.equals(right))
    except Exception as error:
        result["operation_errors"].append(f"equals: {type(error).__name__}: {error}")
    try:
        result["symmetric_difference_area_m2"] = metric(left.symmetric_difference(right).area)
    except Exception as error:
        result["operation_errors"].append(f"symmetric_difference: {type(error).__name__}: {error}")
    return result


def geometry_parts(geom):
    """Expose each direct overlay fragment, including tiny and nonpolygon parts."""
    if geom is None:
        return []
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    return [
        {
            "index": index,
            "geometry_type": part.geom_type,
            "is_empty": bool(part.is_empty),
            "area_m2": metric(part.area),
            "length_m": metric(part.length),
            "coordinate_count": geometry_record(part)["coordinate_count"],
            "bounds_m": [metric(value) for value in part.bounds] if not part.is_empty else None,
        }
        for index, part in enumerate(parts)
    ]


def gap_coverage_record(gap, members):
    """Measure areal coverage and line contact separately on unchanged shapes."""
    row = {
        "member_count": len(members),
        "invalid_member_ids": [],
        "gap_area_m2": metric(gap.area),
        "covered_area_m2": None,
        "uncovered_residual_area_m2": None,
        "covered_fraction": None,
        "gap_intersection_type": None,
        "gap_intersection_parts": [],
        "uncovered_residual": None,
        "uncovered_residual_geometry_epsg25829": None,
        "shared_boundary_contact_length_m": None,
        "boundary_contact_type": None,
        "boundary_contact_parts": [],
        "operation_errors": [],
    }
    try:
        for identity, member in members:
            if member is None:
                row["operation_errors"].append(f"missing geometry: {identity}")
                continue
            if not member.is_valid:
                row["invalid_member_ids"].append(identity)
        if row["operation_errors"]:
            return row
        union = None
        for _, member in members:
            candidate = projected(member)
            union = candidate if union is None else union.union(candidate)
        intersection = gap.intersection(union)
        residual = gap.difference(union)
        contact = gap.boundary.intersection(union.boundary)
        row.update({
            "covered_area_m2": metric(intersection.area),
            "uncovered_residual_area_m2": metric(residual.area),
            "covered_fraction": metric(intersection.area / gap.area) if gap.area else None,
            "gap_intersection_type": intersection.geom_type,
            "gap_intersection_parts": geometry_parts(intersection),
            "uncovered_residual": geometry_record(residual),
            "uncovered_residual_geometry_epsg25829": mapping(residual),
            "shared_boundary_contact_length_m": metric(contact.length),
            "boundary_contact_type": contact.geom_type,
            "boundary_contact_parts": geometry_parts(contact),
        })
    except Exception as error:
        row["operation_errors"].append(f"coverage/union/contact: {type(error).__name__}: {error}")
    return row


def normalize_name(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(character for character in normalized if not unicodedata.combining(character)).casefold()


def main():
    run_id = sys.argv[1] if len(sys.argv) == 2 else None
    if run_id is None or not re.fullmatch(r"run-[0-9]{2}", run_id):
        raise RuntimeError("usage: reproduce-comparison.py run-01|run-02 (use a distinct empty output directory for each complete run)")
    output_dir = OWNED / "outputs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise RuntimeError(f"output directory must be empty: {output_dir}")
    hashes = {}
    pin_paths = {
        "baseline_release_manifest": ROOT / "data/geographic-releases/current-manifest.json",
        "baseline_grid_manifest": ROOT / "data/canonical-grid/manifest.json",
        "baseline_hierarchy": ROOT / "data/hierarchy.json",
        "gap_shard": ROOT / "coordination/engineering/geographic-components-946-20261005-local06/components-v2/components-004.json.gz",
        "gap_report": ROOT / "coordination/engineering/geographic-components-946-20261005-local06/components-v2/report.json",
        "triage_report": ROOT / "coordination/engineering/geographic-grid-triage-946-20261005-local08/triage-v1/report.json",
        "triage_inputs": ROOT / "coordination/engineering/geographic-grid-triage-946-20261005-local08/inputs.json",
        "baseline_admin_sources": ROOT / "data/administrative-sources.json",
        "baseline_semantic_report": ROOT / "data/semantic-report.json",
        "baseline_part19": ROOT / "data/geography/part-19.json",
        "baseline_part28": ROOT / "data/geography/part-28.json",
        "baseline_admin_importer": ROOT / "scripts/administrative.py",
    }
    for pin, expected in EXPECTED_HASHES.items():
        if pin not in pin_paths:
            continue
        actual = sha256_path(pin_paths[pin])
        if actual != expected:
            raise RuntimeError(f"pinned baseline mismatch for {pin}: {actual}")
        hashes[pin] = {"path": str(pin_paths[pin].relative_to(ROOT)), "bytes": pin_paths[pin].stat().st_size, "sha256": actual}

    source_roots = {
        "esp_raw": SOURCES / "gb-esp-adm3-original/chunks",
        "esp_simplified": SOURCES / "gb-esp-adm3-baseline-simplified/whole-original",
        "prt_raw": SOURCES / "gb-prt-adm2-original/whole-original",
        "prt_simplified": SOURCES / "gb-prt-adm2-baseline-simplified/whole-original",
    }
    for key, source_dir in source_roots.items():
        receipt_file = source_dir / "verified-partition-receipt.json"
        if not receipt_file.exists():
            receipt_file = source_dir / "partition-receipt.json"
        receipt = json_file(receipt_file)
        expected = EXPECTED_HASHES[key]
        if receipt.get("actual_sha256") != expected or receipt.get("actual_bytes") != receipt.get("expected_bytes"):
            raise RuntimeError(f"source bytes are not verified against the correct source object: {key}")
        hashes[key + "_receipt"] = {"path": str(receipt_file.relative_to(ROOT)), "bytes": receipt_file.stat().st_size, "sha256": sha256_path(receipt_file)}

    dgt_receipt = json_file(API / "response-receipt.json")
    ign_receipt = json_file(API / "ign-native-items/response-receipt.json")
    ign_polygon_receipt = json_file(API / "ign-administrativeunit-native-items/response-receipt.json")
    discovery_record = json_file(API / "ign-bbox-discovery-receipt.json")
    if dgt_receipt.get("status") == "failed":
        raise RuntimeError("DGT source receipt is failed")
    if ign_receipt.get("status", "").startswith("partial"):
        raise RuntimeError("IGN native item receipt is partial")
    discovery_path = API / "ign-bbox-discovery-only.json"
    if sha256_path(discovery_path) != discovery_record["sha256"]:
        raise RuntimeError("IGN discovery response hash mismatch")
    hashes["ign_discovery"] = {"path": str(discovery_path.relative_to(ROOT)), "bytes": discovery_path.stat().st_size, "sha256": discovery_record["sha256"]}

    api_docs = {
        "dgt_collection": API / "dgt-municipios-collection.json",
        "dgt_queryables": API / "dgt-municipios-queryables.json",
        "ign_collection": API / "ign-administrativeboundary-collection.json",
        "ign_queryables": API / "ign-administrativeboundary-queryables.json",
        "ign_collection_index": API / "ign-collections.json",
        "ign_adminunit_collection": API / "ign-administrativeunit-collection.json",
        "ign_adminunit_queryables": API / "ign-administrativeunit-queryables.json",
    }
    for key, path in api_docs.items():
        hashes[key] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256_path(path)}
    for key, path in {
        "dgt_response_receipt": API / "response-receipt.json",
        "ign_native_items_receipt": API / "ign-native-items/response-receipt.json",
        "ign_adminunit_items_receipt": API / "ign-administrativeunit-native-items/response-receipt.json",
        "ign_discovery_receipt": API / "ign-bbox-discovery-receipt.json",
    }.items():
        hashes[key] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256_path(path)}

    dgt_items = {}
    for subject, (native_id, expected_name) in DGT_BY_PRT_ID.items():
        # Keep the authored item path explicit; normalization is not a source ID.
        filenames = {"Nisa": "dgt-municipios-nisa.json", "Idanha-a-Nova": "dgt-municipios-idanha-a-nova.json", "Castelo Branco": "dgt-municipios-castelo-branco.json", "Vila Velha de Ródão": "dgt-municipios-vila-velha-de-rodao.json"}
        path = API / filenames[expected_name]
        record = next((item for item in dgt_receipt.get("records", []) if item["id"] == path.stem), None)
        if record is None:
            raise RuntimeError(f"DGT item lacks a complete fetch receipt: {path.name}")
        actual_sha = sha256_path(path)
        if actual_sha != record["sha256"]:
            raise RuntimeError(f"DGT item hash changed after receipt: {path.name}")
        feature = json_file(path)
        if feature.get("id") != native_id or feature.get("properties", {}).get("dtmn") != native_id:
            raise RuntimeError(f"DGT native ID mismatch for {expected_name}")
        if feature["properties"].get("municipio") != expected_name:
            raise RuntimeError(f"DGT municipality name mismatch for {expected_name}")
        dgt_items[subject] = (feature, path)
        hashes["dgt_" + native_id] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": actual_sha}

    ign_items = {}
    ign_receipt_by_id = {item["native_id"]: item for item in ign_receipt["records"]}
    for native_id in IGN_BORDER_IDS + [IGN_COUNTRY_ID, IGN_NEGATIVE_CONTROL_ID]:
        path = API / "ign-native-items" / f"ign-administrativeboundary-{native_id}.json"
        record = ign_receipt_by_id[native_id]
        actual_sha = sha256_path(path)
        if actual_sha != record["sha256"]:
            raise RuntimeError(f"IGN item hash changed after receipt: {path.name}")
        feature = json_file(path)
        if feature.get("id") is not None and str(feature.get("id")) != native_id and str(feature.get("properties", {}).get("gid")) != native_id:
            raise RuntimeError(f"IGN native item identity mismatch: {native_id}")
        ign_items[native_id] = feature
        record["response_path"] = str(path.relative_to(ROOT))
        record["response_bytes"] = path.stat().st_size
        hashes["ign_" + native_id] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": actual_sha}

    if ign_polygon_receipt.get("returned_native_item_count") != 8:
        raise RuntimeError("IGN administrativeunit direct item count differs from the retained eight-name audit")
    ign_polygon_features = {}
    ign_polygon_crosswalk = []
    for record in ign_polygon_receipt["records"]:
        query_records = [record.get("name_query_response"), record.get("code_query_response")]
        if not any(query_records):
            query_records = [record["query_response"]]
        for query_kind, query_record in zip(("name", "native_code"), query_records):
            if query_record is None:
                continue
            query_rel = query_record["path"]
            query_path = API / query_rel
            query_hash = sha256_path(query_path)
            if query_hash != query_record["sha256"]:
                raise RuntimeError(f"IGN administrativeunit {query_kind}-response bytes changed: {query_path.name}")
            suffix = "_" + query_kind if len(query_records) > 1 else ""
            key = "ign_adminunit_query_" + normalize_name(record["nameunit"]).replace(" ", "_") + suffix
            hashes[key] = {"path": str(query_path.relative_to(ROOT)), "bytes": query_path.stat().st_size, "sha256": query_hash}
            query_receipt_path = query_path.with_name(query_path.stem + "-receipt.json")
            hashes[key + "_receipt"] = {"path": str(query_receipt_path.relative_to(ROOT)), "bytes": query_receipt_path.stat().st_size, "sha256": sha256_path(query_receipt_path)}
        if record.get("native_item_response") is None:
            ign_polygon_crosswalk.append({"requested_nameunit": record["nameunit"], "resolution": record["resolution"], "candidate_ids": record.get("candidates", []), "query_response_path": str(query_path.relative_to(ROOT))})
            continue
        item_rel = record["native_item_response"]["path"]
        item_path = API / item_rel
        item_sha = sha256_path(item_path)
        if item_sha != record["native_item_response"]["sha256"]:
            raise RuntimeError(f"IGN administrativeunit direct feature bytes changed: {item_path.name}")
        feature = json_file(item_path)
        native_id = str(record["gid"])
        if str(feature.get("id")) != native_id or feature.get("properties", {}).get("nameunit") != record["nameunit"] or feature.get("properties", {}).get("country") != "ES" or not feature.get("geometry"):
            raise RuntimeError(f"IGN administrativeunit native identity/full geometry mismatch: {native_id}")
        ign_polygon_features[normalize_name(record["nameunit"])] = (native_id, feature, item_path, record)
        item_receipt_path = item_path.with_name(item_path.stem + "-receipt.json")
        hashes["ign_adminunit_" + native_id] = {"path": str(item_path.relative_to(ROOT)), "bytes": item_path.stat().st_size, "sha256": item_sha}
        hashes["ign_adminunit_receipt_" + native_id] = {"path": str(item_receipt_path.relative_to(ROOT)), "bytes": item_receipt_path.stat().st_size, "sha256": sha256_path(item_receipt_path)}
        ign_polygon_crosswalk.append({"requested_nameunit": record["nameunit"], "resolution": record["resolution"], "native_id": native_id, "nameunit": feature["properties"]["nameunit"], "nationalcode": feature["properties"].get("nationalcode"), "nationallevelname": feature["properties"].get("nationallevelname"), "response_path": str(item_path.relative_to(ROOT)), "response_receipt": record["native_item_response"]})

    ign_adminunit_collection = json_file(API / "ign-administrativeunit-collection.json")
    if ign_adminunit_collection.get("storageCRS") != "http://www.opengis.net/def/crs/OGC/1.3/CRS84":
        raise RuntimeError("IGN administrativeunit storage CRS changed from the pinned service metadata")

    part19 = json_file(pin_paths["baseline_part19"])
    part28 = json_file(pin_paths["baseline_part28"])
    current = {}
    current_paths = {}
    for feature in feature_list(part19) + feature_list(part28):
        identity = feature_id(feature)
        if identity in SUBJECTS:
            current[identity] = feature
            current_paths[identity] = pin_paths["baseline_part19"] if feature in feature_list(part19) else pin_paths["baseline_part28"]
    if set(current) != set(SUBJECTS):
        raise RuntimeError(f"baseline subjects missing: {sorted(set(SUBJECTS) - set(current))}")
    member_groups = {}
    member_ids = set()
    for subject in ["atlas:district:ESP-1003:a5622946", "atlas:district:ESP-1004:a5622946", "atlas:district:ESP-1010:a5622946"]:
        metadata = current[subject]["properties"]["metadata"]
        member_groups[subject] = list(metadata.get("source_member_ids", []))
        member_ids.update(member_groups[subject])
    if len(member_ids) != sum(len(value) for value in member_groups.values()):
        raise RuntimeError("Spanish district source member IDs overlap unexpectedly")

    scratch = OWNED / "scratch"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="run-", dir=scratch) as temporary_dir:
        temporary_dir = Path(temporary_dir)
        esp_raw = joined_part_file(source_roots["esp_raw"], temporary_dir / "esp-raw.geojson", EXPECTED_HASHES["esp_raw"], 149105849)
        esp_simplified = joined_part_file(source_roots["esp_simplified"], temporary_dir / "esp-simplified.geojson", EXPECTED_HASHES["esp_simplified"], 18613175)
        esp_raw_count, esp_raw_features = stream_feature_collection(esp_raw, member_ids, "gb:ESP:ADM3:")
        esp_simple_count, esp_simple_features = stream_feature_collection(esp_simplified, member_ids, "gb:ESP:ADM3:")
        if set(esp_raw_features) != member_ids or set(esp_simple_features) != member_ids:
            raise RuntimeError("some of the exact Atlas Spanish source member IDs are absent in the complete upstream files")
        if esp_raw_count != esp_simple_count:
            raise RuntimeError("full and simplified Spain files differ in feature count")

    prt_raw_path = source_roots["prt_raw"] / "part-001.bin"
    prt_simple_path = source_roots["prt_simplified"] / "part-001.bin"
    prt_raw_doc = json_file(prt_raw_path)
    prt_simple_doc = json_file(prt_simple_path)
    prt_raw_features = {}
    prt_simple_features = {}
    for doc, result in [(prt_raw_doc, prt_raw_features), (prt_simple_doc, prt_simple_features)]:
        for feature in feature_list(doc):
            shape_id = feature.get("properties", {}).get("shapeID")
            if shape_id:
                result["gb:PRT:ADM2:" + str(shape_id)] = feature

    esp_member_rows = []
    member_name_index = {}
    for subject, ids in member_groups.items():
        for identity in ids:
            raw = esp_raw_features[identity]
            simple = esp_simple_features[identity]
            name = raw.get("shape_name") or ""
            normalized = normalize_name(name)
            member_name_index.setdefault(normalized, []).append(identity)
            esp_member_rows.append({
                "atlas_district_subject": subject,
                "source_member_id": identity,
                "native_shape_id": raw["shape_id"],
                "native_name": name,
                "native_iso": raw["shape_iso"],
                "native_group": raw["shape_group"],
                "native_type": raw["shape_type"],
                "raw_geometry": geometry_record(raw["geometry"]),
                "simplified_geometry": geometry_record(simple["geometry"]),
                "raw_to_baseline_simplified": polygon_difference_metrics(projected(raw["geometry"]), projected(simple["geometry"])),
            })
    esp_member_rows.sort(key=lambda row: (row["atlas_district_subject"], row["native_name"], row["source_member_id"]))

    subject_rows = []
    current_geometries = {}
    for subject, feature in current.items():
        current_geom = shape(feature["geometry"])
        current_geometries[subject] = current_geom
        row = {"subject_id": subject, "baseline_name": feature["properties"]["name"], "baseline_file": str(current_paths[subject].relative_to(ROOT)), "baseline_geometry": geometry_record(current_geom)}
        if subject in DGT_BY_PRT_ID:
            dgt_feature, dgt_path = dgt_items[subject]
            raw_feature = prt_raw_features.get(subject)
            simple_feature = prt_simple_features.get(subject)
            row.update({
                "native_source_id": subject,
                "geoBoundaries_raw_name": raw_feature.get("properties", {}).get("shapeName") if raw_feature else None,
                "geoBoundaries_simplified_name": simple_feature.get("properties", {}).get("shapeName") if simple_feature else None,
                "dgt_caop2025_native_id": DGT_BY_PRT_ID[subject][0],
                "dgt_caop2025_name": dgt_feature["properties"].get("municipio"),
                "dgt_caop2025_district": dgt_feature["properties"].get("distrito_ilha"),
                "dgt_caop2025_geometry": geometry_record(shape(dgt_feature["geometry"])),
                "baseline_vs_full_geoboundaries": polygon_difference_metrics(projected(current_geom), projected(shape(raw_feature["geometry"])) if raw_feature else None),
                "baseline_vs_baseline_simplified_source": polygon_difference_metrics(projected(current_geom), projected(shape(simple_feature["geometry"])) if simple_feature else None),
                "baseline_vs_dgt_caop2025": polygon_difference_metrics(projected(current_geom), projected(shape(dgt_feature["geometry"]))),
                "geoboundaries_full_vs_caop2025": polygon_difference_metrics(projected(shape(raw_feature["geometry"])) if raw_feature else None, projected(shape(dgt_feature["geometry"]))),
            })
        else:
            ids = member_groups[subject]
            row["source_member_count"] = len(ids)
            row["source_member_ids"] = ids
            row["source_member_union_geometry"] = None
            try:
                geometries = [projected(esp_raw_features[identity]["geometry"]) for identity in ids]
                union = geometries[0]
                for geometry in geometries[1:]:
                    union = union.union(geometry)
                row["source_member_union_geometry"] = geometry_record(union)
                row["baseline_vs_union_of_named_source_members"] = polygon_difference_metrics(projected(current_geom), union)
            except Exception as error:
                row["source_member_union_geometry_error"] = f"{type(error).__name__}: {error}"
        subject_rows.append(row)

    component_shard = pin_paths["gap_shard"]
    with gzip.open(component_shard, "rt", encoding="utf-8") as stream:
        component_doc = json.load(stream)
    gap_feature = find_feature(component_doc, GAP_ID)
    if gap_feature is None:
        raise RuntimeError("exact full-gap component was not found in its pinned complete shard")
    gap_geom = shape(gap_feature["geometry"])
    gap_projected = projected(gap_geom)
    gap_source = {
        "gap_id": GAP_ID,
        "component_geometry": geometry_record(gap_geom),
        "component_geometry_hash": hashlib.sha256(json.dumps(gap_feature["geometry"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }

    spanish_subjects = ["atlas:district:ESP-1003:a5622946", "atlas:district:ESP-1004:a5622946", "atlas:district:ESP-1010:a5622946"]
    portuguese_subjects = list(DGT_BY_PRT_ID)
    coverage_inputs = {
        "spanish_exact_55_raw_members": [(identity, esp_raw_features[identity]["geometry"]) for identity in sorted(member_ids)],
        "spanish_exact_55_baseline_simplified_members": [(identity, esp_simple_features[identity]["geometry"]) for identity in sorted(member_ids)],
        "spanish_three_current_atlas_districts": [(subject, shape(current[subject]["geometry"])) for subject in spanish_subjects],
        "spanish_eight_ign_border_member_raw_polygons": [],
        "spanish_eight_ign_border_member_baseline_simplified_polygons": [],
        "spanish_eight_returned_ign_administrativeunit_polygons": [(native_id, shape(feature["geometry"])) for native_id, feature, _, _ in ign_polygon_features.values()],
        "portugal_four_geoboundaries_raw_municipalities": [(subject, shape(prt_raw_features[subject]["geometry"])) for subject in portuguese_subjects],
        "portugal_four_geoboundaries_baseline_simplified_municipalities": [(subject, shape(prt_simple_features[subject]["geometry"])) for subject in portuguese_subjects],
        "portugal_four_dgt_caop2025_municipalities": [(subject, shape(dgt_items[subject][0]["geometry"])) for subject in portuguese_subjects],
        "portugal_four_current_atlas_municipalities": [(subject, current_geometries[subject]) for subject in portuguese_subjects],
        "combined_seven_current_atlas_subjects": [(subject, geom) for subject, geom in current_geometries.items()],
        "combined_2018_spanish_raw_and_caop2025_portuguese": [(identity, esp_raw_features[identity]["geometry"]) for identity in sorted(member_ids)] + [(subject, shape(dgt_items[subject][0]["geometry"])) for subject in portuguese_subjects],
    }
    border_member_ids = []
    for native_id in IGN_BORDER_IDS:
        properties = ign_items[native_id]["properties"]
        name_key = normalize_name(properties.get("name_boundary", "").split("#", 1)[0])
        matches = member_name_index.get(name_key, [])
        if len(matches) != 1:
            raise RuntimeError(f"IGN border line does not have a unique exact-seven-roster source member crosswalk: {native_id}")
        border_member_ids.extend(matches)
    if len(set(border_member_ids)) != 8:
        raise RuntimeError("Eight IGN municipal line items did not crosswalk to eight distinct exact Spanish source members")
    coverage_inputs["spanish_eight_ign_border_member_raw_polygons"] = [(identity, esp_raw_features[identity]["geometry"]) for identity in border_member_ids]
    coverage_inputs["spanish_eight_ign_border_member_baseline_simplified_polygons"] = [(identity, esp_simple_features[identity]["geometry"]) for identity in border_member_ids]
    coverage_inputs["combined_eight_returned_ign_and_four_caop_polygons"] = [(native_id, shape(feature["geometry"])) for native_id, feature, _, _ in ign_polygon_features.values()] + [(subject, shape(dgt_items[subject][0]["geometry"])) for subject in portuguese_subjects]
    gap_coverage = {name: gap_coverage_record(gap_projected, members) for name, members in coverage_inputs.items()}
    gap_coverage["spanish_eight_returned_ign_administrativeunit_polygons"]["requested_member_count"] = 8
    gap_coverage["spanish_eight_returned_ign_administrativeunit_polygons"]["missing_nameunit"] = [row["requested_nameunit"] for row in ign_polygon_crosswalk if row.get("native_id") is None]
    gap_coverage["combined_eight_returned_ign_and_four_caop_polygons"]["missing_spanish_nameunit"] = [row["requested_nameunit"] for row in ign_polygon_crosswalk if row.get("native_id") is None]

    ign_lines = [projected(shape(ign_items[native_id]["geometry"])) for native_id in IGN_BORDER_IDS]
    ign_line_union = ign_lines[0]
    for line in ign_lines[1:]:
        ign_line_union = ign_line_union.union(line)
    ign_line_intersection = gap_projected.intersection(ign_line_union)
    ign_line_boundary_contact = gap_projected.boundary.intersection(ign_line_union)
    ign_line_gap_coverage = {
        "native_line_item_count": len(IGN_BORDER_IDS),
        "total_unique_line_length_m": metric(ign_line_union.length),
        "line_length_inside_gap_polygon_m": metric(ign_line_intersection.length),
        "gap_polygon_boundary_contact_length_m": metric(ign_line_boundary_contact.length),
        "gap_intersection_geometry_type": ign_line_intersection.geom_type,
        "gap_intersection_parts": geometry_parts(ign_line_intersection),
        "boundary_contact_geometry_type": ign_line_boundary_contact.geom_type,
        "boundary_contact_parts": geometry_parts(ign_line_boundary_contact),
        "operation_errors": [],
    }

    # Pairwise measurements only. Names and identifiers establish the crosswalk;
    # distances never assign ownership or resolve a disputed boundary.
    target_member_lookup = {identity: row for row in esp_member_rows for identity in [row["source_member_id"]]}
    line_rows = []
    line_matrix = []
    for native_id in IGN_BORDER_IDS + [IGN_NEGATIVE_CONTROL_ID]:
        item = ign_items[native_id]
        properties = item["properties"]
        line_geom = shape(item["geometry"]) if item.get("geometry") else None
        line_projected = projected(line_geom)
        name = properties.get("name_boundary", "")
        spanish_name = name.split("#", 1)[0]
        candidates = member_name_index.get(normalize_name(spanish_name), [])
        matched_ids = [identity for identity in candidates if any(identity in member_groups[group] for group in member_groups)]
        line_row = {
            "ign_native_id": native_id,
            "name_boundary": name,
            "spanish_native_name_key": spanish_name,
            "crosswalk_source_member_candidates": matched_ids,
            "crosswalk_status": "unique name match" if len(matched_ids) == 1 else "unresolved or ambiguous name match",
            "type_boundary": properties.get("type_boundary"),
            "nationallevelname": properties.get("nationallevelname"),
            "date_boundary": properties.get("date_boundary"),
            "legalstatus": properties.get("legalstatus"),
            "nil_legalstatus": properties.get("nil_legalstatus"),
            "nilreason_legalstatus": properties.get("nilreason_legalstatus"),
            "accuracy": properties.get("accuracy"),
            "official_record_url": properties.get("url_resource"),
            "response_receipt": {
                key: ign_receipt_by_id[native_id].get(key)
                for key in ["request_url", "final_response_url", "retrieved_at", "http_status", "content_type", "content_length_header", "content_encoding_header", "etag", "last_modified", "bytes", "sha256"]
            },
            "line_geometry": geometry_record(line_geom),
            "line_length_m": metric(line_projected.length) if line_projected is not None else None,
            "gap_relation": safe_geometry_metrics(line_projected, gap_projected),
            "spanish_member_relations": [],
            "portugal_caop_relations": [],
        }
        if native_id in IGN_BORDER_IDS:
            polygon_match = ign_polygon_features.get(normalize_name(spanish_name))
            matched_member = esp_raw_features[matched_ids[0]] if len(matched_ids) == 1 else None
            matched_simplified_member = esp_simple_features[matched_ids[0]] if len(matched_ids) == 1 else None
            line_row["ign_administrativeunit_polygon_crosswalk"] = ({
                "resolution": "unique exact normalized nameunit match",
                "native_id": polygon_match[0],
                "nameunit": polygon_match[1]["properties"].get("nameunit"),
                "nationalcode": polygon_match[1]["properties"].get("nationalcode"),
                "nationallevelname": polygon_match[1]["properties"].get("nationallevelname"),
                "geometry": geometry_record(shape(polygon_match[1]["geometry"])),
                "line_to_polygon_boundary": safe_geometry_metrics(line_projected, projected(shape(polygon_match[1]["geometry"]).boundary)),
                "polygon_vs_2018_geoboundaries_raw_member": polygon_difference_metrics(projected(shape(polygon_match[1]["geometry"])), projected(matched_member["geometry"]) if matched_member else None),
                "polygon_vs_2018_geoboundaries_simplified_member": polygon_difference_metrics(projected(shape(polygon_match[1]["geometry"])), projected(matched_simplified_member["geometry"]) if matched_simplified_member else None),
                "crosswalked_geoboundaries_member_id": matched_ids[0] if len(matched_ids) == 1 else None,
                "native_response": polygon_match[3]["native_item_response"],
            } if polygon_match else {"resolution": "no exact nameunit item returned by IGN administrativeunit query", "requested_nameunit": spanish_name,
                "query_response": next(row["query_response_path"] for row in ign_polygon_crosswalk if row["requested_nameunit"] == spanish_name)})
        for identity in matched_ids:
            source_geom = esp_raw_features[identity]["geometry"]
            metric_pair = safe_geometry_metrics(line_projected, projected(source_geom.boundary) if source_geom else None)
            line_row["spanish_member_relations"].append({"source_member_id": identity, "native_name": esp_raw_features[identity]["shape_name"], **metric_pair})
        for subject in DGT_BY_PRT_ID:
            dgt_feature, _ = dgt_items[subject]
            relation = safe_geometry_metrics(line_projected, projected(shape(dgt_feature["geometry"]).boundary))
            line_row["portugal_caop_relations"].append({"subject_id": subject, "dgt_native_id": DGT_BY_PRT_ID[subject][0], **relation})
        line_rows.append(line_row)

    gap_relation_rows = []
    for subject, current_geom in current_geometries.items():
        relation = {"subject_id": subject, "overlap_area_m2": None, "distance_m": None, "intersection_geometry_type": None, "intersection_is_empty": None, "operation_errors": []}
        current_projected = projected(current_geom)
        try:
            intersection = gap_projected.intersection(current_projected)
            relation.update({"overlap_area_m2": metric(intersection.area), "distance_m": metric(gap_projected.distance(current_projected)), "intersection_geometry_type": intersection.geom_type, "intersection_is_empty": bool(intersection.is_empty), "intersection_coordinate_count": geometry_record(intersection)["coordinate_count"], "intersection_fragment_count": len(intersection.geoms) if hasattr(intersection, "geoms") else (0 if intersection.is_empty else 1), "intersection_parts": geometry_parts(intersection)})
        except Exception as error:
            relation["operation_errors"].append(f"intersection/distance: {type(error).__name__}: {error}")
        gap_relation_rows.append(relation)

    national = ign_items[IGN_COUNTRY_ID]["properties"]
    control = ign_items[IGN_NEGATIVE_CONTROL_ID]["properties"]
    collection = json_file(API / "ign-administrativeboundary-collection.json")
    dgt_collection = json_file(API / "dgt-municipios-collection.json")
    manifest = {
        "version": 1,
        "stage": "bounded-source-research; no map edit or legal boundary determination",
        "executed_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "analysis_script_sha256": sha256_path(Path(__file__).resolve()),
        "software": {"python": os.sys.version.split()[0], "shapely": shapely.__version__, "geos": shapely.geos_version_string, "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str},
        "baseline_commit": "27be77596f23304de6a720735538427e6d23e242",
        "input_files": hashes,
        "source_versions": {
            "esp_full": {"release_commit": "9469f09592ced973a3448cf66b6100b741b64c0d", "vintage": "2018", "license": "CC BY 4.0", "role": "full unsimplified source used to crosswalk all exact Spanish member identities"},
            "esp_baseline_simplified": {"release_commit": "9469f09592ced973a3448cf66b6100b741b64c0d", "vintage": "2018", "license": "CC BY 4.0", "role": "whole source file consumed by the baseline administrative importer"},
            "prt_full": {"release_commit": "90a1d5290ede3adc147c5a2351472fd000412e72", "vintage": "2020", "license": "CC0 1.0", "role": "full source for Portuguese municipality identity"},
            "prt_baseline_simplified": {"release_commit": "90a1d5290ede3adc147c5a2351472fd000412e72", "vintage": "2020", "license": "CC0 1.0", "role": "whole source file consumed by the baseline administrative importer"},
            "portugal_current_admin": {"product": dgt_collection.get("title"), "description": dgt_collection.get("description"), "service_temporal_extent": dgt_collection.get("extent", {}).get("temporal"), "geometry_crs_default": "OGC:CRS84 as declared by OGC API Features", "license": "CC BY 4.0 per DGT official open-data terms", "metadata_route": "https://ogcapi.dgterritorio.gov.pt/collections/municipios?f=json", "product_page": "https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop?language=pt", "reuse_terms": "https://www.dgterritorio.gov.pt/dados-abertos"},
            "spain_admin_line_service": {"product": collection.get("title"), "description": collection.get("description"), "date_boundary_per_item": "record field", "geometry_crs_default": "OGC:CRS84 as declared by OGC API Features", "license": "CC BY 4.0 with mandatory attribution per linked IGN license", "license_url": next((link.get("href") for link in collection.get("links", []) if link.get("rel") == "license"), None), "metadata_route": "https://api-features.ign.es/collections/administrativeboundary?f=json"},
            "spain_admin_polygon_service": {"product": ign_adminunit_collection.get("title"), "description": ign_adminunit_collection.get("description"), "collection_id": ign_adminunit_collection.get("id"), "metadata_catalog_id": "spaignLLM", "storage_crs": ign_adminunit_collection.get("storageCRS"), "feature_crs_list": ign_adminunit_collection.get("crs"), "returned_geometry_policy": "Complete direct item geometries in collection storage CRS84; no bbox or output CRS parameter", "license": "CC BY 4.0 with mandatory attribution per linked IGN license", "version_status": "Current API snapshot; collection response declares no represented publication vintage or feature validity date", "metadata_route": "https://api-features.ign.es/collections/administrativeunit?f=json"},
        },
        "baseline_source_member_counts": {
            "Spanish_subjects": {subject: len(ids) for subject, ids in member_groups.items()},
            "unique_source_members": len(member_ids),
            "complete_spain_feature_count_raw": esp_raw_count,
            "complete_spain_feature_count_simplified": esp_simple_count,
            "crosswalk_members_found_raw": len(esp_raw_features),
            "crosswalk_members_found_simplified": len(esp_simple_features),
        },
        "crs_and_method": {
            "source_coordinate_order": "longitude, latitude (GeoJSON/OGC CRS84 default); no axis swap, rounding, snapping or buffering",
            "measurement_crs": "EPSG:25829 (ETRS89 / UTM zone 29N), metres and square metres",
            "overlay_method": "direct GEOS intersections/distances/equals/symmetric differences on unchanged source geometries; no validity repair",
            "invalid_geometry_policy": "Record validity and per-operation errors; do not repair or omit invalid, line, point, empty or tiny outputs",
            "name_crosswalk": "exact source shapeID links from baseline subject metadata; Spanish line row names normalize accents/case only and must uniquely match a source shapeName inside the exact seven-subject member set",
            "distance_policy": "All pairwise line-to-source measurements are diagnostics only; they never assign an owner or choose a disputed boundary.",
        },
        "portuguese_subject_crosswalk_and_comparison": subject_rows,
        "spanish_source_member_crosswalk": esp_member_rows,
        "ign_administrativeunit_municipality_crosswalk": ign_polygon_crosswalk,
        "ign_selected_line_items": line_rows,
        "ign_country_level_status_control": {
            "native_id": IGN_COUNTRY_ID,
            "name_boundary": national.get("name_boundary"),
            "date_boundary": national.get("date_boundary"),
            "legalstatus": national.get("legalstatus"),
            "nil_legalstatus": national.get("nil_legalstatus"),
            "nilreason_legalstatus": national.get("nilreason_legalstatus"),
            "accuracy": national.get("accuracy"),
            "geometry": geometry_record(shape(ign_items[IGN_COUNTRY_ID]["geometry"]) if ign_items[IGN_COUNTRY_ID].get("geometry") else None),
            "interpretation": "This country-level row's legal status is unpopulated; it does not negate or elevate the separate municipality-line `agreed` fields."
        },
        "ign_interior_negative_control": {
            "native_id": IGN_NEGATIVE_CONTROL_ID,
            "name_boundary": control.get("name_boundary"),
            "type_boundary": control.get("type_boundary"),
            "date_boundary": control.get("date_boundary"),
            "legalstatus": control.get("legalstatus"),
            "accuracy": control.get("accuracy"),
            "interpretation": "An agreed interior Spanish municipal-line record exercises the name/type control; it is not a Portugal-border candidate."
        },
        "full_gap": gap_source,
        "gap_to_subject_geometry_comparisons": gap_relation_rows,
        "full_gap_areal_coverage_and_boundary_contacts": gap_coverage,
        "ign_selected_line_geometry_overlay": ign_line_gap_coverage,
        "physical_water_evidence": {
            "status": "not established",
            "explanation": "The retained geoBoundaries administrative polygons, CAOP municipal polygons, and IGN administrative-boundary line records are not physical water/shoreline or seasonal-channel observations. No dated hydrographic source for the exact gap was retained.",
        },
        "decision": {
            "shared_seam_edit_proposed": False,
            "supported": [
                "The 2018 Spanish ADM3 native source contains every member linked from the three exact Atlas districts; all eight selected Spain–Portugal municipal line items are separately preserved by native IGN ID and named member crosswalk.",
                "The four exact Portugal Atlas municipalities crosswalk by native geoBoundaries IDs/names to complete CAOP2025 municipality items.",
                "The selected IGN municipality rows carry line-level `legalstatus=agreed`, item dates, `accuracy` method 3 and per-record source URLs; the country-level Spain–Portugal row carries an explicitly unpopulated legal-status field.",
                "IGN exposes a distinct current `administrativeunit` polygon collection; seven exact nameunit queries and one exact Spanish nationalcode crosswalk returned complete direct municipality polygons for all eight municipalities named by the selected border-line items. The eighth name query returned zero; its line record nationalcode prefix uniquely resolves the complete Zarza la Mayor polygon (gid 1173184). The full-gap ledger measures all eight polygons separately from line contacts and the 2018 Spanish source-member coverage.",
            ],
            "unresolved": [
                "The exact point-by-point bilateral boundary instrument/registered cross-border line coordinates and a complete cross-provider crosswalk linking that record to both countries' current administrative units remain unestablished by the retained responses; item-level `agreed` status is not treated as bilateral authority. The current Spanish polygon crosswalk is source-supported by seven exact names and the eighth line-native nationalcode, but has no published validity date in the retained collection/item responses.",
                "The CAOP2025 collection metadata reports a 2000–2007 temporal extent despite its CAOP2025 title; the DGT product version page and direct item features must be considered alongside that metadata discrepancy.",
                "Physical water/land position, seasonal channel movement, datum/registration history, and any consequence for the limited-AOI pilot remain unknown; no dated physical-water source was retained.",
            ],
            "recommendation": "The retained sources support a limited, explicitly labeled current-service administrative reference comparison using unchanged complete CAOP2025 Portuguese municipality polygons and eight complete IGN Spanish municipality polygons, with Zarza la Mayor resolved through its exact line-record nationalcode after the exact-name query returned zero. Preserve the full-union areal coverage and residual ledger separately from 2022 line contacts. This is not a single complete, mutually authoritative legal seam and does not establish physical water/shoreline position, territorial ownership, or a map repair. No engineering geometry edit is proposed."
        }
    }
    destination = output_dir / "report.json"
    destination.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(destination.relative_to(ROOT)), "execution_commit": manifest["executed_git_commit"], "analysis_sha256": manifest["analysis_script_sha256"], "spanish_members": len(esp_member_rows), "ign_border_items": len(IGN_BORDER_IDS), "source_bytes_verified": True}, sort_keys=True))


if __name__ == "__main__":
    main()
