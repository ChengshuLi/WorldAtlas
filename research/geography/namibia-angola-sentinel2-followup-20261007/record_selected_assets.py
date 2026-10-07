#!/usr/bin/env python3
"""Pin public COG object metadata and retain source granule/tile metadata XML."""
from __future__ import annotations
import concurrent.futures,datetime,hashlib,json,pathlib,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
items=json.loads((ROOT/'inputs'/'selected-sentinel2-items.json').read_text())['selected_items']
bands=['green','nir','swir16','scl']
metadata=['granule_metadata','tileinfo_metadata']
heads=[]
def head_one(item,asset_name):
 asset=item['assets'][asset_name];url=asset['href'];req=urllib.request.Request(url,method='HEAD')
 with urllib.request.urlopen(req,timeout=60) as r:
  h=dict(r.headers.items());status=r.status
 keep={k:v for k,v in h.items() if k.lower() in ('content-length','content-type','etag','last-modified','accept-ranges','x-amz-version-id','x-amz-checksum-sha256')}
 return {'item_id':item['id'],'asset':asset_name,'href':url,'http_status':status,'headers':keep,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def get_one(item,asset_name):
 asset=item['assets'][asset_name];url=asset['href'];req=urllib.request.Request(url,headers={'Accept':'application/xml'})
 with urllib.request.urlopen(req,timeout=120) as r:
  raw=r.read();h=dict(r.headers.items());status=r.status
 name=f"{item['id']}_{asset_name}.xml";path=ROOT/'sources'/'metadata'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 keep={k:v for k,v in h.items() if k.lower() in ('content-length','content-type','etag','last-modified','accept-ranges','x-amz-version-id','x-amz-checksum-sha256')}
 return {'item_id':item['id'],'asset':asset_name,'href':url,'http_status':status,'headers':keep,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'path':str(path.relative_to(ROOT)),'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for rec in pool.map(lambda pair:head_one(*pair),[(i,b) for i in items for b in bands]):heads.append(rec)
metas=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for rec in pool.map(lambda pair:get_one(*pair),[(i,m) for i in items for m in metadata if m in i['assets']]):metas.append(rec)
(ROOT/'inputs'/'cog-object-head-receipts.json').write_text(json.dumps(heads,indent=2)+'\n')
(ROOT/'inputs'/'source-metadata-receipts.json').write_text(json.dumps(metas,indent=2)+'\n')
print(json.dumps({'cog_asset_heads':len(heads),'metadata_objects':len(metas),'metadata_bytes':sum(x['bytes'] for x in metas),'missing_head_headers':sum(not x['headers'].get('ETag') for x in heads),'failed':False},indent=2))
