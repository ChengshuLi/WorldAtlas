#!/usr/bin/env python3
"""Authenticate retained #1334 products and publish bounded actual control receipts."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
ORIGINAL = "research/geography/kazakhstan-russia-nineteen-gap-family-source-fitness-20261007"
OWNED = "research/geography/kazakhstan-russia-control-integrity-1334-20261008/"
EXPECTED_OUTPUTS = {
    "candidate-assessment.jsonl",
    "contact-lineage.json",
    "family-reconciliation.json",
    "source-products.json",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_json(raw: bytes, label: str):
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON in {label}") from exc


def exact_unique(values, expected, label):
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError(f"empty or non-string identity in {label}")
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate identity in {label}")
    if set(values) != set(expected):
        raise ValueError(f"identity roster differs in {label}")


def check_products(manifest, products):
    descriptors = manifest.get("outputs")
    if not isinstance(descriptors, list) or len(descriptors) != len(EXPECTED_OUTPUTS):
        raise ValueError("incomplete output manifest")
    names = [row.get("path") for row in descriptors]
    exact_unique(names, EXPECTED_OUTPUTS, "output manifest")
    if set(products) != EXPECTED_OUTPUTS:
        raise ValueError("actual product inventory is incomplete or unexpected")
    for row in descriptors:
        raw = products[row["path"]]
        if not isinstance(raw, bytes) or len(raw) != row.get("bytes") or sha(raw) != row.get("sha256"):
            raise ValueError("actual output bytes differ from manifest: " + row["path"])


def check_output_comparison(comparison, run1, run2):
    if comparison.get("status") != "identical":
        raise ValueError("retained output comparison is not identical")
    if comparison.get("run1_output_manifest_sha256") != sha(run1[1]) or comparison.get("run2_output_manifest_sha256") != sha(run2[1]):
        raise ValueError("retained output comparison hashes differ from actual manifests")
    if any(run1[2][path] != run2[2][path] for path in EXPECTED_OUTPUTS):
        raise ValueError("actual retained products differ between runs")


def check_candidate_rows(rows, expected_ids):
    exact_unique([row.get("component_id") for row in rows], expected_ids, "candidate assessment")
    classes = Counter(row.get("source_fitness_class") for row in rows)
    expected = {
        "compatible-original coverage candidate": 28,
        "partial/unbound original source-fitness case": 24,
    }
    if dict(classes) != expected:
        raise ValueError("source-relative classification counts differ from the preserved 28/24 scope")


def check_family_rows(rows, expected_families, expected_ids):
    ids = [row.get("id") for row in rows]
    exact_unique(ids, expected_families, "families")
    owners = {}
    for row in rows:
        members = row.get("candidate_ids")
        count = row.get("component_count")
        if not isinstance(members, list) or not isinstance(count, int) or count != len(members):
            raise ValueError("family membership count differs")
        exact_unique(members, members, "family members")
        for candidate in members:
            if candidate in owners:
                raise ValueError("candidate assigned to multiple families")
            owners[candidate] = row["id"]
    exact_unique(list(owners), expected_ids, "family candidate closure")


def check_contacts(rows, expected_contacts, expected_records):
    ids = [row.get("id") for row in rows]
    exact_unique(ids, expected_contacts, "contacts")
    for row in rows:
        source = expected_records[row["id"]]
        feature = row.get("feature")
        if feature != source.get("full_feature"):
            raise ValueError("contact feature differs from immutable handoff: " + row["id"])
        if row.get("feature_sha256") != source.get("full_feature_sha256"):
            raise ValueError("contact feature digest differs: " + row["id"])
        if row.get("geometry_sha256") != source.get("geometry_sha256"):
            raise ValueError("contact geometry digest differs: " + row["id"])
        if row.get("ordinal") != source.get("ordinal"):
            raise ValueError("contact ordinal differs: " + row["id"])
        if row.get("source_path") != source.get("containing_path") or row.get("source_part_sha256") != source.get("containing_sha256"):
            raise ValueError("contact source binding differs: " + row["id"])


def verify_run(baseline, packet, run_number, handoff, input_manifest, freeze):
    prefix = f"{packet}/executions/run-{run_number}"
    receipt_path = f"{packet}/executions/run-{run_number}-receipt.json"
    manifest_path = f"{prefix}/output-manifest.json"
    receipt = load_json(baseline.pinned_bytes(receipt_path), receipt_path)
    manifest_raw = baseline.pinned_bytes(manifest_path)
    manifest = load_json(manifest_raw, manifest_path)
    if receipt.get("run") != run_number or receipt.get("exit_code") != 0 or receipt.get("outcome") != "PASS":
        raise ValueError(f"run-{run_number} receipt is not successful")
    if receipt.get("producer_sha256") != freeze.get("producer_sha256"):
        raise ValueError(f"run-{run_number} producer pin differs from source freeze")
    if receipt.get("input_manifest_sha256") != sha(baseline.pinned_bytes(f"{packet}/input-manifest.json")):
        raise ValueError(f"run-{run_number} input-manifest receipt differs")
    if receipt.get("input_manifest_sha256") != freeze.get("input_manifest_sha256"):
        raise ValueError(f"run-{run_number} input manifest differs from source freeze")
    if receipt.get("output_manifest_sha256") != sha(manifest_raw):
        raise ValueError(f"run-{run_number} output-manifest digest differs")
    if receipt.get("output_manifest") != manifest:
        raise ValueError(f"run-{run_number} receipt and output manifest disagree")
    if manifest.get("inputs_frozen") is not True:
        raise ValueError(f"run-{run_number} does not record frozen inputs")
    if manifest.get("rows") != len(handoff["component_ids"]) or manifest.get("families") != len(handoff["complete_family_ids"]) or manifest.get("contacts") != len(handoff["contact_ids"]):
        raise ValueError(f"run-{run_number} declared counts disagree with original scope")
    products = {}
    descriptors = manifest.get("outputs")
    if not isinstance(descriptors, list) or {row.get("path") for row in descriptors} != EXPECTED_OUTPUTS or len(descriptors) != len(EXPECTED_OUTPUTS):
        raise ValueError(f"run-{run_number} product inventory is incomplete or duplicated")
    for row in descriptors:
        name = f"{prefix}/{row['path']}"
        raw = baseline.pinned_bytes(name)
        if len(raw) != row.get("bytes") or sha(raw) != row.get("sha256"):
            raise ValueError(f"run-{run_number} actual product differs from manifest: {row['path']}")
        products[row["path"]] = raw
    check_products(manifest, products)
    rows = [load_json(line, f"{prefix}/candidate-assessment.jsonl") for line in products["candidate-assessment.jsonl"].splitlines() if line]
    expected = sorted(handoff["component_ids"])
    check_candidate_rows(rows, expected)
    families = load_json(products["family-reconciliation.json"], f"{prefix}/family-reconciliation.json")
    check_family_rows(families.get("families", []), handoff["complete_family_ids"], expected)
    candidate_owner = {candidate: family["id"] for family in families["families"] for candidate in family["candidate_ids"]}
    for row in rows:
        if candidate_owner.get(row["component_id"]) != row.get("family_id"):
            raise ValueError("candidate-to-family join differs: " + row["component_id"])
    contacts = load_json(products["contact-lineage.json"], f"{prefix}/contact-lineage.json")
    if contacts.get("contact_count") != len(contacts.get("contacts", [])):
        raise ValueError("contact_count differs from actual contact array")
    check_contacts(contacts["contacts"], handoff["contact_ids"], handoff["full_current_contacts"])
    return receipt, manifest_raw, products, rows, families, contacts


def source_id_rows(full_raw: bytes, simplified_raw: bytes):
    def parse(raw, label):
        value = load_json(raw, label)
        features = value.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError(f"empty or missing FeatureCollection features in {label}")
        ids = []
        for feature in features:
            identity = feature.get("properties", {}).get("shapeID")
            if not isinstance(identity, str) or not identity:
                raise ValueError(f"missing shapeID in {label}")
            ids.append(identity)
        exact_unique(ids, ids, label)
        return sorted(ids)

    full_ids, simple_ids = parse(full_raw, "full native source"), parse(simplified_raw, "simplified native source")
    if full_ids != simple_ids:
        raise ValueError("full and simplified source ID rosters differ")
    return full_ids


def controls(baseline, packet, handoff, freeze, runs):
    run1, run2 = runs
    rows = [load_json(line, "run-1 candidate table") for line in run1[2]["candidate-assessment.jsonl"].splitlines() if line]
    fam_doc = load_json(run1[2]["family-reconciliation.json"], "run-1 family report")
    families = fam_doc["families"]
    contacts_doc = load_json(run1[2]["contact-lineage.json"], "run-1 contact report")
    ids, family_ids = sorted(handoff["component_ids"]), sorted(handoff["complete_family_ids"])
    expected_contacts = sorted(handoff["contact_ids"])
    positive = {
        "method_id": "assessment-producer",
        "kind": "positive-control",
        "outcome": "passed",
        "observed": {"components": len(rows), "families": len(families), "contacts": len(contacts_doc["contacts"]),
                     "source_fitness_classes": dict(Counter(row.get("source_fitness_class") for row in rows))},
        "source_id_comparison": {"country": "KAZ", "id_count": len(source_id_rows(
            baseline.pinned_bytes(f"{packet}/inputs/geoboundaries-kaz-adm2-2017-full-source.geojson"),
            baseline.pinned_bytes(f"{packet}/inputs/geoboundaries-kaz-adm2-2017-simplified-full-source.geojson"))),
            "full_source_sha256": baseline.pins[f"{packet}/inputs/geoboundaries-kaz-adm2-2017-full-source.geojson"]["sha256"],
            "simplified_source_sha256": baseline.pins[f"{packet}/inputs/geoboundaries-kaz-adm2-2017-simplified-full-source.geojson"]["sha256"]},
        "claim_limit": "Exact identity/output custody only. No geometry equivalence or geographic approval.",
    }

    failures = []
    def expect_rejection(label, operation):
        try:
            operation()
        except (ValueError, KeyError, TypeError):
            failures.append({"case": label, "rejected": True})
            return
        raise AssertionError("negative control accepted: " + label)

    run2_manifest = load_json(run2[1], "run-two manifest adverse fixture")
    expect_rejection("run-two-product-drift", lambda: check_products(run2_manifest, {**run2[2], "candidate-assessment.jsonl": run2[2]["candidate-assessment.jsonl"] + b"\n"}))
    expect_rejection("run-two-missing-product", lambda: check_products(run2_manifest, {k: v for k, v in run2[2].items() if k != "source-products.json"}))
    wrong_manifest = json.loads(json.dumps(run2_manifest))
    wrong_manifest["outputs"][0]["sha256"] = "0" * 64
    expect_rejection("run-two-wrong-product-manifest-hash", lambda: check_products(wrong_manifest, run2[2]))
    comparison = load_json(baseline.pinned_bytes(f"{packet}/executions/output-comparison.json"), "retained output comparison")
    expect_rejection("stale-output-comparison-hash", lambda: check_output_comparison({**comparison, "run2_output_manifest_sha256": "0" * 64}, run1, run2))
    for kind in ("contact-omission", "contact-duplicate", "contact-rebound"):
        changed = json.loads(json.dumps(contacts_doc["contacts"]))
        if kind == "contact-omission": changed.pop()
        elif kind == "contact-duplicate": changed.append(changed[0])
        else: changed[0]["id"] = "gb:KAZ:ADM2:foreign-control"
        expect_rejection(kind, lambda changed=changed: check_contacts(changed, expected_contacts, handoff["full_current_contacts"]))
    for kind in ("family-duplicate", "family-empty-duplicate", "family-foreign-member"):
        changed = json.loads(json.dumps(families))
        if kind == "family-duplicate": changed.append(json.loads(json.dumps(changed[0])))
        elif kind == "family-empty-duplicate":
            duplicate = json.loads(json.dumps(changed[0])); duplicate["candidate_ids"] = []; duplicate["component_count"] = 0; changed.append(duplicate)
        else: changed[0]["candidate_ids"][0] = "physical-component:foreign-control"
        expect_rejection(kind, lambda changed=changed: check_family_rows(changed, family_ids, ids))
    full = baseline.pinned_bytes(f"{packet}/inputs/geoboundaries-kaz-adm2-2017-full-source.geojson")
    simplified = baseline.pinned_bytes(f"{packet}/inputs/geoboundaries-kaz-adm2-2017-simplified-full-source.geojson")
    altered = load_json(simplified, "simplified source adverse fixture")
    altered["features"][0]["properties"]["shapeID"] += ":changed"
    expect_rejection("actual-source-reader-identity-drift", lambda: source_id_rows(full, json.dumps(altered).encode()))
    negative = {"method_id": "assessment-producer", "kind": "negative-control", "outcome": "passed",
                "cases": failures, "executed_count": len(failures),
                "claim_limit": "Tests actual retained-reader and scope validators. Does not test full RUS source (120,489,189 bytes exceeds the per-file cap), geometry truth or legal status."}
    check_output_comparison(comparison, run1, run2)
    reproducibility = {
        "method_id": "assessment-producer", "kind": "reproducibility", "outcome": "passed",
        "run_one_sha256": sha(run1[1]), "run_two_sha256": sha(run2[1]),
        "executions": [run1[0]["output_manifest_sha256"], run2[0]["output_manifest_sha256"]],
        "products_compared": sorted(EXPECTED_OUTPUTS),
        "comparison_sha256": sha(baseline.pinned_bytes(f"{packet}/executions/output-comparison.json")),
        "claim_limit": "Reconciles actual retained bytes, not a new execution of the oversized original science producer.",
    }
    return {
        "positive-control.json": positive,
        "negative-control.json": negative,
        "reproducibility-control.json": reproducibility,
    }


def run(repo: Path, base: str, vintage: str):
    repo = repo.resolve()
    candidate_manifest_path = repo / OWNED / "evidence-quality.json"
    manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
    baseline_cfg = manifest["baseline"]
    if baseline_cfg["commit"] != base:
        raise ValueError("requested baseline differs from manifest")
    # Bootstrap only the reader; then execute the exact immutable shared helper bytes.
    sys.path.insert(0, str(repo / "scripts"))
    from evidence.immutable import Baseline as BootstrapBaseline, descriptor
    helper_path = "scripts/evidence/immutable.py"
    helper_desc = next(row for row in baseline_cfg["files"] if row["path"] == helper_path)
    bootstrap = BootstrapBaseline(repo, base, [helper_desc])
    pinned = bootstrap.load_modules({"immutable": helper_path})["immutable"]
    baseline = pinned.Baseline(repo, base, baseline_cfg["files"])
    filenames = ["positive-control.json", "negative-control.json", "reproducibility-control.json"]
    # Admit the full fresh output set and all ancestors before parsing reports or sources.
    vintage_writer = pinned.NewVintage(baseline, OWNED, vintage, filenames)
    packet = ORIGINAL
    handoff = load_json(baseline.pinned_bytes(f"{packet}/inputs/complete-kazakhstan-russia-handoff.json"), "complete original handoff")
    freeze = load_json(baseline.pinned_bytes(f"{packet}/source-freeze.json"), "source freeze")
    input_manifest_raw = baseline.pinned_bytes(f"{packet}/input-manifest.json")
    if sha(input_manifest_raw) != freeze.get("input_manifest_sha256"):
        raise ValueError("original frozen input manifest digest differs")
    producer = baseline.pinned_bytes(f"{packet}/build_assessment.py")
    if sha(producer) != freeze.get("producer_sha256"):
        raise ValueError("original producer bytes differ from freeze")
    prior_controls = {
        name: baseline.pinned_bytes(f"{packet}/executions/{name}")
        for name in ("positive-control.json", "negative-control.json", "reproducibility-control.json")
    }
    run1 = verify_run(baseline, packet, 1, handoff, input_manifest_raw, freeze)
    run2 = verify_run(baseline, packet, 2, handoff, input_manifest_raw, freeze)
    if not prior_controls:
        raise AssertionError("prior controls were not consumed")
    values = controls(baseline, packet, handoff, freeze, [run1, run2])
    records = vintage_writer.publish(values)
    return {"status": "complete", "baseline": base, "vintage": vintage, "outputs": records,
            "controls_executed": values["negative-control.json"]["executed_count"],
            "historical_runs": 2, "scoped_components": len(handoff["component_ids"]),
            "scoped_families": len(handoff["complete_family_ids"]), "scoped_contacts": len(handoff["contact_ids"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT.parents[2])
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--vintage", required=True)
    args = parser.parse_args()
    result = run(args.repo, args.baseline, args.vintage)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
