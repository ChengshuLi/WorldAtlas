#!/usr/bin/env python3
"""Reproduce #402's scoped identity and pinned Natural Earth source comparison."""
import gzip
import hashlib
import json
import gzip
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
POLICY_FILE = ROOT / "data/location-policy.json"
CORRECTIONS = ROOT / "data/source-policy-corrections/europe-v1.json.gz"
WORLD_REVIEW = ROOT / "data/world-review.json"
SA_REVIEW = ROOT / "data/geographic-semantic-followup/south-america.json.gz"
SOURCE_ARCHIVE = ROOT / "data/regional-review/regional-review-7cf674a63057d43f/source/NaturalEarth-ca96624/ne_10m_admin_1_states_provinces.geojson.gz"
SNAPSHOT = HERE / "source/issue-402-api-snapshot.json"
SELECTED = HERE / "source/natural-earth-selected-features.geojson"
OUT = HERE / "findings/reproduction.json"
POLICY_CONTEXT = HERE / "source/source-policy-context.json"
MEMBERS = ["FLK-5152", "atlas:coverage:SGS+00?"]
SOURCE_IDS = {"FLK-5152": "FLK-5152", "atlas:coverage:SGS+00?": "SGS+00?"}

def sha(data): return hashlib.sha256(data).hexdigest()
def ring_signature(ring, digits=6):
    points=[tuple(round(v,digits) for v in point) for point in ring[:-1]]
    if not points: return ()
    def rotate_min(points):
        start=min(range(len(points)),key=lambda i:points[i:]+points[:i])
        return tuple(points[start:]+points[:start])
    return min(rotate_min(points),rotate_min(list(reversed(points))))
def ring_multiset_equal(a,b):
    from collections import Counter
    ar=[ring_signature(r) for poly in a["coordinates"] for r in poly]
    br=[ring_signature(r) for poly in b["coordinates"] for r in poly]
    return Counter(ar)==Counter(br)
