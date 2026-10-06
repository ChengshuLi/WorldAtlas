#!/usr/bin/env python3
"""Guarded, non-destructive reproduction of the eight-county #980 screen."""
import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import transform
from shapely.validation import explain_validity

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
INPUTS = ROOT / "expected-inputs.json"
BASE = "0bf17acf0f02b7ac2e6eff3fea3171237aad0a59"
SUBJECTS = {
    "13051": ("gb:USA:ADM2:52423323B68249799438553", "Chatham"),
    "13127": ("gb:USA:ADM2:52423323B35006791438696", "Glynn"),
    "13191": ("gb:USA:ADM2:52423323B58673559392327", "McIntosh"),
    "13039": ("gb:USA:ADM2:52423323B71362647483761", "Camden"),
    "13179": ("gb:USA:ADM2:52423323B31615661575159", "Liberty"),
    "13249": ("gb:USA:ADM2:52423323B40186233786127", "Schley"),
    "13231": ("gb:USA:ADM2:52423323B93853380479562", "Pike"),
    "13273": ("gb:USA:ADM2:52423323B62158301450735", "Terrell"),
}
COASTAL = {"Chatham", "Glynn", "McIntosh", "Camden", "Liberty"}
PARENT = "framework:province:georgia:99c5fb82481b"
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform


class Refusal(RuntimeError):
    pass


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def verify_pin(path, expected_bytes, expected_sha256, actual):
    if len(actual) != expected_bytes or digest_bytes(actual) != expected_sha256:
        raise Refusal(f"changed expected source bytes: {path}")


def unique_index(records, key, label):
    """Reject duplicates before a dict can silently overwrite a record."""
    result = {}
    for record in records:
        value = str(record.get("properties", {}).get(key, ""))
        if not value:
            raise Refusal(f"{label}: missing {key}")
        if value in result:
            raise Refusal(f"{label}: duplicate {key}={value}")
        result[value] = record
    return result


def load_json(path):
    return json.loads(Path(path).read_bytes())


def verify_inputs():
    inventory = load_json(INPUTS)
    if inventory.get("schema") != "coastal-input-guards:v1" or inventory.get("verified_branch_base") != BASE:
        raise Refusal("stale or malformed expected-input inventory")
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    merge_base = subprocess.check_output(["git", "-C", str(REPO), "merge-base", head, BASE], text=True).strip()
    if merge_base != BASE:
        raise Refusal("branch does not descend from the declared fresh-main baseline")
    if subprocess.check_output(["git", "-C", str(REPO), "rev-parse", f"{BASE}^{{commit}}"], text=True).strip() != BASE:
        raise Refusal("expected baseline commit is unavailable")
    expected_ids = {f"input_{i}" for i in range(1, 58)}
    if {entry.get("id") for entry in inventory.get("inputs", [])} != expected_ids:
        raise Refusal("expected-input inventory must contain exactly the 57 issue pins")
    if len({entry.get("path") for entry in inventory["inputs"]}) != 57:
        raise Refusal("issue input pins must cover 57 distinct repository paths")
    program = inventory.get("reproduction_program", {})
    program_bytes = Path(__file__).read_bytes()
    verify_pin("reproduce.py", program.get("bytes"), program.get("sha256"), program_bytes)
    total_bytes = 0
    decoded_bytes = 0
    checked = []
    for entry in inventory["inputs"]:
        path = entry["path"]
        if path.startswith("/") or ".." in Path(path).parts:
            raise Refusal("unsafe pinned path")
        current = (REPO / path).read_bytes()
        verify_pin(path, entry["bytes"], entry["sha256"], current)
        baseline = subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASE}:{path}"])
        try:
            verify_pin(path, entry["bytes"], entry["sha256"], baseline)
        except Refusal as error:
            raise Refusal(f"baseline/registry pin mismatch: {path}")
        total_bytes += len(current)
        if path.endswith(".gz"):
            unpacked_size = len(gzip.decompress(current))
            if unpacked_size > 32 * 1024 * 1024:
                raise Refusal(f"uncompressed input exceeds per-file limit: {path}")
            decoded_bytes += unpacked_size
        checked.append({"id": entry["id"], "path": path, "bytes": len(current), "sha256": digest_bytes(current)})
    reserve = 200_000
    admitted_bytes = total_bytes + decoded_bytes + reserve
    if admitted_bytes > 256 * 1024 * 1024:
        raise Refusal(f"complete pinned/decompressed/reserve phase exceeds 256 MiB: {admitted_bytes}")
    return {"baseline": BASE, "reproduction_program_sha256": digest_bytes(program_bytes),
            "input_count": len(checked), "ordinary_input_bytes": total_bytes,
            "gzip_decoded_bytes": decoded_bytes, "reserve_bytes": reserve, "admitted_phase_bytes": admitted_bytes,
            "inputs_sha256": digest_bytes(json.dumps(checked, sort_keys=True, separators=(",", ":")).encode()),
            "verified_inputs": checked}


def ensure_roster(feature_index, expected, label):
    if set(feature_index) != set(expected):
        raise Refusal(f"{label}: missing, unexpected, or wrong scoped IDs")


