#!/usr/bin/env python3
"""Screen every assigned v5 location against GSHHG full-resolution land records."""
from __future__ import annotations
import gzip, hashlib, json, math, pathlib, struct, sys
from shapely.geometry import shape, Point

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE_SHA = "28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc"  # checked below from the full published archive
MEMBER_SHA = "af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6"
if len(sys.argv) != 2:
    raise SystemExit("usage: screen-gshhg.py /path/to/gshhs_f.b")
data = pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(data).hexdigest() != MEMBER_SHA:
    raise SystemExit("GSHHG member hash mismatch")
scope = json.loads((HERE / "issue-scope.json").read_text())
ids = scope["member_location_ids"]
index = json.loads((ROOT / "data/world-index.json").read_text())
features = {}
for part in index["parts"]:
    for f in json.loads((ROOT / "data" / part).read_text())["features"]:
        if f["id"] in ids:
            features[f["id"]] = f
if set(features) != set(ids):
    raise SystemExit("current v5 feature set differs from issue scope")
units = {}
for i, f in features.items():
    g = shape(f["geometry"])
    units[i] = {"name": f["properties"]["name"], "geom": g, "bbox": g.bounds, "count": 0, "source_records": []}
# Candidate spatial bins at 2 degrees, used only to avoid irrelevant global records.
bins = {}
for i, u in units.items():
    x1, y1, x2, y2 = u["bbox"]
    for gx in range(math.floor(x1 / 2), math.floor(x2 / 2) + 1):
        for gy in range(math.floor(y1 / 2), math.floor(y2 / 2) + 1):
            bins.setdefault((gx, gy), set()).add(i)

def record_centroid(coords):
    # For these GSHHG closed exterior rings, the standard shoelace centroid is
    # a stable representative for a presence screen; it is not a shoreline proof.
    a = sx = sy = 0.0
    for j, (x, y) in enumerate(coords):
        x2, y2 = coords[(j + 1) % len(coords)]
        cross = x * y2 - x2 * y
        a += cross
        sx += (x + x2) * cross
        sy += (y + y2) * cross
    if abs(a) < 1e-14:
        return sum(p[0] for p in coords) / len(coords), sum(p[1] for p in coords) / len(coords)
    return sx / (3 * a), sy / (3 * a)

pos = total = level1 = 0
matched = []
while pos < len(data):
    lid, n, flag, west, east, south, north, area, area_full, container, ancestor = struct.unpack_from(">IIIiiiiIIii", data, pos)
    start = pos
    pos += 44
    end = pos + n * 8
    if end > len(data):
        raise SystemExit("truncated GSHHG record")
    total += 1
    level = flag & 255
    if level == 1:
        level1 += 1
        west /= 1e6; east /= 1e6; south /= 1e6; north /= 1e6
        if west >= 180: west -= 360; east -= 360
        candidates = set()
        for gx in range(math.floor(west / 2), math.floor(east / 2) + 1):
            for gy in range(math.floor(south / 2), math.floor(north / 2) + 1):
                candidates.update(bins.get((gx, gy), ()))
        maybe = [i for i in candidates if west <= units[i]["bbox"][2] and east >= units[i]["bbox"][0] and south <= units[i]["bbox"][3] and north >= units[i]["bbox"][1]]
        if maybe:
            coords = [struct.unpack_from(">ii", data, pos + j * 8) for j in range(n)]
            coords = [(x / 1e6 - (360 if x / 1e6 > 180 else 0), y / 1e6) for x, y in coords]
            point = record_centroid(coords)
            hit = [i for i in maybe if units[i]["geom"].covers(Point(point))]
            for i in hit:
                units[i]["count"] += 1
                units[i]["source_records"].append(lid)
            if hit:
                matched.append({"id": lid, "point": point, "hits": sorted(hit), "record": data[start:end]})
    pos = end

raw = b"".join(x["record"] for x in matched)
packed = gzip.compress(raw, mtime=0)
(HERE / "sources/gshhg-scope-land-candidates.bin.gz").write_bytes(packed)
report = {
    "source": {
        "title": "GSHHG full-resolution global shoreline database, version 2.3.7",
        "authors": "Paul Wessel and Walter H. F. Smith, University of Hawaii / NOAA",
        "release_date": "2017-06-15",
        "archive_url": "https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip",
        "archive_sha256": "28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc","member": "gshhs_f.b",
        "member_bytes": len(data), "member_sha256": hashlib.sha256(data).hexdigest(),
        "license": "LGPLv3 or later; exact notice retained in sources/gshhg-LGPL.txt",
        "restoration": "Download the pinned archive, verify its SHA-256, extract gshhs_f.b, and verify member SHA-256."
    },
    "scope_count": len(units), "source_level1_record_count": level1, "source_total_record_count": total,
    "retained": {"path": "sources/gshhg-scope-land-candidates.bin.gz", "record_count": len(matched), "uncompressed_bytes": len(raw), "uncompressed_sha256": hashlib.sha256(raw).hexdigest(), "compressed_bytes": len(packed), "compressed_sha256": hashlib.sha256(packed).hexdigest()},
    "method": "Scan every source record in the complete GSHHG 2.3.7 binary. For each level-1 physical-land record whose bbox intersects at least one assigned location bbox, compute the closed ring shoelace centroid and test it against all bbox-compatible current location geometries (including holes). Retain the full source record when its centroid is covered by one or more assigned locations.",
    "interpretation": "A hit shows only that the centroid of one 2017 GSHHG physical-land polygon falls inside an assigned current feature. It does not certify shoreline completeness, island identity, administrative membership, or absence of omitted land. A zero hit is not proof of omitted land; feature geometry is not changed.",
    "per_location": {i: {"name": u["name"], "current_geometry_type": units[i]["geom"].geom_type, "current_geometry_components": len(units[i]["geom"].geoms) if units[i]["geom"].geom_type == "MultiPolygon" else 1, "gshhg_level1_centroid_hits": u["count"], "gshhg_record_ids": sorted(u["source_records"])} for i, u in units.items()},
    "summary": {"locations_with_one_or_more_GSHHG_centroid_hits": sum(u["count"] > 0 for u in units.values()), "locations_without_GSHHG_centroid_hits": [i for i, u in units.items() if not u["count"]]}
}
(HERE / "gshhg-screen.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
