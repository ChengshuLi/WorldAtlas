#!/usr/bin/env python3
"""Reproduce the Turkey issue #75 source-ID and parent-roster assessment.

Reads only immutable baseline blobs. Writes only beside this script. The source
GeoJSON remains retained in the prior #71 packet and is SHA-256 checked here.
"""
import csv, gzip, hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
BASE = "f9a1dfa98b664dcf322806c843e82ab29d2b7935"
SOURCE_PATH = "data/regional-review/regional-review-ef67318527f5f3a3/sources/geoBoundaries-TUR-ADM2.geojson.gz"
SOURCE_SHA256 = "a88007de2cf14f14e06da390aab8861442c7a8332ef8e70865d78e0d9b549d78"
EXPECTED = {
"gb:TUR:ADM2:54988432B11506112394599":"framework:province:hakkari:45bd46f77b6f",
"gb:TUR:ADM2:54988432B12859589940172":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B27415936221667":"framework:province:igdr:1542a52eac4f",
"gb:TUR:ADM2:54988432B29564092922191":"framework:province:hakkari:45bd46f77b6f",
"gb:TUR:ADM2:54988432B35038871298949":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B39980691668600":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B42317071313317":"framework:province:hakkari:45bd46f77b6f",
"gb:TUR:ADM2:54988432B47270758673920":"framework:province:igdr:1542a52eac4f",
"gb:TUR:ADM2:54988432B48034047733274":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B49000461137157":"framework:province:hakkari:45bd46f77b6f",
"gb:TUR:ADM2:54988432B50394805884304":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B53167672259322":"framework:province:igdr:1542a52eac4f",
"gb:TUR:ADM2:54988432B53179569886424":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B53845687770419":"framework:province:igdr:1542a52eac4f",
"gb:TUR:ADM2:54988432B59251116366587":"framework:province:agr:dc819bd911a0",
"gb:TUR:ADM2:54988432B62353974928440":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B6281772994077":"framework:province:agr:dc819bd911a0",
"gb:TUR:ADM2:54988432B66454172152747":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B69584017445691":"framework:province:agr:dc819bd911a0",
"gb:TUR:ADM2:54988432B71225398808763":"framework:province:agr:dc819bd911a0",
"gb:TUR:ADM2:54988432B73173192257924":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B7371544527763":"framework:province:agr:dc819bd911a0",
"gb:TUR:ADM2:54988432B79438437943955":"framework:province:agr:dc819bd911a0",
"gb:TUR:ADM2:54988432B81567150601582":"framework:province:agr:dc819bd911a0",
"gb:TUR:ADM2:54988432B84066107129786":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B84889548595985":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B86310086710434":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B86685660972424":"framework:province:van:f871881e462f",
"gb:TUR:ADM2:54988432B8973824492298":"framework:province:hakkari:45bd46f77b6f",
"gb:TUR:ADM2:54988432B97639118870532":"framework:province:agr:dc819bd911a0"
}
PROVINCES = {
"framework:province:agr:dc819bd911a0":("Ağrı", "Ağrı Valiliği İl Protokol Listesi"),
"framework:province:van:f871881e462f":("Van", "Van Valiliği Yöneticilerimiz"),
"framework:province:igdr:1542a52eac4f":("Iğdır", "Iğdır Valiliği İlçeleri"),
"framework:province:hakkari:45bd46f77b6f":("Hakkâri", "Hakkâri Valiliği İlçelerimiz and official notices")
}

def blob(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASE}:{path}"])
def sha(data): return hashlib.sha256(data).hexdigest()

raw_source = blob(SOURCE_PATH)
assert sha(raw_source) == SOURCE_SHA256, sha(raw_source)
source = json.loads(gzip.decompress(raw_source))
features = {}
for f in source["features"]:
    p=f["properties"]
    sid="gb:TUR:ADM2:"+p["shapeID"]
    if sid in EXPECTED: features[sid]=f
assert set(features)==set(EXPECTED), (set(EXPECTED)-set(features), set(features)-set(EXPECTED))

