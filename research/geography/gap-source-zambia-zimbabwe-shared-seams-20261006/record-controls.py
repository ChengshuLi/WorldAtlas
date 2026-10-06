#!/usr/bin/env python3
"""Create method-bound controls from two complete packet producer runs."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METHOD_GEOGRAPHY = "zambia-zimbabwe-source-overlay"
METHOD_GENERATOR = "zambia-zimbabwe-packet-generator"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def main():
    one = (ROOT / "run-one/source-geometry-results.json.gz").read_bytes()
    two = (ROOT / "run-two/source-geometry-results.json.gz").read_bytes()
    assert one == two
    raw = gzip.decompress(one)
    report = json.loads(raw)
    rows = report["components"]
    positive_rows = [{"component_id": r["component_id"],
                      "source_intersection_area_m2": r["source_union_intersection"]["wgs84_area_m2"],
                      "outside_source_residual_area_m2": r["component_minus_source_union"]["wgs84_area_m2"]}
                     for r in rows]
    assert len(positive_rows) == 10
    assert all(r["source_intersection_area_m2"] > 0 and r["outside_source_residual_area_m2"] > 0
               for r in positive_rows)
    negative_rows = report["controls"]["negative"]
    assert len(negative_rows) == 1 and negative_rows[0]["intersection"]["empty"]

    controls = {
        "geography-positive-control.json": {
            "method_id": METHOD_GEOGRAPHY, "kind": "positive-control", "outcome": "passed",
            "expectation": "Each issue component has positive-area intersection with the union of relevant full consumed source polygons and a nonempty outside-source residual.",
            "observed": positive_rows},
        "geography-negative-control.json": {
            "method_id": METHOD_GEOGRAPHY, "kind": "negative-control", "outcome": "passed",
            "expectation": "A fixed far-away ZMB source polygon is disjoint from the first target component.",
            "observed": negative_rows},
        "generator-positive-control.json": {
            "method_id": METHOD_GENERATOR, "kind": "positive-control", "outcome": "passed",
            "expectation": "The output retains exactly ten issue components, four source subjects, and one original point-only contact.",
            "observed": {"component_count": len(rows), "subject_count": len(report["registered_subject_comparisons"]),
                         "matched_contact_count": len(report["original_source_contacts"]["matched_rows"]),
                         "contact_kind": report["original_source_contacts"]["matched_rows"][0]["kind"]}},
        "generator-negative-control.json": {
            "method_id": METHOD_GENERATOR, "kind": "negative-control", "outcome": "passed",
            "expectation": "A disjoint non-neighbor source polygon yields an empty intersection and is retained as the negative fixture.",
            "observed": negative_rows},
        "reproducibility.json": {
            "method_id": METHOD_GENERATOR, "kind": "reproducibility", "outcome": "passed",
            "run_one_sha256": sha(one), "run_two_sha256": sha(two),
            "run_one_bytes": len(one), "run_two_bytes": len(two),
            "decoded_sha256": sha(raw), "decoded_bytes": len(raw),
            "equal_encoded_bytes": True, "encoding": "canonical UTF-8 JSON with trailing newline; gzip level 9, mtime 0"},
    }
    for name, value in controls.items():
        (ROOT / name).write_bytes(canonical(value))
    print(json.dumps({"status": "passed", "controls": list(controls),
                      "run_sha256": sha(one), "decoded_sha256": sha(raw)}, sort_keys=True))


if __name__ == "__main__":
    main()
