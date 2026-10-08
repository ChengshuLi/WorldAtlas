#!/usr/bin/env python3
"""Verify and reproduce the exact 268-subject #1146 source handoff safely.

All immutable inputs are admitted by exact commit, path, length and whole-file
SHA-256 before any result directory is created. Each result vintage must be a
new direct child of this packet's runs/ directory.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
RUNS = PACKET / "runs"
PIN_FILE = PACKET / "source-pins.json"
PIN_INVENTORY_SHA256 = "a6b40dd3f1161d32dea5d0559f517158b4a58af509a668539f514be007f4d2b2"
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
ZIP_PATH = "data/regional-review/south-atlantic-source-reuse-basis-429/sources/cb_2018_us_county_500k.zip"
OLD_CODE_PATH = "data/regional-review/south-atlantic-source-reuse-basis-429/reproduce.py"
OLD_CROSSWALK_PATH = "data/regional-review/south-atlantic-source-reuse-basis-429/subject-source-crosswalk.jsonl"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
        stderr=subprocess.PIPE,
        timeout=30,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_pins() -> tuple[dict, dict[str, bytes]]:
    raw = PIN_FILE.read_bytes()
    require(sha256(raw) == PIN_INVENTORY_SHA256,
            "Issue-declared source pin inventory was altered")
    pins = json.loads(raw)
    rows = pins.get("inputs")
    require(pins.get("version") == 1 and pins.get("issue") == 1369, "Wrong pin inventory")
    require(len(rows) == 36 and len({row["key"] for row in rows}) == 36,
            "The declared 36-input pin inventory is incomplete or duplicated")
    require(len({row["path"] for row in rows}) == 36, "Pin inventory repeats an input path")
    total, checked = 0, {}
    for row in rows:
        require(row["bytes"] <= MAX_FILE, "A pinned input exceeds the 32 MiB file bound")
        total += row["bytes"]
        require(total <= MAX_TOTAL, "Pinned inputs exceed the 256 MiB phase bound")
        data = git_bytes(row["commit"], row["path"])
        require(len(data) == row["bytes"] and sha256(data) == row["sha256"],
                f"Immutable input pin mismatch before output creation: {row['key']}")
        checked[row["key"]] = data
    verify_census_zip_pin(checked["original_1146_14"])
    return pins, checked


def verify_census_zip_pin(raw: bytes) -> None:
    require(len(raw) == 11_530_479 and sha256(raw) ==
            "aaa866af327754e1b80aa87bfb97b04a7209f4f871075aef84affb8f0b3afe67",
            "Complete Census CBF ZIP does not match its declared source pin")


def load_pinned_producer(code: bytes):
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("pinned_1146_reproducer", loader=None)
    )
    module.__file__ = str(ROOT / OLD_CODE_PATH)
    exec(compile(code, module.__file__, "exec"), module.__dict__)
    return module


def bounded_archive(zip_bytes: bytes):
    require(len(zip_bytes) <= MAX_FILE, "Compressed archive exceeds the 32 MiB bound")
    archive = zipfile.ZipFile(io.BytesIO(zip_bytes), "r")
    infos = archive.infolist()
    require(len(infos) <= 100 and len({item.filename for item in infos}) == len(infos),
            "Archive has duplicate members or exceeds the member-count bound")
    unpacked = 0
    for item in infos:
        require(not item.flag_bits & 1, "Encrypted ZIP members are not accepted")
        require(item.file_size <= MAX_FILE, "ZIP member exceeds the 32 MiB bound")
        unpacked += item.file_size
        require(unpacked <= MAX_TOTAL, "ZIP expansion exceeds the 256 MiB phase bound")
        require(item.compress_size == 0 or item.file_size <= item.compress_size * 100,
                "ZIP member exceeds the 100:1 expansion bound")
    expected = {"cb_2018_us_county_500k.dbf", "cb_2018_us_county_500k.cpg"}
    require({item.filename for item in infos} >= expected, "Expected 2018 Census DBF/CPG members are absent")
    dbfs = [item.filename for item in infos if item.filename.lower().endswith(".dbf")]
    require(dbfs == ["cb_2018_us_county_500k.dbf"], "Unexpected Census DBF inventory")
    return archive, unpacked


def safe_output_path(relative: str, receipt: str | None) -> tuple[Path, Path | None]:
    require(relative and not Path(relative).is_absolute() and ".." not in Path(relative).parts,
            "Output directory must be a safe relative path")
    target = (PACKET / relative).resolve()
    require(RUNS == PACKET / "runs" and not RUNS.is_symlink(),
            "Output root must be the ordinary owned runs directory")
    require(target.parent == RUNS.resolve(), "Output must be a direct child of this packet's runs directory")
    require(not target.exists(), "Output vintage already exists; outputs are immutable")
    receipt_path = None
    if receipt is not None:
        require(not Path(receipt).is_absolute() and ".." not in Path(receipt).parts,
                "Receipt path must be relative to the new output vintage")
        receipt_path = (target / receipt).resolve()
        require(target in receipt_path.parents and receipt_path.suffix == ".json",
                "Receipt must be a JSON path inside the new output vintage")
    return target, receipt_path


def write_fresh(target: Path, files: dict[str, bytes]) -> None:
    total = sum(len(value) for value in files.values())
    require(all(len(value) <= MAX_FILE for value in files.values()) and total <= MAX_TOTAL,
            "Generated outputs exceed declared file/phase bounds")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=False, exist_ok=False)
    for name, data in files.items():
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts,
                "Unsafe output filename")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(destination, flags, 0o644)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)


def build_result(pins: dict, checked: dict[str, bytes], module, run_name: str):
    contract = json.loads(checked["original_1146_4"])
    expected = contract["issue"]["machine_contract"]["evidence_quality"]["subject_ids"]
    require(len(expected) == 268 and len(set(expected)) == 268, "Exact 268-subject scope is invalid")
    scope = json.loads(checked["baseline_7"])
    require(expected == scope["member_location_ids"], "Subject roster differs from the pinned regional scope")

    archive, expanded_bytes = bounded_archive(checked["original_1146_14"])
    with archive:
        cpg = archive.read("cb_2018_us_county_500k.cpg").decode("ascii").strip()
        require(cpg.upper() == "UTF-8", "Unexpected Census DBF text encoding")
        dbf = archive.read("cb_2018_us_county_500k.dbf")
    record_count, cbf_rows = module.parse_dbf(dbf)
    require(record_count == 3233 and len(cbf_rows) == 3233, "Census 2018 DBF roster differs")
    cbf_index = {}
    for row in cbf_rows:
        cbf_index.setdefault((row["STATEFP"], row["NAME"]), []).append(row)

    feature_collection = json.loads(checked["baseline_10"])
    feature_map = {}
    for feature in feature_collection["features"]:
        shape_id = feature.get("properties", {}).get("shapeID")
        require(shape_id and shape_id not in feature_map, "Missing or duplicate geoBoundaries shapeID")
        feature_map[shape_id] = feature
    with io.TextIOWrapper(io.BytesIO(checked["baseline_13"]), encoding="utf-8", newline="") as stream:
        assessments = list(csv.DictReader(stream))
    by_id = {row["atlas_id"]: row for row in assessments}
    require(len(assessments) == len(by_id) == 268 and set(by_id) == set(expected),
            "Subject assessments differ from the exact scope")
    state_fips = {"Florida": "12", "North Carolina": "37", "South Carolina": "45", "West Virginia": "54"}
    crosswalk = module.build_crosswalk(expected, by_id, feature_map, cbf_index, state_fips)
    crosswalk_bytes = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":")) + "\n"
                               for row in crosswalk).encode("utf-8")
    require(crosswalk_bytes == checked["original_1146_23"],
            "Independent recomputation differs from the immutable retained crosswalk")

    def rejected(call):
        try:
            call()
        except (ValueError, KeyError):
            return True
        return False

    duplicate_rejected = rejected(lambda: module.build_crosswalk(
        expected + [expected[0]], by_id, feature_map, cbf_index, state_fips))
    first_assessment = by_id[expected[0]]
    first_key = (state_fips[first_assessment["parent_name"]], first_assessment["source_name"])
    missing_index = dict(cbf_index)
    missing_index.pop(first_key)
    missing_rejected = rejected(lambda: module.build_crosswalk(
        expected, by_id, feature_map, missing_index, state_fips))
    ambiguous_index = dict(cbf_index)
    ambiguous_index[first_key] = list(cbf_index[first_key]) + [dict(cbf_index[first_key][0])]
    ambiguous_rejected = rejected(lambda: module.build_crosswalk(
        expected, by_id, feature_map, ambiguous_index, state_fips))
    require(duplicate_rejected and missing_rejected and ambiguous_rejected,
            "Duplicate/missing/ambiguous join control did not fail")

    pin_rows = [{"key": row["key"], "commit": row["commit"], "path": row["path"],
                 "bytes": len(checked[row["key"]]), "sha256": sha256(checked[row["key"]])}
                for row in pins["inputs"]]
    digest_bytes = (json.dumps({"version": 1, "issue": 1369, "run_id": run_name,
                                "inputs": pin_rows}, sort_keys=True, indent=2) + "\n").encode()
    summary = {
        "version": 1,
        "issue": 1369,
        "run_id": run_name,
        "python": sys.version.split()[0],
        "integrity_reproducer_sha256": sha256((PACKET / "reproduce_integrity.py").read_bytes()),
        "source_pin_inventory_sha256": sha256(PIN_FILE.read_bytes()),
        "baseline_commit": pins["baseline_commit"],
        "affected_merge": pins["affected_merge"],
        "subject_count": len(expected),
        "unique_subject_count": len(set(expected)),
        "census_archive_bytes": len(checked["original_1146_14"]),
        "census_archive_sha256": sha256(checked["original_1146_14"]),
        "census_archive_expanded_bytes": expanded_bytes,
        "census_dbf_rows": record_count,
        "scoped_unique_name_state_matches": len(crosswalk),
        "unique_source_shape_ids": len({row["source_shape_id"] for row in crosswalk}),
        "unique_census_geoids": len({row["census_2018_geoid"] for row in crosswalk}),
        "retained_crosswalk_sha256": sha256(crosswalk_bytes),
        "comparison": "byte-identical to exact retained PR #1146 crosswalk",
        "limits": [
            "This checks identity and source-vintage joins, not polygon equivalence or legal boundaries.",
            "It does not establish current county validity or completeness beyond the exact 268-subject scope.",
            "The exact scope, 2018 source vintage, and derivative-rights uncertainty are preserved.",
        ],
    }
    summary_bytes = (json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    positive = {"issue": 1369, "kind": "positive-control", "outcome": "passed",
                "subjects": 268, "source_matches": 268, "census_matches": 268,
                "archive_pin_checked_before_output_creation": True,
                "crosswalk_matches_retained": True}
    negative = {"issue": 1369, "kind": "negative-controls", "outcome": "passed",
                "wrong_archive_bytes_rejected_before_join": True,
                "same_state_geoid_swap_rejected_by_archive_pin": True,
                "archive_comment_drift_rejected_by_archive_pin": True,
                "duplicate_subject_rejected": duplicate_rejected,
                "missing_census_join_rejected": missing_rejected,
                "ambiguous_census_join_rejected": ambiguous_rejected,
                "existing_output_and_invalid_receipt_rejected_before_new_writes": True,
                "legacy_main_overwrite_and_late_receipt_failure_reproduced_in_isolation": True}
    phase_bytes = sum(row["bytes"] for row in pin_rows) + expanded_bytes + sum(map(len, (
        digest_bytes, crosswalk_bytes, summary_bytes,
        (json.dumps(positive, sort_keys=True, indent=2) + "\n").encode(),
        (json.dumps(negative, sort_keys=True, indent=2) + "\n").encode())))
    require(phase_bytes <= MAX_TOTAL, "Complete input, expanded data and output phase exceeds 256 MiB")
    return {
        "baseline-input-digests.json": digest_bytes,
        "subject-source-crosswalk.jsonl": crosswalk_bytes,
        "reproduction-summary.json": summary_bytes,
        "positive-control.json": (json.dumps(positive, sort_keys=True, indent=2) + "\n").encode(),
        "negative-control.json": (json.dumps(negative, sort_keys=True, indent=2) + "\n").encode(),
    }


def run_legacy_main(code: bytes, contract: bytes, zip_bytes: bytes, mode: str) -> dict:
    """Execute the exact merged main in a throwaway Git-linked packet sandbox."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="worldatlas-1369-legacy-") as temp:
        scratch = Path(temp)
        common_git = Path(subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            text=True).strip())
        (scratch / ".git").symlink_to(common_git, target_is_directory=True)
        packet = scratch / "data/regional-review/south-atlantic-source-reuse-basis-429"
        (packet / "sources").mkdir(parents=True)
        (packet / "reproduce.py").write_bytes(code)
        (packet / "issue-1143-contract.json").write_bytes(contract)
        (packet / "sources/cb_2018_us_county_500k.zip").write_bytes(zip_bytes)
        first = subprocess.run([sys.executable, str(packet / "reproduce.py")],
                               capture_output=True, text=True, timeout=60)
        require(first.returncode == 0, "Isolated exact-merge producer failed unexpectedly")
        generated = ["baseline-input-digests.json", "subject-source-crosswalk.jsonl",
                     "reproduction-summary.json", "positive-control.json", "negative-control.json"]
        result = {"first_run": "passed", "mode": mode}
        old = {name: (packet / name).read_bytes() for name in generated}
        result["first_outputs_sha256"] = {name: sha256(value) for name, value in old.items()}
        if mode == "geoid-swap":
            result["wrong_crosswalk_jsonl"] = old["subject-source-crosswalk.jsonl"].decode("utf-8")
        second = subprocess.run([sys.executable, str(packet / "reproduce.py")],
                                 capture_output=True, text=True, timeout=60)
        result["existing_output_run"] = "passed-and-replaced" if second.returncode == 0 and all(
            (packet / name).read_bytes() == old[name] for name in generated) else "unexpected"
        require(result["existing_output_run"] == "passed-and-replaced",
                "Legacy existing-output behavior did not reproduce")
        for name in generated:
            (packet / name).write_bytes(("sentinel:" + name).encode())
        invalid = subprocess.run([sys.executable, str(packet / "reproduce.py"), "receipt.txt"],
                                 capture_output=True, text=True, timeout=60)
        after = {name: (packet / name).read_bytes() for name in generated}
        result["invalid_receipt_exit"] = invalid.returncode
        result["invalid_receipt_error"] = "Run receipt must be a JSON path inside this packet" in invalid.stderr
        result["invalid_receipt_stderr"] = invalid.stderr
        result["invalid_receipt_stdout"] = invalid.stdout
        result["outputs_replaced_before_failure"] = all(
            after[name] != ("sentinel:" + name).encode() for name in generated)
        result["failure_outputs_sha256"] = {name: sha256(value) for name, value in after.items()}
        require(invalid.returncode != 0 and result["invalid_receipt_error"] and
                result["outputs_replaced_before_failure"], "Legacy late-receipt failure changed")
        if mode == "geoid-swap":
            crosswalk = [json.loads(line) for line in (packet / "subject-source-crosswalk.jsonl").read_text().splitlines()]
            lancaster = next(row for row in crosswalk if row["atlas_id"] ==
                             "gb:USA:ADM2:52423323B10055621117527")
            result["mutated_lancaster_geoid"] = lancaster["census_2018_geoid"]
            require(lancaster["census_2018_geoid"] == "45013",
                    "Same-state GEOID-swap reproduction differs from issue finding")
            result["both_controls_passed"] = all(json.loads((packet / name).read_text())["outcome"] == "passed"
                                                for name in ("positive-control.json", "negative-control.json"))
        if mode == "zip-comment":
            summary = json.loads((packet / "reproduction-summary.json").read_text())
            result["changed_zip_hash_recorded_after_acceptance"] = summary["census_cb_zip_sha256"] != \
                "aaa866af327754e1b80aa87bfb97b04a7209f4f871075aef84affb8f0b3afe67"
            require(result["changed_zip_hash_recorded_after_acceptance"],
                    "ZIP-comment drift did not reproduce")
        return result


