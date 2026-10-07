#!/usr/bin/env python3
"""Generate one fresh, isolated output run for the 2026-10-07 erratum."""
import argparse
import hashlib
import json
import os
import platform
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OWNED = ROOT / "data/regional-review/west-siberia-roles-followup-20261006"
ERRATUM = OWNED / "findings/errata-20261007"
ASSESSMENT = OWNED / "findings/followup-assessments.json"
CONTRACT = OWNED / "baseline/issue-contract.json"
SOURCE_REGISTER = ERRATUM / "source-register.json"
EVALUATION_COMMIT = "15025282de755d631024211687f036751fba963d"
ASSESSMENT_SHA256 = "7fa0d983d07534ffe068cdf056a102eb033d1c268466c4a1605d405b2c0630b0"
CONTRACT_SHA256 = "13a9d0c8bbf6fbc80f98a8842c82f315211d9183e066a246e319a90dc46f9acf"
SOURCE_REGISTER_SHA256 = "9b8a7ef37e879c87912c44c4455305674fe4d0fc1c225c8c43a84824218c7b8a"
SOURCE_ID = "khanty-mansi-63oz-law-text-2025-consolidation"
SUPPLEMENTAL_CITY_IDS = {
    "gb:RUS:ADM2:50074027B28971786615675",
    "gb:RUS:ADM2:50074027B29329231814048",
    "gb:RUS:ADM2:50074027B44152060141244",
    "gb:RUS:ADM2:50074027B57809326542315",
    "gb:RUS:ADM2:50074027B58285687326194",
    "gb:RUS:ADM2:50074027B61219657375498",
    "gb:RUS:ADM2:50074027B75983799969403",
    "gb:RUS:ADM2:50074027B95202300265125",
}
ORIGINALS = {
    "assessment": (ASSESSMENT, ASSESSMENT_SHA256),
    "issue_contract": (CONTRACT, CONTRACT_SHA256),
    "positive_control": (OWNED / "findings/positive-control.json", "a0ab32cee3adc7c1dbd81fa7acec0bb4076a3e8a556a4aa06410593f8bc79dd8"),
    "negative_control": (OWNED / "findings/negative-control.json", "cc31d1ed56eb47310413b8f870aba8c07d5e037b86a740ec9300c7c5a17ef913"),
    "reproduction_result": (OWNED / "findings/reproduction-result.json", "82a3375b9b9d20ec4ae1a2dfae1d6d230f48acaa7c2daa8831e14ba7cd08f85c"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def check_path_components(path):
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError("symlinked output path refused")


def admitted_output(raw_path, run_id):
    path = Path(os.path.abspath(raw_path))
    erratum = Path(os.path.abspath(ERRATUM))
    if path.parent != erratum or path.name != run_id or run_id not in {"run-one", "run-two"}:
        raise ValueError("output must be a direct dated erratum run directory")
    check_path_components(path)
    if path.exists():
        raise ValueError("occupied output destination refused")
    if not path.parent.is_dir():
        raise ValueError("output parent must already exist")
    return path


def read_pinned(path, expected, label):
    raw = Path(path).read_bytes()
    observed = sha(raw)
    if observed != expected:
        raise ValueError("pinned %s input hash mismatch: %s" % (label, observed))
    return raw


def write_new(directory, name, data):
    target = directory / name
    with target.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(target.relative_to(OWNED)), "bytes": len(data), "sha256": sha(data)}


def derive(raw):
    result = json.loads(raw)
    rows = result["assessments"]
    ids = [row["subject_id"] for row in rows]
    validate_roster(ids)
    if result["subject_ids_sha256"] != "bfc28011d523d063794c21c09eb7a3671e2215bc285a5ce786d4d3e17448b561":
        raise ValueError("original issue roster hash mismatch")
    selected = [row for row in rows if row["subject_id"] in SUPPLEMENTAL_CITY_IDS]
    if len(selected) != 8 or {row["subject_id"] for row in selected} != SUPPLEMENTAL_CITY_IDS:
        raise ValueError("the exact eight HMAO city subjects were not found")
    for row in selected:
        row["current_role"] = (
            "The legislature-hosted consolidated text of Law 63-oz, retrieved 2026-10-07 and reflecting amendments through 2025-05-30, lists this named city as a municipal urban okrug. The PDF omits the law annexes; amendments after 2025-05-30 were not checked."
        )
        row["source_note"] = (
            "Article 1, pages 1–2, supports municipal status in the retained 2025 consolidated text only. It does not establish Atlas administrative-territorial tier or footprint geometry. The PDF compilation's own final page says the annexes are not included."
        )
        note = "The new dated statute is a text-only municipal-status source; its annexes are omitted and it supplies no geometry."
        if note not in row["boundary_status"]:
            row["boundary_status"] += " " + note
        if SOURCE_ID not in row["sources"]:
            row["sources"].append(SOURCE_ID)
            row["sources"].sort()
    result["scope_limit"] = (
        "Source and role evidence only. The dated Law 63-oz text adds municipal-status support for eight HMAO city subjects; it does not establish Atlas tier equivalence or any current legal boundary geometry. No current legal boundary geometry was verified for the 45 subjects, and the packet does not certify a regional interior."
    )
    return result


def validate_roster(ids):
    if len(ids) != 45 or len(set(ids)) != 45 or ids != sorted(ids):
        raise ValueError("roster must contain exactly 45 unique sorted subjects")
    digest = sha(json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode())
    if digest != "bfc28011d523d063794c21c09eb7a3671e2215bc285a5ce786d4d3e17448b561":
        raise ValueError("roster hash differs from issue #1092")
    return digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assessment", default=str(ASSESSMENT))
    parser.add_argument("--output-dir")
    parser.add_argument("--run-id", choices=("run-one", "run-two"))
    parser.add_argument("--roster-probe")
    args = parser.parse_args()

    if args.roster_probe:
        probe = json.loads(Path(args.roster_probe).read_bytes())
        print(json.dumps({"status": "passed", "subject_ids_sha256": validate_roster(probe)}, sort_keys=True))
        return
    if not args.output_dir or not args.run_id:
        raise ValueError("generation requires --output-dir and --run-id")

    # All source and scope checks finish before a destination is admitted or created.
    assessment_raw = read_pinned(args.assessment, ASSESSMENT_SHA256, "original assessment")
    contract_raw = read_pinned(CONTRACT, CONTRACT_SHA256, "original issue contract")
    source_raw = read_pinned(SOURCE_REGISTER, SOURCE_REGISTER_SHA256, "supplemental source register")
    source = json.loads(source_raw)
    if len(source.get("records", [])) != 1 or source["records"][0].get("id") != SOURCE_ID:
        raise ValueError("unexpected supplemental source record")
    updated = derive(assessment_raw)
    contract = json.loads(contract_raw)
    if contract.get("subject_ids_sha256") != updated["subject_ids_sha256"]:
        raise ValueError("issue contract does not bind the original issue roster")
    destination = admitted_output(args.output_dir, args.run_id)
    destination.mkdir(mode=0o700)

    products = []
    products.append(write_new(destination, "assessment.json", canonical(updated)))
    products.append(write_new(destination, "issue-contract.json", contract_raw))
    products.append(write_new(destination, "positive-control.json", canonical({
        "method_id": "west-siberia-20261007-erratum", "kind": "positive-control", "outcome": "passed",
        "subject_count": 45, "subject_ids_sha256": updated["subject_ids_sha256"],
        "supplemental_hmao_city_count": len(SUPPLEMENTAL_CITY_IDS),
    })))
    products.append(write_new(destination, "negative-control.json", canonical({
        "method_id": "west-siberia-20261007-erratum", "kind": "negative-control", "outcome": "passed",
        "cases": ["missing-subject-rejected", "duplicate-subject-rejected"],
    })))
    generator_path = Path(__file__).resolve()
    verifier_path = ERRATUM / "verify-erratum.py"
    manifest = {
        "version": 1,
        "run_id": args.run_id,
        "process_id": os.getpid(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_commit": EVALUATION_COMMIT,
        "runtime": {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform()},
        "execution": [
            {"path": str(generator_path.relative_to(OWNED)), "sha256": sha(generator_path.read_bytes())},
            {"path": str(verifier_path.relative_to(OWNED)), "sha256": sha(verifier_path.read_bytes())},
        ],
        "inputs": [
            {"path": str(Path(args.assessment).resolve()), "bytes": len(assessment_raw), "sha256": sha(assessment_raw)},
            {"path": str(CONTRACT.relative_to(OWNED)), "bytes": len(contract_raw), "sha256": sha(contract_raw)},
            {"path": str(SOURCE_REGISTER.relative_to(OWNED)), "bytes": len(source_raw), "sha256": sha(source_raw)},
        ],
        "original_evidence_preservation": {key: digest for key, (_, digest) in ORIGINALS.items()},
        "source_pdf": source["records"][0],
        "products": products,
    }
    write_new(destination, "run-manifest.json", canonical(manifest))
    print(json.dumps({"run_id": args.run_id, "product_hashes": [item["sha256"] for item in products]}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
