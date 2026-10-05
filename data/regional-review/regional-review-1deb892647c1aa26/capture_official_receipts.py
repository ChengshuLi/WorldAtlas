#!/usr/bin/env python3
"""Capture hashes and retrieval metadata, not unlicensed page/PDF bodies."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, urllib.request
ROOT=Path(__file__).resolve().parent
SOURCES=[
 {"id":"ghana-gss-2021-phc-manual","url":"https://census2020.statsghana.gov.gh/gssmain/fileUpload/pressrelease/2021%20PHC_Field%20Officers%20Manual_05.05.2021.pdf","claim":"Official 2021 Population and Housing Census field manual distinguishes the 16 administrative regions and 260 MMDAs from 271 census statistical districts; districts are nested within regions.","source_vintage":"2021 PHC manual; describes 2019 post-region-change administrative state"},
 {"id":"guinea-government-presentation","url":"https://gouvernement.gov.gn/presentation/","claim":"Government of Guinea describes seven administrative regions plus the special Conakry zone, 33 prefectures, 344 sub-prefectures, and municipal/village tiers.","source_vintage":"Page content's own vintage is unstated; text references 2021-2025 national health digital strategy"},
 {"id":"guinea-bissau-unfccc-nc4","url":"https://unfccc.int/sites/default/files/resource/GNB_NC4_English_FINAL_16112025_JLT.pdf","claim":"Guinea-Bissau's 2025 national communication says the country has eight regions and one autonomous sector; its text reports 36 sectors under the regions.","source_vintage":"National Communication 4, 2025 (file name dates final 2025-11-16)"},
 {"id":"guinea-bissau-uk-toponymic-factfile","url":"https://assets.publishing.service.gov.uk/media/65f31c5efa1851001a011765/Guinea-Bissau_toponymic_factfile.pdf","claim":"The UK Permanent Committee on Geographical Names 2024 factfile reports eight regions and one autonomous sector, with 39 sectors at ADM2, citing the national Direcção Geral de Geografia e Cadastro via UN SALB.","source_vintage":"Factfile copyright year 2024; exact publication day not established"},
 {"id":"liberia-lisgis-open-data-license","url":"https://lisgis.gov.lr/open-data-license","claim":"LISGIS states that its statistical data are published under CC BY 4.0; the covered dataset catalog separately assigns CC BY 4.0 to 2022 district/county boundaries.","source_vintage":"Current page accessed 2026-10-05; exact page revision date unknown"},
 {"id":"liberia-lisgis-2022-districts","url":"https://lisgis.gov.lr/api/visualizations/datasets/geo-districts/2022","claim":"Primary LISGIS 2022 census administrative GIS district layer; response describes full-resolution boundary data and embeds original archive file hashes and processing CRS.","source_vintage":"LISGIS 2022 Population and Housing Census cartography; no observation period"},
 {"id":"liberia-lisgis-2022-counties","url":"https://lisgis.gov.lr/api/visualizations/datasets/geo-counties/2022","claim":"Primary LISGIS 2022 census county layer with 15 county polygons, parent context for the 160 district rows.","source_vintage":"LISGIS 2022 Population and Housing Census cartography; no observation period"}
]
rows=[]
for item in SOURCES:
 req=urllib.request.Request(item['url'],headers={'User-Agent':'WorldAtlas-geography-research/1','Accept':'application/pdf,application/json,text/html,*/*'})
 try:
  with urllib.request.urlopen(req,timeout=180) as r:
   data=r.read(); code=r.status; ctype=r.headers.get('Content-Type'); final=r.geturl()
  rows.append({**item,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'final_url':final,'http_status':code,'content_type':ctype,'response_bytes':len(data),'response_sha256':sha256(data).hexdigest()})
 except Exception as e:
  rows.append({**item,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'error':type(e).__name__+': '+str(e)})
(ROOT/'official-context.json').write_text(json.dumps({'version':1,'retrievals':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps([{k:r.get(k) for k in ['id','http_status','response_bytes','response_sha256','error']} for r in rows],indent=2))
