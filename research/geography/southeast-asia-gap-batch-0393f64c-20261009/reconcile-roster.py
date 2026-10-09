#!/usr/bin/env python3
"""Join the retained 318-ID batch to the latest complete refreshed membership ledger."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from scripts.evidence.immutable import Baseline, NewVintage, descriptor, sha256

OWNED = "research/geography/southeast-asia-gap-batch-0393f64c-20261009/"
INDEX = Path(REPO, OWNED, "inputs/geo3-next-full-batch-318.json")
INDEX_SHA = "9857d3c03f94799b4e7e22c9afce68259dc4e2747d2864d6eb580030222f3430"
MANIFEST = "coordination/engineering/global-gap-candidate-refresh-20261009/evidence-quality.json"
REFRESH_DATA_BASELINE = "d27978f7d463c957c7e09e67fe5c5731d4bd4869"
CURRENT_HEAD = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()


def git_bytes(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def main():
    raw_index = INDEX.read_bytes()
    if sha256(raw_index) != INDEX_SHA:
        raise ValueError("retained batch index raw bytes differ from the stated custody hash")
    index = json.loads(raw_index)
    batch = index["original_batch"]
    ids = batch["complete_component_ids"]
    if len(ids) != 318 or len(ids) != len(set(ids)) or batch["component_count"] != 318:
        raise ValueError("batch index does not contain exactly 318 unique component IDs")
    family_ids = [family["family_id"] for family in batch["family_locators"]]
    if len(family_ids) != 122 or len(set(family_ids)) != 122:
        raise ValueError("batch index does not contain 122 unique family locators")

    manifest = json.loads(git_bytes("show", f"{CURRENT_HEAD}:{MANIFEST}"))
    output_by_path = {x["path"]: x for x in manifest["outputs"]}
    membership = [x for x in manifest["outputs"] if "/corrected-run-1-leaf-" in x["path"] and x["path"].endswith("/membership-metrics.jsonl.gz")]
    if len(membership) != 7:
        raise ValueError(f"expected seven complete corrected-run membership outputs, got {len(membership)}")
    helper = git_bytes("show", f"{REFRESH_DATA_BASELINE}:scripts/evidence/immutable.py")
    if helper != Path(REPO, "scripts/evidence/immutable.py").read_bytes():
        raise ValueError("immutable evidence helper changed after the retained execution baseline")
    inputs = membership + [descriptor("scripts/evidence/immutable.py", helper)]
    baseline = Baseline(str(REPO), CURRENT_HEAD, inputs)

    family_by_component = {}
    for family in batch["family_locators"]:
        family_id = family["family_id"]
        for component in family["complete_component_ids"]:
            family_by_component.setdefault(component, []).append(family_id)
    if set(family_by_component) != set(ids):
        raise ValueError("complete 122-family map and 318-component roster disagree")

    expected = set(ids)
    found = {}
    sources = []
    for pin in membership:
        path = pin["path"]
        compressed = baseline.pinned_bytes(path)
        decoded = gzip.decompress(compressed)
        baseline.admit(path + ":decoded", len(decoded))
        line_count = 0
        for line in decoded.splitlines():
            if not line:
                continue
            line_count += 1
            row = json.loads(line)
            identity = row.get("component_id")
            if identity in expected:
                if identity in found:
                    raise ValueError("batch identity appears more than once in refreshed membership: " + identity)
                found[identity] = {"component_id": identity, "family_locators": sorted(family_by_component[identity]),
                                   "membership": row}
        sources.append({"path": path, "bytes": pin["bytes"], "sha256": pin["sha256"],
                        "uncompressed_bytes": pin["uncompressed_bytes"],
                        "uncompressed_sha256": pin["uncompressed_sha256"], "rows": line_count})
    if set(found) != expected:
        raise ValueError("refreshed membership does not cover exact batch roster: " +
                         json.dumps({"missing": sorted(expected - set(found)), "unexpected": sorted(set(found) - expected)}))

    rows = []
    for identity in ids:
        row = found[identity]
        member = row["membership"]
        missing = member.get("missing_facts") or member.get("unassigned_requirements") or []
        state = "unresolved" if member.get("class") == "unresolved" else "non-unresolved-review-required"
        if member.get("delivered") or member.get("fully_integrated") or member.get("implemented"):
            state = "reported-progress-reconcile-exact-decision"
        row["reconciled_state"] = state
        row["exact_id_reason"] = missing if missing else ["No unresolved-fact list in membership row; inspect preserved source case before any decision."]
        row["next_action"] = ("Resolve only listed missing facts from retained, component-bound evidence; otherwise preserve unresolved/partial state."
                              if missing else "Check retained source and decision evidence for this exact ID; do not infer approval from absence.")
        rows.append(row)

    from collections import Counter
    classes = Counter(x["membership"].get("class") for x in rows)
    pipeline = Counter((x["membership"].get("pipeline_status") or {}).get("state") for x in rows)
    progress = {flag: sum(bool(x["membership"].get(flag)) for x in rows)
                for flag in ("repair_ready", "implemented", "fully_integrated", "delivered")}
    run_name = "roster-reconcile-001"
    vintage = NewVintage(baseline, OWNED, run_name,
                         ["component-state.json", "summary.json"])
    component_state = {"version": 1, "batch_id": batch["batch_id"], "current_head": CURRENT_HEAD,
                       "refresh_execution_baseline": REFRESH_DATA_BASELINE, "verified_output_commit": CURRENT_HEAD,
                       "batch_index_sha256": INDEX_SHA,
                       "component_count": len(rows), "family_count": len(batch["family_locators"]),
                       "priority_family_count": len(index["existing_priority_families"]),
                       "rows": sorted(rows, key=lambda x: x["component_id"])}
    summary = {"version": 1, "batch_id": batch["batch_id"], "current_head": CURRENT_HEAD,
               "refresh_execution_baseline": REFRESH_DATA_BASELINE, "verified_output_commit": CURRENT_HEAD,
               "batch_index_sha256": INDEX_SHA,
               "component_count": len(rows), "family_count": len(batch["family_locators"]),
               "country_codes": batch["countries"], "subcontinents": batch["subcontinents"],
               "priority_component_count": sum(len(x["research_component_ids"]) for x in index["existing_priority_families"]),
               "class_counts": dict(classes), "exclusive_pipeline_state_counts": {str(k): v for k, v in pipeline.items()},
               "progress_flag_counts": progress, "membership_sources": sources,
               "scope": "Exact batch status projection from the retained full corrected membership outputs; not source approval or an engineering repair.",
               "limitations": ["The catalog refresh is metadata progress only; it makes no physical, water/ice, causal, authority or repair finding.",
                               "Deep source/current-target facts for the 30 prioritized IDs are handled separately."]}
    vintage.publish({"component-state.json": component_state, "summary.json": summary})
    print(json.dumps({"run": run_name, "rows": len(rows), "families": len(batch["family_locators"]),
                      "classes": dict(classes), "pipeline": {str(k): v for k, v in pipeline.items()},
                      "progress": progress, "decoded_input_bytes": sum(baseline.consumed.values())}, indent=2))


if __name__ == "__main__":
    main()
