#!/usr/bin/env python3
"""Rebuild the additive #1491 byte/change receipt from immutable main inputs."""

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OWNED = "research/geography/kazakhstan-russia-control-integrity-1334-20261008"
ORIGINAL = "research/geography/kazakhstan-russia-nineteen-gap-family-source-fitness-20261007"
BASE = "016fa2c0cce935382d0995a503bfc09d3e7ac513"
WORKER = "01a10947-b3d7-7812-8b2f-c5a47e88ccb2"
MANIFEST = ROOT / "evidence-quality.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def pinned(path):
    raw = git("show", f"{BASE}:{path}")
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError("baseline file exceeds evidence file cap: " + path)
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def issue_contract():
    issue = json.loads((ROOT / "issue-1491-current.json").read_text())
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{[\s\S]*?\})\s*-->", issue["body"])
    if not match:
        raise ValueError("current issue snapshot lacks its reviewed work contract")
    return json.loads(match.group(1))


def issue_subjects():
    return sorted(issue_contract()["evidence_quality"]["subject_ids"])


def candidate_files():
    paths = set()
    for row in git("diff", "--name-only", "--no-renames", BASE, "--").decode().splitlines():
        if row.startswith(OWNED + "/"):
            paths.add(row)
    for row in git("ls-files", "--others", "--exclude-standard", "--", OWNED).decode().splitlines():
        if row.startswith(OWNED + "/") and (REPO / row).is_file() and not (REPO / row).is_symlink():
            paths.add(row)
    paths.add(OWNED + "/evidence-quality.json")
    return sorted(paths)


