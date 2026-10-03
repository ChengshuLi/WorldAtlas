#!/usr/bin/env python3
"""Acquire 2021 Statistics Canada population centre metadata and BC polygons."""
import gzip,hashlib,json,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'sources';item_id='94507e9ee40746f6a52a65387dbd4f73'
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'WorldAtlas geography source review'}),timeout=90) as r:return r.read()
item=json.loads(get(f'https://www.arcgis.com/sharing/rest/content/items/{item_id}?f=json')); url=item['url'].rstrip('/')+'/0'
layer=json.loads(get(url+'?f=pjson'))
for fn,obj in [('statistics-canada-population-centres-item-metadata.json',item),('statistics-canada-population-centres-layer-metadata.json',layer)]:
 (SRC/fn).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
params={'where':"PRUID = '59'",'outFields':'*','returnGeometry':'true','outSR':'4326','f':'geojson'}
raw=json.loads(get(url+'/query?'+urllib.parse.urlencode(params)));assert 'features'in raw,raw
blob=(json.dumps(raw,separators=(',',':'),ensure_ascii=False)+'\n').encode();p=SRC/'statistics-canada-bc-population-centres-2021.geojson.gz'
with p.open('wb') as fp:
 with gzip.GzipFile(filename='',fileobj=fp,mode='wb',compresslevel=9,mtime=0) as z:z.write(blob)
print(json.dumps({'item_id':item_id,'title':item['title'],'layer':layer['name'],'count':len(raw['features']),'raw_bytes':len(blob),'raw_sha256':hashlib.sha256(blob).hexdigest(),'gzip_bytes':p.stat().st_size,'gzip_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'layer_editing':layer.get('editingInfo'),'description':item.get('description'),'license':item.get('licenseInfo')},indent=2))
