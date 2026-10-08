#!/usr/bin/env python3
"""Authenticated additive matrix reproduction for issue #1437.

Only writes a new, empty directory below this packet's vintages/ directory.
Original source files and historical reports are read-only inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from shapely.geometry import shape


REPO = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
INVENTORY = OWNED / "source-pin-inventory.json"
ISSUE_SNAPSHOT = OWNED / "sources/issue-1437-api-snapshot.json"
INVENTORY_SHA256 = "a6aa58da227bb7e9f12b48839fd7299d64396e85b831205c97a1d608fdeb5216"
ISSUE_BODY_SHA256 = "380c7a61e78319372ea00805ced0ab36370416f3b62b89f5d5fa1c994caf4e35"
COMPONENT_PATH = "research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson"
CONTACT_PATH = "research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson"
FULL_NAM_PATH = "research/geography/gap-source-namibia-angola-20261006/sources/geoBoundaries-NAM-ADM2-full-9469f09.geojson"
FULL_AGO_PATH = "research/geography/gap-source-namibia-angola-20261006/sources/geoBoundaries-AGO-ADM2-full-9469f09.geojson"
EXPECTED_CONTACT_IDS = {
    "gb:AGO:ADM2:16411231B14510444140190", "gb:AGO:ADM2:16411231B28551746118834",
    "gb:AGO:ADM2:16411231B36562728226085", "gb:NAM:ADM2:8085530B15355770078360",
    "gb:NAM:ADM2:8085530B25496891828693", "gb:NAM:ADM2:8085530B32015186497374",
    "gb:NAM:ADM2:8085530B43563455443088", "gb:NAM:ADM2:8085530B54610932550654",
    "gb:NAM:ADM2:8085530B8620298556926", "gb:NAM:ADM2:8085530B94702234009846",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned_blobs() -> tuple[dict[str, bytes], dict[str, dict]]:
    inv_raw = INVENTORY.read_bytes()
    if digest(inv_raw) != INVENTORY_SHA256:
        raise ValueError("Issue source-pin inventory differs from fixed digest")
    snapshot = json.loads(ISSUE_SNAPSHOT.read_bytes())
    if snapshot["body_sha256"] != ISSUE_BODY_SHA256 or digest(snapshot["body"].encode()) != ISSUE_BODY_SHA256:
        raise ValueError("Issue acceptance snapshot differs from fixed body digest")
    inv = json.loads(inv_raw)
    if inv["issue_body_sha256"] != ISSUE_BODY_SHA256 or len(inv["pins"]) != inv["declared_pin_count"]:
        raise ValueError("Issue pin inventory does not match the acceptance snapshot")
    blobs: dict[str, bytes] = {}
    rows: dict[str, dict] = {}
    for pin in inv["pins"]:
        raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{pin['commit']}:{pin['path']}"])
        if len(raw) != pin["bytes"] or digest(raw) != pin["sha256"]:
            raise ValueError("Pinned Git blob mismatch: " + pin["path"])
        if pin["path"] in blobs and blobs[pin["path"]] != raw:
            raise ValueError("Conflicting source vintages for one path")
        blobs[pin["path"]] = raw
        rows[pin["path"]] = pin
    return blobs, rows


def unique_index(rows, key, label):
    indexed = {}
    for row in rows:
        value = key(row)
        if not value or value in indexed:
            raise ValueError(f"Missing or duplicate {label}: {value!r}")
        indexed[value] = row
    return indexed


def contact_id(row):
    props = row.get("properties", {})
    return f"gb:{props.get('shapeGroup')}:ADM2:{props.get('shapeID')}"


def full_index(raw, group, expected_count):
    rows = json.loads(raw)["features"]
    selected = [r for r in rows if r.get("properties", {}).get("shapeGroup") == group]
    if len(selected) != expected_count:
        raise ValueError(f"{group} full product expected {expected_count} rows, got {len(selected)}")
    return unique_index(selected, lambda r: r.get("properties", {}).get("shapeID"), f"{group} shapeID")


def checked_shape(feature, label):
    geom = shape(feature.get("geometry"))
    if geom.is_empty or not geom.is_valid:
        raise ValueError(f"Empty or invalid geometry: {label}")
    return geom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_name", help="fresh output directory name")
    args = ap.parse_args()
    if not args.run_name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.run_name):
        raise ValueError("run_name must contain only letters, digits, hyphen, underscore")
    blobs, pins = pinned_blobs()
    components = json.loads(blobs[COMPONENT_PATH])["features"]
    contacts = json.loads(blobs[CONTACT_PATH])["features"]
    component_rows = unique_index(components, lambda r: r.get("id"), "component ID")
    contact_rows = unique_index(contacts, contact_id, "contact subject ID")
    if len(component_rows) != 21 or set(contact_rows) != EXPECTED_CONTACT_IDS or len(contact_rows) != 10:
        raise ValueError("Complete candidate/contact inventory differs from issue-pinned membership")
    nam_full = full_index(blobs[FULL_NAM_PATH], "NAM", 109)
    ago_full = full_index(blobs[FULL_AGO_PATH], "AGO", 161)
    matrix = []
    different = 0
    for component_id, candidate in sorted(component_rows.items()):
        candidate_geom = checked_shape(candidate, component_id)
        for subject_id, contact in sorted(contact_rows.items()):
            props = contact["properties"]
            group, sid = props["shapeGroup"], props["shapeID"]
            same_id_full = (nam_full if group == "NAM" else ago_full)[sid]
            consumed_geom = checked_shape(contact, subject_id + " consumed")
            full_geom = checked_shape(same_id_full, subject_id + " full")
            consumed_area = candidate_geom.intersection(consumed_geom).area
            full_area = candidate_geom.intersection(full_geom).area
            changed = consumed_area != full_area
            different += int(changed)
            matrix.append({"component_id": component_id, "contact_subject_id": subject_id,
                           "consumed_operand": f"{group} ADM2 represented vintage {2007 if group == 'NAM' else 2018}",
                           "same_release_full_operand": "geoBoundaries release 9469f09592ced973a3448cf66b6100b741b64c0d",
                           "consumed_intersection_area_square_degrees": consumed_area,
                           "full_intersection_area_square_degrees": full_area,
                           "area_differs": changed,
                           "consumed_vs_full_topologically_equal": consumed_geom.equals(full_geom)})
    keys = [(r["component_id"], r["contact_subject_id"]) for r in matrix]
    if len(matrix) != 210 or len(set(keys)) != 210:
        raise ValueError("Matrix is not exactly 210 unique candidate/contact pairs")
    report = {
        "version": 1,
        "issue": 1437,
        "issue_body_sha256": ISSUE_BODY_SHA256,
        "pin_inventory_sha256": INVENTORY_SHA256,
        "pair_operand_statement": "The consumed matrix uses retained simplified source-contact-features.geojson geometries. Same-release full product geometries are computed as a separate explicitly named operand.",
        "inventory": {"components": len(component_rows), "contacts": len(contact_rows), "unique_pairs": len(matrix),
                      "full_product_rows": {"NAM": 109, "AGO": 161}},
        "different_contact_shapes": sum(
            not checked_shape(contact, "contact topology control").equals(
                checked_shape((nam_full if contact["properties"]["shapeGroup"] == "NAM" else ago_full)[contact["properties"]["shapeID"]], "full topology control")
            ) for contact in contact_rows.values()
        ),
        "pairs_with_different_intersection_area": different,
        "source_blobs": [{"path": p, "commit": pins[p]["commit"], "bytes": len(blobs[p]), "sha256": digest(blobs[p])}
                         for p in [COMPONENT_PATH, CONTACT_PATH, FULL_NAM_PATH, FULL_AGO_PATH]],
        "matrix": matrix,
        "limits": ["Planar square-degree intersections are reproduction metrics, not area on the ground.",
                   "No territorial, legal, water, parent, or physical-component assignment is made.",
                   "Source license labels and represented vintages are transcribed from pinned metadata; this run is not legal review."],
    }
    vintage_root = OWNED / "vintages"
    if vintage_root.is_symlink() or not vintage_root.is_dir() or vintage_root.resolve() != vintage_root:
        raise ValueError("Vintage output root must be an ordinary directory inside the owned packet")
    outdir = vintage_root / args.run_name
    if outdir.resolve(strict=False).parent != vintage_root:
        raise ValueError("Output path escapes the owned vintage directory")
    outdir.mkdir(exist_ok=False)
    output = (json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    target = outdir / "authenticated-matrix.json"
    with target.open("xb") as stream:
        stream.write(output)
    print(json.dumps({"path": str(target.relative_to(REPO)), "bytes": len(output), "sha256": digest(output),
                      "pairs": len(matrix), "changed_area_pairs": different,
                      "different_contact_shapes": report["different_contact_shapes"]}, sort_keys=True))


if __name__ == "__main__":
    main()
