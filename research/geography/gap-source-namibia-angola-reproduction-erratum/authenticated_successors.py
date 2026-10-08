#!/usr/bin/env python3
"""Shared implementation for the independently runnable #1437 successors."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from shapely.geometry import shape


OWNED = Path(__file__).resolve().parent
REPO = Path(subprocess.check_output(["git", "-C", str(OWNED), "rev-parse", "--show-toplevel"], text=True).strip())
PIN_FILE = OWNED / "source-pin-inventory.json"
OLD_ISSUE_SNAPSHOT = OWNED / "sources/issue-1437-api-snapshot.json"
CURRENT_ISSUE_SNAPSHOT = OWNED / "sources/issue-1437-amended-scope-snapshot.json"
PIN_SHA256 = "a6aa58da227bb7e9f12b48839fd7299d64396e85b831205c97a1d608fdeb5216"
OLD_ISSUE_BODY_SHA256 = "380c7a61e78319372ea00805ced0ab36370416f3b62b89f5d5fa1c994caf4e35"
CURRENT_ISSUE_BODY_SHA256 = "15d6ad98802815d5b325bc4573208e32f24258bbe3dc459a7e553f1d7d155aae"
COMPONENTS = "research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson"
CONTACTS = "research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson"
BINDINGS = "research/geography/gap-source-namibia-angola-20261006/inputs/input-bindings.json"
FULL_NAM = "research/geography/gap-source-namibia-angola-20261006/sources/geoBoundaries-NAM-ADM2-full-9469f09.geojson"
FULL_AGO = "research/geography/gap-source-namibia-angola-20261006/sources/geoBoundaries-AGO-ADM2-full-9469f09.geojson"
CODE_PATHS = (
    "research/geography/gap-source-namibia-angola-reproduction-erratum/authenticated_successors.py",
    "research/geography/gap-source-namibia-angola-reproduction-erratum/reproduce_source_geometry_successor.py",
    "research/geography/gap-source-namibia-angola-reproduction-erratum/reproduce_full_product_successor.py",
)
EXPECTED_CONTACT_IDS = {
    "gb:AGO:ADM2:16411231B14510444140190", "gb:AGO:ADM2:16411231B28551746118834",
    "gb:AGO:ADM2:16411231B36562728226085", "gb:NAM:ADM2:8085530B15355770078360",
    "gb:NAM:ADM2:8085530B25496891828693", "gb:NAM:ADM2:8085530B32015186497374",
    "gb:NAM:ADM2:8085530B43563455443088", "gb:NAM:ADM2:8085530B54610932550654",
    "gb:NAM:ADM2:8085530B8620298556926", "gb:NAM:ADM2:8085530B94702234009846",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(rev: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{rev}:{path}"])


def require_committed_code(head: str) -> list[dict]:
    receipts = []
    for rel in CODE_PATHS:
        committed = git_blob(head, rel)
        local = (REPO / rel).read_bytes()
        if local != committed:
            raise ValueError(f"Executed code differs from immutable HEAD blob: {rel}")
        receipts.append({"path": rel, "commit": head, "bytes": len(committed), "sha256": sha(committed)})
    return receipts


def pinned_inputs(head: str):
    inv_raw = PIN_FILE.read_bytes()
    if sha(inv_raw) != PIN_SHA256:
        raise ValueError("The reviewed issue pin inventory changed")
    old_snapshot = json.loads(OLD_ISSUE_SNAPSHOT.read_bytes())
    if (old_snapshot["body_sha256"] != OLD_ISSUE_BODY_SHA256
            or sha(old_snapshot["body"].encode()) != OLD_ISSUE_BODY_SHA256):
        raise ValueError("The original issue acceptance snapshot changed")
    current_snapshot = json.loads(CURRENT_ISSUE_SNAPSHOT.read_bytes())
    current_body = current_snapshot.get("body", "")
    if (current_snapshot.get("issue") != 1437
            or current_snapshot.get("body_sha256") != CURRENT_ISSUE_BODY_SHA256
            or current_snapshot.get("body_bytes") != len(current_body.encode())
            or sha(current_body.encode()) != CURRENT_ISSUE_BODY_SHA256
            or "Explicit Main scope decision" not in current_body
            or '"max_prs":2' not in current_body
            or '"owned_paths":["research/geography/gap-source-namibia-angola-reproduction-erratum/"]' not in current_body):
        raise ValueError("The currently authorized issue scope or ownership changed")
    inventory = json.loads(inv_raw)
    if inventory["issue_body_sha256"] != OLD_ISSUE_BODY_SHA256 or len(inventory["pins"]) != inventory["declared_pin_count"]:
        raise ValueError("Issue pin inventory is incomplete or detached from its acceptance snapshot")
    blobs = {}
    records = {}
    for pin in inventory["pins"]:
        raw = git_blob(pin["commit"], pin["path"])
        if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
            raise ValueError(f"Immutable issue-pinned Git blob mismatch: {pin['path']}")
        if pin["path"] in blobs and blobs[pin["path"]] != raw:
            raise ValueError(f"Conflicting pinned vintages for path: {pin['path']}")
        blobs[pin["path"]] = raw
        records[pin["path"]] = pin
    # These are actual files consumed by both successors. Check the materialized
    # operands too; otherwise an altered local inventory could be silently ignored.
    for rel in (COMPONENTS, CONTACTS, BINDINGS, FULL_NAM, FULL_AGO):
        if rel not in blobs or (REPO / rel).read_bytes() != blobs[rel]:
            raise ValueError(f"Executed source input differs from its immutable pinned bytes: {rel}")
    code = require_committed_code(head)
    return blobs, records, code


def unique(rows, key, label):
    result = {}
    for row in rows:
        value = key(row)
        if not value or value in result:
            raise ValueError(f"Missing or duplicate {label}: {value!r}")
        result[value] = row
    return result


def subject_id(feature):
    props = feature.get("properties", {})
    return f"gb:{props.get('shapeGroup')}:ADM2:{props.get('shapeID')}"


def shape_checked(feature, identity):
    geom = shape(feature.get("geometry"))
    if geom.is_empty or not geom.is_valid:
        raise ValueError(f"Empty or invalid geometry: {identity}")
    return geom


def prepare(blobs):
    component_rows = json.loads(blobs[COMPONENTS])["features"]
    contact_rows = json.loads(blobs[CONTACTS])["features"]
    bindings = json.loads(blobs[BINDINGS])
    components = unique(component_rows, lambda row: row.get("id"), "candidate ID")
    contacts = unique(contact_rows, subject_id, "contact subject ID")
    bound_components = {row["id"] for row in bindings["component_features"]}
    bound_contacts = {row["source_id"] for row in bindings["contacts"]}
    if len(components) != 21 or set(components) != bound_components:
        raise ValueError("Candidate inventory does not equal all 21 pinned bound identities")
    if len(contacts) != 10 or set(contacts) != EXPECTED_CONTACT_IDS or set(contacts) != bound_contacts:
        raise ValueError("Contact inventory does not equal all 10 issue-declared subject identities")
    full = {}
    for country, path, expected in (("NAM", FULL_NAM, 109), ("AGO", FULL_AGO, 161)):
        rows = json.loads(blobs[path])["features"]
        if len(rows) != expected:
            raise ValueError(f"{country} complete ADM2 product expected {expected} rows, found {len(rows)}")
        full[country] = unique(rows, lambda row: row.get("properties", {}).get("shapeID"), f"{country} full-product ID")
        for sid, row in full[country].items():
            shape_checked(row, f"{country}:{sid}")
    component_geometries = {identity: shape_checked(row, identity) for identity, row in components.items()}
    contact_geometries = {identity: shape_checked(row, identity) for identity, row in contacts.items()}
    # Every retained contact must resolve by exact country and source ID in the full product.
    for identity, row in contacts.items():
        props = row["properties"]
        country, sid = props["shapeGroup"], props["shapeID"]
        if country not in full or sid not in full[country]:
            raise ValueError(f"Contact is absent from same-release full product: {identity}")
    return components, contacts, full, component_geometries, contact_geometries


def build_report(mode: str, head: str, blobs, records, code_receipts):
    components, contacts, full, component_geometries, contact_geometries = prepare(blobs)
    matrix = []
    if mode == "source-geometry":
        for cid, candidate in sorted(components.items()):
            candidate_geom = component_geometries[cid]
            for sid, contact in sorted(contacts.items()):
                geom = contact_geometries[sid]
                intersection = candidate_geom.intersection(geom)
                matrix.append({"candidate_id": cid, "contact_subject_id": sid,
                               "operand": "retained consumed source-contact-features.geojson geometry",
                               "intersects": not intersection.is_empty,
                               "intersection_type": intersection.geom_type,
                               "intersection_area_square_degrees": intersection.area})
        expected_rows = 210
    elif mode == "full-product":
        # Complete row coverage includes disjoint pairs; this prevents a sparse
        # hit list or headline count from standing in for product completeness.
        for cid, candidate in sorted(components.items()):
            candidate_geom = component_geometries[cid]
            for country in ("NAM", "AGO"):
                for source_id, source in sorted(full[country].items()):
                    intersection = candidate_geom.intersection(shape(source["geometry"]))
                    matrix.append({"candidate_id": cid, "country": country,
                                   "full_product_shape_id": source_id,
                                   "intersects": not intersection.is_empty,
                                   "intersection_type": intersection.geom_type,
                                   "intersection_area_square_degrees": intersection.area})
        expected_rows = 21 * (109 + 161)
    else:
        raise ValueError("Unknown successor mode")
    keys = [(row["candidate_id"], row["contact_subject_id"]) if mode == "source-geometry"
            else (row["candidate_id"], row["country"] + ":" + row["full_product_shape_id"])
            for row in matrix]
    if len(matrix) != expected_rows or len(set(keys)) != expected_rows:
        raise ValueError(f"Complete unique pair matrix expected {expected_rows} rows")
    # Exact consumed/full same-ID operands are named and compared for both modes.
    operand_checks = []
    for sid, contact in sorted(contacts.items()):
        props = contact["properties"]
        full_feature = full[props["shapeGroup"]][props["shapeID"]]
        consumed_geom = contact_geometries[sid]
        full_geom = shape_checked(full_feature, sid + " same-release full")
        operand_checks.append({"contact_subject_id": sid,
                               "consumed_geometry_sha256": sha(json.dumps(contact["geometry"], sort_keys=True, separators=(",", ":")).encode()),
                               "same_release_full_geometry_sha256": sha(json.dumps(full_feature["geometry"], sort_keys=True, separators=(",", ":")).encode()),
                               "topologically_equal": consumed_geom.equals(full_geom)})
    pins = []
    for path in (COMPONENTS, CONTACTS, BINDINGS, FULL_NAM, FULL_AGO):
        record = records[path]
        pins.append({"path": path, "commit": record["commit"], "bytes": len(blobs[path]), "sha256": sha(blobs[path])})
    return {"version": 1, "issue": 1437, "mode": mode, "source_code": code_receipts,
            "executed_at_commit": head, "issue_acceptance_snapshot_sha256": OLD_ISSUE_BODY_SHA256,
            "current_issue_scope_sha256": CURRENT_ISSUE_BODY_SHA256,
            "pin_inventory_sha256": PIN_SHA256,
            "inventory": {"candidate_count": 21, "contact_count": 10,
                          "complete_full_product_counts": {"NAM": 109, "AGO": 161},
                          "unique_matrix_rows": len(matrix)},
            "pair_operand_identity": "source-geometry mode uses consumed retained contacts; full-product mode uses complete same-release NAM/AGO products. They are distinct operands.",
            "contact_operand_checks": operand_checks, "verified_input_blobs": pins, "matrix": matrix,
            "limits": ["Planar longitude/latitude intersection areas are square-degree reproducibility metrics, not ground areas.",
                       "No territorial, legal, water, parent, or physical-component assignment is made.",
                       "The source's recorded vintage and license are not independent legal or authority determinations."]}


def main(mode: str, run_name: str):
    if not run_name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_name):
        raise ValueError("Run name must contain only ASCII letters, digits, hyphen, and underscore")
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    blobs, records, code_receipts = pinned_inputs(head)
    report = build_report(mode, head, blobs, records, code_receipts)
    vintage_root = OWNED / "vintages"
    if vintage_root.is_symlink() or not vintage_root.is_dir() or vintage_root.resolve() != vintage_root:
        raise ValueError("Output root must be an ordinary directory inside the owned packet")
    outdir = vintage_root / run_name
    if outdir.parent != vintage_root or outdir.exists() or outdir.is_symlink():
        raise ValueError("Output must be a fresh exclusive directory under the owned vintage root")
    outdir.mkdir(exist_ok=False)
    filename = "source-geometry-successor.json" if mode == "source-geometry" else "full-product-successor.json"
    output = (json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    target = outdir / filename
    with target.open("xb") as stream:
        stream.write(output)
    print(json.dumps({"path": str(target.relative_to(REPO)), "bytes": len(output), "sha256": sha(output),
                      "rows": report["inventory"]["unique_matrix_rows"], "mode": mode}, sort_keys=True))
