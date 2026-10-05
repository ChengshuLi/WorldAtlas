#!/usr/bin/env python3
"""Hash retained original sources and record explicit source retrieval limits."""
import csv
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = ROOT / "data/regional-review/regional-review-088ef1b8992c5b6c"
SRC = OWNED / "sources"
EXPECTED = {
    "geoBoundaries-BFA-ADM2-metaData.json": "5a436248cca65ac8e892856f91c9f6361fb5cf08151fba0d3b06a3eda0628a94",
    "geoBoundaries-BFA-ADM2.geojson": "aea17813a774c47f3ee0ccc0f39906116d9e0b48add0c8adf091998281f723b0",
    "geoBoundaries-BFA-ADM3-metaData.json": "b559ada1ddb95c401556801cfef3b444c49d96590a736ec914e1d66f97469dae",
    "geoBoundaries-BFA-ADM3.geojson": "6f4d9351318bd29ace3e56d17fdcd26d74a798f47abc3c5674605b083d34cf12",
    "geoBoundaries-CIV-ADM2-metaData.json": "d7246f239e6cdef768672085ef422270edf22b3083e868e09d6d5b507121a84e",
    "geoBoundaries-CIV-ADM2.geojson": "a9035b8f759e54ae5f6c1289a7b06711d6cd4f0e9545f83e319388304e1a1403",
    "geoBoundaries-CIV-ADM3-metaData.json": "6e335f347fb1209e5dc3006ac7788cb9d0354d4f21534175e67d7a2d86066452",
    "geoBoundaries-CIV-ADM3.geojson": "7bf038dd0c666f76f5638289cf80991997a7f26e891578b57222d939e11b9da8",
    "INSD-local-poverty-2019-report.pdf": "6e7c672523bd633189646e953a22586da0cb3b7940b4545478cad242649eb55a",
    "CI-SCIO-Agroforet-EIES-2026.pdf": "b848d76f0508647665131d5f9a6ffa7ac2d64a42758754543e467d0d570610fd",
    "bfa-insd-2019-commune-roster.csv": "6c42229c7f557c48ddb2f0a5d0bb670aedbe0da2e18345007fae9358bebef2ad",
    "civ-cavally-2019-project-roster.csv": "b2c1e3cd04c6dc87ad1e7c564b75b0c20f0586954fc785b8d76a87925823ee3e",
    "cntig-ocha-subprefectures-query-2025.geojson": "11deee85b6d41698d371846b0fd57cac6ad7b28a723e686c1ab6a0e149c3065e",
    "cntig-ocha-subprefectures-layer-metadata.json": "49855a9332d87b143f04e9914559867475fda45b28f6a186af864e3a02134868",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rec(path, source_url, retrieved_at, vintage, role, license_text, provenance, **extra):
    data = path.read_bytes()
    expected = EXPECTED.get(path.name)
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit(f"Pinned source/result SHA-256 changed: {path}")
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": len(data),
        "sha256": sha(path),
        "source_url": source_url,
        "retrieved_at_utc": retrieved_at,
        "source_vintage": vintage,
        "role": role,
        "license": license_text,
        "provenance": provenance,
        **extra,
    }


gb = SRC / "geoboundaries-9469f09"
items = []
specs = {
    "BFA-ADM3": ("2007", "commune/local administrative unit; canonical source tier blank", "Public Domain (geoBoundaries metadata; license detail references source pop-up)", "retrieved 2026-10-05 in this packet from media.githubusercontent.com; LFS raw pointer was not used as content"),
    "BFA-ADM2": ("2017", "Province", "CC BY 4.0", "retrieved 2026-10-05 in this packet from media.githubusercontent.com; comparator vintage"),
    "CIV-ADM3": ("2021", "Departments (geoBoundaries layer-level label; row-level role unresolved)", "CC BY 3.0 IGO", "retained original from merged #470 packet; upstream bytes/hash match that packet's receipt; retrieved upstream at 2026-10-05T02:06:34Z"),
    "CIV-ADM2": ("2016", "régions de Côte d'Ivoire", "CC BY 4.0", "retained original from merged #470 packet; upstream bytes/hash match that packet's receipt; retrieved upstream at 2026-10-05T02:10:18Z"),
}
for name, (vintage, role, license_text, provenance) in specs.items():
    code, level = name.split("-")
    folder = gb
    if code == "CIV":
        # The preserved copy is stored flat under this packet's owned path.
        base = f"geoBoundaries-{code}-{level}"
        geo = folder / f"{base}.geojson"
        meta = folder / f"{base}-metaData.json"
        urlbase = f"https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/{code}/{level}/"
    else:
        base = f"geoBoundaries-{code}-{level}"
        geo = folder / f"{base}.geojson"
        meta = folder / f"{base}-metaData.json"
        urlbase = f"https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/{code}/{level}/"
    meta_data = json.loads(meta.read_text())
    items.append(rec(geo, urlbase + geo.name, provenance.split("; ")[-1].replace("retrieved upstream at ", "") if code == "CIV" else "2026-10-05", vintage, role, license_text, provenance,
                     feature_count=int(meta_data["admUnitCount"]), upstream_commit="9469f09592ced973a3448cf66b6100b741b64c0d"))
    items.append(rec(meta, urlbase + meta.name, provenance.split("; ")[-1].replace("retrieved upstream at ", "") if code == "CIV" else "2026-10-05", vintage, "source metadata", "as stated in metadata", provenance,
                     boundary_id=meta_data["boundaryID"], upstream_commit="9469f09592ced973a3448cf66b6100b741b64c0d"))

