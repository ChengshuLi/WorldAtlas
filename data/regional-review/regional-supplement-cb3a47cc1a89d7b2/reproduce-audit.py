#!/usr/bin/env python3
"""Verify source evidence and reconcile historical v3 pins to assigned v5 baseline."""
import gzip
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[3]
PKG = ROOT / "data/macro-improvements/marcus-restoration"
HERE = pathlib.Path(__file__).resolve().parent
LOCATION = "atlas:named-land:location:825337016c35d6a8235a"
REGION = "framework:region:northwestern-pacific:2357073b3888"
EXPECTED_CHAIN = [
    "atlas:named-land:province:8e2c400cda9a948c06bb",
    "atlas:named-land:area:812ad26d42ad1d6edb86",
    REGION,
    "framework:subcontinent:micronesia:44f839aaab87",
    "framework:continent:oceania:48580dd0c4b4",
]


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def release_tuple(row):
    return {key: row[key] for key in ("id", "version", "hierarchy_sha256", "footprints_sha256")}


def recorded_tuple(row):
    return {
        "id": row["release_id"], "version": row["release_version"],
        "hierarchy_sha256": row["hierarchy_sha256"], "footprints_sha256": row["footprints_sha256"],
    }


manifest = read_json(PKG / "manifest.json")
for name, row in manifest["files"].items():
    payload = (PKG / name).read_bytes()
    check(len(payload) == row["bytes"] and sha(payload) == row["sha256"], f"retained source package hash {name}")

reconciliation = read_json(HERE / "baseline-reconciliation.json")
audit = read_json(HERE / "audit.json")
issue_scope_path = HERE / "issue-524-scope.json"
issue_scope = read_json(issue_scope_path)
check(sha(issue_scope_path.read_bytes()) == reconciliation["assigned_issue_scope"]["scope_file_sha256"], "retained current #524 scope block hash")
old = reconciliation["prior_audit"]["recorded_baseline_pins"]
historical = reconciliation["prior_audit"]["historical_registry_entry"]
check(recorded_tuple(audit["historical_baseline_pins"]) == recorded_tuple(old), "prior v3 pins preserved as explicitly historical")
check(recorded_tuple(old) == release_tuple(historical), "prior audit v3 tuple resolves to registry v3")
old_audit_bytes = (HERE / "audit-v1-original.json").read_bytes()
old_audit = json.loads(old_audit_bytes)
check(sha(old_audit_bytes) == reconciliation["prior_audit"]["pre_correction_sha256"], "original pre-reconciliation audit bytes are preserved")
check(old_audit["baseline_pins"] == old, "preserved audit retains the original v3 pin values")
check(historical["version"] == 3 and historical["id"] == old["release_id"], "prior audit tuple maps to a v3 registry entry")

current_pointer_path = ROOT / "data/geographic-releases/current-manifest.json"
current_pointer = read_json(current_pointer_path)
registry_path = ROOT / "data/geographic-releases" / current_pointer["path"]
registry_gzip = registry_path.read_bytes()
registry_raw = gzip.decompress(registry_gzip)
registry = json.loads(registry_raw)
check(sha(current_pointer_path.read_bytes()) == reconciliation["current_v5"]["release_pointer_sha256"], "current release pointer source hash")
check(sha(registry_gzip) == current_pointer["sha256"] == reconciliation["current_v5"]["release_registry_gzip_sha256"], "current release registry pointer and archive hash")
check(sha(registry_raw) == reconciliation["current_v5"]["release_registry_uncompressed_sha256"], "restored versioned release registry hash")
releases = registry["releases"]
v3 = next(row for row in releases if row["version"] == 3)
check(v3 == historical, "historical pins match the actual versioned v3 registry record")
check(recorded_tuple(old) == release_tuple(v3), "old audit pins are preserved as a true but non-current v3 tuple")
v5 = next(row for row in releases if row["version"] == 5)
check(v5["version"] == max(row["version"] for row in releases), "v5 is the latest release in the pointed registry")
assigned_pins = issue_scope["release"]
check(release_tuple(v5) == assigned_pins, "current issue #524 release tuple matches authoritative registry v5")
check(release_tuple(v5) == release_tuple(reconciliation["current_v5"]["release"]), "reconciliation records the exact current v5 release")
check(recorded_tuple(audit["baseline_pins"]) == release_tuple(v5), "audit baseline_pins now designate verified v5")
check(audit["historical_baseline_pins"]["release_version"] == 3 and audit["baseline_pins"]["release_version"] == 5, "historical and assigned baseline versions are distinguished")

