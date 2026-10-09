#!/usr/bin/env python3
"""Build the v1 evidence receipt for the additive #1515 integrity packet."""
from __future__ import annotations

import hashlib
import json
import argparse
import os
import subprocess
from pathlib import Path

from safe_workflow import PACKET, REPO, EXEC, ORIGINAL, EvidenceError, canonical, load_json, require_regular, safe_relative, sha, write_manifest_receipt

ISSUE = 1515
WORKER = "01a10948-7d38-75d0-bc01-4cc28ea41f49"
EVALUATION = "f2b129423c04d32b4b47ea36abae198651c50dae"
BASELINE = "432c5b8e0ac9b9597738a31f5386569312c75966"
ORIGINAL_MERGE = "0c30d0bf9cee9a8c300c7e3c8f45720b471a74ff"
OWNED = "research/geography/eastern-europe-evidence-integrity-1360"
MANIFEST = PACKET / "evidence-quality.json"
SUBJECTS = sorted([
    "gb:BLR:ADM2:67162791B30498032594927",
    "gb:POL:ADM2:97123803B24100086136213",
    "gb:POL:ADM2:97123803B33088815311851",
    "gb:POL:ADM2:97123803B66371363243422",
    "gb:UKR:ADM2:74538382B51634820959847",
    "gb:UKR:ADM2:74538382B5714887404176",
    "gb:UKR:ADM2:74538382B72123275564902",
    "gb:UKR:ADM2:74538382B9478118461291",
    "gb:UKR:ADM2:74538382B97249439308301",
])

# Exact pins declared by the original #1515 work contract. Historical files
# remain bound to the commit at which each alias was actually retained.
PINS = {
    "audited_world_index": (BASELINE, "data/world-index.json", "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03"),
    "delivered_numeric_report": (BASELINE, "coordination/engineering/complete-numeric-closure-diagnosis-20261007/r1/report.json", "e47379a74c053b57781fec04aaedc702ecba24adb773b42bb8c75d142326647a"),
    "delivered_routing_input_config": (BASELINE, "coordination/engineering/global-actionability-routing-20261007/input-config.json", "7623fa8a61b72c33a1560f0ab612e70c463e8c25beef930043c985fd6657f173"),
    "delivered_routing_report": (BASELINE, "coordination/engineering/global-actionability-routing-20261007/results/report.json", "2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265"),
    "scoped_contact_part_0": (BASELINE, "data/geography/part-2.json", "93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf"),
    "scoped_contact_part_1": (BASELINE, "data/geography/part-19.json", "baeade0e3ad11cdd65beb101e7b79284ae2b6ee8794f9b08e86631c7f20e6269"),
    "scoped_contact_part_2": (BASELINE, "data/geography/part-25.json", "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394"),
    "whole_source_transport_gb_BLR_ADM2_0": (BASELINE, "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-BLR-ADM2-000.bin.gz", "308fe6563c7735f625ee11b725a67dda2b729b3c1e1d72034a28edc4e06a120e"),
    "whole_source_transport_gb_POL_ADM2_0": (BASELINE, "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-POL-ADM2-000.bin.gz", "d6ddf97bcf615136b4be684ca630f4eb12eb675f0dd054e409efa492054ff24f"),
    "whole_source_transport_gb_UKR_ADM2_0": (BASELINE, "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-UKR-ADM2-000.bin.gz", "35cef639ce0928d52a51699b0183d5369ba725befec9de43415e8b51664405b9"),
    "research/geography/eastern-europe-border-source-fitness-20261007/produce.py": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/produce.py", "1345d36a60d90d0c49340860125c436826d32e9bed0c17d9459b757c7f1dcaa1"),
    "research/geography/eastern-europe-border-source-fitness-20261007/control-checks.py": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/control-checks.py", "8c3e882b3ddaf4c082d9f42d3f072e1809119ff110b6eaaedde05f1473db4480"),
    "research/geography/eastern-europe-border-source-fitness-20261007/execute.py": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/execute.py", "fdc66851011afe0b20705ba65e0995f69d01601f5fdc11fc97de433081e179bb"),
    "research/geography/eastern-europe-border-source-fitness-20261007/stage_inputs.py": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/stage_inputs.py", "4b40f49f4bd258aa8bd71415a5bca424a3f7bc3f8795ef9e78adb2efb47da909"),
    "research/geography/eastern-europe-border-source-fitness-20261007/build_manifest.py": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/build_manifest.py", "5822aa51684f12aaf4369074caa4671e372329742b575cce8e087fe222f6162e"),
    "research/geography/eastern-europe-border-source-fitness-20261007/inputs/source-custody.json": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/inputs/source-custody.json", "db511bb8db98154ea189e6c0f8e3a6551277e68873084e0148e875a46e8cb01f"),
    "research/geography/eastern-europe-border-source-fitness-20261007/runs/run-one/run-summary.json": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/runs/run-one/run-summary.json", "5588dd339fe0a485e54bae8db4c283f8c6614b97e44f4fc55505c0aa1d4e6e9e"),
    "research/geography/eastern-europe-border-source-fitness-20261007/runs/run-two/run-summary.json": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/runs/run-two/run-summary.json", "5588dd339fe0a485e54bae8db4c283f8c6614b97e44f4fc55505c0aa1d4e6e9e"),
    "research/geography/eastern-europe-border-source-fitness-20261007/runs/run-two/source-fitness.json": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/runs/run-two/source-fitness.json", "ca80125002ab89d57b6208405402755e1be072bddec31fe792ea15063f4ce029"),
    "research/geography/eastern-europe-border-source-fitness-20261007/history/two-run-summary.json": (ORIGINAL_MERGE, "research/geography/eastern-europe-border-source-fitness-20261007/history/two-run-summary.json", "8e63d399e9e6a9c0c9691ecb7a2a559dabc69232e932a95912931270f93a2cd2"),
}


