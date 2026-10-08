#!/usr/bin/env python3
"""Build a bounded source-only assessment from retained pinned records.

No GIS operation, candidate geometry edit, or live source request occurs here.
The builder authenticates the accepted funnel rows, their original routing
records, whole physical-comparison rows, retained GSHHG native-record metadata,
and the seven full 2018 Alaska county/equivalent source features.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
HEAD = "6c0ea95b7a8214ac1548161368bd952af136b5c2"
FUNNEL_REV = "c8df65e1d5c4d235c33e2f488c3e29d26223860f"
ROUTE_REV = "12e90af4ff876e619a8eb0e6c1445821573500e6"
FAMILY = "gap-source-batch:9a8d66e4d47f5883620328f9"
IDS = {
    "physical-component:073d9a81648d56c1b63a4e495fbd0140c17659bedb5c9b211739642b438ee488",
    "physical-component:4d36c81ff35079341e6ec0d5a207ba3844e26f5d55c30c7205924dfd33b8dc18",
    "physical-component:5874689a46f7945e9dcc67cc3b0321d4e534572e4b4bd8a85f4a07c5005d1922",
    "physical-component:66e4f6c15eb17f53815844efc04e7cae9faf9118de313541d3a4be2ff1fcf0a2",
    "physical-component:70174bffffdbb4a421344d6c10d80b760972f9c5452daf0d7c26408fdf18bb53",
    "physical-component:777e7bc99320bf155684f99b0903c336f9a07862de4a7fa0ac8cde990d7d6ee5",
    "physical-component:8435dc6d973751bab55c4eff12c872ba331c3e005254ceb21b76933a8cc6207a",
    "physical-component:8fb2ed9360ba13f6b19f8bb6ee9a16099039d8b59c9f51eab0a442249f428e7d",
    "physical-component:9f130f023a510be6e4b2f9075ed99cf75c4f88053e93189dda3f0bd51080f14a",
    "physical-component:cffd5f514585665c2d76279e036889887df24efa229a67f88052aef0d8ee4a83",
    "physical-component:d688afd3657ded3f0cf85a95956f2d42726f44923b168499320d681080539fb1",
    "physical-component:e76fd386dc9a23375537ede302f7f380a217fd4bbccd9536f856e8b4253a5ab8",
    "physical-component:ef7383db4412abe64b7e8d009679cffa4a3174d6da100c6de1fc37272aadeca9",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def git_bytes(rev: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{rev}:{path}"], cwd=ROOT)


def verify_bytes(raw: bytes, expected_bytes: int, expected_sha256: str, label: str) -> None:
    if len(raw) != expected_bytes or sha(raw) != expected_sha256:
        raise ValueError(f"{label}: whole-file bytes or SHA-256 mismatch")


def verify_roster(actual_ids, expected_ids, label: str) -> None:
    actual, expected = set(actual_ids), set(expected_ids)
    if actual != expected:
        raise ValueError(f"{label}: identity roster differs (missing={len(expected-actual)}, extra={len(actual-expected)})")


def verify_candidate_bindings(rows) -> None:
    if len(rows) != len(IDS):
        raise ValueError("candidate binding count differs from exact assigned scope")
    verify_roster((row["component_id"] for row in rows), IDS, "candidate binding roster")
    for row in rows:
        source = row["component_feature_source"]
        if (source["feature_sha256"] != row["current_feature_sha256"] or
                source["geometry_sha256"] != row["current_geometry_sha256"]):
            raise ValueError(f"candidate component feature/geometry mismatch: {row['component_id']}")
        target = row["admin_context"]
        if (target["atlas_target_source_id"] != "gb:USA:ADM2" or
                target["atlas_target_original_id"] != target["source_id"].split(":")[-1] or
                target["atlas_target_recorded_year"] != "2018" or
                target["atlas_target_source_role"] != "Counties" or
                target["atlas_target_administrative_level"] != "ADM2" or
                target["atlas_target_parent_id"] != "framework:province:alaska:4057e2fddbc5"):
            raise ValueError(f"native Atlas county target lineage mismatch: {row['component_id']}")


def jsonl(data: bytes):
    for n, line in enumerate(data.splitlines()):
        if line:
            yield n, line, json.loads(line)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main() -> None:
    requested_out = Path(sys.argv[1]) if len(sys.argv) > 1 else PACKET / "sources"
    lexical_out = requested_out if requested_out.is_absolute() else ROOT / requested_out
    if any(part.is_symlink() for part in [lexical_out, *lexical_out.parents]):
        raise ValueError("output path must not traverse a symlink")
    out = requested_out.resolve() if len(sys.argv) > 1 else (PACKET / "sources")
    if not out.is_relative_to(PACKET.resolve()):
        raise ValueError("output vintage must remain within the owned packet")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("output directory must be a fresh empty vintage")
    report_path = "coordination/engineering/global-gap-candidate-funnel-20261008/vintages/report-one/report.json"
    report_bytes = git_bytes(FUNNEL_REV, report_path)
    report = json.loads(report_bytes)
    funnel_inventory = {d["path"]: d for d in report["catalog_output_inventory"]}

    candidates = {}
    family_counts = {}
    family_source = {}
    scan_descriptors = []
    phase_receipts = []
    for batch in range(1, 8):
        batch_encoded = 0
        batch_decoded = 0
        for shard in range(6):
            path = f"coordination/engineering/global-gap-candidate-funnel-20261008/vintages/catalog-one-{batch:02}/catalog-{shard:02}.jsonl.gz"
            desc = funnel_inventory.get(path)
            if not desc:
                continue
            encoded = git_bytes(FUNNEL_REV, path)
            verify_bytes(encoded, desc["bytes"], desc["sha256"], f"funnel output {path}")
            decoded = gzip.decompress(encoded)
            if len(decoded) != desc["uncompressed_bytes"] or sha(decoded) != desc["uncompressed_sha256"]:
                raise ValueError(f"funnel output decoded mismatch: {path}")
            scan_descriptors.append({"path": path, "bytes": len(encoded), "sha256": sha(encoded), "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded)})
            batch_encoded += len(encoded)
            batch_decoded += len(decoded)
            for _, line, row in jsonl(decoded):
                if row.get("source_flags", {}).get("land_plus_unique_route_1005"):
                    fam = row["family"]
                    family_counts[fam] = family_counts.get(fam, 0) + 1
                    e = row["source_evidence"]
                    cohort = (e.get("source_products"), e.get("source_reference_year"))
                    family_source.setdefault(fam, {})[str(cohort)] = family_source.setdefault(fam, {}).get(str(cohort), 0) + 1
                    if fam == FAMILY:
                        if row["component_id"] in candidates:
                            raise ValueError("duplicate selected component row")
                        candidates[row["component_id"]] = row
        batch_total = batch_encoded + batch_decoded + len(report_bytes) + len(Path(__file__).read_bytes()) + 16 * 1024 * 1024
        if batch_total > 256 * 1024 * 1024:
            raise ValueError(f"catalog batch {batch:02} exceeds 256 MiB phase budget")
        phase_receipts.append({"phase": f"funnel-catalog-batch-{batch:02}", "encoded_input_bytes": batch_encoded, "decoded_input_bytes": batch_decoded, "metadata_input_bytes": len(report_bytes), "project_code_bytes": len(Path(__file__).read_bytes()), "reserved_output_bytes": 16 * 1024 * 1024, "total_bytes": batch_total})
    if sum(family_counts.values()) != 1005 or len(family_counts) != 711:
        raise ValueError(f"expected 1005 candidates / 711 families, got {sum(family_counts.values())}/{len(family_counts)}")
    verify_roster(candidates, IDS, "selected family roster")
    rank = sorted(family_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if rank[0] != ("gap-source-batch:3f21c83705d3cef5988b1295", 15) or rank[1] != (FAMILY, 13):
        raise ValueError(f"unexpected eligible-family ranking head: {rank[:2]}")

    # Authenticate the actual original 95,173-component GeoJSON subjects and
    # retain just the 13 exact features. This binds each manifest subject to a
    # real baseline feature without changing or simplifying its geometry.
    routing_report_path = "coordination/engineering/global-actionability-routing-20261007/results/report.json"
    routing_report_bytes = git_bytes(HEAD, routing_report_path)
    routing_report = json.loads(routing_report_bytes)
    component_feature_descriptors = [d for d in routing_report["complete_input_receipts"]
        if d.get("kind") == "components" and "physical-gap-components-1005-20261005-local19" in d.get("original_logical_path", "")]
    component_features = {}
    component_feature_inputs = []
    for desc in component_feature_descriptors:
        path = desc["path"]
        encoded = git_bytes(HEAD, path)
        verify_bytes(encoded, desc["bytes"], desc["sha256"], f"physical component feature payload {path}")
        decoded = gzip.decompress(encoded)
        if len(decoded) != desc["uncompressed_bytes"] or sha(decoded) != desc["uncompressed_sha256"]:
            raise ValueError(f"physical component decoded payload mismatch: {path}")
        collection = json.loads(decoded)
        if collection.get("type") != "FeatureCollection":
            raise ValueError(f"physical component subject source is not a FeatureCollection: {path}")
        component_feature_inputs.append({"path": path, "commit": HEAD, "bytes": len(encoded), "sha256": sha(encoded), "uncompressed_bytes": len(decoded), "uncompressed_sha256": sha(decoded)})
        for feature in collection["features"]:
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in IDS:
                if identity in component_features:
                    raise ValueError(f"duplicate exact physical component feature: {identity}")
                if sha(canonical(feature)) != candidates[identity]["current_feature_sha256"] or sha(canonical(feature["geometry"])) != candidates[identity]["current_geometry_sha256"]:
                    raise ValueError(f"retained original component feature/hash binding mismatch: {identity}")
                component_features[identity] = (path, feature)
    if set(component_features) != IDS or len(component_feature_descriptors) != 11:
        raise ValueError(f"expected all 13 selected features from 11 retained component payloads; got {len(component_features)}")
    component_encoded_total = sum(x["bytes"] for x in component_feature_inputs)
    component_decoded_total = sum(x["uncompressed_bytes"] for x in component_feature_inputs)
    component_phase_total = component_encoded_total + component_decoded_total + len(routing_report_bytes) + len(Path(__file__).read_bytes()) + 16 * 1024 * 1024
    if component_phase_total > 256 * 1024 * 1024:
        raise ValueError("original component feature payloads exceed 256 MiB phase budget")
    phase_receipts.append({"phase": "original-component-geojson-subjects", "encoded_input_bytes": component_encoded_total, "decoded_input_bytes": component_decoded_total, "metadata_input_bytes": len(routing_report_bytes), "project_code_bytes": len(Path(__file__).read_bytes()), "reserved_output_bytes": 16 * 1024 * 1024, "total_bytes": component_phase_total, "component_payload_count": len(component_feature_descriptors)})

    # Recover and retain the exact complete native family record; output shards
    # split JSONL records across gzip members, so their decoded streams must be
    # concatenated before parsing.
    family_report_path = "coordination/engineering/global-actionability-routing-20261007/results/report.json"
    family_report_bytes = git_bytes(HEAD, family_report_path)
    family_report = json.loads(family_report_bytes)
    family_parts = []
    family_decoded_parts = []
    for desc in family_report["outputs"]:
        if not desc["path"].startswith("families-"):
            continue
        full_path = f"coordination/engineering/global-actionability-routing-20261007/results/{desc['path']}"
        encoded = git_bytes(HEAD, full_path)
        verify_bytes(encoded, desc["bytes"], desc["sha256"], f"family output {full_path}")
        decoded_part = gzip.decompress(encoded)
        if len(decoded_part) != desc["uncompressed_bytes"] or sha(decoded_part) != desc["uncompressed_sha256"]:
            raise ValueError(f"family output decoded bytes mismatch: {full_path}")
        family_parts.append({"path": full_path, "bytes": len(encoded), "sha256": sha(encoded), "decoded_bytes": len(decoded_part), "decoded_sha256": sha(decoded_part)})
        family_decoded_parts.append(decoded_part)
    family_stream = b"".join(family_decoded_parts)
    family_matches = [(line, json.loads(line)) for line in family_stream.splitlines() if line and FAMILY.encode() in line]
    family_matches = [(line, obj) for line, obj in family_matches if obj.get("id") == FAMILY]
    if len(family_matches) != 1:
        raise ValueError(f"expected exactly one complete native family record, got {len(family_matches)}")
    family_line, family_record = family_matches[0]
    if family_record.get("component_count") != 995 or set(candidates) - set(family_record.get("complete_component_ids", [])):
        raise ValueError("complete native family roster does not contain the exact 13 candidates")
    if set(candidates) - set(family_record.get("compatible_original_admin_component_ids", [])):
        raise ValueError("one or more selected candidates lacks a compatible original admin witness")
    family_encoded_total = sum(x["bytes"] for x in family_parts)
    family_decoded_total = sum(x["decoded_bytes"] for x in family_parts)
    family_phase_total = family_encoded_total + family_decoded_total + len(family_report_bytes) + len(Path(__file__).read_bytes()) + 16 * 1024 * 1024
    if family_phase_total > 256 * 1024 * 1024:
        raise ValueError("complete family context exceeds 256 MiB phase budget")
    phase_receipts.append({"phase": "complete-native-family-context", "encoded_input_bytes": family_encoded_total, "decoded_input_bytes": family_decoded_total, "metadata_input_bytes": len(family_report_bytes), "project_code_bytes": len(Path(__file__).read_bytes()), "reserved_output_bytes": 16 * 1024 * 1024, "total_bytes": family_phase_total})

    catalog_bytes = git_bytes(HEAD, "coordination/engineering/global-gap-candidate-funnel-20261008/inputs/original-source-catalog.json")
    source_catalog = json.loads(catalog_bytes)
    source_files = {f["path"]: f for f in source_catalog["files"]}
    source_inputs = []
    component_sources = sorted((f for f in source_files.values() if "/components-" in f["path"]), key=lambda f: int(f["path"].rsplit("components-", 1)[1].split(".", 1)[0]))
    component_prefix = {}
    cursor = 0
    for source in component_sources:
        component_prefix[source["path"]] = cursor
        cursor += source["uncompressed_bytes"]
    source_cache = {}
    for cid, row in candidates.items():
        ref = row["original_source_provenance"]["record"]["component_record"]
        source = next((f for f in component_sources if f["path"].endswith("/" + ref["starts_in_descriptor"])), None)
        if source is None:
            raise ValueError(f"missing pinned original component shard {ref['starts_in_descriptor']}")
        path = source["path"]
        if path not in source_cache:
            encoded = git_bytes(source["commit"], path)
            verify_bytes(encoded, source["bytes"], source["sha256"], f"original component input {path}")
            decoded = gzip.decompress(encoded)
            if len(decoded) != source["uncompressed_bytes"] or sha(decoded) != source["uncompressed_sha256"]:
                raise ValueError(f"original component decoded bytes mismatch: {path}")
            source_cache[path] = decoded
            source_inputs.append({"path": path, "commit": source["commit"], "bytes": len(encoded), "sha256": sha(encoded), "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded)})
        decoded = source_cache[path]
        if sha(decoded) != ref["descriptor_decoded_sha256"]:
            raise ValueError(f"candidate descriptor pin mismatch: {cid}")
        local_offset = ref["decoded_stream_byte_offset"] - component_prefix[path]
        if local_offset < 0 or local_offset >= len(decoded):
            raise ValueError(f"candidate source offset is outside its declared shard: {cid}")
        tail = decoded[local_offset:]
        if b"\n" not in tail:
            source_index = int(ref["starts_in_descriptor"].split("components-")[1].split(".")[0]) + 1
            next_source = next((f for f in component_sources if f["path"].endswith(f"components-{source_index:03}.bin.gz")), None)
            if next_source is None:
                raise ValueError(f"candidate source row crosses beyond final shard: {cid}")
            next_encoded = git_bytes(next_source["commit"], next_source["path"])
            if len(next_encoded) != next_source["bytes"] or sha(next_encoded) != next_source["sha256"]:
                raise ValueError(f"original next component shard mismatch: {next_source['path']}")
            next_decoded = gzip.decompress(next_encoded)
            if len(next_decoded) != next_source["uncompressed_bytes"] or sha(next_decoded) != next_source["uncompressed_sha256"]:
                raise ValueError(f"original next component decoded shard mismatch: {next_source['path']}")
            tail += next_decoded
            if next_source["path"] not in source_cache:
                source_cache[next_source["path"]] = next_decoded
                source_inputs.append({"path": next_source["path"], "commit": next_source["commit"], "bytes": len(next_encoded), "sha256": sha(next_encoded), "decoded_bytes": len(next_decoded), "decoded_sha256": sha(next_decoded)})
        line = tail.split(b"\n", 1)[0]
        original = json.loads(line)
        if original.get("component") != cid or original.get("current_feature_sha256") != row["current_feature_sha256"] or original.get("current_geometry_sha256") != row["current_geometry_sha256"]:
            raise ValueError(f"funnel-to-original component mismatch: {cid}")
        row["_original_component_record"] = original
    source_encoded_total = sum(x["bytes"] for x in source_inputs)
    source_decoded_total = sum(x["decoded_bytes"] for x in source_inputs)
    source_phase_total = source_encoded_total + source_decoded_total + len(catalog_bytes) + len(Path(__file__).read_bytes()) + 16 * 1024 * 1024
    if source_phase_total > 256 * 1024 * 1024:
        raise ValueError("selected original component shards exceed 256 MiB phase budget")
    phase_receipts.append({"phase": "original-component-records", "encoded_input_bytes": source_encoded_total, "decoded_input_bytes": source_decoded_total, "metadata_input_bytes": len(catalog_bytes), "project_code_bytes": len(Path(__file__).read_bytes()), "reserved_output_bytes": 16 * 1024 * 1024, "total_bytes": source_phase_total})

    physical_report_path = "coordination/engineering/global-physical-comparison-20261006/results/report.json"
    physical_report_bytes = git_bytes(HEAD, physical_report_path)
    physical_report = json.loads(physical_report_bytes)
    physical_inventory = {d["path"]: d for d in physical_report.get("outputs", physical_report.get("output_inventory", [])) if isinstance(d, dict) and "path" in d}
    row_paths = sorted({r["_original_component_record"]["whole_physical_containing_file"] for r in candidates.values()})
    physical_blobs = {}
    for path in row_paths:
        full = path if path.startswith("coordination/") else f"coordination/engineering/global-physical-comparison-20261006/results/{path}"
        encoded = git_bytes(HEAD, full)
        desc = physical_inventory.get(full) or physical_inventory.get(path)
        if desc:
            verify_bytes(encoded, desc.get("bytes"), desc.get("sha256"), f"physical output {full}")
        decoded = gzip.decompress(encoded)
        physical_blobs[full] = {"rows": list(jsonl(decoded)), "bytes": len(encoded), "sha256": sha(encoded), "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded)}
    physical_encoded_total = sum(x["bytes"] for x in physical_blobs.values())
    physical_decoded_total = sum(x["decoded_bytes"] for x in physical_blobs.values())
    physical_phase_total = physical_encoded_total + physical_decoded_total + len(physical_report_bytes) + len(Path(__file__).read_bytes()) + 16 * 1024 * 1024
    if physical_phase_total > 256 * 1024 * 1024:
        raise ValueError("selected physical comparison shards exceed 256 MiB phase budget")
    phase_receipts.append({"phase": "candidate-physical-query-rows", "encoded_input_bytes": physical_encoded_total, "decoded_input_bytes": physical_decoded_total, "metadata_input_bytes": len(physical_report_bytes), "project_code_bytes": len(Path(__file__).read_bytes()), "reserved_output_bytes": 16 * 1024 * 1024, "total_bytes": physical_phase_total})

    physical_rows = {}
    for cid, row in candidates.items():
        original = row["_original_component_record"]
        target = original["whole_physical_containing_file"]
        full = target if target.startswith("coordination/") else f"coordination/engineering/global-physical-comparison-20261006/results/{target}"
        matches = [(line, x) for _, line, x in physical_blobs[full]["rows"] if x.get("component_id") == cid]
        if len(matches) != 1:
            raise ValueError(f"expected one physical row for {cid}, got {len(matches)}")
        line, physical = matches[0]
        packed_canonical = (json.dumps(physical, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
        physical_rows[cid] = {"line": packed_canonical[:-1], "row": physical, "path": full,
            "row_sha256": sha(packed_canonical), "raw_line_sha256": sha(line),
            "routing_declared_row_sha256": original["whole_physical_row_sha256"],
            "routing_row_hash_matches_current_retained_row": sha(packed_canonical) == original["whole_physical_row_sha256"]}

    # Retain the exact complete native metadata rows for every GSHHG source ID
    # referenced by these 13 physical query rows.
    target_native_ids = set()
    for entry in physical_rows.values():
        for relation in entry["row"].get("query_relations", []):
            if relation.get("source_level") == 1 and relation.get("source_id") is not None:
                target_native_ids.add(relation["source_id"])
    native_rows = {}
    native_inputs = []
    results_root = PACKET.parent.parent.parent / "coordination/engineering/gshhg-native-member-custody-20261007/results"
    for path in sorted(results_root.glob("records-*.jsonl.gz")):
        encoded = path.read_bytes()
        decoded = gzip.decompress(encoded)
        for _, line, obj in jsonl(decoded):
            if obj.get("id") in target_native_ids:
                native_rows[obj["id"]] = obj
        native_inputs.append({"path": str(path.relative_to(ROOT)), "bytes": len(encoded), "sha256": sha(encoded), "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded)})
    if set(native_rows) != target_native_ids:
        raise ValueError(f"missing native GSHHG metadata rows: {sorted(target_native_ids-set(native_rows))}")
    native_encoded_total = sum(x["bytes"] for x in native_inputs)
    native_decoded_total = sum(x["decoded_bytes"] for x in native_inputs)
    native_phase_total = native_encoded_total + native_decoded_total + len(Path(__file__).read_bytes()) + 16 * 1024 * 1024
    if native_phase_total > 256 * 1024 * 1024:
        raise ValueError("retained GSHHG metadata shard inputs exceed 256 MiB phase budget")
    phase_receipts.append({"phase": "gshhg-native-record-metadata", "encoded_input_bytes": native_encoded_total, "decoded_input_bytes": native_decoded_total, "metadata_input_bytes": 0, "project_code_bytes": len(Path(__file__).read_bytes()), "reserved_output_bytes": 16 * 1024 * 1024, "total_bytes": native_phase_total})
    for cid, entry in physical_rows.items():
        for relation in entry["row"].get("query_relations", []):
            sid = relation.get("source_id")
            if sid in native_rows and relation.get("source_record_sha256") != native_rows[sid].get("record_sha256"):
                raise ValueError(f"physical-to-native record hash mismatch for candidate {cid}, source {sid}")

    # Authenticate the full original USA ADM2 source product and retain its
    # seven exact Alaska source features with their complete geometry.
    corpus_catalog = json.loads(git_bytes(HEAD, "coordination/engineering/original-geography-source-corpus-20261006/catalogue.json"))
    usa = next(p for p in corpus_catalog["products"] if p.get("key") == "gb:USA:ADM2")
    payload_rel = "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-USA-ADM2-000.bin.gz"
    payload = (ROOT / payload_rel).read_bytes()
    part = usa["parts"][0]
    verify_bytes(payload, part["bytes"], part["sha256"], "USA ADM2 retained source payload")
    decoded = gzip.decompress(payload)
    if len(decoded) != part["uncompressed_bytes"] or sha(decoded) != part["uncompressed_sha256"]:
        raise ValueError("USA ADM2 source decoded payload does not match its original catalogue")
    fc = json.loads(decoded)
    selected_subjects = {row["source_evidence"]["unique_source_subject_id"].split(":")[-1] for row in candidates.values()}
    features = [f for f in fc["features"] if f.get("properties", {}).get("shapeID") in selected_subjects]
    if {f["properties"]["shapeID"] for f in features} != selected_subjects or len(features) != 7:
        raise ValueError("expected seven exact selected Alaska geoBoundaries features")
    feature_collection = {"type": "FeatureCollection", "features": features}
    dump(out / "selected-2018-usa-adm2-features.geojson", feature_collection)

    target_parts = []
    target_features = []
    for part_number in range(25, 28):
        target_path = f"data/geography/part-{part_number}.json"
        target_raw = git_bytes(HEAD, target_path)
        target_obj = json.loads(target_raw)
        target_parts.append({"path": target_path, "bytes": len(target_raw), "sha256": sha(target_raw)})
        for atlas_feature in target_obj["features"]:
            props = atlas_feature.get("properties", {})
            meta = props.get("metadata", {})
            if meta.get("original_id") in selected_subjects:
                target_features.append(atlas_feature)
    target_by_source_id = {f["properties"]["metadata"]["original_id"]: f for f in target_features}
    if set(target_by_source_id) != selected_subjects or len(target_features) != 7:
        raise ValueError("expected exact one-to-one Atlas geography target records for seven source subjects")
    if any(f["properties"]["metadata"].get("source_id") != "gb:USA:ADM2"
           or f["properties"]["metadata"].get("reference_year") != "2018"
           or f["properties"].get("parent_id") != "framework:province:alaska:4057e2fddbc5"
           for f in target_features):
        raise ValueError("Atlas target metadata does not bind every selected subject to the 2018 USA ADM2 source and Alaska parent")
    target_phase_total = sum(x["bytes"] for x in target_parts) + len(Path(__file__).read_bytes()) + 16 * 1024 * 1024
    if target_phase_total > 256 * 1024 * 1024:
        raise ValueError("three native target reference parts exceed 256 MiB phase budget")
    phase_receipts.append({"phase": "native-atlas-target-reference-parts-25-to-27", "encoded_input_bytes": sum(x["bytes"] for x in target_parts), "decoded_input_bytes": 0, "metadata_input_bytes": 0, "project_code_bytes": len(Path(__file__).read_bytes()), "reserved_output_bytes": 16 * 1024 * 1024, "total_bytes": target_phase_total, "part_descriptors": target_parts})
    dump(out / "native-atlas-target-features.geojson", {"type": "FeatureCollection", "features": target_features})
    dump(out / "candidate-components.geojson", {"type": "FeatureCollection", "features": [component_features[cid][1] for cid in sorted(IDS)]})

    source_registry = json.loads((ROOT / "data/administrative-sources.json").read_bytes())
    admin_meta = source_registry["gb:USA:ADM2"]
    if admin_meta["sha256"] != usa["original_sha256"] or admin_meta["boundaryYearRepresented"] != "2018":
        raise ValueError("administrative registry and retained source catalogue disagree")
    dump(out / "usa-adm2-source-metadata.json", {"registry": admin_meta, "catalogue": usa, "payload": {"path": payload_rel, "bytes": len(payload), "sha256": sha(payload), "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded)}, "source_features": [{"shapeID": f["properties"]["shapeID"], "shapeName": f["properties"]["shapeName"], "canonical_feature_sha256": sha(json.dumps(f, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())} for f in features]})

    rows_out = []
    physical_lines = []
    for cid in sorted(candidates):
        row = candidates[cid]
        original = row.pop("_original_component_record")
        physical = physical_rows[cid]["row"]
        physical_lines.append(physical_rows[cid]["line"])
        relations = physical.get("query_relations", [])
        covered = [r for r in relations if r.get("source_covers_candidate") is True]
        source_id = row["source_evidence"]["unique_source_subject_id"].split(":")[-1]
        feature = next(f for f in features if f["properties"]["shapeID"] == source_id)
        atlas_target = target_by_source_id[source_id]
        rows_out.append({
            "component_id": cid,
            "family": FAMILY,
            "current_feature_sha256": row["current_feature_sha256"],
            "current_geometry_sha256": row["current_geometry_sha256"],
            "route": row["source_evidence"],
            "original_source_provenance": row["original_source_provenance"],
            "original_component_record": original,
            "component_feature_source": {"path": component_features[cid][0], "commit": HEAD, "feature_sha256": sha(canonical(component_features[cid][1])), "geometry_sha256": sha(canonical(component_features[cid][1]["geometry"]))},
            "admin_context": {"source_id": "gb:USA:ADM2:" + source_id, "shape_name": feature["properties"]["shapeName"], "represented_year": "2018", "role": "native Atlas administrative county/county-equivalent target", "atlas_target_id": atlas_target["properties"]["id"], "atlas_target_parent_id": atlas_target["properties"]["parent_id"], "atlas_target_source_id": atlas_target["properties"]["metadata"]["source_id"], "atlas_target_original_id": atlas_target["properties"]["metadata"]["original_id"], "atlas_target_geometry_sha256": sha(canonical(atlas_target["geometry"])), "atlas_target_source_url": atlas_target["properties"]["metadata"].get("source_url"), "atlas_target_recorded_year": atlas_target["properties"]["metadata"].get("reference_year"), "atlas_target_source_role": atlas_target["properties"]["metadata"].get("source_role"), "atlas_target_administrative_level": atlas_target["properties"]["metadata"].get("administrative_level"), "source_subject_geometry_sha256": sha(canonical(feature["geometry"])), "route_source_geometry_sha256": row["source_evidence"].get("source_geometry_sha256"), "source_subject_matches_native_target_id": True, "source_product_variant": "retained geoBoundaries simplified GeoJSON from release tag 9469f09", "atlas_recorded_source_product_variant": "geoBoundaries non-simplified GeoJSON URL from release tag 9469f09", "source_product_variant_matches_atlas_url": False, "retained_product_geometry_matches_route_geometry_hash": row["source_evidence"].get("source_geometry_sha256") == sha(canonical(feature["geometry"])), "retained_product_geometry_matches_atlas_geometry": sha(canonical(atlas_target["geometry"])) == sha(canonical(feature["geometry"])), "recorded_admin_target_fit": "source subject and source role fit the named Atlas county/county-equivalent target; exact geometry variant equivalence remains unresolved"},
            "physical_query": {"path": physical_rows[cid]["path"], "current_retained_canonical_row_sha256": physical_rows[cid]["row_sha256"], "routing_declared_row_sha256": physical_rows[cid]["routing_declared_row_sha256"], "routing_row_hash_matches_current_retained_row": physical_rows[cid]["routing_row_hash_matches_current_retained_row"], "status": physical.get("physical_status"), "authority": physical.get("physical_authority"), "source_vintage": physical.get("source_vintage"), "relations": [{"source_id": r.get("source_id"), "source_level": r.get("source_level"), "candidate_covered": r.get("source_covers_candidate"), "candidate_covers_source": r.get("candidate_covers_source"), "witness": r.get("witness"), "source_record_sha256": r.get("source_record_sha256"), "source_pointset_sha256": r.get("source_pointset_sha256"), "disjoint": r.get("disjoint")} for r in relations], "unresolved": physical.get("unresolved"), "physical_limits": physical.get("physical_limits")},
            "gshhg_covering_records": [{"id": r.get("source_id"), "metadata": native_rows[r.get("source_id")]} for r in covered if r.get("source_id") in native_rows],
            "decision": {"recorded_target_source_fit": "fit-to-the-recorded-2018-Alaska-county-target", "exact_geometry_variant_fit": "unresolved", "coarse_land_support": "fit-source-relative-only" if covered else "unresolved", "historical_cause_or_repair_authority": "unresolved"},
            "missing_facts": ["the source geometry variant and transformations that bind the simplified retained feature and route geometry hash to the current Atlas target geometry", "candidate-specific no-loss/source-geometry predicates and the original processing history that explain the current fragment boundary", "target-specific shoreline registration/accuracy evidence where the boundary follows a registration-sensitive coast or channel", "an authorized repair decision"],
        })
    verify_candidate_bindings(rows_out)
    dump(out / "candidate-source-screen.json", {"version": 1, "tracker_head": FUNNEL_REV, "baseline_head": HEAD, "family": FAMILY, "candidate_count": len(rows_out), "component_feature_count": len(component_features), "recorded_target_identity_unresolved_count": 0, "source_subject_identity_fit_count": sum(r["decision"]["recorded_target_source_fit"] == "fit-to-the-recorded-2018-Alaska-county-target" for r in rows_out), "exact_geometry_variant_unresolved_count": sum(r["decision"]["exact_geometry_variant_fit"] == "unresolved" for r in rows_out), "family_native_component_count": family_record["component_count"], "native_target_record_count": len(target_features), "gshhg_native_source_record_count": len(native_rows), "family_context": {"grouping": family_record["original_fine_family"]["grouping"], "related_issues": family_record["collision_prerequisites"], "existing_related_issues": family_record["original_fine_family"]["existing_related_issues"], "edge_neighbor_ids": family_record["original_fine_family"]["edge_neighbor_ids"], "compatible_original_admin_component_ids": family_record["compatible_original_admin_component_ids"], "scope_limit": "the other 982 family components and all contacts are read-only context, not assigned"}, "findings": rows_out})
    with (out / "physical-query-rows.jsonl").open("xb") as stream:
        stream.write(b"\n".join(physical_lines) + b"\n")
    with (out / "complete-native-family-record.jsonl").open("xb") as stream:
        stream.write(family_line + b"\n")
    dump(out / "gshhg-native-query-records.json", {"source_vintage": "GSHHG 2.3.7, release 2017-06-15", "all_native_source_ids_referenced": sorted(target_native_ids), "records": [native_rows[x] for x in sorted(native_rows)], "input_descriptors": native_inputs, "limits": ["source-relative L1 land mask only", "heterogeneous WVS/WDBII observation ages", "per-feature observation dates not established", "shoreline/channel registration and narrow-feature accuracy remain unapproved"]})
    dump(out / "selection-ranking.json", {"total_land_plus_unique_candidates": sum(family_counts.values()), "complete_families": len(family_counts), "ranked_largest_families": [{"rank": n + 1, "family": fam, "candidate_count": count, "source_cohorts": family_source[fam]} for n, (fam, count) in enumerate(rank[:12])], "exclusions": {"rank_1_nordic": "family excluded by existing #1229/#1483 routing decision", "active_exact_component_claims": "none found for these 13; #1295, #1431, #1481 exact scopes remain excluded"}, "selection": "largest eligible family after Nordic exclusion: 13 USA ADM2 candidates, represented year 2018"})
    attribution_path = "coordination/engineering/original-geography-source-corpus-20261006/individual-source-attribution.json"
    attribution = json.loads(git_bytes(HEAD, attribution_path))
    usa_citation = next(x for x in attribution["individual_source_citations"] if x.get("id") == "gb:USA:ADM2")
    usa_credit = next(x for x in attribution["original_individual_metadata_source_credits"] if x.get("key") == "gb:USA:ADM2")
    terms_path = "coordination/engineering/original-geography-source-corpus-20261006/CITATION-AND-USE-geoBoundaries-original.txt"
    terms_bytes = git_bytes(HEAD, terms_path)
    with (out / "geoBoundaries-derivative-use-terms.txt").open("xb") as stream:
        stream.write(terms_bytes)
    dump(out / "usa-adm2-attribution.json", {"derivative_product_terms": "CC-BY 4.0; attribution to geoBoundaries required according to retained upstream terms", "individual_source_citation": usa_citation, "underlying_original_metadata_credit": usa_credit, "limits": ["license metadata and terms are preserved source claims, not a new legal opinion", "source authority and effective applicability remain unverified"]})
    # These controls exercise the same byte and identity validators consumed
    # above. They are evidence about the extraction joins, not geometry tests.
    verify_candidate_bindings(rows_out)
    corrupted = bytes([report_bytes[0] ^ 1]) + report_bytes[1:]
    try:
        verify_bytes(corrupted, len(report_bytes), sha(report_bytes), "negative control mutated funnel bytes")
    except ValueError:
        byte_mutation_rejected = True
    else:
        byte_mutation_rejected = False
    mutated_rows = json.loads(json.dumps(rows_out))
    mutated_rows[0]["admin_context"]["atlas_target_original_id"] += "-altered"
    try:
        verify_candidate_bindings(mutated_rows)
    except ValueError:
        target_join_mutation_rejected = True
    else:
        target_join_mutation_rejected = False
    if not byte_mutation_rejected or not target_join_mutation_rejected:
        raise ValueError("negative control failed to reject altered consumed source bytes or target join")
    for method_id, kind, evidence in [
        ("source-identity", "positive-control", {"candidate_feature_bindings": len(rows_out), "exact_feature_and_geometry_hash_matches": len(rows_out), "native_Atlas_county_target_lineage_matches": len(rows_out)}),
        ("source-identity", "negative-control", {"mutation": "altered one native Atlas target original_id in a candidate join", "target_join_mutation_rejected": target_join_mutation_rejected}),
        ("packet-generator", "positive-control", {"candidate_feature_bindings": len(rows_out), "exact_feature_and_geometry_hash_matches": len(rows_out), "native_Atlas_county_target_lineage_matches": len(rows_out)}),
        ("packet-generator", "negative-control", {"mutation": "changed one byte in the consumed funnel report and altered one target original_id", "consumed_source_byte_mutation_rejected": byte_mutation_rejected, "target_join_mutation_rejected": target_join_mutation_rejected}),
    ]:
        dump(out / f"control-{method_id}-{kind}.json", {"method_id": method_id, "kind": kind, "outcome": "passed", "evidence": evidence})
    input_receipt_path = out / "input-receipts.json"
    dump(input_receipt_path, {"funnel_report": {"path": report_path, "commit": FUNNEL_REV, "bytes": len(report_bytes), "sha256": sha(report_bytes)}, "funnel_catalogue_shards_scanned": scan_descriptors, "original_component_shards": source_inputs, "component_feature_source_report": {"path": routing_report_path, "bytes": len(routing_report_bytes), "sha256": sha(routing_report_bytes), "payloads": component_feature_inputs}, "family_report": {"path": family_report_path, "commit": HEAD, "bytes": len(family_report_bytes), "sha256": sha(family_report_bytes), "family_record_sha256": sha(family_line), "family_record_count": family_record["component_count"], "family_output_shards": family_parts}, "physical_rows": [{"path": path, "bytes": data["bytes"], "sha256": data["sha256"], "decoded_bytes": data["decoded_bytes"], "decoded_sha256": data["decoded_sha256"]} for path, data in sorted(physical_blobs.items())], "atlas_target_parts": target_parts, "usa_adm2_product": {"path": payload_rel, "bytes": len(payload), "sha256": sha(payload), "decoded_bytes": len(decoded), "decoded_sha256": sha(decoded), "catalogue_original_sha256": usa["original_sha256"], "attribution_path": attribution_path, "attribution_sha256": sha(git_bytes(HEAD, attribution_path)), "terms_path": terms_path, "terms_sha256": sha(terms_bytes)}, "current_head": HEAD})
    outputs = []
    for path in sorted(out.iterdir()):
        data = path.read_bytes()
        if len(data) > 32 * 1024 * 1024:
            raise ValueError(f"output exceeds 32 MiB: {path.name}")
        outputs.append({"path": str(path.relative_to(PACKET)), "bytes": len(data), "sha256": sha(data), "readback_sha256": sha(path.read_bytes())})
    total_output = sum(x["bytes"] for x in outputs)
    if total_output > 32 * 1024 * 1024:
        raise ValueError("aggregate ordinary outputs exceed reserved 32 MiB")
    output_receipt = {"version": 1, "inputs": phase_receipts, "outputs": outputs, "output_total_bytes": total_output, "limits": {"per_file_bytes": 32 * 1024 * 1024, "aggregate_output_bytes": 32 * 1024 * 1024, "phase_bytes": 256 * 1024 * 1024, "phase_reservation_each": 16 * 1024 * 1024}, "notes": ["All files are source-only evidence; no GIS, production, source download, or geometry mutation was performed.", "Every output was exclusively created, then byte-readback hashed."]}
    dump(out / "build-receipt.json", output_receipt)
    print(json.dumps({"candidate_count": len(rows_out), "family_count": len(family_counts), "source_rows": len(native_rows), "physical_row_count": len(physical_rows), "selected_admin_features": len(features), "output_paths": [str(p.relative_to(PACKET)) for p in sorted(out.iterdir())]}, indent=2))


if __name__ == "__main__":
    main()
