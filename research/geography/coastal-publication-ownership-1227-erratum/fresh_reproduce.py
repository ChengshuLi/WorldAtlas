#!/usr/bin/env python3
"""Reproduce the retained eight-county comparison from authenticated Git blobs.

This is cooperative provenance tooling, not a sandbox. Historical project code is
executed only from the source commit's captured Git blobs. Output cleanup is
inode-bound so a replaced directory is never removed as if it were ours.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[3]
OWNED = "research/geography/coastal-publication-ownership-1227-erratum/"
SOURCE_COMMIT = "a37ad37b94168f9b458617489a702bbb72afbd3d"
RUNNER_COMMIT = "de506f51100568e150e51f2926a5259b71e55272"
PIN_FILE = "data/regional-review/coastal-fresh-run-1160-erratum/input-pins.json"
PIN_FILE_SHA256 = "99d6b1ac1551160e46d58076dbfe0269973bc518e5037f371622e9903005b8c9"
HELPER_FILE = "scripts/evidence/immutable.py"
HELPER_SHA256 = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
PROGRAM = "data/regional-review/coastal-reference-reproduction-980/reproduce.py"
GEOMETRY = "scripts/evidence/geometry.py"
ELLIPSOID = "scripts/ellipsoidal_area.py"
PRODUCTS = ("admission.json", "eight-county-comparison.json", "positive-control.json", "negative-control.json")
SUBJECTS = [
    "gb:USA:ADM2:52423323B68249799438553",
    "gb:USA:ADM2:52423323B35006791438696",
    "gb:USA:ADM2:52423323B58673559392327",
    "gb:USA:ADM2:52423323B71362647483761",
    "gb:USA:ADM2:52423323B31615661575159",
    "gb:USA:ADM2:52423323B40186233786127",
    "gb:USA:ADM2:52423323B93853380479562",
    "gb:USA:ADM2:52423323B62158301450735",
]


class Refusal(RuntimeError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False, allow_nan=False) + "\n").encode()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), *args], stderr=subprocess.PIPE)


def safe_run_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise Refusal("run ID must be one safe path component")
    return value


def blob(commit: str, path: str) -> bytes:
    return git("show", f"{commit}:{path}")


def pin_row(path: str, raw: bytes) -> dict:
    if len(raw) > 32 * 1024 * 1024:
        raise Refusal(f"per-file byte limit exceeded: {path}")
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def trusted_immutable():
    """Load the shared reader itself from its authenticated main Git blob."""
    raw = blob(RUNNER_COMMIT, HELPER_FILE)
    if sha(raw) != HELPER_SHA256:
        raise Refusal("shared immutable reader Git blob hash changed")
    module = types.ModuleType("worldatlas_trusted_immutable")
    module.__file__ = str(REPO / HELPER_FILE)
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module, raw


def load_baseline():
    helper_module, helper = trusted_immutable()
    raw_inventory = blob(RUNNER_COMMIT, PIN_FILE)
    if sha(raw_inventory) != PIN_FILE_SHA256:
        raise Refusal("retained original input inventory differs from its authenticated main-commit bytes")
    inventory = json.loads(raw_inventory)
    if inventory.get("schema") != "coastal-fresh-run-input-pins:v1" or inventory.get("issue") != 1218:
        raise Refusal("retained original issue inventory is stale")
    if inventory.get("baseline_commit") != SOURCE_COMMIT or len(inventory.get("inputs", [])) != 57:
        raise Refusal("retained 57-input source inventory does not match its declared vintage")
    if sorted(inventory.get("subject_ids", [])) != sorted(SUBJECTS):
        raise Refusal("original eight-subject roster differs from issue #1381")

    descriptors = []
    for item in inventory["inputs"]:
        descriptors.append({**item, "hash_kind": "file-bytes"})
    descriptors.extend([inventory["prior_program"], inventory["prior_input_inventory"]])
    descriptors.extend({k: row[k] for k in ("path", "bytes", "sha256")} for row in inventory["historical_outputs"])
    descriptors = [{**row, "hash_kind": "file-bytes"} for row in descriptors]
    for path in (PROGRAM, GEOMETRY, ELLIPSOID):
        if path not in {row["path"] for row in descriptors}:
            raise Refusal("executed project code is missing from original pin inventory: " + path)
    baseline = helper_module.Baseline(str(REPO), SOURCE_COMMIT, descriptors,
                                      max_phase_bytes=helper_module.MAX_PHASE_BYTES)
    baseline.admit("runner-main:" + PIN_FILE, len(raw_inventory))
    baseline.admit("runner-main:" + HELPER_FILE, len(helper))
    captured = {path: baseline.pinned_bytes(path) for path in baseline.pins}

    # Count all decompressed original inputs, executable bytes, controls, and
    # outputs in one complete phase, rather than just the compressed archives.
    import gzip
    for path, raw in captured.items():
        if path.endswith(".gz"):
            decoded = gzip.decompress(raw)
            baseline.admit(path + ":decoded", len(decoded))
    baseline.admit("runner:" + Path(__file__).name, len(Path(__file__).read_bytes()))
    baseline.admit("trusted-reader:" + HELPER_FILE, len(helper))
    return helper_module.Baseline, baseline, inventory, captured, helper


def old_module(baseline, captured, materialized_root=None, file_overrides=None):
    modules = baseline.load_modules({
        "coastal_980_historical": PROGRAM,
        "scripts.evidence.geometry": GEOMETRY,
        "ellipsoidal_area": ELLIPSOID,
    })
    mod = modules["coastal_980_historical"]
    repo_root = Path(materialized_root) if materialized_root else REPO
    mod.REPO = repo_root
    mod.ROOT = repo_root / "data/regional-review/coastal-reference-reproduction-980"
    if materialized_root:
        modules["scripts.evidence.geometry"].__file__ = str(repo_root / GEOMETRY)
    admission_path = next(path for path in captured if path.endswith("/runs/run-one/admission.json"))
    old_admission = json.loads(captured[admission_path])
    mod.verify_inputs = lambda: old_admission
    original_read = Path.read_bytes
    allowed = {str((repo_root / path).resolve()): raw for path, raw in captured.items()}

    def read_captured(path):
        key = str(Path(path).resolve())
        try:
            relative = Path(key).relative_to(repo_root).as_posix()
        except ValueError:
            relative = None
        if relative in (file_overrides or {}):
            return file_overrides[relative]
        if key in allowed:
            return allowed[key]
        if Path(key).is_relative_to(repo_root):
            relative = Path(key).relative_to(repo_root).as_posix()
            drift_path = repo_root / GEOMETRY
            if relative == GEOMETRY and materialized_root and drift_path.is_file():
                return drift_path.read_bytes()
            raise Refusal("historical program attempted an unpinned repository read: " + relative)
        return original_read(path)

    Path.read_bytes = read_captured
    try:
        result = mod.compute()
    finally:
        Path.read_bytes = original_read
    values = dict(zip(PRODUCTS, result))
    return modules, {name: canonical(values[name]) for name in PRODUCTS}


def historical_products(inventory, captured, run="run-one"):
    rows = [row for row in inventory["historical_outputs"] if row["run"] == run]
    values = {row["product"]: captured[row["path"]] for row in rows}
    if set(values) != set(PRODUCTS):
        raise Refusal("retained historical product inventory is incomplete")
    return values


def verify_environment():
    import pyproj
    import shapely
    values = {"python": sys.version.split()[0], "shapely": shapely.__version__, "pyproj": pyproj.__version__}
    expected = {"python": "3.12.14", "shapely": "2.1.2", "pyproj": "3.7.2"}
    if values != expected:
        raise Refusal(f"runtime differs from retained calculation environment: {values}")
    return values


def created_file(path: Path, raw: bytes, created: list, writer=None):
    with path.open("xb") as stream:
        info = os.fstat(stream.fileno())
        created.append((path, info.st_dev, info.st_ino))
        (writer or (lambda out, data: out.write(data)))(stream, raw)
        stream.flush()
        os.fsync(stream.fileno())


def cleanup_owned_files(created):
    for path, device, inode in reversed(created):
        try:
            current = path.lstat()
            if stat.S_ISREG(current.st_mode) and current.st_dev == device and current.st_ino == inode:
                path.unlink()
        except OSError:
            pass


def publish(directory: Path, products: dict, writer=None):
    """Publish exclusively and clean only inode-authenticated invocation output."""
    if directory.exists() or directory.is_symlink():
        raise FileExistsError("refuse occupied output vintage")
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir(exist_ok=False)
    owned = directory.lstat()
    created = []
    try:
        for name, raw in products.items():
            created_file(directory / name, raw, created, writer)
        receipt = canonical({"version": 1, "status": "complete", "outputs": [
            {"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in products.items()
        ]})
        if len(receipt) > 4096:
            raise Refusal("completion receipt exceeds 4 KiB")
        pending = directory / ".publication-incomplete"
        created_file(pending, receipt, created)
        final = directory / "publication.json"
        os.link(pending, final)
        final_info = final.lstat()
        created.append((final, final_info.st_dev, final_info.st_ino))
        pending.unlink()
        created[:] = [row for row in created if row[0] != pending]
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        cleanup_owned_files(created)
        try:
            now = directory.lstat()
            if (stat.S_ISDIR(now.st_mode) and now.st_dev == owned.st_dev and now.st_ino == owned.st_ino
                    and not any(directory.iterdir())):
                directory.rmdir()
        except OSError:
            pass
        raise


def run_one(run_id):
    immutable, _ = trusted_immutable()
    safe_run_id(run_id)
    _, baseline, inventory, captured, helper = load_baseline()
    environment = verify_environment()
    names = [*PRODUCTS, "execution-evidence.json"]
    admitted = immutable.NewVintage(baseline, OWNED, run_id, names)  # destination admitted before compute
    modules, computed = old_module(baseline, captured)
    expected = historical_products(inventory, captured)
    if computed != expected:
        raise Refusal("reproduced four products differ from retained historical baseline")
    module_bytes = {
        PROGRAM: captured[PROGRAM], GEOMETRY: captured[GEOMETRY], ELLIPSOID: captured[ELLIPSOID],
        HELPER_FILE: helper,
    }
    evidence = {
        "schema": "coastal-integrity-execution:v1", "issue": 1381, "run_id": run_id,
        "checkout_head": git("rev-parse", "HEAD").decode().strip(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "command": f"python3.12 {Path(__file__).relative_to(REPO)} --run-id {run_id}",
        "source_commit": SOURCE_COMMIT, "source_pin_inventory_sha256": PIN_FILE_SHA256,
        "runner_sha256": sha(Path(__file__).read_bytes()), "trusted_reader_sha256": sha(helper),
        "executed_project_code": [
            {"path": path, "bytes": len(raw), "sha256": sha(raw), "loaded_from": "immutable Git object bytes"}
            for path, raw in module_bytes.items()
        ],
        "loaded_module_sha256": {
            "coastal_980_historical": sha(captured[PROGRAM]),
            "scripts.evidence.geometry": sha(captured[GEOMETRY]),
            "ellipsoidal_area": sha(captured[ELLIPSOID]),
        },
        "environment": environment,
        "products_match_retained_run_one": True,
        "limits": ["The captured historical code is cooperatively executed, not sandboxed."],
    }
    output = {**computed, "execution-evidence.json": canonical(evidence)}
    for name, raw in output.items():
        if len(raw) > 32 * 1024 * 1024:
            raise Refusal("output exceeds per-file bound")
    if sum(baseline.consumed.values()) + sum(map(len, output.values())) + 4096 > 256 * 1024 * 1024:
        raise Refusal("complete raw/decoded/code/output phase exceeds 256 MiB")
    # Reuse the shared admission object for its preflight/pin check; publication
    # uses the inode-bound writer because shared NewVintage intentionally retains
    # partial directories and does not authenticate directory ownership cleanup.
    if admitted.root.exists():
        raise FileExistsError("output vintage appeared after admission")
    for path in baseline.pins:
        baseline.pinned_bytes(path)
    publish(admitted.root, output)
    return {name: sha(raw) for name, raw in output.items()}


def run_pair(run_one_id, run_two_id):
    safe_run_id(run_one_id)
    safe_run_id(run_two_id)
    if run_one_id == run_two_id:
        raise Refusal("pair comparison requires two distinct output vintages")
    _, baseline, inventory, captured, _ = load_baseline()
    immutable, _ = trusted_immutable()
    name = "pair-" + sha((run_one_id + "\0" + run_two_id).encode())[:12]
    admitted = immutable.NewVintage(baseline, OWNED, name, ["pair-comparison.json"])
    expected = historical_products(inventory, captured)
    runner_hash = sha(Path(__file__).read_bytes())
    checked = []
    for run_id in (run_one_id, run_two_id):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
            raise Refusal("unsafe run ID")
        root = REPO / OWNED / "vintages" / run_id
        if not root.is_dir() or root.is_symlink():
            raise Refusal("missing or unsafe output vintage")
        receipt = json.loads((root / "publication.json").read_bytes())
        if receipt.get("status") != "complete" or receipt.get("version") != 1:
            raise Refusal("incomplete output vintage")
        hashes = {}
        actual_outputs = {}
        for product in (*PRODUCTS, "execution-evidence.json"):
            target = root / product
            if target.is_symlink() or not target.is_file():
                raise Refusal("missing or unsafe published product: " + product)
            raw = target.read_bytes()
            baseline.admit(f"pair:{run_id}:{product}", len(raw))
            actual_outputs[product] = raw
            if product in expected and raw != expected[product]:
                raise Refusal(f"fresh product differs from retained historical baseline: {run_id}/{product}")
            if product in expected:
                hashes[product] = sha(raw)
        actual_receipt = [{"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in actual_outputs.items()]
        if receipt.get("outputs") != actual_receipt:
            raise Refusal("published receipt does not bind the complete actual product set")
        execution = json.loads(actual_outputs["execution-evidence.json"])
        if (execution.get("runner_sha256") != runner_hash
                or execution.get("source_commit") != SOURCE_COMMIT
                or execution.get("loaded_module_sha256") != {
                    "coastal_980_historical": sha(captured[PROGRAM]),
                    "scripts.evidence.geometry": sha(captured[GEOMETRY]),
                    "ellipsoidal_area": sha(captured[ELLIPSOID]),
                }):
            raise Refusal("execution record does not bind this runner and captured code closure")
        checked.append(hashes)
    if checked[0] != checked[1]:
        raise Refusal("fresh product vintages are not byte-identical")
    result = {"method_id": "coastal-eight-county-fresh-reproduction", "kind": "code",
              "outcome": "passed", "issue": 1381, "run_ids": [run_one_id, run_two_id],
              "both_runs_match_retained_originals": True, "run_bytes_match": True,
              "products": [{"path": key, "sha256": value} for key, value in checked[0].items()]}
    raw = canonical(result)
    baseline.admit("pair-output", len(raw))
    for path in baseline.pins:
        baseline.pinned_bytes(path)
    publish(admitted.root, {"pair-comparison.json": raw})
    return result


def controls():
    immutable, _ = trusted_immutable()
    _, baseline, inventory, captured, _ = load_baseline()
    vintage = "controls-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    admitted = immutable.NewVintage(baseline, OWNED, vintage, ["control-results.json"])
    (REPO / OWNED).mkdir(parents=True, exist_ok=True)
    bad_names = ["../escape", "/absolute", "a/b", "a\\b", ".", ""]
    rejected_names = 0
    for value in bad_names:
        try:
            safe_run_id(value)
        except Refusal:
            rejected_names += 1
    if rejected_names != len(bad_names):
        raise Refusal("path traversal run-name control failed")
    modules, products = old_module(baseline, captured)
    expected = historical_products(inventory, captured)
    if products != expected:
        raise Refusal("positive scientific control failed: actual retained calculation changed")
    mod = modules["coastal_980_historical"]
    # Exercise the actual duplicate and roster predicates used by the historical
    # calculation, with records that would otherwise silently collapse in a dict.
    duplicate_rejected = False
    try:
        mod.unique_index([{"properties": {"GEOID": "13051"}}, {"properties": {"GEOID": "13051"}}], "GEOID", "fixture")
    except mod.Refusal:
        duplicate_rejected = True
    if not duplicate_rejected:
        raise Refusal("duplicate source identity was accepted")
    roster_rejected = False
    try:
        mod.ensure_roster({"wrong": {}}, {"expected"}, "fixture")
    except mod.Refusal:
        roster_rejected = True
    if not roster_rejected:
        raise Refusal("incomplete identity roster was accepted")
    # The original source registry is checked by the real calculation. Its
    # complete 36-item inventory must reject a stale/short fixture before output.
    world = json.loads(captured["data/world-index.json"])
    if len(world.get("parts", [])) != 36 or len(set(world["parts"])) != 36:
        raise Refusal("retained registry is not the expected complete vintage")
    stale_world = dict(world, parts=world["parts"][:-1])
    stale_world_bytes = canonical(stale_world)
    stale_rejected = False
    try:
        old_module(baseline, captured, file_overrides={"data/world-index.json": stale_world_bytes})
    except RuntimeError:
        stale_rejected = True
    if not stale_rejected:
        raise Refusal("actual calculation accepted a stale world-index registry")
    # A changed real input hash is rejected by the immutable baseline before a
    # destination can be created.
    index_pin = next(row for row in inventory["inputs"] if row["path"] == "data/world-index.json")
    bad_pin = {**index_pin, "sha256": "0" * 64, "hash_kind": "file-bytes"}
    changed_rejected = False
    try:
        immutable.Baseline(str(REPO), SOURCE_COMMIT, [bad_pin])
    except ValueError:
        changed_rejected = True
    if not changed_rejected or admitted.root.exists():
        raise Refusal("changed-input control did not reject before output creation")
    # Admit every intentionally materialized fixture before creating its path.
    duplicate_fixture = canonical([{"properties": {"GEOID": "13051"}}, {"properties": {"GEOID": "13051"}}])
    roster_fixture = canonical({"wrong": {}})
    sentinel_fixture = b"pre-existing sentinel\n"
    replacement_fixture = b"foreign replacement sentinel\n"
    partial_fixture = b"a bounded partial product fixture"
    drift_marker = b"\nDRIFT_FIXTURE_MARKER = 'untrusted-materialized-helper'\n"
    for name, raw in (("fixture:duplicate", duplicate_fixture), ("fixture:wrong-roster", roster_fixture),
                      ("fixture:stale-registry", stale_world_bytes), ("fixture:occupied-sentinel", sentinel_fixture),
                      ("fixture:replacement-sentinel", replacement_fixture), ("fixture:partial-product", partial_fixture)):
        baseline.admit(name, len(raw))

    # Occupied-target control uses an exact sentinel and the producer entry point.
    directory_evidence = {}
    with tempfile.TemporaryDirectory(prefix="coastal-control-", dir=REPO / OWNED) as scratch:
        root = Path(scratch)
        occupied = root / "occupied"
        occupied.mkdir()
        sentinel = occupied / "sentinel"
        sentinel.write_bytes(sentinel_fixture)
        before = sentinel.read_bytes()
        occupied_rejected = False
        try:
            publish(occupied, {"product.json": b"must not write"})
        except FileExistsError:
            occupied_rejected = sentinel.read_bytes() == before
        if not occupied_rejected:
            raise Refusal("occupied output did not preserve its original sentinel")

        own_failure_target = root / "own-failure"
        partial_attempt = {}

        def fail_own_partial(stream, data):
            attempted = data[:max(1, len(data) // 2)]
            stream.write(attempted)
            stream.flush()
            partial_attempt["bytes"] = attempted
            raise OSError("injected partial write without directory replacement")

        own_failure_rejected = False
        try:
            publish(own_failure_target, {"partial-product.json": partial_fixture}, fail_own_partial)
        except OSError as exc:
            own_failure_rejected = str(exc) == "injected partial write without directory replacement"
        if (not own_failure_rejected or own_failure_target.exists() or own_failure_target.is_symlink()
                or not partial_attempt.get("bytes")):
            raise Refusal("ordinary partial-write cleanup did not remove its own failed output")

        # Fault the actual first output writer after a partial write, swap the
        # invocation's directory for a different directory, then raise. Cleanup
        # must leave the replacement inode and every foreign entry untouched.
        target = root / "swap-target"
        moved = root / "original-owned-directory"
        replacement_marker = replacement_fixture
        identities = {}

        def replace_after_partial(stream, data):
            stream.write(data[:max(1, len(data) // 2)])
            stream.flush()
            before_info = target.lstat()
            os.rename(target, moved)
            target.mkdir()
            marker = target / "foreign-sentinel"
            marker.write_bytes(replacement_marker)
            identities["replacement_dev"] = target.lstat().st_dev
            identities["replacement"] = target.lstat().st_ino
            identities["original_dev"] = before_info.st_dev
            identities["original"] = before_info.st_ino
            raise OSError("injected after actual first partial product write")

        injected = False
        try:
            publish(target, {"partial-product.json": partial_fixture}, replace_after_partial)
        except OSError as exc:
            injected = str(exc) == "injected after actual first partial product write"
        if not injected or not moved.is_dir() or not target.is_dir():
            raise Refusal("directory replacement fault did not reach actual publisher cleanup")
        marker = target / "foreign-sentinel"
        if marker.read_bytes() != replacement_marker or target.lstat().st_ino != identities["replacement"]:
            raise Refusal("cleanup altered the different replacement directory")
        partial = moved / "partial-product.json"
        if not partial.is_file() or partial.stat().st_size == 0:
            raise Refusal("the command-owned partial product was not retained as failure evidence")
        partial_bytes = partial.read_bytes()
        directory_evidence = {
            "fault": "injected after actual first partial product write",
            "owned_directory_identity_before_replacement": [identities["original_dev"], identities["original"]],
            "replacement_directory_identity_after_cleanup": [target.lstat().st_dev, target.lstat().st_ino],
            "replacement_directory_identity_before_cleanup": [identities["replacement_dev"], identities["replacement"]],
            "replacement_sentinel": {"path": "foreign-sentinel", "bytes": len(replacement_marker),
                                      "sha256": sha(replacement_marker), "preserved": marker.read_bytes() == replacement_marker},
            "ordinary_partial_write": {"attempted_bytes": len(partial_attempt["bytes"]),
                                       "attempted_sha256": sha(partial_attempt["bytes"]),
                                       "own_output_removed": own_failure_rejected and not own_failure_target.exists()},
            "moved_original_partial": {"path": "original-owned-directory/partial-product.json",
                                       "bytes": len(partial_bytes), "sha256": sha(partial_bytes),
                                       "hex": partial_bytes.hex(), "preserved": True},
        }

    # Retain the complete altered module at the exact fixture import path. The
    # executable loader reads the pinned Git blob instead of this materialized
    # replacement; the unique marker must stay unexecuted while products match.
    fixture_root = REPO / OWNED / "validation/fixtures/code-drift-checkout"
    helper_fixture = fixture_root / GEOMETRY
    altered = captured[GEOMETRY] + drift_marker
    baseline.admit("fixture:complete-altered-geometry-module", len(altered))
    helper_fixture.parent.mkdir(parents=True, exist_ok=True)
    if helper_fixture.exists():
        if helper_fixture.is_symlink() or helper_fixture.read_bytes() != altered:
            raise Refusal("retained complete code-drift fixture is occupied by different bytes")
    else:
        with helper_fixture.open("xb") as stream:
            stream.write(altered)
            stream.flush()
            os.fsync(stream.fileno())
    marker_present_on_disk = b"untrusted-materialized-helper" in helper_fixture.read_bytes()
    drift_modules, drift_products = old_module(baseline, captured, materialized_root=fixture_root,
                                                file_overrides={GEOMETRY: altered})
    actual_module = drift_modules["scripts.evidence.geometry"]
    if not marker_present_on_disk or hasattr(actual_module, "DRIFT_FIXTURE_MARKER") or drift_products != expected:
        raise Refusal("actual import path did not execute captured bytes under materialized helper drift")

    result = {
        "method_id": "coastal-integrity-adversarial-controls", "kind": "code", "outcome": "passed",
        "issue": 1381, "traversal_names_rejected": rejected_names, "changed_input_rejected_before_output": changed_rejected,
        "stale_registry_rejected": stale_rejected, "duplicate_identity_rejected": duplicate_rejected,
        "incomplete_roster_rejected": roster_rejected, "occupied_target_sentinel_preserved": occupied_rejected,
        "replacement_directory_and_foreign_sentinel_preserved": True,
        "ordinary_partial_write_removed_only_owned_output": True,
        "partial_command_product_retained_in_moved_original_directory": True,
        "directory_replacement_failure_evidence": directory_evidence,
        "materialized_helper_drift_marker_present": marker_present_on_disk,
        "altered_helper_fixture": {"path": str(helper_fixture.relative_to(REPO)), "bytes": len(altered),
                                   "sha256": sha(altered), "pinned_executed_sha256": sha(captured[GEOMETRY])},
        "executed_helper_is_pinned_git_blob": not hasattr(actual_module, "DRIFT_FIXTURE_MARKER"),
        "actual_positive_products_match_retained_baseline": True,
        "scientific_negative_axis_control_in_retained_product": json.loads(products["negative-control.json"]),
        "limits": ["The retained comparison remains a statistical screen; it does not establish legal boundaries or shoreline completeness."]
    }
    raw = canonical(result)
    baseline.admit("control-output", len(raw))
    for path in baseline.pins:
        baseline.pinned_bytes(path)
    publish(admitted.root, {"control-results.json": raw})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--verify-pair", nargs=2)
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    if args.run_id:
        print(json.dumps(run_one(args.run_id), indent=2))
    elif args.verify_pair:
        print(json.dumps(run_pair(*args.verify_pair), indent=2))
    elif args.controls_only:
        print(json.dumps(controls(), indent=2))
    else:
        parser.error("--run-id is required")


if __name__ == "__main__":
    try:
        main()
    except (Refusal, FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        sys.exit(2)
