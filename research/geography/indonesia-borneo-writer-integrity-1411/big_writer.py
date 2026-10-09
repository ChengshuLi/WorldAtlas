#!/usr/bin/env python3
"""Safe additive, offline-capable replacement for PR #1411's BIG overlay writer.

The old entry point is retained unchanged. This writer admits a fresh owned
output set before reading a source, and requires a caller-supplied exact-hash
BIG response plus the authenticated retained selection reply. It never calls
the BIG service itself.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from output_admission import MAX_FILE_BYTES, read_external_regular, read_regular, reserve_output_set, sha256


ISSUE = 1557
WORKER = "01a10947-b3d7-7812-8b2f-c5a47e88ccb2"
BASELINE = "e8dec40bd63ef80345798047cbd3f2a4b6ae0db9"
OWNED = Path(__file__).resolve().parent
REPO = OWNED.parents[2]
SOURCE_SHA256 = "d45aedf8f0f70031804a2666e1a6061cb5c67c1a36add6fee51ed3dd273ee94e"
SELECTION_SHA256 = "f270c1c04cf8a53bf48ec5c9b632d6642680ce67c3f07b3a0b0f47477a0e517c"
SELECTION_IDS = [57, 402, 403, 358, 366, 369, 376, 377, 378, 387, 490, 491]
SOURCE_IDS = set(SELECTION_IDS)
SELECTION_ENVELOPE = [116.25791778895884, -2.2215, 119.011729, 2.318793]
CONTACT_IDS = {
    "gb:IDN:ADM2:22746128B17746000623405",
    "gb:IDN:ADM2:22746128B2679722836886",
    "gb:IDN:ADM2:22746128B34069275840087",
    "gb:IDN:ADM2:22746128B55621143702768",
    "gb:IDN:ADM2:22746128B66626446070966",
    "gb:IDN:ADM2:22746128B75924443266043",
    "gb:IDN:ADM2:22746128B87893249930832",
    "gb:IDN:ADM2:22746128B96540112180119",
}
INPUTS = {
    "family-row": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/family-row.json",
                   "a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3"),
    "component-roster": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/component-roster.txt",
                         "8542c017a9d25fe717f19a4e0c418cf76002dc69869f16c34981f935e1fe39d1"),
    "contact-part": ("data/geography/part-10.json",
                     "ead134bcf52c068ef2893dfc9a976781bd80d7162cc1f2bfab763acbb22357a2"),
    "selection-response": ("inputs/big-selection-response.json",
                           SELECTION_SHA256),
    "original-overlay-code": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/assess-big-ksp-overlay.py",
                              "fada1d5cf5cff4f382940ca78680f0a3310642ae8f49efb5f5a2431847d6d3d4"),
    "original-big-receipt": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/metadata/big-2022-ksp-overlay-receipt.json",
                             "9bac830e06b2bfe87baf44bc8fd7bcc4958ccbb7f2ad8dbcec2ac39cc7b7fc5d"),
    "original-big-assessment": ("research/geography/indonesia-borneo-source-fitness-20261007/vintages/run-forty-one/big-ksp-overlay-assessment.json",
                                "9a23a4b0dbf44bfe66701672dda96c0cdb03fc08abe3d604bfbdd18e153f5a0d"),
    "original-components": ("research/geography/indonesia-borneo-source-fitness-20261007/vintages/run-thirty-eight/intersections.geojson.gz",
                            "9f80ab7b43c605c3d2691893728d2dcf142b3ea154372a46cf1069cbcc66a039"),
}
OUTPUTS = ("big-ksp-overlay-assessment.json", "completion.json")
LAYER_URL = "https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/BATAS_WILAYAH/MapServer/2"
FEATURE_URL = (
    "https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/BATAS_WILAYAH/MapServer/2/query?"
    "objectIds=57%2C402%2C403%2C358%2C366%2C369%2C376%2C377%2C378%2C387%2C490%2C491"
    "&outFields=%2A&returnGeometry=true&outSR=4326&f=geoJSON"
)


def _inflate_bounded(raw: bytes, limit: int = MAX_FILE_BYTES) -> bytes:
    import zlib
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    result = decoder.decompress(raw, limit + 1)
    if len(result) > limit or decoder.unconsumed_tail:
        raise ValueError("Compressed component comparison exceeds the decoded-byte bound")
    tail = decoder.flush(limit + 1 - len(result))
    result += tail
    if len(result) > limit or not decoder.eof or decoder.unused_data:
        raise ValueError("Compressed component comparison is incomplete or oversized")
    return result


def _load_authenticated(repo_root: Path, packet_root: Path, source_file: str) -> tuple[dict, dict]:
    records = {}
    loaded = {}
    for name, (relative, expected) in INPUTS.items():
        root = packet_root if name == "selection-response" else repo_root
        path = relative
        raw = read_regular(root, path)
        actual = sha256(raw)
        if actual != expected:
            raise ValueError(f"Pinned input changed: {name}")
        if name == "original-components":
            decoded = _inflate_bounded(raw)
            loaded[name] = json.loads(decoded)
            records[name] = {"path": relative, "commit": BASELINE, "bytes": len(raw),
                             "sha256": actual, "uncompressed_bytes": len(decoded),
                             "uncompressed_sha256": sha256(decoded)}
        else:
            loaded[name] = raw
            record = {"path": relative if name != "selection-response" else
                      "research/geography/indonesia-borneo-writer-integrity-1411/inputs/big-selection-response.json",
                      "bytes": len(raw), "sha256": actual}
            if name != "selection-response":
                record["commit"] = BASELINE
            records[name] = record
    source_raw = read_external_regular(source_file)
    source_hash = sha256(source_raw)
    if source_hash != SOURCE_SHA256:
        raise ValueError(f"BIG input hash differs from the exact retained response: {source_hash}")
    records["big-response"] = {"path": "caller-supplied local file (not copied or retained)",
                               "bytes": len(source_raw), "sha256": source_hash}
    selection_raw = loaded["selection-response"]
    selection = json.loads(selection_raw)
    selected = selection.get("objectIds")
    if selected != SELECTION_IDS:
        raise ValueError("Retained BIG selection snapshot differs from the exact pinned ID order")
    family = json.loads(loaded["family-row"])
    native_ids = family.get("complete_component_ids")
    if (family.get("component_count") != 45 or not isinstance(native_ids, list) or
            len(native_ids) != 45 or len(set(native_ids)) != 45 or
            any(not isinstance(value, str) or not value.startswith("physical-component:") for value in native_ids)):
        raise ValueError("Pinned family record does not contain the exact 45 component identities")
    roster = loaded["component-roster"].decode("utf-8").splitlines()
    if len(roster) != 45 or len(set(roster)) != 45 or sorted(roster) != roster:
        raise ValueError("Pinned component roster is missing, duplicate, or unsorted")
    if sorted(native_ids) != roster:
        raise ValueError("Pinned family IDs and component roster disagree")
    contacts = json.loads(loaded["contact-part"])
    matched_contacts = [feature.get("id") for feature in contacts.get("features", [])
                        if feature.get("id") in CONTACT_IDS]
    actual_contacts = set(matched_contacts)
    if len(matched_contacts) != 8 or actual_contacts != CONTACT_IDS:
        raise ValueError("The eight read-only contact identities are missing or duplicated")
    source = json.loads(source_raw)
    features = validate_source_features(source.get("features"))
    loaded["big-response"] = source_raw
    loaded["big-features"] = features
    loaded["component-ids"] = sorted(native_ids)
    loaded["selection"] = selection
    return loaded, records


def _component_features(loaded: dict) -> list[dict]:
    features = loaded["original-components"].get("features")
    if not isinstance(features, list):
        raise ValueError("Pinned component comparison is not a feature collection")
    rows = [feature for feature in features
            if feature.get("properties", {}).get("role") == "original_pinned_component"]
    ids = [feature.get("properties", {}).get("component_id") for feature in rows]
    expected = set(loaded["component-ids"])
    if len(rows) != 45 or len(set(ids)) != 45 or set(ids) != expected:
        raise ValueError("Pinned comparison components are missing, duplicate, or fabricated")
    return rows


def validate_source_features(features: object) -> list[dict]:
    if (not isinstance(features, list) or len(features) != 12 or
            any(not isinstance(row, dict) or not isinstance(row.get("properties"), dict) for row in features)):
        raise ValueError("BIG source is not the exact 12-feature GeoJSON response")
    source_ids = [row["properties"].get("objectid") for row in features]
    if len(set(source_ids)) != len(source_ids) or set(source_ids) != SOURCE_IDS:
        raise ValueError("BIG source feature identities are missing, duplicate, or fabricated")
    return features


def compare_original_assessment(result: dict, original: dict) -> None:
    """Refuse a changed comparison product; this is not a claim of new science."""
    for key in ("scope", "summary", "component_results"):
        if result.get(key) != original.get(key):
            raise ValueError(f"Changed comparison product: {key}")


def _compute_assessment(loaded: dict) -> dict:
    # Heavy geometry code is imported only after output admission and exact input
    # authentication. A refusal in the writer never calls this function.
    from shapely.geometry import shape

    source_rows = loaded["big-features"]
    big = [(row["properties"], shape(row["geometry"])) for row in source_rows]
    components = _component_features(loaded)
    component_geometries = [shape(row["geometry"]) for row in components]
    envelope = [
        min(geometry.bounds[0] for geometry in component_geometries),
        min(geometry.bounds[1] for geometry in component_geometries),
        max(geometry.bounds[2] for geometry in component_geometries),
        max(geometry.bounds[3] for geometry in component_geometries),
    ]
    if envelope != SELECTION_ENVELOPE:
        raise ValueError("Pinned component envelope differs from the authenticated BIG selection")
    pair_count = 0
    relation_counts = {"positive_area": 0, "positive_length": 0, "point_only": 0}
    component_rows = []
    for feature in sorted(components, key=lambda row: row["properties"]["component_id"]):
        component_id = feature["properties"]["component_id"]
        geometry = shape(feature["geometry"])
        intersections = []
        for properties, source_geometry in big:
            pair_count += 1
            if not geometry.intersects(source_geometry):
                continue
            overlap = geometry.intersection(source_geometry)
            if overlap.is_empty:
                continue
            if overlap.area > 0:
                relation = "positive_area"
            elif overlap.length > 0:
                relation = "positive_length"
            else:
                relation = "point_only"
            relation_counts[relation] += 1
            intersections.append({
                "big_objectid": properties["objectid"],
                "name": properties.get("namobj"),
                "province": properties.get("wadmpr"),
                "admin_code": properties.get("kdpkab"),
                "relation": relation,
            })
        component_rows.append({
            "component_id": component_id,
            "intersection_count": len(intersections),
            "intersections": sorted(intersections, key=lambda row: row["big_objectid"]),
        })
    return {
        "version": 1,
        "source": {
            "product": "BIG KSP 2022 Peta Wilayah Administrasi Kabupaten/Kota (Area)",
            "layer_url": LAYER_URL,
            "query_url": FEATURE_URL,
            "feature_selection": {
                "method": "Official service envelope intersection with bounds of the 45 exact pinned component geometries; authenticated retained returnIdsOnly snapshot; no live selection request.",
                "envelope_wgs84": SELECTION_ENVELOPE,
                "ids_response_sha256": SELECTION_SHA256,
                "selected_objectids": SELECTION_IDS,
                "selection_snapshot_retrieved_utc": "2026-10-09T01:31:54Z",
            },
            "query_response_sha256": SOURCE_SHA256,
            "query_response_bytes": len(loaded["big-response"]),
            "source_feature_count": len(big),
            "out_spatial_reference": 4326,
            "geometry_retained_in_packet": False,
            "license_status": "unknown",
        },
        "method": "Direct, unbuffered Shapely intersections in WGS84; no repair; classifications only, no area measurements.",
        "scope": {"component_count": len(components), "source_feature_count": len(big), "candidate_pair_count": pair_count},
        "summary": {
            "components_with_intersection": sum(bool(row["intersections"]) for row in component_rows),
            "components_without_intersection": sum(not row["intersections"] for row in component_rows),
            "intersection_count_by_relation": relation_counts,
        },
        "component_results": component_rows,
        "limits": [
            "The public service's layer metadata has empty copyrightText and states no open redistribution license; the exact raw BIG geometry response is not included.",
            "The overlay does not establish legal boundary authority, effective date, completeness, positional accuracy, or physical land/water status.",
            "Two components had no polygon intersection in the historical selected source subset; this does not establish whether they are outside official territory or reflect a source/coverage gap.",
            "Eight current Indonesian ADM2 contact features were identity-authenticated and kept read-only; no contact is changed or treated as territorial approval.",
        ],
    }


def execute(run_id: str, source_file: str, *, repo_root: Path = REPO, packet_root: Path = OWNED,
            load_inputs: Callable = _load_authenticated,
            compute: Callable = _compute_assessment,
            compare: Callable = compare_original_assessment) -> dict:
    # Reserve before loading source bytes, checking provider data, importing GIS,
    # or invoking a computation. Tests inject counters at both later boundaries.
    with reserve_output_set(packet_root, run_id, OUTPUTS) as reservation:
        loaded, input_records = load_inputs(repo_root, packet_root, source_file)
        result = compute(loaded)
        original = json.loads(loaded["original-big-assessment"])
        compare(result, original)
        products = {"big-ksp-overlay-assessment.json":
                    (json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()}
        code_records = {
            "writer": sha256(read_regular(repo_root, "research/geography/indonesia-borneo-writer-integrity-1411/big_writer.py")),
            "output_admission": sha256(read_regular(repo_root, "research/geography/indonesia-borneo-writer-integrity-1411/output_admission.py")),
        }
        completion = {
            "version": 1, "status": "complete", "issue": ISSUE, "worker_id": WORKER,
            "run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "entry_point": "big_writer.py", "baseline_commit": BASELINE,
            "code_sha256": code_records, "inputs": input_records,
            "limits": [
                "A matching exact-hash BIG response is required as a local file; this program never performs a network request.",
                "The source declares no open redistribution license. Raw geometry is hashed and processed in memory but is not copied into the packet.",
                "This mechanism does not approve BIG boundaries, Indonesian territorial meaning, parent relationships, completeness, physical/water status, source rights, or any regional branch.",
            ],
        }
        publication = reservation.publish(products, completion)
        return {"status": "complete", "run_id": run_id, **publication}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Fresh owned run id, for example run-20261009-a")
    parser.add_argument("--source-file", required=True,
                        help="Lawfully available exact SHA-256 BIG response; read locally without following symlinks")
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args.run_id, args.source_file), sort_keys=True))
        return 0
    except Exception as exc:
        parser.exit(2, f"refused: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
