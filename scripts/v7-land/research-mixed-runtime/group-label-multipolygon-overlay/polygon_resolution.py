"""Resolve selected raw-source polygon decisions to current component roots.

Library entry point only: caller authenticates Neon/revision/category and the
same-generation component manifest, pins/rechecks code and supervises a process
group with bounded RSS, host memory, disk and time. No V7 grid is an input.
"""
import json
from osgeo import ogr
import polygon_loader,polygon_intersection,writer,full_coverage_policy

def need(v,m):
 if not v:raise ValueError(m)
def resolve(policy,snapshot,source_files,grid,inputs,guard):
 need(isinstance(policy,dict) and policy.get('schema')=='stage3-polygon-decisions-v1' and policy.get('status')=='requires-source-resolution' and policy.get('revision')==snapshot.get('decision_revision',{}).get('id'),'invalid polygon policy')
 names=('physical_rows','physical_runs','component_rows','component_runs');need(isinstance(inputs,dict) and set(inputs)==set(names) and isinstance(source_files,list),'invalid polygon inputs')
 def key(s):return (s.get('source_id'),s.get('version'))
 sources={key(s):s for s in source_files};expected={key(s):s for s in policy['source_pins']};need(len(sources)==len(source_files) and len(expected)==len(policy['source_pins']) and set(sources)==set(expected),'polygon source set mismatch')
 for k,s in sources.items():need(all(s.get(x)==expected[k].get(x) for x in ('sha256','size_bytes')) and writer.sha(s['path'],guard)==s['sha256'],'source pin mismatch')
 for x in names:need(writer.sha(inputs[x]['path'],guard)==inputs[x]['sha256'],'stream pin mismatch')
 categories={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'};claims=[]
 for d in policy['decisions']:
  guard();geometries=[];traces=[]
  fs=d['features'];keys=[(f['source_id'],f['source_version']) for f in fs];ids=[f.get('source_feature_id') for f in fs]
  if len(fs)>1 and len(set(keys))==1 and len(set(ids))==len(ids) and all(f.get('extractor_version')=='osm-split-land-archive-v1' and f.get('source_format')=='osm-split-land-shapefile' for f in fs):
   extracted=polygon_loader.extract_land_many(fs,sources[keys[0]],guard)
  else:extracted=[polygon_loader.extract(f,sources[k],guard) for f,k in zip(fs,keys)]
  need(len(extracted)==len(fs),'polygon feature extraction count mismatch')
  for f,(geometry,trace) in zip(fs,extracted):geometries.append(geometry);traces.append({'feature_id':f['feature_id'],'source_id':f['source_id'],'source_version':f['source_version'],**trace})
  split=d['method']=='component_containment_v1' and len(geometries)==1 and geometries[0].get('type')=='MultiPolygon'
  if split:
   original=ogr.CreateGeometryFromJson(json.dumps(geometries[0],allow_nan=False));need(original is not None and not original.IsEmpty() and original.IsValid(),'invalid multipolygon')
   parts=[{'type':'Polygon','coordinates':coords} for coords in geometries[0]['coordinates']];need(0<len(parts)<=1000,'invalid multipolygon part count')
   roots,trace=polygon_intersection.intersect(parts,grid,*(inputs[x]['path'] for x in names),d['include_witnesses'],d['exclude_witnesses'],guard)
   totals={}
   for counts in trace['per_feature_root_inside_cells']:
    for root,n in counts.items():totals[root]=totals.get(root,0)+n
   trace['multipolygon_part_count']=len(parts);trace['per_feature_components']=[len(roots)];trace['per_feature_root_inside_cells']=[totals]
  else:roots,trace=polygon_intersection.intersect(geometries,grid,*(inputs[x]['path'] for x in names),d['include_witnesses'],d['exclude_witnesses'],guard)
  containment=None
  if d['method'] in ('component_containment_v1','osm_archipelago_component_containment_v1','osm_way_component_containment_v1','osm_relation_component_containment_v1'):
   need(len(geometries)==1 and (geometries[0].get('type') in ('Polygon','MultiPolygon') if d['method']=='component_containment_v1' else geometries[0].get('type')=='MultiPolygon') and not d['include_witnesses'] and not d['exclude_witnesses'] and len(trace['per_feature_root_inside_cells'])==1,'invalid containment polygon')
   hits=trace['per_feature_root_inside_cells'][0];need(set(map(str,roots))==set(hits),'containment root/hit mismatch');roots,containment=full_coverage_policy.select_all_centers(hits,grid,*(inputs[x]['path'] for x in names),guard)
  code=categories.get(d['entity_id']);need(type(code) is int and 17<=code<=22,'invalid polygon target')
  claims.append({'affiliation_id':d['affiliation_id'],'entity_id':d['entity_id'],'entity_code':code,'method':d['method'],'component_ids':roots,'source_features':traces,'intersection':trace,'decision_limitations':d['decision_limitations'],**({'exclusion_witness_assertion':d['exclusion_witness_assertion']} if 'exclusion_witness_assertion' in d else {}),**({'containment':containment} if containment is not None else {})})
 for k,s in sources.items():need(writer.sha(s['path'],guard)==s['sha256'],'source changed')
 for x in names:need(writer.sha(inputs[x]['path'],guard)==inputs[x]['sha256'],'stream changed')
 return {'schema':'source-polygon-component-report-v1','status':'research-only-not-a-build','revision':policy['revision'],'entity_revision':snapshot['entity_revision']['id'],'grid':grid,'input_sha256':{x:inputs[x]['sha256'] for x in names},'claims':claims,'limitations':['Source capture/custody assertions require independent authentication.','A polygon intersecting a physical component does not alone establish whole-island identity.','Current-generation roots cannot be reused with a different physical/component generation.']}
