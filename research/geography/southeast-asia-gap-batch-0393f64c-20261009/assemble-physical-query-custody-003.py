"""Assemble retained #1641 physical/query custody; never reruns GIS comparisons."""
from __future__ import annotations

import ast
import gzip
import hashlib
import io
import json
import struct
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from shapely.geometry import mapping, Polygon


BASELINE = "f0a0c5f1c252e68b3b987cef8625ba9d185c215f"
PACKET = Path(__file__).resolve().parent
PRIORITY = PACKET / "vintages/priority-source-target-001/priority-source-target.json"
HANDOFF = PACKET / "inputs/native-geo3-318-engineering-handoff-20261009.json"
OUT_DIR = PACKET / "inputs/physical-custody-003"
MANIFEST = OUT_DIR / "manifest.json"
GIT_ROOT = PACKET.parents[2]
BATCH_INDEX = PACKET / "inputs/geo3-next-full-batch-318.json"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def ordered_ids_digest(values: list[str]) -> str:
    return digest(("\n".join(values) + "\n").encode())


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def git_blob(commit: str, path: str, descriptor: dict | None = None) -> bytes:
    if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts:
        raise ValueError(f"Unsafe pinned path: {path!r}")
    meta = subprocess.check_output(
        ["git", "-C", str(GIT_ROOT), "ls-tree", "-z", commit, "--", path]
    ).decode().rstrip("\0")
    if not meta or "\t" not in meta:
        raise ValueError(f"Missing committed input: {commit}:{path}")
    header, actual_path = meta.split("\t", 1)
    mode, kind, oid = header.split()
    if mode not in ("100644", "100755") or kind != "blob" or actual_path != path:
        raise ValueError(f"Expected one ordinary committed file: {commit}:{path}")
    size = int(subprocess.check_output(
        ["git", "-C", str(GIT_ROOT), "cat-file", "-s", oid]
    ))
    if descriptor is not None and size != descriptor["bytes"]:
        raise ValueError(f"Pinned file size differs: {path}")
    raw = subprocess.check_output(["git", "-C", str(GIT_ROOT), "cat-file", "blob", oid])
    if len(raw) != size:
        raise ValueError(f"Short Git blob read: {path}")
    if descriptor is not None and digest(raw) != descriptor["sha256"]:
        raise ValueError(f"Pinned file SHA differs: {path}")
    return raw


def decode_descriptor(commit: str, descriptor: dict, path: str | None = None) -> bytes:
    raw = git_blob(commit, path or descriptor["path"], descriptor)
    decoded = gzip.decompress(raw)
    if len(decoded) != descriptor["uncompressed_bytes"]:
        raise ValueError(f"Pinned decoded size differs: {descriptor['path']}")
    if digest(decoded) != descriptor["uncompressed_sha256"]:
        raise ValueError(f"Pinned decoded SHA differs: {descriptor['path']}")
    return decoded


def descriptor(commit: str, path: str) -> dict:
    raw = git_blob(commit, path)
    return {"commit": commit, "path": path, "bytes": len(raw),
            "hash_kind": "file-bytes", "sha256": digest(raw)}


