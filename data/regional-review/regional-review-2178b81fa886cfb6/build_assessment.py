#!/usr/bin/env /usr/bin/python3
"""Build exhaustive issue #487 evidence from pinned scope and retained sources."""
import gzip
import hashlib
import json
import os
from pathlib import Path
from osgeo import ogr, osr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "sources"
ogr.UseExceptions()

def read_json(path):
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding="utf-8"))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check(ok, message):
    if not ok:
        raise SystemExit(f"FAIL: {message}")

scope = read_json(HERE / "scope.json")
ids = scope["member_location_ids"]
all_features = {}
for part in read_json(ROOT / "data/world-index.json")["parts"]:
    for feature in read_json(ROOT / "data" / part)["features"]:
        all_features[feature["properties"]["id"]] = feature
for node in read_json(ROOT / "data/hierarchy.json"):
    all_features.setdefault(node["id"], {"properties": node})
current = {i: all_features[i] for i in ids if i in all_features}
check(set(current) == set(ids) and len(ids) == 100, "pinned current members must all resolve once")

source2_data = read_json(SOURCE / "geoboundaries-USA-ADM2-2018.geojson.gz")
source1_data = read_json(SOURCE / "geoboundaries-USA-ADM1-2018.geojson.gz")
tiger_data = read_json(SOURCE / "tigerline-2024-western-county-neighbors.geojson.gz")
eco_data = read_json(SOURCE / "resolve-ca-ecoregions-4.geojson.gz")
source2 = {f["properties"]["shapeID"]: f for f in source2_data["features"]}
source1 = {f["properties"]["shapeName"].casefold(): f for f in source1_data["features"]}
tiger = {}
for f in tiger_data["features"]:
    props = f["properties"]
    tiger[(props["STATEFP"], props["NAME"].casefold())] = f
eco = {int(f["properties"]["ECO_ID"]): f for f in eco_data["features"]}
check(set(eco) == {422, 424, 433, 435}, "four exact RESOLVE Eco_IDs required")

src_srs = osr.SpatialReference()
src_srs.ImportFromEPSG(4326)
src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
area_srs = osr.SpatialReference()
area_srs.ImportFromEPSG(5070)
area_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
to_area = osr.CoordinateTransformation(src_srs, area_srs)

def geojson_geometry(obj, srs=src_srs):
    geom = ogr.CreateGeometryFromJson(json.dumps(obj, separators=(",", ":")))
    if geom is None:
        raise ValueError("invalid GeoJSON geometry")
    geom.AssignSpatialReference(srs)
    return geom

def project(geom):
    result = geom.Clone()
    result.Transform(to_area)
    repaired = not bool(result.IsValid())
    if repaired:
        result = result.MakeValid()
    if result is None or result.IsEmpty() or not result.IsValid():
        raise ValueError("temporary projected geometry could not be made valid")
    return result, repaired

