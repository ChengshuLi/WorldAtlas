#!/usr/bin/env python3
"""Read-only source, geometry, settlement and parent checks for issue #527."""
from __future__ import annotations
import gzip, hashlib, io, json, re, struct, subprocess, tarfile, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
A = json.loads((HERE / "assessment.json").read_text())
BASE = ROOT / "data/macro-improvements"
PREP = BASE / "three-island-restoration"
COV = BASE / "macro-coverage-africa-americas"
sha = lambda b: hashlib.sha256(b).hexdigest()

def run(args):
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)

def parse_wkb(data, offset=0):
    endian = data[offset]
    order = "<" if endian == 1 else ">"
    offset += 1
    typ = struct.unpack_from(order + "I", data, offset)[0]
    offset += 4
    if typ == 6:  # MultiPolygon
        count = struct.unpack_from(order + "I", data, offset)[0]
        offset += 4
        polys = []
        for _ in range(count):
            child, offset = parse_wkb(data, offset)
            assert child["type"] == "Polygon"
            polys.append(child["coordinates"])
        return {"type": "MultiPolygon", "coordinates": polys}, offset
    if typ == 3:  # Polygon
        rings_n = struct.unpack_from(order + "I", data, offset)[0]
        offset += 4
        rings = []
        for _ in range(rings_n):
            points_n = struct.unpack_from(order + "I", data, offset)[0]
            offset += 4
            xy = struct.unpack_from(order + "d" * (2 * points_n), data, offset)
            offset += 16 * points_n
            ring = list(zip(xy[::2], xy[1::2]))
            assert len(ring) >= 4 and ring[0] == ring[-1]
            rings.append([[x, y] for x, y in ring])
        return {"type": "Polygon", "coordinates": rings}, offset
    raise AssertionError(f"Unexpected WKB type {typ}")

def polygons(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    return geometry["coordinates"]

def in_ring(point, ring):
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1:
            inside = not inside
    return inside

def covers_point(point, geom):
    return any(in_ring(point, p[0]) and not any(in_ring(point, h) for h in p[1:]) for p in polygons(geom))

def bbox(geom):
    pts = [xy for p in polygons(geom) for r in p for xy in r]
    return min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)

class sqlite_db:
    """Create a private GPKG containing one OSM admin relation and candidate land."""
    def __init__(self, path, admin_path, land_path):
        self.path, self.admin_path, self.land_path = path, admin_path, land_path
    def __enter__(self):
        run(["ogr2ogr", "-f", "GPKG", str(self.path), str(self.admin_path), "-nln", "admin"])
        run(["ogr2ogr", "-f", "GPKG", "-update", str(self.path), str(self.land_path), "-nln", "land"])
        return self.path
    def __exit__(self, *_):
        return False

# Check every byte declared by the upstream preparation manifest before use.
manifest = json.loads((PREP / "manifest.json").read_text())
for rel, proof in manifest["files"].items():
    raw = (PREP / rel).read_bytes()
    assert len(raw) == proof["bytes"] and sha(raw) == proof["sha256"], rel
proposal = json.loads((PREP / "proposal.json").read_text())
for rel, expected in proposal["source_inputs"].items():
    assert sha((ROOT / rel).read_bytes()) == expected, rel
assert sha((PREP / "water-review.json").read_bytes()) == A["source_geometry_accounting"]["osm_water_source_review_sha256"]

# Match both source-profile identities to exact original GeoNames rows.
geo_tar_path = COV / "geonames-country-dumps.tar.gz"
with tarfile.open(geo_tar_path) as tf:
    member = next(m for m in tf if m.name.endswith("/GL.zip"))
    gl_zip_bytes = tf.extractfile(member).read()
assert sha(gl_zip_bytes) == "2acb73eb045dabfa2d9d84b9132372a55f51a5fcd8a895777e31fc41036994ae"
with zipfile.ZipFile(io.BytesIO(gl_zip_bytes)) as zf:
    rows = [line.split("\t") for line in zf.read("GL.txt").decode("utf-8").splitlines()]
by_id = {row[0]: row for row in rows}
for slug, target in (("disko", A["source_geometry_accounting"]["disko"]), ("milne-land", A["source_geometry_accounting"]["milne_land"])):
    ident = target["location_id"].rsplit(":", 1)[1]
    expected = target["geonames_row"]
    assert by_id[ident] == expected and expected[6:8] == ["T", "ISL"]
    assert int(expected[18][:4]) <= 2022

# Account for every source exterior/interior ring and all in-footprint GeoNames PPL/PPLQ entries.
expected_ppl = {"disko": ["3419009", "3419818", "3420388", "3420635", "3421745", "3422467", "3423734", "3424030"], "milne-land": []}
metrics = {}
for slug, key in (("disko", "disko"), ("milne-land", "milne_land")):
    target = A["source_geometry_accounting"][key]
    raw = gzip.decompress((ROOT / target["source_geometry"]["dry_land_wkb_path"]).read_bytes())
    geom, end = parse_wkb(raw)
    assert end == len(raw) and sha(raw) == target["source_geometry"]["dry_land_uncompressed_sha256"]
    ps = polygons(geom)
    assert len(ps) == target["source_geometry"]["polygon_components"]
    assert sum(len(p) for p in ps) == target["source_geometry"]["exterior_rings"] + target["source_geometry"]["interior_rings"]
    hits = sorted(r[0] for r in rows if r[6] == "P" and r[7].startswith("PPL") and covers_point((float(r[5]), float(r[4])), geom))
    assert hits == expected_ppl[slug], (slug, hits)
    metrics[slug] = {"components": len(ps), "rings": sum(len(p) for p in ps), "bbox": bbox(geom), "geonames_populated_records": hits}

