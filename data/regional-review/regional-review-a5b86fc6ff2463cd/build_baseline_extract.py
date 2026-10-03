#!/usr/bin/env python3
"""Freeze exact #134 features, ancestors, memberships, and release pins."""
import gzip, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
issue=json.loads((OUT/'issue-metadata.json').read_text(encoding='utf-8'))
scope=json.loads(issue['body'].split('```json\n',1)[1].split('\n```',1)[0])
IDS=scope['member_location_ids']; region_id=scope['region_id']
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
hier_path=ROOT/'data/hierarchy.json'; hierarchy=load(hier_path); hmap={x['id']:x for x in hierarchy}
features={}
for path in sorted((ROOT/'data/geography').glob('part-*.json')):
 for feature in load(path)['features']:
  ident=feature.get('id',feature.get('properties',{}).get('id'))
  if ident in IDS: features[ident]=feature
if set(features)!=set(IDS): raise SystemExit(f'exact issue IDs missing: {sorted(set(IDS)-set(features))}')
chains={}; parent_ids=set()
for ident,feature in features.items():
 chain=[feature['properties']]; parent=feature['properties'].get('parent_id'); seen={ident}
 while parent:
  if parent in seen: raise SystemExit(f'parent cycle {ident} {parent}')
  seen.add(parent); node=hmap.get(parent)
  if node is None: raise SystemExit(f'missing parent {parent} of {ident}')
  chain.append(node); parent_ids.add(parent); parent=node.get('parent_id')
 chains[ident]=chain
inv_path=ROOT/'data/macro-foundation/current-membership-inventory.json.gz'
with gzip.open(inv_path,'rt',encoding='utf-8') as f: inv={x['id']:x for x in json.load(f)}
membership={k:inv[k] for k in sorted(parent_ids) if k in inv}
if set(membership)!=parent_ids: raise SystemExit(f'missing ancestor membership rows {sorted(parent_ids-set(membership))}')
handoff_path=ROOT/'data/macro-foundation/regional-handoffs.json.gz'
with gzip.open(handoff_path,'rt',encoding='utf-8') as f: handoffs=json.load(f)
region=next(x for x in handoffs['regions'] if x['region_id']==region_id)
proj_path=ROOT/'data/macro-foundation/current-membership-projection.json.gz'
with gzip.open(proj_path,'rt',encoding='utf-8') as f: projection=json.load(f)
projection_rows={x['id']:x for x in projection['locations'] if x['id'] in IDS}
if set(projection_rows)!=set(IDS): raise SystemExit('scope IDs absent from projection')
partpaths=sorted({ROOT/'data/geography'/f'part-{int(x.get("properties",{}).get("part",0))}.json' for x in features.values()})
paths=[ROOT/'data/world-index.json',hier_path,ROOT/'data/semantic-report.json',inv_path,proj_path,handoff_path,ROOT/'data/macro-foundation/macro-certificate.json',*partpaths]
record={'baseline_commit':__import__('subprocess').check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'issue':134,'region':{'id':region['region_id'],'name':region['name'],'envelope':region['envelope'],'subcontinent_id':region['subcontinent_id'],'continent_id':region['continent_id'],'location_count':region['envelope']['locations'],'required_work':region['required_work']},'scope_location_ids':IDS,'locations':features,'projection_rows':projection_rows,'complete_parent_chains':chains,'parent_membership_inventory_rows':membership,'baseline_files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]}
(OUT/'baseline-extract.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'ids':len(IDS),'location_names':{i:features[i]['properties'].get('name') for i in IDS},'parent_chains':{i:[x.get('id') for x in c] for i,c in chains.items()},'parent_memberships':len(membership),'baseline_files':record['baseline_files'],'extract_bytes':(OUT/'baseline-extract.json').stat().st_size},indent=2,ensure_ascii=False))
