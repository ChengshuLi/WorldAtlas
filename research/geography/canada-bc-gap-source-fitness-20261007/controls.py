#!/usr/bin/env python3
"""Directed completeness, lineage and uncertainty controls for the #1362 packet."""
import argparse
import collections
import gzip
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


QUERY_FIELDS = ("source_id", "source_level", "source_container", "periodic_offset", "status",
                "witness", "intersects", "disjoint", "candidate_covers_source",
                "source_covers_candidate", "source_record_sha256", "source_pointset_sha256",
                "container_chain_issues")


def compact_query(query):
    return {key: query[key] for key in QUERY_FIELDS if key in query}


def pinned_original_queries(repo, source_index, review_rows):
    """Re-derive query identities from the pinned original containing-file blobs."""
    commit = source_index["accepted_routing_commit"]
    expected_files = {row["path"]: row for row in source_index["complete_original_physical_row_files"]}
    member_ids = {row["component_id"] for row in review_rows}
    expected_rows = {row["component_id"]: row["original_physical_record"] for row in review_rows}
    originals = {}
    for path in sorted({record["path"] for record in expected_rows.values()}):
        pin = expected_files.get(path)
        if not pin or pin["commit"] != commit:
            raise ValueError(f"original physical input is not pinned: {path}")
        if pin["bytes"] > 32 * 1024 * 1024:
            raise ValueError(f"original physical input exceeds control byte limit: {path}")
        blob = subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"],
                                       stderr=subprocess.PIPE)
        tree = subprocess.check_output(["git", "-C", str(repo), "ls-tree", commit, "--", path],
                                       text=True).strip().split()
        if (len(blob) != pin["bytes"] or hashlib.sha256(blob).hexdigest() != pin["sha256"] or
                len(tree) < 3 or tree[0] != pin["mode"] or tree[2] != pin["oid"]):
            raise ValueError(f"pinned original physical input bytes/mode/OID differ: {path}")
        decoded = gzip.decompress(blob)
        if len(decoded) > 32 * 1024 * 1024:
            raise ValueError(f"decompressed original physical input exceeds control byte limit: {path}")
        for line in decoded.splitlines():
            if not line or not any(cid.encode("ascii") in line for cid in member_ids):
                continue
            original = json.loads(line)
            cid = original.get("component_id")
            if cid not in member_ids:
                continue
            if cid in originals:
                raise ValueError(f"duplicate pinned original physical row: {cid}")
            if (originals.get(cid) is None and
                    hashlib.sha256(canonical(original)).hexdigest() != expected_rows[cid]["row_sha256"]):
                raise ValueError(f"pinned original physical row hash differs: {cid}")
            originals[cid] = {"path": path,
                               "query_relations": [compact_query(q) for q in original.get("query_relations", [])]}
    if set(originals) != member_ids:
        raise ValueError("pinned original physical rows do not cover the complete member roster")
    return originals


def verify_query_identity(review_rows, pinned_rows):
    if len(review_rows) != 43 or {row["component_id"] for row in review_rows} != set(pinned_rows):
        raise ValueError("query identity review roster differs from pinned original rows")
    count = 0
    for row in review_rows:
        cid = row["component_id"]
        output = row["original_physical_record"]
        original = pinned_rows[cid]
        if output["path"] != original["path"] or output["query_relations"] != original["query_relations"]:
            raise ValueError(f"query relationship identity differs from pinned original row: {cid}")
        if output["query_relation_count"] != len(original["query_relations"]):
            raise ValueError(f"query relationship count differs from pinned original row: {cid}")
        count += len(original["query_relations"])
    return count


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

    source_index = json.loads((base / "source-input-pins.json").read_bytes())
    repo = base.resolve().parents[4]
    pinned_queries = pinned_original_queries(repo, source_index, rows)
    query_total = verify_query_identity(rows, pinned_queries)
    control("positive-pinned-original-query-identities", lambda: query_total,
            summary["complete_query_relation_count"])
    mutated_queries = json.loads(json.dumps(rows))
    first_query = next(row for row in mutated_queries
                       if row["original_physical_record"]["query_relations"])
    first_query["original_physical_record"]["query_relations"][0]["source_id"] += 1
    control("negative-same-count-query-identity-mutation",
            lambda: verify_query_identity(mutated_queries, pinned_queries), "rejected")

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
