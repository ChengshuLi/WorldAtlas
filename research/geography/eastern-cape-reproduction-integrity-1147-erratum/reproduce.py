#!/usr/bin/env python3
"""Authenticated, bounded reproduction for the Eastern Cape #1371 erratum."""
from __future__ import annotations
import argparse
import contextlib
import copy
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.evidence import immutable as immutable_tools
from scripts.evidence.immutable import Baseline, NewVintage

OWNED = "research/geography/eastern-cape-reproduction-integrity-1147-erratum/"
BASELINE_COMMIT = "de506f51100568e150e51f2926a5259b71e55272"
ISSUE_BODY_PATH = OWNED + "source-records/issue-contract-20261007.md"
ISSUE_BODY_SHA256 = "b1e95090949c9d058284bc58290e0fd9650ed94afc2aaa16eb607369c78cc916"
SOURCE_LOCK_PATH = OWNED + "source-lock.json"
SOURCE_LOCK_SHA256 = "475283fffd4e507cb96c933aefbf3ddcfdfd82e5abcb2e74474110970651d377"
CURRENT_HELPER_PINS = {
    "scripts/evidence/immutable.py": "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46",
    "scripts/evidence/geometry.py": "4b016a4efccf8a1080b048f350c0db94ac14343b40e0ed890c2ce4d2300436a9",
    "scripts/ellipsoidal_area.py": "4ead1c5de909b257a7b300984e4d3dc56124e9a6c0d27240662024e44fd8ed12",
}
OLD_MEASUREMENT = "data/regional-review/eastern-cape-source-restoration-435/measure_boundary_vintages.py"
OLD_RESULT = "data/regional-review/eastern-cape-source-restoration-435/findings/boundary-vintage-differences.json"
INPUT_PATHS = {
    "attributes_2021": "data/regional-review/eastern-cape-source-restoration-435/sources/mdb-2021-eastern-cape-attribute-roster.json",
    "geometry_2021": "data/regional-review/eastern-cape-source-restoration-435/sources/mdb-2021-eastern-cape-boundaries.geojson",
    "attributes_2026": "data/regional-review/eastern-cape-source-restoration-435/sources/mdb-2026-eastern-cape-attribute-roster.json",
    "geometry_2026": "data/regional-review/eastern-cape-source-restoration-435/sources/mdb-2026-eastern-cape-boundaries.geojson",
}
OUTPUT_NAMES = ["legacy-result.json", "result.json", "execution.json"]
PIN_RE = re.compile(
    r"^- `(baseline_\d+|original_1147_\d+)`: `([^`]+)` at `([a-f0-9]{40})`; "
    r"(\d+) bytes; SHA-256 `([a-f0-9]{64})`\.$", re.M
)
IDENTITY_FIELDS = ("CAT_B", "MUNICNAME", "CATEGORY", "DISTRICT", "DISTRICT_N", "PROVINCE")
MEASURE_FIELDS = (
    "area_2021_m2", "area_2026_m2", "net_area_change_m2", "symmetric_difference_m2",
    "intersection_over_union", "old_polygon_parts", "new_polygon_parts",
)
FIXTURE_NAMES = [
    "duplicate-geometry-2021.geojson",
    "missing-geometry-2021.geojson",
    "swapped-code-geometry-2021.geojson",
    "ambiguous-name-geometry-2021.geojson",
    "geometry-helper-altered.py",
    "source-lock-substitution.json",
    "fixtures.json",
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def relpath(path: str) -> str:
    if not isinstance(path, str) or not path or "\\" in path or "\0" in path or any(x in ("", ".", "..") for x in path.split("/")):
        raise ValueError("Unsafe repository path")
    return path


def read_repo(path: str, limit: int = 32 * 1024 * 1024) -> bytes:
    path = relpath(path)
    target = ROOT / path
    for ancestor in (target, *target.parents):
        if ancestor == ROOT.parent:
            break
        if ancestor.is_symlink():
            raise ValueError(f"Symlink in evidence input path: {path}")
    raw = target.read_bytes()
    if len(raw) > limit:
        raise ValueError(f"Input exceeds 32 MiB: {path}")
    return raw


def load_issue_and_lock(lock_path: str = SOURCE_LOCK_PATH) -> tuple[dict, bytes]:
    issue_raw = read_repo(ISSUE_BODY_PATH)
    if sha(issue_raw) != ISSUE_BODY_SHA256:
        raise ValueError("Exact captured GitHub issue body drifted")
    lock_raw = read_repo(lock_path)
    if lock_path == SOURCE_LOCK_PATH and sha(lock_raw) != SOURCE_LOCK_SHA256:
        raise ValueError("Committed source lock changed; review against the exact issue body")
    if sha(lock_raw) != SOURCE_LOCK_SHA256:
        raise ValueError("Source-lock substitution does not match the reviewed issue pins")
    lock = json.loads(lock_raw, object_pairs_hook=unique_object)
    if lock.get("version") != 1 or lock.get("issue_number") != 1371 or lock.get("baseline_commit") != BASELINE_COMMIT:
        raise ValueError("Unsupported issue source lock")
    if lock.get("issue_body_sha256") != ISSUE_BODY_SHA256:
        raise ValueError("Source lock is not bound to the exact issue body")
    contract_body = issue_raw.decode("utf-8")
    matches = list(PIN_RE.finditer(contract_body))
    expected = [{"id": m[1], "path": m[2], "contract_commit": m[3], "bytes": int(m[4]), "sha256": m[5]}
                for m in matches]
    if len(expected) != 27 or lock.get("contract_pins") != expected:
        raise ValueError("Issue pin roster differs from the captured source lock")
    if len({x["path"] for x in expected}) != 27:
        raise ValueError("Issue contains duplicate source paths")
    if len(lock.get("files", [])) != 30 or lock.get("complete_pinned_input_and_code_bytes", 0) > 256 * 1024 * 1024:
        raise ValueError("Source lock violates complete file/phase bounds")
    code = {x["path"]: x["sha256"] for x in lock["current_project_code"]}
    if code != CURRENT_HELPER_PINS:
        raise ValueError("Project-helper inventory differs from its reviewed current-main pins")
    return lock, lock_raw


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"Duplicate JSON object key: {key}")
        out[key] = value
    return out


