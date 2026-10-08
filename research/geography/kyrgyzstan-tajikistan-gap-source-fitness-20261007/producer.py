#!/usr/bin/env python3
"""Pinned, bounded source-relative overlays for two complete KGT families."""
from __future__ import annotations
import argparse
import atexit
import gzip
import hashlib
import io
import importlib.util
import json
import os
import pathlib
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
ROOT = pathlib.Path(__file__).resolve().parent
OWNED = "research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/"
EXECUTION_PINS = OWNED + "execution-pins.json"
INPUT_PINS = OWNED + "inputs/input-pins.json"
RUNTIME_MANIFEST = OWNED + "inputs/runtime/runtime-manifest.json"
RUNTIME_BUNDLE_REL = "inputs/runtime/runtime-bundle.tar.gz"
CONTEXT = OWNED + "inputs/context/selected-routing-and-operational-context.json"
MAX_INPUT_BYTES = 256 * 1024 * 1024
MAX_OUTPUT_BYTES = 12 * 1024 * 1024
MAX_RSS_BYTES = 768 * 1024 * 1024
MAX_SECONDS = 1200
HOST_MEMORY_RESERVE_BYTES = 512 * 1024 * 1024
EXTERNAL_RSS_STOP_BYTES = 640 * 1024 * 1024
EXTERNAL_RSS_MARGIN_BYTES = MAX_RSS_BYTES - EXTERNAL_RSS_STOP_BYTES
EXTERNAL_RSS_SAMPLE_SECONDS = 0.1
SUPERVISION_ENV = "WORLDATLAS_SOURCE_FITNESS_SUPERVISOR"
SUPERVISION_ENV_VALUE = "process-tree-rss-v1"
WORKTREE_CAP_BYTES = 1024 * 1024 * 1024
SCRATCH_CAP_BYTES = 512 * 1024 * 1024
FINAL_EVIDENCE_CAP_BYTES = 512 * 1024 * 1024
DISK_RESERVATION_BYTES = WORKTREE_CAP_BYTES + SCRATCH_CAP_BYTES + FINAL_EVIDENCE_CAP_BYTES
MAX_CONTROL_OUTPUT_BYTES = 1 * 1024 * 1024
MAX_EXTERNAL_SUPERVISION_BYTES = 6 * 1024 * 1024 + 36 * 1024
RUNTIME_BUNDLE = OWNED + "inputs/runtime/runtime-bundle.tar.gz"
_RUNTIME_TEMP_DIR = None
CONTACTS = {
    "gb:KGZ:ADM2:92254566B28866404519709",
    "gb:KGZ:ADM2:92254566B65149347501284",
    "gb:KGZ:ADM2:92254566B65536554507768",
    "gb:TJK:ADM2:16282066B17537121350265",
    "gb:TJK:ADM2:16282066B25952413622692",
    "gb:TJK:ADM2:16282066B48594859138803",
    "gb:TJK:ADM2:16282066B4928854450407",
    "gb:TJK:ADM2:16282066B70669453487294",
    "gb:TJK:ADM2:16282066B88100265425771",
}
FAMILIES = {
    "gap-source-batch:74be953b1fb31c15200742da",
    "gap-source-batch:65911e15791d12ebb2ccacf5",
}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def bootstrap(repo, commit, phase=None):
    """Bootstrap only from a complete immutable Git commit and bound helper bytes."""
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise ValueError("exact immutable baseline commit required")
    raw_config = git(repo, "show", f"{commit}:{EXECUTION_PINS}")
    config = json.loads(raw_config)
    all_files = list(config["files"])
    if phase is None or phase == "full":
        files = all_files
    else:
        phase_paths = config.get("phase_paths", {}).get(phase)
        if not isinstance(phase_paths, list) or not phase_paths:
            raise ValueError(f"Unknown or empty immutable input phase: {phase}")
        required = set(phase_paths) | set(config["code_files"].values()) | {
            INPUT_PINS, "scripts/evidence/immutable.py", "scripts/evidence/contracts.py"
        }
        available = {x["path"] for x in all_files}
        if not required.issubset(available):
            raise ValueError(f"Phase pin inventory is incomplete: {sorted(required - available)}")
        files = [x for x in all_files if x["path"] in required]
    config_path = pathlib.Path(repo) / EXECUTION_PINS
    config_descriptor = {"path": EXECUTION_PINS, "bytes": len(raw_config),
                         "sha256": sha(raw_config), "hash_kind": "file-bytes"}
    files = [x for x in files if x["path"] != EXECUTION_PINS] + [config_descriptor]
    helper_path = "scripts/evidence/immutable.py"
    helper_bytes = git(repo, "show", f"{commit}:{helper_path}")
    expected_helper = next(x for x in files if x["path"] == helper_path)
    if len(helper_bytes) != expected_helper["bytes"] or sha(helper_bytes) != expected_helper["sha256"]:
        raise ValueError("pinned immutable helper differs")
    namespace = {"__name__": "_verified_bootstrap_immutable", "__file__": helper_path}
    exec(compile(helper_bytes, helper_path, "exec"), namespace)
    bootstrap_baseline = namespace["Baseline"](repo, commit, files)
    modules = bootstrap_baseline.load_modules({
        "evidence.immutable": helper_path,
        "evidence.contracts": "scripts/evidence/contracts.py",
        "jrc_support": config["code_files"]["jrc_support"],
    })
    evidence = modules["evidence.immutable"]
    baseline = evidence.Baseline(repo, commit, files)
    if baseline.pinned_bytes(EXECUTION_PINS) != raw_config:
        raise ValueError("execution pin file drift")
    for name, path in config["code_files"].items():
        expected = next(x for x in files if x["path"] == path)
        raw = baseline.pinned_bytes(path)
        actual = (pathlib.Path(repo) / path).read_bytes()
        if len(raw) != expected["bytes"] or sha(raw) != expected["sha256"] or actual != raw:
            raise ValueError(f"executed candidate code differs from pinned commit: {name}")
    return baseline, evidence, modules["evidence.contracts"], config