def mutate_zip_comment(raw: bytes) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(raw), "r")
    output = io.BytesIO()
    with source, zipfile.ZipFile(output, "w") as destination:
        for info in source.infolist():
            destination.writestr(info, source.read(info.filename))
        destination.comment = b"comment-only mutation; payload unchanged"
    return output.getvalue()


def mutate_same_state_geoid(raw: bytes, module) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(raw), "r")
    output = io.BytesIO()
    with source:
        dbf = bytearray(source.read("cb_2018_us_county_500k.dbf"))
        offset, fields = 32, []
        while dbf[offset] != 13:
            desc = dbf[offset:offset + 32]
            name = desc[:11].split(b"\0", 1)[0].decode("ascii")
            width = desc[16]
            fields.append((name, width))
            offset += 32
        header = int.from_bytes(dbf[8:10], "little")
        record_length = int.from_bytes(dbf[10:12], "little")
        positions, cursor = {}, 1
        for name, width in fields:
            positions[name] = (cursor, width)
            cursor += width
        count = int.from_bytes(dbf[4:8], "little")
        rows = {}
        for index in range(count):
            start = header + index * record_length
            record = dbf[start:start + record_length]
            values = {name: bytes(record[pos:pos + width]).decode("utf-8").strip()
                      for name, (pos, width) in positions.items()}
            if values.get("STATEFP") == "45" and values.get("NAME") in {"Lancaster", "Beaufort"}:
                rows[values["NAME"]] = (start, values)
        require(set(rows) == {"Lancaster", "Beaufort"}, "Expected South Carolina control counties missing")
        for name, other in (("Lancaster", "Beaufort"), ("Beaufort", "Lancaster")):
            start, _ = rows[name]
            other_values = rows[other][1]
            for field in ("COUNTYFP", "GEOID"):
                pos, width = positions[field]
                value = other_values[field].encode("ascii").rjust(width, b" ")
                dbf[start + pos:start + pos + width] = value
        with zipfile.ZipFile(output, "w") as destination:
            for info in source.infolist():
                payload = bytes(dbf) if info.filename == "cb_2018_us_county_500k.dbf" else source.read(info.filename)
                destination.writestr(info, payload)
    return output.getvalue()


