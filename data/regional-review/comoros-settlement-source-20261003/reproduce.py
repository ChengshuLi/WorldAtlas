#!/usr/bin/env python3
"""Reproduce the bounded OCHA COD-AB administrative reference crosswalk.

This deliberately does not extract or infer settlement coordinates. It reads
the immutable source archive already retained by predecessor issue #482.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import zipfile

PACKET = pathlib.Path(__file__).resolve().parent
REPO = PACKET.parents[2]
SOURCE = (
    REPO
    / "data/regional-review/regional-review-4f180b98473f1071/sources"
    / "com_admin_boundaries.geojson.zip"
)
SOURCE_SHA256 = "c094bd9fe28236deaf22403ad86c9d576cd8b0b087c8d7cb428bea44b47a4573"
OUTPUT = PACKET / "administrative-crosswalk.csv"
FIELDS = [
    "crosswalk_level",
    "unit_pcode",
    "unit_name",
    "parent_pcode",
    "parent_name",
    "island_pcode",
    "island_name",
    "valid_on",
    "source_role",
]


def source_features(archive: zipfile.ZipFile, filename: str) -> list[dict]:
    document = json.loads(archive.read(filename))
    return document["features"]


def rows_from_source() -> list[dict[str, str]]:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"COD-AB source hash mismatch: {digest}")

    with zipfile.ZipFile(SOURCE) as archive:
        islands = source_features(archive, "com_admin1.geojson")
        districts = source_features(archive, "com_admin2.geojson")
        communes = source_features(archive, "com_admin3.geojson")

    if (len(islands), len(districts), len(communes)) != (3, 17, 55):
        raise SystemExit(
            "COD-AB feature count changed: "
            f"ADM1={len(islands)}, ADM2={len(districts)}, ADM3={len(communes)}"
        )

    by_island = {f["properties"]["adm1_pcode"]: f["properties"] for f in islands}
    by_district = {f["properties"]["adm2_pcode"]: f["properties"] for f in districts}
    if len(by_island) != 3 or len(by_district) != 17:
        raise SystemExit("Duplicate island or district p-code")

    rows: list[dict[str, str]] = []
    for feature in islands:
        p = feature["properties"]
        rows.append(
            {
                "crosswalk_level": "ADM1_island",
                "unit_pcode": p["adm1_pcode"],
                "unit_name": p["adm1_name"],
                "parent_pcode": p["adm0_pcode"],
                "parent_name": p["adm0_name"],
                "island_pcode": p["adm1_pcode"],
                "island_name": p["adm1_name"],
                "valid_on": p["valid_on"],
                "source_role": "administrative-unit reference; not a settlement",
            }
        )

    for feature in districts:
        p = feature["properties"]
        if p["adm1_pcode"] not in by_island:
            raise SystemExit(f"Unmatched island parent for {p['adm2_pcode']}")
        rows.append(
            {
                "crosswalk_level": "ADM2_prefecture",
                "unit_pcode": p["adm2_pcode"],
                "unit_name": p["adm2_name"],
                "parent_pcode": p["adm1_pcode"],
                "parent_name": p["adm1_name"],
                "island_pcode": p["adm1_pcode"],
                "island_name": p["adm1_name"],
                "valid_on": p["valid_on"],
                "source_role": "administrative-unit reference; not a settlement",
            }
        )

    for feature in communes:
        p = feature["properties"]
        island = by_island.get(p["adm1_pcode"])
        district = by_district.get(p["adm2_pcode"])
        if island is None or district is None:
            raise SystemExit(f"Missing parent for {p['adm3_pcode']}")
        if district["adm1_pcode"] != p["adm1_pcode"]:
            raise SystemExit(f"Parent chain mismatch for {p['adm3_pcode']}")
        rows.append(
            {
                "crosswalk_level": "ADM3_commune",
                "unit_pcode": p["adm3_pcode"],
                "unit_name": p["adm3_name"],
                "parent_pcode": p["adm2_pcode"],
                "parent_name": p["adm2_name"],
                "island_pcode": p["adm1_pcode"],
                "island_name": island["adm1_name"],
                "valid_on": p["valid_on"],
                "source_role": "administrative-unit reference; not a settlement",
            }
        )

    return sorted(rows, key=lambda row: (row["crosswalk_level"], row["unit_pcode"]))


def render(rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the fixed packet output")
    args = parser.parse_args()
    rows = rows_from_source()
    output = render(rows)
    if args.write:
        if OUTPUT.exists():
            raise SystemExit(f"Refusing to overwrite existing output: {OUTPUT}")
        OUTPUT.write_bytes(output)
        print(f"wrote {OUTPUT.relative_to(REPO)} sha256={hashlib.sha256(output).hexdigest()}")
    else:
        if not OUTPUT.exists():
            raise SystemExit("Output missing; run with --write once")
        existing = OUTPUT.read_bytes()
        if existing != output:
            raise SystemExit("Output differs from reproducible source extraction")
        counts = {}
        for row in rows:
            counts[row["crosswalk_level"]] = counts.get(row["crosswalk_level"], 0) + 1
        print(
            "crosswalk reproduces; "
            + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
            + f"; sha256={hashlib.sha256(existing).hexdigest()}"
        )


if __name__ == "__main__":
    main()
