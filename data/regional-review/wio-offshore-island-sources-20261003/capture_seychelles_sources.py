#!/usr/bin/env python3
"""Hash current official Seychelles source pages without retaining unlicensed bodies."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
import json

PACKET=Path(__file__).parent
OUT=PACKET/"seychelles-source-access-20261008.json"
SOURCES=[
 {"id":"Seychelles-MACCE-ecosystems","url":"https://environment.gov.sc/seychelles-clearing-house-mechanism/ecosystems/","role":"official high-level physical island inventory context; geology/groups","finding":"The ministry page describes 115 granitic and coral islands and groups/physical character. It cites Government of Seychelles biodiversity sources around 2011/2014; it is not a dated per-island polygon inventory or region crosswalk. The number is a broad descriptive aggregate and does not reconcile the assigned Other Islands geometry."},
 {"id":"Seychelles-MACCE-outer-island-management","url":"https://macce.gov.sc/management-and-biodiversity-conservation-of-outer-islands/","role":"official outer-island administrative/management context","finding":"The ministry page states outer-island management arrangements and that outer islands account for more than half the archipelago total; cited content does not provide an exhaustive per-island GIS inventory or a region membership crosswalk."},
 {"id":"Seychelles-National-Spatial-Data-Sharing-Policy","url":"https://lh.gov.sc/media/documents/NATIONAL_SPATIAL_DATA_SHARING_POLICY.PDF","role":"official geospatial data request/license policy","finding":"The policy includes a bilateral GIS Data License Agreement. Article 8.1 states delivered datasets are for internal use; products may be shown but not sold, traded, transmitted, or otherwise made available to third parties, except stated corporate affiliates, unless Article 8 stipulates otherwise. A project-specific written agreement is therefore not an open redistribution license. Request a dataset-specific agreement authorizing intended retention/reuse before obtaining or sharing licensed island/region geometry."},
 {"id":"Seychelles-NBS-GIS","url":"https://www.nbs.gov.sc/statistics/gis","role":"official census/GIS access route","finding":"The NBS GIS page describes census mapping supporting enumerators and supervisors to identify enumeration areas and locate households/structures. Public page does not provide a licensed complete settlement-point layer; census operational mapping should not be inferred as a public geocoded settlement gazetteer."},
 {"id":"Seychelles-NBS-Census-2022","url":"https://www.nbs.gov.sc/downloads/1555-seychelles-population-and-housing-census-2022","role":"current statistical publication and named locality context","finding":"The official census report is downloadable as a PDF and supplies census geography/statistics; it does not establish public redistribution of operational GIS coordinates or a complete settlement-point dataset. No such dataset/license is exposed from its page."},
 {"id":"Seychelles-NBS-Seychelles-in-Figures-2013","url":"https://www.statehouse.gov.sc/uploads/downloads/filepath_67.pdf","role":"older official archipelago descriptive context only","finding":"NBS 2013 says the country has over 116 islands, describes a Mahé group of 43 and an outlying coralline group of 73 or more, and provides a schematic map. Its count differs from the current ministry 115 description, is explicitly approximate/older, and is not a feature-level catalog or region crosswalk."},
]
retrieved=datetime.now(timezone.utc).isoformat(timespec="seconds")
out={"version":1,"issue":633,"retrieved_utc":retrieved,"retention":"Only URL, exact response-body SHA-256, byte length, retrieval timestamp, and research finding are retained; official web/PDF bodies are not redistributed here.","sources":[]}
for s in SOURCES:
 req=Request(s["url"],headers={"User-Agent":"WorldAtlas geography source research; issue #633"})
 try:
  with urlopen(req,timeout=45) as r:
   body=r.read()
   entry={**s,"http_status":r.status,"content_type":r.headers.get("Content-Type"),"response_sha256":sha256(body).hexdigest(),"response_bytes":len(body)}
 except Exception as e:
  entry={**s,"retrieval_error":type(e).__name__+": "+str(e)}
 out["sources"].append(entry)
with OUT.open("x",encoding="utf-8") as f: f.write(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({"output":str(OUT.name),"retrieved_utc":retrieved,"sources":[{"id":x["id"],"sha256":x.get("response_sha256"),"bytes":x.get("response_bytes"),"error":x.get("retrieval_error")} for x in out["sources"]]},indent=2))
