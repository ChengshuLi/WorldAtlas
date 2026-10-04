#!/usr/bin/env python3
"""Reproduce issue #616 outputs from its immutable project/source snapshots.

Default operation is --check: it writes only to private temporary storage. To
create a packet vintage, pass --new-vintage NAME; the destination is exclusive.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = "research/geography/pacific-ne-source-reproduction-followup/"
PACKET = ROOT / OWNED.rstrip("/")
MANIFEST = PACKET / "evidence-quality.json"
PROJECT_BASELINE = "f592b3d8b72f40036218803d2c70c733112e4d37"
SOURCE_SNAPSHOT = "6c6271af6b0dac49b82eaafb2db4de8b9c4611f2"
ORIGINAL_PACKET = "data/regional-review/pacific-natural-earth-source-profiles-20261003"
SOURCE_QUALITY_PATH = ORIGINAL_PACKET + "/evidence-quality.json"
IDS = ["ASM-4998", "ASM-4999", "ASM-5000", "ASM-5001", "ASM-5002",
       "WLF-4995", "WLF-4996", "WLF-4997"]
GENERATED = ["issue-scope.json", "american-samoa-census-inventory.json",
             "wallis-futuna-insee-inventory.json",
             "american-samoa-census-geometry-comparison.json",
             "administrative-role-review.json",
             "natural-earth-current-geometry-comparison.json",
             "natural-earth-source-profiles.json"]
sys.path.insert(0, str(ROOT / "scripts"))
sys.dont_write_bytecode = True
from evidence.immutable import (  # noqa: E402
    Baseline, VERSION, canonical_json, descriptor, sha256,
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def read_at(commit: str, path: str) -> bytes:
    if ".." in pathlib.PurePosixPath(path).parts or path.startswith("/"):
        raise ValueError("unsafe committed source path")
    row = git("ls-tree", "-z", commit, "--", path).decode().rstrip("\0")
    if not row.startswith(("100644 ", "100755 ")) or row[row.find("\t") + 1:] != path:
        raise ValueError("source snapshot file is absent or nonordinary: " + path)
    return git("show", f"{commit}:{path}")


def verify_descriptor(raw: bytes, item: dict) -> None:
    if len(raw) != item.get("bytes") or sha256(raw) != item.get("sha256"):
        raise ValueError("whole-file source descriptor mismatch: " + str(item.get("path")))
    if item.get("uncompressed_sha256") is not None:
        unpacked = gzip.decompress(raw)
        if len(unpacked) != item["uncompressed_bytes"] or sha256(unpacked) != item["uncompressed_sha256"]:
            raise ValueError("compressed/uncompressed source hashes disagree: " + item["path"])


def source_snapshot_inventory() -> dict:
    prefix = ORIGINAL_PACKET + "/"
    rows = git("ls-tree", "-r", "-z", "--full-tree", SOURCE_SNAPSHOT, "--", ORIGINAL_PACKET).decode().split("\0")
    files = []
    for row in rows:
        if not row:
            continue
        meta, path = row.split("\t", 1)
        mode, kind, oid = meta.split()
        if mode not in ("100644", "100755") or kind != "blob" or not path.startswith(prefix):
            raise ValueError("source snapshot contains a nonordinary entry")
        raw = git("cat-file", "blob", oid)
        item = descriptor(path, raw)
        if path.endswith(".gz"):
            unpacked = gzip.decompress(raw)
            item.update(uncompressed_bytes=len(unpacked), uncompressed_sha256=sha256(unpacked))
        files.append(item)
    if not files:
        raise ValueError("pinned source snapshot is empty")
    return {"source_commit": SOURCE_SNAPSHOT, "issue": 616,
            "path": ORIGINAL_PACKET, "files": sorted(files, key=lambda x: x["path"])}


def verify_source_snapshot(manifest: dict) -> dict:
    inventory = source_snapshot_inventory()
    source_files = {x["path"]: x for x in inventory["files"]}
    old_quality = json.loads(read_at(SOURCE_SNAPSHOT, SOURCE_QUALITY_PATH))
    if old_quality["baseline"]["commit"] != PROJECT_BASELINE:
        raise ValueError("issue #616 source packet names an unexpected geography baseline")
    for source in old_quality["sources"]:
        for item in source.get("files", []):
            actual = source_files.get(item["path"])
            if not actual:
                raise ValueError("original source receipt differs from source snapshot: " + item["path"])
            raw = read_at(SOURCE_SNAPSHOT, item["path"])
            verify_descriptor(raw, item)
            if raw != (ROOT / item["path"]).read_bytes():
                raise ValueError("working source bytes differ from pinned source snapshot: " + item["path"])
    # Verify every original result, not just the files the generator consumes.
    for item in old_quality["outputs"]:
        actual = source_files.get(item["path"])
        if not actual or actual["bytes"] != item["bytes"] or actual["sha256"] != item["sha256"]:
            raise ValueError("original output descriptor differs from source snapshot: " + item["path"])
    old_outputs = {}
    for name in GENERATED:
        path = ORIGINAL_PACKET + "/" + name
        raw = read_at(SOURCE_SNAPSHOT, path)
        old_outputs[name] = {"bytes": len(raw), "sha256": sha256(raw),
                             "value": json.loads(raw)}
    return {"inventory": inventory, "old_quality": old_quality,
            "old_outputs": old_outputs, "source_files": source_files}


def verify_project_baseline(manifest: dict) -> tuple[Baseline, dict, dict]:
    base = manifest["baseline"]
    if base["commit"] != PROJECT_BASELINE:
        raise ValueError("manifest no longer names the declared #616 project baseline")
    baseline = Baseline(str(ROOT), PROJECT_BASELINE, base["files"])
    pins = base.get("pins", {})
    for key, value in pins.items():
        item = next((x for x in base["files"] if x["path"] == base["pin_files"][key]), None)
        if not item or item["sha256"] != value:
            raise ValueError("baseline named pin and file descriptor disagree: " + key)
    index = json.loads(baseline.read(base["pin_files"]["world_index"]))
    part_paths = {"data/" + x for x in index["parts"]}
    if not part_paths.issubset({x["path"] for x in base["files"]}):
        raise ValueError("every actual indexed geography part must be pinned")
    features, containing = baseline.subjects(IDS, base["pin_files"]["world_index"])
    if sorted(features) != sorted(IDS):
        raise ValueError("exact eight issue subjects are not present")
    expected_part = base["subject_files"]
    for identity in IDS:
        if containing[identity]["path"] != expected_part[identity]:
            raise ValueError("actual containing geography part differs for " + identity)
    hierarchy = {x["id"]: x for x in json.loads(baseline.read(base["pin_files"]["hierarchy"]))}
    chains = {}
    wanted_levels = ["province", "area", "region", "subcontinent", "continent"]
    for identity in IDS:
        cursor = features[identity]["properties"]["parent_id"]
        chain, seen = [], set()
        while cursor:
            if cursor in seen or cursor not in hierarchy:
                raise ValueError("cycle or missing ancestor for " + identity)
            seen.add(cursor)
            node = hierarchy[cursor]
            chain.append({"id": node["id"], "name": node["name"], "level": node["level"]})
            cursor = node.get("parent_id")
        if [x["level"] for x in chain] != wanted_levels:
            raise ValueError("incomplete parent chain for " + identity)
        chains[identity] = chain
    gate = json.loads(baseline.read(base["pin_files"]["macro_gate"]))
    release_raw = baseline.read(base["pin_files"]["macro_release"])
    release = json.loads(gzip.decompress(release_raw))
    handoffs = json.loads(gzip.decompress(baseline.read(base["pin_files"]["regional_handoffs"])))
    published = gate["macro_boundaries"]["approved_release"]
    if published["id"] != release["release"]["id"]:
        raise ValueError("pinned macro gate and release ID disagree")
    if published["hierarchy_sha256"] != base["pins"]["hierarchy"]:
        raise ValueError("pinned hierarchy differs from published release")
    if handoffs["release"]["id"] != published["id"]:
        raise ValueError("pinned regional scope handoff is not for the approved release")
    inventory = json.loads(gzip.decompress(baseline.read(base["pin_files"]["current_membership"])))
    membership = {x["id"]: set(x.get("member_location_ids", [])) for x in inventory}
    for identity in IDS:
        if not any(identity in members for members in membership.values()):
            raise ValueError("subject absent from pinned administrative membership inventory: " + identity)
    return baseline, {"features": features, "chains": chains, "containing": containing}, {
        "index_parts": len(index["parts"]), "subject_count": len(features),
        "approved_release_id": published["id"], "hierarchy_sha256": base["pins"]["hierarchy"],
        "handoff_release_id": handoffs["release"]["id"],
        "subject_containing_paths": {k: v["path"] for k, v in sorted(containing.items())}}


def run_original_generator(baseline: Baseline, source: dict) -> dict[str, bytes]:
    """Run a temp copy of the #648 generator with output redirection only."""
    with tempfile.TemporaryDirectory(prefix="worldatlas-663-run-") as temp_name:
        temp = pathlib.Path(temp_name)
        # Materialize only hash-verified baseline inputs in the private workspace.
        for item in baseline.pins.values():
            target = temp / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(baseline.read(item["path"]))
        # Restore the complete original #616 packet from its immutable merge commit.
        for item in source["inventory"]["files"]:
            target = temp / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = read_at(SOURCE_SNAPSHOT, item["path"])
            if len(raw) != item["bytes"] or sha256(raw) != item["sha256"]:
                raise ValueError("source snapshot changed while staging: " + item["path"])
            target.write_bytes(raw)
        script = temp / ORIGINAL_PACKET / "build_audit.py"
        text = script.read_text()
        old_import = "import csv, hashlib, io, json, pathlib, sys, zipfile, unicodedata"
        old_packet = "PACKET = pathlib.Path(__file__).resolve().parent"
        old_dump = "(PACKET/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+'\\n')"
        if old_import not in text or old_packet not in text or old_dump not in text:
            raise ValueError("pinned #616 generator has unexpected output layout")
        text = text.replace(old_import, "import csv, hashlib, io, json, pathlib, sys, zipfile, unicodedata, os", 1)
        text = text.replace(old_packet, old_packet + "\nOUTPUT_PACKET = pathlib.Path(os.environ['WORLDATLAS_REPRO_OUTPUT'])", 1)
        text = text.replace(old_dump, "(OUTPUT_PACKET/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+'\\n')", 1)
        script.write_text(text)
        output = temp / "private-generated-output"
        output.mkdir()
        env = os.environ.copy()
        env["WORLDATLAS_REPRO_OUTPUT"] = str(output)
        subprocess.run([sys.executable, str(script)], cwd=temp, env=env,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        generated = {}
        for name in GENERATED:
            path = output / name
            raw = path.read_bytes()
            # Keep semantic JSON while serializing new bytes under the shared
            # deterministic UTF-8/compact-output contract.
            generated[name] = canonical_json(json.loads(raw))
        extra = [x.name for x in output.iterdir() if x.name not in GENERATED]
        if extra or len(generated) != len(GENERATED):
            raise ValueError("generator emitted an unreviewed output set")
        return generated


def json_differences(left, right, path="") -> list[str]:
    if type(left) is not type(right):
        return [path or "/"]
    if isinstance(left, dict):
        out = []
        for key in sorted(set(left) | set(right)):
            child = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
            if key not in left or key not in right:
                out.append(child)
            else:
                out.extend(json_differences(left[key], right[key], child))
        return out
    if isinstance(left, list):
        if len(left) != len(right):
            return [path + "/length"]
        out = []
        for i, (a, b) in enumerate(zip(left, right)):
            out.extend(json_differences(a, b, path + "/" + str(i)))
        return out
    return [] if left == right else [path or "/"]


def create_payloads(manifest: dict, vintage: str) -> dict[str, bytes]:
    baseline, subjects, baseline_report = verify_project_baseline(manifest)
    source = verify_source_snapshot(manifest)
    check_negative_controls(manifest)
    first = run_original_generator(baseline, source)
    second = run_original_generator(baseline, source)
    if first != second:
        raise ValueError("two private baseline runs generated different bytes")
    target = PACKET / "vintages" / vintage
    issue_scope = json.loads(first["issue-scope.json"])
    profiles = json.loads(first["natural-earth-source-profiles.json"])
    if issue_scope["baseline_commit"] != PROJECT_BASELINE:
        raise ValueError("generated scope carries the wrong named baseline")
    if {x["id"] for x in issue_scope["locations"]} != set(IDS):
        raise ValueError("generated scope omitted or added an assigned subject")
    if {x["location_id"] for x in profiles["records"]} != set(IDS):
        raise ValueError("source profiles omitted or added an assigned subject")
    for row in issue_scope["locations"]:
        expected = subjects["chains"][row["id"]]
        if row["parent_chain"] != expected or row["containing_file"] != subjects["containing"][row["id"]]["path"]:
            raise ValueError("generated parent chain or actual containing file differs for " + row["id"])
    comparison = {}
    for name in GENERATED:
        old = source["old_outputs"][name]
        new_value = json.loads(first[name])
        paths = json_differences(old["value"], new_value)
        comparison[name] = {"original_source_snapshot": {
                                "path": ORIGINAL_PACKET + "/" + name,
                                "bytes": old["bytes"], "sha256": old["sha256"]},
                            "new_baseline_vintage": {
                                "path": str(target.relative_to(ROOT)) + "/" + name,
                                "bytes": len(first[name]), "sha256": sha256(first[name])},
                            "semantic_json_equal": not paths,
                            "changed_json_pointer_count": len(paths),
                            "changed_json_pointers_sample": paths[:100]}
    new_bytes = {"source-snapshot-pin.json": canonical_json(source["inventory"]),
                 **first,
                 "output-comparison.json": canonical_json({
                     "project_baseline_commit": PROJECT_BASELINE,
                     "original_source_snapshot_commit": SOURCE_SNAPSHOT,
                     "outputs": comparison,
                     "interpretation": "Byte and semantic output comparisons identify reproducibility differences only. They do not establish a new administrative or territorial conclusion."})}
    project_file = manifest["baseline"]["files"][0]
    controls = {
        "positive-control.json": {"method_id": "immutable-source-reproduction", "kind": "positive-control", "outcome": "passed",
            "subject_count": len(subjects["features"]), "expected_subject_ids": IDS,
            "all_subjects_found_once": True, "parent_chain_levels": ["province", "area", "region", "subcontinent", "continent"],
            **baseline_report},
        "negative-control.json": {"method_id": "immutable-source-reproduction", "kind": "negative-control", "outcome": "passed",
            "wrong_baseline_hash_rejected_before_destination_creation": True,
            "wrong_source_sidecar_hash_rejected_before_destination_creation": True,
            "existing_destination_rejected_without_modification": True,
            "positive_control_input_sha256": project_file["sha256"]},
        "reproducibility-control.json": {"method_id": "immutable-source-reproduction", "kind": "reproducibility", "outcome": "passed",
            "run_one_sha256": sha256(canonical_json({k: sha256(v) for k, v in sorted(first.items())})),
            "run_two_sha256": sha256(canonical_json({k: sha256(v) for k, v in sorted(second.items())})),
            "matching_file_count": len(first), "output_file_names": GENERATED},
    }
    new_bytes.update({k: canonical_json(v) for k, v in controls.items()})
    summary = {"method_version": VERSION, "issue": 663, "baseline_commit": PROJECT_BASELINE,
        "source_snapshot_commit": SOURCE_SNAPSHOT, "vintage": vintage,
        "subject_count": len(subjects["features"]), "output_count": len(first),
        "pinned_geography_part_count": baseline_report["index_parts"],
        "source_snapshot_file_count": len(source["inventory"]["files"]),
        "source_snapshot_sha256": sha256(canonical_json(source["inventory"])),
        "generated_outputs": {k: {"bytes": len(v), "sha256": sha256(v)} for k, v in sorted(first.items())},
        "semantic_comparison_file": "output-comparison.json",
        "negative_controls": "negative-control.json",
        "reproducibility_control": "reproducibility-control.json",
        "limitations": ["Natural Earth is cartographic reference, not legal boundary authority.",
            "Census geometries are statistical and do not establish jurisdiction or title.",
            "Restricted/unknown-term legal and Assembly pages remain restoration-only; they were not expanded or treated as legal proof.",
            "GSHHG is a physical shoreline diagnostic and cannot prove settlement or administrative completeness."],
        "project_geography": baseline_report}
    new_bytes["reproduction-run.json"] = canonical_json(summary)
    return new_bytes


def exclusive_destination(target: pathlib.Path) -> None:
    target.mkdir()


def check_negative_controls(manifest: dict) -> None:
    # Mutate only private in-memory descriptors. Baseline verification must fail
    # before any destination directory is made.
    bad = json.loads(json.dumps(manifest))
    bad["baseline"]["files"][0]["sha256"] = "0" * 64
    try:
        verify_project_baseline(bad)
    except (ValueError, subprocess.CalledProcessError):
        pass
    else:
        raise AssertionError("wrong baseline whole-file hash was accepted")
    # The committed DCRA/source inventory counterpart for Natural Earth is the
    # first retained sidecar; a changed digest must be rejected as well.
    ne = next(x for x in manifest["sources"] if x["id"] == "natural-earth-5-1-1")
    expected = json.loads(read_at(SOURCE_SNAPSHOT, SOURCE_QUALITY_PATH))
    source_item = ne["files"][0]
    original_item = expected["sources"][0]["files"][0]
    if source_item["path"] != original_item["path"] or source_item["sha256"] != original_item["sha256"]:
        raise AssertionError("Natural Earth source descriptor changed before the negative control")
    bad_descriptor = dict(source_item, sha256="0" * 64)
    good_bytes = read_at(SOURCE_SNAPSHOT, source_item["path"])
    try:
        verify_descriptor(good_bytes, bad_descriptor)
    except ValueError:
        pass
    else:
        raise AssertionError("wrong source-sidecar hash was accepted")
    with tempfile.TemporaryDirectory(prefix="worldatlas-663-negative-") as temp_name:
        target = pathlib.Path(temp_name) / "already-exists"
        target.mkdir()
        marker = target / "preserve-me.txt"
        marker.write_text("pre-existing bytes")
        before = marker.read_bytes()
        try:
            exclusive_destination(target)
        except FileExistsError:
            pass
        else:
            raise AssertionError("existing vintage destination was overwritten")
        if marker.read_bytes() != before or len(list(target.iterdir())) != 1:
            raise AssertionError("existing destination changed during overwrite negative control")


def write_exclusive(vintage: str, payloads: dict[str, bytes]) -> None:
    target = PACKET / "vintages" / vintage
    # Check before running or writing any result. mkdir is atomic/exclusive.
    target.parent.mkdir(parents=True, exist_ok=True)
    exclusive_destination(target)
    for name, raw in sorted(payloads.items()):
        if pathlib.PurePosixPath(name).name != name:
            raise ValueError("output filename must remain a direct vintage child")
        path = target / name
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())


