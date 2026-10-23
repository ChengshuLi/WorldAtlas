#!/usr/bin/env python3
"""Authenticate actual stable findings bodies before comparing treaty audit runs."""
from __future__ import print_function

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

METHOD_ID = "treaty-page-locator-audit"
PREDECESSOR_VALIDATOR_PATH = "research/geography/namibia-angola-treaty-pages-1346-20261008/validate_treaty_pages.py"
PREDECESSOR_VALIDATOR_SHA256 = "e66584ecd3c8769cee83174646127e96254b8e63b84252d7aee360a519d3a15a"
OUTPUT_NAMES = {"findings.json", "positive-control.json", "negative-control.json"}
VOLATILE = {"run_id", "started_at_utc", "semantic_result_sha256"}


class Rejected(Exception):
    pass


def fail(message):
    raise Rejected(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw, label):
    def reject_constant(value):
        fail("non-finite JSON value: " + value)
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
    except (UnicodeDecodeError, ValueError) as exc:
        fail("invalid JSON in " + label + ": " + str(exc))
    if not isinstance(value, dict):
        fail("JSON root must be an object in " + label)
    return value


def derive(findings):
    if not isinstance(findings, dict):
        fail("findings root must be an object")
    stable = {key: value for key, value in findings.items() if key not in VOLATILE}
    try:
        payload = json.dumps(stable, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        fail("stable findings cannot be canonically serialized: " + str(exc))
    return sha(payload)


def confined_file(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        fail("unsafe publication path: " + str(relative))
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            fail("symlink publication path rejected: " + str(relative))
    resolved, root_real = current.resolve(), root.resolve()
    if (os.path.commonpath((str(root_real), str(resolved))) != str(root_real)
            or not resolved.is_file()):
        fail("publication output is missing or escapes repository root: " + str(relative))
    return resolved


def load_run(root, folder_arg):
    folder = Path(folder_arg)
    if not folder.is_absolute():
        folder = root / folder
    receipt_file = folder / "publication.json"
    if receipt_file.is_symlink() or not receipt_file.is_file():
        fail("missing regular publication.json: " + str(receipt_file))
    receipt_raw = receipt_file.read_bytes()
    receipt = parse(receipt_raw, str(receipt_file))
    if receipt.get("version") != 1 or receipt.get("status") != "complete":
        fail("publication receipt is not complete version 1: " + str(folder))
    rows = receipt.get("outputs")
    if not isinstance(rows, list):
        fail("publication outputs must be an array")
    by_name = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            fail("malformed publication output descriptor")
        name = Path(row["path"]).name
        if name in by_name:
            fail("duplicate output name: " + name)
        by_name[name] = row
    if set(by_name) != OUTPUT_NAMES:
        fail("output inventory must contain findings and both control files")
    products = {}
    for name, row in by_name.items():
        raw = confined_file(root, row["path"]).read_bytes()
        if row.get("bytes") != len(raw) or row.get("sha256") != sha(raw):
            fail("output bytes or SHA do not match publication: " + row["path"])
        products[name] = parse(raw, row["path"])
    findings = products["findings.json"]
    run_id, method = findings.get("run_id"), findings.get("method")
    if not isinstance(run_id, str) or not run_id:
        fail("findings lacks run_id")
    if (not isinstance(method, dict)
            or method.get("path") != PREDECESSOR_VALIDATOR_PATH
            or method.get("sha256") != PREDECESSOR_VALIDATOR_SHA256):
        fail("findings are not bound to the pinned predecessor validator")
    for kind in ("positive-control", "negative-control"):
        control = products[kind + ".json"]
        if (control.get("method_id"), control.get("kind"), control.get("outcome"),
                control.get("run_id")) != (METHOD_ID, kind, "passed", run_id):
            fail("invalid real-format " + kind + " control")
    actual = derive(findings)
    if findings.get("semantic_result_sha256") != actual:
        fail("declared semantic_result_sha256 does not authenticate actual stable findings: " + run_id)
    return {
        "run_id": run_id,
        "stable_findings_sha256": actual,
        "publication_sha256": sha(receipt_raw),
        "findings_sha256": by_name["findings.json"]["sha256"],
        "positive_control_sha256": by_name["positive-control.json"]["sha256"],
        "negative_control_sha256": by_name["negative-control.json"]["sha256"],
        "method_sha256": method["sha256"],
    }


def write_exclusive(root, path, payload):
    rel = Path(path)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        fail("unsafe comparison destination: " + str(path))
    output = root / rel
    current = root
    for part in rel.parts[:-1]:
        current = current / part
        if current.is_symlink():
            fail("symlink comparison destination parent rejected: " + str(path))
    if output.exists() or output.is_symlink():
        fail("refusing to replace existing comparison destination: " + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            output.unlink()
        except OSError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="repository root for publication output paths")
    parser.add_argument("--left", required=True, help="first folder containing publication.json")
    parser.add_argument("--right", required=True, help="second folder containing publication.json")
    parser.add_argument("--output", help="optional new path for a passed receipt; never overwritten")
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        left, right = load_run(root, args.left), load_run(root, args.right)
        if left["run_id"] == right["run_id"]:
            fail("two distinct run IDs are required")
        if left["stable_findings_sha256"] != right["stable_findings_sha256"]:
            result = {"method_id": METHOD_ID, "kind": "reproducibility", "outcome": "disagreed",
                      "run_one": left, "run_two": right}
            print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
            return 2
        result = {
            "method_id": METHOD_ID, "kind": "reproducibility", "outcome": "passed",
            "run_one_sha256": left["stable_findings_sha256"],
            "run_two_sha256": right["stable_findings_sha256"], "runs": [left, right],
            "baseline_commit": "947fa467d11379dd6a2e5f4772df2e891402d735",
            "note": "Hashes are derived from authenticated stable findings; only run_id, started_at_utc and semantic_result_sha256 are excluded.",
        }
        if args.output:
            payload = (json.dumps(result, sort_keys=True, ensure_ascii=False,
                                  separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
            write_exclusive(root, args.output, payload)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
        return 0
    except (Rejected, OSError) as exc:
        print(json.dumps({"outcome": "rejected", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
