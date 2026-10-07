#!/usr/bin/env python3
"""One-time bounded capture of the three target Census TIGERweb county records."""
import datetime,hashlib,json,pathlib,urllib.parse,urllib.request
OUT=pathlib.Path(__file__).resolve().parent/'sources'
ENDPOINT='https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query'
PARAMS={'where':"STATE = '36' AND COUNTY IN ('059','103','119')",'outFields':'*','returnGeometry':'true','outSR':'4326','f':'geojson','orderByFields':'COUNTY'}
URL=ENDPOINT+'?'+urllib.parse.urlencode(PARAMS)
HEADERS={'User-Agent':'WorldAtlas bounded source-fitness research/1.0'}
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,b):
 p=OUT/name;p.write_bytes(b);return p
with urllib.request.urlopen(urllib.request.Request(URL,headers=HEADERS),timeout=45) as r:
 raw=r.read();headers=dict(r.headers.items());status=r.status;final_url=r.geturl()
assert status==200 and len(raw)<32*1024*1024
x=json.loads(raw);assert sorted(f['properties']['GEOID'] for f in x['features'])==['36059','36103','36119']
write('census-tigerweb-2026-target-counties.geojson',raw)
meta_url='https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1?f=pjson'
with urllib.request.urlopen(urllib.request.Request(meta_url,headers=HEADERS),timeout=30) as r:
 meta=r.read();meta_headers=dict(r.headers.items());meta_status=r.status;meta_final=r.geturl()
assert meta_status==200 and json.loads(meta).get('description','').endswith('January 1, 2026 vintage')
write('census-tigerweb-2026-layer-metadata.json',meta)
receipt={'service_endpoint':ENDPOINT,'parameters':PARAMS,'request_url':URL,'final_url':final_url,'http_status':status,'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'headers':headers,'response_path':'sources/census-tigerweb-2026-target-counties.geojson','response_bytes':len(raw),'response_sha256':sha(raw),'feature_count':len(x['features']),'features_by_geoid':sorted(f['properties']['GEOID'] for f in x['features']),'layer_metadata_url':meta_url,'layer_metadata_final_url':meta_final,'layer_metadata_http_status':meta_status,'layer_metadata_headers':meta_headers,'layer_metadata_path':'sources/census-tigerweb-2026-layer-metadata.json','layer_metadata_bytes':len(meta),'layer_metadata_sha256':sha(meta)}
write('census-tigerweb-2026-retrieval.json',(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps({'retrieved_at_utc':receipt['retrieved_at_utc'],'response_bytes':len(raw),'response_sha256':sha(raw),'features':receipt['features_by_geoid'],'layer_metadata_sha256':sha(meta)},indent=2))
