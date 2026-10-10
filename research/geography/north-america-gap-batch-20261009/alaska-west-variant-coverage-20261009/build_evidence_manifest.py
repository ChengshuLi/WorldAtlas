#!/usr/bin/env python3
"""Bind the measured four-case output to the existing #1630 evidence manifest."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[4]
BATCH = "research/geography/north-america-gap-batch-20261009"
PACKET = BATCH + "/alaska-west-variant-coverage-20261009"
MANIFEST = BATCH + "/evidence-quality.json"
RESULT = BATCH + "/vintages/coverage-run-20261010-02/source-variant-coverage.json"
README = PACKET + "/README.md"
BASELINE_CANDIDATE = BATCH + "/alaska-west-four-source-physical-evidence.json"
CANDIDATE_SOURCE_COMMIT = "b2b34087682b9a20e53c72c83f6d53054e09e8cf"
SOURCE_PATHS = [
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/geoboundaries-USA-ADM2-full-9469f09.geojson",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/geoboundaries-USA-ADM2-full-9469f09-receipt.json",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/geoboundaries-USA-ADM2-full-9469f09-source-check.json",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/geoBoundaries-USA-ADM2_simplified.geojson",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/simplified-object-retrieval.json",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/retrieval.json",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/geoBoundaries-USA-ADM2-metaData.json",
]
CHANGED_PATHS = [
    f"{PACKET}/README.md",
    f"{PACKET}/build_evidence_manifest.py",
    f"{PACKET}/build_phase_admission.py",
    f"{PACKET}/phase-admission.json",
    f"{PACKET}/variant_coverage_driver.py",
    f"{PACKET}/variant_coverage_run_phase.py",
    f"{PACKET}/execution/coverage-run-20261010-01-operating-receipt.json",
    f"{PACKET}/execution/coverage-run-20261010-02-operating-receipt.json",
    f"{BATCH}/vintages/coverage-run-20261010-02/publication.json",
    RESULT,
    MANIFEST,
]
FULL_SOURCE = SOURCE_PATHS[0]
ADMISSION = PACKET + "/phase-admission.json"
SOURCE_ID = "geoBoundaries-USA-ADM2-9469f09-full-and-simplified-retained-variants"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def descriptor(path: str, role: str) -> dict:
    target = ROOT / path
    if target.is_symlink() or not target.is_file():
        raise SystemExit("manifest member must be an ordinary file: " + path)
    raw = target.read_bytes()
    if len(raw) > 32 * 1024 * 1024:
        raise SystemExit("manifest member exceeds 32 MiB: " + path)
    return {"path": path, "bytes": len(raw), "sha256": digest(raw), "hash_kind": "file-bytes", "role": role}


def atomic_write(path: str, raw: bytes, *, exclusive: bool) -> None:
    target = ROOT / path
    if target.is_symlink():
        raise SystemExit("unsafe evidence output destination: " + path)
    if exclusive and target.exists():
        if target.is_file() and target.read_bytes() == raw:
            return
        raise SystemExit("refusing to replace existing evidence output: " + path)
    if not exclusive and not target.is_file():
        raise SystemExit("required manifest is missing or not an ordinary file: " + path)
    temporary = target.with_name("." + target.name + "." + uuid.uuid4().hex + ".incomplete")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if exclusive:
        os.link(temporary, target)
        temporary.unlink()
    else:
        os.replace(temporary, target)


def metric_id(name: str) -> str:
    return "alaska_west_variant_coverage_" + name


def main() -> None:
    result = json.loads((ROOT / RESULT).read_bytes())
    run_commit = result["baseline_commit"]
    if not isinstance(run_commit, str) or len(run_commit) != 40:
        raise SystemExit("coverage result lacks its immutable execution baseline")
    manifest_raw = (ROOT / MANIFEST).read_bytes()
    if manifest_raw != git("show", f"{run_commit}:{MANIFEST}"):
        raise SystemExit("existing #1630 evidence manifest changed since measurement baseline")
    manifest = json.loads(manifest_raw)

    # Retain candidate identity and geometry provenance as an explicit baseline
    # file; the original 4,674/152 subject inventory and all earlier evidence stay.
    raw_candidate = git("show", f"{CANDIDATE_SOURCE_COMMIT}:{BASELINE_CANDIDATE}")
    if raw_candidate != git("show", f"{run_commit}:{BASELINE_CANDIDATE}"):
        raise SystemExit("retained physical-evidence bytes differ from their merged #1653 source commit")
    candidate_descriptor = {"path": BASELINE_CANDIDATE, "bytes": len(raw_candidate),
                            "sha256": digest(raw_candidate), "hash_kind": "file-bytes", "commit": CANDIDATE_SOURCE_COMMIT}
    if not any(row["path"] == BASELINE_CANDIDATE and row.get("commit") == CANDIDATE_SOURCE_COMMIT for row in manifest["baseline"]["files"]):
        manifest["baseline"]["files"].append(candidate_descriptor)

    source_files = [descriptor(path, "retained-2018-USA-ADM2-full-or-simplified-variant") for path in SOURCE_PATHS]
    source = {
        "id": SOURCE_ID,
        "url": "https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/USA/ADM2",
        "role": "Already-retained full and simplified geoBoundaries USA ADM2 source variants; comparison reference for four exact Aleutians West component candidates.",
        "vintage": "geoBoundaries immutable release commit 9469f09592ced973a3448cf66b6100b741b64c0d; source metadata carries a 2018 boundary-year claim.",
        "retrieved_at": "2026-10-08",
        "license": {"status": "redistributable", "terms": "Retained source metadata and attribution state CC-BY 4.0 with attribution; original retrieval and source-check records are preserved. This evidence adds no new legal determination."},
        "retention": "retained",
        "verification": "verified",
        "temporal_status": "reference",
        "files": source_files,
        "limit": "Source-version coverage agreement does not establish real-world boundary accuracy, political authority, currentness, repair approval or publication permission.",
    }
    old = next((row for row in manifest["sources"] if row["id"] == SOURCE_ID), None)
    if old:
        manifest["sources"].remove(old)
    manifest["sources"].append(source)

    case_lines = []
    for case in result["cases"]:
        full = case["full"]
        simple = case["simplified"]
        p = case["literal_retained_county_coverage_premises"]
        case_lines.append(
            f"| `{case['component_id']}` | {full['status']} / {full['candidate_covered_exactly']} / {full['candidate_uncovered_area_projected_m2_exact']} / {full['candidate_coverage_ratio']} | "
            f"{simple['status']} / {simple['candidate_covered_exactly']} / {simple['candidate_uncovered_area_projected_m2_exact']} / {simple['candidate_coverage_ratio']} | "
            f"{case['source_variants_agree_on_coverage_predicate_outputs']} | {p['candidate_source_variants_agree_for_this_candidate']} |"
        )
    readme = "\n".join([
        "# Aleutians West retained-source variant coverage",
        "",
        "This source-only evidence adds the eight first-time coverage measurements authorized by the amended #1630 work item. It uses the four exact candidates from the merged #1653 handoff and the already-retained full and simplified USA ADM2 variants from release 9469f09.",
        "",
        "The first admitted attempt stopped at the shared evidence writer's owned-path check before any spatial comparison. Its failed operating receipt is retained under `execution/coverage-run-20261010-01-operating-receipt.json`; the successful fresh run uses the issue-owned batch namespace.",
        "",
        "The unchanged `intersections()` overlay method is used for each candidate/source pair. The literal coverage rule is `status=measured`, `candidate_covered_exactly=true`, `candidate_uncovered_area_projected_m2_exact=0`, and `candidate_coverage_ratio=1`. Per-candidate variant agreement compares measured coverage outputs, including overlap and exact projected areas. It requires no whole-source or clipped-geometry equality.",
        "",
        "| Component | Full: status / covered / uncovered m² / ratio | Simplified: status / covered / uncovered m² / ratio | Coverage outputs agree | Literal candidate agreement |",
        "|---|---|---|---:|---:|",
        *case_lines,
        "",
        f"Summary: {result['summary']['variant_comparisons']} overlays across {result['summary']['candidate_count']} candidates; full coverage premises pass for {result['summary']['full_coverage_pass_count']}; simplified coverage premises pass for {result['summary']['simplified_coverage_pass_count']}; coverage outputs agree for {result['summary']['candidate_variant_agreement_count']}; candidate-level source agreement passes for {result['summary']['literal_source_variant_agreement_count']}; all three literal premises fit for {result['summary']['literal_rule_fit_count']}.",
        "",
        "This result changes no source, geography, physical classification, native relation, roster, conservation, production record or approval. See `vintages/coverage-run-20261010-02/source-variant-coverage.json` and its `publication.json` for the complete exact values and execution pins.",
        "",
    ])
    atomic_write(README, readme.encode("utf-8"), exclusive=True)

    generated_roles = {
        f"{PACKET}/README.md": "supporting-evidence",
        f"{PACKET}/build_evidence_manifest.py": "code",
        f"{PACKET}/build_phase_admission.py": "code",
        f"{PACKET}/phase-admission.json": "phase-admission",
        f"{PACKET}/variant_coverage_driver.py": "code",
        f"{PACKET}/variant_coverage_run_phase.py": "code",
        f"{PACKET}/execution/coverage-run-20261010-01-operating-receipt.json": "failed-operating-receipt",
        f"{PACKET}/execution/coverage-run-20261010-02-operating-receipt.json": "operating-receipt",
        f"{BATCH}/vintages/coverage-run-20261010-02/publication.json": "publication-receipt",
        RESULT: "generated-result",
    }
    known = {row["path"] for row in manifest["outputs"]}
    for path, role in generated_roles.items():
        if path not in known:
            manifest["outputs"].append(descriptor(path, role))
    manifest["outputs"] = [descriptor(path, generated_roles.get(path, row.get("role", "generated-evidence")))
                            if path in generated_roles else row for path, row in
                            ((row["path"], row) for row in manifest["outputs"])]

    summary = result["summary"]
    metric_rows = [
        ("overlay_comparison_count", summary["variant_comparisons"], "candidate-source overlay comparisons"),
        ("full_coverage_pass_count", summary["full_coverage_pass_count"], "candidates satisfying the full-source literal coverage rule"),
        ("simplified_coverage_pass_count", summary["simplified_coverage_pass_count"], "candidates satisfying the simplified-source literal coverage rule"),
        ("coverage_variant_agreement_count", summary["candidate_variant_agreement_count"], "candidates with matching full/simplified coverage predicate outputs"),
        ("literal_variant_agreement_count", summary["literal_source_variant_agreement_count"], "candidates satisfying existing candidate-level source-variant agreement"),
        ("literal_rule_fit_count", summary["literal_rule_fit_count"], "candidates satisfying both source coverage premises and per-candidate variant agreement"),
    ]
    input_sha = digest((ROOT / ADMISSION).read_bytes())
    existing_metrics = {row["id"] for row in manifest["metrics"]}
    existing_bindings = {row["metric_id"] for row in manifest["metric_bindings"]}
    existing_summaries = {row["metric_id"] for row in manifest["summaries"]}
    for name, value, unit in metric_rows:
        identity = metric_id(name)
        if identity in existing_metrics:
            manifest["metrics"] = [row for row in manifest["metrics"] if row["id"] != identity]
        if identity in existing_bindings:
            manifest["metric_bindings"] = [row for row in manifest["metric_bindings"] if row["metric_id"] != identity]
        if identity in existing_summaries:
            manifest["summaries"] = [row for row in manifest["summaries"] if row["metric_id"] != identity]
        manifest["metrics"].append({"id": identity, "value": value, "unit": unit,
                                     "input_sha256": input_sha, "input_file": {"path": ADMISSION, "commit": "candidate"},
                                     "evaluation_commit": run_commit, "vintage": "archived"})
        manifest["metric_bindings"].append({"metric_id": identity, "path": RESULT,
                                             "json_pointer": "/summary/" + {
                                                 "overlay_comparison_count": "variant_comparisons",
                                                 "full_coverage_pass_count": "full_coverage_pass_count",
                                                 "simplified_coverage_pass_count": "simplified_coverage_pass_count",
                                                 "coverage_variant_agreement_count": "candidate_variant_agreement_count",
                                                 "literal_variant_agreement_count": "literal_source_variant_agreement_count",
                                                 "literal_rule_fit_count": "literal_rule_fit_count",
                                             }[name]})
        manifest["summaries"].append({"metric_id": identity, "value": value, "unit": unit})

    if not any(row["id"] == "alaska-west-four-retained-variant-coverage-v1" for row in manifest["methods"]):
        manifest["methods"].append({
            "id": "alaska-west-four-retained-variant-coverage-v1",
            "kind": "measurement",
            "description": "Four exact #1653 candidate geometries intersected against only the Aleutians West feature in the already-retained full and simplified geoBoundaries USA ADM2 9469f09 products. Reuses the pinned intersections() function, exact covers predicate, exact candidate-minus-source area and EPSG:3338 area method.",
            "software": "Python 3.12.14; Shapely 2.1.2; pyproj 3.7.2; immutable.py pinned Baseline/NewVintage custody",
            "units": "exact boolean coverage predicates; square metres for projected area; eight candidate/source comparisons",
        })
    new_conclusion = {
        "text": "The measured full/simplified coverage results and candidate-level agreement for the four exact Aleutians West components are recorded in the new source-variant output; they establish only the retained-source comparison required by amended #1630.",
        "status": "supported",
        "source_ids": [SOURCE_ID],
    }
    manifest["conclusions"] = [row for row in manifest["conclusions"] if row.get("text") != new_conclusion["text"]]
    manifest["conclusions"].append(new_conclusion)
    command = "/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/north-america-gap-batch-20261009/alaska-west-variant-coverage-20261009/variant_coverage_run_phase.py"
    if command not in manifest["commands"]:
        manifest["commands"].append(command)

    base = git("merge-base", "HEAD", "origin/main").decode().strip()
    receipts = []
    for path in sorted(CHANGED_PATHS):
        old = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{base}:{path}"], capture_output=True)
        row = {"path": path, "status": "modified" if old.returncode == 0 else "added"}
        if old.returncode == 0:
            row["original_sha256"] = digest(git("show", f"{base}:{path}"))
        receipts.append(row)
    manifest["change_receipts"] = receipts
    atomic_write(MANIFEST, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), exclusive=False)
    print(json.dumps({"manifest": MANIFEST, "outputs_added": len(generated_roles),
                      "metric_bindings_added": len(metric_rows), "change_receipts": len(receipts),
                      "baseline_commit_for_new_measurements": run_commit,
                      "result_summary": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
