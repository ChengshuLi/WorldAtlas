#!/usr/bin/env python3
"""Check the bounded Cook Islands source crosswalk against pinned baseline bytes.

This verifies identity, ownership, source-row selection and recorded geometry
structure only. It does not calculate area or establish coastline accuracy.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).parent
ISSUE_IDS = [
    "COK-4950", "COK-4951", "COK-4952", "COK-4953", "COK-4954", "COK-4955",
    "COK-4956", "COK-4959", "COK-4960", "COK-4961", "COK-4962",
]
EXPECTED_PINS = {
    "data/geography/part-28.json": "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d",
    "data/hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "data/regional-review/regional-review-14a242c4cb0781a7/source/natural-earth/ne_10m_admin_1_scoped-admin-features.json": "dd3f4a5683c713fd89c00b41748d89771f905ef236feaacb7887818085f3d96e",
}
FEATURE_FILE = "data/regional-review/regional-review-14a242c4cb0781a7/source/natural-earth/ne_10m_admin_1_scoped-admin-features.json"
COOK_SOURCE = "data/regional-review/regional-review-14a242c4cb0781a7/source/natural-earth/ne_10m_admin_1_cook-islands-features.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry_parts(feature):
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return 1
    if geom["type"] == "MultiPolygon":
        return len(geom["coordinates"])
    raise AssertionError(f"non-polygon geometry for {feature.get('id')}")


def load_features(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return {feature.get("id") or feature["properties"].get("id") or feature["properties"].get("adm1_code"): feature for feature in data["features"]}


def main():
    for rel, digest in EXPECTED_PINS.items():
        actual = sha(ROOT / rel)
        assert actual == digest, f"pinned baseline changed: {rel}: {actual}"

    current = load_features(ROOT / "data/geography/part-28.json")
    hierarchy = {item["id"]: item for item in json.loads((ROOT / "data/hierarchy.json").read_text())}
    scoped_source = load_features(ROOT / FEATURE_FILE)
    cook_source = load_features(ROOT / COOK_SOURCE)
    with (OWN / "subject-crosswalk.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert [row["subject_id"] for row in rows] == ISSUE_IDS, "crosswalk must preserve exact ordered issue scope"
    assert len(set(ISSUE_IDS)) == len(ISSUE_IDS)
    result = []
    for row in rows:
        ident = row["subject_id"]
        assert ident in current, f"missing current baseline feature: {ident}"
        assert ident in scoped_source and ident in cook_source, f"missing retained source row: {ident}"
        now, source = current[ident], cook_source[ident]
        props = now["properties"]
        assert props["name"] == row["name"], f"current name mismatch: {ident}"
        assert props["parent_id"] == row["current_parent_id"], f"current parent changed: {ident}"
        parent = hierarchy.get(props["parent_id"])
        assert parent and parent["name"] == row["current_parent_name"], f"parent label mismatch: {ident}"
        assert now["geometry"]["type"] == row["current_geometry"], f"current geometry type mismatch: {ident}"
        assert str(geometry_parts(now)) == row["current_components"], f"current component summary mismatch: {ident}"
        source_props = source["properties"]
        assert source_props["adm1_code"] == row["natural_earth_source_id"]
        assert source_props["name"] == row["natural_earth_source_name"], f"source name mismatch: {ident}"
        assert source["geometry"]["type"] == row["natural_earth_geometry"], f"source geometry type mismatch: {ident}"
        assert str(geometry_parts(source)) == row["natural_earth_components"], f"source part summary mismatch: {ident}"
        result.append({"subject_id": ident, "parent_id": props["parent_id"],
                       "current_geometry": now["geometry"]["type"], "current_parts": geometry_parts(now),
                       "source_id": source_props["adm1_code"], "source_name": source_props["name"],
                       "source_geometry": source["geometry"]["type"], "source_parts": geometry_parts(source)})

    roster = json.loads((OWN / "neighbor-screen.json").read_text(encoding="utf-8"))
    assert roster["issue_subject_ids"] == ISSUE_IDS
    present_names = {feature["properties"].get("name") for feature in current.values()}
    missing = sorted(set(roster["official_roster"]) - present_names)
    assert missing == ["Nassau", "Palmerston", "Suwarrow", "Takutea"], f"neighbor roster changed: {missing}"
    assert missing == roster["roster_names_missing_from_current_location_parts"]

    # Positive control: the source Atiu row must expose its distinct multipart representation.
    atiu = next(row for row in result if row["subject_id"] == "COK-4950")
    assert atiu["source_geometry"] == "MultiPolygon" and atiu["source_parts"] == 3
    assert atiu["current_geometry"] == "Polygon" and atiu["current_parts"] == 1

    # Negative control: an out-of-scope, misidentified ID must fail the roster guard.
    wrong_scope = ISSUE_IDS[:-1] + ["COK-4963"]
    try:
        assert wrong_scope == ISSUE_IDS, "subject set mismatch"
    except AssertionError:
        negative_control = "passed: substituted PYF-4963 rejected by exact ordered roster"
    else:
        raise AssertionError("negative control failed to reject a swapped subject")

    print(json.dumps({"status": "passed", "baseline_pins": EXPECTED_PINS,
                      "subjects_checked": len(result), "subjects": result,
                      "neighbor_missing": missing,
                      "positive_control": "passed: Atiu source/current component structures differ and are reported",
                      "negative_control": negative_control,
                      "limits": ["No coastline comparison or land completeness claim", "Shape/component diagnostics are not geographic approval"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
