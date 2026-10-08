#!/usr/bin/env python3
"""Additive, pinned producer and strict publication-custody comparison."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/chn-tjk-publication-integrity-1354/"
OLD = "research/geography/chn-tjk-workbook-inventory-1127-erratum/"
BASE = "432c5b8e0ac9b9597738a31f5386569312c75966"
CORRECTION = "c53f0aa473eb32c07a5cf4f57df3a86663a625ae"
SUBJECTS = ["gb:CHN:ADM2:17275852B723995182906", "gb:CHN:ADM2:17275852B99352197075157", "gb:TJK:ADM2:16282066B16686410577714"]
FILES = ["member-inventory.json", "positive-control.json", "negative-control.json", "execution.json"]
PINNED_PRODUCER = OLD + "reproduce.py"
PINNED_HELPER = "scripts/evidence/immutable.py"
PRODUCER_SHA = "e05ae6e04bb1d609142c26b3cc01c4eb77c47e0cb642da755ab88ce1bb35749d"
HELPER_SHA = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
PUBS = {
    "run-20261007-07": "7bb250bd28e130415c0a8e443268988d44fb32678c69be2f00e77ce5864c358a",
    "run-20261007-08": "a92472d432503fc925cdeff4ebcdc651dffa699ea622a4c59332c911a7012110",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def git_blob(commit, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def module_from_pinned_source():
    code = git_blob(CORRECTION, PINNED_PRODUCER)
    need(sha(code) == PRODUCER_SHA, "Pinned predecessor producer code mismatch")
    module = types.ModuleType("worldatlas_pinned_predecessor")
    module.__file__ = str(ROOT / PINNED_PRODUCER)
    exec(compile(code, module.__file__, "exec"), module.__dict__)
    baseline, source, prior, helper = module.capture_inputs()
    need(helper.sha256(git_blob(BASE, PINNED_HELPER)) == HELPER_SHA, "Pinned helper mismatch")
    return module, baseline, source, prior, helper


def authenticate_correction_pins():
    producer = git_blob(CORRECTION, PINNED_PRODUCER)
    need(sha(producer) == PRODUCER_SHA, "Pinned producer differs from correction merge")
    manifest_path = OLD + "evidence-quality.json"
    manifest = git_blob(CORRECTION, manifest_path)
    need(sha(manifest) == "5228274c845062d831bae749f00dc6836c4da29a13b8945d5c97d667d4118d3a", "Pinned producer manifest mismatch")
    pins = [{"path": PINNED_PRODUCER, "bytes": len(producer), "sha256": PRODUCER_SHA},
            {"path": manifest_path, "bytes": len(manifest), "sha256": sha(manifest)}]
    for vintage, expected in PUBS.items():
        path = OLD + f"vintages/{vintage}/publication.json"
        raw = git_blob(CORRECTION, path)
        need(sha(raw) == expected, "Pinned historical publication mismatch: " + vintage)
        pins.append({"path": path, "bytes": len(raw), "sha256": expected})
    return pins


def make_baseline(helper, baseline, additional=()):
    # The legacy helper accounts immutable input bytes and all new output bytes.
    # Admit actual comparison run bytes plus a fixed 32 MiB runtime/temporary reserve.
    for name, size in additional:
        baseline.admit(name, size)
    baseline.admit("successor:runtime-and-temporary-reserve", 32 * 1024 * 1024)
    need(sum(baseline.consumed.values()) <= 256 * 1024 * 1024, "Complete phase exceeds 256 MiB")
    return baseline


def produce(vintage):
    module, baseline, source, prior, helper = module_from_pinned_source()
    correction_pins = authenticate_correction_pins()
    baseline = make_baseline(helper, baseline, [("correction-pin:" + x["path"], x["bytes"]) for x in correction_pins])
    destination = helper.NewVintage(baseline, OWNED, vintage, FILES)
    inventory, positive, negative, execution = module.outputs_for(source, prior, baseline)
    execution["successor"] = {"producer_source": PINNED_PRODUCER, "producer_commit": CORRECTION,
                              "producer_sha256": PRODUCER_SHA,
                              "note": "The authenticated predecessor's pure capture/output functions are run in memory; its legacy writer is never called."}
    destination.publish({"member-inventory.json": inventory, "positive-control.json": positive,
                         "negative-control.json": negative, "execution.json": execution})
    print(destination.root.relative_to(ROOT))


def ordinary_bytes(path, max_bytes=32 * 1024 * 1024):
    path = Path(path)
    need(not path.is_symlink() and path.is_file(), "Publication product must be an ordinary file: " + str(path))
    for parent in path.parents:
        if parent == ROOT.parent:
            break
        need(not parent.is_symlink(), "Symlink in publication path")
    size = path.stat().st_size
    need(size <= max_bytes, "Publication file exceeds 32 MiB")
    raw = path.read_bytes()
    need(len(raw) == size, "Publication file changed during read")
    return raw


def inspect_publication(vintage):
    need(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", vintage) is not None, "Unsafe run vintage")
    root_rel = OWNED + "vintages/" + vintage
    root = ROOT / root_rel
    receipt_raw = ordinary_bytes(root / "publication.json", 4096)
    receipt = json.loads(receipt_raw)
    need(type(receipt) is dict and set(receipt) == {"version", "status", "outputs"}, "Unsupported publication schema")
    need(type(receipt["version"]) is int and receipt["version"] == 1, "Unsupported publication version")
    need(receipt["status"] == "complete", "Publication is not complete")
    rows = receipt["outputs"]
    need(type(rows) is list and len(rows) == len(FILES), "Publication must declare the exact complete inventory")
    paths = [row.get("path") if type(row) is dict else None for row in rows]
    expected = {root_rel + "/" + name for name in FILES}
    need(len(set(paths)) == len(FILES) and set(paths) == expected, "Duplicate, foreign, or incomplete exact output paths")
    payloads = {}
    for name in FILES:
        path_rel = root_rel + "/" + name
        row = next(row for row in rows if row["path"] == path_rel)
        need(set(row) == {"path", "bytes", "sha256", "hash_kind"}, "Malformed output descriptor")
        need(row["hash_kind"] == "file-bytes" and type(row["bytes"]) is int and re.fullmatch(r"[a-f0-9]{64}", str(row["sha256"])) is not None,
             "Unsupported whole-file descriptor")
        raw = ordinary_bytes(root / name)
        need(row["bytes"] == len(raw) and row["sha256"] == sha(raw), "Publication product size/hash mismatch: " + name)
        payloads[name] = raw
    return payloads, {"path": root_rel + "/publication.json", "bytes": len(receipt_raw), "sha256": sha(receipt_raw), "hash_kind": "file-bytes"}


def compare(first, second, vintage):
    need(first != second, "Reproducibility requires two distinct producer runs")
    for name in (first, second, vintage):
        need(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) is not None, "Unsafe run vintage")
    module, baseline, _, _, helper = module_from_pinned_source()
    correction_pins = authenticate_correction_pins()
    roots = [OWNED + "vintages/" + first, OWNED + "vintages/" + second]
    additions = [("correction-pin:" + x["path"], x["bytes"]) for x in correction_pins]
    additions += [(path + "/" + name, (ROOT / path / name).stat().st_size) for path in roots for name in ["publication.json", *FILES]]
    # Ensure actual read sizes, including publication receipts and both complete products, are budgeted.
    baseline = make_baseline(helper, baseline, additions)
    destination = helper.NewVintage(baseline, OWNED, vintage, ["reproducibility.json"])
    payloads = []
    receipts = []
    for run in (first, second):
        products, receipt = inspect_publication(run)
        payloads.append(products)
        receipts.append(receipt)
    need(all(payloads[0][name] == payloads[1][name] for name in FILES), "Complete deterministic result files differ")
    comparison = {"method_id": "zip-member-inventory", "kind": "reproducibility", "outcome": "passed",
                  "run_vintages": [first, second], "payload_names": FILES,
                  "byte_identical_payloads": True, "payload_sha256": {name: sha(payloads[0][name]) for name in FILES},
                  "run_one_sha256": sha(payloads[0]["member-inventory.json"]),
                  "run_two_sha256": sha(payloads[1]["member-inventory.json"]), "publication_receipts": receipts,
                  "note": "Both complete run-relative publication inventories and actual whole product bytes were validated before comparison."}
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
        produce(args.vintage)


if __name__ == "__main__":
    main()
