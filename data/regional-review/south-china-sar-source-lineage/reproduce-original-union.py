#!/usr/bin/env python3
"""Bounded replay of the historical semantic-locations merge for HKG/MAC."""
import hashlib
import json
import pathlib
import struct
import subprocess
import sys

from shapely import __version__ as shapely_version
from shapely import make_valid, union_all
from shapely.geometry import Polygon, mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[3]
BASELINE = "d43cce74959376d8ef052afd3fd09e875bb08938"
CODE_COMMIT = "4bdba3d40acc2d725e4aeb54c3b9aab559a91469"
NE_DIR = ROOT / "data/regional-review/regional-review-365cbd6478904888/source/natural-earth-admin1"
GB_PATH = ROOT / "data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-chn-adm2-2017.geojson"
OUT = pathlib.Path(__file__).with_name("original-union-results.json")

def sha(data): return hashlib.sha256(data).hexdigest()

def dbf_rows(path):
    data = path.read_bytes()
    count, header_len, rec_len = struct.unpack_from("<IHH", data, 4)
    fields, offset = [], 32
    while data[offset] != 0x0d:
        raw = data[offset:offset + 32]
        fields.append((raw[:11].split(b"\0", 1)[0].decode("ascii"), raw[16]))
        offset += 32
    rows = []
    for i in range(count):
        off = header_len + i * rec_len + 1
        row = {}
        for name, size in fields:
            row[name] = data[off:off + size].decode("utf8").strip(" \0")
            off += size
        row["__index"] = i
        rows.append(row)
    return rows

def shp_geometries(shp_path, shx_path):
    shp, shx = shp_path.read_bytes(), shx_path.read_bytes()
    count = (len(shx) - 100) // 8
    result = []
    for i in range(count):
        off_words, length_words = struct.unpack_from(">ii", shx, 100 + i * 8)
        off, length = off_words * 2, length_words * 2
        stype = struct.unpack_from("<i", shp, off + 8)[0]
        if stype != 5: raise ValueError(f"Unexpected shapefile record type {stype}")
        content = off + 12
        nparts, npoints = struct.unpack_from("<ii", shp, content + 32)
        part_offsets = struct.unpack_from("<" + "i" * nparts, shp, content + 40)
        points_at = content + 40 + 4 * nparts
        coords = [struct.unpack_from("<dd", shp, points_at + j * 16) for j in range(npoints)]
        ends = list(part_offsets[1:]) + [npoints]
        rings = [coords[a:b] for a, b in zip(part_offsets, ends)]
        # ESRI polygon ring orientation: clockwise shells, counter-clockwise holes.
        polys, holes = [], []
        for ring in rings:
            area = sum((b[0] - a[0]) * (b[1] + a[1]) for a, b in zip(ring, ring[1:]))
            (polys if area > 0 else holes).append(ring)
        # Shapely's make_valid/union are the material transformation in the original.
        # Ring containment assigns holes robustly for the small target feature set.
        from shapely.geometry import LinearRing
        shells = [Polygon(r) for r in polys]
        assigned = [[] for _ in shells]
        for hole in holes:
            h = Polygon(hole)
            candidates = [j for j, shell in enumerate(shells) if shell.covers(h.representative_point())]
            if candidates: assigned[min(candidates, key=lambda j: shells[j].area)].append(hole)
        result.append(Polygon(shells[0].exterior.coords, assigned[0]) if len(shells) == 1 else
                      __import__('shapely').geometry.MultiPolygon([Polygon(s.exterior.coords, assigned[j]) for j, s in enumerate(shells)]))
    return result

def polygon(g):
    if g.is_empty: return Polygon()
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    return union_all([polygon(p) for p in g.geoms])

def facts(g):
    obj = mapping(g)
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
    return {"type": g.geom_type, "valid": bool(g.is_valid), "area_degrees2": g.area,
            "bounds_wgs84_lonlat": list(g.bounds), "position_count": sum(1 for _ in coords(obj["coordinates"])),
            "geometry_json_sha256": sha(raw), "geometry": obj}

def coords(value):
    if isinstance(value, (tuple, list)) and len(value) >= 2 and isinstance(value[0], (int, float)):
        yield value
    elif isinstance(value, (tuple, list)):
        for child in value: yield from coords(child)

def main():
    stem = NE_DIR / "ne_10m_admin_1_states_provinces"
    rows = dbf_rows(stem.with_suffix(".dbf"))
    geoms = shp_geometries(stem.with_suffix(".shp"), stem.with_suffix(".shx"))
    if len(rows) != len(geoms): raise ValueError("SHP/SHX/DBF counts differ")
    hkg = [geoms[r["__index"]] for r in rows if r["adm0_a3"] == "HKG"]
    mac_ne = [geoms[r["__index"]] for r in rows if r["adm1_code"] == "MAC+00?"]
    gb_doc = json.loads(GB_PATH.read_text())
    gb = [shape(f["geometry"]) for f in gb_doc["features"] if f["properties"].get("shapeID") == "17275852B34966799109471"]
    if len(hkg) != 18 or len(mac_ne) != 1 or len(gb) != 1:
        raise ValueError(f"Unexpected source member counts: HKG={len(hkg)} MAC-NE={len(mac_ne)} MAC-GB={len(gb)}")
    baseline = json.loads(subprocess.check_output(["git", "show", f"{BASELINE}:data/geography/part-28.json"], cwd=ROOT))
    atlas = {f["properties"]["id"]: f for f in baseline["features"]}
    subjects = {}
    for ident, members in (("atlas:territory:HKG", hkg), ("atlas:territory:MAC", mac_ne + gb)):
        # Mirrors historical merge(): polygon(make_valid(union_all(geoms))).
        merged = polygon(make_valid(union_all(members)))
        expected = shape(atlas[ident]["geometry"])
        actual_facts, expected_facts = facts(merged), facts(expected)
        subjects[ident] = {
            "selected_member_count": len(members),
            "member_bounds": [list(g.bounds) for g in members],
            "replayed_union": {k:v for k,v in actual_facts.items() if k != "geometry"},
            "baseline_atlas": {k:v for k,v in expected_facts.items() if k != "geometry"},
            "topologically_equals_baseline": bool(merged.equals(expected)),
            "symmetric_difference_area_degrees2": float(merged.symmetric_difference(expected).area),
            "hausdorff_distance_degrees": float(merged.hausdorff_distance(expected)),
        }
    result = {"schema_version": 1, "historical_code": {"path":"scripts/semantic-locations.py", "commit":CODE_COMMIT,
              "sha256":"ac18022fa1c881bdbedc590f150a501ad23d52ba86cb47c5a005643012f1ad1a",
              "merge_operation":"polygon(make_valid(union_all([geoms[i] for i in indices])))"},
              "source_vintage_limit":"The historical cache input.geojson used by CODE_COMMIT was untracked and is not present in the parent commit. This bounded replay uses retained Natural Earth shapefile source and retained 2017 geoBoundaries bytes; it does not claim byte-identical historical inputs.",
              "runtime":{"python":sys.version.split()[0],"shapely":shapely_version},
              "sources":{"natural_earth_admin1_commit":"ca96624a56bd078437bca8184e78163e5039ad19", "geoboundaries_sha256":sha(GB_PATH.read_bytes()), "baseline_commit":BASELINE},
              "subjects":subjects}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "subjects"}, indent=2))
    print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk not in ("replayed_union", "baseline_atlas", "member_bounds")} for k,v in subjects.items()}, indent=2))

if __name__ == "__main__": main()
