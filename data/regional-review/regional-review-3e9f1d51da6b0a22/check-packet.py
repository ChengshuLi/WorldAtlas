#!/usr/bin/env python3
"""Check packet scope, source capture bytes, outputs, and declared triage totals."""
import hashlib
import json
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
sha = lambda b: hashlib.sha256(b).hexdigest()
read_json = lambda p: json.loads(p.read_text())
scope = read_json(PACKET / "scope.json")
pinned = read_json(PACKET / "issue-scope-pinned.json")
compare = read_json(PACKET / "geometry-summary.json")
comparison_records = [json.loads(line) for line in (PACKET / "geometry-comparisons.jsonl").read_text().splitlines() if line]
assess_records = [json.loads(line) for line in (PACKET / "location-assessments.jsonl").read_text().splitlines() if line]
source_inventory = read_json(PACKET / "source-inventory.json")
summary = assess_records[0]

assert pinned["issue"]["number"] == 444
assert pinned["snapshot_commit"] == summary["baseline_commit"]
assert len(scope["member_location_ids"]) == scope["location_count"] == 230
assert len(set(scope["member_location_ids"])) == 230
assert scope["release"]["hierarchy_sha256"] == "03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d"
assert scope["release"]["footprints_sha256"] == "2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286"
assert scope["macro_certificate_sha256"] == "979afaf22e10dc936ecfe80a8cd288b2ef33d8c7bf509aba9fae4255e3d94d6e"

base_features = {}
for part in ("data/geography/part-0.json", "data/geography/part-2.json"):
    for f in read_json(ROOT / part)["features"]:
        if f["id"] in scope["member_location_ids"]:
            assert f["id"] not in base_features
            base_features[f["id"]] = f
assert set(base_features) == set(scope["member_location_ids"])
assert sum(i.startswith("gb:ARG:") for i in base_features) == 53
assert sum(i.startswith("gb:CHL:") for i in base_features) == 177
assert compare["scoped_location_count"] == 230 and compare["matched_current_feature_count"] == 228
assert len(comparison_records) == 230 and len({r["id"] for r in comparison_records}) == 230
assert set(r["id"] for r in comparison_records) == set(scope["member_location_ids"])
assert set(compare["type_change_location_ids"]) == {r["id"] for r in comparison_records if r.get("geometry_type_changed")}
assert set(compare["iou_below_0_95_location_ids"]) == {r["id"] for r in comparison_records if r.get("simplified_iou_0_001_degrees", 1) < 0.95}

root_input_checks = []
for entry in source_inventory["baseline_inputs"]:
    raw = (ROOT / entry["path"]).read_bytes()
    assert len(raw) == entry["bytes"] and sha(raw) == entry["sha256"], f"pinned baseline input changed: {entry['path']}"
    root_input_checks.append(entry["path"])
for entry in source_inventory["packet_control_files"]:
    raw = (ROOT / entry["path"]).read_bytes()
    assert len(raw) == entry["bytes"] and sha(raw) == entry["sha256"], f"packet scope control changed: {entry['path']}"
for entry in source_inventory["outputs"] + source_inventory["reproduction_methods"]:
    raw = (ROOT / entry["path"]).read_bytes()
    assert len(raw) == entry["bytes"] and sha(raw) == entry["sha256"], f"recorded output/method hash mismatch: {entry['path']}"

arg_path = PACKET / "source-cache/ign-argentina-south-generalized.geojson"
arg_hash = None
if arg_path.exists():
    arg_raw = arg_path.read_bytes()
    assert len(arg_raw) == 1_420_162
    arg_hash = sha(arg_raw)
    assert arg_hash == "3f2b63b4499b01a67274142ec66814997207591090e402ca7bf208b1ac3fc2f3"
    arg_payload = json.loads(arg_raw)
    assert len(arg_payload["features"]) == 56
    assert {str(f["properties"]["CODPROV"]) for f in arg_payload["features"]} == {"26", "58", "62", "78", "94"}

