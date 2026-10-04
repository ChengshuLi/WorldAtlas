#!/usr/bin/env python3
"""Build reproducible evidence for every one of issue #479's 49 pinned IDs."""
from __future__ import annotations
import csv, gzip, hashlib, io, json, pathlib, re, unicodedata, zipfile
from collections import Counter, defaultdict
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Geod, Transformer

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "sources"
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
GEOD = Geod(ellps="WGS84")
ALIASES = {"TGO": {"plainedemo": "plainedumo", "tandjouare": "tandjoare"}}

def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", value)

def key(code, value):
    value = norm(value)
    return ALIASES.get(code, {}).get(value, value)

def unz(name): return gzip.decompress((SRC / name).read_bytes())
def jz(name): return json.loads(unz(name))
def zjson(archive, member): return json.loads(zipfile.ZipFile(io.BytesIO(unz(archive))).read(member))
def sha(data): return hashlib.sha256(data).hexdigest()
def poly_area_km2(geom): return transform(PROJECT, geom).area / 1e6

scope = json.loads((ROOT / "scope.json").read_text())
ids = scope["member_location_ids"]
assert len(ids) == scope["location_count"] == 49
assert sha("\n".join(ids).encode()) == scope["member_location_ids_sha256"]
assert scope["release"]["id"] == "geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e"
members = json.loads((ROOT / "baseline-members.json").read_text())
assert [r["id"] for r in members] == ids

old, current, parent_features, current_sources = {}, {}, {}, {}
for code, slug in [("SLE", "sle"), ("TGO", "tgo")]:
    source = json.loads(unz(f"geoboundaries-{code}-adm2-2017.geojson.gz"))
    old[code] = {key(code, f["properties"]["shapeName"]): f for f in source["features"]}
    adm2 = zjson(f"hdx-cod-ab-{slug}-geojson.zip.gz", f"{slug}_admin2.geojson")["features"]
    current[code] = {key(code, f["properties"]["adm2_name"]): f for f in adm2}
    adm1 = zjson(f"hdx-cod-ab-{slug}-geojson.zip.gz", f"{slug}_admin1.geojson")["features"]
    parent_features[code] = {f["properties"]["adm1_pcode"]: f for f in adm1}
    current_sources[code] = zjson(f"hdx-cod-ab-{slug}-geojson.zip.gz", f"{slug}_admin2.geojson")
    assert len(old[code]) == (14 if code == "SLE" else 37)
    assert len(current[code]) == (16 if code == "SLE" else 40)
    assert len({f["properties"]["adm2_pcode"] for f in adm2}) == len(adm2), f"duplicate current COD-AB pcode: {code}"

places = jz("wca-sle-tgo-settlements-subset.geojson.gz")["features"]
place_points = defaultdict(list)
for code, slug in [("SLE", "sle"), ("TGO", "tgo")]:
    for f in zjson(f"hdx-cod-ab-{slug}-geojson.zip.gz", f"{slug}_admincapitals.geojson")["features"]:
        p = f["properties"]
        place_points[(code, p.get("adm2_pcode"))].append(p)

summary = {"scope": {"count": 49, "member_ids_sha256": scope["member_location_ids_sha256"], "SLE": 12, "TGO": 37},
 "published_baseline": scope["published_region_baseline"], "source_inventory": {}, "members": [],
 "scope_deltas": [], "parent_inventory": {}, "neighbor_edge_screen": [], "method": {
  "name_match": "Unicode NFKD, ASCII lowercase alphanumeric; explicit Togo source aliases: Plaine de Mô/Plaine du Mo and Tandjouare/Tandjoare.",
  "overlap": "EPSG:6933 equal-area overlays; source-vintage screening only, never an approved border test.",
  "settlement_point_source": "OCHA WCA CC BY layer (source feature subset retained). Group by current COD-AB pcode, then test GeoJSON point geometry against the matching current ADM2 polygon.",
  "limits": ["Administrative source evidence does not establish sovereign title or physical-geography roles.",
    "Settlement points document named place presence only; catalog absence does not establish settlement absence.",
    "Point-to-polygon outliers and overlap differences are unresolved source/vintage crosswalks, not automatic reassignment instructions.",
    "Polygon components are exhaustively enumerated but do not by themselves identify every island, river fragment, or omitted land.",
    "No shared boundary, hierarchy, canonical grid, application or live geography data is modified."]}}

