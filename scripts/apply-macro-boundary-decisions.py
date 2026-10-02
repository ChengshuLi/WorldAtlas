#!/usr/bin/env python3
"""Stage pinned macro reference changes after independently validated source repairs."""
import argparse,collections,copy,gzip,hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))

ROOT=pathlib.Path(__file__).resolve().parents[1]
TIERS=['location','province','area','region','subcontinent','continent']
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())
def raw_sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);data=(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode();p.write_bytes(gzip.compress(data,mtime=0) if p.suffix=='.gz' else data)
def load_data(path):
 index=read(path/'world-index.json');parts={x:read(path/x) for x in index['parts']};return index,parts,{u['id']:u for u in read(path/'hierarchy.json')},[f for c in parts.values() for f in c['features']]
def chain(f,units):
 parent=f['properties']['parent_id'];result=[]
 for tier in TIERS[1:]:
  if parent not in units or units[parent]['level']!=tier:raise ValueError('Incomplete adjacent-tier chain: '+f['properties']['id'])
  u=units[parent];result.append({'id':u['id'],'name':u['name'],'level':tier});parent=u['parent_id']
 if parent is not None:raise ValueError('Continent cannot have a parent')
 return result

def apply(document,units,features,source_receipt):
 if not source_receipt.get('geometry_stage_validated'):raise ValueError('Source repair stage is not independently validated')
 original_units=copy.deepcopy(units);original_features=copy.deepcopy(features);units=copy.deepcopy(units);features=copy.deepcopy(features);by_id={f['properties']['id']:f for f in features}
 if len(by_id)!=len(features):raise ValueError('Duplicate active location identities')
 changed_or_removed=set(source_receipt['changed_ids'])|set(source_receipt['removed_ids'])|set(source_receipt['added_ids'])
 required={x['id'] for x in document['location_changes']}|{i for r in document['group_changes'] for i in r.get('affected_location_ids',[])}
 if required&changed_or_removed:raise ValueError('Source footprint repair intersects a macro proposal; new area measurements required')
 if required-set(by_id):raise ValueError('Missing proposal identity after source repair')
 old_chains={i:chain(f,units) for i,f in by_id.items()}
 for row in document['group_changes']:
  old=units.get(row['id'])
  if not old or (old['name'],old['parent_id'],old['level'])!=(row['current_name'],row['current_parent_id'],row['level']):raise ValueError('Stale macro group proposal: '+row['id'])
  if row['action']=='reparent':
   actual={i for i,c in old_chains.items() if any(a['id']==row['id'] for a in c)}
   if actual!=set(row['affected_location_ids']):raise ValueError('Macro association member set changed: '+row['id'])
 for row in document['location_changes']:
  f=by_id[row['id']];p=f['properties']
  if (p['name'],p['parent_id'])!=(row['current_name'],row['current_parent_id']):raise ValueError('Stale macro location proposal: '+row['id'])
  if digest(f['geometry'])!=row['geometry_sha256']:raise ValueError('Source repair changed an assigned footprint: '+row['id'])
  # Source-independent repair stage may change unrelated descendants, but never
  # silently change the ancestor identity against which this proposal was made.
  if {x['level']:x['id'] for x in old_chains[row['id']]}!=row['evidence']['current_chain']:raise ValueError('Changed macro assignment chain: '+row['id'])
  proof=row['evidence'];share=proof['first_share'] if proof['proposed_continent']==proof['first_continent'] else proof['second_share']
  if share-proof['source_uncertainty_share']<=.5+1e-8:raise ValueError('Assignment lacks conservative strict whole-footprint majority')
 new_ids=[]
 for row in document['new_groups']:
  if row['id'] in units:raise ValueError('New macro group already exists')
  u={k:row[k] for k in ['id','name','level','parent_id']};u['metadata']={'kind':'geographic','framework_status':'atlas-defined','basis':row['role'],'reference_only':True,'reference_source':'macro-boundary-decisions','derived_from_id':row.get('derived_from_id'),'semantic_review':{'action':'create','boundary_status':'open','rationale':row['role'],'evidence':[{'url':document['sources']['physical-rivers']['url'],'title':'Pinned Natural Earth physical river/lake source','source_sha256':document['sources']['physical-rivers']['sha256'],'inspected_fact':'Member locations are individually assigned by conservative strict majority of their entire WGS84 land footprint; the geographic group footprint is the union of those members, not a new independent polygon.'}],'remaining_reasons':['Geographic side and parent chain are sourced; local-cluster granularity/descendant semantics are not certified by a continental-side assignment.']}}
  units[u['id']]=u;new_ids.append(u['id'])
 for row in document['group_changes']:
  u=units[row['id']]
  if row['action']=='rename':u['name']=row['name']
  elif row['action']=='reparent':u['parent_id']=row['parent_id']
  else:raise ValueError('Unsupported geographic group action')
  evidence=[{'url':document['sources'][s]['url'],'title':s,'inspected_fact':row['rationale'],'source_sha256':document['sources'][s].get('sha256')} for s in row['source_ids']]
  u.setdefault('metadata',{})['macro_reference_correction']={**row,'evidence':evidence,'history_transfer':'none'}
 for row in document['location_changes']:
  p=by_id[row['id']]['properties'];p['parent_id']=row['parent_id'];p.setdefault('metadata',{})['macro_boundary_assignment']={'evidence_file':'macro-boundary-decisions','divide':row['evidence']['divide'],'first_share':row['evidence']['first_share'],'second_share':row['evidence']['second_share'],'outside_surveyed_share':row['evidence']['outside_surveyed_share'],'source_uncertainty_share':row['evidence']['source_uncertainty_share'],'proposed_continent':row['evidence']['proposed_continent'],'method':row['evidence']['method'],'reference_only':True,'history_transfer':'none'}
 for row in document['groups']:
  if row['id'] not in units:raise ValueError('An independently reviewed macro identity disappeared')
  u=units[row['id']];u.setdefault('metadata',{})['macro_boundary_review']={k:row[k] for k in ['convention','source_ids','convention_status','boundary_status','semantic_status','descendant_completion','definition_method']}
  u['metadata']['macro_boundary_review']['evidence_file']='macro-boundary-decisions'
  evidence=[{'url':document['sources'][s]['url'],'title':s,'inspected_fact':document['sources'][s]['inspected_fact'],'source_sha256':document['sources'][s].get('sha256')} for s in row['source_ids']]
  # Explicitly separate the own reporting convention from descendant closure.
  u['metadata']['semantic_review']={'action':'retain','boundary_status':'supported' if row['boundary_status']=='supported-convention' else 'open','rationale':row['convention'],'evidence':evidence,'remaining_reasons':[] if row['boundary_status']=='supported-convention' else ['Exact physical segment, pending geographic association, named-island crosswalk or source omission remains open; see macro-boundary-decisions.'],'semantic_status':'open','convention_status':row['convention_status'],'descendant_completion':row['descendant_completion']}
 # Parent footprints remain membership-derived; no independently drawn parent
 # polygon is permitted to override the unique adjacent-tier memberships.
 for u in units.values():
  if u['level']=='continent':
   if u['parent_id'] is not None:raise ValueError('Continent parent')
  elif u['parent_id'] not in units or units[u['parent_id']]['level']!=TIERS[TIERS.index(u['level'])+1]:raise ValueError('Non-adjacent group parent')
 new_chains={i:chain(f,units) for i,f in by_id.items()};used={a['id'] for c in new_chains.values() for a in c};retired=[copy.deepcopy(u) for i,u in units.items() if i not in used]
 if set(new_ids)-used:raise ValueError('Created empty macro group')
 units={i:u for i,u in units.items() if i in used};counts=collections.Counter(f['properties']['parent_id'] for f in features);counts.update(u['parent_id'] for u in units.values() if u['parent_id'])
 for u in units.values():u['metadata']['child_count']=counts[u['id']]
 originals={f['properties']['id']:f for f in original_features};crosswalk=[];changed_properties=[]
 for f in features:
  i=f['properties']['id'];old=originals[i]
  if old['geometry']!=f['geometry']:raise ValueError('Macro migration changed location geometry')
  if old_chains[i]!=new_chains[i]:crosswalk.append({'location_id':i,'before_chain':old_chains[i],'after_chain':new_chains[i],'history_transfer':'none','footprint_unchanged':True})
  if old['properties']!=f['properties']:changed_properties.append({'location_id':i,'before_properties':old['properties'],'after_properties':f['properties'],'geometry_sha256':digest(f['geometry']),'history_transfer':'none'})
 groupchanges=[{'id':i,'before':original_units.get(i),'after':units.get(i)} for i in sorted(set(original_units)|set(units)) if original_units.get(i)!=units.get(i)]
 receipt={'version':1,'reference_only':True,'scope':'Macro-geographic reference migration following validated source-territory repair; no dated historical attribute/membership transfer','before_sha256':digest([original_units,original_features]),'after_sha256':digest([units,features]),'before_units':list(original_units.values()),'retired_units':retired,'new_group_ids':new_ids,'group_changes':groupchanges,'location_chain_crosswalk':crosswalk,'changed_location_properties':changed_properties,'unchanged_geometry_ids':sorted(by_id),'unchanged_geometry_sha256':digest([[i,by_id[i]['geometry']] for i in sorted(by_id)]),'historical_claims_transferred':False,'source_repair_disjointness':{'changed_or_removed_ids':sorted(changed_or_removed),'required_macro_location_ids':sorted(required),'intersection':[]},'counts':dict(collections.Counter(u['level'] for u in units.values()))|{'location':len(features)},'summary':{'direct_location_parent_changes':len(document['location_changes']),'changed_location_chains':len(crosswalk),'changed_location_properties':len(changed_properties),'group_changes':len(groupchanges),'new_groups':len(new_ids),'retired_groups':len(retired),'geometry_changes':0,'historical_records_touched':0,'semantic_complete':False}}
 return units,features,receipt

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-stage',default=str(ROOT/'.cache/source-territory-repair-stage'));p.add_argument('--output',default=str(ROOT/'.cache/macro-boundary-repair-stage'));a=p.parse_args();source=pathlib.Path(a.source_stage);output=pathlib.Path(a.output);decision_path=ROOT/'data/macro-boundary-decisions.json';doc=read(decision_path)
 # Verify the exact original source snapshot and all frozen review documents.
 for relative,pin in doc['input_content_sha256'].items():
  target=ROOT/relative if relative.startswith('data/geographic-decisions/') else source/'before'/relative.removeprefix('data/')
  if not target.exists() or digest(read(target))!=pin:raise ValueError('Changed original macro/source-repair content: '+relative)
 receipt_path=source/'migration-receipt.json';source_receipt=read(receipt_path)
 if source_receipt['before_hierarchy_sha256']!=doc['input_sha256']['data/hierarchy.json'] or any(source_receipt['input_parts'][part]!=doc['input_sha256']['data/'+part] for part in source_receipt['input_parts']):raise ValueError('Source repair receipt belongs to another original release')
 retained_rivers=ROOT/'data/macro-boundary-source-rivers.geojson.gz'
 if hashlib.sha256(gzip.decompress(retained_rivers.read_bytes())).hexdigest()!=doc['sources']['physical-rivers']['sha256']:raise ValueError('Retained physical geometry archive changed')
 index,parts,units,features=load_data(source/'after');revised,changed,receipt=apply(doc,units,features,source_receipt)
 receipt['retained_physical_geometry']={'path':str(retained_rivers.relative_to(ROOT)),'sha256':raw_sha(retained_rivers),'uncompressed_sha256':doc['sources']['physical-rivers']['sha256']};receipt['decisions_file_sha256']=raw_sha(decision_path);receipt['source_repair_receipt_sha256']=raw_sha(receipt_path);receipt['source_stage_after_input_sha256']={str(p.relative_to(source/'after')):raw_sha(p) for p in [source/'after/hierarchy.json',source/'after/world-index.json']+[source/'after'/x for x in index['parts']]};receipt['preparation_script_sha256']=raw_sha(pathlib.Path(__file__))
 write(output/'before/hierarchy.json',list(units.values()));write(output/'before/world-index.json',index);write(output/'after/hierarchy.json',list(revised.values()));write(output/'after/world-index.json',index);by_id={f['properties']['id']:f for f in changed}
 for part,collection in parts.items():
  write(output/'before'/part,collection);replaced={**collection,'features':[by_id[f['properties']['id']] for f in collection['features']]};write(output/'after'/part,replaced)
 write(output/'migration-receipt.json.gz',receipt);write(ROOT/'data/macro-boundary-migration.json.gz',receipt);print(json.dumps(receipt['summary']|{'counts':receipt['counts'],'output':str(output)}))
if __name__=='__main__':main()