def check_vintage(vintage: str) -> dict:
    target = PACKET / "vintages" / vintage
    if not target.is_dir() or target.is_symlink():
        raise FileNotFoundError("vintage is absent or not an ordinary directory")
    manifest = json.loads(MANIFEST.read_text())
    generated = create_payloads(manifest, vintage)
    expected = json.loads((target / "reproduction-run.json").read_bytes())
    for name, raw in generated.items():
        path = target / name
        if not path.is_file() or path.is_symlink() or path.read_bytes() != raw:
            raise ValueError("read-only two-run reproduction differs from stored vintage: " + name)
    return {"status": "passed", "vintage": vintage,
            "checked_output_count": len(generated),
            "reproduction_run_sha256": sha256((target / "reproduction-run.json").read_bytes()),
            "source_snapshot_commit": SOURCE_SNAPSHOT,
            "project_baseline_commit": PROJECT_BASELINE,
            "expected_vintage": expected["vintage"]}


def create_vintage(vintage: str) -> dict:
    target = PACKET / "vintages" / vintage
    if target.exists() or target.is_symlink():
        raise FileExistsError("refusing to overwrite an existing vintage")
    manifest = json.loads(MANIFEST.read_text())
    payloads = create_payloads(manifest, vintage)
    write_exclusive(vintage, payloads)
    return {"status": "created", "vintage": vintage,
            "file_count": len(payloads),
            "file_sha256": {k: sha256(v) for k, v in sorted(payloads.items())}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", metavar="VINTAGE", help="read-only two-run verification of a stored vintage")
    group.add_argument("--new-vintage", metavar="VINTAGE", help="exclusively create a new baseline/source vintage")
    args = parser.parse_args()
    if args.check:
        result = check_vintage(args.check)
    elif args.new_vintage:
        result = create_vintage(args.new_vintage)
    else:
        parser.error("default operation requires explicit --check VINTAGE or --new-vintage VINTAGE")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