index=json.loads(blob("data/world-index.json"))
found={}
for path in index["parts"]:
    part=json.loads(blob("data/"+path))
    for f in part.get("features",[]):
        p=f.get("properties",{})
        ident=p.get("id") or f.get("id")
        if ident in EXPECTED:
            if ident in found: raise ValueError("duplicate baseline ID: "+ident)
            found[ident]={"name":p.get("name", ""),"parent_id":p.get("parent_id", "")}
assert set(found)==set(EXPECTED), set(EXPECTED)-set(found)

rows=[]
for ident in sorted(EXPECTED):
    feature=features[ident]; sp=feature["properties"]; bp=found[ident]
    province,roster=PROVINCES[EXPECTED[ident]]
    rows.append({
      "location_id":ident,"atlas_name":bp["name"],"atlas_parent_id":bp["parent_id"],
      "province_name":province,"retained_source_shapeID":sp["shapeID"],
      "retained_source_name":sp.get("shapeName", ""),"source_shapeGroup":sp.get("shapeGroup", ""),
      "source_geometry_type":feature["geometry"]["type"],
      "source_polygon_component_count":(len(feature["geometry"]["coordinates"]) if feature["geometry"]["type"]=="MultiPolygon" else (1 if feature["geometry"]["type"]=="Polygon" else "")),
      "source_role_vintage_license":"geoBoundaries TUR ADM2; metadata says Districts; 2021; ODbL 1.0",
      "official_roster_source":roster,
      "roster_join":("Ağrı Valiliği lists the seven named kaymakam districts; Ağrı Valiliği project notice separately refers to seven districts plus the provincial center" if ident.endswith("B81567150601582") else ("official roster match; center label normalized to Merkez" if "merkez" in sp.get("shapeName", "").lower() else "official roster match")),
      "classification":"insufficient-evidence",
      "reason":"District role and parent roster membership are supported; current authoritative boundary, legal crosswalk, complete source population, and district-vs-city territorial semantics are not established.",
      "recommendation":"Preserve identity and parent; do not replace geometry. Obtain lawful authoritative versioned district boundary and official identity crosswalk, then compare source coverage, edge topology, urban subdivision and neighboring level.",
    })
    assert bp["parent_id"] == EXPECTED[ident], (ident,bp["parent_id"],EXPECTED[ident])
    # The retained source contains no authoritative province parent code; do not infer one.
    assert sp.get("shapeGroup")=="TUR"

scope={"batch_id":"regional-review:3e1fa7fa469a0b13","issue":75,"baseline_commit":BASE,"location_count":len(EXPECTED),"member_location_ids":sorted(EXPECTED),"issue_member_location_ids_sha256":"a1ae27720aaea5dc9d34b2cdd8dac7650c2ea40f77de45bfaec2053941a400ba","province_scopes":[{"id":pid,"name":name,"owned_location_ids":sorted([i for i,p in EXPECTED.items() if p==pid]),"classification":"insufficient-evidence"} for pid,(name,_) in PROVINCES.items()],"source":{"id":"gb:TUR:ADM2","retained_original_path":SOURCE_PATH,"retained_original_sha256":SOURCE_SHA256,"release_commit":"9469f09592ced973a3448cf66b6100b741b64c0d","vintage":"2021","source_metadata":"Districts; ODbL 1.0","geojson_feature_count":len(source["features"]),"metadata_admUnitCount":999,"count_difference":26,"source_parent_property":"shapeGroup=TUR only; no province code"},"classification_summary":{"justified":0,"correction-needed":0,"insufficient-evidence":len(EXPECTED)}}
(OUT/"scope.json").write_text(json.dumps(scope,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
with (OUT/"assessment.csv").open("w",encoding="utf-8",newline="") as h:
    w=csv.DictWriter(h,fieldnames=list(rows[0]),lineterminator="\n"); w.writeheader(); w.writerows(rows)
print(json.dumps({"subjects":len(rows),"source_features":len(source["features"]),"source_sha256":sha(raw_source),"assessment_sha256":sha((OUT/"assessment.csv").read_bytes()),"scope_sha256":sha((OUT/"scope.json").read_bytes())},sort_keys=True))
