#!/usr/bin/env python3
"""Reproduce the 17 named county-pair screens against immutable parent inputs.
Only reads repository sources and writes findings.json inside this issue's owned path.
"""
import gzip, hashlib, json
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.geometry import Polygon
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARENT = ROOT / "data/regional-review/regional-review-2178b81fa886cfb6"
SRC = PARENT / "sources"
SCOPE = json.loads((HERE / "scope.json").read_text())
ISSUE = json.loads((HERE / "issue-metadata.json").read_text())
if ISSUE.get("issue_number") != SCOPE["issue"] or hashlib.sha256(ISSUE["body"].encode()).hexdigest() != SCOPE["issue_body_sha256"]:
    raise SystemExit("actual issue identity/body hash differs from pinned scope")
if ISSUE.get("state") != "open" or "type:geography" not in [x["name"] for x in ISSUE.get("labels", [])]:
    raise SystemExit("actual issue metadata no longer satisfies open geography scope")

def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

# Explicit GIS axis order: GeoJSON coordinates are longitude, latitude.
project = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True).transform
project_nad83 = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True).transform
def geom(feature):
    g = shape(feature["geometry"])
    if not g.is_valid:
        raise ValueError("invalid input geometry; no repair is performed")
    return transform(project, g)
def geom_nad83(feature):
    g = shape(feature["geometry"])
    if not g.is_valid:
        raise ValueError("invalid official 2018 TIGER geometry; no repair is performed")
    return transform(project_nad83, g)

# Physical-only screen against the 79 retained full-resolution GSHHG level-1 land
# records from the parent packet. This source is not a legal county line authority.
gshhg_path = PARENT / "sources/gshhg-pacific-land-candidates.bin.gz"
gshhg_bytes = gzip.open(gshhg_path, "rb").read()
land_parts = []
pos = 0
while pos < len(gshhg_bytes):
    lid, n, flag, west, east, south, north, area, area_full, container, ancestor = struct.unpack_from(">IIIiiiiIIii", gshhg_bytes, pos)
    if (flag & 255) == 1:
        coords = []
        for k in range(n):
            x, y = struct.unpack_from(">ii", gshhg_bytes, pos + 44 + k * 8)
            lon = x / 1_000_000
            if lon > 180: lon -= 360
            coords.append((lon, y / 1_000_000))
        poly = Polygon(coords)
        if not poly.is_valid:
            raise ValueError(f"invalid retained GSHHG ring {lid}; no repair is performed")
        land_parts.append(transform(project, poly))
    pos += 44 + n * 8
if pos != len(gshhg_bytes) or len(land_parts) != 79:
    raise ValueError(f"GSHHG parse control failed: offset={pos}, level-1 candidates={len(land_parts)}")
gshhg_land = unary_union(land_parts)

def physical_mask_metrics(a, b):
    boundary = a.boundary.intersection(b.boundary)
    length = boundary.length
    land_length = boundary.intersection(gshhg_land).length
    outside_length = boundary.difference(gshhg_land).length
    return {"shared_boundary_m": round(length, 3),
            "within_retained_GSHHG_level1_land_m": round(land_length, 3),
            "outside_retained_GSHHG_level1_land_mask_m": round(outside_length, 3),
            "mask_coverage_fraction": round(land_length / length, 6) if length else None}

old_features = load(SRC / "geoboundaries-USA-ADM2-2018.geojson.gz")["features"]
tiger_features = load(SRC / "tigerline-2024-western-county-neighbors.geojson.gz")["features"]
tiger2018_path = HERE / "tigerline-2018-assigned-counties.geojson.gz"
tiger2018_features = load(tiger2018_path)["features"]
tiger2018 = {f["properties"]["GEOID"]: f for f in tiger2018_features}
old = {f["properties"]["shapeID"]: f for f in old_features}
tiger = {f["properties"]["GEOID"]: f for f in tiger_features}
current_geo = {}
for part in json.loads((ROOT / "data/world-index.json").read_text())["parts"]:
    doc = json.loads((ROOT / "data" / part).read_text())
    current_geo.update((f["properties"]["id"], f) for f in doc["features"])
current = {i: current_geo[i] for i in SCOPE["member_location_ids"]}
if len(current) != 16:
    raise SystemExit(f"current subject scope mismatch: {len(current)} != 16")

# Verify whole-file hashes and bytes from the cited source registry before analysis.
def assert_source(path, byte_count, digest):
    if not path.exists() or path.stat().st_size != byte_count or sha(path) != digest:
        raise SystemExit(f"source integrity mismatch: {path}")
