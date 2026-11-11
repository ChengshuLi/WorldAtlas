"""Strict adapter from pinned selected Neon L2 boundary records.

The caller must authenticate that the pinned bytes were actually exported
from the intended Neon branch/revision. A JSON `source` label is not proof.
No preview or prior assignment map is accepted as executable input.
"""
import hashlib,json,re
from pathlib import Path
from regions import points,geometry_hash,SUPPORTING_RELATIONSHIPS,CONSTRUCTION_RELATIONSHIP


def no_duplicates(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate JSON key')
  d[k]=v
 return d

def load_pinned_snapshot(path,expected_sha256,guard):
 if not callable(guard):raise ValueError('resource guard required')
 h=hashlib.sha256();parts=[]
 with open(path,'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   parts.append(b);h.update(b)
 if h.hexdigest()!=expected_sha256:raise ValueError('snapshot pin mismatch')
 return json.loads(b''.join(parts),object_pairs_hook=no_duplicates,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))

def boundary_records(snapshot):
 if not isinstance(snapshot,dict) or snapshot.get('source')!='neon-export' or snapshot.get('schema')!='worldatlas-geography-decision-draft-evidence-v1' or snapshot.get('serialization')!='worldatlas-canonical-json-v1':raise ValueError('selected Neon combined export required')
 rev=snapshot.get('decision_revision');ent=snapshot.get('entity_revision')
 if not isinstance(rev,dict) or not isinstance(ent,dict) or rev.get('status')!='draft' or ent.get('status')!='draft' or not isinstance(rev.get('id'),str) or not rev['id'] or rev.get('entity_revision')!=ent.get('id'):raise ValueError('invalid decision/entity revision')
 sources=snapshot.get('sources');lineages=snapshot.get('source_lineage_assets');dependencies=snapshot.get('source_lineage_dependencies');items=snapshot.get('mainland_boundaries')
 if not isinstance(sources,list) or not isinstance(lineages,list) or not isinstance(dependencies,list) or not isinstance(items,list) or not items:raise ValueError('missing source/boundary records')
 def unique(xs):
  out={}
  for x in xs:
   if not isinstance(x,dict):raise ValueError('invalid source catalog item')
   key=(x.get('source_id'),x.get('version'))
   if not all(isinstance(v,str) and v for v in key) or key in out:raise ValueError('duplicate or invalid source key')
   out[key]=x
  return out
 catalog=unique(sources);lineage=unique(lineages);normalized={};source_out={};derived_keys=set()
 for dep in dependencies:
  if not isinstance(dep,dict) or not isinstance(dep.get('source_id'),str) or not isinstance(dep.get('version'),str):raise ValueError('invalid source dependency')
  derived_keys.add((dep['source_id'],dep['version']))
 for r in items:
  if not isinstance(r,dict):raise ValueError('invalid boundary record')
  bid=r.get('boundary_id');p=r.get('provenance')
  if not isinstance(bid,str) or not bid or ('boundary',bid) in normalized or r.get('execution_status')!='selected_for_research' or r.get('method')!='stored_linestring_v1' or r.get('coordinate_reference')!='OGC:CRS84' or r.get('geometry_hash_method')!='binary64-sorted-compact-geojson-v1' or not isinstance(p,dict):raise ValueError('invalid or duplicate selected boundary')
  if r.get('decision_revision')!=rev['id']:raise ValueError('missing or stale boundary revision')
  geom=r.get('geometry');v=points(geom);binary={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in v]}
  if geometry_hash(binary)!=r.get('geometry_sha256'):raise ValueError('stored boundary geometry hash mismatch')
  refs=p.get('source_refs');status=p.get('lineage_status')
  if not isinstance(refs,list) or not refs or status not in ('complete','incomplete'):raise ValueError('boundary lacks registered raw source references')
  relationships=p.get('source_relationships')
  if not isinstance(relationships,list) or len(relationships)!=len(refs):raise ValueError('boundary source relationships missing')
  relmap={}
  for item in relationships:
   if not isinstance(item,dict) or set(item)!={'source_id','version','relationship'}:raise ValueError('invalid boundary source relationship')
   key=(item['source_id'],item['version']);relationship=item['relationship']
   if key in relmap or relationship not in SUPPORTING_RELATIONSHIPS|{CONSTRUCTION_RELATIONSHIP}:raise ValueError('duplicate or unsupported boundary source relationship')
   relmap[key]=relationship
  clean=[]; qualified=[]; construction_count=0
  for ref in refs:
   if not isinstance(ref,dict) or set(ref)!={'source_id','version'}:raise ValueError('invalid boundary source reference')
   key=(ref['source_id'],ref['version']);src=catalog.get(key);lin=lineage.get(key)
   relationship=relmap.get(key)
   if not relationship or not src or not lin or key in derived_keys or lin.get('kind')!='raw' or not isinstance(lin.get('provider'),str) or not lin['provider'] or not isinstance(lin.get('source_uri'),str) or not lin['source_uri'] or any(src.get(k)!=lin.get(k) for k in ('sha256','r2_bucket','r2_key','size_bytes')) or not re.fullmatch('[0-9a-f]{64}',str(src.get('sha256'))) or not src.get('r2_bucket') or not src.get('r2_key') or type(src.get('size_bytes')) is not int or src['size_bytes']<=0:raise ValueError('boundary source is not pinned raw R2 asset')
   if relationship==CONSTRUCTION_RELATIONSHIP:
    prov=lin.get('provenance')
    if not isinstance(prov,dict) or not isinstance(prov.get('origin'),str) or not prov['origin'] or prov.get('representation') not in ('provider_original','provider_original_bundle'):raise ValueError('construction source is not an identified provider original')
    construction_count+=1
   clean.append(ref);qualified.append({**ref,'relationship':relationship,'role':'construction_input' if relationship==CONSTRUCTION_RELATIONSHIP else 'supporting_research_evidence'});source_out[key]={'kind':'raw','sha256':src['sha256'],'bucket':src['r2_bucket'],'key':src['r2_key'],'size_bytes':src['size_bytes'],'origin':(lin.get('provenance') or {}).get('origin')}
  if set(relmap)!={(x['source_id'],x['version']) for x in clean} or len(clean)!=len(relmap):raise ValueError('boundary source relationship mismatch')
  if status=='complete' and not construction_count:raise ValueError('complete lineage requires construction input')
  normalized[('boundary',bid)]={'id':bid,'kind':'boundary','revision_id':rev['id'],'execution_status':'selected_for_research','geometry':geom,'geometry_sha256':r['geometry_sha256'],'geometry_hash_method':r['geometry_hash_method'],'source_refs':clean,'qualified_source_refs':qualified,'lineage_status':status,'provenance':p}
 return rev['id'],ent['id'],normalized,source_out

