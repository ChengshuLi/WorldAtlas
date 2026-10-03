#!/usr/bin/env /usr/bin/python3
"""Compare full state-county neighbor graphs with 2018, 2024 and current footprints."""
import gzip
import json
from pathlib import Path
from osgeo import ogr, osr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = HERE / "sources"
ogr.UseExceptions()

def load(path):
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    return json.loads(path.read_text())

scope = load(HERE / "scope.json")
ids = set(scope["member_location_ids"])
geo = {}
for part in load(ROOT / "data/world-index.json")["parts"]:
    for f in load(ROOT / "data" / part)["features"]:
        geo[f["properties"]["id"]] = f
current = {i: geo[i] for i in ids}
old = {f["properties"]["shapeID"]: f for f in load(SRC / "geoboundaries-USA-ADM2-2018.geojson.gz")["features"]}
tiger = load(SRC / "tigerline-2024-western-county-neighbors.geojson.gz")["features"]
state_names = {"06": "California", "53": "Washington", "41": "Oregon", "32": "Nevada", "04": "Arizona", "16": "Idaho"}

src = osr.SpatialReference(); src.ImportFromEPSG(4326); src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
aea = osr.SpatialReference(); aea.ImportFromEPSG(5070); aea.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
tx = osr.CoordinateTransformation(src, aea)

def shape(obj):
    g = ogr.CreateGeometryFromJson(json.dumps(obj, separators=(",", ":")))
    g.AssignSpatialReference(src)
    g.Transform(tx)
    if not g.IsValid():
        g = g.MakeValid()
    if g is None or not g.IsValid():
        raise ValueError("temporary projected geometry repair failed")
    return g

def cross_state(f):
    # TIGER FIPS is embedded in the authoritative source feature.
    return f["properties"]["STATEFP"]

old_by_state_name = {}
for f in old.values():
    old_by_state_name.setdefault(f["properties"]["shapeName"].casefold(), []).append(f)

# Use full county source features in six states to include every plausible domestic
# neighbor along the assigned CA/WA boundaries; only CA/WA are owned scope.
tiger_nodes = {}
for tf in tiger:
    state = cross_state(tf)
    name = tf["properties"]["NAME"]
    candidates = old_by_state_name.get(name.casefold(), [])
    tg = shape(tf["geometry"])
    ranked = sorted(((shape(c["geometry"]).Intersection(tg).GetArea(), c) for c in candidates), key=lambda x: x[0], reverse=True)
    if not ranked or ranked[0][0] <= 0:
        continue
    old_feature = ranked[0][1]
    sid = old_feature["properties"]["shapeID"]
    key = (state, sid)
    tiger_nodes[key] = {"key": key, "state": state, "state_name": state_names[state], "name": name, "geoid": tf["properties"]["GEOID"], "shape_id": sid, "geom": tg, "old_geom": shape(old_feature["geometry"])}

# Map each published USA county source ID to its current footprint, grouping the four
# San Bernardino physical portions back to their original administrative predecessor.
current_admin = {}
for loc_id, f in geo.items():
    props = f["properties"]
    meta = props.get("metadata", {})
    sid = loc_id.rsplit(":", 1)[-1] if loc_id.startswith("gb:USA:ADM2:") else meta.get("original_id") if loc_id.startswith("atlas:physical:") else None
    if sid not in old:
        continue
    geom = shape(f["geometry"])
    current_admin.setdefault(sid, []).append((loc_id, geom))
for sid, pieces in list(current_admin.items()):
    g = pieces[0][1].Clone()
    for _, p in pieces[1:]:
        g = g.Union(p)
    current_admin[sid] = g

assigned = {i.rsplit(":", 1)[-1] if i.startswith("gb:USA:ADM2:") else current[i]["properties"].get("metadata", {}).get("original_id") for i in ids}
missing_current = []
nodes = {}
for key, item in tiger_nodes.items():
    sid = item["shape_id"]
    if sid in current_admin:
        item["current_geom"] = current_admin[sid]
    else:
        item["current_geom"] = None
        if key[0] in {"06", "53"}:
            missing_current.append({"state": item["state_name"], "name": item["name"], "shape_id": sid, "geoid": item["geoid"]})
    nodes[key] = item

