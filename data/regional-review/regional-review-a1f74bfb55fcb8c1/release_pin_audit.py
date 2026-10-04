#!/usr/bin/env python3
"""Verify issue 496's claimed V5/V3 release pins against retained artifacts."""
import gzip
import hashlib
import json
import pathlib
import re
import subprocess

V5_COMMIT = "277b8ecbb3199ae3d5fb07bab96353d17a049b1c"
SCOPE_COMMIT = "b5254801fdd6f8be73c7d49ff203bd4e9fdfcbb2"
SCOPE_PATH = "data/regional-review/regional-review-a1f74bfb55fcb8c1/scope.json"
SCOPE_SHA256 = "6d55cb5a51ae8670563514485ff0baa28af37de46da8256219a37b2bedcbda41"
RELEASE_CATALOG = "data/geographic-releases/releases-v5-gzip.json.gz"
V5_ENVELOPE_INDEX = "data/macro-foundation/envelopes-v5/envelope-index.json"
V5_HANDOFFS = "data/macro-foundation/regional-handoffs.json.gz"
V5_HIERARCHY = "data/hierarchy.json"
V5_CERTIFICATE = "data/macro-foundation/macro-certificate.json"
V3_HIERARCHY_ARCHIVE = "data/macro-foundation/predecessor-inspections/4cd48d8704e3510a6cacef89838704e04f2a9ee886570852aa2ed940e175cafa/hierarchy.json.gz"
V3_ENVELOPE_INDEX = "data/macro-foundation/envelopes-v3/envelope-index.json"
V5_HIERARCHY_ARCHIVE = "data/macro-foundation/predecessor-inspections/beb2739a65c67f01a65deab96ebf209a159b257453e156ef590106e1f1c9a348/hierarchy.json.gz"
V5_REGION = "framework:region:western-south-america:7fe9d26228d5"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def git_blob(root, commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root)


def json_bytes(data, label):
    try:
        return json.loads(data)
    except Exception as exc:
        raise ValueError(f"Invalid JSON artifact {label}: {exc}") from exc


def validate_claimed_pins(scope, assessment, actual):
    """Pure assertions used by the positive verifier and mutation controls."""
    release = scope["release"]
    original = scope["original_scope_release"]
    pins = assessment["release_pins"]
    claimed_hashes = {
        "scope.member_location_ids_sha256": scope.get("member_location_ids_sha256"),
        "scope.release.hierarchy_sha256": scope["release"].get("hierarchy_sha256"),
        "scope.release.footprints_sha256": scope["release"].get("footprints_sha256"),
        "scope.original_scope_release.hierarchy_sha256": scope["original_scope_release"].get("hierarchy_sha256"),
        "scope.original_scope_release.footprints_sha256": scope["original_scope_release"].get("footprints_sha256"),
        "scope.macro_certificate_sha256": scope.get("macro_certificate_sha256"),
        "scope.frozen_region_geometry_sha256": scope.get("frozen_region_geometry_sha256"),
        "scope.frozen_region_member_ids_sha256": scope.get("frozen_region_member_ids_sha256"),
        **{f"assessment.release_pins.{key}": value for key, value in pins.items() if key.endswith("_sha256")},
    }
    for name, digest in {**actual, **claimed_hashes}.items():
        if name.endswith("_sha256"):
            require(re.fullmatch(r"[a-f0-9]{64}", digest or "") is not None,
                    f"Actual {name} must be a 64-character SHA-256")
    require(release["id"] == actual["release"] and release["version"] == actual["release_version"],
            "Scope V5 release identity/version differs from assigned V5 release")
    require(scope.get("region_id") == V5_REGION, "Frozen scope region identity differs from assigned V5 region")
    require(release["hierarchy_sha256"] == actual["hierarchy_sha256"],
            "Scope V5 hierarchy pin differs from actual assigned V5 hierarchy bytes")
    require(release["footprints_sha256"] == actual["footprints_sha256"],
            "Scope V5 footprint pin differs from assigned V5 release catalog")
    require(original["id"] == actual["original_release"] and original["version"] == actual["original_release_version"],
            "Original scope release identity/version differs from assigned V5 catalog")
    require(original["hierarchy_sha256"] == actual["original_hierarchy_sha256"],
            "Original scope hierarchy pin differs from retained original hierarchy bytes")
    require(original["footprints_sha256"] == actual["original_footprints_sha256"],
            "Original scope footprint pin differs from assigned V5 catalog")
    expected_pins = {
        "release": actual["release"],
        "hierarchy_sha256": actual["hierarchy_sha256"],
        "footprints_sha256": actual["footprints_sha256"],
        "macro_certificate_sha256": actual["macro_certificate_sha256"],
        "region_geometry_sha256": actual["region_geometry_sha256"],
        "region_member_ids_sha256": actual["region_member_ids_sha256"],
    }
    require(pins == expected_pins, "Assessment release pins differ from the verified V5 artifacts")
    require(scope["macro_certificate_sha256"] == actual["macro_certificate_sha256"],
            "Scope macro-certificate pin differs from actual V5 certificate bytes")
    require(scope["frozen_region_geometry_sha256"] == actual["region_geometry_sha256"],
            "Frozen region geometry pin differs from the assigned V5 envelope")
    require(scope["frozen_region_member_ids_sha256"] == actual["region_member_ids_sha256"],
            "Frozen region member-ID pin differs from the assigned V5 envelope")
    ids = scope["member_location_ids"]
    scope_hash = sha("\n".join(sorted(ids)).encode())
    require(len(ids) == 228 and len(set(ids)) == 228, "Issue 496 exact 228-ID roster is not unique/complete")
    require(scope["member_location_ids_sha256"] == scope_hash, "Scope's assigned 228-ID hash is malformed or stale")
    require(assessment["scope"]["member_count"] == 228 and assessment["scope"]["scope_sha256"] == scope_hash,
            "Assessment scope does not match the exact assigned 228-ID roster")
    return expected_pins


