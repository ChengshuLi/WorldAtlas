#!/usr/bin/env python3
"""Join retained #1650 records to engineering's immutable selected-target join.

This is a record extraction/classification script. It performs no geometry
operations, source requests, native evaluations, or operator executions.
"""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def rows(name):
    with gzip.open(HERE / name, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)

def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

physical = {r["component_id"]: r for r in rows("physical-records-327.jsonl.gz")}
source = {r["component"]: r for r in rows("source-comparison-records-249.jsonl.gz")}
outcomes = {r["component_id"]: r for r in rows("outcomes-327.jsonl.gz")}
join_path = HERE / "engineering-current-target-joins.json"
preimages_path = HERE / "engineering-current-target-preimages.json"
join = json.loads(join_path.read_text(encoding="utf-8"))
target_by_component = {}
for target in join["targets"]:
    for component in target["component_ids"]:
        if component in target_by_component:
            raise SystemExit("component has multiple selected targets: " + component)
        target_by_component[component] = target

if len(physical) != 327 or len(outcomes) != 327 or len(source) != 249:
    raise SystemExit("unexpected retained row counts")
if join["target_count"] != 43 or join["component_links"] != 229 or join["passed"] != 43 or join["refused"]:
    raise SystemExit("unexpected selected-target join status")
if sum(len(t["component_ids"]) for t in join["targets"]) != 229:
    raise SystemExit("selected target component link count mismatch")

empty_support_names = [
    "mapped_inland_water_support", "outside_mapped_L1_context",
    "contradictory_land_water_support", "missing_reconstruction",
    "extra_reconstruction",
]
records = []
counts = {}
for component, outcome in sorted(outcomes.items()):
    p = physical[component]
    s = source.get(component)
    evidence_class = "no-administrative-comparison"
    subjects = []
    residual = None
    full_cover = False
    if s is not None:
        pos = s["positive_area_feature_ids"]
        subjects = sorted({sid for item in pos for sid in item["recorded_stable_subject_ids"]})
        residual = s["component_minus_source_union"]
        if s["status"] == "one-compatible-recorded-subject-uniquely-covers-component":
            evidence_class = "full-source-cover"
            full_cover = True
        elif s["status"] == "no-source-intersection-in-literal-domain":
            evidence_class = "no-source-intersection"
        elif len(pos) == 1 and len(pos[0]["recorded_stable_subject_ids"]) == 1:
            evidence_class = "single-subject-partial"
        elif len(pos) > 1 or len(subjects) > 1:
            evidence_class = "multi-subject-exception"
        else:
            evidence_class = "positive-source-subject-unresolved"

    land = p["complete_support"]["mapped_land_support"]
    l1_cover_relations = [q for q in p["query_relations"]
                          if q["source_level"] == 1 and q["source_covers_candidate"]
                          and q["status"] == "checked" and not q["container_chain_issues"]]
    clean_other_support = all(p["complete_support"][k].get("kind") == "empty"
                              for k in empty_support_names)
    clean_hierarchy = all(v.get("kind") == "empty"
                          for v in p["complete_support"]["hierarchy_disagreements"].values())
    source_remainder_exact = False
    if residual is not None:
        if evidence_class == "full-source-cover":
            source_remainder_exact = (residual["is_empty"] is True
                                      and residual["planar_area_coordinate_units_squared"] == 0
                                      and residual["planar_length_coordinate_units"] == 0
                                      and residual["is_valid"] is True
                                      and residual["geometry_type"] == "Polygon"
                                      and bool(residual.get("geometry_sha256")))
        elif evidence_class == "single-subject-partial":
            source_remainder_exact = (residual["is_empty"] is False
                                      and residual["planar_area_coordinate_units_squared"] > 0
                                      and residual["planar_length_coordinate_units"] > 0
                                      and residual["is_valid"] is True
                                      and residual["geometry_type"] in ("Polygon", "MultiPolygon")
                                      and bool(residual.get("geometry_sha256")))
    unique_subject_fit = evidence_class in ("full-source-cover", "single-subject-partial") and len(subjects) == 1
    whole_land = land.get("kind") == "whole-operation-pointset"
    rule_fit = bool(s and unique_subject_fit and whole_land and clean_other_support
                    and clean_hierarchy and l1_cover_relations and source_remainder_exact)
    target = target_by_component.get(component)
    if component in target_by_component and not target:
        raise SystemExit("invalid selected target join")
    if evidence_class in ("full-source-cover", "single-subject-partial") and target is None:
        raise SystemExit("supported source row lacks selected-target link: " + component)
    record = {
        "component_id": component,
        "candidate_full_feature_sha256": outcome["candidate_current_target"]["feature_sha256"],
        "candidate_geometry_sha256": outcome["candidate_current_target"]["geometry_sha256"],
        "source_evidence_class": evidence_class,
        "source_products": s["source_products"] if s else [],
        "source_status": s["status"] if s else None,
        "positive_area_subject_ids": subjects,
        "source_union_remainder": ({"is_empty": residual["is_empty"],
                                     "is_valid": residual["is_valid"],
                                     "geometry_type": residual["geometry_type"],
                                     "planar_area_coordinate_units_squared": residual["planar_area_coordinate_units_squared"],
                                     "planar_length_coordinate_units": residual["planar_length_coordinate_units"],
                                     "geometry_sha256": residual.get("geometry_sha256")}
                                    if residual else None),
        "physical_rule_facts": {
            "mapped_land_whole_candidate_pointset": whole_land,
            "mapped_land_kind": land.get("kind"),
            "mapped_land_geometry_sha256": land.get("geometry_sha256"),
            "other_supports_empty": clean_other_support,
            "hierarchy_disagreements_empty": clean_hierarchy,
            "level1_source_cover_query_count": len(l1_cover_relations),
            "physical_source_vintage": p["source_vintage"],
            "physical_authority": p["physical_authority"],
            "physical_status": p["physical_status"],
        },
        "predicate_matches": {
            "unique_compatible_recorded_source_subject": unique_subject_fit,
            "whole_mapped_land_pointset": whole_land,
            "clean_other_physical_and_hierarchy_support": clean_other_support and clean_hierarchy,
            "retained_level1_source_cover_query": bool(l1_cover_relations),
            "exact_full_or_partial_remainder_custody": source_remainder_exact,
        },
        "source_only_rule_fit": rule_fit,
        "selected_current_target": ({
            "target_id": target["target_id"],
            "owner_index": target["owner_index"],
            "parent_id": target["current_parent_id"],
            "reference_year": target["reference_year"],
            "source_id": target["source_id"],
            "recorded_feature_sha256": target["recorded_feature_sha256"],
            "original_id_hash_parent_year_consistency": target["original_id_hash_parent_year_consistency"],
            "python_js_preimage_equal": target["js_canonical_equals_original_python_preimage"],
        } if target else None),
        "exception_or_limit": ("source-only predicate fit; actual selected-target/native qualification remains engineering work"
                                if rule_fit else
                                "source fact absent or literal #1647 predicate not fully met; retain original exception/remainder and unresolved facts"),
        "source_cause_status": s["cause_status"] if s else None,
        "authority_and_causality": "unresolved; no source authority, historical truth, processing cause, or native approval inferred",
    }
    records.append(record)
    counts[evidence_class] = counts.get(evidence_class, 0) + 1

