#!/usr/bin/env python3
"""Acquire pinned 2017/2019/2022 boundaries and current OCHA COD-AB evidence."""
from __future__ import annotations
import gzip, hashlib, json, pathlib, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
S=ROOT/'sources';S.mkdir(exist_ok=True)
UA='WorldAtlas-geography-evidence/1.0 (source metadata and geographic research)'

def get(url, timeout=180, method='GET'):
    req=urllib.request.Request(url,method=method,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return (r.read() if method=='GET' else b''),r.geturl(),dict(r.headers.items())

def save(name,data):
    p=S/name;p.write_bytes(gzip.compress(data,mtime=0));raw=p.read_bytes()
    return {'file':f'sources/{name}','gzip_sha256':hashlib.sha256(raw).hexdigest(),'gzip_bytes':len(raw),'restored_bytes':len(data),'restored_sha256':hashlib.sha256(data).hexdigest()}

def api(url): return json.loads(get(url)[0])
def compact(h): return {k:v for k,v in h.items() if k.lower() in ('content-type','content-length','last-modified','etag','accept-ranges')}

issue_roles={'NGA':('Local Government Areas','2022','Creative Commons Attribution 4.0 International (CC BY 4.0)'),
 'SEN':('department','2019','Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'),
 'SLE':('Districts','2017','Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)')}
results={'acquired_at_utc':'2026-10-04','sources':[]}
for code,(role,vintage,license_) in issue_roles.items():
 url=f'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/{code}/ADM2/geoBoundaries-{code}-ADM2.geojson'
 data,final,headers=get(url)
 saved=save(f'geoboundaries-{code}-adm2-{vintage}.geojson.gz',data)
 meta_url=f'https://www.geoboundaries.org/api/current/gbOpen/{code}/ADM2/'
 mraw,mfinal,_=get(meta_url);msave=save(f'geoboundaries-{code}-adm2-current-api-metadata.json.gz',mraw);meta=json.loads(mraw)
 results['sources'].append({'id':f'geoboundaries-{code}-adm2','provider':'geoBoundaries','country_code':code,
   'issue_declared_role':role,'issue_declared_vintage':vintage,'issue_declared_license':license_,
   'canonical_download_url':url,'resolved_download_url':final,'download_headers':compact(headers),
   'retrieved_bytes':saved['restored_bytes'],'retrieved_sha256':saved['restored_sha256'],'retained':saved,
   'catalog_metadata_url':meta_url,'catalog_metadata_resolved_url':mfinal,'catalog_snapshot_metadata':meta,'retained_catalog_metadata':msave,
   'catalog_temporal_limit':'The API is the current catalog endpoint, not an immutable metadata snapshot for tag 9469f09; issue-declared represented role/vintage/license are preserved separately.'})

for code,dataset_id,resource_stub in [('NGA','cod-ab-nga','nga_admin_boundaries.geojson.zip'),('SEN','cod-ab-sen','sen_admin_boundaries.geojson.zip'),('SLE','cod-ab-sle','sle_admin_boundaries.geojson.zip')]:
 url=f'https://data.humdata.org/api/3/action/package_show?id={dataset_id}';raw,resolved,_=get(url);pkg=json.loads(raw)['result'];meta_saved=save(f'hdx-{dataset_id}-package-metadata.json.gz',raw)
 resources=pkg.get('resources',[]);resource=next((x for x in resources if x.get('name')==resource_stub),None)
 if resource is None: raise RuntimeError(f'No {resource_stub} in {dataset_id}')
 data,download_url,headers=get(resource['url']);retained=save(f'hdx-{dataset_id}-admin-boundaries.geojson.zip.gz',data)
 results['sources'].append({'id':dataset_id,'provider':'OCHA HDX COD-AB','country_code':code,'dataset_title':pkg.get('title'),
   'catalog_license':pkg.get('license_title'),'metadata_modified':pkg.get('metadata_modified'),'notes':pkg.get('notes'),
   'canonical_catalog_url':url,'resolved_catalog_url':resolved,'retained_package_metadata':meta_saved,'resource':resource,
   # Keep the durable HDX resource route rather than a short-lived signed redirect URL.
   'resolved_download_url':resource['url'],'download_redirect_note':'The retrieved bytes followed a temporary signed HDX redirect; its credentials are omitted. Restore from the canonical catalog/resource route.',
   'download_headers':compact(headers),'retained_original_archive':retained})

# National OCHA settlement catalogs: retain reusable Senegal 2017 points; preserve only
# metadata and restoration links for Nigeria/Sierra Leone packages labeled Other.
for code,dataset_id,reusable in [('NGA','nigeria-settlements-villages-towns-cities',False),('SEN','senegal-settlements',True),('SLE','sierra-leone-settlements',False)]:
 url=f'https://data.humdata.org/api/3/action/package_show?id={dataset_id}';raw,resolved,_=get(url);pkg=json.loads(raw)['result']
 record={'id':dataset_id,'provider':'OCHA HDX national settlements catalog','country_code':code,'title':pkg.get('title'),
  'license':pkg.get('license_title'),'metadata_modified':pkg.get('metadata_modified'),'notes':pkg.get('notes'),
  'canonical_catalog_url':url,'resolved_catalog_url':resolved,'retained_package_metadata':save(f'hdx-{dataset_id}-package-metadata.json.gz',raw),
  'resources':pkg.get('resources',[]),'rows_retained':False}
 if reusable:
  wanted=next((x for x in pkg.get('resources',[]) if x.get('name')=='sen_plpp_gov_ocha_09082017.zip'),None)
  if not wanted: raise RuntimeError('Senegal settlement layer not found')
  data,download_url,headers=get(wanted['url']);record.update({'resource':wanted,'resolved_download_url':wanted['url'],'download_redirect_note':'The retrieved bytes followed a temporary signed HDX redirect; its credentials are omitted. Restore from the canonical catalog/resource route.','download_headers':compact(headers),
    'retained_original_archive':save('hdx-senegal-settlements-2017.zip.gz',data),'rows_retained':True})
 else:
  record['reason']='The catalog labels this package Other; preserve canonical metadata and lawful restoration link only, do not redistribute settlement rows.'
 results['sources'].append(record)

# GRID3 settlement extent metadata. Large/blocked resources are not downloaded; their
# database-ready extent distributions need bounded partitions or authorized queries.
for code,dataset_id,resource_id in [('NGA','grid3-nga-settlement-extents-v4_1','c78c9033-af77-4bc3-85cc-f1c34710f504'),('SEN','grid3-sen-settlement-extents-v3-0','7321a6fe-ec39-47ea-bc7f-1278ce259504'),('SLE','grid3-sle-settlement-extents-v3-0',None)]:
 url=f'https://data.humdata.org/api/3/action/package_show?id={dataset_id}'
 try:
  raw,resolved,_=get(url);pkg=json.loads(raw)['result']
  entry={'id':dataset_id,'provider':'GRID3/HDX settlement extents','country_code':code,'title':pkg.get('title'),
   'license':pkg.get('license_title'),'metadata_modified':pkg.get('metadata_modified'),'notes':pkg.get('notes'),
   'canonical_catalog_url':url,'resolved_catalog_url':resolved,'retained_package_metadata':save(f'hdx-{dataset_id}-package-metadata.json.gz',raw),
   'resources':pkg.get('resources',[]),'rows_retained':False}
  resource=next((x for x in pkg.get('resources',[]) if x.get('id')==resource_id),None) if resource_id else None
  if resource:
   try:
    _,actual,headers=get(resource['url'],method='HEAD');entry['access_screen']={'status':200,'resolved_url':actual,'headers':compact(headers),'downloaded':False,
      'reason':'Not downloaded: full-country extent file is large and subset/partition route has not been verified.'}
   except Exception as e: entry['access_screen']={'error':repr(e),'downloaded':False}
  results['sources'].append(entry)
 except Exception as e:
  results['sources'].append({'id':dataset_id,'country_code':code,'catalog_error':repr(e),'catalog_url':url,'rows_retained':False})

(S/'acquisition.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{'id':x.get('id'),'country':x.get('country_code'),'license':x.get('license') or x.get('catalog_license'),'role':x.get('issue_declared_role'),'vintage':x.get('issue_declared_vintage'),'retained':bool(x.get('retained_original_archive') or x.get('retained'))} for x in results['sources']],ensure_ascii=False,indent=2))
