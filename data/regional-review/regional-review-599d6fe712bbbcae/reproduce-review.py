#!/usr/bin/env python3
"""Reproduce the read-only #427 county crosswalk and geometry diagnostics.

Run from the repository root with Python 3.8+, and install the reported
Shapely, pyproj and pyshp versions in a private environment. Outputs are
limited to this packet. Geometry scores are diagnostics, not boundary proof.
"""
import csv
import hashlib
import io
import json
import math
import pathlib
import re
import subprocess
import sys
import zipfile

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union
import shapely
import shapefile

ROOT = pathlib.Path.cwd()
PACKET = ROOT / "data/regional-review/regional-review-599d6fe712bbbcae"
SOURCES = PACKET / "sources"
OUT = PACKET / "findings"
OUT.mkdir(exist_ok=True)

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    return json.loads(path.read_text())

def norm(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())

def features(path):
    return read_json(path)["features"]

issue = read_json(PACKET / "source/issue-427-api-snapshot.json")
body = issue["body"]
match = re.search(r"member_location_ids`?\s*:\s*(\[[^\]]*\])", body)
if not match:
    match = re.search(r'"member_location_ids"\s*:\s*(\[[^\]]*\])', body)
if not match:
    raise RuntimeError("Could not parse issue pinned member_location_ids")
ids = json.loads(match.group(1))
assert len(ids) == 245 and len(set(ids)) == 245
assert ids.count("atlas:territory:BMU") == 1
scope_hash = re.search(r'"member_location_ids_sha256"\s*:\s*"([0-9a-f]{64})"', body).group(1)
assert hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest() == scope_hash
neighbor_issue = read_json(PACKET / "source/issue-428-api-snapshot-after-research-20261005.json")
neighbor_match = re.search(r'"member_location_ids"\s*:\s*(\[[^\]]*\])', neighbor_issue["body"])
if not neighbor_match:
    neighbor_match = re.search(r"member_location_ids`?\s*:\s*(\[[^\]]*\])", neighbor_issue["body"])
if not neighbor_match:
    raise RuntimeError("Could not parse sibling issue #428 pinned members")
neighbor_ids = json.loads(neighbor_match.group(1))
assert len(neighbor_ids) == 279 and len(set(neighbor_ids)) == 279
neighbor_body = neighbor_issue["body"]
neighbor_hash = re.search(r'"member_location_ids_sha256"\s*:\s*"([0-9a-f]{64})"', neighbor_body).group(1)
assert hashlib.sha256("\n".join(sorted(neighbor_ids)).encode()).hexdigest() == neighbor_hash
east_south_central_427 = {x for x in ids if x.startswith("gb:USA:ADM2:")}
east_south_central_428 = {x for x in neighbor_ids if x.startswith("gb:USA:ADM2:")}
assert not east_south_central_427.intersection(east_south_central_428)
assert len(east_south_central_427) == 244 and len(east_south_central_428) == 279
south_atlantic_issue = read_json(PACKET / "source/issue-429-api-snapshot-20261005.json")
assert neighbor_issue["state"] == "open" and "status:claimed" in [label["name"] for label in neighbor_issue["labels"]]
assert south_atlantic_issue["state"] == "closed"
south_atlantic_body = south_atlantic_issue["body"]
third_match = re.search(r'"member_location_ids"\s*:\s*(\[[^\]]*\])', south_atlantic_body)
if not third_match:
    third_match = re.search(r"member_location_ids`?\s*:\s*(\[[^\]]*\])", south_atlantic_body)
if not third_match:
    raise RuntimeError("Could not parse neighboring South Atlantic issue #429 pinned members")
south_atlantic_ids = json.loads(third_match.group(1))
assert len(south_atlantic_ids) == 268 and len(set(south_atlantic_ids)) == 268
south_atlantic_hash = re.search(r'"member_location_ids_sha256"\s*:\s*"([0-9a-f]{64})"', south_atlantic_body).group(1)
assert hashlib.sha256("\n".join(sorted(south_atlantic_ids)).encode()).hexdigest() == south_atlantic_hash
assert not set(ids).intersection(south_atlantic_ids) and not set(neighbor_ids).intersection(south_atlantic_ids)

atlas = {}
for path in (ROOT / "data/geography").glob("*.json"):
    for f in read_json(path).get("features", []):
        ident = f.get("properties", {}).get("id")
        if ident in ids:
            atlas[ident] = f
