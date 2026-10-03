#!/usr/bin/env python3
"""Freeze exact #399 features, ancestors, memberships, and release pins."""
import gzip, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
issue=json.loads((OUT/'issue-metadata.json').read_text(encoding='utf-8'))
pinned_path=OUT/'baseline-extract.json'
pinned=json.loads(pinned_path.read_text(encoding='utf-8')) if pinned_path.exists() else None
baseline_commit=pinned['baseline_commit'] if pinned else __import__('subprocess').check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
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
def coord_stats(geometry):
 coords=[]
 def walk(value):
  if isinstance(value,(list,tuple)):
   if len(value)>=2 and all(isinstance(x,(int,float)) for x in value[:2]): coords.append(value[:2])
   else:
    for child in value: walk(child)
 walk(geometry['coordinates'])
 return {'bounds':[min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords)],'vertices':len(coords)}
def feature_summary(feature):
 props=feature['properties']; geom=feature['geometry']; meta=props.get('metadata',{})
 fields=('source_name','source_id','source_url','license','reference_year','administrative_level','location_basis','source_role','hierarchy_source','parent_match','geographic_area_code','geographic_region_code','semantic_review')
 return {'id':props.get('id'),'name':props.get('name'),'parent_id':props.get('parent_id'),'reference_owner':props.get('reference_owner'),'geometry_type':geom.get('type'),'geometry_sha256':hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),**coord_stats(geom),'metadata':{k:meta[k] for k in fields if k in meta}}
chains={}; parent_ids=set()
for ident,feature in features.items():
 chain=[feature['properties']]; parent=feature['properties'].get('parent_id'); seen={ident}
 while parent:
  if parent in seen: raise SystemExit(f'parent cycle {ident} {parent}')
  seen.add(parent); node=hmap.get(parent)
  if node is None: raise SystemExit(f'missing parent {parent} of {ident}')
  chain.append(node); parent_ids.add(parent); parent=node.get('parent_id')
 chains[ident]=[{'id':x.get('id'),'name':x.get('name'),'level':x.get('level'),'parent_id':x.get('parent_id')} for x in chain]
inv_path=ROOT/'data/macro-foundation/current-membership-inventory.json.gz'
with gzip.open(inv_path,'rt',encoding='utf-8') as f: inv={x['id']:x for x in json.load(f)}
if not parent_ids.issubset(inv): raise SystemExit(f'missing ancestor membership rows {sorted(parent_ids-set(inv))}')
handoff_path=ROOT/'data/macro-foundation/regional-handoffs.json.gz'
with gzip.open(handoff_path,'rt',encoding='utf-8') as f: handoffs=json.load(f)
region=next(x for x in handoffs['regions'] if x['region_id']==region_id)
proj_path=ROOT/'data/macro-foundation/current-membership-projection.json.gz'
with gzip.open(proj_path,'rt',encoding='utf-8') as f: projection=json.load(f)
projection_rows={x['id']:x for x in projection['locations'] if x['id'] in IDS}
if set(projection_rows)!=set(IDS): raise SystemExit('scope IDs absent from projection')
# Retain only direct membership IDs needed to account for this packet, its partial parents, and immediate region neighbors.
review_group_ids={x for x in parent_ids if hmap[x].get('level') in ('province','area','region')}
group_members={k:inv[k].get('member_location_ids',[]) for k in sorted(review_group_ids)}
partpaths=sorted({ROOT/'data/geography'/f'part-{int(x.get("properties",{}).get("part",0))}.json' for x in features.values()})
paths=[ROOT/'data/world-index.json',hier_path,ROOT/'data/semantic-report.json',inv_path,proj_path,handoff_path,ROOT/'data/macro-foundation/macro-certificate.json',*partpaths]
record={'baseline_commit':baseline_commit,'issue':399,'region':{'id':region['region_id'],'name':region['name'],'continent_id':region['continent_id'],'subcontinent_id':region['subcontinent_id'],'frozen_geometry_sha256':region['envelope']['geometry_sha256'],'frozen_member_ids_sha256':region['envelope']['member_location_ids_sha256'],'location_count':region['envelope']['locations']},'scope_location_ids':IDS,'locations':{i:feature_summary(features[i]) for i in IDS},'projection_rows':projection_rows,'complete_parent_chains':chains,'review_group_member_location_ids':group_members,'region_member_location_ids':next(v for k,v in group_members.items() if hmap[k].get('level')=='region'),'baseline_files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]}
payload=json.dumps(record,indent=2,ensure_ascii=False)+'\n'
target=OUT/'baseline-extract.json'
if '--check' in sys.argv:
 if not target.exists() or target.read_text(encoding='utf-8')!=payload: raise SystemExit('baseline extract differs; regenerate deliberately without --check')
else: target.write_text(payload,encoding='utf-8')
print(json.dumps({'check':'passed' if '--check' in sys.argv else 'written','ids':len(IDS),'location_names':{i:features[i]['properties'].get('name') for i in IDS},'parent_chains':{i:[x.get('id') for x in c] for i,c in chains.items()},'reviewed_parent_groups':len(group_members),'baseline_files':record['baseline_files'],'extract_bytes':target.stat().st_size},indent=2,ensure_ascii=False))
