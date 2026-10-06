#!/usr/bin/env python3
"""Additive, bounded fresh-vintage reproduction for the exact #1218 roster."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
RUNS = ROOT / "runs"
PINS = ROOT / "input-pins.json"
PROGRAM_PIN = ROOT / "program-pin.json"
PIN_INDEX_SHA256 = "99d6b1ac1551160e46d58076dbfe0269973bc518e5037f371622e9903005b8c9"
PROGRAM_RELATIVE = "data/regional-review/coastal-fresh-run-1160-erratum/fresh-reproduce.py"
FRESH_MAIN = "bd3b4ab860f11320717c354b10378c9972726373"
SOURCE_BASE = "a37ad37b94168f9b458617489a702bbb72afbd3d"
PRODUCTS = ("admission.json", "eight-county-comparison.json", "positive-control.json", "negative-control.json")
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PHASE_BYTES = 256 * 1024 * 1024
RESERVE_BYTES = 200_000


class Refusal(RuntimeError):
    pass


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")


def read_json(path: Path):
    return json.loads(path.read_bytes())


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def verify_pin(path: str, expected_bytes: int, expected_sha256: str, actual: bytes) -> None:
    if len(actual) != expected_bytes or sha256(actual) != expected_sha256:
        raise Refusal(f"changed or wrong pinned bytes: {path}")


def safe_run_id(value: str) -> str:
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value)
            or value in {".", ".."} or value.endswith(".")
            or "/" in value or "\\" in value or Path(value).is_absolute()
            or re.match(r"^[A-Za-z]:", value)):
        raise Refusal("run ID must be a safe, fresh, single-component name")
    if value.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        raise Refusal("run ID is a reserved device name")
    return value


def ordinary_path(path: Path) -> None:
    for component in [*reversed(path.parents), path]:
        if component.exists() and (component.is_symlink() or not component.is_dir() and component == path.parent):
            raise Refusal(f"refusing symlink or non-directory output ancestor: {component}")


def ensure_run_root() -> None:
    if RUNS.exists() and (RUNS.is_symlink() or not RUNS.is_dir()):
        raise Refusal("runs output root must be an ordinary directory")
    RUNS.mkdir(parents=False, exist_ok=True)


def load_pin_index():
    raw = PINS.read_bytes()
    if sha256(raw) != PIN_INDEX_SHA256:
        raise Refusal("fresh-run input inventory changed")
    pins = json.loads(raw)
    if (pins.get("schema") != "coastal-fresh-run-input-pins:v1" or pins.get("issue") != 1218
            or pins.get("baseline_commit") != SOURCE_BASE or pins.get("fresh_main_commit") != FRESH_MAIN
            or len(pins.get("inputs", [])) != 57
            or {x.get("id") for x in pins["inputs"]} != {f"input_{i}" for i in range(1, 58)}):
        raise Refusal("stale or malformed fresh-run input inventory")
    return pins


def verify_program_pin() -> dict:
    pin = read_json(PROGRAM_PIN)
    actual = Path(__file__).read_bytes()
    if pin.get("path") != PROGRAM_RELATIVE:
        raise Refusal("runner pin names a different program")
    verify_pin(PROGRAM_RELATIVE, pin.get("bytes"), pin.get("sha256"), actual)
    return pin


def verify_environment() -> dict:
    import pyproj
    import shapely
    actual = {"python": sys.version.split()[0], "shapely": shapely.__version__, "pyproj": pyproj.__version__}
    expected = {"python": "3.12.14", "shapely": "2.1.2", "pyproj": "3.7.2"}
    if actual != expected:
        raise Refusal(f"reproduction environment differs from pinned runtime: {actual}")
    return actual


def verify_registry(world: dict, pins: dict):
    parts = world.get("parts")
    expected = [f"geography/part-{i}.json" for i in range(34)] + [
        "geography/source-restoration-additions.json", "geography/macro-loose-ends-v5-additions.json"]
    if parts != expected:
        raise Refusal("stale or changed world-index part registry")
    paths = {item["path"] for item in pins["inputs"]}
    if any(f"data/{part}" not in paths for part in parts):
        raise Refusal("world-index references an unpinned geographic part")


def verify_baseline(pins: dict):
    head = git("rev-parse", "HEAD").decode().strip()
    if git("merge-base", head, FRESH_MAIN).decode().strip() != FRESH_MAIN:
        raise Refusal("checkout does not descend from the fresh-main claim baseline")
    if git("merge-base", head, SOURCE_BASE).decode().strip() != SOURCE_BASE:
        raise Refusal("pinned source vintage is not an ancestor of this checkout")

    all_inputs = list(pins["inputs"]) + [pins["prior_program"], pins["prior_input_inventory"]]
    all_inputs += [{k: row[k] for k in ("path", "bytes", "sha256")} for row in pins["historical_outputs"]]
    total_bytes = decoded_total = 0
    checked, source_bytes = [], {}
    for item in all_inputs:
        name = item["path"]
        if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
            raise Refusal("unsafe path in pin inventory")
        raw = git("show", f"{SOURCE_BASE}:{name}")
        verify_pin(name, item["bytes"], item["sha256"], raw)
        if len(raw) > MAX_FILE_BYTES:
            raise Refusal(f"pinned input exceeds per-file limit: {name}")
        total_bytes += len(raw)
        decoded = 0
        if name.endswith(".gz"):
            decoded = len(gzip.decompress(raw))
            if decoded > MAX_FILE_BYTES:
                raise Refusal(f"decoded input exceeds per-file limit: {name}")
            decoded_total += decoded
        source_bytes[name] = raw
        checked.append({"path": name, "bytes": len(raw), "sha256": sha256(raw), "decoded_bytes": decoded})

    original = json.loads(source_bytes[pins["prior_input_inventory"]["path"]])
    if original.get("schema") != "coastal-input-guards:v1" or len(original.get("inputs", [])) != 57:
        raise Refusal("historical issue input inventory is stale")
    if pins["prior_program"]["sha256"] != "be7d84a1d75663c5169dca35cd530018f17d079b3f24e0527a08b190cb1c4493":
        raise Refusal("historical reproduction program pin is stale")
    if pins["prior_input_inventory"]["sha256"] != "fdcc56ba18706f1427683c09d95492145ffa8b96d490816667e8612d2c0600a0":
        raise Refusal("historical expected-input inventory pin is stale")
    for i, item in enumerate(original["inputs"], 1):
        if pins["issue_pins"].get(f"input_{i}") != item["sha256"]:
            raise Refusal(f"issue pin mismatch: input_{i}")

    world = json.loads(source_bytes["data/world-index.json"])
    verify_registry(world, pins)
    phase = total_bytes + decoded_total + RESERVE_BYTES
    if phase > MAX_PHASE_BYTES:
        raise Refusal(f"complete input/decompression/output-reserve phase exceeds 256 MiB: {phase}")
    return {"baseline": SOURCE_BASE, "fresh_main": FRESH_MAIN,
            "historical_input_baseline": original["verified_branch_base"],
            "input_count": len(checked), "issue_input_count": 57, "ordinary_input_bytes": total_bytes,
            "gzip_decoded_bytes": decoded_total, "reserve_bytes": RESERVE_BYTES,
            "admitted_phase_bytes": phase, "max_phase_bytes": MAX_PHASE_BYTES,
            "inputs_sha256": sha256(canonical_json(checked)), "verified_inputs": checked,
            "registry_part_count": len(world["parts"]), "program_pin": read_json(PROGRAM_PIN),
            "source_bytes": source_bytes}


def load_historical_program(pins: dict, source_bytes: dict):
    path = REPO / pins["prior_program"]["path"]
    module = types.ModuleType("coastal_1160_historical_reproducer")
    module.__file__ = str(path)
    module.__package__ = ""
    exec(compile(source_bytes[pins["prior_program"]["path"]], str(path), "exec"), module.__dict__)
    return module


def original_admission(pins: dict, source_bytes: dict):
    original = json.loads(source_bytes[pins["prior_input_inventory"]["path"]])
    checked = []
    total_bytes = decoded_bytes = 0
    for item in original["inputs"]:
        raw = source_bytes[item["path"]]
        verify_pin(item["path"], item["bytes"], item["sha256"], raw)
        total_bytes += len(raw)
        if item["path"].endswith(".gz"):
            decoded = gzip.decompress(raw)
            if len(decoded) > MAX_FILE_BYTES:
                raise Refusal(f"decoded input exceeds original per-file limit: {item['path']}")
            decoded_bytes += len(decoded)
        checked.append({"id": item["id"], "path": item["path"], "bytes": len(raw), "sha256": sha256(raw)})
    phase = total_bytes + decoded_bytes + RESERVE_BYTES
    if phase > MAX_PHASE_BYTES:
        raise Refusal("historical scientific input phase exceeds reviewed 256 MiB limit")
    return {"baseline": original["verified_branch_base"],
            "reproduction_program_sha256": sha256(source_bytes[pins["prior_program"]["path"]]),
            "input_count": len(checked), "ordinary_input_bytes": total_bytes,
            "gzip_decoded_bytes": decoded_bytes, "reserve_bytes": RESERVE_BYTES,
            "admitted_phase_bytes": phase,
            "inputs_sha256": sha256(json.dumps(checked, sort_keys=True, separators=(",", ":")).encode()),
            "verified_inputs": checked}


def compute_with_immutable_inputs(module, admission, source_bytes):
    module.verify_inputs = lambda: admission
    original_read_bytes = Path.read_bytes
    files = {os.path.abspath(os.fspath(REPO / name)): raw for name, raw in source_bytes.items()}

    def pinned_read_bytes(path):
        absolute = os.path.abspath(os.fspath(path))
        if absolute in files:
            return files[absolute]
        if absolute == str(REPO) or absolute.startswith(str(REPO) + os.sep):
            raise Refusal(f"historical program attempted an unpinned repository read: {os.path.relpath(absolute, REPO)}")
        return original_read_bytes(path)

    helper_name = "scripts.evidence.geometry"
    helper_path = "scripts/evidence/geometry.py"
    helper = types.ModuleType(helper_name)
    helper.__file__ = str(REPO / helper_path)
    exec(compile(source_bytes[helper_path], helper.__file__, "exec"), helper.__dict__)
    package = sys.modules.get("scripts.evidence")
    if package is None:
        import importlib
        package = importlib.import_module("scripts.evidence")
    previous_helper = sys.modules.get(helper_name)
    previous_attribute = getattr(package, "geometry", None)
    sys.modules[helper_name] = helper
    package.geometry = helper
    Path.read_bytes = pinned_read_bytes
    try:
        return module.compute()
    finally:
        Path.read_bytes = original_read_bytes
        if previous_helper is None:
            sys.modules.pop(helper_name, None)
        else:
            sys.modules[helper_name] = previous_helper
        if previous_attribute is None:
            try:
                del package.geometry
            except AttributeError:
                pass
        else:
            package.geometry = previous_attribute


def product_bytes(module, admission, source_bytes):
    admission, comparison, positive, negative = compute_with_immutable_inputs(module, admission, source_bytes)
    values = {"admission.json": admission, "eight-county-comparison.json": comparison,
              "positive-control.json": positive, "negative-control.json": negative}
    return {name: canonical_json(values[name]) for name in PRODUCTS}


def historical_product_bytes(pins: dict, run: str):
    result = {}
    for row in pins["historical_outputs"]:
        if row["run"] == run:
            raw = git("show", f"{SOURCE_BASE}:{row['path']}")
            verify_pin(row["path"], row["bytes"], row["sha256"], raw)
            result[row["product"]] = raw
    if set(result) != set(PRODUCTS):
        raise Refusal(f"historical {run} output inventory is incomplete")
    return result


def _write_exclusive(destination: Path, content: bytes, created: list, writer=None):
    with destination.open("xb") as stream:
        identity = os.fstat(stream.fileno())
        # Register ownership before the first write, so a partial write or
        # close/flush error can still be cleaned up without touching a rival.
        created.append((destination, identity.st_dev, identity.st_ino))
        (writer or (lambda output, data: output.write(data)))(stream, content)


def _remove_created(created: list):
    # Device/inode identity covers partial files whose full hash was never
    # completed and preserves any replacement or concurrent file.
    for path, device, inode in reversed(created):
        try:
            current = path.lstat()
            if stat.S_ISREG(current.st_mode) and current.st_dev == device and current.st_ino == inode:
                path.unlink()
        except OSError:
            pass


def publish_single_exclusive(destination: Path, content: bytes, writer=None):
    created = []
    try:
        _write_exclusive(destination, content, created, writer)
    except Exception:
        _remove_created(created)
        raise


def publish_products(target: Path, products: dict[str, bytes], receipt: dict, writer=None):
    ordinary_path(target)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"refusing occupied output vintage: {target.name}")
    target.mkdir(parents=False, exist_ok=False)
    created = []
    try:
        for name in PRODUCTS:
            destination = target / name
            _write_exclusive(destination, products[name], created, writer)
        receipt_path = target / "execution.json"
        receipt_bytes = canonical_json(receipt)
        _write_exclusive(receipt_path, receipt_bytes, created, writer)
    except Exception:
        _remove_created(created)
        try:
            target.rmdir()
        except OSError:
            pass
        raise


def run_one(run_id: str):
    run_id = safe_run_id(run_id)
    environment = verify_environment()
    started = datetime.now(timezone.utc).isoformat()
    program_pin = verify_program_pin()
    pins = load_pin_index()
    admission = verify_baseline(pins)
    source_bytes = admission.pop("source_bytes")
    old_admission = original_admission(pins, source_bytes)
    module = load_historical_program(pins, source_bytes)
    products = product_bytes(module, old_admission, source_bytes)
    expected = historical_product_bytes(pins, "run-one")
    if products != expected:
        raise Refusal("fresh result differs from retained historical four-product baseline")
    if sum(map(len, products.values())) > RESERVE_BYTES:
        raise Refusal("serialized run outputs exceed the reviewed 200,000 byte reserve")
    ensure_run_root()
    output_dir = RUNS / run_id
    hashes = {name: sha256(data) for name, data in products.items()}
    receipt = {"schema": "coastal-fresh-execution:v1", "issue": 1218,
               "run_id": run_id, "started_at": started,
               "completed_at": datetime.now(timezone.utc).isoformat(),
               "command": f"python3.12 {PROGRAM_RELATIVE} --run-id {run_id}",
               "checkout_head": git("rev-parse", "HEAD").decode().strip(),
               "input_inventory_sha256": sha256(PINS.read_bytes()),
               "prior_program_sha256": pins["prior_program"]["sha256"],
               "program_sha256": program_pin["sha256"],
               "python": environment["python"], "shapely": environment["shapely"],
               "pyproj": environment["pyproj"],
               "products": [{"path": name, "bytes": len(products[name]), "sha256": hashes[name],
                             "historical_baseline_sha256": sha256(expected[name]),
                             "matches_historical_baseline": True} for name in PRODUCTS]}
    receipt["admission"] = {k: admission[k] for k in ("input_count", "issue_input_count", "ordinary_input_bytes",
        "gzip_decoded_bytes", "reserve_bytes", "admitted_phase_bytes", "registry_part_count")}
    if sum(map(len, products.values())) + len(canonical_json(receipt)) > RESERVE_BYTES:
        raise Refusal("serialized products and execution receipt exceed the reviewed 200,000-byte reserve")
    publish_products(output_dir, products, receipt)
    print(json.dumps({"run_id": run_id, "output": str(output_dir.relative_to(REPO)),
                      "product_hashes": hashes, "receipt": str((output_dir / "execution.json").relative_to(REPO))}, indent=2))


def verify_pair(run_one: str, run_two: str, summary_id: str = "two-run-summary"):
    a, b = safe_run_id(run_one), safe_run_id(run_two)
    summary_id = safe_run_id(summary_id)
    if a == b:
        raise Refusal("two-run verification requires distinct output vintages")
    pins = load_pin_index()
    program_pin = verify_program_pin()
    environment = verify_environment()
    records = []
    for run in (a, b):
        directory = RUNS / run
        if not directory.is_dir() or directory.is_symlink():
            raise Refusal(f"missing or unsafe fresh output vintage: {run}")
        execution = read_json(directory / "execution.json")
        if (execution.get("schema") != "coastal-fresh-execution:v1" or execution.get("run_id") != run
                or execution.get("program_sha256") != program_pin["sha256"]
                or execution.get("input_inventory_sha256") != sha256(PINS.read_bytes())
                or any(execution.get(key) != value for key, value in environment.items())):
            raise Refusal(f"execution receipt is stale or names different pinned bytes: {run}")
        hashes = {}
        for name in PRODUCTS:
            raw = (directory / name).read_bytes()
            hashes[name] = sha256(raw)
            baseline = historical_product_bytes(pins, "run-one")[name]
            if raw != baseline:
                raise Refusal(f"fresh output does not match retained product: {run}/{name}")
        receipt_products = {item.get("path"): item for item in execution.get("products", [])}
        if set(receipt_products) != set(PRODUCTS) or any(
                receipt_products[name].get("sha256") != hashes[name]
                or receipt_products[name].get("matches_historical_baseline") is not True for name in PRODUCTS):
            raise Refusal(f"execution receipt output hashes differ: {run}")
        records.append({"run_id": run, "execution": execution, "product_sha256": hashes})
    equal = all(records[0]["product_sha256"][name] == records[1]["product_sha256"][name] for name in PRODUCTS)
    if not equal:
        raise Refusal("fresh output vintages differ")
    summary = {"method_id": "deterministic-report-reproduction", "kind": "code", "outcome": "passed",
               "schema": "coastal-fresh-two-run:v1", "issue": 1218,
               "run_ids": [a, b], "distinct_run_ids": True,
               "baseline_products_match": True, "run_products_byte_identical": True,
               "products": [{"path": name, "run_one_sha256": records[0]["product_sha256"][name],
                             "run_two_sha256": records[1]["product_sha256"][name],
                             "historical_sha256": sha256(historical_product_bytes(pins, "run-one")[name])}
                            for name in PRODUCTS],
               "runs": records}
    out = ROOT / f"{summary_id}.json"
    publish_single_exclusive(out, canonical_json(summary))
    print(json.dumps({"summary": str(out.relative_to(REPO)), "sha256": sha256(out.read_bytes()),
                      "baseline_products_match": True, "run_products_byte_identical": True}, indent=2))


def run_controls():
    verify_environment()
    verify_program_pin()
    rejected_ids = ["../escape", "/absolute", "nested/name", r"nested\\name", "..", "CON", "name."]
    for value in rejected_ids:
        try:
            safe_run_id(value)
        except Refusal:
            pass
        else:
            raise Refusal(f"unsafe run ID accepted: {value}")
    expected_hash = "a" * 64
    try:
        verify_pin("fixture", 1, expected_hash, b"x")
    except Refusal:
        pass
    else:
        raise Refusal("altered-input fixture was accepted")
    world = {"parts": ["geography/part-0.json"]}
    try:
        if world["parts"] != [f"geography/part-{i}.json" for i in range(34)] + [
                "geography/source-restoration-additions.json", "geography/macro-loose-ends-v5-additions.json"]:
            raise Refusal("stale or changed world-index part registry")
    except Refusal:
        pass
    else:
        raise Refusal("stale registry fixture was accepted")
    with tempfile.TemporaryDirectory(prefix=".fresh-run-control-", dir=ROOT) as tmp:
        target = Path(tmp) / "occupied"
        target.mkdir()
        sentinel = target / "sentinel.txt"
        sentinel.write_bytes(b"preserve-me\n")
        before = sentinel.read_bytes()
        try:
            publish_products(target, {}, {})
        except FileExistsError:
            pass
        else:
            raise Refusal("existing target was accepted")
        if sentinel.read_bytes() != before:
            raise Refusal("existing target sentinel changed")
        partial = Path(tmp) / "partial"

        def fail_after_partial_write(stream, data):
            stream.write(data[:max(1, len(data) // 2)])
            raise OSError("simulated write interruption")

        try:
            publish_products(partial, {"admission.json": b"bounded-fixture"}, {}, fail_after_partial_write)
        except OSError as error:
            if str(error) != "simulated write interruption":
                raise
        else:
            raise Refusal("partial-write fixture unexpectedly completed")
        if partial.exists() or partial.is_symlink():
            raise Refusal("failed publication left its own partial output behind")
        partial_summary = Path(tmp) / "partial-summary.json"
        try:
            publish_single_exclusive(partial_summary, b"summary-fixture", fail_after_partial_write)
        except OSError as error:
            if str(error) != "simulated write interruption":
                raise
        else:
            raise Refusal("partial summary fixture unexpectedly completed")
        if partial_summary.exists() or partial_summary.is_symlink():
            raise Refusal("failed summary publication left its own partial file behind")
    # Positive controls execute the real immutable preflight and both original
    # scientific controls without publishing an output vintage.
    pins = load_pin_index()
    admission = verify_baseline(pins)
    source_bytes = admission.pop("source_bytes")
    old_admission = original_admission(pins, source_bytes)
    module = load_historical_program(pins, source_bytes)
    products = product_bytes(module, old_admission, source_bytes)
    if products != historical_product_bytes(pins, "run-one"):
        raise Refusal("positive result fixture differs from retained baseline")
    return {"unsafe_names_rejected": len(rejected_ids), "changed_input_rejected": True,
            "stale_registry_rejected": True, "existing_target_sentinel_preserved": True,
            "partial_write_cleanup_verified": True,
            "partial_summary_cleanup_verified": True,
            "exact_pinned_inputs_admitted": admission["input_count"],
            "four_positive_products_match_baseline": sorted(products)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--verify-pair", nargs=2, metavar=("RUN_ONE", "RUN_TWO"))
    parser.add_argument("--summary-id", help="fresh summary filename stem for --verify-pair")
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    if args.controls_only:
        print(json.dumps(run_controls(), indent=2, sort_keys=True))
    elif args.verify_pair:
        verify_pair(*args.verify_pair, summary_id=args.summary_id or "two-run-summary")
    elif args.run_id:
        run_one(args.run_id)
    else:
        parser.error("--run-id, --verify-pair, or --controls-only is required")


if __name__ == "__main__":
    try:
        main()
    except (Refusal, FileNotFoundError, OSError, json.JSONDecodeError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        sys.exit(2)
