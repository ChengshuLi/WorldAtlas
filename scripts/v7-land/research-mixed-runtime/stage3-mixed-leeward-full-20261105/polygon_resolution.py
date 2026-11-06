"""Resolve selected raw-source polygon decisions to current component roots.

Library entry point only: caller authenticates Neon/revision/category and the
same-generation component manifest, pins/rechecks code and supervises a process
group with bounded RSS, host memory, disk and time. No V7 grid is an input.
"""
import polygon_loader,polygon_intersection,writer,full_coverage_policy

def need(v,m):
 if not v:raise ValueError(m)
def resolve(policy,snapshot,source_files,grid,inputs,guard,coverage_index=None):
 need(isinstance(policy,dict) and policy.get('schema')=='stage3-polygon-decisions-v1' and policy.get('status')=='requires-source-resolution' and policy.get('revision')==snapshot.get('decision_revision',{}).get('id'),'invalid polygon policy')
 names=('physical_rows','physical_runs','component_rows','component_runs');need(isinstance(inputs,dict) and set(inputs)==set(names) and isinstance(source_files,list),'invalid polygon inputs')
 def key(s):return (s.get('source_id'),s.get('version'))
 sources={key(s):s for s in source_files};expected={key(s):s for s in policy['source_pins']};need(len(sources)==len(source_files) and len(expected)==len(policy['source_pins']) and set(sources)==set(expected),'polygon source set mismatch')
 for k,s in sources.items():need(all(s.get(x)==expected[k].get(x) for x in ('sha256','size_bytes')) and writer.sha(s['path'],guard)==s['sha256'],'source pin mismatch')
 for x in names:need(writer.sha(inputs[x]['path'],guard)==inputs[x]['sha256'],'stream pin mismatch')
 containment_methods={'component_containment_v1','osm_archipelago_component_containment_v1'}
 if coverage_index is None and any(d.get('method') in containment_methods for d in policy['decisions']):
  coverage_index=full_coverage_policy.build_coverage_index(grid,*(inputs[x]['path'] for x in names),guard)
 categories={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'};claims=[]
 for d in policy['decisions']:
  guard();geometries=[];traces=[]
  for f in d['features']:
   s=sources[(f['source_id'],f['source_version'])];geometry,trace=polygon_loader.extract(f,s,guard);geometries.append(geometry);traces.append({'feature_id':f['feature_id'],'source_id':f['source_id'],'source_version':f['source_version'],**trace})
  roots,trace=polygon_intersection.intersect(geometries,grid,*(inputs[x]['path'] for x in names),d['include_witnesses'],d['exclude_witnesses'],guard)
  containment=None
  if d['method'] in ('component_containment_v1','osm_archipelago_component_containment_v1'):
   need(len(geometries)==1 and geometries[0].get('type')==('MultiPolygon' if d['method']=='osm_archipelago_component_containment_v1' else 'Polygon') and not d['include_witnesses'] and not d['exclude_witnesses'] and len(trace['per_feature_root_inside_cells'])==1,'invalid containment polygon')
   hits=trace['per_feature_root_inside_cells'][0];need(set(map(str,roots))==set(hits),'containment root/hit mismatch');roots,containment=full_coverage_policy.select_all_centers(hits,grid,*(inputs[x]['path'] for x in names),guard,coverage_index=coverage_index)
  code=categories.get(d['entity_id']);need(type(code) is int and 17<=code<=22,'invalid polygon target')
  claims.append({'affiliation_id':d['affiliation_id'],'entity_id':d['entity_id'],'entity_code':code,'method':d['method'],'component_ids':roots,'source_features':traces,'intersection':trace,'decision_limitations':d['decision_limitations'],**({'exclusion_witness_assertion':d['exclusion_witness_assertion']} if 'exclusion_witness_assertion' in d else {}),**({'containment':containment} if containment is not None else {})})
 for k,s in sources.items():need(writer.sha(s['path'],guard)==s['sha256'],'source changed')
 for x in names:need(writer.sha(inputs[x]['path'],guard)==inputs[x]['sha256'],'stream changed')
 return {'schema':'source-polygon-component-report-v1','status':'research-only-not-a-build','revision':policy['revision'],'entity_revision':snapshot['entity_revision']['id'],'grid':grid,'input_sha256':{x:inputs[x]['sha256'] for x in names},'claims':claims,'limitations':['Source capture/custody assertions require independent authentication.','A polygon intersecting a physical component does not alone establish whole-island identity.','Current-generation roots cannot be reused with a different physical/component generation.']}
