#!/usr/bin/env python3
"""Reproduce the pinned BC–Washington IBC section 25 sample ledger.

IBC archive bytes are mapping-only and restricted. Supply a temporary copy of
the official archive; this program checks its complete size and SHA-256 before
reading any geographic inputs. It never writes archive bytes into the packet.
"""
import argparse
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path

BASELINE = "a1fd3383e89dea4c4497bf3a6f469494871ad758"
IBC_SIZE = 258764
IBC_SHA256 = "eb327459528b87cbc27e55ccc6bfd6982562c75559823a00b6dc50c04abcaab1"
PREFIX = "data/regional-review/regional-review-4254da254d94f450/"
OUT = Path(__file__).resolve().parent / "reproduced-assessment.json"
PINS = {
    "data/world-index.json": (944, "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03"),
    "data/hierarchy.json": (10165703, "03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d"),
    "data/geography/part-27.json": (4863162, "e8df7555853e9262162c5e5d5c85e5c30be3fa8f0e6339bafec0e08323054758"),
    "data/geography/part-29.json": (12932167, "077e3bdfb18a42318e27bad840bba823a5049ced449407584fb4b9be2ef67c7a"),
    PREFIX + "scope.json": (19009, "eeeba48c2ac959c2304b31f2008251b2dd8b34751d9aab1b9735d825532bf055"),
    PREFIX + "sources/current-parent-chains.json.gz": (106481, "aa0c1643d376baa9b7478d26886510718d3c0e242782df004e2defd028938290"),
    PREFIX + "sources/current-scope-and-parents.geojson.gz": (280642, "7ac3154985ef3bf5aae5b978481233e3a73c0ef6b2a753e1c7a15cef4c9302bb"),
    PREFIX + "sources/statistics-canada-bc-census-divisions-2021.geojson.gz": (38880150, "8a31cf19ad0694638c88275fec9ff1005970cd8600ca6baed245b8826756e9bf"),
    PREFIX + "sources/tigerline-2024-washington-counties.geojson.gz": (859249, "74c2822d327082e2738a8d93d59bc5eadf42590f7fef0941221e61deb36a4034"),
    "data/regional-review/bc-washington-coastal-edge-followup-2026/sample-assessment.json": (14978, "0f5f8d1a742032c149ce47a8aae01442cc1a5c5dc2e9b6719e11ae2f7080df13"),
}
SUBJECTS = {
    "atlas:district:CAN-5915:BRC": "framework:province:british-columbia:83abeaaac0ca",
    "gb:USA:ADM2:52423323B9068998137459": "framework:province:washington:b01ae89096c9",
    "gb:USA:ADM2:52423323B32782252789959": "framework:province:washington:b01ae89096c9",
}


def blob(commit, path):
    return subprocess.run(["git", "show", f"{commit}:{path}"], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def load_json(raw):
    return json.loads(raw)


def baseline_bytes(commit):
    if commit != BASELINE:
        raise ValueError(f"refusing unpinned baseline commit: {commit}")
    out = {}
    for path, (size, digest) in PINS.items():
        raw = blob(commit, path)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"baseline size/hash mismatch: {path}")
        out[path] = raw
    return out


def project(geometry, ogr, osr):
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    target.ImportFromEPSG(3347)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    shape = ogr.CreateGeometryFromJson(json.dumps(geometry, separators=(",", ":")))
    shape.AssignSpatialReference(source)
    shape.TransformTo(target)
    if not shape.IsValid():
        shape = shape.MakeValid()
    return shape


def parent_chain(subject, feature_by_id, hierarchy_by_id):
    feature = feature_by_id[subject]
    parent = feature.get("properties", {}).get("parent_id") or feature.get("parent_id")
    chain = [subject]
    while parent:
        if parent in chain or parent not in hierarchy_by_id:
            raise ValueError(f"broken/cyclic parent chain for {subject}: {parent}")
        chain.append(parent)
        parent = hierarchy_by_id[parent].get("parent_id")
    if len(chain) != 6 or chain[1] != SUBJECTS[subject]:
        raise ValueError(f"unexpected complete parent chain for {subject}: {chain}")
    return chain


