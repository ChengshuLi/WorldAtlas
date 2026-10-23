#!/usr/bin/env python3
"""Derive the exact held-32 native request from retained COM source/physical evidence."""
import hashlib
import json
import pathlib
import subprocess

REPO = pathlib.Path.cwd()
OLD_COMMIT = "88482b58d6662a34436d2ff8fb82dc64720f71dd"
OLD_ROOT = "coordination/engineering/comoros-original-disposition-20261021"
KEY_PATH = OLD_ROOT + "/decision-review-001/decision-and-key-join.json"
SOURCE_PATH = OLD_ROOT + "/evidence/source-004/source-evidence.json"
KEY_SHA256 = "0fc8371056c99f27635bc821ee42cbfc2468f585ef1afd1ba1b94a2cc437464c"
SOURCE_SHA256 = "1696a8cb4d7e97dbefbf8bfbd939433e4b971fb3b00c7806693099e5ba96edc7"
CURRENT_SELECTOR = "0e50bd281afec27ce32fac8dcb4dfe2401f94b6c"
TARGET = pathlib.Path("coordination/engineering/comoros-held32-qualification-20261023/input")


def git_body(commit, path):
    return subprocess.check_output(["git", "show", commit + ":" + path], cwd=REPO)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(name, value):
    target = TARGET / name
    if target.exists():
        raise SystemExit("refusing to overwrite " + str(target))
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    target.write_bytes(raw)
    return {"path": str(target), "bytes": len(raw), "sha256": sha(raw)}


def runs_for_keys(keys, owner, kind=None):
    by_y = {}
    for y, x in sorted(keys):
        by_y.setdefault(y, []).append(x)
    rows = []
    for y, xs in sorted(by_y.items()):
        start = prev = xs[0]
        runs = []
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
                continue
            runs.append([start, prev + 1, owner] if kind is None else [start, prev + 1, kind])
            start = prev = x
        runs.append([start, prev + 1, owner] if kind is None else [start, prev + 1, kind])
        rows.append({"y": y, "runs": runs})
    return rows


