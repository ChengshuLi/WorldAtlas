#!/usr/bin/env python3
"""Safe additive replacement for PR #1411's identity-only standalone writer.

This entry point never writes into the original source packet. Each invocation
admits one fresh owned run before reading pinned inputs, then publishes two
exclusive products and a final completion receipt.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from output_admission import read_regular, reserve_output_set, sha256


ISSUE = 1557
WORKER = "01a10947-b3d7-7812-8b2f-c5a47e88ccb2"
BASELINE = "e8dec40bd63ef80345798047cbd3f2a4b6ae0db9"
PREFIX = "physical-component:"
OUTPUTS = ("subject-inventory.json", "subject-registry.json", "completion.json")
INPUTS = {
    "family-row": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/family-row.json",
                   "a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3"),
    "component-roster": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/component-roster.txt",
                         "8542c017a9d25fe717f19a4e0c418cf76002dc69869f16c34981f935e1fe39d1"),
    "original-inventory": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/subject-inventory.json",
                           "1488d350960e3e745bba830b065299a2632e22d9bb9e7f012f9bb541c51dcfa6"),
    "original-registry": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/subject-registry.json",
                          "c1b1b1555fa7aafcefc84423e06f5a32593b4c0be9b72193ca3af142bf846ab6"),
    "original-writer-code": ("research/geography/indonesia-borneo-source-fitness-20261007/sources/v1/build-subject-inventory.py",
                             "a8602c0d2643accc4e53ee4a880e2b238a09a3840a2ae99d9695af0ac95b3f9a"),
}
OWNED = Path(__file__).resolve().parent
REPO = OWNED.parents[2]


def _load_inputs(repo_root: Path) -> tuple[dict, list[str], dict[str, bytes], dict]:
    records = {}
    for key, (relative, expected) in INPUTS.items():
        raw = read_regular(repo_root, relative)
        actual = sha256(raw)
        if actual != expected:
            raise ValueError(f"Pinned input changed: {key}")
        records[key] = {"path": relative, "commit": BASELINE, "bytes": len(raw), "sha256": actual}
        if key == "family-row":
            family_raw = raw.rstrip(b"\n")
            if sha256(family_raw) != expected:
                raise ValueError("Family record byte convention differs from its pinned digest")
            family = json.loads(family_raw)
        elif key == "component-roster":
            roster = raw.decode("utf-8").splitlines()
        elif key == "original-inventory":
            original_inventory = raw
        elif key == "original-registry":
            original_registry = raw
    if len(roster) != 45 or len(set(roster)) != 45 or roster != sorted(roster):
        raise ValueError("Pinned component roster is missing, duplicate, or unsorted")
    return family, roster, {"subject-inventory.json": original_inventory,
                            "subject-registry.json": original_registry}, records


def identity_products(family: dict, roster: list[str]) -> dict[str, bytes]:
    """Pure identity projection; executable after authenticated inputs are admitted."""
    ids = family.get("complete_component_ids")
    if (family.get("component_count") != 45 or not isinstance(ids, list) or len(ids) != 45 or
            len(set(ids)) != 45 or sorted(ids) != roster or
            any(not isinstance(value, str) or not value.startswith(PREFIX) for value in ids)):
        raise ValueError("Family row and the complete native 45-ID roster disagree")
    native = sorted(value[len(PREFIX):] for value in ids)
    if len(native) != 45 or len(set(native)) != 45 or [PREFIX + value for value in native] != roster:
        raise ValueError("Identity projection is missing, duplicate, or fabricated")
    inventory = {"version": 1, "source_family_id": family["id"],
                 "source_row_sha256": "a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3",
                 "component_roster_sha256": "88831aad22806bf4f461197a12cb8309bf9a0139e5bd82b967a55e8255ad26ec",
                 "component_ids": native}
    registry = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": PREFIX + value,
         "properties": {"source_value": value, "id": PREFIX + value,
                        "source_property": "component_id"}, "geometry": None} for value in native]}
    return {
        "subject-inventory.json": (json.dumps(inventory, sort_keys=True, ensure_ascii=False,
                                                separators=(",", ":")) + "\n").encode(),
        "subject-registry.json": (json.dumps(registry, sort_keys=True, ensure_ascii=False,
                                               separators=(",", ":")) + "\n").encode(),
    }


def compare_original_products(products: dict[str, bytes], originals: dict[str, bytes]) -> None:
    if set(products) != set(originals):
        raise ValueError("Identity writer output inventory differs from the original complete product set")
    for name, original in originals.items():
        if products[name] != original:
            raise ValueError(f"Changed comparison product: {name}")


def execute(run_id: str, *, repo_root: Path = REPO, packet_root: Path = OWNED,
            load_inputs=_load_inputs) -> dict:
    # This is deliberately the first filesystem operation involving project inputs.
    with reserve_output_set(packet_root, run_id, OUTPUTS) as reservation:
        family, roster, originals, input_records = load_inputs(repo_root)
        products = identity_products(family, roster)
        compare_original_products(products, originals)
        code_records = {
            "writer": sha256(read_regular(repo_root, "research/geography/indonesia-borneo-writer-integrity-1411/identity_writer.py")),
            "output_admission": sha256(read_regular(repo_root, "research/geography/indonesia-borneo-writer-integrity-1411/output_admission.py")),
        }
        completion = {
            "version": 1, "status": "complete", "issue": ISSUE, "worker_id": WORKER,
            "run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "entry_point": "identity_writer.py", "baseline_commit": BASELINE,
            "code_sha256": code_records, "inputs": input_records,
            "limits": [
                "Identity-only inventory and null-geometry registry; no source authority or geographic result is implied.",
                "The original 45-component science, 8 contacts, 21 numeric-closure unknowns, and all source/authority limits are preserved.",
            ],
        }
        publication = reservation.publish(products, completion)
        return {"status": "complete", "run_id": run_id, **publication}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Fresh owned run id, for example run-20261009-a")
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args.run_id), sort_keys=True))
        return 0
    except Exception as exc:
        parser.exit(2, f"refused: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
