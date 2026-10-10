#!/usr/bin/env python3
"""Assemble the 327-row Melanesia handoff from retained, hash-pinned products.

This script only authenticates, selects, and links existing records and pointsets.
It does not run spatial predicates, repair geometry, retrieve provider data, or
reclassify the retained scientific observations.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.immutable import canonical_json  # noqa: E402

INDEX_DEFAULT = pathlib.Path.home() / "world-atlas-workspace/.cache/global-gap-work-index-20261009/geo4-next-full-batch-327.json"
ACTION = "coordination/engineering/global-actionability-routing-20261007"
PHYSICAL = "coordination/engineering/global-physical-comparison-20261006"
COMPONENTS = "coordination/engineering/physical-gap-components-1005-20261005-local19"
CORPUS = "coordination/engineering/original-geography-source-corpus-20261006"
MAKIRA = "research/geography/makira-gap-source-fitness-20261008"
CONTEXT = "research/campaigns/solomon-islands-source-fitness-20261007/batch-context.json"
MAKIRA_ISSUE = 1457
EXPECTED_BATCH = "gap-operational-batch:f94321eb696d00702d30402d"
EXPECTED_COUNT = 327
OWNED_PATH = pathlib.Path("research/geography/melanesia-full-batch-327-20261009")
OUTPUT_NAMES = (
    "actionability-records-327.jsonl.gz", "admin-binding-records-249.jsonl.gz", "assembly-receipt.json",
    "candidate-current-target-features.geojson.gz", "component-custody-origin.json", "component-subject-files.json",
    "context-reuse.json", "evidence-quality.json", "fine-family-records-38.jsonl.gz",
    "inherited-makira-findings-15.jsonl.gz", "operational-batch-record.jsonl.gz", "outcomes-327.jsonl.gz",
    "physical-records-327.jsonl.gz", "prior-work-reuse.json", "source-comparison-records-249.jsonl.gz",
    "source-feature-index.json", "source-features-gb-FJI-ADM2.geojson.gz", "source-features-gb-IDN-ADM2.geojson.gz",
    "source-features-gb-PNG-ADM3.geojson.gz", "source-features-gb-SLB-ADM1.geojson.gz",
    "source-features-gb-VUT-ADM1.geojson.gz", "summary.json", "work-index.json",
)
PRIOR_363 = "research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/batch-outcomes-363-002/batch-outcomes-363-v2.json"
PRIOR_25 = "research/geography/melanesia-gap-batch-241e2ce0-20261009/component-outcomes.jsonl"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def blob(commit: str, path: str) -> tuple[str, bytes]:
    tree = git("ls-tree", "-z", commit, "--", path).decode().rstrip("\0")
    if not tree or "\t" not in tree:
        raise ValueError(f"missing immutable input {commit}:{path}")
    meta, name = tree.split("\t", 1)
    mode, kind, oid = meta.split()
    if (mode, kind, name) != ("100644", "blob", path):
        raise ValueError(f"nonordinary immutable input {commit}:{path}")
    raw = git("cat-file", "blob", oid)
    return oid, raw


def read_json_blob(commit: str, path: str):
    _oid, raw = blob(commit, path)
    return json.loads(raw), raw


def local_bytes(path: str) -> bytes:
    return (ROOT / path).read_bytes()


def json_bytes(value) -> bytes:
    return canonical_json(value)


def deterministic_gzip(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=9, mtime=0)


def write_json(path: pathlib.Path, value) -> None:
    write_bytes_exclusive(path, json_bytes(value))


def write_jsonl_gz(path: pathlib.Path, rows) -> None:
    write_bytes_exclusive(path, deterministic_gzip(b"".join(json_bytes(row) + b"\n" for row in rows)))


def write_bytes_exclusive(path: pathlib.Path, value: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(value)


def admit_output_directory(requested: pathlib.Path) -> pathlib.Path:
    owned = (ROOT / OWNED_PATH).absolute()
    out = pathlib.Path(os.path.abspath(requested))
    try:
        out.relative_to(owned)
    except ValueError as error:
        raise ValueError(f"output must be inside the owned packet path: {OWNED_PATH}") from error
    cursor = out
    while cursor != owned.parent:
        if cursor.is_symlink():
            raise ValueError(f"symlink output path is not allowed: {cursor}")
        cursor = cursor.parent
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"output directory must be fresh; refusing to modify: {out}")
    for name in OUTPUT_NAMES:
        target = out / name
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"output file already exists; refusing to modify: {target}")
    out.mkdir(parents=True, exist_ok=False)
    return out


def descriptor(path: str, commit: str, raw: bytes, decoded: bytes | None = None):
    value = {"path": path, "commit": commit, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    if decoded is not None:
        value.update(uncompressed_bytes=len(decoded), uncompressed_sha256=sha(decoded))
    return value


def local_descriptor(path: str, raw: bytes, decoded: bytes | None = None):
    value = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    if decoded is not None:
        value.update(uncompressed_bytes=len(decoded), uncompressed_sha256=sha(decoded))
    return value


def verified_gzip(path: str, expected: dict) -> tuple[bytes, bytes]:
    raw = local_bytes(path)
    if len(raw) != expected["bytes"] or sha(raw) != expected["sha256"]:
        raise ValueError(f"encoded bytes differ: {path}")
    decoded = gzip.decompress(raw)
    if (len(decoded), sha(decoded)) != (expected["uncompressed_bytes"], expected["uncompressed_sha256"]):
        raise ValueError(f"decoded bytes differ: {path}")
    return raw, decoded


def actionability_bodies(report: dict):
    base = f"{ACTION}/results"
    bodies = {}
    used_parts = {}
    for body in report["complete_whole_raw_bodies"]:
        if body["name"] not in {"components", "families", "batches", "admin-bindings"}:
            continue
        pieces = []
        for part in body["parts"]:
            path = f"{base}/{part['path']}"
            expected = {"bytes": part["bytes"], "sha256": part["sha256"],
                        "uncompressed_bytes": part["uncompressed_bytes"],
                        "uncompressed_sha256": part["uncompressed_sha256"]}
            _raw, decoded = verified_gzip(path, expected)
            pieces.append(decoded)
            used_parts[path] = expected
        raw = b"".join(pieces)
        if (len(raw), sha(raw)) != (body["bytes"], body["sha256"]):
            raise ValueError(f"whole actionability body differs: {body['name']}")
        bodies[body["name"]] = (raw, body)
    return bodies, used_parts


def parse_jsonl(raw: bytes):
    lines = raw.splitlines(keepends=True)
    values = []
    for line in lines:
        if line.strip():
            values.append((json.loads(line), line))
    return values


def source_catalogue(corpus_root: pathlib.Path):
    catalogue = json.loads((corpus_root / "catalogue.json").read_bytes())
    wanted = {"gb:FJI:ADM2", "gb:IDN:ADM2", "gb:PNG:ADM3", "gb:SLB:ADM1", "gb:VUT:ADM1"}
    products = {row["key"]: row for row in catalogue["products"] if row["key"] in wanted}
    if set(products) != wanted:
        raise ValueError("source corpus lacks one of the five retained products")
    feature_maps = {}
    encoded_inputs = {}
    for source_id, product in products.items():
        raw_parts = []
        cursor = 0
        for part in sorted(product["parts"], key=lambda p: p["offset"]):
            if part["offset"] != cursor:
                raise ValueError(f"noncontiguous source product {source_id}")
            encoded = local_bytes(part["path"])
            if len(encoded) != part["bytes"] or sha(encoded) != part["sha256"]:
                raise ValueError(f"source product encoded bytes differ: {part['path']}")
            decoded = gzip.decompress(encoded)
            if (len(decoded), sha(decoded)) != (part["uncompressed_bytes"], part["uncompressed_sha256"]):
                raise ValueError(f"source product decoded bytes differ: {part['path']}")
            raw_parts.append(decoded)
            cursor += len(decoded)
            encoded_inputs[part["path"]] = (encoded, decoded)
        body = b"".join(raw_parts)
        if (len(body), sha(body)) != (product["original_bytes"], product["original_sha256"]):
            raise ValueError(f"source product whole bytes differ: {source_id}")
        geo = json.loads(body)
        rows = {}
        for feature in geo["features"]:
            sid = f"{source_id}:{feature['properties']['shapeID']}"
            if sid in rows:
                raise ValueError(f"duplicate source subject {sid}")
            rows[sid] = feature
        feature_maps[source_id] = rows
    return catalogue, products, feature_maps, encoded_inputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-index", type=pathlib.Path, default=INDEX_DEFAULT)
    parser.add_argument("--out", type=pathlib.Path,
        help="fresh output directory inside the owned packet path; existing paths are refused")
    args = parser.parse_args()
    requested_out = args.out or (ROOT / OWNED_PATH / "reproductions" / f"run-{uuid.uuid4().hex}")
    out = admit_output_directory(requested_out)
    index_raw = args.work_index.read_bytes()
    index = json.loads(index_raw)
    batch = index["original_operational_batch"]
    ids = batch["complete_component_ids"]
    if batch["batch_id"] != EXPECTED_BATCH or len(ids) != EXPECTED_COUNT or len(set(ids)) != EXPECTED_COUNT:
        raise ValueError("work-index exact 327 identity contract differs")
    if index["original_count"] != EXPECTED_COUNT or index["original_families"] != 38:
        raise ValueError("work-index count contract differs")
    id_set = set(ids)
    priority_rows = index["source_fitness_priority_families"]
    priority_ids = {component for family in priority_rows for component in family["selected_component_ids"]}
    if len(priority_ids) != index["priority_component_count"] or len(priority_ids) != 29:
        raise ValueError("priority component inventory differs")
    family_ids = {family["family_id"] for family in batch["family_locators"]}
    if len(family_ids) != 38 or any(family["family_id"] not in family_ids for family in priority_rows):
        raise ValueError("fine family inventory differs")

    # Existing immutable global routing and physical-result ledgers.
    action_report_path = f"{ACTION}/results/report.json"
    action_report, action_report_raw = read_json_blob("HEAD", action_report_path)
    bodies, action_parts = actionability_bodies(action_report)
    action_rows = {row["component"]: (row, line) for row, line in parse_jsonl(bodies["components"][0]) if row["component"] in id_set}
    admin_rows = {row["component"]: (row, line) for row, line in parse_jsonl(bodies["admin-bindings"][0]) if row["component"] in id_set}
    if set(action_rows) != id_set or len(admin_rows) != 249:
        raise ValueError("retained actionability/admin-binding subject counts differ")
    family_rows_all = [row for row, _ in parse_jsonl(bodies["families"][0])]
    family_rows = [row for row in family_rows_all if row.get("id") in family_ids]
    if len(family_rows) != 38 or {row["id"] for row in family_rows} != family_ids:
        raise ValueError("retained fine-family rows differ")
    flattened = [component for family in family_rows for component in family["complete_component_ids"] if component in id_set]
    if len(flattened) != EXPECTED_COUNT or set(flattened) != id_set:
        raise ValueError("family to component join is not a disjoint 327-row partition")
    batch_rows_all = [row for row, _ in parse_jsonl(bodies["batches"][0])]
    global_batch_count = action_report["counts"]["operational_batches"]
    if global_batch_count != 594 or len(batch_rows_all) != global_batch_count:
        raise ValueError("the immutable global operational-batch count is not 594")
    batch_rows = [row for row in batch_rows_all if row.get("id") == EXPECTED_BATCH or row.get("operational_batch") == EXPECTED_BATCH]
    if len(batch_rows) != 1 or set(batch_rows[0].get("complete_component_ids", [])) != id_set:
        raise ValueError("retained operational-batch member row differs")

    physical_report_path = f"{PHYSICAL}/results/report.json"
    physical_report, _physical_report_raw = read_json_blob("HEAD", physical_report_path)
    physical_quality_path = f"{PHYSICAL}/evidence-quality.json"
    physical_quality, physical_quality_raw = read_json_blob("HEAD", physical_quality_path)
    physical_descriptors = {row["path"]: row for row in physical_quality["outputs"]
                            if row["path"].startswith(f"{PHYSICAL}/results/components-")}
    used_physical_paths = {row[0]["whole_physical_containing_file"] for row in action_rows.values()}
    physical_rows = {}
    physical_input_file_records = {}
    for path in sorted(used_physical_paths):
        rel = path.split(f"{PHYSICAL}/results/", 1)[-1]
        descriptor_row = physical_descriptors.get(path)
        if descriptor_row is None:
            raise ValueError(f"missing physical product descriptor: {path}")
        _encoded, decoded = verified_gzip(path, descriptor_row)
        for row, line in parse_jsonl(decoded):
            component = row.get("component_id")
            if component in id_set:
                if component in physical_rows:
                    raise ValueError(f"duplicate physical row {component}")
                physical_rows[component] = (row, line, path)
        physical_input_file_records[path] = (descriptor_row, _encoded)
    if set(physical_rows) != id_set:
        raise ValueError("retained physical result does not cover all 327 components")

    # Pin exact byte-identical custody aliases to the current base tree so all
    # historical evidence commits are ancestors of the PR base. Preserve each
    # original content-addressed custody reference in a separate output.
    source_tree_commit = git("merge-base", "HEAD", "origin/main").decode().strip()
    # Exact source component FeatureCollections at the physical-product delivery.
    physical_config_path = f"{PHYSICAL}/input-config.json"
    physical_config, physical_config_raw = read_json_blob(source_tree_commit, physical_config_path)
    component_features = {}
    component_source_files = {}
    component_source_file_records = {}
    component_custody_origin = {}
    for pin in physical_config["inputs"]:
        if pin.get("kind") != "components":
            continue
        path = pin["path"]
        origin_oid, origin_raw = blob(pin["commit"], path)
        if len(origin_raw) != pin["bytes"] or sha(origin_raw) != pin["sha256"]:
            raise ValueError(f"candidate component custody bytes differ: {path}")
        oid, raw = blob(source_tree_commit, path)
        if raw != origin_raw:
            raise ValueError(f"current-base custody alias differs from recorded origin: {path}")
        decoded = gzip.decompress(raw)
        if (len(decoded), sha(decoded)) != (pin["uncompressed_bytes"], pin["uncompressed_sha256"]):
            raise ValueError(f"candidate component decoded custody bytes differ: {path}")
        collection = json.loads(decoded)
        for feature in collection["features"]:
            component = feature.get("id")
            if component in id_set:
                if component in component_features:
                    raise ValueError(f"duplicate candidate component {component}")
                component_features[component] = feature
                component_source_files[component] = path
        if any(feature.get("id") in id_set for feature in collection["features"]):
            component_source_file_records[path] = ({**pin, "commit": source_tree_commit}, raw, decoded, oid)
            component_custody_origin[path] = {"origin_commit": pin["commit"], "origin_git_blob": origin_oid,
                "origin_sha256": sha(origin_raw), "rebound_commit": source_tree_commit,
                "rebound_git_blob": oid, "rebound_sha256": sha(raw),
                "component_ids": sorted(feature.get("id") for feature in collection["features"] if feature.get("id") in id_set)}
    if set(component_features) != id_set:
        raise ValueError("physical custody source does not contain all exact candidate features")

    # Existing original source-comparison records are pulled from their pinned base tree.
    comparison_rows = {}
    comparison_file_records = {}
    for component, (binding, _line) in admin_rows.items():
        observations = binding["observations"]
        if len(observations) != 1:
            raise ValueError(f"unexpected number of retained observations for {component}")
        obs = observations[0]
        path = obs["containing_file"]
        if path not in comparison_file_records:
            oid, encoded = blob(source_tree_commit, path)
            decoded = gzip.decompress(encoded)
            records = json.loads(decoded)
            if not isinstance(records, list):
                raise ValueError(f"source comparison file is not a JSON array: {path}")
            by_id = {row["component"]: row for row in records}
            comparison_file_records[path] = (oid, encoded, decoded, by_id)
        row = comparison_file_records[path][3].get(component)
        if row is None or sha(json_bytes(row)) != obs["whole_original_row_sha256"]:
            raise ValueError(f"retained source comparison row differs: {component}")
        feature = component_features[component]
        feature_sha = sha(json_bytes(feature))
        geometry_sha = sha(json_bytes(feature["geometry"]))
        action = action_rows[component][0]
        physical_row = physical_rows[component][0]
        if not (feature_sha == action["current_feature_sha256"] == row["full_component_feature_sha256"]):
            raise ValueError(f"candidate/current-target full feature hash differs: {component}")
        if not (geometry_sha == action["current_geometry_sha256"] == row["component_geometry_sha256"]):
            raise ValueError(f"candidate/current-target exact pointset hash differs: {component}")
        if sha(json_bytes(physical_row)) != action["whole_physical_row_sha256"]:
            raise ValueError(f"physical row whole hash differs: {component}")
        comparison_rows[component] = row

    # Authenticate source payloads and extract only source features referenced by
    # the existing full comparison intersections. No new spatial operation occurs.
    corpus_root = ROOT / CORPUS
    catalogue, products, source_feature_maps, source_encoded_inputs = source_catalogue(corpus_root)
    used_source_features = defaultdict(dict)
    source_joins = defaultdict(list)
    for component, row in comparison_rows.items():
        for intersection in row["feature_intersections"]:
            binding = intersection["binding"]
            sid = f"{binding['source_id']}:{binding['shapeID']}"
            feature = source_feature_maps[binding["source_id"]].get(sid)
            if feature is None:
                raise ValueError(f"source feature absent from retained product: {sid}")
            feature_sha = sha(json_bytes(feature))
            geometry_sha = sha(json_bytes(feature["geometry"]))
            if feature_sha != binding["feature_sha256"] or geometry_sha != binding["geometry_sha256"]:
                raise ValueError(f"retained source feature hash differs: {sid}")
            used_source_features[binding["source_id"]][sid] = feature
            source_joins[component].append({"source_feature_id": sid, "feature_sha256": feature_sha,
                                            "geometry_sha256": geometry_sha,
                                            "intersection_sha256": intersection["intersection"]["geometry_sha256"]})

    # Exact inherited findings from #1457, used only for its 15 overlapping IDs.
    makira_register, makira_register_raw = read_json_blob("HEAD", f"{MAKIRA}/source-register.json")
    makira_assessment, makira_assessment_raw = read_json_blob("HEAD", f"{MAKIRA}/assessment.json")
    inherited_ids = set(makira_assessment["component_ids"]) & id_set
    inherited_rows = [row for row in makira_register["components"] if row["id"] in inherited_ids]
    if len(inherited_ids) != 15 or len(inherited_rows) != 15 or len(inherited_ids & priority_ids) != 4:
        raise ValueError("Makira exact inherited 15-row source-fitness scope differs")
    if not set(makira_assessment["component_ids"]).isdisjoint(set(ids) - inherited_ids):
        raise ValueError("Makira inheritance mapping is not disjoint")

    # #1424 is the retained cross-batch Solomon context; its subjects are distinct.
    context_value, context_raw = read_json_blob("HEAD", CONTEXT)
    context_ids = {row["component"] for row in context_value["components"]}
    if context_value["issue"] != 1424 or len(context_value["batches"]) != 2 or len(context_ids) != 45 or context_ids & id_set:
        raise ValueError("#1424 source/physical context is not the declared disjoint two-batch reference")

    # Exact prior outcomes are checked by subject ID before reuse/deferral. The
    # two other accepted packets are disjoint; only #1457 supplies inherited rows.
    prior_363_raw = local_bytes(PRIOR_363)
    prior_363 = json.loads(prior_363_raw)
    prior_363_ids = {row["component_id"] for row in prior_363["cases"]}
    prior_25_raw = local_bytes(PRIOR_25)
    prior_25_rows = [row for row, _line in parse_jsonl(prior_25_raw)]
    prior_25_ids = {row["component_id"] for row in prior_25_rows}
    if (prior_363["candidate_count"] != 363 or len(prior_363_ids) != 363 or prior_363_ids & id_set
            or len(prior_25_rows) != 25 or len(prior_25_ids) != 25 or prior_25_ids & id_set):
        raise ValueError("prior 363- or 25-component packets overlap or differ from their declared rosters")
    if len(inherited_ids) != 15 or len(inherited_ids & priority_ids) != 4:
        raise ValueError("prior Makira inheritance or priority overlap differs")
    prior_reuse = {
        "current_issue": 1646,
        "current_batch": EXPECTED_BATCH,
        "current_component_ids_sha256": sha(json.dumps(sorted(id_set), separators=(",", ":")).encode()),
        "prior_evidence": [
            {"issues": [1424], "status": "closed", "path": CONTEXT, "sha256": sha(context_raw), "bytes": len(context_raw),
             "subjects": 45, "overlap_with_current_327": 0, "use": "Two-batch Solomon source/physical context only; referenced by context-reuse.json."},
            {"issues": [1457, 1465], "status": "closed-and-merged", "path": f"{MAKIRA}/assessment.json", "sha256": sha(makira_assessment_raw), "bytes": len(makira_assessment_raw),
             "subjects": 15, "overlap_with_current_327": 15, "priority_overlap": len(inherited_ids & priority_ids),
             "use": "All 15 exact rows inherited; no source-fitness redo."},
            {"issues": [1604], "status": "open", "url": "https://github.com/ChengshuLi/WorldAtlas/issues/1604",
             "subjects": 15, "overlap_with_current_327": 15, "use": "Separate Makira checksum-algorithm provenance erratum; not addressed or duplicated."},
            {"issues": [1626, 1639], "status": "closed-and-merged", "path": PRIOR_363, "sha256": sha(prior_363_raw), "bytes": len(prior_363_raw),
             "subjects": len(prior_363_ids), "overlap_with_current_327": 0, "use": "Prior complete 363-component Melanesia packet; exact roster checked and disjoint."},
            {"issues": [1643, 1644], "status": "open-issue-and-merged-pr", "path": PRIOR_25, "sha256": sha(prior_25_raw), "bytes": len(prior_25_raw),
             "subjects": len(prior_25_ids), "overlap_with_current_327": 0, "use": "Prior 25-component packet; exact roster checked and disjoint."}
        ],
        "issue_deduplication": "One exact full-batch issue (#1646); no per-gap or sub-batch issue created.",
        "global_594_operational_batches": {"count": global_batch_count, "preserved": True}
    }

    # Emit exact full pointsets, full source features, unchanged science rows and a
    # disjoint classification/status ledger. Current target equals retained
    # candidate Feature byte-semantics, as proved above for every subject.
    ordered_features = [component_features[component] for component in sorted(ids)]
    write_bytes_exclusive(out / "candidate-current-target-features.geojson.gz",
        deterministic_gzip(json_bytes({"type": "FeatureCollection", "features": ordered_features})))
    component_commit_by_path = {path: entry[0]["commit"] for path, entry in component_source_file_records.items()}
    write_json(out / "component-subject-files.json", {
        component: {"commit": component_commit_by_path[component_source_files[component]],
                   "path": component_source_files[component]}
        for component in sorted(ids)
    })
    write_json(out / "component-custody-origin.json", {
        "version": 1, "physical_input_config_path": physical_config_path,
        "physical_input_config_commit": source_tree_commit,
        "physical_input_config_sha256": sha(physical_config_raw),
        "rebound_payloads": [component_custody_origin[path] for path in sorted(component_custody_origin)]
    })
    source_feature_index = []
    for source_id in sorted(used_source_features):
        features = [used_source_features[source_id][sid] for sid in sorted(used_source_features[source_id])]
        filename = "source-features-" + source_id.replace(":", "-") + ".geojson.gz"
        write_bytes_exclusive(out / filename, deterministic_gzip(json_bytes({"type": "FeatureCollection", "features": features})))
        for sid, feature in sorted(used_source_features[source_id].items()):
            source_feature_index.append({"source_feature_id": sid, "source_product": source_id,
                                         "shapeID": feature["properties"]["shapeID"],
                                         "feature_sha256": sha(json_bytes(feature)),
                                         "geometry_sha256": sha(json_bytes(feature["geometry"])),
                                         "bundle_file": filename})
    write_json(out / "source-feature-index.json", {"features": source_feature_index})
    write_jsonl_gz(out / "source-comparison-records-249.jsonl.gz", [comparison_rows[k] for k in sorted(comparison_rows)])
    write_jsonl_gz(out / "physical-records-327.jsonl.gz", [physical_rows[k][0] for k in sorted(physical_rows)])
    write_jsonl_gz(out / "actionability-records-327.jsonl.gz", [action_rows[k][0] for k in sorted(action_rows)])
    write_jsonl_gz(out / "admin-binding-records-249.jsonl.gz", [admin_rows[k][0] for k in sorted(admin_rows)])
    write_jsonl_gz(out / "fine-family-records-38.jsonl.gz", sorted(family_rows, key=lambda row: row["id"]))
    write_jsonl_gz(out / "operational-batch-record.jsonl.gz", batch_rows)
    write_jsonl_gz(out / "inherited-makira-findings-15.jsonl.gz", sorted(inherited_rows, key=lambda row: row["id"]))

    outcomes = []
    route_counts = Counter()
    admin_counts = Counter()
    for component in sorted(ids):
        action = action_rows[component][0]
        feature = component_features[component]
        binding = admin_rows.get(component, (None, None))[0]
        comparison = comparison_rows.get(component)
        obs = binding["observations"][0] if binding else None
        if component in inherited_ids:
            outcome = "inherited-source-fitness-unresolved-from-1457"
            disposition = "No qualifying physical/imagery source; all source fitness and physical authority remain unapproved."
        elif component in priority_ids:
            outcome = "priority-source-fitness-unresolved"
            disposition = "Retained admin source comparison has a unique compatible covering subject; this is not physical/source fitness approval."
        elif obs:
            outcome = "retained-source-comparison:" + obs["status"]
            disposition = "Preserve the existing comparison status; cause and source/physical authority remain unresolved."
        else:
            outcome = "retained-actionability-prerequisite:" + action["next_prerequisite"]
            disposition = "No admin-binding observation exists in the retained comparison output; preserve the recorded prerequisite."
        route_counts[outcome] += 1
        if obs:
            admin_counts[obs["status"]] += 1
        row = {"component_id": component, "family_id": action["family"], "operational_batch": action["operational_batch"],
               "outcome": outcome, "disposition": disposition, "priority_source_fitness": component in priority_ids,
               "inherited_issue": MAKIRA_ISSUE if component in inherited_ids else None,
               "candidate_current_target": {"feature_id": feature["id"], "feature_sha256": sha(json_bytes(feature)),
                                            "geometry_sha256": sha(json_bytes(feature["geometry"])),
                                            "relation": "same-retained-complete-feature-and-pointset"},
               "source_product_ids": (obs["source_products"] if obs else []),
               "source_features": source_joins.get(component, []),
               "source_comparison": ({"status": obs["status"], "cause_status": obs["cause_status"],
                                      "surface_status": obs["surface_status"],
                                      "record_sha256": sha(json_bytes(comparison)),
                                      "component_minus_source_union": comparison["component_minus_source_union"],
                                      "source_union_intersection": comparison["source_union_intersection"],
                                      "whole_relevant_source_union": comparison["whole_relevant_source_union"]}
                                     if comparison and obs else None),
               "physical": {"status": physical_rows[component][0]["status"],
                            "physical_status": physical_rows[component][0]["physical_status"],
                            "physical_authority": physical_rows[component][0]["physical_authority"],
                            "record_sha256": sha(json_bytes(physical_rows[component][0]))},
               "routing": {"next_prerequisite": action["next_prerequisite"], "dispatch_ready": action["dispatch_ready"],
                           "source_fitness_prerequisite": action["source_fitness_prerequisite"],
                           "physical_status": action["physical_status"], "physical_authority": action["physical_authority"]}}
        outcomes.append(row)
    if len(outcomes) != EXPECTED_COUNT or sum(route_counts.values()) != EXPECTED_COUNT:
        raise ValueError("outcomes do not form a complete disjoint 327-row partition")
    write_jsonl_gz(out / "outcomes-327.jsonl.gz", outcomes)

    write_bytes_exclusive(out / "work-index.json", index_raw)
    write_json(out / "context-reuse.json", {
        "issue": 1424, "path": CONTEXT, "sha256": sha(context_raw), "bytes": len(context_raw),
        "retained_context": {"operational_batches": len(context_value["batches"]),
                             "fine_families": len(context_value["families"]),
                             "components": len(context_ids), "admin_bindings": len(context_value["admin_bindings"]),
                             "physical_rows": len(context_value["physical_result_rows"])},
        "relationship": "disjoint Melanesia region source/physical context; reused by reference only, not mixed into the 327 subject roster or outcomes"
    })
    write_json(out / "prior-work-reuse.json", prior_reuse)
    summary = {"operational_batch": EXPECTED_BATCH, "component_count": len(outcomes), "fine_family_count": len(family_ids),
               "operational_batch_accounting_total": global_batch_count, "priority_source_fitness_count": len(priority_ids),
               "priority_inherited_from_1457": len(inherited_ids & priority_ids),
               "priority_without_inherited_assessment": len(priority_ids - inherited_ids),
               "inherited_1457_not_in_priority_29": len(inherited_ids - priority_ids),
               "retained_admin_binding_count": len(admin_rows), "no_admin_binding_row_count": len(id_set - set(admin_rows)),
               "retained_source_comparison_status_counts": dict(sorted(admin_counts.items())),
               "disjoint_outcome_counts": dict(sorted(route_counts.items())),
               "candidate_current_target_features": len(ordered_features), "unique_retained_source_features": len(source_feature_index),
               "source_comparison_rows": len(comparison_rows), "physical_rows": len(physical_rows),
               "prior_363_overlap": len(id_set & prior_363_ids), "prior_25_overlap": len(id_set & prior_25_ids),
               "all_327_current_targets_equal_full_candidate_features": True,
               "spatial_operations_run": False, "external_sources_retrieved": False,
               "authority": {"source": "unapproved", "physical": "unapproved", "territorial": "undetermined",
                             "causality": "unknown", "current-production-release": "not asserted"}}
    write_json(out / "summary.json", summary)

    input_pin = {"path": str(args.work_index), "bytes": len(index_raw), "sha256": sha(index_raw)}
    write_json(out / "assembly-receipt.json", {"version": 1, "base_commit": source_tree_commit,
        "input_packet": input_pin, "actionability_report_sha256": sha(action_report_raw),
        "physical_report_sha256": sha(_physical_report_raw), "component_custody_files": len(component_source_file_records),
        "source_comparison_files": len(comparison_file_records), "physical_result_files": len(physical_input_file_records),
        "actionability_parts": len(action_parts), "source_product_files": len(source_encoded_inputs),
        "checks": {"component_ids_exact": True, "families_disjoint": True, "full_candidate_target_hashes": True,
                   "source_feature_hashes": True, "comparison_remainders_preserved": True,
                   "physical_row_hashes": True, "all_327_outcomes_disjoint": True,
                   "makira_15_inherited": True, "1424_context_disjoint": True,
                   "prior_363_and_25_rosters_disjoint": True, "594_global_batch_count_preserved": True,
                   "no_spatial_or_provider_operations": True}})

    # Evidence quality descriptor is generated only after all deliverables exist.
    # The complete source graph is assembled below from the exact blobs consumed.
    create_evidence_manifest(out, source_tree_commit, ids, component_source_file_records,
                             action_report_path, action_report_raw, action_parts,
                             physical_report_path, _physical_report_raw, physical_quality_path, physical_quality_raw,
                             physical_input_file_records, physical_config_path, physical_config_raw,
                             comparison_file_records, source_encoded_inputs, catalogue,
                             makira_register_raw, makira_assessment_raw, context_raw)


def create_evidence_manifest(out, base_commit, ids, component_files, action_report_path,
                             action_report_raw, action_parts, physical_report_path,
                             physical_report_raw, physical_quality_path, physical_quality_raw,
                             physical_files, physical_config_path, physical_config_raw, comparison_files,
                             source_files, catalogue, makira_register_raw,
                             makira_assessment_raw, context_raw):
    baseline = {}
    def add_baseline(path, commit, raw, decoded=None):
        baseline[(commit, path)] = descriptor(path, commit, raw, decoded)

    add_baseline(action_report_path, base_commit, action_report_raw)
    add_baseline(physical_report_path, base_commit, physical_report_raw)
    add_baseline(physical_quality_path, base_commit, physical_quality_raw)
    add_baseline(physical_config_path, base_commit, physical_config_raw)
    for path, expected in action_parts.items():
        raw, decoded = verified_gzip(path, expected)
        add_baseline(path, base_commit, raw, decoded)
    for path, (pin, raw, decoded, _oid) in component_files.items():
        add_baseline(path, pin["commit"], raw, decoded)
    for path, (desc, raw) in physical_files.items():
        decoded = gzip.decompress(raw)
        add_baseline(path, base_commit, raw, decoded)
    for path, (oid, raw, decoded, _rows) in comparison_files.items():
        add_baseline(path, base_commit, raw, decoded)
    for path in (PRIOR_363, PRIOR_25):
        _oid, raw = blob(base_commit, path)
        add_baseline(path, base_commit, raw)
    required_pin_paths = {
        "global_actionability_routing": "coordination/engineering/global-actionability-routing-20261007/evidence-quality.json",
        "global_physical_comparison": "coordination/engineering/global-physical-comparison-20261006/evidence-quality.json",
        "original_geography_source_corpus": "coordination/engineering/original-geography-source-corpus-20261006/evidence-quality.json",
        "solomon_islands_source_fitness": "research/campaigns/solomon-islands-source-fitness-20261007/evidence-quality.json",
        "makira_15_source_fitness": f"{MAKIRA}/evidence-quality.json",
    }
    required_pins = {}
    for key, path in required_pin_paths.items():
        _oid, raw = blob(base_commit, path)
        add_baseline(path, base_commit, raw)
        required_pins[key] = sha(raw)
    catalogue_path = f"{CORPUS}/catalogue.json"
    catalogue_raw = local_bytes(catalogue_path)
    add_baseline(catalogue_path, base_commit, catalogue_raw)
    helper_path = "scripts/evidence/immutable.py"
    _helper_oid, helper_raw = blob(base_commit, helper_path)
    if helper_raw != (ROOT / helper_path).read_bytes():
        raise ValueError("executed immutable evidence helper differs from the pinned base helper")
    add_baseline(helper_path, base_commit, helper_raw)
    for path, (raw, decoded) in source_files.items():
        add_baseline(path, base_commit, raw, decoded)
    for path, raw in [(f"{MAKIRA}/source-register.json", makira_register_raw),
                      (f"{MAKIRA}/assessment.json", makira_assessment_raw), (CONTEXT, context_raw)]:
        add_baseline(path, base_commit, raw)
    # Data used only to prove previous source-feature registry terms and dates.
    admin_registry_path = "data/administrative-sources.json"
    try:
        _oid, admin_raw = blob(base_commit, admin_registry_path)
        add_baseline(admin_registry_path, base_commit, admin_raw)
    except Exception:
        pass

    # Output inventory is exact bytes, including decoded size/hash for gzip products.
    out_files = []
    for path in sorted(p for p in out.iterdir() if p.is_file() and p.name != "evidence-quality.json"):
        raw = path.read_bytes()
        decoded = gzip.decompress(raw) if path.name.endswith(".gz") else None
        out_files.append(local_descriptor(path.relative_to(ROOT).as_posix(), raw, decoded))

    # Each ID is bound to its original whole FeatureCollection custody blob.
    # Rebuild exact component -> source path from the emitted feature receipt data.
    # The physical custody manifests are stable and included above.
    # `component-subject-files.json` is assembled by the main extraction below.
    subject_map_path = out / "component-subject-files.json"
    subject_map = json.loads(subject_map_path.read_bytes())
    subject_files = {component: {"commit": value["commit"], "path": value["path"]}
                     for component, value in subject_map.items()}
    file_map = {(f["commit"], f["path"]): f for f in baseline.values()}
    if any((v["commit"], v["path"]) not in file_map for v in subject_files.values()):
        raise ValueError("evidence subject map refers to an unpinned candidate input")

    # Source citations inherit recorded metadata; no legal or temporal authority is
    # upgraded by selecting the exact geometry records.
    source_rows = []
    corpus_products = {p["key"]: p for p in catalogue["products"]}
    for source_id in ["gb:FJI:ADM2", "gb:IDN:ADM2", "gb:PNG:ADM3", "gb:SLB:ADM1", "gb:VUT:ADM1"]:
        p = corpus_products[source_id]
        source_rows.append({"id": source_id, "url": p["recorded_consumed_url"],
            "role": "Retained simplified GeoBoundaries administrative product used only for literal source comparison geometry.",
            "vintage": f"source vintage 79ffb2ed04702e16f009e4675a8d74ef9bd09d4f; represented-year claim {p.get('source_represented_year_claim','unknown')}",
            "license": {"status": "redistributable" if p.get("recorded_license") else "unknown",
                        "terms": f"The original source catalogue records: {p.get('recorded_license','unknown')}. Preserve the applicable attribution/share-alike terms; no independent legal qualification or source-authority review is asserted."},
            "retention": "retained", "verification": "verified", "temporal_status": "reference",
            "retrieved_at": "2026-10-06 (repository source-corpus capture; not a source effective date)",
            "restoration": "See the exact original product and source-corpus catalogue pins in baseline.files.",
            "limit": "The source-catalogue represented-year value is a claim, not a supported effective interval. Literal geometry comparison is not boundary authority, present-day truth, or physical/source fitness approval.",
            "files": [local_descriptor(part["path"], source_files[part["path"]][0], source_files[part["path"]][1])
                      for part in p["parts"]]})
    makira_manifest = json.loads(makira_assessment_raw) if False else None
    # Inherited source assessment sources are already fully cited by the exact #1457
    # assessment manifest; do not duplicate/reinterpret their conclusions here.
    source_rows.append({"id": "makira-prior-assessment-1457", "url": "https://github.com/ChengshuLi/WorldAtlas/issues/1457",
        "role": "Prior accepted 15-component Makira source-fitness assessment, inherited by exact component ID.",
        "vintage": "issue #1457 and retained source-fitness packet dated 2026-10-08",
        "license": {"status": "unknown", "terms": "Issue and evidence packet citation; external candidate-source rights remain exactly as recorded in the original assessment."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
        "retrieved_at": "2026-10-09", "restoration": f"{MAKIRA}/assessment.json and source-register.json",
        "limit": "Inherited findings remain unresolved/unapproved and are not repeated as a new source search."})
    physical_quality = json.loads(physical_quality_raw)
    for inherited_source in physical_quality["sources"]:
        source_rows.append({key: value for key, value in inherited_source.items() if key != "files"} | {
            "retention": "restoration-only",
            "restoration": "Reused only through the already retained #1261 physical comparison records; its original source bytes and licenses remain in the pinned physical-source packet.",
            "limit": "This work did not re-read the original physical source archive or native reader; source geometry outputs are inherited source-relative observations only."})

    subject_ids = sorted(ids)
    # subject hash follows scripts/evidence-quality.mjs exactly.
    subject_hash = sha(json.dumps(subject_ids, separators=(",", ":")).encode())
    manifest = {"version": 1, "issue": 1646, "lane": "geography",
        "worker_id": "01a112c1-ac99-74b1-9047-a1da2dd0e245", "subject_ids": subject_ids,
        "subject_ids_sha256": subject_hash,
        "baseline": {"version": 2, "commit": base_commit, "files": list(baseline.values()),
            "pins": required_pins | {"actionability_report": sha(action_report_raw), "physical_report": sha(physical_report_raw),
                     "source_corpus_catalogue": sha(catalogue_raw), "makira_assessment": sha(makira_assessment_raw),
                     "makira_source_register": sha(makira_register_raw), "solomon_context_1424": sha(context_raw)},
            "pin_files": {"actionability_report": {"commit": base_commit, "path": action_report_path},
                          "physical_report": {"commit": base_commit, "path": physical_report_path},
                          "source_corpus_catalogue": {"commit": base_commit, "path": catalogue_path},
                          "makira_assessment": {"commit": base_commit, "path": f"{MAKIRA}/assessment.json"},
                          "makira_source_register": {"commit": base_commit, "path": f"{MAKIRA}/source-register.json"},
                          "solomon_context_1424": {"commit": base_commit, "path": CONTEXT}} | {
                key: {"commit": base_commit, "path": path} for key, path in required_pin_paths.items()},
            "subject_files": subject_files},
        "sources": source_rows, "outputs": out_files,
        "methods": [{"id": "retained-record-bundle-and-disjoint-roster", "description":
            "Authenticated exact candidate FeatureCollections, current-target full-feature/pointset identities, retained source-comparison rows and retained physical/actionability rows. Extracted only existing GeoJSON features from pinned source payloads; preserved precomputed literal intersections and component-minus-source-union remainders. No new spatial predicate, GIS replay, provider retrieval, current production operation, or factual reclassification was performed.",
            "software": "Python 3; repository scripts/evidence/immutable.py canonical JSON; Git immutable blob reader; gzip/JSON extraction only",
            "units": "Exact feature identity and source comparison rows; inherited areas remain the original recorded measurements only", "kind": "source"}],
        "metrics": [], "summaries": [],
        "conclusions": [{"text": "The 327-subject roster is complete and partitioned into 38 exact fine families within the unchanged 594 operational-batch accounting.", "status": "supported", "source_ids": ["gb:FJI:ADM2", "gb:IDN:ADM2", "gb:PNG:ADM3", "gb:SLB:ADM1", "gb:VUT:ADM1"]},
            {"text": "Retained administrative source comparisons and GSHHG-based physical support records are source-relative geometric observations only; source, physical, territorial and causal authority remain unapproved or unknown.", "status": "unresolved", "source_ids": ["gb:FJI:ADM2", "gb:IDN:ADM2", "gb:PNG:ADM3", "gb:SLB:ADM1", "gb:VUT:ADM1", "gshhg-2.3.7-original-binary"]},
            {"text": "All 15 Makira overlaps inherit the unresolved #1457 assessment; four overlap the 29 priority IDs, leaving 25 priority components without that inherited assessment; no new imagery/source fitness is asserted.", "status": "unresolved", "source_ids": ["makira-prior-assessment-1457"]}],
        "stages": {"research": "complete", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": ["python3 research/geography/melanesia-full-batch-327-20261009/assemble.py --work-index .cache/global-gap-work-index-20261009/geo4-next-full-batch-327.json",
                     "Assembly validates recorded whole-byte and row-hash relationships, extracts retained features/rows, and performs no new geometry operation.",
                     "No browser/provider calls, native evaluation, production writes, or source/GIS replay were run."]}
    write_json(out / "evidence-quality.json", manifest)


if __name__ == "__main__":
    main()