def expand(rows, owner=None):
    cells = set()
    for row in rows:
        for run in row["runs"]:
            start, end = run[:2]
            if owner is not None and run[2] != owner:
                raise SystemExit("unexpected native owner")
            for x in range(start, end):
                key = (row["y"], x)
                if key in cells:
                    raise SystemExit("duplicate native cell")
                cells.add(key)
    return cells


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    key_raw = git_body(OLD_COMMIT, KEY_PATH)
    source_raw = git_body(OLD_COMMIT, SOURCE_PATH)
    if sha(key_raw) != KEY_SHA256 or sha(source_raw) != SOURCE_SHA256:
        raise SystemExit("retained COM source or join bytes differ from their exact pins")
    key_doc, source = json.loads(key_raw), json.loads(source_raw)
    results = key_doc["key_results"]
    if len(results) != 571:
        raise SystemExit("the original 571-key denominator changed")
    selected = [row for row in results if row.get("ocha_concordant") is True
                and row.get("gshhg_mapped_land_center_hit") is False]
    if len(selected) != 32 or any(row.get("candidate_screen") is not False
                                  or row.get("disposition") != "held"
                                  or row.get("gshhg_mapped_inland_water_center_hit") is not False
                                  or row.get("whole_target_difference_center_hits") != []
                                  for row in selected):
        raise SystemExit("the exact held-32 predicate or preserved adverse context changed")
    if sum(row.get("candidate_screen") is True for row in results) != 485:
        raise SystemExit("the accepted 485 partition changed")
    held = [row for row in results if row.get("candidate_screen") is False]
    ocha_adverse = [row for row in held if row.get("ocha_concordant") is False]
    if len(held) != 86 or len(ocha_adverse) != 54 or len(held) - len(selected) != 54:
        raise SystemExit("the 485 + 32 + 54 partition changed")

    keys = {(row["y"], row["x"]) for row in selected}
    if len(keys) != 32:
        raise SystemExit("duplicate original key in held-32 subset")
    all_targets = {target["id"] for target in source["targets"]}
    key_targets = {row["source_feature_id"] for row in selected}
    if all_targets != key_targets:
        raise SystemExit("held-32 subset does not bind every exact original source member")

    # Verify that each selected cell was already classed as mapped land in all
    # three authenticated physical/source target bindings. Only narrow the exact
    # complete owner coverage; do not modify source geometries or observations.
    original_by_target = {}
    for target in source["targets"]:
        cells = {}
        for row in target["coverage_rows"]:
            for start, end, kind in row["runs"]:
                for x in range(start, end):
                    key = (row["y"], x)
                    if key in cells:
                        raise SystemExit("duplicate retained physical coverage key")
                    cells[key] = kind
        if len(cells) != 571:
            raise SystemExit("retained physical coverage does not match the original denominator")
        if any(cells.get(key) != "mapped_land_support" for key in keys):
            raise SystemExit("a held-32 key lacks the retained mapped-land support class")
        original_by_target[target["id"]] = cells

    patch_rows = runs_for_keys(keys, 7114)
    if len(expand(patch_rows, 7114)) != 32:
        raise SystemExit("derived native request does not contain exactly32 cells")
    for target in source["targets"]:
        target["coverage_rows"] = runs_for_keys(keys, "mapped_land_support")
    # The stock helper must derive the accepted contract/baseline itself for the
    # current final selection; do not carry stale historical baseline fields.
    for field in ("native_contract", "native_latitudes", "owner_roster", "base_reference"):
        source.pop(field, None)

    partition_rows = []
    for row in results:
        group = ("accepted-485" if row.get("candidate_screen") is True else
                 "held-32-stock-qualification" if row in selected else
                 "held-54-ocha-adverse")
        partition_rows.append({
            "x": row["x"], "y": row["y"], "owner": 7114,
            "source_feature_id": row["source_feature_id"],
            "source_feature_name": row["source_feature_name"],
            "source_feature_index": row["source_feature_index"],
            "ocha_concordant": row["ocha_concordant"],
            "gshhg_mapped_land_center_hit": row["gshhg_mapped_land_center_hit"],
            "gshhg_mapped_inland_water_center_hit": row["gshhg_mapped_inland_water_center_hit"],
            "whole_target_difference_center_hits": row["whole_target_difference_center_hits"],
            "prior_observation_owner": row["existing_effective_owner"],
            "disposition_at_review": row["disposition"],
            "partition": group,
        })
    config = {"version": 1,
              "selector": {"commit": CURRENT_SELECTOR, "path": "data/ownership-selection.json"},
              "source_evidence": source}
    partition = {
        "version": 1,
        "kind": "comoros-held32-stock-qualification-input-derivation",
        "retained_inputs": {
            "commit": OLD_COMMIT,
            "key_join": {"path": KEY_PATH, "bytes": len(key_raw), "sha256": KEY_SHA256},
            "source_evidence": {"path": SOURCE_PATH, "bytes": len(source_raw), "sha256": SOURCE_SHA256},
            "source_contract": key_doc["source_contract"],
        },
        "current_selection": {"commit": CURRENT_SELECTOR, "path": "data/ownership-selection.json"},
        "original_scope": {"keys": 571, "accepted_candidate": 485, "held": 86, "owner": 7114},
        "qualification_scope": {"keys": 32, "owner": 7114, "rule": "OCHA-concordant and no GSHHG mapped-land center hit; all were held; no inland-water or whole-target-difference center hit", "source_members": sorted(key_targets)},
        "preserved_adverse_scope": {"keys": 54, "rule": "OCHA-discordant; remains held and is not part of this stock attempt"},
        "rows": partition_rows,
        "limits": [
            "This derives only the exact 32-key native request from the authenticated original 571 rows.",
            "No source, physical, owner-observation or geometry producer is rerun.",
            "The 32 are pending this stock qualification result; this file grants no repair, acceptance or credit.",
            "The 54 OCHA-adverse keys remain held; OCHA is comparator context only and no OCHA geometry is redistributed.",
            "Prior owner observation is retained literally; current selected-state conservation is checked by the stock constructor."
        ]
    }
    print(json.dumps({
        "source_inputs": write_new("source-evidence-config.json", config),
        "native_patch": write_new("native-patch.json", {"rows": patch_rows}),
        "partition": write_new("partition.json", partition),
        "counts": {"original": len(results), "accepted_candidate": 485, "held": 86,
                   "qualification": len(keys), "OCHA_adverse_held": 54,
                   "intervals_in_qualification_patch": len(patch_rows),
                   "source_members": sorted(key_targets)},
    }, sort_keys=True))


if __name__ == "__main__":
    main()
