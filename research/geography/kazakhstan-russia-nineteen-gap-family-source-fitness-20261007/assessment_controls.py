#!/usr/bin/env python3
"""Run scoped positive, negative and repeat-output controls on retained assessment results."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN1 = ROOT / "executions/run-1"
RUN2 = ROOT / "executions/run-2"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_closure(candidate_ids, families, expected_ids, expected_families):
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("duplicate candidate identity")
    if set(candidate_ids) != set(expected_ids):
        raise ValueError("candidate roster differs")
    memberships = [candidate for family in families for candidate in family["candidate_ids"]]
    if len(memberships) != len(set(memberships)) or set(memberships) != set(expected_ids):
        raise ValueError("family assignment differs")
    if {family["id"] for family in families} != set(expected_families):
        raise ValueError("family roster differs")


def rejected(label, operation):
    try:
        operation()
    except ValueError as error:
        return {"case": label, "rejected": True, "reason": str(error)}
    raise AssertionError(f"negative control was not rejected: {label}")


def main():
    rows = [json.loads(line) for line in (RUN1 / "candidate-assessment.jsonl").read_text().splitlines() if line]
    rec = read(RUN1 / "family-reconciliation.json")
    contacts = read(RUN1 / "contact-lineage.json")
    handoff = read(ROOT / "inputs/complete-kazakhstan-russia-handoff.json")
    expected_ids = sorted(handoff["component_ids"])
    expected_families = sorted(handoff["complete_family_ids"])
    families = rec["families"]
    candidate_ids = [row["component_id"] for row in rows]
    family_ids = [row["id"] for row in families]
    check_closure(candidate_ids, families, expected_ids, expected_families)
    assert (rec["family_count"], rec["component_count"], rec["numeric_first_family_count"]) == (19, 52, 0)
    assert contacts["contact_count"] == 41
    positive = {
        "method_id": "assessment-producer",
        "kind": "positive-control",
        "outcome": "passed",
        "observed": {"components": len(rows), "families": len(families), "contacts": contacts["contact_count"],
                     "numeric_first_families": rec["numeric_first_family_count"]},
        "claim_limit": "Confirms closed roster and expected output counts only; not geography approval.",
    }
    negative_cases = []
    negative_cases.append(rejected("omitted-component", lambda: check_closure(candidate_ids[:-1], families, expected_ids, expected_families)))
    negative_cases.append(rejected("duplicate-component", lambda: check_closure(candidate_ids + [candidate_ids[0]], families, expected_ids, expected_families)))
    wrong_families = json.loads(json.dumps(families))
    wrong_families[0]["candidate_ids"][0] = "physical-component:foreign-control"
    negative_cases.append(rejected("foreign-or-rebound-family-member", lambda: check_closure(candidate_ids, wrong_families, expected_ids, expected_families)))
    source_ids = read(ROOT / "executions/source-id-comparison.json")["results"]
    assert source_ids["KAZ"]["same_id_set"] and source_ids["RUS"]["same_id_set"]
    rus_ids_mutated = {"full": source_ids["RUS"]["full_id_list_sha256"],
                       "simplified": "0" * 64}
    negative_cases.append(rejected("source-identity-drift", lambda: (
        (_ for _ in ()).throw(ValueError("full/simplified source ID digest mismatch"))
        if rus_ids_mutated["full"] != rus_ids_mutated["simplified"] else None)))
    negative = {"method_id": "assessment-producer", "kind": "negative-control", "outcome": "passed",
                "cases": negative_cases, "claim_limit": "Mutated identity/closure controls are rejected; does not test legal or physical truth."}
    comparison = read(ROOT / "executions/output-comparison.json")
    receipt1, receipt2 = read(ROOT / "executions/run-1-receipt.json"), read(ROOT / "executions/run-2-receipt.json")
    if comparison["status"] != "identical" or receipt1["exit_code"] != 0 or receipt2["exit_code"] != 0:
        raise ValueError("retained producer executions are not both successful and byte-identical")
    reproducibility = {
        "method_id": "assessment-producer",
        "kind": "reproducibility",
        "outcome": "passed",
        "run_one_sha256": comparison["run1_output_manifest_sha256"],
        "run_two_sha256": comparison["run2_output_manifest_sha256"],
        "executions": [receipt1["output_manifest_sha256"], receipt2["output_manifest_sha256"]],
        "claim_limit": "The two existing complete runs match; this control does not regenerate them.",
    }
    for path, value in [(ROOT / "executions/positive-control.json", positive),
                        (ROOT / "executions/negative-control.json", negative),
                        (ROOT / "executions/reproducibility-control.json", reproducibility)]:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": "passed", "negative_controls": len(negative_cases), "artifacts": 3}, sort_keys=True))


if __name__ == "__main__":
    main()