def route_records(snapshot,revision_id,selected_route_ids,source_out):
 """Normalize explicitly selected stage-2 stored route geometries.

 Unknown route methods fail closed; this routine never generates ocean or sea
 routes, and only IDs selected by the mainland partition are consumed.
 """
 items=snapshot.get('routes')
 sources=snapshot.get('sources');lineages=snapshot.get('source_lineage_assets');dependencies=snapshot.get('source_lineage_dependencies')
 if not isinstance(source_out,dict) or not isinstance(sources,list) or not isinstance(lineages,list) or not isinstance(dependencies,list):raise ValueError('missing route raw-source catalog')
 def index(items):
  result={}
  for x in items:
   if not isinstance(x,dict):raise ValueError('invalid route source catalog item')
   key=(x.get('source_id'),x.get('version'))
   if not all(isinstance(v,str) and v for v in key) or key in result:raise ValueError('invalid or duplicate route source')
   result[key]=x
  return result
 catalog=index(sources);lineage=index(lineages);derived=set();selected_sources=set()
 if selected_route_ids:
  stage1=snapshot.get('stage1_source_inputs');ordinals={'physical_land':set(),'inland_water':set()}
  if not isinstance(stage1,list) or not stage1:raise ValueError('missing selected stage-1 source inputs')
  for item in stage1:
   if not isinstance(item,dict) or item.get('decision_revision')!=revision_id or item.get('execution_status')!='selected_for_research' or item.get('role') not in ordinals or type(item.get('ordinal')) is not int or item['ordinal']<0 or item['ordinal'] in ordinals[item['role']] or not isinstance(item.get('source_id'),str) or not isinstance(item.get('source_version'),str):raise ValueError('invalid selected stage-1 source input')
   ordinals[item['role']].add(item['ordinal']);selected_sources.add((item['source_id'],item['source_version']))
  if any(not nums or nums!=set(range(len(nums))) for nums in ordinals.values()):raise ValueError('incomplete selected stage-1 source roles')
 for dep in dependencies:
  if not isinstance(dep,dict) or not isinstance(dep.get('source_id'),str) or not isinstance(dep.get('version'),str):raise ValueError('invalid route source dependency')
  derived.add((dep['source_id'],dep['version']))
 if not isinstance(items,list) or not isinstance(selected_route_ids,list) or len(selected_route_ids)!=len(set(selected_route_ids)):raise ValueError('invalid selected route list')
 byid={}
 for r in items:
  if not isinstance(r,dict) or not isinstance(r.get('route_id'),str) or r['route_id'] in byid:raise ValueError('duplicate or invalid route ID')
  byid[r['route_id']]=r
 out={}
 for rid in selected_route_ids:
  r=byid.get(rid)
  if not r or r.get('decision_revision')!=revision_id or r.get('execution_status')!='selected_for_research' or r.get('route_type')!='stored_linestring_v1' or r.get('role')!='water_closure' or r.get('coordinate_reference')!='OGC:CRS84' or r.get('geometry_hash_method')!='binary64-sorted-compact-geojson-v1':raise ValueError('missing, stale or unsupported selected route')
  provenance=r.get('provenance');refs=provenance.get('source_refs') if isinstance(provenance,dict) else None
  if not isinstance(refs,list) or not refs:raise ValueError('route raw-source references missing')
  clean=[];seen=set()
  for ref in refs:
   if not isinstance(ref,dict) or set(ref)!={'source_id','version'}:raise ValueError('invalid route source reference')
   key=(ref['source_id'],ref['version']);src=catalog.get(key);lin=lineage.get(key)
   if key in seen or not src or not lin or key in derived or lin.get('kind')!='raw' or not isinstance(lin.get('provider'),str) or not lin['provider'] or not isinstance(lin.get('source_uri'),str) or not lin['source_uri'] or not isinstance(lin.get('provenance'),dict) or not isinstance(lin['provenance'].get('origin'),str) or not lin['provenance']['origin'] or any(src.get(k)!=lin.get(k) for k in ('sha256','r2_bucket','r2_key','size_bytes')) or not re.fullmatch('[0-9a-f]{64}',str(src.get('sha256'))) or not src.get('r2_bucket') or not src.get('r2_key') or type(src.get('size_bytes')) is not int or src['size_bytes']<=0:raise ValueError('route source is not pinned raw R2 asset')
   seen.add(key);clean.append(ref);source_out[key]={'kind':'raw','sha256':src['sha256'],'bucket':src['r2_bucket'],'key':src['r2_key'],'size_bytes':src['size_bytes'],'origin':lin['provenance']['origin']}
  if seen!=selected_sources:raise ValueError('route sources differ from selected stage-1 inputs')
  required_pins=('physical_rows_sha256','physical_runs_sha256','physical_report_sha256','encoding_evidence_sha256','checker_sha256','support_checker_sha256','contract_sha256')
  if provenance.get('lineage_status') not in ('complete','incomplete') or any(not re.fullmatch('[0-9a-f]{64}',str(provenance.get(k))) for k in required_pins):raise ValueError('invalid route physical provenance pins')
  g=r.get('geometry');v=points(g);binary={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in v]}
  if geometry_hash(binary)!=r.get('geometry_sha256'):raise ValueError('stored route geometry hash mismatch')
  method=r.get('closure_method')
  if method not in ('physical_water_closure_v1','physical_terminal_closure_v1'):raise ValueError('unsupported closure method')
  normalized={'id':rid,'kind':'route','role':r['role'],'revision_id':revision_id,'execution_status':'selected_for_research','geometry':g,'geometry_sha256':r['geometry_sha256'],'geometry_hash_method':r['geometry_hash_method'],'closure_method':method,'source_refs':clean,'lineage_status':provenance['lineage_status'],'provenance':provenance}
  if method=='physical_terminal_closure_v1':
   for side in ('start','end'):
    terminal=r.get(side+'_terminal')
    if not isinstance(terminal,dict) or set(terminal)!={'boundary_id','endpoint'} or not isinstance(terminal['boundary_id'],str) or not terminal['boundary_id'] or terminal['endpoint'] not in ('start','end'):raise ValueError('invalid selected closure terminal')
    normalized[side+'_terminal']=terminal
  out[('route',rid)]=normalized
 return out