def load_spatial_runtime(baseline, config):
    """Verify captured runtime bodies, then import Shapely from the pinned copy."""
    raw = baseline.pinned_bytes(RUNTIME_MANIFEST)
    manifest = json.loads(raw)
    if manifest.get("status") != "captured" or manifest.get("projection_runtime", {}).get("used") is not False:
        raise ValueError("Captured spatial runtime manifest is missing or unexpected")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Runtime body inventory is empty")
    bundle = manifest.get("bundle")
    if (not isinstance(bundle, dict) or bundle.get("path") != RUNTIME_BUNDLE_REL or
            not isinstance(bundle.get("bytes"), int) or
            not isinstance(bundle.get("sha256"), str)):
        raise ValueError("Runtime bundle descriptor is missing or malformed")
    bundle_raw = baseline.pinned_bytes(RUNTIME_BUNDLE)
    if len(bundle_raw) != bundle["bytes"] or sha(bundle_raw) != bundle["sha256"]:
        raise ValueError("Captured runtime bundle differs from its manifest descriptor")
    by_path = {}
    for item in files:
        path = item.get("path")
        if not isinstance(path, str) or path in by_path:
            raise ValueError("Runtime body inventory has missing or duplicate paths")
        relative = pathlib.PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "python":
            raise ValueError(f"Unsafe runtime bundle member path: {path}")
        if not isinstance(item.get("bytes"), int) or not isinstance(item.get("sha256"), str):
            raise ValueError(f"Runtime file descriptor is malformed: {path}")
        by_path[path] = item
    global _RUNTIME_TEMP_DIR
    runtime_root = pathlib.Path(tempfile.mkdtemp(prefix="worldatlas-kgt-runtime-"))
    _RUNTIME_TEMP_DIR = runtime_root
    atexit.register(shutil.rmtree, runtime_root, True)
    try:
        with tarfile.open(fileobj=io.BytesIO(bundle_raw), mode="r:gz") as archive:
            members = archive.getmembers()
            member_paths = [member.name for member in members]
            if len(member_paths) != len(set(member_paths)) or set(member_paths) != set(by_path):
                raise ValueError("Runtime bundle members do not exactly match the manifest inventory")
            for member in members:
                if not member.isfile():
                    raise ValueError(f"Runtime bundle contains a non-regular member: {member.name}")
            for path, item in by_path.items():
                member = archive.getmember(path)
                if member.size != item["bytes"] or member.size > 32 * 1024 * 1024:
                    raise ValueError(f"Runtime bundle member size differs from its manifest: {path}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"Runtime bundle member cannot be read: {path}")
                captured = stream.read(32 * 1024 * 1024 + 1)
                if len(captured) != item["bytes"] or sha(captured) != item["sha256"]:
                    raise ValueError(f"Runtime body differs from its per-file manifest: {path}")
                baseline.admit("runtime-expanded:" + path, len(captured))
                source_path = pathlib.Path(item["source_path"])
                try:
                    installed = source_path.read_bytes()
                except OSError as exc:
                    raise ValueError(f"Installed runtime body is unavailable: {source_path}") from exc
                if installed != captured:
                    raise ValueError(f"Installed runtime body differs from captured bytes: {source_path}")
                destination = runtime_root.joinpath(*pathlib.PurePosixPath(path).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as target:
                    target.write(captured)
                destination.chmod(member.mode & 0o777)
    except Exception:
        shutil.rmtree(runtime_root, ignore_errors=True)
        _RUNTIME_TEMP_DIR = None
        raise
    executable = pathlib.Path(sys.executable).resolve()
    if str(executable) != manifest["python"]["executable_realpath"]:
        raise ValueError("Running interpreter differs from the captured executable")
    if sys.version != manifest["python"]["version"]:
        raise ValueError("Running Python version/build differs from captured runtime")
    package_parent = runtime_root / "python/lib/python3.12/site-packages"
    sys.path.insert(0, str(package_parent))
    import shapely
    from shapely.geometry import shape
    package_file = pathlib.Path(shapely.__file__).resolve()
    if not package_file.is_relative_to(package_parent.resolve()):
        raise ValueError("Shapely was imported from outside the captured runtime")
    if (shapely.__version__ != manifest["spatial_runtime"]["shapely_version"] or
            shapely.geos_version_string != manifest["spatial_runtime"]["geos_version"]):
        raise ValueError("Loaded Shapely/GEOS differs from captured runtime metadata")
    return shapely, shape, manifest, sha(raw)


def verify_input_manifest(baseline, config, *, allow_unpinned=False):
    raw = baseline.pinned_bytes(INPUT_PINS)
    pins = json.loads(raw)
    staged = {OWNED + x["path"]: x for x in pins["files"]}
    if len(staged) != len(pins["files"]):
        raise ValueError("Whole-file input inventory contains duplicate paths")
    for path, entry in staged.items():
        pin = baseline.pins.get(path)
        if pin is None and allow_unpinned:
            continue
        if not pin or pin["bytes"] != entry["bytes"] or pin["sha256"] != entry["sha256"]:
            raise ValueError(f"staged input manifest does not match baseline: {path}")
    subject_ids = set(config["subject_ids"])
    if subject_ids != set(json.loads(baseline.pinned_bytes(OWNED + "inputs/subject-inventory.json"))["subject_ids"]):
        raise ValueError("scope inventory differs from execution pin")
    registry = json.loads(baseline.pinned_bytes(OWNED + "scope/subject-registry.geojson"))
    features = registry.get("features") if registry.get("type") == "FeatureCollection" else None
    if not isinstance(features, list) or len(features) != len(subject_ids):
        raise ValueError("Exact scope registry is incomplete")
    registry_ids = []
    for feature in features:
        identity = feature.get("id")
        props = feature.get("properties", {})
        if (not isinstance(identity, str) or feature.get("geometry") is not None or
                props.get("id") != identity or props.get("subject_id") != identity or
                props.get("source_value") != identity or props.get("source_property") != "subject_id"):
            raise ValueError("Scope registry identity-only record is malformed")
        registry_ids.append(identity)
    if len(set(registry_ids)) != len(registry_ids) or set(registry_ids) != subject_ids:
        raise ValueError("Scope registry does not match exact 26-subject inventory")
    runtime_kinds = {"runtime-bundle", "runtime-manifest"}
    if sum(item["kind"] not in runtime_kinds for item in pins["files"]) != config["source_file_count"]:
        raise ValueError("Unexpected original source-evidence inventory size")
    runtime_file_count = sum(item["kind"] in runtime_kinds for item in pins["files"])
    if runtime_file_count != config["runtime_file_count"]:
        raise ValueError("Runtime inventory size differs from the exact execution pin")
    return pins, staged


def decode_pinned(baseline, staged, path):
    item = staged[path]
    raw = baseline.pinned_bytes(path)
    decoded = gzip.decompress(raw)
    baseline.admit(path + ":decoded", len(decoded))
    if len(decoded) != item["decoded_bytes"] or sha(decoded) != item["decoded_sha256"]:
        raise ValueError(f"decoded whole-file pin mismatch: {path}")
    return decoded


def validate_pointset_route_hashes(pointsets_by_id, routes, contract_helpers):
    """Bind complete retained pointsets to independently routed feature hashes."""
    ids = sorted(routes)
    point_hash_rows = [
        {"id": cid, "feature_sha256": sha(canonical(feature)),
         "geometry_sha256": sha(canonical(feature["geometry"]))}
        for cid, feature in pointsets_by_id.items()
    ]
    route_hash_rows = [
        {"id": cid, "feature_sha256": row["current_feature_sha256"],
         "geometry_sha256": row["current_geometry_sha256"]}
        for cid, row in routes.items()
    ]
    contract_helpers.join_rows(
        point_hash_rows, route_hash_rows,
        {"feature_sha256": "feature_sha256", "geometry_sha256": "geometry_sha256"},
    )
    return ids


def load_inputs(baseline, contract_helpers, config, *, require_custody=True,
                inventory_preverified=False):
    pins, staged = verify_input_manifest(
        baseline, config, allow_unpinned=require_custody or inventory_preverified)
    input_manifest_sha = sha(baseline.pinned_bytes(INPUT_PINS))
    context = json.loads(baseline.pinned_bytes(CONTEXT))
    if require_custody:
        custody_vintage = config.get("custody_vintage")
        if not isinstance(custody_vintage, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", custody_vintage):
            raise ValueError("Exact custody-preflight vintage is missing from execution pins")
        custody_receipt_path = OWNED + f"vintages/{custody_vintage}/custody-preflight.json"
        custody_publication_path = OWNED + f"vintages/{custody_vintage}/publication.json"
        custody_raw = baseline.pinned_bytes(custody_receipt_path)
        custody = json.loads(custody_raw)
        if custody.get("status") != "pass" or custody.get("context_sha256") != sha(canonical(context)):
            raise ValueError("whole-input custody preflight is absent or bound to different context")
        if (custody.get("input_pins_sha256") != input_manifest_sha or
                custody.get("input_file_count") != len(pins["files"]) or
                custody.get("source_file_count") != config["source_file_count"] or
                custody.get("runtime_artifact_count") != config["runtime_file_count"]):
            raise ValueError("whole-input custody preflight is bound to different whole-file inventory")
        if (custody.get("baseline_commit") != config.get("custody_preflight_commit") or
                custody.get("execution_pins_sha256") != config.get("custody_preflight_execution_pins_sha256")):
            raise ValueError("whole-input custody preflight is bound to different code/input freeze")
        code_bindings = custody.get("code_bindings", {})
        for name, path in config["code_files"].items():
            binding = code_bindings.get(name)
            pin = baseline.pins.get(path)
            if (not isinstance(binding, dict) or not pin or binding.get("path") != path or
                    binding.get("bytes") != pin["bytes"] or binding.get("sha256") != pin["sha256"]):
                raise ValueError(f"Preflight code binding differs from the exact execution code: {name}")
        publication = json.loads(baseline.pinned_bytes(custody_publication_path))
        outputs = publication.get("outputs")
        if publication.get("status") != "complete" or not isinstance(outputs, list):
            raise ValueError("whole-input custody preflight publication is incomplete")
        records = {x.get("path"): x for x in outputs}
        receipt_path = custody_receipt_path
        if (len(records) != 2 or receipt_path not in records or
                records[receipt_path].get("bytes") != len(custody_raw) or
                records[receipt_path].get("sha256") != sha(custody_raw)):
            raise ValueError("Custody-preflight publication does not bind its receipt")
    routes = context["routes"]
    physical = context["physical_records"]
    family_rows = list(context["selected_families_source_rows"].values())
    ids = sorted(routes)
    expected_ids = sorted(config["component_ids"])
    if ids != expected_ids or set(physical) != set(ids):
        raise ValueError("exact 15-component scope mismatch")
    route_rows = [dict(row, id=cid) for cid, row in routes.items()]
    route_rows = contract_helpers.exact_rows(route_rows, ids)
    physical_rows = [dict(row, id=cid) for cid, row in physical.items()]
    physical_rows = contract_helpers.exact_rows(physical_rows, ids)
    families = contract_helpers.exact_rows(family_rows, sorted(FAMILIES))
    batch = context["operational_batch"]
    if (len(batch["complete_fine_family_ids"]) != 85 or
            len(batch["complete_component_ids"]) != 441 or
            len(set(batch["complete_component_ids"])) != 441):
        raise ValueError("complete 85-family / 441-component batch context mismatch")
    for family_id, row in families.items():
        members = row["complete_component_ids"]
        if len(members) not in (3, 12) or any(routes[cid]["family"] != family_id for cid in members):
            raise ValueError(f"selected family membership mismatch: {family_id}")
    if set(ids) != {cid for row in families.values() for cid in row["complete_component_ids"]}:
        raise ValueError("selected family rows do not reconcile all 15 components")

    pointsets = []
    for item in pins["files"]:
        if item["kind"] != "complete-component-pointset-part":
            continue
        doc = json.loads(decode_pinned(baseline, staged, OWNED + item["path"]))
        pointsets.extend(f for f in doc.get("features", []) if f.get("id") in set(ids))
    pointsets_by_id = contract_helpers.exact_rows(pointsets, ids)
    for cid, feature in pointsets_by_id.items():
        if feature.get("type") != "Feature" or feature.get("geometry", {}).get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"complete component feature is malformed: {cid}")
    validate_pointset_route_hashes(pointsets_by_id, routes, contract_helpers)
    physical_hash_rows = [{"id": cid, "row_sha256": sha(canonical(row))} for cid, row in physical.items()]
    route_physical_rows = [{"id": cid, "row_sha256": routes[cid]["whole_physical_row_sha256"]} for cid in ids]
    contract_helpers.join_rows(physical_hash_rows, route_physical_rows, {"row_sha256": "row_sha256"})

    catalogue = json.loads(baseline.pinned_bytes(OWNED + "inputs/sources/catalogue.json"))
    metadata = json.loads(baseline.pinned_bytes(OWNED + "inputs/sources/administrative-sources.json"))
    attribution = json.loads(baseline.pinned_bytes(OWNED + "inputs/sources/individual-source-attribution.json"))
    products = {}
    for source_id, filename, expected_count in (
        ("gb:KGZ:ADM2", "gb-KGZ-ADM2-000.bin.gz", 41),
        ("gb:TJK:ADM2", "gb-TJK-ADM2-000.bin.gz", 58),
    ):
        path = OWNED + "inputs/sources/" + filename
        doc = json.loads(decode_pinned(baseline, staged, path))
        features = doc["features"]
        if len(features) != expected_count:
            raise ValueError(f"complete source feature count differs: {source_id}")
        indexed = [{"id": f.get("properties", {}).get("shapeID"), "feature": f} for f in features]
        by_shape = contract_helpers.exact_rows(indexed, [r["id"] for r in indexed])
        products[source_id] = {"features": features, "by_shape": by_shape}
    contact_features = {}
    for contact in sorted(CONTACTS):
        source_id, shape_id = contact.rsplit(":", 1)
        feature = products[source_id]["by_shape"].get(shape_id, {}).get("feature")
        if feature is None or feature["properties"]["shapeID"] != shape_id:
            raise ValueError(f"complete full-shapeID source contact absent: {contact}")
        contact_features[contact] = feature
    family_contacts = {x for row in families.values() for x in row["original_fine_family"]["contact_ids"]}
    if family_contacts != CONTACTS:
        raise ValueError("selected complete family contacts differ from exact issue scope")
    jrc_summary = modules_for_jrc(baseline, config, pointsets_by_id)
    return pins, context, pointsets_by_id, products, contact_features, catalogue, metadata, attribution, jrc_summary


def modules_for_jrc(baseline, config, pointsets_by_id):
    """Load the pinned metadata-only JRC validator from this immutable baseline."""
    path = config["code_files"]["jrc_support"]
    raw = baseline.pinned_bytes(path)
    namespace = {"__name__": "_pinned_jrc_support", "__file__": path}
    exec(compile(raw, path, "exec"), namespace)
    return namespace["load_and_validate"](baseline, config,
                                           config["component_ids"], config["contact_ids"])


def source_product_staged_descriptors(input_pins, catalogue):
    """Return only exact, ordered whole-product descriptors after origin checks."""
    expected = [
        ("gb:KGZ:ADM2", "inputs/sources/gb-KGZ-ADM2-000.bin.gz"),
        ("gb:TJK:ADM2", "inputs/sources/gb-TJK-ADM2-000.bin.gz"),
    ]
    files = input_pins.get("files") if isinstance(input_pins, dict) else None
    if not isinstance(files, list):
        raise ValueError("Source-product context requires the pinned whole-file inventory")
    paths = [item.get("path") for item in files if isinstance(item, dict)]
    if len(paths) != len(files) or len(paths) != len(set(paths)):
        raise ValueError("Source-product inventory contains malformed or duplicate paths")
    expected_names = {pathlib.PurePosixPath(path).name for _, path in expected}
    candidates = [
        item for item in files
        if item.get("kind") == "whole-simplified-source-product" or
        pathlib.PurePosixPath(str(item.get("path", ""))).name in expected_names
    ]
    if [item.get("path") for item in candidates] != [path for _, path in expected]:
        raise ValueError("Source-product descriptors must be complete, exact-path and in declared order")
    catalogue_by_key = {item.get("key"): item for item in catalogue.get("products", [])}
    source_commit = input_pins.get("source_corpus_commit")
    result = {}
    for source_id, relative_path in expected:
        item = candidates[0] if source_id == "gb:KGZ:ADM2" else candidates[1]
        product = catalogue_by_key.get(source_id)
        parts = product.get("parts") if isinstance(product, dict) else None
        if not isinstance(parts, list) or len(parts) != 1:
            raise ValueError(f"Catalogue source product must have exactly one retained part: {source_id}")
        part = parts[0]
        if (item.get("path") != relative_path or
                item.get("kind") != "whole-simplified-source-product" or
                item.get("source_commit") != source_commit or
                item.get("source_path") != part.get("path") or
                item.get("bytes") != part.get("bytes") or
                item.get("sha256") != part.get("sha256") or
                item.get("decoded_bytes") != part.get("uncompressed_bytes") or
                item.get("decoded_sha256") != part.get("uncompressed_sha256")):
            raise ValueError(f"Source-product descriptor differs from its exact retained catalogue origin: {source_id}")
        result[OWNED + relative_path] = item
    return result


def output_product_context(baseline, products, catalogue, metadata, attribution, input_pins):
    staged = source_product_staged_descriptors(input_pins, catalogue)
    output = {}
    for source_id, product in products.items():
        source = next(x for x in catalogue["products"] if x["key"] == source_id)
        citation = next(x for x in attribution["individual_source_citations"] if x["id"] == source_id)
        registry = metadata[source_id]
        filename = "gb-KGZ-ADM2-000.bin.gz" if "KGZ" in source_id else "gb-TJK-ADM2-000.bin.gz"
        path = OWNED + "inputs/sources/" + filename
        item = staged[path]
        output[source_id] = {
            "input_path": path, "encoded_bytes": item["bytes"], "encoded_sha256": item["sha256"],
            "original_bytes": source["original_bytes"], "original_sha256": source["original_sha256"],
            "feature_count": len(product["features"]), "recorded_consumed_url": source["recorded_consumed_url"],
            "source_represented_year_claim": source["source_represented_year_claim"],
            "recorded_license": source["recorded_license"],
            "complete_original_metadata_row": registry,
            "individual_source_citation_and_terms_claim": citation,
            "crs_datum_precision_accuracy": "Retained catalogue/metadata do not establish candidate-scale CRS datum, registration accuracy, coordinate precision, or effective date; source coordinates are consumed as literal GeoJSON longitude/latitude values.",
        }
    return output


def _directory_bytes(path):
    total = 0
    for root, directories, files in os.walk(path, followlinks=False):
        for name in directories + files:
            target = pathlib.Path(root) / name
            if target.is_symlink():
                raise ValueError(f"Symlink in admitted storage tree: {target}")
            if target.is_file():
                total += target.stat().st_size
    return total


def fixed_memory_snapshot():
    """Return exact macOS VM page counts; inactive/speculative pages are estimates, not guarantees."""
    snapshot_started = time.monotonic()
    physical_raw = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
    if not physical_raw.isdigit():
        raise ValueError("Could not read the physical-memory byte count")
    vm = subprocess.check_output(["vm_stat"], text=True, stderr=subprocess.STDOUT)
    page_match = re.search(r"page size of ([0-9]+) bytes", vm)
    if page_match is None:
        raise ValueError("Could not read the VM page size")
    page_size = int(page_match.group(1))
    counts = {}
    for label in ("Pages free", "Pages inactive", "Pages speculative"):
        match = re.search(r"^" + re.escape(label) + r":\s*([0-9,]+)", vm, re.MULTILINE)
        if match is None:
            raise ValueError(f"Could not read the VM statistic: {label}")
        counts[label] = int(match.group(1).replace(",", ""))
    free_bytes = counts["Pages free"] * page_size
    candidate_bytes = sum(counts.values()) * page_size
    return {
        "physical_memory_bytes": int(physical_raw),
        "snapshot_elapsed_seconds": time.monotonic() - snapshot_started,
        "page_size_bytes": page_size,
        "page_counts": {key: counts[key] for key in sorted(counts)},
        "free_page_bytes": free_bytes,
        "free_inactive_speculative_candidate_bytes": candidate_bytes,
        "candidate_includes_reclaimable_pages": True,
        "candidate_is_guaranteed_available_memory": False,
    }


def admit_run_capacity(repo, baseline, vintage, runtime_manifest, coordinated_window_id):
    """Admit RAM, disk and every output destination before constructing geometry."""
    if not isinstance(coordinated_window_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", coordinated_window_id):
        raise ValueError("An explicit coordinator-issued GIS memory-window ID is required")
    memory = fixed_memory_snapshot()
    required_candidate_bytes = MAX_RSS_BYTES + HOST_MEMORY_RESERVE_BYTES
    candidate_bytes = memory["free_inactive_speculative_candidate_bytes"]
    if candidate_bytes < required_candidate_bytes:
        raise ValueError("Fixed-byte VM page-supply estimate is below the process cap plus host reserve")
    disk_free = shutil.disk_usage(repo).free
    if disk_free < DISK_RESERVATION_BYTES:
        raise ValueError("Free disk space is below the admitted worktree/scratch/evidence reserves")
    worktree_bytes = _directory_bytes(pathlib.Path(repo) / OWNED)
    output_reserve = (2 * MAX_OUTPUT_BYTES + 2 * MAX_CONTROL_OUTPUT_BYTES +
                      2 * MAX_EXTERNAL_SUPERVISION_BYTES + 1024 * 1024)
    if worktree_bytes + output_reserve > WORKTREE_CAP_BYTES:
        raise ValueError("Packet plus maximum run/control outputs exceeds its worktree cap")
    evidence_bytes = _directory_bytes(pathlib.Path(repo) / OWNED / "vintages")
    if evidence_bytes + output_reserve > FINAL_EVIDENCE_CAP_BYTES:
        raise ValueError("Existing and reserved outputs exceed the final evidence cap")
    runtime_scratch = int(runtime_manifest["captured_bytes"])
    scratch_reserve = runtime_scratch + 128 * 1024 * 1024
    if scratch_reserve > SCRATCH_CAP_BYTES:
        raise ValueError("Captured runtime plus the scratch reserve exceeds the scratch cap")
    phase_bytes = sum(baseline.consumed.values())
    if phase_bytes + MAX_OUTPUT_BYTES + MAX_EXTERNAL_SUPERVISION_BYTES + 4096 > baseline.max_phase_bytes:
        raise ValueError("Complete input/runtime phase leaves insufficient room for the admitted run outputs")
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss) if sys.platform == "darwin" else int(rss * 1024)
    if rss_bytes > MAX_RSS_BYTES:
        raise ValueError("Pre-GIS process RSS already exceeds its execution ceiling")
    return {
        "coordinated_window_id": coordinated_window_id,
        "fixed_memory_snapshot": memory,
        "estimated_page_supply_required_bytes": required_candidate_bytes,
        "host_memory_reserve_bytes": HOST_MEMORY_RESERVE_BYTES,
        "pre_geometry_max_rss_bytes": rss_bytes,
        "process_rss_limit_bytes": MAX_RSS_BYTES,
        "external_process_tree_rss_stop_bytes": EXTERNAL_RSS_STOP_BYTES,
        "external_process_tree_rss_margin_bytes": EXTERNAL_RSS_MARGIN_BYTES,
        "external_process_tree_rss_sample_seconds": EXTERNAL_RSS_SAMPLE_SECONDS,
        "phase_consumed_bytes_before_geometry": phase_bytes,
        "phase_byte_limit": baseline.max_phase_bytes,
        "output_bytes_per_run_limit": MAX_OUTPUT_BYTES,
        "external_supervision_bytes_per_run_limit": MAX_EXTERNAL_SUPERVISION_BYTES,
        "two_run_output_reserve_bytes": 2 * MAX_OUTPUT_BYTES,
        "two_run_supervision_reserve_bytes": 2 * MAX_EXTERNAL_SUPERVISION_BYTES,
        "two_control_output_reserve_bytes": 2 * MAX_CONTROL_OUTPUT_BYTES,
        "current_packet_bytes": worktree_bytes,
        "projected_worktree_bytes_with_outputs": worktree_bytes + output_reserve,
        "worktree_cap_bytes": WORKTREE_CAP_BYTES,
        "current_evidence_bytes": evidence_bytes,
        "projected_evidence_bytes_with_outputs": evidence_bytes + output_reserve,
        "final_evidence_cap_bytes": FINAL_EVIDENCE_CAP_BYTES,
        "runtime_scratch_bytes": runtime_scratch,
        "projected_scratch_bytes": scratch_reserve,
        "scratch_cap_bytes": SCRATCH_CAP_BYTES,
        "free_disk_bytes": disk_free,
        "disk_reservation_bytes": DISK_RESERVATION_BYTES,
        "destination_vintages": [
            "source-fitness-run-01", "source-fitness-run-02",
            "source-fitness-controls-01", "source-fitness-controls-02",
            "process-supervision/source-fitness-run-01",
            "process-supervision/source-fitness-run-02",
        ],
        "status": "admitted",
    }


def run(repo, commit, vintage, coordinated_window_id):
    if os.environ.get(SUPERVISION_ENV) != SUPERVISION_ENV_VALUE:
        raise ValueError("Source overlays must run under the pinned external RSS supervisor")
    started = time.monotonic()
    baseline, evidence, contract_helpers, config = bootstrap(repo, commit, phase="overlay")
    if sum(baseline.consumed.values()) > MAX_INPUT_BYTES:
        raise ValueError("Pinned raw input/runtime bytes exceed the admitted input ceiling")
    run = evidence.NewVintage(baseline, OWNED, vintage,
                              ["source-fitness.json", "run-summary.json"])
    shapely, shape, runtime_manifest, runtime_manifest_sha256 = load_spatial_runtime(baseline, config)
    loaded = load_inputs(baseline, contract_helpers, config)
    pins, context, pointsets, products, contacts, catalogue, metadata, attribution, jrc_summary = loaded
    admission = admit_run_capacity(repo, baseline, vintage, runtime_manifest,
                                   coordinated_window_id)
    component_geoms = {cid: shape(feature["geometry"]) for cid, feature in pointsets.items()}
    source_geoms = {source_id: [(f"{source_id}:{f['properties']['shapeID']}", f, shape(f["geometry"]))
                                for f in product["features"]]
                    for source_id, product in products.items()}
    rows = []
    for cid in sorted(component_geoms):
        component = component_geoms[cid]
        if not component.is_valid:
            raise ValueError(f"unchanged original component geometry is invalid: {cid}")
        for source_id in sorted(source_geoms):
            for feature_id, feature, source_geom in source_geoms[source_id]:
                if not source_geom.is_valid:
                    rows.append({"component_id": cid, "source_id": source_id,
                                 "source_feature_id": feature_id, "source_feature_sha256": sha(canonical(feature)),
                                 "source_geometry_valid": False, "overlay_status": "unavailable-invalid-original-source",
                                 "intersects": None, "source_feature_covers_component": None,
                                 "component_covers_source_feature": None,
                                 "intersection_area_coordinate_units_squared": None,
                                 "intersection_length_coordinate_units": None,
                                 "positive_area_intersection": None})
                    continue
                inter = component.intersection(source_geom)
                area, length = float(inter.area), float(inter.length)
                row = {
                    "component_id": cid,
                    "component_geometry_sha256": context["routes"][cid]["current_geometry_sha256"],
                    "source_id": source_id, "source_feature_id": feature_id,
                    "source_shapeID": feature["properties"]["shapeID"],
                    "source_feature_sha256": sha(canonical(feature)),
                    "source_geometry_sha256": sha(canonical(feature["geometry"])),
                    "source_geometry_valid": True, "overlay_status": "checked",
                    "intersects": bool(component.intersects(source_geom)),
                    "component_covers_source_feature": bool(component.covers(source_geom)),
                    "source_feature_covers_component": bool(source_geom.covers(component)),
                    "intersection_empty": bool(inter.is_empty),
                    "intersection_geometry_type": inter.geom_type,
                    "intersection_area_coordinate_units_squared": area,
                    "intersection_length_coordinate_units": length,
                    "positive_area_intersection": bool(area > 0),
                    "relation_domain": "literal original GeoJSON longitude/latitude; no projection or coordinate change",
                }
                rows.append(row)
    rows.sort(key=lambda r: (r["component_id"], r["source_id"], r["source_feature_id"]))
    component_ids = sorted(component_geoms)
    product_context = output_product_context(baseline, products, catalogue, metadata, attribution,
                                             pins)
    result = {
        "version": 1,
        "scope": {"families": sorted(FAMILIES), "component_ids": component_ids,
                  "contact_ids": sorted(CONTACTS), "operational_batch_families": 85,
                  "operational_batch_components": 441},
        "source_products": product_context,
        "jrc_support": jrc_summary,
        "complete_contact_feature_sha256": {c: sha(canonical(f)) for c, f in sorted(contacts.items())},
        "complete_contact_features": contacts,
        "selected_family_rows": context["selected_families_source_rows"],
        "complete_operational_batch_row": context["operational_batch"],
        "component_routing_rows": context["routes"],
        "component_physical_source_rows": context["physical_records"],
        "component_source_fit_rows": rows,
        "row_count": len(rows),
        "intersecting_pair_count": sum(r.get("intersects") is True for r in rows),
        "positive_area_pair_count": sum(r.get("positive_area_intersection") is True for r in rows),
        "point_or_line_only_pair_count": sum(r.get("intersects") is True and r.get("intersection_area_coordinate_units_squared") == 0 for r in rows),
        "limits": [
            "Overlay area and length are in literal coordinate units; they are not square metres or geodesic measurements.",
            "Positive area, intersection, and coverage are source-product relations only; none establishes physical land, rightful administrative assignment, or processing cause.",
            "Both inputs are historical simplified products; represented years and license statements are preserved metadata claims, not verified effective dates or territorial authority.",
            "Candidate-scale registration accuracy, source precision, physical water/shoreline truth, source lineage/cause, rights, authority, and ownership remain unknown.",
            "No complete official candidate-scale boundary/water geometry with dated accuracy and reusable original bytes was available for direct comparison in this bounded packet.",
            "No candidate clipping, geometry repair, buffering, snapping, simplification, or mutation is performed.",
        ],
        "runtime": {"python": sys.version, "shapely": shapely.__version__,
                    "geos": shapely.geos_version_string,
                    "captured_runtime_manifest_sha256": runtime_manifest_sha256,
                    "captured_runtime_bytes": runtime_manifest["captured_bytes"],
                    "captured_runtime_file_count": runtime_manifest["captured_file_count"]},
        "precalculation_admission": admission,
        "helper_versions": {"immutable": evidence.VERSION, "record_contracts": "pinned scripts/evidence/contracts.py"},
        "execution_pins_sha256": sha(baseline.pinned_bytes(EXECUTION_PINS)),
        "input_pins_sha256": sha(baseline.pinned_bytes(INPUT_PINS)),
        "custody_preflight_sha256": sha(baseline.pinned_bytes(
            OWNED + f"vintages/{config['custody_vintage']}/custody-preflight.json")),
    }
    contract_helpers.finite_metrics({"row_count": result["row_count"],
                                     "positive_area_pair_count": result["positive_area_pair_count"]},
                                    ["row_count", "positive_area_pair_count"])
    elapsed = time.monotonic() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss) if sys.platform == "darwin" else int(rss * 1024)
    output_files = {
        "source-fitness.json": canonical(result),
        "run-summary.json": canonical({"status": "complete", "elapsed_seconds": elapsed,
            "prepublication_ru_maxrss_bytes": rss_bytes, "input_bytes": sum(baseline.consumed.values()),
            "row_count": len(rows), "intersecting_pair_count": result["intersecting_pair_count"],
            "source_fitness_sha256": sha(canonical(result)),
        "jrc_support": jrc_summary,
        "precalculation_admission": admission}),
    }
    if elapsed > MAX_SECONDS or rss_bytes > MAX_RSS_BYTES or sum(map(len, output_files.values())) > MAX_OUTPUT_BYTES:
        raise ValueError("admitted run resource bound exceeded before publication")
    published = run.publish_bytes(output_files)
    print(json.dumps({"status": "complete", "vintage": vintage,
                      "coordinated_window_id": coordinated_window_id, "publication": published,
                      "elapsed_seconds": elapsed, "prepublication_ru_maxrss_bytes": rss_bytes,
                      "row_count": len(rows), "intersecting_pair_count": result["intersecting_pair_count"]}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--vintage", required=True)
    parser.add_argument("--coordinated-window-id", required=True)
    args = parser.parse_args()
    run(pathlib.Path(args.repo).resolve(), args.baseline_commit, args.vintage,
        args.coordinated_window_id)


if __name__ == "__main__":
    main()
