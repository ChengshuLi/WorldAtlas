#!/usr/bin/env python3
"""Assemble the issue-declared, whole-file evidence manifest after packet runs."""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
RUN = ROOT / "vintages/run-16"
CONTACT = "atlas:district:CAN-5917:BRC"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                        allow_nan=False) + "\n").encode()


def git(*args):
    return subprocess.check_output(["git", *args])


def descriptor(path, raw, **extra):
    return {"path": path, "bytes": len(raw), "sha256": sha(raw),
            "hash_kind": "file-bytes", **extra}


def main():
    inputs = json.loads((RUN / "source-input-pins.json").read_bytes())
    scope = json.loads((RUN / "scope-summary.json").read_bytes())
    assessment = json.loads((RUN / "source-assessment.json").read_bytes())
    base = inputs["current_main_baseline"]

    pinned = {}
    for row in inputs["current_and_retained_source_files"]:
        pinned[row["path"]] = row
    for row in inputs["complete_original_physical_row_files"]:
        pinned[row["path"]] = row
    pinned[inputs["diagnosis_execution_report"]["path"]] = inputs["diagnosis_execution_report"]
    helper_path = "scripts/evidence/immutable.py"
    helper_raw = git("show", f"{base}:{helper_path}")
    pinned[helper_path] = {"path": helper_path, "bytes": len(helper_raw), "sha256": sha(helper_raw)}
    route_report_path = inputs["routing_report"]["path"]
    diagnosis_report_path = inputs["diagnosis_execution_report"]["path"]
    route_report = json.loads(git("show", f"{base}:{route_report_path}"))
    diagnosis_report = json.loads(git("show", f"{base}:{diagnosis_report_path}"))
    partition_pins = []
    route_root = "coordination/engineering/global-actionability-routing-20261007/results"
    diagnosis_root = "coordination/engineering/complete-numeric-closure-diagnosis-20261007/r1"
    for report, root, prefixes in ((route_report, route_root, ("families-", "components-")),
                                    (diagnosis_report, diagnosis_root, ("diagnoses-",))):
        for part in report["outputs"]:
            if not part["path"].startswith(prefixes):
                continue
            path = f"{root}/{part['path']}"
            row = {"path": path, "bytes": part["bytes"], "sha256": part["sha256"],
                   "uncompressed_bytes": part["uncompressed_bytes"],
                   "uncompressed_sha256": part["uncompressed_sha256"]}
            pinned[path] = row
            partition_pins.append((path, row))
    baseline_files = []
    oversized = []
    for path, row in sorted(pinned.items()):
        raw = git("show", f"{base}:{path}")
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError(f"Issue baseline no longer contains exact retained input: {path}")
        tree = git("ls-tree", base, "--", path).decode().strip().split()
        if len(tree) < 4 or tree[0] not in ("100644", "100755"):
            raise ValueError(f"Baseline source is not an ordinary file: {path}")
        if len(raw) > 32 * 1024 * 1024:
            rel = path.removeprefix("data/regional-review/regional-review-4254da254d94f450/")
            prior = json.loads(git("show", f"{base}:data/regional-review/regional-review-4254da254d94f450/sources-manifest.json"))
            matches = [x for x in prior["files"] if x.get("path") == rel]
            if len(matches) != 1 or matches[0].get("bytes") != len(raw) or matches[0].get("sha256") != sha(raw):
                raise ValueError(f"Oversized source is not independently bound by its retained whole-source manifest: {path}")
            oversized.append({"path": path, "bytes": len(raw), "sha256": sha(raw),
                              "prior_manifest": "data/regional-review/regional-review-4254da254d94f450/sources-manifest.json"})
            continue
        extra = {"mode": tree[0], "oid": tree[2]}
        if "uncompressed_bytes" in row:
            extra.update(uncompressed_bytes=row["uncompressed_bytes"],
                         uncompressed_sha256=row["uncompressed_sha256"])
        baseline_files.append(descriptor(path, raw, **extra))

    report_pin = next(row for row in baseline_files if row["path"] == inputs["routing_report"]["path"])
    diagnosis_path = inputs["diagnosis_execution_report"]["path"]
    diagnosis_pin = next(row for row in baseline_files if row["path"] == diagnosis_path)
    pins = {
        "accepted_routing_report": report_pin["sha256"],
        "accepted_diagnosis_report": diagnosis_pin["sha256"],
    }
    pin_files = {"accepted_routing_report": report_pin["path"],
                 "accepted_diagnosis_report": diagnosis_pin["path"]}
    ids = [CONTACT]
    ids_digest = sha(json.dumps(ids, separators=(",", ":")).encode())

    def run_digest(name):
        run = ROOT / "vintages" / name
        products = []
        for leaf in ("family-row.json", "component-review.jsonl", "source-input-pins.json", "source-assessment.json",
                     "scope-summary.json", "run-receipt.json"):
            raw = (run / leaf).read_bytes()
            products.append({"path": leaf, "bytes": len(raw), "sha256": sha(raw)})
        return sha(canonical(products)), products

    digest_one, run_one = run_digest("run-15")
    digest_two, run_two = run_digest("run-16")
    if digest_one != digest_two:
        raise ValueError("Fresh producer vintages are not byte-identical")
    control_path = ROOT / "vintages/run-16-controls.json"
    control_bytes = control_path.read_bytes()
    control_result = json.loads(control_bytes)
    if control_result.get("counts", {}).get("controls") != 13 or control_result["counts"].get("passed") != 13:
        raise ValueError("Complete directed-control receipt is missing or unsuccessful")
    control_ids = {row["id"] for row in control_result["directed_controls"] if row["passed"]}
    positive_ids = sorted(x for x in control_ids if x.startswith("positive-"))
    negative_ids = sorted(x for x in control_ids if x.startswith("negative-"))
    if len(positive_ids) < 6 or len(negative_ids) < 6:
        raise ValueError("Required positive/negative controls are absent")
    validation_dir = ROOT / "validation"
    validation_dir.mkdir(exist_ok=True)
    owned_prefix = ROOT.relative_to(ROOT.parent.parent.parent).as_posix()
    validation = [
        {"path": f"{owned_prefix}/validation/generator-positive-controls.json", "value": {
            "method_id": "source-packet-generator", "kind": "positive-control", "outcome": "passed",
            "source_control_path": "vintages/run-16-controls.json",
            "source_control_sha256": sha(control_bytes), "control_ids": positive_ids}},
        {"path": f"{owned_prefix}/validation/generator-negative-controls.json", "value": {
            "method_id": "source-packet-generator", "kind": "negative-control", "outcome": "passed",
            "source_control_path": "vintages/run-16-controls.json",
            "source_control_sha256": sha(control_bytes), "control_ids": negative_ids}},
        {"path": f"{owned_prefix}/validation/generator-reproducibility.json", "value": {
            "method_id": "source-packet-generator", "kind": "reproducibility", "outcome": "passed",
            "run_one_sha256": digest_one, "run_two_sha256": digest_two,
            "run_one": run_one, "run_two": run_two}},
    ]
    for row in validation:
        (ROOT / pathlib.PurePosixPath(row["path"]).relative_to(owned_prefix)).write_bytes(canonical(row["value"]))

    outputs = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "evidence-quality.json"):
        rel = path.relative_to(ROOT.parent.parent.parent).as_posix()
        raw = path.read_bytes()
        outputs.append(descriptor(rel, raw))
    output_paths = {row["path"] for row in outputs}
    changed_paths = sorted(output_paths)
    if len(changed_paths) != len(outputs):
        raise ValueError("Duplicate output path")

    route_source = f"https://github.com/ChengshuLi/WorldAtlas/tree/{inputs['accepted_routing_commit']}/coordination/engineering/global-actionability-routing-20261007"
    diagnosis_source = f"https://github.com/ChengshuLi/WorldAtlas/tree/{inputs['accepted_diagnosis_commit']}/coordination/engineering/complete-numeric-closure-diagnosis-20261007"
    sources = [
        {"id": "accepted-routing-family-record", "url": route_source,
         "role": "Immutable source-family and current-candidate routing record",
         "vintage": inputs["accepted_routing_commit"], "retrieved_at": "2026-10-07",
         "license": {"status": "unknown", "terms": "Repository-retained diagnostic evidence; no separate third-party source license asserted."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
         "restoration": "Read the exact pinned Git commit and verify the complete routing report and chunk receipts.",
         "limit": "Routing is diagnostic triage; it does not approve source fitness or physical authority."},
        {"id": "accepted-numeric-diagnosis-record", "url": diagnosis_source,
         "role": "Immutable complete numerical-closure diagnosis and original replay record",
         "vintage": inputs["accepted_diagnosis_commit"], "retrieved_at": "2026-10-07",
         "license": {"status": "unknown", "terms": "Repository-retained diagnostic evidence; no separate third-party source license asserted."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
         "restoration": "Read the exact pinned Git commit and verify its report and all diagnosis part receipts.",
         "limit": "Nine construction contradictions are local diagnoses, not source or land validation."},
        {"id": "current-atlas-administrative-aggregation",
         "url": "https://www.arcgis.com/home/item.html?id=24f45c7b49d84aaf8e55e566a7fd670b",
         "role": "Recorded locator for the current undated modern administrative aggregation",
         "vintage": "Undated modern reference", "retrieved_at": "2026-10-03",
         "license": {"status": "unknown", "terms": "Underlying member-source license terms are retained in semantic-report.json; complete authority, member coverage and redistribution rights were not independently re-established."},
         "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
         "restoration": "Use pinned data/geography/part-29.json and its metadata; do not treat the ArcGIS locator as proof that the current aggregate was reacquired.",
         "limit": "Undated aggregation; 22 source member IDs are retained, but exact current authority, currency, completeness and legal role remain unresolved."},
        {"id": "statistics-canada-2021-census-division",
         "url": "https://www.arcgis.com/home/item.html?id=24f45c7b49d84aaf8e55e566a7fd670b",
         "role": "Dated statistical Census Division cross-check, CDUID 5917 / Capital (RD)",
         "vintage": "2021 Census geography", "retrieved_at": "2026-10-03",
         "license": {"status": "unknown", "terms": "Retained packet README records Statistics Canada Open Licence; item metadata links General Terms and Conditions. This assessment preserves that terms discrepancy."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "historical",
         "supported_interval": {"from": 2021, "to": 2022},
         "restoration": "Read the retained 2021 CDUID 5917 feature and item/layer metadata from the pinned regional-review packet.",
         "limit": "Statistical unit and 2021 vintage only; current contact is not topologically equal and this is not a legal or physical-land boundary. The full 38,880,150-byte compressed source exceeds the shared 32 MiB per-file manifest cap; its original whole-file hash and byte count are cross-checked against the pinned prior sources-manifest, while the original tracked blob remains available for review."},
        {"id": "gshhg-2.3.7-full-resolution",
         "url": "https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip",
         "role": "Generalized global 2017 shoreline and mapped-land screening source",
         "vintage": "GSHHG 2.3.7 released 2017-06-15", "retrieved_at": "2026-10-03",
         "license": {"status": "redistributable", "terms": "LGPLv3 or later; notices and license text retained in the regional-review packet."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "historical",
         "supported_interval": {"from": 2017, "to": 2018},
         "restoration": "Follow the pinned archive/member SHA-256 instructions in the prior regional-review evidence; the local derived screen is retained.",
         "limit": "Point/centroid screening does not cover component polygons; absence of a mapped-water match does not prove dry land."},
    ]

    summary_file = f"{ROOT.relative_to(ROOT.parent.parent.parent).as_posix()}/vintages/run-16/scope-summary.json"
    assessment_file = f"{ROOT.relative_to(ROOT.parent.parent.parent).as_posix()}/vintages/run-16/source-assessment.json"
    source_pin = report_pin["sha256"]
    metric_specs = [
        ("complete_components", 43, "physical component records", summary_file, "/complete_component_count"),
        ("complete_contact_source_members", 22, "retained source-member IDs", assessment_file, "/contact/source_member_count"),
        ("complete_original_queries", 146, "original query relationships", summary_file, "/complete_query_relation_count"),
        ("numeric_siblings", 28, "numeric sibling records", summary_file, "/numeric_component_count"),
        ("construction_contradictions", 9, "local construction contradictions", summary_file, "/numeric_diagnosis_status_counts/local-construction-contradiction-demonstrated"),
        ("unresolved_numeric_or_context", 18, "unresolved numeric/context records", summary_file, "/numeric_diagnosis_status_counts/retained-unresolved-numerical-or-context-prerequisite"),
        ("original_replay_mismatches", 1, "unresolved replay mismatches", summary_file, "/numeric_diagnosis_status_counts/retained-unresolved-original-replay-mismatch"),
        ("nonnumeric_siblings", 15, "nonnumeric sibling records", summary_file, "/nonnumeric_sibling_count"),
        ("mixed_source_support", 15, "physical components", summary_file, "/physical_status_counts/mixed-source-support"),
        ("physical_unknowns", 28, "physical components", summary_file, "/physical_status_counts/unknown"),
        ("inherited_family_impact", 116441477.74262899, "m² inherited diagnostic accounting", summary_file, "/family_impact_m2_inherited"),
    ]
    metrics = [{"id": mid, "value": value, "unit": unit, "vintage": "baseline",
                "input_sha256": source_pin, "evaluation_commit": base}
               for mid, value, unit, _, _ in metric_specs]
    bindings = [{"metric_id": mid, "path": path, "json_pointer": pointer}
                for mid, _, _, path, pointer in metric_specs]

    manifest_path = "research/geography/canada-bc-gap-source-fitness-20261007/evidence-quality.json"
    manifest = {
        "version": 1, "issue": 1362, "lane": "geography",
        "worker_id": "01a11522-1da9-75a1-8ecb-765bae224f1c",
        "subject_ids": ids, "subject_ids_sha256": ids_digest,
        "baseline": {"commit": base, "files": baseline_files, "pins": pins,
                     "pin_files": pin_files,
                     "subject_files": {CONTACT: "data/geography/part-29.json"}},
        "sources": sources, "outputs": outputs,
        "methods": [
            {"id": "source-packet-generator", "kind": "generator",
             "helper_version": "worldatlas-evidence-preparation-v1",
             "description": "Build complete source and diagnosis output rows from authenticated, bounded report/source partitions; exclusively admit the full fresh output set and publish a success receipt only after every payload is written.",
             "software": "Python 3.12; shared WorldAtlas immutable preparation helper; Shapely " + json.loads((RUN / "source-input-pins.json").read_bytes())["runtime"].get("shapely", "unknown"),
             "units": "bounded source/member/query counts, exact SHA-256 byte identity"},
            {"id": "accepted-source-record-reconstruction", "kind": "source",
             "description": "Authenticate complete accepted routing and numeric diagnosis chunk receipts, restore all original physical source records by pinned whole-file inputs and compare the full current contact with retained dated administrative and physical references. No original operator or external source service was run.",
             "software": "Python 3.12; Shapely " + json.loads((RUN / "source-input-pins.json").read_bytes())["runtime"].get("shapely", "unknown") + "; packet scripts at candidate revision",
             "units": "identity counts, square metres as inherited diagnostic accounting; geometry comparison is topological equality only"},
        ],
        "metrics": metrics, "metric_bindings": bindings, "summaries": [],
        "validation": [{"method_id": "source-packet-generator", "kind": row["value"]["kind"],
                        "outcome": "passed", "evidence_path": row["path"]} for row in validation],
        "conclusions": [
            {"text": "The accepted source family contains 43 uniquely identified component records, one full district contact, 146 original query relationships and the complete 28-row numeric cohort. These identities and record closures are authenticated to the accepted immutable reports and original physical rows.", "status": "supported", "source_ids": ["accepted-routing-family-record", "accepted-numeric-diagnosis-record"]},
            {"text": "The current BRC contact is topologically unequal to the retained 2021 Statistics Canada CDUID 5917 feature. That comparison does not determine which geometry is legally authoritative or current.", "status": "supported", "source_ids": ["current-atlas-administrative-aggregation", "statistics-canada-2021-census-division"]},
            {"text": "No inspected source establishes physical land/water status for every member, full current administrative authority, complete aggregation membership, or legal boundary status. All component dispositions remain unapproved.", "status": "unresolved", "source_ids": ["current-atlas-administrative-aggregation", "statistics-canada-2021-census-division", "gshhg-2.3.7-full-resolution"]},
        ],
        "stages": {"research": "complete", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "Set PYTHON to Python 3.12 with the recorded Shapely runtime; from the repository root run build_packet.py twice into fresh vintages, then run controls.py once for each packet and assemble_manifest.py.",
            "Run scripts/evidence-quality.mjs on research/geography/canada-bc-gap-source-fitness-20261007/evidence-quality.json.",
        ],
        "limits": [
            "The retained 38,880,150-byte compressed Statistics Canada 2021 Census Division response exceeds the shared 32 MiB per-file evidence cap. It remains in baseline Git and its exact whole-file byte count/SHA-256 is cross-checked against the prior packet sources-manifest; the source-input-pins output also records that Git blob identity. No size limit is waived and no source bytes are recopied into this packet. Review can restore the original tracked file and check its single 5917 feature directly."
        ] if oversized else [],
        "oversized_original_source_pins": oversized,
        "partition_closure": {"authenticated_source_chunks": len(partition_pins),
                               "routes_and_diagnoses": [path for path, _ in partition_pins],
                               "note": "Every named compressed source/diagnosis part is separately pinned by whole-file and uncompressed SHA-256, allowing independent bounded decompression and complete partition-roster review."},
        "directed_control_runs": [
            {"packet": "vintages/run-15", "controls": "vintages/run-15-controls.json"},
            {"packet": "vintages/run-16", "controls": "vintages/run-16-controls.json"},
        ],
        "change_receipts": ([{"path": path, "status": "added"} for path in changed_paths] +
                            [{"path": manifest_path, "status": "added"}]),
    }
    out = ROOT / "evidence-quality.json"
    out.write_bytes(canonical(manifest))
    print(json.dumps({"manifest": str(out), "baseline_files": len(baseline_files),
                      "outputs": len(outputs), "subjects": len(ids),
                      "metrics": len(metrics), "changes": len(changed_paths)}, sort_keys=True))


if __name__ == "__main__":
    main()
