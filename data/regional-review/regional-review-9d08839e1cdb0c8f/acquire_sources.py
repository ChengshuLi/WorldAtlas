#!/usr/bin/env python3
"""Reproducibly restore the licensed boundary inputs and metadata in this packet."""
from __future__ import annotations
import gzip, hashlib, json, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
SOURCES.mkdir(parents=True, exist_ok=True)
UA = "WorldAtlas-geography-evidence/1.0 (source metadata and geographic research)"

def get(url: str, timeout: int = 90) -> tuple[bytes, str, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), response.geturl(), dict(response.headers.items())

def save_gzip(name: str, data: bytes) -> dict:
    path = SOURCES / name
    path.write_bytes(gzip.compress(data, mtime=0))
    return {"file": f"sources/{name}", "gzip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "gzip_bytes": path.stat().st_size, "restored_bytes": len(data),
            "restored_sha256": hashlib.sha256(data).hexdigest()}

results = {"acquired_at_utc": "2026-10-04", "sources": []}
for code, gb_url in [
    ("SLE", "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SLE/ADM2/geoBoundaries-SLE-ADM2.geojson"),
    ("TGO", "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TGO/ADM2/geoBoundaries-TGO-ADM2.geojson"),
]:
    data, final_url, headers = get(gb_url)
    saved = save_gzip(f"geoboundaries-{code}-adm2-2017.geojson.gz", data)
    meta, meta_final, _ = get(f"https://www.geoboundaries.org/api/current/gbOpen/{code}/ADM2/")
    m = json.loads(meta)
    meta_saved = save_gzip(f"geoboundaries-{code}-adm2-current-api-metadata.json.gz", meta)
    results["sources"].append({"provider": "geoBoundaries", "country": code, "role": m.get("boundaryCanonical"),
        "vintage": m.get("boundaryYearRepresented"), "source": m.get("boundarySource"),
        "license": m.get("boundaryLicense"), "canonical_url": gb_url, "resolved_url": final_url,
        "headers": {k:v for k,v in headers.items() if k.lower() in ("content-type","content-length","last-modified","etag")},
        "catalog_metadata_url": f"https://www.geoboundaries.org/api/current/gbOpen/{code}/ADM2/",
        "catalog_metadata_resolved_url": meta_final, "catalog_api_metadata": m,
        "retained_geojson": saved, "retained_metadata": meta_saved})

for code, dataset_id, resource_id in [
    ("SLE", "cod-ab-sle", "dfd53f5f-9846-4f14-bda7-953d3c767279"),
    ("TGO", "cod-ab-tgo", "e08c2ae7-411b-4d83-a61e-2350ba93c924"),
]:
    meta_url = f"https://data.humdata.org/api/3/action/package_show?id={dataset_id}"
    raw, resolved, _ = get(meta_url)
    package = json.loads(raw)["result"]
    pkg_saved = save_gzip(f"hdx-{dataset_id}-package-metadata.json.gz", raw)
    resource = next(x for x in package["resources"] if x["id"] == resource_id)
    raw, download_url, headers = get(resource["url"], timeout=180)
    saved = save_gzip(f"hdx-{dataset_id}-geojson.zip.gz", raw)
    results["sources"].append({"provider": "OCHA HDX Common Operational Dataset", "country": code,
        "dataset_id": dataset_id, "dataset_title": package["title"], "license": package.get("license_title"),
        "metadata_modified": package.get("metadata_modified"), "dataset_notes": package.get("notes"),
        "catalog_metadata_url": meta_url, "catalog_metadata_resolved_url": resolved,
        "catalog_metadata_file": pkg_saved, "resource": resource,
        "download_resolved_url": download_url,
        "headers": {k:v for k,v in headers.items() if k.lower() in ("content-type","content-length","last-modified","etag")},
        "retained_original_archive": saved})

# These two OCHA catalog entries expose settlement files under `Other` rather
# than an explicit reusable license. Record exact restoration routes and rights
# metadata but do not put the files in the public packet.
for code, dataset_id in [("SLE", "sierra-leone-settlements"), ("TGO", "togo-settlements")]:
    meta_url = f"https://data.humdata.org/api/3/action/package_show?id={dataset_id}"
    raw, resolved, _ = get(meta_url)
    package = json.loads(raw)["result"]
    meta_saved = save_gzip(f"hdx-{dataset_id}-package-metadata.json.gz", raw)
    results["sources"].append({"provider": "OCHA HDX Common Operational Dataset settlements catalog",
        "country": code, "dataset_id": dataset_id, "dataset_title": package["title"],
        "license": package.get("license_title"), "metadata_modified": package.get("metadata_modified"),
        "dataset_notes": package.get("notes"), "catalog_metadata_url": meta_url,
        "catalog_metadata_resolved_url": resolved, "retained_catalog_metadata": meta_saved,
        "resources_for_restoration": package.get("resources", []),
        "bytes_retained": False,
        "reason": "Catalog license is `Other`; redistribution terms are unspecified. Restore only after reviewing the current catalog license and conditions."})

# Region-wide edge-matched COD geometry provides a common-vintage neighbor
# screen; these are evidence inputs, never replacement shared boundaries.
dataset_id = "west-and-central-africa-administrative-boundaries-levels"
meta_url = f"https://data.humdata.org/api/3/action/package_show?id={dataset_id}"
raw, resolved, _ = get(meta_url)
package = json.loads(raw)["result"]
pkg_saved = save_gzip("hdx-wca-cod-package-metadata.json.gz", raw)
wanted = {
    "wca_admbnda_adm0_edgematched_942026.zip",
    "wca_admbnda_adm1_edgematched_942026.zip",
    "wca_pplp_ocha.zip",
}
resources = []
for resource in package.get("resources", []):
    if resource.get("name") not in wanted:
        continue
    data, download_url, headers = get(resource["url"], timeout=180)
    saved = save_gzip("hdx-wca-" + resource["name"] + ".gz", data)
    resources.append({"resource": resource, "download_resolved_url": download_url,
        "headers": {k:v for k,v in headers.items() if k.lower() in ("content-type","content-length","last-modified","etag")},
        "retained_original_archive": saved})
results["sources"].append({"provider": "OCHA West and Central Africa Regional Office",
    "dataset_id": dataset_id, "dataset_title": package["title"], "license": package.get("license_title"),
    "metadata_modified": package.get("metadata_modified"), "dataset_notes": package.get("notes"),
    "catalog_metadata_url": meta_url, "catalog_metadata_resolved_url": resolved,
    "catalog_metadata_file": pkg_saved, "retained_resources": resources,
    "neighbor_settlement_resource_restoration": next((r for r in package.get("resources", []) if r.get("name") == "wca_pplp_ocha.zip"), None),
    "neighbor_admin2_resource_restoration": next((r for r in package.get("resources", []) if r.get("name") == "wca_admbnda_adm2_edgematched_942026.zip"), None),
    "not_retained_reason": "The regional ADM2 archive has no scoped features-only transfer method in this packet and would add over 26 MB of broad data. Current country COD-AB sources and the licensed WCA point source are retained; official catalog restoration routes are recorded."})

(SOURCES / "acquisition.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
print(json.dumps([{k:s.get(k) for k in ("provider","country","role","vintage","license","dataset_id","dataset_title","metadata_modified")} for s in results["sources"]], ensure_ascii=False, indent=2))
