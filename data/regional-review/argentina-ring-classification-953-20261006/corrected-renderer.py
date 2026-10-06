#!/usr/bin/env python3
"""Re-render Argentina ring flags from the pinned source coordinates.

Reads the immutable #953 comparison table and 214-feature 2020 geoBoundaries
extract, verifies exact subject and native-ID joins, then writes outputs only
to the caller's path. No source packet or Atlas geography file is modified.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
from io import StringIO
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify_hole_count(raw):
    """Accept a canonical, non-negative base-10 integer only."""
    if not isinstance(raw, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)", raw):
        raise ValueError(f"invalid interior-ring count: {raw!r}")
    return "yes" if int(raw) > 0 else "no"


def count_interior_rings(geometry):
    kind, coordinates = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        polygons = [coordinates]
    elif kind == "MultiPolygon":
        polygons = coordinates
    else:
        raise ValueError(f"unsupported source geometry type {kind!r}")
    if not polygons:
        raise ValueError("source geometry has no polygons")
    count = 0
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("source polygon has no exterior ring")
        count += len(polygon) - 1
    return count


def build_outputs(scope_path, source_path, table_path, baseline_renderer_path):
    scope = json.loads(Path(scope_path).read_text(encoding="utf-8"))
    ids = scope["subject_ids"]
    if len(ids) != 214 or len(set(ids)) != 214:
        raise ValueError("issue scope must contain exactly 214 unique IDs")

    source = json.loads(Path(source_path).read_text(encoding="utf-8"))
    features = source.get("features", [])
    by_shape = {}
    for feature in features:
        props = feature.get("properties", {})
        native_id = props.get("shapeID")
        if not isinstance(native_id, str) or native_id in by_shape:
            raise ValueError("source shapeID is absent or duplicated")
        by_shape[native_id] = feature
    shape_ids = {identity.rsplit(":", 1)[1] for identity in ids}
    if len(features) != 214 or set(by_shape) != shape_ids:
        raise ValueError("retained source roster differs from exact issue subjects")

    measured = {}
    for identity in ids:
        native_id = identity.rsplit(":", 1)[1]
        feature = by_shape[native_id]
        props = feature.get("properties", {})
        if props.get("shapeType") != "ADM2":
            raise ValueError(f"unexpected source level for {identity}")
        count = count_interior_rings(feature.get("geometry") or {})
        measured[identity] = {
            "source_shape_id": native_id,
            "source_name": props.get("shapeName"),
            "interior_ring_count": count,
            "has_interior_rings": classify_hole_count(str(count)),
        }

    with Path(table_path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields or "has_interior_rings" not in fields or not rows:
        raise ValueError("pinned comparison table schema is invalid")
    if rows[0].get("record_type") != "summary" or rows[0].get("record_count") != "214":
        raise ValueError("pinned comparison summary must declare 214 detail rows")
    detail = rows[1:]
    by_atlas = {}
    for row in detail:
        identity = row.get("atlas_id")
        if row.get("record_type") != "detail" or not identity or identity in by_atlas:
            raise ValueError("pinned comparison detail IDs are absent or duplicated")
        by_atlas[identity] = row
    if len(detail) != 214 or set(by_atlas) != set(ids):
        raise ValueError("pinned comparison rows differ from exact issue subjects")

    before = {identity: dict(by_atlas[identity]) for identity in ids}
    for identity, measurement in measured.items():
        row = by_atlas[identity]
        if row.get("source_2020_shape_id") != measurement["source_shape_id"]:
            raise ValueError(f"source crosswalk mismatch for {identity}")
        row["has_interior_rings"] = measurement["has_interior_rings"]

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerow(rows[0])
    writer.writerows(detail)
    output = {"corrected-findings.csv": buffer.getvalue().encode("utf-8")}

    total = sum(value["interior_ring_count"] for value in measured.values())
    ring_ids = sorted(identity for identity, value in measured.items() if value["interior_ring_count"] > 0)
    ring_measurements = {
        "version": 1,
        "subject_ids_sha256": scope["subject_ids_sha256"],
        "measurement": "Count interior rings directly from GeoJSON Polygon/MultiPolygon coordinate arrays.",
        "subjects": [{"id": identity, **measured[identity]} for identity in sorted(measured)],
        "summary": {
            "subject_count": len(measured),
            "zero_ring_subjects": len(measured) - len(ring_ids),
            "subjects_with_rings": len(ring_ids),
            "total_rings": total,
            "ring_subject_ids": ring_ids,
        },
    }
    output["ring-measurements.json"] = (json.dumps(ring_measurements, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()

    # Re-read the serialized table and prove every field but the target flag is unchanged.
    rendered = list(csv.DictReader(StringIO(output["corrected-findings.csv"].decode("utf-8"))))
    if len(rendered) != 215 or rendered[0].get("record_type") != "summary":
        raise ValueError("rendered table row count or summary changed")
    rendered_by_id = {row["atlas_id"]: row for row in rendered[1:]}
    for identity in ids:
        if set(before[identity]) != set(rendered_by_id[identity]):
            raise ValueError("rendered detail schema changed")
        for key, value in before[identity].items():
            expected = measured[identity]["has_interior_rings"] if key == "has_interior_rings" else value
            if rendered_by_id[identity][key] != expected:
                raise ValueError(f"unexpected detail-field change for {identity}: {key}")

    report = {
        "version": 1,
        "baseline_source_sha256": sha256(source_path),
        "baseline_table_sha256": sha256(table_path),
        "baseline_renderer_sha256": sha256(baseline_renderer_path),
        "preservation": "All comparison detail fields except has_interior_rings match the pinned input row by row; source and prior packet remain read-only.",
        "changed_flag_ids": sorted(identity for identity in ids if before[identity]["has_interior_rings"] != measured[identity]["has_interior_rings"]),
        "limits": [
            "This corrects classification for the pinned 2020 source extract; it does not establish current legal boundaries or national completeness.",
            "Earlier overlay measurements remain archived and unchanged; only source-ring measurement and flag rendering are repeated here.",
            "Source metadata declares 526 ADM2 units while the restored geometry contains 525; the national discrepancy remains unresolved.",
            "The neighboring current Georef comparison layer mixes Departamento, Partido and Comuna categories and is not legal boundary adjudication.",
        ],
    }
    output["reproduction-report.json"] = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()

    positive = {
        "method_id": "ring-flag-renderer", "kind": "positive-control", "outcome": "passed",
        "control": "CSV count zero renders no; a positive ring count renders yes.",
        "zero_flag": classify_hole_count("0"), "positive_flag": classify_hole_count("5"),
    }
    output["positive-control.json"] = (json.dumps(positive, indent=2, sort_keys=True) + "\n").encode()

    malformed = ["", "-1", "+1", "1.0", "NaN", " 0", "0 ", "00"]
    for raw in malformed:
        try:
            classify_hole_count(raw)
        except ValueError:
            continue
        raise AssertionError(f"malformed count accepted: {raw!r}")
    negative = {
        "method_id": "ring-flag-renderer", "kind": "negative-control", "outcome": "passed",
        "control": "Malformed, signed, fractional, non-finite and non-canonical counts are rejected.",
        "all_cases_rejected": True,
    }
    output["negative-control.json"] = (json.dumps(negative, indent=2, sort_keys=True) + "\n").encode()

    # Execute the actual pinned production category_row against a CSV-like
    # record, preventing this control from becoming an informal reimplementation.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("pinned_categorizer", baseline_renderer_path)
    if spec is None or spec.loader is None:
        raise ValueError("could not load pinned baseline categorizer")
    baseline_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline_module)
    fixture = {
        "atlas_id": "gb:ARG:ADM2:control-zero", "atlas_name": "control",
        "atlas_parent_id": "framework:province:control", "source_2020_shape_id": "control-zero",
        "source_2020_name": "control", "source_2020_admin_level": "ADM2",
        "source_2020_geometry_type": "Polygon", "source_2020_component_count": "1",
        "source_2020_hole_count": "0", "source_2020_valid": "True", "old_area_km2_equal_area": "1",
        "current_intersecting_feature_count": "0", "top_current_georef_id": "", "top_current_name": "",
        "top_current_province": "", "top_current_category": "", "top_share_of_old_area": "0",
        "current_union_coverage_of_old": "0", "current_overlap_excess_share": "0",
        "all_current_intersections": "[]", "same_normalized_name_candidate_count": "0",
        "best_same_name_candidate_id": "", "best_same_name_candidate_province": "",
        "best_same_name_candidate_share_of_old_area": "0", "best_same_name_candidate_symmetric_difference_share": "0",
        "same_name_candidates": "[]", "over_1sqm_sliver_count": "0", "top_five_current_hits": "[]",
        "interpretation": "control",
    }
    baseline_row = baseline_module.category_row("scoped-2020-to-current-georef-overlay.csv", fixture)
    old_zero = baseline_row["has_interior_rings"]
    regression = {
        "method_id": "ring-flag-renderer", "kind": "negative-control", "outcome": "passed",
        "control": "The original expression reports yes for CSV string zero; corrected numeric parsing reports no.",
        "original_expression_for_zero": old_zero,
        "corrected_expression_for_zero": classify_hole_count("0"),
        "regression_detects_original_defect": old_zero != classify_hole_count("0"),
    }
    output["regression-control.json"] = (json.dumps(regression, indent=2, sort_keys=True) + "\n").encode()
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--baseline-renderer", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    # Run the complete scope measurement and rendering twice independently.
    run_one = build_outputs(args.scope, args.source, args.table, args.baseline_renderer)
    run_two = build_outputs(args.scope, args.source, args.table, args.baseline_renderer)
    hashes_one = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(run_one.items())}
    hashes_two = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(run_two.items())}
    if hashes_one != hashes_two:
        raise AssertionError("two corrected measurement/render runs differ")
    receipt = {
        "method_id": "ring-flag-renderer", "kind": "reproducibility", "outcome": "passed",
        "run_one_sha256": hashlib.sha256(json.dumps(hashes_one, sort_keys=True).encode()).hexdigest(),
        "run_two_sha256": hashlib.sha256(json.dumps(hashes_two, sort_keys=True).encode()).hexdigest(),
        "outputs": hashes_one, "byte_identical": True,
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in run_one.items():
        (out_dir / name).write_bytes(data)
    (out_dir / "reproducibility.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**hashes_one, "reproducibility.json": sha256(out_dir / "reproducibility.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
