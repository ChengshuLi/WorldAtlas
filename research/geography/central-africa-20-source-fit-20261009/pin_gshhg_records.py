#!/usr/bin/env python3
"""Pin existing GSHHG native records whose stored bounds touch the 20 IDs.

This only selects archived record byte ranges by their retained integer bounds.
It performs no geometry operations and makes no land/water inference.
"""
import gzip
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/central-africa-20-source-fit-20261009"
BASE = "coordination/engineering/gshhg-native-member-custody-20261007/"
COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
SOURCE_COMMIT = "f8f99612e4d83d561b370189a1969c3e4301a1e3"


def git_bytes(path):
    return subprocess.check_output(["git", "show", f"{COMMIT}:{BASE}{path}"], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounds(feature):
    xy = []
    def walk(c):
        if isinstance(c, (list, tuple)) and len(c) >= 2 and isinstance(c[0], (int, float)) and isinstance(c[1], (int, float)):
            xy.append((c[0], c[1]))
        elif isinstance(c, (list, tuple)):
            for v in c:
                walk(v)
    walk(feature["geometry"]["coordinates"])
    return (min(x for x, y in xy), min(y for x, y in xy), max(x for x, y in xy), max(y for x, y in xy))


def overlaps(a, b):
    # Inclusive integer-bounds comparison only; touching counts as selection.
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def main():
    components_path = PACKET / "inputs/components/selected-20-components.json.gz"
    with gzip.open(components_path, "rt", encoding="utf-8") as f:
        components = json.load(f)["features"]
    component_boxes = {f["id"]: bounds(f) for f in components}
    member_index_raw = git_bytes("results/member-index.json")
    member_index = json.loads(member_index_raw)
    assert member_index["member_name"] == "gshhs_f.b"
    assert member_index["member_bytes"] == 95809336
    assert member_index["member_sha256"] == "af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6"
    assert member_index["original_source_commit"] == SOURCE_COMMIT
    selected = []
    record_manifest = []
    for shard in member_index["records"]:
        raw = git_bytes("results/" + shard["path"])
        assert len(raw) == shard["bytes"] and sha(raw) == shard["sha256"]
        decoded = gzip.decompress(raw)
        assert len(decoded) == shard["uncompressed_bytes"] and sha(decoded) == shard["uncompressed_sha256"]
        for line in decoded.splitlines():
            rec = json.loads(line)
            rb = tuple(v / 1_000_000 for v in rec["native_bounds_microdegrees"])
            hits = [cid for cid, cb in component_boxes.items() if overlaps(rb, cb)]
            if hits:
                selected.append({"record": rec, "candidate_ids_by_bounds_only": sorted(hits)})
        record_manifest.append({"path": BASE + "results/" + shard["path"], "commit": COMMIT,
                                "bytes": len(raw), "sha256": sha(raw),
                                "uncompressed_bytes": len(decoded), "uncompressed_sha256": sha(decoded)})
    assert member_index["record_count"] == 188612

    # Recover exact full records from the three archived, contiguous gzip aliases.
    native_parts = []
    native_manifest = []
    for part in member_index["parts"]:
        raw = git_bytes("results/" + part["path"])
        assert len(raw) == part["bytes"] and sha(raw) == part["sha256"]
        decoded = gzip.decompress(raw)
        assert len(decoded) == part["uncompressed_bytes"] and sha(decoded) == part["uncompressed_sha256"]
        native_parts.append(decoded)
        native_manifest.append({"path": BASE + "results/" + part["path"], "commit": COMMIT,
                                "bytes": len(raw), "sha256": sha(raw),
                                "uncompressed_bytes": len(decoded), "uncompressed_sha256": sha(decoded)})
    native = b"".join(native_parts)
    assert len(native) == member_index["member_bytes"] and sha(native) == member_index["member_sha256"]

    output = PACKET / "inputs/gshhg-records"
    output.mkdir(parents=True, exist_ok=True)
    for item in selected:
        rec = item["record"]
        start, end = rec["offset"], rec["offset"] + rec["record_bytes"]
        record_bytes = native[start:end]
        assert len(record_bytes) == rec["record_bytes"] and sha(record_bytes) == rec["record_sha256"]
        filename = f"gshhs_f-record-{rec['id']}.bin"
        (output / filename).write_bytes(record_bytes)
        item["custody_path"] = str((output / filename).relative_to(PACKET))
        item["record_bytes_sha256"] = sha(record_bytes)
        item["record_bytes_length"] = len(record_bytes)
        # Do not emit the full source record metadata; keep required byte identity fields.

    result = {
        "schema": "central-africa-gshhg-bbox-byte-custody-v1",
        "selection_method": "exact retained integer native_bounds_microdegrees compared with candidate bounding boxes; inclusive bbox only",
        "no_geometry_operations": True,
        "no_land_or_water_inference": True,
        "candidate_geometry_source": {"path": str(components_path.relative_to(ROOT)),
                                       "bytes": components_path.stat().st_size,
                                       "sha256": sha(components_path.read_bytes()), "count": len(component_boxes)},
        "gshhg_native_member": {"custody_commit": COMMIT, "original_source_commit": SOURCE_COMMIT,
                                "member_name": member_index["member_name"], "bytes": member_index["member_bytes"],
                                "sha256": member_index["member_sha256"], "record_count": member_index["record_count"],
                                "record_index_path": BASE + "results/member-index.json",
                                "record_index_bytes": len(member_index_raw), "record_index_sha256": sha(member_index_raw),
                                "record_index_git_blob": subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{BASE}results/member-index.json"], cwd=ROOT, text=True).strip()},
        "record_shards": record_manifest,
        "native_record_byte_parts": native_manifest,
        "selected_record_count": len(selected),
        "selected_raw_record_bytes": sum(x["record_bytes_length"] for x in selected),
        "selected_records": [{"id": x["record"]["id"], "level": x["record"]["level"],
                              "source": x["record"]["source"], "offset": x["record"]["offset"],
                              "bytes": x["record_bytes_length"], "record_sha256": x["record_bytes_sha256"],
                              "native_bounds_microdegrees": x["record"]["native_bounds_microdegrees"],
                              "bbox_candidate_ids_only": x["candidate_ids_by_bounds_only"],
                              "metadata_geometry_validity": x["record"]["geometry_validity"],
                              "path": x["custody_path"]} for x in selected],
        "limits": ["bbox selection is not a geometry intersection or source-to-candidate correspondence",
                   "the archived native custody explicitly did not evaluate geometry validity",
                   "these bytes establish no current land/water/ice state and do not change any fit decision"],
    }
    raw = json.dumps(result, indent=2).encode() + b"\n"
    dest = PACKET / "gshhg-custody.json"
    dest.write_bytes(raw)
    print(json.dumps({"manifest": str(dest), "sha256": sha(raw), "selected_records": len(selected),
                      "raw_record_bytes": result["selected_raw_record_bytes"],
                      "records": result["selected_records"]}, indent=2))


if __name__ == "__main__":
    main()