assert set(atlas) == set(ids), (len(atlas), set(ids) - set(atlas))
all_atlas = {}
for path in (ROOT / "data/geography").glob("*.json"):
    for f in read_json(path).get("features", []):
        ident = f.get("properties", {}).get("id")
        if ident:
            all_atlas[ident] = f
neighbor_states = {}
for ident in east_south_central_428:
    f = all_atlas[ident]
    parent_name = f["properties"]["parent_id"].split(":")[2]
    neighbor_states[parent_name] = neighbor_states.get(parent_name, 0) + 1
assert neighbor_states == {"kentucky": 120, "georgia": 159}, neighbor_states
third_states = {}
for ident in south_atlantic_ids:
    feature = all_atlas[ident]
    parent_name = feature["properties"]["parent_id"].split(":")[2]
    third_states[parent_name] = third_states.get(parent_name, 0) + 1
assert third_states == {"florida": 67, "south-carolina": 46, "west-virginia": 55, "north-carolina": 100}, third_states

gb_file = SOURCES / "geoboundaries-2018/geoBoundaries-USA-ADM2.geojson"
gb = {f["properties"]["shapeID"]: f for f in features(gb_file)}
tiger = {}
for state in ("01", "21", "28", "47"):
    path = SOURCES / ("census-tigerweb-acs26/counties-state-" + state + ".geojson")
    for f in features(path):
        props = f["properties"]
        tiger[props["GEOID"]] = f
assert [sum(1 for g in tiger.values() if g["properties"]["STATE"] == s)
        for s in ("01", "21", "28", "47")] == [67, 120, 82, 95]

cbf_zip = zipfile.ZipFile(SOURCES / "census-2018-cartographic-boundaries/cb_2018_us_county_500k.zip")
shp = next(n for n in cbf_zip.namelist() if n.endswith(".shp"))
dbf = next(n for n in cbf_zip.namelist() if n.endswith(".dbf"))
reader = shapefile.Reader(shp=io.BytesIO(cbf_zip.read(shp)), dbf=io.BytesIO(cbf_zip.read(dbf)))
fields = [f[0] for f in reader.fields[1:]]
cbf = {}
for rec, geom in zip(reader.records(), reader.shapes()):
    p = dict(zip(fields, rec))
    cbf[p["GEOID"]] = {"properties": p, "geometry": geom.__geo_interface__}

to5070 = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True).transform
def iou(a, b):
    aa, bb = transform(to5070, a), transform(to5070, b)
    union = aa.union(bb).area
    return aa.intersection(bb).area / union if union else 0.0

states = {"01": "Alabama", "21": "Kentucky", "28": "Mississippi", "47": "Tennessee"}
rows, assessments = [], []
for ident in sorted((x for x in ids if x.startswith("gb:USA:ADM2:"))):
    props = atlas[ident]["properties"]
    sid = ident.rsplit(":", 1)[1]
    source = gb[sid]
    sp = source["properties"]
    parent_prefix = props["parent_id"].split(":")
    parent_state_name = parent_prefix[2] if len(parent_prefix) > 2 else ""
    parent_state = next((code for code, name in states.items() if norm(name) == norm(parent_state_name)), None)
    assert parent_state, (ident, props["parent_id"])
    candidates = [g for g in tiger.values()
                  if g["properties"]["STATE"] == parent_state
                  and norm(g["properties"]["BASENAME"]) == norm(sp["shapeName"])]
    assert len(candidates) == 1, (ident, sp["shapeName"], [c["properties"]["GEOID"] for c in candidates])
    current = candidates[0]
    cp = current["properties"]
    geoid = cp["GEOID"]
    old = cbf[geoid]
    source_geom = shape(source["geometry"])
    old_geom = shape(old["geometry"])
    current_geom = shape(current["geometry"])
    old_score = iou(source_geom, old_geom)
    current_score = iou(source_geom, current_geom)
    expected_parent = "framework:province:" + states[cp["STATE"]].casefold() + ":"
    parent_ok = props["parent_id"].startswith(expected_parent)
    assert cp["LSADC"] == "06"
    assert parent_ok, (ident, props["parent_id"], cp["STATE"])
    assert norm(props["name"]) == norm(sp["shapeName"]) == norm(cp["BASENAME"])
    rows.append({"atlas_id": ident, "atlas_name": props["name"], "parent_id": props["parent_id"],
                 "state": states[cp["STATE"]], "state_fips": cp["STATE"], "source_shape_id": sid,
                 "source_name": sp["shapeName"], "geoid_2018_and_2026": geoid,
                 "census_2026_name": cp["NAME"], "lsadc": cp["LSADC"], "funcstat": cp["FUNCSTAT"],
                 "parent_state_match": parent_ok, "2018_cb_iou": round(old_score, 8),
                 "2026_tiger_iou": round(current_score, 8), "below_095_2018": old_score < .95,
                 "below_095_2026": current_score < .95,
                 "boundary_interpretation": "diagnostic-only; neither generalized/cartographic comparison certifies legal boundary"})
    assessments.append({"subject_id": ident, "subject_name": props["name"], "parent_id": props["parent_id"],
                        "semantic_role_status": "justified", "semantic_basis": "Named U.S. county/county-equivalent; current Census county-equivalent row is one-to-one by unique state+name and GEOID; Census county-equivalent tier and state parent agree.",
                        "parent_relationship_status": "justified",
                        "boundary_status": "insufficient-evidence", "boundary_limit": "Geometries are generalized/cartographic vintages; overlay scores diagnose change/representation but do not establish legal boundary accuracy or completeness."})

