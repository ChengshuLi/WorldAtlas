#!/usr/bin/env python3
"""Reproduce the scoped XLSX decoded-member inventory correction."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import types
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
OWNED = "research/geography/chn-tjk-workbook-inventory-1127-erratum/"
BASELINE_COMMIT = "432c5b8e0ac9b9597738a31f5386569312c75966"
SHARED = "research/geography/shared-seam-chn-tjk-admin-reference-20261006/"
SOURCE = SHARED + "sources/tajik-stat-admin-units-2025.xlsx"
OLD_INVENTORY = SHARED + "sources/source-inventory.json"
ORIGINAL_SCRIPT = SHARED + "scripts/inspect_admin_table.py"
ORIGINAL_MANIFEST = SHARED + "evidence-quality.json"
HELPER = "scripts/evidence/immutable.py"
SUBJECTS = [
    "gb:CHN:ADM2:17275852B723995182906",
    "gb:CHN:ADM2:17275852B99352197075157",
    "gb:TJK:ADM2:16282066B16686410577714",
]
SOURCE_SHA = "c0576b220fa3d2b7281d4c4680b3e143a523dec3a733c0fe3eba23ed91e47e40"
CORRECTED_STYLES_SHA = "7ccd4c42f9df7e401782679d46e7bd2f1c67a3b30fbaf8be3ed51331e9041a2b"
HISTORICAL_STYLES_SHA = "7ccd4c42f9df7e401782679d46e7bd8b8c5a2d83205b23ca43104054ceaa971f0"

# Reviewed whole-file pins from the exact immutable baseline.
PINS = [
    {"path": SOURCE, "bytes": 11242, "sha256": SOURCE_SHA, "hash_kind": "file-bytes"},
    {"path": OLD_INVENTORY, "bytes": 8168, "sha256": "9ff39b033b63ad7f10e2b7a5fec8ecb025f99d65c54365224d77d30e54169f6a", "hash_kind": "file-bytes"},
    {"path": ORIGINAL_SCRIPT, "bytes": 4947, "sha256": "3bd574fa5ec541348f37673243702cdf92cacc46072aff410e2bae6488865a8b", "hash_kind": "file-bytes"},
    {"path": ORIGINAL_MANIFEST, "bytes": 24472, "sha256": "c9e0961cc6483acbe13d98bb4a2dc25596563a44ca7b1ad7ad276b0739c3986a", "hash_kind": "file-bytes"},
    {"path": HELPER, "bytes": 17414, "sha256": "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46", "hash_kind": "file-bytes"},
    {"path": "data/world-index.json", "bytes": 944, "sha256": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03", "hash_kind": "file-bytes"},
    {"path": "data/geography/part-3.json", "bytes": 5153118, "sha256": "e28e1ef867d6550ad65964125bd86a8f1d0919e4834e0d920af4046145a00617", "hash_kind": "file-bytes"},
    {"path": "data/geography/part-23.json", "bytes": 4962410, "sha256": "d61082ccd69b319723fadc4cad582b8d5c8a8ced3e50b4f90f00b4eb17e6a9c2", "hash_kind": "file-bytes"},
]

def need(condition, message):
    if not condition:
        raise ValueError(message)


def descriptor(path, raw):
    return {"path": path, "bytes": len(raw), "sha256": sha256(raw), "hash_kind": "file-bytes"}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def capture_inputs():
    helper_pin = PINS[4]
    helper_bytes = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:{HELPER}"])
    need(len(helper_bytes) == helper_pin["bytes"] and hashlib.sha256(helper_bytes).hexdigest() == helper_pin["sha256"],
         "Pinned immutable helper bytes disagree")
    need((ROOT / HELPER).read_bytes() == helper_bytes, "Materialized immutable helper differs from captured baseline code")
    helper = types.ModuleType("worldatlas_immutable")
    exec(compile(helper_bytes, str(ROOT / HELPER), "exec"), helper.__dict__)
    baseline = helper.Baseline(ROOT, BASELINE_COMMIT, PINS)
    # The code and legacy reader actually materialized in this checkout must be
    # the exact bytes authenticated above; source and inventory are consumed as
    # the returned pinned Git-blob bytes below.
    need(baseline.materialized_bytes(HELPER) == helper_bytes, "Consumed helper bytes differ from captured code")
    baseline.materialized_bytes(ORIGINAL_SCRIPT)
    source = baseline.pinned_bytes(SOURCE)
    old_inventory = json.loads(baseline.pinned_bytes(OLD_INVENTORY))
    prior_manifest = json.loads(baseline.pinned_bytes(ORIGINAL_MANIFEST))
    for name in ("data/geography/part-3.json", "data/geography/part-23.json"):
        baseline.pinned_bytes(name)
    mapping = prior_manifest["baseline"]["subject_files"]
    need(mapping == {
        SUBJECTS[0]: "data/geography/part-3.json",
        SUBJECTS[1]: "data/geography/part-3.json",
        SUBJECTS[2]: "data/geography/part-23.json",
    }, "Original subject-to-containing-file mapping drifted")
    for subject, name in mapping.items():
        record = json.loads(baseline.pinned_bytes(name))
        matches = [x for x in record["features"] if x.get("id") == subject or x.get("properties", {}).get("id") == subject]
        need(len(matches) == 1, "Subject missing/duplicated in pinned containing file: " + subject)
    workbook_records = [x for x in old_inventory["sources"] if x["id"] == "tajik-stat-admin-units-2025"]
    need(len(workbook_records) == 1, "Expected unique historical workbook inventory")
    prior = workbook_records[0]
    need(prior["encoded_bytes"] == len(source) and prior["encoded_sha256"] == SOURCE_SHA,
         "Historical whole-workbook byte pin disagrees")
    return baseline, source, prior, helper


def verify_archive(source, expected):
    """Return exact complete-member descriptors, rejecting incomplete inventory."""
    if not isinstance(expected, list) or not expected:
        raise ValueError("Expected inventory must be a nonempty member list")
    expected_by_name = {}
    for entry in expected:
        if set(entry) != {"path", "bytes", "sha256"} or not isinstance(entry["path"], str):
            raise ValueError("Malformed expected member record")
        if entry["path"] in expected_by_name or not isinstance(entry["bytes"], int) or entry["bytes"] < 0:
            raise ValueError("Duplicate member or invalid decoded size")
        # Keep the historical 65-character bad value representable so the
        # original inventory is rejected by the same byte comparison at the
        # actual member, rather than by a special-case fixture rule.
        if not isinstance(entry["sha256"], str) or not re.fullmatch(r"[a-f0-9]{1,128}", entry["sha256"]):
            raise ValueError("Invalid expected digest")
        expected_by_name[entry["path"]] = entry
    with zipfile.ZipFile(io.BytesIO(source), "r") as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise ValueError("ZIP archive contains duplicate member names")
        if set(names) != set(expected_by_name):
            raise ValueError("ZIP member name inventory mismatch")
        rows = []
        decoded_total = 0
        for item in infos:
            digest = hashlib.sha256()
            count = 0
            with archive.open(item, "r") as stream:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    count += len(chunk)
                    decoded_total += len(chunk)
                    if count > 32 * 1024 * 1024 or decoded_total > 256 * 1024 * 1024:
                        raise ValueError("Decoded ZIP member/phase exceeds byte limit")
                    digest.update(chunk)
            row = {"path": item.filename, "bytes": count, "sha256": digest.hexdigest()}
            if row["bytes"] != expected_by_name[item.filename]["bytes"] or row["sha256"] != expected_by_name[item.filename]["sha256"]:
                raise ValueError("Decoded member size/digest mismatch: " + item.filename)
            rows.append(row)
    if decoded_total != sum(row["bytes"] for row in rows):
        raise ValueError("Decoded complete-member aggregate does not reconcile")
    rows.sort(key=lambda row: row["path"])
    return {"member_count": len(rows), "decoded_bytes_total": decoded_total, "members": rows}


def corrected_inventory(prior):
    result = [{"path": x["path"], "bytes": x["bytes"], "sha256": x["sha256"]} for x in prior["members"]]
    hit = [x for x in result if x["path"] == "xl/styles.xml"]
    need(len(hit) == 1 and hit[0]["sha256"] == HISTORICAL_STYLES_SHA and hit[0]["bytes"] == 5820,
         "Historical styles.xml defect did not match declared erratum")
    hit[0]["sha256"] = CORRECTED_STYLES_SHA
    return result


def reject(expected, source, contains):
    try:
        verify_archive(source, expected)
    except (ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        return contains in str(exc)
    return False


def mutate_archive(source, omit=None, duplicate=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source), "r") as original, zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as output:
        for info in original.infolist():
            if info.filename != omit:
                output.writestr(info.filename, original.read(info))
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                output.writestr(duplicate, original.read(duplicate))
    return stream.getvalue()


def outputs_for(source, prior, baseline):
    expected = corrected_inventory(prior)
    inventory = verify_archive(source, expected)
    historical = [{"path": x["path"], "bytes": x["bytes"], "sha256": x["sha256"]} for x in prior["members"]]
    tampered = [dict(x) for x in expected]
    tampered[0]["sha256"] = "0" * 64
    duplicate_zip = mutate_archive(source, duplicate="xl/styles.xml")
    missing_zip = mutate_archive(source, omit="xl/styles.xml")
    controls = {
        "corrected_inventory_accepts_all_complete_members": verify_archive(source, expected) == inventory,
        "historical_inventory_rejected_at_styles_member": reject(historical, source, "xl/styles.xml"),
        "single_wrong_digest_rejected_by_same_checker": reject(tampered, source, "Decoded member size/digest mismatch"),
        "duplicate_member_archive_rejected": reject(expected, duplicate_zip, "duplicate member names"),
        "missing_member_archive_rejected": reject(expected, missing_zip, "member name inventory mismatch"),
    }
    need(all(controls.values()), "One or more semantic positive/adverse controls failed")
    actual = {x["path"]: x for x in inventory["members"]}
    old = {x["path"]: x for x in historical}
    differences = [name for name in sorted(actual) if actual[name] != old[name]]
    need(differences == ["xl/styles.xml"], "Correction must differ from history only at styles.xml")
    execution = {
        "kind": "complete-decoded-zip-member-inventory",
        "baseline_commit": BASELINE_COMMIT,
        "retrieved_at": "2026-10-07",
        "whole_workbook": descriptor(SOURCE, source),
        "helper": PINS[4],
        "original_inventory": PINS[1],
        "original_subjects": SUBJECTS,
        "method": "Python standard-library zipfile; stream each complete member body to EOF (CRC checked); SHA-256 over decoded member bytes",
        "runtime": {"python": sys.version.split()[0], "implementation": sys.implementation.name},
        "limits": [
            "Workbook administrative counts as of 2025-01-01; not boundary geometry.",
            "This packet does not establish current territorial assignment, geometry completeness, border placement, or neighboring granularity.",
            "No new legal review or official page acquisition; prior workbook CC BY 4.0 statement is not re-adjudicated here.",
        ],
    }
    positive = {"method_id": "zip-member-inventory", "kind": "positive-control", "outcome": "passed",
                "member_count": inventory["member_count"], "decoded_bytes_total": inventory["decoded_bytes_total"],
                "actual_styles_member": actual["xl/styles.xml"]}
    negative = {"method_id": "zip-member-inventory", "kind": "negative-control", "outcome": "passed", "controls": controls,
                "historical_styles_sha256": old["xl/styles.xml"]["sha256"],
                "corrected_styles_sha256": actual["xl/styles.xml"]["sha256"],
                "differing_member_names": differences}
    return inventory, positive, negative, execution


def run(vintage):
    baseline, source, prior, helper = capture_inputs()
    names = ["member-inventory.json", "positive-control.json", "negative-control.json", "execution.json"]
    destination = helper.NewVintage(baseline, OWNED, vintage, names)
    inventory, positive, negative, execution = outputs_for(source, prior, baseline)
    destination.publish({"member-inventory.json": inventory, "positive-control.json": positive,
                         "negative-control.json": negative, "execution.json": execution})
    print(destination.root.relative_to(ROOT))


def compare(first, second, vintage):
    baseline, _, _, helper = capture_inputs()
    paths = [ROOT / OWNED / "vintages" / name for name in (first, second)]
    payload_names = ["member-inventory.json", "positive-control.json", "negative-control.json", "execution.json"]
    payloads = []
    publications = []
    for root in paths:
        publication_raw = (root / "publication.json").read_bytes()
        publication = json.loads(publication_raw)
        declared = {x["path"].split("/")[-1]: x for x in publication["outputs"]}
        need(set(declared) == set(payload_names), "Publication has incomplete or unexpected outputs")
        current = {}
        for name in payload_names:
            raw = (root / name).read_bytes()
            need(declared[name]["bytes"] == len(raw) and declared[name]["sha256"] == sha256(raw),
                 "Publication descriptor mismatch: " + name)
            current[name] = raw
        payloads.append(current)
        publications.append(descriptor(str((root / "publication.json").relative_to(ROOT)), publication_raw))
    need(all(payloads[0][name] == payloads[1][name] for name in payload_names), "Complete deterministic result files differ")
    comparison = {
        "method_id": "zip-member-inventory",
        "kind": "reproducibility",
        "outcome": "passed",
        "run_vintages": [first, second],
        "payload_names": payload_names,
        "byte_identical_payloads": True,
        "payload_sha256": {name: sha256(payloads[0][name]) for name in payload_names},
        "run_one_sha256": sha256(payloads[0]["member-inventory.json"]),
        "run_two_sha256": sha256(payloads[1]["member-inventory.json"]),
        "publication_receipts": publications,
        "note": "Run payloads are identical; publication receipts differ only because their output paths name distinct fresh vintages.",
    }
    destination = helper.NewVintage(baseline, OWNED, vintage, ["reproducibility.json"])
    destination.publish({"reproducibility.json": comparison})
    print(destination.root.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True)
    parser.add_argument("--compare", nargs=2, metavar=("FIRST", "SECOND"))
    args = parser.parse_args()
    if args.compare:
        compare(*args.compare, args.vintage)
    else:
        run(args.vintage)


if __name__ == "__main__":
    main()
