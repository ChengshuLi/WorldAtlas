#!/usr/bin/env python3
"""Retrieve the exact five-state GNIS Populated Place screen for issue #486."""
import hashlib,json,time,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from gzip import GzipFile
HERE=Path(__file__).resolve().parent;OUT=HERE/'sources'
ENDPOINT='https://cartowfs.nationalmap.gov/arcgis/rest/services/geonames/MapServer/0/query'
params={'where':"state_alpha IN ('AK','CO','NM','OR','WY') AND gaz_featureclass = 'Populated Place'",'outFields':'OBJECTID,gaz_name,gaz_featureclass,state_alpha,county_name,objectid_1,isunknowncoords,gaz_id,fcode,incounty_id','returnGeometry':'true','outSR':'4326','f':'geojson','orderByFields':'OBJECTID ASC'}
features=[];pages=[];offset=0;page_size=2000
while True:
 q={**params,'resultOffset':str(offset),'resultRecordCount':str(page_size)};url=ENDPOINT+'?'+urllib.parse.urlencode(q)
 req=urllib.request.Request(url,headers={'User-Agent':'WorldAtlas-GeographyEvidence/1.0'})
 with urllib.request.urlopen(req,timeout=90) as response:raw=response.read()
 page=json.loads(raw)
 if 'error' in page:raise RuntimeError(f"GNIS service error: {page['error']}")
 rows=page.get('features',[]);pages.append({'result_offset':offset,'requested_count':page_size,'returned_count':len(rows),'response_bytes':len(raw),'response_sha256':hashlib.sha256(raw).hexdigest(),'request_url':url,'exceeded_transfer_limit':page.get('exceededTransferLimit',False)})
 features.extend(rows)
 if len(rows)<page_size and not page.get('exceededTransferLimit',False):break
 offset+=len(rows)
 if offset>50000:raise RuntimeError('Unexpectedly large GNIS result; stop and bound the query')
 if not rows:break
payload={'type':'FeatureCollection','features':features}
raw=(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n').encode();path=OUT/'usgs-gnis-populated-places-AK-CO-NM-OR-WY.geojson.gz'
with path.open('wb') as f:
 with GzipFile(fileobj=f,mode='wb',compresslevel=6,mtime=0) as z:z.write(raw)
receipt={'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'endpoint':ENDPOINT,'query_parameters':params,'page_size':page_size,'pages':pages,'feature_count':len(features),'retained_feature_count':len(features),'retained_path':str(path.relative_to(HERE)),'retained_compressed_bytes':path.stat().st_size,'retained_compressed_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'retained_uncompressed_bytes':len(raw),'retained_uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'source_description':'USGS The National Map Gazetteer based on GNIS; source service documents official/federally standardized named features but explicitly uses a flat model with no administrative, jurisdictional or other feature relationships. This query is only gaz_featureclass=Populated Place in the five assigned states. Features are not a complete settlement census.'}
(HERE/'usgs-gnis-query-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'features':len(features),'compressed_bytes':path.stat().st_size,'compressed_sha256':receipt['retained_compressed_sha256'],'uncompressed_sha256':receipt['retained_uncompressed_sha256'],'pages':len(pages)},indent=2))
