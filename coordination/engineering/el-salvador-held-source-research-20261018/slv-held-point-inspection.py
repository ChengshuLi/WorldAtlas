import subprocess,gzip,json,hashlib,struct,pathlib
R='/workspace/scratch/127991fc8b8e/worldatlas-primary'
def blob(x):return subprocess.check_output(['git','--no-lazy-fetch','-C',R,'cat-file','blob',x])
def inside_ring(p,ring):
 x,y=p;hit=False
 for a,b in zip(ring,ring[1:]+ring[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
 return hit
def inside(p,g):
 polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
 return any(inside_ring(p,q[0]) and not any(inside_ring(p,h) for h in q[1:]) for q in polys)
e=json.load(open('/workspace/shared/worldatlas-recovery/slv-original-source-evidence.json'));lat=gzip.decompress(blob('de6905e162dc031b1b93248fae91190c39c4ad53'));res=[]
for owner,x,y in [(39827,67180,121014),(39842,67200,121199),(39842,67198,121202)]:
 p=((360*x+180-180*262166)/262166,struct.unpack_from('<d',lat,y*8)[0]);t=next(t for t in e['targets'] if t['pixelIndex']==owner);row={'owner':owner,'x':x,'y':y,'centre':p,'stable_id':t['id'],'matches':[]}
 for family in e['territorial_exclusion_sources']+e['families']:
  if family['source_id'] not in ['gb:HND:ADM1','gb:HND:ADM2','gb:SLV:ADM2']:continue
  pin=family['parts'][0];b=blob(pin['git_blob_oid']);d=gzip.decompress(b);assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256'] and hashlib.sha256(d).hexdigest()==pin['decoded_sha256'];j=json.loads(d)
  for i,f in enumerate(j['features']):
   if inside(p,f['geometry']):row['matches'].append({'family':family['source_id'],'ordinal':i,'properties':f.get('properties'),'pin':pin})
 res.append(row)
p=pathlib.Path('/workspace/shared/worldatlas-recovery/slv-held-point-inspection.json');p.write_text(json.dumps({'method':'Independent read-only point-in-original-polygon attribution, not stock science or acceptance','rows':res},indent=2));print(json.dumps(res,indent=2))
