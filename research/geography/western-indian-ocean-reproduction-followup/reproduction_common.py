"""Pinned, fail-closed inputs and safe outputs for the #662 reproduction."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

from shapely import make_valid

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST_PATH = HERE / "evidence-quality.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
BASELINE = MANIFEST["baseline"]["commit"]
PACKET_COMMIT = MANIFEST["baseline"]["packet_commit"]
INPUT_PINS_PATH = HERE / "input-pins.json"
INPUT_PINS_BYTES = INPUT_PINS_PATH.read_bytes()
if hashlib.sha256(INPUT_PINS_BYTES).hexdigest() != MANIFEST["input_pins_sha256"]:
    raise ValueError("input-pins.json digest differs from evidence manifest")
INPUT_PINS = json.loads(INPUT_PINS_BYTES)
if INPUT_PINS["geography_baseline_commit"] != BASELINE or INPUT_PINS["issue_packet_commit"] != PACKET_COMMIT:
    raise ValueError("input-pins.json commit identities differ from evidence manifest")
INPUT_PREFIX = "data/regional-review/regional-review-4f180b98473f1071/"
SCOPE_PATH = INPUT_PREFIX + "issue-scope.json"


def pinned_bytes(path: str, role: str = "geography_baseline") -> bytes:
    """Read bytes from the immutable baseline commit and verify their SHA-256."""
    expected = INPUT_PINS["sha256"][role].get(path)
    if expected is None:
        raise ValueError(f"unmanifested input path: {path}")
    commit = BASELINE if role == "geography_baseline" else PACKET_COMMIT
    data = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f"changed baseline input {path}: sha256 {actual} != {expected}")
    return data


def pinned_json(path: str, role: str = "geography_baseline"):
    return json.loads(pinned_bytes(path, role))


for commit in (BASELINE, PACKET_COMMIT):
    subprocess.check_call(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT)

SCOPE = pinned_json(SCOPE_PATH, "issue_packet")
ASSIGNED_IDS = set(SCOPE["member_location_ids"])
if len(ASSIGNED_IDS) != SCOPE["location_count"]:
    raise ValueError("issue scope contains duplicate or unexpected assigned IDs")
if set(MANIFEST["subject_ids"]) != ASSIGNED_IDS or len(MANIFEST["subject_ids"]) != len(ASSIGNED_IDS):
    raise ValueError("evidence manifest subject IDs differ from the pinned issue scope")
if INPUT_PINS["subject_ids_sha256"] != MANIFEST["subject_ids_sha256"]:
    raise ValueError("input-pins.json subject digest differs from the evidence manifest")


def index_unique(rows, key, context):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError(f"duplicate {context} identity: {value}")
        result[value] = row
    return result


def unique_mapping(rows, key_function, context):
    result = {}
    for row in rows:
        value = key_function(row)
        if value in result:
            raise ValueError(f"duplicate {context} identity: {value}")
        result[value] = row
    return result


def index_feature_property(rows, key, context):
    result = {}
    for row in rows:
        value = row["properties"][key]
        if value in result:
            raise ValueError(f"duplicate {context} identity: {value}")
        result[value] = row
    return result


def load_scope_features():
    """Check all current partitions for duplicate assigned IDs and exact scope."""
    world_index = pinned_json("data/world-index.json")
    found = {}
    for part in world_index["parts"]:
        path = "data/" + part
        rows = pinned_json(path)["features"]
        add_scoped_features(found, rows, ASSIGNED_IDS)
    missing = ASSIGNED_IDS - found.keys()
    extra = found.keys() - ASSIGNED_IDS
    if missing or extra or len(found) != len(ASSIGNED_IDS):
        raise ValueError(f"baseline subject inventory mismatch: missing={sorted(missing)} extra={sorted(extra)}")
    return found


def add_scoped_features(found, rows, assigned_ids):
    for feature in rows:
        ident = feature["id"]
        if ident not in assigned_ids:
            continue
        if ident in found:
            raise ValueError(f"duplicate scoped subject across baseline parts: {ident}")
        found[ident] = feature


FEATURES = load_scope_features()
HIERARCHY = index_unique(pinned_json("data/hierarchy.json"), "id", "hierarchy")


def repaired_areal(g):
    """Return an ephemeral valid polygonal clone; never mutate retained inputs."""
    candidate = make_valid(g) if not g.is_valid else g
    if not candidate.is_valid or candidate.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"unsupported geometry after validity handling: {candidate.geom_type}")
    return candidate


def metric(a, b):
    a_valid_original, b_valid_original = a.is_valid, b.is_valid
    a_fixed, b_fixed = repaired_areal(a), repaired_areal(b)
    union = a_fixed.union(b_fixed).area
    return {
        "source_area_km2": a_fixed.area / 1e6,
        "current_area_km2": b_fixed.area / 1e6,
        "relative_area_change_percent": 100 * (b_fixed.area - a_fixed.area) / a_fixed.area if a_fixed.area else None,
        "symmetric_difference_of_union_percent": 100 * a_fixed.symmetric_difference(b_fixed).area / union if union else 0,
        "source_valid_original": a_valid_original,
        "current_valid_original": b_valid_original,
        "source_repair_applied": not a_valid_original,
        "current_repair_applied": not b_valid_original,
    }


def write_candidate(name: str, value) -> None:
    if "--check-only" in sys.argv:
        print(f"check-only: validated candidate {name}; no output written")
        return
    target = HERE / name
    with target.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"created candidate {target.relative_to(ROOT)}")


def verify_manifest_inputs():
    for path in INPUT_PINS["sha256"]["geography_baseline"]:
        pinned_bytes(path, "geography_baseline")
    for path in INPUT_PINS["sha256"]["issue_packet"]:
        pinned_bytes(path, "issue_packet")


verify_manifest_inputs()