# Independently compare the current release, gate, publication evidence, hierarchy bytes, and certificate.
gate_path = ROOT / "data/research-geography-gate.json"
gate = read_json(gate_path)
publication_path = ROOT / "data/validation/macro-publication-v5.json"
publication = read_json(publication_path)
expected_v5 = reconciliation["current_v5"]
check(sha(gate_path.read_bytes()) == expected_v5["gate_file_sha256"], "research gate file hash")
check(sha(publication_path.read_bytes()) == expected_v5["publication_receipt_sha256"], "v5 publication receipt file hash")
check(gate["macro_boundaries"]["approved_release"] == assigned_pins, "research gate approves the assigned v5 release tuple")
check(publication["published"] and publication["verified_by_root"], "v5 publication evidence records successful verification")
check(publication["release"] == assigned_pins, "publication receipt records the assigned v5 release tuple")
check(gate["macro_boundaries"]["boundary_sha256"] == expected_v5["macro_certificate_sha256"] == publication["macro_certificate_sha256"] == issue_scope["macro_certificate_sha256"], "macro certificate hash agrees across issue, gate and publication")
check(not publication["regional_interiors_approved"] and not publication["historical_location_attribute_imports_enabled"], "baseline verification does not imply regional approval or attribute-import readiness")
hierarchy_path = ROOT / "data/hierarchy.json"
hierarchy_bytes = hierarchy_path.read_bytes()
check(sha(hierarchy_bytes) == assigned_pins["hierarchy_sha256"] == expected_v5["actual_hierarchy_sha256"], "actual hierarchy bytes match assigned v5 hash")

# Check exact issue subject and its complete location-to-continent parent chain.
check(issue_scope["location_count"] == 1 and issue_scope["member_location_ids"] == [LOCATION], "issue #524 assigns exactly the recorded location")
check(sha("\n".join(sorted(issue_scope["member_location_ids"])).encode()) == issue_scope["member_location_ids_sha256"], "issue member ID fingerprint")
check(issue_scope["release"] == assigned_pins and issue_scope["region_id"] == REGION, "issue scope region and release are pinned to v5")
check(issue_scope["frozen_region_geometry_sha256"] == expected_v5["region_envelope"]["uncompressed_geometry_sha256"], "issue frozen region geometry pin matches v5 envelope")
check(issue_scope["frozen_region_member_ids_sha256"] == expected_v5["region_envelope"]["member_location_ids_sha256"], "issue frozen region membership pin matches v5 envelope")
check(issue_scope["original_partition_unchanged"] is True, "current issue snapshot preserves its original member partition")

hierarchy = json.loads(hierarchy_bytes)
by_id = {row["id"]: row for row in hierarchy}
index_doc = read_json(ROOT / "data/world-index.json")
part_paths = [ROOT / "data" / relative for relative in index_doc["parts"]]
check(all(path.is_file() for path in part_paths), "all geography index parts are present")
feature = None
all_features = []
for path in part_paths:
    doc = read_json(path)
    all_features.extend(doc.get("features", []))
    for item in doc.get("features", []):
        if item.get("id") == LOCATION:
            check(feature is None, "assigned location ID appears only once")
            feature = item
check(feature is not None, "assigned location appears in geography parts")
props = feature["properties"]
check(props.get("parent_id") == EXPECTED_CHAIN[0], "location points to declared province")
check(props.get("reference_owner") is None, "location does not encode a political owner")
check(props["metadata"]["source_way_versions"] == [{"id": "130970566", "version": "27", "timestamp": "2025-12-20T23:39:26Z"}], "published source identity pins coastline way/version")
actual_chain = []
parent = props.get("parent_id")
while parent:
    check(parent in by_id, f"parent {parent} exists")
    actual_chain.append(parent)
    parent = by_id[parent].get("parent_id")
check(actual_chain == EXPECTED_CHAIN, "actual parent chain resolves location, province, area, region, subcontinent and continent")
recorded_chain = [row["id"] for row in audit["current_parent_chain_child_to_ancestor"]]
check(recorded_chain == actual_chain, "audit parent chain matches current hierarchy")
for item in audit["current_parent_chain_child_to_ancestor"]:
    check(item["name"] == by_id[item["id"]]["name"] and item["parent_id"] == by_id[item["id"]].get("parent_id"), f"audit parent record matches hierarchy for {item['id']}")