def exercise_legacy(code: bytes, contract: bytes, zip_bytes: bytes, module) -> dict:
    comment = run_legacy_main(code, contract, mutate_zip_comment(zip_bytes), "zip-comment")
    swap = run_legacy_main(code, contract, mutate_same_state_geoid(zip_bytes, module), "geoid-swap")
    return {"zip_comment_only": comment, "same_state_geoid_swap": swap}


def exercise_safe_guards(zip_bytes: bytes) -> dict:
    outcomes = {}
    for label, changed in (("comment_only", mutate_zip_comment(zip_bytes)),
                           ("same_state_geoid_swap", mutate_same_state_geoid(zip_bytes, None))):
        try:
            verify_census_zip_pin(changed)
            outcomes[label] = False
        except ValueError:
            outcomes[label] = True
    require(all(outcomes.values()), "Safe input guard accepted mutated Census archive bytes")
    # Exercise the production destination validator in a disposable packet tree.
    import tempfile
    global PACKET, RUNS
    original_packet, original_runs = PACKET, RUNS
    try:
        with tempfile.TemporaryDirectory(prefix="worldatlas-1369-destination-") as temp:
            PACKET = Path(temp)
            RUNS = PACKET / "runs"
            RUNS.mkdir()
            existing = RUNS / "existing"
            existing.mkdir()
            sentinel = existing / "prior.json"
            sentinel.write_text("preserve-me")
            for relative, receipt, label in (("runs/existing", "receipt.json", "existing_output"),
                                               ("runs/new", "../receipt.json", "invalid_receipt"),
                                               ("runs/new", "receipt.txt", "invalid_receipt_extension"),
                                               ("outside/new", "receipt.json", "outside_output")):
                try:
                    safe_output_path(relative, receipt)
                    outcomes[label] = False
                except ValueError:
                    outcomes[label] = True
            outcomes["existing_sentinel_unchanged"] = sentinel.read_text() == "preserve-me"
    finally:
        PACKET, RUNS = original_packet, original_runs
    require(all(outcomes.values()), "Safe output/receipt guard accepted an invalid destination")
    return outcomes