def read_packet_json(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    return json.loads(raw), raw


def source_reconstructor(config: dict):
    physical_root = "coordination/engineering/global-physical-comparison-20261006/"
    report = json.loads(git_blob(BASELINE, physical_root + "results/report.json"))
    immutable_path = physical_root + "immutable.py"
    immutable_raw = git_blob(report["execution_commit"], immutable_path)
    immutable_sha = next(row["sha256"] for row in report["executed_code"]
                         if row["path"].endswith("/immutable.py"))
    if digest(immutable_raw) != immutable_sha:
        raise ValueError("Exact original canonical JSON helper differs")
    immutable_tree = ast.parse(immutable_raw.decode())
    canonical_node = next((node for node in immutable_tree.body
                           if isinstance(node, ast.FunctionDef)
                           and node.name == "canonical_json"), None)
    if canonical_node is None:
        raise ValueError("Pinned canonical JSON helper is absent")
    canonical_namespace = {"json": json}
    canonical_code = ast.get_source_segment(immutable_raw.decode(), canonical_node) + "\n"
    exec(compile(canonical_code, "<pinned-canonical-json>", "exec"), canonical_namespace)
    frozen_canonical_json = canonical_namespace["canonical_json"]
    source = git_blob(config["existing_reconstructor"]["commit"],
                      config["existing_reconstructor"]["path"])
    if digest(source) != config["existing_reconstructor"]["sha256"]:
        raise ValueError("Exact existing component reconstructor differs")
    text = source.decode()
    tree = ast.parse(text)
    functions = {node.name: node for node in tree.body
                 if isinstance(node, ast.FunctionDef)
                 and node.name in ("contact_key", "reconstruct")}
    if set(functions) != {"contact_key", "reconstruct"}:
        raise ValueError("Pinned pure reconstruction functions are incomplete")
    code = "\n\n".join(ast.get_source_segment(text, functions[name])
                          for name in ("contact_key", "reconstruct")) + "\n"
    namespace = {"canonical_json": frozen_canonical_json, "digest": digest}
    exec(compile(code, "<pinned-existing-reconstructor>", "exec"), namespace)
    return namespace["reconstruct"], frozen_canonical_json, {
        "canonical_json_helper": {"commit": report["execution_commit"],
                                  "path": immutable_path, "sha256": immutable_sha},
    }


def current_candidates(config: dict, priority_cases: dict) -> tuple[dict, dict]:
    reconstruct, frozen_canonical_json, canonical_provenance = source_reconstructor(config)
    originals = []
    input_descriptors = []
    for row in config["inputs"]:
        if row["kind"] != "components":
            continue
        raw = git_blob(row["commit"], row["path"], row)
        decoded = gzip.decompress(raw)
        if len(decoded) != row["uncompressed_bytes"] or digest(decoded) != row["uncompressed_sha256"]:
            raise ValueError(f"Original current-component input differs: {row['path']}")
        value = json.loads(decoded)
        originals.extend(value["features"] if isinstance(value, dict) else value)
        input_descriptors.append({k: row[k] for k in (
            "commit", "path", "bytes", "sha256", "uncompressed_bytes", "uncompressed_sha256")})
    delta_row = next(row for row in config["inputs"] if row["kind"] == "components_delta")
    delta_bytes = git_blob(delta_row["commit"], delta_row["path"], delta_row)
    delta_decoded = gzip.decompress(delta_bytes)
    if digest(delta_decoded) != delta_row["uncompressed_sha256"]:
        raise ValueError("Current-component delta differs")
    delta = json.loads(delta_decoded)
    current = reconstruct(originals, delta)
    if len(current) != config["current_components"]:
        raise ValueError("Complete current-component roster count differs")
    by_id = {row["id"]: row for row in current}
    if len(by_id) != len(current):
        raise ValueError("Duplicate current-component identity")
    selected = {}
    for identity, case in priority_cases.items():
        row = by_id[identity]
        catalog = case["catalog_record"]
        feature_sha = digest(frozen_canonical_json(row))
        geometry_sha = digest(frozen_canonical_json(row["geometry"]))
        if (feature_sha != catalog["current_feature_sha256"]
                or geometry_sha != catalog["current_geometry_sha256"]):
            raise ValueError(f"Reconstructed complete candidate differs: {identity}")
        target = case["target_record"]
        if (target["feature_sha256"] != feature_sha
                or target["geometry_sha256"] != geometry_sha
                or digest(frozen_canonical_json(target["feature"])) != feature_sha):
            raise ValueError(f"Prior administrative target pin differs: {identity}")
        selected[identity] = row
    provenance = {
        "candidate_delivery_commit": config["candidate_delivery"],
        "current_component_count": len(current),
        "selected_candidate_count": len(selected),
        "reconstruction_source": {
            "commit": config["existing_reconstructor"]["commit"],
            "path": config["existing_reconstructor"]["path"],
            "sha256": config["existing_reconstructor"]["sha256"],
        },
        **canonical_provenance,
        "component_inputs": input_descriptors,
        "component_delta": {k: delta_row[k] for k in (
            "commit", "path", "bytes", "sha256", "uncompressed_bytes", "uncompressed_sha256")},
    }
    return selected, provenance


def actionability_rows(pointer_rows: list[dict], selected_ids: set[str], manifest: dict):
    rows = {}
    descriptors = sorted(
        [row for row in manifest["outputs"]
         if "/results/components-" in row["path"] and row["path"].endswith(".bin.gz")],
        key=lambda row: row["path"])
    starts = {}
    decoded_cache = {}
    offset = ordinal = 0
    for row in descriptors:
        name = Path(row["path"]).name
        starts[name] = (offset, ordinal, row)
        decoded = decode_descriptor(BASELINE, row)
        decoded_cache[name] = decoded
        offset += row["uncompressed_bytes"]
        ordinal += decoded.count(b"\n")
    groups = defaultdict(list)
    for pointer in pointer_rows:
        if pointer["component_id"] in selected_ids:
            groups[pointer["component_record_pointer"]["starts_in_descriptor"]].append(pointer)
    for name, pointers in groups.items():
        descriptor_index = next(i for i, row in enumerate(descriptors)
                                if Path(row["path"]).name == name)
        start, ordinal_start, desc = starts[name]
        decoded = decoded_cache[name]
        for pointer in pointers:
            source_pointer = pointer["component_record_pointer"]
            if source_pointer["descriptor_decoded_sha256"] != desc["uncompressed_sha256"]:
                raise ValueError(f"Actionability descriptor pointer differs: {name}")
            local = source_pointer["decoded_stream_byte_offset"] - start
            if local < 0:
                raise ValueError(f"Actionability global offset precedes descriptor: {name}")
            if ordinal_start + decoded[:local].count(b"\n") != source_pointer["record_ordinal"]:
                raise ValueError(f"Actionability global record ordinal differs: {pointer['component_id']}")
            record = bytearray(decoded[local:])
            end = record.find(b"\n")
            next_index = descriptor_index + 1
            while end < 0 and next_index < len(descriptors):
                next_decoded = decoded_cache.get(Path(descriptors[next_index]["path"]).name)
                if next_decoded is None:
                    next_decoded = decode_descriptor(BASELINE, descriptors[next_index])
                    decoded_cache[Path(descriptors[next_index]["path"]).name] = next_decoded
                record.extend(next_decoded)
                end = record.find(b"\n")
                next_index += 1
            if end < 0:
                raise ValueError(f"Actionability row is incomplete at pointer: {pointer['component_id']}")
            raw_line = bytes(record[:end])
            row = json.loads(raw_line)
            if row.get("component") != pointer["component_id"]:
                raise ValueError(f"Actionability row ID differs at pointer: {pointer['component_id']}")
            rows[pointer["component_id"]] = {
                "pointer": source_pointer,
                "descriptor": {k: desc[k] for k in (
                    "path", "bytes", "sha256", "uncompressed_bytes", "uncompressed_sha256")},
                "row": row,
                "record_bytes": len(raw_line),
                "record_sha256": digest(raw_line),
            }
    if set(rows) != selected_ids:
        raise ValueError("Incomplete selected actionability row set")
    return rows


def physical_rows(pointer_rows: list[dict], selected_ids: set[str], action_rows: dict,
                  report: dict, transport: dict):
    original_products = {Path(row["path"]).name: row for row in report["products"]}
    delivered = {entry["original"]["path"]: entry["delivered"]
                 for entry in transport["entries"]}
    groups = defaultdict(list)
    for identity in selected_ids:
        row = action_rows[identity]["row"]
        groups[row["whole_physical_containing_file"]].append(identity)
    packed_rows = {}
    for path, identities in groups.items():
        name = Path(path).name
        if name not in original_products or name not in delivered:
            raise ValueError(f"Physical product lacks original/delivered descriptor: {path}")
        product = delivered[name]
        decoded = decode_descriptor(BASELINE, product, path)
        index = {}
        for line in decoded.splitlines():
            if not line:
                continue
            row = json.loads(line)
            if row.get("component_id") in identities:
                index[row["component_id"]] = (row, line)
        for identity in identities:
            if identity not in index:
                raise ValueError(f"Physical row missing from pinned product: {identity}")
            row, raw_line = index[identity]
            expected = action_rows[identity]["row"]["whole_physical_row_sha256"]
            if row.get("complete_current_record_metadata_alias") != "v1":
                raise ValueError(f"Unexpected physical transport product: {identity}")
            if digest(canonical_json(row)) != expected:
                raise ValueError(f"Packed physical-row hash differs: {identity}")
            if canonical_json(row).rstrip(b"\n") != raw_line:
                raise ValueError(f"Packed physical row is not canonical: {identity}")
            packed_rows[identity] = {
                "path": path,
                "original_product": original_products[name],
                "delivered_product": product,
                "whole_packed_scientific_row_sha256": expected,
                "record": row,
            }
    if set(packed_rows) != selected_ids:
        raise ValueError("Incomplete selected physical result row set")
    return packed_rows


def source_metadata_and_geometries(source_ids: set[int], config: dict, report: dict,
                                   transport: dict):
    if not source_ids or max(source_ids) > 10745:
        raise ValueError("Selected query sources escape the pinned sources-000 product")
    delivered = {entry["original"]["path"]: entry["delivered"]
                 for entry in transport["entries"]}
    source_path = "coordination/engineering/global-physical-comparison-20261006/results/sources-000.jsonl.gz"
    source_desc = delivered["sources-000.jsonl.gz"]
    source_decoded = decode_descriptor(BASELINE, source_desc, source_path)
    selected_meta = {}
    for line in source_decoded.splitlines():
        if line:
            row = json.loads(line)
            if row["id"] in source_ids:
                selected_meta[row["id"]] = row
    if set(selected_meta) != source_ids:
        raise ValueError("Selected physical query source metadata is incomplete")

    archive_cfg = config["source_archive"]
    parts = sorted((row for row in config["inputs"] if row["kind"] == "archive_part"),
                   key=lambda row: row["ordinal"])
    archive = bytearray()
    archive_pins = []
    for ordinal, row in enumerate(parts):
        if row["ordinal"] != ordinal or row["offset"] != len(archive):
            raise ValueError("Original GSHHG archive pieces are incomplete or reordered")
        raw = git_blob(row["commit"], row["path"], row)
        archive.extend(raw)
        archive_pins.append({k: row[k] for k in (
            "commit", "path", "bytes", "sha256", "ordinal", "offset")})
    if len(archive) != archive_cfg["original_bytes"] or digest(archive) != archive_cfg["original_sha256"]:
        raise ValueError("Complete original GSHHG archive differs")
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        if len(zipped.namelist()) != 18 or len(set(zipped.namelist())) != 18:
            raise ValueError("Original GSHHG ZIP member inventory differs")
        native = zipped.read(archive_cfg["member"])
    if len(native) != archive_cfg["member_bytes"] or digest(native) != archive_cfg["member_sha256"]:
        raise ValueError("Complete original GSHHG native member differs")
    del archive

    comparison_path = "coordination/engineering/global-physical-comparison-20261006/comparison.py"
    comparison_raw = git_blob(report["execution_commit"], comparison_path)
    expected_comparison = next(row["sha256"] for row in report["executed_code"]
                               if row["path"].endswith("/comparison.py"))
    if digest(comparison_raw) != expected_comparison:
        raise ValueError("Pinned original source decoder differs")
    tree = ast.parse(comparison_raw.decode())
    nodes = {node.name: node for node in tree.body
             if isinstance(node, ast.FunctionDef)
             and node.name in ("checked_validity", "decode_record")}
    if set(nodes) != {"checked_validity", "decode_record"}:
        raise ValueError("Pinned original source decoder functions incomplete")
    code = "\n\n".join(ast.get_source_segment(comparison_raw.decode(), nodes[name])
                          for name in ("checked_validity", "decode_record")) + "\n"
    env = {"np": np, "HEADER": struct.Struct(">3I4i2I2i"), "digest": digest,
           "Polygon": Polygon}
    exec(compile(code, "<pinned-original-source-decoder>", "exec"), env)

    result = {}
    offset = ordinal = 0
    remaining = set(source_ids)
    while offset < len(native) and remaining:
        header = native[offset:offset + 44]
        if len(header) != 44:
            raise ValueError("Truncated original GSHHG header")
        values = struct.Struct(">3I4i2I2i").unpack(header)
        length = 44 + values[1] * 8
        if offset + length > len(native):
            raise ValueError("Truncated original GSHHG coordinate record")
        identity = values[0]
        if identity in remaining:
            packed = selected_meta[identity]
            native_record = native[offset:offset + length]
            points = native[offset + 44:offset + length]
            meta, geometry = env["decode_record"](header, points, ordinal, offset, None)
            restored_meta = dict(packed)
            if restored_meta.pop("complete_original_native_byte_hash_alias", None) != "v1":
                raise ValueError(f"Source metadata alias differs: {identity}")
            restored_meta["record_sha256"] = digest(native_record)
            restored_meta["coordinate_bytes_sha256"] = digest(points)
            if restored_meta != meta:
                raise ValueError(f"Complete restored source metadata differs: {identity}")
            pointset = np.frombuffer(points, dtype=">i4").reshape(values[1], 2).astype(np.float64)
            pointset *= 1.0e-6
            seam = (values[2] >> 16) & 3
            shifted = ((np.frombuffer(points, dtype=">i4").reshape(values[1], 2)[:, 0] >
                        (270000000 if ordinal == 0 else 180000000)) & bool(seam)) | (values[3] > 180000000)
            pointset[shifted, 0] -= 360.0
            if identity == 4:
                pass
            elif identity != 0 and seam & 2:
                pointset[pointset[:, 0] < 0.0, 0] += 360.0
            packed_pointset = np.asarray(pointset, dtype=">f8").tobytes(order="C")
            if digest(packed_pointset) != meta["decoded_pointset_binary64_sha256"]:
                raise ValueError(f"Full original decoded source pointset differs: {identity}")
            geometry_value = mapping(geometry) if geometry is not None else None
            if geometry is not None:
                if geometry.geom_type != "Polygon":
                    raise ValueError(f"Unexpected original native source geometry type: {identity}")
                ring = np.asarray(geometry.exterior.coords, dtype=">f8")
                if digest(ring.tobytes(order="C")) != meta["decoded_pointset_binary64_sha256"]:
                    raise ValueError(f"Decoded polygon does not preserve full native pointset: {identity}")
            result[identity] = {
                "source_id": identity,
                "native_metadata": meta,
                "native_record_sha256": digest(native_record),
                "coordinate_bytes_sha256": digest(points),
                "decoded_pointset_binary64_sha256": meta["decoded_pointset_binary64_sha256"],
                "polygon_geometry": geometry_value,
                "complete_pointset_coordinates_when_no_polygon_object": (
                    pointset.tolist() if geometry is None else None),
                "geometry_status": ("original-supported-polygon-object"
                                    if geometry is not None else "complete-pointset-no-polygon-object"),
            }
            remaining.remove(identity)
        offset += length
        ordinal += 1
    if remaining:
        raise ValueError(f"Original native source IDs unavailable: {sorted(remaining)}")
    return result, {
        "complete_archive": {"bytes": archive_cfg["original_bytes"],
                             "sha256": archive_cfg["original_sha256"],
                             "input_commit": config["source_delivery"],
                             "parts": archive_pins},
        "complete_native_member": {"name": archive_cfg["member"],
                                   "bytes": archive_cfg["member_bytes"],
                                   "sha256": archive_cfg["member_sha256"]},
        "source_metadata_product": {"path": source_path,
                                     "bytes": source_desc["bytes"],
                                     "sha256": source_desc["sha256"],
                                     "uncompressed_bytes": source_desc["uncompressed_bytes"],
                                     "uncompressed_sha256": source_desc["uncompressed_sha256"]},
        "decoder": {"commit": report["execution_commit"], "path": comparison_path,
                    "sha256": expected_comparison},
    }


def provenance_records(pointer_rows: list[dict], selected_ids: set[str]):
    groups = defaultdict(list)
    for pointer in pointer_rows:
        if pointer["component_id"] in selected_ids:
            pin = pointer["containing_provenance_pin"]
            groups[(pin["commit"], pin["path"])].append(pointer)
    result = {}
    pins = []
    for (commit, path), pointers in groups.items():
        pin = pointers[0]["containing_provenance_pin"]
        raw = git_blob(commit, path, pin)
        decoded = gzip.decompress(raw)
        if (len(decoded) != pin["uncompressed_bytes"]
                or digest(decoded) != pin["uncompressed_sha256"]):
            raise ValueError(f"Original provenance shard differs: {path}")
        lines = decoded.splitlines()
        pins.append({k: pin[k] for k in ("commit", "path", "bytes", "sha256",
                                         "uncompressed_bytes", "uncompressed_sha256")})
        for pointer in pointers:
            index = int(pointer["containing_provenance_pin"]["pointer"].split("/")[-1])
            row = json.loads(lines[index])
            if row["component_id"] != pointer["component_id"]:
                raise ValueError(f"Original provenance ordinal differs: {pointer['component_id']}")
            for row_key, pointer_key in (("component_record", "component_record_pointer"),
                                         ("admin_comparison_record", "administrative_query_record_pointer")):
                if row[row_key] != pointer[pointer_key]:
                    raise ValueError(f"Original provenance nested pointer differs: {pointer['component_id']}")
            lp = pointer["physical_land_fitness_record_pointer"]
            if row["land_source_fitness_record"] != {
                    "product": lp["product"],
                    "json_array_record_ordinal": lp["json_array_record_ordinal"]}:
                raise ValueError(f"Original provenance land-fitness pointer differs: {pointer['component_id']}")
            result[pointer["component_id"]] = {
                "descriptor": {k: pin[k] for k in ("commit", "path", "bytes", "sha256",
                                                     "uncompressed_bytes", "uncompressed_sha256")},
                "pointer": pointer["containing_provenance_pin"]["pointer"],
                "record_ordinal_zero_based": index,
                "record": row,
            }
    if set(result) != selected_ids:
        raise ValueError("Original provenance record set incomplete")
    return result, pins


def admin_query_rows(pointer_rows: list[dict], selected_ids: set[str], manifest: dict):
    descriptors = sorted(
        [row for row in manifest["outputs"]
         if "/results/admin-bindings-" in row["path"] and row["path"].endswith(".bin.gz")],
        key=lambda row: row["path"])
    starts = {}
    decoded_cache = {}
    offset = ordinal = 0
    for row in descriptors:
        name = Path(row["path"]).name
        starts[name] = (offset, ordinal, row)
        decoded = decode_descriptor(BASELINE, row)
        decoded_cache[name] = decoded
        offset += row["uncompressed_bytes"]
        ordinal += decoded.count(b"\n")
    groups = defaultdict(list)
    for pointer in pointer_rows:
        if pointer["component_id"] in selected_ids:
            groups[pointer["administrative_query_record_pointer"]["starts_in_descriptor"]].append(pointer)
    result = {}
    for name, pointers in groups.items():
        descriptor_index = next(i for i, row in enumerate(descriptors)
                                if Path(row["path"]).name == name)
        start, ordinal_start, desc = starts[name]
        decoded = decoded_cache[name]
        for pointer in pointers:
            p = pointer["administrative_query_record_pointer"]
            if p["descriptor_decoded_sha256"] != desc["uncompressed_sha256"]:
                raise ValueError(f"Administrative query descriptor pointer differs: {name}")
            local = p["decoded_stream_byte_offset"] - start
            if local < 0 or ordinal_start + decoded[:local].count(b"\n") != p["record_ordinal"]:
                raise ValueError(f"Administrative query global ordinal differs: {pointer['component_id']}")
            record = bytearray(decoded[local:])
            end = record.find(b"\n")
            next_index = descriptor_index + 1
            while end < 0 and next_index < len(descriptors):
                next_name = Path(descriptors[next_index]["path"]).name
                next_decoded = decoded_cache.get(next_name)
                if next_decoded is None:
                    next_decoded = decode_descriptor(BASELINE, descriptors[next_index])
                    decoded_cache[next_name] = next_decoded
                record.extend(next_decoded)
                end = record.find(b"\n")
                next_index += 1
            if end < 0:
                raise ValueError(f"Administrative query row is out of range: {pointer['component_id']}")
            raw_line = bytes(record[:end])
            row = json.loads(raw_line)
            if row.get("component_id", row.get("component")) != pointer["component_id"]:
                raise ValueError(f"Administrative query row ID differs: {pointer['component_id']}")
            result[pointer["component_id"]] = {
                "pointer": p,
                "descriptor": {k: desc[k] for k in (
                    "path", "bytes", "sha256", "uncompressed_bytes", "uncompressed_sha256")},
                "record_bytes": len(raw_line),
                "record_sha256": digest(raw_line),
                "record": row,
            }
    if set(result) != selected_ids:
        raise ValueError("Administrative query row set incomplete")
    return result


def land_fitness_rows(pointer_rows: list[dict], selected_ids: set[str], manifest: dict):
    desc = next(row for row in manifest["outputs"]
                if row["path"].endswith("/results/land-source-fitness-000.bin.gz"))
    records = json.loads(decode_descriptor(BASELINE, desc))
    result = {}
    for pointer in pointer_rows:
        identity = pointer["component_id"]
        if identity not in selected_ids:
            continue
        p = pointer["physical_land_fitness_record_pointer"]
        if p["product"] != "land-source-fitness-000.bin.gz":
            raise ValueError(f"Unexpected land fitness product: {identity}")
        row = records[p["json_array_record_ordinal"]]
        if row.get("component_id", row.get("component")) != identity:
            raise ValueError(f"Land fitness row ID differs: {identity}")
        result[identity] = {
            "product": p["product"],
            "json_array_record_ordinal": p["json_array_record_ordinal"],
            "record": row,
        }
    if set(result) != selected_ids:
        raise ValueError("Land source-fitness row set incomplete")
    return result, {k: desc[k] for k in ("path", "bytes", "sha256",
                                         "uncompressed_bytes", "uncompressed_sha256")}


def full_admin_comparison_rows(priority_cases: dict, selected_ids: set[str]):
    result = {}
    for identity in selected_ids:
        case = priority_cases[identity]
        pointer = case["existing_comparison"]
        path = pointer["path"]
        desc = {k: pointer[k] for k in ("path", "bytes", "sha256", "uncompressed_sha256")}
        raw = git_blob(BASELINE, path, desc)
        decoded = gzip.decompress(raw)
        if digest(decoded) != pointer["uncompressed_sha256"]:
            raise ValueError(f"Existing full comparison decoded hash differs: {identity}")
        records = json.loads(decoded)
        index = pointer["record_ordinal"] - 1
        row = records[index]
        if row.get("component", row.get("component_id")) != identity:
            raise ValueError(f"Existing full comparison ordinal differs: {identity}")
        result[identity] = {
            "descriptor": desc,
            "record_ordinal_one_based": pointer["record_ordinal"],
            "record": row,
        }
    if set(result) != selected_ids:
        raise ValueError("Full existing administrative comparison row set incomplete")
    return result


def write_exact(path: Path, raw: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise ValueError(f"Refusing to replace differing existing custody output: {path}")
        return
    with path.open("xb") as stream:
        stream.write(raw)


def main():
    if subprocess.check_output(["git", "-C", str(GIT_ROOT), "rev-parse", "HEAD"]).decode().strip() != BASELINE:
        raise ValueError("Run assembly on the exact assigned baseline commit")
    handoff, handoff_raw = read_packet_json(HANDOFF)
    if digest(handoff_raw) != "b5949b9643083a0759933df32690cf2193ed5ea24756d36909c4576d2fc7422b":
        raise ValueError("Whole-batch engineering handoff pin differs")
    priority, priority_raw = read_packet_json(PRIORITY)
    if priority["batch_id"] != "gap-operational-batch:0393f64c9f8549bcfca1ace9":
        raise ValueError("Wrong operational batch")
    cases = {row["catalog_record"]["component_id"]: row for row in priority["cases"]}
    if len(cases) != 30:
        raise ValueError("Expected the same exact 30 priority subjects")
    pointers = handoff["original_physical_query_pointer_handoff"]
    pointer_ids = {row["component_id"] for row in pointers}
    selected_ids = set(cases)
    if len(pointers) != 30 or pointer_ids != selected_ids:
        raise ValueError("Priority IDs differ from original physical/query handoff")
    batch_index, batch_index_raw = read_packet_json(BATCH_INDEX)
    if (digest(batch_index_raw) != "9857d3c03f94799b4e7e22c9afce68259dc4e2747d2864d6eb580030222f3430"
            or batch_index["original_batch"]["component_count"] != 318
            or len(batch_index["original_batch"]["complete_component_ids"]) != 318
            or len(batch_index["original_batch"]["family_locators"]) != 122):
        raise ValueError("Original complete batch index or 318/122 roster pin differs")
    if ordered_ids_digest(batch_index["original_batch"]["complete_component_ids"]) != (
            "9bc07f2c8a8fb023105c07f367858e5ef87b2d663668d3192ddc53d5b19f0c61"):
        raise ValueError("Exact ordered 318-component issue roster differs")
    family_ids = sorted(row["family_id"] for row in batch_index["original_batch"]["family_locators"])
    if ordered_ids_digest(family_ids) != (
            "cec4d0b174dce6c31f53938dd9212069f496d2293f0f7767a5159ecd0cad5bd6"):
        raise ValueError("Exact sorted 122-family issue roster differs")
    if ordered_ids_digest(sorted(selected_ids)) != (
            "3b33e97e1e5f30fb51801d36088cfea63eade7c798f546c7ec03bba6d5595892"):
        raise ValueError("Exact 30-priority issue roster differs")

    source_manifest_path = "coordination/engineering/global-actionability-routing-20261007/evidence-quality.json"
    action_manifest = json.loads(git_blob(BASELINE, source_manifest_path))
    physical_root = "coordination/engineering/global-physical-comparison-20261006/"
    report_path = physical_root + "results/report.json"
    transport_path = physical_root + "results/transport-map.json"
    physical_report = json.loads(git_blob(BASELINE, report_path))
    transport = json.loads(git_blob(BASELINE, transport_path))
    input_config_path = physical_root + "input-config.json"
    config = json.loads(git_blob(BASELINE, input_config_path))

    candidates, candidate_provenance = current_candidates(config, cases)
    action_rows = actionability_rows(pointers, selected_ids, action_manifest)
    packed_physical = physical_rows(pointers, selected_ids, action_rows,
                                    physical_report, transport)
    source_ids = {relation["source_id"]
                  for row in packed_physical.values()
                  for relation in row["record"]["query_relations"]}
    source_features, source_provenance = source_metadata_and_geometries(
        source_ids, config, physical_report, transport)
    provenance, provenance_pins = provenance_records(pointers, selected_ids)
    admin_queries = admin_query_rows(pointers, selected_ids, action_manifest)
    land_fitness, land_descriptor = land_fitness_rows(pointers, selected_ids, action_manifest)
    full_admin = full_admin_comparison_rows(cases, selected_ids)

    assembled_cases = []
    for identity in sorted(selected_ids):
        case = cases[identity]
        relations = packed_physical[identity]["record"]["query_relations"]
        if any(relation["source_id"] not in source_features for relation in relations):
            raise ValueError(f"A physical query relation lacks its full source pointset: {identity}")
        # Administrative source/target roles are retained from phase 1. They are
        # linked by their original feature hashes and never treated as owner/cell bindings.
        admin_source = case["source_record"]
        admin_target = case["target_record"]
        assembled_cases.append({
            "component_id": identity,
            "family_id": case["family_id"],
            "administrative_source_target": {
                "phase1_packet": "vintages/priority-source-target-001/priority-source-target.json",
                "source_product": admin_source["product_id"],
                "source_subject_id": admin_source["subject_id"],
                "source_feature_sha256": admin_source["feature_sha256"],
                "source_geometry_sha256": admin_source["geometry_sha256"],
                "source_feature": admin_source["feature"],
                "source_record_ordinal": admin_source["record_ordinal"],
                "target_record_path": admin_target["path"],
                "target_record_feature_sha256": admin_target["feature_sha256"],
                "target_record_geometry_sha256": admin_target["geometry_sha256"],
                "target_record_feature": admin_target["feature"],
                "target_feature_id": admin_target["feature"]["id"],
                "target_feature_sha256": admin_target["feature_sha256"],
                "target_geometry_sha256": admin_target["geometry_sha256"],
                "existing_admin_comparison_record_sha256": case["existing_comparison"]["sha256"],
                "note": "These are the retained administrative source/target bindings. The physical query candidate and its GSHHG query sources are separately represented below; no owner, ordinal, parent, native-cell or uncovered-cell selection is asserted.",
            },
            "complete_current_component_candidate": {
                "feature_sha256": digest(canonical_json(candidates[identity])),
                "geometry_sha256": digest(canonical_json(candidates[identity]["geometry"])),
                "feature": candidates[identity],
            },
            "original_provenance": provenance[identity],
            "actionability_component_record": action_rows[identity],
            "physical_comparison_packed_row": packed_physical[identity],
            "physical_land_source_fitness": land_fitness[identity],
            "administrative_query_record": admin_queries[identity],
            "existing_full_admin_comparison": full_admin[identity],
            "physical_query_source_ids": sorted({row["source_id"] for row in relations}),
            "physical_query_relations": relations,
        })

    payload = {
        "version": 1,
        "kind": "retained-original-physical-query-custody",
        "batch_id": priority["batch_id"],
        "issue": 1641,
        "batch_roster": {
            "component_count": 318,
            "family_count": 122,
            "component_ids": batch_index["original_batch"]["complete_component_ids"],
            "family_locators": batch_index["original_batch"]["family_locators"],
            "batch_index_sha256": digest(batch_index_raw),
            "priority_component_count": 30,
            "priority_component_ids_sha256": digest(canonical_json(sorted(selected_ids))),
        },
        "source_identity": {
            "handoff_file": {"path": HANDOFF.relative_to(GIT_ROOT).as_posix(),
                             "bytes": len(handoff_raw), "sha256": digest(handoff_raw)},
            "priority_file": {"path": PRIORITY.relative_to(GIT_ROOT).as_posix(),
                              "bytes": len(priority_raw), "sha256": digest(priority_raw)},
            "original_batch_index": {"path": BATCH_INDEX.relative_to(GIT_ROOT).as_posix(),
                                      "bytes": len(batch_index_raw), "sha256": digest(batch_index_raw)},
            "baseline_commit": BASELINE,
            "actionability_manifest": descriptor(BASELINE, source_manifest_path),
            "physical_report": descriptor(BASELINE, report_path),
            "physical_transport_map": descriptor(BASELINE, transport_path),
            "physical_input_config": descriptor(BASELINE, input_config_path),
            "candidate_reconstruction": candidate_provenance,
            "original_physical_sources": source_provenance,
            "original_provenance_shards": provenance_pins,
            "land_source_fitness_descriptor": land_descriptor,
        },
        "physical_query_source_pointsets": [source_features[identity]
                                           for identity in sorted(source_features)],
        "cases": assembled_cases,
        "dispositions": {
            "all_30_component_decisions": "unresolved; no repair, physical class, cause, authority, water or ice conclusion is made here",
            "administrative_target": "retained separately from the physical comparison candidate; no selected owner/ordinal/parent/native-cell/uncovered-cell binding",
            "other_288_components": "retain their existing phase-1 exact-ID states, reasons and limitations",
            "scope": "reuse only; no source overlay, GIS comparison, or physical operator rerun",
        },
        "limitations": [
            "GSHHG is a 2017 distributed release with older heterogeneous WVS/WDBII observation dates; source fitness and contemporary physical truth are unresolved.",
            "Narrow registration-sensitive shoreline/channel truth, unrecorded river widths and seasonal wetness are not resolved by these retained rows.",
            "The query relations and pointsets are source-relative diagnostics; they do not establish land/water, repair cause, political ownership or authority.",
            "Complete current component candidates are not selected current-owner features and do not bind native cells or uncovered cells.",
        ],
    }
    # Keep every decoded evidence file within the trusted 32 MiB ordinary-file
    # budget. The original monolith exceeded that decoded limit despite being
    # only 8.7 MiB compressed, so retain independently hashed gzip JSON records.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload_descriptors = []
    records = [("index.json.gz", {k: v for k, v in payload.items()
                                  if k not in ("cases", "physical_query_source_pointsets")})]
    records.extend((f"cases/{row['component_id'].replace(':', '_')}.json.gz",
                    {"version": 1, "kind": "retained-original-physical-query-case",
                     "batch_id": payload["batch_id"], "case": row})
                   for row in assembled_cases)
    records.extend((f"sources/{str(row['source_id']).replace(':', '_')}.json.gz",
                    {"version": 1, "kind": "retained-original-physical-query-source-pointset",
                     "batch_id": payload["batch_id"], "source": row})
                   for row in payload["physical_query_source_pointsets"])
    for relative, value in records:
        raw_record = canonical_json(value)
        compressed = io.BytesIO()
        with gzip.GzipFile(fileobj=compressed, mode="wb", filename="", mtime=0, compresslevel=9) as stream:
            stream.write(raw_record)
        encoded = compressed.getvalue()
        path = OUT_DIR / relative
        write_exact(path, encoded)
        payload_descriptors.append({
            "path": str(path.relative_to(GIT_ROOT)),
            "bytes": len(encoded), "hash_kind": "file-bytes",
            "sha256": digest(encoded), "uncompressed_bytes": len(raw_record),
            "uncompressed_sha256": digest(raw_record),
        })
    manifest = {
        "version": 1,
        "batch_id": priority["batch_id"],
        "issue": 1641,
        "status": "assembled-from-retained-inputs-no-operator-rerun",
        "payloads": payload_descriptors,
        "counts": {"priority_cases": len(assembled_cases),
                   "complete_current_component_candidates": len(candidates),
                   "physical_comparison_rows": len(packed_physical),
                   "physical_query_relations": sum(len(row["physical_query_relations"])
                                                    for row in assembled_cases),
                   "complete_original_query_source_pointsets": len(source_features),
                   "administrative_query_rows": len(admin_queries),
                   "land_source_fitness_rows": len(land_fitness),
                   "full_existing_admin_comparison_rows": len(full_admin)},
        "validation": [
            {"kind": "exact-roster-join", "outcome": "passed", "count": 30},
            {"kind": "current-component-complete-record-and-geometry-hashes", "outcome": "passed", "count": 30},
            {"kind": "original-physical-packed-row-pointer-and-hash", "outcome": "passed", "count": 30},
            {"kind": "original-query-pointset-hash-and-source-record-binding", "outcome": "passed", "count": len(source_features)},
            {"kind": "original-provenance-record-and-nested-pointers", "outcome": "passed", "count": len(provenance)},
            {"kind": "admin-query-land-fitness-and-existing-comparison-row-pointers", "outcome": "passed", "count": 30},
        ],
        "limits": payload["limitations"],
    }
    manifest_raw = canonical_json(manifest)
    write_exact(MANIFEST, manifest_raw)
    print(json.dumps({"result": "PASS", "manifest": str(MANIFEST),
                      "manifest_sha256": digest(manifest_raw),
                      "payload_count": len(payload_descriptors),
                      "counts": manifest["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