def create_baseline(lock: dict) -> Baseline:
    helper_file = ROOT / "scripts/evidence/immutable.py"
    if sha(helper_file.read_bytes()) != CURRENT_HELPER_PINS["scripts/evidence/immutable.py"]:
        raise ValueError("Executing shared immutable helper is not the pinned current-main code")
    baseline = Baseline(str(ROOT), BASELINE_COMMIT, lock["files"])
    if sum(baseline.consumed.values()) != lock["complete_pinned_input_and_code_bytes"]:
        raise ValueError("Authenticated complete phase byte count differs from source lock")
    # Compare the actual materialized project code with its Git blob before relying on it.
    for path, digest in CURRENT_HELPER_PINS.items():
        raw = baseline.materialized_bytes(path)
        if sha(raw) != digest:
            raise ValueError(f"Materialized project helper mismatch: {path}")
    return baseline


def parse_json(raw: bytes, name: str) -> dict:
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except Exception as exc:
        raise ValueError(f"Invalid unique-key JSON in {name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected object root in {name}")
    return value


def parse_feature_roster(raw: bytes, *, has_geometry: bool, label: str) -> list[dict]:
    value = parse_json(raw, label)
    rows = value.get("features")
    if not isinstance(rows, list):
        raise ValueError(f"{label}: missing complete MDB feature array")
    out = []
    for position, feature in enumerate(rows):
        if not isinstance(feature, dict):
            raise ValueError(f"{label}: malformed feature at row {position}")
        props = feature.get("properties") if has_geometry else feature.get("attributes")
        if not isinstance(props, dict):
            raise ValueError(f"{label}: missing source attributes/properties at row {position}")
        for field in IDENTITY_FIELDS:
            if not isinstance(props.get(field), str) or not props[field].strip():
                raise ValueError(f"{label}: missing required {field} at row {position}")
        expected_province = "Eastern Cape" if "2026" in label else "EC"
        if props["PROVINCE"] != expected_province or props["CATEGORY"] not in ("A", "B"):
            raise ValueError(f"{label}: unexpected province/category at row {position}")
        if has_geometry:
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict) or geometry.get("type") != "Polygon" or not isinstance(geometry.get("coordinates"), list):
                raise ValueError(f"{label}: missing Polygon geometry at row {position}")
        out.append({"props": props, "feature": feature})
    codes = [x["props"]["CAT_B"] for x in out]
    if len(codes) != len(set(codes)):
        raise ValueError(f"{label}: duplicate raw municipality codes")
    if len(out) != 33:
        raise ValueError(f"{label}: expected the complete 33-feature MDB roster; found {len(out)}")
    return out


