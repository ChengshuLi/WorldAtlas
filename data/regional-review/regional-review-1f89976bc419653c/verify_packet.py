#!/usr/bin/env python3
"""Independent offline invariants for the issue-462 evidence packet."""
import gzip
import hashlib
import json
import pathlib

PACKET = pathlib.Path(__file__).resolve().parent


def read(name):
    return json.loads((PACKET / name).read_text())


scope = read("issue-scope-pinned.json")
assessment = read("assessment.json")
register = read("source-register.json")
ids = scope["member_location_ids"]
assert len(ids) == 230 and len(set(ids)) == 230
assert hashlib.sha256("\n".join(ids).encode()).hexdigest() == scope["member_location_ids_sha256"]
rows = assessment["subjects"]
assert len(rows) == 230 and {r["location_id"] for r in rows} == set(ids)
assert assessment["scope"]["release"] == scope["release"]
assert assessment["scope"]["member_location_ids_sha256"] == scope["member_location_ids_sha256"]
assert assessment["counts"]["total"] == 230
assert assessment["counts"]["correction_needed"] == 17
assert assessment["counts"]["insufficient_evidence"] == 213
assert assessment["counts"]["justified"] == 0
assert assessment["counts"]["point_parent_name_disagreements"] == 1
assert sum(assessment["counts"]["by_source_id"].values()) == 230
assert set(assessment["counts"]["by_source_id"]) == set(scope["source_ids"])
assert all(r["source_feature_id"] and r["source_feature_geometry"]["coordinate_pairs"] > 0 for r in rows)
eco = [r for r in rows if r["location_id"].startswith("atlas:physical:")]
assert len(eco) == 17 and all(r["classification"] == "correction-needed" for r in eco)
assert {r["ecological_source_feature_name"] for r in eco} == {
    "East Sahara Desert", "East Saharan montane xeric woodlands", "Sahelian Acacia savanna",
    "South Sahara desert", "Tibesti-Jebel Uweinat montane xeric woodlands",
}
for item in register["sources"]:
    path = PACKET / item["file"]
    data = path.read_bytes()
    if "original_byte_length" in item:
        assert len(data) == item["original_byte_length"], item["file"]
        assert hashlib.sha256(data).hexdigest() == item["original_sha256"], item["file"]
    else:
        assert len(data) == item["derived_output_byte_length"], item["file"]
        assert hashlib.sha256(data).hexdigest() == item["derived_output_sha256"], item["file"]
baseline = json.loads(gzip.decompress((PACKET / "baseline-members.geojson.gz").read_bytes()))
assert [f["id"] for f in baseline["features"]] == ids
audit = read("geometry-audit.json")
assert audit["subject_count"] == 230
assert audit["scope_ids_sha256"] == scope["member_location_ids_sha256"]
chad_units = audit["chad_source_units_represented_only_by_physical_portions"]
assert len(chad_units) == 6
assert sum(x["portion_subject_count"] for x in chad_units) == 17
assert {x["source_name"] for x in chad_units} == {
    "Tibesti Ouest", "Tibesti Est", "Am-Djarass", "Fada", "Borkou Yala", "Borkou"
}
assert all(0.996 < x["source_admin_area_share_covered_by_all_atlas_physical_parts_planar"] <= 1
           for x in chad_units)
assert all(x["limit"].startswith("Planar comparison") for x in chad_units)
handoffs = read("handoffs.json")
assert handoffs["parent_issue"] == 462
assert [(x["issue"], x["subject_count"]) for x in handoffs["items"]] == [
    (875, 17), (876, 1), (877, 6), (878, 20), (879, 46)
]
assert all(x["status"] == "blocked" and x["depends_on"] == [462] for x in handoffs["items"])
print(json.dumps({"ok": True, "subject_count": len(rows), "source_count": len(register["sources"]),
                  "classification_counts": {k: assessment["counts"][k] for k in ["correction_needed", "insufficient_evidence", "justified"]},
                  "point_parent_disagreements": assessment["source_point_parent_disagreements"],
                  "chad_source_units_represented_only_by_physical_portions": len(chad_units),
                  "linked_blocked_followups": len(handoffs["items"])}, ensure_ascii=False))