def main():
    baseline_paths = [
        "scripts/evidence/immutable.py",
        f"{ORIGINAL}/assessment_controls.py",
        f"{ORIGINAL}/build_assessment.py",
        f"{ORIGINAL}/compare_source_ids.py",
        f"{ORIGINAL}/input-manifest.json",
        f"{ORIGINAL}/source-freeze.json",
        f"{ORIGINAL}/inputs/complete-kazakhstan-russia-handoff.json",
        f"{ORIGINAL}/inputs/atlas/part-12.json",
        f"{ORIGINAL}/inputs/atlas/part-20.json",
        f"{ORIGINAL}/inputs/atlas/part-21.json",
        f"{ORIGINAL}/inputs/geoboundaries-kaz-adm2-2017-full-source.geojson",
        f"{ORIGINAL}/inputs/geoboundaries-kaz-adm2-2017-simplified-full-source.geojson",
        f"{ORIGINAL}/inputs/geoboundaries-rus-adm2-2017-simplified-full-source.geojson",
        f"{ORIGINAL}/inputs/metadata/KAZ-CITATION-AND-USE-geoBoundaries.txt",
        f"{ORIGINAL}/inputs/metadata/KAZ-geoBoundaries-KAZ-ADM2-metaData.json",
        f"{ORIGINAL}/inputs/metadata/RUS-CITATION-AND-USE-geoBoundaries.txt",
        f"{ORIGINAL}/inputs/metadata/RUS-geoBoundaries-RUS-ADM2-metaData.json",
    ]
    for run in (1, 2):
        prefix = f"{ORIGINAL}/executions/run-{run}"
        baseline_paths.extend([
            f"{ORIGINAL}/executions/run-{run}-receipt.json",
            f"{prefix}/output-manifest.json",
            *(f"{prefix}/{name}" for name in (
                "candidate-assessment.jsonl", "contact-lineage.json",
                "family-reconciliation.json", "source-products.json")),
        ])
    baseline_paths.extend(f"{ORIGINAL}/executions/{name}" for name in (
        "positive-control.json", "negative-control.json", "reproducibility-control.json",
        "output-comparison.json", "source-id-comparison.json", "source-id-comparison-receipt.json"))
    files = [pinned(path) for path in sorted(set(baseline_paths))]
    by_path = {row["path"]: row for row in files}
    issue_pins = issue_contract()["evidence_quality"]["pins"]
    pins = {
        "shared_immutable_helper": by_path["scripts/evidence/immutable.py"]["sha256"],
        "original_assessment_producer": by_path[f"{ORIGINAL}/build_assessment.py"]["sha256"],
        "original_input_manifest": by_path[f"{ORIGINAL}/input-manifest.json"]["sha256"],
        "complete_assigned_handoff": by_path[f"{ORIGINAL}/inputs/complete-kazakhstan-russia-handoff.json"]["sha256"],
    }
    pin_files = {
        "shared_immutable_helper": "scripts/evidence/immutable.py",
        "original_assessment_producer": f"{ORIGINAL}/build_assessment.py",
        "original_input_manifest": f"{ORIGINAL}/input-manifest.json",
        "complete_assigned_handoff": f"{ORIGINAL}/inputs/complete-kazakhstan-russia-handoff.json",
    }
    for path, digest in issue_pins.items():
        if path not in by_path or by_path[path]["sha256"] != digest:
            raise ValueError("original issue pin does not match exact baseline bytes: " + path)
        pins[path] = digest
        pin_files[path] = path
    part_paths = [f"{ORIGINAL}/inputs/atlas/part-{n}.json" for n in (12, 20, 21)]
    part_features = {}
    for path in part_paths:
        geo = json.loads(git("show", f"{BASE}:{path}"))
        for feature in geo["features"]:
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in part_features:
                raise ValueError("duplicate source subject in containing files: " + str(identity))
            part_features[identity] = path
    subjects = issue_subjects()
    if any(identity not in part_features for identity in subjects):
        raise ValueError("declared issue subject missing from pinned Atlas parts")
    helper_path = "scripts/evidence/immutable.py"
    baseline = {
        "commit": BASE,
        "files": files,
        "pins": pins,
        "pin_files": pin_files,
        "subject_files": {identity: part_features[identity] for identity in subjects},
    }
    outputs = []
    for path in candidate_files():
        if path == OWNED + "/evidence-quality.json":
            continue
        target = REPO / path
        if not target.is_file() or target.is_symlink():
            raise ValueError("candidate output must be an ordinary file: " + path)
        raw = target.read_bytes()
        outputs.append({"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
    subject_hash = sha(json.dumps(subjects, ensure_ascii=False, separators=(",", ":")).encode())
    sources = [
        {
            "id": "retained-kazakhstan-russia-assessment",
            "url": f"https://github.com/ChengshuLi/WorldAtlas/tree/{BASE}/{ORIGINAL}",
            "role": "Immutable #1334 source-fit context, scoped contact records and prior run products; not boundary authority",
            "vintage": f"Exact main commit {BASE}; original geoBoundaries source vintage 2017 represented year",
            "retrieved_at": "2026-10-08",
            "license": {"status": "unknown", "terms": "Internal repository evidence; underlying source terms are separately recorded in the retained packet and are not independently re-adjudicated here."},
            "retention": "restoration-only", "verification": "verified", "temporal_status": "unknown",
            "restoration": f"Read the exact pinned original packet at {BASE}:{ORIGINAL}; this PR intentionally retains references rather than copying source bytes.",
            "limit": "The prior assessment and reports establish records/custody only. Source role, effective date, legal boundaries, completeness and current applicability remain unresolved.",
        },
        {
            "id": "geoboundaries-kazakhstan-2017-adm2",
            "url": "https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/KAZ/ADM2",
            "role": "Full and simplified KAZ native products used only for a feature identity-set comparison",
            "vintage": "2017 represented source; release commit 9469f09592ced973a3448cf66b6100b741b64c0d; metadata/citation bytes retained in prior packet",
            "retrieved_at": "2026-10-07",
            "license": {"status": "redistributable", "terms": "geoBoundaries records gbOpen CC-BY 4.0 with attribution; retained country metadata records underlying ODbL 1.0. No independent legal opinion or geometry-equivalence finding."},
            "retention": "restoration-only", "verification": "verified", "temporal_status": "unknown",
            "restoration": f"Read exact full/simplified KAZ products and attribution at {BASE}:{ORIGINAL}/inputs/; source bytes remain in the original packet.",
            "limit": "This control verifies 174 unique shapeID values per product and exact set agreement only; it does not compare geometry, prove national completeness, or establish current territorial correspondence.",
        },
        {
            "id": "geoboundaries-russia-2017-full-adm2",
            "url": "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/RUS/ADM2/geoBoundaries-RUS-ADM2.geojson",
            "role": "Previously captured full-resolution Russian source referenced by original identity comparison only",
            "vintage": "2017 represented source; release commit 9469f09592ced973a3448cf66b6100b741b64c0d",
            "retrieved_at": "2026-10-07",
            "license": {"status": "redistributable", "terms": "geoBoundaries gbOpen CC-BY 4.0 attribution; retained country metadata records underlying ODbL 1.0. No independent legal opinion."},
            "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
            "restoration": "Restore only from the exact URL above and verify 120,489,189 bytes and SHA-256 74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0 before any authorized partitioned review.",
            "limit": "The file exceeds the 32 MiB per-file budget and is not loaded or replayed here. Prior identity-comparison receipt remains historical evidence, not a new validation.",
        },
    ]
    validation_root = OWNED + "/vintages/controls-reviewed-two"
    manifest = {
        "version": 1, "issue": 1491, "lane": "geography", "worker_id": WORKER,
        "subject_ids": subjects, "subject_ids_sha256": subject_hash,
        "baseline": baseline, "sources": sources, "outputs": outputs,
        "methods": [
            {"id": "control-integrity", "kind": "code", "description": "Validate exact original issue scope, authenticate the full input-manifest/source-freeze/producer hashes, preserve 28 compatible and 24 partial/unbound classifications from actual rows, join candidate/family/contact records to the immutable handoff, and verify both complete four-product reports against actual manifests and run receipts. Exercise parsed altered-product, scope and Kazakhstan source-ID negative fixtures and exclusive output admission.", "software": "Python 3.12.14; pinned shared immutable helper; standard library", "units": "whole-file SHA-256, bytes, IDs, records, families and contacts"},
            {"id": "kazakhstan-source-identity", "kind": "source", "description": "Parse the complete pinned full and simplified Kazakhstan ADM2 FeatureCollections and compare unique properties.shapeID sets; no geometry equality claim.", "software": "Python 3.12.14; standard library; control_integrity.py", "units": "native feature IDs"},
        ],
        "metrics": [], "summaries": [],
        "conclusions": [
            {"text": "Both retained #1334 producer outputs are byte-authenticated against their complete manifests and original run receipts; actual candidate, family and contact identity joins match the retained handoff. This is custody/control evidence, not proof of the original scientific producer's current behavior.", "status": "supported", "source_ids": ["retained-kazakhstan-russia-assessment"]},
            {"text": "The two 2017 Kazakhstan source files contain identical unique shapeID sets. The underlying Russian full source, geometry equivalence, current boundary correspondence and legal/current completeness remain unresolved.", "status": "unresolved", "source_ids": ["geoboundaries-kazakhstan-2017-adm2", "geoboundaries-russia-2017-full-adm2"]},
        ],
        "stages": {"research": "partial", "implementation": "proposed", "geographic_approval": "unapproved"},
        "commands": [
            f"python3.12 {OWNED}/control_integrity.py --baseline {BASE} --vintage controls-reviewed-one",
            f"python3.12 {OWNED}/control_integrity.py --baseline {BASE} --vintage controls-reviewed-two",
            f"python3.12 {OWNED}/test_control_integrity.py",
        ],
        "validation": [
            {"method_id": "control-integrity", "kind": "positive-control", "outcome": "passed", "evidence_path": f"{validation_root}/positive-control.json"},
            {"method_id": "control-integrity", "kind": "negative-control", "outcome": "passed", "evidence_path": f"{validation_root}/negative-control.json"},
            {"method_id": "control-integrity", "kind": "reproducibility", "outcome": "passed", "evidence_path": f"{validation_root}/reproducibility-control.json"},
        ],
        "change_receipts": [{"path": path, "status": "added"} for path in candidate_files()],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"baseline_files": len(files), "subjects": len(subjects), "candidate_outputs": len(outputs),
                      "change_receipts": len(manifest["change_receipts"]), "manifest": str(MANIFEST)}, sort_keys=True))


if __name__ == "__main__":
    main()
