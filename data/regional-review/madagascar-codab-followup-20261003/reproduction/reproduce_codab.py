#!/usr/bin/env python3
"""Reproduce an additive Madagascar COD-AB crosswalk from immutable Git inputs.

All inputs are read as blobs from the recorded PR-base commit. Output is written
only to a new, caller-named vintage beneath the issue-owned directory. Existing
or partial output is never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import pathlib
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict

from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

BASE = "b765c34077b6d7c5745c7285f08e954edd62144a"
PARENT = "data/regional-review/regional-review-4f180b98473f1071/"
OWNED = pathlib.Path(__file__).resolve().parents[1]
INPUT_PATHS = [
    "data/world-index.json",
    "data/geography/part-13.json",
    "data/hierarchy.json",
    PARENT + "issue-scope.json",
    PARENT + "sources.json",
    PARENT + "sources/mdg-COD-AB-ADM2-2026-reviewed.geojson.gz",
    PARENT + "sources/mdg-COD-AB-ADM1-2026-reviewed.geojson.gz",
    PARENT + "sources/mdg_admpop_adm2_2018.csv",
    PARENT + "sources/mdg_admpop_adm3_2018.csv",
    PARENT + "sources/mdg_admpop_adm4_2018.csv",
]
TRANSFORM = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
THRESHOLD = 5.0


def git_blob(repo: pathlib.Path, path: str) -> tuple[bytes, str]:
    spec = f"{BASE}:{path}"
    blob = subprocess.run(["git", "show", spec], cwd=repo, check=True, stdout=subprocess.PIPE).stdout
    oid = subprocess.run(["git", "rev-parse", spec], cwd=repo, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    return blob, oid


def normalized(value: object) -> str:
    raw = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", raw)


def matching_parent_candidates(rows: list[dict], parent_name: str) -> list[dict]:
    return [row for row in rows if normalized(row["ADM2_EN"]) == normalized(parent_name)]


def unique_index(rows: list[dict], key, label: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    duplicates: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        raw = str(key(row))
        norm = normalized(raw)
        duplicates[norm].append(raw)
        if norm in result:
            continue
        result[norm] = row
    dup = {k: v for k, v in duplicates.items() if len(v) > 1}
    if dup:
        raise ValueError(f"{label} has duplicate normalized join keys: {list(dup.items())[:8]}")
    return result


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_output_root(owned_dir: pathlib.Path, run_id: str | None = None) -> pathlib.Path:
    """Reject symlinked output ancestors and any destination escaping the packet."""
    owned = owned_dir.resolve(strict=True)
    if not owned.is_dir():
        raise ValueError(f"owned packet is not a directory: {owned_dir}")
    output_root = owned_dir / "vintages"
    if output_root.is_symlink():
        raise ValueError(f"output root must not be a symlink: {output_root}")
    if output_root.exists() and not output_root.is_dir():
        raise ValueError(f"output root must be an ordinary directory: {output_root}")
    candidate = output_root / run_id if run_id is not None else output_root
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(owned)
    except ValueError as exc:
        raise ValueError(f"output destination escapes the owned packet: {candidate}") from exc
    return output_root


def output_path_controls() -> dict:
    """Exercise live and dangling symlink attacks without writing outside a fixture."""
    with tempfile.TemporaryDirectory(dir=OWNED, prefix=".output-root-control-") as temporary:
        fixture = pathlib.Path(temporary) / "owned-fixture"
        outside = pathlib.Path(temporary) / "outside"
        fixture.mkdir()
        outside.mkdir()
        results = {}
        for label, target in (("live", outside), ("dangling", pathlib.Path(temporary) / "absent")):
            output_root = fixture / "vintages"
            output_root.symlink_to(target, target_is_directory=True)
            try:
                checked_output_root(fixture, "probe")
            except ValueError:
                results[label] = "rejected"
            else:
                raise ValueError(f"{label} symlink output-root control was not rejected")
            if list(outside.iterdir()):
                raise ValueError(f"{label} symlink control created an outside file")
            output_root.unlink()
        return {
            "live_symlink_output_root": results["live"],
            "dangling_symlink_output_root": results["dangling"],
            "outside_fixture_files_created": 0,
            "control": "both symlinked output-root ancestors are rejected before any write",
        }


def rounded(value: float | None) -> float | None:
    return round(float(value), 9) if value is not None and math.isfinite(float(value)) else None


def projected(feature: dict):
    return transform(TRANSFORM, shape(feature["geometry"]))


def repaired(geom):
    return geom if geom.is_valid else make_valid(geom)


def geometry_metric(source, current) -> dict:
    source_raw_valid, current_raw_valid = source.is_valid, current.is_valid
    a, b = repaired(source), repaired(current)
    union_area = a.union(b).area
    return {
        "source_area_km2": rounded(a.area / 1e6),
        "current_area_km2": rounded(b.area / 1e6),
        "intersection_km2": rounded(a.intersection(b).area / 1e6),
        "source_overlap_percent": rounded(100 * a.intersection(b).area / a.area) if a.area else None,
        "current_overlap_percent": rounded(100 * a.intersection(b).area / b.area) if b.area else None,
        "symmetric_difference_percent_of_union": rounded(100 * a.symmetric_difference(b).area / union_area) if union_area else None,
        "relative_area_change_percent": rounded(100 * (b.area - a.area) / a.area) if a.area else None,
        "source_valid_before_ephemeral_repair": source_raw_valid,
        "current_valid_before_ephemeral_repair": current_raw_valid,
        "source_valid_after_ephemeral_repair": a.is_valid,
        "current_valid_after_ephemeral_repair": b.is_valid,
        "repair_used": not source_raw_valid or not current_raw_valid,
    }


def union_metric(source, current) -> dict:
    a, b = repaired(source), repaired(current)
    union_area = a.union(b).area
    return {
        "source_union_km2": rounded(a.area / 1e6),
        "current_union_km2": rounded(b.area / 1e6),
        "intersection_km2": rounded(a.intersection(b).area / 1e6),
        "intersection_percent_of_source": rounded(100 * a.intersection(b).area / a.area) if a.area else None,
        "symmetric_difference_percent_of_union": rounded(100 * a.symmetric_difference(b).area / union_area) if union_area else None,
        "relative_area_change_percent": rounded(100 * (b.area - a.area) / a.area) if a.area else None,
        "source_connected_components": len(a.geoms) if hasattr(a, "geoms") else 1,
        "current_connected_components": len(b.geoms) if hasattr(b, "geoms") else 1,
        "source_valid_after_ephemeral_repair": a.is_valid,
        "current_valid_after_ephemeral_repair": b.is_valid,
    }


def csv_bytes(rows: list[dict], fields: list[str]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def method_controls(old2_by_name, old3_by_name, current_by_name, codab2_by_name):
    """Source-backed join controls and synthetic checks of geometry metrics."""
    key = normalized("Tsihombe")
    source = codab2_by_name[key]
    current = current_by_name[key]
    old = old2_by_name[key]
    if (source["properties"]["adm2_pcode"] != "MG52514" or old["ADM2_PCODE"] != "MG52514"
            or source["properties"]["adm1_name"] != "Androy" or not current["id"]):
        raise ValueError("positive source join control failed: Tsihombe")
    ant_key = normalized("Antanimora Atsimo")
    ant_source = codab2_by_name[ant_key]
    ant_old3 = old3_by_name.get(ant_key, [])
    if ant_key in current_by_name or ant_key in old2_by_name or len(ant_old3) != 1:
        raise ValueError("negative source join control failed: Antanimora Atsimo")
    ant = ant_old3[0]
    if ant["ADM3_PCODE"] != "MG52516130" or ant["ADM3_TYPE"] != "Commune" or ant["ADM2_PCODE"] != "MG52516":
        raise ValueError("negative source level/parent control failed: Antanimora Atsimo")
    repeated = old3_by_name.get(normalized("Ambohimanambola"), [])
    if len(repeated) < 2:
        raise ValueError("repeat-name positive control is no longer non-vacuous")
    first = repeated[0]
    genuine_parent = matching_parent_candidates(repeated, first["ADM2_EN"])
    # Change both parent name and code to the second real parent pair; the
    # source roster itself remains unchanged and coherent.
    adverse_parent_name = repeated[1]["ADM2_EN"]
    adverse_parent_code = repeated[1]["ADM2_PCODE"]
    adverse_parent = matching_parent_candidates(repeated, adverse_parent_name)
    if len(genuine_parent) != 1 or len(adverse_parent) != 1 or genuine_parent[0]["ADM3_PCODE"] == adverse_parent[0]["ADM3_PCODE"]:
        raise ValueError("coherent parent-mutation negative control failed")
    positive_geom = geometry_metric(box(0, 0, 1000, 1000), box(0, 0, 1000, 1000))
    negative_geom = geometry_metric(box(0, 0, 1000, 1000), box(2000, 0, 3000, 1000))
    if positive_geom["symmetric_difference_percent_of_union"] != 0 or positive_geom["source_overlap_percent"] != 100:
        raise ValueError("positive synthetic geometry control failed")
    if negative_geom["intersection_km2"] != 0 or negative_geom["symmetric_difference_percent_of_union"] != 100:
        raise ValueError("negative synthetic geometry control failed")
    return {
        "version": 1, "issue": 632, "method_id": "madagascar-codab-crosswalk-controls", "outcome": "passed",
        "positive_source_join": {"name": "Tsihombe", "codab_pcode": source["properties"]["adm2_pcode"], "codps_2018_pcode": old["ADM2_PCODE"], "current_id": current["id"], "control": "same-name ADM2 source rows join across all three rosters"},
        "negative_level_control": {"name": "Antanimora Atsimo", "codab_adm2_pcode": ant_source["properties"]["adm2_pcode"], "current_adm2_match": False, "codps_adm2_match": False, "codps_adm3_candidate": {"pcode": ant["ADM3_PCODE"], "type": ant["ADM3_TYPE"], "parent_pcode": ant["ADM2_PCODE"]}, "control": "same-name ADM3 commune is not silently promoted or joined as ADM2"},
        "repeat_name_control": {"name": "Ambohimanambola", "codps_adm3_candidates": len(repeated), "control": "duplicate nationwide commune names remain multi-valued"},
        "coherent_parent_mutation_negative_control": {"commune_name": "Ambohimanambola", "original_parent": first["ADM2_EN"], "original_parent_code": first["ADM2_PCODE"], "selected_adm3_pcode": genuine_parent[0]["ADM3_PCODE"], "mutated_parent": adverse_parent_name, "mutated_parent_code": adverse_parent_code, "selected_adm3_pcode_after_mutation": adverse_parent[0]["ADM3_PCODE"], "control": "changing an actual source parent name and code coherently changes the unique parent-qualified candidate"},
        "positive_geometry_control": positive_geom, "negative_geometry_control": negative_geom,
        "output_path_containment_control": output_path_controls(),
        "limitations": ["Synthetic controls exercise metric implementation only, not Madagascar boundaries.", "Source-backed controls verify selected rows and do not prove complete legal history."],
    }


def write_exclusive(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def build(repo: pathlib.Path, run_id: str, compare_to: str | None = None) -> pathlib.Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise ValueError("run id must be a lowercase alphanumeric/hyphen token")
    output_root = checked_output_root(OWNED, run_id)
    destination = output_root / run_id
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"destination already exists; preserved unchanged: {destination}")
    if compare_to is not None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", compare_to):
            raise ValueError("comparison run id must be a lowercase alphanumeric/hyphen token")
        reference = output_root / compare_to
        if reference.is_symlink() or not reference.is_dir():
            raise ValueError("comparison run must be a retained ordinary directory")
    if subprocess.run(["git", "rev-parse", "--verify", f"{BASE}^{{commit}}"], cwd=repo, stdout=subprocess.DEVNULL).returncode:
        raise ValueError("recorded baseline commit is unavailable")

    blobs: dict[str, bytes] = {}
    pins: list[dict] = []
    for path in INPUT_PATHS:
        data, oid = git_blob(repo, path)
        blobs[path] = data
        pins.append({"path": path, "git_blob": oid, "bytes": len(data), "sha256": sha(data)})

    def json_input(path: str):
        return json.loads(blobs[path].decode("utf-8-sig"))

    def csv_input(path: str):
        return list(csv.DictReader(io.StringIO(blobs[path].decode("utf-8-sig", errors="strict"))))

    index = json_input("data/world-index.json")
    if "geography/part-13.json" not in index.get("parts", []):
        raise ValueError("Madagascar baseline feature file is absent from the pinned world index")
    current_part = json_input("data/geography/part-13.json")
    hierarchy = {row["id"]: row for row in json_input("data/hierarchy.json")}
    issue_scope = json_input(PARENT + "issue-scope.json")
    scoped_ids = issue_scope.get("member_location_ids", [])
    mdg_ids = [value for value in scoped_ids if value.startswith("gb:MDG:ADM2:")]
    if len(mdg_ids) != 119 or len(set(mdg_ids)) != 119:
        raise ValueError("the inherited issue scope must contain the exact 119 unique Madagascar ADM2 IDs")
    id_set = set(mdg_ids)
    current_features = [f for f in current_part["features"] if f.get("id") in id_set]
    if {f["id"] for f in current_features} != id_set:
        raise ValueError("pinned part-13 feature file does not resolve the exact issue subject roster")
    if any(f["properties"].get("metadata", {}).get("administrative_level") != "ADM2" for f in current_features):
        raise ValueError("a scoped current feature is not recorded as ADM2")
    current_by_name = unique_index(current_features, lambda f: f["properties"]["name"], "current Atlas roster")
    current_by_id = {f["id"]: f for f in current_features}
    current_parent_names = {}
    current_by_parent = defaultdict(list)
    for f in current_features:
        pid = f["properties"]["parent_id"]
        if pid not in hierarchy:
            raise ValueError(f"missing current parent {pid}")
        current_parent_names[pid] = hierarchy[pid]["name"]
        current_by_parent[pid].append(f)
    if len(current_by_parent) != 22:
        raise ValueError(f"expected 22 current Madagascar parent groups, found {len(current_by_parent)}")

    old2 = csv_input(PARENT + "sources/mdg_admpop_adm2_2018.csv")
    old3 = csv_input(PARENT + "sources/mdg_admpop_adm3_2018.csv")
    old4 = csv_input(PARENT + "sources/mdg_admpop_adm4_2018.csv")
    if len(old2) != 119 or len(old3) != 1579 or len(old4) != 17465:
        raise ValueError(f"unexpected inherited 2018 CSV row counts: {len(old2)}/{len(old3)}/{len(old4)}")
    if len({r["ADM2_PCODE"] for r in old2}) != len(old2):
        raise ValueError("2018 ADM2 code roster is not unique")
    old2_by_name = unique_index(old2, lambda r: r["ADM2_EN"], "2018 COD-PS ADM2 roster")
    # ADM3 commune names repeat nationally, so retain all rows per normalized
    # name and report candidates without pretending a name alone is a join key.
    old3_by_name: dict[str, list[dict]] = defaultdict(list)
    for row in old3:
        old3_by_name[normalized(row["ADM3_EN"])].append(row)

    codab2 = json.loads(gzip.decompress(blobs[PARENT + "sources/mdg-COD-AB-ADM2-2026-reviewed.geojson.gz"]))["features"]
    codab1 = json.loads(gzip.decompress(blobs[PARENT + "sources/mdg-COD-AB-ADM1-2026-reviewed.geojson.gz"]))["features"]
    if len(codab2) != 120 or len(codab1) != 24:
        raise ValueError(f"unexpected COD-AB feature counts: {len(codab2)}/{len(codab1)}")
    codab2_by_name = unique_index(codab2, lambda f: f["properties"]["adm2_name"], "COD-AB ADM2 roster")
    codab1_by_name = unique_index(codab1, lambda f: f["properties"]["adm1_name"], "COD-AB ADM1 roster")
    if len({f["properties"]["adm2_pcode"] for f in codab2}) != 120:
        raise ValueError("COD-AB ADM2 p-codes are not unique")
    if len({f["properties"]["adm1_pcode"] for f in codab1}) != 24:
        raise ValueError("COD-AB ADM1 p-codes are not unique")
    for row in codab2 + codab1:
        p = row["properties"]
        if p.get("adm0_pcode") != "MG" or p.get("valid_on") != "2018-08-10" or p.get("valid_to") is not None or p.get("version") != "v01":
            raise ValueError("COD-AB metadata date/version/country roster drift")

    tr = json_input(PARENT + "sources.json")
    codab_registry = next(x for x in tr["additional_sources"] if x.get("source_id") == "OCHA/HDX:cod-ab-mdg")
    original_members = {x["member"]: x for x in codab_registry["retained_exact_members"]}
    for member, compressed in [("mdg_admin2.geojson", PARENT + "sources/mdg-COD-AB-ADM2-2026-reviewed.geojson.gz"), ("mdg_admin1.geojson", PARENT + "sources/mdg-COD-AB-ADM1-2026-reviewed.geojson.gz")]:
        descriptor = original_members[member]
        if sha(gzip.decompress(blobs[compressed])) != descriptor["raw_bytes_sha256"]:
            raise ValueError(f"retained {member} differs from the exact upstream ZIP member")

    old_current_matches = set()
    adm2_rows: list[dict] = []
    current_geoms = {f["id"]: projected(f) for f in current_features}
    codab_geoms = {f["properties"]["adm2_pcode"]: projected(f) for f in codab2}
    for src in codab2:
        p = src["properties"]
        norm = normalized(p["adm2_name"])
        current = current_by_name.get(norm)
        old = old2_by_name.get(norm)
        if current:
            old_current_matches.add(current["id"])
        parent_id = current["properties"]["parent_id"] if current else ""
        parent_name = current_parent_names.get(parent_id, "")
        old3_same = old3_by_name.get(norm, [])
        old3_parent_matches = matching_parent_candidates(old3_same, p["adm2_name"])
        row = {
            "source_adm2_name": p["adm2_name"], "source_adm2_pcode": p["adm2_pcode"],
            "source_adm1_name": p["adm1_name"], "source_adm1_pcode": p["adm1_pcode"],
            "source_valid_on": p["valid_on"], "source_valid_to": p["valid_to"], "source_version": p["version"],
            "current_location_id": current["id"] if current else "",
            "current_location_name": current["properties"]["name"] if current else "",
            "current_parent_id": parent_id, "current_parent_name": parent_name,
            "match_basis": "unique normalized exact ADM2 name" if current else "unmatched source ADM2",
            "old_2018_adm2_name": old["ADM2_EN"] if old else "",
            "old_2018_adm2_pcode": old["ADM2_PCODE"] if old else "",
            "old_2018_adm1_name": old["ADM1_EN"] if old else "",
            "old_2018_adm1_pcode": old["ADM1_PCODE"] if old else "",
            "old_2018_same_name_adm3_candidate_count": len(old3_same),
            "old_2018_same_name_adm3_parent_match_count": len(old3_parent_matches),
            "old_2018_same_name_adm3_candidates": json.dumps([{"name": r["ADM3_EN"], "pcode": r["ADM3_PCODE"], "parent": r["ADM2_EN"], "parent_pcode": r["ADM2_PCODE"], "type": r["ADM3_TYPE"]} for r in old3_same], ensure_ascii=False, sort_keys=True),
            "old_new_adm2_pcode_equal": bool(old and old["ADM2_PCODE"] == p["adm2_pcode"]),
        }
        if current:
            row.update(geometry_metric(codab_geoms[p["adm2_pcode"]], current_geoms[current["id"]]))
        else:
            row.update({"source_area_km2": rounded(repaired(codab_geoms[p["adm2_pcode"]]).area / 1e6), "current_area_km2": None,
                        "intersection_km2": None, "source_overlap_percent": None, "current_overlap_percent": None,
                        "symmetric_difference_percent_of_union": None, "relative_area_change_percent": None,
                        "source_valid_before_ephemeral_repair": shape(src["geometry"]).is_valid,
                        "current_valid_before_ephemeral_repair": None,
                        "source_valid_after_ephemeral_repair": repaired(codab_geoms[p["adm2_pcode"]]).is_valid,
                        "current_valid_after_ephemeral_repair": None, "repair_used": not shape(src["geometry"]).is_valid})
        row["over_5_percent_symmetric_difference"] = bool(row.get("symmetric_difference_percent_of_union") is not None and row["symmetric_difference_percent_of_union"] > THRESHOLD)
        adm2_rows.append(row)
    if old_current_matches != id_set or len(old_current_matches) != 119:
        raise ValueError("COD-AB names do not join all 119 distinct current Atlas IDs exactly once")

    old_ant = next((r for r in old3 if normalized(r["ADM3_EN"]) == normalized("Antanimora Atsimo")), None)
    if not old_ant or old_ant["ADM2_PCODE"] != "MG52516" or old_ant["ADM3_PCODE"] != "MG52516130" or old_ant["ADM3_TYPE"] != "Commune":
        raise ValueError("2018 Antanimora Atsimo source-level/code lineage is not as recorded")
    ant_fokontany = [r for r in old4 if r.get("ADM3_PCODE") == old_ant["ADM3_PCODE"]]

    # Geometry comparisons are diagnostic only; no parent/member assignment is changed.
    source2_union = unary_union([repaired(projected(f)) for f in codab2])
    current_union = unary_union([repaired(current_geoms[i]) for i in id_set])
    source2_internal_overlaps = []
    geometries2 = [repaired(projected(f)) for f in codab2]
    tree = STRtree(geometries2)
    for i, geom in enumerate(geometries2):
        for idx in tree.query(geom):
            j = int(idx)
            if j <= i:
                continue
            area = geom.intersection(geometries2[j]).area / 1e6
            if area > 0.001:
                source2_internal_overlaps.append({"a": codab2[i]["properties"]["adm2_pcode"], "b": codab2[j]["properties"]["adm2_pcode"], "overlap_km2": rounded(area)})

    current_parent_geoms = {pid: unary_union([repaired(current_geoms[f["id"]]) for f in fs]) for pid, fs in current_by_parent.items()}
    adm1_matrix: list[dict] = []
    source_parent_geoms = {}
    for src in codab1:
        p = src["properties"]
        src_geom = repaired(projected(src))
        source_parent_geoms[p["adm1_pcode"]] = src_geom
        same = current_parent_names.get(next((pid for pid, name in current_parent_names.items() if normalized(name) == normalized(p["adm1_name"])), ""), "")
        for pid, current_geom in sorted(current_parent_geoms.items()):
            inter = src_geom.intersection(repaired(current_geom)).area
            adm1_matrix.append({
                "source_adm1_name": p["adm1_name"], "source_adm1_pcode": p["adm1_pcode"],
                "source_valid_on": p["valid_on"], "source_version": p["version"],
                "current_parent_id": pid, "current_parent_name": current_parent_names[pid],
                "normalized_exact_name_match": normalized(p["adm1_name"]) == normalized(current_parent_names[pid]),
                "intersection_km2": rounded(inter / 1e6),
                "percent_of_source_adm1": rounded(100 * inter / src_geom.area) if src_geom.area else None,
                "percent_of_current_parent_union": rounded(100 * inter / repaired(current_geom).area) if repaired(current_geom).area else None,
            })
    if len(adm1_matrix) != 24 * 22:
        raise ValueError("ADM1-to-parent intersection matrix does not cover all 24 x 22 pairs")
    source1_union = unary_union(list(source_parent_geoms.values()))
    current1_union = unary_union(list(current_parent_geoms.values()))

    # Preserve every disconnected source component that is a review candidate.
    components: list[dict] = []
    for feature in codab2:
        p = feature["properties"]
        geom = repaired(projected(feature))
        parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
        for part_index, part in enumerate(parts):
            area = part.area / 1e6
            if area <= 0.01:
                continue
            inter = part.intersection(repaired(current_union)).area / 1e6
            frac = inter / area if area else 0
            if frac >= 0.01:
                continue
            hits = []
            for fid, current_geom in current_geoms.items():
                overlap = part.intersection(repaired(current_geom)).area / 1e6
                if overlap > 0.000001:
                    hits.append({"current_location_id": fid, "current_location_name": current_by_id[fid]["properties"]["name"], "intersection_km2": rounded(overlap)})
            centroid = part.centroid
            lonlat = transform(Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True).transform, centroid)
            components.append({
                "source_adm2_name": p["adm2_name"], "source_adm2_pcode": p["adm2_pcode"],
                "source_parent_name": p["adm1_name"], "part_index": part_index,
                "area_km2": rounded(area), "centroid_lon": rounded(lonlat.x), "centroid_lat": rounded(lonlat.y),
                "intersection_with_current_union_km2": rounded(inter), "overlap_percent_of_component": rounded(100 * frac),
                "intersected_current_locations": sorted(hits, key=lambda x: x["intersection_km2"], reverse=True),
                "physical_status": "unresolved: component screen is not physical-land proof",
            })

    missing = [row for row in adm2_rows if not row["current_location_id"]]
    over = [row for row in adm2_rows if row["over_5_percent_symmetric_difference"]]
    source_name_code_equal = sum(bool(row["old_new_adm2_pcode_equal"]) for row in adm2_rows if row["current_location_id"])
    if len(missing) != 1 or missing[0]["source_adm2_pcode"] != "MG52519" or len(over) != 15:
        raise ValueError(f"scope drift: unmatched={len(missing)}; >5% overlays={len(over)}")
    if len(components) != 55:
        raise ValueError(f"component candidate scope changed: expected 55, found {len(components)}")

    antanimora = next(f for f in codab2 if f["properties"]["adm2_pcode"] == "MG52519")
    current_names = {normalized(f["properties"]["name"]): f for f in current_features}
    ant_geom = repaired(projected(antanimora))
    neighbor_rows = []
    for name in ["Ambovombe-Androy", "Bekily", "Amboasary-Atsimo", "Beloha", "Tsihombe"]:
        current = current_names.get(normalized(name))
        if current is None:
            raise ValueError(f"required Antanimora neighbor is absent from current scope: {name}")
        geom = repaired(current_geoms[current["id"]])
        overlap = ant_geom.intersection(geom).area
        neighbor_rows.append({
            "source_adm2_name": "Antanimora Atsimo", "source_adm2_pcode": "MG52519",
            "current_neighbor_name": name, "current_neighbor_id": current["id"],
            "current_parent_name": current_parent_names[current["properties"]["parent_id"]],
            "source_antanimora_area_km2": rounded(ant_geom.area / 1e6),
            "current_neighbor_area_km2": rounded(geom.area / 1e6),
            "intersection_km2": rounded(overlap / 1e6),
            "percent_of_source_antanimora": rounded(100 * overlap / ant_geom.area) if ant_geom.area else None,
            "percent_of_current_neighbor": rounded(100 * overlap / geom.area) if geom.area else None,
            "interpretation": "geometric intersection only; legal adjacency, boundary identity and land status unresolved",
        })
    controls = method_controls(old2_by_name, old3_by_name, current_by_name, codab2_by_name)

    source_pin = {"base_commit": BASE, "retrieved_upstream": "2026-10-03 inherited source registry; exact original COD-AB members retained in #482", "inputs": pins}
    methods = {
        "crosswalk": "Current ADM2, COD-AB ADM2/ADM1 and 2018 COD-PS ADM2 normalized names are required unique within their own rosters. Nationwide 2018 ADM3 commune names repeat; all candidates and parent-name matches are retained, and no commune join is inferred from name alone. Codes are retained as vintage-specific identifiers, not treated as stable across products.",
        "geometry": "EPSG:6933 equal-area; MakeValid is applied only to ephemeral in-memory comparison geometries. Symmetric difference is divided by the union area. Geometry comparisons are triage, not legal boundary proof.",
        "components": "Each source ADM2 polygon component >0.01 km2 with <1% overlap against the union of all 119 current Madagascar features is retained as an unresolved candidate. A GSHHG non-hit is not evidence that land is absent.",
    }
    results = {
        "version": 1, "issue": 632, "method_id": "madagascar-codab-crosswalk", "baseline_commit": BASE,
        "source_adm2_count": len(codab2), "source_adm1_count": len(codab1),
        "current_location_count": len(current_features), "current_parent_group_count": len(current_by_parent),
        "unique_source_adm2_pcodes": len({r["properties"]["adm2_pcode"] for r in codab2}),
        "unique_source_adm1_pcodes": len({r["properties"]["adm1_pcode"] for r in codab1}),
        "unique_source_adm2_normalized_names": len(codab2_by_name), "unique_source_adm1_normalized_names": len(codab1_by_name),
        "current_ids_joined_once": len(old_current_matches), "unmatched_source_adm2": missing,
        "name_matched_current_rows_with_same_old_and_new_adm2_pcode": source_name_code_equal,
        "adm2_geometry_rows_over_5_percent": len(over), "adm2_over_5_percent_pcodes": [x["source_adm2_pcode"] for x in over],
        "old_2018_antanimora": {"adm2_name": old_ant["ADM2_EN"], "adm2_pcode": old_ant["ADM2_PCODE"], "adm3_name": old_ant["ADM3_EN"], "adm3_pcode": old_ant["ADM3_PCODE"], "adm3_type": old_ant["ADM3_TYPE"], "adm4_rows": len(ant_fokontany)},
        "codab_source_date": {"valid_on": "2018-08-10", "valid_to": None, "version": "v01", "metadata_reviewed": "2026-07-06", "retrieved": "2026-10-03"},
        "adm2_union_comparison": union_metric(source2_union, current_union),
        "adm1_union_comparison": union_metric(source1_union, current1_union),
        "source_adm2_interior_overlaps_over_0_001_km2": source2_internal_overlaps,
        "source_component_count": sum(len(list(repaired(projected(f)).geoms)) if hasattr(repaired(projected(f)), "geoms") else 1 for f in codab2),
        "component_candidate_count": len(components),
        "component_candidate_total_km2": rounded(sum(x["area_km2"] for x in components)),
        "adm1_full_matrix_rows": len(adm1_matrix), "current_parent_names": sorted(current_parent_names.values()),
        "source_adm1_names": sorted(x["properties"]["adm1_name"] for x in codab1),
        "methods": methods,
        "limitations": [
            "2018-08-10 is the COD-AB valid_on metadata field, not a legal creation/effect date.",
            "The name crosswalk does not establish historical or current polygon equivalence.",
            "The 22 current parent groups are reviewed as a complete intersection matrix; no parent assignment is approved or changed.",
            "Disconnected components and GSHHG L1 non-detection do not establish physical land presence or absence.",
            "The 2018 population CSV is attribute/statistics evidence and does not provide boundary geometry.",
        ],
    }

    products = {
        "input-pins.json": (json.dumps(source_pin, ensure_ascii=False, indent=2) + "\n").encode(),
        "adm2-crosswalk-and-geometry.csv": csv_bytes(adm2_rows, list(adm2_rows[0].keys())),
        "adm1-parent-intersections.csv": csv_bytes(adm1_matrix, list(adm1_matrix[0].keys())),
        "disconnected-components.csv": csv_bytes(components, list(components[0].keys())),
        "antanimora-neighbor-intersections.csv": csv_bytes(neighbor_rows, list(neighbor_rows[0].keys())),
        "results.json": (json.dumps(results, ensure_ascii=False, indent=2) + "\n").encode(),
        "controls.json": (json.dumps(controls, ensure_ascii=False, indent=2) + "\n").encode(),
    }
    output_files = [{"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in sorted(products.items())]
    bundle = "\n".join(f"{row['path']}\0{row['bytes']}\0{row['sha256']}" for row in output_files).encode()
    bundle_hash = sha(bundle)
    code_hash = sha(pathlib.Path(__file__).read_bytes())
    output_root.mkdir(parents=True, exist_ok=True)
    checked_output_root(OWNED, run_id)
    if compare_to:
        prior = json.loads((reference / "completion.json").read_text())
        if prior.get("outcome") != "passed" or prior.get("code_sha256") != code_hash or prior.get("output_bundle_sha256") != bundle_hash:
            raise ValueError("reproduced result differs from the retained first run or uses different code")
        for row in prior.get("outputs", []):
            expected = products.get(row["path"])
            retained_path = reference / row["path"]
            if retained_path.is_symlink() or not retained_path.is_file():
                raise ValueError(f"retained output must be an ordinary file: {row['path']}")
            retained = retained_path.read_bytes()
            if expected is None or expected != retained or sha(expected) != row["sha256"]:
                raise ValueError(f"reproduction output differs from retained first run: {row['path']}")
        if set(products) != {row["path"] for row in prior.get("outputs", [])}:
            raise ValueError("reproduction output inventory differs from retained first run")
        destination.mkdir(mode=0o700)
        checked_output_root(OWNED, run_id)
        receipt = {"version": 1, "issue": 632, "method_id": "madagascar-codab-crosswalk", "kind": "reproducibility-control", "outcome": "passed", "run_one_id": compare_to, "run_two_id": run_id, "code_sha256": code_hash, "run_one_bundle_sha256": bundle_hash, "run_two_bundle_sha256": sha(bundle), "products_recomputed_in_memory": output_files, "matches_retained_run": True}
        write_exclusive(destination / "reproducibility.json", (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode())
        return destination
    destination.mkdir(mode=0o700)
    checked_output_root(OWNED, run_id)
    for name, data in products.items():
        write_exclusive(destination / name, data)
    completion = {"version": 1, "issue": 632, "method_id": "madagascar-codab-crosswalk", "kind": "reproducibility", "outcome": "passed", "run_id": run_id, "code_sha256": code_hash, "output_bundle_sha256": bundle_hash, "outputs": output_files}
    write_exclusive(destination / "completion.json", (json.dumps(completion, ensure_ascii=False, indent=2) + "\n").encode())
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--compare-to", help="recompute all products in memory and compare with a retained completed run")
    args = parser.parse_args()
    repo = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, stdout=subprocess.PIPE, text=True).stdout.strip())
    try:
        result = build(repo, args.run_id, args.compare_to)
        receipt_name = "reproducibility.json" if args.compare_to else "completion.json"
        print(json.dumps({"status": "complete", "path": str(result.relative_to(OWNED)), "receipt": json.loads((result / receipt_name).read_text())}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