shared = ROOT / "data/regional-review/regional-review-ab07a23bcfd9b1db/sources"
items.append(rec(shared / "cntig-ocha-subprefectures-query-2025.geojson", "https://services-eu1.arcgis.com/HApVBfqpU6uDawrd/ArcGIS/rest/services/SP/FeatureServer/14", "2026-10-05", "reference period 2018-08-06 through 2023-09-20; service last data edit 2025-04-11", "official CNTIG/OCHA admin1 region, admin2 department, admin3 sub-prefecture cross-source comparator; original retained in merged #469 packet", "CC BY for Intergovernmental Organisations (metadata states CNTIG copyright; no version number stated)", "read-only reuse from #469 owned path; exact source bytes and hash verified against #469 source manifest"))
items.append(rec(shared / "cntig-ocha-subprefectures-layer-metadata.json", "https://services-eu1.arcgis.com/HApVBfqpU6uDawrd/ArcGIS/rest/services/SP/FeatureServer/14", "2026-10-05", "layer metadata for service data last edited 2025-04-11", "official layer schema, source and license metadata", "CC BY for Intergovernmental Organisations (metadata states CNTIG copyright; no version number stated)", "read-only reuse from #469 owned path; exact source bytes and hash verified against #469 source manifest"))

derived = []
for rel, desc in (
    ("acceptance-screen.json", "per-concern review screen for the issue's 9 geographic acceptance risks; records candidate IDs and explicit limits"),
    ("evidence/bfa-insd-2019-commune-roster.csv", "text extraction of commune/province/region rows; 342 parsed rows versus report-stated 351; incomplete and not used for absence claims"),
    ("evidence/civ-cavally-2019-project-roster.csv", "17-row extract from the official indexed AfDB text; source PDF unavailable here; preserve uncertainty"),
    ("evidence/source-review-notes.md", "worker analysis and source outcome limits"),
    ("evidence/civ-roster-provenance.md", "transcribed source passage, direct retrieval outcomes, restoration instruction"),
    ("evidence/controls/geometry-positive-control.json", "identical-polygon positive control for the WGS84 ellipsoidal-area intersection-over-union method"),
    ("evidence/controls/geometry-negative-control.json", "translated disjoint-polygon negative control for the WGS84 ellipsoidal-area intersection-over-union method"),
):
    path = OWNED / rel
    derived.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path), "description": desc})

blocked = [
    {"source_url": "https://www.insd.bf/sites/default/files/2024-10/EHCVM%202021_Rapport_IPM.pdf", "retrieved_at_utc": "2026-10-05", "status": "original inspected for Annex 6; no reuse license identified; not redistributed", "bytes": 5721087, "sha256": "6e7c672523bd633189646e953a22586da0cb3b7940b4545478cad242649eb55a", "required_restoration": "Retrieve the official PDF to a temporary local path, verify this exact SHA-256, then run evidence/extract_insd_commune_roster.py --source-pdf PATH. The report's Annex 6 states 351 communes; the pinned extraction method recovers only 342, and nonmatches are not absence evidence."},
    {"source_url": "https://eauxetforets.gouv.ci/sites/default/files/communique/clean_rapport_final_pif2_eiesa_agro-foret_scio_20260306-1.pdf", "retrieved_at_utc": "2026-10-05", "status": "original inspected for printed pages 72 and 81; no reuse license identified; not redistributed", "bytes": 10779871, "sha256": "b848d76f0508647665131d5f9a6ffa7ac2d64a42758754543e467d0d570610fd", "required_restoration": "Retrieve the official final report to a temporary path, verify this exact SHA-256, then inspect printed pages 72 and 81. Use only its described project footprint; it is not a complete territory roster."},
    {"source_url": "https://www.afdb.org/sites/default/files/ci_projet_appui_psgouv_rapport_final_cges_25oct19.pdf", "retrieved_at_utc": "2026-10-05", "status": "indexed official text inspected; direct binary retrieval returned HTTP 403 (alternate ESA host returned HTTP 502)", "sha256": None, "bytes": None, "required_restoration": "Fetch the exact final report from the official AfDB URL, verify title/date/page/wording, then record upstream hash and byte count before using it as a retained original."},
    {"source_url": "https://interieur.gouv.ci/uploads/publications/175397417134.pdf", "retrieved_at_utc": "2026-10-05 (prior inspection)", "status": "official indexed ministry source reported; direct PDF retrieval blocked", "sha256": None, "bytes": None, "required_restoration": "Retain the original Ministry order and verify its date, appointment, spelling and department relationship."},
    {"source_url": "https://rp2021.anstat.ci/wp-content/uploads/2023/09/TABLEAUX-11_DE-BASES_RP-RELIGION.pdf", "retrieved_at_utc": "2026-10-05 (prior inspection)", "status": "direct request returned 403 / Cloudflare HTML; not treated as table evidence", "sha256": None, "bytes": None, "required_restoration": "Retrieve original 2021 census tables and inspect the exact Cavally departmental/sous-prefecture roster."},
    {"source_url": "https://www.anstat.ci/public/api", "retrieved_at_utc": "2026-10-05 (prior inspection)", "status": "official API request returned 403; no rows retained", "sha256": None, "bytes": None, "required_restoration": "Retrieve all pages for department and sous-prefecture endpoints and preserve response bytes/hash and retrieval parameters."},
]
doc = {"version": 1, "issue_number": 468, "retrieval_snapshot_utc": "2026-10-05", "sources": items, "derived_research_artifacts": derived, "unavailable_sources": blocked}
out = OWNED / "source-receipts.json"
out.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
print(f"sources={len(items)} derived={len(derived)} unavailable={len(blocked)} source_receipts_sha256={sha(out)}")
