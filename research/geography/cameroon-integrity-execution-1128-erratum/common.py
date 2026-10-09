#!/usr/bin/env python3
"""Authenticated, bounded execution support for the Cameroon erratum."""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import subprocess
import uuid
import zipfile

from scripts.evidence.immutable import Baseline, NewVintage, MAX_FILE_BYTES, MAX_PHASE_BYTES
from scripts.evidence.contracts import exact_rows

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/cameroon-integrity-execution-1128-erratum/"
PACKET = ROOT / OWNED
PIN_PATH = PACKET / "input-pins.json"
OLD = "research/geography/cmr-adm3-audit-integrity-20261006"
SOURCE = "data/regional-review/cameroon-adm3-authoritative-source-restoration"
EXPECTED_IDS = json.loads((PACKET / "issue-scope.json").read_text(encoding="utf-8"))
ISSUE_BODY_SHA256 = "5d46a1bc3c1c4c29a15570a8604869ba5bbae480fae62c15da6cc4aa12720391"
ISSUE_CONTRACT_SHA256 = "b7cc1bbdbb33b9cad0028f915c20562bb3ef5b50a02d6af53ae84e174bc7a171"
ISSUE_SCOPE_SHA256 = "777661c91c40a4e7175e08e62f1ee7af5e4530aecbda9cef0d914a672926329e"
BASELINE_COMMIT = "7319f888aa203228c4990c479d7291b1b78e262f"
ISSUE_SOURCE_PINS = {
    "data/geography/part-4.json": "e204a879e160f8b22ccfff698e8063a79d91cdba5ef7aa87df94661323b0bd3c",
    "data/geography/part-5.json": "20215ef8574bcf8958b3177868a7e7a8bbe206e4770ae7824915e233a90e7cbc",
    "data/regional-review/cameroon-adm3-authoritative-source-restoration/candidate-crosswalk.json": "28725b15d2f112f4cfbdc9390f39075164bb191ea91ca9904c63203b7b797fd3",
    "data/regional-review/cameroon-adm3-authoritative-source-restoration/evidence-quality.json": "4f473ecf6068cb5082575504fe45039733fee6d106e26e86e1e78ad426b2326f",
    "data/regional-review/cameroon-adm3-authoritative-source-restoration/issue-subject-ids.json": "777661c91c40a4e7175e08e62f1ee7af5e4530aecbda9cef0d914a672926329e",
    "data/regional-review/cameroon-adm3-authoritative-source-restoration/reproduce.py": "12cf806b0ca0cce6f820fa87b8e57e9baac75ee869ac9f77980a5c52c48bdf1f",
    "data/regional-review/cameroon-adm3-authoritative-source-restoration/review.md": "3f062c83445e12823dd5bd825887c77110edfd6e215cd91d9455b6aa860a0a77",
    "data/regional-review/cameroon-adm3-authoritative-source-restoration/source/arrondissements.geojson": "760a5998f6d6cecb094ab7e02252ae1e7f2f8c9f4b9d16e601247a3b5e0165c9",
    "data/regional-review/cameroon-adm3-authoritative-source-restoration/source/cmr_admin_boundaries.geojson.zip": "f24a75c41ee2e107448ff1d2b8769ee970dad376d20cd7093da0c9106814ab5a",
    "data/regional-review/regional-review-4c8c1c55a35245d1/sources/geoBoundaries-CMR-ADM3.geojson": "9d0ff998057c3afe7f3a6334d71e9d7c353c64fe6e7c35b01fe14d804c97f04b",
    "data/regional-review/regional-review-4c8c1c55a35245d1/sources/geoboundaries-CMR-ADM3-metadata.json": "84fa6e5cf34f72119a5e217e046974a03cf3a7ff091bbaa3bfc8d3aa6a3782b7",
    "data/regional-review/regional-review-d1c8bea8b9425b8c/unit-review.csv": "c724773005fb85d7247ac1c16418dcae98b2ec05ab92986a63693b8fc9cab3ea",
    "research/geography/cmr-adm3-audit-integrity-20261006/corrected-measurements.json": "8597e1c53c3bb2be31d05d831ddeaa18994e5e14f1640c8882929cb4218400c5",
    "research/geography/cmr-adm3-audit-integrity-20261006/declared-subject-ids.json": "777661c91c40a4e7175e08e62f1ee7af5e4530aecbda9cef0d914a672926329e",
    "research/geography/cmr-adm3-audit-integrity-20261006/evidence-quality.json": "6bdc16e311a13ec452442cef93c9c552c61f15945a32783c62221791c6cb397a",
    "research/geography/cmr-adm3-audit-integrity-20261006/reproduce-corrected.py": "ffd65ab0307d57b349de13f992f2b59079c6f6e540d3d66c46da1bc8e75f600b",
    "research/geography/cmr-adm3-audit-integrity-20261006/reproduce-original.py": "5dbe80dba2eff9c64ceaf9b69ea39b5ac84b859a958085a44c4fd35f24bea096",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def execution_code(base: Baseline):
    paths = ["research/geography/cameroon-integrity-execution-1128-erratum/common.py",
             "research/geography/cameroon-integrity-execution-1128-erratum/reproduce-corrected.py",
             "research/geography/cameroon-integrity-execution-1128-erratum/reproduce-legacy.py",
             "research/geography/cameroon-integrity-execution-1128-erratum/verify-pairs.py"]
    files = []
    for path in paths:
        raw = (ROOT / path).read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError("Successor runner source exceeds ordinary-file limit")
        files.append({"path": path, "bytes": len(raw), "sha256": sha(raw),
                      "execution_binding": "actual current source bytes executed by this run"})
    return {"baseline_commit": base.commit, "issue_scope_sha256": sha((PACKET / "issue-scope.json").read_bytes()),
            "scope_source_sha256": sha((PACKET / "scope-source.json").read_bytes()),
            "input_pin_manifest_sha256": sha(PIN_PATH.read_bytes()), "successor_code": files}


def baseline() -> Baseline:
    pins = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    scope_raw = (PACKET / "issue-scope.json").read_bytes()
    source_raw = (PACKET / "scope-source.json").read_bytes()
    source = json.loads(source_raw)
    declared_pins = {x["path"]: x["sha256"] for x in pins["files"]}
    if sha(scope_raw) != pins.get("issue_scope_sha256") or sha(source_raw) != pins.get("scope_source_sha256"):
        raise ValueError("Retained API issue scope/source hashes do not match the committed pin manifest")
    if (sha(scope_raw) != ISSUE_SCOPE_SHA256 or source.get("issue_body_sha256") != ISSUE_BODY_SHA256 or
            source.get("machine_contract_sha256") != ISSUE_CONTRACT_SHA256 or
            pins.get("baseline_commit") != BASELINE_COMMIT or
            any(declared_pins.get(path) != digest for path, digest in ISSUE_SOURCE_PINS.items())):
        raise ValueError("Retained issue scope, contract, or source pins disagree with the reviewed issue")
    result = Baseline(ROOT, pins["baseline_commit"], pins["files"])
    # These imported safeguards must be the same materialized bytes as the pinned Git objects.
    result.materialized_bytes("scripts/evidence/immutable.py")
    result.materialized_bytes("scripts/evidence/contracts.py")
    for prefix in (SOURCE + "/", OLD + "/"):
        required = set(result._git("ls-tree", "-r", "--name-only", result.commit, "--", prefix).decode().splitlines())
        if not required.issubset(result.pins):
            raise ValueError("Baseline pin closure omits retained packet files under " + prefix)
    for path in ("data/geography/part-4.json", "data/geography/part-5.json", "data/hierarchy.json",
                 "scripts/evidence/immutable.py", "scripts/evidence/contracts.py", "requirements.txt"):
        if path not in result.pins:
            raise ValueError("Baseline pin closure omits required adjacent/code evidence: " + path)
    context_files = {
        "research/geography/cameroon-integrity-execution-1128-erratum/input-pins.json": PIN_PATH.read_bytes(),
        "research/geography/cameroon-integrity-execution-1128-erratum/issue-scope.json": scope_raw,
        "research/geography/cameroon-integrity-execution-1128-erratum/scope-source.json": source_raw,
    }
    for path in ("research/geography/cameroon-integrity-execution-1128-erratum/common.py",
                 "research/geography/cameroon-integrity-execution-1128-erratum/reproduce-corrected.py",
                 "research/geography/cameroon-integrity-execution-1128-erratum/reproduce-legacy.py",
                 "research/geography/cameroon-integrity-execution-1128-erratum/verify-pairs.py"):
        target = ROOT / path
        if target.is_symlink() or not target.is_file():
            raise ValueError("Successor execution code must be a regular local file")
        context_files[path] = target.read_bytes()
    for path, raw in context_files.items():
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError("Scope, pin manifest, or successor code exceeds ordinary-file budget")
        result.admit(path, len(raw))
    if len(EXPECTED_IDS) != 226 or len(set(EXPECTED_IDS)) != 226:
        raise ValueError("The retained issue scope must contain exactly 226 unique identities")
    return result


class CapturedReads:
    """Provide only authenticated commit bytes to the legacy code under test."""
    def __init__(self, base: Baseline, overrides=None):
        self.base = base
        self.overrides = overrides or {}
        self.bytes = {}
        for name in base.pins:
            raw = base.materialized_bytes(name)
            self.bytes[(Path(base.repo) / name).resolve()] = raw
        self.virtual = {}
        self.deleted = {}
        self.directories = set()
        self.overwrite_attempts = []

    def raw(self, path: Path) -> bytes:
        p = Path(path).resolve()
        if p in self.virtual:
            return self.virtual[p]
        if p not in self.bytes:
            raise ValueError("Unpinned legacy read: " + str(p))
        return self.bytes[p]

    @contextlib.contextmanager
    def install(self):
        old = {"open": Path.open, "read_text": Path.read_text, "read_bytes": Path.read_bytes,
               "exists": Path.exists, "write_text": Path.write_text, "mkdir": Path.mkdir,
               "unlink": Path.unlink, "zipfile": zipfile.ZipFile}

        def open_(path, mode="r", *args, **kwargs):
            if any(c in mode for c in "wax+"):
                raise ValueError("Legacy writer attempted a physical file open")
            raw = self.raw(path)
            binary = "b" in mode
            stream = io.BytesIO(raw)
            if binary:
                return stream
            return io.TextIOWrapper(stream, encoding=kwargs.get("encoding") or "utf-8", newline=kwargs.get("newline"))

        def read_text(path, encoding=None, errors=None):
            return self.raw(path).decode(encoding or "utf-8", errors or "strict")

        def read_bytes(path):
            return self.raw(path)

        def exists(path):
            try:
                self.raw(path)
                return True
            except ValueError:
                return False

        def write_text(path, data, encoding=None, errors=None, newline=None):
            p = Path(path).resolve()
            if p in self.bytes:
                old_packet = (Path(self.base.repo) / OLD).resolve()
                if not p.is_relative_to(old_packet):
                    raise ValueError("Legacy writer targeted a pinned original outside its output packet: " + str(p))
                self.overwrite_attempts.append({"path": str(p.relative_to(Path(self.base.repo))),
                                                "retained_sha256": sha(self.bytes[p]),
                                                "retained_bytes": len(self.bytes[p]),
                                                "physical_write_blocked": True})
            raw = data.encode(encoding or "utf-8", errors or "strict") if isinstance(data, str) else bytes(data)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError("Legacy virtual output exceeds the ordinary-file budget")
            self.virtual[p] = raw
            return len(data)

        def mkdir(path, mode=0o777, parents=False, exist_ok=False):
            self.directories.add(Path(path).resolve())

        def unlink(path, missing_ok=False):
            p = Path(path).resolve()
            if p in self.virtual:
                self.deleted[p] = self.virtual.pop(p)
            elif not missing_ok:
                raise FileNotFoundError(str(p))

        def zipfile_(file, *args, **kwargs):
            if isinstance(file, (str, os.PathLike, Path)):
                zip_path = str(Path(file).resolve().relative_to(Path(self.base.repo)))
                archive = old["zipfile"](io.BytesIO(self.raw(Path(file))), *args, **kwargs)
                class AuditedZip:
                    def __enter__(self):
                        archive.__enter__()
                        return self
                    def __exit__(self, *exc):
                        return archive.__exit__(*exc)
                    def read(self, member, *a, **kw):
                        raw = archive.read(member, *a, **kw)
                        self_base = self_outer.base
                        self_base.admit(zip_path + ":decoded:" + str(member), len(raw))
                        return raw
                    def __getattr__(self, key):
                        return getattr(archive, key)
                self_outer = self
                return AuditedZip()
            return old["zipfile"](file, *args, **kwargs)

        Path.open, Path.read_text, Path.read_bytes = open_, read_text, read_bytes
        Path.exists, Path.write_text, Path.mkdir, Path.unlink = exists, write_text, mkdir, unlink
        zipfile.ZipFile = zipfile_
        try:
            yield
        finally:
            Path.open, Path.read_text, Path.read_bytes = old["open"], old["read_text"], old["read_bytes"]
            Path.exists, Path.write_text, Path.mkdir, Path.unlink = old["exists"], old["write_text"], old["mkdir"], old["unlink"]
            zipfile.ZipFile = old["zipfile"]


def pinned_exec(base: Baseline, name: str, namespace=None):
    raw = base.pinned_bytes(name)
    return exec(compile(raw, str(Path(base.repo) / name), "exec"), namespace if namespace is not None else {})


def source_joins(base: Baseline, crosswalk):
    """Check the raw candidate roster against independent pinned registers."""
    ids = json.loads(base.materialized_bytes(SOURCE + "/issue-subject-ids.json"))
    scope = exact_rows([{"id": x} for x in ids], EXPECTED_IDS)
    rows = exact_rows(crosswalk, EXPECTED_IDS, key="subject_id")
    if set(scope) != set(rows):
        raise ValueError("Crosswalk does not have exact issue-subject coverage")

    prior = list(csv.DictReader(io.StringIO(base.materialized_bytes(
        "data/regional-review/regional-review-d1c8bea8b9425b8c/unit-review.csv").decode())))
    prior_cmr = [r for r in prior if r["country"] == "CMR"]
    exact_rows(prior_cmr, EXPECTED_IDS, key="location_id")
    prior_by_id = {r["location_id"]: r for r in prior_cmr}

    gb = json.loads(base.materialized_bytes(
        "data/regional-review/regional-review-4c8c1c55a35245d1/sources/geoBoundaries-CMR-ADM3.geojson"))
    gb_features = gb["features"]
    gb_ids = [f["properties"].get("shapeID") for f in gb_features]
    gb_by_id = exact_rows([{"id": x, "feature": f} for x, f in zip(gb_ids, gb_features)], gb_ids)

    atlas_features = []
    for part in ("data/geography/part-4.json", "data/geography/part-5.json"):
        raw = base.materialized_bytes(part)
        atlas_features.extend(json.loads(raw)["features"])
    atlas_index = {}
    for feature in atlas_features:
        identity = feature.get("id") or feature.get("properties", {}).get("id")
        if identity in EXPECTED_IDS:
            if identity in atlas_index:
                raise ValueError("Scoped Atlas feature appears in multiple pinned parts")
            atlas_index[identity] = feature
    if set(atlas_index) != set(EXPECTED_IDS):
        raise ValueError("Scoped Atlas subject features do not match the exact issue roster")
    hierarchy = json.loads(base.materialized_bytes("data/hierarchy.json"))
    hierarchy_rows = exact_rows(hierarchy, [x.get("id") for x in hierarchy])

    names = ["cmr_admin1_em.geojson", "cmr_admin2_em.geojson", "cmr_admin3_em.geojson"]
    zraw = base.materialized_bytes(SOURCE + "/source/cmr_admin_boundaries.geojson.zip")
    members = {}
    decoded_receipts = []
    with zipfile.ZipFile(io.BytesIO(zraw)) as archive:
        for member in names:
            raw = archive.read(member)
            base.admit(SOURCE + "/source/cmr_admin_boundaries.geojson.zip:decoded:" + member, len(raw))
            decoded_receipts.append({"archive_path": SOURCE + "/source/cmr_admin_boundaries.geojson.zip",
                                     "member": member, "bytes": len(raw), "sha256": sha(raw)})
            members[member] = json.loads(raw)["features"]
    a1, a2, a3 = (members[x] for x in names)

    def unique(features, field):
        ids_ = [f["properties"].get(field) for f in features]
        return exact_rows([{"id": x, "feature": f} for x, f in zip(ids_, features)], ids_)

    adm1 = unique(a1, "adm1_pcode")
    adm2 = unique(a2, "adm2_pcode")
    adm3 = unique(a3, "adm3_pcode")
    if (len(adm1), len(adm2), len(adm3)) != (10, 58, 360):
        raise ValueError("Unexpected neighboring source tier counts")
    def level_names(props, level):
        values = [props.get(level + "_name" + (str(n) if n else "")) for n in ("", 1, 2, 3)]
        values.append(props.get(level + "_en"))
        return {value for value in values if isinstance(value, str) and value}

    for row in a2:
        props = row["properties"]
        parent = adm1.get(props.get("adm1_pcode"), {}).get("feature", {}).get("properties", {})
        if not parent or not (level_names(props, "adm1") & level_names(parent, "adm1")):
            raise ValueError("ADM2 has unresolved ADM1 parent")
    for row in a3:
        p = row["properties"]
        parent = adm2.get(p.get("adm2_pcode"), {}).get("feature", {}).get("properties", {})
        parent1 = adm1.get(p.get("adm1_pcode"), {}).get("feature", {}).get("properties", {})
        if (not parent or p.get("adm1_pcode") not in adm1 or
                p.get("adm1_pcode") != parent.get("adm1_pcode") or
                not (level_names(p, "adm2") & level_names(parent, "adm2")) or
                not (level_names(p, "adm1") & level_names(parent1, "adm1"))):
            raise ValueError("ADM3 has unresolved native parent code")

    output = []
    for sid, row in rows.items():
        prior_row = prior_by_id[sid]
        atlas_feature = atlas_index[sid]
        atlas_props = atlas_feature["properties"]
        parent_id = atlas_props.get("parent_id")
        parent = hierarchy_rows.get(parent_id)
        if not parent or parent.get("level") != "province":
            raise ValueError("Atlas administrative parent is missing or at unexpected granularity: " + sid)
        if row.get("atlas_name") != atlas_props.get("name") or row.get("current_atlas_parent_name") != parent.get("name"):
            raise ValueError("Crosswalk Atlas subject or parent-name join mismatch: " + sid)
        gbid = row.get("gb_source_feature_id")
        candidate = row.get("ocha_spatial_candidate_pcode")
        atlas_original_id = atlas_props.get("metadata", {}).get("original_id")
        if gbid != prior_row.get("source_feature_id") or gbid not in gb_by_id or atlas_original_id != gbid:
            raise ValueError("Source feature join mismatch: " + sid)
        if candidate not in adm3:
            raise ValueError("Candidate crosswalk has unresolved OCHA candidate code: " + sid)
        feature = adm3[candidate]["feature"]
        props = feature["properties"]
        if row.get("ocha_spatial_candidate_adm3_name") != props.get("adm3_name"):
            raise ValueError("Candidate name join mismatch: " + sid)
        if row.get("ocha_spatial_candidate_adm2_name") != props.get("adm2_name"):
            raise ValueError("Candidate parent name join mismatch: " + sid)
        if props.get("adm2_pcode") not in adm2:
            raise ValueError("Candidate parent code unresolved: " + sid)
        output.append({"subject_id": sid, "source_feature_id": gbid, "candidate_pcode": candidate,
                       "atlas_name": atlas_props.get("name"), "atlas_parent_id": parent_id,
                       "atlas_parent_name": parent.get("name"),
                       "candidate_adm3_name": props.get("adm3_name"),
                       "candidate_adm2_pcode": props.get("adm2_pcode"),
                       "candidate_adm2_name": props.get("adm2_name"),
                       "candidate_adm1_pcode": props.get("adm1_pcode")})
    exact_rows(output, EXPECTED_IDS, key="subject_id")
    return {"scope_count": len(output), "source_feature_count": len(gb_ids),
            "scoped_atlas_rows": len(atlas_index), "parent_level": "province",
            "ocha_neighbor_tiers": {"adm1": len(a1), "adm2": len(a2), "adm3": len(a3)},
            "all_parent_codes_resolve": True, "decoded_source_members": decoded_receipts, "rows": output}


def validate_archived_numbers(result, archived):
    rows = exact_rows(result["rows"], EXPECTED_IDS, key="subject_id")
    old = exact_rows(archived["rows"], EXPECTED_IDS, key="subject_id")
    numeric = 0
    scores = 0
    for sid in EXPECTED_IDS:
        a, b = rows[sid]["recorded_numeric_values"], old[sid]["recorded_numeric_values"]
        if a != b:
            raise ValueError("Original numeric measurement values changed: " + sid)
        numeric += len(a)
        m, record = rows[sid]["measurements"], rows[sid]["recorded"]
        if m != record:
            raise ValueError("Recomputed score differs from the pinned correction: " + sid)
        scores += len(m)
    if numeric != 2486 or scores != 678:
        raise ValueError("Unexpected measurement or score count")
    if result.get("aggregate_counts") != archived.get("aggregate_counts") or len(result["aggregate_counts"]) != 14:
        raise ValueError("The 14 historical aggregates changed")
    return {"exact_subject_rows": 226, "original_numeric_values": numeric,
            "corrected_scores": scores, "all_original_numeric_values_preserved": True,
            "all_selected_scores_reconciled_to_8_decimals": True,
            "all_14_aggregate_counts_match_archived_correction": True}


def independent_geodesic_ring_check(base, candidate):
    """Independently sum exterior minus hole ellipsoidal ring areas."""
    from pyproj import Geod
    from shapely.geometry import shape
    from shapely.validation import make_valid
    geod = Geod(ellps="WGS84")
    gb = json.loads(base.materialized_bytes(
        "data/regional-review/regional-review-4c8c1c55a35245d1/sources/geoBoundaries-CMR-ADM3.geojson"))
    gb_by_id = {f["properties"]["shapeID"]: shape(f["geometry"]) for f in gb["features"]}
    zraw = base.materialized_bytes(SOURCE + "/source/cmr_admin_boundaries.geojson.zip")
    with zipfile.ZipFile(io.BytesIO(zraw)) as archive:
        ocha = json.loads(archive.read("cmr_admin3_em.geojson"))["features"]
        base.admit(SOURCE + "/source/cmr_admin_boundaries.geojson.zip:decoded:cmr_admin3_em.geojson", len(archive.read("cmr_admin3_em.geojson")))
    ocha_by_code = {f["properties"]["adm3_pcode"]: f for f in ocha}

    def ring_m2(coords):
        points = list(coords)
        return abs(geod.polygon_area_perimeter([p[0] for p in points], [p[1] for p in points])[0])

    def area(geom):
        kind = geom.geom_type
        if kind == "Polygon":
            return max(0.0, ring_m2(geom.exterior.coords) - sum(ring_m2(r.coords) for r in geom.interiors))
        if kind in ("MultiPolygon", "GeometryCollection"):
            return sum(area(g) for g in geom.geoms)
        return 0.0

    def score(a, b):
        if not a.is_valid:
            a = make_valid(a)
        if not b.is_valid:
            b = make_valid(b)
        overlap = area(a.intersection(b))
        aa, ba = area(a), area(b)
        union = area(a.union(b))
        return {"iou": round(overlap / union if union else 0.0, 8),
                "reference_coverage": round(overlap / aa if aa else 0.0, 8),
                "candidate_coverage": round(overlap / ba if ba else 0.0, 8)}

    checks = []
    raw_valid = 0
    for row in candidate["crosswalk"]:
        reference = gb_by_id[row["gb_source_feature_id"]]
        other = shape(ocha_by_code[row["ocha_spatial_candidate_pcode"]]["geometry"])
        raw_valid += int(reference.is_valid) + int(other.is_valid)
        observed = score(reference, other)
        recorded = {"iou": row["ocha_spatial_best_iou"],
                    "reference_coverage": row["ocha_spatial_best_reference_coverage"],
                    "candidate_coverage": row["ocha_spatial_best_candidate_coverage"]}
        if observed != recorded:
            raise ValueError("Independent exterior-minus-hole ring calculation mismatch: " + row["subject_id"])
        checks.append({"subject_id": row["subject_id"], "scores": observed})
    if len(checks) != 226 or raw_valid != 452:
        raise ValueError("Unexpected selected-pair count or an invalid raw geometry")
    return {"method": "PyProj WGS84 polygon_area_perimeter on each exterior minus absolute area of each interior ring; components summed explicitly.",
            "independent_of_producer_area_accumulator": True, "shared_numerical_kernels": "PyProj Geod and GEOS overlay operations",
            "selected_pairs": len(checks), "scores": len(checks) * 3,
            "raw_selected_geometries_valid": raw_valid, "all_scores_match_to_8_decimals": True,
            "rows": checks}


def roster_controls(base, candidate):
    ids = json.loads(base.materialized_bytes(SOURCE + "/issue-subject-ids.json"))
    cases = {}
    cases["exact_issue_roster"] = ids
    cases["duplicate_issue_id"] = ids[:-1] + [ids[0]]
    cases["missing_issue_id"] = ids[:-1]
    cases["fabricated_issue_id"] = ids[:-1] + ["gb:CMR:ADM3:NOT-IN-SCOPE"]
    results = {}
    for label, values in cases.items():
        try:
            exact_rows([{"id": x} for x in values], EXPECTED_IDS)
            accepted = True
        except ValueError:
            accepted = False
        results[label] = {"count": len(values), "unique_count": len(set(values)), "accepted": accepted}
    if not results["exact_issue_roster"]["accepted"] or any(
        results[x]["accepted"] for x in ("duplicate_issue_id", "missing_issue_id", "fabricated_issue_id")
    ):
        raise ValueError("Issue-ID exact-row controls did not preserve the original guard behavior")

    crosswalk = candidate["crosswalk"]
    crosswalk_cases = {
        "duplicate_crosswalk_row": [*crosswalk[:-1], json.loads(json.dumps(crosswalk[0]))],
        "missing_crosswalk_row": crosswalk[:-1],
        "fabricated_crosswalk_subject": [*crosswalk[:-1], {**crosswalk[-1], "subject_id": "gb:CMR:ADM3:NOT-IN-SCOPE"}],
    }
    crosswalk_results = {}
    for label, rows in crosswalk_cases.items():
        fixture = {**candidate, "crosswalk": rows}
        fixture_bytes = (json.dumps(fixture, ensure_ascii=False, indent=2) + "\n").encode()
        try:
            source_joins(base, fixture["crosswalk"])
            accepted = True
        except ValueError:
            accepted = False
        crosswalk_results[label] = {"row_count": len(rows),
                                    "unique_subject_count": len({r.get("subject_id") for r in rows}),
                                    "refreshed_fixture_sha256": sha(fixture_bytes),
                                    "declared_count_refreshed": len(rows),
                                    "declared_score_count": 3 * len(rows),
                                    "accepted": accepted}
    if any(x["accepted"] for x in crosswalk_results.values()):
        raise ValueError("Malformed consumed crosswalk passed independent exact-row/source joins")
    fixture = {**candidate, "crosswalk": crosswalk_cases["duplicate_crosswalk_row"]}
    fixture_bytes = (json.dumps(fixture, ensure_ascii=False, indent=2) + "\n").encode()
    return {"method": "Validate raw identities against the independent issue roster and pinned source joins before compute.",
            "issue_roster_cases": results, "crosswalk_cases": crosswalk_results,
            "complete_duplicate_crosswalk_fixture": {"bytes": len(fixture_bytes), "sha256": sha(fixture_bytes),
                "row_count": len(fixture["crosswalk"]),
                "unique_row_count": len({r["subject_id"] for r in fixture["crosswalk"]}),
                "missing_subject": sorted(set(EXPECTED_IDS) - {r["subject_id"] for r in fixture["crosswalk"]})},
            "reported_upstream_fixture": {"bytes": 263846,
                "sha256": "3dba096bc814c323f99ccc5a86a5e7a4c977a58b1f7e85f6332f6088107e0818",
                "custody": "Issue-reported; original byte artifact not retained in the GitHub packet and therefore not asserted as reproduced by this successor."},
            "_fixture_bytes": fixture_bytes}


def destination_controls(base):
    """Exercise destination collision/symlink rejection and leave no control debris."""
    vintages = ROOT / OWNED / "vintages"
    vintages.mkdir(parents=True, exist_ok=True)
    scratch = vintages / ("admission-control-" + uuid.uuid4().hex[:12])
    scratch.mkdir()
    outcomes = {}
    temporary = []
    try:
        # A preexisting ordinary sentinel and an existing directory both block admission.
        sentinel_name = scratch.name + "-sentinel"
        root = vintages / sentinel_name
        root.mkdir()
        temporary.append(root)
        sentinel = root / "corrected-measurements.json"
        sentinel.write_bytes(b"retained sentinel\n")
        before = sentinel.read_bytes()
        try:
            NewVintage(base, OWNED, root.name, ["corrected-measurements.json"])
            outcomes["ordinary_sentinel"] = False
        except (FileExistsError, ValueError):
            outcomes["ordinary_sentinel"] = sentinel.read_bytes() == before

        directory_name = scratch.name + "-directory"
        directory_root = vintages / directory_name
        directory_root.mkdir()
        temporary.append(directory_root)
        blocked_directory = directory_root / "corrected-measurements.json"
        blocked_directory.mkdir()
        try:
            NewVintage(base, OWNED, directory_name, ["corrected-measurements.json"])
            outcomes["output_directory"] = False
        except (FileExistsError, ValueError):
            outcomes["output_directory"] = blocked_directory.is_dir()

        for kind, target_name in (("broken_file_symlink", "missing-target"), ("resolving_file_symlink", "target")):
            name = scratch.name + "-" + kind
            test_root = vintages / name
            test_root.mkdir()
            temporary.append(test_root)
            link = test_root / "corrected-measurements.json"
            if kind == "resolving_file_symlink":
                target = vintages / (scratch.name + "-" + target_name)
                target.write_bytes(b"symlink target sentinel\n")
                temporary.append(target)
            else:
                target = vintages / (scratch.name + "-" + target_name)
            link.symlink_to(target)
            try:
                NewVintage(base, OWNED, name, ["corrected-measurements.json"])
                outcomes[kind] = False
            except ValueError:
                outcomes[kind] = link.is_symlink()
            link.unlink()
            shutil.rmtree(test_root)
        target = vintages / (scratch.name + "-ancestor-target")
        target.mkdir()
        temporary.append(target)
        ancestor_name = scratch.name + "-ancestor-link"
        ancestor_link = vintages / ancestor_name
        ancestor_link.symlink_to(target, target_is_directory=True)
        temporary.append(ancestor_link)
        try:
            NewVintage(base, OWNED, ancestor_name, ["corrected-measurements.json"])
            outcomes["ancestor_symlink"] = False
        except ValueError:
            outcomes["ancestor_symlink"] = ancestor_link.is_symlink()
        ancestor_link.unlink()
        try:
            NewVintage(base, OWNED, "traversal", ["../escape.json"])
            outcomes["traversal"] = False
        except ValueError:
            outcomes["traversal"] = True
        outcomes["sentinel_unchanged"] = sentinel.read_bytes() == before
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        for path in reversed(temporary):
            if path.is_symlink() or path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
    if not all(outcomes.values()):
        raise ValueError("Output admission control did not block a collision or unsafe path")
    return {"method": "Shared whole-run admission inspected destination, ancestors and output names before computation.",
            "cases": outcomes, "temporary_controls_removed": True}


def input_mutation_controls(base):
    # Baseline pins are proven first; then independently corrupt captured source/code reads.
    target = "data/regional-review/cameroon-adm3-authoritative-source-restoration/candidate-crosswalk.json"
    code = OLD + "/reproduce-corrected.py"
    results = {}
    for label, path in (("changed_consumed_input", target), ("changed_consumed_code", code)):
        original = base.read
        def changed(name, original=original, path=path):
            raw = original(name)
            return raw + b"\n" if name == path else raw
        base.read = changed
        try:
            try:
                base.pinned_bytes(path)
                rejected = False
            except ValueError:
                rejected = True
        finally:
            base.read = original
        results[label] = {"path": path, "mutation": "append one byte to authenticated captured read",
                          "rejected_before_compute_or_publication": rejected}
    if not all(x["rejected_before_compute_or_publication"] for x in results.values()):
        raise ValueError("Changed consumed input/code was not rejected by the whole-file pin")
    return results


def failure_after_computation_control(base):
    vintage = "failed-publication-" + uuid.uuid4().hex[:10]
    file_names = ["computed.json"]
    writer = NewVintage(base, OWNED, vintage, file_names)
    computed = {"computation_completed": True, "example_score_count": 678,
                "hash": sha(canonical({"example": "completed scientific work"}))}
    import scripts.evidence.immutable as immutable
    original_link = immutable.os.link
    def fail_completion(src, dst, *args, **kwargs):
        if Path(dst).name == "publication.json":
            raise OSError("injected failure after computation and payload write")
        return original_link(src, dst, *args, **kwargs)
    immutable.os.link = fail_completion
    try:
        try:
            writer.publish({"computed.json": computed})
            failed = False
        except OSError:
            failed = True
    finally:
        immutable.os.link = original_link
    root = writer.root
    if not failed or (root / "publication.json").exists() or not (root / "computed.json").exists():
        raise ValueError("Post-computation publication fault did not remain failed and unreceipted")
    retained = []
    for p in sorted(root.iterdir()):
        if p.is_file():
            raw = p.read_bytes()
            retained.append({"name": p.name, "bytes": len(raw), "sha256": sha(raw)})
    return {"injected_after_computation": True, "failure_reached_exclusive_completion_receipt": True,
            "status": "failed", "publication_receipt_absent": True,
            "retained_partial_outputs": retained, "partial_run_path": str(root.relative_to(ROOT))}


def run_corrected(vintage: str):
    base = baseline()
    names = ["corrected-measurements.json", "source-joins.json", "independent-geodesic-check.json",
             "duplicate-crosswalk-fixture.json", "controls.json", "geometry-positive-control.json",
             "geometry-negative-control.json", "geometry-mixed-winding-control.json", "roster-controls.json",
             "admission-controls.json", "input-mutation-controls.json", "failed-publication-control.json",
             "provenance.json"]
    writer = NewVintage(base, OWNED, vintage, names)
    archived = json.loads(base.materialized_bytes(OLD + "/corrected-measurements.json"))
    candidate = json.loads(base.materialized_bytes(SOURCE + "/candidate-crosswalk.json"))
    exact_rows(candidate["crosswalk"], EXPECTED_IDS, key="subject_id")
    roster = roster_controls(base, candidate)
    duplicate_fixture_bytes = roster.pop("_fixture_bytes")
    admission = destination_controls(base)
    mutation = input_mutation_controls(base)
    joined = source_joins(base, candidate["crosswalk"])
    # The old function is pinned and its actual source path is covered by the adapter.
    captured = CapturedReads(base)
    path = OLD + "/reproduce-corrected.py"
    namespace = {"__name__": "worldatlas_pinned_corrected", "__file__": str(ROOT / path)}
    output = io.StringIO()
    with captured.install(), contextlib.redirect_stdout(output):
        pinned_exec(base, path, namespace)
        result = namespace["one_run"]()
        controls = namespace["controls"]()
        old_roster = namespace["subject_controls"]()
    rows_check = validate_archived_numbers(result, archived)
    geodesic = independent_geodesic_ring_check(base, candidate)
    output_values = {
        names[0]: result,
        names[1]: joined,
        names[2]: geodesic,
        names[4]: {"positive": controls["positive"], "mixed": controls["mixed"], "negative": controls["negative"]},
        names[5]: controls["positive"],
        names[6]: controls["negative"],
        names[7]: controls["mixed"],
        names[8]: {"new_exact_crosswalk_controls": roster, "preserved_issue_id_controls": old_roster},
        names[9]: admission,
        names[10]: mutation,
        names[11]: failure_after_computation_control(base),
        names[12]: {"baseline_commit": base.commit, "captured_inputs": [
            {"path": k, "bytes": v["bytes"], "sha256": v["sha256"]} for k, v in base.pins.items()],
            "execution": execution_code(base),
            "reconciliation": rows_check, "source_join_hash": sha(canonical(joined)),
            "runtime": runtime_versions(), "stdout_sha256": sha(output.getvalue().encode()),
            "unique_phase_inputs": [{"path": k, "bytes": v} for k, v in base.consumed.items()],
            "phase_input_bytes": sum(base.consumed.values()),
            "source_limit": "Comparison-only evidence; does not establish legal boundary identity, official endorsement, full current national coverage, or closure of #897.",
            "admission": "All planned output paths were admitted before scientific computation; outputs were published exclusively and publication.json last."}}
    raw_outputs = {name: canonical(value) for name, value in output_values.items()}
    raw_outputs[names[3]] = duplicate_fixture_bytes
    writer.publish_bytes(raw_outputs)
    return output_values


def run_legacy(vintage: str):
    base = baseline()
    names = ["legacy-replay.json", "legacy-products.json", "legacy-provenance.json"]
    writer = NewVintage(base, OWNED, vintage, names)
    wrapper = OLD + "/reproduce-original.py"
    producer = SOURCE + "/reproduce.py"
    protected = [producer, SOURCE + "/issue-subject-ids.json", SOURCE + "/candidate-crosswalk.json",
                 SOURCE + "/positive-control.json", SOURCE + "/negative-control.json",
                 SOURCE + "/source/cmr_admin_boundaries.geojson.zip", SOURCE + "/source/arrondissements.geojson"]
    before = {x: sha(base.materialized_bytes(x)) for x in protected}
    products_by_run = []
    replay_rows = []
    for label in ("invocation-one", "invocation-two"):
        captured = CapturedReads(base)
        old_runpy = runpy.run_path
        def execute_pinned(path, run_name=None, init_globals=None):
            raw = base.pinned_bytes(producer)
            ns = dict(init_globals or {})
            ns.update({"__name__": run_name or "<run_path>", "__file__": str(ROOT / producer)})
            exec(compile(raw, str(ROOT / producer), "exec"), ns)
            return ns
        runpy.run_path = execute_pinned
        stdout = io.StringIO()
        old_argv = sys.argv[:]
        try:
            with captured.install(), contextlib.redirect_stdout(stdout):
                ns = {}
                pinned_exec(base, wrapper, {"__name__": "__main__", "__file__": str(ROOT / wrapper)})
        finally:
            runpy.run_path = old_runpy
            sys.argv = old_argv
        # The wrapper's target outputs are captured before its intended unlink.
        generated = {str(k.relative_to(ROOT)): v for k, v in captured.deleted.items()}
        expected = {f"{OLD}/reproduction/{roster}/{name}" for roster in ("original-roster", "duplicate-roster")
                    for name in ("candidate-crosswalk.json", "positive-control.json", "negative-control.json")}
        if set(generated) != expected:
            raise ValueError("Legacy replay did not capture all six deleted producer products")
        virtual_products = {str(k.relative_to(ROOT)): v for k, v in captured.virtual.items()}
        required_virtual = {f"{OLD}/fixtures/duplicate-issue-subject-ids.json",
                            f"{OLD}/reproduction/original-roster/stdout.json",
                            f"{OLD}/reproduction/duplicate-roster/stdout.json",
                            f"{OLD}/reproduction/legacy-integrity-reproduction.json"}
        if not required_virtual.issubset(virtual_products):
            raise ValueError("Legacy fixture/stdout/report paths were not captured")
        for filename, raw in generated.items():
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError("Legacy generated output exceeds file budget")
        if before != {x: sha(base.materialized_bytes(x)) for x in protected}:
            raise ValueError("Protected original changed during legacy replay")
        products_by_run.append({**generated, **virtual_products})
        replay_rows.append({"run": label,
                            "stdout": json.loads(stdout.getvalue()),
                            "outputs": {k: {"bytes": len(v), "sha256": sha(v)} for k, v in generated.items()},
                            "virtual_fixture_stdout_and_report": {k: {"bytes": len(v), "sha256": sha(v)} for k, v in virtual_products.items()},
                            "retained_packet_overwrite_attempts_captured": captured.overwrite_attempts,
                            "protected_originals_unchanged_after_this_replay": True})
    if any(products_by_run[0][n] != products_by_run[1][n] for n in products_by_run[0]):
        raise ValueError("Legacy duplicate-roster replay changed the historical products")
    result = {"method": "Execute exact pinned legacy wrapper and producer with authenticated reads and virtual writes/deletion.",
              "runs": replay_rows, "generated_products_equal": True,
              "captured_products_before_virtual_deletion": True,
              "protected_paths_sha256": before,
              "limitation": "The legacy producer's set-only issue-ID guard accepts a 227-row roster with 226 unique IDs. No original files were written."}
    product_manifest = {k: {"bytes": len(v), "sha256": sha(v), "base64": __import__("base64").b64encode(v).decode()}
                        for k, v in products_by_run[0].items()}
    provenance = {"baseline_commit": base.commit,
                  "wrapper_sha256": sha(base.pinned_bytes(wrapper)),
                  "producer_sha256": sha(base.pinned_bytes(producer)),
                  "captured_inputs": [{"path": k, "bytes": v["bytes"], "sha256": v["sha256"]} for k, v in base.pins.items()],
                  "execution": execution_code(base),
                  "unique_phase_inputs": [{"path": k, "bytes": v} for k, v in base.consumed.items()],
                  "phase_input_bytes": sum(base.consumed.values()),
                  "runtime": runtime_versions(),
                  "scope_limit": "Retained source/audit uncertainty unchanged; this replay does not certify geography or legal source authority."}
    writer.publish({names[0]: result, names[1]: product_manifest, names[2]: provenance})
    return result


def runtime_versions():
    import pyproj
    import shapely
    from shapely import geos_version_string
    return {"python": sys.version.split()[0], "pyproj": pyproj.__version__,
            "GEOS": geos_version_string, "shapely": shapely.__version__,
            "proj_data_directory": pyproj.datadir.get_data_dir(),
            "coordinate_transformations": "none; retained GeoJSON coordinates consumed as WGS84 longitude-latitude"}
