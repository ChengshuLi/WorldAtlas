#!/usr/bin/env python3
"""Capture public source bytes and explicit restoration-only source receipts."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

ROOT = Path(__file__).resolve().parents[3]
PKT = ROOT / "data/regional-review/regional-review-599d6fe712bbbcae"
SOURCES = PKT / "sources"
US = SOURCES / "census-tigerweb-acs26"
CENSUS = SOURCES / "census-documents"
BERMUDA = SOURCES / "bermuda-official"
for directory in (US, CENSUS, BERMUDA):
    directory.mkdir(parents=True, exist_ok=True)


def capture(source_id, url, relative_path, *, retain, terms, limit=None):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (WorldAtlas public evidence research)"})
    try:
        with urlopen(request, timeout=120) as response:
            data = response.read((limit or (128 * 1024 * 1024)) + 1)
            if limit is not None and len(data) > limit:
                raise RuntimeError(f"Response exceeds declared capture bound for {source_id}")
            headers = {key: value for key, value in response.headers.items()
                       if key.lower() not in {"set-cookie", "set-cookie2"}}
            record = {
                "source_id": source_id,
                "requested_url": url,
                "final_url": response.geturl(),
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "response_headers": headers,
                "bytes": len(data),
                "sha256": sha256(data).hexdigest(),
                "retained": retain,
                "reuse_terms": terms,
            }
    except (HTTPError, URLError, TimeoutError) as error:
        return {
            "source_id": source_id,
            "requested_url": url,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "http_status": getattr(error, "code", None),
            "error": str(error),
            "retained": False,
            "reuse_terms": terms,
        }
    target = SOURCES / relative_path
    if retain:
        if target.name.endswith(".geojson"):
            try:
                parsed = json.loads(data)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError(f"Non-GeoJSON response for {source_id}: {error}") from error
            if parsed.get("type") != "FeatureCollection" or not isinstance(parsed.get("features"), list):
                raise RuntimeError(f"Invalid GeoJSON response for {source_id}")
            record["feature_count"] = len(parsed["features"])
        if target.exists():
            if sha256(target.read_bytes()).hexdigest() != record["sha256"]:
                raise FileExistsError(f"Remote source changed; preserve existing vintage and assign a new path: {target}")
            record["existing_retained_bytes_match"] = True
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    record["retained_path"] = relative_path if retain else None
    return record


base = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2026/MapServer"
fields = "GEOID%2CSTATE%2CCOUNTY%2CCOUNTYNS%2CBASENAME%2CNAME%2CLSADC%2CFUNCSTAT%2CCOUNTYCC%2CAREALAND%2CAREAWATER"
records = []
for state in ("01", "21", "28", "47"):
    where = f"STATE%20%3D%20%27{state}%27"
    url = f"{base}/82/query?where={where}&outFields={fields}&returnGeometry=true&outSR=4326&f=geojson"
    records.append(capture(
        f"census-tigerweb-acs26-state-{state}",
        url,
        f"census-tigerweb-acs26/counties-state-{state}.geojson",
        retain=True,
        terms="U.S. Census Bureau federal work; public domain. TIGERweb ACS26 county-equivalent layer, current source vintage described as 2026-01-01.",
    ))
out = PKT / "census-tigerweb-state-retrieval-receipts.json"
if out.exists():
    raise FileExistsError(f"Refusing to overwrite source receipts: {out}")
out.write_text(json.dumps({"version": 1, "records": records}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"captured": len(records), "records": records}, indent=2))
