#!/usr/bin/env python3
"""Reproduce concise #439 member, parent-chain, group and source pins from current baseline."""
import gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
issue=json.loads((OUT/'issue-metadata.json').read_text()); body=issue['body']
scope=json.loads(body.split('Machine-readable exact workload scope (JSON; it is an evidence workload partition, not an atlas geographic partition):\n\n```json\n',1)[1].split('\n```',1)[0])
ids=scope['member_location_ids']; region_id=scope['region_id']
old=json.loads((OUT/'baseline-extract.json').read_text()) if (OUT/'baseline-extract.json').exists() else None
baseline=old['baseline_commit'] if old else subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
hier=load(ROOT/'data/hierarchy.json'); hm={x['id']:x for x in hier}; features={}; feature_paths={}
for p in sorted((ROOT/'data/geography').glob('part-*.json')):
 for f in load(p)['features']:
  i=f.get('id',f.get('properties',{}).get('id'))
  if i in ids: features[i]=f; feature_paths[i]=p
if set(features)!=set(ids): raise SystemExit(f'missing IDs: {sorted(set(ids)-set(features))}')
def coords(g):
 out=[]
 def walk(v):
  if isinstance(v,(list,tuple)):
   if len(v)>=2 and all(isinstance(x,(int,float)) for x in v[:2]): out.append(v[:2])
   else:
    for c in v: walk(c)
 walk(g['coordinates']); return out
def summary(f):
 p=f['properties']; g=f['geometry']; cs=coords(g); m=p.get('metadata',{})
 fields=('source_name','source_id','source_url','license','reference_year','administrative_level','location_basis','source_role','hierarchy_source','parent_match','geographic_area_code','geographic_region_code','semantic_review')
 return {'id':p.get('id'),'name':p.get('name'),'parent_id':p.get('parent_id'),'reference_owner':p.get('reference_owner'),'geometry_type':g['type'],'geometry_sha256':hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'vertices':len(cs),'bounds':[min(x for x,y in cs),min(y for x,y in cs),max(x for x,y in cs),max(y for x,y in cs)],'metadata':{k:m[k] for k in fields if k in m}}
chains={}; parents=set()
for i,f in features.items():
 c=[f['properties']]; n=f['properties'].get('parent_id'); seen={i}
 while n:
  if n in seen or n not in hm: raise SystemExit(f'bad parent chain for {i}: {n}')
  seen.add(n); x=hm[n]; c.append(x); parents.add(n); n=x.get('parent_id')
 chains[i]=[{'id':x.get('id'),'name':x.get('name'),'level':x.get('level'),'parent_id':x.get('parent_id')} for x in c]
with gzip.open(ROOT/'data/macro-foundation/current-membership-inventory.json.gz','rt') as f: inv={x['id']:x for x in json.load(f)}
review={k:inv[k]['member_location_ids'] for k in sorted(parents) if hm[k].get('level') in ('province','area','region')}
with gzip.open(ROOT/'data/macro-foundation/regional-handoffs.json.gz','rt') as f: hand=json.load(f)
r=next(x for x in hand['regions'] if x['region_id']==region_id)
paths=[ROOT/'data/world-index.json',ROOT/'data/hierarchy.json',ROOT/'data/semantic-report.json',ROOT/'data/macro-foundation/current-membership-inventory.json.gz',ROOT/'data/macro-foundation/current-membership-projection.json.gz',ROOT/'data/macro-foundation/regional-handoffs.json.gz',ROOT/'data/macro-foundation/macro-certificate.json']
parts=sorted(set(feature_paths.values())); paths+=parts
projection=json.load(gzip.open(ROOT/'data/macro-foundation/current-membership-projection.json.gz','rt'))
proj={x['id']:x for x in projection['locations'] if x['id'] in ids}
rec={'baseline_commit':baseline,'issue':439,'region':{'id':region_id,'name':r['name'],'continent_id':r['continent_id'],'subcontinent_id':r['subcontinent_id'],'frozen_geometry_sha256':r['envelope']['geometry_sha256'],'frozen_member_ids_sha256':r['envelope']['member_location_ids_sha256'],'location_count':r['envelope']['locations']},'scope_location_ids':ids,'locations':{i:summary(features[i]) for i in ids},'complete_parent_chains':chains,'review_group_member_location_ids':review,'region_member_location_ids':next(v for k,v in review.items() if hm[k].get('level')=='region'),'projection_rows':proj,'baseline_files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]}
payload=json.dumps(rec,indent=2,ensure_ascii=False)+'\n'; target=OUT/'baseline-extract.json'
if '--check' in sys.argv:
 if not target.exists() or target.read_text()!=payload: raise SystemExit('baseline changed; review before regeneration')
else: target.write_text(payload)
print(json.dumps({'result':'passed' if '--check' in sys.argv else 'written','locations':len(ids),'parent_chains':len(chains),'group_counts':{k:len(v) for k,v in review.items()},'bytes':target.stat().st_size},indent=2))