def bounds(g):
    return g.GetEnvelope() # minx, maxx, miny, maxy

def bbox_overlap(a, b):
    x1, x2, y1, y2 = a
    u1, u2, v1, v2 = b
    return not (x2 < u1 or u2 < x1 or y2 < v1 or v2 < y1)

def line_length(geom):
    name = geom.GetGeometryName().upper()
    if name in {"LINESTRING", "LINEARRING", "CIRCULARSTRING", "COMPOUNDCURVE"}:
        return geom.Length()
    if name in {"MULTILINESTRING", "GEOMETRYCOLLECTION", "MULTICURVE"}:
        return sum(line_length(geom.GetGeometryRef(i)) for i in range(geom.GetGeometryCount()))
    return 0.0

def contact_pairs(field):
    pairs = []
    target_nodes = [n for n in nodes.values() if n["shape_id"] in assigned and n[field] is not None]
    compare_nodes = list(nodes.values())
    for a in target_nodes:
        ga = a[field]
        ba = bounds(ga)
        for b in compare_nodes:
            if a["key"] == b["key"] or b[field] is None or not bbox_overlap(ba, bounds(b[field])):
                continue
            boundary = ga.Boundary().Intersection(b[field].Boundary())
            shared_m = line_length(boundary)
            if shared_m > 1.0:
                pairs.append((a["shape_id"], b["shape_id"]))
    return set(tuple(sorted(pair)) for pair in pairs)

old_edges = contact_pairs("old_geom")
tiger_edges = contact_pairs("geom")
current_edges = contact_pairs("current_geom")
def edge_rows(edges):
    by_sid = {n["shape_id"]: n for n in nodes.values()}
    out = []
    for a, b in sorted(edges):
        left, right = by_sid[a], by_sid[b]
        out.append({"left": {"state": left["state_name"], "name": left["name"], "tiger_geoid": left["geoid"], "shape_id": a}, "right": {"state": right["state_name"], "name": right["name"], "tiger_geoid": right["geoid"], "shape_id": b}, "cross_state": left["state"] != right["state"]})
    return out

def edge_metrics(edges):
    by_sid = {n["shape_id"]: n for n in nodes.values()}
    out = []
    for a, b in sorted(edges):
        left, right = by_sid[a], by_sid[b]
        item = {"left": {"state": left["state_name"], "name": left["name"], "tiger_geoid": left["geoid"], "shape_id": a}, "right": {"state": right["state_name"], "name": right["name"], "tiger_geoid": right["geoid"], "shape_id": b}}
        for label, field in [("geoboundaries_2018", "old_geom"), ("tigerline_2024", "geom"), ("current_atlas", "current_geom")]:
            ga, gb = left[field], right[field]
            if ga is None or gb is None:
                item[label] = None
                continue
            item[label] = {"shared_boundary_m": round(line_length(ga.Boundary().Intersection(gb.Boundary())), 3), "polygon_overlap_km2": round(ga.Intersection(gb).GetArea() / 1e6, 6), "polygon_distance_m": round(ga.Distance(gb), 3)}
        out.append(item)
    return out

def scoped_edges(edges):
    return {pair for pair in edges if pair[0] in assigned and pair[1] in assigned}

old_internal = scoped_edges(old_edges)
tiger_internal = scoped_edges(tiger_edges)
current_internal = scoped_edges(current_edges)
old_current_missing = old_edges - current_edges
current_old_extra = current_edges - old_edges
tiger_current_missing = tiger_edges - current_edges
current_tiger_extra = current_edges - tiger_edges
source_vintage_new_pairs = tiger_edges - old_edges
source_vintage_old_pairs = old_edges - tiger_edges
graph_difference_rows = edge_metrics(old_current_missing | current_old_extra | tiger_current_missing | current_tiger_extra)

