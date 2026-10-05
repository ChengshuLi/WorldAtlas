#!/usr/bin/env python3
"""Build additive, country-bound license provenance from immutable main blobs."""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
CONTRACT_PATH = OWNED / "issue-contract.json"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(path: str, commit: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def read_json(raw: bytes):
    return json.loads(raw.decode("utf-8"))


def source_entry(acquisition: dict, country: str) -> dict:
    matches = [row for row in acquisition["sources"]
               if row.get("provider") == "geoBoundaries" and row.get("country") == country]
    if len(matches) != 1:
        raise ValueError(f"Expected one retained geoBoundaries acquisition for {country}")
    return matches[0]


def assert_country_binding(member: dict, country: str, metadata: dict) -> None:
    """Reject cross-country metadata even when its license string is plausible."""
    code = {"SLE": "Sierra Leone", "TGO": "Togo"}.get(country)
    if code is None:
        raise ValueError(f"Unsupported country context: {country}")
    if not member["id"].startswith(f"gb:{country}:ADM2:"):
        raise ValueError(f"Subject ID does not belong to {country}: {member['id']}")
    if member.get("country") != code or metadata.get("boundaryISO") != country:
        raise ValueError(f"Country-bound metadata mismatch for {member['id']}")
    if member.get("pinned_source_id") != f"gb:{country}:ADM2":
        raise ValueError(f"Pinned source country differs for {member['id']}")
    if metadata.get("boundaryType") != "ADM2":
        raise ValueError(f"Expected ADM2 source metadata for {country}")


def validate_sle_record(record: dict, metadata: dict) -> None:
    if record["corrected_license"] != metadata.get("boundaryLicense"):
        raise ValueError(f"License differs from country-bound SLE metadata: {record['id']}")
    if record["represented_vintage"] != metadata.get("boundaryYearRepresented"):
        raise ValueError(f"Represented year differs from SLE metadata: {record['id']}")
    if record["source_role"] != metadata.get("boundaryCanonical"):
        raise ValueError(f"Source role differs from SLE metadata: {record['id']}")


def main() -> None:
    contract = read_json(CONTRACT_PATH.read_bytes())
    baseline = contract["baseline_commit"]
    pins = contract["pins"]
    paths = contract["baseline_paths"]

    inputs = {}
    pin_for_path = {
        "scope": "scope_sha256",
        "assessment": "assessment_sha256",
        "assessment_csv": "assessment_csv_sha256",
        "builder": "builder_sha256",
        "sle_metadata": "sle_metadata_gzip_sha256",
        "tgo_metadata": "tgo_metadata_gzip_sha256",
    }
    for name, path in paths.items():
        raw = blob(path, baseline)
        expected = pins.get(pin_for_path.get(name, name))
        if expected and digest(raw) != expected:
            raise SystemExit(f"Pinned input hash mismatch: {name} ({path})")
        inputs[name] = {"path": path, "bytes": len(raw), "sha256": digest(raw), "raw": raw}

    scope = read_json(inputs["scope"]["raw"])
    assessment = read_json(inputs["assessment"]["raw"])
    acquisition = read_json(inputs["acquisition"]["raw"])
    hierarchy_rows = read_json(inputs["hierarchy"]["raw"])
    hierarchy = {row["id"]: row for row in hierarchy_rows}
    if len(hierarchy) != len(hierarchy_rows):
        raise SystemExit("Pinned hierarchy contains duplicate IDs")
    sle_path = paths["sle_metadata"]
    tgo_path = paths["tgo_metadata"]
    sle_gzip = inputs["sle_metadata"]["raw"]
    tgo_gzip = inputs["tgo_metadata"]["raw"]
    sle_raw = gzip.decompress(sle_gzip)
    tgo_raw = gzip.decompress(tgo_gzip)
    sle = read_json(sle_raw)
    tgo = read_json(tgo_raw)
    if digest(sle_gzip) != pins["sle_metadata_gzip_sha256"]:
        raise SystemExit("Sierra Leone compressed metadata pin mismatch")
    if digest(tgo_gzip) != pins["tgo_metadata_gzip_sha256"]:
        raise SystemExit("Togo compressed metadata pin mismatch")

    sle_acquisition = source_entry(acquisition, "SLE")
    tgo_acquisition = source_entry(acquisition, "TGO")
    for country, meta, compressed, uncompressed, source, path in (
        ("SLE", sle, sle_gzip, sle_raw, sle_acquisition, sle_path),
        ("TGO", tgo, tgo_gzip, tgo_raw, tgo_acquisition, tgo_path),
    ):
        retained = source["retained_metadata"]
        if retained["file"] != f"sources/{Path(path).name}":
            raise SystemExit(f"Acquisition path mismatch for {country} metadata")
        if retained["gzip_sha256"] != digest(compressed) or retained["gzip_bytes"] != len(compressed):
            raise SystemExit(f"Acquisition compressed receipt mismatch for {country}")
        if retained["restored_sha256"] != digest(uncompressed) or retained["restored_bytes"] != len(uncompressed):
            raise SystemExit(f"Acquisition restored receipt mismatch for {country}")
        if source.get("license") != meta.get("boundaryLicense"):
            raise SystemExit(f"Acquisition license differs from retained {country} metadata")
        inv = assessment["source_inventory"][country]["geoBoundaries"]
        expected_inv = {
            "source": meta.get("boundarySource"),
            "role": meta.get("boundaryCanonical"),
            "adm_level": meta.get("boundaryType"),
            "represented_vintage": meta.get("boundaryYearRepresented"),
            "license": meta.get("boundaryLicense"),
        }
        if any(inv.get(key) != value for key, value in expected_inv.items()):
            raise SystemExit(f"Assessment source inventory differs from {country} metadata")

    members = assessment["members"]
    sle_members = [row for row in members if row["id"].startswith("gb:SLE:ADM2:")]
    tgo_members = [row for row in members if row["id"].startswith("gb:TGO:ADM2:")]
    expected_ids = contract["subject_ids"]
    if len(sle_members) != 12 or len(tgo_members) != 37:
        raise SystemExit("Pinned assessment no longer contains the 12/37 country groups")
    if {row["id"] for row in sle_members} != set(expected_ids):
        raise SystemExit("Sierra Leone subjects differ from the exact issue scope")
    if len(expected_ids) != len(set(expected_ids)) or scope["member_location_ids_sha256"] != contract["scope_members_sha256"]:
        raise SystemExit("Issue identity/scope pin mismatch")
    if set(scope["member_location_ids"]) != {row["id"] for row in members}:
        raise SystemExit("Original assessment members differ from the immutable scope roster")

    def canonical_parent_chain(member: dict) -> list[str]:
        chain = []
        parent = member["atlas_parent_id"]
        visited = {member["id"]}
        while parent is not None:
            if parent in visited or parent not in hierarchy:
                raise SystemExit(f"Missing or cyclic canonical hierarchy parent for {member['id']}: {parent}")
            visited.add(parent)
            chain.append(parent)
            parent = hierarchy[parent].get("parent_id")
        return chain

    for member in sle_members + tgo_members:
        if canonical_parent_chain(member) != member["atlas_parent_chain"]:
            raise SystemExit(f"Assessment parent chain disagrees with pinned hierarchy: {member['id']}")

    sle_license = sle["boundaryLicense"]
    tgo_license = tgo["boundaryLicense"]
    rows = []
    for member in sorted(sle_members, key=lambda item: item["id"]):
        assert_country_binding(member, "SLE", sle)
        if member["baseline_license"] != tgo_license:
            raise SystemExit(f"Expected the audited inherited Togo value on {member['id']}")
        record = {
            "id": member["id"],
            "name": member["name"],
            "country": "SLE",
            "parent_id": member["atlas_parent_id"],
            "parent_chain": member["atlas_parent_chain"],
            "source_id": member["pinned_source_id"],
            "represented_vintage": sle["boundaryYearRepresented"],
            "source_role": sle["boundaryCanonical"],
            "source_admin_level": sle["boundaryType"],
            "source_name": sle["boundarySource"],
            "original_assessment_license": member["baseline_license"],
            "corrected_license": sle_license,
            "license_source": sle.get("licenseSource"),
            "boundary_source_url": sle.get("boundarySourceURL"),
            "correction_kind": "country-bound metadata provenance supersession",
            "legal_license_opinion": False,
        }
        validate_sle_record(record, sle)
        rows.append(record)

    tgo_context = []
    for member in sorted(tgo_members, key=lambda item: item["id"]):
        assert_country_binding(member, "TGO", tgo)
        if member["baseline_license"] != tgo_license:
            raise SystemExit(f"Togo comparison row changed from its source metadata: {member['id']}")
        tgo_context.append({
            "id": member["id"],
            "name": member["name"],
            "country": "TGO",
            "parent_id": member["atlas_parent_id"],
            "parent_chain": member["atlas_parent_chain"],
            "original_assessment_license": member["baseline_license"],
            "source_metadata_license": tgo_license,
            "license_match": True,
        })

    out = {
        "version": 1,
        "issue_number": contract["issue_number"],
        "audit_merge_commit": contract["audit_merge_commit"],
        "baseline_commit": baseline,
        "supersedes": {
            "issue": 479,
            "pr": 746,
            "original_packet": "data/regional-review/regional-review-9d08839e1cdb0c8f/",
            "original_assessment_sha256": pins["assessment_sha256"],
            "original_builder_sha256": pins["builder_sha256"],
            "scope_is_unchanged": True,
            "supersedes_license_provenance_only": True,
        },
        "source_snapshots": {
            "acquired_at_utc_date": acquisition["acquired_at_utc"],
            "SLE": {
                "metadata_path": sle_path,
                "metadata_url": sle_acquisition["catalog_metadata_resolved_url"],
                "gzip_bytes": len(sle_gzip),
                "gzip_sha256": digest(sle_gzip),
                "uncompressed_bytes": len(sle_raw),
                "uncompressed_sha256": digest(sle_raw),
                "represented_vintage": sle["boundaryYearRepresented"],
                "source": sle["boundarySource"],
                "role": sle["boundaryCanonical"],
                "admin_level": sle["boundaryType"],
                "feature_count_declared": int(sle["admUnitCount"]),
                "metadata_declared_license": sle_license,
                "license_source": sle.get("licenseSource"),
                "boundary_source_url": sle.get("boundarySourceURL"),
                "detailed_license_field": sle.get("licenseDetail"),
            },
            "TGO": {
                "metadata_path": tgo_path,
                "metadata_url": tgo_acquisition["catalog_metadata_resolved_url"],
                "gzip_bytes": len(tgo_gzip),
                "gzip_sha256": digest(tgo_gzip),
                "uncompressed_bytes": len(tgo_raw),
                "uncompressed_sha256": digest(tgo_raw),
                "represented_vintage": tgo["boundaryYearRepresented"],
                "source": tgo["boundarySource"],
                "role": tgo["boundaryCanonical"],
                "admin_level": tgo["boundaryType"],
                "feature_count_declared": int(tgo["admUnitCount"]),
                "metadata_declared_license": tgo_license,
                "license_source": tgo.get("licenseSource"),
                "boundary_source_url": tgo.get("boundarySourceURL"),
                "detailed_license_field": tgo.get("licenseDetail"),
            },
        },
        "counts": {
            "sierra_leone_subjects": len(rows),
            "sierra_leone_original_license_mismatches": sum(
                row["original_assessment_license"] != row["corrected_license"] for row in rows),
            "togo_context_rows": len(tgo_context),
            "togo_context_license_matches": sum(row["license_match"] for row in tgo_context),
        },
        "source_terms_and_scope_limit": [
            "The retained geoBoundaries metadata declares the exact license label recorded here; this packet does not independently adjudicate legal licensing.",
            "Sierra Leone and Togo metadata snapshots are retained in the original #479 packet and are pinned by compressed and uncompressed SHA-256; no source archive is recopied or rewritten.",
            "The SLE metadata says represented year 2017, source Government of Sierra Leone, OCHA ROWCA, role Districts, and declares CC BY 3.0 IGO. Its detailed license field is `nan`; the license-source field points to the recorded HDX dataset.",
            "The TGO metadata says represented year 2017, source OpenStreetMap, Wambacher, role Prefectures, and declares CC BY-SA 2.0. Its value is read-only comparison context, not a source for Sierra Leone.",
            "This correction supersedes only the inherited license-provenance field for the 12 SLE rows. It changes no names, IDs, parents, geometries, settlement counts, boundaries, or original records and is not a license legal opinion.",
        ],
        "sierra_leone_rows": rows,
        "togo_read_only_context": tgo_context,
        "input_hashes": {name: {key: value for key, value in row.items() if key != "raw"}
                         for name, row in sorted(inputs.items())},
        "unresolved": [
            "No new boundary or legal administrative-status review is performed.",
            "The source metadata label and attribution URL are reported as retained; detailed license terms are not independently adjudicated.",
            "The corrected metadata attribution does not resolve the original packet's physical land/island, source completeness, statutory-role, or regional-approval limitations.",
        ],
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
