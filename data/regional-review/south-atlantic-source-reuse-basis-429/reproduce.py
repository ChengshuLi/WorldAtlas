#!/usr/bin/env python3
"""Reproduce issue #1143's exact 268-subject source-vintage crosswalk."""

import csv
import hashlib
import io
import json
import struct
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
BASELINE = "dab6ef29468eb97226f642783127720444f299c9"
PARENT = "data/regional-review/regional-review-e5d9b45b0ad3ed31/"
GEOJSON_PATH = PARENT + "sources/geoboundaries-USA-ADM2-2018.geojson"
METADATA_PATH = PARENT + "sources/geoboundaries-USA-ADM2-2018-metadata.json"
CSV_PATH = PARENT + "individual-assessments.csv"
SCOPE_PATH = PARENT + "issue-scope.json"
REGISTRY_PATH = PARENT + "source-register.json"
CBF_ZIP = PACKET / "sources/cb_2018_us_county_500k.zip"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def baseline_bytes(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", BASELINE + ":" + path])


def parse_dbf(data):
    if len(data) < 33 or data[32] == 13:
        raise ValueError("Empty or invalid DBF")
    record_count = struct.unpack_from("<I", data, 4)[0]
    header_length, record_length = struct.unpack_from("<HH", data, 8)
    fields = []
    offset = 32
    while data[offset] != 13:
        desc = data[offset:offset + 32]
        name = desc[:11].split(b"\0", 1)[0].decode("ascii")
        fields.append((name, desc[16]))
        offset += 32
    if offset + 1 != header_length:
        raise ValueError("Unexpected DBF header length")
    rows = []
    for index in range(record_count):
        start = header_length + index * record_length
        record = data[start:start + record_length]
        if len(record) != record_length:
            raise ValueError("Truncated DBF record")
        if record[0:1] == b"*":
            continue
        cursor, row = 1, {}
        for name, width in fields:
            row[name] = record[cursor:cursor + width].decode("utf-8").strip()
            cursor += width
        rows.append(row)
    return record_count, rows


def main():
    contract = json.loads((PACKET / "issue-1143-contract.json").read_text(encoding="utf-8"))
    expected = contract["issue"]["machine_contract"]["evidence_quality"]["subject_ids"]
    pins = contract["baseline_pins"]
    input_digests = []
    for pin in pins:
        raw = baseline_bytes(pin["path"])
        if sha256(raw) != pin["sha256"]:
            raise ValueError("Issue pin mismatch: " + pin["path"])
        input_digests.append({"path": pin["path"], "sha256": sha256(raw), "bytes": len(raw)})

    scope = json.loads(baseline_bytes(SCOPE_PATH))
    if expected != scope["member_location_ids"] or len(set(expected)) != 268:
        raise ValueError("Issue #1143 subjects differ from exact parent packet scope")
    atlas_locations = {}
    for part in (25, 26, 27):
        collection = json.loads(baseline_bytes("data/geography/part-" + str(part) + ".json"))
        for feature in collection["features"]:
            location_id = feature.get("id") or feature.get("properties", {}).get("id")
            if location_id in expected:
                atlas_locations.setdefault(location_id, []).append(part)
    if set(atlas_locations) != set(expected) or any(len(parts) != 1 for parts in atlas_locations.values()):
        raise ValueError("Scoped IDs do not map once to pinned Atlas geography parts")
    source = json.loads(baseline_bytes(GEOJSON_PATH))
    metadata = json.loads(baseline_bytes(METADATA_PATH))
    source_register = json.loads(baseline_bytes(REGISTRY_PATH))
    source_descriptor = next(row for row in source_register["retained_evidence"]
                             if row["path"] == GEOJSON_PATH)
    if source_descriptor["sha256"] != sha256(baseline_bytes(GEOJSON_PATH)):
        raise ValueError("Source-register GeoJSON digest mismatch")
    if metadata.get("boundaryLicense") != "Public Domain" or metadata.get("admUnitCount") != "3233":
        raise ValueError("Pinned source metadata differs from recorded license/count")
    if len(source["features"]) != 3233:
        raise ValueError("Pinned GeoBoundaries feature count mismatch")

    feature_map = {}
    for feature in source["features"]:
        shape_id = feature.get("properties", {}).get("shapeID")
        if not shape_id or shape_id in feature_map:
            raise ValueError("Missing or duplicate source shapeID")
        feature_map[shape_id] = feature

    with io.TextIOWrapper(io.BytesIO(baseline_bytes(CSV_PATH)), encoding="utf-8", newline="") as stream:
        assessments = list(csv.DictReader(stream))
    by_id = {row["atlas_id"]: row for row in assessments}
    if len(assessments) != 268 or len(by_id) != 268 or set(by_id) != set(expected):
        raise ValueError("Prior per-subject assessment roster is incomplete or differs")

    with zipfile.ZipFile(CBF_ZIP, "r") as archive:
        dbf_names = [name for name in archive.namelist() if name.endswith(".dbf")]
        if dbf_names != ["cb_2018_us_county_500k.dbf"]:
            raise ValueError("Unexpected Census CBF archive DBF inventory")
        cpg = archive.read("cb_2018_us_county_500k.cpg").decode("ascii").strip()
        if cpg.upper() != "UTF-8":
            raise ValueError("Unexpected Census CBF DBF character encoding")
        dbf_bytes = archive.read(dbf_names[0])
    dbf_count, cbf_rows = parse_dbf(dbf_bytes)
    if dbf_count != 3233 or len(cbf_rows) != dbf_count:
        raise ValueError("Census CBF 2018 DBF count mismatch")
    cbf_index = {}
    for row in cbf_rows:
        key = (row["STATEFP"], row["NAME"])
        cbf_index.setdefault(key, []).append(row)

    state_fips = {"Florida": "12", "North Carolina": "37",
                  "South Carolina": "45", "West Virginia": "54"}
    crosswalk = []
    for atlas_id in expected:
        assessment = by_id[atlas_id]
        native_id = atlas_id.rsplit(":", 1)[1]
        feature = feature_map.get(native_id)
        if feature is None or feature.get("properties", {}).get("shapeGroup") != "USA":
            raise ValueError("Subject does not resolve uniquely to USA source: " + atlas_id)
        properties = feature["properties"]
        if properties.get("shapeName") != assessment["source_name"]:
            raise ValueError("Source name differs for " + atlas_id)
        if (assessment["source_role"] != "ADM2" or assessment["atlas_admin_role"] != "Counties" or
                assessment["semantic_role_finding"] != "justified" or
                assessment["identity_and_parent_finding"] != "justified"):
            raise ValueError("Prior subject-level county role/parent finding differs for " + atlas_id)
        fips = state_fips.get(assessment["parent_name"])
        if fips is None:
            raise ValueError("Unexpected state parent: " + assessment["parent_name"])
        matches = cbf_index.get((fips, assessment["source_name"]), [])
        if len(matches) != 1:
            raise ValueError("Census 2018 name/state match is not unique for " + atlas_id)
        cbf = matches[0]
        geoid = cbf["GEOID"]
        if geoid != fips + cbf["COUNTYFP"]:
            raise ValueError("Census GEOID disagrees with state/county components")
        crosswalk.append({
            "atlas_id": atlas_id,
            "source_id": "gb:USA:ADM2",
            "source_shape_id": native_id,
            "source_name": properties["shapeName"],
            "source_role": assessment["source_role"],
            "atlas_admin_role": assessment["atlas_admin_role"],
            "prior_role_finding": assessment["semantic_role_finding"],
            "prior_identity_parent_finding": assessment["identity_and_parent_finding"],
            "parent_state": assessment["parent_name"],
            "census_2018_statefp": fips,
            "census_2018_countyfp": cbf["COUNTYFP"],
            "census_2018_geoid": geoid,
            "census_2018_name": cbf["NAME"],
            "census_match_count": 1,
        })

    if len({row["source_shape_id"] for row in crosswalk}) != 268:
        raise ValueError("Scoped source feature IDs are not unique")
    if len({row["census_2018_geoid"] for row in crosswalk}) != 268:
        raise ValueError("Scoped 2018 Census GEOIDs are not unique")

    digest_ledger = {
        "version": 1,
        "baseline_commit": BASELINE,
        "issue_pins": input_digests,
        "additional_reproduction_inputs": [
            {"path": CSV_PATH, "sha256": sha256(baseline_bytes(CSV_PATH)), "bytes": len(baseline_bytes(CSV_PATH))},
        ],
        "atlas_geography_parts": [
            {"path": "data/geography/part-" + str(part) + ".json",
             "sha256": sha256(baseline_bytes("data/geography/part-" + str(part) + ".json")),
             "bytes": len(baseline_bytes("data/geography/part-" + str(part) + ".json"))}
            for part in (25, 26, 27)
        ],
    }
    digest_ledger_bytes = (json.dumps(digest_ledger, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (PACKET / "baseline-input-digests.json").write_bytes(digest_ledger_bytes)

    source_payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")) + "\n"
                              for row in crosswalk).encode("utf-8")
    (PACKET / "subject-source-crosswalk.jsonl").write_bytes(source_payload)
    summary = {
        "version": 1,
        "method_id": "county-product-source-crosswalk",
        "baseline_commit": BASELINE,
        "subject_count": len(expected),
        "unique_subject_count": len(set(expected)),
        "issue_pin_count": len(pins),
        "pinned_atlas_geography_matches": len(atlas_locations),
        "geoboundaries_feature_count": len(source["features"]),
        "scoped_geoboundaries_feature_matches": len(crosswalk),
        "census_2018_cbf_dbf_record_count": dbf_count,
        "census_2018_cbf_dbf_encoding": cpg,
        "scoped_census_name_state_unique_matches": sum(row["census_match_count"] == 1 for row in crosswalk),
        "unique_source_shape_ids": len({row["source_shape_id"] for row in crosswalk}),
        "unique_census_2018_geoids": len({row["census_2018_geoid"] for row in crosswalk}),
        "county_admin_role_assessments": sum(row["atlas_admin_role"] == "Counties" and row["prior_role_finding"] == "justified" for row in crosswalk),
        "all_parent_states_in_scope": sorted(set(row["parent_state"] for row in crosswalk)),
        "crosswalk_sha256": sha256(source_payload),
        "census_cb_zip_sha256": sha256(CBF_ZIP.read_bytes()),
        "limitations": [
            "Name/state crosswalk is identity evidence only, not boundary or geometry equivalence.",
            "A matching CBF row does not establish current validity, completeness, or legal authority.",
            "Project-specific derivative rights remain unresolved as documented in source-reuse-assessment.json.",
        ],
    }
    summary_bytes = (json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (PACKET / "reproduction-summary.json").write_bytes(summary_bytes)

    positive = {
        "method_id": "county-product-source-crosswalk", "kind": "measurement", "outcome": "passed",
        "evidence_path": "data/regional-review/south-atlantic-source-reuse-basis-429/positive-control.json",
        "subject_count": 268, "matched_source_ids": 268, "unique_census_name_state_matches": 268,
        "assertion": "Every exact issue subject resolves once in pinned Atlas geography parts, once to its pinned source shapeID, and once by source name plus state to the retrieved 2018 Census CBF.",
    }
    negative = {
        "method_id": "county-product-source-crosswalk", "kind": "measurement", "outcome": "passed",
        "evidence_path": "data/regional-review/south-atlantic-source-reuse-basis-429/negative-control.json",
        "duplicate_subject_rejected": len(set(expected + [expected[0]])) != len(expected + [expected[0]]),
        "unknown_source_id_rejected": "NOT-A-SOURCE-ID" not in feature_map,
        "wrong_state_match_count": len(cbf_index.get(("00", by_id[expected[0]]["source_name"]), [])),
        "assertion": "Duplicate roster input, an invented source ID, and a deliberately invalid state code do not pass the scoped identity checks.",
    }
    if not positive["subject_count"] == positive["matched_source_ids"] == positive["unique_census_name_state_matches"] == 268:
        raise ValueError("Positive control failed")
    if not negative["duplicate_subject_rejected"] or not negative["unknown_source_id_rejected"] or negative["wrong_state_match_count"] != 0:
        raise ValueError("Negative control failed")
    for name, result in (("positive-control.json", positive), ("negative-control.json", negative)):
        (PACKET / name).write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    generated = ["baseline-input-digests.json", "subject-source-crosswalk.jsonl",
                 "reproduction-summary.json", "positive-control.json", "negative-control.json"]
    print(json.dumps({"status": "passed", "subject_count": 268,
                      "outputs": {name: sha256((PACKET / name).read_bytes()) for name in generated}},
                     sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