subdere_path = PACKET / "source-cache/subdere-dpa-2023.rar"
subdere_hash = None
commune_count = province_count = None
if subdere_path.exists():
    import shapefile
    assert subdere_path.stat().st_size == 262_380_302
    subdere_hash = sha(subdere_path.read_bytes())
    assert subdere_hash == "4c8dd01ca4ca7d8b111dac78b88cc8ac64c1af7b8ebe0c85a21eaab337ae3fd3"
    communes = shapefile.Reader(str(PACKET / "source-cache/DPA_2023/COMUNAS/COMUNAS_v1.shp"), encoding="utf-8")
    provinces = shapefile.Reader(str(PACKET / "source-cache/DPA_2023/PROVINCIAS/PROVINCIAS_v1.shp"), encoding="utf-8")
    commune_count, province_count = len(communes), len(provinces)
    assert commune_count == 345 and province_count == 56

assert summary["record_type"] == "summary" and summary["location_count"] == 230
rows = [r for r in assess_records if r["record_type"] == "location"]
parents = [r for r in assess_records if r["record_type"] == "parent"]
assert len(rows) == 230 and {r["location_id"] for r in rows} == set(scope["member_location_ids"])
counts = {name: sum(r["disposition"] == name for r in rows) for name in ("justified", "correction-needed", "insufficient-evidence")}
assert counts == {"justified": 116, "correction-needed": 113, "insufficient-evidence": 1}
assert len(parents) == 29
assert {p["parent_id"] for p in parents} == {p["id"] for p in scope["province_scopes"]}
assert {p["parent_id"]: p["child_count_in_this_packet"] for p in parents} == {
    pid: sum(r["parent_id"] == pid for r in rows) for pid in {r["parent_id"] for r in rows}}
assert sum(p["parent_name"] == "Tierra del Fuego" and p["disposition"] == "correction-needed" for p in parents) == 2
arg_followup = {r["location_id"] for r in rows if r["location_id"].startswith("gb:ARG:") and r["disposition"] != "justified"}
chile_followup = {r["location_id"] for r in rows if r["location_id"].startswith("gb:CHL:") and r["disposition"] == "correction-needed"}
assert len(arg_followup) == 16 and len(chile_followup) == 98
arg_geometry_flags = {i for i in compare["type_change_location_ids"] + compare["iou_below_0_95_location_ids"] if i.startswith("gb:ARG:")}
arg_expected_corrections = arg_geometry_flags | {r["location_id"] for r in rows if r["name"] == "Pilnaniyeu"}
assert {r["location_id"] for r in rows if r["disposition"] == "correction-needed" and r["location_id"].startswith("gb:ARG:")} == arg_expected_corrections
explicit_chile_regions = {"Libertador General Bernardo O'Higgins", "Maule", "Valparaíso"}
explicit_chile_units = {r["location_id"] for r in rows if r["current_region_name"] in explicit_chile_regions or r["name"] in {"Peñaflor", "Padre Hurtado"}}
chile_geometry_flags = {i for i in compare["type_change_location_ids"] + compare["iou_below_0_95_location_ids"] if i.startswith("gb:CHL:")}
assert len(explicit_chile_units) == 74
assert {r["location_id"] for r in rows if r["disposition"] == "correction-needed" and r["location_id"].startswith("gb:CHL:")} == explicit_chile_units | chile_geometry_flags
assert sum(r["disposition"] == "insufficient-evidence" and r["name"] == "Paso de los Indios" for r in rows) == 1

print(json.dumps({"scope_ids": len(base_features), "argentina_ids": 53, "chile_ids": 177,
                  "parents": len(parents), "dispositions": counts,
                  "argentina_followup_scope_including_name_gap": len(arg_followup),
                  "chile_followup_scope": len(chile_followup),
                  "pinned_baseline_files_checked": root_input_checks,
                  "ign_sha256_checked_if_restored": arg_hash,
                  "subdere_sha256_checked_if_restored": subdere_hash,
                  "restored_subdere_record_counts_if_available": [commune_count, province_count],
                  "source_restoration_needed_for_full_geometry_reproduction": arg_hash is None or subdere_hash is None,
                  "source_inventory_sources": len(source_inventory["sources"])}, indent=2))
