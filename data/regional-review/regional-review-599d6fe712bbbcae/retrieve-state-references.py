#!/usr/bin/env python3
"""Retain separate official TIGERweb 2026 state reference queries; no overwrite."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
import json

root = Path.cwd()
pkt = root / 'data/regional-review/regional-review-599d6fe712bbbcae'
out = pkt / 'sources/census-tigerweb-acs26'
out.mkdir(parents=True, exist_ok=True)
metadata_url = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2026/MapServer/80?f=pjson'
records = []
for source_id, url, name in [('tigerweb-acs26-states-layer-80-metadata', metadata_url, 'states-layer-80-metadata.json')]:
    target = out / name
    assert not target.exists(), f'Refusing to overwrite {target}'
    req = Request(url, headers={'User-Agent':'WorldAtlas source research'})
    with urlopen(req, timeout=60) as r:
        data = r.read()
        target.write_bytes(data)
        records.append({'source_id':source_id,'requested_url':url,'final_url':r.geturl(),'retrieved_utc':datetime.now(timezone.utc).isoformat(),'http_status':r.status,'content_type':r.headers.get('Content-Type'),'bytes':len(data),'sha256':sha256(data).hexdigest(),'retained':True,'retained_path':'census-tigerweb-acs26/'+name,'reuse_terms':'U.S. Census Bureau public service metadata; public domain.'})
for state in ('01','28','47'):
    url = ('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2026/MapServer/80/query?where=STATE%20%3D%20%27'
           + state + '%27&outFields=GEOID%2CSTATE%2CSTATENS%2CBASENAME%2CNAME%2CLSADC%2CFUNCSTAT%2CAREALAND%2CAREAWATER&returnGeometry=true&outSR=4326&f=geojson')
    name = 'states-state-' + state + '.geojson'
    target = out / name
    assert not target.exists(), f'Refusing to overwrite {target}'
    req = Request(url, headers={'User-Agent':'WorldAtlas source research'})
    with urlopen(req, timeout=60) as r:
        data = r.read()
        target.write_bytes(data)
        payload = json.loads(data)
        assert r.status == 200 and len(payload.get('features', [])) == 1
        records.append({'source_id':'tigerweb-acs26-state-'+state,'requested_url':url,'final_url':r.geturl(),'retrieved_utc':datetime.now(timezone.utc).isoformat(),'http_status':r.status,'content_type':r.headers.get('Content-Type'),'bytes':len(data),'sha256':sha256(data).hexdigest(),'retained':True,'feature_count':len(payload['features']),'retained_path':'census-tigerweb-acs26/'+name,'reuse_terms':'U.S. Census Bureau federal work and public service response; public domain. TIGERweb ACS26 States layer, 2026-01-01 vintage.'})
receipt = pkt / 'census-tigerweb-state-reference-retrieval-receipts.json'
assert not receipt.exists(), f'Refusing to overwrite {receipt}'
receipt.write_text(json.dumps({'version':1,'records':records},indent=2)+'\n')
print(json.dumps({'captured':len(records),'records':records},indent=2))
