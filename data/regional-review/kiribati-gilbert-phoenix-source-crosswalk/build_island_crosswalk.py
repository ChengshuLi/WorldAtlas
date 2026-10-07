#!/usr/bin/env python3
"""Build an explicit name-level crosswalk; never infers island polygon identity."""
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY_PATH = "data/regional-review/kiribati-gilbert-phoenix-source-crosswalk/source-component-inventory.json"
FOLLOWUP_PATH = "data/regional-review/kiribati-gilbert-phoenix-source-crosswalk/followup-2026-10-07-evidence.json"
OUTPUT = ROOT / "physical-island-crosswalk.json"
REPOSITORY = ROOT.parents[2]
CURRENT_BASELINE_COMMIT = "8b6835dfa645cf763137374c3730401d5ac2f732"
PART13_PATH = Path("data/geography/part-13.json")
PHOENIX_CURRENT_PATH = Path("data/geography/source-restoration-additions.json")


def norm(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def tokens(value):
    return [part.strip() for part in re.split(r"[/,]", value) if part.strip()]


def main():
    inventory = json.loads((ROOT / "source-component-inventory.json").read_text())
    followup = json.loads((ROOT / "followup-2026-10-07-evidence.json").read_text())
    group_names = followup["physical_group_roster"]
    aliases = followup["archive_name_lookup"]["physical_name_aliases"]
    name_hits = followup["archive_name_lookup"]["hits"]
    hits_by_norm = {norm(name): rows for name, rows in name_hits.items()}
    components = {feature["name"]: feature for feature in inventory["source_feature_component_inventory"]}
    source_ids = {feature["name"]: feature["source_feature_id"] for feature in inventory["source_feature_component_inventory"]}
    archive_subjects = {row["current_source_id"]: row for row in inventory["archived_id_crosswalk"]["subjects"]}
    member_rows = inventory["phoenix_526_members"]
    census_rows = inventory["gilbert_census_rows"]["rows"]
    for input_path in (PART13_PATH, PHOENIX_CURRENT_PATH):
        pinned = subprocess.check_output(["git", "show", f"{CURRENT_BASELINE_COMMIT}:{input_path.as_posix()}"], cwd=REPOSITORY)
        if hashlib.sha256(pinned).hexdigest() != hashlib.sha256(input_path.read_bytes()).hexdigest():
            raise ValueError(f"Current geography input differs from pinned baseline: {input_path}")
    current_rows = json.loads(PART13_PATH.read_text())["features"]
    current_rows.extend(json.loads(PHOENIX_CURRENT_PATH.read_text())["features"])
    current_by_id = {row.get("id", row.get("properties", {}).get("id")): row for row in current_rows}
    physical_rows = []
    for group, names in group_names.items():
        feature = components[group]
        feature_id = source_ids[group]
        for official_name in names:
            name_aliases = tokens(official_name)
            census_matches = []
            if group == "Gilbert Islands":
                for row in census_rows:
                    row_name = row["census_row"]
                    physical = "Tarawa" if "Tarawa" in row_name else "Tabiteuea" if "Tabiteuea" in row_name else row_name
                    if norm(physical) == norm(official_name):
                        census_matches.append({"row": row_name, "division": row["division"], "qualification": row["qualification"], "candidate_current_subject_ids": row["candidate_current_subject_ids"]})
            phoenix_member = None
            if group == "Phoenix Islands":
                wanted = {norm(alias) for alias in name_aliases}
                for member in member_rows:
                    if wanted.intersection(norm(token) for token in tokens(member["name"])):
                        phoenix_member = {"id": member["id"], "name": member["name"], "source_bbox": member["source_bbox"], "source_license": member["source_license"], "retained_archive": member["retained_archive"], "retained_archive_sha256": member["retained_archive_sha256"]}
                        break
            if group == "Gilbert Islands":
                current_ids = sorted({identifier for row in census_matches for identifier in row["candidate_current_subject_ids"]})
            elif phoenix_member:
                current_ids = [phoenix_member["id"]]
            elif group == "Line Islands":
                current_ids = ["gb:KIR:ADM1:97431129B35506555718846"]
            else:
                current_ids = []
            current_records = []
            for identifier in current_ids:
                if identifier not in current_by_id:
                    raise ValueError(f"Expected retained location ID not found in pinned current files: {identifier}")
                current_feature = current_by_id[identifier]
                props = current_feature.get("properties", {})
                retained_name = props.get("name", current_feature.get("name"))
                if group == "Phoenix Islands" and not {norm(alias) for alias in name_aliases}.intersection(norm(alias) for alias in tokens(retained_name or "")):
                    raise ValueError(f"Phoenix physical name does not match retained source name: {official_name} / {retained_name}")
                storage = str(PHOENIX_CURRENT_PATH) if identifier.startswith("atlas:macro-coverage:location:") else str(PART13_PATH)
                current_records.append({"id": identifier, "name": retained_name, "parent_id": props.get("parent_id", current_feature.get("parent_id")), "storage_path": storage, "name_match": "normalized alias intersection" if group == "Phoenix Islands" else "group-level current feature candidate"})
            matched_hits = []
            for alias in name_aliases:
                matched_hits.extend(hits_by_norm.get(norm(alias), []))
            unique_hits = {(row["collection"], row["id"]): row for row in matched_hits}
            candidate_source_parts = []
            for part in feature["parts"]:
                candidates = part.get("phoenix_526_osm_bbox_candidates", []) if group == "Phoenix Islands" else part.get("retained_bbox_candidates", [])
                if group == "Phoenix Islands" and phoenix_member and any(item == phoenix_member["id"] for item in candidates):
                    candidate_source_parts.append(part["source_part"])
                elif group != "Phoenix Islands" and any(item.get("id") in current_ids for item in candidates if isinstance(item, dict)):
                    candidate_source_parts.append(part["source_part"])
            physical_rows.append({
                "group": group,
                "official_name": official_name,
                "name_aliases": name_aliases,
                "census_reporting_rows": census_matches,
                "current_retained_location_candidates": current_records,
                "current_location_source_paths": sorted({record["storage_path"] for record in current_records}),
                "phoenix_526_member": phoenix_member,
                "archived_exact_name_matches": list(unique_hits.values()),
                "source_feature": {"name": group, "shape_id": feature["source_shape_id"], "feature_id": feature["source_feature_id"]},
                "group_level_bbox_candidate_source_parts_for_current_location": candidate_source_parts,
                "crosswalk_status": "Name/group-level candidate only. The source feature is multipart and does not identify which component is this island; no polygon, legal jurisdiction, or ownership assignment is asserted.",
            })
    source_component_status = []
    for source_feature in inventory["source_feature_component_inventory"]:
        for part in source_feature["parts"]:
            current_candidates = part.get("retained_bbox_candidates", [])
            phoenix_osm_candidates = part.get("phoenix_526_osm_bbox_candidates", [])
            phoenix_land_candidates = part.get("phoenix_526_land_component_bbox_candidates", [])
            source_component_status.append({
                "feature_name": source_feature["name"],
                "source_shape_id": source_feature["source_shape_id"],
                "source_feature_id": source_feature["source_feature_id"],
                "source_part": part["source_part"],
                "retained_current_bbox_candidates": current_candidates,
                "phoenix_526_osm_bbox_candidates": phoenix_osm_candidates,
                "phoenix_526_land_component_bbox_candidates": phoenix_land_candidates,
                "exact_physical_island_assignment": None,
                "status": "unassigned to a named physical island; bbox candidates are screening evidence only",
            })
    unmatched = [row for row in source_component_status if not (row["retained_current_bbox_candidates"] or row["phoenix_526_osm_bbox_candidates"] or row["phoenix_526_land_component_bbox_candidates"])]
    result = {
        "issue": 611,
        "as_of": "2026-10-07",
        "method": "Name-level crosswalk built from the cited official physical roster, retained census-row candidate IDs, #526 Phoenix source-member inventory, pinned archive exact-name lookup, and geoBoundaries component inventory. Bbox candidates are not polygon matches.",
        "inventory_path": INVENTORY_PATH,
        "followup_path": FOLLOWUP_PATH,
        "current_geography_baseline_commit": CURRENT_BASELINE_COMMIT,
        "input_hashes": {path: hashlib.sha256((ROOT / path.split("/")[-1]).read_bytes()).hexdigest() for path in ("source-component-inventory.json", "followup-2026-10-07-evidence.json")},
        "current_input_hashes": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (PART13_PATH, PHOENIX_CURRENT_PATH)},
        "physical_island_group_count": len(physical_rows),
        "groups": {group: sum(row["group"] == group for row in physical_rows) for group in group_names},
        "rows": physical_rows,
        "archive_group_identity_rows": {group: archive_subjects.get(source_ids[group], {}).get("archive_records", []) for group in group_names},
        "source_feature_component_groups": {feature["name"]: {"shape_id": feature["source_shape_id"], "feature_id": feature["source_feature_id"], "component_count": feature["component_count"], "part_numbers": [part["source_part"] for part in feature["parts"]]} for feature in inventory["source_feature_component_inventory"]},
        "source_component_status": source_component_status,
        "bbox_screen_unmatched_source_components": unmatched,
        "completeness_and_unmatched": {
            "all_named_physical_groups_listed": True,
            "gilbert_census_row_count": len(census_rows),
            "gilbert_group_targets": len({row["official_name"] for row in physical_rows if row["group"] == "Gilbert Islands"}),
            "source_component_counts": {feature["name"]: feature["component_count"] for feature in inventory["source_feature_component_inventory"]},
            "source_component_exact_island_assignments": 0,
            "source_component_exact_island_assignment_limit": "The retained source provides three group-labelled multipart features, not part-to-island names. All part-level bbox candidates are preserved in source-component-inventory.json; they do not resolve exact identity.",
            "current_representation_limit": "Current Gilbert and Line subjects are group-level polygons. The two retained remainder parts lie near Banaba/Tarawa; they are candidates, not validated island polygons. All eight Phoenix names and IDs are checked against current retained source-restoration additions and #526 OSM member records; that does not prove equality with geoBoundaries parts.",
            "unmatched_physical_groups": "No exact individual historical archive name row or source-component-to-island geometry match was established. For Gilbert and Line, no island-level current location ID was identified; group-level candidates remain. Phoenix names are matched to all eight #526 members.",
            "bbox_screen_unmatched_source_component_count": len(unmatched),
            "bbox_screen_unmatched_source_components_are_listed": True,
            "all_components_lack_exact_physical_island_assignment": all(row["exact_physical_island_assignment"] is None for row in source_component_status),
        },
        "limits": ["This crosswalk is not a map or boundary verdict.", "Archived exact-name misses can reflect aliases, missing history or non-name IDs; they do not prove absence.", "#526 OSM records are source families and bbox candidates, not legal boundaries.", "Group-level source components cannot be truthfully assigned one-to-one to 33 named islands without better source evidence."],
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "groups": result["groups"], "rows": len(physical_rows), "source_component_exact_island_assignments": 0}, indent=2))


if __name__ == "__main__":
    main()
