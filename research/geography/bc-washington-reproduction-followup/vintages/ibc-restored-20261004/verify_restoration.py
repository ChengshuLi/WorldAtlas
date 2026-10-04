#!/usr/bin/env python3
"""Exercise read-only, exclusive-create, input-pin, and reproducibility checks."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPRODUCER = HERE / "reproduce.py"
RECEIPT = HERE / "reproduced-assessment.json"
BASELINE = "a1fd3383e89dea4c4497bf3a6f469494871ad758"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, expected=0):
    result = subprocess.run([sys.executable, str(REPRODUCER), *map(str, args)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if (result.returncode == 0) != (expected == 0):
        raise RuntimeError(f"unexpected reproduction exit {result.returncode}: {result.stderr.decode(errors='replace')[-1200:]}")
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--write-controls", action="store_true")
    args = parser.parse_args()
    before = digest(RECEIPT)
    run(["--archive", args.archive])
    if digest(RECEIPT) != before:
        raise RuntimeError("default read-only comparison changed the stored receipt")
    with tempfile.TemporaryDirectory(prefix="wa-bc-repro-") as tmp:
        temp = Path(tmp)
        one, two = temp / "one.json", temp / "two.json"
        run(["--archive", args.archive, "--new-vintage", "--output", one])
        run(["--archive", args.archive, "--new-vintage", "--output", two])
        one_hash, two_hash, expected_hash = digest(one), digest(two), digest(RECEIPT)
        if one_hash != two_hash or one_hash != expected_hash:
            raise RuntimeError("two-run results differ from each other or the committed receipt")

        changed_archive = temp / "changed-archive.zip"
        data = bytearray(Path(args.archive).read_bytes())
        data[-1] ^= 1
        changed_archive.write_bytes(data)
        changed_archive_output = temp / "changed-archive-result.json"
        run(["--archive", changed_archive, "--new-vintage", "--output", changed_archive_output], expected=1)
        if changed_archive_output.exists():
            raise RuntimeError("archive hash failure occurred after output creation")

        changed_base_output = temp / "changed-base-result.json"
        run(["--archive", args.archive, "--baseline-commit", "fbd3bf4991dbd5a9bf89a79b14e5b4deb6225ff9",
             "--new-vintage", "--output", changed_base_output], expected=1)
        if changed_base_output.exists():
            raise RuntimeError("baseline commit rejection occurred after output creation")

        occupied_hash = digest(RECEIPT)
        run(["--archive", args.archive, "--new-vintage", "--output", RECEIPT], expected=1)
        if digest(RECEIPT) != occupied_hash:
            raise RuntimeError("exclusive-create refusal changed the existing receipt")

    controls = {
        "positive": {"runs": 1, "read_only_comparison": "passed", "inherited_rows_equal": True,
                     "sample_count": 18, "strict_noncontainments": [55, 63, 64, 65, 66]},
        "negative": {"changed_archive_pin_rejected_before_output": True,
                     "changed_baseline_commit_rejected_before_output": True,
                     "existing_vintage_exclusive_create_refused_unchanged": True},
        "reproducibility": {"runs": 2, "run_one_sha256": one_hash, "run_two_sha256": two_hash,
                             "equal": one_hash == two_hash, "matches_committed_receipt": one_hash == expected_hash},
    }
    if args.write_controls:
        control_kinds = {"positive": "positive-control", "negative": "negative-control",
                         "reproducibility": "reproducibility"}
        for name, details in controls.items():
            payload = {"method_id": "ibc-section25-pinned-reproduction", "kind": control_kinds[name],
                       "outcome": "passed", **details}
            path = HERE / "validation" / f"{name}-control.json"
            encoded = (json.dumps(payload, indent=2) + "\n").encode()
            with path.open("xb") as stream:
                stream.write(encoded)
    print(json.dumps({"status": "passed", "receipt_sha256": expected_hash,
                      "two_runs_equal": one_hash == two_hash, "changed_inputs_rejected_before_write": True}))


if __name__ == "__main__":
    main()
