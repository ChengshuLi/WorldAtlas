#!/usr/bin/env python3
"""Reconstruct and verify #134's immutable source paths and release pins."""
from __future__ import annotations
import gzip, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PARENT_EVIDENCE_COMMIT = "3d2c5cee2fa748a7eff90051088b6998c9c84968"
PARENT_PACKET = "data/regional-review/regional-review-a5b86fc6ff2463cd"
EXPECTED_BASELINE_COMMIT = "dd83dcad2ec486b89844a78e5e137935b101c167"
EXPECTED_REGION = "atlas:macro-review:region:3f0693a087ae4902"
EXPECTED_CONTAINING_FILE_SHA256 = {
    "data/geography/part-23.json": "d61082ccd69b319723fadc4cad582b8d5c8a8ced3e50b4f90f00b4eb17e6a9c2",
    "data/geography/part-24.json": "b816b89f2d6b9e4aed1bca44748e1ca74e775a8f850793c7b3e8751d88a9705c",
    "data/geography/part-28.json": "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d",
}
PUBLICATION_PATH = "data/validation/macro-publication-v5.json"
GATE_PATH = "data/research-geography-gate.json"

class PinError(ValueError):
    pass

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()

def git_blob(commit: str, path: str) -> bytes:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise PinError(f"missing pinned Git object {commit}:{path}") from exc

def pinned_blob(commit: str, path: str, reader=git_blob) -> bytes:
    """Read bytes and confirm they are exactly the blob named by the commit tree."""
    raw = reader(commit, path)
    try:
        expected = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", f"{commit}:{path}"], text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError as exc:
        raise PinError(f"pinned commit has no tree entry for {path}") from exc
    git_blob_bytes = b"blob " + str(len(raw)).encode() + b"\0" + raw
    actual = hashlib.sha1(git_blob_bytes).hexdigest()
    if actual != expected:
        raise PinError(f"input bytes do not match immutable Git blob {commit}:{path}")
    return raw