def validate_inputs(inputs: dict[str, bytes]) -> dict:
    parsed = {}
    for key, path in INPUT_PATHS.items():
        if key not in inputs:
            raise ValueError(f"Missing actual source input: {key}")
        parsed[key] = parse_feature_roster(inputs[key], has_geometry=key.startswith("geometry_"), label=path)
    attr21, geo21 = parsed["attributes_2021"], parsed["geometry_2021"]
    attr26, geo26 = parsed["attributes_2026"], parsed["geometry_2026"]

    def associate(attributes: list[dict], geometries: list[dict], label: str) -> dict[str, dict]:
        attrs = {x["props"]["CAT_B"]: x["props"] for x in attributes}
        geos = {x["props"]["CAT_B"]: x for x in geometries}
        if len(attrs) != 33 or len(geos) != 33 or set(attrs) != set(geos):
            raise ValueError(f"{label}: incomplete or ambiguous code join")
        for code in sorted(attrs):
            for field in IDENTITY_FIELDS:
                if attrs[code][field] != geos[code]["props"][field]:
                    raise ValueError(f"{label}: code/name/source-field mismatch for {code} ({field})")
        return attrs

    source21 = associate(attr21, geo21, "MDB 2021")
    source26 = associate(attr26, geo26, "MDB 2026")
    codes21, codes26 = set(source21), set(source26)
    if codes21 != codes26 or len(codes21) != 33:
        raise ValueError("2021/2026 complete code rosters differ")
    if any(not source21[code]["DISTRICT"] or not source21[code]["DISTRICT_N"] for code in codes21):
        raise ValueError("MDB 2021 has an empty source district code/name")
    return {
        "attributes_2021": source21,
        "attributes_2026": source26,
        "codes": sorted(codes21),
        "counts": {
            "features_2021_attributes": len(attr21), "features_2021_geometry": len(geo21),
            "features_2026_attributes": len(attr26), "features_2026_geometry": len(geo26),
            "unique_codes_2021": len(source21), "unique_codes_2026": len(source26),
            "nonempty_2021_district_codes": len(source21),
            "district_code_values_2021": len({x["DISTRICT"] for x in source21.values()}),
            "distinct_2021_district_names": len({x["DISTRICT_N"] for x in source21.values()}),
            "identity_field_join_checks": 33 * 2 * len(IDENTITY_FIELDS),
        },
    }


def authenticated_inputs(baseline: Baseline, fixtures: dict | None = None) -> tuple[dict[str, bytes], dict]:
    inputs = {key: baseline.materialized_bytes(path) for key, path in INPUT_PATHS.items()}
    fixture_descriptors = {}
    if fixtures:
        for input_key, (path, raw) in fixtures.items():
            baseline.admit("candidate-fixture:" + path, len(raw))
            inputs[input_key] = raw
            fixture_descriptors[path] = {"bytes": len(raw), "sha256": sha(raw)}
    return inputs, fixture_descriptors


def original_module(baseline: Baseline):
    modules = baseline.load_modules({
        "evidence.geometry": "scripts/evidence/geometry.py",
        "ellipsoidal_area": "scripts/ellipsoidal_area.py",
    })
    package = types.ModuleType("evidence")
    package.__path__ = []
    sys.modules["evidence"] = package
    sys.modules["evidence.geometry"] = modules["evidence.geometry"]
    return modules["evidence.geometry"]


def run_pinned_original(baseline: Baseline, inputs: dict[str, bytes], geometry_module) -> tuple[dict, bytes, str, str]:
    source = baseline.pinned_bytes(OLD_MEASUREMENT)
    encoded_output = {}
    expected_input_paths = set(INPUT_PATHS.values())
    for path, raw in inputs.items():
        # All source bytes are already admitted through the pinned baseline or candidate fixture.
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError("Actual consumed file exceeds 32 MiB")

    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes
    original_write_text = Path.write_text
    stdout, stderr = io.StringIO(), io.StringIO()

    def mapped_path(target: Path) -> str | None:
        try:
            return target.resolve(strict=False).relative_to(ROOT).as_posix()
        except (ValueError, OSError):
            return None

    by_path = {INPUT_PATHS[key]: raw for key, raw in inputs.items()}

    def read_text(target: Path, encoding=None, errors=None):
        path = mapped_path(target)
        if path in by_path:
            return by_path[path].decode(encoding or "utf-8", errors or "strict")
        return original_read_text(target, encoding=encoding, errors=errors)

    def read_bytes(target: Path):
        path = mapped_path(target)
        if path in by_path:
            return by_path[path]
        return original_read_bytes(target)

    def write_text(target: Path, data, encoding=None, errors=None, newline=None):
        path = mapped_path(target)
        if path == "data/regional-review/eastern-cape-source-restoration-435/findings/boundary-vintage-differences.json":
            if encoded_output:
                raise ValueError("Pinned legacy entry point attempted multiple output writes")
            encoded_output["legacy-result.json"] = data.encode(encoding or "utf-8", errors or "strict")
            return len(data)
        return original_write_text(target, data, encoding=encoding, errors=errors, newline=newline)

    Path.read_text = read_text
    Path.read_bytes = read_bytes
    Path.write_text = write_text
    try:
        globals_ = {"__name__": "__main__", "__file__": str(ROOT / OLD_MEASUREMENT), "__package__": None}
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(compile(source, str(ROOT / OLD_MEASUREMENT), "exec"), globals_)
    finally:
        Path.read_text = original_read_text
        Path.read_bytes = original_read_bytes
        Path.write_text = original_write_text
    if set(encoded_output) != {"legacy-result.json"} or not isinstance(globals_.get("result"), dict):
        raise ValueError("Pinned actual measurement entry point did not produce its complete expected output")
    result = json.loads(encoded_output["legacy-result.json"].decode("utf-8"), object_pairs_hook=unique_object)
    if globals_["result"] != result:
        raise ValueError("Captured private output differs from the pinned entry point's result object")
    return result, encoded_output["legacy-result.json"], stdout.getvalue(), stderr.getvalue()


