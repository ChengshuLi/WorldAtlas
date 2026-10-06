#!/usr/bin/env python3
"""Reproduce #420's historical crosswalk from verified immutable Git inputs.

The original script is executed byte-for-byte from its cited baseline, inside a
fresh private staging tree. This wrapper validates complete inputs, native and
source ID multiplicity, hierarchy context, and fresh output ownership first.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

ISSUE = 1161
BASELINE = "96f2a6d201236ba62f471535db240b123de60c09"
AUTHOR = "01a10947-7d6e-7ba2-98a1-a9f91dedabfc"
BRANCH = "geography/eu420-repro-erratum-g0-20261006"
OWNED = "data/regional-review/southeastern-europe-reproduction-420-erratum/"
OLD_PACKET = "data/regional-review/regional-review-c64d17e99f61d668/"
OLD_SCRIPT = OLD_PACKET + "reproduce_crosswalk.py"
OLD_RESULT = OLD_PACKET + "crosswalk.json"
RELEASE_GZIP = "data/geographic-releases/releases-v6-gzip.json.gz"
CURRENT_MANIFEST = "data/geographic-releases/current-manifest.json"
SCOPE_PATH = OLD_PACKET + "scope.json"
WORLD_INDEX = "data/world-index.json"
HIERARCHY = "data/hierarchy.json"
INPUT_TOTAL_LIMIT = 256 * 1024 * 1024
OUTPUT_RESERVE = 2 * 1024 * 1024
BASELINE_TABLE = re.compile(r"^\| `([^`]+)` \| (\d+) \| `([a-f0-9]{64})` \|$", re.M)
WORK_BLOCK = re.compile(r"<!-- worldatlas-work:v1\s*(.*?)\s*-->", re.S)

class EvidenceError(RuntimeError):
    pass

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def checked_bytes(path: str, raw: bytes, descriptor: dict) -> bytes:
    if len(raw) != descriptor["bytes"] or sha(raw) != descriptor["sha256"]:
        raise EvidenceError(f"whole-file input differs from pinned bytes: {path}")
    return raw

def check_baseline(actual: str, expected: str = BASELINE) -> None:
    if actual != expected:
        raise EvidenceError(f"wrong immutable input baseline: expected {expected}, got {actual}")

def exact_occurrences(ids: list[str], observed: list[str], label: str) -> None:
    counts = collections.Counter(observed)
    wrong = {subject: counts.get(subject, 0) for subject in ids if counts.get(subject, 0) != 1}
    extras = sorted(set(observed) - set(ids))
    if wrong or extras:
        raise EvidenceError(f"{label} subject multiplicity/scope mismatch: wrong={wrong}, extras={extras[:5]}")

def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)

def require_sha(expected: str, raw: bytes, label: str) -> None:
    if sha(raw) != expected:
        raise EvidenceError(f"{label} code/input hash mismatch")

def git_bytes(repo: Path, commit: str, path: str) -> bytes:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise EvidenceError("unsafe baseline commit")
    safe = PurePosixPath(path)
    if safe.is_absolute() or any(part in ("", ".", "..") for part in safe.parts) or "\\" in path:
        raise EvidenceError(f"unsafe repository path: {path}")
    result = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise EvidenceError(f"missing baseline input {path}: {result.stderr.decode('utf-8','replace')[:200]}")
    return result.stdout

def issue_contract(root: Path) -> tuple[dict, dict, list[dict], dict[str, dict]]:
    issue = json.loads((root / "issue-scope-snapshot.json").read_bytes())
    if issue.get("number") != ISSUE or issue.get("state") != "open":
        raise EvidenceError("issue snapshot does not represent the open #1161 work item")
    match = WORK_BLOCK.search(issue.get("body", ""))
    if not match:
        raise EvidenceError("issue's canonical geography work block is missing")
    work = json.loads(match.group(1))
    quality = work.get("evidence_quality", {})
    if work.get("mode") != "geography" or OWNED.rstrip("/") + "/" not in work.get("owned_paths", []):
        raise EvidenceError("issue mode/owned path differs from this packet")
    subjects = quality.get("subject_ids", [])
    if len(subjects) != 207 or len(set(subjects)) != 207:
        raise EvidenceError("issue contract must declare the exact unique 207-subject roster")
    rows = BASELINE_TABLE.findall(issue["body"])
    if len(rows) != 61:
        raise EvidenceError(f"expected 61 issue-pinned complete inputs, found {len(rows)}")
    pins = quality.get("pins", {})
    if len(pins) != 61:
        raise EvidenceError(f"issue contract must pin all 61 inputs, found {len(pins)}")
    descriptors, by_path = [], {}
    for path, byte_text, digest in rows:
        if path in by_path:
            raise EvidenceError(f"duplicate input descriptor: {path}")
        key = f"{BASELINE}:{path}"
        if pins.get(key) != digest:
            raise EvidenceError(f"issue pin/table disagreement: {path}")
        descriptor = {"path": path, "bytes": int(byte_text), "sha256": digest}
        descriptors.append(descriptor); by_path[path] = descriptor
    if set(pins) != {f"{BASELINE}:{row['path']}" for row in descriptors}:
        raise EvidenceError("issue evidence pins are not the exact complete 61-file inventory")
    claim = json.loads((root / "claim-receipt.json").read_bytes())
    c = claim.get("claim", {})
    if not claim.get("accepted") or claim.get("issue_number") != ISSUE or c.get("worker_id") != AUTHOR or c.get("branch") != BRANCH or c.get("owned_paths") != work["owned_paths"]:
        raise EvidenceError("claim receipt does not match #1161, GEO 0, branch and exact owned path")
    return issue, work, descriptors, by_path

def sha_mapping(obj: dict) -> dict:
    return {"bytes": len(obj), "sha256": sha(obj)}

def _first_number(value):
    if isinstance(value, list):
        if value and isinstance(value[0], (int, float)):
            return value
        for child in value:
            found = _first_number(child)
            if found is not None:
                return found
    return None

def _context_objects(scope: dict, hierarchy: list, parent_counts: collections.Counter,
                     atlas_subjects: dict, subject_ids: list[str]) -> tuple[list[dict], list[dict]]:
    if len(scope.get("province_scopes", [])) != 10:
        raise EvidenceError("prior scope must retain exactly ten province workload contexts")
    if len(scope.get("area_scopes", [])) != 2:
        raise EvidenceError("prior scope must retain exactly two area workload contexts")
    hcounts = collections.Counter(row.get("id") for row in hierarchy)
    if any(hcounts[k] != 1 for k in hcounts):
        raise EvidenceError("hierarchy has duplicate native identity rows")
    h = {row["id"]: row for row in hierarchy}
    area_by_id = {row["id"]: row for row in scope["area_scopes"]}
    expected_area_by_country = {"GRC": next(x["id"] for x in scope["area_scopes"] if x["name"] == "Greece"),
                                "HRV": next(x["id"] for x in scope["area_scopes"] if x["name"] == "Yugoslavia")}
    areas = []
    for area in scope["area_scopes"]:
        row = h.get(area["id"])
        if not row or row.get("level") != "area" or row.get("name") != area["name"] or row.get("parent_id") != scope.get("region_id"):
            raise EvidenceError(f"area context does not match exact retained hierarchy row: {area['id']}")
        member_ids = [x for x in subject_ids if x.startswith("gb:GRC:") == (area["name"] == "Greece")]
        if len(member_ids) != area.get("owned_member_location_count"):
            raise EvidenceError(f"scoped subject count differs from retained area inventory: {area['id']}")
        areas.append({"id": area["id"], "name": area["name"], "level": row["level"],
                      "parent_id": row.get("parent_id"), "scoped_subjects": len(member_ids),
                      "full_area_location_count": area.get("full_area_location_count"),
                      "workload_only": True, "semantic_approval": False})
    parents = []
    scope_parent_ids = {x["id"] for x in scope["province_scopes"]}
    if set(parent_counts) != scope_parent_ids:
        raise EvidenceError("Atlas parent count inventory differs from the exact ten prior contexts")
    for context in scope["province_scopes"]:
        row = h.get(context["id"])
        if not row or row.get("level") != "province" or row.get("name") != context["name"]:
            raise EvidenceError(f"province context does not match exact retained hierarchy row: {context['id']}")
        actual_children = parent_counts[context["id"]]
        expected_children = context.get("full_province_locations")
        if actual_children != expected_children or row.get("metadata", {}).get("child_count") != expected_children:
            raise EvidenceError(f"complete province child count mismatch: {context['id']} ({actual_children}/{expected_children})")
        by_country = {"GRC": 0, "HRV": 0}
        for subject, feature in atlas_subjects.items():
            if feature["properties"].get("parent_id") == context["id"]:
                country = subject.split(":")[1]
                by_country[country] = by_country.get(country, 0) + 1
        if row.get("parent_id") not in area_by_id:
            raise EvidenceError(f"province's parent area is outside the original two areas: {context['id']}")
        parents.append({"id": context["id"], "name": context["name"], "level": row["level"],
                        "parent_area_id": row.get("parent_id"), "full_location_count": expected_children,
                        "complete_atlas_child_count": actual_children, "issue_subject_count": sum(by_country.values()),
                        "issue_subjects_by_source_country": by_country,
                        "source_scope_partial": context.get("partial"), "workload_only": True,
                        "semantic_approval": False})
    actual_parent_ids = {x["properties"].get("parent_id") for x in atlas_subjects.values()}
    if actual_parent_ids != scope_parent_ids:
        raise EvidenceError("Exact scoped subjects do not retain all and only the ten declared parents")
    for subject, feature in atlas_subjects.items():
        expected_area = expected_area_by_country[subject.split(":")[1]]
        parent = h[feature["properties"]["parent_id"]]
        if parent.get("parent_id") != expected_area:
            raise EvidenceError(f"subject's existing hierarchy path differs from retained area context: {subject}")
    return areas, parents

def inspect_source_file(path: str, raw: bytes, descriptors: dict[str, dict], subjects: list[str], meta: dict):
    data = json.loads(raw)
    features = data.get("features")
    if not isinstance(features, list):
        raise EvidenceError(f"source GeoJSON has no feature array: {path}")
    grc = "/GRC/ADM3/" in path
    code, adm = ("GRC", "ADM3") if grc else ("HRV", "ADM2")
    target_prefix = f"gb:{code}:{adm}:"
    layer_subjects = [subject for subject in subjects if subject.startswith(target_prefix)]
    source_ids = []
    target_ids = []
    for feature in features:
        props = feature.get("properties", {})
        source_id = props.get("shapeID")
        if not isinstance(source_id, str) or not source_id:
            raise EvidenceError(f"missing native shapeID in {path}")
        source_ids.append(source_id)
        native = target_prefix + source_id
        if native in subjects:
            target_ids.append(native)
    if len(set(source_ids)) != len(source_ids):
        raise EvidenceError(f"duplicate source IDs in complete {code}-{adm} layer")
    exact_occurrences(layer_subjects, target_ids, f"{code}-{adm} source")
    declared_count = int(meta.get("admUnitCount", "0"))
    return {"path": path, "source_layer": f"{code}-{adm}", "feature_count": len(features),
            "metadata_declared_unit_count": declared_count, "feature_count_matches_metadata": len(features) == declared_count,
            "unique_source_ids": len(set(source_ids)), "scoped_subject_count": len(target_ids),
            "source_geometry_comparison": "serialization hashes only; no spatial boundary comparison",
            "bytes": descriptors[path]["bytes"], "sha256": descriptors[path]["sha256"]}

def verify_runner_pin(root: Path) -> dict:
    pin = json.loads((root / "runner-pin.json").read_bytes())
    raw = Path(__file__).read_bytes()
    require_sha(pin["runner_sha256"], raw, "separate immutable runner")
    if pin.get("runner_path") != "reproduce-crosswalk.py" or pin.get("baseline_commit") != BASELINE:
        raise EvidenceError("runner pin does not identify this exact program and baseline")
    return pin

def run(run_id: str) -> dict:
    if not re.fullmatch(r"run-[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", run_id):
        raise EvidenceError("run ID must be a fresh bounded run-* identifier")
    root = Path(__file__).resolve().parent
    repo = root.parents[2]
    pin = verify_runner_pin(root)
    issue, work, descriptors, by_path = issue_contract(root)
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise EvidenceError("runner must execute in the managed repository worktree")
    branch = subprocess.check_output(["git", "-C", str(repo), "symbolic-ref", "--short", "HEAD"], text=True).strip()
    if branch != BRANCH:
        raise EvidenceError(f"wrong author branch: {branch}")
    merge_base = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", BASELINE, "HEAD"], check=False)
    if merge_base.returncode:
        raise EvidenceError("pinned baseline is not an ancestor of this fresh-main worker branch")
    scope_desc = by_path[SCOPE_PATH]
    scope_raw = checked_bytes(SCOPE_PATH, git_bytes(repo, BASELINE, SCOPE_PATH), scope_desc)
    scope = json.loads(scope_raw)
    subjects = work["evidence_quality"]["subject_ids"]
    if scope.get("member_location_ids") != subjects or scope.get("location_count") != 207:
        raise EvidenceError("issue subjects differ from the exact retained #420 source scope")
    if len(scope.get("province_scopes", [])) != 10:
        raise EvidenceError("retained scope does not declare ten original province contexts")
    issue_counts = collections.Counter(x.split(":")[1] for x in subjects)
    if issue_counts != {"GRC": 80, "HRV": 127}:
        raise EvidenceError(f"issue subject country counts differ from the retained 80/127 scope: {dict(issue_counts)}")
    output_dir = root / "runs" / run_id
    if output_dir.exists():
        raise EvidenceError(f"refusing to reuse existing output directory: {output_dir.relative_to(root)}")
    audit_raw = (root / "baseline-input-audit.json").read_bytes()
    audit = json.loads(audit_raw)
    if audit.get("baseline_commit") != BASELINE or audit.get("descriptor_count") != 61 or audit.get("total_input_bytes") != 236953157 or not audit.get("all_hashes_match"):
        raise EvidenceError("independent 61-input hash audit is absent or differs from issue pins")
    audit_by_path = {item["path"]: item for item in audit["inputs"]}
    if len(audit_by_path) != 61 or any(audit_by_path.get(d["path"], {}).get("sha256") != d["sha256"] for d in descriptors):
        raise EvidenceError("baseline audit rows do not match all 61 issue descriptors")

    total_input_bytes = 0
    atlas_counts = collections.Counter()
    source_occurrences = collections.Counter()
    parent_counts = collections.Counter()
    atlas_subjects = {}
    subject_paths = {}
    hierarchy = None
    world = None
    source_manifest = None
    geo_meta = {}
    source_layers = []
    dgu = None
    ministry_notice = None
    greek_catalog = None
    access_attempts = None
    release_bytes = 0
    release_sha = None
    release_json = None
    historical_crosswalk = None
    original_code_sha = None
    stage_root_parent = Path(tempfile.mkdtemp(prefix=".worldatlas-1161-stage-", dir=repo))
    stage = stage_root_parent / "repo"
    stage.mkdir()
    try:
        for descriptor in descriptors:
            path = descriptor["path"]
            raw = checked_bytes(path, git_bytes(repo, BASELINE, path), descriptor)
            total_input_bytes += len(raw)
            if total_input_bytes > INPUT_TOTAL_LIMIT:
                raise EvidenceError("unique original input bytes exceed the 256 MiB phase cap")
            if path == OLD_RESULT:
                historical_crosswalk = raw
                dest = stage_root_parent / "pinned-original-crosswalk.json"
            else:
                dest = stage / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as handle:
                handle.write(raw)
            if path == OLD_SCRIPT:
                original_code_sha = sha(raw)
            elif path == SCOPE_PATH:
                if raw != scope_raw:
                    raise EvidenceError("scope bytes changed during verified input read")
            elif path == WORLD_INDEX:
                world = json.loads(raw)
            elif path == HIERARCHY:
                hierarchy = json.loads(raw)
            elif path == OLD_PACKET + "source-manifest.json":
                source_manifest = json.loads(raw)
            elif path.endswith("/GRC/ADM3/geoBoundaries-GRC-ADM3-metaData.json"):
                geo_meta["GRC"] = json.loads(raw)
            elif path.endswith("/HRV/ADM2/geoBoundaries-HRV-ADM2-metaData.json"):
                geo_meta["HRV"] = json.loads(raw)
            elif path.endswith("/GRC/ADM3/geoBoundaries-GRC-ADM3.geojson") or path.endswith("/HRV/ADM2/geoBoundaries-HRV-ADM2.geojson"):
                code = "GRC" if "/GRC/" in path else "HRV"
                meta = geo_meta.get(code)
                if meta is None:
                    # Both metadata files precede their geometry in the fixed issue inventory.
                    raise EvidenceError(f"missing pinned {code} geoBoundaries product metadata before geometry input")
                source_layers.append(inspect_source_file(path, raw, by_path, subjects, meta))
                document = json.loads(raw)
                adm = "ADM3" if code == "GRC" else "ADM2"
                prefix = f"gb:{code}:{adm}:"
                for feature in document["features"]:
                    native = prefix + feature["properties"]["shapeID"]
                    if native in subjects:
                        source_occurrences[native] += 1
                del document
            elif re.fullmatch(r"data/geography/part-\d+\.json", path):
                document = json.loads(raw)
                features = document.get("features")
                if not isinstance(features, list):
                    raise EvidenceError(f"Atlas part has no feature list: {path}")
                for feature in features:
                    props = feature.get("properties", {})
                    native = props.get("id")
                    parent = props.get("parent_id")
                    if parent in {x["id"] for x in scope["province_scopes"]}:
                        parent_counts[parent] += 1
                    if native in subjects:
                        atlas_counts[native] += 1
                        subject_paths[native] = path
                        if feature.get("id") is not None and feature.get("id") != native:
                            raise EvidenceError(f"Feature.id and properties.id disagree for {native}")
                        atlas_subjects[native] = {"properties": props, "geometry_sha256": sha(json.dumps(feature.get("geometry"), sort_keys=True).encode("utf-8"))}
                del document
            elif path == RELEASE_GZIP:
                expanded = gzip.decompress(raw)
                release_bytes = len(expanded); release_sha = sha(expanded)
                release_json = json.loads(expanded)
                del expanded
            elif path == OLD_PACKET + "source/official-croatia/dgu-scoped-unit-crosswalk.json":
                dgu = json.loads(raw)
            elif path == OLD_PACKET + "source/official-croatia/ministry-list-extract-notice.json":
                ministry_notice = json.loads(raw)
            elif path == OLD_PACKET + "source/official-greece/helix-package-show.json":
                greek_catalog = json.loads(raw)
            elif path == OLD_PACKET + "source/access-attempts.json":
                access_attempts = json.loads(raw)
            del raw

        if total_input_bytes != 236953157 or len(descriptors) != 61:
            raise EvidenceError(f"complete input accounting changed: {len(descriptors)} files / {total_input_bytes} bytes")
        exact_occurrences(subjects, list(atlas_counts.elements()), "Atlas")
        exact_occurrences(subjects, list(source_occurrences.elements()), "geoBoundaries")
        if len(source_layers) != 2 or any(not row["feature_count_matches_metadata"] for row in source_layers):
            raise EvidenceError("complete GeoBoundaries file counts disagree with pinned product metadata")
        if not historical_crosswalk or len(historical_crosswalk) != by_path[OLD_RESULT]["bytes"]:
            raise EvidenceError("pinned historical crosswalk was not retained for comparison")
        if original_code_sha != by_path[OLD_SCRIPT]["sha256"]:
            raise EvidenceError("old reproduction code is not the exact issue-pinned source")
        if world is None or hierarchy is None or source_manifest is None:
            raise EvidenceError("missing complete hierarchy/world/source context inputs")
        world_parts = {"data/" + item for item in world.get("parts", [])
                       if re.fullmatch(r"geography/part-\d+\.json", item)}
        declared_parts = {d["path"] for d in descriptors if re.fullmatch(r"data/geography/part-\d+\.json", d["path"])}
        if world_parts != declared_parts or len(declared_parts) != 34:
            raise EvidenceError("complete 34-part issue input set differs from pinned world index")
        manifest_hash = by_path[RELEASE_GZIP]["sha256"]
        if release_bytes != 536565 or not release_json or json.loads((stage / CURRENT_MANIFEST).read_bytes()).get("sha256") != manifest_hash:
            raise EvidenceError("release decode or current-manifest input binding differs from declared phase budget")
        areas, parents = _context_objects(scope, hierarchy, parent_counts, atlas_subjects, subjects)
        # Verify the full global province totals still match the retained source scope.
        for parent in parents:
            if parent["issue_subject_count"] != parent["full_location_count"]:
                raise EvidenceError(f"issue subjects do not cover the complete declared province context: {parent['id']}")
        if len(set(subject_paths)) != 207:
            raise EvidenceError("cannot construct an exact native-ID-to-containing-file map")
        admission = total_input_bytes + release_bytes + OUTPUT_RESERVE
        if admission != 239586874 or admission >= INPUT_TOTAL_LIMIT:
            raise EvidenceError(f"complete-phase admission changed: {admission}")
        if not (stage / OLD_PACKET / "crosswalk.json").exists():
            # The old result was deliberately relocated outside the script's output path.
            pass
        elif (stage / OLD_PACKET / "crosswalk.json").read_bytes() == historical_crosswalk:
            raise EvidenceError("staging unexpectedly contains the old crosswalk at the runner's fixed output path")
        script = stage / OLD_SCRIPT
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        proc = subprocess.run([sys.executable, str(script)], cwd=stage, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode:
            raise EvidenceError("pinned historical reproduction failed in verified scratch tree: " + proc.stderr.decode("utf-8", "replace")[-1000:])
        staged_output = stage / OLD_RESULT
        if not staged_output.is_file() or staged_output.is_symlink():
            raise EvidenceError("pinned runner did not create an ordinary fresh result file")
        result_bytes = staged_output.read_bytes()
        output_obj = json.loads(result_bytes)
        if output_obj.get("scope_count") != 207 or len(output_obj.get("rows", [])) != 207:
            raise EvidenceError("pinned runner output does not contain the exact 207 declared subjects")
        run_path = output_dir / "crosswalk.json"
        receipt_path = output_dir / "run-receipt.json"
        stdout_path = output_dir / "pinned-runner-stdout.txt"
        if output_dir.exists() or run_path.exists() or receipt_path.exists() or stdout_path.exists():
            raise EvidenceError("fresh output path already exists; refusing overwrite")
        output_dir.mkdir(parents=True, exist_ok=False)
        write_exclusive(run_path, result_bytes)
        write_exclusive(stdout_path, proc.stdout)
        issue_retrieval = audit.get("checked_at")
        source_dates = sorted({x.get("retrieved_at") for x in source_manifest.get("retained_source_files", []) if x.get("retrieved_at")})
        source_vintages = {}
        for code in ("GRC", "HRV"):
            meta = geo_meta[code]
            source_vintages[code] = {k:meta.get(k) for k in ("boundaryYear","boundaryType","boundaryCanonical","boundarySource","boundaryLicense","licenseDetail","licenseSource","sourceDataUpdateDate","buildDate","admUnitCount")}
        receipt = {
            "version": 1, "issue": ISSUE, "run_id": run_id, "status": "completed",
            "baseline_commit": BASELINE, "branch": branch,
            "runner_sha256": pin["runner_sha256"], "legacy_runner_path": OLD_SCRIPT,
            "legacy_runner_sha256": original_code_sha,
            "baseline_input_audit_sha256": sha(audit_raw), "input_descriptor_count": len(descriptors),
            "input_bytes_admitted": total_input_bytes, "release_uncompressed_bytes": release_bytes,
            "release_uncompressed_sha256": release_sha, "output_reserve_bytes": OUTPUT_RESERVE,
            "complete_phase_admission_bytes": admission, "phase_limit_bytes": INPUT_TOTAL_LIMIT,
            "historical_crosswalk_bytes": len(historical_crosswalk), "historical_crosswalk_sha256": sha(historical_crosswalk),
            "output_bytes": len(result_bytes), "output_sha256": sha(result_bytes),
            "byte_identical_to_historical_crosswalk": result_bytes == historical_crosswalk,
            "execution_started_at": dt.datetime.fromtimestamp(float(os.environ.get("WORLDATLAS_RUN_STARTED_EPOCH", "0")), dt.timezone.utc).isoformat().replace("+00:00","Z") if os.environ.get("WORLDATLAS_RUN_STARTED_EPOCH") else None,
            "execution_completed_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
            "source_retrieval_dates": source_dates,
            "source_vintages": source_vintages,
            "atlas_subject_count": len(atlas_subjects),
            "source_subject_count": sum(row["scoped_subject_count"] for row in source_layers),
            "atlas_subject_file_map": {subject:subject_paths[subject] for subject in sorted(subject_paths)},
            "area_contexts": areas, "province_contexts": parents,
            "geoboundaries_layers": source_layers,
            "scope_semantic_approval": False,
            "boundary_accuracy_claim": False,
            "source_scope": "The execution reproduces a historical identity/source crosswalk; it does not validate legal boundaries, source completeness, territorial meaning or license conclusions.",
            "pinned_runner_stdout_sha256": sha(proc.stdout),
            "pinned_runner_stdout_bytes": len(proc.stdout)
        }
        write_exclusive(receipt_path, (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode())
        return receipt
    finally:
        shutil.rmtree(stage_root_parent)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    started = dt.datetime.now(dt.timezone.utc).timestamp()
    os.environ["WORLDATLAS_RUN_STARTED_EPOCH"] = str(started)
    print(json.dumps(run(args.run_id), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
