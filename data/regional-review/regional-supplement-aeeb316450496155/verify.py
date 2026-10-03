#!/usr/bin/env python3
"""Read-only Fugloy packet and retained-source checks."""
import gzip
import hashlib
import json
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/regional-supplement-aeeb316450496155"
A = json.loads((PACKET / "assessment.json").read_text())
assert A["issue"] == 522
ids = A["scope"]["member_location_ids"]
assert ids == ["atlas:restoration:location:fugloy"]
assert hashlib.sha256(ids[0].encode()).hexdigest() == A["scope"]["member_location_ids_sha256"]
assert A["scope"]["assigned_assessed"] == 1
src = A["sources"][0]["retained_original"]
archive = ROOT / src["repository_archive"]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == src["archive_sha256"]
with tarfile.open(archive, "r:gz") as tf:
    member = tf.extractfile(src["archive_member"]).read()
    geom = tf.extractfile(src["candidate_land_geometry"]["archive_member"]).read()
assert len(member) == src["member_compressed_bytes"]
assert hashlib.sha256(member).hexdigest() == src["member_compressed_sha256"]
raw = gzip.decompress(member)
assert len(raw) == src["member_uncompressed_bytes"]
assert hashlib.sha256(raw).hexdigest() == src["member_uncompressed_sha256"]
assert len(geom) == src["candidate_land_geometry"]["compressed_bytes"]
assert hashlib.sha256(geom).hexdigest() == src["candidate_land_geometry"]["compressed_sha256"]
assert hashlib.sha256(gzip.decompress(geom)).hexdigest() == src["candidate_land_geometry"]["uncompressed_sha256"]
xml = ET.fromstring(raw)
coast = [w for w in xml.findall("way") if any(t.attrib.get("k") == "natural" and t.attrib.get("v") == "coastline" for t in w.findall("tag"))]
assert len(coast) == 74
coast_ids = {w.attrib["id"] for w in coast}
review = json.loads((ROOT / "data/macro-improvements/macro-coverage-europe-asia/modern-candidate-review.json").read_text())
q = next(x for x in review["query_results"] if x["name"] == "FugloyWide")
assert q["original_sha256"] == src["member_uncompressed_sha256"]
assert len(q["closed_rings"]) == 35 and len(q["open_chains"]) == 2
accounted_way_ids = {w for r in q["closed_rings"] + q["open_chains"] for w in r["way_ids"]}
assert accounted_way_ids == coast_ids
ring_way_ids = {w for r in q["closed_rings"] for w in r["way_ids"]}
for way in coast:
    if way.attrib["id"] in ring_way_ids:
        tags = {t.attrib.get("k"): t.attrib.get("v") for t in way.findall("tag")}
        assert tags.get("natural") == "coastline" and "name" not in tags
main_ring = A["sources"][0]["inspected_facts"]["main_island_ring"]
assert q["closed_rings"][0]["way_ids"] == main_ring["way_ids"]
assert len(main_ring["way_ids"]) == 14
small_rings = A["sources"][0]["inspected_facts"]["other_ring_inventory"]
assert len(small_rings) == 34
assert [x["way_ids"] for x in small_rings] == [r["way_ids"] for r in q["closed_rings"][1:]]
assert abs(sum(x["area_km2"] for x in small_rings) - 0.014353194089349505) < 1e-12
assert len(A["sources"][0]["inspected_facts"]["open_chain_way_ids"]) == 2

hierarchy = {x["id"]: x for x in json.loads((ROOT / "data/hierarchy.json").read_text())}
chain = A["subject_assessments"][0]["parent_chain_assessment"]["chain"]
assert [x["id"] for x in chain] == [
    "atlas:restoration:province:fugloyar-municipality",
    "framework:area:froyar:04fca3ca6320",
    "framework:region:nordic-europe:830e13d9350b",
    "framework:subcontinent:northern-europe:de794fa8b517",
    "framework:continent:europe:d247cf0382c8",
]
for child, parent in zip(chain, chain[1:]):
    assert hierarchy[child["id"]]["parent_id"] == parent["id"]
world_index = json.loads((ROOT / "data/world-index.json").read_text())
locations = []
area_members = []
area_provinces = {x["id"] for x in hierarchy.values() if x.get("parent_id") == chain[1]["id"]}
for part in world_index["parts"]:
    data = json.loads((ROOT / "data" / part).read_text())
    for feature in data.get("features", []):
        pr = feature.get("properties", {})
        if pr.get("id") == ids[0]:
            locations.append(pr)
        if pr.get("parent_id") in area_provinces:
            area_members.append(pr.get("id"))
assert len(locations) == 1 and locations[0]["parent_id"] == chain[0]["id"]
assert set(area_members) == {"FRO-1443", ids[0]}

handoff = json.loads(gzip.open(ROOT / "data/macro-foundation/regional-handoffs.json.gz", "rt").read())
region = next(x for x in handoff["regions"] if x["region_id"] == A["scope"]["region_id"])
assert region["envelope"]["geometry_sha256"] == "54da14590d2faf695dcb16731f337d9a8470998b37d4957583c2242847a15ffa"
assert region["envelope"]["member_location_ids_sha256"] == "cc5bbb819c377ab48c2a3f7ede29e45f11f6cb8b31ca7fb3fcce4f697884a4aa"
print("Fugloy evidence checks passed: 1/1 locations, five ancestors, complete accounting of 74 coastline ways, 35 closed rings and 2 open chains. Detached-ring association and legal municipality boundary remain unresolved.")