assert len(rows) == 244 and len({r["geoid_2018_and_2026"] for r in rows}) == 244
assert {r["state"] for r in rows} == {"Alabama", "Mississippi", "Tennessee"}
assert len([r for r in rows if r["state"] == "Alabama"]) == 67
assert len([r for r in rows if r["state"] == "Mississippi"]) == 82
assert len([r for r in rows if r["state"] == "Tennessee"]) == 95

# Bermuda comparison is deliberately bounded to public-domain Natural Earth.
bmu = atlas["atlas:territory:BMU"]
ne_zip = zipfile.ZipFile(SOURCES / "natural-earth-5.1.1/ne_10m_admin_0_countries.zip")
ne_shp = next(n for n in ne_zip.namelist() if n.endswith(".shp"))
ne_dbf = next(n for n in ne_zip.namelist() if n.endswith(".dbf"))
ne_reader = shapefile.Reader(shp=io.BytesIO(ne_zip.read(ne_shp)), dbf=io.BytesIO(ne_zip.read(ne_dbf)))
ne_fields = [f[0] for f in ne_reader.fields[1:]]
bermuda = []
for rec, geom in zip(ne_reader.records(), ne_reader.shapes()):
    p = dict(zip(ne_fields, rec))
    if p.get("ADMIN") == "Bermuda" or p.get("NAME") == "Bermuda":
        bermuda.append({"properties": p, "geometry": geom.__geo_interface__})
assert len(bermuda) == 1
atlas_bmu = shape(bmu["geometry"])
ne_bmu = shape(bermuda[0]["geometry"])
bermuda_summary = {"subject_id": "atlas:territory:BMU", "name": bmu["properties"]["name"],
                   "parent_id": bmu["properties"]["parent_id"], "natural_earth_name": bermuda[0]["properties"].get("ADMIN"),
                   "natural_earth_iso": bermuda[0]["properties"].get("ADM0_A3"),
                   "atlas_parts": len(atlas_bmu.geoms) if atlas_bmu.geom_type == "MultiPolygon" else 1,
                   "natural_earth_parts": len(ne_bmu.geoms) if ne_bmu.geom_type == "MultiPolygon" else 1,
                   "atlas_to_natural_earth_iou": round(iou(atlas_bmu, ne_bmu), 8),
                   "semantic_role_status": "justified-with-limits",
                   "semantic_basis": "Official UK government reference identifies Bermuda as a British Overseas Territory; this supports territory identity only and says nothing about the Atlas reporting parent or historic status.",
                   "boundary_status": "insufficient-evidence",
                   "boundary_limit": "Natural Earth is generalized cartographic evidence only. Current reusable authoritative whole-territory geometry was not found. The inspected Esri item metadata says its MBR data may not be exported; no geometry was downloaded or used."}
assessments.append({"subject_id": "atlas:territory:BMU", "subject_name": "Bermuda", "parent_id": bmu["properties"]["parent_id"],
                    "semantic_role_status": "justified", "semantic_basis": bermuda_summary["semantic_basis"],
                    "parent_relationship_status": "insufficient-evidence",
                    "boundary_status": "insufficient-evidence", "boundary_limit": bermuda_summary["boundary_limit"]})

