#!/usr/bin/env python3
"""Reproduce scoped membership, source-vintage, parent, and geometry diagnostics.

No network access. Run from repo root with the pinned repository requirements.
Writes assessment files only in this issue-owned directory.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import csv, gzip, json, re
from pathlib import Path
import unicodedata
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SOURCE = ROOT / "sources" / "geoboundaries-9469f09"
LISGIS = ROOT / "sources" / "lisgis-2022"
OUT = ROOT / "reproduction"
OUT.mkdir(exist_ok=True)
SCOPE = json.loads((ROOT / "scope.json").read_text(encoding="utf-8"))
AREAS = {x["id"]: x for x in SCOPE["area_scopes"]}
PROVINCES = {x["id"]: x for x in SCOPE["province_scopes"]}
IDS = SCOPE["member_location_ids"]
if len(IDS) != SCOPE["location_count"] or len(IDS) != len(set(IDS)):
    raise SystemExit("issue scope roster count/uniqueness mismatch")
if sha256("\n".join(sorted(IDS)).encode()).hexdigest() != SCOPE["member_location_ids_sha256"]:
    raise SystemExit("issue scope roster digest mismatch")

review = {}
for p in sorted((REPO / "data").glob("world-review-locations-*.json.gz")):
    for row in json.loads(gzip.decompress(p.read_bytes())):
        if row["id"] in set(IDS):
            if row["id"] in review:
                raise SystemExit("duplicate retained inspection identity: " + row["id"])
            review[row["id"]] = row
if set(review) != set(IDS):
    raise SystemExit(f"retained prior inspection differs: found {len(review)} of {len(IDS)} issue subjects")

project = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform

def norm(value):
    value = unicodedata.normalize("NFKD", value or "").casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    value = re.sub(r"\b(region|region administrative|adm|province|county)\b", " ", value)
    return " ".join(value.split())

def load_collection(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("type") != "FeatureCollection":
        raise SystemExit("not a GeoJSON FeatureCollection: " + str(path))
    return d["features"]

features, metadata, parents, parent_metadata, countries, country_metadata = {}, {}, {}, {}, {}, {}
SHARED_PACKET = REPO / "data/regional-review/regional-review-97ccc950999ad631"
SHARED_REGISTER = json.loads((SHARED_PACKET / "sources/register.json").read_text(encoding="utf-8"))
LBR_REGISTER = next(x for x in SHARED_REGISTER["sources"] if x["source_id"] == "gb:LBR:ADM2")
LBR_SHARED_FILES = {}
for level, name, raw_sha, compressed_sha, raw_bytes in (
    ("ADM1", "geoboundaries-lbr-adm1-2021.geojson.gz", LBR_REGISTER["adm1_source"]["sha256"], LBR_REGISTER["adm1_source"]["retained_gzip_sha256"], LBR_REGISTER["adm1_source"]["bytes"]),
    ("ADM2", "geoboundaries-lbr-adm2-2021.geojson.gz", LBR_REGISTER["original_sha256"], LBR_REGISTER["retained_gzip_sha256"], LBR_REGISTER["original_bytes"]),
):
    path = SHARED_PACKET / "sources" / name
    compressed = path.read_bytes()
    raw = gzip.decompress(compressed)
    if sha256(compressed).hexdigest() != compressed_sha or len(raw) != raw_bytes or sha256(raw).hexdigest() != raw_sha:
        raise SystemExit("shared Liberia source receipt differs from merged packet: " + str(path))
    LBR_SHARED_FILES[level] = json.loads(raw)
for iso in ("GHA", "GIN", "GNB", "LBR"):
    for level, target, metatarget in (("ADM0", countries, country_metadata), ("ADM1", parents, parent_metadata), ("ADM2", features, metadata)):
        base = SOURCE / f"{iso}-geoBoundaries-{iso}-{level}"
        meta = json.loads(Path(str(base) + "-metaData.json").read_text(encoding="utf-8"))
        if iso == "LBR" and level in LBR_SHARED_FILES:
            collection = LBR_SHARED_FILES[level]["features"]
        else:
            collection = load_collection(Path(str(base) + ".geojson"))
        metatarget[iso] = meta
        target[iso] = collection
        declared = int(meta["admUnitCount"])
        if len(collection) != declared:
            raise SystemExit(f"{iso} {level} features {len(collection)} != metadata count {declared}")

# Scope subject IDs are derived directly from exact native shape IDs.
source_for_id = {}
for iso, coll in features.items():
    for feature in coll:
        sid = feature["properties"]["shapeID"]
        source_for_id[f"gb:{iso}:ADM2:{sid}"] = feature
for identity in IDS:
    if identity not in source_for_id:
        raise SystemExit("issue subject missing from pinned ADM2 source: " + identity)

# The cited membership is an evidence-work partition. Compare every native member
# with its retained row, issue-owned area/province, source layer, and ADM1 overlay.
rows = []
for identity in IDS:
    prior = review[identity]
    iso = prior["iso"]
    feature = source_for_id[identity]
    props = feature["properties"]
    geom = shape(feature["geometry"])
    if geom.is_empty:
        raise SystemExit("empty source geometry: " + identity)
    fixed = geom if geom.is_valid else geom.buffer(0)
    if fixed.is_empty or not fixed.is_valid:
        raise SystemExit("invalid source geometry after diagnostic repair: " + identity)
    eq = transform(project, fixed)
    area_km2 = eq.area / 1_000_000
    components = list(fixed.geoms) if fixed.geom_type == "MultiPolygon" else [fixed]
    component_areas = sorted((transform(project, g).area / 1_000_000 for g in components), reverse=True)
    vertices = 0
    for polygon in components:
        vertices += len(polygon.exterior.coords) + sum(len(r.coords) for r in polygon.interiors)
    parent_id = prior["parent_id"]
    province = PROVINCES.get(parent_id)
    if not province:
        raise SystemExit("scoped subject has unlisted parent: " + identity)
    candidates = []
    for pfeature in parents[iso]:
        pg = shape(pfeature["geometry"])
        peq = transform(project, pg if pg.is_valid else pg.buffer(0))
        overlap = eq.intersection(peq).area / eq.area if eq.area else 0.0
        candidates.append((overlap, pfeature["properties"]["shapeName"], pfeature["properties"]["shapeID"]))
    candidates.sort(reverse=True)
    max_share, best_parent, best_parent_shapeid = candidates[0]
    parent_name_match = norm(province["name"]) == norm(best_parent)
    meta2 = metadata[iso]
    canonical = meta2.get("boundaryCanonical") or ""
    exact_name = prior["name"] == props["shapeName"]
    exact_license = prior.get("license") == meta2["boundaryLicense"]
    exact_vintage = str(prior.get("source_year")) == str(meta2["boundaryYear"])
    exact_url_commit = prior.get("source_url", "").startswith("https://github.com/wmgeolab/geoBoundaries/raw/9469f09/")
    # For this study these labels describe the evidence state for the scoped row,
    # not legal certification of its border or a region-level approval.
    if not exact_name or not exact_license or not exact_vintage or not parent_name_match:
        classification = "correction-needed"
    elif iso == "GIN" and norm(props["shapeName"]) == "conakry":
        classification = "correction-needed"
    elif max_share < 0.98:
        classification = "insufficient-evidence"
    elif iso == "GNB":
        classification = "insufficient-evidence"
    elif iso == "LBR":
        classification = "insufficient-evidence"
    else:
        classification = "justified"
    reason = ""
    if iso == "GIN" and norm(props["shapeName"]) == "conakry":
        reason = "Official Guinea source describes Conakry as a special zone and lists 33 prefectures; source metadata canonical='prefecture' and 34th ADM2 feature flatten that distinction."
    elif iso == "GNB":
        reason = "Pinned 2017 39-feature source and 2024 UK/DGGC-referenced roster conflict with Guinea-Bissau's 2025 government report of 36 sectors; exact current sector completeness remains unresolved."
    elif iso == "LBR":
        reason = "2021 UNMIL/OCHA-derived 136-district source is superseded/does not match LISGIS 2022's 160-district census cartography; unit-specific change crosswalk still required."
    elif max_share < 0.98:
        reason = f"Declared parent name matches, but the child overlay with the separate {parent_metadata[iso].get('boundaryYear')} {parent_metadata[iso].get('boundarySource')} ADM1 layer covers {max_share:.1%}; the cross-vintage geometry mismatch is a screening flag, not proof the declared parent is wrong."
    elif classification == "justified":
        reason = "Exact source ID/name, source role and vintage, and spatial parent overlay agree with retained source and official country-level tier context; this does not establish legal boundary accuracy or completeness."
    else:
        reason = "Source ID/name/license/vintage or parent-overlay evidence differs; resolve before using this unit as a factual boundary claim."
    area_id = next(x["id"] for x in SCOPE["area_scopes"] if x["name"] == prior["owner"])
    area_scope = AREAS[area_id]
    rows.append({
        "subject_id": identity, "country_iso": iso, "source_shape_id": props["shapeID"],
        "source_name": props["shapeName"], "retained_name": prior["name"], "name_exact": exact_name,
        "area_id": area_id, "area_name": area_scope["name"], "area_owned_subject_count": area_scope["owned_member_location_count"], "area_full_location_count": area_scope["full_area_location_count"], "area_partial": area_scope["partial"],
        "declared_parent_id": parent_id, "declared_parent_name": province["name"],
        "overlay_parent_name": best_parent, "overlay_parent_shape_id": best_parent_shapeid,
        "overlay_parent_area_share": round(max_share, 8), "parent_name_match": parent_name_match,
        "source_role": canonical, "source_vintage": meta2["boundaryYear"],
        "source_layer_count": int(meta2["admUnitCount"]), "source_license": meta2["boundaryLicense"],
        "retained_license_exact": exact_license, "retained_vintage_exact": exact_vintage,
        "source_type": geom.geom_type, "source_components": len(components), "source_vertices": vertices,
        "source_area_epsg6933_km2": round(area_km2, 8),
        "retained_area_km2": prior.get("area_km2"),
        "source_vs_retained_area_fraction": round((area_km2 - float(prior["area_km2"])) / float(prior["area_km2"]), 8) if prior.get("area_km2") else None,
        "bounds_wgs84": [round(v, 8) for v in fixed.bounds],
        "classification": classification, "finding": reason,
        "independent_legal_boundary_check": "not established by geoBoundaries comparison",
        "source_url_exact_commit": exact_url_commit
    })

# Liberia names and parents are compared to the official current 2022 layer.
old_lbr = {norm(f["properties"]["shapeName"]): f for f in features["LBR"]}
county_features = json.loads((LISGIS / "county-boundaries.json").read_text(encoding="utf-8"))["features"]
district_features = json.loads((LISGIS / "district-boundaries.json").read_text(encoding="utf-8"))["features"]
counties_by_code = {f["properties"]["code"]: f["properties"]["name"] for f in county_features}
current_pairs = {(norm(f["properties"]["name"]), f["properties"]["parent_code"]): f for f in district_features}
old_parent_by_name = {}
for f in parents["LBR"]:
    old_parent_by_name[f["properties"]["shapeID"]] = f["properties"]["shapeName"]
old_county_name = {}
for f in features["LBR"]:
    geom = shape(f["geometry"]); eq = transform(project, geom if geom.is_valid else geom.buffer(0))
    overlaps=[]
    for p in parents["LBR"]:
        pg=shape(p["geometry"]); peq=transform(project,pg if pg.is_valid else pg.buffer(0))
        overlaps.append((eq.intersection(peq).area/eq.area,p["properties"]["shapeName"],p["properties"]["shapeID"]))
    old_county_name[norm(f["properties"]["shapeName"])] = max(overlaps)[1]
new_lbr_rows=[]
for identity in IDS:
    if ":LBR:" not in identity: continue
    row=review[identity]; name=row["name"]; county=old_county_name[norm(name)]
    lisgis_county_code=next((code for code,cname in counties_by_code.items() if norm(cname)==norm(county)),None)
    match=current_pairs.get((norm(name),lisgis_county_code)) if lisgis_county_code else None
    candidate = None
    if name == "Commonwealth":
        candidate = current_pairs.get((norm("Commonwealth Rs"), lisgis_county_code)) if lisgis_county_code else None
    old_geom = shape(source_for_id[identity]["geometry"])
    old_eq = transform(project, old_geom if old_geom.is_valid else old_geom.buffer(0))
    new_geom = shape(match["geometry"] if match else candidate["geometry"]) if (match or candidate) else None
    new_eq = transform(project, new_geom if new_geom.is_valid else new_geom.buffer(0)) if new_geom else None
    intersection = old_eq.intersection(new_eq).area if new_eq else None
    new_lbr_rows.append({"subject_id":identity,"name":name,"old_parent":county,"lisgis_parent_code":lisgis_county_code,"lisgis_parent_name":counties_by_code.get(lisgis_county_code),"name_parent_match":bool(match),"new_shape_code":match["properties"]["code"] if match else None,"possible_alias":"Commonwealth Rs" if candidate else None,"possible_alias_shape_code":candidate["properties"]["code"] if candidate else None,"possible_alias_not_confirmed":bool(candidate and not match),"old_area_km2":round(old_eq.area/1e6,6),"current_area_km2":round(new_eq.area/1e6,6) if new_eq else None,"area_change_fraction":round((new_eq.area-old_eq.area)/old_eq.area,8) if new_eq else None,"symmetric_difference_over_old_fraction":round((old_eq.area+new_eq.area-2*intersection)/old_eq.area,8) if new_eq else None})

# Country-level count/vintage and coverage diagnostics. The coverage overlay is
# comparative evidence, not a legal or completeness certification.
country_summary=[]
for iso in ("GHA","GIN","GNB","LBR"):
    adm0=shape(countries[iso][0]["geometry"]); adm0eq=transform(project,adm0 if adm0.is_valid else adm0.buffer(0))
    child_eq=[]
    for f in features[iso]:
        g=shape(f["geometry"]); child_eq.append(transform(project,g if g.is_valid else g.buffer(0)))
    dissolved=unary_union(child_eq)
    in0=dissolved.intersection(adm0eq).area / adm0eq.area
    out=dissolved.difference(adm0eq).area / dissolved.area if dissolved.area else 0
    overlap_excess=(sum(g.area for g in child_eq)-dissolved.area)/dissolved.area if dissolved.area else 0
    country_summary.append({"iso":iso,"adm0_features":len(countries[iso]),"adm1_features":len(parents[iso]),"adm1_role":parent_metadata[iso].get("boundaryCanonical"),"adm1_license":parent_metadata[iso].get("boundaryLicense"),"adm2_features":len(features[iso]),"adm2_metadata_count":int(metadata[iso]["admUnitCount"]),"adm2_role":metadata[iso].get("boundaryCanonical"),"source_year":metadata[iso].get("boundaryYear"),"source_builder_commit":metadata[iso].get("buildDate"),"source_update_date":metadata[iso].get("sourceDataUpdateDate"),"source_license":metadata[iso].get("boundaryLicense"),"source_provider":metadata[iso].get("boundarySource"),"country_union_overlap_share":round(in0,8),"outside_country_share":round(out,8),"overlap_excess_share":round(overlap_excess,8)})

lbr_names_old={norm(f["properties"]["shapeName"]): f for f in features["LBR"]}
lbr_names_new={norm(f["properties"]["name"]): f for f in district_features}
lbr_name_only=sorted(set(lbr_names_old)&set(lbr_names_new))
lbr_parent_matches=[]
for normalized in lbr_name_only:
    oldcounty=old_county_name[normalized]
    newprop=lbr_names_new[normalized]["properties"]
    newcounty=counties_by_code.get(newprop["parent_code"])
    if norm(oldcounty)==norm(newcounty): lbr_parent_matches.append(normalized)

summary={
 "version":1,"scope_batch":SCOPE["batch_id"],"scope_member_count":len(rows),"scope_id_sha256":SCOPE["member_location_ids_sha256"],
 "scope_country_counts":dict(sorted(Counter(x["country_iso"] for x in rows).items())),
 "classification_counts":dict(sorted(Counter(x["classification"] for x in rows).items())),
 "issue_area_scopes":SCOPE["area_scopes"],"issue_province_scope_count":len(PROVINCES),
 "country_sources":country_summary,
 "lisgis_liberia_2022":{"official_district_features":len(district_features),"official_counties":len(county_features),"source_dataset":"LISGIS 2022 Population and Housing Census administrative GIS shapefiles","issue_scoped_subjects":new_lbr_rows,"old_2021_source_count":len(features["LBR"]),"exact_name_matches_old_to_current":len(lbr_name_only),"same_county_for_name_matches":len(lbr_parent_matches),"names_not_found_current":sorted(norm(x["properties"]["shapeName"]) for x in features["LBR"] if norm(x["properties"]["shapeName"]) not in lbr_names_new)},
 "scoped_findings":rows,
 "limits":["Source-layer topology/count/name/parent overlays do not establish legal demarcation or settlement/island completeness.","GNB 2017/2024 39-sector and 2025 government 36-sector claims conflict; do not assert current 39-unit completeness until DGGC or another primary national source reconciles them.","LBR geoBoundaries 2021 ADM2 has 136 features, while primary LISGIS 2022 census cartography has 160 district features; full Liberia crosswalk is outside this packet's exact 9-unit LBR scope.","Source-derived 2022 Liberia geometries are later than the older issue/source roster and cannot be silently substituted into any atlas geography or historical evidence.","Conakry is a distinct special zone in the official Guinea government description but is included in geoBoundaries ADM2's prefecture-canonical 34-feature file; exact tier assignment needs a bounded source correction."]
}
(OUT/"findings.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
with (OUT/"subject-assessments.csv").open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()),extrasaction="ignore");writer.writeheader();writer.writerows(rows)
print(json.dumps({k:summary[k] for k in ["scope_member_count","scope_country_counts","classification_counts","issue_province_scope_count","country_sources","lisgis_liberia_2022"]},indent=2,ensure_ascii=False))
