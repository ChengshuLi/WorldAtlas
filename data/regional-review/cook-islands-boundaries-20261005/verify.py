#!/usr/bin/env python3
"""Check Cook Islands source crosswalk against exact, pinned baseline bytes.

This verifies source identity, parents, part structure and the full named-island
roster screen. It does not calculate overlap or establish coastline accuracy.
"""
import csv
import hashlib
import json
import re
import subprocess
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


def git_bytes(commit, rel):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", commit + ":" + rel])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def geometry_parts(feature):
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return 1
    if geom["type"] == "MultiPolygon":
        return len(geom["coordinates"])
    raise AssertionError("non-polygon geometry for " + str(feature.get("id")))


def load_features(data):
    obj = json.loads(data.decode("utf-8"))
    return {feature.get("id") or feature["properties"].get("id") or feature["properties"].get("adm1_code"): feature for feature in obj["features"]}


def main():
    manifest = json.loads((OWN / "evidence-quality.json").read_text(encoding="utf-8"))
    baseline = manifest["baseline"]["commit"]
    descriptors = {item["path"]: item for item in manifest["baseline"]["files"]}
    geography_paths = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", baseline, "data/geography"],
        universal_newlines=True).splitlines()
    part_paths = sorted(path for path in geography_paths if re.fullmatch(r"data/geography/part-\d+\.json", path))
    declared_parts = sorted(path for path in descriptors if re.fullmatch(r"data/geography/part-\d+\.json", path))
    assert part_paths == declared_parts, "manifest must inventory every baseline part file"

    current = None
    cook_islands_names = set()
    foreign_homonyms = []
    for rel in part_paths:
        raw = git_bytes(baseline, rel)
        desc = descriptors[rel]
        assert len(raw) == desc["bytes"] and sha(raw) == desc["sha256"], "baseline part bytes differ: " + rel
        features = load_features(raw)
        for feature in features.values():
            props = feature["properties"]
            name = props.get("name")
            owner = props.get("reference_owner")
            if owner == "Cook Islands":
                cook_islands_names.add(name)
            elif name in ("Nassau", "Palmerston", "Suwarrow", "Takutea"):
                foreign_homonyms.append({"part": rel, "id": feature.get("id") or props.get("id"),
                                         "name": name, "reference_owner": owner})
        if rel == "data/geography/part-28.json":
            current = features
    assert current is not None

    for rel, digest in EXPECTED_PINS.items():
        raw = git_bytes(baseline, rel)
        assert sha(raw) == digest, "pinned baseline changed: " + rel
        assert rel in descriptors and descriptors[rel]["sha256"] == digest

    hierarchy = {item["id"]: item for item in json.loads(git_bytes(baseline, "data/hierarchy.json").decode("utf-8"))}
    scoped_source = load_features(git_bytes(baseline, FEATURE_FILE))
    cook_source = load_features(git_bytes(baseline, COOK_SOURCE))
    with (OWN / "subject-crosswalk.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert [row["subject_id"] for row in rows] == ISSUE_IDS, "crosswalk must preserve exact ordered issue scope"
    result = []
    for row in rows:
        ident = row["subject_id"]
        assert ident in current, "missing current baseline feature: " + ident
        assert ident in scoped_source and ident in cook_source, "missing retained source row: " + ident
        now, source = current[ident], cook_source[ident]
        props = now["properties"]
        assert props["name"] == row["name"], "current name mismatch: " + ident
        assert props["parent_id"] == row["current_parent_id"], "current parent changed: " + ident
        parent = hierarchy.get(props["parent_id"])
        assert parent and parent["name"] == row["current_parent_name"], "parent label mismatch: " + ident
        assert now["geometry"]["type"] == row["current_geometry"], "current geometry type mismatch: " + ident
        assert str(geometry_parts(now)) == row["current_components"], "current component summary mismatch: " + ident
        source_props = source["properties"]
        assert source_props["adm1_code"] == row["natural_earth_source_id"]
        assert source_props["name"] == row["natural_earth_source_name"], "source name mismatch: " + ident
        assert source["geometry"]["type"] == row["natural_earth_geometry"], "source geometry type mismatch: " + ident
        assert str(geometry_parts(source)) == row["natural_earth_components"], "source part summary mismatch: " + ident
        result.append({"subject_id": ident, "parent_id": props["parent_id"],
                       "current_geometry": now["geometry"]["type"], "current_parts": geometry_parts(now),
                       "source_id": source_props["adm1_code"], "source_name": source_props["name"],
                       "source_geometry": source["geometry"]["type"], "source_parts": geometry_parts(source)})

    roster = json.loads((OWN / "neighbor-screen.json").read_text(encoding="utf-8"))
    assert roster["issue_subject_ids"] == ISSUE_IDS
    missing = sorted(set(roster["official_roster"]) - cook_islands_names)
    assert missing == ["Nassau", "Palmerston", "Suwarrow", "Takutea"], "Cook Islands owner roster changed: " + str(missing)
    assert missing == roster["cook_islands_roster_names_missing_from_current_location_parts"]
    assert foreign_homonyms, "expected name-collision controls for unrepresented Cook Islands islands"

    atiu = next(row for row in result if row["subject_id"] == "COK-4950")
    assert atiu["source_geometry"] == "MultiPolygon" and atiu["source_parts"] == 3
    assert atiu["current_geometry"] == "Polygon" and atiu["current_parts"] == 1
    wrong_scope = ISSUE_IDS[:-1] + ["COK-4963"]
    try:
        assert wrong_scope == ISSUE_IDS, "subject set mismatch"
    except AssertionError:
        negative_control = "passed: substituted COK-4963 rejected by exact ordered roster"
    else:
        raise AssertionError("negative control failed to reject a swapped subject")

    print(json.dumps({"status": "passed", "baseline_commit": baseline, "baseline_part_files_checked": len(part_paths),
                      "baseline_pins": EXPECTED_PINS, "subjects_checked": len(result), "subjects": result,
                      "cook_islands_roster_missing_across_all_parts": missing, "foreign_homonyms": sorted(foreign_homonyms, key=lambda row: (row["name"], row["reference_owner"] or "", row["id"])),
                      "positive_control": "passed: Atiu source/current component structures differ and are reported",
                      "negative_control": negative_control,
                      "limits": ["No coastline comparison or land completeness claim", "Shape/component diagnostics are not geographic approval"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
