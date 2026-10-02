#!/usr/bin/env python3
"""Read-only full membership audit. Bounding-box screens identify review candidates, not reassignment evidence."""
import argparse,collections,hashlib,json,pathlib
from shapely.geometry import shape

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def audit(root):
 root=pathlib.Path(root);hierarchy=json.loads((root/'data/hierarchy.json').read_text());units={u['id']:u for u in hierarchy};index=json.loads((root/'data/world-index.json').read_text());features=[];pins={'data/hierarchy.json':digest(root/'data/hierarchy.json'),'data/world-index.json':digest(root/'data/world-index.json')}
 for part in index['parts']:
  path=root/'data'/part;pins['data/'+part]=digest(path);features.extend(json.loads(path.read_text())['features'])
 macros={u['id']:{'id':u['id'],'name':u['name'],'level':u['level'],'parent_id':u['parent_id'],'immediate_child_ids':sorted(c['id'] for c in hierarchy if c['parent_id']==u['id']),'location_ids':[],'descendant_group_ids':[],'source_ids':collections.Counter(),'reference_owners':collections.Counter(),'bounds':None,'invalid_location_ids':[],'source_island_associations':collections.defaultdict(list)} for u in hierarchy if u['level'] in ['continent','subcontinent']}
 def ancestors(parent):
  seen=set()
  while parent:
   if parent in seen:raise ValueError('Cyclic parent chain: '+parent)
   seen.add(parent);u=units[parent];yield u;parent=u['parent_id']
 for u in hierarchy:
  for a in ancestors(u['parent_id']):
   if a['id'] in macros:macros[a['id']]['descendant_group_ids'].append(u['id'])
 candidates=[];locations=[]
 for f in features:
  p=f['properties'];i=p['id'];geom=shape(f['geometry']);bounds=list(geom.bounds);chain=list(ancestors(p['parent_id']));chain_by_level={u['level']:u for u in chain};m=p.get('metadata',{});continent=chain_by_level['continent']['name'];screens=[]
  # These are intentionally generous spatial envelopes. They do not purport to digitize divides.
  if continent=='Asia' and bounds[0]<61 and bounds[2]>45 and bounds[3]>40:screens.append('europe-asia-land-divide')
  if continent=='Europe' and bounds[2]>45 and bounds[3]>40:screens.append('europe-asia-land-divide')
  if bounds[0]<36 and bounds[2]>31 and bounds[1]<32 and bounds[3]>27:screens.append('suez-sinai')
  if bounds[0]<44 and bounds[2]>39 and bounds[1]<43 and bounds[3]>38:screens.append('aegean-cyprus')
  if bounds[0]<151 and bounds[2]>128 and bounds[1]<1 and bounds[3]>-12:screens.append('asia-oceania-archipelago')
  if bounds[0]<-76 and bounds[2]>-79 and bounds[1]<10 and bounds[3]>7:screens.append('panama-darien')
  if m.get('source_role') in ('remote island','remote island group') or m.get('remote_version') or any(x in p['name'].lower() for x in ['island','azores','sokotra','socotra','bermuda','sinai','macquarie']):
   # Source area code permits a complete archipelago crosswalk without treating owner as geography.
   for u in chain:
    if u['id'] in macros:macros[u['id']]['source_island_associations'][m.get('geographic_area_code','unclassified')].append(i)
  for u in chain:
   if u['id'] not in macros:continue
   a=macros[u['id']];a['location_ids'].append(i);a['source_ids'][m.get('source_id','unknown')]+=1;a['reference_owners'][p.get('reference_owner','unknown')]+=1
   if not geom.is_valid:a['invalid_location_ids'].append(i)
   a['bounds']=bounds if a['bounds'] is None else [min(a['bounds'][0],bounds[0]),min(a['bounds'][1],bounds[1]),max(a['bounds'][2],bounds[2]),max(a['bounds'][3],bounds[3])]
  row={'id':i,'name':p['name'],'parent_id':p['parent_id'],'chain':{u['level']:u['id'] for u in reversed(chain)},'bounds':bounds,'source_id':m.get('source_id'),'source_area_code':m.get('geographic_area_code'),'reference_owner':p.get('reference_owner'),'source_role':m.get('source_role'),'source_url':m.get('source_url'),'reference_year':m.get('reference_year'),'license':m.get('license')}
  locations.append(row)
  if screens:candidates.append({**row,'screens':screens})
 for m in macros.values():
  for key in ['location_ids','descendant_group_ids','invalid_location_ids']:m[key]=sorted(m[key])
  m['location_count']=len(m['location_ids']);m['source_ids']=dict(sorted(m['source_ids'].items()));m['reference_owners']=dict(sorted(m['reference_owners'].items()));m['source_island_associations']={k:sorted(v) for k,v in sorted(m['source_island_associations'].items())}
 assert len([m for m in macros.values() if m['level']=='continent'])==6
 assert len([m for m in macros.values() if m['level']=='subcontinent'])==29
 assert sum(m['location_count'] for m in macros.values() if m['level']=='continent')==len(features)
 return {'version':1,'input_sha256':pins,'location_count':len(features),'groups':sorted(macros.values(),key=lambda m:(m['level'],m['name'])),'boundary_screen_candidates':candidates,'locations':locations,'method':'Every current geometry and adjacent-tier parent chain inspected. Spatial-envelope candidates are diagnostic only; no geometry or hierarchy is mutated.'}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parents[1]));parser.add_argument('--output',default='.cache/research/macro-boundary/membership-audit.json');args=parser.parse_args();result=audit(args.root);output=pathlib.Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'groups':len(result['groups']),'locations':result['location_count'],'boundary_screen_candidates':len(result['boundary_screen_candidates']),'output':str(output)}))
