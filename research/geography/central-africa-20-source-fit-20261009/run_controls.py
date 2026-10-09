#!/usr/bin/env python3
"""Produce positive and negative method controls for the bounded fit."""
import hashlib
import json
import pathlib

from shapely.geometry import shape

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/central-africa-20-source-fit-20261009"
METHOD = "simplified-source-fit"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write(name, value):
    p = PACKET / "controls" / name
    p.parent.mkdir(exist_ok=True)
    raw = json.dumps(value, indent=2).encode() + b"\n"
    p.write_bytes(raw)
    return {"path": str(p.relative_to(ROOT)), "sha256": sha(raw), "bytes": len(raw)}


def main():
    fit_path = PACKET / "results/simplified-source-fit.json"
    fit_raw = fit_path.read_bytes()
    fit = json.loads(fit_raw)
    components_path = PACKET / "inputs/components/selected-20-components.json.gz"
    import gzip
    components = {f["id"]: f for f in json.load(gzip.open(components_path, "rt"))["features"]}
    good = next(r for r in fit["fit_rows"] if r["proposal_eligible"])
    positive = {
        "method_id": METHOD, "kind": "positive-control", "outcome": "passed",
        "control": "known exact source-supported additive candidate remains admitted",
        "fit_result": {"path": str(fit_path.relative_to(ROOT)), "sha256": sha(fit_raw)},
        "component_id": good["component_id"], "target_id": good["current_target"]["id"],
        "source_target_id": good["source_target"]["id"],
        "conditions": good["conditions"],
        "assertion": bool(good["proposal_eligible"] and all(good["conditions"].values())),
    }
    assert positive["assertion"]
    positive_file = write("positive-control.json", positive)

    candidate = components[good["component_id"]]
    source_file = PACKET / "inputs/sources/geoBoundaries-COG-ADM2_simplified.geojson"
    source_doc = json.loads(source_file.read_bytes())
    expected_shape = good["source_target"]["shapeID"]
    wrong = next(f for f in source_doc["features"] if f["properties"].get("shapeID") != expected_shape)
    wrong_geom = shape(wrong["geometry"])
    candidate_geom = shape(candidate["geometry"])
    wrong_covers = wrong_geom.covers(candidate_geom)
    negative = {
        "method_id": METHOD, "kind": "negative-control", "outcome": "passed" if not wrong_covers else "failed",
        "control": "foreign source feature cannot satisfy the exact candidate-to-source identity/coverage predicate",
        "component_id": good["component_id"], "expected_source_shapeID": expected_shape,
        "wrong_source_shapeID": wrong["properties"]["shapeID"],
        "wrong_source_feature_sha256": sha(json.dumps(wrong, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()),
        "wrong_source_covers_component": wrong_covers,
        "component_geometry_sha256": good["component_geometry_sha256"],
        "assertion": not wrong_covers,
        "limit": "negative identity/coverage control only; does not establish physical class or source truth",
    }
    assert negative["assertion"]
    negative_file = write("negative-control.json", negative)
    print(json.dumps({"positive": positive_file, "negative": negative_file}, indent=2))


if __name__ == "__main__":
    main()