# The issue also declares the three full U.S. state provinces and Bermuda's
# synthetic parent. Compare the union of each state province's exact children
# with the current official Census state layer; do not certify legal borders.
province_specs = {
    "framework:province:alabama:2ea4f64966c3": ("Alabama", "01", 67),
    "framework:province:mississippi:ea192a347106": ("Mississippi", "28", 82),
    "framework:province:tennessee:1e9839d5c457": ("Tennessee", "47", 95),
}
hierarchy = {r["id"]: r for r in read_json(ROOT / "data/hierarchy.json")}
province_rows = []
province_geometries = []
for pid, (name, state_code, expected_count) in province_specs.items():
    node = hierarchy[pid]
    children = [f for f in all_atlas.values() if f.get("properties", {}).get("parent_id") == pid]
    assert node["level"] == "province" and node["name"] == name and len(children) == expected_count
    state_path = SOURCES / ("census-tigerweb-acs26/states-state-" + state_code + ".geojson")
    state_features = features(state_path)
    assert len(state_features) == 1 and state_features[0]["properties"]["GEOID"] == state_code
    assert norm(state_features[0]["properties"]["BASENAME"]) == norm(name)
    assert node["metadata"]["child_count"] == expected_count
    county_union = unary_union([shape(f["geometry"]) for f in children])
    state_geom = shape(state_features[0]["geometry"])
    score = iou(county_union, state_geom)
    province_rows.append({"province_id": pid, "name": name, "semantic_status": "justified",
                          "role_basis": "Current named U.S. state-level administrative unit; Census state layer and Census Regions/Divisions roster name the state.",
                          "current_state_geoid": state_code, "atlas_child_count": len(children),
                          "tigerweb_child_count": sum(1 for g in tiger.values() if g["properties"]["STATE"] == state_code),
                          "children_complete_against_layer_count": len(children) == sum(1 for g in tiger.values() if g["properties"]["STATE"] == state_code),
                          "boundary_status": "insufficient-evidence",
                          "county_union_vs_2026_state_iou": round(score, 8),
                          "boundary_limit": "Diagnostic comparison of the union of 2018-derived Atlas county shapes with Census 2026 state cartography; not a legal-boundary or completeness certificate."})
    province_geometries.append({"province_id": pid, "name": name, "union_vs_state_iou": round(score, 8)})
bermuda_parent = hierarchy[bmu["properties"]["parent_id"]]
assert bermuda_parent["level"] == "province" and bermuda_parent["name"] == "Bermuda"
assert bermuda_parent["metadata"]["child_count"] == 1
province_rows.append({"province_id": bermuda_parent["id"], "name": bermuda_parent["name"],
                      "semantic_status": "insufficient-evidence",
                      "role_basis": "Retained Atlas framework grouping is named as a territory and coextensive with one location; no separate administrative parent tier is established.",
                      "current_state_geoid": "", "atlas_child_count": 1,
                      "tigerweb_child_count": "", "children_complete_against_layer_count": "",
                      "boundary_status": "insufficient-evidence", "county_union_vs_2026_state_iou": "",
                      "boundary_limit": "No current, reusable authoritative whole-territory reference boundary established; Natural Earth diagnostic does not certify this parent."})

def write_csv(path, records):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader(); w.writerows(records)

write_csv(OUT / "usa-county-crosswalk.csv", rows)
write_csv(OUT / "subject-assessments.csv", sorted(assessments, key=lambda r:r["subject_id"]))
write_csv(OUT / "province-assessments.csv", sorted(province_rows, key=lambda r:r["province_id"]))
(OUT / "bermuda-assessment.json").write_text(json.dumps(bermuda_summary, indent=2, ensure_ascii=False) + "\n")

# Explicit controls protect the match method against name-only accidental joins.
positive = next(r for r in rows if r["atlas_name"] == "Morgan" and r["state"] == "Tennessee")
assert positive["geoid_2018_and_2026"] == "47129" and positive["parent_state_match"]
negative_wrong_state = [g for g in tiger.values() if g["properties"]["STATE"] != "47" and g["properties"]["STATE"] in ("01", "28") and norm(g["properties"]["BASENAME"]) == norm("Morgan")]
assert negative_wrong_state and len([g for g in tiger.values() if g["properties"]["STATE"] == "47" and norm(g["properties"]["BASENAME"]) == norm("Morgan")]) == 1
controls = {"method": "unique same-state normalized name; unique GEOID carries 2018 and 2026 comparisons; no geometry-selected identity repair",
            "positive_control": {"name": positive["atlas_name"], "state": positive["state"], "geoid": positive["geoid_2018_and_2026"], "passed": True},
            "negative_control": {"wrong_state_candidate_states": sorted({g["properties"]["STATE"] for g in negative_wrong_state}), "name": "Morgan", "target_state": "Tennessee", "selected_geoid": positive["geoid_2018_and_2026"], "passed": True},
            "axis_order_control": "Inputs read as GeoJSON longitude,latitude; EPSG:5070 transform is explicitly always_xy. Reversed-axis trial omitted because it produces out-of-range latitude for most county coordinates and is not a valid alternative input.",
            "interpretive_limit": "Controls validate the identity join and code path, not legal or positional truth of any boundary."}
