"""Fresh two-source Bering resolution bridge. Caller authenticates all inputs.

No historic/reference root selections. All returned root IDs are ephemeral and
must be re-resolved for each physical/component generation.
"""
import hashlib
from pathlib import Path
import bering_resolver

def need(v,m):
 if not v:raise ValueError(m)
def protected_roots(baseline,stage2,request,resolution,resolution_sha):
 need(isinstance(resolution,dict) and resolution.get('schema')=='mainland-witness-resolution-v1' and resolution.get('status')=='selected-research-identity-claims-not-mainland-proof' and stage2.get('resolution_report_sha256')==resolution_sha,'invalid protected witness report')
 need(resolution.get('snapshot_sha256')==request['baseline_snapshot_sha256'] and resolution.get('decision_revision')==baseline['decision_revision']['id'] and resolution.get('entity_revision')==baseline['entity_revision']['id'] and resolution.get('component_manifest_sha256')==request['component_manifest_sha256'] and resolution.get('input_sha256')==request['input_sha256'] and resolution.get('grid')==request['grid'],'protected witness provenance mismatch')
 def unique(rows,key):
  need(isinstance(rows,list) and rows,'missing protected rows');out={}
  for row in rows:
   need(isinstance(row,dict) and isinstance(row.get(key),str) and row[key] and row[key] not in out,'duplicate protected row');out[row[key]]=row
  return out
 groups=unique(baseline.get('mainland_witness_groups'),'group_id');results=unique(resolution.get('groups'),'group_id');witnesses=unique(baseline.get('mainland_witnesses'),'witness_id');observed=unique(resolution.get('witnesses'),'witness_id');need(set(groups)==set(results) and set(witnesses)==set(observed),'protected group/witness coverage mismatch');roots=set(stage2.get('physical_coverage',{}).get('seed_roots',[]));need(roots and all(type(x) is int and 0<=x<0xffffffff for x in roots),'invalid mainland roots')
 for gid,g in groups.items():
  r=results[gid];ids=g.get('witness_ids');need(g.get('decision_revision')==baseline['decision_revision']['id'] and g.get('execution_status')=='selected_for_research' and g.get('role') in ('mainland','sentinel') and r.get('role')==g['role'] and r.get('target_entity_ids')==g.get('target_entity_ids') and isinstance(ids,list) and ids and len(ids)==len(set(ids)) and {w for w,x in observed.items() if x.get('group_id')==gid}==set(ids),'protected group mismatch');root=r.get('component_id_current_generation_only');need(type(root) is int and 0<=root<0xffffffff,'invalid protected root');roots.add(root)
  for wid in ids:
   v=witnesses.get(wid);o=observed.get(wid);need(isinstance(v,dict) and isinstance(o,dict) and v.get('decision_revision')==baseline['decision_revision']['id'] and v.get('execution_status')=='selected_for_research' and v.get('group_id',gid)==gid and all(v.get(k)==o.get(k) for k in ('point_feature_id','identity_feature_id')),'protected witness mismatch')
 return roots

def resolve(policy,snapshot,source_files,inputs,grid,protected,guard,profiler,extractor,reader):
 need(isinstance(policy,dict) and policy.get('schema')=='stage3-label-ecoregion-research-decisions-v1' and policy.get('status')=='requires-source-resolution' and policy.get('revision')==snapshot.get('decision_revision',{}).get('id') and isinstance(policy.get('decisions'),list),'invalid Bering policy')
 need(isinstance(source_files,list) and len(source_files)<=2000,'invalid Bering source files');files={}
 for s in source_files:
  need(isinstance(s,dict) and set(s)=={'source_id','version','path','sha256','size_bytes'} and isinstance(s['source_id'],str) and isinstance(s['version'],str) and isinstance(s['path'],str) and type(s['size_bytes']) is int and s['size_bytes']>0,'invalid Bering source file');k=(s['source_id'],s['version']);need(k not in files,'duplicate Bering source');files[k]=s
 expected={}
 for d in policy['decisions']:
  for role in ('label','ecoregion'):
   src=d[role]['source'];k=(src['source_id'],src['version']);need(k not in expected or expected[k]==src,'source description conflict');expected[k]=src
 need(set(files)==set(expected),'Bering source file set mismatch')
 for k,s in files.items():need(all(s[a]==expected[k][a] for a in ('sha256','size_bytes')),'Bering source pin mismatch')
 need(isinstance(inputs,dict) and set(inputs)=={'physical_rows','physical_runs','component_rows','component_runs'},'invalid physical inputs');converted={}
 for k,s in inputs.items():
  need(isinstance(s,dict) and set(s)=={'path','sha256'},'invalid stream pin');p=Path(s['path']).resolve(strict=True);need(p.is_file(),'missing physical stream');converted[k]={**s,'size_bytes':p.stat().st_size}
 bindings={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'};claims=[];details=[]
 for d in policy['decisions']:
  guard();data={**converted}
  for role in ('label','ecoregion'):
   s=d[role]['source'];v=files[(s['source_id'],s['version'])];data[role]={k:v[k] for k in ('path','sha256','size_bytes')}
  r=bering_resolver.resolve(d,data,grid,protected,{},guard,profiler,extractor,reader);roots=[x['component_id'] for x in r['claims']];need(roots and len(roots)==len(set(roots)),'empty or duplicate Bering roots');code=bindings.get(d['entity_id']);need(type(code) is int and 17<=code<=22,'invalid Bering target');claims.append({'affiliation_id':d['affiliation_id'],'entity_id':d['entity_id'],'entity_code':code,'method':d['method'],'component_ids':roots});details.append({'affiliation_id':d['affiliation_id'],'resolution':r})
 return {'schema':'source-label-ecoregion-component-report-v1','status':'research-only-not-a-build','revision':policy['revision'],'entity_revision':snapshot['entity_revision']['id'],'grid':grid,'input_sha256':{k:v['sha256'] for k,v in inputs.items()},'policy':policy,'claims':claims,'details':details,'limitations':['Source center containment and coarse EPA contact do not prove whole-root island identity.','Operation bounding boxes do not establish exact operation-area applicability.','Source custody and lineage must be authenticated and rechecked by the caller.']}