for code, slug, country in [("SLE", "sle", "Sierra Leone"), ("TGO", "tgo", "Togo")]:
    gb_meta = jz(f"geoboundaries-{code}-adm2-current-api-metadata.json.gz")
    cod_pkg = jz(f"hdx-cod-ab-{slug}-package-metadata.json.gz")["result"]
    summary["source_inventory"][code] = {
      "geoBoundaries": {"source":gb_meta["boundarySource"],"role":gb_meta["boundaryCanonical"],
        "adm_level":gb_meta["boundaryType"],"represented_vintage":gb_meta["boundaryYearRepresented"],
        "license":gb_meta["boundaryLicense"],"metadata_url":f"https://www.geoboundaries.org/api/current/gbOpen/{code}/ADM2/",
        "snapshot_sha256":sha(unz(f"geoboundaries-{code}-adm2-2017.geojson.gz")),"features":len(old[code])},
      "ocha_cod_ab": {"title":cod_pkg["title"],"license":cod_pkg.get("license_title"),
        "metadata_modified":cod_pkg.get("metadata_modified"),"notes":cod_pkg.get("notes"),
        "dataset_url":f"https://data.humdata.org/dataset/{cod_pkg['name']}","admin2_features":len(current[code])}}
    summary["parent_inventory"][code] = sorted({(f["properties"]["adm1_name"],f["properties"]["adm1_pcode"]) for f in current[code].values()})