(OUT / "controls.json").write_text(json.dumps(controls, indent=2, ensure_ascii=False) + "\n")

summary = {"scope": {"issue": 427, "pinned_members": len(ids), "county_members": len(rows), "bermuda_members": 1},
           "repository_head_at_reproduction": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
           "counts": {"current_tigerweb": {s: sum(1 for g in tiger.values() if g["properties"]["STATE"] == s) for s in ("01", "21", "28", "47")},
                      "scope_county_by_state": {s: sum(1 for r in rows if r["state_fips"] == s) for s in ("01", "28", "47")},
                      "east_south_central_full_division": {"states": ["Alabama", "Kentucky", "Mississippi", "Tennessee"],
                                                            "four_state_count": sum(1 for s in ("01", "21", "28", "47") for g in tiger.values() if g["properties"]["STATE"] == s),
                                                            "issue_427_subset": len(east_south_central_427),
                                                            "sibling_428_total_members": len(neighbor_ids),
                                                            "sibling_428_east_south_central_subset": neighbor_states["kentucky"],
                                                            "sibling_state_counts": neighbor_states,
                                                            "disjoint": not bool(east_south_central_427.intersection(east_south_central_428))},
                      "neighboring_packet_partition": {"427_members": len(ids), "428_members": len(neighbor_ids), "429_members": len(south_atlantic_ids),
                                                        "pairwise_disjoint": not bool(set(ids).intersection(neighbor_ids) or set(ids).intersection(south_atlantic_ids) or set(neighbor_ids).intersection(south_atlantic_ids)),
                                                        "429_current_state_counts": third_states,
                                                        "429_issue_state_at_snapshot": south_atlantic_issue["state"],
                                                        "428_issue_state_at_snapshot": neighbor_issue["state"],
                                                        "428_status_label_at_snapshot": "status:claimed" in [label["name"] for label in neighbor_issue["labels"]]},
                      "parent_match_count": sum(1 for r in rows if r["parent_state_match"]),
                      "province_count": len(province_rows),
                      "u_s_province_union_vs_state_iou": {r["name"]: r["county_union_vs_2026_state_iou"] for r in province_rows if r["current_state_geoid"]},
                      "unique_current_geoid_count": len({r["geoid_2018_and_2026"] for r in rows}),
                      "2018_iou_below_095": sum(1 for r in rows if r["below_095_2018"]),
                      "2026_iou_below_095": sum(1 for r in rows if r["below_095_2026"])},
           "method": {"projection": "EPSG:5070; always_xy", "score": "intersection area / union area", "interpretation": "diagnostic only; both 2018 and 2026 geometry sources are generalized/cartographic or service representations"},
           "software": {"python": sys.version.split()[0], "shapely": shapely.__version__, "pyproj": __import__("pyproj").__version__, "pyshp": shapefile.__version__},
           "input_hashes": {"geoBoundaries": digest(gb_file),
                            "Census_2018_cartographic_zip": digest(SOURCES / "census-2018-cartographic-boundaries/cb_2018_us_county_500k.zip"),
                            "Natural_Earth_zip": digest(SOURCES / "natural-earth-5.1.1/ne_10m_admin_0_countries.zip"),
                            "TIGERweb_state_layer_80_metadata": digest(SOURCES / "census-tigerweb-acs26/states-layer-80-metadata.json"),
                            **{"TIGERweb_counties_" + s: digest(SOURCES / ("census-tigerweb-acs26/counties-state-" + s + ".geojson")) for s in ("01", "21", "28", "47")},
                            **{"TIGERweb_state_" + s: digest(SOURCES / ("census-tigerweb-acs26/states-state-" + s + ".geojson")) for s in ("01", "28", "47")}},
           "issue_snapshot_sha256": digest(PACKET / "source/issue-427-api-snapshot.json"),
           "issue_pinned_member_ids_sha256": scope_hash,
           "sibling_428_pinned_member_ids_sha256": neighbor_hash,
           "sibling_429_pinned_member_ids_sha256": south_atlantic_hash,
           "findings": "See subject-assessments.csv, usa-county-crosswalk.csv, bermuda-assessment.json and REVIEW.md. No core geography modified."}
(OUT / "reproduction-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(summary, indent=2))
