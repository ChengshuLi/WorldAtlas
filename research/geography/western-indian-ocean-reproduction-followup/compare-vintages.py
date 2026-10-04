#!/usr/bin/env python3
"""Compare corrected reproduction results with immutable #637 historical outputs."""
import hashlib
import json
import math

from reproduction_common import HERE, MANIFEST, pinned_bytes, write_candidate

PREFIX = "data/regional-review/regional-review-4f180b98473f1071/"


def read_json(raw):
    return json.loads(raw)


def compare_values(old, new, path, changes):
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(old.keys() & new.keys()):
            if key in {"method", "baseline_commit", "source_commit"}:
                continue
            compare_values(old[key], new[key], f"{path}.{key}", changes)
        return
    if isinstance(old, list) and isinstance(new, list):
        def identity(item):
            if isinstance(item, dict):
                for key in ("id", "atlas_id", "current_id", "province_id", "source_name", "a"):
                    if key in item:
                        return (key, item[key])
            return None
        old_map = {identity(item): item for item in old if identity(item) is not None}
        new_map = {identity(item): item for item in new if identity(item) is not None}
        if old_map and new_map:
            for key in old_map.keys() & new_map.keys():
                compare_values(old_map[key], new_map[key], f"{path}[{key[1]}]", changes)
            return
        for index, (left, right) in enumerate(zip(old, new)):
            compare_values(left, right, f"{path}[{index}]", changes)
        if len(old) != len(new):
            changes.append({"path": path, "historical_count": len(old), "reproduced_count": len(new)})
        return
    if isinstance(old, bool) or isinstance(new, bool):
        if old != new:
            changes.append({"path": path, "historical": old, "reproduced": new})
    elif isinstance(old, (int, float)) and isinstance(new, (int, float)):
        if not math.isclose(old, new, rel_tol=1e-10, abs_tol=1e-8):
            changes.append({"path": path, "historical": old, "reproduced": new})
    elif type(old) is type(new) and old != new:
        changes.append({"path": path, "historical": old, "reproduced": new})


old_geometry = read_json(pinned_bytes(PREFIX + "geometry-comparison.json", "issue_packet"))
new_geometry = json.loads((HERE / "geometry-comparison.json").read_text(encoding="utf-8"))
old_codab = read_json(pinned_bytes(PREFIX + "madagascar-current-COD-AB-review.json", "issue_packet"))
new_codab = json.loads((HERE / "madagascar-current-COD-AB-review.json").read_text(encoding="utf-8"))
geometry_changes, codab_changes = [], []
compare_values(old_geometry, new_geometry, "geometry", geometry_changes)
compare_values(old_codab, new_codab, "codab", codab_changes)

result = {
    "version": 1,
    "issue": 662,
    "historical": {
        "evaluation_commit": MANIFEST["historical_vintage"]["evaluation_commit"],
        "packet_commit": MANIFEST["baseline"]["packet_commit"],
        "geometry_output_sha256": MANIFEST["historical_vintage"]["original_geometry_sha256"],
        "codab_output_sha256": MANIFEST["historical_vintage"]["original_codab_sha256"],
    },
    "reproduced": {
        "geography_baseline_commit": MANIFEST["baseline"]["commit"],
        "packet_commit": MANIFEST["baseline"]["packet_commit"],
        "geometry_output_sha256": hashlib.sha256((HERE / "geometry-comparison.json").read_bytes()).hexdigest(),
        "codab_output_sha256": hashlib.sha256((HERE / "madagascar-current-COD-AB-review.json").read_bytes()).hexdigest(),
    },
    "comparison": {
        "numeric_tolerance": {"relative": 1e-10, "absolute": 1e-8},
        "geometry_changed_values_count": len(geometry_changes),
        "geometry_changed_values": geometry_changes,
        "codab_changed_values_count": len(codab_changes),
        "codab_changed_values": codab_changes,
        "interpretation": "Only the listed reproduced-value or disposition deltas differ from the immutable historical outputs. An unchanged value confirms reproducibility under corrected input and validity controls; it does not establish regional approval. No metric delta alone establishes that a former measurement was known to be wrong.",
    },
}
write_candidate("metric-comparison.json", result)
print(json.dumps({
    "geometry_changed_values": len(geometry_changes),
    "codab_changed_values": len(codab_changes),
    "geometry_changed_examples": geometry_changes[:5],
    "codab_changed_examples": codab_changes[:5],
}, ensure_ascii=False, indent=2))