assert_source(tiger2018_path, 255129, "1a168f18afefc8c16902ef894aa7b9c6fc560287bedd974c732d38f1bb2c5d9e")
assert_source(SRC / "geoboundaries-USA-ADM2-2018.geojson.gz", 3264221, "f42991ac50eb7d6fab5ae50de404e4d198957316aec3035f8018bdd2bca8044a")
assert_source(SRC / "tigerline-2024-western-county-neighbors.geojson.gz", 5850604, "b4da7a5c442821e798c71945ba63f5ca279e18e1dca0355e714b495e2c294180")
assert_source(PARENT / "sources/gshhg-pacific-land-candidates.bin.gz", 5122132, "6e90ac5c64fd3fe992363fee2870ee582213e6ba51c20049606e934ccb69425a")
if sha(ROOT / "data/world-index.json") != "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03":
    raise SystemExit("pinned world-index hash mismatch")

# Make source-vintage counterparts explicit by GEOID. Legacy shapeIDs match exact
# current `gb:USA:ADM2:<shapeID>` IDs; 41007 is added through dependency #486.
current_by_shape = {}
for ident, feat in current.items():
    sid = ident.rsplit(":", 1)[-1]
    if sid in old:
        current_by_shape.setdefault(sid, []).append(feat)
names = {g: f["properties"]["NAMELSAD"] for g, f in tiger.items()}
def shared(a, b):
    return float(a.boundary.intersection(b.boundary).length)
def metric(srcgeom, a, b):
    if a is None or b is None:
        return None
    x, y = geom(a), geom(b)
    return {"shared_boundary_m": round(shared(x, y), 3),
            "overlap_km2": round(x.intersection(y).area / 1e6, 6),
            "gap_m": round(x.distance(y), 3)}

def find_old(geoid):
    tf = tiger[geoid]
    nm = tf["properties"]["NAME"].casefold()
    candidates = [f for f in old_features if f["properties"]["shapeName"].casefold() == nm]
    # There are same-name counties across states; disambiguate using county centroid
    # containment/overlap with source-vintage TIGER polygon.
    tg = geom(tf)
    ranked = sorted(((geom(f).intersection(tg).area, f) for f in candidates), key=lambda x: x[0], reverse=True)
    if not ranked or ranked[0][0] == 0 or (len(ranked) > 1 and ranked[0][0] == ranked[1][0]):
        raise ValueError(f"cannot uniquely crosswalk {geoid} {tf['properties']['NAMELSAD']}")
    return ranked[0][1]

def find_current(geoid):
    old_id = find_old(geoid)["properties"]["shapeID"]
    pieces = current_by_shape.get(old_id, [])
    return pieces or None

rows = []
for ga, gb in SCOPE["pair_geoid_leads"]:
    fa, fb = tiger[ga], tiger[gb]
    oa, ob = find_old(ga), find_old(gb)
    ca, cb = find_current(ga), find_current(gb)
    ca_union = None if not ca else ca[0] if len(ca) == 1 else {"geometry": {"type": "MultiPolygon", "coordinates": []}}
    # Current members for this issue are individual assigned county IDs; merge only
    # if multiple pieces exist, using Shapely. (No output geometry is retained.)
    from shapely.ops import unary_union
    if ca: ca_union = unary_union([geom(x) for x in ca])
    if cb: cb_union = unary_union([geom(x) for x in cb])
    def pairmetric(x, y):
        if x is None or y is None: return None
        return {"shared_boundary_m": round(float(x.boundary.intersection(y.boundary).length), 3),
                "overlap_km2": round(x.intersection(y).area/1e6, 6),
                "gap_m": round(x.distance(y), 3)}
    A, B = geom(oa), geom(ob)
    T, U = geom(fa), geom(fb)
    rows.append({
        "geoids": [ga, gb],
        "counties": [fa["properties"]["NAMELSAD"], fb["properties"]["NAMELSAD"]],
        "states": [fa["properties"]["STATEFP"], fb["properties"]["STATEFP"]],
        "member_location_ids": [f"gb:USA:ADM2:{oa['properties']['shapeID']}", f"gb:USA:ADM2:{ob['properties']['shapeID']}"],
        "2018_geoBoundaries": pairmetric(A, B),
        "2018_official_Census_TIGER_Line": pairmetric(geom_nad83(tiger2018[ga]), geom_nad83(tiger2018[gb])),
        "2024_TIGER_Line": pairmetric(T, U),
        "current_Atlas": pairmetric(ca_union, cb_union),
        "2024_attributes": [{k: fa["properties"].get(k) for k in ("ALAND", "AWATER", "GEOID", "NAMELSAD")},
                            {k: fb["properties"].get(k) for k in ("ALAND", "AWATER", "GEOID", "NAMELSAD")}],
        "physical_land_mask_screen": {
            "geoBoundaries_2018": physical_mask_metrics(A, B),
            "official_Census_TIGER_2018": physical_mask_metrics(geom_nad83(tiger2018[ga]), geom_nad83(tiger2018[gb])),
            "Census_TIGER_2024": physical_mask_metrics(T, U),
            "current_Atlas": physical_mask_metrics(ca_union, cb_union) if ca_union is not None and cb_union is not None else None
        },
        "interpretation": "Geometry contact/gap is a screen. ALAND/AWATER are county totals, not edge-specific land/water attribution or a legal marine-boundary determination."
    })