def load_v5_context(root, scope, assessment):
    root = pathlib.Path(root)
    require(subprocess.run(["git", "merge-base", "--is-ancestor", V5_COMMIT, "HEAD"], cwd=root,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
            "Pinned V5 evidence commit must be an ancestor of the working branch")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", SCOPE_COMMIT, "HEAD"], cwd=root,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
            "Pinned issue scope baseline commit must be an ancestor of the working branch")
    scope_raw = git_blob(root, SCOPE_COMMIT, SCOPE_PATH)
    require(sha(scope_raw) == SCOPE_SHA256 and sha((root / SCOPE_PATH).read_bytes()) == SCOPE_SHA256,
            "Issue scope bytes differ from the pinned original issue-scope baseline")
    catalog_raw = git_blob(root, V5_COMMIT, RELEASE_CATALOG)
    catalog = json_bytes(gzip.decompress(catalog_raw), RELEASE_CATALOG)
    releases = catalog["releases"]
    v5_rows = [row for row in releases if row["id"] == scope["release"]["id"]]
    v3_rows = [row for row in releases if row["id"] == scope["original_scope_release"]["id"]]
    require(len(v5_rows) == 1 and len(v3_rows) == 1, "Assigned V5/V3 release IDs must resolve exactly once")
    v5, v3 = v5_rows[0], v3_rows[0]
    hierarchy_raw = git_blob(root, V5_COMMIT, V5_HIERARCHY)
    hierarchy_sha = sha(hierarchy_raw)
    envelope_index_raw = git_blob(root, V5_COMMIT, V5_ENVELOPE_INDEX)
    envelope_index = json_bytes(envelope_index_raw, V5_ENVELOPE_INDEX)
    handoffs_raw = git_blob(root, V5_COMMIT, V5_HANDOFFS)
    handoffs = json_bytes(gzip.decompress(handoffs_raw), V5_HANDOFFS)
    handoff_rows = handoffs.get("regions", []) if isinstance(handoffs, dict) else handoffs
    handoff = next((row for row in handoff_rows if row.get("region_id") == V5_REGION), None)
    require(handoff is not None, "Assigned V5 regional handoff is absent")
    envelope = handoff["envelope"]
    group = next((row for row in envelope_index["groups"] if row["id"] == V5_REGION), None)
    require(group is not None, "Assigned V5 region envelope is absent from the V5 envelope index")
    require(group["path"] == envelope["path"] and group["sha256"] == envelope["sha256"] and
            group["geometry_sha256"] == envelope["geometry_sha256"] and
            group["member_location_ids_sha256"] == envelope["member_location_ids_sha256"],
            "V5 envelope index and regional handoff disagree")
    envelope_blob = git_blob(root, V5_COMMIT,
                             f"data/macro-foundation/envelopes-v5/{group['path']}")
    envelope_unpacked = gzip.decompress(envelope_blob)
    require(sha(envelope_blob) == group["sha256"] and sha(envelope_unpacked) == group["geometry_sha256"],
            "V5 region envelope bytes do not match assigned hashes")
    certificate_raw = git_blob(root, V5_COMMIT, V5_CERTIFICATE)
    certificate = json_bytes(certificate_raw, V5_CERTIFICATE)
    original_archive = (root / V3_HIERARCHY_ARCHIVE).read_bytes()
    original_hierarchy = gzip.decompress(original_archive)
    original_index = json_bytes((root / V3_ENVELOPE_INDEX).read_bytes(), V3_ENVELOPE_INDEX)
    actual = {
        "release": v5["id"],
        "release_version": v5["version"],
        "hierarchy_sha256": hierarchy_sha,
        "footprints_sha256": v5["footprints_sha256"],
        "macro_certificate_sha256": sha(certificate_raw),
        "region_geometry_sha256": sha(envelope_unpacked),
        "region_member_ids_sha256": group["member_location_ids_sha256"],
        "original_release": v3["id"],
        "original_release_version": v3["version"],
        "original_hierarchy_sha256": sha(original_hierarchy),
        "original_footprints_sha256": v3["footprints_sha256"],
    }
    require(v5["hierarchy_sha256"] == hierarchy_sha == envelope_index["hierarchy_sha256"],
            "V5 release catalog, actual hierarchy bytes, and envelope hierarchy pin disagree")
    require(v5["version"] == 5, "Assigned release is not version 5")
    require(v5["id"] == certificate["release"]["id"] and
            v5["version"] == certificate["release"]["version"] and
            v5["hierarchy_sha256"] == certificate["release"]["hierarchy_sha256"] and
            v5["footprints_sha256"] == certificate["release"]["footprints_sha256"],
            "V5 macro certificate and V5 release catalog disagree")
    require(v3["hierarchy_sha256"] == actual["original_hierarchy_sha256"] == original_index["hierarchy_sha256"],
            "Original V3 release catalog, retained hierarchy bytes and envelope index disagree")
    require(original_index.get("groups"), "Original V3 envelope index has no groups")
    pins = validate_claimed_pins(scope, assessment, actual)
    artifacts = [
        {"commit": V5_COMMIT, "path": RELEASE_CATALOG, "bytes": len(catalog_raw), "sha256": sha(catalog_raw),
         "uncompressed_bytes": len(gzip.decompress(catalog_raw)), "uncompressed_sha256": sha(gzip.decompress(catalog_raw))},
        {"commit": V5_COMMIT, "path": V5_HIERARCHY, "bytes": len(hierarchy_raw), "sha256": sha(hierarchy_raw)},
        {"commit": V5_COMMIT, "path": V5_CERTIFICATE, "bytes": len(certificate_raw), "sha256": sha(certificate_raw)},
        {"commit": V5_COMMIT, "path": V5_ENVELOPE_INDEX, "bytes": len(envelope_index_raw), "sha256": sha(envelope_index_raw)},
        {"commit": V5_COMMIT, "path": V5_HANDOFFS, "bytes": len(handoffs_raw), "sha256": sha(handoffs_raw),
         "uncompressed_bytes": len(gzip.decompress(handoffs_raw)), "uncompressed_sha256": sha(gzip.decompress(handoffs_raw))},
        {"commit": V5_COMMIT, "path": f"data/macro-foundation/envelopes-v5/{group['path']}",
         "bytes": len(envelope_blob), "sha256": sha(envelope_blob), "uncompressed_bytes": len(envelope_unpacked),
         "uncompressed_sha256": sha(envelope_unpacked)},
        {"commit": "PR-base", "path": V3_HIERARCHY_ARCHIVE, "bytes": len(original_archive),
         "sha256": sha(original_archive), "uncompressed_bytes": len(original_hierarchy),
         "uncompressed_sha256": sha(original_hierarchy)},
        {"commit": "PR-base", "path": V3_ENVELOPE_INDEX,
         "bytes": len((root / V3_ENVELOPE_INDEX).read_bytes()), "sha256": sha((root / V3_ENVELOPE_INDEX).read_bytes())},
        {"commit": SCOPE_COMMIT, "path": SCOPE_PATH, "bytes": len(scope_raw), "sha256": sha(scope_raw)},
    ]
    audit = {
        "version": 1,
        "status": "passed",
        "issue": 579,
        "assigned_packet_issue": 496,
        "assigned_v5_commit": V5_COMMIT,
        "v5_release_id": v5["id"],
        "v5_release_version": v5["version"],
        "original_scope_release_id": v3["id"],
        "original_scope_release_version": v3["version"],
        "actual_pins": actual,
        "assessment_pins": pins,
        "scope": {
            "assigned_count": len(scope["member_location_ids"]),
            "scope_sha256": scope["member_location_ids_sha256"],
            "region_id": V5_REGION,
            "v5_region_location_count": envelope["locations"],
            "region_geometry_sha256": envelope["geometry_sha256"],
            "region_member_location_ids_sha256": envelope["member_location_ids_sha256"],
        },
        "artifacts": artifacts,
        "limits": [
            "This checks release, hierarchy, macro-certificate and frozen scope pins; it does not approve regional semantics or boundaries.",
            "The original Ecuador/Peru administrative, settlement, GSHHG, island and neighbor findings remain those of the preserved #496 packet.",
        ],
    }
    return actual, audit


