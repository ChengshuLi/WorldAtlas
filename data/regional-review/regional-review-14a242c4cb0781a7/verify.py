#!/usr/bin/env python3
"""Reproduce pinned source/hash, scope, and comparative geometry observations for issue #405."""
import csv, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts/evidence"))
SCOPE = json.loads((ROOT / "scope.json").read_text())
expected = set(SCOPE["member_location_ids"])
assert len(expected) == 23
baseline = json.loads((ROOT / "baseline-inputs.json").read_text())
assert baseline["baseline_commit"] == "a57085b7a5cfdbe3c1e0e4b0cd2e07c6240899fc"
for descriptor in baseline["files"]:
    raw = subprocess.check_output(["git", "show", f"{baseline['baseline_commit']}:{descriptor['path']}"], cwd=REPO)
    assert hashlib.sha256(raw).hexdigest() == descriptor["sha256"], descriptor["path"]
    assert hashlib.sha256((REPO / descriptor["path"]).read_bytes()).hexdigest() == descriptor["sha256"], descriptor["path"]
features = {}
for rel in ("data/geography/part-2.json", "data/geography/part-13.json", "data/geography/part-28.json"):
    for feature in json.loads((REPO / rel).read_text())["features"]:
        loc_id = feature["properties"]["id"]
        if loc_id in expected:
            assert loc_id not in features, loc_id
            features[loc_id] = feature
assert set(features) == expected
with (ROOT / "location-assessments.csv").open(newline="") as f:
    locations = list(csv.DictReader(f))
assert len(locations) == 23 and {x["location_id"] for x in locations} == expected
assert all(x["determination"] in {"justified", "correction-needed", "insufficient-evidence"} for x in locations)
with (ROOT / "province-assessments.csv").open(newline="") as f:
    provinces = list(csv.DictReader(f))
assert len(provinces) == len(SCOPE["province_scopes"]) == 23
assert {x["province_id"] for x in provinces} == {x["id"] for x in SCOPE["province_scopes"]}
with (ROOT / "area-assessments.csv").open(newline="") as f:
    areas = list(csv.DictReader(f))
assert len(areas) == len(SCOPE["area_scopes"]) == 10
assert {x["area_id"] for x in areas} == {x["id"] for x in SCOPE["area_scopes"]}
with (ROOT / "source-policy-review.csv").open(newline="") as f:
    policy_reviews = list(csv.DictReader(f))
assert {x["country_code"] for x in policy_reviews} == {"COK", "PCN", "PYF", "UMI"}
assert all(x["determination"] == "unresolved" for x in policy_reviews)
location_policy = json.loads((REPO / "data/location-policy.json").read_text())
administrative_sources = json.loads((REPO / "data/administrative-sources.json").read_text())
assert not ({"COK", "PCN", "PYF", "UMI"} & set(location_policy["countries"]))
assert not any(key.startswith(("COK:", "PCN:", "PYF:", "UMI:")) for key in administrative_sources)
child_contracts = {
    1052: {"gb:CHL:ADM3:31580391B33082267781919"},
    1058: {"COK-4950", "COK-4951", "COK-4952", "COK-4953", "COK-4954", "COK-4955", "COK-4956", "COK-4959", "COK-4960", "COK-4961", "COK-4962"},
    1059: {"PYF-4963", "PYF-4964", "PYF-4965", "PYF-4966", "PYF-4967"},
    1060: {"PCN+00?"},
    1061: {"UMI-5171", "UMI-5172", "UMI-5173", "UMI-5178"},
}
for number, subjects in child_contracts.items():
    rel = "source/chile-followup-1052-api-snapshot.json" if number == 1052 else f"source/followup-issue-{number}-api-snapshot.json"
    issue = json.loads((ROOT / rel).read_text())
    blocks = re.findall(r"<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->", issue["body"])
    assert issue["state"] == "open" and len(blocks) == 1
    spec = json.loads(blocks[0]); quality = spec["evidence_quality"]
    assert spec["mode"] == "geography" and spec["depends_on"] == [405] and spec["max_prs"] == 1
    assert set(quality["subject_ids"]) == subjects and quality["version"] == 1 and quality["review_kind"] == "geometry"
    assert len(spec["owned_paths"]) == 1 and quality["manifest_path"].startswith(spec["owned_paths"][0])
    assert all(re.fullmatch(r"[a-f0-9]{64}", pin) for pin in quality["pins"].values())
