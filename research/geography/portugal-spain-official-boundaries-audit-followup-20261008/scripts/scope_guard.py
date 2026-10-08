"""Acceptance and output guards for the additive #1482 producer copies."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCOPE_SHA256 = "ca652688f051fbd44bed3cc5a4130bb9b4ada0d3b20667f6b3a91209bd68a6c5"
SUBJECTS = [
    "atlas:district:ESP-2101:def08fa9",
    "gb:ESP:ADM3:28895703B56784737193540",
    "gb:PRT:ADM2:2272694B13078000098594",
    "gb:PRT:ADM2:2272694B82300393258858",
]
FAMILIES = {
    "gap-source-batch:509d6812e22b584f960be362": {
        "physical-component:137a1e1873ef3c0d140480618abd24f8b0125182e0e2c5fbe92242c64ed0cc1a",
        "physical-component:a1ad449c3035d6ee93d8c07ac3eef6292300891765e6ba3a7debe76135dc1b2c",
    },
    "gap-source-batch:4c43b39b2038f22dfdedebce": {
        "physical-component:188a372fefa2333a034123c6a2bb6134f649e44b5be92367725902ea2d568c70",
        "physical-component:3d26d33457b023a510afc6d77bbd5441ddca5cc9ea597be323c9c1d6b728616e",
    },
}
COMPONENTS = [
    "physical-component:137a1e1873ef3c0d140480618abd24f8b0125182e0e2c5fbe92242c64ed0cc1a",
    "physical-component:a1ad449c3035d6ee93d8c07ac3eef6292300891765e6ba3a7debe76135dc1b2c",
    "physical-component:188a372fefa2333a034123c6a2bb6134f649e44b5be92367725902ea2d568c70",
    "physical-component:3d26d33457b023a510afc6d77bbd5441ddca5cc9ea597be323c9c1d6b728616e",
]
INCIDENCES = {
    "gap-source-batch:509d6812e22b584f960be362": {
        "atlas:district:ESP-2101:def08fa9",
        "gb:PRT:ADM2:2272694B13078000098594",
        "gb:PRT:ADM2:2272694B82300393258858",
    },
    "gap-source-batch:4c43b39b2038f22dfdedebce": {
        "gb:ESP:ADM3:28895703B56784737193540",
        "gb:PRT:ADM2:2272694B82300393258858",
    },
}


def load_frozen_scope(path: Path):
    raw = path.read_bytes()
    scope = json.loads(raw)
    if scope.get("subject_ids") != SUBJECTS:
        raise ValueError("Duplicate, missing, or wrong exact subject roster")
    families = scope.get("families")
    if not isinstance(families, list) or len(families) != 2:
        raise ValueError("Frozen family roster mismatch")
    if len({row.get("id") for row in families}) != 2:
        raise ValueError("Duplicate family identity")
    for row in families:
        family = row.get("id")
        components = row.get("component_ids")
        contacts = row.get("contact_subjects")
        if family not in FAMILIES:
            raise ValueError("Unknown family identity")
        if not isinstance(components, list) or len(components) != 2 or len(set(components)) != 2 or set(components) != FAMILIES[family]:
            raise ValueError("Duplicate, missing, or wrong component identity")
        if not isinstance(contacts, list) or len(contacts) != len(INCIDENCES[family]) or len(set(contacts)) != len(contacts) or set(contacts) != INCIDENCES[family]:
            raise ValueError("Duplicate, missing, or wrong family-subject incidence")
    if {row["id"] for row in families} != set(FAMILIES):
        raise ValueError("Missing family identity")
    flat = [subject for row in families for subject in row["contact_subjects"]]
    if len(flat) != 5 or len(set(flat)) != 4 or set(flat) != set(SUBJECTS):
        raise ValueError("Wrong total subject roster or family-incidence count")
    if scope.get("baseline_commit") != "fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7":
        raise ValueError("Wrong baseline reference commit")
    expected_files = {
        SUBJECTS[0]: "data/geography/part-29.json",
        SUBJECTS[1]: "data/geography/part-8.json",
        SUBJECTS[2]: "data/geography/part-19.json",
        SUBJECTS[3]: "data/geography/part-19.json",
    }
    if scope.get("pinned_baseline_subject_files") != expected_files:
        raise ValueError("Wrong subject-to-reference part binding")
    if hashlib.sha256(raw).hexdigest() != SCOPE_SHA256:
        raise ValueError("Frozen source scope hash mismatch")
    return scope


SUBJECT_PARENTS = {
    "atlas:district:ESP-2101:def08fa9": "framework:province:huelva:67e82699c154",
    "gb:ESP:ADM3:28895703B56784737193540": "framework:province:huelva:67e82699c154",
    "gb:PRT:ADM2:2272694B13078000098594": "framework:province:beja:2057344bed65",
    "gb:PRT:ADM2:2272694B82300393258858": "framework:province:beja:2057344bed65",
}


def validate_subject_parents(subjects):
    if set(subjects) != set(SUBJECT_PARENTS):
        raise ValueError("Exact subject identity set required before parent validation")
    for identity, feature in subjects.items():
        parent = (feature.get("properties") or {}).get("parent_id")
        if parent != SUBJECT_PARENTS[identity]:
            raise ValueError("Wrong pinned parent relationship: " + identity)


def capture_tree(repo: Path, source_root: Path):
    """Authenticate the entire original PR #1312 packet before consumption."""
    manifest_path = source_root / "evidence-quality.json"
    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "cb1a3e8d3c88b64807d735b4411423209c117e442073408e827618b83003ecd0":
        raise ValueError("Original source packet manifest hash mismatch")
    manifest = json.loads(raw)
    if manifest.get("issue") != 1299 or manifest.get("lane") != "geography":
        raise ValueError("Original source packet contract mismatch")
    paths = {}
    rows = list(manifest.get("outputs", [])) + [file for source in manifest.get("sources", []) for file in source.get("files", [])]
    unique = {}
    for row in rows:
        path = row.get("path")
        if not isinstance(path, str) or not path.startswith("research/geography/portugal-spain-official-boundaries-20261007/"):
            continue
        previous = unique.get(path)
        current = (row.get("bytes"), row.get("sha256"))
        if previous is not None and previous != current:
            raise ValueError("Original packet has conflicting whole-file descriptors: " + path)
        unique[path] = current
    for path, (expected_bytes, expected_sha256) in unique.items():
        relative = path.split("research/geography/portugal-spain-official-boundaries-20261007/", 1)[1]
        target = source_root / relative
        if target.is_symlink() or not target.is_file():
            raise ValueError("Original packet file missing or unsafe: " + relative)
        body = target.read_bytes()
        if len(body) != expected_bytes or hashlib.sha256(body).hexdigest() != expected_sha256:
            raise ValueError("Original packet evidence changed: " + relative)
        paths[relative] = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    return {"version": 1, "issue": 1482, "original_issue": 1299,
            "source_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "source_packet_commit": "cbae22cc877f6f8a70650069d91d2b34240582f7",
            "files": paths}
