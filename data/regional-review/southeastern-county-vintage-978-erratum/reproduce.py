#!/usr/bin/env python3
"""Immutable, offline reproduction for the exact six #1252 county subjects."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OWNED = "data/regional-review/southeastern-county-vintage-978-erratum/"
PACKET = ROOT / OWNED
INVENTORY = PACKET / "baseline-inventory.json"
BASELINE_COMMIT = "a1cf4cd86fd07d00ae592b4705e4b39f50628df7"
EXPECTED_RUNTIME = ("3.12.14", "2.1.2", "3.7.2")
STATE_LAYER_PATHS = {
    "01": "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-tigerweb-acs26/counties-state-01.geojson",
    "28": "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-tigerweb-acs26/counties-state-28.geojson",
    "47": "data/regional-review/regional-review-599d6fe712bbbcae/sources/census-tigerweb-acs26/counties-state-47.geojson",
}
ATLAS_PARTS = ["data/geography/part-25.json", "data/geography/part-26.json", "data/geography/part-27.json"]
CROSSWALK = "data/regional-review/regional-review-599d6fe712bbbcae/findings/usa-county-crosswalk.csv"
GEOB = "data/regional-review/regional-review-599d6fe712bbbcae/sources/geoboundaries-2018/geoBoundaries-USA-ADM2.geojson"
SUBJECTS = {
    "gb:USA:ADM2:52423323B10934602069357": {"name": "Jackson", "geoid": "28059", "state": "28", "part": "26"},
    "gb:USA:ADM2:52423323B16895111765374": {"name": "Moore", "geoid": "47127", "state": "47", "part": "26"},
    "gb:USA:ADM2:52423323B27952664457255": {"name": "Harrison", "geoid": "28047", "state": "28", "part": "26"},
    "gb:USA:ADM2:52423323B49198903326940": {"name": "Hancock", "geoid": "28045", "state": "28", "part": "27"},
    "gb:USA:ADM2:52423323B60515004813393": {"name": "Baldwin", "geoid": "01003", "state": "01", "part": "25"},
    "gb:USA:ADM2:52423323B65626355292212": {"name": "Mobile", "geoid": "01097", "state": "01", "part": "26"},
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def unique_index(rows, key, label):
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Missing {label} identity")
        if value in result:
            raise ValueError(f"Duplicate {label} identity: {value}")
        result[value] = row
    return result


def exact_roster(found, expected, label):
    if set(found) != set(expected):
        raise ValueError(f"{label} roster mismatch; missing={sorted(set(expected) - set(found))}; extra={sorted(set(found) - set(expected))}")


def geometry_summary(feature, shape, explain_validity):
    geometry = shape(feature["geometry"])
    pieces = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
    return {
        "type": geometry.geom_type,
        "valid": bool(geometry.is_valid),
        "validity_reason": explain_validity(geometry),
        "empty": bool(geometry.is_empty),
        "bounds_epsg4326": list(geometry.bounds),
        "components": len(pieces),
        "holes": sum(len(part.interiors) for part in pieces),
        "vertices": sum(len(part.exterior.coords) + sum(len(hole.coords) for hole in part.interiors) for part in pieces),
        "area_degrees2_diagnostic_only": geometry.area,
    }, geometry


def exclusive_write(root: Path, relative: str, raw: bytes, owned_root: str = OWNED) -> Path:
    """Exclusive output under the declared owned prefix; no overwrite or symlink traversal."""
    if not isinstance(relative, str) or "\\" in relative or "\0" in relative or Path(relative).is_absolute():
        raise ValueError("Unsafe output path")
    if any(part in ("", ".", "..") for part in relative.split("/")):
        raise ValueError("Unsafe output path")
    if not relative.startswith(owned_root) or relative == owned_root.rstrip("/"):
        raise ValueError("Output outside the declared owned prefix")
    target = root / relative
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink in output path")
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(target, flags, 0o644)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def run(baseline, *, Shapely, pyproj, vintage, expected_runner_hash):
    from shapely.geometry import shape
    from shapely.ops import transform
    from shapely.validation import explain_validity
    from pyproj import Transformer

    if (sys.version.split()[0], Shapely.__version__, pyproj.__version__) != EXPECTED_RUNTIME:
        raise RuntimeError("Pinned Python/Shapely/pyproj runtime mismatch")
    # Read every file descriptor before parsing; Baseline validated all 26 original
    # #1162 descriptors plus the shared immutable-read helper at exact baseline.
    atlas_by_id = {}
    for path in ATLAS_PARTS:
        part = Path(path).stem.removeprefix("part-")
        features = json.loads(baseline.read(path))["features"]
        for feature in features:
            ident = feature.get("id") or feature.get("properties", {}).get("id")
            if ident in SUBJECTS:
                if ident in atlas_by_id:
                    raise ValueError(f"Duplicate Atlas subject across parts: {ident}")
                if part != SUBJECTS[ident]["part"]:
                    raise ValueError(f"Atlas subject in wrong pinned part: {ident}")
                atlas_by_id[ident] = feature
    exact_roster(atlas_by_id, SUBJECTS, "Atlas")

    geob_features = json.loads(baseline.read(GEOB))["features"]
    # GeoBoundaries source identity is properties.shapeID; assert uniqueness directly.
    geob_by_id = {}
    for feature in geob_features:
        ident = feature.get("properties", {}).get("shapeID")
        if not ident or ident in geob_by_id:
            raise ValueError(f"Missing or duplicate geoBoundaries shapeID: {ident}")
        geob_by_id[ident] = feature

    census = {}
    rosters = {}
    for state, path in STATE_LAYER_PATHS.items():
        features = json.loads(baseline.read(path))["features"]
        properties = [feature.get("properties", {}) for feature in features]
        roster = unique_index(properties, "GEOID", f"Census {state} GEOID")
        rosters[state] = len(roster)
        for geoid, row in roster.items():
            if row.get("STATE") != state:
                raise ValueError(f"Census GEOID does not match state response: {geoid}")
            census[geoid] = row
    expected_rosters = {"01": 67, "28": 82, "47": 95}
    if rosters != expected_rosters:
        raise ValueError(f"Unexpected complete-state roster counts: {rosters}")

    crosswalk_rows = list(csv.DictReader(baseline.read(CROSSWALK).decode("utf-8-sig").splitlines()))
    crosswalk_by_id = unique_index(crosswalk_rows, "atlas_id", "crosswalk Atlas")
    metadata = json.loads(baseline.read("data/regional-review/regional-review-599d6fe712bbbcae/sources/census-tigerweb-acs26/layer-82-metadata-20261005.json"))
    layer_text = json.dumps(metadata, sort_keys=True)
    if "January 1, 2026" not in layer_text and "2026-01-01" not in layer_text:
        raise ValueError("Pinned TIGERweb metadata does not support January 1, 2026 vintage")

    to5070 = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True).transform
    audit = []
    for ident, expected in SUBJECTS.items():
        atlas = atlas_by_id[ident]
        geob = geob_by_id.get(ident.rsplit(":", 1)[1])
        row = census.get(expected["geoid"])
        xwalk = crosswalk_by_id.get(ident)
        if not geob or not row or not xwalk:
            raise ValueError(f"Missing unique source/parent join for {ident}")
        if geob.get("properties", {}).get("shapeName") != expected["name"]:
            raise ValueError(f"geoBoundaries name mismatch: {ident}")
        if atlas.get("properties", {}).get("name") != expected["name"]:
            raise ValueError(f"Atlas name mismatch: {ident}")
        if (row.get("GEOID"), row.get("STATE"), row.get("NAME"), row.get("LSADC")) != (
            expected["geoid"], expected["state"], expected["name"] + " County", "06"
        ):
            raise ValueError(f"Census subject identity mismatch: {ident}")
        if row.get("COUNTY") != expected["geoid"][2:] or xwalk.get("geoid_2018_and_2026") != expected["geoid"]:
            raise ValueError(f"County FIPS/GEOID mismatch: {ident}")
        if atlas.get("properties", {}).get("parent_id") != xwalk.get("parent_id"):
            raise ValueError(f"Atlas parent differs from pinned crosswalk: {ident}")

        atlas_summary, atlas_geom = geometry_summary(atlas, shape, explain_validity)
        source_summary, source_geom = geometry_summary(geob, shape, explain_validity)
        census_feature = next(f for f in json.loads(baseline.read(STATE_LAYER_PATHS[expected["state"]]))["features"] if f.get("properties", {}).get("GEOID") == expected["geoid"])
        census_summary, census_geom = geometry_summary(census_feature, shape, explain_validity)
        for label, summary in (("Atlas", atlas_summary), ("geoBoundaries", source_summary), ("TIGERweb", census_summary)):
            if summary["empty"] or not summary["valid"] or summary["type"] not in ("Polygon", "MultiPolygon"):
                raise ValueError(f"{label} native geometry invalid for {ident}: {summary['validity_reason']}")
        projected_source = transform(to5070, source_geom)
        projected_census = transform(to5070, census_geom)
        reproduced_iou = projected_source.intersection(projected_census).area / projected_source.union(projected_census).area
        prior_2018 = float(xwalk["2018_cb_iou"])
        prior_2026 = float(xwalk["2026_tiger_iou"])
        if round(reproduced_iou, 8) != round(prior_2026, 8):
            raise ValueError(f"Fresh TIGERweb IoU fails to reproduce #1162 archived result: {ident}")
        audit.append({
            "id": ident, "name": expected["name"], "geoid": expected["geoid"], "state_fips": expected["state"],
            "atlas_parent_id": atlas["properties"]["parent_id"], "source_join": "unique GEOID + STATE + county name + LSADC within complete state layer",
            "archived_2018_cbf_iou": prior_2018, "archived_2026_tigerweb_iou": prior_2026,
            "reproduced_2026_tigerweb_iou": reproduced_iou,
            "matches_archived_2026_iou_at_8dp": True,
            "atlas": atlas_summary, "geoboundaries_2018": source_summary, "tigerweb_2026": census_summary,
            "baseline_crosswalk_parent_id": xwalk["parent_id"],
        })

    result = {
        "version": 1,
        "issue": 1252,
        "scope": "exactly the six subjects declared by issue #1252; no neighboring-region certification",
        "baseline_commit": baseline.commit,
        "runner_sha256": expected_runner_hash,
        "source_vintage": "geoBoundaries boundaryYear 2018; Census TIGERweb layer 82 January 1, 2026; original retrievals October 5, 2026 UTC",
        "runtime": {"python": sys.version.split()[0], "shapely": Shapely.__version__, "geos": Shapely.geos_version_string, "pyproj": pyproj.__version__},
        "roster_counts_by_state_fips": rosters,
        "geometry_method": "Validity and component summaries in native EPSG:4326 without repair; reproducibility IoU transforms valid geoBoundaries and TIGERweb coordinates to EPSG:5070 with pyproj always_xy and computes intersection / union. No legal boundary inference.",
        "sources_and_limits": [
            "geoBoundaries metadata describes 2018 Census MAF/TIGER cartographic lineage; generated-product CC BY 4.0 attribution and underlying Public Domain are distinct statements.",
            "Census 2018 1:500,000 cartographic geometry is generalized and may omit small holes, discontiguous pieces, or offshore extents.",
            "TIGERweb is a Census statistical representation; the retained 2025 TIGER/Line legal disclaimer is not a legal determination for a 2026 service feature.",
            "No current Census-host reauthentication; legal coastline, islands/offshore completeness, causal attribution, and exact county boundary correctness remain unresolved.",
        ],
        "subjects": audit,
        "status": "reproduced bounded evidence; no geographic approval or correction proposed",
    }
    raw = (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    target = f"{OWNED}vintages/{vintage}/native-geometry-audit.json"
    exclusive_write(ROOT, target, raw)
    return result, sha256(raw), target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("--inventory-sha256", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"2026-10-07-[a-d]", args.vintage):
        raise SystemExit("Use one of the four reserved additive run vintages: 2026-10-07-a through -d")
    own_bytes = Path(__file__).read_bytes()
    if sha256(own_bytes) != args.runner_sha256:
        raise SystemExit("Executed runner hash differs from the explicit reviewed pin")
    inventory_bytes = INVENTORY.read_bytes()
    if sha256(inventory_bytes) != args.inventory_sha256:
        raise SystemExit("Baseline inventory hash differs from the explicit reviewed pin")
    inventory = json.loads(inventory_bytes)
    if inventory.get("commit") != BASELINE_COMMIT or inventory.get("issue") != 1252:
        raise SystemExit("Unexpected immutable baseline inventory")
    sys.path.insert(0, str(ROOT))
    from scripts.evidence.immutable import Baseline
    helper_path = ROOT / "scripts/evidence/immutable.py"
    helper_expected = next((f for f in inventory["files"] if f["path"] == "scripts/evidence/immutable.py"), None)
    if not helper_expected or sha256(helper_path.read_bytes()) != helper_expected["sha256"]:
        raise SystemExit("Immutable reader code differs from exact baseline pin")
    baseline = Baseline(ROOT, inventory["commit"], inventory["files"])
    import shapely
    import pyproj
    result, digest, path = run(baseline, Shapely=shapely, pyproj=pyproj, vintage=args.vintage, expected_runner_hash=args.runner_sha256)
    print(json.dumps({"path": path, "sha256": digest, "subjects": len(result["subjects"]), "rosters": result["roster_counts_by_state_fips"]}, sort_keys=True))


if __name__ == "__main__":
    main()