def selected_regions(snapshot,revision_id,normalized_boundaries,source_catalog):
 policy=snapshot.get('land_baseline_policy');items=snapshot.get('seed_regions')
 if not isinstance(policy,dict) or policy.get('execution_status')!='selected_for_research' or policy.get('decision_revision')!=revision_id or policy.get('island_overrides')!='none' or not isinstance(items,list):raise ValueError('missing simple baseline region policy')
 ids=policy.get('region_ids');boundary_ids=policy.get('boundary_ids');route_ids=policy.get('route_ids')
 if any(not isinstance(x,list) or len(x)!=len(set(x)) for x in (ids,boundary_ids,route_ids)):raise ValueError('invalid selected geometry IDs')
 byid={}
 for r in items:
  if not isinstance(r,dict) or not isinstance(r.get('region_id'),str) or r['region_id'] in byid:raise ValueError('duplicate or invalid region ID')
  byid[r['region_id']]=r
 if set(boundary_ids)!={x[1] for x in normalized_boundaries}:raise ValueError('selected boundary set mismatch')
 routes=route_records(snapshot,revision_id,route_ids,source_catalog);out=[];used_b=set();used_r=set()
 for rid in ids:
  r=byid.get(rid);required={'region_id','decision_revision','execution_status','segments','geometry_sha256','geometry_hash_method','witnesses'}
  if not r or set(r)!=required or r['decision_revision']!=revision_id or r['execution_status']!='selected_for_research' or r['geometry_hash_method']!='binary64-sorted-compact-geojson-v1' or not isinstance(r['segments'],list) or not r['segments'] or not isinstance(r['witnesses'],list):raise ValueError('invalid selected region')
  for segment in r['segments']:
   if not isinstance(segment,dict) or set(segment)!={'kind','id','start','end','reverse'}:raise ValueError('invalid selected region segment')
   key=(segment['kind'],segment['id'])
   if key in normalized_boundaries:used_b.add(segment['id'])
   elif key in routes:used_r.add(segment['id'])
   else:raise ValueError('region references unselected geometry')
  out.append({'region_id':rid,'revision_id':revision_id,'execution_status':r['execution_status'],'segments':r['segments'],'geometry_sha256':r['geometry_sha256'],'geometry_hash_method':r['geometry_hash_method'],'witnesses':r['witnesses']})
 if used_b!=set(boundary_ids) or used_r!=set(route_ids):raise ValueError('selected boundary or route not consumed')
 return out,{**normalized_boundaries,**routes}
