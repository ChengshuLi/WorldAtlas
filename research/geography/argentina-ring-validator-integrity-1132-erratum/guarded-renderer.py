#!/usr/bin/env python3
"""Run the pinned #1129 Argentina ring correction behind safe input/output gates.

The historical corrected-renderer remains unchanged. This entry point executes
its captured, immutable bytes in a private staging directory, then publishes
the complete result as one exclusive new vintage using the shared safeguards.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

OWN = "research/geography/argentina-ring-validator-integrity-1132-erratum/"
PIN_FILE = OWN + "input-pins.json"
PIN_SHA256 = "d35256e62ce2af7d7337178232605d4b41ce1a5c191a25a86483daa081942cac"
REQUIRED_PRODUCTS = (
    "corrected-findings.csv",
    "ring-measurements.json",
    "reproduction-report.json",
    "positive-control.json",
    "negative-control.json",
    "regression-control.json",
    "reproducibility.json",
)
REQUIRED_INPUTS = {
    "renderer": "data/regional-review/argentina-ring-classification-953-20261006/corrected-renderer.py",
    "scope": "data/regional-review/argentina-ring-classification-953-20261006/scope.json",
    "scope-evidence": "data/regional-review/argentina-ring-classification-953-20261006/evidence-quality.json",
    "table": "data/regional-review/argentina-adm2-source-revalidation-443/findings/scoped-2020-to-current-georef-overlay.csv",
    "source": "data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020-scoped-214.geojson",
    "baseline-renderer": "data/regional-review/argentina-adm2-source-revalidation-443/categorize-tabular-findings.py",
}
PINNED_PRODUCT_PATHS = {
    "corrected-findings.csv": "data/regional-review/argentina-ring-classification-953-20261006/output/corrected-findings.csv",
    "ring-measurements.json": "data/regional-review/argentina-ring-classification-953-20261006/output/ring-measurements.json",
    "reproduction-report.json": "data/regional-review/argentina-ring-classification-953-20261006/output/reproduction-report.json",
    "reproducibility.json": "data/regional-review/argentina-ring-classification-953-20261006/output/reproducibility.json",
}
SOURCE_REGISTER = "data/regional-review/argentina-adm2-source-revalidation-443/source-register.json"
SOURCE_METADATA = "data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020/geoBoundaries-ARG-ADM2-metaData.json"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_helper(repo: Path, helper_pin: dict):
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{helper_pin['commit']}:{helper_pin['path']}"]
    )
    if len(raw) != helper_pin["bytes"] or digest(raw) != helper_pin["sha256"]:
        raise ValueError("Shared immutable evidence helper differs from its whole-file pin")
    module = type(sys)("pinned_immutable_evidence")
    module.__file__ = helper_pin["path"]
    exec(compile(raw, helper_pin["path"], "exec"), module.__dict__)
    return module


def load_pin_contract(repo: Path) -> tuple[dict, bytes]:
    raw = (repo / PIN_FILE).read_bytes()
    if digest(raw) != PIN_SHA256:
        raise ValueError("Input-pin contract changed; compare it with the issue's reviewed pins")
    pins = json.loads(raw)
    if pins.get("scope_issue") != 1351 or pins.get("scope_subject_count") != 214:
        raise ValueError("Unexpected issue or subject scope")
    entries = {row["path"]: row for row in pins["files"]}
    if len(entries) != len(pins["files"]):
        raise ValueError("Duplicate immutable pin paths")
    if not set(REQUIRED_INPUTS.values()).issubset(entries):
        raise ValueError("A required consumed input lacks a whole-file pin")
    if not set(PINNED_PRODUCT_PATHS.values()).issubset(entries):
        raise ValueError("A required prior product lacks a whole-file pin")
    for key, name in REQUIRED_INPUTS.items():
        if name not in entries:
            raise ValueError("Unexpected input contract")
    return pins, raw


def select_input_path(repo: Path, supplied: str | None, expected: str) -> Path:
    target = (repo / expected).resolve()
    if supplied is None:
        return target
    actual = Path(supplied).resolve()
    if actual != target:
        raise ValueError(f"Unpinned caller-selected input rejected: {supplied}")
    return actual


def run_renderer(python: str, renderer: bytes, inputs: dict[str, bytes], stage: Path) -> dict[str, bytes]:
    stage.mkdir(mode=0o700)
    script = stage / "corrected-renderer.py"
    script.write_bytes(renderer)
    args = [python, "-B", str(script)]
    for flag, key in (("--scope", "scope"), ("--source", "source"), ("--table", "table"),
                      ("--baseline-renderer", "baseline-renderer")):
        path = stage / (key + (".csv" if key == "table" else ".json" if key == "scope" else ".py" if key == "baseline-renderer" else ".geojson"))
        path.write_bytes(inputs[key])
        args.extend((flag, str(path)))
    out = stage / "products"
    args.extend(("--out-dir", str(out)))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    subprocess.run(args, check=True, cwd=stage, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not out.is_dir():
        raise ValueError("Pinned renderer did not create its private output directory")
    names = sorted(p.name for p in out.iterdir())
    if names != sorted(REQUIRED_PRODUCTS) or any(not (out / n).is_file() or (out / n).is_symlink() for n in names):
        raise ValueError("Pinned renderer output inventory is incomplete or unexpected")
    return {name: (out / name).read_bytes() for name in REQUIRED_PRODUCTS}


def inspect_products(products: dict[str, bytes], expected_ids: list[str], prior_table: bytes) -> dict:
    measurements = json.loads(products["ring-measurements.json"])
    subjects = measurements.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 214:
        raise ValueError("Renderer did not report all 214 scoped source subjects")
    by_id = {row.get("id"): row for row in subjects}
    if len(by_id) != 214 or set(by_id) != set(expected_ids):
        raise ValueError("Renderer output identity roster differs from the exact issue scope")
    rings = {identity: by_id[identity].get("interior_ring_count") for identity in expected_ids}
    positive = {identity: value for identity, value in rings.items() if value != 0}
    itati = "gb:ARG:ADM2:61730980B76052784863315"
    if rings.get(itati) != 5 or positive != {itati: 5} or sum(rings.values()) != 5:
        raise ValueError("Pinned source did not reproduce the independently expected 213/one/five ring result")
    prior_rows = list(csv.DictReader(io.StringIO(prior_table.decode("utf-8"), newline="")))
    table = list(csv.DictReader(io.StringIO(products["corrected-findings.csv"].decode("utf-8"), newline="")))
    details = [row for row in table if row.get("record_type") == "detail"]
    prior_details = [row for row in prior_rows if row.get("record_type") == "detail"]
    if len(details) != 214 or {row.get("atlas_id") for row in details} != set(expected_ids):
        raise ValueError("Corrected CSV does not contain the exact 214 detail identities")
    if len(prior_rows) != 215 or len(prior_details) != 214 or table[0] != prior_rows[0]:
        raise ValueError("Pinned prior table summary or row inventory changed")
    prior_by_id = {row["atlas_id"]: row for row in prior_details}
    if len(prior_by_id) != 214 or set(prior_by_id) != set(expected_ids):
        raise ValueError("Pinned prior table identities differ from the issue scope")
    flags = {row["atlas_id"]: row["has_interior_rings"] for row in details}
    if sum(flag == "no" for flag in flags.values()) != 213 or flags.get(itati) != "yes" or sum(flag == "yes" for flag in flags.values()) != 1:
        raise ValueError("Corrected table does not report exactly 213 false flags and Itatí's positive flag")
    changed = 0
    by_id = {row["atlas_id"]: row for row in details}
    for identity in expected_ids:
        before, after = prior_by_id[identity], by_id[identity]
        if before.keys() != after.keys():
            raise ValueError("Output table schema changed")
        for field, old_value in before.items():
            if field == "has_interior_rings":
                changed += old_value != after[field]
                if after[field] != ("yes" if rings[identity] > 0 else "no"):
                    raise ValueError("Rendered flag disagrees with direct coordinate ring count")
            elif old_value != after[field]:
                raise ValueError("A non-target comparison-table field changed")
    if changed != 213:
        raise ValueError("Expected exactly 213 corrected false flags relative to the pinned prior output")
    for name, value in (("positive-control.json", {"outcome": "passed"}),
                        ("negative-control.json", {"outcome": "passed"}),
                        ("regression-control.json", {"outcome": "passed", "original_expression_for_zero": "yes", "corrected_expression_for_zero": "no", "regression_detects_original_defect": True})):
        record = json.loads(products[name])
        if any(record.get(key) != expected for key, expected in value.items()):
            raise ValueError("A nonvacuous renderer control did not pass: " + name)
    positive_control = json.loads(products["positive-control.json"])
    if positive_control.get("zero_flag") != "no" or positive_control.get("positive_flag") != "yes":
        raise ValueError("Zero/positive ring controls do not exercise expected cases")
    if json.loads(products["negative-control.json"]).get("all_cases_rejected") is not True:
        raise ValueError("Malformed and negative count cases were not rejected")
    return {"subjects": 214, "zero_ring_subjects": 213, "positive_ring_subjects": 1,
            "total_interior_rings": 5, "positive_subject_ids": [itati],
            "changed_false_flag_count": 213,
            "all_other_table_fields": "byte-parsed detail cells and complete summary row equal the pinned prior output"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintage", required=True, help="A fresh plain-name output vintage under this packet")
    parser.add_argument("--out-dir", help="Optional spelling of the exact owned vintage path; escapes are rejected")
    parser.add_argument("--scope")
    parser.add_argument("--source")
    parser.add_argument("--table")
    parser.add_argument("--baseline-renderer")
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[3]
    pins, pin_contract_bytes = load_pin_contract(repo)
    helper = load_helper(repo, pins["runner_helper"])
    baseline = helper.Baseline(repo, pins["baseline_commit"], pins["files"] + pins.get("context_files", []))
    ids = pins["subject_ids"]
    if len(ids) != 214 or len(set(ids)) != 214 or digest(json.dumps(ids, separators=(",", ":"), ensure_ascii=False).encode()) != pins["subject_ids_sha256"]:
        raise ValueError("Exact issue subject inventory failed its canonical digest")

    actual_paths = {key: select_input_path(repo, getattr(args, key.replace("-", "_"), None), value)
                    for key, value in REQUIRED_INPUTS.items() if key in ("scope", "source", "table", "baseline-renderer")}
    # Capture all bytes from the immutable commit before any computation. The
    # explicit materialized-byte equality also detects drift in the working copy.
    captured = {key: baseline.materialized_bytes(path.relative_to(repo).as_posix())
                for key, path in actual_paths.items()}
    scope = json.loads(captured["scope"])
    if scope.get("subject_ids") != ids or scope.get("subject_ids_sha256") != pins["subject_ids_sha256"]:
        raise ValueError("Actually consumed scope differs from the exact issue identity roster")
    renderer_path = REQUIRED_INPUTS["renderer"]
    renderer = baseline.pinned_bytes(renderer_path)
    pins_by_path = {row["path"]: row for row in pins["files"]}
    for key, path in actual_paths.items():
        if digest(captured[key]) != pins_by_path[path.relative_to(repo).as_posix()]["sha256"]:
            raise ValueError("Captured materialized input differs from its named issue pin: " + key)

    out_root = repo / OWN / "vintages" / args.vintage
    if args.out_dir is not None and Path(args.out_dir).resolve() != out_root.resolve():
        raise ValueError("Output path must equal the issue-owned new-vintage path")
    output_names = list(REQUIRED_PRODUCTS) + ["consumed-inputs.json", "run-summary.json", "guarded-reproducibility.json"]
    vintage = helper.NewVintage(baseline, OWN, args.vintage, output_names)

    with tempfile.TemporaryDirectory(prefix=".renderer-scratch-", dir=repo / OWN) as scratch:
        scratch = Path(scratch)
        run_one = run_renderer(sys.executable, renderer, captured, scratch / "run-one")
        run_two = run_renderer(sys.executable, renderer, captured, scratch / "run-two")
    if run_one != run_two:
        raise ValueError("Two fresh actual pinned-renderer CLI executions differ")
    for product, source_path in PINNED_PRODUCT_PATHS.items():
        if run_one[product] != baseline.pinned_bytes(source_path):
            raise ValueError("Actual output differs from its exact prior corrected-output pin: " + product)
    summary = inspect_products(run_one, ids, baseline.pinned_bytes(REQUIRED_INPUTS["table"]))
    register = json.loads(baseline.pinned_bytes(SOURCE_REGISTER))
    source_rows = [row for row in register["sources"] if row.get("id") == "geoboundaries-arg-adm2-2020-scoped-214"]
    if len(source_rows) != 1 or not isinstance(source_rows[0].get("original_full_object", {}).get("feature_count"), int):
        raise ValueError("Pinned #443 source register lacks its unique full-object feature-count record")
    prior_full_count = source_rows[0]["original_full_object"]["feature_count"]
    metadata = json.loads(baseline.pinned_bytes(SOURCE_METADATA))
    declared_count = metadata.get("admUnitCount")
    if isinstance(declared_count, str) and re.fullmatch(r"(?:0|[1-9][0-9]*)", declared_count):
        declared_count = int(declared_count)
    if not isinstance(declared_count, int) or isinstance(declared_count, bool):
        raise ValueError("Pinned geoBoundaries metadata lacks a numeric ADM2 declared count")
    product_hashes = {name: digest(raw) for name, raw in sorted(run_one.items())}
    consumed = {
        "version": 1,
        "baseline_commit": pins["baseline_commit"],
        "subject_count": len(ids),
        "subject_ids_sha256": pins["subject_ids_sha256"],
        "inputs": [{"path": path.relative_to(repo).as_posix(), "bytes": len(raw), "sha256": digest(raw), "hash_kind": "file-bytes"}
                   for key, raw in captured.items() for path in [actual_paths[key]]],
        "renderer": {"path": renderer_path, "bytes": len(renderer), "sha256": digest(renderer), "hash_kind": "file-bytes"},
        "guarded_entry_point": {"path": OWN + "guarded-renderer.py", "bytes": Path(__file__).stat().st_size,
                                "sha256": digest(Path(__file__).read_bytes()), "hash_kind": "file-bytes",
                                "note": "Entry-point source identity; independent review is bound to the exact committed PR head."},
        "pin_contract": {"path": PIN_FILE, "bytes": len(pin_contract_bytes), "sha256": digest(pin_contract_bytes), "hash_kind": "file-bytes"},
        "verified_context_files": [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"], "hash_kind": "file-bytes"}
                                   for row in pins.get("context_files", [])],
        "runtime": {"python_executable": Path(sys.executable).name, "python_version": platform.python_version(), "standard_library_only": True},
        "execution": "Two fresh subprocess CLI executions of the captured corrected-renderer.py bytes; each legacy execution performs its own two complete internal builds.",
    }
    reproducibility = {"method_id": "argentina-ring-guarded-renderer", "kind": "reproducibility", "outcome": "passed",
                       "run_count": 2, "products": product_hashes, "byte_identical": True,
                       "all_four_pinned_products_match": True}
    outputs = dict(run_one)
    outputs["consumed-inputs.json"] = (json.dumps(consumed, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    outputs["run-summary.json"] = (json.dumps({"issue": 1351, "scope": "Argentina ADM2 exact 214 subjects",
        "prior_full_source_register_feature_count": prior_full_count,
        "source_metadata_admUnitCount": declared_count,
        **summary,
        "geographic_limits": ["2020 retained source vintage only; no current legal-boundary adjudication.",
        "The pinned #443 source register records 525 features for the restored full object, while its pinned metadata declares 526 ADM2 units; the mismatch remains unresolved.",
        "Interior-ring presence does not determine physical or legal meaning; no regional approval, import or publication is claimed."]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    outputs["guarded-reproducibility.json"] = (json.dumps(reproducibility, indent=2, sort_keys=True) + "\n").encode()
    vintage.publish_bytes(outputs)
    receipt_hash = digest((out_root / "publication.json").read_bytes())
    print(json.dumps({"vintage": args.vintage, "output": str(out_root), "publication_receipt_sha256": receipt_hash,
                      "summary": summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as error:
        print(f"guarded renderer rejected run: {error}", file=sys.stderr)
        raise SystemExit(2)