component_rows, point_anomaly_rows, crosswalk_rows = [], [], []
for member in members:
    code = "SLE" if member["owner"] == "Sierra Leone" else "TGO"
    bname = member["name"]
    oldf = old[code].get(key(code, bname))
    nowf = current[code].get(key(code, bname))
    assert oldf and nowf, f"No unambiguous name crosswalk for {member['id']}"
    op, np = oldf["properties"], nowf["properties"]
    assert op["shapeID"] == member["id"].rsplit(":", 1)[1], f"geoBoundaries stable ID mismatch for {member['id']}"
    assert member["source_id"] == f"gb:{code}:ADM2" and member["source_year"] == "2017", f"pinned source role/vintage mismatch for {member['id']}"
    geom_old, geom = shape(oldf["geometry"]), shape(nowf["geometry"])
    old_m, new_m = transform(PROJECT, geom_old), transform(PROJECT, geom)
    union = old_m.union(new_m).area
    iou = old_m.intersection(new_m).area / union if union else None
    parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    pcode = np["adm2_pcode"]
    points = [f for f in places if f["properties"].get("admin0Name") == member["owner"] and f["properties"].get("admin2Pcod") == pcode]
    inside = sum(geom.covers(shape(f["geometry"])) for f in points)
    source_names, destinations, component_counts = Counter(), Counter(), Counter()
    row_outliers=[]
    for f in points:
        p, pg = f["properties"], shape(f["geometry"])
        source_names[str(p.get("admin2Name") or "")] += 1
        if geom.covers(pg):
            for ix, part in enumerate(parts):
                if part.covers(pg): component_counts[str(ix)] += 1; break
            continue
        found=[]
        for other in current[code].values():
            q=other["properties"]
            if shape(other["geometry"]).covers(pg): found.append(q)
        dest=";".join(sorted({f"{q['adm2_name']}[{q['adm2_pcode']}]" for q in found})) or "outside current COD-AB ADM2 polygons"
        destinations[dest]+=1
        anomaly={"assigned_location_id":member["id"],"assigned_location_name":bname,
          "assigned_current_admin2_pcode":pcode,"point_object_id":p.get("OBJECTID"),"point_name":p.get("featureNam"),
          "geojson_lon_lat":json.dumps(list(pg.coords[0])),"catalog_admin2_name":p.get("admin2Name"),
          "catalog_admin2_pcode":p.get("admin2Pcod"),"containing_current_codab_candidates":dest,
          "last_modified":p.get("last_modif"),"source":p.get("source"),
          "finding":"Assigned-code point falls outside its matched current polygon; destination is a crosswalk candidate, not an automatic transfer."}
        row_outliers.append(anomaly);point_anomaly_rows.append(anomaly)
    current_parent=np["adm1_name"]
    parent_mismatch=(code=="SLE" and member["parent_id"].endswith(":northern:6611b338a991") and current_parent=="North Western")
    atlas_parent_name=member["parent_id"].split(":")[-2].replace("-region", "").replace("-", " ").title()
    parent_status="correction-needed" if parent_mismatch else ("supported" if norm(atlas_parent_name)==norm(current_parent) else "insufficient-evidence")
    status="correction-needed" if parent_mismatch else "insufficient-evidence"
    finding=("Current OCHA ADM1 is North Western while the assigned atlas province parent is Northern; source-year reconciliation required. " if parent_mismatch else "")
    finding += "ADM2 role/name and source parent code are documented. Boundary-vintage, settlements, source completeness, and physical island/land identity still need reconciliation."
    if code == "TGO" and key(code, bname) == key(code, "Lome Commune"):
        finding += " The source name is Lome Commune while OCHA dataset notes summarize all 40 ADM2 units as prefectures; retain generic ADM2 placement but verify this unit's statutory role before treating it as a prefecture."
    if parent_status == "insufficient-evidence":
        finding += f" The current OCHA parent {current_parent!r} does not normalize to the atlas parent label {atlas_parent_name!r}; verify aliases and parent role."
    if iou < 0.8: finding += " The old/current polygon overlay differs substantially; the complete source-vintage crosswalk records every positive-overlap candidate."
    row={"id":member["id"],"name":bname,"country":member["owner"],"atlas_parent_id":member["parent_id"],
      "atlas_parent_chain":member["parent_chain"],"pinned_source_id":member["source_id"],"pinned_source_year":member["source_year"],
      "baseline_geoBoundaries_name":op["shapeName"],"baseline_shape_id":op["shapeID"],
      "baseline_role":"Districts" if code=="SLE" else "Prefectures","baseline_license":gb_meta["boundaryLicense"],
      "current_COD_AB_name":np["adm2_name"],"current_COD_AB_parent":current_parent,"current_COD_AB_pcode":pcode,
      "current_parent_pcode":np["adm1_pcode"],"current_valid_on":np.get("valid_on"),
      "current_role":"district" if code=="SLE" else ("commune" if key(code,bname)==key(code,"Lome Commune") else "prefecture"),
      "atlas_parent_label":atlas_parent_name,"parent_assignment_assessment":parent_status,
      "current_official_area_km2":np.get("area_sqkm"),
      "current_geometry_valid":geom.is_valid,"current_disconnected_components":len(parts),
      "component_count_under_1km2":sum(poly_area_km2(p)<1 for p in parts),"component_settlement_counts":dict(component_counts),
      "legacy_current_area_IoU_screen":round(iou,6),"settlement_rows_for_current_code":len(points),
      "settlement_points_inside_current_polygon":inside,"settlement_points_outside_current_polygon":len(points)-inside,
      "settlement_catalog_admin2_name_counts_for_code":dict(source_names),
      "settlement_source_name_mismatch_count":sum(n for name,n in source_names.items() if key(code,name)!=key(code,np["adm2_name"])),
      "outlier_destination_counts":dict(destinations),
      "official_administrative_capital_points":place_points.get((code,pcode),[]),
      "assessment_status":status,"assessment":finding,
      "decision_limit":"Administrative membership and settlement-point evidence are separate; neither establishes political title, settlement completeness, or complete physical footprint."}
    summary["members"].append(row)
    for ix,part in enumerate(parts):
        part_points=[]
        for f in points:
            pg=shape(f["geometry"])
            if part.covers(pg): part_points.append(str(f["properties"].get("featureNam") or "(unnamed)"))
        component_rows.append({"location_id":member["id"],"location_name":bname,"country":member["owner"],
          "current_admin2_pcode":pcode,"component_index_source_order":ix,"component_count":len(parts),
          "component_area_km2":round(poly_area_km2(part),6),"bbox_lonlat":json.dumps(list(part.bounds)),
          "settlement_points_inside_this_component":len(part_points),"settlement_point_names":json.dumps(part_points,ensure_ascii=False),
          "interpretation":"Disconnected polygon component; identity as island or administrative fragment not independently established."})