def negative_controls(scope, assessment, actual):
    import copy
    controls = []
    bad_assessment = copy.deepcopy(assessment)
    bad_assessment["release_pins"]["hierarchy_sha256"] = actual["hierarchy_sha256"][:-1]
    try:
        validate_claimed_pins(scope, bad_assessment, actual)
    except ValueError:
        controls.append({"id": "reject-malformed-hierarchy-hash", "outcome": "passed"})
    else:
        raise ValueError("Negative control failed: malformed hierarchy hash was accepted")
    bad_actual = dict(actual)
    bad_actual["hierarchy_sha256"] = "0" * 64
    try:
        validate_claimed_pins(scope, assessment, bad_actual)
    except ValueError:
        controls.append({"id": "reject-actual-baseline-hash-mismatch", "outcome": "passed"})
    else:
        raise ValueError("Negative control failed: mismatched actual hierarchy baseline was accepted")
    bad_scope = copy.deepcopy(scope)
    bad_scope["release"]["id"] = actual["original_release"]
    try:
        validate_claimed_pins(bad_scope, assessment, actual)
    except ValueError:
        controls.append({"id": "reject-release-identity-mismatch", "outcome": "passed"})
    else:
        raise ValueError("Negative control failed: mismatched release identity was accepted")
    bad_scope = copy.deepcopy(scope)
    bad_scope["member_location_ids_sha256"] = "0" * 64
    try:
        validate_claimed_pins(bad_scope, assessment, actual)
    except ValueError:
        controls.append({"id": "reject-frozen-scope-hash-mismatch", "outcome": "passed"})
    else:
        raise ValueError("Negative control failed: mismatched frozen scope hash was accepted")
    require(len(controls) == 4, "Not all negative controls ran")
    return controls


