"""Resolve selected raw-source polygon decisions to current component roots.

Library entry point only: caller authenticates Neon/revision/category and the
same-generation component manifest, pins/rechecks code and supervises a process
group with bounded RSS, host memory, disk and time. No V7 grid is an input.
"""
import json
from osgeo import ogr
import polygon_loader,polygon_intersection,writer,full_coverage_policy,negative_component_filter

def need(v,m):
 if not v:raise ValueError(m)
def prefetch_land_features(decisions,sources,guard):
 # Extract every unique archive feature once per authenticated source. The
 # extractor hashes the archive and its materialized members before and after
 # extraction. The resolver rehashes each source again before it returns.
 groups={}
 for decision in decisions:
  fs=decision['features'];keys=[(f['source_id'],f['source_version']) for f in fs];ids=[f.get('source_feature_id') for f in fs]
  # Preserve the existing per-feature behavior when a decision repeats a FID.
  if len(set(zip(keys,ids)))!=len(fs):continue
  for feature in fs:
   if feature.get('extractor_version')!='osm-split-land-archive-v1' or feature.get('source_format')!='osm-split-land-shapefile':continue
   key=(feature['source_id'],feature['source_version']);fid=feature['source_feature_id'];group=groups.setdefault(key,{})
   if fid in group:need(group[fid].get('geometry_sha256')==feature.get('geometry_sha256'),'conflicting geometry pins for archive feature')
   else:group[fid]=feature
 result={}
 for key,features in groups.items():
  values=list(features.values())
  # The trusted extractor limits each request to 1000 features.
  for offset in range(0,len(values),1000):
   chunk=values[offset:offset+1000]; extracted=polygon_loader.extract_land_many(chunk,sources[key],guard)
   need(len(extracted)==len(chunk),'polygon feature extraction count mismatch')
   for feature,value in zip(chunk,extracted):result[(key,feature['source_feature_id'])]=value
 return result
