import json,gzip,hashlib,subprocess,time,resource
from pathlib import Path
root=Path('.cache/global-rescreen');start=time.monotonic();inputs=[]
def canon(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def read(p,path=None):
 b=subprocess.check_output(['git','show','HEAD:'+(path or p['path'])]);assert len(b)==p['bytes'] and sha(b)==p['sha256'];raw=gzip.decompress(b);assert len(raw)==p['uncompressed_bytes'] and sha(raw)==p['uncompressed_sha256'];inputs.append(dict(p,actual_path=path or p['path']));return json.loads(raw)
i=json.load(open(root/'inventory-report.json'));s=json.load(open(root/'successor-report.json'));m={}
for p in i['complete_products']['components']:
 actual=next(x['path'] for x in i['source_descriptors'] if x['sha256']==p['sha256']);value=read(p,actual);assert value['type']=='FeatureCollection'
 for f in value['features']:
  assert f['id'] not in m;m[f['id']]=f
p=next(p for p in s['products'] if p['path']=='components-delta.json.gz');d=read(p,'coordination/engineering/worldwide-successor-1215-20261006/run-one/'+p['path'])
assert len(m)==d['original_count'] and sha(canon([m[k] for k in sorted(m)]))==d['original_records_sha256']
for k in d['removed_ids']:del m[k]
assert len(m)==d['retained_count'] and sha(canon(sorted(m)))==d['retained_ids_sha256']
for f in d['upsert_records']:
 assert f['id'] not in m;m[f['id']]=f
assert len(m)==d['current_count'] and sha(canon([m[k] for k in sorted(m)]))==d['current_records_sha256']
w=json.load(open(root/'current-owner-witnesses.json'));wanted={x['component_id'] for x in w if x['current_owner']==0};assert wanted<=set(m)
rows=[]
for k in sorted(wanted):
 f=m[k];g=f['geometry'];rows.append({'id':k,'geometry':g,'geometry_sha256':sha(canon(g)),'whole_feature_sha256':sha(canon(f))})
(root/'current-positive-geometries.json').write_bytes(canon(rows));report={'original_components':d['original_count'],'current_components':len(m),'selected_current_owner_zero_witnesses':len(rows),'inputs':inputs,'elapsed_seconds':time.monotonic()-start,'maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};(root/'geometry-restoration-report.json').write_bytes(canon(report));print(json.dumps({k:v for k,v in report.items() if k!='inputs'}))