# Exact current location-level graph records the four ecoregion shards and every
# current county seam independently of the coarser 97 predecessor-county graph.
location_shapes = {i: shape(f["geometry"]) for i, f in current.items()}
location_edges = []
loc_items = sorted(location_shapes.items())
for ix, (a_id, a_geom) in enumerate(loc_items):
    for b_id, b_geom in loc_items[ix + 1:]:
        if not bbox_overlap(bounds(a_geom), bounds(b_geom)):
            continue
        length = line_length(a_geom.Boundary().Intersection(b_geom.Boundary()))
        if length > 1.0:
            location_edges.append({"left_id": a_id, "right_id": b_id, "shared_boundary_m_screen": round(length, 3)})

report = {
    "issue": 487,
    "method": {"basis": "Exact shared boundary-line length in temporary EPSG:5070 projection, with a 1 m threshold; compare every assigned California/Washington county predecessor against all six-state source candidates (California, Washington, Oregon, Nevada, Arizona, Idaho).", "sources": ["geoBoundaries USA ADM2 2018 (Census MAF/TIGER-derived, whole USA source)", "U.S. Census Bureau TIGER/Line county 2024 (CA, WA and four contiguous domestic neighbor states)", "published current Atlas geometry from the pinned scope and main index"], "caveats": ["An exact current contact is a geometric screening result, not proof of legal line placement.", "The comparison does not imply a boundary change or a political ownership conclusion.", "This audit covers domestic adjacent county features in the six-state comparison. International boundary evidence is handled separately as an explicit unresolved source requirement."]},
    "source_scope": {"assigned_predecessor_counties": len(assigned), "six_state_tiger_counties": len(tiger_nodes), "assigned_county_current_footprints_missing": missing_current},
    "assigned_internal_predecessor_edges": {"geoBoundaries_2018": len(old_internal), "TIGER_2024": len(tiger_internal), "current_Atlas": len(current_internal), "old_2018_missing_current": edge_rows(old_internal - current_internal), "current_extra_vs_2018": edge_rows(current_internal - old_internal), "tiger_2024_missing_current": edge_rows(tiger_internal - current_internal), "current_extra_vs_tiger_2024": edge_rows(current_internal - tiger_internal)},
    "all_assigned_county_external_contacts": {"geoBoundaries_2018": edge_rows(old_edges - old_internal), "TIGER_2024": edge_rows(tiger_edges - tiger_internal), "current_Atlas": edge_rows(current_edges - current_internal), "old_2018_pair_graph_difference_count": len(old_current_missing) + len(current_old_extra), "missing_current_vs_2018": edge_rows(old_current_missing), "extra_current_vs_2018": edge_rows(current_old_extra), "tiger_2024_pair_graph_difference_count": len(tiger_current_missing) + len(current_tiger_extra), "missing_current_vs_tiger_2024": edge_rows(tiger_current_missing), "extra_current_vs_tiger_2024": edge_rows(current_tiger_extra)},
    "source_vintage_pair_set_differences": {"added_in_TIGER_2024_vs_geoBoundaries_2018": edge_metrics(source_vintage_new_pairs), "present_in_geoBoundaries_2018_missing_TIGER_2024": edge_metrics(source_vintage_old_pairs)},
    "current_pair_graph_difference_metrics": graph_difference_rows,
    "current_assigned_location_edges": location_edges,
    "current_location_pair_count": len(location_edges),
    "interpretation": "A difference between named source graph sets identifies an exact comparison lead. It does not justify changing shared county boundaries without source/scale and neighboring-owner review. The four San Bernardino portions are coarsened to their original county only for county-neighbor comparison; their internal ecoregion seams remain in current_assigned_location_edges.",
}
(HERE / "neighbor-screen.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"assigned_counties": len(assigned), "six_state_counties": len(nodes), "internal_edges": {"2018": len(old_internal), "2024": len(tiger_internal), "current": len(current_internal)}, "external_edges": {"2018": len(old_edges - old_internal), "2024": len(tiger_edges - tiger_internal), "current": len(current_edges - current_internal)}, "current_locations": len(current), "current_location_edges": len(location_edges), "graph_diff": {"old_missing": len(old_current_missing), "current_extra": len(current_old_extra), "tiger_missing": len(tiger_current_missing), "current_extra_tiger": len(current_tiger_extra)}}, indent=2))
