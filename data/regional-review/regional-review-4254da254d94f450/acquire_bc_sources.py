#!/usr/bin/env python3
"""Acquire pinned official ArcGIS metadata and the exact BC ecoregion/CD cohorts."""
import gzip,hashlib,json,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent; SRC=ROOT/'sources'; SRC.mkdir(exist_ok=True)

def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'WorldAtlas geography evidence research'})
 with urllib.request.urlopen(req,timeout=120) as r:return r.read()
def save(name,b): (SRC/name).write_bytes(b);return {'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def fetch_json(name,url):
 b=get(url); data=json.loads(b); save(name,json.dumps(data,ensure_ascii=False,indent=2).encode()+b'\n'); return data

aafc_id='ee462b0692cc4005aefee69dc44f010d'; cd_id='24f45c7b49d84aaf8e55e566a7fd670b'; csd_id='594124f0380d42b7a4b450574dd9630c'
aafc_item=fetch_json('aafc-ecoregions-item-metadata.json',f'https://www.arcgis.com/sharing/rest/content/items/{aafc_id}?f=json')
cd_item=fetch_json('statistics-canada-census-divisions-item-metadata.json',f'https://www.arcgis.com/sharing/rest/content/items/{cd_id}?f=json')
csd_item=fetch_json('statistics-canada-census-subdivisions-item-metadata.json',f'https://www.arcgis.com/sharing/rest/content/items/{csd_id}?f=json')
aafc_layer_url=aafc_item['url'].rstrip('/')+'/0'; cd_layer_url='https://services.arcgis.com/wjcPoefzjpzCgffS/arcgis/rest/services/Census_Division/FeatureServer/0'; csd_layer_url=csd_item['url'].rstrip('/')+'/0'
aafc_layer=fetch_json('aafc-ecoregions-layer-metadata.json',aafc_layer_url+'?f=pjson')
cd_layer=fetch_json('statistics-canada-census-divisions-layer-metadata.json',cd_layer_url+'?f=pjson')
csd_layer=fetch_json('statistics-canada-census-subdivisions-layer-metadata.json',csd_layer_url+'?f=pjson')
# IDs are the exact currently assigned EcoRegion source IDs, not all Canadian regions.
features=json.load(gzip.open(SRC/'current-scope-and-parents.geojson.gz','rt'))['features']
ecos=sorted({int(f['properties']['metadata']['source_id'].rsplit(':',1)[1]) for f in features if f['properties']['metadata'].get('source_id','').startswith('aafc:ecoregion:')})
def query(base,where):
 params={'where':where,'outFields':'*','returnGeometry':'true','outSR':'4326','f':'geojson','returnExceededLimitFeatures':'true'}
 data=json.loads(get(base+'/query?'+urllib.parse.urlencode(params)))
 if 'features' not in data:raise RuntimeError(data)
 return data['features']
aafc_features=query(aafc_layer_url,f'ECOREGION_ID IN ({",".join(map(str,ecos))})')
cd_features=query(cd_layer_url,"PRUID = '59'")
csd_features=query(csd_layer_url,"PRUID = '59'")
if {int(f['properties']['ECOREGION_ID']) for f in aafc_features}!=set(ecos):raise RuntimeError('AAFC exact ID roster mismatch')
if len(cd_features)<1:raise RuntimeError('No British Columbia census divisions')
for name,features in [('aafc-bc-scope-ecoregions.geojson.gz',aafc_features),('statistics-canada-bc-census-divisions-2021.geojson.gz',cd_features),('statistics-canada-bc-census-subdivisions-2021.geojson.gz',csd_features)]:
 raw=(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,separators=(',',':'))+'\n').encode()
 path=SRC/name
 with path.open('wb') as rawout:
  with gzip.GzipFile(filename='',fileobj=rawout,mode='wb',compresslevel=9,mtime=0) as f:f.write(raw)
 print(json.dumps({'path':name,'features':len(features),'raw_bytes':len(raw),'raw_sha256':hashlib.sha256(raw).hexdigest(),'gzip_bytes':path.stat().st_size,'gzip_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
print(json.dumps({'aafc_feature_count':len(aafc_features),'aafc_ids':ecos,'cd_2021_bc_feature_count':len(cd_features),'aafc_last_edit':aafc_layer.get('editingInfo'),'cd_last_edit':cd_layer.get('editingInfo'),'csd_feature_count':len(csd_features),'csd_last_edit':csd_layer.get('editingInfo')},indent=2))