def git_bytes(commit: str, path: str) -> tuple[bytes, str]:
    raw = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO,
                         check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    row = subprocess.run(["git", "ls-tree", commit, "--", path], cwd=REPO,
                         check=True, text=True, stdout=subprocess.PIPE).stdout.split()
    if len(row) < 4 or row[3] != path or row[0] not in ("100644", "100755"):
        raise EvidenceError(f"historical ordinary-file pin is absent: {commit}:{path}")
    return raw, row[0]


def descriptor(path: Path, role: str) -> dict:
    raw = require_regular(path)
    return {"path": path.relative_to(REPO).as_posix(), "bytes": len(raw),
            "sha256": sha(raw), "hash_kind": "file-bytes", "role": role}


def packet_evidence_files():
    """Only inventory the selected successful workspace and packet-level sources/code."""
    for path in sorted(PACKET.rglob("*")):
        if not path.is_file() or path.is_symlink() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.parent == PACKET or path.is_relative_to(EXEC):
            yield path


def main() -> None:
    global EXEC
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default="execution", help="existing successful run directory under the owned packet")
    args = parser.parse_args()
    EXEC = PACKET / safe_relative(Path(args.workspace), PACKET)
    if not (EXEC / "fresh-execution.json").is_file():
        raise EvidenceError("complete two-run success receipt is missing")
    if not (EXEC / "controls/producer-negative-control.json").is_file():
        raise EvidenceError("actual producer negative controls are missing")
    if not (EXEC / "controls/writer-and-comparison-controls.json").is_file():
        raise EvidenceError("safe-writer and actual-product comparison controls are missing")
    if MANIFEST.exists() or MANIFEST.is_symlink():
        raise EvidenceError("evidence manifest already exists; never replace an earlier receipt")

    historical = []
    pins = {}
    pin_files = {}
    for name, (commit, path, expected_sha) in PINS.items():
        raw, mode = git_bytes(commit, path)
        digest = sha(raw)
        if digest != expected_sha:
            raise EvidenceError(f"issue pin changed: {name}")
        historical.append({"path": path, "commit": commit, "bytes": len(raw),
                           "sha256": digest, "hash_kind": "file-bytes",
                           "git_mode": mode, "role": "original-source" if path.startswith(("data/geography/", "coordination/engineering/original-geography-source-corpus")) else "baseline-reference"})
        pins[name] = digest
        pin_files[name] = {"path": path, "commit": commit}

    subject_files = {}
    for subject in SUBJECTS:
        country = subject.split(":")[1]
        part = {"BLR": "data/geography/part-2.json", "POL": "data/geography/part-19.json",
                "UKR": "data/geography/part-25.json"}[country]
        subject_files[subject] = {"path": part, "commit": BASELINE}

    old = load_json(ORIGINAL / "evidence-quality.json")
    source_files = set()
    sources = []
    for old_source in old["sources"]:
        source = {k: v for k, v in old_source.items() if k != "files"}
        files = []
        for old_file in old_source.get("files", []):
            marker = "/inputs/"
            if marker not in old_file["path"]:
                raise EvidenceError(f"unexpected inherited source path: {old_file['path']}")
            rel = Path(old_file["path"].split(marker, 1)[1])
            copied = EXEC / "staged-inputs" / rel
            file_desc = descriptor(copied, "retained-original-source")
            files.append(file_desc)
            source_files.add(file_desc["path"])
        if files:
            source["files"] = files
        sources.append(source)

    outputs = []
    for path in packet_evidence_files():
        if path == MANIFEST:
            continue
        relative = path.relative_to(REPO).as_posix()
        if relative in source_files:
            continue
        if path.name == "README.md":
            role = "research-summary"
        elif path.suffix == ".py":
            role = "reproduction-code" if path.parent == PACKET else "preserved-code-copy"
        elif "staged-inputs/baseline/" in relative:
            role = "baseline-custody-copy"
        elif relative.endswith("staged-inputs/source-custody.json"):
            role = "source-custody-index"
        elif "staged-inputs/" in relative:
            role = "control-fixture-copy" if "tampered-inputs/" in relative else "retained-input-copy"
        elif "/runs/" in relative:
            role = "generated-result"
        elif "/history/" in relative or relative.endswith("fresh-execution.json"):
            role = "execution-receipt"
        elif "/controls/" in relative:
            role = "control-evidence"
        else:
            role = "reproduction-code-or-evidence"
        outputs.append(descriptor(path, role))

    # The machine-readable receipt accounts for each newly added path, including
    # itself, while source files remain indexed in their source records.
    changes = [{"path": path.relative_to(REPO).as_posix(), "status": "added"}
               for path in packet_evidence_files() if path != MANIFEST]
    changes.append({"path": MANIFEST.relative_to(REPO).as_posix(), "status": "added"})
    changes.sort(key=lambda x: x["path"])

    generated = load_json(EXEC / "fresh-execution.json")
    run_prefix = f"{OWNED}/{EXEC.relative_to(PACKET).as_posix()}"
    positive_path = f"{run_prefix}/controls/positive-control.json"
    negative_path = f"{run_prefix}/controls/producer-negative-control.json"
    comparison_path = f"{run_prefix}/controls/writer-and-comparison-controls.json"
    reproducibility_path = f"{run_prefix}/controls/reproducibility.json"
    controls_dir = EXEC / "controls"
    positive = load_json(controls_dir / "positive-control.json")
    negative = load_json(controls_dir / "producer-negative-control.json")
    reproducibility = load_json(controls_dir / "reproducibility.json")
    writer_controls = load_json(controls_dir / "writer-and-comparison-controls.json")
    if (positive.get("kind") != "positive-control" or positive.get("outcome") != "passed" or
            negative.get("kind") != "negative-control" or negative.get("outcome") != "passed" or
            reproducibility.get("kind") != "reproducibility" or reproducibility.get("outcome") != "passed" or
            writer_controls.get("kind") != "negative-control" or writer_controls.get("outcome") != "passed"):
        raise EvidenceError("a complete successful control receipt set is missing")
    if generated.get("status") != "passed" or generated.get("comparison", {}).get("identical") is not True:
        raise EvidenceError("two-run success receipt does not verify actual complete products")

    methods = [
        {"id": "frozen-producer", "kind": "source", "description": "Run the exact pinned #1344 producer against the exact source-custody input tree in two fresh admitted namespaces; compare all actual products to their declared actual summaries and historical whole-file pins.", "software": "Python 3.12.14; NumPy 2.3.5; pyproj 3.7.2; Shapely 2.1.2; GEOS 3.13.1", "units": "whole-file bytes and SHA-256; no new geographic unit or measurement"},
        {"id": "safe-writers", "kind": "code", "description": "Exercise exclusive complete-set staging/receipt admission, the actual producer's six rejection branches, and changed/missing/false actual-output controls with sentinel preservation.", "software": "Python 3.12.14; standard library", "units": "file existence, byte lengths, SHA-256, exit status, and exact rejection reason"},
    ]
    validation = [
        {"method_id": "frozen-producer", "kind": "positive-control", "outcome": "passed", "evidence_path": positive_path},
        {"method_id": "frozen-producer", "kind": "negative-control", "outcome": "passed", "evidence_path": negative_path},
        {"method_id": "frozen-producer", "kind": "reproducibility", "outcome": "passed", "evidence_path": reproducibility_path},
        {"method_id": "safe-writers", "kind": "negative-control", "outcome": "passed", "evidence_path": comparison_path},
    ]
    manifest = {
        "version": 1, "issue": ISSUE, "lane": "geography", "worker_id": WORKER,
        "subject_ids": SUBJECTS,
        "subject_ids_sha256": hashlib.sha256(json.dumps(SUBJECTS, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
        "baseline": {"version": 2, "commit": EVALUATION, "files": historical, "pins": pins,
                     "pin_files": pin_files, "subject_files": subject_files},
        "sources": sources,
        "outputs": outputs,
        "methods": methods,
        "metrics": [], "summaries": [], "metric_bindings": [], "record_checks": [],
        "validation": validation,
        "conclusions": [
            {"source_ids": ["geoboundaries-blr-adm2-simplified", "geoboundaries-pol-adm2-simplified", "geoboundaries-ukr-adm2-simplified"], "status": "supported", "text": "The frozen complete Belarus, Poland and Ukraine simplified ADM2 source bytes, feature inventory, and nine exact source-shapeID joins reproduce the inherited #1344 assessment. This is byte/source inventory evidence only; represented years, national authority, effective dates, positional accuracy, and legal boundary are not newly verified."},
            {"source_ids": ["natural-earth-10m-lakes"], "status": "supported", "text": "The inherited Natural Earth 10m major-lakes scan is retained and reproduced; its coverage is incomplete hydrology and cannot establish the candidate is dry land."},
            {"source_ids": ["geoboundaries-blr-adm2-simplified", "geoboundaries-pol-adm2-simplified", "geoboundaries-ukr-adm2-simplified", "natural-earth-10m-lakes", "gshhg-physical-context"], "status": "unresolved", "text": "Candidate cause and partition, current physical class, legal boundary, historical ownership, effective dates, positional accuracy, source lineage, source authority, licensing interpretation, and permitted engineering/publication action remain unresolved. No regional approval or completion is claimed."},
        ],
        "stages": {"research": "complete", "implementation": "proposed", "geographic_approval": "unapproved"},
        "commands": [
            f"PYTHONDONTWRITEBYTECODE=1 python3.12 research/geography/eastern-europe-evidence-integrity-1360/safe_workflow.py --fresh --workspace {EXEC.relative_to(PACKET).as_posix()}",
            f"PYTHONDONTWRITEBYTECODE=1 python3.12 research/geography/eastern-europe-evidence-integrity-1360/safe_workflow.py --controls --workspace {EXEC.relative_to(PACKET).as_posix()}",
            f"PYTHONDONTWRITEBYTECODE=1 python3.12 research/geography/eastern-europe-evidence-integrity-1360/build_manifest.py --workspace {EXEC.relative_to(PACKET).as_posix()}",
            "node scripts/evidence-quality.mjs research/geography/eastern-europe-evidence-integrity-1360/evidence-quality.json",
        ],
        "change_receipts": changes,
    }
    write_manifest_receipt(MANIFEST, canonical(manifest))
    print(json.dumps({"status": "built", "baseline_pins": len(pins), "subjects": len(SUBJECTS),
                      "sources": len(sources), "outputs": len(outputs), "changed_paths": len(changes)}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except EvidenceError as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True))
        raise SystemExit(2)
