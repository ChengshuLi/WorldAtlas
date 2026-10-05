#!/usr/bin/env python3
"""Reproduce selected Natural Earth Admin-1 source records for issue #449.

This is an attribute/provenance extraction, not a boundary-accuracy test.
It checks whole-file hashes from source-register.json and reads DBF fields
without external GIS packages.
"""
import csv
import gzip
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source/natural-earth-admin1"
REGISTER = json.loads((SOURCE / "source-register.json").read_text())
DATASET = REGISTER["geometry_dataset"]

for name, entry in DATASET["files"].items():
    data = (SOURCE / name).read_bytes()
    assert len(data) == entry["bytes"], f"byte count mismatch: {name}"
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], f"SHA-256 mismatch: {name}"
for entry in REGISTER["files"]:
    stored_name = Path(entry["stored_path"]).name
    stored = (SOURCE / stored_name).read_bytes()
    assert len(stored) == entry["stored_bytes"], f"stored byte count mismatch: {stored_name}"
    assert hashlib.sha256(stored).hexdigest() == entry["stored_sha256"], f"stored SHA-256 mismatch: {stored_name}"
    data = gzip.decompress(stored)
    assert len(data) == entry["bytes"], f"raw byte count mismatch: {stored_name}"
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], f"raw SHA-256 mismatch: {stored_name}"

dbf = (SOURCE / "ne_10m_admin_1_states_provinces.dbf").read_bytes()
record_count = struct.unpack("<I", dbf[4:8])[0]
header_length, record_length = struct.unpack("<HH", dbf[8:12])
fields = []
offset = 32
while offset < header_length and dbf[offset] != 13:
    descriptor = dbf[offset:offset + 32]
    fields.append((descriptor[:11].split(b"\0", 1)[0].decode("ascii"), descriptor[16]))
    offset += 32
assert record_length == 1 + sum(width for _, width in fields)
assert header_length + record_count * record_length <= len(dbf)

rows = []
for ordinal in range(record_count):
    record = dbf[header_length + ordinal * record_length:header_length + (ordinal + 1) * record_length]
    pos = 1  # first byte is the DBF deletion marker
    values = {}
    for name, width in fields:
        values[name] = record[pos:pos + width].decode("utf-8", "replace").rstrip("\0 ").strip()
        pos += width
    if values.get("adm0_a3") == "CHN" and values.get("region") == "Southwest China":
        rows.append({
            "source_record_ordinal_zero_based": ordinal,
            "name_en": values.get("name_en", ""),
            "name_zh": values.get("name_zh", ""),
            "admin": values.get("admin", ""),
            "adm0_a3": values.get("adm0_a3", ""),
            "iso_3166_2": values.get("iso_3166_2", ""),
            "type_en": values.get("type_en", ""),
            "gadm_level": values.get("gadm_level", ""),
            "region": values.get("region", ""),
            "region_sub": values.get("region_sub", ""),
            "ne_id": values.get("ne_id", ""),
        })

expected = {"Chongqing", "Guizhou", "Sichuan", "Tibet", "Yunnan"}
assert {row["name_en"] for row in rows} == expected, "Southwest China source roster changed"
assert len(rows) == len(expected)
by_name = {row["name_en"]: row for row in rows}
assert by_name["Chongqing"]["type_en"] == "Municipality"
assert by_name["Guizhou"]["type_en"] == "Province"
assert by_name["Sichuan"]["type_en"] == "Province"
assert by_name["Tibet"]["type_en"] == "Autonomous Region"
assert by_name["Yunnan"]["type_en"] == "Province"

output = ROOT / "findings/natural-earth-admin1-southwest-china.csv"
with output.open("w", newline="") as fp:
    writer = csv.DictWriter(fp, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda row: row["name_en"]))

shp = (SOURCE / "ne_10m_admin_1_states_provinces.shp").read_bytes()
shx = (SOURCE / "ne_10m_admin_1_states_provinces.shx").read_bytes()
assert struct.unpack(">I", shp[:4])[0] == 9994
assert struct.unpack(">I", shx[:4])[0] == 9994
assert struct.unpack(">I", shp[24:28])[0] * 2 == len(shp)
assert struct.unpack("<I", shp[32:36])[0] == 5  # ESRI Polygon shapefile
shape_count = (len(shx) - 100) // 8
assert (len(shx) - 100) % 8 == 0 and shape_count == record_count
summary = {
    "issue": 449,
    "source_repository": DATASET["repository"],
    "source_commit": DATASET["commit"],
    "source_version_claim": DATASET["version"],
    "retained_source_file_count": len(DATASET["files"]) + len(REGISTER["files"]),
    "shapefile_geometry_type": "Polygon",
    "dbf_records": record_count,
    "shape_index_records": shape_count,
    "southwest_china_china_admin1_features": len(rows),
    "southwest_china_admin1_names": sorted(expected),
    "issue449_members_found": ["Chongqing", "Guizhou", "Sichuan"],
    "neighbor_packet_members_found": ["Tibet", "Yunnan"],
    "interpretation": "Natural Earth attributes these five first-order China units to Southwest China. This supports a source-defined regional grouping and component names/classes at the dataset's map vintage; it does not prove current legal status, official boundary correctness, the WorldAtlas area-tier design, coastline/fragment completeness, or geometry agreement with Atlas units.",
    "output": "data/regional-review/regional-review-365cbd6478904888/findings/natural-earth-admin1-southwest-china.csv",
}
(ROOT / "findings/natural-earth-admin1-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(summary, ensure_ascii=False))