def iou(a, b):
    union = a.union(b).area
    return 1.0 if not union else a.intersection(b).area / union


def create_run_dir(run_id):
    return (ROOT / "runs" / run_id).mkdir(parents=True, exist_ok=False)


def exclusive_write(path, value):
    with Path(path).open("xb") as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=False) + "\n").encode())


def compute():
    # All bytes and baseline membership are admitted before parsing/calculation.
    admission = verify_inputs()
    world_path = REPO / "data/world-index.json"
    world = load_json(world_path)
    parts = world.get("parts")
    if not isinstance(parts, list) or len(parts) != 36 or len(parts) != len(set(parts)):
        raise Refusal("stale world-index registry or unexpected part roster")
    atlas_records = []
    for part in parts:
        doc = load_json(REPO / "data" / part)
        atlas_records.extend(f for f in doc.get("features", [])
                             if f.get("properties", {}).get("id") in {v[0] for v in SUBJECTS.values()})
    atlas = unique_index(atlas_records, "id", "Atlas discovery")
    expected_atlas = {v[0] for v in SUBJECTS.values()}
    ensure_roster(atlas, expected_atlas, "Atlas discovery")

    parent = REPO / "data/regional-review/regional-review-528e53393a4376b4/source"
    source_paths = {
        2018: parent / "census-2018/georgia-kentucky-counties.geojson",
        2025: parent / "census-2025/georgia-kentucky-counties.geojson",
        2026: REPO / "data/regional-review/coastal-reference-check-428/source/census-2026/eight-counties.geojson",
    }
    county = {}
    for year, path in source_paths.items():
        fc = load_json(path)
        county[year] = unique_index(fc.get("features", []), "GEOID", f"Census {year}")
        expected = set(SUBJECTS) if year == 2026 else set(SUBJECTS)
        if year == 2026 and len(fc.get("features", [])) != 8:
            raise Refusal("2026 source must contain exactly eight source records")
        if not expected.issubset(county[year]):
            raise Refusal(f"Census {year}: scoped GEOID missing")
        if year == 2026 and set(county[year]) != expected:
            raise Refusal("Census 2026 contains unexpected scoped records")

    from scripts.evidence.geometry import VERSION as HELPER_VERSION, transform_point
    axis = transform_point(10, 45, "EPSG:3857")
    if abs(axis[0] - 1113194.9079) > 1 or abs(axis[1] - 5621521.4862) > 1:
        raise Refusal("shared helper longitude/latitude control failed")

    rows = []
    for geoid, (subject_id, name) in SUBJECTS.items():
        features = {"atlas": atlas[subject_id], **{f"tiger_{year}": county[year][geoid] for year in (2018, 2025, 2026)}}
        props = features["atlas"].get("properties", {})
        meta = props.get("metadata", {})
        if props.get("name") != name or props.get("parent_id") != PARENT:
            raise Refusal(f"Atlas name/parent mismatch: {subject_id}")
        if (meta.get("source_id"), meta.get("administrative_level"), meta.get("source_role"), meta.get("reference_year"), meta.get("original_id")) != ("gb:USA:ADM2", "ADM2", "Counties", "2018", subject_id.rsplit(":", 1)[-1]):
            raise Refusal(f"Atlas lineage/tier mismatch: {subject_id}")
        for year in (2018, 2025, 2026):
            p = features[f"tiger_{year}"].get("properties", {})
            if (p.get("STATE"), p.get("GEOID"), p.get("BASENAME"), p.get("LSADC")) != ("13", geoid, name, "06"):
                raise Refusal(f"Census county tier/code/name mismatch: {year}/{geoid}")
        geoms = {k: shape(v["geometry"]) for k, v in features.items()}
        validity = {k: {"valid": g.is_valid, "reason": explain_validity(g)} for k, g in geoms.items()}
        repaired = {k: (g if g.is_valid else make_valid(g)) for k, g in geoms.items()}
        projected = {k: transform(PROJECT, g) for k, g in repaired.items()}
        rows.append({
            "geoid": geoid, "subject_id": subject_id, "name": name,
            "atlas_attributes": {"name": props.get("name"), "parent_id": props.get("parent_id"), "source_id": meta.get("source_id"), "source_role": meta.get("source_role"), "administrative_level": meta.get("administrative_level"), "reference_year": meta.get("reference_year"), "source_shape_id": meta.get("original_id")},
            "source_attributes": {f"tiger_{year}": {key: features[f"tiger_{year}"].get("properties", {}).get(key) for key in ["GEOID", "STATE", "COUNTY", "NAME", "BASENAME", "LSADC", "FUNCSTAT", "COUNTYNS", "AREALAND", "AREAWATER"]} for year in (2018, 2025, 2026)},
            "validity": validity,
            "components": {k: len(g.geoms) if g.geom_type == "MultiPolygon" else (1 if g.geom_type == "Polygon" else 0) for k, g in geoms.items()},
            "equal_area_area_km2": {k: round(g.area / 1e6, 3) for k, g in projected.items()},
            "atlas_2018_2026_difference_km2": {
                "atlas_minus_tiger_2026": round(projected["atlas"].difference(projected["tiger_2026"]).area / 1e6, 3),
                "tiger_minus_atlas": round(projected["tiger_2026"].difference(projected["atlas"]).area / 1e6, 3),
                "tiger_minus_atlas_as_share_of_census_areawater": round(projected["tiger_2026"].difference(projected["atlas"]).area / features["tiger_2026"]["properties"]["AREAWATER"], 6)},
            "iou": {f"{a}_to_{b}": round(iou(projected[a], projected[b]), 9) for a, b in [("atlas", "tiger_2018"), ("atlas", "tiger_2025"), ("atlas", "tiger_2026"), ("tiger_2018", "tiger_2025"), ("tiger_2025", "tiger_2026")]},
            "interpretation": "IoU is a repeatable statistical geometry screen only; repaired geometries exist in memory only; neither validates legal lines or proves coastal completeness."})

    if len(rows) != 8 or {r["subject_id"] for r in rows} != expected_atlas:
        raise Refusal("computed roster differs from exact eight issue subjects")
    coastal_values = {r["name"]: r["iou"]["tiger_2025_to_tiger_2026"] for r in rows if r["name"] in COASTAL}
    if set(coastal_values) != COASTAL or any(v != 1.0 for v in coastal_values.values()):
        raise Refusal("positive unchanged-coastal comparator failed")
    right = PROJECT(10, 45)
    wrong = PROJECT(45, 10)
    separation = ((wrong[0]-right[0])**2 + (wrong[1]-right[1])**2) ** .5
    if separation < 1_000_000:
        raise Refusal("swapped-axis negative measurement control failed")
    source_hashes = {str(path.relative_to(REPO)): digest_bytes(path.read_bytes()) for path in source_paths.values()}
    return admission, {"baseline": BASE, "projection": "EPSG:6933; always_xy; lon/lat source",
        "shared_helper_version": HELPER_VERSION, "shared_helper_axis_control_EPSG3857_lon10_lat45_m": list(axis),
        "scope_count": len(rows), "source_hashes": source_hashes, "rows": rows}, {
        "method_id": "coastal-comparison-guarded-screen", "kind": "positive-control", "outcome": "passed",
        "description": "The five coastal 2025-to-2026 retained geometry pairs remain identical (IoU 1.0).", "observed_iou": coastal_values}, {
        "method_id": "coastal-comparison-guarded-screen", "kind": "negative-control", "outcome": "passed",
        "description": "Swapped longitude/latitude axis order is rejected by a >1,000 km projected-coordinate separation.",
        "correct_xy_m": [round(v, 6) for v in right], "swapped_xy_m": [round(v, 6) for v in wrong], "separation_m": round(separation, 3)}


