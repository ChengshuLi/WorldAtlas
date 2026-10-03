#!/usr/bin/env python3
"""Reproduce the full 89-location source, parent, and sibling-scope audit."""

import gzip
import hashlib
import json
import pathlib
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = pathlib.Path(__file__).resolve().parent
SOURCES = PACKET / "sources"
AREA = "framework:area:peru:77f6710f2fdb"
REGION = "framework:region:western-south-america:7fe9d26228d5"
EXPECTED_WORKER_SCOPE = 89
EXPECTED_PERU_AREA_SCOPE = 204


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def member_hash(ids):
    return sha256("\n".join(sorted(ids)).encode())


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


def normalize(text):
    # geoBoundaries has one UTF-8 string decoded as Latin-1 in its source payload.
    if "Ã" in text:
        text = text.encode("latin-1").decode("utf-8")
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


scope = json.loads((PACKET / "issue-scope.json").read_text())
check(scope["location_count"] == EXPECTED_WORKER_SCOPE == len(scope["member_location_ids"]), "issue scope pins exactly 89 subjects")
check(member_hash(scope["member_location_ids"]) == scope["member_location_ids_sha256"], "issue member ID fingerprint")

index = json.loads((ROOT / "data/world-index.json").read_text())
features = {}
for relative in index["parts"]:
    data = json.loads((ROOT / "data" / relative).read_text())
    for feature in data.get("features", []):
        if feature.get("id") in set(scope["member_location_ids"]):
            features[feature["id"]] = feature
check(set(features) == set(scope["member_location_ids"]), "all assigned subjects are present in indexed geography")

hierarchy = json.loads((ROOT / "data/hierarchy.json").read_text())
groups = {group["id"]: group for group in hierarchy}
check(sha256((ROOT / "data/hierarchy.json").read_bytes()) == scope["release"]["hierarchy_sha256"], "pinned hierarchy release hash")

def chain_for(feature):
    chain = []
    parent = feature["properties"].get("parent_id")
    while parent:
        group = groups.get(parent)
        if group is None:
            raise AssertionError(f"missing hierarchy group {parent}")
        chain.append(group)
        parent = group.get("parent_id")
    return chain

for identity, feature in features.items():
    chain = chain_for(feature)
    ids = [group["id"] for group in chain]
    check(ids[1:5] == [AREA, REGION, "framework:subcontinent:andean-south-america:9579d3e91c2b", "framework:continent:south-america:bbda637e3435"], f"complete published parent chain for {identity}")
    check(feature["properties"].get("reference_owner") == "Peru", f"modern reference owner retained separately for {identity}")

members_497 = set(scope["member_location_ids"])
peer = json.loads((PACKET / "peer-scope-496.json").read_text())
members_496_peru = set(peer["member_location_ids"])
peru_descendants = set()
for relative in index["parts"]:
    data = json.loads((ROOT / "data" / relative).read_text())
    for feature in data.get("features", []):
        parent = feature.get("properties", {}).get("parent_id")
        seen = set()
        while parent and parent not in seen:
            seen.add(parent)
            if parent == AREA:
                peru_descendants.add(feature["id"])
                break
            parent = groups.get(parent, {}).get("parent_id")
check(len(peru_descendants) == EXPECTED_PERU_AREA_SCOPE, "Peru area has 204 current descendant locations")
check(len(members_496_peru) == 115 and len(members_497) == 89, "sibling packets own the pinned 115 and 89 Peru-area subjects")
check(not members_496_peru & members_497, "Peru-area sibling scope IDs do not overlap")
check(members_496_peru | members_497 == peru_descendants, "#496 and #497 scopes account for all Peru-area descendants")
check(member_hash(members_496_peru) == peer["member_location_ids_sha256"], "#496 Peru-area sibling fingerprint")

gb_data = gzip.decompress((SOURCES / "geoboundaries-PER-ADM2-2020.geojson.gz").read_bytes())
gb = json.loads(gb_data)
check(sha256(gb_data) == "58d0720bc01abd27bd02fb73d2ee8443fc6067352d97b752d100a18e3b97bb58", "pinned 2020 GeoBoundaries source bytes")
check(len(gb["features"]) == 196, "GeoBoundaries source contains all 196 Peru ADM2 province features")
by_shape_id = {f["properties"]["shapeID"]: f for f in gb["features"]}
admin = [f for f in features.values() if f["properties"]["metadata"].get("source_id") == "gb:PER:ADM2"]
check(len(admin) == 78, "78 assigned locations are direct GeoBoundaries ADM2 provinces")
for feature in admin:
    meta = feature["properties"]["metadata"]
    source = by_shape_id.get(meta.get("original_id"))
    check(source is not None, f"GeoBoundaries source ID exists for {feature['id']}")
    check(source["properties"]["shapeGroup"] == "PER" and source["properties"]["shapeType"] == "ADM2", f"source country and administrative tier match for {feature['id']}")
    check(normalize(source["properties"]["shapeName"]) == normalize(feature["properties"]["name"]), f"source name matches for {feature['id']}")

resolve_data = gzip.decompress((SOURCES / "resolve-ecoregions-2017-selected.geojson.gz").read_bytes())
resolve = json.loads(resolve_data)
check(sha256(resolve_data) == "37e8bbb6a64fb798e24eee7f056a0108682ebcd4347bf8153af9696cb816018f", "pinned RESOLVE selected-feature response")
resolve_by_id = {f["properties"]["ECO_ID"]: f for f in resolve["features"]}
physical = [f for f in features.values() if f["properties"]["metadata"].get("source_name") == "Named physical region adaptation"]
check(len(physical) == 11, "11 Loreto subjects are ecoregion-derived physical portions")
check(len(audit_subjects := json.loads((PACKET / "audit.json").read_text())["subjects"]) == 89, "individual audit inventory count")
check({x["location_id"] for x in audit_subjects} == set(scope["member_location_ids"]), "audit covers every assigned ID exactly once")
check(sum(x["assessment"] == "correction-needed" for x in audit_subjects) == 11, "11 ecological/admin-grain findings are individually flagged")
for feature in physical:
    meta = feature["properties"]["metadata"]
    eco_id = int(meta["source_id"].split(":")[1])
    source = resolve_by_id.get(eco_id)
    check(source is not None and source["properties"]["ECO_NAME"] in feature["properties"]["name"], f"RESOLVE ecoregion source matches {feature['id']}")
    check(meta.get("source_role") == "Provinces", f"recorded source-role conflict is reproducible for {feature['id']}")
    check(len(meta.get("source_member_ids", [])) == 1, f"one original province source link is recorded for {feature['id']}")

pdf = (SOURCES / "inei-bulletin-26-2020.pdf").read_bytes()
check(sha256(pdf) == "5a0a84793cddcd19e7f9db9cc9f62e03cb1240f93c0cc275abc135ba09c4d053", "retained INEI Bulletin 26 source hash")

audit = json.loads((PACKET / "audit.json").read_text())
check(len(audit["subjects"]) == 89 and {x["location_id"] for x in audit["subjects"]} == set(scope["member_location_ids"]), "audit provides one assessment for every assigned subject")
print("RESULT: membership and source identities reproduce. The check does not certify the spatial union of the 11 Loreto fragments or approve the regional interior.")