# Every positive-area old/current overlap is retained; no threshold chooses winners.
for code in ("SLE","TGO"):
    for oldf in old[code].values():
        a=transform(PROJECT,shape(oldf["geometry"]))
        for nowf in current[code].values():
            b=transform(PROJECT,shape(nowf["geometry"]))
            intersection=a.intersection(b).area
            if intersection<=0:continue
            km2=intersection/1e6
            crosswalk_rows.append({"country_code":code,"legacy_name":oldf["properties"]["shapeName"],
              "legacy_shape_id":oldf["properties"]["shapeID"],"current_name":nowf["properties"]["adm2_name"],
              "current_pcode":nowf["properties"]["adm2_pcode"],"current_parent":nowf["properties"]["adm1_name"],
              "positive_intersection_km2":round(km2,6),"legacy_area_covered_pct":round(100*intersection/a.area,4) if a.area else None,
              "current_area_covered_pct":round(100*intersection/b.area,4) if b.area else None,
              "interpretation":"Source-vintage overlap candidate; not an approved member reassignment."})

for code,country in [("SLE","Sierra Leone"),("TGO","Togo")]:
    extras=[]
    for n,f in current[code].items():
        if n not in old[code]:
            p=f["properties"]
            extras.append({"name":p["adm2_name"],"pcode":p["adm2_pcode"],"parent":p["adm1_name"],"valid_on":p.get("valid_on")})
    summary["scope_deltas"].append({"country":country,"legacy_total":len(old[code]),"current_COD_AB_total":len(current[code]),
      "current_units_unmatched_to_legacy_names":extras,"packet_scope_limit":"These units are national context outside the 49 pinned IDs; this packet does not add subjects."})

# Explicit review of the two area and eight province work partitions.
admin_group_rows=[]
for area in scope["area_scopes"]:
    country=area["name"];code="SLE" if country=="Sierra Leone" else "TGO"
    assigned=[r for r in summary["members"] if r["country"]==country]
    extra=next(d["current_units_unmatched_to_legacy_names"] for d in summary["scope_deltas"] if d["country"]==country)
    current_names={key(code,f["properties"]["adm2_name"]):f["properties"]["adm2_name"] for f in current[code].values()}
    legacy_names={key(code,f["properties"]["shapeName"]):f["properties"]["shapeName"] for f in old[code].values()}
    unowned_legacy=[v for k,v in legacy_names.items() if k not in {key(code,r["name"]) for r in assigned}]
    admin_group_rows.append({"scope_level":"area","scope_id":area["id"],"name":country,"country":country,
      "baseline_full_location_count":area["full_area_location_count"],"owned_location_count":area["owned_member_location_count"],
      "owned_ids_in_this_packet":len(assigned),"partial_area":area["partial"],"legacy_2017_source_feature_count":len(old[code]),
      "current_OCHA_admin2_feature_count":len(current[code]),"current_OCHA_admin1_feature_count":len(parent_features[code]),
      "current_source_only_units_not_matching_legacy_names":json.dumps([e["name"] for e in extra]),
      "legacy_scope_members_owned_elsewhere":json.dumps(unowned_legacy),
      "current_parent_assignment_counts":"; ".join(f"{k}: {sum(r['current_COD_AB_parent']==k for r in assigned)}" for k in sorted({r["current_COD_AB_parent"] for r in assigned})),
      "current_admin1_source_comparison":"not applicable to area row",
      "assessment":"Togo owns all 37 pinned legacy IDs but the current OCHA catalog has 40 units. Sierra Leone owns 12 of 14 legacy IDs; #478 owns Western Area Rural and Western Area Urban. Current OCHA has 16 units, including Fabala and Karene beyond the old 14-unit list.",
      "status":"insufficient-evidence"})
