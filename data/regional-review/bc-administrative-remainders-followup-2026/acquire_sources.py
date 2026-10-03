#!/usr/bin/env python3
"""Acquire pinned, scoped official administrative boundary responses for issue #609."""
from __future__ import annotations

import gzip
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
SOURCES = PACKET / "sources"
PARENT = ROOT / "data/regional-review/regional-review-4254da254d94f450/sources"
TARGETS = ["5901", "5933", "5939", "5941", "5949", "5951", "5953", "5955", "5957", "5959"]
BC_SERVICE = "https://delivery.maps.gov.bc.ca/arcgis/rest/services/whse/bcgw_pub_whse_legal_admin_boundaries/MapServer"
NR_CAN_LAYER = "https://proxyinternet.nrcan-rncan.gc.ca/arcgis/rest/services/CLSS-SATC/CLSS_Administrative_Boundaries/MapServer/0/query"
BC_GROUPS = [
    "Regional District of East Kootenay",
    "Thompson-Nicola Regional District",
    "Columbia Shuswap Regional District",
    "Cariboo Regional District",
    "Regional District of Kitimat-Stikine",
    "Regional District of Bulkley-Nechako",
    "Regional District of Fraser-Fort George",
    "Peace River Regional District",
]
BC_LAYER_METADATA = {
    16: "https://catalogue.data.gov.bc.ca/api/3/action/package_show?id=d1aff64e-dbfe-45a6-af97-582b7f6418b9",
    24: "https://catalogue.data.gov.bc.ca/api/3/action/package_show?id=81940c47-a534-47e0-94d0-947c96a59de4",
    18: "https://catalogue.data.gov.bc.ca/api/3/action/package_show?id=e3c3c580-996a-4668-8bc5-6aa7c7dc4932",
}
NR_CAN_METADATA = "https://open.canada.ca/data/api/3/action/package_show?id=522b07b9-78e2-4819-b736-ad9208eb1067"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "WorldAtlas geography source review/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def fetch_json(url: str) -> dict:
    return json.loads(get(url))


def write_response(path: Path, url: str, raw: bytes, receipt: dict) -> None:
    retained = raw
    retained_path = path
    if path.suffix == ".geojson":
        retained = gzip.compress(raw, compresslevel=9, mtime=0)
        retained_path = path.with_suffix(path.suffix + ".gz")
    retained_path.write_bytes(retained)
    if retained_path != path:
        path.unlink(missing_ok=True)
    receipt[retained_path.name] = {
        "canonical_request_url": url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "retained_path": str(retained_path.relative_to(PACKET)),
        "retained_bytes": len(retained),
        "retained_sha256": hashlib.sha256(retained).hexdigest(),
        "retained_encoding": "gzip (lossless; decompress to recover exact response bytes)" if retained_path != path else "identity",
        "feature_count": len(json.loads(raw).get("features", [])),
    }


def arcgis_query(layer: int, *, where: str, geometry: dict | None = None) -> tuple[str, bytes]:
    params: dict[str, str] = {
        "where": where,
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": "1000",
    }
    if geometry:
        params.update(
            geometry=json.dumps(geometry, separators=(",", ":")),
            geometryType="esriGeometryEnvelope",
            inSR="4326",
            spatialRel="esriSpatialRelIntersects",
        )
    url = f"{BC_SERVICE}/{layer}/query?{urllib.parse.urlencode(params)}"
    return url, get(url)