def run_controls():
    # Exercise the same admission functions used by the reproduction with actual
    # malformed fixture records, a changed expected pin and an occupied output.
    features = [{"properties": {"GEOID": f"130{i:02d}"}} for i in range(1, 9)]
    features.append({"properties": {"GEOID": "13001"}})
    for label, records, key in [
        ("duplicate ninth county", features, "GEOID"),
        ("duplicate Atlas ID", [{"properties": {"id": "same"}}, {"properties": {"id": "same"}}], "id")]:
        try:
            unique_index(records, key, label)
        except Refusal:
            pass
        else:
            raise Refusal(f"negative control failed to reject {label}")
    try:
        ensure_roster({"wrong": {}}, {"expected"}, "wrong scoped ID")
    except Refusal:
        pass
    else:
        raise Refusal("negative control failed to reject wrong scoped ID")
    pin = {"bytes": 1, "sha256": "0" * 64}
    try:
        verify_pin("fixture", pin["bytes"], pin["sha256"], b"x")
    except Refusal:
        pass
    else:
        raise Refusal("altered-source-pin negative control failed")
    # A fresh exclusive output writer must refuse any existing path.
    path = ROOT / "runs" / ".existing-output-control"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    try:
        try:
            create_run_dir(".existing-output-control")
            raise AssertionError("existing output directory was accepted")
        except FileExistsError:
            pass
    finally:
        path.rmdir()
    return {"duplicate_ninth_county": "rejected-before-indexing", "duplicate_atlas_id": "rejected-before-indexing",
            "wrong_scoped_id": "rejected-by-exact-roster-check", "altered_source_pin": "rejected-by-size-and-sha256-preflight",
            "existing_output": "rejected-by-exclusive-create"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", choices=["run-one", "run-two"])
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    if args.controls_only:
        print(json.dumps(run_controls(), indent=2, sort_keys=True))
        return
    if not args.run_id:
        parser.error("--run-id is required; every output vintage is exclusive")
    out = ROOT / "runs" / args.run_id
    create_run_dir(args.run_id)
    admission, result, positive, negative = compute()
    files = {
        "admission.json": admission,
        "eight-county-comparison.json": result,
        "positive-control.json": positive,
        "negative-control.json": negative,
    }
    for name, value in files.items():
        exclusive_write(out / name, value)
    print(json.dumps({name: digest_bytes((out / name).read_bytes()) for name in files}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Refusal as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        sys.exit(2)