for ps in scope["province_scopes"]:
    name=ps["name"]
    country="Togo" if name.endswith("Region") else "Sierra Leone"
    code="TGO" if country=="Togo" else "SLE"
    assigned=[r for r in summary["members"] if r["atlas_parent_id"]==ps["id"]]
    current_parent_counts=Counter(r["current_COD_AB_parent"] for r in assigned)
    expected=norm(name.replace(" Region",""))
    supported=sum(norm(r["current_COD_AB_parent"])==expected for r in assigned)
    current_source_parent_units=Counter(f["properties"]["adm1_name"] for f in current[code].values())
    admins=sorted({r["current_COD_AB_parent"] for r in assigned})
    admin_group_rows.append({"scope_level":"province","scope_id":ps["id"],"name":name,"country":country,
      "baseline_full_location_count":ps["full_province_locations"],"owned_location_count":ps["full_province_locations"],
      "owned_ids_in_this_packet":len(assigned),"partial_area":ps.get("partial",False),"legacy_2017_source_feature_count":None,
      "current_OCHA_admin2_feature_count":None,"current_OCHA_admin1_feature_count":len(admins),
      "current_source_only_units_not_matching_legacy_names":json.dumps([]),"legacy_scope_members_owned_elsewhere":json.dumps([]),
      "current_parent_assignment_counts":"; ".join(f"{k}: {current_parent_counts[k]} (source unit total {current_source_parent_units[k]})" for k in admins),
      "current_admin1_source_comparison":"; ".join(f"{r['name']} IoU {r['equal_area_IoU']:.6f}; symmetric difference {r['symmetric_difference_km2']:.3f} km2" for r in []),
      "assessment":f"{supported} of {len(assigned)} assigned members retain this current source parent name; all parent-coded subjects are individually listed in assessment.csv.",
      "status":"correction-needed" if supported<len(assigned) else "insufficient-evidence"})
summary["area_and_province_assessment_count"]=len(admin_group_rows)

# OCHA same-vintage edge-matched national neighbor screen, limited to the four
# directly adjacent countries and the countries assigned to this issue.
edge0=json.loads(unz("wca-edge-matched-adm0-neighbors.geojson.gz"))["features"]
edge0={f["properties"]["adm0_name"]:shape(f["geometry"]) for f in edge0}
edge1=json.loads(unz("wca-edge-matched-adm1-neighbors.geojson.gz"))["features"]
edge1={(f["properties"]["adm0_name"],f["properties"]["adm1_pcode"]):f for f in edge1}
admin1_comparisons=[]
for code,country in [("SLE","Sierra Leone"),("TGO","Togo")]:
    for pcode,f in sorted(parent_features[code].items()):
        other=edge1.get((country,pcode))
        assert other is not None, f"current admin1 lacks an edge-matched source counterpart: {country} {pcode}"
        a,b=transform(PROJECT,shape(f["geometry"])),transform(PROJECT,shape(other["geometry"]))
        union=a.union(b).area
        admin1_comparisons.append({"country":country,"pcode":pcode,"current_COD_AB_name":f["properties"]["adm1_name"],
          "WCA_edge_matched_name":other["properties"]["adm1_name"],"current_valid_on":f["properties"].get("valid_on"),
          "WCA_valid_on":other["properties"].get("valid_on"),"equal_area_IoU":round(a.intersection(b).area/union,6) if union else None,
          "symmetric_difference_km2":round(a.symmetric_difference(b).area/1e6,6),
          "screen_limit":"Separate packaging/generalization of the same administrative source; not a shared-boundary or physical-land certificate."})
