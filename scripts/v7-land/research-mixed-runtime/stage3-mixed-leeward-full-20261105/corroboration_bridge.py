"""Resolve revision-bound corroboration from authenticated raw sources.

Caller must preverify all imported code, authenticate snapshot/compiled policy
and streams before/after, supervise resources and apply mainland/conflict guards.
The result is evidence only; it never changes, selects or excludes roots.
"""
import hashlib,re
from pathlib import Path
import corroboration_adapter as adapter,corroboration_source as source,corroboration_evaluate as evaluate

def need(v,m):
 if not v:raise ValueError(m)
def filehash(p,guard):
 h=hashlib.sha256();total=0
 with p.open('rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   total+=len(b);need(total<=16<<20,'administrative source limit');h.update(b)
 return total,h.hexdigest()
def resolve(snapshot,polygon_policy,polygon_resolution,source_files,grid,inputs,input_sha256,guard):
 need(callable(guard),'guard required');policy=adapter.adapt(snapshot,polygon_policy);pins={(s['source_id'],s['version']):s for s in policy['source_pins']};need(isinstance(source_files,list) and len(source_files)==len(pins),'source file set mismatch');files={}
 for f in source_files:
  need(isinstance(f,dict) and set(f)=={'path','source_id','version','sha256','size_bytes','r2_bucket','r2_key'},'invalid source file');key=(f['source_id'],f['version']);pin=pins.get(key);need(key not in files and isinstance(pin,dict) and all(f[k]==pin[k] for k in ('sha256','size_bytes','r2_bucket','r2_key')),'source pin mismatch');p=Path(f['path']).resolve(strict=True);need(p.is_file() and filehash(p,guard)==(f['size_bytes'],f['sha256']),'source bytes mismatch');files[key]=p
 need(set(files)==set(pins),'source files missing');admin={};source_traces=[]
 for key in sorted(pins):
  ds=[{k:f[k] for k in ('feature_id','source_feature_id','name','geometry_sha256','geometry_hash_method')} for f in policy['features'] if (f['source_id'],f['source_version'])==key];need(ds,'unconsumed source');extracted,trace=source.extract(files[key],pins[key]['sha256'],ds,source.METHOD,guard);need(len(extracted)==len(ds),'source feature mismatch')
  for f in extracted.values():need(f['feature_id'] not in admin,'duplicate administrative feature');admin[f['feature_id']]=f
  source_traces.append({'source_id':key[0],'version':key[1],**trace})
 input_keys={'physical_rows','physical_runs','component_rows','component_runs'};need(isinstance(input_sha256,dict) and set(input_sha256)==input_keys and all(isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) for x in input_sha256.values()),'invalid stream pins')
 need(isinstance(polygon_resolution,dict) and polygon_resolution.get('schema')=='source-polygon-component-report-v1' and polygon_resolution.get('status')=='research-only-not-a-build' and polygon_resolution.get('revision')==policy['revision'] and isinstance(snapshot.get('entity_revision'),dict) and polygon_resolution.get('entity_revision')==snapshot['entity_revision'].get('id') and polygon_resolution.get('grid')==grid and polygon_resolution.get('input_sha256')==input_sha256 and isinstance(polygon_resolution.get('claims'),list),'invalid polygon resolution');claims={}
 for claim in polygon_resolution['claims']:
  aid=claim.get('affiliation_id') if isinstance(claim,dict) else None;need(isinstance(aid,str) and aid not in claims,'duplicate resolved affiliation');claims[aid]=claim
 groups={}
 for row in policy['mappings']:groups.setdefault(row['affiliation_id'],[]).append({'selected_feature_id':row['selected_feature_id'],'administrative_feature_ids':row['administrative_feature_ids']})
 decisions={d['affiliation_id']:d for d in polygon_policy['decisions']};polygon_sources={(s['source_id'],s['version']):s for s in polygon_policy['source_pins']};bindings={b['entity_id']:b['code'] for b in snapshot.get('category_bindings',[]) if b.get('physical_class')=='land'}
 results=[]
 for aid,associations in sorted(groups.items()):
  claim=claims.get(aid);decision=decisions.get(aid);need(isinstance(claim,dict) and isinstance(decision,dict) and claim.get('method')==decision.get('method')=='component_intersection_v1' and type(decision.get('entity_id')) is int and decision['entity_id'] in bindings and claim.get('entity_id')==decision.get('entity_id') and claim.get('entity_code')==bindings[decision['entity_id']],'unresolved or misbound corroborated affiliation')
  expected=decision.get('features');traces=claim.get('source_features');need(isinstance(expected,list) and isinstance(traces,list) and len(expected)==len(traces),'source trace set mismatch')
  for f,t in zip(expected,traces):
   need(isinstance(f,dict) and isinstance(t,dict) and all(t.get(k)==f.get(k) for k in ('feature_id','source_id','source_version','geometry_sha256')),'source trace mismatch');pin=polygon_sources.get((f.get('source_id'),f.get('source_version')));need(isinstance(pin,dict) and t.get('source_sha256')==pin.get('sha256'),'source trace hash mismatch')
  used={x for a in associations for x in a['administrative_feature_ids']};results.append(evaluate.evaluate(claim,associations,{k:admin[k] for k in used},grid,inputs,guard))
 for key,p in files.items():need(filehash(p,guard)==(pins[key]['size_bytes'],pins[key]['sha256']),'administrative source changed')
 return {'schema':'administrative-corroboration-bridge-v1','revision':policy['revision'],'status':'research-evidence-not-a-selector','policy':policy,'source_traces':source_traces,'affiliations':results,'limitations':['Provider origin, coordinate order and feature-to-municipality links are selected assertions.','Counts do not prove island identity and do not change selected components.']}
