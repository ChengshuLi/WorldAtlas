#!/usr/bin/env python3
"""Build the issue-1129 v1 evidence manifest from pinned baseline bytes."""
import hashlib
import csv
import io
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).resolve().parent
OWN_REL = OWN.relative_to(ROOT).as_posix()
BASELINE = "4877ef4e99528615daf657a376b7605d1657f817"
WORKER = "01a10947-7d6e-7ba2-98a1-a9f91dedabfc"
EXPECTED_PINS = {
    "renderer": ("data/regional-review/argentina-adm2-source-revalidation-443/categorize-tabular-findings.py", "1d07c2bb5202d095f64dc0bf05749338cd49eb40d27cd527316d6da535b58bcc"),
    "comparison-table": ("data/regional-review/argentina-adm2-source-revalidation-443/findings/scoped-2020-to-current-georef-overlay.csv", "0d9c8c89cd5131bce1c712b66e6f0caf4b1a083fd73b7e257eb484d6b7ff47d2"),
    "scoped-source": ("data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020-scoped-214.geojson", "7bcfe3ab98e03372a8d6e3c2d5a844f4176011c577cc090d2c823f6603cb1305"),
    "measurement-code": ("data/regional-review/argentina-adm2-source-revalidation-443/reproduce-spatial.py", "0905be0483fb1ef6f25ca28aac44b231a28a1cac9e135431c11d29eabda0be61"),
}
EXTRA_BASELINE = [
    "data/geography/part-0.json",
    "data/regional-review/argentina-adm2-source-revalidation-443/README.md",
    "data/regional-review/argentina-adm2-source-revalidation-443/source-register.json",
    "data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020/geoBoundaries-ARG-ADM2-metaData.json",
]
OUTPUTS = [
    f"{OWN_REL}/README.md",
    f"{OWN_REL}/scope.json",
    f"{OWN_REL}/corrected-renderer.py",
    f"{OWN_REL}/build-evidence-manifest.py",
    *[f"{OWN_REL}/output/{name}" for name in [
        "corrected-findings.csv", "ring-measurements.json", "reproduction-report.json",
        "positive-control.json", "negative-control.json", "regression-control.json", "reproducibility.json",
    ]],
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def baseline_bytes(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASELINE}:{path}"])


def descriptor(path, data):
    return {"path": path, "bytes": len(data), "sha256": digest(data), "hash_kind": "file-bytes"}


def main():
    scope = json.loads((OWN / "scope.json").read_text(encoding="utf-8"))
    ids = scope["subject_ids"]
    if len(ids) != 214 or len(set(ids)) != 214:
        raise ValueError("scope roster must have exactly 214 unique subjects")
    scoped = json.loads(baseline_bytes(EXPECTED_PINS["scoped-source"][0]))
    table = list(csv.DictReader(io.StringIO(baseline_bytes(EXPECTED_PINS["comparison-table"][0]).decode("utf-8"), newline="")))
    atlas = json.loads(baseline_bytes("data/geography/part-0.json"))
    atlas_ids = {feature.get("id") or feature.get("properties", {}).get("id") for feature in atlas["features"]}
    if not set(ids).issubset(atlas_ids):
        raise ValueError("one or more issue subjects are absent from pinned Atlas part-0")
    if len(scoped.get("features", [])) != 214 or len(table) != 215:
        raise ValueError("pinned scoped source/table counts changed")

    baseline_paths = sorted({path for path, _ in EXPECTED_PINS.values()} | set(EXTRA_BASELINE))
    baseline_files = [descriptor(path, baseline_bytes(path)) for path in baseline_paths]
    baseline_by_path = {item["path"]: item for item in baseline_files}
    for name, (path, expected) in EXPECTED_PINS.items():
        if baseline_by_path[path]["sha256"] != expected:
            raise ValueError(f"issue pin mismatch for {name}")

    out_paths = sorted(OUTPUTS)
    out_descriptors = [descriptor(path, (ROOT / path).read_bytes()) for path in out_paths]
    out_by_path = {item["path"]: item for item in out_descriptors}
    source_hash = baseline_by_path[EXPECTED_PINS["scoped-source"][0]]["sha256"]
    measurement = json.loads((OWN / "output/ring-measurements.json").read_text(encoding="utf-8"))
    summary = measurement["summary"]

    metrics = []
    bindings = []

    def add_metric(metric_id, value, unit, input_hash, path, pointer):
        metrics.append({"id": metric_id, "value": value, "unit": unit, "vintage": "baseline",
                        "input_sha256": input_hash, "evaluation_commit": BASELINE})
        bindings.append({"metric_id": metric_id, "path": path, "json_pointer": pointer})

    ring_path = f"{OWN_REL}/output/ring-measurements.json"
    for index, subject in enumerate(measurement["subjects"]):
        metric_id = f"interior_rings_{subject['id']}"
        add_metric(metric_id, subject["interior_ring_count"], "interior-rings", source_hash,
                   ring_path, f"/subjects/{index}/interior_ring_count")
    for key, unit in [("zero_ring_subjects", "subjects"), ("subjects_with_rings", "subjects"), ("total_rings", "interior-rings")]:
        metric_id = key
        add_metric(metric_id, summary[key], unit, source_hash, ring_path, f"/summary/{key}")
    count_metric = "scope_subject_count"
    add_metric(count_metric, summary["subject_count"], "subjects", source_hash, ring_path, "/summary/subject_count")

    csv_path = f"{OWN_REL}/output/corrected-findings.csv"
    csv_bytes = (ROOT / csv_path).read_bytes()
    lines = csv_bytes.decode("utf-8").splitlines()
    summary_row = next(csv.DictReader(lines))
    if summary_row["record_type"] != "summary" or summary_row["record_count"] != "214":
        raise ValueError("corrected table summary row is not the exact 214-subject count")
    summary_line = lines[1]
    template = summary_line.replace("214", "{value}", 1)

    issue_source = {
        "id": "issue-1129-scope", "url": "https://api.github.com/repos/ChengshuLi/WorldAtlas/issues/1129",
        "role": "GitHub issue declaration of the exact subjects, pins, owned path and renderer-correction acceptance scope.",
        "vintage": "Issue body retrieved by GitHub API on 2026-10-06",
        "retrieved_at": "2026-10-06",
        "license": {"status": "unknown", "terms": "Issue text is scope evidence, not a geographic dataset."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
        "restoration": "Retrieve issue 1129 through GitHub API and compare its worldatlas-work:v1 evidence_quality.subject_ids array with scope.json.",
        "limit": "The issue defines this bounded scope and is not independent geographic evidence.",
    }
    geo_source = {
        "id": "geoboundaries-arg-adm2-2020", "url": "https://api.github.com/repos/wmgeolab/geoBoundaries/contents/releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2.geojson?ref=9469f09",
        "role": "Retained 2020 Argentina ADM2 geometry extract used solely to count coordinate interior rings and crosswalk exact native IDs.",
        "vintage": "geoBoundaries commit 9469f09; metadata boundaryYear 2020, sourceDataUpdateDate 2023-01-19, buildDate 2023-12-12; source agencies named as Instituto Geográfico Nacional and UNHCR/OCHA ROLAC",
        "retrieved_at": "2026-10-05",
        "license": {"status": "redistributable", "terms": "The exact source metadata declares Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO); attribute geoBoundaries and named source agencies."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
        "restoration": "Use pinned ancestor file data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020-scoped-214.geojson (SHA-256 7bcfe3ab98e03372a8d6e3c2d5a844f4176011c577cc090d2c823f6603cb1305); full source restoration directions and object hashes are retained in the pinned #443 source-register.json.",
        "limit": "A 214-feature scoped extract is not national-completeness or legal-boundary evidence. The #443 source register records an unresolved one-unit discrepancy between full-geometry features and metadata count.",
    }
    prior_context = {
        "id": "argentina-georef-neighbor-context", "url": "https://datos.gob.ar/dataset/jgm-servicio-normalizacion-datos-geograficos",
        "role": "Prior #443 neighboring comparison-source context; not used to measure or classify interior rings.",
        "vintage": "#443 full current Georef capture retrieved 2026-10-05; no legal effective date or version declared",
        "retrieved_at": "2026-10-05",
        "license": {"status": "redistributable", "terms": "#443 source register records CC BY 4.0 for the official normalization service."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
        "restoration": "Read the pinned #443 README.md and source-register.json in the declared baseline; the source register records retained Georef response paths, hashes, headers and source limitations.",
        "limit": "Comparison granularity mixes Departamento, Partido and Comuna; no legal boundary adjudication or complete comparable neighboring partition is inferred here.",
    }

    method = {
        "id": "ring-flag-renderer", "kind": "measurement",
        "description": "Count interior rings from each exact pinned GeoJSON polygon coordinate array, join source shapeID to the issue's exact Atlas subject, and render has_interior_rings with strict non-negative integer parsing. Preserve all other pinned table fields.",
        "software": "Python 3 standard library; JSON and CSV; SHA-256",
        "units": "interior ring count and yes/no flag",
    }
    evidence = {
        "version": 1, "issue": 1129, "lane": "geography", "worker_id": WORKER,
        "subject_ids": ids, "subject_ids_sha256": scope["subject_ids_sha256"],
        "baseline": {
            "commit": BASELINE, "files": baseline_files,
            "pins": {name: value for name, (_, value) in EXPECTED_PINS.items()},
            "pin_files": {name: path for name, (path, _) in EXPECTED_PINS.items()},
            "subject_files": {identity: "data/geography/part-0.json" for identity in ids},
        },
        "sources": [issue_source, geo_source, prior_context],
        "outputs": out_descriptors,
        "methods": [method], "metrics": metrics,
        "summaries": [
            {"metric_id": "zero_ring_subjects", "value": summary["zero_ring_subjects"], "unit": "subjects"},
            {"metric_id": "subjects_with_rings", "value": summary["subjects_with_rings"], "unit": "subjects"},
            {"metric_id": "total_rings", "value": summary["total_rings"], "unit": "interior-rings"},
        ],
        "metric_bindings": bindings,
        "rendered_tables": [{"path": csv_path, "rows": [{"metric_id": count_metric, "line": 2, "template": template, "decimals": 0}]}],
        "conclusions": [
            {"text": "The pinned source-coordinate measurement supports the corrected interior-ring flags for this exact 214-subject 2020 extract.", "status": "supported", "source_ids": ["geoboundaries-arg-adm2-2020"]},
            {"text": "The legal or physical meaning of the retained interior rings, current legal boundaries, and national completeness remain unresolved by this correction.", "status": "unresolved", "source_ids": ["geoboundaries-arg-adm2-2020", "argentina-georef-neighbor-context"]},
        ],
        "stages": {"research": "complete", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "python3 data/regional-review/argentina-ring-classification-953-20261006/corrected-renderer.py --scope data/regional-review/argentina-ring-classification-953-20261006/scope.json --source data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020-scoped-214.geojson --table data/regional-review/argentina-adm2-source-revalidation-443/findings/scoped-2020-to-current-georef-overlay.csv --baseline-renderer data/regional-review/argentina-adm2-source-revalidation-443/categorize-tabular-findings.py --out-dir data/regional-review/argentina-ring-classification-953-20261006/output",
            "node scripts/evidence-quality.mjs data/regional-review/argentina-ring-classification-953-20261006/evidence-quality.json .",
        ],
        "change_receipts": [{"path": path, "status": "added"} for path in sorted([*out_paths, f"{OWN_REL}/evidence-quality.json"])],
        "validation": [
            {"method_id": "ring-flag-renderer", "kind": "positive-control", "outcome": "passed", "evidence_path": f"{OWN_REL}/output/positive-control.json"},
            {"method_id": "ring-flag-renderer", "kind": "negative-control", "outcome": "passed", "evidence_path": f"{OWN_REL}/output/negative-control.json"},
            {"method_id": "ring-flag-renderer", "kind": "negative-control", "outcome": "passed", "evidence_path": f"{OWN_REL}/output/regression-control.json"},
            {"method_id": "ring-flag-renderer", "kind": "reproducibility", "outcome": "passed", "evidence_path": f"{OWN_REL}/output/reproducibility.json"},
        ],
    }
    # The table's numeric summary field is rendered with its exact row template.
    corrected = next(item for item in evidence["outputs"] if item["path"] == csv_path)
    corrected["role"] = "generated-table"
    target = OWN / "evidence-quality.json"
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target.relative_to(ROOT)} with {len(ids)} subjects, {len(metrics)} numeric metrics, and {len(evidence['change_receipts'])} change receipts")


if __name__ == "__main__":
    main()
