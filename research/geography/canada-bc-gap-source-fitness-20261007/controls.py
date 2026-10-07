#!/usr/bin/env python3
"""Directed completeness, lineage and uncertainty controls for the #1362 packet."""
import argparse
import collections
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                        allow_nan=False) + "\n").encode("utf-8")


def require_roster(actual, expected):
    if len(actual) != len(expected) or len(set(actual)) != len(actual) or actual != expected:
        raise ValueError("complete ordered roster does not match")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=pathlib.Path, required=True)
    p.add_argument("--out", type=pathlib.Path, required=True)
    args = p.parse_args()
    base = args.packet
    if args.out.exists():
        raise SystemExit(f"Refusing to replace control output {args.out}")
    rows = [json.loads(line) for line in (base / "component-review.jsonl").read_text().splitlines()]
    summary = json.loads((base / "scope-summary.json").read_bytes())
    receipt = json.loads((base / "run-receipt.json").read_bytes())
    ids = [r["component_id"] for r in rows]
    expected = summary["complete_component_ids"]
    if len(rows) != 43:
        raise ValueError("production reader failed complete component count")
    require_roster(ids, expected)

    outcomes = []
    def control(name, operation, expected_result):
        try:
            actual = operation()
            passed = actual == expected_result
        except Exception as exc:
            actual = f"rejected:{type(exc).__name__}"
            passed = expected_result == "rejected"
        if not passed:
            raise ValueError(f"Control {name} failed: {actual!r}")
        outcomes.append({"id": name, "expected": expected_result, "actual": actual, "passed": True})

    control("positive-exact-43-member-roster", lambda: (require_roster(ids, expected) or len(ids)), 43)
    control("negative-omitted-member", lambda: (require_roster(ids[:-1], expected) or "accepted"), "rejected")
    control("negative-duplicate-member", lambda: (require_roster(ids[:-1] + [ids[-2]], expected) or "accepted"), "rejected")
    control("negative-foreign-member", lambda: (require_roster(ids[:-1] + ["physical-component:" + "f" * 64], expected) or "accepted"), "rejected")

    query_counts = [r["original_physical_record"]["query_relation_count"] for r in rows]
    query_total = sum(query_counts)
    control("positive-complete-original-query-closure", lambda: query_total, summary["complete_query_relation_count"])
    if query_total != 146 or any(not r["original_physical_record"]["row_sha256"] for r in rows):
        raise ValueError("Original query relation/row bindings are incomplete")

    numeric = [r for r in rows if r["numeric_diagnosis"] is not None]
    classes = collections.Counter(r["numeric_diagnosis"]["conservative_class"] for r in numeric)
    expected_classes = {
        "local-construction-contradiction-demonstrated": 9,
        "retained-unresolved-numerical-or-context-prerequisite": 18,
        "retained-unresolved-original-replay-mismatch": 1,
    }
    control("positive-numeric-disposition-partition", lambda: dict(classes), expected_classes)
    control("positive-full-contact-and-active-geographic-subject", lambda: (receipt["active_geographic_subject_ids"], summary["complete_contact_ids"]), (["atlas:district:CAN-5917:BRC"], ["atlas:district:CAN-5917:BRC"]))

    contact = json.loads((base / "source-assessment.json").read_bytes())["contact"]
    stats = json.loads((base / "source-assessment.json").read_bytes())["statistics_canada_2021_census_division"]
    control("positive-retained-full-contact-source-members", lambda: contact["source_member_count"], 22)
    control("negative-authoritative-boundary-equivalence", lambda: stats["current_contact_topologically_equal"], False)
    physical = json.loads((base / "source-assessment.json").read_bytes())["gshhg_physical_screen"]
    control("positive-retained-physical-unknowns", lambda: physical["family_routing_physical_status_counts"], {"mixed-source-support": 15, "unknown": 28})

    # Bind the actual complete source-family row, then require a mutation to fail.
    source_index = json.loads((base / "source-input-pins.json").read_bytes())
    route_hash = source_index["family_row_sha256"]
    family_row = json.loads((base / "family-row.json").read_bytes())
    family_digest = hashlib.sha256(canonical(family_row)).hexdigest()
    control("positive-authenticated-complete-family-row", lambda: family_digest, route_hash)
    mutated_family = dict(family_row)
    mutated_family["source_fitness"] = "tampered"
    def verify_family_binding():
        if hashlib.sha256(canonical(mutated_family)).hexdigest() != route_hash:
            raise ValueError("complete family row differs from pinned SHA-256")
        return "accepted"
    control("negative-family-row-hash-mutation", verify_family_binding, "rejected")

    # The documented producer must reject an occupied destination before touching it.
    repo = base.parents[1]
    producer = repo / "research/geography/canada-bc-gap-source-fitness-20261007/build_packet.py"
    def occupied_destination():
        with tempfile.TemporaryDirectory(prefix="source-fitness-control-", dir=base.parent) as scratch:
            destination = pathlib.Path(scratch) / "occupied"
            destination.mkdir()
            sentinel = destination / "preserve.txt"
            sentinel.write_text("original bytes\n")
            result = subprocess.run([sys.executable, str(producer), "--repo", str(repo),
                                     "--out", str(destination)], capture_output=True, text=True)
            if result.returncode == 0 or sentinel.read_text() != "original bytes\n":
                raise ValueError("producer failed to reject/preserve occupied destination")
            return "rejected-and-preserved"
    control("negative-existing-output-preserved", occupied_destination, "rejected-and-preserved")
    payload = {"version": 1, "result": "PASS", "directed_controls": outcomes,
               "counts": {"controls": len(outcomes), "passed": sum(x["passed"] for x in outcomes),
                          "components": len(rows), "numeric": len(numeric), "query_relations": query_total},
               "limits": ["These controls verify identity, completeness, retained provenance and conservative disposition; they do not establish legal boundaries or physical land/water truth."]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical(payload))
    print(json.dumps(payload["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