def resolve(policy,snapshot,source_files,grid,inputs,guard):
 need(isinstance(policy,dict) and policy.get('schema')=='stage3-polygon-decisions-v1' and policy.get('status')=='requires-source-resolution' and policy.get('revision')==snapshot.get('decision_revision',{}).get('id'),'invalid polygon policy')
 names=('physical_rows','physical_runs','component_rows','component_runs');need(isinstance(inputs,dict) and set(inputs)==set(names) and isinstance(source_files,list),'invalid polygon inputs')
 def key(s):return (s.get('source_id'),s.get('version'))
 sources={key(s):s for s in source_files};expected={key(s):s for s in policy['source_pins']};need(len(sources)==len(source_files) and len(expected)==len(policy['source_pins']) and set(sources)==set(expected),'polygon source set mismatch')
 for k,s in sources.items():need(all(s.get(x)==expected[k].get(x) for x in ('sha256','size_bytes')) and writer.sha(s['path'],guard)==s['sha256'],'source pin mismatch')
 for x in names:need(writer.sha(inputs[x]['path'],guard)==inputs[x]['sha256'],'stream pin mismatch')
 land_features=prefetch_land_features(policy['decisions'],sources,guard)
 categories={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'};claims=[]
 coverage_index=None
 def all_centers(hits):
  nonlocal coverage_index
  if coverage_index is None:coverage_index=full_coverage_policy.build_coverage_index(grid,*(inputs[x]['path'] for x in names),guard)
  return full_coverage_policy.select_all_centers(hits,grid,*(inputs[x]['path'] for x in names),guard,coverage_index=coverage_index)
 for d in policy['decisions']:
  guard();geometries=[];traces=[]
  fs=d['features'];keys=[(f['source_id'],f['source_version']) for f in fs];ids=[f.get('source_feature_id') for f in fs]
  use_cache=len(set(zip(keys,ids)))==len(fs)
  extracted=[land_features[(k,f['source_feature_id'])] if use_cache and f.get('extractor_version')=='osm-split-land-archive-v1' and f.get('source_format')=='osm-split-land-shapefile' else polygon_loader.extract(f,sources[k],guard) for f,k in zip(fs,keys)]
  need(len(extracted)==len(fs),'polygon feature extraction count mismatch')
  for f,(geometry,trace) in zip(fs,extracted):geometries.append(geometry);traces.append({'feature_id':f['feature_id'],'source_id':f['source_id'],'source_version':f['source_version'],**trace})
  source_exclusion=d['method']=='component_containment_excluding_source_v1'
  if source_exclusion:
   need(len(geometries)==2 and geometries[0].get('type') in ('Polygon','MultiPolygon') and geometries[1].get('type')=='Polygon' and not d['include_witnesses'] and not d['exclude_witnesses'],'invalid source-negative geometry')
   positive=geometries[:1]
  else:positive=geometries
  split=d['method'] in ('component_containment_v1','component_containment_excluding_source_v1') and len(positive)==1 and positive[0].get('type')=='MultiPolygon'
  if split:
   original=ogr.CreateGeometryFromJson(json.dumps(positive[0],allow_nan=False));need(original is not None and not original.IsEmpty() and original.IsValid(),'invalid multipolygon')
   parts=[{'type':'Polygon','coordinates':coords} for coords in positive[0]['coordinates']];need(0<len(parts)<=1000,'invalid multipolygon part count')
   roots,trace=polygon_intersection.intersect(parts,grid,*(inputs[x]['path'] for x in names),d['include_witnesses'],d['exclude_witnesses'],guard,allow_empty_features=True)
   totals={}
   for counts in trace['per_feature_root_inside_cells']:
    for root,n in counts.items():totals[root]=totals.get(root,0)+n
   trace['multipolygon_part_count']=len(parts);trace['multipolygon_part_components']=trace['per_feature_components'][:];trace['per_feature_components']=[len(roots)];trace['per_feature_root_inside_cells']=[totals]
  else:roots,trace=polygon_intersection.intersect(positive,grid,*(inputs[x]['path'] for x in names),d['include_witnesses'],d['exclude_witnesses'],guard)
  containment=None;negative_trace=None;negative_decision=None
  if d['method'] in ('component_containment_v1','component_containment_excluding_source_v1','osm_reef_envelope_component_containment_v1','osm_archipelago_component_containment_v1','osm_way_component_containment_v1','osm_relation_component_containment_v1','osm_land_archive_component_containment_v1'):
   need(len(positive)==1 and (positive[0].get('type') in ('Polygon','MultiPolygon') if d['method'] in ('component_containment_v1','component_containment_excluding_source_v1') else positive[0].get('type')=='Polygon' if d['method']=='osm_land_archive_component_containment_v1' else positive[0].get('type')=='MultiPolygon') and not d['include_witnesses'] and not d['exclude_witnesses'] and len(trace['per_feature_root_inside_cells'])==1,'invalid containment polygon')
   hits=trace['per_feature_root_inside_cells'][0];need(set(map(str,roots))==set(hits),'containment root/hit mismatch');roots,containment=all_centers(hits)
   if source_exclusion:
    containment['stage']='positive_full_center_before_exclusion'
    negative,negative_trace=polygon_intersection.intersect([geometries[1]],grid,*(inputs[x]['path'] for x in names),[],[],guard)
    negative_decision=negative_component_filter.exclude_footprint(roots,negative);need(negative_decision['selected_roots'] and negative_decision['excluded_roots'],'empty source exclusion or selection');roots=negative_decision['selected_roots']
  if d['method']=='osm_admin_group_containment_v1':
   need(len(positive)==2 and all(x.get('type') in ('Polygon','MultiPolygon') for x in positive) and not d['include_witnesses'] and not d['exclude_witnesses'] and len(trace['per_feature_root_inside_cells'])==2,'invalid two-source containment')
   hits=trace['per_feature_root_inside_cells'];first,first_audit=all_centers(hits[0]);second,second_audit=all_centers(hits[1]);roots=sorted(set(first)&set(second));need(roots,'empty two-source containment');containment={'policy':'all-centers-within-both-sources-v1','administrative':first_audit,'geographic_group':second_audit,'selected_count':len(roots),'limitations':['Both sources constrain all current component centers; neither proves a coastline or named-island identity.']}
  code=categories.get(d['entity_id']);need(type(code) is int and 17<=code<=22,'invalid polygon target')
  claims.append({'affiliation_id':d['affiliation_id'],'entity_id':d['entity_id'],'entity_code':code,'method':d['method'],'component_ids':roots,'source_features':traces,'intersection':trace,'decision_limitations':d['decision_limitations'],**({'source_negative_intersection':negative_trace,'source_negative_filter':negative_decision} if source_exclusion else {}),**({'exclusion_witness_assertion':d['exclusion_witness_assertion']} if 'exclusion_witness_assertion' in d else {}),**({'containment':containment} if containment is not None else {})})
 for k,s in sources.items():need(writer.sha(s['path'],guard)==s['sha256'],'source changed')
 for x in names:need(writer.sha(inputs[x]['path'],guard)==inputs[x]['sha256'],'stream changed')
 return {'schema':'source-polygon-component-report-v1','status':'research-only-not-a-build','revision':policy['revision'],'entity_revision':snapshot['entity_revision']['id'],'grid':grid,'input_sha256':{x:inputs[x]['sha256'] for x in names},'claims':claims,'limitations':['Source capture/custody assertions require independent authentication.','A polygon intersecting a physical component does not alone establish whole-island identity.','Current-generation roots cannot be reused with a different physical/component generation.']}
