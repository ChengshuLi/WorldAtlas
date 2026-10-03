#!/usr/bin/env python3
"""Acquire authoritative CGNDB populated-place records for British Columbia."""
import gzip,hashlib,json,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'sources';item='79781d18a7fe469989bee7e4060aad94'
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'WorldAtlas geography source review'}),timeout=90) as r:return r.read()
itemdata=json.loads(get(f'https://www.arcgis.com/sharing/rest/content/items/{item}?f=json'));base=itemdata['url'].rstrip('/');layer=json.loads(get(base+'/0?f=pjson'))
for fn,d in [('canadian-geographical-names-item-metadata.json',itemdata),('canadian-geographical-names-layer-metadata.json',layer)]: (SRC/fn).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
where="PROV_TERR = 'British Columbia' AND CATEGORY = 'Populated Place'"
offset=0;items=[];pages=[]
while True:
 p={'where':where,'outFields':'*','returnGeometry':'true','outSR':'4326','f':'geojson','resultOffset':offset,'resultRecordCount':2000,'orderByFields':'CGNDB_ID'}
 url=base+'/0/query?'+urllib.parse.urlencode(p);d=json.loads(get(url));fs=d.get('features',[])
 if 'features' not in d:raise RuntimeError(d)
 pages.append({'offset':offset,'count':len(fs),'url':url});items.extend(fs);offset+=len(fs)
 if len(fs)<2000:break
raw=(json.dumps({'type':'FeatureCollection','features':items},ensure_ascii=False,separators=(',',':'))+'\n').encode();path=SRC/'canadian-geographical-names-populated-places-BC.geojson.gz'
with path.open('wb') as f:
 with gzip.GzipFile(filename='',fileobj=f,mode='wb',compresslevel=9,mtime=0) as z:z.write(raw)
(SRC/'canadian-geographical-names-query-receipt.json').write_text(json.dumps({'service_url':base,'layer_id':0,'retrieval_date_utc':'2026-10-03','where':where,'feature_count':len(items),'page_count':len(pages),'pages':pages,'interpretation':'GNBC/NRCan authoritative federal named features classified as Populated Place; this is a names database, not a settlement census. No-hit does not establish absence.','license':'Open Government Licence - Canada per item/service metadata'},indent=2)+'\n')
print(json.dumps({'count':len(items),'raw_bytes':len(raw),'raw_sha256':hashlib.sha256(raw).hexdigest(),'gzip_bytes':path.stat().st_size,'gzip_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'item':itemdata['title'],'data_last_edit_ms':layer.get('editingInfo',{}).get('dataLastEditDate'),'categories':sorted({f['properties'].get('CONCISE') for f in items})},indent=2))