def v5_world_inventory(root, scope, assessment):
    """Check every assigned row/chain against the frozen V5 world index and hierarchy."""
    root = pathlib.Path(root)
    index_raw = git_blob(root, V5_COMMIT, "data/world-index.json")
    index = json_bytes(index_raw, "data/world-index.json")
    locations = {}
    part_artifacts = []
    for relpath in index["parts"]:
        path = f"data/{relpath}"
        raw = git_blob(root, V5_COMMIT, path)
        part = json_bytes(raw, path)
        for feature in part["features"]:
            location_id = feature["properties"]["id"]
            require(location_id not in locations, f"Duplicate V5 location ID: {location_id}")
            locations[location_id] = feature
        part_artifacts.append({"path": path, "bytes": len(raw), "sha256": sha(raw),
                               "git_blob": subprocess.check_output(["git", "rev-parse", f"{V5_COMMIT}:{path}"], cwd=root, text=True).strip()})
    hierarchy_raw = git_blob(root, V5_COMMIT, V5_HIERARCHY)
    hierarchy = {row["id"]: row for row in json_bytes(hierarchy_raw, V5_HIERARCHY)}
    expected_ids = set(scope["member_location_ids"])
    require(len(locations) == 49625, "Assigned V5 world index has an unexpected location count")
    require(expected_ids <= set(locations), f"Assigned IDs missing from V5 index: {sorted(expected_ids-set(locations))[:5]}")
    assessment_rows = {row["location_id"]: row for row in assessment["locations"]}
    require(set(assessment_rows) == expected_ids, "Assessment subject set differs from exact issue scope")
    region_id = scope["region_id"]
    region_members = []
    descendants = {}
    province_ids = set()
    area_ids = set()
    for location_id, feature in locations.items():
        pid = feature["properties"].get("parent_id")
        seen = set()
        while pid and pid not in seen:
            if pid == region_id:
                region_members.append(location_id)
                break
            seen.add(pid)
            node = locations.get(pid, {}).get("properties") or hierarchy.get(pid)
            if node is None:
                break
            descendants.setdefault(pid, []).append(location_id)
            pid = node.get("parent_id")
    member_digest = sha(json.dumps(sorted(region_members), ensure_ascii=False, separators=(",", ":")).encode())
    require(len(region_members) == 1667, "V5 region membership count differs from frozen handoff")
    require(member_digest == scope["frozen_region_member_ids_sha256"],
            "Reconstructed V5 region member IDs differ from the frozen scope hash")
    for area in scope["area_scopes"]:
        descendants_here = descendants.get(area["id"], [])
        assigned_here = len(expected_ids.intersection(descendants_here))
        require(len(descendants_here) == area["full_area_location_count"] and
                assigned_here == area["owned_member_location_count"],
                f"V5 area workload count mismatch: {area['id']}")
    scopes_by_id = {row["id"]: row for row in scope["province_scopes"]}
    for location_id in sorted(expected_ids):
        feature = locations[location_id]
        pid = feature["properties"].get("parent_id")
        expected_chain = []
        seen = set()
        while pid:
            require(pid not in seen, f"V5 parent cycle at {location_id}")
            seen.add(pid)
            node = locations.get(pid, {}).get("properties") or hierarchy.get(pid)
            if node is None:
                expected_chain.append({"id": pid, "missing_from_pinned_records": True})
                break
            level = node.get("level", "location" if pid in locations else None)
            if level == "province": province_ids.add(pid)
            if level == "area": area_ids.add(pid)
            expected_chain.append({"id": pid, "name": node.get("name"),
                                   "level": level, "parent_id": node.get("parent_id"),
                                   "metadata": node.get("metadata", {})})
            pid = node.get("parent_id")
        require(assessment_rows[location_id]["full_parent_chain"] == expected_chain,
                f"Assessment full parent chain differs from assigned V5 source: {location_id}")
    require(len(area_ids) == len(scope["area_scopes"]) and len(province_ids) == len(scope["province_scopes"]),
            "Scope does not enumerate each assigned V5 area/province")
    require(set(scopes_by_id) == province_ids, "V5 assigned province set differs from the exact scope")
    for province_id, row in scopes_by_id.items():
        require(len(descendants.get(province_id, [])) == row["full_province_locations"],
                f"V5 full province member count mismatch: {province_id}")
    require({row["id"] for row in assessment["parents"]} == area_ids | province_ids,
            "Assessment parent inventory does not exactly cover assigned V5 areas/provinces")
    return {
        "v5_world_index_sha256": sha(index_raw),
        "v5_world_index_parts": len(index["parts"]),
        "v5_location_count": len(locations),
        "assigned_subjects": len(expected_ids),
        "assigned_subjects_present": len(expected_ids.intersection(locations)),
        "parent_chains_revalidated": len(expected_ids),
        "region_member_count_reconstructed": len(region_members),
        "region_member_ids_sha256_reconstructed": member_digest,
        "areas_revalidated": len(area_ids),
        "provinces_revalidated": len(province_ids),
        "part_artifacts": part_artifacts,
    }


def v5_footprints_sha256(root):
    """Reproduce the repository's canonical Node footprint hash on the pinned V5 tree."""
    script = r'''
const cp=require('node:child_process'),crypto=require('node:crypto'),commit=process.argv[1];
const show=p=>cp.execFileSync('git',['show',`${commit}:${p}`],{cwd:process.cwd(),maxBuffer:128*1024*1024});
const world=JSON.parse(show('data/world-index.json'));const features=[];
for(const part of world.parts){const parsed=JSON.parse(show(`data/${part}`));for(const f of parsed.features)features.push([f.properties.id,f.geometry]);}
features.sort((a,b)=>a[0].localeCompare(b[0]));
process.stdout.write(JSON.stringify({count:features.length,sha256:crypto.createHash('sha256').update(JSON.stringify(features)).digest('hex')}));
'''
    result = json.loads(subprocess.check_output(["node", "-e", script, V5_COMMIT], cwd=root, text=True))
    return result
