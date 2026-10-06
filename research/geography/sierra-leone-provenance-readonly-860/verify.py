#!/usr/bin/env python3
"""Read-only superseding verifier for the retained Sierra Leone receipt."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / "research/geography/sierra-leone-license-provenance-746"
BASE = "f0dad9f05852fd71b986e8200531f4113bb784d3"
PINS = {
    "verify.py": "7ba6e88e75803ea4b9492216d003db94f41cb7556f03891d43f965b815014d8e",
    "verification-results.json": "799f34a7287c6121156c4eb128b7dfc8d6d8c07271bfe9b3fa46cc92298ae949",
    "license-provenance.json": "3b106d961b9b1a3c6ee691f8c8ab89904d55270fe985183c652fa702bdec6763",
    "issue-contract.json": "37ab337e0e3dc333bfbb9fc337a58ebe76df9d81a7f14f15c7610afbdd0dcdc1",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def compare_receipt(expected_path: Path, candidate_path: Path) -> None:
    """Exit nonzero without mutation when an existing receipt differs."""
    expected = expected_path.read_bytes()
    candidate = candidate_path.read_bytes()
    if candidate != expected:
        raise ValueError(
            f"retained receipt mismatch: expected {digest(expected)}, got {digest(candidate)}"
        )


def pinned_bytes(name: str) -> bytes:
    raw = (OLD / name).read_bytes()
    if digest(raw) != PINS[name]:
        raise ValueError(f"retained predecessor pin mismatch for {name}: {digest(raw)}")
    from_git = subprocess.check_output(
        ["git", "show", f"{BASE}:research/geography/sierra-leone-license-provenance-746/{name}"],
        cwd=ROOT,
    )
    if from_git != raw:
        raise ValueError(f"working predecessor bytes differ from pinned PR-base blob: {name}")
    return raw


def run_predecessor_once() -> bytes:
    target = (OLD / "verification-results.json").resolve()
    writes: list[bytes] = []
    captured = io.StringIO()
    spec = importlib.util.spec_from_file_location("retained_sle_verifier", OLD / "verify.py")
    if spec is None or spec.loader is None:
        raise ValueError("cannot load retained verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    from pathlib import Path as LocalPath
    original_write_text = LocalPath.write_text

    def intercept(path: Path, data: str, *args, **kwargs):
        if path.resolve() != target:
            raise ValueError(f"unexpected verifier write target: {path}")
        writes.append(data.encode(kwargs.get("encoding") or "utf-8"))
        return len(data)

    try:
        LocalPath.write_text = intercept
        with contextlib.redirect_stdout(captured):
            module.main()
    finally:
        LocalPath.write_text = original_write_text

    if len(writes) != 1:
        raise ValueError(f"expected exactly one intercepted write attempt, got {len(writes)}")
    printed = captured.getvalue().encode("utf-8")
    if writes[0] != printed:
        raise ValueError("verifier's attempted receipt differs from its displayed result")
    return writes[0]


def expected_control(kind: str, details: dict) -> dict:
    return {"version": 1, "method_id": "sle-readonly-receipt", "kind": kind,
            "outcome": "passed", **details}


def build_result() -> tuple[dict, dict, dict, dict]:
    original = {name: pinned_bytes(name) for name in PINS}
    retained = original["verification-results.json"]
    first = run_predecessor_once()
    second = run_predecessor_once()
    if first != retained or second != retained:
        raise ValueError("computed verification receipt differs from immutable retained bytes")
    if first != second:
        raise ValueError("repeated read-only verification results are not byte-identical")
    if any((OLD / name).read_bytes() != raw for name, raw in original.items()):
        raise ValueError("a retained predecessor file changed during reproduction")

    # A real subprocess reads an existing mismatched sentinel. Its nonzero exit
    # proves ordinary comparison rejects; byte checks prove rejection is read-only.
    with tempfile.TemporaryDirectory(prefix="worldatlas-sle-receipt-control-") as tmp:
        temp = Path(tmp)
        expected = temp / "expected.json"
        sentinel = temp / "sentinel.json"
        expected.write_bytes(retained)
        sentinel_bytes = b"SENTINEL: deliberately mismatched retained receipt\n"
        sentinel.write_bytes(sentinel_bytes)
        before_expected = expected.read_bytes()
        before_sentinel = sentinel.read_bytes()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        rejected = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--compare", str(expected), str(sentinel)],
            cwd=tmp, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if rejected.returncode != 1 or b"retained receipt mismatch" not in rejected.stderr:
            raise ValueError("sentinel mismatch did not fail through the expected receipt comparator")
        if expected.read_bytes() != before_expected or sentinel.read_bytes() != before_sentinel:
            raise ValueError("mismatch rejection changed an existing receipt or sentinel")

    positive = expected_control("positive-control", {
        "base_commit": BASE,
        "predecessor_verifier_sha256": PINS["verify.py"],
        "retained_verification_receipt_sha256": digest(retained),
        "computed_receipt_sha256": digest(first),
        "intercepted_write_attempts": 1,
        "attempted_bytes_equal_retained": True,
        "retained_receipt_unchanged": True,
    })
    negative = expected_control("negative-control", {
        "sentinel_mismatch_rejected_nonzero": True,
        "sentinel_bytes_unchanged": True,
        "expected_receipt_bytes_unchanged": True,
        "subprocess_return_code": rejected.returncode,
    })
    reproducibility = expected_control("reproducibility", {
        "base_commit": BASE,
        "run_one_sha256": digest(first),
        "run_two_sha256": digest(second),
        "equal_runs": first == second,
        "working_tree_receipt_writes": 0,
    })
    provenance = json.loads(original["license-provenance.json"])
    summary = {
        "version": 1,
        "method_id": "sle-readonly-receipt",
        "kind": "source",
        "outcome": "passed",
        "scope": {"sierra_leone_subjects": 12, "togo_context_rows": 37,
                  "sierra_leone_subject_ids": sorted(row["id"] for row in provenance["sierra_leone_rows"])},
        "predecessor_pins": {name: {"sha256": digest(original[name]), "bytes": len(original[name])}
                              for name in sorted(PINS)},
        "result_receipt_sha256": digest(first),
        "positive_control": "passed",
        "negative_control": "passed",
        "reproducibility": "passed",
        "limits": [
            "The metadata findings are inherited from the retained #784 packet; this follow-up does not independently re-adjudicate territorial meaning, boundary completeness, statutory status or reuse rights.",
            "The receipt verifier preserves source assertions but does not approve geography, close #746's wider audit, publish a region or authorize historical imports.",
        ],
    }
    return summary, positive, negative, reproducibility


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def record_new_vintage(values: tuple[dict, dict, dict, dict]) -> None:
    vintage_root = HERE / "vintages"
    try:
        vintage_root.mkdir(exist_ok=False)
    except FileExistsError:
        if vintage_root.is_symlink() or not vintage_root.is_dir():
            raise ValueError("vintage root must be an ordinary directory")
    target_dir = vintage_root / "20261005-readonly-check"
    target_dir.mkdir(exist_ok=False)
    names = ("verification-results.json", "positive-control.json", "negative-control.json", "reproducibility-control.json")
    for name, value in zip(names, values, strict=True):
        with (target_dir / name).open("xb") as stream:
            stream.write(canonical(value))


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--compare":
        try:
            compare_receipt(Path(sys.argv[2]), Path(sys.argv[3]))
        except (OSError, ValueError) as error:
            print(str(error), file=sys.stderr)
            return 1
        return 0

    record = len(sys.argv) == 2 and sys.argv[1] == "--record-new"
    if len(sys.argv) > 1 and not record:
        print("usage: verify.py [--record-new] | --compare EXPECTED CANDIDATE", file=sys.stderr)
        return 2
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    try:
        values = build_result()
        if record:
            record_new_vintage(values)
            print("Created a new dated evidence vintage with exclusive file creation.")
        else:
            target_dir = HERE / "vintages/20261005-readonly-check"
            names = ("verification-results.json", "positive-control.json", "negative-control.json", "reproducibility-control.json")
            for name, value in zip(names, values, strict=True):
                actual = (target_dir / name).read_bytes()
                expected = canonical(value)
                if actual != expected:
                    raise ValueError(f"retained new-vintage receipt mismatch: {name}")
            print(canonical(values[0]).decode("utf-8"), end="")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
