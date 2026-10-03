#!/usr/bin/env python3
"""Retrieve the pinned release metadata for exactly the source boundaries in issue #485."""
import json,urllib.request,datetime,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;S=P/'sources';S.mkdir(exist_ok=True)
PIN='9469f09';entries=[('CAN','ADM3'),('USA','ADM1'),('USA','ADM2')]
for iso,adm in entries:
 url=f'https://www.geoboundaries.org/api/current/gbOpen/{iso}/{adm}/'
 req=urllib.request.Request(url,headers={'User-Agent':'WorldAtlas geography evidence research'})
 with urllib.request.urlopen(req,timeout=45) as r:raw=r.read()
 meta=json.loads(raw)
 expected=f'https://github.com/wmgeolab/geoBoundaries/raw/{PIN}/releaseData/gbOpen/{iso}/{adm}/geoBoundaries-{iso}-{adm}.geojson'
 if meta.get('gjDownloadURL')!=expected:raise SystemExit(f'{iso}/{adm}: release changed; found {meta.get("gjDownloadURL")}')
 out={'metadata_endpoint':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metadata_response_sha256':hashlib.sha256(raw).hexdigest(),'metadata':meta}
 path=S/f'geoboundaries-{iso}-{adm}-source-metadata.json';b=(json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode();path.write_bytes(b)
 print(json.dumps({'path':path.name,'response_sha256':out['metadata_response_sha256'],'file_sha256':hashlib.sha256(b).hexdigest(),'boundaryLicense':meta.get('boundaryLicense'),'licenseDetail':meta.get('licenseDetail'),'sourceDataUpdateDate':meta.get('sourceDataUpdateDate'),'boundaryYearRepresented':meta.get('boundaryYearRepresented'),'admUnitCount':meta.get('admUnitCount'),'pinned_geojson':meta.get('gjDownloadURL')},ensure_ascii=False))
