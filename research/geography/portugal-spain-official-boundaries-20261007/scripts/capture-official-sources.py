#!/usr/bin/env python3
"""Capture complete official CAOP/IGN metadata, legal notices and native items."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ("dgt-caop-page", "https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop?language=pt", "application/pdf, text/html"),
    ("dgt-caop2025-change-list", "https://www.dgterritorio.gov.pt/sites/default/files/ficheiros-cartografia/alteracoes_CAOP2025.pdf", "application/pdf"),
    ("dgt-caop2025-approval-notice", "https://www.dgterritorio.gov.pt/sites/default/files/ficheiros-artigos/DR_AvisoCAOP2025.pdf", "application/pdf"),
    ("dgt-open-data-terms", "https://www.dgterritorio.gov.pt/dados-abertos", "text/html"),
    ("dgt-caop2025-collection", "https://ogcapi.dgterritorio.gov.pt/collections/municipios?f=json", "application/json"),
    ("dgt-caop2025-queryables", "https://ogcapi.dgterritorio.gov.pt/collections/municipios/queryables?f=json", "application/schema+json, application/json"),
    ("dgt-barrancos-0204", "https://ogcapi.dgterritorio.gov.pt/collections/municipios/items/0204?f=json", "application/geo+json, application/json"),
    ("dgt-moura-0210", "https://ogcapi.dgterritorio.gov.pt/collections/municipios/items/0210?f=json", "application/geo+json, application/json"),
    ("ign-administrativeunit-collection", "https://api-features.ign.es/collections/administrativeunit?f=json", "application/json"),
    ("ign-administrativeunit-queryables", "https://api-features.ign.es/collections/administrativeunit/queryables?f=json", "application/schema+json, application/json"),
    ("ign-administrativeboundary-collection", "https://api-features.ign.es/collections/administrativeboundary?f=json", "application/json"),
    ("ign-administrativeboundary-queryables", "https://api-features.ign.es/collections/administrativeboundary/queryables?f=json", "application/schema+json, application/json"),
    ("ign-openapi", "https://api-features.ign.es/openapi?f=json", "application/vnd.oai.openapi+json;version=3.0, application/json"),
    ("ign-encinasola-1166667", "https://api-features.ign.es/collections/administrativeunit/items/1166667?f=json", "application/geo+json, application/json"),
    ("ign-rosal-1166698", "https://api-features.ign.es/collections/administrativeunit/items/1166698?f=json", "application/geo+json, application/json"),
    ("ign-encinasola-portugal-5679963", "https://api-features.ign.es/collections/administrativeboundary/items/5679963?f=json", "application/geo+json, application/json"),
    ("ign-rosal-portugal-5671403", "https://api-features.ign.es/collections/administrativeboundary/items/5671403?f=json", "application/geo+json, application/json"),
    ("ign-encinasola-record-page", "https://centrodedescargas.cnig.es/CentroDescargas/busquedaIdProductor.do?idProductor=M011569M014001&Serie=HRLLJ", "text/html"),
    ("ign-rosal-record-page", "https://centrodedescargas.cnig.es/CentroDescargas/busquedaIdProductor.do?idProductor=M011779M014001&Serie=HRLLJ", "text/html"),
    ("ign-license-terms", "https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf", "application/pdf"),
    ("ign-data-policy", "https://www.ign.es/web/ign/portal/politica-datos", "text/html"),
    ("ign-legal-notice", "https://www.ign.es/web/ign/portal/info-aviso-legal", "text/html"),
    ("ign-fom-2807-2015", "https://www.boe.es/buscar/doc.php?id=BOE-A-2015-14129", "text/html"),
]

FAILED_ATTEMPTS = [{
    "id": "dgt-caop2025-change-list-incorrect-route-404",
    "request_url": "https://www.dgterritorio.gov.pt/sites/default/files/ficheiros-artigos/alteracoes_CAOP2025.pdf",
    "http_status": 404,
    "body_path": "sources/failed-requests/dgt-caop2025-change-list-incorrect-route-404.body",
    "headers_path": "sources/failed-requests/dgt-caop2025-change-list-incorrect-route-404.headers.txt",
    "body_bytes": 59563,
    "body_sha256": "f409d82df5e0e96135a89c229740254ace0514f63b26f94957e1d84aee6025d8",
    "reason": "Initial link path was guessed incorrectly; the official CAOP page linked the corrected URL, which is separately captured.",
}]

def main() -> int:
    raw_dir = ROOT / "sources" / "official"
    header_dir = ROOT / "sources" / "http-headers"
    raw_dir.mkdir(parents=True, exist_ok=True)
    header_dir.mkdir(parents=True, exist_ok=True)
    index_path = ROOT / "sources" / "official-capture-index.json"
    old_index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"captures": []}
    existing = {row["id"]: row for row in old_index.get("captures", [])}
    captured = []
    failed = False
    for source_id, url, accept in SOURCES:
        body_path = raw_dir / f"{source_id}.body"
        header_path = header_dir / f"{source_id}.headers.txt"
        if source_id in existing:
            prior = existing[source_id]
            body = body_path.read_bytes() if body_path.exists() else b""
            if (not body or len(body) != prior.get("body_bytes") or
                    sha256(body).hexdigest() != prior.get("body_sha256") or not header_path.exists()):
                raise RuntimeError(f"Existing capture changed or incomplete: {source_id}")
            captured.append(prior)
            continue
        command = [
            "curl", "--silent", "--show-error", "--location", "--retry", "2",
            "--connect-timeout", "30", "--max-time", "180",
            "--user-agent", "WorldAtlas-issue-1299-source-capture/1.0",
            "--header", f"Accept: {accept}",
            "--dump-header", str(header_path), "--output", str(body_path),
            "--write-out", "%{http_code}\n%{url_effective}\n%{content_type}\n%{size_download}\n",
            url,
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        fields = result.stdout.splitlines()
        status = int(fields[0]) if fields and fields[0].isdigit() else 0
        final_url = fields[1] if len(fields) > 1 else ""
        content_type = fields[2] if len(fields) > 2 else ""
        body = body_path.read_bytes() if body_path.exists() else b""
        record = {
            "id": source_id,
            "request_url": url,
            "final_url": final_url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "retrieved_at_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            "http_status": status,
            "content_type": content_type,
            "body_path": body_path.relative_to(ROOT).as_posix(),
            "body_bytes": len(body),
            "body_sha256": sha256(body).hexdigest(),
            "headers_path": header_path.relative_to(ROOT).as_posix(),
            "curl_exit": result.returncode,
            "stderr": result.stderr.strip(),
        }
        captured.append(record)
        if status != 200 or result.returncode != 0 or not body:
            failed = True
            print(json.dumps({"capture": source_id, "status": status, "curl_exit": result.returncode, "stderr": record["stderr"]}), file=sys.stderr)
    index = {
        "version": 1,
        "scope": "Whole official DGT CAOP2025 and IGN native item, collection, legal and provenance responses for the four retained Portugal-Spain contact subjects.",
        "capture_method": "curl exact response body with raw response headers; no content decoding, clipping, geometry transformation or JSON reserialization.",
        "captures": captured,
        "failed_attempts": FAILED_ATTEMPTS,
        "limits": [
            "Direct OGC API item responses are whole native feature items, not complete national datasets.",
            "Provider status and administrative cartography do not independently prove bilateral authority, historic ownership, or physical land/water.",
        ],
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"captures": len(captured), "failed": failed, "items": [{"id": x["id"], "status": x["http_status"], "bytes": x["body_bytes"], "sha256": x["body_sha256"]} for x in captured]}, indent=2))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
