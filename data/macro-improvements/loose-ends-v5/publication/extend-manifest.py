from pathlib import Path
import json,gzip,tarfile,hashlib,shutil
import argparse
a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--prepared',required=True);a.add_argument('--output',required=True);opts=a.parse_args()
root=Path(opts.root).resolve();d=Path(opts.prepared).resolve();out=Path(opts.output).resolve();out.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(root/'data/macro-improvements/loose-ends-v5/publication/prior-v4-geographic-release.tar.gz') as t:
 for m in t:
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
  p=out/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
base=json.loads((out/'index.json').read_bytes());pointer=json.loads((out/'current-manifest.json').read_bytes());packed=(out/pointer['path']).read_bytes();assert sha(packed)==pointer['sha256'];prior=json.loads(gzip.decompress(packed));current=json.loads((d/'index.json').read_bytes());last=current['releases'][-1];assert last['version']==5 and prior['releases'][-1]['version']==4
known={}
for p in prior['batches']:
 if p['route']=='/api/records/import':
  b=(out/p['path']).read_bytes();assert sha(b)==p['sha256'];payload=gzip.decompress(b) if p.get('encoding')=='gzip' else b
  for e in json.loads(payload).get('entities',[]):known[e['id']]=e
next=json.loads(json.dumps(prior));next['releases'].append(last);added=0;retained=0
for p in current['batches']:
 if not(p['path'].startswith('5-') or p['path']=='release-5.json' or p['path'].startswith('entities-') or p['path']=='sources.json'):continue
 b=(d/p['path']).read_bytes();assert sha(b)==p['sha256'];payload=json.loads(b)
 if 'entities' in payload:
  rows=[]
  for e in payload['entities']:
   if e['id'] in known:
    old=known[e['id']]
    assert all(old.get(k)==e.get(k) for k in ['id','kind','name','parent_id','active','is_example']),e['id'];retained+=1
   else:rows.append(e)
  if not rows:continue
  added+=len(rows);payload={'entities':rows,'ingestion_id':'geographic-live-new-identities:'+sha(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode())}
 raw=json.dumps(payload,separators=(',',':'),ensure_ascii=False).encode();name='v5-'+p['path'] if p['route']=='/api/records/import' else p['path'];name+='.gz';packed=gzip.compress(raw,mtime=0);(out/name).write_bytes(packed)
 next['batches'].append({'path':name,'route':p['route'],'sha256':sha(packed),'encoding':'gzip','payload_sha256':sha(raw)})
 if 'sources' in payload:next['sources_batches'].append(name)
assert added==2 and retained==42
next['new_entities']=prior['new_entities']+added;next['total_memberships']=prior['total_memberships']+current['total_memberships'];next['changes']=prior['changes']+current['changes'];next['validated_geometry_v5']=current['validated_geometry'];next['prepared_original_registry_difference_v5']=44
raw=json.dumps(next,separators=(',',':'),ensure_ascii=False).encode();packed=gzip.compress(raw,mtime=0);name='releases-v5-gzip.json.gz';(out/name).write_bytes(packed);(out/'current-manifest.json').write_text(json.dumps({'path':name,'sha256':sha(packed),'predecessor_index_sha256':sha((out/'index.json').read_bytes())},separators=(',',':'))+'\n')
receipt={'prior_release':4,'final_release':5,'versions':[r['version'] for r in next['releases']],'retained_existing_entities':retained,'new_entities':added,'predecessor_manifest_sha256':sha((out/pointer['path']).read_bytes()),'extension_sha256':sha(packed),'original_index_preserved':True,'all_predecessor_batches_preserved':True};(root/'data/macro-improvements/loose-ends-v5/publication/manifest-extension-receipt.json').write_text(json.dumps(receipt,separators=(',',':'))+'\n');print(receipt)

