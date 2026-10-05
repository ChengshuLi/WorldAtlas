#!/usr/bin/env python3
"""Reproduce bounded, pinned geoBoundaries and RESOLVE source acquisitions."""
from __future__ import annotations
import gzip, hashlib, json, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
AGENT = "WorldAtlas geography evidence research"


def fetch(url: str, timeout: int = 90) -> tuple[bytes, str, int, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.geturl(), response.status, response.headers.get("Content-Type")


def write_gzip(name: str, content: bytes) -> pathlib.Path:
    path = SOURCES / name
    import io
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0, filename="") as output:
        output.write(content)
    packed = buffer.getvalue()
    if path.exists():
        if path.read_bytes() != packed:
            raise FileExistsError(f"Refusing to replace retained source evidence: {path}")
    else:
        path.write_bytes(packed)
    return path


def write_json_preserving(path: pathlib.Path, value: object) -> None:
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"Refusing to replace retained source receipt: {path}")
    else:
        path.write_bytes(data)


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> None:
    register = json.loads((SOURCES / "register.json").read_text())
    for item in register["sources"]:
        code = item["country_code"]
        year = item["source_vintage"]
        url = item["source_url"].replace("/ADM2/", "/ADM1/").replace(f"{code}-ADM2", f"{code}-ADM1")
        body, resolved, status, content_type = fetch(url)
        collection = json.loads(body)
        output_name = f"geoboundaries-{code.lower()}-adm1-{year}.geojson.gz"
        retained = write_gzip(output_name, body)
        item["adm1_source"] = {
            "url": url, "resolved_url": resolved, "retrieved_utc": "2026-10-04",
            "http_status": status, "content_type": content_type, "bytes": len(body),
            "sha256": sha(body), "features": len(collection["features"]),
            "retained_gzip_path": "sources/" + output_name,
            "retained_gzip_bytes": retained.stat().st_size,
            "retained_gzip_sha256": sha(retained.read_bytes()),
            "feature_property_schema": sorted(collection["features"][0]["properties"].keys()) if collection["features"] else [],
            "limitation": "Pinned ADM1 name cohort retained for parent context; no overlay-based parent certification is made by acquisition alone."
        }

    item_id = "37ea320eebb647c6838c23f72abae5ef"
    layer = "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0"
    fields = "FID,ECO_NAME,BIOME_NUM,BIOME_NAME,REALM,ECO_BIOME_,NNH,ECO_ID,NNH_NAME,LICENSE"
    where = "ECO_ID IN (53,71,745,842,846)"
    query = layer + "/query?" + urllib.parse.urlencode({
        "where": where, "outFields": fields, "outSR": "4326",
        "returnGeometry": "true", "f": "geojson"
    })
    body, resolved, status, content_type = fetch(query)
    collection = json.loads(body)
    output_name = "resolve-ecoregions-53-71-745-842-846.geojson.gz"
    retained = write_gzip(output_name, body)
    receipt = {
        "publisher": "RESOLVE / Esri Living Atlas",
        "service_item": "https://www.arcgis.com/sharing/rest/content/items/" + item_id,
        "layer": layer, "query_url": query, "resolved_url": resolved,
        "method": "GET query, outSR=4326, returnGeometry=true, f=geojson",
        "where": where, "out_fields": fields, "retrieved_utc": "2026-10-04",
        "http_status": status, "content_type": content_type, "response_bytes": len(body),
        "response_sha256": sha(body), "feature_count": len(collection.get("features", [])),
        "features": [{
            "eco_id": feature["properties"].get("ECO_ID"),
            "name": feature["properties"].get("ECO_NAME"),
            "biome": feature["properties"].get("BIOME_NAME"),
            "realm": feature["properties"].get("REALM"),
            "license": feature["properties"].get("LICENSE")
        } for feature in collection.get("features", [])],
        "retained_gzip_path": "sources/" + output_name,
        "retained_gzip_bytes": retained.stat().st_size,
        "retained_gzip_sha256": sha(retained.read_bytes()),
        "limitation": "Selected complete global ecoregion polygons for all referenced ECO_IDs; this is not the full 846-feature source and no geometric intersection calculation is asserted."
    }
    write_json_preserving(SOURCES / "resolve-query-receipt.json", receipt)
    register["retrieval_date"] = "2026-10-04"
    write_json_preserving(SOURCES / "register.json", register)
    print(json.dumps({"adm1": [{"country": s["country_code"], "feature_count": s["adm1_source"]["features"], "sha256": s["adm1_source"]["sha256"]} for s in register["sources"]], "resolve": receipt}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
