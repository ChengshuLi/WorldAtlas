#!/usr/bin/env python3
"""Capture public Shom Litto3D product inventories and package metadata without raster payloads."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, urllib.request, xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).parent / "sources" / "shom_litto3d_catalog_20261008"
RAW = ROOT / "raw"
LISTING_ARCHIVE = ROOT / "package-listing-responses.zip"
PRODUCTS = {
    "eparses": "LITTO3D_EPARSES_2012_PACK_DL",
    "mayotte": "LITTO3D_MAYOT_2012_PACK_DL",
    "reunion": "LITTO3D_REUNION_2016_PACK_DL",
}
BASE = "https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/"
API = "https://services.data.shom.fr/geonetwork/system/api/records/"
UTC_RETRIEVED = datetime.now(timezone.utc).isoformat(timespec="seconds")
HEADERS = {"User-Agent": "WorldAtlas geography source research; issue #633"}

def get(url, accept=None):
    headers = dict(HEADERS)
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        return body, {k.lower(): v for k, v in r.headers.items()}

def fetch_record(task):
    area, product, pkg, metadata_id = task
    url = API + metadata_id.removesuffix(".xml") + ".xml?approved=true&increasePopularity=false"
    body, headers = get(url, "application/xml")
    path = RAW / area / (pkg + ".xml")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(body)
    return {"area": area, "product": product, "package": pkg, "metadata_id": metadata_id,
            "url": url, "path": str(path.relative_to(ROOT)), "sha256": sha256(body).hexdigest(),
            "bytes": len(body), "content_type": headers.get("content-type"),
            "retrieved_utc": UTC_RETRIEVED}

def fetch_listing(task):
    area, product, pkg = task
    url = BASE + product + "/prepackage/" + pkg
    body, headers = get(url, "application/json")
    obj = json.loads(body)
    return {"area": area, "package": pkg, "url": url,
            "sha256": sha256(body).hexdigest(), "bytes": len(body),
            "files": obj.get("downloadFiles", []), "raw_member": area+"/"+pkg+".json",
            "retrieved_utc": UTC_RETRIEVED, "_raw_body": body}

ROOT.mkdir(parents=True, exist_ok=True)
group_entries = {}
tasks = []
for area, product in PRODUCTS.items():
    url = BASE + product
    body, headers = get(url, "application/json")
    path = ROOT / (area + "-product-group.json")
    with path.open("xb") as f:
        f.write(body)
    obj = json.loads(body)
    entries = obj.get("prepackageResources", [])
    group_entries[area] = {"url": url, "path": path.name, "sha256": sha256(body).hexdigest(),
        "bytes": len(body), "product_name": product, "package_count": len(entries),
        "retrieved_utc": UTC_RETRIEVED}
    for e in entries:
        for mid in e.get("metadataIds", []):
            tasks.append((area, product, e["prepackageName"], mid))

records = []
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(fetch_record, t) for t in tasks]
    for f in as_completed(futures):
        records.append(f.result())
records.sort(key=lambda x: (x["area"], x["package"]))
list_tasks = [(x["area"], x["product"], x["package"]) for x in records]
listings = []
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(fetch_listing, t) for t in list_tasks]
    for f in as_completed(futures):
        listings.append(f.result())
listings.sort(key=lambda x: (x["area"], x["package"]))
with ZipFile(LISTING_ARCHIVE, "x", compression=ZIP_DEFLATED) as archive:
    for row in listings:
        archive.writestr(row["raw_member"], row.pop("_raw_body"))
listing_archive_bytes = LISTING_ARCHIVE.read_bytes()
inventory = {"retrieved_utc": UTC_RETRIEVED, "source": "Shom INSPIRE prepackage catalog",
    "product_groups": group_entries, "metadata_records": records,
    "package_file_listings": listings,
    "package_listings_archive": {"path": LISTING_ARCHIVE.name,
        "sha256": sha256(listing_archive_bytes).hexdigest(), "bytes": len(listing_archive_bytes),
        "format": "ZIP with original per-package response bytes"}}
out = ROOT / "catalog-capture.json"
with out.open("x", encoding="utf-8") as f:
    f.write(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"retrieved_utc": UTC_RETRIEVED,
    "products": {k: v["package_count"] for k,v in group_entries.items()},
    "metadata_records":len(records),"listings":len(listings),
    "listing_archive_bytes":len(listing_archive_bytes),
    "capture_sha256":sha256(out.read_bytes()).hexdigest(),
    "metadata_bytes":sum(x["bytes"] for x in records),
    "packages_with_files":sum(bool(x["files"]) for x in listings)}, indent=2))
