#!/usr/bin/env python3
"""Reproduce the pinned scope-to-source crosswalk for issue #443."""
import csv
import gzip
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAPSHOT = HERE / "source/issue-443-api-snapshot.json"
ARCHIVE = HERE / "source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2.geojson.gz"
ADM1_ARCHIVE = HERE / "source/geoBoundaries-ARG-ADM1/geoBoundaries-ARG-ADM1.geojson"
NE_ARCHIVE = HERE / "source/NaturalEarth-ca96624/ne_10m_admin_1_states_provinces.geojson.gz"
GEOREF = HERE / "source/Georef/argentina-provinces.json"
OUT = HERE / "findings"
OUT.mkdir(exist_ok=True)

issue = json.loads(SNAPSHOT.read_text())
body = issue["body"]
marker = "Machine-readable exact workload scope (JSON;"
start = body.index(marker)
start = body.index("{", start)
depth = 0
end = None
for i in range(start, len(body)):
    if body[i] == "{":
        depth += 1
    elif body[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break
scope = json.loads(body[start:end])
member_ids = scope["member_location_ids"]
if len(member_ids) != scope["location_count"] or len(set(member_ids)) != len(member_ids):
    raise SystemExit("issue scope count or uniqueness check failed")
if hashlib.sha256("\n".join(member_ids).encode("utf-8")).hexdigest() != scope["member_location_ids_sha256"]:
    raise SystemExit("issue scope member list does not match its declared SHA-256")
if {row["owned_member_location_count"] for row in scope["area_scopes"] if row["id"].endswith("argentina-northeast:923e3bf23c86")} != {53}:
    raise SystemExit("Argentina Northeast partial-scope count changed")
if {row["owned_member_location_count"] for row in scope["area_scopes"] if row["id"].endswith("argentina-northwest:c0219373ced5")} != {162}:
    raise SystemExit("Argentina Northwest scope count changed")

raw = gzip.decompress(ARCHIVE.read_bytes())
raw_sha = hashlib.sha256(raw).hexdigest()
source = json.loads(raw)
source_by_id = {"gb:ARG:ADM2:" + f["properties"]["shapeID"]: f for f in source["features"]}
if len(source_by_id) != len(source["features"]):
    raise SystemExit("source shapeID uniqueness check failed")
metadata_path = ARCHIVE.parent / "geoBoundaries-ARG-ADM2-metaData.json"
source_metadata = json.loads(metadata_path.read_text())
lfs_pointer = (ARCHIVE.parent / "geoBoundaries-ARG-ADM2.geojson.lfs-pointer.txt").read_text()
pointer_hash = re.search(r"oid sha256:([0-9a-f]{64})", lfs_pointer)
pointer_size = re.search(r"^size (\d+)$", lfs_pointer, re.MULTILINE)
if not pointer_hash or pointer_hash.group(1) != raw_sha or not pointer_size or int(pointer_size.group(1)) != len(raw):
    raise SystemExit("restored source does not match retained upstream LFS pointer")

adm1_raw = ADM1_ARCHIVE.read_bytes()
adm1_sha = hashlib.sha256(adm1_raw).hexdigest()
adm1_source = json.loads(adm1_raw)
adm1_metadata_path = ADM1_ARCHIVE.with_name("geoBoundaries-ARG-ADM1-metaData.json")
adm1_metadata = json.loads(adm1_metadata_path.read_text())
adm1_by_name = {f["properties"]["shapeName"]: f for f in adm1_source["features"]}
adm1_pointer = ADM1_ARCHIVE.with_name("geoBoundaries-ARG-ADM1.geojson.lfs-pointer.txt").read_text()
adm1_pointer_hash = re.search(r"oid sha256:([0-9a-f]{64})", adm1_pointer)
adm1_pointer_size = re.search(r"^size (\d+)$", adm1_pointer, re.MULTILINE)
if len(adm1_by_name) != len(adm1_source["features"]) or not adm1_pointer_hash or adm1_pointer_hash.group(1) != adm1_sha or not adm1_pointer_size or int(adm1_pointer_size.group(1)) != len(adm1_raw):
    raise SystemExit("restored ADM1 source does not match its retained upstream LFS pointer")
official_jurisdictions = json.loads(GEOREF.read_text())["provincias"]
if len(official_jurisdictions) != 24:
    raise SystemExit("retained official Georef response no longer lists the expected 24 jurisdictions")

def norm_name(value):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(c) != "Mn")

