#!/usr/bin/env python3
"""Capture bounded official Kartverket WFS source snapshots; no GIS is performed."""
from __future__ import annotations
import hashlib
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "sources" / "sjoekart-dybdedata-wfs-20261008"
PREDECESSOR = Path("research/geography/norway-adm2-source-fit-1492/vintages/exact-overlay-acceptance-20261008/overlay-v1.json")
EXPECTED_PREDECESSOR_SHA256 = "3bb69e040b98e6a14f1b6a91deec73543a9b82cb94a4b893d3b401e69395fe8f"
HITS_LEDGER = ROOT / "sources" / "kartverket-metadata-20261008" / "sjoekart-dybdedata-wfs-bbox-hits" / "query-ledger.json"
ENDPOINT = "https://wfs.geonorge.no/skwms1/wfs.dybdedata"
LICENSE = "CC BY 4.0; attribute Kartverket"
PER_RESPONSE_LIMIT = 32 * 1024 * 1024
TOTAL_RESPONSE_LIMIT = 224 * 1024 * 1024
TYPE_SUFFIX = {"app:Kystkontur": "kystkontur", "app:Landareal": "landareal"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def main() -> None:
    source_raw = PREDECESSOR.read_bytes()
    if sha(source_raw) != EXPECTED_PREDECESSOR_SHA256:
        raise SystemExit("pinned #1492 overlay bytes changed")
    ledger = json.loads(HITS_LEDGER.read_text())
    if len(ledger["queries"]) != 14:
        raise SystemExit("expected exactly fourteen prior count-only window queries")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    captures = []
    for query in ledger["queries"]:
        typename = query["type_name"]
        if typename not in TYPE_SUFFIX:
            raise SystemExit(f"unrecognized WFS typename: {typename}")
        expected = int(query["numberMatched"])
        if not 0 <= expected < 200:
            raise SystemExit(f"unsafe feature count {expected} for {typename}")
        original = urllib.parse.urlsplit(query["url"])
        params = dict(urllib.parse.parse_qsl(original.query, keep_blank_values=True))
        if params.get("resultType") != "hits":
            raise SystemExit("prior query is not resultType=hits")
        params["resultType"] = "results"
        params["count"] = "200"
        params["srsName"] = "urn:ogc:def:crs:EPSG::4258"
        url = urllib.parse.urlunsplit((original.scheme, original.netloc, original.path, urllib.parse.urlencode(params), ""))
        request = urllib.request.Request(url, headers={"User-Agent": "WorldAtlas bounded source-custody research"})
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read(PER_RESPONSE_LIMIT + 1)
            headers = {"date": response.headers.get("Date"), "content_type": response.headers.get("Content-Type"),
                       "content_disposition": response.headers.get("Content-Disposition"), "final_url": response.geturl()}
            status = response.status
        if len(data) > PER_RESPONSE_LIMIT:
            raise SystemExit(f"per-response safety cap exceeded for {query['component_id']} {typename}; response not retained")
        if total_bytes + len(data) > TOTAL_RESPONSE_LIMIT:
            raise SystemExit("combined response safety cap exceeded; current response not retained")
        root = ET.fromstring(data)
        matched, returned = root.get("numberMatched"), root.get("numberReturned")
        members = [node for node in root if local(node.tag) == "member"]
        feature_nodes = [child for member in members for child in list(member)]
        feature_ids = [next((value for key, value in feature.attrib.items() if local(key) == "id"), None) for feature in feature_nodes]
        if status != 200 or len(feature_nodes) != expected:
            raise SystemExit(f"incomplete WFS response: expected={expected} actual_members={len(feature_nodes)} matched={matched} returned={returned}")
        if matched not in ("unknown", str(expected)) or returned not in ("unknown", "0", str(expected)):
            raise SystemExit(f"unexpected WFS count attributes: expected={expected} matched={matched} returned={returned} actual_members={len(feature_nodes)}")
        if len(set(feature_ids)) != len(feature_ids) or any(value is None for value in feature_ids):
            raise SystemExit("missing or duplicate gml:id in returned features")
        names = {local(feature.tag) for feature in feature_nodes}
        if names - {typename.split(":", 1)[1]}:
            raise SystemExit(f"unexpected returned feature type(s): {sorted(names)}")
        dates = {key: [] for key in ("førsteDatafangstdato", "oppdateringsdato", "datauttaksdato")}
        for feature in feature_nodes:
            for element in feature.iter():
                key = local(element.tag)
                if key in dates and element.text:
                    dates[key].append(element.text.strip())
        name = f"{query['component_id'].split(':', 1)[1][:8]}-{TYPE_SUFFIX[typename]}.gml"
        target = SOURCE_DIR / name
        target.write_bytes(data)
        total_bytes += len(data)
        captures.append({
            "component_id": query["component_id"], "target_id": query["target_id"], "typename": typename,
            "request_url": url, "request_bbox": query["added_area_bbox_deg_with_0.02_context_margin"],
            "bbox_margin_degrees": 0.02, "margin_role": query["margin_role"], "license": LICENSE,
            "http_status": status, **headers, "service_timestamp": root.get("timeStamp"),
            "number_matched_attribute": matched, "number_returned_attribute": returned,
            "count_validation": "member_count matched prior resultType=hits; WFS count attributes reported inconsistently and are recorded without relying on them",
            "member_count": len(feature_nodes),
            "feature_ids": feature_ids, "feature_dates": {key: sorted(set(values)) for key, values in dates.items()},
            "path": target.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha(data),
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "request_wall_seconds": round(time.monotonic() - started, 3),
        })
        print(f"{query['component_id'].split(':')[-1][:8]} {typename} {expected} features {len(data)} bytes sha256={sha(data)}", flush=True)
    index = {
        "version": 1, "issue": 1510, "source": "Kartverket Sjøkart - Dybdedata WFS",
        "endpoint": ENDPOINT, "license": LICENSE, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "predecessor_overlay_sha256": EXPECTED_PREDECESSOR_SHA256, "capture_script_sha256": sha(Path(__file__).read_bytes()),
        "crs": "urn:ogc:def:crs:EPSG::4258", "feature_types": ["app:Kystkontur", "app:Landareal"],
        "record_count": len(captures), "total_response_bytes": total_bytes,
        "response_limits": {"per_response_bytes": PER_RESPONSE_LIMIT, "combined_bytes": TOTAL_RESPONSE_LIMIT},
        "limits": [
            "This packet retains source features only; it performs no overlay, distance, coverage, topology or land/water classification.",
            "WFS is updated continuously; every raw response is pinned by retrieval timestamp, service timestamp, request, byte count and SHA-256.",
            "WFS 2.0.0 responses inconsistently report numberMatched=unknown and numberReturned=0 despite including feature members. Completeness is checked against the preceding resultType=hits count and parsed member count; raw contradictory attributes are preserved.",
            "Kystkontur is defined as mean high water, but feature-level survey age and positional registration vary; exact applicability remains unknown until admitted geometry comparison and evidence review.",
            "A 0.02-degree request margin supplies nearby source context only; it is not a measurement buffer, tolerance, accuracy estimate or physical inference."
        ],
        "captures": captures,
    }
    out = SOURCE_DIR / "source-snapshot-index.json"
    if out.exists():
        raise SystemExit("refusing to overwrite source snapshot index")
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "source-bytes-captured", "records": len(captures), "bytes": total_bytes, "index": out.relative_to(ROOT).as_posix()}))


if __name__ == "__main__":
    main()
