#!/usr/bin/env python3
"""Reproduce the source-ID, name, geometry, and ownership audit for issue #460.

Uses only Python's standard library. Source files are fetched into a temporary
directory, hashed, parsed, and discarded; the output retains only attributes
and evidence metadata needed for this bounded review.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import pathlib
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
SCOPE = OUT / "scope.json"
SOURCES = {
    "AGO": {
        "url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbHumanitarian/AGO/ADM2/geoBoundaries-AGO-ADM2.geojson",
        "sha256": "44e58b2a8c2fefb9369294a32e2adde3e3637b9e02e8f1e2c53b400bec04f404",
        "vintage": "2018",
        "license": "Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)",
        "name": "geoBoundaries gbHumanitarian AGO ADM2",
    },
    "CMR": {
        "url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CMR/ADM3/geoBoundaries-CMR-ADM3.geojson",
        "sha256": "9d0ff998057c3afe7f3a6334d71e9d7c353c64fe6e7c35b01fe14d804c97f04b",
        "vintage": "2017",
        "license": "Open Data Commons Open Database License 1.0",
        "name": "geoBoundaries gbOpen CMR ADM3",
    },
}
LEGAL = {
    "url": "https://c2a.portais.gov.ao/uploads/Lei_14_24_de_5_de_Setembro_Cabinda_5c86d750e1.pdf",
    "sha256": "dfaab2fa7059d8447aee3cab492deb94793971883b6a4998dc5353bf3d6e6e6a",
    "vintage": "2024-09-05",
    "reuse": "Official Gazette PDF; no explicit open license located. Restoration-only; do not redistribute the PDF without confirming reuse terms.",
}
YAOUNDE_PARENT_CHECK = {
    "gb:CMR:ADM3:9386221B56027412894684": "Yaoundé I",
    "gb:CMR:ADM3:9386221B66762903352612": "Yaoundé II",
    "gb:CMR:ADM3:9386221B47531248617039": "Yaoundé V",
    "gb:CMR:ADM3:9386221B18291950390240": "Yaoundé VII",
}
MINDDEVEL = {
    "url": "https://www.minddevel.gov.cm/mfoundi/",
    "sha256": "db416e29e1705fa1a4fa8775e5f5ff4e8d2642f9a7b950e00322c125fc209d97",
}
CONTEXT_HASHES = {
    "minat_services": ("https://minat.gov.cm/presentation/services-locaux/", "5459c95800284d4229241b9d59e8eb336ac8e4127c3709a15f0dd12bf0144e06"),
    "salb_cameroon": ("https://salb.un.org/en/data/cmr", "eef4a0653a2a26c7f84e40036d1cc480fdfadcfa901841aefd26ca5be2ee256c"),
    "salb_terms": ("https://salb.un.org/sites/default/files/wysiwyg_uploads/docs_uploads/TermsOfUseSALB2021.pdf", "aaac013743486c9f4be986e236fdba6b3a4ac0ff00921cecc171c42778544381"),
    "salb_specifications": ("https://salb.un.org/sites/default/files/wysiwyg_uploads/docs_uploads/SALB_DataSpecifications.pdf", "01882723ead36592eb8d8ba61a4c5fb9a4f0eb839e874689bbb822c9d8391a78"),
}


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str, destination: pathlib.Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "WorldAtlas geography source audit"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as f:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            f.write(block)


def vertex_count(value) -> int:
    if isinstance(value, list) and value and isinstance(value[0], (int, float)):
        return 1
    if isinstance(value, list):
        return sum(vertex_count(child) for child in value)
    return 0


def ring_area_m2(ring) -> float:
    """Spherical ring area approximation suitable for relative size screening."""
    import math
    total = 0.0
    for a, b in zip(ring, ring[1:]):
        lon1, lat1 = map(math.radians, a[:2])
        lon2, lat2 = map(math.radians, b[:2])
        delta = lon2 - lon1
        if delta > math.pi:
            delta -= 2 * math.pi
        elif delta < -math.pi:
            delta += 2 * math.pi
        total += delta * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(total) * (6371008.8 ** 2) / 2


def source_area_m2(geometry) -> float:
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return 0.0
    area = 0.0
    for polygon in polygons:
        if not polygon:
            continue
        area += ring_area_m2(polygon[0])
        area -= sum(ring_area_m2(hole) for hole in polygon[1:])
    return max(0.0, area)


def main() -> None:
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    allowed = set(scope["member_location_ids"])
    assert len(allowed) == 230 == scope["location_count"]
    id_digest = hashlib.sha256("\n".join(scope["member_location_ids"]).encode("utf-8")).hexdigest()
    assert id_digest == scope["member_location_ids_sha256"], f"scope ID digest mismatch: {id_digest}"
    hierarchy = json.loads((ROOT / "data/hierarchy.json").read_text(encoding="utf-8"))
    hierarchy_nodes = {n["id"]: n for n in hierarchy}
    atlas = {}
    for part in json.loads((ROOT / "data/world-index.json").read_text(encoding="utf-8"))["parts"]:
        for feature in json.loads((ROOT / "data" / part).read_text(encoding="utf-8"))["features"]:
            p = feature["properties"]
            if p["id"] in allowed:
                atlas[p["id"]] = (p, feature["geometry"])
    assert set(atlas) == allowed, f"scope/current-main mismatch: {len(allowed-set(atlas))} missing"

    official = {}
    results = {}
    with tempfile.TemporaryDirectory(prefix="worldatlas-460-") as td:
        temp = pathlib.Path(td)
        law_path = temp / "angola-law-14-24.pdf"
        fetch(LEGAL["url"], law_path)
        if digest(law_path) != LEGAL["sha256"]:
            raise RuntimeError("Angola official-law PDF changed from the inspected byte hash")
        mfoundi_path = temp / "cameroon-minddevel-mfoundi.html"
        fetch(MINDDEVEL["url"], mfoundi_path)
        mfoundi_text = mfoundi_path.read_text(encoding="utf-8").upper()
        if not all(f"YAOUNDE {roman}" in mfoundi_text for roman in ("I ", "II ", "III ", "IV ", "V ", "VI ", "VII ")):
            raise RuntimeError("MINDDEVEL page no longer exposes the seven Mfoundi Yaounde mayor records")
        observed_context_hashes = {"minddevel_mfoundi": digest(mfoundi_path)}
        for name, (url, expected_hash) in CONTEXT_HASHES.items():
            source_path = temp / name
            fetch(url, source_path)
            observed_context_hashes[name] = digest(source_path)
            if name in ("salb_terms", "salb_specifications") and observed_context_hashes[name] != expected_hash:
                raise RuntimeError(f"Stable SALB PDF changed from the inspected byte hash: {name}")
            if name == "minat_services":
                body = source_path.read_text(encoding="utf-8").lower()
                if not all(value in body for value in ("360", "58", "arrondissements")):
                    raise RuntimeError("MINAT Services Locaux page no longer supports the recorded administrative counts")
            if name == "salb_cameroon":
                body = source_path.read_text(encoding="utf-8").lower()
                if "2024-08-07" not in body or "cameroon" not in body:
                    raise RuntimeError("SALB Cameroon record no longer supports the recorded validation/vintage statement")
        for code, meta in SOURCES.items():
            path = temp / f"{code}.geojson"
            fetch(meta["url"], path)
            actual_hash = digest(path)
            if actual_hash != meta["sha256"]:
                raise RuntimeError(f"{code} source hash changed: expected {meta['sha256']}, got {actual_hash}")
            raw = json.loads(path.read_text(encoding="utf-8"))
            features = raw["features"]
            indexed = {f["properties"]["shapeID"]: f for f in features}
            assert len(indexed) == len(features), f"duplicate source IDs in {code}"
            official[code] = indexed
            results[code] = {"feature_count": len(features), "sha256": actual_hash}

    provinces = {}
    lines = []
    summary = collections.Counter()
    for location_id in sorted(allowed):
        p, geom = atlas[location_id]
        meta = p["metadata"]
        code = "AGO" if location_id.startswith("gb:AGO:") else "CMR"
        source_id = location_id.rsplit(":", 1)[1]
        raw = official[code].get(source_id)
        assert raw is not None, f"scoped ID absent from pinned source: {location_id}"
        rawp = raw["properties"]
        expected_level = "ADM2" if code == "AGO" else "ADM3"
        assert rawp["shapeGroup"] == code and rawp["shapeType"] == expected_level
        assert meta["source_id"] == f"gb:{code}:{expected_level}"
        parent_id = p.get("parent_id", "")
        parent = hierarchy_nodes.get(parent_id, {}).get("name", "")
        provinces[parent_id] = provinces.get(parent_id, 0) + 1
        atlas_geom_type = geom.get("type", "")
        atlas_component_count = len(geom.get("coordinates", [])) if atlas_geom_type == "MultiPolygon" else 1
        source_geom = raw.get("geometry") or {}
        source_geom_type = source_geom.get("type", "")
        source_component_count = len(source_geom.get("coordinates", [])) if source_geom_type == "MultiPolygon" else 1
        area_km2 = source_area_m2(source_geom) / 1_000_000
        geometry_equal = json.dumps(geom, sort_keys=True, separators=(",", ":")) == json.dumps(source_geom, sort_keys=True, separators=(",", ":"))
        source_name_latin1_roundtrip = False
        try:
            source_name_latin1_roundtrip = rawp["shapeName"].encode("latin-1").decode("utf-8") == p["name"]
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        recommended_parent = ""
        if code == "AGO":
            classification = "correction-needed"
            rationale = "The 2018 source's four-unit Cabinda ADM2 roster is superseded by Angola Law 14/24 (2024), which defines ten municipalities. Existing geometry may be historical; it does not establish all current municipalities or their boundaries."
        elif location_id in YAOUNDE_PARENT_CHECK:
            classification = "correction-needed"
            recommended_parent = "framework:province:mfoundi:93d34314f8de"
            rationale = "MINDDEVEL's Mfoundi department page includes 2020 mayor-election instruments for Yaoundé I–VII; the issue-pinned atlas parent is a neighboring department (Lékié for Yaoundé I, II, VII; Mefou-et-Afamba for Yaoundé V). Propose Mfoundi parent reconciliation and inspect geometry against official boundary sources; this source supports the administrative parent, not exact polygon accuracy or present-day boundary currency."
        else:
            classification = "insufficient-evidence"
            rationale = "ID and geometry reproduce from the pinned 2017 source. MINAT confirms 360 arrondissements nationally, but this reviewed evidence set lacks a primary current, unit-by-unit third-level legal roster and boundary source; count agreement does not validate this unit's name, parent or boundary."
        summary[classification] += 1
        hierarchy_overlap = meta.get("hierarchy_overlap")
        lines.append({
            "location_id": location_id,
            "country": code,
            "source_id": meta["source_id"],
            "source_feature_id": source_id,
            "atlas_name": p["name"],
            "source_name": rawp["shapeName"],
            "name_equal_exactly": p["name"] == rawp["shapeName"],
            "source_name_latin1_utf8_roundtrip_matches_atlas": source_name_latin1_roundtrip,
            "atlas_parent_id": parent_id,
            "atlas_parent_name": parent,
            "hierarchy_source": meta.get("hierarchy_source", ""),
            "hierarchy_overlap": hierarchy_overlap if hierarchy_overlap is not None else "",
            "weak_parent_overlap_signal_lt_0_80": bool(hierarchy_overlap is not None and hierarchy_overlap < 0.8),
            "recommended_parent_id": recommended_parent,
            "independent_parent_evidence": "https://www.minddevel.gov.cm/mfoundi/" if recommended_parent else "",
            "source_level": expected_level,
            "source_vintage": SOURCES[code]["vintage"],
            "atlas_geometry_type": atlas_geom_type,
            "atlas_geometry_components": atlas_component_count,
            "source_geometry_type": source_geom_type,
            "source_geometry_components": source_component_count,
            "source_atlas_component_counts_equal": source_component_count == atlas_component_count,
            "source_geometry_equal_to_atlas": geometry_equal,
            "atlas_coordinate_vertices": vertex_count(geom.get("coordinates", [])),
            "source_coordinate_vertices": vertex_count(source_geom.get("coordinates", [])),
            "source_area_km2_screening_estimate": round(area_km2, 3),
            "classification": classification,
            "rationale": rationale,
        })

    with (OUT / "unit-review.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(lines[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(lines)
    expected_portions = {row["id"]: row["full_province_locations"] for row in scope["province_scopes"]}
    observed_portions = {parent_id: count for parent_id, count in provinces.items()}
    assert observed_portions == expected_portions, "province portion scope differs from the pinned scope.json"

    source_report = {
        "retrieved_utc_date": "2026-10-05",
        "reproduction_context_response_sha256": observed_context_hashes,
        "sources": {
            code: {**meta, **results[code], "retention": "restoration-only; exact original URL and SHA-256 recorded; raw GeoJSON is not committed"}
            for code, meta in SOURCES.items()
        },
        "primary_context_sources": [
            {"name": "Angola Diário da República, Lei 14/24", **LEGAL},
            {"name": "Cameroon MINAT, Services Locaux", "url": CONTEXT_HASHES["minat_services"][0], "retrieved_utc_date": "2026-10-05", "sha256": CONTEXT_HASHES["minat_services"][1], "finding": "10 regions, 58 departments, 360 arrondissements; ministry assigns governors/prefects/sub-prefects to respective tiers"},
            {"name": "UN SALB Cameroon", "url": CONTEXT_HASHES["salb_cameroon"][0], "retrieved_utc_date": "2026-10-05", "sha256": CONTEXT_HASHES["salb_cameroon"][1], "finding": "Validated administrative polygon data with temporal validity to 2024-08-07; national geospatial authority listed as Institut National de Cartographie; SALB is second administrative level, so it does not validate ADM3 boundaries"},
            {"name": "UN SALB Terms of Use 2021", "url": CONTEXT_HASHES["salb_terms"][0], "retrieved_utc_date": "2026-10-05", "sha256": CONTEXT_HASHES["salb_terms"][1], "finding": "Non-commercial use; original content/geometry cannot be changed without contributor consent; do not commit its data to this public evidence packet absent license clearance"},
            {"name": "UN SALB Data Specifications", "url": CONTEXT_HASHES["salb_specifications"][0], "retrieved_utc_date": "2026-10-05", "sha256": CONTEXT_HASHES["salb_specifications"][1], "finding": "SALB attribute specification identifies administrative levels and fields through ADM2; this source cannot itself validate country ADM3 boundaries"},
            {"name": "Cameroon MINDDEVEL Mfoundi department page", "url": "https://www.minddevel.gov.cm/mfoundi/", "retrieved_utc_date": "2026-10-05", "sha256": "db416e29e1705fa1a4fa8775e5f5ff4e8d2642f9a7b950e00322c125fc209d97", "source_vintage": "2020 records; page modified 2020-03-04", "finding": "Official departmental page identifies Mfoundi and lists the seven Yaoundé I–VII commune mayor-election instruments; supports a Mfoundi parent correction proposal but does not prove present-day boundary coordinates"},
        ],
        "outputs": {"scope_count": len(lines), "by_classification": dict(summary), "by_country": dict(collections.Counter(r["country"] for r in lines)), "source_name_mismatches": [r["location_id"] for r in lines if not r["name_equal_exactly"]], "encoding_roundtrip_repairs": sum((not r["name_equal_exactly"]) and r["source_name_latin1_utf8_roundtrip_matches_atlas"] for r in lines), "corrected_parent_recommendations": {r["location_id"]: {"atlas_parent_id": r["atlas_parent_id"], "recommended_parent_id": r["recommended_parent_id"]} for r in lines if r["recommended_parent_id"]}, "weak_parent_overlap_review_triggers_lt_0_80": [{"location_id": r["location_id"], "atlas_name": r["atlas_name"], "atlas_parent_id": r["atlas_parent_id"], "overlap": r["hierarchy_overlap"]} for r in lines if r["weak_parent_overlap_signal_lt_0_80"]], "largest_source_features_km2_screening_estimate": [{"location_id": r["location_id"], "atlas_name": r["atlas_name"], "area_km2": r["source_area_km2_screening_estimate"]} for r in sorted((r for r in lines if r["country"] == "CMR"), key=lambda x: x["source_area_km2_screening_estimate"], reverse=True)[:10]], "exact_geometry_object_matches": sum(r["source_geometry_equal_to_atlas"] for r in lines), "total_source_coordinate_vertices": sum(r["source_coordinate_vertices"] for r in lines), "total_atlas_coordinate_vertices": sum(r["atlas_coordinate_vertices"] for r in lines), "atlas_geometry_types": {"/".join(k): v for k, v in collections.Counter((r["country"], r["atlas_geometry_type"]) for r in lines).items()}, "source_geometry_types": {"/".join(k): v for k, v in collections.Counter((r["country"], r["source_geometry_type"]) for r in lines).items()}, "multipart_atlas_locations": [{"location_id": r["location_id"], "atlas_parts": r["atlas_geometry_components"], "source_parts": r["source_geometry_components"]} for r in lines if r["atlas_geometry_type"] == "MultiPolygon"], "source_atlas_component_count_differences": [{"location_id": r["location_id"], "atlas_name": r["atlas_name"], "source_parts": r["source_geometry_components"], "atlas_parts": r["atlas_geometry_components"]} for r in lines if not r["source_atlas_component_counts_equal"]], "province_portion_counts": provinces},
        "limits": ["This compares ID/name/geometry provenance and source tier; it does not independently certify geometry correctness.", "Cabinda Law 14/24 defines municipality names and natural/coordinate boundary descriptions; polygons still need reconstruction from legally reusable detailed evidence and review.", "Cameroon national and regional administrative counts do not authenticate individual third-level names, boundaries, parent assignments, or complete coverage for this subset.", "Official HTML pages include dynamic response markup. Their exact retrieval-time byte hashes are retained above; reruns record the current response hash and verify substantive text markers. Stable GeoJSON/PDF inputs are strictly checked against their exact source hashes.", "No locations, IDs, parents, geometry, pins, or release files are modified."],
    }
    (OUT / "audit-summary.json").write_text(json.dumps(source_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(source_report["outputs"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
