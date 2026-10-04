#!/usr/bin/env python3
"""Prepare bounded, lossless feature subsets from immutable #609/#485 inputs.

The original packets are never written. This command is one-shot: it refuses an
existing inputs directory and reads only the pinned Git baseline commit.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

BASELINE_COMMIT = "24629e5918a144a1979db80ba7012baea42036e7"
OWNED = Path(__file__).resolve().parent
REPO = OWNED.parents[2]
ORIGINAL = "data/regional-review/bc-administrative-remainders-followup-2026"
PARENT = "data/regional-review/regional-review-4254da254d94f450"
TARGETS = ("5901", "5933", "5939", "5941", "5949", "5951", "5953", "5955", "5957", "5959")
PARENT_INPUTS = (
    "assessment.json",
    "sources-manifest.json",
    "sources/statistics-canada-bc-census-divisions-2021.geojson.gz",
    "sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz",
    "sources/geoboundaries-CAN-ADM3-2016.geojson",
    "sources/statistics-canada-bc-population-centres-2021.geojson.gz",
    "sources/canadian-geographical-names-populated-places-BC.geojson.gz",
    "sources/current-parent-chains.json.gz",
)


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASELINE_COMMIT}:{path}"])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tracked_paths(prefix: str) -> list[str]:
    rows = subprocess.check_output(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", BASELINE_COMMIT, "--", prefix], text=True)
    return sorted(p for p in rows.splitlines() if p.startswith(prefix + "/"))


def bounds(geometry: dict) -> tuple[float, float, float, float]:
    xy = []
    def visit(value):
        if isinstance(value, (list, tuple)) and len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
            xy.append((float(value[0]), float(value[1])))
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)
    visit(geometry.get("coordinates", []))
    if not xy:
        raise ValueError("Empty geometry in pinned source")
    return min(x for x, _ in xy), min(y for _, y in xy), max(x for x, _ in xy), max(y for _, y in xy)


def overlaps(a, b) -> bool:
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def deterministic_gzip(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=9, mtime=0)


def canonical_json(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def load_json(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))


def file_descriptor(path: Path, raw: bytes | None = None) -> dict:
    data = path.read_bytes() if raw is None else raw
    result = {"path": path.relative_to(OWNED).as_posix(), "bytes": len(data), "sha256": sha(data), "hash_kind": "file-bytes"}
    if path.suffix == ".gz":
        unpacked = gzip.decompress(data)
        result.update({"uncompressed_bytes": len(unpacked), "uncompressed_sha256": sha(unpacked)})
    return result


def main() -> None:
    input_dir = OWNED / "inputs"
    if input_dir.exists():
        raise SystemExit("Refusing to replace retained inputs; choose a fresh owned vintage")

    original_paths = tracked_paths(ORIGINAL)
    parent_paths = [f"{PARENT}/{name}" for name in PARENT_INPUTS]
    inventory = []
    raw_blobs = {}
    for repo_path in original_paths + parent_paths:
        raw = git_bytes(repo_path)
        raw_blobs[repo_path] = raw
        row = {"path": repo_path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
        if repo_path.endswith(".gz"):
            unpacked = gzip.decompress(raw)
            row.update({"uncompressed_bytes": len(unpacked), "uncompressed_sha256": sha(unpacked)})
        inventory.append(row)

    original_root = load_json(raw_blobs[f"{ORIGINAL}/sources/acquisition-receipt.json"])
    for name, rec in original_root["responses"].items():
        repo_path = f"{ORIGINAL}/{rec['retained_path']}"
        raw = raw_blobs[repo_path]
        if len(raw) != rec["retained_bytes"] or sha(raw) != rec["retained_sha256"]:
            raise ValueError(f"Acquisition receipt mismatch: {name}")
        unpacked = gzip.decompress(raw) if rec["retained_encoding"].startswith("gzip") else raw
        if len(unpacked) != rec["bytes"] or sha(unpacked) != rec["sha256"]:
            raise ValueError(f"Original response-byte mismatch: {name}")

    parent_assessment = load_json(raw_blobs[f"{PARENT}/assessment.json"])
    parent_manifest = load_json(raw_blobs[f"{PARENT}/sources-manifest.json"])
    parent_sources = {name: raw_blobs[f"{PARENT}/{name}"] for name in PARENT_INPUTS if name.startswith("sources/")}
    for row in parent_manifest["files"]:
        name = row["path"]
        if name in parent_sources and sha(parent_sources[name]) != row["sha256"]:
            raise ValueError(f"#485 source-manifest mismatch: {name}")

    cds = load_json(gzip.decompress(parent_sources["sources/statistics-canada-bc-census-divisions-2021.geojson.gz"]))["features"]
    csds = load_json(gzip.decompress(parent_sources["sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz"]))["features"]
    gb = load_json(parent_sources["sources/geoboundaries-CAN-ADM3-2016.geojson"])["features"]
    target_cds = [f for f in cds if str(f["properties"].get("CDUID")) in TARGETS]
    target_csds = [f for f in csds if str(f["properties"].get("CSDUID", ""))[:4] in TARGETS]
    if len(target_cds) != len(TARGETS) or len({f["properties"]["CDUID"] for f in target_cds}) != len(TARGETS):
        raise ValueError("The exact ten assigned CD identities are not unique and present")
    if len(target_csds) != 335 or len({f["properties"]["CSDUID"] for f in target_csds}) != 335:
        raise ValueError("The exact 335 current CSD identities are not unique and present")

    relevant_geometries = [f["geometry"] for f in target_cds + target_csds]
    boxes = [bounds(g) for g in relevant_geometries]
    # Coordinate traversal is performed once per source feature; the ensuing
    # rectangle tests are cheap and preserve the tighter multi-envelope filter.
    original_gb_candidates = []
    for feature in gb:
        feature_box = bounds(feature["geometry"])
        if any(overlaps(feature_box, box) for box in boxes):
            original_gb_candidates.append(feature)
    if not original_gb_candidates:
        raise ValueError("Expected source-bbox candidate extract is empty")

    # A full Canada/BC source file exceeds the shared per-file validator budget.
    # Exact single-CD, target-CSD and bounding-box-superset parts keep each
    # retained derivative small while the complete original blob is pinned above.
    input_dir.mkdir()
    (input_dir / "parent").mkdir()
    (input_dir / "parent/sources").mkdir()
    (input_dir / "parent/census-divisions").mkdir()
    (input_dir / "parent/census-subdivisions").mkdir()
    (input_dir / "parent/geoboundaries").mkdir()

    for feature in cds:
        cd = str(feature["properties"]["CDUID"])
        feature_collection = {"type": "FeatureCollection", "features": [feature]}
        raw_feature = canonical_json(feature_collection)
        if len(raw_feature) <= 32 * 1024 * 1024:
            path = input_dir / f"parent/census-divisions/{cd}.geojson.gz"
            path.write_bytes(deterministic_gzip(raw_feature))
        else:
            geometry = feature["geometry"]
            if geometry.get("type") != "MultiPolygon":
                raise ValueError(f"Oversized CD {cd} is not a MultiPolygon that can be split losslessly")
            coordinates = geometry["coordinates"]
            part_index = 0
            for start in range(0, len(coordinates), 100):
                part = dict(feature)
                part["geometry"] = {"type": "MultiPolygon", "coordinates": coordinates[start:start + 100]}
                payload = canonical_json({"type": "FeatureCollection", "features": [part]})
                if len(payload) > 32 * 1024 * 1024:
                    raise ValueError(f"A geometry part for CD {cd} still exceeds the byte validator budget")
                path = input_dir / f"parent/census-divisions/{cd}-part-{part_index:04d}.geojson.gz"
                path.write_bytes(deterministic_gzip(payload))
                part_index += 1
    for cd in TARGETS:
        part = [f for f in target_csds if str(f["properties"]["CSDUID"])[:4] == cd]
        path = input_dir / f"parent/census-subdivisions/{cd}.geojson.gz"
        path.write_bytes(deterministic_gzip(canonical_json({"type": "FeatureCollection", "features": part})))
    for i in range(0, len(original_gb_candidates), 40):
        part = original_gb_candidates[i:i + 40]
        path = input_dir / f"parent/geoboundaries/part-{i // 40:04d}.geojson.gz"
        path.write_bytes(deterministic_gzip(canonical_json({"type": "FeatureCollection", "features": part})))

    # Preserve exact #485 files that carry identity, parent-chain and settlement references.
    exact_parent_names = (
        "assessment.json",
        "sources/current-parent-chains.json.gz",
        "sources/statistics-canada-bc-population-centres-2021.geojson.gz",
        "sources/canadian-geographical-names-populated-places-BC.geojson.gz",
    )
    for name in exact_parent_names:
        target = input_dir / "parent" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw_blobs[f"{PARENT}/{name}"])

    subject_registry = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": f"StatisticsCanada:2021:CD:{cd}",
             "properties": {"id": f"StatisticsCanada:2021:CD:{cd}", "source_property": "CDUID", "source_value": cd},
             "geometry": None}
            for cd in TARGETS
        ],
    }
    (OWNED / "source-subject-registry.geojson").write_bytes(canonical_json(subject_registry))

    derived_files = sorted(p for p in input_dir.rglob("*") if p.is_file())
    source_inventory = [file_descriptor(p) for p in derived_files]
    custom_manifest_files = []
    for p in derived_files:
        if p.is_relative_to(input_dir / "parent"):
            custom_manifest_files.append({"path": p.relative_to(input_dir / "parent").as_posix(), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())})
    custom_manifest = {"source_baseline_commit": BASELINE_COMMIT, "files": custom_manifest_files}
    custom_sources_manifest = input_dir / "parent/sources-manifest.json"
    custom_sources_manifest.write_text(json.dumps(custom_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    source_inventory.append(file_descriptor(custom_sources_manifest))
    source_inventory.sort(key=lambda row: row["path"])

    input_baseline = {
        "version": 1,
        "baseline_commit": BASELINE_COMMIT,
        "scope": list(TARGETS),
        "original_issue_609_packet": ORIGINAL,
        "parent_issue_485_packet": PARENT,
        "files": inventory,
        "bounded_derived_inputs": source_inventory,
        "source_extraction": {
            "census_divisions": "All BC Census Division features retained in source order. A single feature over 32 MiB uncompressed is partitioned by original MultiPolygon components into lossless ordered parts and reassembled before analysis.",
            "census_subdivisions": "Exactly all 335 source CSD features whose source CSDUID starts with one of the ten assigned CDUID values; retained per CD in original source order.",
            "geoboundaries": "Lossless source features whose coordinate bounding boxes intersect at least one assigned full CD or one of its target CSD bounding boxes; this is a complete candidate superset for exact polygon intersections, retained in source order and split into 40-feature parts.",
            "other_parent_files": "Identity assessment, exact full parent chains, population-centre source and GNBC populated-place source retained byte-for-byte from #485.",
            "oversized_files": "The complete original CD, CSD and geoBoundaries blobs exceed the shared 32 MiB per-input EQLY byte-inspection limit. They are streamed/verified against these whole-file SHA-256 pins before extraction. Their small lossless/superset derivatives are the bounded inputs to the reproduced audit.",
        },
        "original_sha256": sha(raw_blobs[f"{ORIGINAL}/evidence-manifest.json"]),
        "parent_sha256": sha(raw_blobs[f"{PARENT}/sources-manifest.json"]),
        "subject_registry_sha256": sha((OWNED / "source-subject-registry.geojson").read_bytes()),
    }
    (OWNED / "input-baseline.json").write_text(json.dumps(input_baseline, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    receipt = {
        "issue": 667,
        "source_baseline_commit": BASELINE_COMMIT,
        "subject_count": len(TARGETS),
        "cd_source_features_retained": len(cds),
        "target_csd_source_features_retained": len(target_csds),
        "geoboundaries_bbox_superset_features_retained": len(original_gb_candidates),
        "original_source_feature_count": len(gb),
        "original_source_order_preserved": True,
        "exact_filter_counts": {cd: sum(1 for f in target_csds if str(f["properties"]["CSDUID"])[:4] == cd) for cd in TARGETS},
        "derivative_files": source_inventory,
        "method": "Full source bytes came from Git commit baseline_commit. SHA-256 and byte counts were checked against Git objects and all #609 acquisition-receipt retained/raw response descriptors before filtering. Compressed-source raw SHA-256 values are in input-baseline.json. Derived JSON is UTF-8, compact, allow_nan=false with a trailing LF; gzip uses level 9 and mtime=0.",
    }
    (OWNED / "input-extraction-receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"input_files": len(inventory), "derived_files": len(source_inventory), "cds": len(TARGETS), "csds": len(target_csds), "geoboundary_candidates": len(original_gb_candidates)}, indent=2))


if __name__ == "__main__":
    main()
