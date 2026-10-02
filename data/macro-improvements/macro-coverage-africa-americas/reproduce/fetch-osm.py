from urllib.request import urlopen,Request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,time
P=Path('/tmp/worldatlas-macro-coverage-africa-americas');(P/'osm').mkdir(exist_ok=True)
boxes={'disko':(69.1,-55.15,70.42,-51.7),'milne-land':(70.35,-28.3,71.2,-25.1),'inaccessible':(-37.4,-12.78,-37.25,-12.55)}
def f(a):
 name,b=a;q='[out:json][timeout:120];way["natural"="coastline"]('+','.join(map(str,b))+');out geom;';(P/'osm'/(name+'-query.txt')).write_text(q)
 for host in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
  try:
   req=Request(host,data=q.encode(),headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'WorldAtlas scholarly geographic coverage verification'})
   with urlopen(req,timeout=150) as r:raw=r.read();status=r.status
   (P/'osm'/(name+'.json')).write_bytes(raw);v=json.loads(raw);row=dict(id='osm-coast-'+name,url=host,query=q,status=status,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),elements=len(v.get('elements',[])),remark=v.get('remark'),osm_timestamp=v.get('osm3s',{}).get('timestamp_osm_base'),license='ODbL-1.0 OpenStreetMap contributors; attribution and database share-alike',retrieved_on='2026-10-02');print(row);return row
  except Exception as e:print(name,host,str(e));last=str(e)
 return dict(id='osm-coast-'+name,error=last)
with ThreadPoolExecutor(max_workers=2) as e:rows=list(e.map(f,boxes.items()))
(P/'osm-source-inventory.json').write_text(json.dumps(rows,separators=(',',':')))
