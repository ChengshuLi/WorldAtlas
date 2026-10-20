#!/usr/bin/env python3
"""Build a bounded interval disposition proposal from retained Angola evidence."""

import argparse
import gzip
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


PACKAGE = "gb-AGO-ADM2--repair-evaluation"
REVIEWED_MAIN = "c58875b56e3954070632f1626a0724ef3108dc11"
ROOT = Path("coordination/engineering/angola-repair-delivery-20261017")
ACCEPTED_RECEIPT = "https://github.com/ChengshuLi/WorldAtlas/pull/2377#issuecomment-6230307071"
SOURCE_REVIEW = "https://github.com/ChengshuLi/WorldAtlas/issues/2313#issuecomment-6228143772"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(body):
    return hashlib.sha256(body).hexdigest()


def blob_oid(path, commit):
    return subprocess.check_output(
        ["git", "rev-parse", f"{commit}:{path}"], text=True
    ).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", REVIEWED_MAIN, head], check=True)

    package = read_json(ROOT / "source-stage/original-package.json")
    disposition = read_json(ROOT / "conservative-003/original-scope-disposition.json")
    held_rows = read_json(ROOT / "conservative-003/held-native-rows.json")["rows"]
    observation_path = ROOT / "unresolved-disposition-001/current-selected-owner-observation.json.gz"
    observation_bytes = observation_path.read_bytes()
    observation = json.loads(gzip.decompress(observation_bytes))

    if package["package_id"] != PACKAGE:
        raise SystemExit("Original package ID changed")
    if observation["commit"] != head or observation["original_package"]["package_id"] != PACKAGE:
        raise SystemExit("Selected-owner report is not for this exact package/current head")
    if observation["kind"] != "literal-selected-owner-observation-v1":
        raise SystemExit("Unexpected selected-owner report kind")
    if observation["query_count"] != package["native_cells"]:
        raise SystemExit("Selected-owner report does not cover the full original package")
    if observation["acquisition"]["complete_scientific_closure"] is not False:
        raise SystemExit("Unexpected scientific-closure assertion")

    targets = {row["pixelIndex"]: row for row in disposition["targets"]}
    if len(targets) != len(package["owners"]):
        raise SystemExit("Owner target roster does not match the original package")
    if set(targets) != set(package["owners"]):
        raise SystemExit("Owner identities differ from the original package")

    held = {}
    for row in held_rows:
        y = row["y"]
        for start, end, owner in row["runs"]:
            if end <= start or owner not in targets:
                raise SystemExit("Invalid held range or owner")
            for x in range(start, end):
                key = (y, x)
                if key in held:
                    raise SystemExit("Duplicate held key")
                held[key] = owner

    observed = {}
    for row in observation["keys"]:
        key = (row["y"], row["x"])
        if key in observed:
            raise SystemExit("Duplicate selected-owner key")
        observed[key] = row
    if len(observed) != package["native_cells"]:
        raise SystemExit("Selected-owner key count differs from the original package")

    interval_rows = []
    summary = Counter()
    per_owner_held = Counter()
    per_owner_supported = Counter()
    interval_keys = set()
    for queue_path in sorted((ROOT / "frozen-queue").glob("block-*.json.gz")):
        queue = json.loads(gzip.decompress(queue_path.read_bytes()))
        for row_number, item in enumerate(queue):
            y, start, end, owners, source_features, source_class = item
            if not all(isinstance(v, int) for v in (y, start, end)) or end <= start:
                raise SystemExit("Malformed original interval")
            if len(owners) != 1 or owners[0] not in targets:
                raise SystemExit("Original interval lacks one authenticated owner")
            owner = owners[0]
            target_id = targets[owner]["target_id"]
            interval_key = (queue_path.name, row_number)
            if interval_key in interval_keys:
                raise SystemExit("Duplicate original interval identity")
            interval_keys.add(interval_key)

            held_count = 0
            for x in range(start, end):
                key = (y, x)
                selected = observed.get(key)
                if selected is None:
                    raise SystemExit("Original interval key is missing from selected-owner observation")
                held_owner = held.get(key)
                if held_owner is not None:
                    if held_owner != owner:
                        raise SystemExit("Held key owner differs from original interval")
                    if selected["base_owner"] != 0 or selected["accepted_additive_owner"] != 0 or selected["effective_selected_owner"] != 0:
                        raise SystemExit("Held key is assigned in the current selected product")
                    held_count += 1
                else:
                    if selected["effective_selected_owner"] <= 0 or selected["owner_id"] != target_id:
                        raise SystemExit("Supported key is not assigned to its exact original target")

            width = end - start
            if held_count == width:
                status = "proposed_documented_unresolved_source_disagreement"
                per_owner_held[owner] += width
                summary["held_intervals"] += 1
                summary["held_cells"] += width
                source_reason = "foreign_adm1_source_membership_disagreement"
                credit = 0
            elif held_count == 0:
                status = "accepted_supported_delivery"
                per_owner_supported[owner] += width
                summary["supported_intervals"] += 1
                summary["supported_cells"] += width
                source_reason = None
                credit = width
            else:
                raise SystemExit("Original interval is partly held; no interval disposition may be inferred")

            interval_rows.append({
                "block": queue_path.name,
                "row": row_number,
                "y": y,
                "x_start": start,
                "x_end_exclusive": end,
                "cells": width,
                "owner_index": owner,
                "target_id": target_id,
                "source_feature_indices": source_features,
                "original_mask_class": source_class,
                "disposition": status,
                "reason": source_reason,
                "accepted_repair_credit": credit,
            })

    if len(interval_rows) != package["interval_segments"]:
        raise SystemExit("Original interval denominator mismatch")
    if summary["held_cells"] != disposition["held_cells"] or summary["supported_cells"] != disposition["supported_cells"]:
        raise SystemExit("Held/supported cell totals differ from the retained stock disposition")
    if summary["held_intervals"] + summary["supported_intervals"] != package["interval_segments"]:
        raise SystemExit("Some original interval is not dispositioned")
    if set(held) != {key for key in observed if observed[key]["effective_selected_owner"] == 0}:
        raise SystemExit("Held map does not equal the zero-effective-owner set")
    if len(held) != disposition["held_cells"] or len(per_owner_held) != disposition["held_owners"]:
        raise SystemExit("Held-key/owner totals differ from the retained disposition")
    for target in disposition["targets"]:
        owner = target["pixelIndex"]
        if per_owner_held[owner] != target["held_cells"]:
            raise SystemExit("Per-owner held count differs from the retained disposition")
        if per_owner_supported[owner] != target["supported_cells"]:
            raise SystemExit("Per-owner supported count differs from the retained disposition")
    if summary["held_cells"] + summary["supported_cells"] != package["native_cells"]:
        raise SystemExit("Original cell denominator mismatch")

    original_paths = [
        "coordination/engineering/angola-repair-delivery-20261017/source-stage/original-package.json",
        "coordination/engineering/angola-repair-delivery-20261017/conservative-003/original-scope-disposition.json",
        "coordination/engineering/angola-repair-delivery-20261017/conservative-003/held-native-rows.json",
        *[f"coordination/engineering/angola-repair-delivery-20261017/frozen-queue/{p.name}" for p in sorted((ROOT / "frozen-queue").glob("block-*.json.gz"))],
        "data/ownership-selection.json",
    ]
    inputs = []
    for name in original_paths:
        body = Path(name).read_bytes()
        oid = blob_oid(name, REVIEWED_MAIN)
        pinned = subprocess.check_output(["git", "cat-file", "blob", oid])
        if body != pinned:
            raise SystemExit(f"Input differs from immutable current-main bytes: {name}")
        inputs.append({"path": name, "git_blob_oid": oid, "bytes": len(body), "sha256": sha256(body)})
    inputs.append({"path": observation_path.as_posix(), "git_blob_oid": None,
                   "bytes": len(observation_bytes), "sha256": sha256(observation_bytes),
                   "kind": observation["kind"], "query_sha256": observation["query_sha256"]})

    report = {
        "version": 1,
        "kind": "original-package-interval-disposition-proposal-v1",
        "status": "proposal_only",
        "current_main": REVIEWED_MAIN,
        "evidence_base_commit": REVIEWED_MAIN,
        "generator": {
            "path": "coordination/engineering/angola-repair-delivery-20261017/method/build-unresolved-interval-disposition.py",
            "bytes": Path(__file__).stat().st_size,
            "sha256": sha256(Path(__file__).read_bytes()),
        },
        "package_id": PACKAGE,
        "original_scope": {
            "cells": package["native_cells"], "intervals": package["interval_segments"],
            "owners": len(package["owners"]), "land_mask_cells": package["land_cells"],
            "inland_water_mask_cells": package["inland_water_cells"],
        },
        "accounting": {
            "accepted_supported_cells": summary["supported_cells"],
            "accepted_supported_intervals": summary["supported_intervals"],
            "accepted_supported_delivery": ACCEPTED_RECEIPT,
            "proposed_held_cells": summary["held_cells"],
            "proposed_held_intervals": summary["held_intervals"],
            "proposed_held_owners": len(per_owner_held),
            "additional_accepted_credit": 0,
        },
        "held_basis": {
            "disposition": "proposed_documented_unresolved_source_disagreement",
            "basis": "Exact held key set is retained as the conservative union of competing foreign ADM1 source contacts; independent handoff review accepted the scope partition and explicitly left selected/emitted acceptance to integration.",
            "foreign_adm1_union_counts": {"NAM": 15255, "COD": 13269, "COG": 722, "ZMB": 17},
            "independent_source_review": SOURCE_REVIEW,
            "held_source_evidence": "coordination/engineering/angola-repair-delivery-20261017/independent-source-review/foreign-adm1-overlap.json.gz",
            "legal_or_current_boundary_finding": False,
        },
        "current_selected_observation": {
            "path": observation_path.as_posix(),
            "commit": observation["commit"],
            "queried_original_cells": observation["query_count"],
            "base_assigned": sum(k["base_owner"] > 0 for k in observation["keys"]),
            "accepted_additive_assigned": sum(k["accepted_additive_owner"] > 0 for k in observation["keys"]),
            "effective_assigned": sum(k["effective_selected_owner"] > 0 for k in observation["keys"]),
            "zero_effective_held": sum(k["effective_selected_owner"] == 0 for k in observation["keys"]),
            "overlap_count": sum(k["existing_product_overlap"] for k in observation["keys"]),
            "scientific_qualification": False,
        },
        "inputs": inputs,
        "intervals": interval_rows,
        "limitations": [
            "Only the 141,263 supported cells have accepted delivery credit, through the cited PR 2377 receipt.",
            "The 29,263 held cells remain proposed unresolved dispositions with zero accepted repair or exception credit until separately accepted.",
            "This does not resolve applicability between the retained original municipal source and competing foreign ADM1 sources.",
            "The source-relative 2018 Angolan product is CC BY 3.0 IGO; this proposal makes no redistribution of source geometry and no current-law, sovereignty, whole-feature or current-boundary claim.",
            "Original mask classes are retained input labels, not a present-day physical land/water determination.",
            "This report is a literal selected-owner observation and interval accounting; it does not authorize imports, publication, a regional certificate, or package closure.",
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"output": out.as_posix(), "intervals": len(interval_rows), **dict(summary),
                      "inputs": len(inputs), "sha256": sha256(out.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
