#!/usr/bin/env python3
"""Select the assigned USA source records and acquire 2024 Census/GNIS evidence."""
import gzip,hashlib,json,urllib.parse,urllib.request,zipfile,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'sources';SRC.mkdir(exist_ok=True)
UP=ROOT.parents[2]/'data/regional-review/regional-review-93f8f3bee8e205be/sources'

def get(u):
 req=urllib.request.Request(u,headers={'User-Agent':'WorldAtlas geography source research'})
 with urllib.request.urlopen(req,timeout=90) as r:return r.read()
def gzjson(name,obj):
 raw=(json.dumps(obj,separators=(',',':'),ensure_ascii=False)+'\n').encode();p=SRC/name
 with p.open('wb') as f:
  with gzip.GzipFile(filename='',fileobj=f,mode='wb',compresslevel=9,mtime=0) as z:z.write(raw)
 return {'path':name,'features':len(obj.get('features',[])),'raw_bytes':len(raw),'raw_sha256':hashlib.sha256(raw).hexdigest(),'compressed_bytes':p.stat().st_size,'compressed_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def readgz(p):return json.load(gzip.open(p,'rt'))
# #486 retained exact 2018/2024 original inputs, including the national archive digest.
old=json.load(open(UP/'geoboundaries-USA-ADM2.geojson'))
old1=json.load(open(UP/'geoboundaries-USA-ADM1.geojson'))
tiger=readgz(UP/'tigerline-2024-western-county-neighbors.geojson.gz')
ids=[i for i in json.load(open(ROOT/'scope.json'))['member_location_ids'] if i.startswith('gb:USA:ADM2:')]
shapes={i.rsplit(':',1)[1] for i in ids}; oldsel=[f for f in old['features'] if f['properties'].get('shapeID') in shapes]
if len(oldsel)!=161 or {f['properties']['shapeID'] for f in oldsel}!=shapes:raise RuntimeError(f'2018 ADM2 id mismatch {len(oldsel)}')
states=['04','16','30','32','49']; tiger_sel=[f for f in tiger['features'] if f['properties'].get('STATEFP') in states]
if len(tiger_sel)!=161:raise RuntimeError(f'2024 TIGER count {len(tiger_sel)} != 161')
# Five selected state features from the national 2018 ADM1 are preserved for cohort screening.
st1={f['properties'].get('shapeName','').casefold() for f in old1['features']}
want={'arizona','idaho','montana','nevada','utah'}; adm1=[f for f in old1['features'] if f['properties'].get('shapeName','').casefold() in want]
if len(adm1)!=5:raise RuntimeError('ADM1 state extract mismatch')
for fn,fc in [('geoboundaries-USA-ADM2-assigned-5-states.geojson.gz',{'type':'FeatureCollection','features':oldsel}),('geoboundaries-USA-ADM1-assigned-5-states.geojson.gz',{'type':'FeatureCollection','features':adm1}),('tigerline-2024-mountain-counties.geojson.gz',{'type':'FeatureCollection','features':tiger_sel})]:print(json.dumps(gzjson(fn,fc)))
# Census 2024 Places polygons for exactly the five assigned states.
place_counts={};places=[]
for st in states:
 url=f'https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_{st}_place.zip'; b=get(url); p=SRC/f'tl_2024_{st}_place.zip';p.write_bytes(b)
 place_counts[st]={'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 with zipfile.ZipFile(p) as z:
  shp=next(x for x in z.namelist() if x.endswith('.shp')); tmp=Path(tempfile.mkdtemp())
  for n in z.namelist():
   if n.lower().endswith(('.shp','.shx','.dbf','.prj','.cpg')):z.extract(n,tmp)
  from osgeo import ogr
  ds=ogr.Open(str(tmp/shp));ly=ds.GetLayer();ly.ResetReading()
  # Retain downloaded archives; GeoJSON conversion is done later via OGR.
  place_counts[st]['feature_count']=ly.GetFeatureCount();ds=None
shutil.rmtree(tmp,ignore_errors=True)
# Official GNIS populated-place named locations, current query, filtered to exact assigned states.
service='https://cartowfs.nationalmap.gov/arcgis/rest/services/geonames/MapServer';
metadata=json.loads(get(service+'?f=pjson')); layer=json.loads(get(service+'/0?f=pjson'))
(SRC/'usgs-gnis-service-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n');(SRC/'usgs-gnis-layer0-metadata.json').write_text(json.dumps(layer,ensure_ascii=False,indent=2)+'\n')
state_alpha=['AZ','ID','MT','NV','UT']; where="state_alpha IN ("+','.join("'"+x+"'" for x in state_alpha)+") AND gaz_featureclass = 'Populated Place'"
allf=[];offset=0; page=0; receipts=[]
while True:
 q={'where':where,'outFields':'*','returnGeometry':'true','outSR':'4326','f':'geojson','resultOffset':offset,'resultRecordCount':1000,'orderByFields':'gaz_id'}
 url=service+'/0/query?'+urllib.parse.urlencode(q); d=json.loads(get(url));fs=d.get('features',[])
 if 'features' not in d:raise RuntimeError(d)
 receipts.append({'offset':offset,'count':len(fs),'url':url});allf.extend(fs);offset+=len(fs);page+=1
 if len(fs)<1000:break
 if page>20:raise RuntimeError('GNIS pagination cap')
print(json.dumps(gzjson('usgs-gnis-populated-places-AZ-ID-MT-NV-UT.geojson.gz',{'type':'FeatureCollection','features':allf})))
(SRC/'usgs-gnis-query-receipt.json').write_text(json.dumps({'source':'USGS National Map Gazetteer GNIS REST','retrieved_utc':'2026-10-03','service_url':service,'layer_id':0,'filter':where,'states':state_alpha,'feature_class':'Populated Place','page_count':len(receipts),'feature_count':len(allf),'pages':receipts,'public_domain':True},indent=2)+'\n')
(SRC/'tigerline-shared-origin.json').write_text(json.dumps({'source_packet':'#486','local_source_directory':'data/regional-review/regional-review-93f8f3bee8e205be/sources/','national_county_archive_url':'https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip','national_archive_bytes':83913260,'national_archive_sha256':'04e668d3502757c837c13444730547cd967f28a2c49aeffb873d1792ab2cb97b','database_update':'2024-09-16'},indent=2)+'\n')
print(json.dumps({'2024_tiger_five_state_counties':len(tiger_sel),'2024_places':place_counts,'gnis_populated_places':len(allf)},indent=2))