# Positive control: parse the user-authored issue's 17 numeric reproduction leads and
# require the independently computed pair metrics to agree to its stated millimetre.
issue = json.loads((HERE / "issue-metadata.json").read_text())
import re
lead_pattern = re.compile(r"^- .*?\(`(\d{5})`\) ↔ .*?\(`(\d{5})`\): 2018 shared line ([0-9.]+) m; TIGER 2024 shared line ([0-9.]+) m; current Atlas shared line ([0-9.]+) m and polygon gap ([0-9.]+) m\.$", re.M)
leads = {(m.group(1), m.group(2)): tuple(map(float, m.groups()[2:])) for m in lead_pattern.finditer(issue["body"])}
if len(leads) != 17:
    raise SystemExit(f"issue lead parse control failed: found {len(leads)}, expected 17")
for row in rows:
    key = tuple(row["geoids"])
    expected = leads.get(key)
    actual = (row["2018_geoBoundaries"]["shared_boundary_m"], row["2024_TIGER_Line"]["shared_boundary_m"], row["current_Atlas"]["shared_boundary_m"], row["current_Atlas"]["gap_m"])
    if expected is None or any(abs(a - e) > 0.0005 for a, e in zip(actual, expected)):
        raise SystemExit(f"issue positive control mismatch {key}: computed={actual} expected={expected}")
# Scope negative control is the final exact 17-pair/16-subject assertion below;
# dropping any issue lead or member makes the reproduction fail closed.

parent = json.loads((PARENT / "neighbor-screen.json").read_text())
assert parent["source_scope"]["assigned_predecessor_counties"] == 97
assert parent["assigned_internal_predecessor_edges"]["geoBoundaries_2018"] == 219
assert parent["assigned_internal_predecessor_edges"]["TIGER_2024"] == 234
assert parent["assigned_internal_predecessor_edges"]["current_Atlas"] == 218
subjects = {}
for i, row in enumerate(rows, 1):
    for j, geoid in enumerate(row["geoids"]):
        loc_id = row["member_location_ids"][j]
        tf = tiger[geoid]
        item = subjects.setdefault(geoid, {
            "location_id": loc_id,
            "county": tf["properties"]["NAMELSAD"],
            "statefp": tf["properties"]["STATEFP"],
            "tiger_2024_aland_m2": tf["properties"].get("ALAND"),
            "tiger_2024_awater_m2": tf["properties"].get("AWATER"),
            "pair_indices": [],
            "assessment": "Assigned county-equivalent subject assessed in every listed candidate edge. TIGER county-level land/water area and source contacts are recorded; these totals do not identify the material on any individual shared segment. No legal marine line or ownership conclusion is inferred."
        })
        if item["location_id"] != loc_id:
            raise ValueError(f"crosswalk changed for {geoid}: {loc_id}")
        item["pair_indices"].append(i)
if set(item["location_id"] for item in subjects.values()) != set(SCOPE["member_location_ids"]):
    raise SystemExit("issue pair roster does not account for exactly all 16 assigned location IDs")
edge_sets = {}
for label, field in (("geoBoundaries_2018", "2018_geoBoundaries"), ("Census_TIGER_2018", "2018_official_Census_TIGER_Line"), ("TIGER_2024", "2024_TIGER_Line"), ("current_Atlas", "current_Atlas")):
    edges = sorted([row["geoids"] for row in rows if row[field] and row[field]["shared_boundary_m"] > 1.0])
    payload = json.dumps(edges, separators=(",", ":")).encode()
    edge_sets[label] = {"threshold_m_strictly_greater_than": 1.0, "count": len(edges), "pairs": edges, "canonical_json_sha256": hashlib.sha256(payload).hexdigest()}