def verify_old_measurements(actual: dict, expected: dict) -> dict:
    rows = actual.get("rows")
    ref_rows = expected.get("rows")
    if not isinstance(rows, list) or not isinstance(ref_rows, list) or len(rows) != 33 or len(ref_rows) != 33:
        raise ValueError("Historical measurement comparison must contain all 33 rows")
    def index(source, name):
        ids = [x.get("municipality_code") for x in source]
        if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate/missing municipality_code in {name}")
        return {x["municipality_code"]: x for x in source}
    observed, reference = index(rows, "fresh run"), index(ref_rows, "retained result")
    if set(observed) != set(reference):
        raise ValueError("Fresh measurement result does not join the complete retained roster")
    for code in sorted(reference):
        for field in MEASURE_FIELDS:
            if observed[code].get(field) != reference[code].get(field):
                raise ValueError(f"Recomputed measure differs from retained baseline: {code} {field}")
    return {"rows_joined": len(observed), "numeric_fields_compared": len(observed) * len(MEASURE_FIELDS),
            "all_numeric_fields_exactly_equal": True}


def load_context(lock_path: str = SOURCE_LOCK_PATH):
    lock, lock_raw = load_issue_and_lock(lock_path)
    baseline = create_baseline(lock)
    inputs, fixture_descriptors = authenticated_inputs(baseline)
    validation = validate_inputs(inputs)
    original_result_raw = baseline.pinned_bytes(OLD_RESULT)
    original_result = parse_json(original_result_raw, OLD_RESULT)
    return lock, lock_raw, baseline, inputs, validation, original_result


def module_override_bytes(baseline: Baseline, fixture_vintage: str | None, helper_name: str | None):
    if helper_name is None:
        return None
    if not fixture_vintage:
        raise ValueError("Helper override requires a published fixture vintage")
    raw, path = read_fixture(fixture_vintage, helper_name)
    baseline.admit("candidate-helper-fixture:" + path, len(raw))
    expected = CURRENT_HELPER_PINS["scripts/evidence/geometry.py"]
    if sha(raw) != expected:
        raise ValueError("Actually supplied geometry helper bytes differ from immutable project-code pin")
    return raw