summary["admin1_source_comparison"]={"source":"OCHA WCA 2026 edge-matched ADM1 subset compared with each country's OCHA COD-AB v02 ADM1 layer.",
  "rows":admin1_comparisons,"assessment":"All five source ADM1 units in each country have same-code/name counterparts; all differences are retained as source-version screening only."}
for group in admin_group_rows:
    if group["scope_level"]!="province": continue
    parent_ids={r["current_parent_pcode"] for r in summary["members"] if r["atlas_parent_id"]==group["scope_id"]}
    comparisons=[r for r in admin1_comparisons if r["country"]==group["country"] and r["pcode"] in parent_ids]
    group["current_admin1_source_comparison"]="; ".join(f"{r['current_COD_AB_name']} IoU {r['equal_area_IoU']:.6f}; symmetric difference {r['symmetric_difference_km2']:.3f} km2" for r in comparisons)
for country,neighbors in [("Sierra Leone",["Guinea","Liberia"]),("Togo",["Ghana","Benin"])]:
    for neighbor in neighbors:
        a,b=edge0[country],edge0[neighbor]
        shared=a.boundary.intersection(b.boundary)
        overlap=poly_area_km2(a.intersection(b))
        summary["neighbor_edge_screen"].append({"country":country,"neighbor":neighbor,
          "shared_boundary_km":round(abs(GEOD.geometry_length(shared))/1000,3),
          "areal_overlap_km2":round(overlap,6),"source":"OCHA WCA 2026 edge-matched ADM0",
          "finding":"Shared edge represented in both adjacent country outlines with zero areal overlap in this source pair." if shared.length and overlap==0 else "Unresolved source screen difference.",
          "action":"No shared boundary edits; coordinate any national-edge amendment through the macro owner."})

axis_swapped=sum(abs(f["geometry"]["coordinates"][0]-f["properties"].get("LAT",1e99))<1e-6 and abs(f["geometry"]["coordinates"][1]-f["properties"].get("LONG",1e99))<1e-6 for f in places)
axis_conventional=sum(abs(f["geometry"]["coordinates"][0]-f["properties"].get("LONG",1e99))<1e-6 and abs(f["geometry"]["coordinates"][1]-f["properties"].get("LAT",1e99))<1e-6 for f in places)
summary["settlement_source_axis_check"]={"features":len(places),"geometry_x_matches_LAT_and_y_matches_LONG_within_1e-6":axis_swapped,
  "geometry_x_matches_LONG_and_y_matches_LAT_within_1e-6":axis_conventional,"method":"GeoJSON geometry coordinates used for all spatial placement; LAT/LONG attributes were not used.",
  "uncertainty":"The regional table's LAT/LONG field names are reversed relative to conventional coordinate naming; Togo country-source validation is recorded separately. Geometry property semantics remain subject to publisher confirmation."}