def geom_stats(g):
    coords = g["coordinates"]
    if g["type"] == "Polygon": polygons = [coords]
    elif g["type"] == "MultiPolygon": polygons = coords
    else: raise ValueError("Unexpected geometry type: " + g["type"])
    rings = [ring for poly in polygons for ring in poly]
    positions = [pos for ring in rings for pos in ring]
    return {"type":g["type"],"components":len(polygons),"rings":len(rings),"positions":len(positions),
            "bbox":[min(p[0] for p in positions),min(p[1] for p in positions),max(p[0] for p in positions),max(p[1] for p in positions)],
            "canonical_sha256":sha(json.dumps(g,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())}

issue = json.loads(SNAPSHOT.read_text())
body = issue["body"]
marker = "Machine-readable exact workload scope (JSON;"
start = body.index("{", body.index(marker)); depth = 0
for i in range(start, len(body)):
    depth += (body[i] == "{") - (body[i] == "}")
    if depth == 0: break
scope = json.loads(body[start:i+1])
assert issue["number"] == 402 and issue["state"] == "open"
assert scope["member_location_ids"] == MEMBERS and scope["location_count"] == 2
assert sha("\n".join(MEMBERS).encode()) == scope["member_location_ids_sha256"]
archive_bytes = SOURCE_ARCHIVE.read_bytes(); raw = gzip.decompress(archive_bytes)
assert sha(archive_bytes)=="20777a70803489a26b57194f4626797a84784c2ee66b3f56da3d6ea72fc4849c"
assert sha(raw)=="22d0e3ad85eb3e27f17cabf8ba2d50e554fbc27a87796ff891d958185da62fb5"
source = json.loads(raw)
matched = {}
for f in source["features"]:
    code = f["properties"].get("adm1_code")
    if code in SOURCE_IDS.values(): matched[code] = f
assert set(matched) == set(SOURCE_IDS.values())
selected = {"type":"FeatureCollection","features":[matched[SOURCE_IDS[mid]] for mid in MEMBERS]}
selected_bytes = (json.dumps(selected,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
SELECTED.write_bytes(selected_bytes)
source_by_member = {mid:matched[sid] for mid,sid in SOURCE_IDS.items()}
baseline = {}
for feature in json.loads((ROOT/"data/geography/part-28.json").read_text())["features"]:
    p = feature["properties"]
    if p["id"] in MEMBERS: baseline[p["id"]] = feature
assert set(baseline) == set(MEMBERS)
rows=[]
for mid in MEMBERS:
    atlas=baseline[mid]; src=source_by_member[mid]; ap=atlas["properties"]; sp=src["properties"]
    ag=geom_stats(atlas["geometry"]); sg=geom_stats(src["geometry"])
    rows.append({"location_id":mid,"atlas_name":ap["name"],"parent_id":ap.get("parent_id"),
      "atlas_reference_owner":ap.get("reference_owner"),"atlas_reference_polity":ap.get("metadata",{}).get("reference_polity"),
      "atlas_reference_evidence":ap.get("metadata",{}).get("reference_polity_evidence"),
      "source_id":sp.get("adm1_code"),"source_name":sp.get("name"),"source_admin":sp.get("admin"),
      "source_type":src["geometry"]["type"],"atlas_geometry":ag,"source_geometry":sg,
      "geometry_structurally_equal":atlas["geometry"]==src["geometry"],
      "all_rings_match_up_to_rotation_direction_at_6dp":ring_multiset_equal(atlas["geometry"],src["geometry"]),
      "properties_of_source_feature":{k:sp.get(k) for k in ["adm1_code","name","admin","type","type_en","iso_3166_2","postal","region","region_cod","region_sub","homepart"]}})
hierarchy=json.loads((ROOT/"data/hierarchy.json").read_text())
selected_hierarchy_ids={
 "framework:subcontinent:southern-south-america:37612476d887",
 "framework:region:south-atlantic-islands:8be064d49c48",
 "framework:area:falkland-is:aa9151e086ab",
 "framework:province:falkland-islands:5308efe57fb0",
 "framework:area:south-georgia:2cb092c9700c",
 "framework:province:south-georgia-and-the-south-sandwich-islands:170c3c7a36d3"}
hierarchy_rows=[{"id":n["id"],"level":n["level"],"name":n.get("name"),"parent_id":n.get("parent_id"),"child_count":n.get("metadata",{}).get("child_count"),
  "review_reasons":n.get("metadata",{}).get("semantic_review",{}).get("remaining_reasons",[])} for n in hierarchy if n.get("id") in selected_hierarchy_ids]
assert {n["id"] for n in hierarchy_rows}==selected_hierarchy_ids
policy=json.loads(POLICY_FILE.read_text())
corrections=json.loads(gzip.decompress(CORRECTIONS.read_bytes()))
world=json.loads(WORLD_REVIEW.read_text())
sa=json.loads(gzip.decompress(SA_REVIEW.read_bytes()))
country_rows={row["iso"]:row for row in sa["countries"] if row.get("iso") in ("FLK","SGS")}
assert set(country_rows)=={"FLK","SGS"}
assert all(policy["countries"].get(code) is None for code in ("FLK","SGS"))
assert all(world["policy_crosswalk"].get(code) is None for code in ("FLK","SGS"))
assert all(row.get("source_policy") is None and row.get("policy_metadata_receipt") is None for row in country_rows.values())
assert {item["profile_iso"] for item in corrections["policy_corrections"]}=={"ITA","ESP","XKX"}
policy_context={"baseline_commit":"e5393834c715396a60967d366523712edd5d1b65",
 "input_hashes":{"data/location-policy.json":sha(POLICY_FILE.read_bytes()),"data/source-policy-corrections/europe-v1.json.gz":sha(CORRECTIONS.read_bytes()),
  "data/world-review.json":sha(WORLD_REVIEW.read_bytes()),"data/geographic-semantic-followup/south-america.json.gz":sha(SA_REVIEW.read_bytes())},
 "policy_schema":{"version":policy["version"],"principle":policy["principle"],"profile_count":len(policy["countries"]),
  "FLK":policy["countries"].get("FLK"),"SGS":policy["countries"].get("SGS"),"ARG":policy["countries"].get("ARG"),"GBR":policy["countries"].get("GBR")},
 "global_policy_crosswalk":{"basis":world["policy_crosswalk_basis"],"FLK":world["policy_crosswalk"].get("FLK"),"SGS":world["policy_crosswalk"].get("SGS"),
  "unmatched_reference_groups":[name for name in world["unmatched_reference_groups"] if name in ("Falkland Islands","South Georgia and the Islands")]},
 "south_america_semantic_assessment":{"review_date":sa["review_date"],"semantic_complete":sa["semantic_complete"],"countries":[country_rows[k] for k in ("FLK","SGS")]},
 "correction_overlay":{"id":corrections["id"],"profile_isos":sorted(p["profile_iso"] for p in corrections["policy_corrections"]),"applies_to_FLK_or_SGS":False}}
POLICY_CONTEXT.write_text(json.dumps(policy_context,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
handoffs=json.loads(gzip.decompress((ROOT/"data/macro-foundation/regional-handoffs.json.gz").read_bytes()))
region=next(r for r in handoffs["regions"] if r.get("region_id")=="framework:region:south-atlantic-islands:8be064d49c48")
assert region["envelope"]["locations"]==2 and region["envelope"]["member_location_ids_sha256"]==scope["frozen_region_member_ids_sha256"]
assert region["envelope"]["geometry_sha256"]==scope["frozen_region_geometry_sha256"] and not region["regional_interiors_approved"] and not region["publication_verified"]
result={"issue":402,"baseline_commit":"e5393834c715396a60967d366523712edd5d1b65",
 "hierarchy_parent_chain":hierarchy_rows,
 "regional_envelope":{"name":region["name"],"parent_id":region["envelope"]["parent_id"],"locations":region["envelope"]["locations"],
  "geometry_sha256":region["envelope"]["geometry_sha256"],"member_location_ids_sha256":region["envelope"]["member_location_ids_sha256"],
  "region_own_boundary_approved":region["own_boundary_approved"],"regional_interiors_approved":region["regional_interiors_approved"],
  "location_attribute_imports_ready":region["location_attribute_imports_ready"],"publication_verified":region["publication_verified"]},
 "issue_member_ids":MEMBERS,"issue_member_ids_sha256":scope["member_location_ids_sha256"],
 "natural_earth":{"commit":"ca96624a56bd078437bca8184e78163e5039ad19","commit_date":"2022-06-02T07:25:00Z",
  "archive_bytes":len(archive_bytes),"archive_sha256":sha(archive_bytes),"uncompressed_bytes":len(raw),"uncompressed_sha256":sha(raw),
  "feature_count":len(source["features"]),"selected_feature_collection_sha256":sha(selected_bytes)},
 "baseline_hashes":{"part-28.json":sha((ROOT/"data/geography/part-28.json").read_bytes()),
  "world-index.json":sha((ROOT/"data/world-index.json").read_bytes()),"hierarchy.json":sha((ROOT/"data/hierarchy.json").read_bytes()),
  "current-manifest.json":sha((ROOT/"data/geographic-releases/current-manifest.json").read_bytes()),
  "regional-handoffs.json.gz":sha((ROOT/"data/macro-foundation/regional-handoffs.json.gz").read_bytes()),
  "current-membership-inventory.json.gz":sha((ROOT/"data/macro-foundation/current-membership-inventory.json.gz").read_bytes()),
  "location-policy.json":sha(POLICY_FILE.read_bytes()),"europe-policy-corrections.gz":sha(CORRECTIONS.read_bytes()),
  "world-review.json":sha(WORLD_REVIEW.read_bytes()),"south-america-semantic-followup.json.gz":sha(SA_REVIEW.read_bytes())},"locations":rows}
OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
packet_files=[]
for file in sorted(p for p in HERE.rglob("*") if p.is_file() and p.name!="packet-manifest.json" and "__pycache__" not in p.parts):
    raw_file=file.read_bytes()
    packet_files.append({"path":file.relative_to(HERE).as_posix(),"bytes":len(raw_file),"sha256":sha(raw_file)})
(HERE/"packet-manifest.json").write_text(json.dumps({"version":1,"issue":402,"baseline_commit":"e5393834c715396a60967d366523712edd5d1b65","files":packet_files},indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True))
