#!/usr/bin/env python3
"""Bounded 20-ID source-fit and current-neighbor check for issue #1629.

Only ten uniquely covering land-support candidates are overlaid. The seven
mixed, two contact-only, and one inland-water-supported cases remain unknown.
All coordinates are treated literally as lon/lat; no snapping, buffers,
precision changes, repair, or legal/administrative claims are made.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import pathlib
import platform
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone

from shapely.geometry import shape
from shapely import geos_version_string, __version__ as shapely_version

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/central-africa-20-source-fit-20261009"
INPUT = PACKET / "inputs"
OUTPUT = PACKET / "results"
OUTPUT.mkdir(exist_ok=True)
EXPECTED_COUNTRY_PARTS = {
    "CAF": 2, "COD": 5, "COG": 5, "TCD": 23, "AGO": 29,
}
COUNTRY_SOURCE_FILE = {
    "CAF": "geoBoundaries-CAF-ADM3_simplified.geojson",
    "COG": "geoBoundaries-COG-ADM2_simplified.geojson",
    "AGO": "geoBoundaries-AGO-ADM2_simplified.geojson",
    "TCD": "geoBoundaries-TCD-ADM2_simplified.geojson",
}
WATER_EXCEPTION = "physical-component:8f72e31d2921dd094f271cff3e9b37093fcaeb002651d941a9ffcd9ce15e4b4e"
EXPECTED_SOURCE_SHA = {
    "CAF": "e368afac2f5c1ac7503a181e3e62541df88167cf9072a84c5453ffea999ee88a",
    "COG": "b44d1fdcc6f61f0d0b2a4b3402f49dfd317ea9cdddd0a854bd20cae0996291ae",
    "AGO": "7cf2a401b36480f7c22d9783e4364d3eb93c3ac643e2d34778b1ce059c786dcf",
    "TCD": "b8178a45b9a2060889181f75d2754395bba9d165ff06a9fac33c9f3ca45f7e99",
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def feature_hash(feature) -> str:
    return sha(canonical(feature))


def geom_hash(geom) -> str:
    # Geometry identity is pinned to the exact source GeoJSON pointset.
    return sha(canonical(geom))


def read_gzip_json(path: pathlib.Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def row_country(stable_id: str) -> str:
    return stable_id.split(":")[1]


def map_feature_id(f):
    return f.get("properties", {}).get("id")


def main():
    started = time.time()
    preflight = subprocess.check_output(
        ["/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
         str(ROOT / "scripts/local-workspace.mjs"), "check"], text=True
    )
    pressure = subprocess.run(["memory_pressure", "-Q"], text=True, capture_output=True)
    assert pressure.returncode == 0, pressure.stderr
    assert json.loads(preflight)["freeBytes"] >= 10 * 1024**3

    components_path = INPUT / "components/selected-20-components.json.gz"
    comparisons_path = INPUT / "source-comparisons/selected-20-source-comparison-rows.json.gz"
    components_doc = read_gzip_json(components_path)
    comparisons_doc = read_gzip_json(comparisons_path)
    components = {f["id"]: f for f in components_doc["features"]}
    rows = {r["component_id"]: r["source_comparison_row"] for r in comparisons_doc["rows"]}
    assert len(components) == len(rows) == 20
    assert set(components) == set(rows)

    source_bytes, sources = {}, {}
    for country, filename in COUNTRY_SOURCE_FILE.items():
        p = INPUT / "sources" / filename
        b = p.read_bytes()
        assert sha(b) == EXPECTED_SOURCE_SHA[country], (country, sha(b))
        source_bytes[country] = {"path": str(p.relative_to(ROOT)), "bytes": len(b), "sha256": sha(b)}
        fc = json.loads(b)
        sources[country] = fc["features"]

    map_docs, map_features, map_part_pins = {}, [], []
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for country, partnum in EXPECTED_COUNTRY_PARTS.items():
        path = f"data/geography/part-{partnum}.json"
        file = INPUT / "current-map" / f"part-{partnum}.json"
        b = file.read_bytes()
        git_b = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
        oid = subprocess.check_output(["git", "rev-parse", f"{commit}:{path}"], cwd=ROOT, text=True).strip()
        assert b == git_b, path
        doc = json.loads(b)
        map_docs[partnum] = doc
        country_features = [f for f in doc["features"] if map_feature_id(f,).startswith(f"gb:{country}:")]
        assert country_features, (country, partnum)
        map_features.extend(country_features)
        map_part_pins.append({"country": country, "path": path, "commit": commit, "blob_oid": oid,
                              "bytes": len(b), "sha256": sha(b), "country_feature_count": len(country_features)})
    assert len({map_feature_id(f) for f in map_features}) == len(map_features)

    # Construct stable IDs and source-feature lookup before overlay operations.
    source_lookup = {}
    for country, feats in sources.items():
        for f in feats:
            props = f.get("properties", {})
            if props.get("shapeID"):
                source_lookup[(country, props["shapeID"])] = f
    map_by_id = {map_feature_id(f): f for f in map_features}
    target_map_ids = {
        "gb:CAF:ADM3:52401652B84569563404367",
        "gb:COG:ADM2:1427508B96128266527522",
    }
    assert target_map_ids <= map_by_id.keys()

    ids = sorted(components)
    unique = [cid for cid, r in rows.items() if r["status"] == "one-compatible-recorded-subject-uniquely-covers-component"]
    assert len(unique) == 11 and WATER_EXCEPTION in unique
    eligible = [cid for cid in unique if cid != WATER_EXCEPTION]
    assert len(eligible) == 10

    neighbor_universe = []
    for f in map_features:
        g = shape(f["geometry"])
        neighbor_universe.append({"id": map_feature_id(f), "feature_sha256": feature_hash(f),
                                  "geometry_sha256": geom_hash(f["geometry"]),
                                  "bbox": list(g.bounds), "valid": g.is_valid})

    decisions = {}
    for cid in ids:
        r = rows[cid]
        if cid in eligible:
            decisions[cid] = {"prior_source_status": r["status"], "fit_status": "pending"}
        elif cid == WATER_EXCEPTION:
            decisions[cid] = {"prior_source_status": r["status"], "fit_status": "unknown", "reason": "retained inland-water-support exception; do not propose land repair"}
        else:
            reason = ("retained evidence is zero-area contact-only; no positive-area source coverage"
                      if r["status"] == "zero-area-contact-only" else
                      "retained source coverage is mixed/partial or lacks a unique compatible subject")
            decisions[cid] = {"prior_source_status": r["status"], "fit_status": "unknown", "reason": reason}

    output = []
    for cid in eligible:
        old = rows[cid]
        subject = old["uniquely_covering_compatible_recorded_subject"]
        stable_id = subject["id"]
        country = row_country(stable_id)
        shape_id = stable_id.rsplit(":", 1)[1]
        assert country in COUNTRY_SOURCE_FILE, (cid, country)
        sf = source_lookup[(country, shape_id)]
        assert sf["properties"]["shapeID"] == shape_id
        sg = shape(sf["geometry"])
        cf = components[cid]
        cg = shape(cf["geometry"])
        assert sg.is_valid and cg.is_valid and not sg.is_empty and not cg.is_empty
        source_covers = sg.covers(cg)
        # Compare against every feature in the exact source country product.
        source_hits = []
        for f in sources[country]:
            g = shape(f["geometry"])
            if g.is_valid and g.intersects(cg):
                inter = g.intersection(cg)
                if inter.area > 0:
                    source_hits.append({"shapeID": f["properties"].get("shapeID"), "positive_area": True,
                                        "intersection_area_degrees2": inter.area})

        target = map_by_id[stable_id]
        tg = shape(target["geometry"])
        assert tg.is_valid and cg.is_valid
        already_covered = tg.covers(cg)
        target_intersection_area = tg.intersection(cg).area
        after = tg.union(cg)
        gain = after.difference(tg)
        target_loss = tg.difference(after)
        exact_gain = gain.symmetric_difference(cg).area == 0.0
        no_loss = target_loss.area == 0.0
        neighbor_hits = []
        neighbor_evaluations = []
        for nf in map_features:
            nid = map_feature_id(nf)
            if nid == stable_id:
                continue
            ng = shape(nf["geometry"])
            if not ng.is_valid:
                continue
            # Bind the entire affected-neighbor envelope, then evaluate the
            # exact predicate for each envelope candidate. Disjoint features
            # outside the candidate envelope are covered by the universe hash.
            bx0, by0, bx1, by1 = ng.bounds
            cx0, cy0, cx1, cy1 = cg.bounds
            bbox_candidate = not (bx1 < cx0 or bx0 > cx1 or by1 < cy0 or by0 > cy1)
            if bbox_candidate:
                inter = ng.intersection(cg)
                evaluation = {"id": nid, "feature_sha256": feature_hash(nf),
                              "geometry_sha256": geom_hash(nf["geometry"]),
                              "intersects": ng.intersects(cg), "intersection_area_degrees2": inter.area,
                              "relation": "positive-area" if inter.area > 0 else ("touches" if ng.intersects(cg) else "bbox-only")}
                neighbor_evaluations.append(evaluation)
                if inter.area > 0:
                    neighbor_hits.append(evaluation)

        conditions = {
            "simplified_source_target_covers_component": source_covers,
            "only_source_target_has_positive_area_hit": bool(source_hits) and all(h["shapeID"] == shape_id for h in source_hits),
            "current_target_missing_component": not already_covered,
            "current_target_union_has_zero_loss": no_loss,
            "current_target_union_gain_equals_component": exact_gain,
            "no_positive_area_overlap_with_other_current_five_country_features": not neighbor_hits,
        }
        passed = all(conditions.values())
        failed = [name for name, value in conditions.items() if not value]
        decisions[cid] = {"prior_source_status": old["status"], "fit_status": "pass" if passed else "refused",
                          "target_id": stable_id, "conditions": conditions,
                          "failed_predicates": failed,
                          "reason": "all bounded source/map overlays pass" if passed else "; ".join(failed)}
        output.append({
            "component_id": cid,
            "component_full_feature_sha256": sha(canonical(cf)),
            "component_geometry_sha256": geom_hash(cf["geometry"]),
            "component_bbox": list(cg.bounds),
            "component_area_degrees2": cg.area,
            "source_product": source_bytes[country],
            "source_target": {"id": stable_id, "shapeID": shape_id, "feature_sha256": feature_hash(sf),
                              "geometry_sha256": geom_hash(sf["geometry"]), "source_covers_component": source_covers,
                              "positive_area_source_hits": source_hits},
            "current_target": {"part": EXPECTED_COUNTRY_PARTS[country], "id": stable_id,
                               "feature_sha256": feature_hash(target), "geometry_sha256": geom_hash(target["geometry"]),
                               "already_covers_component": already_covered,
                               "intersection_area_degrees2": target_intersection_area,
                               "gain_area_degrees2": gain.area, "loss_area_degrees2": target_loss.area,
                               "gain_component_symmetric_difference_area_degrees2": gain.symmetric_difference(cg).area,
                               "exact_gain_equals_component": exact_gain},
            "current_neighbor_positive_area_hits": neighbor_hits,
            "current_neighbor_envelope_evaluations": neighbor_evaluations,
            "current_neighbor_universe_count": len(neighbor_universe),
            "conditions": conditions,
            "proposal_eligible": passed,
            "limits": ["diagnostic geometry only; no land/water truth, rightful province, or historical ownership established",
                       "geoBoundaries year/role/license remain source metadata, not legal authority",
                       "source relative fit only; no snapping, tolerance, repair, or datum transformation"],
        })

    result = {
        "schema": "central-africa-20-simplified-source-fit-v1",
        "issue": 1629,
        "batch_id": "09022872285309274891eb98",
        "baseline_commit": commit,
        "started_at_utc": datetime.fromtimestamp(started, timezone.utc).isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "shapely": shapely_version, "geos": geos_version_string,
        "bounded_scope": {"roster_ids": len(ids), "overlaid_ids": len(eligible), "country_codes": sorted(EXPECTED_COUNTRY_PARTS),
                          "target_countries": ["CAF", "COG"], "country_map_feature_count": len(map_features),
                          "map_part_pins": map_part_pins, "complete_neighbor_universe_sha256": sha(canonical(neighbor_universe)),
                          "complete_neighbor_universe": neighbor_universe},
        "preflight": {"local_workspace_check": json.loads(preflight), "memory_pressure": pressure.stdout,
                      "source_file_bytes": sum(v["bytes"] for v in source_bytes.values()),
                      "map_part_bytes": sum(r["bytes"] for r in map_part_pins)},
        "roster": [{"component_id": cid, **decisions[cid]} for cid in ids],
        "fit_rows": output,
        "fit_pass_count": sum(1 for row in output if row["proposal_eligible"]),
        "fit_refusal_count": sum(1 for row in output if not row["proposal_eligible"]),
        "unknown_count": sum(1 for row in decisions.values() if row["fit_status"] == "unknown"),
        "gshhg_custody": {"path": "research/geography/central-africa-20-source-fit-20261009/gshhg-custody.json",
                          "note": "retained native GSHHG records were selected by source-record bounding boxes only; no geometry operation or land/water inference"},
        "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "method": "literal GeoJSON coordinates; Shapely/GEOS exact predicates and set operations; no precision changes or repairs",
        "limitations": ["Cause and physical surface class remain unknown for all 20 candidates.",
                        "This does not establish legal title, historical boundary truth, or release readiness.",
                        "Only additive proposals that pass every listed condition can be considered; no core map data changed."],
    }
    result_path = OUTPUT / "simplified-source-fit.json"
    raw = json.dumps(result, indent=2, ensure_ascii=False).encode() + b"\n"
    result_path.write_bytes(raw)
    print(json.dumps({"result": str(result_path), "sha256": sha(raw), "roster": len(ids),
                      "overlays": len(output), "passed": sum(x["proposal_eligible"] for x in output),
                      "refused": sum(not x["proposal_eligible"] for x in output),
                      "peak_rss_bytes": result["process_peak_rss_bytes"],
                      "conditions": {cid: row["conditions"] for cid, row in zip(eligible, output)}}, indent=2))


if __name__ == "__main__":
    main()