summary["subject_count_assessed"] = len(summary["members"])
summary["subject_status_counts"] = dict(Counter(r["assessment_status"] for r in summary["members"]))
summary["settlement_source_scoped_code_rows"] = sum(r["settlement_rows_for_current_code"] for r in summary["members"])
summary["settlement_geometry_outliers"] = sum(r["settlement_points_outside_current_polygon"] for r in summary["members"])
assert len(summary["members"]) == 49 and len(summary["neighbor_edge_screen"]) == 4
assert all(r["settlement_rows_for_current_code"] > 0 for r in summary["members"])
# Lomé urban-role screen: retain ADM2 source geometry and point evidence without
# inferring a city or metropolitan boundary from administrative names.
city_names = ["Lome Commune", "Golfe", "Agoe-Nyive"]
city_features = {f["properties"]["adm2_name"]: f for f in current["TGO"].values()}
city_rows = []
for name in city_names:
    f = city_features[name]
    geom = shape(f["geometry"])
    p = f["properties"]
    points = [x for x in places if x["properties"].get("admin0Name") == "Togo" and x["properties"].get("admin2Pcod") == p["adm2_pcode"]]
    city_rows.append({"name": name, "pcode": p["adm2_pcode"], "parent": p["adm1_name"],
      "source_role": "commune" if name == "Lome Commune" else "prefecture",
      "area_km2": round(float(p["area_sqkm"]), 8),
      "polygon_components": len(list(geom.geoms)) if geom.geom_type == "MultiPolygon" else 1,
      "WCA_settlement_points_by_current_code": len(points),
      "point_names_matching_Lome_casefold": sum("lome" in str(x["properties"].get("featureNam") or "").casefold() for x in points),
      "source": "OCHA HDX COD-AB v02 Togo ADM2 (valid 2021-01-07) and OCHA WCA settlement layer (last_modif vintage recorded in source register)."})
city_edges = []
for i, a in enumerate(city_names):
    for b in city_names[i+1:]:
        boundary = shape(city_features[a]["geometry"]).boundary.intersection(shape(city_features[b]["geometry"]).boundary)
        city_edges.append({"feature_a": a, "feature_b": b,
          "shared_boundary_km": round(abs(GEOD.geometry_length(boundary))/1000, 3)})
city_screen = {"assessment": "Role and continuity screen only; no official continuous Lomé city/metropolitan footprint source was established.",
  "features": city_rows, "shared_boundaries": city_edges,
  "finding": "Lome Commune is one ADM2 polygon component and is named as a commune; Golfe has two components and Agoe-Nyive one. All three are assigned to Maritime by COD-AB and share boundaries in the source. WCA settlement points document named places, not an urban extent. The distribution and continuity of the Lomé metropolitan settlement across adjacent ADM2 units remains unresolved.",
  "limits": ["OCHA dataset notes summarize all 40 ADM2 units as prefectures, while this feature is named Lome Commune; statutory role is unresolved.", "A single administrative polygon component does not establish urban continuity or completeness.", "Agoe-Nyive is current-source external context, not a new atlas member."]}
(ROOT/"city-role-screen.json").write_text(json.dumps(city_screen,ensure_ascii=False,indent=2)+"\n")
(ROOT/"assessment.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
with (ROOT/"assessment.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(summary["members"][0]),lineterminator="\n");w.writeheader()
    for r in summary["members"]:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
for name,rows in [("geometry-components.csv",component_rows),("settlement-point-anomalies.csv",point_anomaly_rows),("source-vintage-crosswalk.csv",crosswalk_rows),("admin-groups.csv",admin_group_rows),("admin1-source-comparison.csv",admin1_comparisons)]:
    with (ROOT/name).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else [],lineterminator="\n");w.writeheader();w.writerows(rows)
print(json.dumps({"subjects":49,"status_counts":summary["subject_status_counts"],
  "current_name_code_matches":sum(bool(r["current_COD_AB_pcode"]) for r in summary["members"]),
  "settlement_rows_for_assigned_codes":summary["settlement_source_scoped_code_rows"],
  "settlement_point_outliers":summary["settlement_geometry_outliers"],"component_rows":len(component_rows),
  "vintage_overlap_pairs":len(crosswalk_rows),"neighbor_edges":summary["neighbor_edge_screen"]},indent=2,ensure_ascii=False))