def geometry_summary(geom):
    if geom.GetGeometryName() == "POLYGON":
        polygons = [geom]
    elif geom.GetGeometryName() == "MULTIPOLYGON":
        polygons = [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
    else:
        polygons = [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
    rings = sum(p.GetGeometryCount() for p in polygons)
    holes = sum(max(0, p.GetGeometryCount() - 1) for p in polygons)
    return {
        "geometry_type": geom.GetGeometryName(),
        "components": len(polygons),
        "rings": rings,
        "interior_rings": holes,
        "vertices": geom.GetPointCount() if geom.GetGeometryName() == "POLYGON" else sum(p.GetPointCount() for p in polygons),
        "area_km2_equal_area_screen": round(geom.GetArea() / 1_000_000, 6),
        "temporary_repair": False,
    }

def feature_state(props):
    parent = props.get("parent_id", "")
    if parent == "framework:province:california:f695c774b8ba":
        return "06"
    if parent == "framework:province:washington:b01ae89096c9":
        return "53"
    raise ValueError(f"unexpected parent for {props.get('id')}: {parent}")

current_geom = {}
current_repaired = {}
admin_groups = {}
admin_ref = {}
for loc_id, feature in current.items():
    props = feature["properties"]
    metadata = props.get("metadata", {})
    pred_id = loc_id.rsplit(":", 1)[-1] if loc_id.startswith("gb:USA:ADM2:") else metadata.get("original_id")
    check(pred_id in source2, f"missing 2018 ADM2 source shape for {loc_id} -> {pred_id}")
    geom, repaired = project(geojson_geometry(feature["geometry"]))
    current_geom[loc_id] = geom
    current_repaired[loc_id] = repaired
    admin_groups.setdefault(pred_id, []).append(loc_id)
    admin_ref[pred_id] = feature_state(props)
check(len(admin_groups) == 97, "96 direct counties plus one San Bernardino predecessor must yield 97 admin units")

admin_current = {}
for pred_id, group_ids in admin_groups.items():
    pieces = [current_geom[i] for i in group_ids]
    combined = pieces[0].Clone()
    for part in pieces[1:]:
        combined = combined.Union(part)
        if combined is None:
            raise SystemExit(f"FAIL: temporary union failed for predecessor {pred_id}")
    admin_current[pred_id] = combined

def source_geom(feature):
    g, _ = project(geojson_geometry(feature["geometry"]))
    return g

admin_stats = {}
for pred_id, assigned_ids in admin_groups.items():
    county = source2[pred_id]
    name = county["properties"]["shapeName"]
    state = admin_ref[pred_id]
    census = tiger.get((state, name.casefold()))
    check(census is not None, f"missing TIGER/Line 2024 counterpart {state}/{name}")
    old_g = source_geom(county)
    now_g = admin_current[pred_id]
    new_g = source_geom(census)
    old_area, current_area, new_area = old_g.GetArea(), now_g.GetArea(), new_g.GetArea()
    old_now = old_g.Intersection(now_g).GetArea()
    old_new = old_g.Intersection(new_g).GetArea()
    now_new = now_g.Intersection(new_g).GetArea()
    stats = {
        "county_predecessor_id": pred_id,
        "county_name": name,
        "state_fips": state,
        "geoboundaries_shape_id": county["properties"]["shapeID"],
        "tiger_2024_geoid": census["properties"]["GEOID"],
        "tiger_2024_classfp": census["properties"].get("CLASSFP"),
        "tiger_2024_aland_m2": int(census["properties"]["ALAND"]),
        "tiger_2024_awater_m2": int(census["properties"]["AWATER"]),
        "tiger_2024_land_area_km2": round(int(census["properties"]["ALAND"]) / 1_000_000, 6),
        "tiger_2024_water_area_km2": round(int(census["properties"]["AWATER"]) / 1_000_000, 6),
        "tiger_2024_water_share_pct": round(int(census["properties"]["AWATER"]) / max(1, int(census["properties"]["ALAND"]) + int(census["properties"]["AWATER"])) * 100, 6),
        "assigned_location_ids": sorted(assigned_ids),
        "assigned_current_piece_count": len(assigned_ids),
        "2018_source_feature_valid_in_raw_wgs84": bool(geojson_geometry(county["geometry"]).IsValid()),
        "tiger_2024_feature_valid_in_raw_wgs84": bool(geojson_geometry(census["geometry"]).IsValid()),
        "current_projected_inputs_repaired_for_overlay": any(current_repaired[i] for i in assigned_ids),
        "2018_area_km2": round(old_area / 1_000_000, 6),
        "current_area_km2": round(current_area / 1_000_000, 6),
        "tiger_2024_area_km2": round(new_area / 1_000_000, 6),
        "current_area_minus_tiger_land_area_km2": round((current_area - int(census["properties"]["ALAND"])) / 1_000_000, 6),
        "current_area_minus_tiger_land_plus_water_km2": round((current_area - int(census["properties"]["ALAND"]) - int(census["properties"]["AWATER"])) / 1_000_000, 6),
        "current_intersection_over_2018_pct": round(old_now / old_area * 100, 6),
        "current_intersection_over_tiger_2024_pct": round(now_new / new_area * 100, 6),
        "2018_tiger_2024_iou_pct": round(old_new / old_g.Union(new_g).GetArea() * 100, 6),
        "current_2018_symdiff_km2": round(old_g.SymDifference(now_g).GetArea() / 1_000_000, 6),
        "current_tiger_2024_symdiff_km2": round(now_g.SymDifference(new_g).GetArea() / 1_000_000, 6),
        "interpretation": "Polygon overlay is an equal-area footprint screen. Water jurisdiction, coastal generalization, detached pieces and source-vintage linework need feature-specific review; no overlay metric alone authorizes moving a shared line.",
    }
    admin_stats[pred_id] = stats

# Audit each entire assigned state cohort against the state-level ADM1 source and parent metadata.
state_nodes = {
    "06": all_features["framework:province:california:f695c774b8ba"]["properties"],
    "53": all_features["framework:province:washington:b01ae89096c9"]["properties"],
}
state_parent_audit = {}
for state, state_name in [("06", "California"), ("53", "Washington")]:
    state_source = source1.get(state_name.casefold())
    check(state_source is not None, f"missing USA ADM1 source state {state_name}")
    state_tiger = [f for f in tiger_data["features"] if f["properties"]["STATEFP"] == state]
    source_counties = []
    for tf in state_tiger:
        name = tf["properties"]["NAME"]
        candidates = [sf for sf in source2_data["features"] if sf["properties"]["shapeName"].casefold() == name.casefold()]
        check(candidates, f"missing 2018 ADM2 shape for {state_name}/{name}")
        tg = source_geom(tf)
        ranked = sorted(((source_geom(sf).Intersection(tg).GetArea(), sf) for sf in candidates), key=lambda pair: pair[0], reverse=True)
        check(ranked[0][0] > 0, f"no source geometry overlap for {state_name}/{name}")
        source_counties.append(ranked[0][1])
    check(len({f["properties"]["shapeID"] for f in source_counties}) == len(state_tiger), f"duplicate ADM2 source matches in {state_name}")
    src_state = source_geom(state_source)
    source_union = None
    for county in source_counties:
        g = source_geom(county)
        source_union = g.Clone() if source_union is None else source_union.Union(g)
    assigned_pred_ids = [pred for pred, value in admin_ref.items() if value == state]
    current_union = None
    for pred in assigned_pred_ids:
        g = admin_current[pred]
        current_union = g.Clone() if current_union is None else current_union.Union(g)
    node = state_nodes[state]
    state_parent_audit[state_name] = {
        "state_fips": state,
        "2018_adm1_source": {"shape_id": state_source["properties"]["shapeID"], "name": state_source["properties"]["shapeName"], "type": state_source["properties"]["shapeType"]},
        "current_parent": {"id": node["id"], "name": node["name"], "level": node["level"], "parent_id": node["parent_id"], "source": node.get("metadata", {}).get("source"), "basis": node.get("metadata", {}).get("basis"), "semantic_review": node.get("metadata", {}).get("semantic_review")},
        "2018_adm2_counties_in_complete_state_cohort": len(source_counties),
        "2024_tigerline_counties_in_state": len(state_tiger),
        "current_locations_in_complete_parent_cohort": sum(1 for i in ids if feature_state(current[i]["properties"]) == state),
        "all_2018_source_counties_represented": len({f["properties"]["shapeID"] for f in source_counties}) == len(state_tiger),
        "source_adm2_roster_shape_ids": sorted(f["properties"]["shapeID"] for f in source_counties),
        "source_adm1_county_union_area_km2": round(source_union.GetArea() / 1e6, 6),
        "source_adm1_area_km2": round(src_state.GetArea() / 1e6, 6),
        "source_adm2_union_intersection_over_adm1_pct": round(source_union.Intersection(src_state).GetArea() / src_state.GetArea() * 100, 6),
        "source_adm2_union_symdiff_km2": round(source_union.SymDifference(src_state).GetArea() / 1e6, 6),
        "current_parent_cohort_union_area_km2": round(current_union.GetArea() / 1e6, 6),
        "current_parent_union_intersection_over_adm1_pct": round(current_union.Intersection(src_state).GetArea() / src_state.GetArea() * 100, 6),
        "current_parent_union_symdiff_km2": round(current_union.SymDifference(src_state).GetArea() / 1e6, 6),
        "interpretation": "Whole-state parent coverage screen from an ADM1 state polygon and complete ADM2/TIGER county cohorts. Water jurisdiction, federal/tribal parcels and small detached islands require authoritative feature-specific interpretation; this is not a boundary certificate.",
    }

# Official TIGER/Line Places polygons are an exhaustive Census place inventory for these states,
# not a complete inventory of every named settlement or inhabited site.
place_records = []
for state, filename in [("06", "tigerline-2024-ca-places.zip"), ("53", "tigerline-2024-wa-places.zip")]:
    path = "/vsizip/" + str((SOURCE / filename).resolve())
    ds = ogr.Open(path)
    if ds is None:
        raise SystemExit(f"FAIL: cannot open retained Census place source {filename}")
    layer = ds.GetLayer(0)
    for feature in layer:
        geom = feature.GetGeometryRef().Clone()
        if geom.GetSpatialReference() is not None:
            geom.TransformTo(area_srs)
        else:
            geom.AssignSpatialReference(area_srs)
        if not geom.IsValid():
            geom = geom.MakeValid()
        definition = layer.GetLayerDefn()
        fields = {definition.GetFieldDefn(i).GetName(): feature.GetField(definition.GetFieldDefn(i).GetName()) for i in range(definition.GetFieldCount())}
        place_records.append({"state_fips": state, "geoid": fields["GEOID"], "name": fields["NAME"], "classfp": fields.get("CLASSFP"), "lsad": fields.get("LSAD"), "geometry": geom})
    ds = None

places_by_location = {}
places_by_county = {}
for loc_id, geom in current_geom.items():
    props = current[loc_id]["properties"]
    state = feature_state(props)
    matches = []
    env = geom.GetEnvelope()
    for place in place_records:
        if place["state_fips"] != state:
            continue
        pg = place["geometry"]
        pe = pg.GetEnvelope()
        if env[1] < pe[0] or pe[1] < env[0] or env[3] < pe[2] or pe[3] < env[2]:
            continue
        if geom.Intersects(pg):
            matches.append({"geoid": place["geoid"], "name": place["name"], "classfp": place["classfp"], "lsad": place["lsad"]})
    places_by_location[loc_id] = sorted(matches, key=lambda x: (x["name"].casefold(), x["geoid"]))
    metadata = props.get("metadata", {})
    pred_id = loc_id.rsplit(":", 1)[-1] if loc_id.startswith("gb:USA:ADM2:") else metadata["original_id"]
    places_by_county.setdefault(pred_id, {})
    for row in matches:
        places_by_county[pred_id][row["geoid"]] = row

# Exact row-level ancestry from the currently published world index.
def ancestry(loc_id):
    chain = []
    seen = set()
    current_id = loc_id
    while current_id:
        if current_id in seen or current_id not in all_features:
            raise ValueError(f"incomplete/cyclic parent chain for {loc_id} at {current_id}")
        seen.add(current_id)
        q = all_features[current_id]["properties"]
        metadata = q.get("metadata", {})
        level = current_id.split(":")[1] if current_id.startswith("framework:") else "location"
        chain.append({"id": current_id, "name": q.get("name"), "level": level, "parent_id": q.get("parent_id"), "source_id": metadata.get("source_id"), "source_role": metadata.get("source_role"), "administrative_level": metadata.get("administrative_level"), "selection_reason": metadata.get("selection_reason")})
        current_id = q.get("parent_id")
    return chain

land = read_json(HERE / "gshhg-pacific-screen.json")
check(set(land["per_location"]) == set(ids), "GSHHG screen must contain each assigned ID")
assessment = []
physical_ids = [i for i in ids if i.startswith("atlas:physical:")]
for loc_id in ids:
    feature = current[loc_id]
    props = feature["properties"]
    metadata = props.get("metadata", {})
    pred_id = loc_id.rsplit(":", 1)[-1] if loc_id.startswith("gb:USA:ADM2:") else metadata.get("original_id")
    county_source = source2[pred_id]
    state = feature_state(props)
    raw_geom = geojson_geometry(feature["geometry"])
    geom, repaired = project(raw_geom)
    area_stats = admin_stats[pred_id]
    source_role_match = loc_id.startswith("gb:USA:ADM2:") and metadata.get("source_role") == "Counties"
    settlement_rows = places_by_location[loc_id]
    eco_id = int(metadata["source_id"].split(":")[-1]) if metadata.get("source_id", "").startswith("resolve:") else None
    physical_identity = None
    if eco_id is not None:
        eco_feature = eco[eco_id]
        eco_props = eco_feature["properties"]
        physical_identity = {
            "source": "RESOLVE Ecoregions 2017, ArcGIS layer 0",
            "eco_id": eco_id,
            "eco_name": eco_props["ECO_NAME"],
            "biome": eco_props["BIOME_NAME"],
            "realm": eco_props["REALM"],
            "license": eco_props["LICENSE"],
            "administrative_predecessor_id": pred_id,
            "administrative_predecessor_name": county_source["properties"]["shapeName"],
            "source_role": "Ecological ecoregion (natural boundary), not an administrative county or political ownership boundary.",
        }
    role_finding = ("Current metadata says source_role=Counties and uses a county selection rationale, but the cited RESOLVE feature is ecological. The fragment's name and source-member link describe county × ecoregion derivation; they do not make it a county." if eco_id is not None else "Current County role and source membership agree with the pinned geoBoundaries ADM2 feature; 2024 Census TIGER/Line provides the current named county-equivalent cross-check.")
    # Spherical component/ring screen comes from original current coordinates; equal-area geometry is temporary.
    rings = sum(len(poly) for poly in (feature["geometry"]["coordinates"] if feature["geometry"]["type"] == "MultiPolygon" else [feature["geometry"]["coordinates"]]))
    holes = sum(max(0, len(poly) - 1) for poly in (feature["geometry"]["coordinates"] if feature["geometry"]["type"] == "MultiPolygon" else [feature["geometry"]["coordinates"]]))
    census2024 = tiger[(state, county_source["properties"]["shapeName"].casefold())]
    row = {
        "location_id": loc_id,
        "name": props["name"],
        "area": "Pacific",
        "parent_state": "California" if state == "06" else "Washington",
        "full_parent_chain": ancestry(loc_id),
        "current_geometry_screen": {"type": raw_geom.GetGeometryName(), "components": len(feature["geometry"]["coordinates"]), "rings": rings, "interior_rings": holes, "vertices": sum(len(ring) for poly in (feature["geometry"]["coordinates"] if feature["geometry"]["type"] == "MultiPolygon" else [feature["geometry"]["coordinates"]]) for ring in poly), "area_km2_equal_area": round(geom.GetArea() / 1_000_000, 6), "temporary_projected_geometry_repair": repaired},
        "administrative_identity": {"2018_source": "geoBoundaries USA ADM2, Census MAF/TIGER source-declared; Public Domain", "source_feature_id": county_source["properties"]["shapeID"], "source_name": county_source["properties"]["shapeName"], "source_type": county_source["properties"]["shapeType"], "match_kind": "direct exact shapeID and name" if loc_id.startswith("gb:USA:ADM2:") else "predecessor county for a physical ecoregion portion", "tiger_2024": {"geoid": census2024["properties"]["GEOID"], "name": census2024["properties"]["NAME"], "name_lsad": census2024["properties"]["NAMELSAD"], "classfp": census2024["properties"].get("CLASSFP"), "state_fips": state, "county_fips": census2024["properties"]["COUNTYFP"], "aland_m2": int(census2024["properties"]["ALAND"]), "awater_m2": int(census2024["properties"]["AWATER"]), "water_share_pct": round(int(census2024["properties"]["AWATER"]) / max(1, int(census2024["properties"]["ALAND"]) + int(census2024["properties"]["AWATER"])) * 100, 6)}, "whole_predecessor_reconciliation": area_stats},
        "source_role_metadata_review": {"current_source_id": metadata.get("source_id"), "current_source_role": metadata.get("source_role"), "current_administrative_level": metadata.get("administrative_level"), "current_selection_reason": metadata.get("selection_reason"), "source_role_agrees": source_role_match, "finding": role_finding},
        "physical_source_identity": physical_identity,
        "settlement_screen": {"source": "U.S. Census Bureau TIGER/Line Places 2024; incorporated places and Census Designated Places", "place_feature_count_intersecting_current_footprint": len(set(r["geoid"] for r in settlement_rows)), "places": settlement_rows, "interpretation": "Official and reproducible populated-place screen. Places features do not enumerate every settlement, unincorporated named site, household or seasonal/Indigenous community; missing a place polygon is not evidence of no settlement."},
        "physical_land_screen": land["per_location"][loc_id],
        "political_historical_distinction": "County and state identity describes source administrative geography; current sovereignty reference and any historical territorial attribution are separate dated questions. RESOLVE ecoregions describe natural systems and do not establish political ownership.",
        "remainders_islands_disconnected_review": "Source and current polygon component/ring counts are recorded. Census county water/island linework and GSHHG centroids are screening evidence only; they do not certify all coastal/island components, hydrography, federal/tribal jurisdiction, detached land, or complete administrative remainders.",
        "decision": "correction_needed" if eco_id is not None else "justified",
        "decision_basis": "The four physical portions are unambiguously linked to four named RESOLVE ecoregions and a San Bernardino County predecessor, but their declared administrative role and selection rationale are inconsistent with the cited ecology source." if eco_id is not None else "The location has a unique 2018 Census-sourced geoBoundaries County ADM2 ID/name, exact 2024 TIGER/Line state/name/GEOID counterpart, a complete published parent chain and a matching California/Washington state role. Footprint, settlement and island screens remain separately qualified and do not certify the full region.",
        "unresolved": ["Current-to-2018 and current-to-2024 area differences are screening results; resolve large water/coastline or detached-component discrepancies from authoritative county/state boundary evidence before proposing line changes.", "Census Places is a populated-place layer, not a complete settlement inventory.", "GSHHG point and polygon-centroid screens do not certify every island, coastline, lake, detached territory, or physical land component."],
    }
    assessment.append(row)

assessment.sort(key=lambda row: row["location_id"])
counts = {value: sum(1 for row in assessment if row["decision"] == value) for value in ["justified", "correction_needed", "insufficient_evidence"]}
source_shape_ids = {i.rsplit(":", 1)[-1] for i in ids if i.startswith("gb:USA:ADM2:")}
source_shape_ids.add("52423323B23069932539838")
check(len(source_shape_ids) == 97 and len(source_shape_ids.intersection(source2)) == 97, "2018 ADM2 roster crosswalk incomplete")
check(sum(i.startswith("gb:USA:ADM2:") for i in ids) == 96 and len(physical_ids) == 4, "current cohort split mismatch")
check(len(tiger) == len(tiger_data["features"]), "duplicate TIGER/Line state/name keys")

report = {
    "issue": 487,
    "date_utc": "2026-10-03",
    "scope": {"count": len(ids), "ids_sha256": hashlib.sha256(("\n".join(sorted(ids)) + "\n").encode()).hexdigest(), "region_id": scope["region_id"], "region_release": scope["release"], "area": "Pacific", "area_count": 191, "assigned_count": 100, "state_counts": {"Washington": 39, "California": 61}},
    "source_accounting": {"geoBoundaries_USA_ADM2_2018_features": len(source2_data["features"]), "assigned_2018_source_counties": 97, "direct_current_county_rows": 96, "predecessor_counties_represented_by_physical_fragments": ["San Bernardino"], "physical_fragments": 4, "unaccounted_source_counties_in_full_state_cohort": 0, "tiger_2024_all_assigned_state_counties": 97, "tiger_2024_neighbor_county_features": len(tiger_data["features"]), "tiger_2024_places_features": len(place_records)},
    "complete_state_parent_cohorts": state_parent_audit,
    "decision_counts": counts,
    "physical_summary": {"gshhg_screen_scope_count": land["scope_count"], "gshhg_points_on_level1_land": sum(bool(x["representative_point_in_level1_land"]) for x in land["per_location"].values()), "gshhg_land_centroid_hits": sum(x["level1_centroid_hits"] for x in land["per_location"].values()), "gshhg_ids_with_land_centroid_hits": sum(bool(x["level1_centroid_hits"]) for x in land["per_location"].values()), "four_eco_ids": [422, 424, 433, 435]},
    "limitations": ["Screen evidence does not certify the entire Western North America region, complete shorelines/island inventories, every named settlement, inland waters, or historical ownership.", "This bottom-up packet assesses 100 assigned subjects only; published parent unions remain the shared baseline.", "No live hierarchy, geometry, certificate, source index, application or claim was changed."],
    "locations": assessment,
}
(HERE / "assessment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Reproducible 2018-admin × 2017-ecoregion comparison for all four current fragments.
derived = []
for loc_id in physical_ids:
    row = next(row for row in assessment if row["location_id"] == loc_id)
    pred_id = current[loc_id]["properties"]["metadata"]["original_id"]
    eco_id = int(current[loc_id]["properties"]["metadata"]["source_id"].split(":")[-1])
    admin_g = source_geom(source2[pred_id])
    eco_g = source_geom(eco[eco_id])
    expected = admin_g.Intersection(eco_g)
    observed = current_geom[loc_id]
    area = expected.GetArea()
    expected_observed = expected.Intersection(observed).GetArea()
    derived.append({"location_id": loc_id, "name": row["name"], "predecessor_shape_id": pred_id, "eco_id": eco_id, "eco_name": eco[eco_id]["properties"]["ECO_NAME"], "expected_area_km2": round(area / 1e6, 6), "current_area_km2": round(observed.GetArea() / 1e6, 6), "current_intersection_over_expected_pct": round(expected_observed / area * 100 if area else 0, 6), "symmetric_difference_km2": round(expected.SymDifference(observed).GetArea() / 1e6, 6), "raw_inputs_preserved": True, "temporary_projected_makevalid": True})
parent_union = source_geom(source2["52423323B23069932539838"])
portion_union = None
for row in derived:
    part = current_geom[row["location_id"]]
    portion_union = part.Clone() if portion_union is None else portion_union.Union(part)
derived_report = {"method": "Transform source and current shapes temporarily to EPSG:5070 equal-area coordinates, run GEOS MakeValid only where reprojection introduced invalid topology, then compare each exact San Bernardino ADM2 × RESOLVE ecoregion intersection with its assigned current atlas fragment. Original bytes and baseline geometries remain unmodified.", "fragment_count": len(derived), "fragments": derived, "parent_union": {"predecessor_shape_id": "52423323B23069932539838", "predecessor_area_km2": round(parent_union.GetArea() / 1e6, 6), "current_four_fragment_union_km2": round(portion_union.GetArea() / 1e6, 6), "intersection_over_predecessor_pct": round(parent_union.Intersection(portion_union).GetArea() / parent_union.GetArea() * 100, 6), "symmetric_difference_km2": round(parent_union.SymDifference(portion_union).GetArea() / 1e6, 6)}, "interpretation": "An ecoregion overlay tests the declared derivation, not a political boundary or county classification. Measured differences require scale, shoreline and precision review; they do not support an uncoordinated line relocation."}
(HERE / "derived-portion-audit.json").write_text(json.dumps(derived_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"locations": len(assessment), "decisions": counts, "place_features": len(place_records), "source_counties": len(admin_groups), "physical_fragments": len(physical_ids), "derived_metrics": len(derived)}, indent=2))