checks = {
    "source/natural-earth/ne_10m_admin_0_map_units.geojson": "57da82be755f4afccd8f3b14251bb2752f5df1395f47d2d86f817470c4a48862",
    "source/natural-earth/ne_10m_land.geojson": "1ac90796408bc6ad6911d69448485d3c4dbf2190370080368a09976e1c9f7416",
    "source/natural-earth/ne_10m_minor_islands.geojson": "8c933ca7a4760256bdc46408355706e39764b0fa01c160c28888b90b4faec29f",
    "source/natural-earth/ne_10m_admin_1_scoped-admin-features.json": "dd3f4a5683c713fd89c00b41748d89771f905ef236feaacb7887818085f3d96e",
    "source/geoboundaries/CHL/geoBoundaries-CHL-ADM3-metaData.json": "658356bb413f8b284b260360d1309527781e1b0c46027e1ae0a4c58da1c99409",
    "source/geoboundaries/CHL/geoBoundaries-CHL-ADM3-Isla-de-Pascua-feature.json": "fb0ea671f05a6334ec7a867ca5cb46fcedb63c5b3cc25a39115f5879c73986cb",
    "source/geoboundaries/KIR/geoBoundaries-KIR-ADM1-metaData.json": "e611d682fb3eb7e64176ac9753942321819a847443c1d3c87f8885e1b981211c",
    "source/geoboundaries/KIR/geoBoundaries-KIR-ADM1.geojson": "93a0914dc2572951a72cae1aef5145bc056180d75b96812c770bff06e8d8e86f",
    "source/chile-followup-1052-api-snapshot.json": "15981340aec150c359975325f4315eb1e569e0e93b7ff93ce29770ab434f385b",
    "source/followup-issue-1058-api-snapshot.json": "abbc5625a971946344117d9eeacf52271d3653a8c0873601dcba4b9ced4bb9f8",
    "source/followup-issue-1059-api-snapshot.json": "0f0d7c49adc2af47d6269c1e4977d692e0772c2216c223aa0d08d9b36ff23099",
    "source/followup-issue-1060-api-snapshot.json": "6e0be04b627127ae68c4cc1f59d022646f524058489504367ef49e939b277614",
    "source/followup-issue-1061-api-snapshot.json": "7eac102d32bea7fda7b8b130093f10514e9973cb86077cd6e68f71b2a19b9793",
}
for rel, wanted in checks.items():
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert got == wanted, (rel, got, wanted)
ne = json.loads((ROOT / "source/natural-earth/ne_10m_admin_1_scoped-admin-features.json").read_text())["features"]
assert len(ne) == 25
assert sum(f["properties"].get("admin") == "Cook Islands" for f in ne) == 11
assert sum(f["properties"].get("admin") == "French Polynesia" for f in ne) == 5
assert sum(f["properties"].get("admin") == "Pitcairn Islands" for f in ne) == 1
assert sum(f["properties"].get("admin") == "United States Minor Outlying Islands" for f in ne) == 8
chl = json.loads((ROOT / "source/geoboundaries/CHL/geoBoundaries-CHL-ADM3-Isla-de-Pascua-feature.json").read_text())
assert chl["properties"]["shapeID"] == "31580391B33082267781919"
kir = json.loads((ROOT / "source/geoboundaries/KIR/geoBoundaries-KIR-ADM1.geojson").read_text())
assert len(kir["features"]) == 3
line = [f for f in kir["features"] if f["properties"]["shapeID"] == "97431129B35506555718846"]
assert len(line) == 1
from shapely.geometry import shape
from shapely import union_all
from geometry import canonical_land, METHOD, VERSION
from ellipsoidal_area import area
from pyproj import Geod
ne_by_key = {(f["properties"].get("admin"), f["properties"].get("name")): f for f in ne}
source_names = {"COK-4951": "Aitutaki", "COK-4956": "Palmerston"}
rows = []
for loc_id in sorted(expected):
    current, props = features[loc_id], features[loc_id]["properties"]
    if loc_id.startswith("gb:CHL:"):
        src, source_name, kind = chl, "Isla de Pascua exact geoBoundaries feature", "exact source feature (geoBoundaries CHL ADM3)"
    elif loc_id.startswith("gb:KIR:"):
        src, source_name, kind = line[0], "Line Islands exact geoBoundaries feature", "exact source feature (geoBoundaries KIR ADM1)"
    elif loc_id == "PCN+00?":
        src = next(f for f in ne if f["properties"].get("admin") == "Pitcairn Islands")
        source_name, kind = "Pitcairn Islands 4-island admin1 group", "parent-group comparison only, not a Henderson shoreline"
    else:
        admin = props.get("reference_owner")
        source_name = source_names.get(loc_id, props.get("name"))
        src = ne_by_key.get((admin, source_name))
        assert src is not None, (loc_id, admin, source_name)
        kind = "same-name Natural Earth admin1 comparator; diagnostic only"
    raw_a, raw_b = shape(current["geometry"]), shape(src["geometry"])
    a, b = canonical_land(raw_a), canonical_land(raw_b)
    overlap = a.intersection(b)
    union = union_all([a, b])
    intersection_area, union_area, source_area, current_area = area(overlap), area(union), area(b), area(a)
    rows.append({"location_id":loc_id,"current_name":props["name"],"comparator_source_name":source_name,"comparison_kind":kind,"current_geometry_type":raw_a.geom_type,"source_geometry_type":raw_b.geom_type,"current_parts":len(raw_a.geoms) if raw_a.geom_type=="MultiPolygon" else 1,"source_parts":len(raw_b.geoms) if raw_b.geom_type=="MultiPolygon" else 1,"current_valid":bool(raw_a.is_valid),"source_valid":bool(raw_b.is_valid),"intersection_over_union":round(intersection_area/union_area,8) if union_area else None,"source_component_coverage":round(intersection_area/source_area,8) if source_area else None,"current_component_coverage":round(intersection_area/current_area,8) if current_area else None,"intersection_area_m2":round(intersection_area,3),"source_area_m2":round(source_area,3),"current_area_m2":round(current_area,3),"current_bounds_lonlat":[round(x,6) for x in raw_a.bounds],"source_bounds_lonlat":[round(x,6) for x in raw_b.bounds],"warning":"WGS84 ellipsoidal overlap diagnostic using the shared helper; not a completeness proof or coastline accuracy score; Pitcairn compares against a broader parent group"})
    if loc_id.startswith("gb:CHL:"):
        remote_components = [g for g in raw_b.geoms if -106 < g.bounds[0] < -105 and g.bounds[2] < -105]
        assert remote_components
        remote = union_all(remote_components)
        remote_clip = canonical_land(remote)
        remote_overlap = area(remote_clip.intersection(a))
        main_components = [g for g in raw_b.geoms if g.bounds[0] < -109 and g.bounds[2] < -109]
        assert main_components
        main_clip = canonical_land(union_all(main_components))
        main_overlap = area(main_clip.intersection(a))
        controls = {"location_id": loc_id, "method": METHOD, "helper_version": VERSION,
                    "positive_self_overlap_iou": round(area(a.intersection(a)) / area(union_all([a, a])), 8),
                    "positive_main_rapa_nui_source_overlap_m2": round(main_overlap, 3),
                    "positive_main_source_overlap_detected": main_overlap > 0,
                    "negative_control_remote_source_component_bounds_lonlat": [round(x, 6) for x in remote_components[0].bounds],
                    "negative_control_remote_source_component_area_m2": round(area(remote_clip), 3),
                    "negative_control_remote_component_overlap_m2": round(remote_overlap, 3),
                    "negative_control_expected_disjoint": remote_overlap == 0,
                    "control_limit": "Controls verify helper reproducibility and detection of the retained remote component; they do not certify the source's legal meaning or current location-record effects."}
        (ROOT / "geometry-controls.json").write_text(json.dumps(controls, indent=2) + "\n")
        current_point = props["metadata"]["representative_point"]
        source_point = remote_components[0].representative_point()
        remote_point = [source_point.x, source_point.y]
        _, _, point_distance = Geod(ellps="WGS84").inv(current_point[0], current_point[1], remote_point[0], remote_point[1])
        geocode_screen = {"location_id": loc_id, "current_name": props["name"],
                          "current_representative_point_lonlat": current_point,
                          "current_point_context": "on Rapa Nui; preserves named island identity but does not exclude commune territory elsewhere",
                          "source_component": "Sala y Gómez detached component in the exact 2020 geoBoundaries commune feature",
                          "source_component_representative_point_lonlat": [round(x, 12) for x in remote_point],
                          "geodesic_distance_m": round(point_distance, 3),
                          "method": "WGS84 inverse geodesic using the exact current metadata point and retained source component",
                          "limits": ["A representative point is not a settlement or territorial-membership claim.", "Distance does not decide whether the off-island component belongs in the current physical-location record."]}
        (ROOT / "geocode-screen.json").write_text(json.dumps(geocode_screen, indent=2) + "\n")
out = ROOT / "geometry-comparison.json"
out.write_text(json.dumps({"method":METHOD,"helper_version":VERSION,"source_commit":"ca96624a56bd078437bca8184e78163e5039ad19","source_file_sha256":"22d0e3ad85eb3e27f17cabf8ba2d50e554fbc27a87796ff891d958185da62fb5","geometry_input_files":["data/geography/part-2.json","data/geography/part-13.json","data/geography/part-28.json"],"outcome_limits":["Different outlines show the atlas and comparator are not identical; they do not establish which outline is correct.","Atolls may be encoded as lagoon-enclosing administrative polygons while the atlas may store dry-land unions; coordinate overlap cannot decide between these semantics.","Refuge/protected-area polygons include submerged territory and are not appropriate island-land comparators.","The tiny remote geoBoundaries component near Sala y Gómez matters as a named legal territory even though it contributes little land area.","For Pitcairn, the source is a four-island parent group, not Henderson's dedicated validated shoreline."],"observations":rows},indent=2)+"\n")
print(json.dumps({"scope_ids":len(expected),"locations":len(locations),"provinces":len(provinces),"areas":len(areas),"natural_earth_comparator_features":len(ne),"geometry_rows":len(rows),"output":str(out)},indent=2))
