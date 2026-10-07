import pathlib,urllib.request,json,hashlib,datetime,zipfile,sys
root=pathlib.Path(__file__).resolve().parent
url='https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip';size=118617033;expected='28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc';target=root/'gshhg-bin-2.3.7-original.zip'
started=datetime.datetime.now(datetime.timezone.utc).isoformat();h=hashlib.sha256();n=0;receipt={'source_url':url,'started_utc':started,'expected_bytes':size,'expected_sha256':expected,'acquisition_code_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'WorldAtlas-original-source-custody/1'}),timeout=60) as r:
  receipt.update(status=r.status,resolved_url=r.url,response_headers=dict(r.headers))
  with target.open('xb') as f:
   while True:
    b=r.read(1024*1024)
    if not b:break
    n+=len(b)
    if n>size:raise ValueError('Original archive exceeds exact expected byte count')
    h.update(b);f.write(b)
 receipt.update(actual_bytes=n,actual_sha256=h.hexdigest());assert n==size and h.hexdigest()==expected,'Original whole archive hash/size mismatch'
 with zipfile.ZipFile(target) as z:
  rows=[{'path':v.filename,'uncompressed_bytes':v.file_size,'compressed_bytes':v.compress_size,'crc32':v.CRC} for v in z.infolist()];receipt['members']=rows
  member='gshhs_f.b';assert len([x for x in rows if x['path']==member])==1
  mh=hashlib.sha256();mn=0
  with z.open(member) as f:
   for b in iter(lambda:f.read(1024*1024),b''):mh.update(b);mn+=len(b)
  assert mh.hexdigest()=='af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
  receipt['full_member']={'name':member,'bytes':mn,'sha256':mh.hexdigest()}
  terms=[]
  for v in z.infolist():
   if any(k in v.filename.upper() for k in ['LICENSE','COPYING','README','NOTICE','COPYRIGHT']):
    b=z.read(v);assert len(b)<1024*1024;terms.append({'name':v.filename,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode('utf-8',errors='replace')})
  receipt['distributed_terms']=terms
 receipt['result']='PASS exact complete original archive and member authentication'
except Exception as e:
 receipt.update(result='FAIL acquisition/authentication',error=repr(e),actual_bytes=n,actual_sha256=h.hexdigest());raise
finally:
 receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(root/'original-acquisition-receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({k:v for k,v in receipt.items() if k not in ['members','distributed_terms','response_headers']}));print('members',len(receipt['members']),'terms',[(x['name'],x['bytes']) for x in receipt['distributed_terms']])