def main() -> None:
    require(len(sys.argv) in (2, 3), "Usage: reproduce_integrity.py RUN_NAME [RECEIPT.json]")
    require(sys.version_info >= (3, 12), "Python 3.12 or later is required for this reproduction")
    run_name = sys.argv[1]
    require(run_name and Path(run_name).name == run_name, "Run name must be a single path component")
    pins, checked = verify_pins()
    module = load_pinned_producer(checked["original_1146_7"])
    # All computation and legacy controls occur before any owned output is created.
    safe_guards = exercise_safe_guards(checked["original_1146_14"])
    legacy = exercise_legacy(checked["original_1146_7"], checked["original_1146_4"],
                             checked["original_1146_14"], module)
    target, receipt_path = safe_output_path(f"runs/{run_name}", sys.argv[2] if len(sys.argv) == 3 else "receipt.json")
    files = build_result(pins, checked, module, run_name)
    control_bytes = (json.dumps({"version": 1, "issue": 1369, "legacy_main": legacy,
                                 "safe_admission": safe_guards},
                                sort_keys=True, indent=2) + "\n").encode()
    files["legacy-controls.json"] = control_bytes
    receipt = {"version": 1, "issue": 1369, "run_id": run_name,
               "outputs": {name: {"bytes": len(data), "sha256": sha256(data)}
                           for name, data in sorted(files.items())}}
    receipt_bytes = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
    require(receipt_path is not None, "Validated receipt path unexpectedly absent")
    files["receipt.json"] = receipt_bytes
    expanded = json.loads(files["reproduction-summary.json"])['census_archive_expanded_bytes']
    phase_bytes = sum(len(value) for value in checked.values()) + expanded + sum(map(len, files.values()))
    require(phase_bytes <= MAX_TOTAL,
            "Complete inputs, archive expansion and all retained outputs exceed 256 MiB")
    write_fresh(target, files)
    print(json.dumps({"status": "passed", "run_id": run_name, "output_dir": str(target),
                      "files": len(files), "crosswalk_sha256": sha256(files["subject-source-crosswalk.jsonl"]),
                      "legacy_controls": {mode: {"swap_accepted": data.get("mutated_lancaster_geoid") == "45013",
                                                  "zip_drift_accepted": data.get("changed_zip_hash_recorded_after_acceptance"),
                                                  "late_receipt_failure": data.get("invalid_receipt_error") and data.get("outputs_replaced_before_failure")}
                                          for mode, data in legacy.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
