#!/usr/bin/env python3
"""Rebuild the #421 exact roster crosswalk from pinned inputs."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.immutable import Baseline

BASELINE_PIN = json.loads((HERE / "baseline-inputs.json").read_text())
BASE = Baseline(ROOT, BASELINE_PIN["commit"], BASELINE_PIN["files"])
SCOPE = json.loads((HERE / "scope.json").read_text())
ISSUE = json.loads((HERE / "issue-421-api.json").read_text())
assert ISSUE["number"] == 421

wanted = SCOPE["member_location_ids"]
assert len(wanted) == 230 and len(set(wanted)) == 230
features = []
for name in ("part-9.json", "part-28.json", "part-29.json"):
    item = json.loads(BASE.read("data/geography/" + name))
    features.extend(item["features"])
locations = {f["properties"]["id"]: f["properties"] for f in features}
assert set(wanted) <= locations.keys()

parents = {x["id"]: x for x in json.loads(BASE.read("data/hierarchy.json"))}
inventory_raw = gzip.decompress(BASE.read("data/macro-foundation/current-membership-inventory.json.gz"))
inventory = {x["id"]: x for x in json.loads(inventory_raw)}
grc_raw = BASE.read("data/regional-review/regional-review-ef67318527f5f3a3/sources/geoBoundaries-GRC-ADM3.geojson.gz")
grc = json.loads(gzip.decompress(grc_raw))
grc_features = {f["properties"]["shapeID"]: f["properties"] for f in grc["features"]}
xkx_path = HERE / "sources/geoBoundaries-XKX-ADM1.geojson"
xkx = json.loads(xkx_path.read_text())
xkx_features = {f["properties"]["shapeID"]: f["properties"] for f in xkx["features"]}
grc_parent = json.loads((HERE / "sources/geoBoundaries-GRC-ADM2.geojson").read_text())
grc_parent_features = {f["properties"]["shapeID"]: f["properties"] for f in grc_parent["features"]}
grc_parent_meta = json.loads((HERE / "sources/geoBoundaries-GRC-ADM2-metaData.json").read_text())
xkx_meta = json.loads((HERE / "sources/geoBoundaries-XKX-ADM1-metaData.json").read_text())

area_names = {"framework:area:greece:e5489fc04cd7": "Greece",
              "framework:area:kriti:88da4b529aa4": "Kriti",
              "framework:area:yugoslavia:cff5e9ba6c8e": "Yugoslavia"}
area_members = {area_id: set(inventory[area_id]["member_location_ids"]) for area_id in area_names}
area_for_location = {}
for area_id, ids in area_members.items():
    for member_id in ids:
        assert member_id not in area_for_location
        area_for_location[member_id] = area_id
assert sum(len(ids) for ids in area_members.values()) == 1475
assert sum(len(set(wanted) & ids) for ids in area_members.values()) == 230
assert Counter(area_names[a] for loc_id in wanted for a, ids in area_members.items() if loc_id in ids) == {
    "Greece": 201, "Kriti": 25, "Yugoslavia": 4}
rows = []
province_counts = Counter()
for loc_id in sorted(wanted):
    p = locations[loc_id]
    m = p["metadata"]
    parent = parents.get(p["parent_id"], {})
    source_id = m["source_id"]
    original_ids = m.get("source_member_ids") or [loc_id]
    if source_id == "gb:GRC:ADM3":
        feature_ids = [sid.rsplit(":", 1)[-1] for sid in original_ids]
        matches = [grc_features.get(fid) for fid in feature_ids]
        match_state = "all source features matched" if all(matches) else "source feature missing"
        names = "; ".join(x["shapeName"] for x in matches if x)
        vintage = "2010"
        role = "Municipality"
        license_ = "CC0 1.0 metadata; licenseDetail also attributes source 2 and 3 CC BY 3.0"
        outcome = "insufficient-evidence"
        finding = ("Pinned source identity/name matches; current legal boundary, 2021+ continuity, island completeness, "+
                   "and current source completeness are not established. Official current structure reports 332 "+
                   "municipalities vs pinned 2010 release's 326 features; the difference is not localized here.")
        if loc_id == "gb:GRC:ADM3:53547021B80449020436996":
            outcome = "correction-needed"
            finding = ("The pinned source labels this feature a Municipality, but Greek Constitution article 105 "+
                       "describes the region of Aghion Oros as a self-governed part of the Greek State. The Atlas "+
                       "location 'Mount Anthos' is nested under a single-child 'Agion Oros' parent. Preserve the ID; "+
                       "engineering/geography should adjudicate the role and repeated tier against the statutory "+
                       "territorial definition before any label, parent or footprint change.")
    elif source_id == "gb:XKX:ADM1":
        feature_ids = [sid.rsplit(":", 1)[-1] for sid in original_ids]
        matches = [xkx_features.get(fid) for fid in feature_ids]
        match_state = "all source features matched" if all(matches) else "source feature missing"
        names = "; ".join(x["shapeName"] for x in matches if x)
        vintage = "2021 metadata (asset built 2023-12-12)"
        role = "Metadata says Municipalities; delivered asset features are Districts"
        license_ = "CC BY-SA 2.0 (geoBoundaries metadata; OpenStreetMap attribution)"
        outcome = "correction-needed"
        finding = ("Pinned source asset has 7 feature names District of …; metadata claims 48 municipalities. "+
                   "This record and its same-name Atlas parent are a district-level unit, not the declared municipal "+
                   "source role; full 38-municipality coverage is unresolved. Do not transfer IDs or infer status.")
    else:
        raise AssertionError((loc_id, source_id))
    # The workload areas are the pinned parent chain, not an inference from country/name.
    area_names_for_row = area_names[area_for_location[loc_id]]
    province_counts[(p["parent_id"], parent.get("name", "<missing>"), p["reference_owner"])] += 1
    rows.append({
        "location_id": loc_id, "location_name": p["name"], "owner": p["reference_owner"],
        "atlas_parent_id": p["parent_id"], "atlas_parent_name": parent.get("name", "<missing>"),
        "workload_area": area_names_for_row, "source_id": source_id,
        "source_shape_ids": ";".join(feature_ids), "source_feature_names": names,
        "source_role_or_conflict": role, "source_vintage": vintage, "source_license": license_,
        "source_feature_match": match_state, "outcome": outcome, "finding": finding,
        "citation_keys": ("S7" if loc_id == "gb:GRC:ADM3:53547021B80449020436996" else
                          "S1;S2;S3" if source_id == "gb:GRC:ADM3" else "S4;S5;S6"),
    })

fields = list(rows[0])
with (HERE / "assessment.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)

province_rows = []
for (pid, name, owner), n in sorted(province_counts.items(), key=lambda x: (x[0][2], x[0][1])):
    h = parents[pid]
    hmeta = h.get("metadata", {})
    evidence_text = "; ".join(x.get("inspected_fact", "") for x in hmeta.get("semantic_review", {}).get("evidence", []))
    shape_match = re.search(r"shapeID ([A-Z0-9]+)", evidence_text)
    parent_shape_id = shape_match.group(1) if shape_match else ""
    if hmeta.get("source") == "gb:GRC:ADM2":
        p_source = grc_parent_features.get(parent_shape_id)
        p_meta = grc_parent_meta
        if p_source:
            p_feature_match = "matched by stored parent shapeID"
        elif name == "East Macedonia and Thrace":
            p_source = next((v for v in grc_parent_features.values() if v.get("shapeName") == "Anatolikis Makedonias kai Thr*"), None)
            p_feature_match = "candidate name only; stored parent shapeID absent" if p_source else "missing"
        else:
            p_feature_match = "missing"
    elif hmeta.get("source") == "gb:XKX:ADM1":
        p_source = xkx_features.get(parent_shape_id)
        p_meta = xkx_meta
        p_feature_match = "matched by stored parent shapeID" if p_source else "missing"
    else:
        p_source = None
        p_meta = {}
        p_feature_match = "no source parent shapeID; fallback evidence only"
    full_children = len(inventory[pid]["member_location_ids"])
    area = parents.get(h.get("parent_id"), {})
    weak_fallback = name in {"Poros", "Ydra", "Elafonisos"}
    parent_outcome = "correction-needed" if owner == "Kosovo" or name == "Agion Oros" or weak_fallback else "insufficient-evidence"
    parent_finding = ("Single-child parent duplicates its only child as a District of the same name; the source asset "+
                      "contradicts its own municipal role/count metadata. Resolve district-to-municipality granularity "+
                      "and source lineage; no ID or parent mutation is authorized.") if owner == "Kosovo" else (
                      "Single-child parent plus its only child is labelled Municipality in the 2010 source, while "+
                      "Article 105 treats Aghion Oros as a self-governed region. Reconcile the role and exact statutory "+
                      "territorial extent before changing the relationship.") if name == "Agion Oros" else (
                      "Single-child same-name parent has no pinned parent shapeID; retained review data records weak/incompatible "+
                      "fallback source-parent geometry from other regions. Keep the location ID; replace or justify the "+
                      "parent grouping only after authoritative regional boundaries establish the correct relationship.") if weak_fallback else (
                      "Workload subset does not establish province purpose/completeness, boundary validity, or child tier.")
    province_rows.append({"province_id": pid, "province_name": name, "reference_owner": owner,
                          "workload_area": area.get("name", "<missing>"),
                          "owned_location_count": n, "published_child_count": full_children,
                          "partial_parent_scope": "yes" if full_children and n < full_children else "unknown",
                          "purpose_and_parent_finding": h.get("metadata", {}).get("basis", ""),
                          "source_id": h.get("metadata", {}).get("source", ""),
                          "source_url": h.get("metadata", {}).get("source_url", ""),
                          "parent_shape_id": parent_shape_id,
                          "parent_feature_match": p_feature_match,
                          "parent_source_feature_name": p_source.get("shapeName", "") if p_source else "",
                          "parent_source_feature_role_label": p_source.get("shapeType", "") if p_source else "",
                          "parent_source_metadata_canonical": p_meta.get("boundaryCanonical", ""),
                          "parent_source_vintage": p_meta.get("boundaryYear", p_meta.get("boundaryYearRepresented", "")),
                          "parent_source_license": p_meta.get("boundaryLicense", ""),
                          "semantic_review_action": h.get("metadata", {}).get("semantic_review", {}).get("action", ""),
                          "review_reasons": "; ".join(h.get("metadata", {}).get("review_reasons", [])),
                          "stored_parent_evidence": "; ".join(x.get("inspected_fact", "") for x in h.get("metadata", {}).get("semantic_review", {}).get("evidence", [])),
                          "outcome": parent_outcome,
                          "finding": parent_finding,
                          "citation_keys": "S1;S2;S3" if owner == "Greece" else "S4;S5;S6"})
with (HERE / "province-scope.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(province_rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(province_rows)

assert len(rows) == 230 and len(province_rows) == 17
assert Counter(r["source_id"] for r in rows) == {"gb:GRC:ADM3": 226, "gb:XKX:ADM1": 4}
assert Counter(r["outcome"] for r in rows) == {"insufficient-evidence": 225, "correction-needed": 5}
assert all(r["source_feature_match"] == "all source features matched" for r in rows)
area_rows = []
for area_id, name in area_names.items():
    full_ids = area_members[area_id]
    owned = set(wanted) & full_ids
    a = parents[area_id]
    area_rows.append({"area_id": area_id, "area_name": name, "owned_location_count": len(owned),
                      "pinned_full_area_count": len(full_ids), "partial_area_scope": "yes" if len(owned) < len(full_ids) else "no",
                      "declared_issue_full_count": next(x["full_area_location_count"] for x in SCOPE["area_scopes"] if x["id"] == area_id),
                      "purpose": a.get("metadata", {}).get("basis", ""),
                      "framework_status": a.get("metadata", {}).get("framework_status", ""),
                      "semantic_review_action": a.get("metadata", {}).get("semantic_review", {}).get("action", ""),
                      "remaining_review_reasons": "; ".join(a.get("metadata", {}).get("semantic_review", {}).get("remaining_reasons", [])),
                      "outcome": "insufficient-evidence",
                      "finding": "The published workload area is a retained WGSRPD level 3 botanical-country grouping; evidence here does not establish complete current geography or justify a new political or geographic boundary."})
with (HERE / "area-scope.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(area_rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(area_rows)
summary = {"issue": 421, "scoped_locations": len(rows), "province_parents": len(province_rows),
                  "outcomes": dict(Counter(r["outcome"] for r in rows)),
                  "source_counts": dict(Counter(r["source_id"] for r in rows)),
                  "GRC_source_features": len(grc_features), "XKX_asset_features": len(xkx_features),
                  "area_counts": {r["area_name"]: [r["owned_location_count"], r["pinned_full_area_count"]] for r in area_rows},
                  "assessment_sha256": hashlib.sha256((HERE / "assessment.csv").read_bytes()).hexdigest(),
                  "province_scope_sha256": hashlib.sha256((HERE / "province-scope.csv").read_bytes()).hexdigest(),
                  "area_scope_sha256": hashlib.sha256((HERE / "area-scope.csv").read_bytes()).hexdigest()}
(HERE / "reproduction-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