def main() -> None:
    SOURCES.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, dict] = {}
    # Current official Statistics Canada 2021 CD polygons from the completed #485 packet.
    cds = json.loads(gzip.open(PARENT / "statistics-canada-bc-census-divisions-2021.geojson.gz", "rb").read())
    target_geometries = {
        f["properties"]["CDUID"]: shape(f["geometry"])
        for f in cds["features"]
        if f["properties"]["CDUID"] in TARGETS
    }
    assert set(target_geometries) == set(TARGETS)

    # The BC legal-area catalogue records and feature-class metadata pin source semantics/licence.
    for layer, url in BC_LAYER_METADATA.items():
        raw = get(url)
        write_response(SOURCES / f"bc-layer-{layer}-catalog.json", url, raw, receipt)
        info_url = f"{BC_SERVICE}/{layer}/info/metadata?f=json"
        write_response(SOURCES / f"bc-layer-{layer}-metadata.json", info_url, get(info_url), receipt)

    groups_sql = ",".join("'" + value.replace("'", "''") + "'" for value in BC_GROUPS)
    # Include Stikine Region as a special province-administered area and Northern Rockies RGM.
    rd_names = [name.replace("Columbia Shuswap", "Columbia-Shuswap") for name in BC_GROUPS] + ["Stikine Region (Unincorporated)"]
    rd_values = ",".join("'" + value.replace("'", "''") + "'" for value in rd_names)
    rd_where = f"ADMIN_AREA_NAME IN ({rd_values})"
    url, raw = arcgis_query(16, where=rd_where)
    write_response(SOURCES / "bc-regional-districts-and-stikine.geojson", url, raw, receipt)

    # Layer 24 uses a different regional-district spelling/assignment convention
    # for some unincorporated areas. Retrieve every EA intersecting each target
    # CD envelope, then deduplicate by OBJECTID instead of trusting group labels.
    ea_features: dict[int, dict] = {}
    ea_urls = []
    for cd, target in target_geometries.items():
        minx, miny, maxx, maxy = target.bounds
        geom = {"xmin": minx, "ymin": miny, "xmax": maxx, "ymax": maxy, "spatialReference": {"wkid": 4326}}
        url, raw = arcgis_query(24, where="1=1", geometry=geom)
        ea_urls.append(url)
        write_response(SOURCES / f"bc-electoral-areas-cd-{cd}.geojson", url, raw, receipt)
        for feature in json.loads(raw)["features"]:
            ea_features[int(feature["properties"]["OBJECTID"])] = feature
    ea_raw = json.dumps({"type": "FeatureCollection", "features": list(ea_features.values())}, separators=(",", ":")).encode()
    write_response(SOURCES / "bc-electoral-areas.geojson", "\n".join(ea_urls), ea_raw, receipt)
    receipt["bc-electoral-areas.geojson.gz"]["note"] = "Derived deduplicated OBJECTID union; all raw original per-CD responses are retained beside it."

    muni_where = f"ADMIN_AREA_GROUP_NAME IN ({groups_sql}) OR ADMIN_AREA_NAME LIKE '%Northern Rockies%'"
    url, raw = arcgis_query(18, where=muni_where)
    write_response(SOURCES / "bc-municipalities.geojson", url, raw, receipt)

    # Fetch the federally maintained legislative-boundary layer only within each assigned CD envelope.
    federal_metadata = get(NR_CAN_METADATA)
    write_response(SOURCES / "nrcan-alclb-catalog.json", NR_CAN_METADATA, federal_metadata, receipt)
    for cd in TARGETS:
        g = target_geometries[cd]
        minx, miny, maxx, maxy = g.bounds
        geom = {"xmin": minx, "ymin": miny, "xmax": maxx, "ymax": maxy, "spatialReference": {"wkid": 4326}}
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultRecordCount": "500",
            "orderByFields": "OBJECTID ASC",
            "geometry": json.dumps(geom, separators=(",", ":")),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
        }
        offset = 0
        page = 0
        while True:
            params["resultOffset"] = str(offset)
            url = f"{NR_CAN_LAYER}?{urllib.parse.urlencode(params)}"
            raw = get(url)
            response = json.loads(raw)
            count = len(response.get("features", []))
            write_response(SOURCES / f"nrcan-alclb-cd-{cd}-page-{page}.geojson", url, raw, receipt)
            if count < 500 and not response.get("exceededTransferLimit"):
                break
            if count == 0:
                raise RuntimeError(f"Empty page while result limit remained set for CD {cd}")
            offset += count
            page += 1
            time.sleep(0.1)

    (SOURCES / "acquisition-receipt.json").write_text(
        json.dumps({"retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "responses": receipt}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({name: {"bytes": value["bytes"], "features": value.get("feature_count")} for name, value in receipt.items()}, indent=2))


if __name__ == "__main__":
    main()
