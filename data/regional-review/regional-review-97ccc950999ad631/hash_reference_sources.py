#!/usr/bin/env python3
"""Record reproducible hashes for lawful/public comparator source endpoints."""
from __future__ import annotations
import hashlib, json, pathlib, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
TARGETS = [
    ("LISGIS open data license and 2022 administrative boundary catalog", "https://lisgis.gov.lr/open-data-license", "Official public HTML catalog; it identifies 2022 district boundaries as CC BY 4.0. Catalog page only; no boundary geometry downloaded.", "https://lisgis.gov.lr/open-data-license"),
    ("LISGIS data catalog API", "https://lisgis.gov.lr/api/datasets", "Official dataset metadata endpoint; if 2022 district data are later acquired, check dataset-specific license and geography vintage.", "https://lisgis.gov.lr/data/api"),
    ("Mali Government 2023 administrative reorganization evidence", "https://gouvernement.ml/5eme-cohorte-de-a-lecole-de-la-citoyennete-le-general-de-brigade-issa-ousmane-coulibaly-fait-le-point-sur-les-reformes-territoriales-et-de-la-decentralisation-dans-notre-pays/", "Government reporting gives the current 19 regions and 159 circles; the official law and regional plan are separately cited. This page is not a boundary dataset.", "https://gouvernement.ml/5eme-cohorte-de-a-lecole-de-la-citoyennete-le-general-de-brigade-issa-ousmane-coulibaly-fait-le-point-sur-les-reformes-territoriales-et-de-la-decentralisation-dans-notre-pays/"),
    ("DNAT Tombouctou regional plan", "https://dnat.gouv.ml/wp-content/uploads/2025/03/Plan-Strat%C3%A9gique-de-D%C3%A9veloppement-R%C3%A9gional-de-Tombouctou-vfinale_090532.pdf", "Official regional planning source citing Law 2023-006 and identifying newer circle/arrondissement codes; not a nationwide boundary layer.", "https://dnat.gouv.ml/wp-content/uploads/2025/03/Plan-Strat%C3%A9gique-de-D%C3%A9veloppement-R%C3%A9gional-de-Tombouctou-vfinale_090532.pdf"),
    ("Mali 2023 National Pathway", "https://www.unfoodsystemshub.org/docs/unfoodsystemslibraries/national-pathways/mali/23-07-25-fr-mali-national-pathway.pdf?sfvrsn=4e112e30_5", "Government-submitted country pathway reports one district, 19 regions and 159 circles; secondary corroboration, not boundary geometry.", "https://www.unfoodsystemshub.org/docs/unfoodsystemslibraries/national-pathways/mali/23-07-25-fr-mali-national-pathway.pdf?sfvrsn=4e112e30_5"),
    ("UN SALB Mauritania data catalog", "https://salb.un.org/en/data/mrt", "UN catalog attributes validated polygons to national authority DCIG and reports temporal validity 2021-09-15 through update 2023-07-27; the page is metadata, not the source dataset.", "https://salb.un.org/en/data/mrt"),
    ("UK PCGN Mauritania Toponymic Fact File", "https://assets.publishing.service.gov.uk/media/6504627b6771b90014fdab69/Mauritania_Toponymic_Factfile-Sept23.pdf", "2023 official UK government reference states 15 wilayas, 54 moughataa/departments and communes below; this is a role/count crosscheck, not boundary geometry.", "https://assets.publishing.service.gov.uk/media/6504627b6771b90014fdab69/Mauritania_Toponymic_Factfile-Sept23.pdf"),
    ("Mauritania Directorate General of Territorial Communities map", "https://mdp.dgct.mr/map", "Official territorial-community map interface exposes wilaya/moughataa and local-government hierarchy; dynamic app and not retained as a geometry extract.", "https://mdp.dgct.mr/map")
]
rows = []
for title, url, use, restore in TARGETS:
    req = urllib.request.Request(url, headers={"User-Agent": "WorldAtlas geography evidence research"})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            body = response.read()
            rows.append({"title": title, "url": url, "retrieved_utc": "2026-10-04", "http_status": response.status,
                "resolved_url": response.geturl(), "content_type": response.headers.get("Content-Type"),
                "response_bytes": len(body), "response_sha256": hashlib.sha256(body).hexdigest(),
                "retained_bytes": False, "retention_reason": "No direct redistribution license was verified for the page/document; retain exact URL, response hash and restoration steps instead.",
                "use_and_limit": use, "restoration_instruction": "Fetch the exact URL again; compare complete response byte count and SHA-256, and record any source vintage/terms changes. " + restore})
    except Exception as error:
        rows.append({"title": title, "url": url, "retrieved_utc": "2026-10-04", "error": str(error),
            "retained_bytes": False, "use_and_limit": use, "restoration_instruction": "Retry this canonical URL and retain the actual access result and hash before relying on it: " + restore})
target = ROOT / "reference-source-checksums.json"
data = (json.dumps({"version": 1, "sources": rows}, indent=2, ensure_ascii=False) + "\n").encode()
if target.exists():
    if target.read_bytes() != data:
        raise FileExistsError(f"Refusing to replace retained comparator evidence: {target}; save this retrieval as a new dated vintage.")
else:
    target.write_bytes(data)
print(json.dumps(rows, indent=2, ensure_ascii=False))