official_names = {norm_name(row["nombre"]): row["nombre"] for row in official_jurisdictions}
short_tierra = norm_name("Tierra del Fuego")
long_tierra = norm_name("Tierra del Fuego, Antártida e Islas del Atlántico Sur")
adm1_normalized_names = {long_tierra if norm_name(name) == short_tierra else norm_name(name): name for name in adm1_by_name}
official_not_in_2006_adm1 = sorted(official_names[key] for key in official_names.keys() - adm1_normalized_names.keys())
adm1_not_in_current_georef = sorted(adm1_by_name[name]["properties"]["shapeName"] for name in adm1_by_name if (long_tierra if norm_name(name) == short_tierra else norm_name(name)) not in official_names)

baseline = {}
for name in ("part-0.json", "part-28.json"):
    doc = json.loads((ROOT / "data/geography" / name).read_text())
    for feature in doc["features"]:
        p = feature["properties"]
        baseline[p["id"]] = p

semantic = json.loads((ROOT / "data/semantic-report.json").read_text())
audits = {"atlas:city:" + a["source"]: a for a in semantic["city_membership_audit"] if a.get("source", "").startswith("ARG-")}

rows = []
for location_id in member_ids:
    p = baseline.get(location_id)
    if p is None:
        raise SystemExit("scope member missing from pinned baseline: " + location_id)
    meta = p.get("metadata", {})
    source_ids = meta.get("source_member_ids", []) if location_id.startswith("atlas:") else [location_id]
    direct = source_by_id.get(location_id)
    audit = audits.get(location_id)
    audit_members = {m["id"]: m for m in (audit or {}).get("members", [])}
    match_flags = []
    for source_id in source_ids:
        sf = source_by_id.get(source_id)
        if sf is None:
            match_flags.append("missing")
        else:
            match_flags.append("matched")
    source_names = [source_by_id[s]["properties"]["shapeName"] for s in source_ids if s in source_by_id]
    if location_id == "atlas:city:ARG-5493":
        classification = "correction-needed"
        finding = "17 ADM2 source members include 15 CABA comunas plus Lanús and Avellaneda (Buenos Aires Province); official CABA sources enumerate 15 comunas. Aggregate boundary/name needs redesign."
    else:
        classification = "insufficient-evidence"
        finding = "Pinned source identity/name and ADM2 role reproduced; current legal boundary match, topology, omissions and 2020-to-current changes are not independently established."
    rows.append({
        "location_id": location_id,
        "atlas_name": p["name"],
        "parent_id": p.get("parent_id", ""),
        "atlas_source_id": meta.get("source_id", ""),
        "atlas_source_role": meta.get("source_role", meta.get("administrative_level", "")),
        "parent_source_level": meta.get("parent_source_level", ""),
        "hierarchy_source": meta.get("hierarchy_source", ""),
        "hierarchy_overlap_recorded": meta.get("hierarchy_overlap", ""),
        "area_code": meta.get("geographic_area_code", ""),
        "original_id": meta.get("original_id", ""),
        "matched_source_member_count": sum(x == "matched" for x in match_flags),
        "expected_source_member_count": len(source_ids),
        "source_names": " | ".join(source_names),
        "source_shape_types": " | ".join(sorted({source_by_id[s]["geometry"]["type"] for s in source_ids if s in source_by_id})),
        "classification": classification,
        "finding": finding,
    })

