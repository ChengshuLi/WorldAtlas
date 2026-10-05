#!/usr/bin/env python3
"""Rebuild the bounded Romania 42-ID/name/parent crosswalk from pinned inputs."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

PACKET = "data/regional-review/followup-romania-422-county-roles-20261005"
PRIOR = "data/regional-review/regional-review-3c4fe25a21fa428d"
METHOD = "romania-42-unit-source-and-parent-crosswalk"


def raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def name_key(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).casefold()
    return "".join(ch for ch in folded if ch.isalnum() and not unicodedata.combining(ch))


def vertices(value) -> int:
    if not isinstance(value, list):
        return 0
    if len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
        return 1
    return sum(vertices(item) for item in value)


def fail(message: str):
    raise ValueError(message)


def load_inputs(root: Path):
    def read(relative):
        return json.loads((root / relative).read_text())

    contract = read(f"{PACKET}/github-issue-contract.json")
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", contract["body"], re.S)
    if not match:
        fail("Issue machine contract is missing")
    work = json.loads(match.group(1))
    quality = work["evidence_quality"]
    expected = quality["subject_ids"]
    if work["mode"] != "geography" or work["max_prs"] != 1:
        fail("Unexpected issue mode or PR budget")
    if work["owned_paths"] != [f"{PACKET}/"]:
        fail("Issue owned path changed")
    if len(expected) != 42 or len(set(expected)) != 42:
        fail("Issue contract does not contain 42 unique subjects")
    for relative, expected_sha in quality["pins"].items():
        if raw_sha(root / relative) != expected_sha:
            fail(f"Issue pin mismatch: {relative}")

    source_manifest = read(f"{PRIOR}/source/source-manifest.json")
    source_meta = read(f"{PRIOR}/source/gb/ROU-ADM1-geoBoundaries-ROU-ADM1-metaData.json")
    source_geo_path = root / f"{PRIOR}/source/gb/gb-ROU-ADM1.geojson"
    source_geo = read(f"{PRIOR}/source/gb/gb-ROU-ADM1.geojson")
    prior_scope = read(f"{PRIOR}/source/scope-subjects.json")
    assessments = read(f"{PRIOR}/source/subject-assessments.json")["subjects"]
    atlas_part = read("data/geography/part-20.json")
    hierarchy = read("data/hierarchy.json")
    neighbors = read(f"{PACKET}/neighbor-source-context.json")
    official_roster = read(f"{PACKET}/official-county-roster.json")

    source_row = next(row for row in source_manifest["sources"] if row["source_id"] == "gb:ROU:ADM1")
    if raw_sha(source_geo_path) != source_row["sha256"]:
        fail("Retained geoBoundaries ROU file hash differs from the #422 source manifest")
    if source_row["features"] != 42 or source_row["scope_members"] != 42:
        fail("Pinned #422 source manifest does not describe the exact 42-feature/42-member ROU layer")
    if source_meta["boundaryYear"] != "2017" or source_meta["admUnitCount"] != "42":
        fail("Pinned ROU metadata vintage/count changed")

    return {
        "work": work, "quality": quality, "expected": expected,
        "source_manifest": source_manifest, "source_row": source_row,
        "source_meta": source_meta, "source_geo": source_geo,
        "source_geo_sha256": raw_sha(source_geo_path),
        "prior_scope": prior_scope, "assessments": assessments,
        "atlas_part": atlas_part, "hierarchy": hierarchy,
        "neighbors": neighbors, "official_roster": official_roster,
    }


def build_crosswalk(inputs, expected_ids=None):
    expected = inputs["expected"] if expected_ids is None else expected_ids
    if len(expected) != 42 or len(set(expected)) != 42:
        fail("Expected scope must contain the 42 unique issue subjects")
    source_features = inputs["source_geo"]["features"]
    source_by_id = {}
    for feature in source_features:
        props = feature["properties"]
        shape_id = props.get("shapeID")
        if not shape_id or shape_id in source_by_id:
            fail("Source shapeIDs must be nonempty and unique")
        source_by_id[shape_id] = feature
    part_features = [f for f in inputs["atlas_part"]["features"] if f["properties"]["id"].startswith("gb:ROU:ADM1:")]
    atlas_by_id = {}
    for feature in part_features:
        props = feature["properties"]
        original_id = props["metadata"].get("original_id")
        if not original_id or original_id in atlas_by_id:
            fail("Atlas original IDs must be nonempty and unique")
        atlas_by_id[original_id] = feature
    if len(source_by_id) != 42 or len(atlas_by_id) != 42:
        fail("Expected exactly 42 source and Atlas ROU features")

    atlas_by_atlas_id = {f["properties"]["id"]: f for f in part_features}
    if set(expected) != {f["properties"]["id"] for f in part_features}:
        fail("Atlas ROU part membership does not match the exact issue subject set")
    source_ids = {"gb:ROU:ADM1:" + key for key in source_by_id}
    if source_ids != set(expected):
        fail("Pinned source shape IDs do not map one-to-one to the issue's Atlas IDs")
    assessment_rows = [row for row in inputs["assessments"] if row.get("source_id") == "gb:ROU:ADM1"]
    if {row["location_id"] for row in assessment_rows} != set(expected) or len(assessment_rows) != 42:
        fail("Prior #422 subject assessments do not cover the exact 42 ROU IDs")
    if any(row["source_sha256"] != inputs["source_geo_sha256"] for row in assessment_rows):
        fail("Prior source assessments do not bind to the retained ROU GeoJSON hash")

    hierarchy = {node["id"]: node for node in inputs["hierarchy"]}
    roster = inputs["official_roster"]
    official_names = roster["county_names_from_law_annex"]
    if len(official_names) != 41 or len({name_key(name) for name in official_names}) != 41:
        fail("Official county roster must contain 41 unique names")
    official_keys = {name_key(name) for name in official_names}
    rows = []
    for atlas_id in sorted(expected):
        atlas = atlas_by_atlas_id[atlas_id]
        props = atlas["properties"]
        original_id = props["metadata"]["original_id"]
        source = source_by_id[original_id]
        source_props = source["properties"]
        source_name = source_props["shapeName"]
        atlas_name = props["name"]
        key = name_key(source_name)
        is_bucharest = key == name_key(roster["bucharest_municipality"])
        county_match = key in official_keys
        if is_bucharest == county_match:
            fail(f"Source unit does not map to exactly one official role: {atlas_id}")
        if name_key(atlas_name) != key:
            fail(f"Atlas and source names do not match: {atlas_id}")
        parent_id = props["parent_id"]
        parent = hierarchy.get(parent_id)
        if not parent:
            fail(f"Missing parent node: {parent_id}")
        if parent["level"] != "province" or parent["name"] != atlas_name or parent["metadata"].get("child_count") != 1:
            fail(f"Expected a same-name singleton province parent: {parent_id}")
        source_geometry = source["geometry"]
        atlas_geometry = atlas["geometry"]
        rows.append({
            "atlas_id": atlas_id,
            "shape_id": source_props["shapeID"],
            "shape_iso": source_props.get("shapeISO"),
            "source_name": source_name,
            "atlas_name": atlas_name,
            "official_role": "Bucharest Municipality" if is_bucharest else "county",
            "official_name_match": roster["bucharest_municipality"] if is_bucharest else next(name for name in official_names if name_key(name) == key),
            "source_geometry_sha256": hashlib.sha256(canonical_json(source_geometry)).hexdigest(),
            "atlas_geometry_sha256": hashlib.sha256(canonical_json(atlas_geometry)).hexdigest(),
            "source_geometry_vertices": vertices(source_geometry.get("coordinates")),
            "atlas_geometry_vertices": vertices(atlas_geometry.get("coordinates")),
            "geometry_json_exact_match": source_geometry == atlas_geometry,
            "parent_id": parent_id,
            "parent_name": parent["name"],
            "parent_level": parent["level"],
            "parent_child_count": parent["metadata"]["child_count"],
            "parent_basis": parent["metadata"].get("basis"),
        })
    roles = [row["official_role"] for row in rows]
    if roles.count("county") != 41 or roles.count("Bucharest Municipality") != 1:
        fail("Official-role crosswalk must resolve to 41 counties plus Bucharest Municipality")
    if len({row["parent_id"] for row in rows}) != 42:
        fail("Each scoped location must have its separately listed parent")
    exact_source_geometry = sum(row["geometry_json_exact_match"] for row in rows)
    output = {
        "version": 1,
        "issue": 997,
        "baseline_commit": "0de4b1f4183d6cf7c5fc6c78b6316f0f3a6b1e15",
        "source_id": "gb:ROU:ADM1",
        "source_sha256": inputs["source_geo_sha256"],
        "source_vintage": inputs["source_meta"]["boundaryYear"],
        "source_metadata_adm_unit_count": int(inputs["source_meta"]["admUnitCount"]),
        "atlas_subject_count": len(rows),
        "county_member_count": roles.count("county"),
        "bucharest_municipality_count": roles.count("Bucharest Municipality"),
        "same_name_singleton_province_parent_count": len({row["parent_id"] for row in rows}),
        "parent_children_all_singleton": all(row["parent_child_count"] == 1 for row in rows),
        "exact_source_atlas_geometry_matches": exact_source_geometry,
        "official_polygon_comparison_performed": False,
        "official_polygon_comparison_limit": "The current ANCPI 2024 county-layer archive was listed with CC BY 4.0 but download timed out; no binary was retained or compared.",
        "rows": rows,
        "neighbor_source_context": inputs["neighbors"],
    }
    return output


def write_outputs(root: Path):
    inputs = load_inputs(root)
    output = build_crosswalk(inputs)
    crosswalk_bytes = json.dumps(output, ensure_ascii=False, indent=2).encode() + b"\n"
    first_hash = hashlib.sha256(crosswalk_bytes).hexdigest()
    second_bytes = json.dumps(build_crosswalk(load_inputs(root)), ensure_ascii=False, indent=2).encode() + b"\n"
    second_hash = hashlib.sha256(second_bytes).hexdigest()
    if crosswalk_bytes != second_bytes:
        fail("Two independent crosswalk rebuilds were not byte-identical")

    validation = root / PACKET / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    (root / PACKET / "source-crosswalk.json").write_bytes(crosswalk_bytes)
    (validation / "positive-control.json").write_text(json.dumps({
        "method_id": METHOD, "kind": "positive-control", "outcome": "passed",
        "source_feature_count": len(inputs["source_geo"]["features"]),
        "issue_subject_count": len(inputs["expected"]),
        "official_role_counts": {"county": output["county_member_count"], "Bucharest Municipality": output["bucharest_municipality_count"]},
        "singleton_parent_count": output["same_name_singleton_province_parent_count"],
        "assertion": "All 42 source shape IDs map uniquely to the exact 42 issue IDs; 41 match the official county roster and one matches the legally distinct Bucharest Municipality; all listed parent nodes are same-name province singletons. This does not validate polygon accuracy."
    }, ensure_ascii=False, indent=2) + "\n")

    try:
        build_crosswalk(inputs, expected_ids=inputs["expected"][:-1])
    except ValueError as exc:
        if "Expected scope must contain the 42 unique issue subjects" not in str(exc):
            raise
        negative = {"method_id": METHOD, "kind": "negative-control", "outcome": "passed",
                    "mutation": "Removed one subject from the issue scope before crosswalk generation.",
                    "observed": "The scope precondition rejected the incomplete subject set before producing any output."}
    else:
        fail("Negative control did not reject the deliberately incomplete issue scope")
    (validation / "negative-control.json").write_text(json.dumps(negative, ensure_ascii=False, indent=2) + "\n")
    (validation / "reproducibility.json").write_text(json.dumps({
        "method_id": METHOD, "kind": "reproducibility", "outcome": "passed",
        "run_one_sha256": first_hash, "run_two_sha256": second_hash,
        "byte_identical": first_hash == second_hash,
        "generator": "reproduce.py build_crosswalk/load_inputs"
    }, ensure_ascii=False, indent=2) + "\n")
    return first_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    digest = write_outputs(args.root.resolve())
    print(json.dumps({"output": f"{PACKET}/source-crosswalk.json", "sha256": digest, "rows": 42}))

if __name__ == "__main__":
    main()