def reproduce(archive, commit):
    raw = Path(archive).read_bytes()
    if len(raw) != IBC_SIZE or hashlib.sha256(raw).hexdigest() != IBC_SHA256:
        raise ValueError("IBC archive size/SHA-256 mismatch; no output written")
    pinned = baseline_bytes(commit)
    try:
        from osgeo import ogr, osr
    except ImportError as error:
        raise RuntimeError("GDAL Python bindings (osgeo) are required") from error
    ds = ogr.Open("/vsizip/" + str(Path(archive).resolve()))
    if ds is None:
        raise ValueError("GDAL could not open the verified IBC archive")
    layer = ds.GetLayer(0)
    line = None
    for feature in layer:
        if feature.GetField("SectionNum") == 25:
            line = feature.GetGeometryRef().Clone()
            source = osr.SpatialReference()
            source.ImportFromEPSG(4269)
            source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            target = osr.SpatialReference()
            target.ImportFromEPSG(3347)
            target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            line.AssignSpatialReference(source)
            line.TransformTo(target)
            break
    if line is None:
        raise ValueError("verified IBC archive does not contain section 25")

    scope = load_json(pinned[PREFIX + "scope.json"])
    member_ids = set(scope["member_location_ids"])
    chain_rows = load_json(gzip.decompress(pinned[PREFIX + "sources/current-parent-chains.json.gz"]))
    chains = {row["id"]: row["parent_chain"] for row in chain_rows}
    if len(member_ids) != 222 or set(chains) != member_ids or len(chains) != 222:
        raise ValueError("pinned BC scope/parent-chain roster is incomplete")
    bc_area = next(area["id"] for area in scope["area_scopes"] if area["name"] == "British Columbia")
    bc_ids = {item for item in member_ids if any(node.get("id") == bc_area for node in chains[item])}
    scoped = load_json(gzip.decompress(pinned[PREFIX + "sources/current-scope-and-parents.geojson.gz"]))["features"]
    feature_by_id = {item["properties"]["id"]: item for item in scoped}
    if set(feature_by_id) != member_ids:
        raise ValueError("pinned scope geometry roster is incomplete")
    hierarchy = load_json(pinned["data/hierarchy.json"])
    hierarchy_by_id = {row["id"]: row for row in hierarchy if isinstance(row, dict) and row.get("id")}
    subject_features = {}
    for path in ("data/geography/part-27.json", "data/geography/part-29.json"):
        for item in load_json(pinned[path])["features"]:
            subject_id = item.get("id") or item.get("properties", {}).get("id")
            if subject_id in SUBJECTS:
                subject_features[subject_id] = item
    if set(subject_features) != set(SUBJECTS):
        raise ValueError("an assigned BC/Washington subject is absent from its pinned geography part")
    parent_chains = {subject: parent_chain(subject, subject_features, hierarchy_by_id) for subject in SUBJECTS}

    cd = load_json(gzip.decompress(pinned[PREFIX + "sources/statistics-canada-bc-census-divisions-2021.geojson.gz"]))["features"]
    wa = load_json(gzip.decompress(pinned[PREFIX + "sources/tigerline-2024-washington-counties.geojson.gz"]))["features"]
    cd_ids = [item["properties"]["CDUID"] for item in cd]
    wa_ids = [item["properties"]["GEOID"] for item in wa]
    if len(cd_ids) != 29 or len(set(cd_ids)) != 29 or "5915" not in cd_ids:
        raise ValueError("Statistics Canada 2021 BC division roster mismatch")
    if len(wa_ids) != 39 or len(set(wa_ids)) != 39 or not {"53073", "53055"} <= set(wa_ids):
        raise ValueError("2024 TIGER Washington county roster mismatch")
    bc = []
    for item in scoped:
        location_id = item["properties"]["id"]
        if location_id in bc_ids:
            edge = project(item["geometry"], ogr, osr).Boundary()
            if edge is not None and not edge.IsEmpty():
                bc.append((location_id, edge))
    city_id = "gb:CAN:ADM3:43193130B1191968375732"
    if city_id not in feature_by_id:
        raise ValueError("assigned Abbotsford comparison feature is absent from the pinned BC scope")
    city_edge = project(feature_by_id[city_id]["geometry"], ogr, osr).Boundary()
    cds = [(item["properties"]["CDUID"], project(item["geometry"], ogr, osr).Boundary()) for item in cd]
    counties = [(item["properties"]["GEOID"], project(item["geometry"], ogr, osr).Boundary(), project(item["geometry"], ogr, osr)) for item in wa]
    if len(bc_ids) != 61 or len(bc) != 60 or len(cds) != 29 or len(counties) != 39:
        raise ValueError(f"incomplete geometry cohort; refusing partial calculation: BC members={len(bc_ids)}, usable BC={len(bc)}, CDs={len(cds)}, counties={len(counties)}")
    steps = math.ceil(line.Length() / 1000)
    rows = []
    for index in range(steps + 1):
        point = line.Value(line.Length() * index / steps)
        nearest_bc = min((point.Distance(edge), key) for key, edge in bc)
        nearest_cd = min((point.Distance(edge), key) for key, edge in cds)
        nearest_wa = min((point.Distance(edge), key) for key, edge, _ in counties)
        contained = sorted(key for key, _, polygon in counties if polygon.Contains(point))
        if 50 <= index <= 67:
            rows.append({
                "sample": index,
                "epsg3347_m": [round(point.GetX(), 1), round(point.GetY(), 1)],
                "nearest_current_bc_location_boundary_m": round(nearest_bc[0], 2),
                "nearest_current_bc_location_id": nearest_bc[1],
                "abbotsford_current_bc_location_boundary_m": round(point.Distance(city_edge), 2),
                "nearest_2021_statscan_cd_boundary_m": round(nearest_cd[0], 2),
                "nearest_2021_statscan_cd_code": nearest_cd[1],
                "nearest_2024_tiger_wa_county_boundary_m": round(nearest_wa[0], 3),
                "nearest_2024_tiger_wa_county_geoid": nearest_wa[1],
                "tiger_wa_county_polygons_containing_point": contained,
            })
    if steps != 73 or [row["sample"] for row in rows] != list(range(50, 68)):
        raise ValueError("source line sampling scheme or focused row roster changed")
    if any(row["nearest_current_bc_location_id"] != "atlas:district:CAN-5915:BRC" for row in rows):
        raise ValueError("nearest BC subject changed")
    if any(row["nearest_2024_tiger_wa_county_geoid"] != "53073" for row in rows):
        raise ValueError("nearest Washington county changed")

    inherited = load_json(pinned["data/regional-review/bc-washington-coastal-edge-followup-2026/sample-assessment.json"])
    if inherited["samples"] != rows:
        raise ValueError("regenerated rows differ from immutable inherited ledger")
    empty = [row["sample"] for row in rows if not row["tiger_wa_county_polygons_containing_point"]]
    distances = [row["nearest_current_bc_location_boundary_m"] for row in rows]
    source_hashes = [{"path": path, "bytes": len(pinned[path]), "sha256": digest}
                     for path, (_, digest) in PINS.items()]
    return {
        "version": 1,
        "baseline_commit": BASELINE,
        "baseline_inputs": source_hashes,
        "source": {
            "id": "ibc-v1-3-section-25",
            "canonical_url": "https://www.internationalboundarycommission.org/uploads/shapefile/us-canada-boundary-v1-3.zip",
            "section": 25,
            "section_name": "49th Parallel (Pacific to Columbia Valley)",
            "metadata_date": "2018-04-20",
            "archive_bytes": len(raw),
            "archive_sha256": hashlib.sha256(raw).hexdigest(),
            "retained": False,
            "terms": "Bundled metadata states mapping purposes only and © International Boundary Commission, all rights reserved; no archive bytes are redistributed.",
        },
        "method": {
            "software": "GDAL/OGR Python bindings",
            "projection": "EPSG:3347; IBC source geometry interpreted as EPSG:4269; retained reference geometries as EPSG:4326",
            "line_samples": steps + 1,
            "maximum_spacing_m": round(line.Length() / steps, 6),
            "scope": "all 61 pinned British Columbia members accounted for; 60 usable area boundaries; one empty boundary explicitly excluded; 29 Statistics Canada divisions and 39 Washington TIGER counties",
            "sample_rule": "equidistant samples at intervals <=1 km; output rows 50–67 inclusive",
        },
        "subjects": [{"id": key, "parent_chain": parent_chains[key]} for key in SUBJECTS],
        "sample_count": len(rows),
        "nearest_bc_location_id_all_samples": "atlas:district:CAN-5915:BRC",
        "nearest_wa_geoid_all_samples": "53073",
        "nearest_bc_distance_m": {"minimum": min(distances), "maximum": max(distances)},
        "strict_tiger_polygon_noncontainment_sample_ids": empty,
        "strict_tiger_polygon_noncontainment_count": len(empty),
        "matches_inherited_rows_exactly": True,
        "narrative_reconciliation": {
            "noncontainment_count": {"inherited_narrative": 4, "reproduced_rows": len(empty)},
            "minimum_distance_m": {"inherited_narrative": 1011.91, "reproduced_rows": min(distances), "display": f"{min(distances):,.2f}"},
        },
        "interpretation": "This confirms source reproducibility and arithmetic only. It does not identify the reason for the offset, establish legal boundaries or political ownership, or support a geometry correction.",
        "uncertainty": "Source vintages/scales differ. Mapping-only IBC line scale and represented shore/water surfaces cannot establish an ownership or coast-treatment cause; neighboring footprint explanation remains unresolved.",
        "samples": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="verified temporary IBC archive path")
    parser.add_argument("--baseline-commit", default=BASELINE)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--new-vintage", action="store_true", help="create output exclusively after all input checks")
    args = parser.parse_args()
    if args.new_vintage and args.output.exists():
        raise SystemExit(f"refusing existing output before reading inputs: {args.output}")
    result = reproduce(args.archive, args.baseline_commit)
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.new_vintage:
        with args.output.open("xb") as stream:
            stream.write(encoded)
    elif not args.output.is_file() or args.output.read_bytes() != encoded:
        raise ValueError("read-only comparison failed: stored receipt differs")
    print(json.dumps({"output": str(args.output), "sha256": hashlib.sha256(encoded).hexdigest(),
                      "samples": result["sample_count"], "noncontainments": result["strict_tiger_polygon_noncontainment_count"],
                      "mode": "created" if args.new_vintage else "read-only-verified"}))


if __name__ == "__main__":
    main()