findings = {
    "issue": 598,
    "baseline_commit": SCOPE["base_commit"],
    "method": {
        "projection": "EPSG:5070, USA Contiguous Albers Equal Area",
        "axis_order": "GeoJSON x=longitude, y=latitude; pyproj Transformer always_xy=True",
        "edge_rule": "shared length of polygon boundary intersection; exact reported lengths, parent graph used >1m screen threshold",
        "geometry_repair": "none; invalid geometries fail closed",
        "physical_mask_screen": "Retained GSHHG 2.3.7 level-1 land records in EPSG:4326 transformed with always_xy=True to EPSG:5070; exact line-in-mask length and outside-mask length. Outside the retained land mask is not independently proven water or legal county line.",
        "software": {"pyproj": "3.7.2", "shapely": "2.1.2", "direct_2018_extract": "pyshp 2.3.1; deterministic sorted-key UTF-8 JSON plus gzip level 9, mtime 0"},
        "additional_2018_source": "Census TIGER/Line 2018 county subset in NAD83 (EPSG:4269), transformed to EPSG:5070 with always_xy=True; distinct comparison from the geoBoundaries 2018 derivative",
        "scope": "exactly the issue's 17 named county GEOID pairs; parent packet's 97-county graph totals independently pinned as comparator"
    },
    "inputs": {str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in [
        SRC / "geoboundaries-USA-ADM2-2018.geojson.gz",
        SRC / "tigerline-2024-western-county-neighbors.geojson.gz",
        HERE / "scope.json",
        PARENT / "neighbor-screen.json",
        PARENT / "scope.json",
        ROOT / "data/regional-review/regional-review-93f8f3bee8e205be/scope.json",
        HERE / "issue-metadata.json",
        ROOT / "data/world-index.json"]},
    "whole_parent_graph_counts": {"2018": 219, "2024": 234, "current": 218,
        "scope": "97 CA/WA county predecessors; copied parent totals and guarded by assertions in this script; full edge arrays are in the pinned parent neighbor-screen.json"},
    "subject_count": len(subjects),
    "subjects": subjects,
    "pair_count": len(rows),
    "alameda_san_francisco_source_vintage_resolution": {
        "geoBoundaries_2018_shared_m": next(r for r in rows if r["geoids"] == ["06001", "06075"])["2018_geoBoundaries"]["shared_boundary_m"],
        "direct_Census_TIGER_2018_shared_m": next(r for r in rows if r["geoids"] == ["06001", "06075"])["2018_official_Census_TIGER_Line"]["shared_boundary_m"],
        "Census_TIGER_2024_shared_m": next(r for r in rows if r["geoids"] == ["06001", "06075"])["2024_TIGER_Line"]["shared_boundary_m"],
        "current_Atlas_shared_m": next(r for r in rows if r["geoids"] == ["06001", "06075"])["current_Atlas"]["shared_boundary_m"],
        "finding": "Direct official Census 2018 and 2024 county polygons agree at the reported shared-edge length; the 2018 geoBoundaries derivative materially differs. This resolves the apparent vintage-change lead as a source-representation discrepancy in that derivative, not evidence of a 2018-to-2024 county-line change. Current Atlas still has no contact; this does not itself justify a correction because the 2024 edge is water-dominant in the dated physical land-mask screen."
    },
    "pair_edge_sets_within_issue_scope": edge_sets,
    "pairs": rows,
    "global_limits": [
        "This reproduction establishes geometric contacts/gaps and the official Census county ALAND/AWATER totals only.",
        "County totals cannot establish that a particular shared segment lies in water.",
        "GSHHG 2.3.7 is a dated physical coastline screen only; its retained 79 level-1 candidate records do not constitute a complete hydrographic, inland-water or official legal marine-boundary source. Outside-mask length can include source-scale mismatch, unrepresented land, inland water or true marine water.",
        "Neither a geometric contact nor a source county water polygon is proof of a legally controlling county marine boundary.",
        "No federal county-by-county legal marine-boundary line source was identified in the retained parent packet; pair-level land/water attribution is unresolved pending authoritative coastal/county line evidence.",
        "Clatsop–Pacific is cross-state and requires the #486/#487 owners and regional integrator to assess the shared issue; no independent boundary correction is proposed."
    ]
}
if len(rows) != 17 or len(subjects) != 16:
    raise SystemExit(f"scope mismatch: {len(rows)} pairs / {len(subjects)} subjects; expected 17 / 16")
(HERE / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
print(json.dumps({"pairs": len(rows), "counts": findings["whole_parent_graph_counts"], "output": str(HERE / "findings.json")}, indent=2))