# Export exact current OSM admin relations, verify full prepared land containment,
# and audit only town/village/hamlet/isolated-dwelling points inside the land.
pbf = COV / "osm/greenland-latest.osm.pbf"
expected_places = {"disko": ["12319028603", "13149571506", "14155852267", "2049649017", "2051281220", "996562205"], "milne-land": []}
for slug, key, relation_id, wanted_name in (("disko", "disko", "8514395", "Qeqertalik"), ("milne-land", "milne_land", "8515166", "Sermersooq")):
    target = A["source_geometry_accounting"][key]
    raw = gzip.decompress((ROOT / target["source_geometry"]["dry_land_wkb_path"]).read_bytes())
    geom, _ = parse_wkb(raw)
    xmin, ymin, xmax, ymax = bbox(geom)
    with tempfile.TemporaryDirectory(prefix="worldatlas-527-") as td:
        td = Path(td)
        land_path = td / "land.geojson"
        land_path.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"name": slug}, "geometry": geom}]}))
        admin_path = td / "admin.geojson"
        run(["ogr2ogr", "-f", "GeoJSON", str(admin_path), str(pbf), "multipolygons", "-where", f"osm_id = '{relation_id}'", "-select", "osm_id,name,boundary,admin_level,other_tags"])
        admin = json.loads(admin_path.read_text())
        assert len(admin["features"]) == 1
        props = admin["features"][0]["properties"]
        assert props["name"] == wanted_name and props["boundary"] == "administrative" and props["admin_level"] == "4"
        with sqlite_db(td / "relations.gpkg", admin_path, land_path) as gpkg:
            result = run(["ogrinfo", "-ro", "-dialect", "SQLITE", "-sql", "SELECT ST_Contains(admin.geom,land.geom) AS contains FROM admin,land", str(gpkg)]).stdout
            assert re.search(r"contains \(Integer\) = 1", result), (slug, result)
        places_json = run(["ogrinfo", "-ro", "-json", "-al", "-features", "-geom=YES", "-spat", str(xmin), str(ymin), str(xmax), str(ymax), "-where", "place IN ('city','town','village','hamlet','isolated_dwelling')", str(pbf), "points"]).stdout
        features = json.loads(places_json)["layers"][0].get("features", [])
        inside = sorted(str(f["fid"]) for f in features if covers_point(tuple(f["geometry"]["coordinates"]), geom))
        assert inside == expected_places[slug], (slug, inside)
        metrics[slug]["osm_place_ids"] = inside
        metrics[slug]["admin_relation"] = {"id": relation_id, "name": wanted_name, "contains_candidate": True}

# Confirm both pinned subjects and their parents in the current core index.
target_ids = set(A["scope"]["member_location_ids"])
h = {x["id"]: x for x in json.loads((ROOT / "data/hierarchy.json").read_text())}
locs = {}
for part in json.loads((ROOT / "data/world-index.json").read_text())["parts"]:
    for f in json.loads((ROOT / "data" / part).read_text())["features"]:
        locs[f["properties"]["id"]] = f["properties"]
assert target_ids.issubset(locs)
assert locs["atlas:island:geonames:3420645"]["parent_id"] == "framework:province:qeqertalik:321d544aeeb4"
assert locs["atlas:island:geonames:3421886"]["parent_id"] == "framework:province:sermersooq:8f8dcd86dde0"
area = "framework:area:greenland:0f042de27bac"
provinces = {x["id"] for x in h.values() if x.get("parent_id") == area}
assert len(provinces) == 6
current_area_locations = []
for ident, loc in locs.items():
    p = loc.get("parent_id")
    while p in h and p != area:
        p = h[p].get("parent_id")
    if p == area:
        current_area_locations.append(ident)
assert len(current_area_locations) == 13
for province, count in (("framework:province:qeqertalik:321d544aeeb4", 2), ("framework:province:sermersooq:8f8dcd86dde0", 3)):
    assert sum(x.get("parent_id") == province for x in locs.values()) == count
    assert h[province]["parent_id"] == area
    assert h[area]["parent_id"] == "framework:region:subarctic-america:4a2093d6d3b9"
expected_chains = {
    "atlas:island:geonames:3420645": ["framework:province:qeqertalik:321d544aeeb4", area, "framework:region:subarctic-america:4a2093d6d3b9", "framework:subcontinent:northern-america:477e054b32f2", "framework:continent:north-america:1ca27616f338"],
    "atlas:island:geonames:3421886": ["framework:province:sermersooq:8f8dcd86dde0", area, "framework:region:subarctic-america:4a2093d6d3b9", "framework:subcontinent:northern-america:477e054b32f2", "framework:continent:north-america:1ca27616f338"]
}
for ident, expected in expected_chains.items():
    chain, parent = [], locs[ident]["parent_id"]
    while parent in h:
        chain.append(parent)
        parent = h[parent].get("parent_id")
    assert chain == expected, (ident, chain)
region = "framework:region:subarctic-america:4a2093d6d3b9"
region_locations = []
for ident, loc in locs.items():
    parent = loc.get("parent_id")
    while parent in h and parent != region:
        parent = h[parent].get("parent_id")
    if parent == region:
        region_locations.append(ident)
assert len(region_locations) == 127

print("PASS: upstream source manifest and pinned PBF/GeoNames hashes; exact 2/2 GeoNames island rows; all 367 exterior/interior rings and all in-footprint PPL/PPLQ records; current OSM administrative relation containment; all mapped inhabited-place point candidates; 6 province/13 current-location parent accounting; both subjects present in core index")
print(json.dumps(metrics, separators=(",", ":")))
