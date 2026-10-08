#!/usr/bin/env python3
"""Independently join successor rows to the preserved legacy full-product baseline."""
import hashlib
import json
from pathlib import Path


PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
BASELINE = REPO / "research/geography/gap-source-namibia-angola-20261006/full-product-comparison.json"


def read(rel):
    return json.loads((REPO / rel).read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    baseline_raw = BASELINE.read_bytes()
    baseline = json.loads(baseline_raw)
    historical_pairs = {(row["component_id"], row["subject_id"]): row
                        for row in baseline["component_by_contact_subject"]}
    source_rel = "research/geography/gap-source-namibia-angola-reproduction-erratum/vintages/successor-source-final-one-20261008/source-geometry-successor.json"
    full_rel = "research/geography/gap-source-namibia-angola-reproduction-erratum/vintages/successor-full-final-one-20261008/full-product-successor.json"
    source = read(source_rel)
    full = read(full_rel)
    source_rows = {(row["candidate_id"], row["contact_subject_id"]): row for row in source["matrix"]}
    if len(historical_pairs) != 210 or len(source_rows) != 210 or set(source_rows) != set(historical_pairs):
        raise SystemExit("Source successor identities do not match the complete 210-row historical baseline")
    for key, row in source_rows.items():
        old = historical_pairs[key]
        expected = (old["intersects"], old["intersection_type"], old["intersection_area_degrees_squared"])
        actual = (row["intersects"], row["intersection_type"], row["intersection_area_square_degrees"])
        if actual != expected:
            raise SystemExit("Consumed-source row differs from preserved baseline: " + repr(key))

    historical_full = {}
    for candidate in baseline["full_product_component_intersections"]:
        for country, data in candidate["per_country"].items():
            for hit in data["hits"]:
                historical_full[(candidate["component_id"], country, hit["source_id"].split(":")[-1])] = hit
    full_rows = {(row["candidate_id"], row["country"], row["full_product_shape_id"]): row
                 for row in full["matrix"]}
    if len(full_rows) != 5670:
        raise SystemExit("Full-product successor does not contain exactly 5,670 unique complete pairs")
    for key, row in full_rows.items():
        old = historical_full.get(key)
        if old is None:
            if row["intersects"] or row["intersection_area_square_degrees"] != 0:
                raise SystemExit("Unexpected full-product hit absent from the preserved baseline: " + repr(key))
        elif ((not row["intersects"]) or row["intersection_type"] != old["intersection_type"]
              or row["intersection_area_square_degrees"] != old["intersection_area_degrees_squared"]):
            raise SystemExit("Full-product successor row differs from preserved baseline: " + repr(key))
    if sum(row["intersects"] for row in full["matrix"]) != len(historical_full):
        raise SystemExit("Complete full-product hit count differs from the preserved baseline")
    result = {"issue": 1437, "verified_against": "preserved historical full-product comparison",
              "baseline_path": str(BASELINE.relative_to(REPO)), "baseline_bytes": len(baseline_raw),
              "baseline_sha256": sha(baseline_raw), "source_successor_path": source_rel,
              "source_successor_sha256": sha((REPO / source_rel).read_bytes()),
              "source_rows_checked": len(source_rows), "source_rows_equal": len(source_rows),
              "full_product_successor_path": full_rel,
              "full_product_successor_sha256": sha((REPO / full_rel).read_bytes()),
              "full_product_rows_checked": len(full_rows), "full_product_rows_equal": len(full_rows),
              "full_product_positive_intersections": len(historical_full),
              "all_successor_values_match_preserved_baseline": True}
    output = PACKET / "vintages/successor-baseline-final-20261008"
    output.mkdir(exist_ok=False)
    target = output / "independent-baseline-comparison.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(target.relative_to(REPO)), "sha256": sha(target.read_bytes()),
                      "source_rows": len(source_rows), "full_rows": len(full_rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
