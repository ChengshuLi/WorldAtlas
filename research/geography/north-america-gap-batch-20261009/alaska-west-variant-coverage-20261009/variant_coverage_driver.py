#!/usr/bin/env python3
"""Run only four candidate coverage checks against two retained USA ADM2 variants."""
from __future__ import annotations

import hashlib
import json
import pathlib
import stat
import subprocess
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = "research/geography/north-america-gap-batch-20261009/alaska-west-variant-coverage-20261009"
PHASE_PATH = PACKET + "/phase-admission.json"
RUN_NAME = "coverage-run-20261010-01"
OUTPUTS = ["source-variant-coverage.json"]
IDS = [
    "physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0",
    "physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a",
    "physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4",
    "physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6",
]
SOURCES = {
    "full": "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/geoboundaries-USA-ADM2-full-9469f09.geojson",
    "simplified": "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/geoBoundaries-USA-ADM2_simplified.geojson",
}
TARGET_ID = "52423323B14067598441828"
EVIDENCE = "research/geography/north-america-gap-batch-20261009/alaska-west-four-source-physical-evidence.json"
METHOD = "research/geography/alaska-thirteen-geometry-measurement-20261008/measure_alaska.py"
HELPER = "scripts/evidence/immutable.py"
PYTHON = "/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def main() -> int:
    commit = git("rev-parse", "HEAD").decode().strip()
    phase_raw = git("show", f"{commit}:{PHASE_PATH}")
    if (ROOT / PHASE_PATH).read_bytes() != phase_raw:
        raise SystemExit("phase admission differs from immutable HEAD")
    phase = json.loads(phase_raw)
    if phase.get("status") != "PASS" or phase.get("scientific_operations_invoked") is not False:
        raise SystemExit("passing prospective phase admission is required")
    if phase.get("max_process_bytes") != 536870912 or phase.get("cap_bytes") != 268435456:
        raise SystemExit("phase must pin the 512 MiB process and 256 MiB complete-phase caps")

    pins = {}
    for row in phase.get("inputs", []) + phase.get("project_code", []):
        desc = {"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"], "hash_kind": "file-bytes"}
        if row["path"] in pins and pins[row["path"]] != desc:
            raise SystemExit("conflicting phase descriptor: " + row["path"])
        pins[row["path"]] = desc
    phase_desc = {"path": PHASE_PATH, "bytes": len(phase_raw), "sha256": sha(phase_raw), "hash_kind": "file-bytes"}
    pins[PHASE_PATH] = phase_desc

    helper_raw = git("show", f"{commit}:{HELPER}")
    if sha(helper_raw) != pins[HELPER]["sha256"]:
        raise SystemExit("immutable helper does not match the admitted code pin")
    helper = types.ModuleType("pinned_evidence_immutable")
    helper.__file__ = str(ROOT / HELPER)
    exec(compile(helper_raw, helper.__file__, "exec"), helper.__dict__)
    baseline = helper.Baseline(ROOT, commit, list(pins.values()))
    for name in pins:
        baseline.materialized_bytes(name)

    runtime = phase["runtime_file_closure"]
    if sum(row["bytes"] for row in runtime) != phase["component_totals"]["imported_runtime_files_and_python_executable"]:
        raise SystemExit("runtime closure does not match prospective byte inventory")
    verified = set()
    for row in runtime:
        path = pathlib.Path(row["path"])
        actual = path.resolve(strict=True)
        raw = actual.read_bytes()
        if (str(actual) != row["realpath"] or not actual.is_file() or len(raw) != row["bytes"]
                or sha(raw) != row["sha256"] or stat.S_IMODE(actual.stat().st_mode) != row["mode"]):
            raise SystemExit("runtime closure changed: " + str(path))
        if str(actual) in verified:
            raise SystemExit("duplicate runtime closure member")
        verified.add(str(actual))
        baseline.admit("runtime:" + str(actual), len(raw))

    totals = phase["component_totals"]
    scratch = totals["scratch_reservation"]
    output_reserve = totals["generated_output_reservation"]
    if not isinstance(scratch, int) or not isinstance(output_reserve, int):
        raise SystemExit("scratch/output reservations are missing")
    baseline.admit("reserve:bounded-source-coverage-scratch", scratch)
    if sum(baseline.consumed.values()) + output_reserve > baseline.max_phase_bytes:
        raise SystemExit("actual raw inputs, runtime, scratch and output reservation exceed 256 MiB")
    if output_reserve > len(OUTPUTS) * helper.MAX_FILE_BYTES:
        raise SystemExit("output reservation exceeds the admitted per-file count")

    vintage = helper.NewVintage(baseline, PACKET + "/", RUN_NAME, OUTPUTS)
    modules = baseline.load_modules({"alaska_measurement": METHOD})
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        resolved = pathlib.Path(filename).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
            continue
        except ValueError:
            pass
        if str(resolved) not in verified:
            raise SystemExit("loaded external code is outside admitted runtime closure: " + str(resolved))
        row = next(item for item in runtime if item["realpath"] == str(resolved))
        raw = resolved.read_bytes()
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"] or stat.S_IMODE(resolved.stat().st_mode) != row["mode"]:
            raise SystemExit("loaded runtime member changed after admission: " + str(resolved))

    producer = modules["alaska_measurement"]
    producer.PROJECT = producer.Transformer.from_crs(
        producer.CRS.from_epsg(4326), producer.CRS.from_epsg(3338), always_xy=True
    ).transform
    evidence_raw = baseline.materialized_bytes(EVIDENCE)
    evidence = json.loads(evidence_raw)
    candidate_rows = {row["component_id"]: row for row in evidence["custody"]["features"]}
    if set(candidate_rows) != set(IDS):
        raise SystemExit("the four admitted candidate feature identities differ")
    candidate_geoms = {}
    candidate_provenance = {}
    for identity in IDS:
        row = candidate_rows[identity]
        feature = row["feature"]
        if feature.get("id") != identity or feature.get("type") != "Feature":
            raise SystemExit("candidate feature identity/type mismatch: " + identity)
        candidate_geoms[identity] = producer.shape(feature["geometry"])
        candidate_provenance[identity] = {
            "component_id": identity,
            "feature_sha256": row["feature_sha256"],
            "geometry_sha256": row["geometry_sha256"],
        }

    source_features = {}
    for variant, path in SOURCES.items():
        raw = baseline.materialized_bytes(path)
        document = json.loads(raw)
        matches = [feature for feature in document["features"]
                   if feature.get("properties", {}).get("shapeID") == TARGET_ID]
        if len(matches) != 1:
            raise SystemExit(f"{variant} source must contain exactly one Aleutians West feature")
        feature = matches[0]
        if feature.get("properties", {}).get("shapeName") != "Aleutians West":
            raise SystemExit(f"{variant} target name differs from pinned source identity")
        source_features[variant] = {
            "feature": feature,
            "descriptor": {"path": path, "bytes": len(raw), "sha256": sha(raw)},
        }

    cases = []
    for identity in IDS:
        measured = {}
        for variant in ("full", "simplified"):
            source = source_features[variant]
            row = producer.intersections(candidate_geoms[identity], producer.shape(source["feature"]["geometry"]))
            measured[variant] = row
        full, simple = measured["full"], measured["simplified"]
        coverage_agreement = bool(
            full.get("status") == simple.get("status") == "measured"
            and full.get("candidate_covered_exactly") == simple.get("candidate_covered_exactly")
            and full.get("positive_area_overlap") == simple.get("positive_area_overlap")
            and full.get("intersection_area_projected_m2_exact") == simple.get("intersection_area_projected_m2_exact")
            and full.get("candidate_uncovered_area_projected_m2_exact") == simple.get("candidate_uncovered_area_projected_m2_exact")
            and full.get("candidate_coverage_ratio") == simple.get("candidate_coverage_ratio")
        )
        exact_cover = lambda row: row.get("status") == "measured" and row.get("candidate_covered_exactly") is True and row.get("candidate_uncovered_area_projected_m2_exact") == 0 and row.get("candidate_coverage_ratio") == 1
        cases.append({
            **candidate_provenance[identity],
            "full": measured["full"],
            "simplified": measured["simplified"],
            "source_variants_agree_on_coverage_predicate_outputs": coverage_agreement,
            "source_variants_same_for_this_candidate": coverage_agreement,
            "literal_retained_county_coverage_premises": {
                "candidate_vs_full_county": exact_cover(full),
                "candidate_vs_simplified_county": exact_cover(simple),
                "candidate_source_variants_agree_for_this_candidate": coverage_agreement,
            },
        })

    result = {
        "schema_version": 1,
        "status": "measured",
        "scope": "Exactly four PR #1653 component candidates measured only against the full and simplified retained geoBoundaries USA ADM2 Aleutians West feature from immutable release 9469f09.",
        "baseline_commit": commit,
        "runtime": phase["runtime"],
        "runtime_file_count": len(phase["runtime_file_closure"]),
        "runtime_closure_bytes": sum(row["bytes"] for row in phase["runtime_file_closure"]),
        "candidate_ids": IDS,
        "target": {"shape_id": TARGET_ID, "source_id": "gb:USA:ADM2:" + TARGET_ID,
                   "administrative_level": "ADM2", "name": "Aleutians West", "represented_year_claim": "2018"},
        "source_release_commit": "9469f09592ced973a3448cf66b6100b741b64c0d",
        "source_variants": {key: value["descriptor"] for key, value in source_features.items()},
        "method": {
            "project": "The unchanged intersections() function from the pinned Alaska measurement method; EPSG:4326 inputs projected with always_xy to EPSG:3338 for areas.",
            "coverage_rule": "status=measured, candidate_covered_exactly=true, candidate_uncovered_area_projected_m2_exact=0, candidate_coverage_ratio=1.",
            "coverage_variant_agreement": "Same measured status, exact coverage boolean, positive-area-overlap boolean, exact projected intersection area, exact projected uncovered area and coverage ratio for each candidate. Neither whole-source nor clipped-geometry equality is tested or required.",
            "authorization": "Single bounded first-time source-coverage check authorized by amended #1630; no source replacement, other candidates, native, roster, conservation or production operation.",
        },
        "cases": cases,
        "summary": {
            "candidate_count": len(cases),
            "variant_comparisons": sum(len(["full", "simplified"]) for _ in cases),
            "full_coverage_pass_count": sum(case["literal_retained_county_coverage_premises"]["candidate_vs_full_county"] for case in cases),
            "simplified_coverage_pass_count": sum(case["literal_retained_county_coverage_premises"]["candidate_vs_simplified_county"] for case in cases),
            "candidate_variant_agreement_count": sum(case["source_variants_agree_on_coverage_predicate_outputs"] for case in cases),
            "literal_source_variant_agreement_count": sum(case["literal_retained_county_coverage_premises"]["candidate_source_variants_agree_for_this_candidate"] for case in cases),
            "literal_rule_fit_count": sum(all(case["literal_retained_county_coverage_premises"].values()) for case in cases),
            "scientific_approval": False,
            "source_approval": False,
        },
    }
    record = vintage.publish({OUTPUTS[0]: result})
    print(json.dumps({"status": result["status"], "run": RUN_NAME, "outputs": record, "summary": result["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
