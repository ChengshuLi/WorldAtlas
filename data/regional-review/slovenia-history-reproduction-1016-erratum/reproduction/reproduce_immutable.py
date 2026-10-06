#!/usr/bin/env python3
"""Bounded immutable reproduction for the exact 53 Slovenia name subjects in #1185.

Inputs are read from Git objects and checked as whole-file bytes before parsing.
The runner writes only an exclusive new vintage under the declared owned prefix.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

ISSUE = 1185
OWNED = "data/regional-review/slovenia-history-reproduction-1016-erratum/"
BASELINE_COMMIT = "aee3bc644593c8e080f4a8495a851890695581ec"
PIN_MANIFEST = OWNED + "input-pins.json"
PIN_MANIFEST_SHA256 = "589bf98315fdb86bc432f1b6c99a52225a3d1dc6b2f941d8255d0ed44b068a05"
EXPECTED_CODE_SHA256 = "408fe92853a0f02b023d709cccadb3876b7ef5e0bdce030378fc9f9370b89271"
SUBJECT_PREFIX = "gb:SVN:ADM2:"
TARGET_DATES = ("2017-01-01T00:00:00Z", "2017-07-01T00:00:00Z")
OLD_PACKET = "data/regional-review/followup-yugoslavia-423-slovenia-names-20261005/"
OLD_ASSESSMENT = OLD_PACKET + "2017-name-assessment.csv"
OLD_SUMMARY = OLD_PACKET + "reproduction-summary.json"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_code_sha256(path: Path) -> str:
    raw = path.read_bytes()
    for name in (b"PIN_MANIFEST_SHA256", b"EXPECTED_CODE_SHA256"):
        import re
        raw, count = re.subn(name + rb' = "[a-f0-9]{64}"', name + b' = "' + b'0'*64 + b'"', raw)
        if count != 1:
            raise ValueError("Runner code pin fields are malformed")
    return sha256(raw)


def verify_code_pin(path: Path) -> str:
    actual = canonical_code_sha256(path)
    if actual != EXPECTED_CODE_SHA256:
        raise ValueError("Runner canonical code pin mismatch")
    return actual


def git_bytes(repo: Path, commit: str, path: str) -> bytes:
    if not commit or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("Expected a full immutable Git commit")
    result = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"],
                            check=True, capture_output=True)
    return result.stdout


def load_pinned(repo: Path, overrides: dict[str, bytes] | None = None) -> tuple[dict, dict[str, bytes]]:
    """Check the pin ledger and every complete input before returning any parsed input."""
    pin_raw = (repo / PIN_MANIFEST).read_bytes()
    if sha256(pin_raw) != PIN_MANIFEST_SHA256:
        raise ValueError("Pinned input ledger changed")
    ledger = json.loads(pin_raw)
    if ledger.get("issue") != ISSUE or ledger.get("baseline_commit") != BASELINE_COMMIT:
        raise ValueError("Input ledger issue/baseline mismatch")
    if ledger.get("runner_code_sha256") != EXPECTED_CODE_SHA256:
        raise ValueError("Input ledger runner code pin mismatch")
    sys.path.insert(0, str(repo / "scripts"))
    from evidence.immutable import Baseline
    descriptors = [{"path": row["path"], "bytes": row["bytes"],
                    "sha256": row["sha256"], "hash_kind": "file-bytes"}
                   for row in ledger["files"]]
    baseline = Baseline(repo, BASELINE_COMMIT, descriptors)
    files: dict[str, bytes] = {}
    for row in ledger["files"]:
        path = row["path"]
        raw = (overrides or {}).get(path)
        if raw is None:
            raw = baseline.read(path)
        if len(raw) != row["bytes"] or sha256(raw) != row["sha256"]:
            raise ValueError(f"Whole-file input pin mismatch: {path}")
        files[path] = raw
    required = [row["path"] for row in ledger["files"] if row.get("required_by_issue")]
    issue_pins = ledger.get("issue_pins_sha256", {})
    if len(required) != 19 or len(issue_pins) != 19:
        raise ValueError("Issue pin inventory is incomplete")
    by_path = {row["path"]: row["sha256"] for row in ledger["files"]}
    for key, expected in issue_pins.items():
        origin, path = key.split(":", 1)
        if by_path.get(path) != expected:
            raise ValueError(f"Issue pin mismatch in ledger: {path}")
        original = git_bytes(repo, origin, path)
        if sha256(original) != expected:
            raise ValueError(f"Original issue-pinned vintage mismatch: {origin}:{path}")
    return ledger, files


def parse_json(files: dict[str, bytes], path: str):
    return json.loads(files[path].decode("utf-8"))


def parse_csv(files: dict[str, bytes], path: str, encoding="utf-8-sig"):
    return list(csv.DictReader(io.StringIO(files[path].decode(encoding), newline="")))


def build_products(ledger: dict, files: dict[str, bytes]) -> dict[str, bytes]:
    """Run a complete exact-scope join after immutable pins have all passed."""
    # The candidate roster is in the parent packet, not the historical-name packet.
    atlas_path = "data/geography/part-22.json"
    atlas = parse_json(files, atlas_path)["features"]
    atlas_by_id = {}
    for feature in atlas:
        props = feature.get("properties", {})
        ident = feature.get("id") or props.get("id")
        if ident in atlas_by_id:
            raise ValueError(f"Duplicate Atlas identity: {ident}")
        atlas_by_id[ident] = feature

    # Use the explicitly pinned path from the issue input contract.
    candidate_path = "data/regional-review/regional-review-d282e62cf0209796/slovenia-name-correction-candidates.csv"
    candidates = parse_csv(files, candidate_path)
    ids = [row["location_id"] for row in candidates]
    if len(ids) != 53 or len(set(ids)) != 53 or any(not ident.startswith(SUBJECT_PREFIX) for ident in ids):
        raise ValueError("The exact 53 unique Slovenia ADM2 subject roster changed")
    expected_ids = sorted(ident for ident in atlas_by_id if ident.startswith(SUBJECT_PREFIX)
                          and atlas_by_id[ident]["properties"].get("metadata", {}).get("reference_year") == "2017"
                          and ident in set(ids))
    if expected_ids != sorted(ids):
        raise ValueError("Requested roster differs from its containing geography part")

    source_geo = parse_json(files, "data/regional-review/regional-review-d282e62cf0209796/source/geoboundaries-9469f09/geoBoundaries-SVN-ADM2.geojson")
    source_by_id = {}
    for feature in source_geo["features"]:
        shape_id = feature.get("properties", {}).get("shapeID")
        if shape_id in source_by_id:
            raise ValueError(f"Duplicate 2017 source shapeID: {shape_id}")
        source_by_id[shape_id] = feature
    source_metadata = parse_json(files, "data/regional-review/regional-review-d282e62cf0209796/source/geoboundaries-9469f09/geoBoundaries-SVN-ADM2-metaData.json")
    if len(source_by_id) != int(source_metadata.get("admUnitCount", -1)):
        raise ValueError("Complete 2017 geoBoundaries ADM2 source roster differs from its metadata count")

    current = parse_json(files, "data/regional-review/regional-review-d282e62cf0209796/source/gurs-municipal-boundaries.geojson")
    current_by_code = {}
    for feature in current["features"]:
        props = feature.get("properties", {})
        code = str(int(props["SIFRA"])).zfill(3)
        if code in current_by_code:
            raise ValueError(f"Duplicate current GURS municipality code: {code}")
        current_by_code[code] = (feature, props)
    if len(current_by_code) != 212:
        raise ValueError("Pinned current official municipality layer is not the complete 212-feature roster")

    hist = parse_json(files, OLD_PACKET + "source/gurs-obcine-h-53-codes-2017.json")["features"]
    history_by_code: dict[str, list] = {}
    for feature in hist:
        props = feature.get("properties", {})
        code = str(int(props["SIFRA"])).zfill(3)
        history_by_code.setdefault(code, []).append(feature)
    if len(history_by_code) != 53 or any(feature.get("geometry") is not None for feature in hist):
        raise ValueError("Historical response must be the exact 53-code, attribute-only record set")

    surs = parse_json(files, OLD_PACKET + "source/sistat-0214809S-2017-area.json")
    if surs["size"] != [213, 2, 1] or surs["id"] != ["OBČINE", "POLLETJE", "MERITVE"]:
        raise ValueError("Unexpected SURS table dimensions/selection")
    if surs["dimension"]["POLLETJE"]["category"]["index"] != {"2017H1": 0, "2017H2": 1}:
        raise ValueError("SURS half-year selection changed")
    if surs["dimension"]["MERITVE"]["category"]["label"].get("1") != "Area [sq. km]":
        raise ValueError("SURS measure changed")
    surs_index = surs["dimension"]["OBČINE"]["category"]["index"]
    surs_labels = surs["dimension"]["OBČINE"]["category"]["label"]

    previous = parse_csv(files, OLD_ASSESSMENT)
    previous_by_id = {row["location_id"]: row for row in previous}
    if len(previous_by_id) != 53 or set(previous_by_id) != set(ids):
        raise ValueError("Retained historical report does not match the exact subject roster")

    rows = []
    context_rows = []
    parent_counts = {}
    for row in candidates:
        ident = row["location_id"]
        shape_id = row["source_shape_id"]
        code = str(int(row["current_GURS_code"])).zfill(3)
        prior = previous_by_id[ident]
        if ident != SUBJECT_PREFIX + shape_id or ident not in atlas_by_id:
            raise ValueError(f"Candidate ID/shape identity mismatch: {ident}")
        atlas_feature = atlas_by_id[ident]
        ap = atlas_feature["properties"]
        if ap.get("name") != row["atlas_name"] or ap.get("metadata", {}).get("original_id") != shape_id:
            raise ValueError(f"Atlas name/original shape correspondence mismatch: {ident}")
        source_feature = source_by_id.get(shape_id)
        if not source_feature:
            raise ValueError(f"2017 geoBoundaries source shape missing: {shape_id}")
        sp = source_feature.get("properties", {})
        if sp.get("shapeType") != "ADM2" or source_metadata.get("boundaryYear") != "2017" or source_metadata.get("boundaryType") != "ADM2":
            raise ValueError(f"Source level/vintage changed: {shape_id}")
        current_feature, cp = current_by_code.get(code, (None, None))
        if not current_feature or cp.get("NAZIV") != row["current_GURS_name"] or str(cp.get("DATUM_SYS")) != row["GURS_feature_date"]:
            raise ValueError(f"Current GURS code/name/vintage correspondence mismatch: {code}")
        if code not in surs_index:
            raise ValueError(f"SURS code absent: {code}")
        si = surs_index[code]
        h1, h2 = surs["value"][si * 2:si * 2 + 2]
        if h1 is None or h2 is None:
            raise ValueError(f"SURS area series missing for {code}")
        if surs_labels[code] != prior["sistat_dimension_label_at_retrieval"]:
            raise ValueError(f"SURS dimension label drift: {code}")

        resolved = {}
        for date in TARGET_DATES:
            matches = []
            for feature in history_by_code.get(code, []):
                p = feature["properties"]
                start, end = p.get("DATUM_OD"), p.get("DATUM_DO")
                if start and start <= date and (not end or end > date):
                    matches.append((feature, p))
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one effective GURS history record for {code} at {date}; got {len(matches)}")
            resolved[date] = matches[0]
        jan, jul = resolved[TARGET_DATES[0]], resolved[TARGET_DATES[1]]
        name_jan, name_jul = jan[1]["NAZIV"], jul[1]["NAZIV"]
        parent = ap.get("parent_id")
        parent_counts[parent] = parent_counts.get(parent, 0) + 1
        rows.append({
            "location_id": ident, "source_shape_id": shape_id,
            "baseline_atlas_name": ap["name"], "municipality_code": code,
            "atlas_2017_reference_name": row["atlas_name"],
            "candidate_packet_current_gurs_name": row["current_GURS_name"],
            "sistat_dimension_label_at_retrieval": surs_labels[code],
            "gurs_current_feature_date": cp["DATUM_SYS"],
            "sistat_area_2017H1_km2": h1, "sistat_area_2017H2_km2": h2,
            "2017_entity_presence": "supported-by-2017-statistical-series",
            "gurs_official_name_2017_01_01": name_jan,
            "gurs_validity_2017_01_01_feature_id": jan[0]["id"],
            "gurs_official_name_2017_07_01": name_jul,
            "gurs_validity_2017_07_01_feature_id": jul[0]["id"],
            "official_names_same_at_both_2017_dates": name_jan == name_jul,
            "current_GURS_name_matches_2017": row["current_GURS_name"] == name_jan == name_jul,
            "atlas_name_matches_official_2017_name": row["atlas_name"] == name_jan == name_jul,
            "2017_official_name": "verified-from-GURS-OBCINE_H-effective-interval",
            "engineering_handoff": ("For approved official-Slovene display policy, replace Atlas reference spelling with this dated official name; preserve stable ID and old source spelling as alias/provenance pending source-lineage review." if row["atlas_name"] != name_jan or row["atlas_name"] != name_jul else "no-name-difference-at-2017-reference-dates")
        })
        context_rows.append({
            "subject_id": ident,
            "source_shape_id": shape_id,
            "source_boundary_vintage": str(source_metadata.get("boundaryYear")),
            "source_level": sp.get("shapeType"),
            "source_canonical_role": source_metadata.get("boundaryCanonical") or "unspecified-by-source",
            "source_name": sp.get("shapeName"),
            "source_license": "Open Data Commons Open Database License 1.0 (ODbL 1.0)",
            "atlas_reference_name": ap["name"],
            "existing_atlas_parent_id": parent,
            "parent_source": ap.get("metadata", {}).get("hierarchy_source"),
            "parent_role_status": "retained framework assignment; not independently approved by this name-reproduction erratum",
            "current_official_municipality_code": code,
            "current_official_name": cp["NAZIV"],
            "current_official_geometry_source_date": cp["DATUM_SYS"],
            "current_source_membership": "matched by native municipality code; no polygon equivalence asserted",
            "official_gurs_name_2017_01_01": name_jan,
            "official_gurs_name_2017_07_01": name_jul,
            "historical_geometry": "not present in OBCINE_H response",
        })

    if len(rows) != 53 or sum(1 for r in rows if r["gurs_official_name_2017_01_01"]) != 53:
        raise ValueError("Incomplete subject/date result")
    csv_out = io.StringIO(newline="")
    writer = csv.DictWriter(csv_out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    assessment = csv_out.getvalue().encode("utf-8")
    summary = {
        "method": "Join the exact 53 pinned candidate rows to SURS 0214809S 2017H1/H2 by code and to retained GURS OBCINE_H history by SIFRA; evaluate each half-open DATUM_OD/DATUM_DO interval at 2017-01-01 and 2017-07-01.",
        "baseline_commit": "3042d1278e87dae00c26924c339e940c9fba240e",
        "baseline_geography_path": atlas_path,
        "baseline_geography_sha256": sha256(files[atlas_path]),
        "candidate_count": len(rows), "unique_subject_count": len({r["location_id"] for r in rows}),
        "baseline_subjects_present_and_names_match": sum(1 for r in rows if r["baseline_atlas_name"] == r["atlas_2017_reference_name"]),
        "current_GURS_code_name_vintage_matches": len(rows), "code_matches": len(rows),
        "non_null_2017H1_H2_area_pairs": sum(1 for r in rows if r["sistat_area_2017H1_km2"] is not None and r["sistat_area_2017H2_km2"] is not None),
        "gurs_history_feature_count_in_retained_response": len(hist),
        "official_names_resolved_at_2017_01_01": sum(bool(r["gurs_official_name_2017_01_01"]) for r in rows),
        "official_names_resolved_at_2017_07_01": sum(bool(r["gurs_official_name_2017_07_01"]) for r in rows),
        "names_stable_between_2017_dates": sum(r["official_names_same_at_both_2017_dates"] for r in rows),
        "current_GURS_names_match_2017_names": sum(r["current_GURS_name_matches_2017"] for r in rows),
        "atlas_names_exactly_match_both_dates": sum(r["atlas_name_matches_official_2017_name"] for r in rows),
        "atlas_names_differ_from_official_2017": sum(not r["atlas_name_matches_official_2017_name"] for r in rows),
        "historical_name_unresolved": 0,
        "name_corrections_proposed": sum(not r["atlas_name_matches_official_2017_name"] for r in rows),
        "name_correction_proposals_are_core_edits": False,
        "engineering_handoffs": sum(not r["atlas_name_matches_official_2017_name"] for r in rows),
        "limitation": "GURS historical municipality name/validity features resolve the two requested reference dates for all 53 codes. The dated register evidence does not determine the product locale/name policy, validate Atlas polygons, establish neighboring granularity, or authorize core edits; no correction is applied in this research packet.",
        "subjects_sha256_ordered_source_ids": [r["location_id"] for r in rows]
    }
    summary_out = (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    context = {
        "version": 1, "issue": ISSUE, "baseline_commit": BASELINE_COMMIT,
        "subject_count": len(context_rows), "subject_ids": [r["subject_id"] for r in context_rows],
        "source_metadata": source_metadata,
        "current_official_municipality_count": len(current_by_code),
        "current_official_subject_matches": len(context_rows),
        "2017_geoboundaries_declared_adm_unit_count": int(source_metadata["admUnitCount"]),
        "rows": context_rows,
        "parent_ids_in_exact_53_scope": parent_counts,
        "parent_meaning": "Atlas assignments are reported for preservation/context only; the source collection does not validate these parent divisions.",
        "boundary_scope_limit": "The 2017 geoBoundaries ADM2 shapes and current GURS municipal polygons are identity/vintage context. The historical OBCINE_H response is attribute-only; no historical geometry, polygon equivalence, completeness approval or boundary replacement is established.",
        "neighboring_granularity_limit": "The 53 rows are a selected historical-name subset, not a national roster. Prior retained #423 evidence records 211 Slovenia source members against 212 current GURS municipalities; no full regional branch or neighboring-tier approval follows.",
        "limits": ["The 53 subjects are a selected subset, not a complete Slovenia roster.", "Current boundary code matches do not prove dated polygon equivalence or authoritative parent hierarchy.", "Historical GURS names and validity dates are supported; product locale and geometry decisions remain open."]
    }
    context_out = (json.dumps(context, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {"2017-name-assessment.csv": assessment,
            "reproduction-summary.json": summary_out,
            "territorial-context.json": context_out}


def exclusive_write(repo: Path, vintage: str, products: dict[str, bytes]) -> Path:
    if not vintage or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in vintage):
        raise ValueError("Vintage must be a lowercase, named safe identifier")
    root = repo / OWNED
    target = root / "vintages" / vintage
    for part in [target, *target.parents]:
        if part.is_symlink():
            raise ValueError(f"Symlink in output path: {part}")
    if target.exists():
        raise FileExistsError(f"Destination already exists; preserved unchanged: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.mkdir(target)  # exclusive directory creation; never reuses or replaces a vintage
    try:
        for name, raw in products.items():
            file = target / name
            with open(file, "xb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    except Exception:
        # Keep any partial files as a forensic checkpoint; never rewrite on retry.
        raise
    return target


def run(repo: Path, vintage: str, overrides: dict[str, bytes] | None = None, emit: bool = True):
    verify_code_pin(Path(__file__).resolve())
    ledger, files = load_pinned(repo, overrides)
    products = build_products(ledger, files)
    if emit:
        return exclusive_write(repo, vintage, products)
    return products


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--vintage", required=True)
    args = parser.parse_args()
    try:
        output_dir = run(args.repo.resolve(), args.vintage)
    except Exception as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"outcome": "written-exclusive", "path": str(output_dir),
                      "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p.read_bytes())}
                                for p in sorted(output_dir.iterdir())}}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