with (OUT / "scoped-location-review.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

direct_scope = [x for x in member_ids if x.startswith("gb:ARG:ADM2:")]
province_name_map = {
    "framework:province:ciudad-autonoma-de-buenos-aires:64e45f3ee651": "Ciudad Autónoma de Buenos Aires",
    "framework:province:ciudad-de-buenos-aires:bd2311b3ca38": "Ciudad Autónoma de Buenos Aires",
    "framework:province:buenos-aires:e6d4b2d1b661": "Buenos Aires",
    "framework:province:corrientes:a04006099866": "Corrientes",
    "framework:province:misiones:2c036a9d514b": "Misiones",
    "framework:province:mendoza:48b57dc0eff4": "Mendoza",
    "framework:province:san-juan:799fda7ed469": "San Juan",
    "framework:province:la-roja:f24d29a5d9d5": "La Rioja",
    "framework:province:catamarca:f79a45014eac": "Catamarca",
    "framework:province:san-luis:cd428b4f89ab": "San Luis",
    "framework:province:jujuy:3ff7dd67ec60": "Jujuy",
    "framework:province:tucuman:13e5687d0f21": "Tucumán",
    "framework:province:salta:7e3f9095353a": "Salta",
    "framework:province:santiago-del-estero:5e9f1329a5b6": "Santiago del Estero",
}
province_rows = []
for province in scope["province_scopes"]:
    pid, name = province["id"], province["name"]
    official_name = province_name_map.get(pid)
    if not official_name:
        raise SystemExit("unmapped scoped province: " + pid)
    if name == "Ciudad de Buenos Aires":
        label_class = "correction-needed"
        assessment = "This separate framework parent is fed by a 17-member city aggregate that includes 2 Buenos Aires Province partidos; reconcile identity and CABA scope."
    elif name != official_name:
        label_class = "correction-needed"
        assessment = "Atlas display differs from official jurisdiction spelling; ID-preserving label correction belongs to hierarchy integration."
    else:
        label_class = "label-justified"
        assessment = "Display name matches official jurisdiction spelling; provincial boundary/currentness and parent approval remain open."
    province_rows.append({
        "province_id": pid,
        "atlas_name": name,
        "official_name_for_name_check": official_name,
        "scoped_child_count": province["full_province_locations"],
        "partial_scope": province["partial"],
        "parent_adm1_source_name": name if name in adm1_by_name else "",
        "parent_adm1_source_shape_id": adm1_by_name[name]["properties"]["shapeID"] if name in adm1_by_name else "",
        "parent_adm1_source_exact_name_match": name in adm1_by_name,
        "parent_adm1_source_year": adm1_metadata["boundaryYear"],
        "parent_adm1_source_role": adm1_metadata["boundaryCanonical"],
        "parent_adm1_source_license": adm1_metadata["boundaryLicense"],
        "name_classification": label_class,
        "boundary_classification": "insufficient-evidence",
        "assessment": assessment,
    })
with (OUT / "scoped-province-review.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(province_rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(province_rows)

direct_matches = 0
name_mismatches = []
geometry_metrics = {"Polygon": 0, "MultiPolygon": 0, "other": 0, "empty": 0, "open_rings": 0, "ring_count": 0, "vertices": 0}
multipart_subjects = []
for location_id in direct_scope:
    p = baseline[location_id]
    sf = source_by_id.get(location_id)
    if sf is None:
        continue
    direct_matches += 1
    if not p["name"].strip() or p.get("metadata", {}).get("original_id") != sf["properties"].get("shapeID"):
        raise SystemExit("blank label or original ID differs from source: " + location_id)
    if p["name"] != sf["properties"]["shapeName"]:
        name_mismatches.append({"id": location_id, "atlas": p["name"], "source": sf["properties"]["shapeName"]})
    if sf["properties"].get("shapeType") != "ADM2" or sf["properties"].get("shapeGroup") != "ARG":
        raise SystemExit("source country/admin-type mismatch: " + location_id)
    typ = sf["geometry"]["type"]
    geometry_metrics[typ if typ in ("Polygon", "MultiPolygon") else "other"] += 1
    coords = sf["geometry"]["coordinates"]
    polys = [coords] if typ == "Polygon" else coords if typ == "MultiPolygon" else []
    if typ == "MultiPolygon":
        component_bounds = []
        for poly in polys:
            points = [point for ring in poly for point in ring]
            component_bounds.append([
                min(point[0] for point in points), min(point[1] for point in points),
                max(point[0] for point in points), max(point[1] for point in points)
            ] if points else None)
        multipart_subjects.append({
            "id": location_id,
            "name": p["name"],
            "parent_id": p.get("parent_id"),
            "component_count": len(polys),
            "component_bounds_lon_lat": component_bounds
        })
    for poly in polys:
        for ring in poly:
            geometry_metrics["ring_count"] += 1
            geometry_metrics["vertices"] += len(ring)
            if not ring or ring[0] != ring[-1]:
                geometry_metrics["open_rings"] += 1
    if not polys:
        geometry_metrics["empty"] += 1
area_code_counts = {}
for location_id in direct_scope:
    code = baseline[location_id].get("metadata", {}).get("geographic_area_code", "") or "(none)"
    area_code_counts[code] = area_code_counts.get(code, 0) + 1
if direct_matches != len(direct_scope) or name_mismatches:
    raise SystemExit("not all direct subjects match the pinned source by exact ID and label")

ne_raw = gzip.decompress(NE_ARCHIVE.read_bytes())
ne_sha = hashlib.sha256(ne_raw).hexdigest()
if ne_sha != "22d0e3ad85eb3e27f17cabf8ba2d50e554fbc27a87796ff891d958185da62fb5":
    raise SystemExit("Natural Earth source does not match pinned raw SHA256")
ne = json.loads(ne_raw)
ne_city = [f for f in ne["features"] if f["properties"].get("adm1_code") == "ARG-5493"]
if len(ne_city) != 1:
    raise SystemExit("pinned Natural Earth source must contain exactly one ARG-5493 feature")
ne_city = ne_city[0]
ne_geom = ne_city["geometry"]
city_features = []
for name in ("part-0.json", "part-28.json"):
    doc = json.loads((ROOT / "data/geography" / name).read_text())
    city_features.extend(f for f in doc["features"] if f["properties"].get("id") == "atlas:city:ARG-5493")
if len(city_features) != 1:
    raise SystemExit("pinned Atlas source must contain one ARG-5493 city feature")
atlas_city_geom = city_features[0]["geometry"]
def exterior_ring(geom):
    if geom["type"] == "Polygon": return geom["coordinates"][0]
    if geom["type"] == "MultiPolygon": return [pt for poly in geom["coordinates"] for pt in poly[0]]
    raise SystemExit("unsupported city geometry type")
def in_ring(point, ring):
    x, y = point; inside = False
    for a, b in zip(ring, ring[1:]):
        if (a[1] > y) != (b[1] > y):
            cross = (b[0]-a[0]) * (y-a[1]) / (b[1]-a[1]) + a[0]
            if x < cross: inside = not inside
    return inside
def bounds(ring):
    return [min(p[0] for p in ring), min(p[1] for p in ring), max(p[0] for p in ring), max(p[1] for p in ring)]
atlas_ring = exterior_ring(atlas_city_geom)
ne_ring = exterior_ring(ne_geom)
city_boundary_diagnostic = {
    "atlas_geometry_type": atlas_city_geom["type"], "atlas_exterior_vertex_count_including_closure": len(atlas_ring), "atlas_exterior_bbox_lon_lat": bounds(atlas_ring),
    "natural_earth_geometry_type": ne_geom["type"], "natural_earth_exterior_vertex_count_including_closure": len(ne_ring), "natural_earth_exterior_bbox_lon_lat": bounds(ne_ring),
    "atlas_vertices_inside_natural_earth_exterior_ring": sum(in_ring(p, ne_ring) for p in atlas_ring[:-1]), "atlas_vertices_tested": len(atlas_ring)-1,
    "natural_earth_vertices_inside_atlas_exterior_ring": sum(in_ring(p, atlas_ring) for p in ne_ring[:-1]), "natural_earth_vertices_tested": len(ne_ring)-1,
    "method_limit": "Planar lon/lat ray casting of exterior vertices only. This is not a polygon overlay, topology validation, geodesic comparison, or legal-boundary determination; differing results can reflect vintage or delineation differences."
}
city = baseline["atlas:city:ARG-5493"]["metadata"]["source_member_ids"]
if len(set(city)) != len(city):
    raise SystemExit("city aggregate source_member_ids contain duplicates")
city_audit = audits.get("atlas:city:ARG-5493", {})
city_result = []
for source_id in city:
    sf = source_by_id[source_id]
    audit = next((x for x in city_audit.get("members", []) if x["id"] == source_id), {})
    city_result.append({"id": source_id, "name": sf["properties"]["shapeName"], "overlap_from_pinned_audit": audit.get("overlap"), "named_parent_match_from_pinned_audit": audit.get("named_parent_match")})

result = {
    "issue": 443,
    "snapshot_updated_at": issue.get("updated_at"),
    "scope_location_count": len(member_ids),
    "scope_member_location_ids_sha256_declared": scope["member_location_ids_sha256"],
    "pinned_release": scope["release"],
    "pinned_region_id": scope["region_id"],
    "pinned_scope_sha256s": {
        "macro_certificate": scope["macro_certificate_sha256"],
        "frozen_region_geometry": scope["frozen_region_geometry_sha256"],
        "frozen_region_member_ids": scope["frozen_region_member_ids_sha256"],
        "hierarchy": scope["release"]["hierarchy_sha256"],
        "footprints": scope["release"]["footprints_sha256"]
    },
    "source_url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2.geojson",
    "source_commit": "9469f09",
    "source_uncompressed_bytes": len(raw),
    "source_sha256_uncompressed": raw_sha,
    "source_metadata_file_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
    "source_feature_count": len(source["features"]),
    "source_unique_shape_ids": len(source_by_id),
    "source_metadata_admUnitCount": int(source_metadata["admUnitCount"]),
    "source_metadata_boundary_year": source_metadata["boundaryYear"],
    "source_metadata_canonical_role": source_metadata["boundaryCanonical"],
    "source_metadata_license": source_metadata["boundaryLicense"],
    "parent_adm1_source": {
        "source_url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ARG/ADM1/geoBoundaries-ARG-ADM1.geojson",
        "source_year": adm1_metadata["boundaryYear"],
        "source_role": adm1_metadata["boundaryCanonical"],
        "source_license": adm1_metadata["boundaryLicense"],
        "source_uncompressed_bytes": len(adm1_raw),
        "source_sha256_uncompressed": adm1_sha,
        "source_metadata_sha256": hashlib.sha256(adm1_metadata_path.read_bytes()).hexdigest(),
        "source_feature_count": len(adm1_source["features"]),
        "source_metadata_feature_count": int(adm1_metadata["admUnitCount"]),
        "repository_register_expected_sha256": json.loads((ROOT / "data/administrative-sources.json").read_text())["gb:ARG:ADM1"]["sha256"],
        "scoped_parent_exact_source_name_matches": sum(row["atlas_name"] in adm1_by_name for row in province_rows),
        "scoped_parent_count": len(province_rows),
        "official_georef_response_sha256": hashlib.sha256(GEOREF.read_bytes()).hexdigest(),
        "official_georef_jurisdiction_count": len(official_jurisdictions),
        "official_jurisdictions_absent_from_2006_source": official_not_in_2006_adm1,
        "2006_source_names_not_in_current_official_list": adm1_not_in_current_georef
    },
    "repository_register_expected_source_sha256": json.loads((ROOT / "data/administrative-sources.json").read_text())["gb:ARG:ADM2"]["sha256"],
    "baseline_input_hashes": {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in ("data/geography/part-0.json", "data/geography/part-28.json", "data/semantic-report.json", "data/administrative-sources.json")
    },
    "subject_source_matches": direct_matches,
    "subject_source_name_mismatches": name_mismatches,
    "direct_subject_count": len(direct_scope),
    "direct_subjects_by_area_code": area_code_counts,
    "scoped_province_count": len(province_rows),
    "province_name_correction_candidates": [r["province_id"] for r in province_rows if r["name_classification"] == "correction-needed"],
    "geometry_metrics_source_only": geometry_metrics,
    "multipart_subjects_source_only": multipart_subjects,
    "city_aggregate_source_members": city_result,
    "natural_earth_pinned_source": {"upstream_commit": "ca96624a56bd078437bca8184e78163e5039ad19", "github_blob_sha": "4a8438f98ac7dfec7dc1739b1eaf91398ad33f22", "source_sha256_uncompressed": ne_sha, "source_uncompressed_bytes": len(ne_raw), "feature": {k: ne_city["properties"].get(k) for k in ("adm1_code", "diss_me", "name", "name_en", "admin", "type_en", "postal", "gn_name", "wikidataid")}, "license": "Public domain per Natural Earth terms; attribution appreciated but not required", "city_boundary_diagnostic": city_boundary_diagnostic},
    "city_members_total": len(city),
    "city_members_official_caba_comunas": sum(x["name"].startswith("Comuna ") for x in city_result),
    "city_members_outside_caba_named_by_geoBoundaries": [x["name"] for x in city_result if x["name"] in ("Lanús", "Avellaneda")],
    "limitations": [
        "Ring closure and source geometry type are syntactic checks, not geometry validity, overlap, hole, boundary correctness or completeness checks.",
        "The exact pinned geoBoundaries source reports 525 features while its companion metadata reports 526; an omitted countrywide unit is not identified by this packet.",
        "Natural Earth commit ca96624 is a pinned public-domain source with a matching ARG-5493 Federal District feature, but its exterior ring and bbox differ from the Atlas city geometry. Vertex containment diagnostics are not a full overlay and do not establish which boundary is legally correct or whether Atlas used that exact upstream geometry.",
        "The official IGN 2017 GeoJSON link in its retained metadata returned HTTP 404 on 2026-10-05; current official INDEC department layer has no specified license in its published metadata and was not redistributed.",
        "The semantic-report city membership overlap values are preserved as prior Atlas audit output and were not recalculated here.",
        "The current official Georef API response verifies jurisdiction names/count only, not provincial boundary geometry. Its raw response is retained at the official URL with a retrieval hash.",
        "The pinned 2006 ADM1 parent source has 23 features and one fewer unit than the 24 jurisdictions in the current official Georef list; name comparison finds no Entre Ríos feature and a La Roja feature where the official list has La Rioja.",
        "Custom Argentina Northwest area purpose requires an explicit Atlas reference framework; official COFEMA groups NOA (5 provinces) and Cuyo (4) separately, while this packet's 162 units span both groups."
    ]
}
(OUT / "reproduction.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("scope_location_count", "source_feature_count", "subject_source_matches", "subject_source_name_mismatches", "repository_register_expected_source_sha256", "direct_subjects_by_area_code", "province_name_correction_candidates", "geometry_metrics_source_only", "city_members_total", "city_members_outside_caba_named_by_geoBoundaries")}, ensure_ascii=False, indent=2))
