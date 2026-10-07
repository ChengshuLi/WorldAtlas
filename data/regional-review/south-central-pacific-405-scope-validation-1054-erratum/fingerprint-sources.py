#!/usr/bin/env python3
"""Record whole-response hashes for cited public pages without retaining page bytes."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "cook-domestic-shipping-policy": "https://www.mfem.gov.ck/post/cook-islands-government-releases-domestic-shipping-policy",
    "french-polynesia-dpam": "https://www.service-public.pf/dpam/presentation-de-la-dpam/",
    "french-polynesia-planning": "https://www.service-public.pf/dca/plansdamenagement/",
    "unesco-henderson": "https://whc.unesco.org/en/list/487",
    "fws-baker": "https://www.fws.gov/refuge/baker-island",
    "fws-howland": "https://www.fws.gov/refuge/howland-island",
    "fws-jarvis": "https://www.fws.gov/refuge/jarvis-island/about-us",
    "fws-palmyra": "https://www.fws.gov/refuge/palmyra-atoll",
    "chile-law-16441-version-1966": "https://nuevo.leychile.cl/navegar?idNorma=28472&idVersion=1966-03-01",
    "kiribati-nso-line-phoenix": "https://nso.gov.ki/kiribati-districts/line-phoenix/",
    "kiribati-met-island-groups": "https://www.met.gov.ki/index.php/component/sppagebuilder/page/18",
}


def retrieve(url):
    request = Request(url, headers={"User-Agent": "WorldAtlas research evidence/1.0", "Accept-Encoding": "identity"})
    with urlopen(request, timeout=30) as response:
        body = response.read(32 * 1024 * 1024 + 1)
        if len(body) > 32 * 1024 * 1024:
            raise ValueError("source response exceeds 32 MiB recording limit")
        headers = response.headers
        return {
            "requested_url": url,
            "final_url": response.geturl(),
            "http_status": response.status,
            "content_type": headers.get("Content-Type"),
            "etag": headers.get("ETag"),
            "last_modified": headers.get("Last-Modified"),
            "response_bytes": len(body),
            "response_sha256": sha256(body).hexdigest(),
            "retention": "response bytes not retained; restore by a new retrieval from final_url",
        }


results = []
for source_id, url in SOURCES.items():
    error = None
    for attempt in range(1, 4):
        try:
            result = retrieve(url)
            result["id"] = source_id
            result["attempt"] = attempt
            results.append(result)
            break
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            if attempt < 3:
                sleep(2 * attempt)
    else:
        results.append({"id": source_id, "requested_url": url, "status": "unavailable", "attempts": 3, "error": error,
                        "web_api_inspection": "The web retrieval inspection remains cited separately; no raw bytes retained."})

record = {
    "version": 1,
    "purpose": "Hash-only retrieval record for copyright-restricted or terms-unclear authoritative pages; raw pages were not retained.",
    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "retrieved_at_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds"),
    "retrieval_method": "Python 3.12 urllib; GET; identity content encoding; 30-second timeout; at most three attempts with waits between failures; SHA-256 of returned HTTP body bytes.",
    "sources": results,
}
(ROOT / "external-source-fingerprints.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"sources": len(results), "available": sum(x.get("http_status") == 200 for x in results),
                  "unavailable": [x["id"] for x in results if x.get("status") == "unavailable"],
                  "output": "external-source-fingerprints.json"}, indent=2))