# Verify the frozen 51-location Northwestern Pacific membership and v5 envelope bytes.
region_ids = set()
for item in all_features:
    parent = item.get("properties", {}).get("parent_id")
    visited = set()
    while parent and parent not in visited:
        visited.add(parent)
        if parent == REGION:
            region_ids.add(item["id"])
            break
        parent = by_id.get(parent, {}).get("parent_id")
region_ids_sorted = sorted(region_ids)
region_members_hash = sha(json.dumps(region_ids_sorted, ensure_ascii=False, separators=(",", ":")).encode())
region_envelope = expected_v5["region_envelope"]
handoffs_path = ROOT / "data/macro-foundation/regional-handoffs.json.gz"
handoffs_bytes = handoffs_path.read_bytes()
handoffs = json.loads(gzip.decompress(handoffs_bytes))
check(handoffs["release"] == assigned_pins, "regional handoffs reference the assigned v5 release")
check(handoffs["macro_certificate_sha256"] == issue_scope["macro_certificate_sha256"], "regional handoffs reference the assigned macro certificate")
region_handoff = next(row for row in handoffs["regions"] if row["region_id"] == REGION)
env = region_handoff["envelope"]
env_path = ROOT / region_envelope["envelope_path"]
env_archive = env_path.read_bytes()
env_wkb = gzip.decompress(env_archive)
check(sha(handoffs_bytes) == expected_v5["regional_handoffs_gzip_sha256"], "regional handoff artifact archive hash")
check(len(region_ids_sorted) == env["locations"] == region_envelope["member_count"] == 51, "all 51 v5 regional member IDs are present")
check(region_members_hash == env["member_location_ids_sha256"] == issue_scope["frozen_region_member_ids_sha256"], "all current regional IDs match frozen v5 membership fingerprint")
check(region_handoff["envelope"] == env and env["geometry_sha256"] == issue_scope["frozen_region_geometry_sha256"], "regional handoff records the frozen v5 region envelope")
check(env_path.as_posix().endswith("envelopes-v5/" + env["path"]), "regional envelope is read from the v5 envelope directory")
check(sha(env_archive) == env["sha256"] == region_envelope["envelope_gzip_sha256"], "v5 envelope gzip bytes match handoff metadata")
check(sha(env_wkb) == env["geometry_sha256"] == region_envelope["uncompressed_geometry_sha256"], "v5 envelope WKB matches frozen geometry hash")

# Reproduce the direct source conflict without deciding its cross-region meaning.
xml = ET.parse(gzip.open(PKG / "original-map.osm.xml.gz", "rb")).getroot()
ways = {w.get("id"): w for w in xml.findall("way")}
rels = {r.get("id"): r for r in xml.findall("relation")}
coast = ways["130970566"]
ctags = {t.get("k"): t.get("v") for t in coast.findall("tag")}
check(ctags.get("natural") == "coastline" and ctags.get("place") == "island", "source coastline is tagged island")
check(coast.find("nd").get("ref") == coast.findall("nd")[-1].get("ref"), "source coastline way is closed")
water = ways["534203444"]
check({t.get("k"): t.get("v") for t in water.findall("tag")}.get("natural") == "water", "one recorded closed water feature is present")
relation = rels["11775500"]
r_tags = {t.get("k"): t.get("v") for t in relation.findall("tag")}
check(r_tags.get("place") == "archipelago" and r_tags.get("name:en") == "Bonin Islands", "named Bonin/Ogasawara archipelago relation is present")
check(any(m.get("type") == "way" and m.get("ref") == "130970566" and m.get("role") == "outer" for m in relation.findall("member")), "archipelago relation directly includes Minamitorishima coastline")
check(relation.get("version") == "38" and relation.get("timestamp") == "2025-04-18T05:32:38Z", "archipelago relation version and timestamp match")
admin = rels["8004038"]
a_tags = {t.get("k"): t.get("v") for t in admin.findall("tag")}
check(a_tags.get("boundary") == "administrative" and a_tags.get("admin_level") == "8", "administrative boundary is separately tagged")
profile_gap = reconciliation["current_profile_gap"]
check(not profile_gap["present"] and not (ROOT / profile_gap["path"]).exists(), "issue-cited source-profile file remains absent")
print("RESULT: v5 assigned baseline, current scope, parents and frozen region envelope verified; historical v3 pins preserved as historical. Source conflict detected; this check does not determine physical grouping, parent assignment, or boundary changes.")