def git_commit_record(commit: str) -> dict:
    try:
        line = subprocess.check_output(["git", "-C", str(ROOT), "show", "-s", "--format=%H%x09%cI%x09%s", commit], text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError as exc:
        raise PinError(f"baseline commit is not available: {commit}") from exc
    sha_value, committed_at, subject = line.split("\t", 2)
    return {"sha": sha_value, "committed_at": committed_at, "subject": subject}

def load_json(raw: bytes, label: str):
    try:
        return json.loads(raw)
    except Exception as exc:
        raise PinError(f"invalid JSON in {label}: {exc}") from exc

def issue_spec(issue_doc: dict) -> dict:
    if issue_doc.get("number") != 134:
        raise PinError("pinned workload issue is not #134")
    matches = re.findall(r"```json\s*(\{.*?\})\s*```", issue_doc.get("body", ""), re.S)
    if len(matches) != 1:
        raise PinError("#134 must contain exactly one machine scope JSON block")
    spec = load_json(matches[0].encode(), "#134 pinned scope")
    work = re.findall(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", issue_doc.get("body", ""), re.S)
    if len(work) != 1:
        raise PinError("#134 must contain exactly one machine-readable geography work block")
    policy = load_json(work[0].encode(), "#134 machine work scope")
    if spec.get("owned_evidence_path") != PARENT_PACKET + "/" or spec.get("batch_id") != "regional-review:a5b86fc6ff2463cd":
        raise PinError("#134 workload identity/owned path changed")
    if policy.get("mode") != "geography" or policy.get("max_prs") != 2 or policy.get("owned_paths") != [PARENT_PACKET + "/"]:
        raise PinError("#134 machine lane/PR/owned-path scope changed")
    return spec

def check_scope_pins(issue_doc: dict, baseline: dict, cert: dict, publication: dict, gate: dict, handoffs: dict, inventory: list, envelope_bytes: bytes, hierarchy_bytes: bytes) -> dict:
    spec = issue_spec(issue_doc)
    ids = spec.get("member_location_ids")
    if not isinstance(ids, list) or len(ids) != 24 or len(set(ids)) != 24:
        raise PinError("#134 exact 24-member scope is absent or duplicated")
    if sorted(ids) != sorted(baseline.get("scope_location_ids", [])):
        raise PinError("issue member IDs differ from the frozen baseline IDs")
    member_sha = sha("\n".join(sorted(ids)).encode())
    if spec.get("member_location_ids_sha256") != member_sha:
        raise PinError("issue scope member hash does not match its 24 exact IDs")
    if spec.get("region_id") != EXPECTED_REGION or baseline.get("region", {}).get("id") != EXPECTED_REGION:
        raise PinError("issue/baseline region identity mismatch")

    active_release = spec.get("release")
    cert_release = cert.get("release")
    publication_release = publication.get("release")
    gate_release = gate.get("macro_boundaries", {}).get("approved_release")
    for label, value in (("certificate", cert_release), ("publication", publication_release), ("research gate", gate_release)):
        if value != active_release:
            raise PinError(f"issue release pins mismatch {label}")
    if active_release.get("hierarchy_sha256") != sha(hierarchy_bytes):
        raise PinError("issue hierarchy pin does not match frozen hierarchy bytes")
    cert_hash = sha(git_blob(EXPECTED_BASELINE_COMMIT, "data/macro-foundation/macro-certificate.json"))
    if spec.get("macro_certificate_sha256") != cert_hash or publication.get("macro_certificate_sha256") != cert_hash:
        raise PinError("issue/publication macro certificate hash mismatch")
    if gate.get("macro_boundaries", {}).get("macro_certificate_sha256") != cert_hash:
        raise PinError("research gate macro certificate hash mismatch")
    if not publication.get("published") or publication.get("release") != cert_release:
        raise PinError("release publication verification does not match pinned release")
    if gate.get("macro_boundaries", {}).get("publication_verified") is not True:
        raise PinError("research gate does not verify the pinned publication")

    region_rows = [r for r in handoffs.get("regions", []) if r.get("region_id") == EXPECTED_REGION]
    if len(region_rows) != 1:
        raise PinError("pinned region must occur once in regional handoffs")
    region = region_rows[0]
    env = region.get("envelope", {})
    if env.get("geometry_sha256") != spec.get("frozen_region_geometry_sha256"):
        raise PinError("issue frozen geometry hash does not match regional handoff")
    if env.get("member_location_ids_sha256") != spec.get("frozen_region_member_ids_sha256"):
        raise PinError("issue frozen region member hash does not match regional handoff")
    if sha(envelope_bytes) != env.get("sha256"):
        raise PinError("frozen envelope compressed bytes do not match handoff hash")
    try:
        geometry_hash = sha(gzip.decompress(envelope_bytes))
    except OSError as exc:
        raise PinError("frozen envelope is not valid gzip") from exc
    if geometry_hash != env.get("geometry_sha256"):
        raise PinError("frozen envelope geometry bytes do not match handoff hash")
    member_rows = [r for r in inventory if r.get("id") == EXPECTED_REGION]
    if len(member_rows) != 1:
        raise PinError("pinned region must occur once in current membership inventory")
    region_members = sorted(member_rows[0].get("member_location_ids", []))
    if sha(canonical(region_members)) != env.get("member_location_ids_sha256"):
        raise PinError("regional membership inventory differs from frozen member hash")
    if not set(ids).issubset(region_members):
        raise PinError("issue scope includes IDs outside its frozen region")
    return {"issue_scope_member_count": len(ids), "issue_scope_member_sha256": member_sha,
            "region_member_count": len(region_members), "region_only_member_ids": sorted(set(region_members)-set(ids)),
            "release": active_release, "macro_certificate_sha256": cert_hash,
            "region_envelope_sha256": env["sha256"], "region_geometry_sha256": geometry_hash,
            "region_member_location_ids_sha256": env["member_location_ids_sha256"]}

def collect(read_blob=git_blob, issue_override=None) -> dict:
    baseline_commit = EXPECTED_BASELINE_COMMIT
    commit_info = git_commit_record(baseline_commit)
    try:
        names = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-r", "-z", "--name-only", PARENT_EVIDENCE_COMMIT, "--", PARENT_PACKET], stderr=subprocess.PIPE).split(b"\0")
    except subprocess.CalledProcessError as exc:
        raise PinError("cannot inventory the preserved parent evidence packet") from exc
    parent_paths = sorted(x.decode("utf-8") for x in names if x)
    if len(parent_paths) < 10 or any(not p.startswith(PARENT_PACKET + "/") for p in parent_paths):
        raise PinError("preserved parent packet Git tree is incomplete or escaped its owned directory")
    parent_files = {}
    for path in parent_paths:
        raw = pinned_blob(PARENT_EVIDENCE_COMMIT, path, read_blob)
        parent_files[path] = {"bytes": len(raw), "sha256": sha(raw)}
    issue_raw = pinned_blob(PARENT_EVIDENCE_COMMIT, f"{PARENT_PACKET}/issue-metadata.json", read_blob)
    if issue_override is not None:
        issue_doc = issue_override
    else:
        issue_doc = load_json(issue_raw, "preserved #134 issue snapshot")
    baseline_raw = pinned_blob(PARENT_EVIDENCE_COMMIT, f"{PARENT_PACKET}/baseline-extract.json", read_blob)
    baseline = load_json(baseline_raw, "preserved #134 baseline extract")
    assessment = load_json(pinned_blob(PARENT_EVIDENCE_COMMIT, f"{PARENT_PACKET}/assessment.json", read_blob), "preserved #134 assessment")
    if baseline.get("baseline_commit") != baseline_commit or assessment.get("baseline_commit") != baseline_commit:
        raise PinError("assessment and baseline extract must name the same frozen baseline commit")
    if baseline_commit != EXPECTED_BASELINE_COMMIT:
        raise PinError("unexpected historical baseline; create an explicitly versioned new campaign")

    # Verify every provenance row the original packet claimed. This checks its
    # hashes but does not assume its containing-file list is complete.
    legacy_files = []
    for row in baseline.get("baseline_files", []):
        raw = pinned_blob(baseline_commit, row["path"], read_blob)
        actual = {"path": row["path"], "bytes": len(raw), "sha256": sha(raw),
                  "recorded_bytes": row["bytes"], "recorded_sha256": row["sha256"],
                  "recorded_hash_matches": len(raw) == row["bytes"] and sha(raw) == row["sha256"]}
        if not actual["recorded_hash_matches"]:
            raise PinError(f"original packet's recorded baseline input changed: {row['path']}")
        legacy_files.append(actual)

    world_index_path = "data/world-index.json"
    world_index_raw = pinned_blob(baseline_commit, world_index_path, read_blob)
    world_index = load_json(world_index_raw, world_index_path)
    ids = set(baseline["scope_location_ids"])
    if len(ids) != 24:
        raise PinError("the frozen baseline must contain exactly 24 assigned IDs")
    located = {i: [] for i in ids}
    containing_files = []
    indexed_source_files = []
    for index_path in world_index.get("parts", []):
        if not isinstance(index_path, str) or index_path.startswith("/") or ".." in Path(index_path).parts:
            raise PinError("world index contains an unsafe source path")
        path = "data/" + index_path
        raw = pinned_blob(baseline_commit, path, read_blob)
        indexed_source_files.append({"path": path, "bytes": len(raw), "sha256": sha(raw)})
        features = load_json(raw, path).get("features", [])
        hits = []
        for feature in features:
            ident = feature.get("id", feature.get("properties", {}).get("id"))
            if ident in ids:
                located[ident].append((path, feature))
                hits.append(ident)
        if hits:
            containing_files.append({"path": path, "bytes": len(raw), "sha256": sha(raw), "feature_ids": sorted(hits)})
    missing = sorted(i for i, rows in located.items() if not rows)
    duplicate = sorted(i for i, rows in located.items() if len(rows) != 1)
    if missing or duplicate:
        raise PinError(f"world-index source crosswalk is incomplete/ambiguous; missing={missing}, duplicate={duplicate}")
    if len(containing_files) != 3:
        raise PinError("expected the frozen 24 identities to resolve to the three observed source files")
    actual_source_pins = {row["path"]: row["sha256"] for row in containing_files}
    if actual_source_pins != EXPECTED_CONTAINING_FILE_SHA256:
        raise PinError("frozen containing-source path/hash inventory changed")

    crosswalk_rows = []
    for ident in sorted(ids):
        path, feature = located[ident][0]
        stored_feature = baseline["locations"].get(ident)
        if stored_feature != feature:
            raise PinError(f"inline baseline feature differs from actual source feature: {ident}")
        props = feature.get("properties", {})
        crosswalk_rows.append({"location_id": ident, "name": props.get("name"), "parent_id": props.get("parent_id"),
            "containing_path": path, "source_file_sha256": next(x["sha256"] for x in containing_files if x["path"] == path),
            "source_file_bytes": next(x["bytes"] for x in containing_files if x["path"] == path),
            "feature_sha256_canonical_json": sha(canonical(feature)), "feature_type": feature.get("geometry", {}).get("type"),
            "legacy_part_property_present": "part" in props})
    if any(row["legacy_part_property_present"] for row in crosswalk_rows):
        raise PinError("expected issue #619's diagnosed absent part property to remain absent in the frozen inputs")

    # Read and pin all release-critical and source-crosswalk inputs at the same baseline.
    baseline_file_paths = sorted({r["path"] for r in legacy_files} | {x["path"] for x in indexed_source_files} | {world_index_path})
    region_row = baseline["region"]["envelope"]
    envelope_path = f"data/macro-foundation/envelopes-v5/{region_row['path']}"
    extra_paths = [PUBLICATION_PATH, GATE_PATH, envelope_path]
    pinned_paths = sorted(set(baseline_file_paths + extra_paths))
    inputs = []
    input_data = {}
    for path in pinned_paths:
        raw = pinned_blob(baseline_commit, path, read_blob)
        input_data[path] = raw
        inputs.append({"path": path, "bytes": len(raw), "sha256": sha(raw)})
    def parse_input(path): return load_json(input_data[path], path)
    cert = parse_input("data/macro-foundation/macro-certificate.json")
    publication = parse_input(PUBLICATION_PATH)
    gate = parse_input(GATE_PATH)
    handoffs_raw = input_data["data/macro-foundation/regional-handoffs.json.gz"]
    inventory_raw = input_data["data/macro-foundation/current-membership-inventory.json.gz"]
    try:
        handoffs = json.loads(gzip.decompress(handoffs_raw)); inventory = json.loads(gzip.decompress(inventory_raw))
    except Exception as exc:
        raise PinError(f"invalid gzip JSON release input: {exc}") from exc
    pin_report = check_scope_pins(issue_doc, baseline, cert, publication, gate, handoffs, inventory,
        input_data[envelope_path], input_data["data/hierarchy.json"])

    # Rebuild full location-to-continent chains from the exact baseline sources.
    hierarchy = load_json(input_data["data/hierarchy.json"], "pinned hierarchy")
    units = {x["id"]: x for x in hierarchy}
    chains = {}
    for row in crosswalk_rows:
        ident = row["location_id"]
        chain = [ident]; parent = row["parent_id"]; seen = {ident}
        while parent:
            if parent in seen or parent not in units: raise PinError(f"invalid full parent chain for {ident}: {parent}")
            seen.add(parent); chain.append(parent); parent = units[parent].get("parent_id")
        if chain != [x.get("id") for x in baseline["complete_parent_chains"][ident]]:
            raise PinError(f"stored full parent chain differs from frozen source hierarchy for {ident}")
        chains[ident] = chain
    legacy_paths = {x["path"] for x in legacy_files}
    actual_paths = {x["path"] for x in containing_files}
    return {"version": 1, "issue": 619,
        "parent_issue": 134, "parent_packet_pr": 617,
        "parent_packet_merge_commit": PARENT_EVIDENCE_COMMIT,
        "parent_packet_files": parent_files,
        "baseline_commit": commit_info,
        "baseline_extract_sha256": sha(baseline_raw), "assessment_sha256": parent_files[f"{PARENT_PACKET}/assessment.json"]["sha256"],
        "preserved_parent_issue_snapshot": {"updated_at": issue_doc.get("updated_at"), "sha256": sha(issue_raw), "issue_number": issue_doc.get("number")},
        "issue_scope_pins": pin_report,
        "pinned_baseline_inputs": inputs,
        "legacy_baseline_file_rows": legacy_files,
        "legacy_containing_path_audit": {"recorded_paths": sorted(legacy_paths), "actual_scoped_containing_paths": sorted(actual_paths),
            "false_containing_path_claim": "data/geography/part-0.json does not contain any of the 24 issue IDs; actual containing files are derived from world-index.json and the exact frozen commit"},
        "indexed_geography_sources": sorted(indexed_source_files,key=lambda x:x["path"]),
        "containing_files": sorted(containing_files,key=lambda x:x["path"]),
        "location_source_crosswalk": crosswalk_rows,
        "complete_parent_chains": chains,
        "checks": {"exact_24_issue_ids": True, "all_24_unique_world_index_sources": True,
            "inline_baseline_features_match_frozen_source": True, "all_original_recorded_baseline_file_hashes_match": True,
            "hierarchy_release_certificate_publication_gate_region_envelope_and_membership_pins_match": True,
            "assessment_and_extract_name_same_frozen_commit": True,
            "old_baseline_preserved_and_not_refreshed_from_current_main": True}}

def verify_packet(packet: dict, read_blob=git_blob, crosswalk_override=None, issue_override=None) -> None:
    rows = crosswalk_override if crosswalk_override is not None else packet["location_source_crosswalk"]
    expected_ids = {x["location_id"] for x in packet["location_source_crosswalk"]}
    if len(rows) != 24 or {x.get("location_id") for x in rows} != expected_ids:
        raise PinError("persisted location crosswalk does not account for the exact 24 frozen subjects")
    pinned_inputs = {x["path"]: x for x in packet["pinned_baseline_inputs"]}
    blobs = {}
    for path, pin in pinned_inputs.items():
        raw = pinned_blob(packet["baseline_commit"]["sha"], path, read_blob)
        if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
            raise PinError(f"frozen baseline input bytes/hash changed: {path}")
        blobs[path] = raw
    world_index = load_json(blobs["data/world-index.json"], "pinned world index")
    indexed = ["data/"+p for p in world_index["parts"]]
    if len(indexed) != len(set(indexed)):
        raise PinError("world index contains duplicate source paths")
    indexed_rows = packet.get("indexed_geography_sources", [])
    if [x.get("path") for x in indexed_rows] != sorted(indexed):
        raise PinError("pinned complete world-index geography source inventory differs")
    located = {ident: [] for ident in expected_ids}
    for index_row in indexed_rows:
        path = index_row["path"]
        if path not in blobs:
            raise PinError(f"world-index geography input was not pinned: {path}")
        raw = blobs[path]
        if len(raw) != index_row["bytes"] or sha(raw) != index_row["sha256"]:
            raise PinError(f"world-index geography source inventory hash mismatch: {path}")
        for feature in load_json(raw, path).get("features", []):
            ident = feature.get("id", feature.get("properties", {}).get("id"))
            if ident in located:
                located[ident].append((path, feature))
    if any(len(matches) != 1 for matches in located.values()):
        raise PinError("world-index scan does not resolve every issue subject exactly once")
    for row in rows:
        path = row.get("containing_path")
        matches = located[row["location_id"]]
        if len(matches) != 1 or matches[0][0] != path or sha(canonical(matches[0][1])) != row["feature_sha256_canonical_json"]:
            raise PinError(f"containing path fails feature identity/content check: {row['location_id']}")
        pin = pinned_inputs.get(path)
        if not pin or row.get("source_file_sha256") != pin["sha256"] or row.get("source_file_bytes") != pin["bytes"]:
            raise PinError(f"containing source-file hash/size differs from pinned input: {row['location_id']}")
    for path, pin in packet["parent_packet_files"].items():
        raw = pinned_blob(PARENT_EVIDENCE_COMMIT, path, read_blob)
        if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
            raise PinError(f"preserved parent packet input changed: {path}")
    issue_path = f"{PARENT_PACKET}/issue-metadata.json"
    issue_pin = packet["parent_packet_files"][issue_path]
    issue_raw = pinned_blob(PARENT_EVIDENCE_COMMIT, issue_path, read_blob)
    if len(issue_raw) != issue_pin["bytes"] or sha(issue_raw) != issue_pin["sha256"]:
        raise PinError("preserved original issue metadata bytes changed")
    issue_doc = issue_override if issue_override is not None else load_json(issue_raw, issue_path)
    # Recheck the currently pinned 24 subjects/release against the exact historic source rows.
    base_path = f"{PARENT_PACKET}/baseline-extract.json"
    baseline_raw = pinned_blob(PARENT_EVIDENCE_COMMIT, base_path, read_blob)
    if len(baseline_raw) != packet["parent_packet_files"][base_path]["bytes"] or sha(baseline_raw) != packet["parent_packet_files"][base_path]["sha256"]:
        raise PinError("preserved baseline extract bytes changed")
    if sha(baseline_raw) != packet["baseline_extract_sha256"]:
        raise PinError("preserved baseline extract hash differs from packet pin")
    baseline = load_json(baseline_raw, base_path)
    if baseline.get("baseline_commit") != packet["baseline_commit"]["sha"]:
        raise PinError("stored baseline extract points at a different historical commit")
    legacy_expected = [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in baseline.get("baseline_files", [])]
    legacy_recorded = [{"path": row["path"], "bytes": row["recorded_bytes"], "sha256": row["recorded_sha256"]} for row in packet["legacy_baseline_file_rows"]]
    if legacy_recorded != legacy_expected:
        raise PinError("legacy baseline-file manifest no longer matches original packet")
    baseline_ids = set(baseline.get("scope_location_ids", []))
    if baseline_ids != expected_ids:
        raise PinError("original baseline and pinned location crosswalk have different subjects")
    for row in rows:
        source = load_json(blobs[row["containing_path"]], row["containing_path"])
        feature = next(f for f in source["features"] if f.get("id", f.get("properties", {}).get("id")) == row["location_id"])
        if baseline["locations"].get(row["location_id"]) != feature:
            raise PinError(f"original inline baseline feature differs from pinned source: {row['location_id']}")
    hierarchy = load_json(blobs["data/hierarchy.json"], "pinned hierarchy")
    units = {x["id"]: x for x in hierarchy}
    for ident in sorted(expected_ids):
        props = baseline["locations"][ident]["properties"]
        chain = [ident]; parent = props.get("parent_id"); seen = {ident}
        while parent:
            if parent in seen or parent not in units: raise PinError(f"invalid full parent chain for {ident}: {parent}")
            seen.add(parent); chain.append(parent); parent = units[parent].get("parent_id")
        expected_chain = [x.get("id") for x in baseline["complete_parent_chains"][ident]]
        if chain != expected_chain or packet["complete_parent_chains"].get(ident) != chain:
            raise PinError(f"stored/reconstructed adjacent-tier parent chain mismatch for {ident}")
    if packet["legacy_containing_path_audit"].get("actual_scoped_containing_paths") != sorted({x["containing_path"] for x in rows}):
        raise PinError("legacy-vs-actual containing path audit differs from source crosswalk")
    cert = load_json(blobs["data/macro-foundation/macro-certificate.json"], "macro certificate")
    publication = load_json(blobs[PUBLICATION_PATH], PUBLICATION_PATH)
    gate = load_json(blobs[GATE_PATH], GATE_PATH)
    handoffs = json.loads(gzip.decompress(blobs["data/macro-foundation/regional-handoffs.json.gz"]))
    inventory = json.loads(gzip.decompress(blobs["data/macro-foundation/current-membership-inventory.json.gz"]))
    region_row = baseline["region"]["envelope"]
    envelope_path = f"data/macro-foundation/envelopes-v5/{region_row['path']}"
    actual_pins = check_scope_pins(issue_doc, baseline, cert, publication, gate, handoffs, inventory,
        blobs[envelope_path], blobs["data/hierarchy.json"])
    if actual_pins != packet["issue_scope_pins"]:
        raise PinError("issue/release/region pins differ from the committed evidence packet")
    assessment_path = f"{PARENT_PACKET}/assessment.json"
    assessment_raw = pinned_blob(PARENT_EVIDENCE_COMMIT, assessment_path, read_blob)
    if sha(assessment_raw) != packet["assessment_sha256"]:
        raise PinError("original row-by-row assessment bytes changed")
    assessment = load_json(assessment_raw, assessment_path)
    if assessment.get("baseline_commit") != packet["baseline_commit"]["sha"]:
        raise PinError("assessment baseline commit mismatches frozen baseline")

def write_packet(output: Path = OUT/"baseline-source-crosswalk.json", read_blob=git_blob, issue_override=None) -> dict:
    output = output.resolve()
    if OUT.resolve() not in output.parents:
        raise PinError("output must remain under the issue-owned directory")
    if output.exists():
        raise PinError(f"refusing to overwrite existing evidence output: {output}")
    packet = collect(read_blob=read_blob, issue_override=issue_override)
    verify_packet(packet, read_blob=read_blob, issue_override=issue_override)
    tmp = output.with_suffix(output.suffix+".tmp")
    tmp.write_text(json.dumps(packet, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    tmp.replace(output)
    return packet
