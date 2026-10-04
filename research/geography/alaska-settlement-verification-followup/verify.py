#!/usr/bin/env python3
"""Strictly verify Alaska settlement source inputs and a dated DCRA live query.

This does not replay the Oct 3 2026 response: its bytes were not retained and the
service does not advertise historical archives. New responses are separate
vintages and are never compared to the old response digest.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.geometry import point as checked_point
OWNED = ROOT / "research/geography/alaska-settlement-verification-followup"
CHILD = "data/regional-review/alaska-settlement-gaps-followup-2026"
PARENT = "data/regional-review/regional-review-93f8f3bee8e205be"
BASELINE_COMMIT = "038d611ee5c275812d53af044f389e85e0f303f9"
SERVICE = "https://maps.commerce.alaska.gov/server/rest/services/Community_Related/Community_Locations_and_Boundaries/MapServer/0"
EXTENT = {"xmin": -180, "ymin": 51, "xmax": -129, "ymax": 72,
          "spatialReference": {"wkid": 4326}}
EXPECTED = (
    "atlas:physical:15fa62117dba20fdd7a3",
    "atlas:physical:2e1dd8f380b0a4f65ad9",
    "atlas:physical:3c48debb2430313aff99",
    "atlas:physical:674981b93623e9cbe385",
    "atlas:physical:770135c5de8a7faad962",
    "atlas:physical:d5c6a8a99d213d352ffc",
    "atlas:physical:db25f36496f102a4e01b",
    "atlas:physical:f1337f9008d75f1a400d",
)
PINS = {
    f"{CHILD}/scope.json": (1171, "4dc4dbe69971a67274a240fdc450d043ea97cf075ba9e25448070bd97fc6dc8d"),
    f"{CHILD}/assessment.json": (42632, "a2f16b10370ef0ad49c9254374e15ad2cbae38951062d80573ef96967c96e6e5"),
    f"{CHILD}/sources.json": (4186, "94fda0407be871fd002a0cc21f2c2fc4ec084a6401499eaf35b8c95144dc222f"),
    f"{CHILD}/verify.py": (3833, "003f6bf2bf44606eedf7309e5bc729e285c6804b126bdb386e93a6f3241f9e57"),
    f"{PARENT}/assessment.json": (11210183, "69400c56a34725f82b6a75edea0213dff2855eb5e9d8469681bb7a394884e2d5"),
    f"{PARENT}/sources/current-scope-and-parents.geojson.gz": (256548, "23f998ab6f874fac86dedeacb20978e391fdd23bf30ce6de8b687e6d57f9d862"),
    f"{PARENT}/scope.json": (13154, "98c39e78569de0a4fc9c02f74ca5662a267ad97d5074bb1691e1cc4626c0ed57"),
    f"{PARENT}/sources.json": (4699, "7a94870f1470d5d7cb6c0883d30fee715021c93959e5f1ecf04930719e83a299"),
}
DECLARED_PARENT_FILES = {
    f"{PARENT}/assessment.json": (11210183, "69400c56a34725f82b6a75edea0213dff2855eb5e9d8469681bb7a394884e2d5"),
    f"{PARENT}/sources/current-scope-and-parents.geojson.gz": (256548, "23f998ab6f874fac86dedeacb20978e391fdd23bf30ce6de8b687e6d57f9d862"),
    f"{PARENT}/sources/resolve-15-ecoregions.geojson.gz": (9761832, "b42d888c27a8adae8ee6ec19db430b3d631e34a123847942cc7a07e2528be3d9"),
    f"{PARENT}/scope.json": (13154, "98c39e78569de0a4fc9c02f74ca5662a267ad97d5074bb1691e1cc4626c0ed57"),
    f"{PARENT}/sources.json": (4699, "7a94870f1470d5d7cb6c0883d30fee715021c93959e5f1ecf04930719e83a299"),
}


class VerificationError(ValueError):
    pass


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned_bytes(path: str) -> bytes:
    try:
        raw = subprocess.run(["git", "show", f"{BASELINE_COMMIT}:{path}"], cwd=ROOT,
                             check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    except subprocess.CalledProcessError as exc:
        raise VerificationError(f"missing immutable baseline file {path} at {BASELINE_COMMIT}") from exc
    check_pin(path, raw)
    return raw


def check_pin(path: str, raw: bytes):
    size, sha = PINS[path]
    if len(raw) != size or digest(raw) != sha:
        raise VerificationError(f"baseline pin mismatch for {path}: bytes={len(raw)} sha256={digest(raw)}")


def canonical_chain(chain):
    if not isinstance(chain, list) or not chain:
        raise VerificationError("parent chain must be a nonempty list")
    out = []
    for row in chain:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) for k in ("id", "name")):
            raise VerificationError("malformed parent-chain row")
        out.append((row["id"], row["name"], row.get("parent_id")))
    if len({row[0] for row in out}) != len(out):
        raise VerificationError("duplicate ID in parent chain")
    return out


def validate_subject_ids(ids, label):
    if not isinstance(ids, list) or tuple(ids) != EXPECTED or len(set(ids)) != len(EXPECTED):
        raise VerificationError(f"{label} is not the exact unique eight-ID list")


def validate_polygon(feature, subject_id):
    geom = feature.get("geometry") if isinstance(feature, dict) else None
    if not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
        raise VerificationError(f"invalid polygon geometry type for {subject_id}")
    try:
        polygon = shape(geom)
    except Exception as exc:
        raise VerificationError(f"malformed polygon coordinates for {subject_id}") from exc
    if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
        raise VerificationError(f"empty, invalid or zero-area polygon for {subject_id}")
    coords = list(_coordinate_pairs(geom.get("coordinates")))
    try:
        for coordinate in coords:
            checked_point(*coordinate)
    except (TypeError, ValueError):
        raise VerificationError(f"invalid longitude/latitude coordinate for {subject_id}")
    if not coords:
        raise VerificationError(f"invalid longitude/latitude coordinate for {subject_id}")
    return polygon


def load_pinned_context():
    blobs = {path: pinned_bytes(path) for path in PINS}
    scope = json.loads(blobs[f"{CHILD}/scope.json"])
    assessment = json.loads(blobs[f"{CHILD}/assessment.json"])
    parent = json.loads(blobs[f"{PARENT}/assessment.json"])
    child_sources = json.loads(blobs[f"{CHILD}/sources.json"])
    inherited = next((source for source in child_sources.get("sources", [])
                      if source.get("title") == "Inherited parent assessment and exact project baseline polygons"), None)
    declared_parent_files = {item["path"]: (item["bytes"], item["sha256"])
                             for item in inherited.get("files", [])} if inherited else {}
    expected_parent_files = DECLARED_PARENT_FILES
    if declared_parent_files != expected_parent_files:
        raise VerificationError("inherited parent file descriptors disagree with the pinned #603 source receipt")
    ids = [item.get("id") for item in scope.get("subjects", []) if isinstance(item, dict)]
    child_rows = assessment.get("subjects", [])
    child_ids = [item.get("id") for item in child_rows if isinstance(item, dict)]
    validate_subject_ids(ids, "assigned scope")
    validate_subject_ids(child_ids, "child assessment")
    if assessment.get("assigned_subject_count") != len(EXPECTED) or assessment.get("assessed_subject_count") != len(EXPECTED):
        raise VerificationError("child assessment counts disagree with the exact assigned scope")
    if assessment.get("result_counts") != {"evidence": 0, "justified_exception": 0, "unresolved": len(EXPECTED)}:
        raise VerificationError("child assessment result ledger changed or no longer preserves all eight unresolved findings")
    parent_rows = [row for row in parent.get("locations", []) if row.get("location_id") in EXPECTED]
    parent_by_id = {row.get("location_id"): row for row in parent_rows}
    if len(parent_rows) != len(EXPECTED) or set(parent_by_id) != set(EXPECTED):
        raise VerificationError("inherited parent assessment is missing or duplicates an assigned ID")
    child_by_id = {row["id"]: row for row in child_rows}
    scope_names = {row["id"]: row.get("name") for row in scope["subjects"]}
    for subject_id in EXPECTED:
        if child_by_id[subject_id].get("name") != scope_names[subject_id]:
            raise VerificationError(f"child scope and assessment names disagree for {subject_id}")
        if canonical_chain(child_by_id[subject_id].get("full_parent_chain")) != canonical_chain(
            parent_by_id[subject_id].get("full_parent_chain")
        ):
            raise VerificationError(f"parent chain differs from inherited assessment for {subject_id}")

    polygon_raw = gzip.decompress(blobs[f"{PARENT}/sources/current-scope-and-parents.geojson.gz"])
    collection = json.loads(polygon_raw)
    if collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
        raise VerificationError("pinned polygon source is not a FeatureCollection")
    found = {subject_id: [] for subject_id in EXPECTED}
    for feature in collection["features"]:
        props = feature.get("properties") if isinstance(feature, dict) else None
        subject_id = props.get("id") if isinstance(props, dict) else None
        if subject_id in found:
            found[subject_id].append(feature)
    polygons = {}
    for subject_id in EXPECTED:
        matches = found[subject_id]
        if len(matches) != 1:
            raise VerificationError(f"pinned geometry occurs {len(matches)} times for {subject_id}")
        feature = matches[0]
        polygons[subject_id] = validate_polygon(feature, subject_id)
    return polygons, {p: {"bytes": PINS[p][0], "sha256": PINS[p][1]} for p in PINS}


def _coordinate_pairs(value):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in value[:2]):
            yield value[0], value[1]
        else:
            for child in value:
                yield from _coordinate_pairs(child)


def validate_layer_metadata(layer):
    if layer.get("geometryType") != "esriGeometryPoint":
        raise VerificationError("service layer is not a point layer")
    if layer.get("advancedQueryCapabilities", {}).get("supportsPagination") is not True:
        raise VerificationError("service metadata does not confirm pagination support")
    maximum = layer.get("maxRecordCount")
    if not isinstance(maximum, int) or maximum <= 0:
        raise VerificationError("invalid service maxRecordCount")
    fields = {field.get("name") for field in layer.get("fields", []) if isinstance(field, dict)}
    if not {"OBJECTID", "CommunityId", "CommunityName"}.issubset(fields):
        raise VerificationError("required service identity/name fields are missing")
    return maximum


def validate_inventory(object_ids, pages):
    if not isinstance(object_ids, list) or not object_ids:
        raise VerificationError("empty or absent source inventory")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in object_ids):
        raise VerificationError("inventory contains a malformed object ID")
    if len(set(object_ids)) != len(object_ids):
        raise VerificationError("inventory contains duplicate object IDs")
    received = {}
    community_ids = set()
    if not isinstance(pages, list) or not pages:
        raise VerificationError("empty or absent feature pages")
    for page in pages:
        if not isinstance(page, dict) or page.get("type") != "FeatureCollection" or "features" not in page:
            raise VerificationError("malformed or absent FeatureCollection")
        if not isinstance(page["features"], list) or not page["features"]:
            raise VerificationError("empty feature page")
        if page.get("exceededTransferLimit") is True:
            raise VerificationError("service reports exceededTransferLimit")
        for feature in page["features"]:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise VerificationError("malformed feature")
            props = feature.get("properties")
            geom = feature.get("geometry")
            if not isinstance(props, dict) or not isinstance(geom, dict) or geom.get("type") != "Point":
                raise VerificationError("missing properties or non-Point geometry")
            oid = props.get("OBJECTID")
            community_id = props.get("CommunityId")
            name = props.get("CommunityName")
            coords = geom.get("coordinates")
            if not isinstance(oid, int) or isinstance(oid, bool) or oid in received:
                raise VerificationError("malformed or duplicate response OBJECTID")
            if feature.get("id", oid) != oid:
                raise VerificationError("GeoJSON feature ID disagrees with OBJECTID")
            if not isinstance(community_id, str) or not community_id or community_id in community_ids:
                raise VerificationError("malformed or duplicate CommunityId")
            if not isinstance(name, str) or not name.strip():
                raise VerificationError("missing CommunityName")
            if not isinstance(coords, list) or len(coords) != 2 or any(
                not isinstance(n, (int, float)) or isinstance(n, bool) or not math.isfinite(n) for n in coords
            ):
                raise VerificationError("malformed point coordinates")
            try:
                checked_point(*coords)
            except (TypeError, ValueError) as exc:
                raise VerificationError("point coordinates outside longitude/latitude bounds") from exc
            community_ids.add(community_id)
            received[oid] = feature
    if set(received) != set(object_ids) or len(received) != len(object_ids):
        raise VerificationError("partial response: feature OBJECTIDs do not equal inventory IDs")
    return received


def intersect(polygons, features):
    hits = {subject_id: [] for subject_id in EXPECTED}
    for feature in features.values():
        props = feature["properties"]
        point = Point(*checked_point(*feature["geometry"]["coordinates"]))
        for subject_id, polygon in polygons.items():
            if polygon.intersects(point):
                hits[subject_id].append({
                    "object_id": props["OBJECTID"],
                    "community_id": props["CommunityId"],
                    "community_name": props["CommunityName"],
                    "area_type": props.get("CommunityAreaTypeName"),
                    "community_type": props.get("CommunityTypeName"),
                    "is_active": props.get("IsActive"),
                })
    return hits


def request_json(url, params):
    request = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                     headers={"User-Agent": "WorldAtlas geography evidence reproduction/2.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("service returned malformed JSON") from exc
    if not isinstance(value, dict) or "error" in value:
        raise VerificationError(f"service error or malformed JSON object: {value.get('error') if isinstance(value, dict) else 'not object'}")
    return value, raw


def query_live(maximum):
    base = {"where": "1=1", "geometry": json.dumps(EXTENT, separators=(",", ":")),
            "geometryType": "esriGeometryEnvelope", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects"}
    inventory, inventory_raw = request_json(SERVICE + "/query", {**base, "returnIdsOnly": "true", "f": "json"})
    ids = inventory.get("objectIds")
    if inventory.get("objectIdFieldName") != "OBJECTID":
        raise VerificationError("source inventory identity field changed from OBJECTID")
    if not isinstance(ids, list) or not ids:
        raise VerificationError("service returned absent or empty objectIds inventory")
    if inventory.get("exceededTransferLimit") is True:
        raise VerificationError("inventory reports exceededTransferLimit")
    pages, page_digests = [], []
    page_size = min(maximum, 500)
    for start in range(0, len(ids), page_size):
        response, raw = request_json(SERVICE + "/query", {
            **base, "outFields": "*", "returnGeometry": "true", "outSR": "4326",
            "resultOffset": str(start), "resultRecordCount": str(page_size), "f": "geojson",
        })
        if response.get("exceededTransferLimit") is True:
            raise VerificationError("feature page reports exceededTransferLimit")
        if response.get("type") != "FeatureCollection":
            raise VerificationError("service page is not a GeoJSON FeatureCollection")
        pages.append(response)
        page_digests.append({"bytes": len(raw), "sha256": digest(raw), "offset": start,
                             "requested_count": min(page_size, len(ids) - start),
                             "returned_features": len(response.get("features", [])) if isinstance(response.get("features"), list) else None})
    features = validate_inventory(ids, pages)
    return features, {"retrieved_at": datetime.now(timezone.utc).isoformat(), "inventory_count": len(ids),
                      "inventory_response_bytes": len(inventory_raw), "inventory_response_sha256": digest(inventory_raw),
                      "single_page_response_bytes": page_digests[0]["bytes"] if len(page_digests) == 1 else None,
                      "single_page_response_sha256": page_digests[0]["sha256"] if len(page_digests) == 1 else None,
                      "pages": page_digests}


def self_test():
    pinned_polygons, _ = load_pinned_context()
    representative = pinned_polygons[EXPECTED[0]].representative_point()
    good = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "OBJECTID": 1, "CommunityId": "c1", "CommunityName": "Control"},
        "geometry": {"type": "Point", "coordinates": [representative.x, representative.y]}}]}
    checks = []
    def rejects(label, object_ids, pages):
        nonlocal checks
        try:
            validate_inventory(object_ids, pages)
        except VerificationError:
            checks.append(label)
            return
        raise AssertionError(f"negative control did not reject: {label}")
    rejects("absent features", [1], [{"type": "FeatureCollection"}])
    rejects("empty features", [1], [{"type": "FeatureCollection", "features": []}])
    rejects("partial page", [1, 2], [good])
    rejects("duplicate object ID", [1], [good, good])
    rejects("duplicate inventory", [1, 1], [good])
    transfer_limited = {"type": "FeatureCollection", "exceededTransferLimit": True, "features": good["features"]}
    rejects("transfer-limited page", [1], [transfer_limited])
    duplicate_community = json.loads(json.dumps(good))
    duplicate_community["features"][0]["properties"]["OBJECTID"] = 2
    rejects("duplicate CommunityId", [1, 2], [good, duplicate_community])
    try:
        validate_subject_ids([EXPECTED[0], *EXPECTED[2:]], "control scope")
    except VerificationError:
        checks.append("missing subject ID")
    else:
        raise AssertionError("missing subject control did not reject")
    try:
        validate_subject_ids([*EXPECTED, EXPECTED[0]], "control scope")
    except VerificationError:
        checks.append("duplicate subject ID")
    else:
        raise AssertionError("duplicate subject control did not reject")
    try:
        validate_polygon({"geometry": {"type": "Polygon", "coordinates": [
            [[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}}, EXPECTED[0])
    except VerificationError:
        checks.append("invalid polygon geometry")
    else:
        raise AssertionError("invalid polygon control did not reject")
    try:
        path = f"{PARENT}/sources/current-scope-and-parents.geojson.gz"
        check_pin(path, b"changed polygon baseline")
    except VerificationError:
        checks.append("changed baseline pin")
    else:
        raise AssertionError("changed baseline control did not reject")
    valid = validate_inventory([1], [good])
    hit = intersect(pinned_polygons, valid)
    hit_total = sum(len(rows) for rows in hit.values())
    if len(hit[EXPECTED[0]]) != 1 or hit_total != 1:
        raise AssertionError("positive one-hit control against the actual pinned subject geometry failed")
    positive_hit_ok = True
    outside_feature = json.loads(json.dumps(good))
    outside_feature["features"][0]["geometry"]["coordinates"] = [0, 0]
    outside = intersect(pinned_polygons, validate_inventory([1], [outside_feature]))
    if any(outside.values()):
        raise AssertionError("positive zero-hit control failed")
    positive_zero_ok = True
    negative = {"method_id": "source-inventory-and-intersection", "kind": "negative-control", "outcome": "passed",
                "controls_passed": checks}
    positive = {"method_id": "source-inventory-and-intersection", "kind": "positive-control", "outcome": "passed",
                "one_hit": positive_hit_ok, "zero_hit": positive_zero_ok,
                "description": "One synthetic point at the representative point of a real pinned subject polygon intersects exactly that one subject; a point outside the Alaska footprints yields zero hits."}
    print(json.dumps({"controls_passed": len(checks) + 2, "positive_hit": "one point intersects one polygon",
                      "negative": checks}, indent=2))
    return positive, negative


def write_new(path, payload):
    destination = Path(path).resolve()
    if OWNED.resolve() not in destination.parents:
        raise VerificationError("output must be inside the declared owned directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
    with destination.open("xb") as stream:
        stream.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="run offline positive/negative controls")
    parser.add_argument("--output", help="write a new dated summary inside this owned directory; existing files are never overwritten")
    parser.add_argument("--positive-control-output")
    parser.add_argument("--negative-control-output")
    args = parser.parse_args(argv)
    if args.self_test:
        positive, negative = self_test()
        if args.positive_control_output:
            write_new(args.positive_control_output, positive)
        if args.negative_control_output:
            write_new(args.negative_control_output, negative)
        return 0
    polygons, pin_summary = load_pinned_context()
    meta, metadata_raw = request_json(SERVICE, {"f": "json"})
    layer = meta
    maximum = validate_layer_metadata(layer)
    features, vintage = query_live(maximum)
    hits = intersect(polygons, features)
    payload = {
        "retrieval": vintage,
        "service_metadata": {"url": SERVICE, "retrieved_at": vintage["retrieved_at"],
                             "bytes": len(metadata_raw), "sha256": digest(metadata_raw),
                             "geometry_type": layer["geometryType"], "max_record_count": maximum,
                             "supports_pagination": layer["advancedQueryCapabilities"]["supportsPagination"]},
        "baseline_commit": BASELINE_COMMIT,
        "baseline_pins": pin_summary,
        "feature_count": len(features),
        "subject_hit_counts": {key: len(hits[key]) for key in EXPECTED},
        "subject_hits": hits,
        "recorded_2026_10_03_content_fingerprint": {
            "status": "exact-content-match" if (
                len(vintage["pages"]) == 1 and
                vintage["single_page_response_sha256"] == "a1c13f271c4a67ab470b99a7adfe5979b2673724fd69a7bde54c61aefa4b5654" and
                vintage["single_page_response_bytes"] == 415447 and len(features) == 487
            ) else "current-vintage-differs-or-not-comparable",
            "recorded_response_sha256": "a1c13f271c4a67ab470b99a7adfe5979b2673724fd69a7bde54c61aefa4b5654",
            "recorded_response_bytes": 415447,
            "recorded_feature_count": 487,
            "temporal_provenance": "The exact original capture time/vintage cannot be independently reconstructed: raw bytes were not retained and the live service reports no historical archive. This fingerprint comparison is against a separately dated current live observation, not an assertion that the observation occurred on the original date."
        },
        "interpretation": "A source point hit is a review lead, not proof that the physical fragment is a settlement. Zero hits do not establish settlement absence; DCRA's inventory is not comprehensive.",
    }
    if args.output:
        write_new(args.output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (VerificationError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        sys.exit(2)
