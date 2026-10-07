#!/usr/bin/env python3
"""Freeze the complete source reader closure and run real-entry positive/negative controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import platform
import zlib

import shapely
sys.path.insert(0, str(Path(__file__).parent))
from measure import (BASE, EXPECTED_COMPONENT, EXPECTED_CONTACT, EXPECTED_SOURCE_ID, META, PINS, RAW_BYTES, RAW_SHA,
                     SOURCE_BYTES, SOURCE_SHA, canonical_sha, sha, bounded_candidate, runtime_receipt)

PACKET = Path(__file__).parent
CODE_NAMES = ["capture-fragments.py", "measure.py", "controls.py", "runner.py"]


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def make_freeze():
    inputs = PACKET / "inputs"
    index_path = inputs / "fragment-index.json"
    index_bytes = bounded_candidate(inputs, "fragment-index.json")
    index = json.loads(index_bytes)
    candidate = {"inputs/fragment-index.json": {"bytes": len(index_bytes), "sha256": sha(index_bytes)}}
    for stream in index["streams"]:
        for part in stream["parts"]:
            path = inputs / part["path"]
            raw = bounded_candidate(inputs, part["path"])
            descriptor = {"bytes": len(raw), "sha256": sha(raw)}
            if descriptor != {"bytes": part["bytes"], "sha256": part["sha256"]}:
                raise ValueError("Fragment bytes changed before freeze")
            candidate["inputs/" + part["path"]] = descriptor
    baseline = {key: {"path": path, "sha256": digest, "bytes": size} for key, (path, digest, size) in PINS.items()}
    code = {name: sha((PACKET / name).read_bytes()) for name in CODE_NAMES}
    runtime = runtime_receipt()
    value = {
        "version": 1, "issue": 1392, "baseline_commit": BASE,
        "execution_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PACKET.parents[2], text=True).strip(),
        "subject_ids": [EXPECTED_CONTACT], "component_ids": [EXPECTED_COMPONENT],
        "original_source_identities": {"encoded_bytes": SOURCE_BYTES, "encoded_sha256": SOURCE_SHA,
                                        "decoded_bytes": RAW_BYTES, "decoded_sha256": RAW_SHA},
        "family_row_locator": {"decoded_shard_bytes": 8_388_608, "decoded_shard_sha256": "a1663477a0e01de8bb56736262b57e95c3c49647d54db95c4d2fd6d86600c328",
                               "offset": 6_232_978, "row_bytes": 5_040, "row_sha256": "b2ac5aaf19131ff0cf778c56f56fb0a8eae60a6d1b4198bfeb5b80be897e2fbd",
                               "family_id": "gap-source-batch:f41df3bc72099aca02d08c88",
                               "component_ids": [EXPECTED_COMPONENT], "contact_ids": [EXPECTED_CONTACT]},
        "baseline_inputs": baseline, "candidate_inputs": candidate, "code": code, "runtime": runtime,
        "method": "whole-collection encoded+decoded byte admission, streamed JSON ID accounting and literal-coordinate geometry diagnostic",
        "run_policy": "two complete CLI invocations with the identical closure freeze; no decoded whole file is written"
    }
    target = PACKET / "closure-freeze.json"
    if target.exists(): raise FileExistsError("Refusing to replace a frozen input closure")
    target.write_bytes(canonical(value))
    return value, sha(canonical(value))


def prepare_case(temp_root, base_packet):
    (temp_root / "inputs").mkdir(parents=True)
    (temp_root / "verification").mkdir()
    shutil.copy2(base_packet / "closure-freeze.json", temp_root / "closure-freeze.json")
    index_path = base_packet / "inputs" / "fragment-index.json"
    shutil.copyfile(index_path, temp_root / "inputs" / "fragment-index.json")
    index = json.loads(index_path.read_text())
    for stream in index["streams"]:
        for part in stream["parts"]:
            source = base_packet / "inputs" / part["path"]
            destination = temp_root / "inputs" / part["path"]
            os.link(source, destination)
    return index


def run_actual_entry(temp_root, *, extra_args=()):
    cmd = [sys.executable, "-I", "-B", str(PACKET / "measure.py"), "--packet", str(temp_root),
           "--result", str(temp_root / "result.json"), *extra_args]
    return subprocess.run(cmd, cwd=PACKET.parents[2], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def refresh_freeze_for_coherent_candidate_rebind(temp_root, index):
    index_path = temp_root / "inputs" / "fragment-index.json"
    index_bytes = canonical(index)
    index_path.write_bytes(index_bytes)
    freeze_path = temp_root / "closure-freeze.json"
    freeze = json.loads(freeze_path.read_text())
    candidate = {"inputs/fragment-index.json": {"bytes": len(index_bytes), "sha256": sha(index_bytes)}}
    for stream in index["streams"]:
        for part in stream["parts"]:
            raw = bounded_candidate(temp_root / "inputs", part["path"])
            candidate["inputs/" + part["path"]] = {"bytes": len(raw), "sha256": sha(raw)}
    freeze["candidate_inputs"] = candidate
    freeze_path.write_bytes(canonical(freeze))


def recompute_stream_hash(temp_root, stream):
    digest = hashlib.sha256()
    for part in stream["parts"]:
        p = temp_root / "inputs" / part["path"]
        raw = p.read_bytes()
        part["sha256"] = sha(raw)
        part["bytes"] = len(raw)
        digest.update(raw)
    stream["bytes"] = sum(x["bytes"] for x in stream["parts"])
    stream["part_bytes"] = stream["bytes"]
    stream["sha256"] = digest.hexdigest()


def negative_case(case_id, mutate, base_packet):
    with tempfile.TemporaryDirectory(prefix="kakinada-control-", dir=PACKET) as name:
        temp_root = Path(name)
        index = prepare_case(temp_root, base_packet)
        mutation_note = mutate(temp_root, index)
        result = run_actual_entry(temp_root)
        if result.returncode == 0:
            raise ValueError("Actual producer entry accepted negative control: " + case_id)
        return {"id": case_id, "entry": "measure.py CLI", "outcome": "rejected", "returncode": result.returncode,
                "rejection": (result.stderr.strip().splitlines()[-1] if result.stderr.strip() else result.stdout.strip())[:300],
                "mutation": mutation_note}


def symlink_packet_case(base_packet):
    with tempfile.TemporaryDirectory(prefix="kakinada-packet-link-", dir=PACKET) as name:
        actual = Path(name) / "actual"
        actual.mkdir()
        prepare_case(actual, base_packet)
        alias = Path(name) / "alias"
        alias.symlink_to(actual, target_is_directory=True)
        result = subprocess.run([sys.executable, "-I", "-B", str(PACKET / "measure.py"),
                                 "--packet", str(alias), "--result", str(alias / "result.json")],
                                cwd=PACKET.parents[2], text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False)
        if result.returncode == 0: raise ValueError("Actual producer accepted a symlink packet root")
        return {"id": "symlink-packet-root", "entry": "measure.py CLI", "outcome": "rejected",
                "returncode": result.returncode,
                "rejection": result.stderr.strip().splitlines()[-1][:300],
                "mutation": "Presented the valid packet through a symlink packet root."}


def drop_encoded(temp, index):
    (temp / "inputs" / index["streams"][0]["parts"][0]["path"]).unlink()
    return "Removed encoded ordinal 0 while retaining its complete index entry."


def reorder_encoded(temp, index):
    index["streams"][0]["parts"].reverse(); (temp / "inputs" / "fragment-index.json").write_bytes(canonical(index))
    return "Reversed encoded fragment ordinal order without changing declarations."


def duplicate_encoded(temp, index):
    index["streams"][0]["parts"][1] = dict(index["streams"][0]["parts"][0]); (temp / "inputs" / "fragment-index.json").write_bytes(canonical(index))
    return "Replaced encoded ordinal 1 with a duplicate of ordinal 0."


def corrupt_encoded(temp, index):
    p = temp / "inputs" / index["streams"][0]["parts"][0]["path"]
    raw = bytearray(p.read_bytes()); raw[len(raw)//2] ^= 1; p.unlink(); p.write_bytes(raw)
    return "Flipped one literal byte in encoded ordinal 0 without updating its declared hash."


def drop_decoded(temp, index):
    (temp / "inputs" / index["streams"][1]["parts"][1]["path"]).unlink()
    return "Removed decoded ordinal 1 while retaining its complete index entry."


def reorder_decoded(temp, index):
    index["streams"][1]["parts"].reverse(); (temp / "inputs" / "fragment-index.json").write_bytes(canonical(index))
    return "Reversed decoded fragment ordinal order without changing declarations."


def duplicate_decoded(temp, index):
    index["streams"][1]["parts"][2] = dict(index["streams"][1]["parts"][1]); (temp / "inputs" / "fragment-index.json").write_bytes(canonical(index))
    return "Replaced decoded ordinal 2 with a duplicate of ordinal 1."


def corrupt_decoded(temp, index):
    p = temp / "inputs" / index["streams"][1]["parts"][0]["path"]
    raw = bytearray(p.read_bytes()); raw[len(raw)//2] ^= 1; p.unlink(); p.write_bytes(raw)
    return "Flipped one literal byte in decoded ordinal 0 without updating its declared hash."


def symlink_index(temp, index):
    target = temp / "inputs" / "fragment-index.json"
    saved = temp / "inputs" / "fragment-index.saved"
    target.rename(saved); target.symlink_to(saved.name)
    return "Replaced the packet index with a symlink to its preserved regular-file body."


def symlink_part(temp, index):
    name = index["streams"][0]["parts"][0]["path"]
    target = temp / "inputs" / name
    saved = temp / "inputs" / (name + ".saved")
    target.rename(saved); target.symlink_to(saved.name)
    return "Replaced encoded fragment ordinal 0 with a symlink to its preserved ordinary body."


def symlink_input_root(temp, index):
    root = temp / "inputs"
    saved = temp / "inputs.saved"
    root.rename(saved); root.symlink_to(saved.name, target_is_directory=True)
    return "Replaced the candidate input directory with a symlink to its preserved ordinary directory."


def oversized_index(temp, index):
    target = temp / "inputs" / "fragment-index.json"
    with target.open("wb") as stream: stream.truncate(32 * 1024 * 1024 + 1)
    return "Replaced the index with a sparse regular file one byte above the pre-read cap."


def oversized_part(temp, index):
    target = temp / "inputs" / index["streams"][0]["parts"][0]["path"]
    target.unlink()
    with target.open("wb") as stream: stream.truncate(32 * 1024 * 1024 + 1)
    return "Replaced an encoded part with a sparse ordinary file one byte above the pre-read cap."


def rebind_foreign_source(temp, index):
    stream = index["streams"][1]
    p = temp / "inputs" / stream["parts"][0]["path"]
    raw = bytearray(p.read_bytes()); raw[0] ^= 1; p.unlink(); p.write_bytes(raw)
    recompute_stream_hash(temp, stream); refresh_freeze_for_coherent_candidate_rebind(temp, index)
    return "Rehashed every decoded part, whole decoded stream and candidate freeze after changing source bytes; fixed ancestor metadata identity remains original."


def rebind_foreign_feature(temp, index):
    stream = index["streams"][1]
    target = EXPECTED_SOURCE_ID.encode()
    for part in stream["parts"]:
        p = temp / "inputs" / part["path"]
        raw = bytearray(p.read_bytes())
        where = raw.find(target)
        if where >= 0:
            raw[where] = ord("8") if raw[where] != ord("8") else ord("9")
            p.unlink(); p.write_bytes(raw)
            recompute_stream_hash(temp, stream); refresh_freeze_for_coherent_candidate_rebind(temp, index)
            return "Changed the selected source feature's native shapeID and coherently recomputed every decoded part/stream/index/freeze hash."
    raise ValueError("Cannot locate selected source feature ID within decoded part bodies")


def rebind_foreign_component(temp, index):
    freeze_path = temp / "closure-freeze.json"
    freeze = json.loads(freeze_path.read_text())
    foreign_path, foreign_hash, foreign_bytes = PINS["original-physical-components"]
    freeze["baseline_inputs"]["original-component-payload"] = {"path": foreign_path, "sha256": foreign_hash, "bytes": foreign_bytes}
    freeze_path.write_bytes(canonical(freeze))
    return "Rebound the complete component payload descriptor to the alternate source-comparison file with matching new byte/hash fields."


def rebind_foreign_context(temp, index):
    freeze_path = temp / "closure-freeze.json"
    freeze = json.loads(freeze_path.read_text())
    foreign_path, foreign_hash, foreign_bytes = PINS["current-location-part-32"]
    freeze["baseline_inputs"]["current-hierarchy"] = {"path": foreign_path, "sha256": foreign_hash, "bytes": foreign_bytes}
    freeze_path.write_bytes(canonical(freeze))
    return "Rebound the current-hierarchy descriptor to the pinned current-location file with internally consistent replacement path/hash/length."


def mutate_family_locator(case_id):
    def mutate(temp, index):
        fp = temp / "closure-freeze.json"
        freeze = json.loads(fp.read_text())
        locator = freeze["family_row_locator"]
        if case_id == "wrong-family-row-offset": locator["offset"] += 1
        elif case_id == "wrong-family-row-identity": locator["row_sha256"] = "0" * 64
        elif case_id == "wrong-family-member-roster": locator["component_ids"] = []
        fp.write_bytes(canonical(freeze))
        return "Changed frozen routed-family locator " + case_id + "; actual CLI must reject before measurement."
    return mutate


def run_controls(base_packet=PACKET):
    checks = [
        negative_case("omit-encoded-part", drop_encoded, base_packet),
        negative_case("reorder-encoded-parts", reorder_encoded, base_packet),
        negative_case("duplicate-encoded-part", duplicate_encoded, base_packet),
        negative_case("corrupt-encoded-part", corrupt_encoded, base_packet),
        negative_case("omit-decoded-part", drop_decoded, base_packet),
        negative_case("reorder-decoded-parts", reorder_decoded, base_packet),
        negative_case("duplicate-decoded-part", duplicate_decoded, base_packet),
        negative_case("corrupt-decoded-part", corrupt_decoded, base_packet),
        negative_case("symlink-fragment-index", symlink_index, base_packet),
        negative_case("symlink-fragment-part", symlink_part, base_packet),
        negative_case("symlink-input-directory", symlink_input_root, base_packet),
        symlink_packet_case(base_packet),
        negative_case("oversized-fragment-index-before-read", oversized_index, base_packet),
        negative_case("oversized-fragment-part-before-read", oversized_part, base_packet),
        negative_case("coherent-foreign-source-rebind", rebind_foreign_source, base_packet),
        negative_case("coherent-foreign-feature-rebind", rebind_foreign_feature, base_packet),
        negative_case("coherent-foreign-component-rebind", rebind_foreign_component, base_packet),
        negative_case("coherent-foreign-context-rebind", rebind_foreign_context, base_packet),
        negative_case("wrong-family-row-offset", mutate_family_locator("wrong-family-row-offset"), base_packet),
        negative_case("wrong-family-row-identity", mutate_family_locator("wrong-family-row-identity"), base_packet),
        negative_case("wrong-family-member-roster", mutate_family_locator("wrong-family-member-roster"), base_packet),
    ]
    with tempfile.TemporaryDirectory(prefix="kakinada-fallback-", dir=PACKET) as name:
        result = run_actual_entry(Path(name), extra_args=("--source-file", "data/regional-review/regional-review-d0984f717127fb3e/sources/geoBoundaries-IND-ADM3-2018-retained.geojson.gz"))
        if result.returncode == 0:
            raise ValueError("Actual producer CLI accepted the removed whole-gzip getter argument")
        checks.append({"id": "old-whole-gzip-getter-fallback", "entry": "measure.py CLI", "outcome": "rejected",
                       "returncode": result.returncode, "rejection": result.stderr.strip().splitlines()[-1][:300],
                       "mutation": "Attempted the legacy whole-gzip source getter argument; CLI rejects undeclared source fallback."})
    if len(checks) != 22 or any(row["outcome"] != "rejected" for row in checks):
        raise ValueError("Not all source-boundary controls rejected at the production entry")
    method = geometry_controls()
    value = {"method_id": "bounded-complete-source-reader-and-ordinary-file-boundary",
             "kind": "negative-control", "outcome": "passed", "entry": "measure.py CLI",
             "cases": checks, "case_count": len(checks), "geometry_method_control": method}
    target = PACKET / "verification" / "source-reader-negative.json"
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(canonical(value))
    return value


def geometry_controls():
    result = subprocess.run([sys.executable, "-I", "-B", str(PACKET / "measure.py"),
                             "--geometry-method-controls"], cwd=str(PACKET.parents[2]),
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise ValueError("Actual measurement CLI failed directed geometry controls: " + result.stderr[-500:])
    payload = json.loads(result.stdout)
    method = payload.get("geometry_method_controls", {})
    if payload.get("ok") is not True or len(method.get("negative_rejections", {})) != 3:
        raise ValueError("Actual measurement CLI geometry method control receipt is incomplete")
    value = {"method_id": "directed-polygon-method-geometry", "kind": "positive-and-negative-control",
             "outcome": "passed", "entry": "measure.py CLI --geometry-method-controls", "receipt": method}
    target = PACKET / "verification" / "geometry-method-controls.json"
    target.write_bytes(canonical(value))
    return value


def positive_control(run_one):
    result = json.loads(Path(run_one).read_text())
    s = result["source_integrity"]
    if (s["encoded_bytes"], s["encoded_sha256"], s["decoded_bytes"], s["decoded_sha256"],
        s["feature_count"], s["unique_native_shape_id_count"], result["source_selection"]["feature_canonical_sha256"]) != (
        SOURCE_BYTES, SOURCE_SHA, RAW_BYTES, RAW_SHA, 6822, 6822,
        "8d4c511ac4c1a541544598d1dec855779711ed75e7263a93d410f0bd15b08726"):
        raise ValueError("Actual complete-reader entry positive result differs from the authenticated source closure")
    value = {"method_id": "bounded-complete-source-reader", "kind": "positive-control", "outcome": "passed",
             "entry": "measure.py CLI", "run_result_sha256": sha(Path(run_one).read_bytes()),
             "checked": ["all five literal parts", "whole encoded and decoded identities", "every decoded byte",
                         "all 6,822 unique shapeIDs", "selected member ID/name/canonical feature identity"]}
    target = PACKET / "verification" / "source-reader-positive.json"
    target.write_bytes(canonical(value))
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "controls", "positive", "geometry"])
    parser.add_argument("--run-one")
    args = parser.parse_args()
    if args.action == "freeze":
        _, digest = make_freeze(); print(json.dumps({"frozen": True, "sha256": digest, "code": json.loads((PACKET / "closure-freeze.json").read_text())["code"]}, sort_keys=True))
    elif args.action == "controls":
        print(json.dumps(run_controls(), sort_keys=True))
    elif args.action == "positive":
        if not args.run_one: raise ValueError("positive control requires --run-one")
        print(json.dumps(positive_control(args.run_one), sort_keys=True))
    else:
        print(json.dumps(geometry_controls(), sort_keys=True))
