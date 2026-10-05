#!/usr/bin/env python3
"""Capture authority references, retaining only sources with clear reuse terms."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

ROOT = Path(__file__).resolve().parents[3]
PKT = ROOT / "data/regional-review/regional-review-599d6fe712bbbcae"
SOURCES = PKT / "sources"
RECEIPT = PKT / "authority-document-retrieval-receipts.json"
assert not RECEIPT.exists(), f"Refusing to overwrite {RECEIPT}"


def capture(source_id, url, relative_path, *, retain, terms, limit=96 * 1024 * 1024):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (WorldAtlas public evidence research)"})
    try:
        with urlopen(request, timeout=120) as response:
            data = response.read(limit + 1)
            if len(data) > limit:
                raise RuntimeError(f"Response exceeds capture bound: {source_id}")
            record = {
                "source_id": source_id,
                "requested_url": url,
                "final_url": response.geturl(),
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "response_headers": {k: v for k, v in response.headers.items()
                                     if k.lower() not in {"set-cookie", "set-cookie2"}},
                "bytes": len(data),
                "sha256": sha256(data).hexdigest(),
                "retained": retain,
                "reuse_terms": terms,
            }
    except (HTTPError, URLError, TimeoutError) as error:
        return {"source_id": source_id, "requested_url": url,
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "http_status": getattr(error, "code", None), "error": str(error),
                "retained": False, "reuse_terms": terms}
    if retain:
        target = SOURCES / relative_path
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite retained source: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        record["retained_path"] = relative_path
    else:
        record["retained_path"] = None
    return record


records = [
    capture(
        "census-tigerweb-acs26-layer-82-current-metadata",
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2026/MapServer/82?f=pjson",
        "census-tigerweb-acs26/layer-82-metadata-20261005.json",
        retain=True,
        terms="U.S. Census Bureau public service metadata; public domain.",
    ),
    capture(
        "census-regions-divisions-reference-20261005",
        "https://www2.census.gov/geo/pdfs/maps-data/maps/reference/us_regdiv.pdf",
        "census-documents/us-regions-divisions-20261005.pdf",
        retain=True,
        terms="U.S. Census Bureau federal publication; public domain.",
    ),
    capture(
        "census-geography-glossary-county-equivalent-20261005",
        "https://www.census.gov/programs-surveys/geography/about/glossary.html",
        "census-documents/geography-glossary-20261005.html",
        retain=True,
        terms="U.S. Census Bureau factual web content; public domain.",
    ),
    capture(
        "govuk-bermuda-overseas-territory-status-20261005",
        "https://www.gov.uk/foreign-travel-advice/bermuda",
        "bermuda-official/govuk-bermuda-advice-20261005.html",
        retain=True,
        terms="UK Government web content under the Open Government Licence v3.0, excluding logos/third-party content.",
    ),
    capture(
        "bermuda-2016-census-parish-definition",
        "https://www.gov.bm/sites/default/files/2016%20Census%20Report.pdf",
        "bermuda-official/2016-census-report.pdf",
        retain=False,
        terms="Official Bermuda statistical report; reuse licence not established. Preserve URL, hash, and restoration instructions only.",
    ),
    capture(
        "bermuda-1991-census-parish-map",
        "https://www.gov.bm/sites/default/files/1991_Census_of_Population_and_Housing_Map_Supplement.pdf",
        "bermuda-official/1991-census-map-supplement.pdf",
        retain=False,
        terms="Official Bermuda statistical map supplement; reuse licence not established. Preserve URL, hash, and restoration instructions only.",
    ),
    capture(
        "arcgis-bermuda-2022-country-boundary-item-metadata",
        "https://www.arcgis.com/sharing/rest/content/items/7ff244bf51954456810b81a98509f21c?f=pjson",
        "bermuda-official/arcgis-country-boundary-item-metadata.json",
        retain=True,
        terms="Metadata only. The item states geometry is provided under Esri terms and may not be exported; no feature/query endpoint was called and no geometry was downloaded or used.",
    ),
]
RECEIPT.write_text(json.dumps({"version": 1, "records": records}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"captured": len(records), "records": records}, indent=2))
