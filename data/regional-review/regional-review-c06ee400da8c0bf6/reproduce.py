#!/usr/bin/env python3
"""Reproduce the issue #464 subject/source/parent evidence table.

Reads immutable main-baseline Git blobs and the lawful, hash-pinned source files
retained beside this script. Network access is not used. Geometry overlaps are
screening diagnostics across different vintages, never proof of legal boundary
correctness, completeness, or regional approval.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from evidence.geometry import VERSION as GEOMETRY_HELPER_VERSION, ownership_overlap
from shapely.geometry import shape


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=REPO, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return "".join(ch for ch in value if ch.isalnum())


def features(path: Path):
    data = read_json(path)
    return {feature["properties"]["shapeID"]: feature for feature in data["features"]}


def main():
    scope = read_json(ROOT / "scope.json")
    manifest = read_json(ROOT / "sources-manifest.json")
    official = read_json(ROOT / "official-roster-extract.json")
    official_context = read_json(ROOT / "official-context.json")

    baseline: dict[str, bytes] = {}
    for descriptor in scope["baseline_files"]:
        raw = baseline_blob(scope["baseline_commit"], descriptor["path"])
        if sha256(raw) != descriptor["sha256"]:
            raise SystemExit(f"baseline pin mismatch: {descriptor['path']}")
        baseline[descriptor["path"]] = raw

    source_descriptors = {entry["path"]: entry for entry in scope["source_inputs"]}
    for rel, descriptor in source_descriptors.items():
        raw = (ROOT / rel).read_bytes()
        if sha256(raw) != descriptor["sha256"]:
            raise SystemExit(f"source hash mismatch: {rel}")

    index = json.loads(baseline["data/world-index.json"])
    hierarchy = json.loads(baseline["data/hierarchy.json"])
    hierarchy_by_id = {row["id"]: row for row in hierarchy}
    wanted = {row["id"] for row in scope["subjects"]}
    locations = {}
    for relative in index["parts"]:
        raw = baseline_blob(scope["baseline_commit"], "data/" + relative)
        data = json.loads(raw)
        for feature in data["features"]:
            if feature.get("id") in wanted:
                if feature["id"] in locations:
                    raise SystemExit(f"duplicate baseline subject: {feature['id']}")
                locations[feature["id"]] = feature
    if set(locations) != wanted:
        raise SystemExit(f"subject mismatch; missing={sorted(wanted-set(locations))}")

    gab = features(ROOT / "sources/gabon-adm2-2018.geojson")
    gab_parents = features(ROOT / "sources/gabon-adm1.geojson")
    stp = features(ROOT / "sources/sao-tome-principe-adm1-2017.geojson")
    official_names = {
        unit["province"]: unit["departments"]
        for unit in official["gabon_ministry_2018"]["units"]
    }
    scope_by_id = {row["id"]: row for row in scope["subjects"]}
    outputs = []
    for subject_id in sorted(wanted):
        subject = scope_by_id[subject_id]
        location = locations[subject_id]
        prop = location["properties"]
        if prop["parent_id"] != subject["parent_id"] or prop["name"] != subject["source_name"]:
            raise SystemExit(f"baseline scope differs for {subject_id}")
        parent = hierarchy_by_id.get(prop["parent_id"])
        if not parent:
            raise SystemExit(f"missing baseline parent {prop['parent_id']}")

        if subject_id.startswith("gb:GAB:ADM2:"):
            source_feature = gab.get(subject_id.rsplit(":", 1)[1])
            if not source_feature:
                raise SystemExit(f"missing pinned GAB source feature: {subject_id}")
            source_name = source_feature["properties"]["shapeName"]
            parent_source = next((feature for feature in gab_parents.values()
                                  if normalized_name(feature["properties"]["shapeName"]) == normalized_name(subject["parent_name"])), None)
            if not parent_source:
                raise SystemExit(f"missing GAB ADM1 context parent {subject['parent_name']}")
            overlap = ownership_overlap(shape(source_feature["geometry"]), {
                parent_source["properties"]["shapeID"]: [shape(parent_source["geometry"])]
            })
            names = official_names[subject["parent_name"]]
            name_match = any(normalized_name(source_name) == normalized_name(n) for n in names)
            if name_match:
                classification = "insufficient-evidence"
                finding = "The 2018 source Department name and province roster entry match, but parent geometry is only screening evidence against a 2005 source ADM1; current legal boundary lineage/completeness is not independently established."
            else:
                classification = "insufficient-evidence"
                finding = "The source's 2018 Department name does not match the 2018 Ministry roster under lossless accent/punctuation normalization; no authoritative dated alias or code crosswalk was found."
            row = {
                "id": subject_id,
                "name": source_name,
                "source_level": "ADM2",
                "source_role": "Department (geoBoundaries metadata)",
                "source_vintage": "2018",
                "source_license": "CC BY 3.0",
                "parent_id": prop["parent_id"],
                "parent_name": subject["parent_name"],
                "official_roster_name_match": name_match,
                "official_roster_match_basis": "2018 Gabon Interior Ministry province-to-department listing; normalized name comparison only",
                "comparison_parent_source": "geoBoundaries GAB ADM1 2005, CC BY-SA 3.0",
                "child_land_share_inside_old_parent": round(overlap["shares"][parent_source["properties"]["shapeID"]], 9),
                "geometry_method": overlap["method"],
                "classification": classification,
                "finding": finding,
                "limits": ["ADM2/ADM1 vintages differ by 13 years", "area overlap does not prove legal parentage or boundaries", "official HTML has no byte-exact retained hash", "the nationwide 49-versus-48 source count is not resolved by this scoped review"]
            }
        else:
            source_feature = stp.get(subject_id.rsplit(":", 1)[1])
            if not source_feature:
                raise SystemExit(f"missing pinned STP source feature: {subject_id}")
            source_name = source_feature["properties"]["shapeName"]
            row = {
                "id": subject_id,
                "name": source_name,
                "source_level": "ADM1",
                "source_role": "blank canonical role; metadata calls feature a named island-level local administrative territory",
                "source_vintage": "2017",
                "source_license": "ODbL 1.0",
                "parent_id": prop["parent_id"],
                "parent_name": subject["parent_name"],
                "official_role_context": "INE 2012 describes six districts on São Tomé and one autonomous region (Príncipe); Príncipe autonomous status dates from 1996. INE 2017 treats R.A.P. separately from the six São Tomé districts.",
                "official_roster_name_match": None,
                "classification": "correction-needed",
                "finding": "The source's 'Province' display label and the atlas one-child province parent do not represent the official current administrative roles: São Tomé is an island containing six districts, while Príncipe is an autonomous region. A geographic island grouping may still be useful, but its role/tier and same-footprint parent purpose need a sourced engineering decision.",
                "limits": ["official primary district-level boundary geometry was not obtained", "two source features do not prove all small-island coverage", "official INE PDF reuse license not identified; exact source hashes and restoration URLs are retained, not the PDFs", "ODbL 1.0 downstream database obligations need review"]
            }

        outputs.append(row)

    statuses = {status: sum(row["classification"] == status for row in outputs)
                for status in ("justified", "correction-needed", "insufficient-evidence")}
    parent_groups = {}
    for subject in scope["subjects"]:
        group = parent_groups.setdefault(subject["parent_id"], {
            "id": subject["parent_id"], "name": subject["parent_name"], "subjects": []})
        group["subjects"].append(subject["id"])
    parent_assessments = []
    for group in sorted(parent_groups.values(), key=lambda row: row["id"]):
        is_stp = group["id"].startswith("framework:province:") and any(i.startswith("gb:STP:") for i in group["subjects"])
        parent_assessments.append({
            **group,
            "classification": "correction-needed" if is_stp else "insufficient-evidence",
            "finding": ("The one-child province grouping duplicates the named island-level source feature, while INE describes six districts on São Tomé and an autonomous region containing one district on Príncipe. The island grouping may have geographic value, but province-tier purpose and same-footprint duplication need an engineering decision." if is_stp else "The retained Gabon province grouping has source roster support for this scoped department subset, but its comparison ADM1 geometry is from 2005, thirteen years older than the 2018 children. The national 49-versus-48 count discrepancy and official same-vintage boundaries remain unresolved."),
            "limits": (["official current-role context does not establish the grouping's geographic purpose", "no authoritative district/island boundary geometry was obtained", "single-child same-footprint grouping purpose remains unresolved"] if is_stp else ["subset roster support does not establish full province completeness", "ADM1 reference geometry is 2005 versus ADM2 2018", "official same-vintage boundary crosswalk unavailable", "national source count is 49 versus a separate 2016 official count of 48"])
        })
    area_assessments = [
        {"id":"framework:area:gabon:f2df9b08a122","name":"Gabon","full_area_location_count":49,"scoped_subject_count":19,"classification":"insufficient-evidence","purpose":"Country-level grouping of Gabon locations; this packet covers only 19 department IDs in Haut-Ogooué, Ogooué-Ivindo and Ogooué-Lolo. Other Gabon subjects belong to sibling Central Africa review scopes (#460–#463).","finding":"This partial packet does not establish nationwide source completeness; 49 geoBoundaries ADM2 features differ from a separate official 2016 aggregate count of 48 departments."},
        {"id":"framework:area:gulf-of-guinea-is:38986b297bde","name":"Gulf of Guinea Islands","full_area_location_count":7,"scoped_subject_count":2,"classification":"insufficient-evidence","purpose":"Regional island grouping; this packet assesses the São Tomé and Príncipe ADM1-derived island features only. The other five area members remain in sibling Central Africa review scopes (#460–#463).","finding":"The regional grouping purpose and full seven-member island coverage are outside this packet's two exact source subjects; no regional or named-island completeness conclusion is made."}
    ]
    result = {
        "version": 1,
        "issue": 464,
        "baseline_commit": scope["baseline_commit"],
        "baseline_pins": {row["path"]: row["sha256"] for row in scope["baseline_files"]},
        "subject_count": len(outputs),
        "subject_ids_sha256": hashlib.sha256(("\n".join(sorted(wanted)) + "\n").encode()).hexdigest(),
        "source_files": {path: descriptor["sha256"] for path, descriptor in sorted(source_descriptors.items())},
        "source_release_commit": manifest["geoBoundaries"]["commit"],
        "geometry_helper_version": GEOMETRY_HELPER_VERSION,
        "geometry_method_limit": "WGS84 land overlap from helper v1; only a cross-vintage screen, not a boundary or completeness conclusion",
        "classifications": statuses,
        "findings": outputs,
        "parent_assessments": parent_assessments,
        "area_assessments": area_assessments,
        "unresolved_handoffs": [
            {"area":"Gabon","issue":866,"url":"https://github.com/ChengshuLi/WorldAtlas/issues/866","subjects":[row["id"] for row in outputs if row["id"].startswith("gb:GAB")],"question":"2018 department-to-province crosswalk against same-vintage official boundaries; resolve Mouloundou/Mulundu and source 49 versus official 48 counts."},
            {"area":"São Tomé and Príncipe","issue":865,"url":"https://github.com/ChengshuLi/WorldAtlas/issues/865","subjects":[row["id"] for row in outputs if row["id"].startswith("gb:STP")],"question":"Find authoritative current island/district boundary geometry and decide whether island-level geographic groupings belong at province tier; verify associated small-island coverage."}
        ],
        "official_source_limits": ["Gabon government pages were inspected through rendered text, not retrieved as original bytes; no original hash is claimed.", "INE PDFs were downloaded for inspection; no PDF bytes are redistributed because license terms were not identified. Their restoration URLs, byte lengths, and exact SHA-256 values are in official-context.json."]
    }

    out = ROOT / "reproduction"
    out.mkdir(exist_ok=True)
    (out / "findings.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    columns = ["id", "name", "source_level", "source_role", "source_vintage", "source_license", "parent_id", "parent_name", "official_roster_name_match", "child_land_share_inside_old_parent", "classification", "finding"]
    with (out / "subject-assessments.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in outputs:
            writer.writerow(row)
    with (out / "province-assessments.csv").open("w", newline="", encoding="utf-8") as stream:
        columns = ["id", "name", "classification", "subjects", "finding", "limits"]
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in parent_assessments:
            writer.writerow({**row, "subjects": ";".join(row["subjects"]), "limits": "; ".join(row["limits"])})
    print(json.dumps({"subjects":len(outputs),"classifications":statuses,"findings_sha256":sha256((out/"findings.json").read_bytes()),"csv_sha256":sha256((out/"subject-assessments.csv").read_bytes())},sort_keys=True))


if __name__ == "__main__":
    main()