def run_once(vintage: str, *, fixture_vintage: str | None = None, geometry_name: str | None = None,
             lock_name: str | None = None, helper_name: str | None = None) -> dict:
    lock_path = SOURCE_LOCK_PATH
    if lock_name:
        if not fixture_vintage:
            raise ValueError("Source-lock override requires a published fixture vintage")
        lock_bytes, lock_path = read_fixture(fixture_vintage, lock_name)
        # The exact issue/body binding is checked before constructing Baseline or reserving output.
        load_issue_and_lock(lock_path)
        if sha(lock_bytes) != SOURCE_LOCK_SHA256:
            raise ValueError("Source-lock substitution rejected against the immutable issue contract")

    lock, lock_raw = load_issue_and_lock(lock_path)
    baseline = create_baseline(lock)
    inputs, fixture_descriptors = authenticated_inputs(baseline)
    if geometry_name:
        if not fixture_vintage:
            raise ValueError("Geometry fixture requires a published fixture vintage")
        raw, path = read_fixture(fixture_vintage, geometry_name)
        baseline.admit("candidate-fixture:" + path, len(raw))
        inputs["geometry_2021"] = raw
        fixture_descriptors[path] = {"bytes": len(raw), "sha256": sha(raw)}
    # Inspect optional altered helper bytes before output admission; normal execution uses load_modules.
    module_override_bytes(baseline, fixture_vintage, helper_name)
    validation = validate_inputs(inputs)

    # Admit the entire fresh output set before shapely/GEOS measurements and old-main execution.
    vintage_writer = NewVintage(baseline, OWNED, vintage, OUTPUT_NAMES)
    geometry_module = original_module(baseline)
    legacy, legacy_bytes, stdout, stderr = run_pinned_original(baseline, inputs, geometry_module)
    reference = parse_json(baseline.pinned_bytes(OLD_RESULT), OLD_RESULT)
    measured = verify_old_measurements(legacy, reference)
    attr21 = validation["attributes_2021"]
    changed_rows = []
    corrected = copy.deepcopy(legacy)
    for row in corrected["rows"]:
        code = row.get("municipality_code")
        if code not in attr21:
            raise ValueError("Measurement row has a fabricated/unjoined municipality code")
        raw_district = row.get("district_2021")
        if raw_district is not None:
            raise ValueError("Expected to reproduce the disclosed null-district defect in all legacy rows")
        row["district_2021"] = attr21[code]["DISTRICT"]
        row["district_name_2021"] = attr21[code]["DISTRICT_N"]
        changed_rows.append(code)
    if set(changed_rows) != set(validation["codes"]) or len(changed_rows) != 33:
        raise ValueError("Corrected district output does not cover the complete unique 33-code roster")
    corrected["inputs"] = [
        {"path": path, "bytes": len(inputs[key]), "sha256": sha(inputs[key]), "hash_kind": "file-bytes"}
        for key, path in INPUT_PATHS.items()
    ]
    corrected["erratum"] = {
        "issue": 1371,
        "corrected_fields": {"district_2021": "DISTRICT", "district_name_2021": "DISTRICT_N"},
        "source_attribute_roster": INPUT_PATHS["attributes_2021"],
        "original_complete_measurements_unchanged": True,
        "geography_or_legal_approval": False,
    }
    execution = {
        "method_id": "eastern-cape-measurement-integrity",
        "kind": "measurement",
        "outcome": "passed",
        "issue": 1371,
        "source_lock_sha256": sha(lock_raw),
        "baseline_commit": lock["baseline_commit"],
        "legacy_measurement_program_sha256": next(x["sha256"] for x in lock["files"] if x["path"] == OLD_MEASUREMENT),
        "executed_project_code": [x for x in lock["current_project_code"]],
        "producer_code_sha256": sha(Path(__file__).read_bytes()),
        "runtime": {"python": sys.version.split()[0], "shapely": importlib.metadata.version("shapely"),
                    "pyproj": importlib.metadata.version("pyproj")},
        "input_descriptors": [{"path": path, "bytes": len(inputs[key]), "sha256": sha(inputs[key])}
                              for key, path in INPUT_PATHS.items()],
        "complete_input_code_bytes": sum(baseline.consumed.values()),
        "phase_limit_bytes": baseline.max_phase_bytes,
        "source_validation": validation["counts"],
        "historical_measurement_reference": OLD_RESULT,
        "historical_numeric_comparison": measured,
        "legacy_stdout": stdout,
        "legacy_stderr": stderr,
        "district_2021_legacy_null_rows": 33,
        "district_values_corrected": 33,
        "private_output_transport": "Pinned original write_text call captured its exact bytes; the complete result set was admitted and published to a new owned vintage with publication.json last.",
        "geographic_approval": "unapproved",
    }
    records = vintage_writer.publish({
        "legacy-result.json": legacy,
        "result.json": corrected,
        "execution.json": execution,
    })
    return {"vintage": vintage, "records": records, "validation": validation["counts"],
            "result": corrected, "execution": execution}


def read_publication(vintage: str) -> tuple[dict, dict[str, bytes]]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", vintage):
        raise ValueError("Unsafe vintage name")
    root = ROOT / OWNED / "vintages" / vintage
    for ancestor in (root, *root.parents):
        if ancestor == ROOT.parent:
            break
        if ancestor.is_symlink():
            raise ValueError("Symlink in published vintage")
    publication = parse_json((root / "publication.json").read_bytes(), "publication.json")
    if publication.get("version") != 1 or publication.get("status") != "complete":
        raise ValueError("Vintage lacks a complete publication receipt")
    descriptors = publication.get("outputs")
    if not isinstance(descriptors, list) or not descriptors:
        raise ValueError("Vintage receipt has no output closure")
    out = {}
    for descriptor in descriptors:
        path = descriptor.get("path")
        if not isinstance(path, str) or not path.startswith(f"{OWNED}vintages/{vintage}/"):
            raise ValueError("Published output escaped owned vintage")
        raw = read_repo(path)
        if len(raw) != descriptor.get("bytes") or sha(raw) != descriptor.get("sha256"):
            raise ValueError("Published output disagrees with completion receipt")
        out[Path(path).name] = raw
    return publication, out


def read_fixture(vintage: str, filename: str) -> tuple[bytes, str]:
    if filename not in FIXTURE_NAMES or filename == "fixtures.json":
        raise ValueError("Unknown fixture name")
    _, payloads = read_publication(vintage)
    raw = payloads.get(filename)
    if raw is None:
        raise ValueError("Fixture is absent from the published fixture closure")
    return raw, f"{OWNED}vintages/{vintage}/{filename}"


