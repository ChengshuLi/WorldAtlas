#!/usr/bin/env python3
"""Pin the issue-1492 immutable baseline before parsing source or geometry inputs."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
OWNED = "research/geography/norway-adm2-source-fit-1492/"
VINTAGE = "baseline-20261008"
OUT = "baseline-admission.json"

IDS = [
    "153efbdb9c28eaba9ef8c4c834577ea44c875c2412493c2581530c2d9c7085f1",
    "1f453e7a436aa2f6a68edfb7433d3d1ec05c72b37ba78fac9b3d2542bc085efb",
    "1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b",
    "4f57d0af8235d8f547395c5d94bfeeb57e8e11168f65b7a566407213d17f1e5c",
    "764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384",
    "7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35",
    "8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9",
    "a82c3dc9980bf083cf15fb0edf1b98301259afb93761549c97ec57d73a41c5ce",
    "a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803",
    "b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a",
    "cc11d3c9c7f82d8c9073539568d8af915da17e21904a60a75d49eb5d2e63ae94",
    "dc92c796890cece117d3a70e1422fc2682a46caf3db64f06b2935b46e31b7a9f",
    "e0bd74d0efc769aa5b98ba28ca22d0b37692f3387d344e32c14516b0fe062904",
    "eb2b6c25d1a8b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40",
    "f082e1ba3a2d1267b17f803511ec164c9c8649fd3fb9cc2bc752a4c833659508",
]

def inputs():
    paths = [
        "data/geography/part-17.json",
        "data/hierarchy.json",
        "data/administrative-sources.json",
        "data/geographic-releases/current-manifest.json",
        "coordination/engineering/original-geography-source-corpus-20261006/catalogue.json",
        "coordination/engineering/original-geography-source-corpus-20261006/evidence-quality.json",
        "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-NOR-ADM1-000.bin.gz",
        "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-NOR-ADM2-000.bin.gz",
        "research/geography/gap-source-nordic-shared-seams-20261006/gb-NOR-ADM2-original-simplified.geojson",
        "research/geography/gap-source-nordic-shared-seams-20261006/evidence-quality.json",
        "coordination/engineering/global-source-comparisons-a-001-20261006/evidence-quality.json",
        "coordination/engineering/global-source-comparisons-a-001-20261006/source-catalogue.json",
        "coordination/engineering/global-source-comparisons-a-001-20261006/scope.json",
        "coordination/engineering/global-source-comparisons-a-001-20261006/supplemental-input-pins.json",
        "coordination/engineering/global-actionability-routing-20261007/evidence-quality.json",
        "coordination/engineering/global-actionability-routing-20261007/results/land-source-fitness-000.bin.gz",
        "coordination/engineering/global-actionability-routing-20261007/results/controls.json",
        "coordination/engineering/global-physical-comparison-20261006/evidence-quality.json",
        "scripts/evidence/immutable.py",
        "scripts/evidence/geometry.py",
    ]
    paths += [
        f"coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-{i:03d}.json.gz"
        for i in range(12)
    ]
    paths += [
        f"coordination/engineering/global-actionability-routing-20261007/results/families-{i:03d}.bin.gz"
        for i in range(14)
    ]
    return paths

def baseline_class():
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline
    return Baseline

def main():
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    branch = subprocess.check_output(["git", "-C", str(ROOT), "branch", "--show-current"], text=True).strip()
    if head != COMMIT or branch != "geography/norway-adm2-source-fit-1492":
        raise SystemExit(f"Refuse baseline drift: {head=} {branch=}")
    status = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain=v2", "--untracked-files=all"], text=True)
    # This script must be the only pre-admission untracked file.
    expected = "? research/geography/norway-adm2-source-fit-1492/prepare.py\n"
    if status != expected:
        raise SystemExit("Unexpected worktree changes before baseline admission")
    paths = inputs()
    descriptors = []
    for path in paths:
        raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{COMMIT}:{path}"])
        descriptors.append({"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "hash_kind": "file-bytes"})
    Baseline = baseline_class()
    baseline = Baseline(ROOT, COMMIT, descriptors)
    admission = {
        "version": 1,
        "status": "baseline-pinned-before-source-parse",
        "issue": 1492,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "commit": COMMIT,
        "branch": branch,
        "worker_id": "01a112b9-e2b7-7d03-8000-eb2890649612",
        "script_path": "research/geography/norway-adm2-source-fit-1492/prepare.py",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "selected_subject_ids": ["physical-component:" + value for value in IDS],
        "baseline_files": descriptors,
        "pinned_file_bytes": sum(x["bytes"] for x in descriptors),
        "helper_phase_admitted_bytes": sum(baseline.consumed.values()),
        "limits": [
            "Pinned source and baseline bytes only; no source feature geometry parsed, decompressed or imported by this admission step.",
            "This baseline entry identifies the exact current repository vintage. Newly retrieved current-source bytes will be retained in a separate immutable NewVintage."
        ],
    }
    from evidence.immutable import write_new_vintage
    output = write_new_vintage(baseline, OWNED, VINTAGE, OUT, admission)
    print(json.dumps({"baseline": admission["commit"], "files": len(descriptors), "pinned_bytes": admission["pinned_file_bytes"], "admission_output": output}, indent=2))

if __name__ == "__main__":
    main()
