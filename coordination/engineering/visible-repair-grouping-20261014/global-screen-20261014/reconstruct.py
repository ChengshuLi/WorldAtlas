import json,gzip,hashlib,subprocess,time,resource
from collections import Counter
from pathlib import Path
root=Path('.cache/global-rescreen');start=time.monotonic();inputs=[]
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
 b=subprocess.check_output(['git','show','HEAD:'+p['path']]);assert len(b)==p['bytes'] and sha(b)==p['sha256'],p['path'];r=gzip.decompress(b);assert len(r)==p['uncompressed_bytes'] and sha(r)==p['uncompressed_sha256'],p['path'];inputs.append(p);return json.loads(r)
f=json.load(open(root/'frozen-report.json'));r=json.load(open(root/'historical-report.json'));old=[]
for p in f['outputs']['frozen-reviewed-native']:old.extend(read(p))
m={x['component']:x for x in old};assert len(m)==len(old)==95174;del old
o=read(f['outputs']['selected-repository-native-complete-overlay'][0])[0]
assert sha(canonical([m[k] for k in sorted(m)]))==o['original_rows_sha256']
for x in o['changed_rows']:m[x['component']]=x
assert sha(canonical([m[k] for k in sorted(m)]))==o['current_rows_sha256']
d=read(r['outputs']['selected-current-native-delta'][0])[0];assert sha(canonical([m[k] for k in sorted(m)]))==d['original_records_sha256']
for k in d['removed_ids']:del m[k]
for x in d['upsert_records']:m[x['component']]=x
assert len(m)==95173 and sha(canonical([m[k] for k in sorted(m)]))==d['current_records_sha256']
counts=Counter(x['native_status'] for x in m.values());assert dict(counts)==r['native_counts'];contexts={}
for p in r['outputs']['current-batches']:
 for b in read(p):
  for k in b['component_ids']:
   assert k not in contexts;contexts[k]={'source_ids':sorted({s['source_id'] for s in b['source_families']}),'contact_ids':b['contact_ids'],'historical_source_families':b['source_families'],'rank':b['best_rank']['measured_impact']}
assert set(contexts)==set(m)
positives=[];unknown=[]
for k,x in sorted(m.items()):
 if x['native_status']=='inside-unassigned-native-cell':
  assert x['native_cell_centre_strictly_inside'] and x['owner_integer']==0
  positives.append({'component_id':k,'cell':x['cell'],'cell_centre_lonlat':x['cell_centre_lonlat'],'bounds':x['original_extent_lonlat'],**contexts[k]})
 else:unknown.append({'component_id':k,'status':'unknown','historical_status':x['native_status']})
(root/'historical-positive-witnesses.json').write_bytes(canonical(positives));(root/'historical-unknowns.json').write_bytes(canonical(unknown));report={'component_count':len(m),'historical_positive_witnesses':len(positives),'unknown_components':len(unknown),'inputs':inputs,'elapsed_seconds':time.monotonic()-start,'maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'Existing observation reconstruction only; current ownership and exact native operator still to be checked.'};(root/'reconstruction-report.json').write_bytes(canonical(report));print(json.dumps({k:v for k,v in report.items() if k!='inputs'}))