def build_fixtures(vintage: str) -> dict:
    lock, lock_raw, baseline, inputs, validation, _ = load_context()
    geometry = parse_json(inputs["geometry_2021"], INPUT_PATHS["geometry_2021"])
    original_features = geometry["features"]
    duplicate = copy.deepcopy(geometry)
    duplicate["features"].append(copy.deepcopy(duplicate["features"][0]))
    missing = copy.deepcopy(geometry)
    missing["features"].pop(0)
    swapped = copy.deepcopy(geometry)
    by_code = {x["properties"]["CAT_B"]: x for x in swapped["features"]}
    first, second = "EC135", "EC138"
    by_code[first]["properties"]["CAT_B"], by_code[second]["properties"]["CAT_B"] = second, first
    ambiguous = copy.deepcopy(geometry)
    ambig_map = {x["properties"]["CAT_B"]: x for x in ambiguous["features"]}
    ambig_map[first]["properties"]["MUNICNAME"] = ambig_map[second]["properties"]["MUNICNAME"]
    helper = baseline.pinned_bytes("scripts/evidence/geometry.py")
    altered_helper = helper.replace(b"VERSION = 'worldatlas-evidence-geometry-v1'", b"VERSION = 'altered-worldatlas-evidence-geometry-v1'", 1)
    if altered_helper == helper:
        raise ValueError("Could not construct the intended full helper-drift fixture")
    source_lock = json.loads(lock_raw)
    source_lock["complete_pinned_input_and_code_bytes"] += 1
    lock_fixture = (json.dumps(source_lock, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
    items = {
        "duplicate-geometry-2021.geojson": (json.dumps(duplicate, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
        "missing-geometry-2021.geojson": (json.dumps(missing, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
        "swapped-code-geometry-2021.geojson": (json.dumps(swapped, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
        "ambiguous-name-geometry-2021.geojson": (json.dumps(ambiguous, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
        "geometry-helper-altered.py": altered_helper,
        "source-lock-substitution.json": lock_fixture,
    }
    baseline.admit("generated-fixture-source:" + INPUT_PATHS["geometry_2021"], len(inputs["geometry_2021"]))
    writer = NewVintage(baseline, OWNED, vintage, FIXTURE_NAMES)
    fixture_rows = []
    for name, raw in items.items():
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError("Complete altered source exceeds per-file limit")
        fixture_rows.append({"path": f"{OWNED}vintages/{vintage}/{name}", "bytes": len(raw), "sha256": sha(raw)})
    report = {
        "method_id": "eastern-cape-integrity-fixture-construction", "kind": "source", "outcome": "passed",
        "issue": 1371, "source_path": INPUT_PATHS["geometry_2021"],
        "source_sha256": sha(inputs["geometry_2021"]), "source_feature_count": len(original_features),
        "source_code_count": len(validation["codes"]), "transformations": {
            "duplicate-geometry-2021.geojson": "Append a complete duplicate of the first original feature (34 rows).",
            "missing-geometry-2021.geojson": "Remove the first original feature (32 rows).",
            "swapped-code-geometry-2021.geojson": "Swap CAT_B values EC135 and EC138 while retaining full names and geometries.",
            "ambiguous-name-geometry-2021.geojson": "Change EC135 MUNICNAME to the distinct EC138 source name while retaining CAT_B and geometry.",
            "geometry-helper-altered.py": "Change the version literal in the complete pinned geometry helper; helper SHA remains bound to the immutable project pin.",
            "source-lock-substitution.json": "Alter the phase-byte pin while leaving the captured issue body unchanged.",
        },
        "fixtures": fixture_rows,
        "complete_fixture_raw_bytes": sum(len(x) for x in items.values()),
        "baseline_plus_fixtures_bytes": sum(baseline.consumed.values()) + sum(len(x) for x in items.values()),
        "limit_bytes": baseline.max_phase_bytes,
        "geographic_approval": "unapproved",
    }
    values = dict(items)
    values["fixtures.json"] = (json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
    records = writer.publish_bytes(values)
    return {"vintage": vintage, "records": records, "report": report}


def run_control_child(vintage: str, fixture_vintage: str, *, geometry: str | None = None,
                      helper: str | None = None, lock: str | None = None) -> dict:
    target = ROOT / OWNED / "vintages" / vintage
    before_exists = target.exists() or target.is_symlink()
    command = [sys.executable, str(Path(__file__).resolve()), "run", "--vintage", vintage,
               "--fixture-vintage", fixture_vintage]
    if geometry:
        command += ["--geometry-fixture", geometry]
    if helper:
        command += ["--geometry-helper-fixture", helper]
    if lock:
        command += ["--source-lock-fixture", lock]
    proc = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    after_exists = target.exists() or target.is_symlink()
    return {"command": [Path(__file__).relative_to(ROOT).as_posix(), *command[2:]],
            "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
            "output_vintage_existed_before": before_exists, "output_vintage_exists_after": after_exists,
            "output_target_unchanged": before_exists == after_exists,
            "rejected_before_output_publication": proc.returncode != 0 and not before_exists and not after_exists}


def run_controls(fixture_vintage: str, run_one: str, attempt: str, report_vintage: str) -> dict:
    lock, _, baseline, _, _, _ = load_context()
    # Admit the report destination before any subprocess controls are run.
    report_writer = NewVintage(baseline, OWNED, report_vintage, [
        "identity-negative-control.json", "execution-negative-control.json", "output-negative-control.json",
    ])
    _, first_payload = read_publication(run_one)
    before_run = {name: sha(raw) for name, raw in first_payload.items()}
    cases = [
        ("duplicate_geometry", "duplicate-geometry-2021.geojson", None, None, "duplicate raw municipality codes"),
        ("missing_geometry", "missing-geometry-2021.geojson", None, None, "expected the complete 33-feature MDB roster"),
        ("swapped_geometry_codes", "swapped-code-geometry-2021.geojson", None, None, "code/name/source-field mismatch"),
        ("ambiguous_geometry_name", "ambiguous-name-geometry-2021.geojson", None, None, "code/name/source-field mismatch"),
        ("project_helper_drift", None, "geometry-helper-altered.py", None, "Actually supplied geometry helper bytes differ"),
        ("source_lock_substitution", None, None, "source-lock-substitution.json", "Source-lock substitution does not match"),
    ]
    outcomes = []
    for name, geometry, helper, lock_name, expected_error in cases:
        child_vintage = f"{attempt}-{name.replace('_', '-')[:38]}"
        observed = run_control_child(child_vintage, fixture_vintage, geometry=geometry, helper=helper, lock=lock_name)
        observed["control_id"] = name
        observed["expected_rejection"] = True
        observed["expected_error_fragment"] = expected_error
        observed["passed"] = (observed["rejected_before_output_publication"] and expected_error in observed["stderr"])
        outcomes.append(observed)
    # Reuse a complete successful output directory as the collision sentinel. No bytes are changed.
    existing = run_control_child(run_one, fixture_vintage)
    after_publication, after_payload = read_publication(run_one)
    after_run = {name: sha(raw) for name, raw in after_payload.items()}
    collision = {
        "control_id": "existing_successful_output_vintage",
        "method_id": "safe-output-admission",
        "kind": "negative-control",
        "outcome": "passed" if existing["exit_code"] != 0 and existing["output_target_unchanged"] and before_run == after_run and "Evidence already exists" in existing["stderr"] else "failed",
        "entrypoint": existing,
        "outputs_unchanged": before_run == after_run,
        "published_receipt_still_valid": after_publication.get("status") == "complete",
        "before_hashes": before_run,
        "after_hashes": after_run,
    }
    negative = {
        "method_id": "eastern-cape-integrity-controls", "kind": "negative-control",
        "outcome": "passed" if all(x["passed"] for x in outcomes) else "failed",
        "issue": 1371, "cases": outcomes,
    }
    execution = {
        "method_id": "eastern-cape-execution-integrity", "kind": "negative-control",
        "outcome": "passed" if all(x["passed"] for x in outcomes) else "failed",
        "issue": 1371,
        "cases": [x for x in outcomes if x["control_id"] in ("project_helper_drift", "source_lock_substitution")],
    }
    records = report_writer.publish({
        "identity-negative-control.json": negative,
        "execution-negative-control.json": execution,
        "output-negative-control.json": collision,
    })
    return {"records": records, "identity": negative, "execution": execution, "output": collision}


def compare_pair(first: str, second: str, controls_vintage: str, report_vintage: str) -> dict:
    lock, _, baseline, _, validation, _ = load_context()
    # Reserve complete pair report before its file reads and comparisons.
    writer = NewVintage(baseline, OWNED, report_vintage, ["reproducibility.json", "positive-control.json", "negative-control.json"])
    first_pub, first_files = read_publication(first)
    second_pub, second_files = read_publication(second)
    control_pub, control_files = read_publication(controls_vintage)
    one = parse_json(first_files["result.json"], f"{first}/result.json")
    two = parse_json(second_files["result.json"], f"{second}/result.json")
    one_exec = parse_json(first_files["execution.json"], f"{first}/execution.json")
    two_exec = parse_json(second_files["execution.json"], f"{second}/execution.json")
    first_hash, second_hash = sha(first_files["result.json"]), sha(second_files["result.json"])
    legacy_hashes_equal = sha(first_files["legacy-result.json"]) == sha(second_files["legacy-result.json"])
    if first_hash != second_hash or not legacy_hashes_equal:
        raise ValueError("Two fresh actual entry-point runs do not reproduce byte-for-byte")
    if one_exec.get("producer_code_sha256") != two_exec.get("producer_code_sha256") or one_exec.get("runtime") != two_exec.get("runtime"):
        raise ValueError("Reproduction pair used different project code or runtime")
    corrected_rows = one.get("rows", [])
    districts = validation["attributes_2021"]
    if len(corrected_rows) != 33:
        raise ValueError("Positive control lacks the complete 33-row result")
    for row in corrected_rows:
        code = row["municipality_code"]
        if row.get("district_2021") != districts[code]["DISTRICT"] or row.get("district_name_2021") != districts[code]["DISTRICT_N"]:
            raise ValueError(f"Corrected district record does not match source attributes: {code}")
    pair = {
        "method_id": "eastern-cape-measurement-integrity", "kind": "reproducibility", "outcome": "passed",
        "issue": 1371, "run_one": first, "run_two": second,
        "run_one_sha256": first_hash, "run_two_sha256": second_hash,
        "legacy_run_one_sha256": sha(first_files["legacy-result.json"]),
        "legacy_run_two_sha256": sha(second_files["legacy-result.json"]),
        "all_33_source_district_codes_and_names_match": True,
        "features_2021": 33, "nonempty_district_code_rows": 33,
        "original_numeric_measure_fields_exactly_equal": 33 * len(MEASURE_FIELDS),
        "geographic_approval": "unapproved",
    }
    positive = {
        "method_id": "eastern-cape-measurement-integrity", "kind": "positive-control", "outcome": "passed",
        "issue": 1371, "complete_2021_and_2026_feature_joins": validation["counts"],
        "source_district_field_2021": "DISTRICT", "source_district_name_field_2021": "DISTRICT_N",
        "corrected_rows_joined": len(corrected_rows), "original_numeric_measure_fields_exactly_equal": 33 * len(MEASURE_FIELDS),
        "reference_result_path": OLD_RESULT, "reference_result_is_legacy_baseline_not_current_geographic_approval": True,
    }
    identity_control = parse_json(control_files["identity-negative-control.json"], f"{controls_vintage}/identity-negative-control.json")
    execution_control = parse_json(control_files["execution-negative-control.json"], f"{controls_vintage}/execution-negative-control.json")
    output_control = parse_json(control_files["output-negative-control.json"], f"{controls_vintage}/output-negative-control.json")
    if any(item.get("outcome") != "passed" for item in (identity_control, execution_control, output_control)):
        raise ValueError("Cannot certify negative control while a documented control is failed")
    negative = {
        "method_id": "eastern-cape-measurement-integrity", "kind": "negative-control", "outcome": "passed",
        "issue": 1371,
        "duplicate_missing_swapped_and_ambiguous_fixtures_rejected": all(item.get("passed") for item in identity_control["cases"]),
        "helper_and_source_lock_substitution_rejected": all(item.get("passed") for item in execution_control["cases"]),
        "existing_successful_output_unchanged": output_control["outputs_unchanged"] and output_control["published_receipt_still_valid"],
        "identity_cases": len(identity_control["cases"]),
        "execution_cases": len(execution_control["cases"]),
        "control_report_vintage": controls_vintage,
        "geographic_approval": "unapproved",
    }
    records = writer.publish({"reproducibility.json": pair, "positive-control.json": positive, "negative-control.json": negative})
    return {"records": records, "pair": pair, "positive": positive, "negative": negative}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    lock = sub.add_parser("run")
    lock.add_argument("--vintage", required=True)
    lock.add_argument("--fixture-vintage")
    lock.add_argument("--geometry-fixture")
    lock.add_argument("--geometry-helper-fixture")
    lock.add_argument("--source-lock-fixture")
    fixture = sub.add_parser("fixtures")
    fixture.add_argument("--vintage", required=True)
    control = sub.add_parser("controls")
    control.add_argument("--fixture-vintage", required=True)
    control.add_argument("--run-one", required=True)
    control.add_argument("--attempt", required=True)
    control.add_argument("--report-vintage", required=True)
    pair = sub.add_parser("pair")
    pair.add_argument("--run-one", required=True)
    pair.add_argument("--run-two", required=True)
    pair.add_argument("--controls-vintage", required=True)
    pair.add_argument("--report-vintage", required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            if args.source_lock_fixture:
                result = run_once(args.vintage, fixture_vintage=args.fixture_vintage, lock_name=args.source_lock_fixture)
            else:
                result = run_once(args.vintage, fixture_vintage=args.fixture_vintage,
                                  geometry_name=args.geometry_fixture, helper_name=args.geometry_helper_fixture)
        elif args.command == "fixtures":
            result = build_fixtures(args.vintage)
        elif args.command == "controls":
            result = run_controls(args.fixture_vintage, args.run_one, args.attempt, args.report_vintage)
        else:
            result = compare_pair(args.run_one, args.run_two, args.controls_vintage, args.report_vintage)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