if len(records) != 327 or sum(1 for r in records if r["source_only_rule_fit"]) != 93:
    raise SystemExit("unexpected exact-327 classification or rule-fit count")
if counts != {"full-source-cover": 52, "single-subject-partial": 177,
              "multi-subject-exception": 2, "no-source-intersection": 18,
              "no-administrative-comparison": 78}:
    raise SystemExit("unexpected preservation classes: " + repr(counts))

out = HERE / "rule-fit-exceptions-327.jsonl.gz"
with open(out, "wb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
        for row in records:
            gz.write((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
summary = {
    "version": 1,
    "scope": "exact 327 Melanesia operational batch; source-only fit to existing #1647 rule predicates",
    "counts": counts,
    "source_only_rule_fit": 93,
    "fit_by_source_product_and_class": {},
    "selected_target_join": {
        "path": "engineering-current-target-joins.json",
        "sha256": sha_file(join_path),
        "status": join["status"], "actual_main_commit": join["actual_main_commit"],
        "targets": join["target_count"], "component_links": join["component_links"],
        "passed": join["passed"], "refused": len(join["refused"]),
        "operator_executions": join["operators_executed"],
        "js_python_preimage_mismatch_targets": len(join["js_python_preimage_mismatch_targets"]),
        "preimages_path": preimages_path.name,
        "preimages_sha256": sha_file(preimages_path),
        "preimages_bytes": preimages_path.stat().st_size,
    },
    "limits": [
        "This is a literal retained-record source-only prequalification, not source fitness/authority approval, current native qualification, repair selection, or processing-cause finding.",
        "The 64 partial rule-fit rows retain their exact nonempty source-union remainders and must not be treated as complete source coverage.",
        "All 98 original exceptions and all 177 partial rows remain individually represented.",
        "No source/GIS/native operators, provider calls, or whole-world replay were run.",
    ],
}
product = {}
for r in records:
    if r["source_only_rule_fit"]:
        k = r["source_products"][0] + ":" + r["source_evidence_class"]
        product[k] = product.get(k, 0) + 1
summary["fit_by_source_product_and_class"] = dict(sorted(product.items()))
summary["output"] = {"path": out.name, "bytes": out.stat().st_size, "sha256": sha_file(out)}
(HERE / "rule-fit-summary-327.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"counts": counts, "source_only_rule_fit": 93,
                  "output_bytes": out.stat().st_size, "output_sha256": sha_file(out),
                  "targets": join["target_count"], "component_links": join["component_links"]}, sort_keys=True))
