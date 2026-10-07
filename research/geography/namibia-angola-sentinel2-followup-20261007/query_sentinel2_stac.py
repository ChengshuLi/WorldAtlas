#!/usr/bin/env python3
"""Retrieve paginated Earth Search STAC snapshots for fixed wet/dry periods."""
from __future__ import annotations
import datetime, hashlib, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
API='https://earth-search.aws.element84.com/v1/search'
AOI=[18.42566188925082,-18.0421,20.943746679773703,-17.399540716612382]
WINDOWS={
 '2019-wet':['2019-01-01T00:00:00Z','2019-03-31T23:59:59Z'],
 '2019-dry':['2019-08-01T00:00:00Z','2019-10-31T23:59:59Z'],
 '2020-wet':['2020-01-01T00:00:00Z','2020-03-31T23:59:59Z'],
 '2020-dry':['2020-08-01T00:00:00Z','2020-10-31T23:59:59Z'],
}
def post(url,payload):
 req=urllib.request.Request(url,data=json.dumps(payload,separators=(',',':')).encode(),
   headers={'Content-Type':'application/json','Accept':'application/geo+json'},method='POST')
 with urllib.request.urlopen(req,timeout=120) as response:
  raw=response.read(); headers=dict(response.headers.items()); status=response.status
 return json.loads(raw),raw,headers,status
receipts=[]
for name,(start,end) in WINDOWS.items():
 payload={'collections':['sentinel-2-l2a'],'bbox':AOI,'datetime':f'{start}/{end}',
   'query':{'eo:cloud_cover':{'lt':20}},'limit':1000}
 page_payload=payload; page=1; item_count=0
 while True:
  obj,raw,headers,status=post(API,page_payload)
  filename=f'earth-search-stac-{name}-page-{page:02d}.json'
  path=ROOT/'inputs'/filename; path.write_bytes(raw)
  features=obj.get('features',[]); item_count+=len(features)
  receipts.append({'window':name,'page':page,'endpoint':API,'request':page_payload,
    'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'http_status':status,
    'response_headers':{k:v for k,v in headers.items() if k.lower() in ('date','content-type','content-length','etag','last-modified','x-amzn-requestid','x-amz-cf-id')},
    'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'item_count':len(features),'response_path':str(path.relative_to(ROOT))})
  next_link=next((link for link in obj.get('links',[]) if link.get('rel')=='next'),None)
  if not next_link: break
  page+=1
  if page>25: raise RuntimeError(f'pagination safety limit for {name}')
  page_payload=next_link.get('body') or page_payload
 print(name,'items=',item_count,'pages=',page)
(ROOT/'inputs'/'stac-query-receipts-2019-2020.json').write_text(json.dumps(receipts,indent=2)+'\n')
