#!/usr/bin/env python3
"""Independently audit native JRC tile metadata and spatial coverage.

This deliberately does not rerun the 552-block monthly pixel summarization.
It reads 24 small TIFF headers, three 1x1 native pixel windows, and overlays
the two native raster footprints with the immutable 70-component GeoJSON.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import rasterio
from pyproj import Transformer
from rasterio.windows import Window
from shapely.geometry import box, shape
from shapely.ops import transform as transform_geometry
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
OWN = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else OWN / "native-coverage-audit.json"
CAPTURE = OLD / "sources/jrc/monthlyhistory-v1_5-2024-capture.json"
GEOJSON = OLD / "inputs/selected-70-component-geometries.geojson"
MATRIX = OLD / "outputs/source-status-matrix.json"
SUMMARY = OLD / "outputs/jrc-2024-component-month-summary.json"
VALIDATION = OLD / "outputs/validation-controls.json"
COMPONENT_ROSTER = "d537eeaee6c9cbc0ac03ff7227cb1a87c214bfde6644df9c50d46bb2e63e5c5f"
FAMILY_ROSTER = "6ccdac13874fa8d4b6f444076ace737a4ac6a9f84fae2c1168207b1385d892a0"
CONTACT_ROSTER = "a47f36a11e723a12f662930f8ac98c4f500e6d0a8f78872699a8592cea60c2d6"
LIMIT_FILE = 32 * 1024 * 1024
LIMIT_PHASE = 256 * 1024 * 1024

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def file_bytes(path: Path) -> int:
    return path.stat().st_size

def roster_sha(values: set[str]) -> str:
    return hashlib.sha256(("\n".join(sorted(values)) + "\n").encode()).hexdigest()

def valid_native_header(epsg: int | None, transform: tuple[float, ...], expected_north: float) -> bool:
    if epsg != 4326 or len(transform) < 6:
        return False
    a, b, c, d, e, f = transform[:6]
    return (a > 0 and e < 0 and abs(b) < 1e-12 and abs(d) < 1e-12 and
            abs(a - 0.00025) < 1e-12 and abs(e + 0.00025) < 1e-12 and
            abs(c + 10) < 1e-10 and abs(f - expected_north) < 1e-10)

def main() -> None:
    out_parent = OUT.parent.resolve()
    assert OWN in out_parent.parents and not OUT.exists() and not OUT.is_symlink(), "refuse overwrite/symlink or output outside owned packet"
    out_parent.mkdir(parents=True, exist_ok=True)
    capture = json.loads(CAPTURE.read_text())
    matrix = json.loads(MATRIX.read_text())
    validation = json.loads(VALIDATION.read_text())
    geo = json.loads(GEOJSON.read_text())
    assert len(capture["assets"]) == 24
    assert len(matrix["components"]) == 70 and len(matrix["families"]) == 52
    assert len(geo["features"]) == 70

    source_bytes = sum(file_bytes(CAPTURE.parent / "monthlyhistory-v1_5-2024" / a["filename"]) for a in capture["assets"])
    ordinary_inputs = [CAPTURE, GEOJSON, MATRIX, VALIDATION, SUMMARY]
    ordinary_inputs.extend(CAPTURE.parent / "monthlyhistory-v1_5-2024" / a["filename"] for a in capture["assets"])
    assert all(file_bytes(p) <= LIMIT_FILE for p in ordinary_inputs), "per-file admission failed"
    code_bytes = file_bytes(Path(__file__))
    fixture_bytes = file_bytes(CAPTURE) + file_bytes(GEOJSON) + file_bytes(MATRIX) + file_bytes(VALIDATION) + file_bytes(SUMMARY)
    projected_phase_bytes = source_bytes + fixture_bytes + code_bytes + 512 * 1024
    assert projected_phase_bytes <= LIMIT_PHASE, "complete metadata/coverage phase exceeds 256 MiB"

    by_name = {}
    assets = []
    for a in capture["assets"]:
        path = CAPTURE.parent / "monthlyhistory-v1_5-2024" / a["filename"]
        actual_sha = sha(path)
        assert actual_sha == a["sha256"] and file_bytes(path) == a["bytes"]
        with rasterio.open(path) as ds:
            assert ds.crs and ds.crs.to_epsg() == 4326
            assert ds.width == ds.height == 40_000 and ds.count == 1
            assert ds.dtypes == ("uint8",) and ds.block_shapes == [(1024, 1024)]
            assert ds.transform.a > 0 and ds.transform.e < 0
            assert abs(ds.transform.a - 0.00025) < 1e-12
            assert abs(ds.transform.e + 0.00025) < 1e-12
            assert abs(ds.transform.c + 10) < 1e-10
            north = ds.bounds.top
            expected_north = 30 if "_30N_" in a["filename"] else 40
            assert valid_native_header(ds.crs.to_epsg(), tuple(ds.transform), expected_north)
            assert abs(north - expected_north) < 1e-10
            assert abs(ds.bounds.bottom - (expected_north - 10)) < 1e-10
            captured_overviews = [round(40_000 / page["width"]) for page in a["pages"][1:]]
            # The historical hand-capture enumerates IFDs through 2,500 px;
            # GDAL also exposes two additional reduced-resolution overviews.
            assert ds.overviews(1)[:len(captured_overviews)] == captured_overviews
            tile = "10W_30N" if "_30N_" in a["filename"] else "10W_40N"
            by_name[a["filename"]] = dict(tile=tile, bounds=[ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top], transform=[ds.transform.a, ds.transform.b, ds.transform.c, ds.transform.d, ds.transform.e, ds.transform.f])
            assets.append({"filename": a["filename"], "url": a["url"], "bytes": file_bytes(path), "sha256": actual_sha,
                           "crs": ds.crs.to_string(), "width": ds.width, "height": ds.height, "dtype": ds.dtypes[0],
                           "transform": list(ds.transform)[:6], "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
                           "block_shape": list(ds.block_shapes[0]), "overviews": ds.overviews(1), "nodata": ds.nodata})

    tile_footprints = {
        tile: box(*next(v["bounds"] for v in by_name.values() if v["tile"] == tile))
        for tile in ("10W_30N", "10W_40N")
    }
    # Use equal-area area for coverage fractions; raster footprints are derived
    # only from actual native bounds, not tile names or the old window plan.
    to_equal_area = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    projected_footprint = transform_geometry(to_equal_area, unary_union(list(tile_footprints.values())))
    old_components = {r["component_id"]: r for r in matrix["components"]}
    component_rows = []
    contact_ids = set()
    family_ids = set()
    for feature in geo["features"]:
        component_id = feature["properties"]["source_payload_id"]
        row = old_components[component_id]
        geom = shape(feature["geometry"])
        pgeom = transform_geometry(to_equal_area, geom)
        cover_area = pgeom.intersection(projected_footprint).area
        area = pgeom.area
        overlap = {name: geom.intersection(footprint).area for name, footprint in tile_footprints.items()}
        contact_ids.update(row["contact_ids"])
        family_ids.update(row["family_ids"])
        component_rows.append({
            "component_id": component_id,
            "family_ids": row["family_ids"],
            "contact_ids": row["contact_ids"],
            "native_tile_intersection_area_deg2": {k: round(v, 14) for k, v in overlap.items()},
            "native_tile_union_coverage_fraction_equal_area": (cover_area / area if area else None),
            "native_tile_union_coverage_status": "none" if cover_area == 0 else ("full" if abs(cover_area-area) <= max(1e-4, area*1e-10) else "partial"),
            "interpretation": "Footprint overlap only. No pixel counts, water class, or full-component physical classification is inferred."
        })
    assert len({r["component_id"] for r in component_rows}) == 70
    assert len(family_ids) == 52 and len(contact_ids) == 57
    assert roster_sha({r["component_id"] for r in component_rows}) == COMPONENT_ROSTER
    assert roster_sha(family_ids) == FAMILY_ROSTER and roster_sha(contact_ids) == CONTACT_ROSTER

    family_rows = []
    subject_components: dict[str, set[str]] = {subject: set() for subject in contact_ids}
    subject_families: dict[str, set[str]] = {subject: set() for subject in contact_ids}
    subject_neighbors: dict[str, set[str]] = {subject: set() for subject in contact_ids}
    subject_details: dict[str, list[dict]] = {subject: [] for subject in contact_ids}
    for comp in component_rows:
        for contact in comp["contact_ids"]:
            subject_components[contact].add(comp["component_id"])
            subject_families[contact].update(comp["family_ids"])
    for family in matrix["families"]:
        fid = family["family_id"]
        fcontacts = family["contact_ids"]
        for contact in fcontacts:
            subject_neighbors[contact].update(set(family.get("edge_neighbor_ids", [])) - {contact})
            for compid in family["component_ids"]:
                for admin in old_components[compid].get("consumed_admin_source_comparison", []):
                    for feature in admin.get("intersections", []):
                        if feature["source_feature_id"] == contact:
                            subject_details[contact].append({"name": feature["source_name"], "country": "Spain" if feature["source_product"] == "gb:ESP:ADM3" else "Portugal",
                                                             "source_product": feature["source_product"], "administrative_granularity": feature["source_type"],
                                                             "recorded_vintage": admin["recorded_vintage"], "recorded_license": admin["recorded_license"],
                                                             "relationship": "positive-area intersection with a scoped component; not an ownership or boundary finding"})
            for join in family.get("mapa_current_snapshot", {}).get("current_service_feature_joins", []):
                if join["contact_id"] == contact:
                    sf = join["source_feature"]
                    subject_details[contact].append({"name": sf.get("ds_comarca"), "parent_name": sf.get("ds_provinc"), "country": "Spain",
                                                     "administrative_granularity": "Atlas agricultural comarca contact joined to a current MAPA comarca snapshot",
                                                     "recorded_vintage": "recent current service snapshot; exact effective date unknown", "recorded_license": "unresolved",
                                                     "relationship": "numeric code suffix joined to current service feature; does not authenticate historical Atlas import"})
        family_rows.append({"family_id": fid, "component_ids": family["component_ids"], "contact_ids": fcontacts,
                            "edge_neighbor_ids": family.get("edge_neighbor_ids", []),
                            "jrc_2024_previous_summary": "withdrawn as spatially supported evidence; its tile-row assignment used the erroneous +10 degree north edge",
                            "other_retained_context": {"administrative_source_comparison": family.get("consumed_admin_source_overlays"),
                                                       "APA_WFD_lines": family.get("apa_wfd_line_context"),
                                                       "MAPA_current_snapshot": family.get("mapa_current_snapshot_context")},
                            "physical_and_historical_status": "unknown", "boundary_edit": False})
    subjects = []
    for contact in sorted(contact_ids):
        parts = contact.split(":")
        subjects.append({"subject_id": contact, "country": "Spain" if ":ESP:" in contact or contact.startswith("atlas:district:ESP-") else "Portugal",
                         "identifier_kind": "Atlas agricultural comarca contact" if contact.startswith("atlas:") else f"{parts[2]} administrative polygon",
                         "families": sorted(subject_families[contact]), "components": sorted(subject_components[contact]),
                         "edge_neighbors_in_scope": sorted(subject_neighbors[contact]), "source_or_parent_context": subject_details[contact],
                         "territorial_limit": "Scoped contact / source comparison only. Parent or neighbor names are source-record context, not an adjudication of rightful territory or a boundary."})
    assert {s["subject_id"] for s in subjects} == contact_ids

    control_definitions = [
        (1265, 11154, 2, [-7.211375, 39.683625], "positive_water_detection"),
        (194, 12287, 1, [-6.928125, 39.951375], "observed_non_detection"),
        (692, 11964, 0, [-7.008875, 39.826875], "no_observation_unknown"),
    ]
    control_path = CAPTURE.parent / "monthlyhistory-v1_5-2024" / "monthlyhistory_10W_30N_v1_5_2024_01.tif"
    control_component = next(shape(f["geometry"]) for f in geo["features"] if f["properties"]["source_payload_id"] == "physical-component:72db06639029f21bb6a9066b8bce95cf6f47c61da8b2d507e7194d8614ea504b")
    controls = []
    with rasterio.open(control_path) as ds:
        native_transform = tuple(ds.transform)
        native_epsg = ds.crs.to_epsg()
        native_bounds = ds.bounds
        for r, c, expected, claimed, kind in control_definitions:
            value = int(ds.read(1, window=Window(c, r, 1, 1))[0, 0])
            native = list(ds.xy(r, c))
            assert value == expected
            claimed_inside = control_component.contains(__import__("shapely").geometry.Point(*claimed))
            native_inside = control_component.contains(__import__("shapely").geometry.Point(*native))
            assert claimed_inside and not native_inside
            assert abs((claimed[1] - native[1]) - 10.0) < 1e-9
            controls.append({"kind": kind, "row": r, "column": c, "value": value, "claimed_lonlat": claimed,
                             "native_center_lonlat": native, "claimed_center_inside_component": claimed_inside,
                             "native_center_inside_component": native_inside,
                             "interpretation": "Pixel value authentic; its claimed component location is false. Code 0 remains unknown; code 1 is monthly non-detection only."})

    outside = (-7.0, 41.0)
    adversarial_fixtures = [
        {"case": "north-edge-shifted-plus-10-degrees", "rejected": not valid_native_header(native_epsg, (*native_transform[:5], native_transform[5] + 10, *native_transform[6:]), 30)},
        {"case": "wrong-crs-web-mercator", "rejected": not valid_native_header(3857, native_transform, 30)},
        {"case": "flipped-row-direction", "rejected": not valid_native_header(native_epsg, (*native_transform[:4], abs(native_transform[4]), *native_transform[5:]), 30)},
        {"case": "out-of-native-coverage-point", "point_lonlat": list(outside), "rejected": not (native_bounds.left <= outside[0] <= native_bounds.right and native_bounds.bottom <= outside[1] <= native_bounds.top)},
        {"case": "claimed-controls-even-if-hashes-refresh", "rejected": all(not c["native_center_inside_component"] for c in controls)},
    ]
    assert all(f["rejected"] for f in adversarial_fixtures)

    capture_manifest = CAPTURE
    current_retrieval = OWN / "jrc-current-retrieval.json"
    guide = OLD / "sources/jrc/DataUsersGuidev2024_v5.pdf"
    page = OLD / "sources/jrc/official-download-page.html"
    output = {
        "schema": "worldatlas-jrc-native-coverage-erratum-v1",
        "method_id": "native-geotiff-coverage-and-pixel-controls",
        "kind": "geography",
        "outcome": "passed",
        "positive_control": "authenticated native code-2 pixel is correctly read; its former claimed center is rejected as outside the exact component",
        "negative_control": "authenticated code-1 and code-0 pixels are read; their false north-shifted locations are rejected, and code-0 remains unknown",
        "created_utc_date": "2026-10-09",
        "method": "Independent Rasterio/GDAL header and three pixel reads plus equal-area polygon footprint overlay from the pinned unchanged geometries. Does not decode or summarize the full monthly rasters.",
        "runtime": {"python": "3.12", "rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__},
        "input_bindings": {"audit_code": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": sha(Path(__file__)), "bytes": file_bytes(Path(__file__))},
                           "capture_manifest": {"path": str(CAPTURE.relative_to(ROOT)), "sha256": sha(CAPTURE), "bytes": file_bytes(CAPTURE)},
                           "component_geometries": {"path": str(GEOJSON.relative_to(ROOT)), "sha256": sha(GEOJSON), "bytes": file_bytes(GEOJSON)},
                           "source_status_matrix": {"path": str(MATRIX.relative_to(ROOT)), "sha256": sha(MATRIX), "bytes": file_bytes(MATRIX)},
                           "prior_jrc_summary": {"path": str(SUMMARY.relative_to(ROOT)), "sha256": sha(SUMMARY), "bytes": file_bytes(SUMMARY)},
                           "prior_validator_result": {"path": str(VALIDATION.relative_to(ROOT)), "sha256": sha(VALIDATION), "bytes": file_bytes(VALIDATION)},
                           "current_official_retrieval": {"path": str(current_retrieval.relative_to(ROOT)), "sha256": sha(current_retrieval), "bytes": file_bytes(current_retrieval)}},
        "admission": {"max_file_bytes": LIMIT_FILE, "max_complete_phase_bytes": LIMIT_PHASE, "encoded_raster_bytes": source_bytes,
                      "complete_phase_upper_bound_bytes_including_128KiB_output_reserve": projected_phase_bytes,
                      "status": "admitted for header/control/footprint phase only; full monthly pixel re-summarization refused (578813952 decoded bytes in the prior plan)"},
        "scope": {"families": len(family_ids), "components": len(component_rows), "contacts": len(contact_ids),
                  "component_roster_sha256": roster_sha({r["component_id"] for r in component_rows}), "family_roster_sha256": roster_sha(family_ids),
                  "contact_roster_sha256": roster_sha(contact_ids), "subject_crosswalk": subjects, "families_detail": family_rows},
        "source_context": {"product": "JRC Global Surface Water Monthly History v1.5, year 2024", "period": "2024-01 through 2024-12",
                           "source_extent_note": "JRC documents individual 10-degree tiles and monthly history. The captured actual TIFFs are EPSG:4326 with bounds determined from their native GeoTIFF transforms below.",
                           "reuse_terms": "JRC data-access page states data are free without restriction and asks for acknowledgement/citation; attribution: Source: EC JRC/Google.",
                           "vintage_limit": "2022-2024 extension; the guide warns the 2022-2024 Landsat Collection 2 registration relative to Collection 1 may vary spatially. This is contemporary monthly context, not a historical administrative boundary or physical land/water truth.",
                           "retained_authoritative_evidence": [
                               {"path": str(page.relative_to(ROOT)), "sha256": sha(page), "retrieved_at_utc": "2026-10-07T02:16:28.598129+00:00", "url": "https://global-surface-water.appspot.com/download"},
                               {"path": str(guide.relative_to(ROOT)), "sha256": sha(guide), "retrieved_at": "original capture date not recorded; exact retained bytes and canonical URL preserved", "url": "https://storage.googleapis.com/water-world/downloads_ancillary/DataUsersGuidev2024_v.5.pdf"},
                               {"path": str(capture_manifest.relative_to(ROOT)), "sha256": sha(capture_manifest), "retrieval_date": "original raster retrieval date not recorded in manifest; each URL, byte count and expected SHA-256 is pinned"},
                               {"path": str(current_retrieval.relative_to(ROOT)), "sha256": sha(current_retrieval), "retrieved_at_utc": json.loads(current_retrieval.read_text())["completed_at_utc"], "url": "each official tile URL is recorded per asset", "verification": "all 24 returned byte streams match retained whole-file hashes and byte lengths"}
                           ]},
        "tile_footprints": {k: {"bounds_lonlat": list(v.bounds), "source": "derived from all six native transform coefficients of whole-byte-authenticated TIFFs"} for k, v in tile_footprints.items()},
        "assets": assets,
        "capture_inventory_difference": "For each of the 24 TIFFs, the frozen raw-tag capture lists overviews 2,4,8,16. Independent GDAL 3.9.3 reports 2,4,8,16,32,64. This does not change native full-resolution georeferencing; preserve the old capture and record its overview inventory as incomplete rather than silently rewriting it.",
        "controls": {"asset": control_path.name, "sha256": sha(control_path), "component_id": "physical-component:72db06639029f21bb6a9066b8bce95cf6f47c61da8b2d507e7194d8614ea504b", "checks": controls,
                     "adversarial_fixtures": adversarial_fixtures,
                     "former_validator_status": validation["status"], "former_validator_claimed_success": "The original control validator reported passed despite all three claimed centers being displaced 10 degrees north.",
                     "replacement_evidence_status": "the test rejects each false claimed location while independently authenticating the native pixel code"},
        "components": component_rows,
        "summary": {"components_with_native_tile_coverage": sum(x["native_tile_union_coverage_status"] != "none" for x in component_rows),
                    "components_with_partial_native_tile_coverage": sum(x["native_tile_union_coverage_status"] == "partial" for x in component_rows),
                    "components_with_full_native_tile_coverage": sum(x["native_tile_union_coverage_status"] == "full" for x in component_rows),
                    "components_with_no_native_tile_coverage": sum(x["native_tile_union_coverage_status"] == "none" for x in component_rows),
                    "limitations": ["Coverage is spatial tile-footprint coverage, not successful-observation coverage.", "The old JRC counts/control/family prose are withdrawn as spatially unsupported; administrative, APA and MAPA findings remain distinct and are not altered.", "No corrected water counts or full-component classification is established.", "The MITECO vectors were not acquired; APA reuse terms and historical MAPA source bytes/terms remain unresolved; these remain explicit neighboring-source gaps.", "No boundary, ownership, cause, ice or historical status is changed; all remain unknown."]}
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    assert file_bytes(OUT) <= 512 * 1024
    assert source_bytes + fixture_bytes + code_bytes + file_bytes(OUT) <= LIMIT_PHASE
    print(json.dumps(output["summary"], indent=2))
    print(f"wrote {OUT} ({file_bytes(OUT)} bytes, sha256 {sha(OUT)})")

if __name__ == "__main__":
    main()
