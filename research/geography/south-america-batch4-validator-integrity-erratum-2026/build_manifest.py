#!/usr/bin/env python3
"""Build an exclusive top-level evidence manifest after two complete vintages."""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/south-america-batch4-validator-integrity-erratum-2026"
BASELINE = "e9190786dbf758524a3bde513fc4bb4d1ed6a3e7"
METHOD = "south-america-batch4-validator-integrity-erratum"
MANIFEST = OWNED + "/evidence-quality.json"
REPRO = OWNED + "/reproducibility.json"
RUN_FILES = ["audit.json", "positive-control.json", "negative-control.json",
             "child-roster-controls.json", "execution-bindings.json",
             "legacy-writer-control.json", "run-metadata.json"]
COMPARE_FILES = [name for name in RUN_FILES if name != "run-metadata.json"]
FINAL_RUNS = ["run-five", "run-six"]
ALL_RUNS = ["run-one", "run-two", "run-three", "run-four", *FINAL_RUNS]

ISSUE_PINS = {
    "world-index": ("data/world-index.json", "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03"),
    "hierarchy": ("data/hierarchy.json", "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b"),
    "original-scope": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json", "29a5984b06b96dff899a2c4d16659e63b66f75ab25dd2a744191e0267bc21af8"),
    "original-crosswalk": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/crosswalk.csv", "7a48c634a5e9d817cd3da977e1a023c7ffe0cc88340811817e68333ea2683ece"),
    "original-reproducer": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce.py", "f077ca8ab415b812e9832eb0340037313314be76947575b2ea6bfbafa56f2d0b"),
    "original-manifest": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/evidence-quality.json", "85d43d138de43b4cde705217276e47716e835f5625263f75f9fc729be19d3aa0"),
    "original-summary": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduction-summary.json", "6a417f7419cbdf940aa6c84fe7e62504f2030e2c3399907a6d4ee39efdf3766b"),
    "original-source-register": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json", "1e124f1c15ce6b9396ffd97e2d791b2d7cc995eb7d134f2d6dcfed1f18f235ca"),
    "affected-verifier": ("data/regional-review/southern-south-america-batch4-validation-20261006/verify-packet.py", "12d3154a530f7ece109cc9b1c7b75db86f953bbcf763130ef5b76b01c6369acb"),
    "affected-manifest": ("data/regional-review/southern-south-america-batch4-validation-20261006/evidence-quality.json", "4ef8fb06e41cc7461b2e4c928256bf87b2ea9e6487b72ca324c5e20fccb2d86d"),
    "original-parent-roster": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/province-review.csv", "26fa50de3fa6515fface069755f89b13dc6cb674b41fb95d9abcb9fbd0f91c2f"),
    "affected-issue-snapshot": ("data/regional-review/southern-south-america-batch4-validation-20261006/issue-1116-contract.json", "04419a2a5916c65f46933cbccd5a1dd43147ece8b96b6f402259c9a55b0be961"),
}
EXTRA = {
    "original-area-roster": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-review.csv", "7971335af98f6c8be11ab8699caca7f698384b2dd871983f5059b66da3fad17a"),
    "chile-source-metadata": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/geoBoundaries-CHL-ADM3-metaData.json", "658356bb413f8b284b260360d1309527781e1b0c46027e1ae0a4c58da1c99409"),
    "paraguay-source-metadata": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/geoBoundaries-PRY-ADM2-metaData.json", "d78f4e8a966cf3b077e62a33e8544e8c4bc08aab269da52f3b8d3602875851aa"),
    "original-source-review": ("data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/source-review.md", None),
    "audit-prevention-helper": ("scripts/evidence/immutable.py", "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"),
    "adjacent-manifest-writer": ("data/regional-review/southern-south-america-batch4-validation-20261006/build-manifest.py", "3ec08036828f262dd88b23b654e861b4d35fb1e4942f1340eced0d61adf8b843"),
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git_bytes(commit, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", commit + ":" + path], stderr=subprocess.PIPE)

def descriptor(path, raw, role=None):
    row = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    if role:
        row["role"] = role
    return row

def candidate_descriptor(path, role=None):
    target = ROOT / path
    if target.is_symlink() or not target.is_file():
        raise ValueError("Expected ordinary, non-symlink candidate output: " + path)
    return descriptor(path, target.read_bytes(), role)

def exclusive_write(path, raw):
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError("Refusing to overwrite evidence: " + path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".erratum-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def issue_subjects():
    snapshot = json.loads((ROOT / (OWNED + "/issue-1332-contract.json")).read_bytes())
    issue = snapshot["issue"]
    if issue["issue_number"] != 1332 or issue["state"] != "open":
        raise ValueError("Wrong or closed issue snapshot")
    import re
    marker = re.search(r"<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->", issue["body"])
    if not marker:
        raise ValueError("Issue snapshot lacks work contract")
    spec = json.loads(marker.group(1))
    if spec["owned_paths"] != [OWNED + "/"] or spec["mode"] != "geography" or spec["max_prs"] != 1:
        raise ValueError("Changed issue lane, scope or budget")
    ids = spec["evidence_quality"]["subject_ids"]
    if len(ids) != 215 or len(set(ids)) != 215:
        raise ValueError("Expected exact 215 unique contract subjects")
    return ids

def validate_run(name):
    root = f"{OWNED}/vintages/{name}"
    publication = json.loads((ROOT / root / "publication.json").read_bytes())
    if publication.get("version") != 1 or publication.get("status") != "complete":
        raise ValueError("Run lacks complete final publication receipt")
    expected = set(RUN_FILES)
    rows = publication.get("outputs", [])
    if {Path(row["path"]).name for row in rows} != expected or len(rows) != len(expected):
        raise ValueError("Run receipt has incomplete/extra output inventory")
    for row in rows:
        path = row["path"]
        if not path.startswith(root + "/"):
            raise ValueError("Run receipt escaped its declared vintage")
        actual = candidate_descriptor(path)
        if actual["sha256"] != row["sha256"] or actual["bytes"] != row["bytes"]:
            raise ValueError("Run output differs from whole-file receipt: " + path)
    hashes = {filename: sha((ROOT / root / filename).read_bytes()) for filename in COMPARE_FILES}
    metadata = json.loads((ROOT / root / "run-metadata.json").read_bytes())
    return {"name": name, "root": root, "hashes": hashes,
            "metadata_sha256": sha((ROOT / root / "run-metadata.json").read_bytes()),
            "publication_sha256": sha((ROOT / root / "publication.json").read_bytes()),
            "metadata": metadata}

def build():
    ids = issue_subjects()
    one, two = [validate_run(name) for name in FINAL_RUNS]
    if one["hashes"] != two["hashes"]:
        raise ValueError("Fresh run calculation products differ")
    one_digest = sha(json.dumps(one["hashes"], sort_keys=True, separators=(",", ":")).encode())
    two_digest = sha(json.dumps(two["hashes"], sort_keys=True, separators=(",", ":")).encode())
    if one["metadata"]["vintage"] == two["metadata"]["vintage"] or one["metadata_sha256"] == two["metadata_sha256"]:
        raise ValueError("Run metadata must truthfully distinguish fresh vintages")
    reproducibility = {
        "method_id": METHOD, "kind": "reproducibility", "outcome": "passed",
        "comparison_policy": "Compare every deterministic calculation/control product byte-for-byte. Run name, timestamp and path-bound publication receipt are retained as different truthful per-run metadata.",
        "run_three": {"vintage": one["name"], "outputs": one["hashes"],
                    "metadata_sha256": one["metadata_sha256"], "publication_sha256": one["publication_sha256"]},
        "run_four": {"vintage": two["name"], "outputs": two["hashes"],
                    "metadata_sha256": two["metadata_sha256"], "publication_sha256": two["publication_sha256"]},
        "run_five_sha256": one_digest, "run_six_sha256": two_digest,
        "equal_deterministic_product_digest": one_digest == two_digest,
        "run_metadata_differ": one["metadata_sha256"] != two["metadata_sha256"],
        "method_note": "The digests bind all six whole calculation/control files; publication receipts independently bind all seven run outputs for each fresh vintage."
    }
    exclusive_write(REPRO, (json.dumps(reproducibility, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())

    index = json.loads(git_bytes(BASELINE, "data/world-index.json"))
    if len(index.get("parts", [])) != 36 or len(set(index["parts"])) != 36:
        raise ValueError("Expected exact complete 36-part index")
    baseline_paths = {path for path, _ in ISSUE_PINS.values()}
    baseline_paths.update(path for path, _ in EXTRA.values())
    baseline_paths.update("data/" + part for part in index["parts"])
    baseline_rows = []
    for path in sorted(baseline_paths):
        raw = git_bytes(BASELINE, path)
        baseline_rows.append(descriptor(path, raw, "original-source" if path in {
            ISSUE_PINS["original-scope"][0], ISSUE_PINS["original-crosswalk"][0],
            ISSUE_PINS["original-parent-roster"][0], ISSUE_PINS["original-source-register"][0]
        } else None))
    baseline_by_path = {item["path"]: item for item in baseline_rows}
    pins = {}
    pin_files = {}
    for key, (path, expected) in list(ISSUE_PINS.items()) + list(EXTRA.items()):
        actual = baseline_by_path[path]["sha256"]
        if expected and expected != actual:
            raise ValueError("Baseline digest differs from declared issue pin: " + key)
        pins[key] = actual
        pin_files[key] = path
    if len(ids) != 215:
        raise ValueError("Subject list changed")
    wanted = set(ids)
    subject_files = {}
    for part in index["parts"]:
        parsed = json.loads(git_bytes(BASELINE, "data/" + part))
        for feature in parsed.get("features", []):
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in wanted:
                if identity in subject_files:
                    raise ValueError("Subject appears in multiple indexed parts: " + identity)
                subject_files[identity] = "data/" + part
    if set(subject_files) != wanted:
        raise ValueError("Subject missing from pinned full index: " + str(sorted(wanted - set(subject_files))))

    run_output_paths = []
    for name in ALL_RUNS:
        run_root = f"{OWNED}/vintages/{name}"
        for filename in RUN_FILES + ["publication.json"]:
            run_output_paths.append((run_root + "/" + filename, "generated evidence"))
    static_output_paths = [
        (OWNED + "/README.md", "method and limits"),
        (OWNED + "/reproduce.py", "reproduction code"),
        (OWNED + "/build_manifest.py", "manifest builder"),
        (OWNED + "/issue-1332-contract.json", "retrieved issue snapshot"),
        (REPRO, "reproducibility comparison"),
        (OWNED + "/drafts/evidence-quality-run-one-two.json", "preserved earlier draft manifest"),
        (OWNED + "/drafts/reproducibility-run-one-two.json", "preserved earlier draft comparison"),
        (OWNED + "/drafts/reproducibility-run-three-four-preview.json", "preserved manifest-generation preview"),
        (OWNED + "/drafts/evidence-quality-intermediate.json", "preserved intermediate manifest"),
        (OWNED + "/drafts/reproducibility-intermediate.json", "preserved intermediate comparison"),
        (OWNED + "/drafts/evidence-quality-prior-final-runs.json", "preserved superseded manifest"),
        (OWNED + "/drafts/reproducibility-prior-final-runs.json", "preserved superseded comparison"),
    ]
    output_rows = [candidate_descriptor(path, role) for path, role in static_output_paths + run_output_paths]
    # Bind the contract snapshot by its captured complete file hash and record
    # the two deliberately distinct historical source-register pins separately.
    issue_snapshot_hash = next(row["sha256"] for row in output_rows if row["path"] == OWNED + "/issue-1332-contract.json")
    old_register = git_bytes("7245eca6d56ee71fd1f40631c72116167ac5037d",
        "data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json")
    merge_register = git_bytes("e7cd364e08a713825daa80a3d085d23bd58d5730",
        "data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json")
    if sha(old_register) != "24d34c91f5e3517d1a05e29f1733cc4c0a656422f54ea71a855f63de95f9f57a":
        raise ValueError("Old register pin differs at its named commit")
    if sha(merge_register) != "1e124f1c15ce6b9396ffd97e2d791b2d7cc995eb7d134f2d6dcfed1f18f235ca":
        raise ValueError("Merge register pin differs at its named commit")

    audit_path = OWNED + "/vintages/run-five/audit.json"
    positive_path = OWNED + "/vintages/run-five/positive-control.json"
    negative_path = OWNED + "/vintages/run-five/negative-control.json"
    report = json.loads((ROOT / audit_path).read_bytes())
    positive = json.loads((ROOT / positive_path).read_bytes())
    negative = json.loads((ROOT / negative_path).read_bytes())
    metrics = [
        ("exact_issue_subjects", 215, "subjects", audit_path, "/subject_count"),
        ("distinct_retained_province_parents", 39, "parents", audit_path, "/parent_count"),
        ("raw_child_ids_independently_checked", 215, "child IDs", positive_path, "/child_id_tokens"),
        ("inherited_area_records_checked", 5, "areas", audit_path, "/area_count"),
        ("adverse_controls_rejected", negative["controls_executed"], "controls", negative_path, "/controls_executed"),
    ]
    metric_rows, summaries, bindings = [], [], []
    output_lookup = {row["path"]: row for row in output_rows}
    for mid, value, unit, path, pointer in metrics:
        metric_rows.append({"id": mid, "value": value, "unit": unit, "vintage": "baseline",
                            "evaluation_commit": BASELINE, "input_sha256": output_lookup[path]["sha256"]})
        summaries.append({"metric_id": mid, "value": value, "unit": unit})
        bindings.append({"metric_id": mid, "path": path, "json_pointer": pointer})

    sources = [
        {"id": "github-issue-1332", "url": "https://github.com/ChengshuLi/WorldAtlas/issues/1332",
         "role": "captured bounded work contract and exact subject scope", "vintage": "2026-10-07 issue state",
         "retrieved_at": "2026-10-07T08:10:00Z", "license": {"status": "unknown", "terms": "Issue text is retained as task evidence; content reuse status is not evaluated by this packet."},
         "retention": "restoration-only", "restoration": "Read the retained issue snapshot at " + OWNED + "/issue-1332-contract.json or fetch the issue through the connected GitHub API.",
         "verification": "verified", "temporal_status": "unknown",
         "limit": "The issue defines the software-evidence scope; it is not an authoritative geography source."},
        {"id": "worldatlas-baseline-e919", "url": "https://github.com/ChengshuLi/WorldAtlas/commit/" + BASELINE,
         "role": "immutable Atlas identity index, hierarchy, source records and executable evidence references",
         "vintage": BASELINE, "retrieved_at": "2026-10-07T08:14:14Z",
         "license": {"status": "unknown", "terms": "Repository source reuse is not independently assessed by this mechanical audit."},
         "retention": "restoration-only", "restoration": "Restore exact path bytes using git show " + BASELINE + ":PATH; every consumed baseline file has a whole-file SHA-256 in baseline.files.",
         "verification": "verified", "temporal_status": "unknown",
         "limit": "Retained Atlas identity agreement does not authenticate source authority, current administrative meaning, boundaries or licenses."},
        {"id": "historic-baseline-7245", "url": "https://github.com/ChengshuLi/WorldAtlas/commit/7245eca6d56ee71fd1f40631c72116167ac5037d",
         "role": "exact earlier source-register and reproducer bytes used by the original historical run",
         "vintage": "7245eca6d56ee71fd1f40631c72116167ac5037d",
         "retrieved_at": "2026-10-07T08:14:14Z",
         "license": {"status": "unknown", "terms": "Repository source reuse is not independently assessed by this mechanical audit."},
         "retention": "restoration-only",
         "restoration": "Use git show 7245eca6d56ee71fd1f40631c72116167ac5037d:data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json and the corresponding findings/reproduce.py path.",
         "verification": "verified", "temporal_status": "unknown",
         "limit": "This earlier 8,886-byte source register is a different exact Git vintage from the 10,930-byte merge-vintage register."},
        {"id": "merge-vintage-e7cd", "url": "https://github.com/ChengshuLi/WorldAtlas/commit/e7cd364e08a713825daa80a3d085d23bd58d5730",
         "role": "corrective merge vintage for #1116 source-register and affected validator references",
         "vintage": "e7cd364e08a713825daa80a3d085d23bd58d5730",
         "retrieved_at": "2026-10-07T08:14:14Z",
         "license": {"status": "unknown", "terms": "Repository source reuse is not independently assessed by this mechanical audit."},
         "retention": "restoration-only",
         "restoration": "Use git show e7cd364e08a713825daa80a3d085d23bd58d5730:PATH; all issue-provided pins are checked against this merge and the fresh main baseline.",
         "verification": "verified", "temporal_status": "unknown",
         "limit": "This merge vintage is kept distinct from the earlier 7245 source-register vintage."},
    ]
    conclusions = [
        {"text": "All 215 declared IDs occur exactly once in the complete pinned index, and each retained crosswalk name and parent ID agrees with the pinned Atlas feature and hierarchy records.", "status": "supported", "source_ids": ["github-issue-1332", "worldatlas-baseline-e919"]},
        {"text": "The captured original audit accepts one fabricated child ID in the raw parent roster; the new exact child join rejects fabricated, missing, duplicate, blank and substituted IDs, and checks all 39 parent names/counts/flags.", "status": "supported", "source_ids": ["github-issue-1332", "worldatlas-baseline-e919", "merge-vintage-e7cd"]},
        {"text": "The actual retained CLI overwrites four existing files in its disposable scratch reproduction, while the complete mutated helper fixture is accepted at the legacy runpy boundary; the new execution path consumes captured helper bytes and records the exact old and merge source-register vintages.", "status": "supported", "source_ids": ["github-issue-1332", "historic-baseline-7245", "merge-vintage-e7cd"]},
        {"text": "Current source authority, source member rows, terms of reuse, Chile and Paraguay legal units, current boundaries, neighboring seams, completeness, and positional accuracy remain unresolved.", "status": "unresolved", "source_ids": ["worldatlas-baseline-e919", "historic-baseline-7245", "merge-vintage-e7cd"]},
    ]
    manifest = {
        "version": 1, "issue": 1332, "lane": "geography",
        "worker_id": "01a10947-7d6e-7ba2-98a1-a9f91dedabfc",
        "subject_ids": ids,
        "subject_ids_sha256": sha(json.dumps(sorted(ids), separators=(",", ":")).encode()),
        "baseline": {"commit": BASELINE, "files": baseline_rows, "pins": pins,
                     "pin_files": pin_files, "subject_files": subject_files},
        "sources": sources, "outputs": output_rows,
        "methods": [{"id": METHOD, "kind": "generator", "helper_version": "worldatlas-evidence-preparation-v1",
                     "description": "Authenticate and exercise #1116's actual retained audit/writer boundaries, compare all exact 215 subjects and 39 parent-child rosters to pinned Atlas records, and publish two final safely admitted output vintages.",
                     "software": "Python 3.12.14 standard library; captured scripts/evidence/immutable.py; authenticated verify-packet.py bytes; Git object reads only; no network or provider calls",
                     "units": "retained Atlas subject identities, raw parent-child IDs, baseline parents and area rows"}],
        "metrics": metric_rows, "summaries": summaries, "metric_bindings": bindings,
        "validation": [
            {"method_id": METHOD, "kind": "positive-control", "outcome": "passed", "evidence_path": positive_path},
            {"method_id": METHOD, "kind": "negative-control", "outcome": "passed", "evidence_path": negative_path},
            {"method_id": METHOD, "kind": "reproducibility", "outcome": "passed", "evidence_path": REPRO},
        ],
        "change_receipts": [{"path": path, "status": "added", "previous_path": None}
                            for path in sorted([row["path"] for row in output_rows] + [MANIFEST])],
        "conclusions": conclusions,
        "stages": {"research": "complete", "implementation": "proposed", "geographic_approval": "unapproved"},
        "commands": [
            "PYTHONDONTWRITEBYTECODE=1 python3 -B " + OWNED + "/reproduce.py --vintage run-five",
            "PYTHONDONTWRITEBYTECODE=1 python3 -B " + OWNED + "/reproduce.py --vintage run-six",
            "PYTHONDONTWRITEBYTECODE=1 python3 -B " + OWNED + "/build_manifest.py",
            "node scripts/evidence-quality.mjs " + MANIFEST,
        ],
        "limits": [
            "No geoBoundaries original geometry or upstream feature row was acquired, retained or reverified.",
            "The original 2022 Paraguay INE response bytes, response-level reuse terms and statistical-to-administrative relation were not rechecked.",
            "Candidate source IDs, vintages, tier labels, names and license strings remain inherited packet observations, not fresh source certification.",
            "Chile ADM3, Paraguay ADM2 and the Asunción aggregate are neighboring candidate granularities; equivalence, adjacency and complete neighboring coverage are not established.",
            "The source register distinguishes exact Git vintages; no external authority, legal parentage, source completeness, boundary quality, positional accuracy or regional approval is established.",
            "The retained Atlas subject index proves only exact stored identity and parent links; it does not prove current administrative truth.",
            "Original #935/#948/#1120 evidence, source hashes, rows and history were read-only and remain unchanged.",
            "The final manifest is built after both safe completed vintages and is installed exclusively; it cannot certify its own bytes, so its whole-file hash is bound by Git/PR review.",
            "run-one and run-two are retained as earlier successful drafts; run-five and run-six are the final two reproducibility runs with complete historical execution-input inventories.",
        ],
    }
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    exclusive_write(MANIFEST, raw)
    print(json.dumps({"manifest": MANIFEST, "baseline_files": len(baseline_rows),
        "outputs": len(output_rows), "total_candidate_output_bytes": sum(x["bytes"] for x in output_rows),
        "total_baseline_bytes": sum(x["bytes"] for x in baseline_rows),
        "phase_bytes_before_runtime_reserve": sum(x["bytes"] for x in baseline_rows) + sum(x["bytes"] for x in output_rows),
        "subject_count": len(ids), "status": "complete"}, indent=2, sort_keys=True))

if __name__ == "__main__":
    build()
