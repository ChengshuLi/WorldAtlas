import urllib.request,pathlib,hashlib,json,concurrent.futures,zipfile,io
P=pathlib.Path('/tmp/worldatlas-macro-coverage-africa-americas');codes=['ES','PT','BM','PM','FR','CU','HT','DO','JM','PR','VI','VG','AI','AG','KN','MS','GP','MQ','DM','LC','VC','BB','GD','TT','AW','CW','BQ','SX','MF','VE','CO','HN','NI']
def f(code):
 u='https://download.geonames.org/export/dump/'+code+'.zip'
 try:
  with urllib.request.urlopen(u,timeout=50) as r:b=r.read();status=r.status
  (P/'geonames'/(code+'.zip')).write_bytes(b);txt=zipfile.ZipFile(io.BytesIO(b)).read(code+'.txt').decode();rows=[]
  for l in txt.splitlines():
   a=l.split('\t')
   if len(a)>=19 and a[7] in ['ISL','ISLS','ATOL','RF','RK','RKS']:rows.append(dict(id=a[0],name=a[1],ascii_name=a[2],aliases=a[3].split(','),latitude=float(a[4]),longitude=float(a[5]),feature_class=a[6],feature_code=a[7],country=a[8],modified=a[18]))
  (P/'geonames'/(code+'-islands.json')).write_text(json.dumps(rows,separators=(',',':')))
  return dict(id='geonames-'+code,url=u,status=status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),file='geonames/'+code+'.zip',named_island_entries=len(rows),license='CC-BY-4.0',vintage='daily dump retrieved2026-10-02')
 except Exception as e:return dict(id='geonames-'+code,url=u,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(f,codes))
(P/'geonames-source-inventory-extra.json').write_text(json.dumps(rows,separators=(',',':')));print([(x['id'],x.get('status'),x.get('bytes'),x.get('named_island_entries')) for x in rows])
