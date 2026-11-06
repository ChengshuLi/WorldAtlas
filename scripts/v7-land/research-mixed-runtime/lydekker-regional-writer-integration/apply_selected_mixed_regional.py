#!/usr/bin/env python3
"""Build a source-resolved land-only List 1 overlay. No reference-map input.

A process-group watchdog must supervise this worker; output is research-only
until its monitor is verified. Unselected or unsupported methods fail closed.
"""
import argparse,hashlib,importlib.util,json,os,sys,shutil,tempfile
from pathlib import Path
import decision_contract,writer,polygon_policy,polygon_resolution,mixed_claims,polygon_loader,polygon_source,entry_evidence,corroboration_bridge,bering_adapter,bering_resolver,bering_bridge,bering_profiler,bering_intersection
HERE=Path(__file__).resolve().parent
POINT=HERE.parent/'geonames-point-integration-20261105/point-component-prototype'
POINT_VALIDATOR=HERE.parent/'geonames-point-claim-validator-20261105/point_claim_validator.py'
POINT_METHODS={'source_point_component_v1','source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1','geonames_zip_island_named_region_component_v1','geonames_zip_named_list1_component_v1','geonames_zip_line_side_component_v1','geonames_zip_airport_named_region_component_v1'}
STAGE2=HERE.parent/'stage2-geodesic-20261104'

def need(v,m):
 if not v: raise ValueError(m)
def read(path,limit=16<<20):
 with open(path,'rb') as f:b=f.read(limit+1)
 need(len(b)<=limit,'input exceeds limit');return json.loads(b)
def available():
 with open('/proc/meminfo') as f:
  for line in f:
   if line.startswith('MemAvailable:'):return int(line.split()[1])
 raise RuntimeError('memory unavailable')
def loadmodule(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify_bering_source_paths(files,others,corroboration):
 paths={}
 for f in files:
  need(isinstance(f,dict) and all(k in f for k in ('path','source_id','version','sha256','size_bytes')),'invalid Bering source path');p=Path(f['path']).resolve(strict=True);need(p not in paths,'duplicate Bering source path');paths[p]=f
 protected={Path(f['path']).resolve(strict=True) for f in corroboration};need(not (set(paths)&protected),'Bering and corroboration sources overlap')
 for f in others:
  p=Path(f['path']).resolve(strict=True)
  if p in paths:need(all(paths[p].get(k)==f.get(k) for k in ('source_id','version','sha256','size_bytes')),'source path identity conflict')
def validate_admin_group_extent(method, per, whole):
 if method=='osm_admin_group_containment_v1':
  need(type(whole) is int and whole>0 and isinstance(per,list) and len(per)==2 and all(type(x.get('inside_cells')) is int and x['inside_cells']==whole and type(x.get('outside_cells')) is int and x['outside_cells']==0 for x in per),'dual-source whole-component extent mismatch')

def positive_extent_features(claim):
 """Pair positive features with positive intersections, separately verifying a source exclusion."""
 features=claim['source_features'];counts=claim['intersection']['per_feature_root_inside_cells']
 if claim['method']=='component_containment_excluding_source_v1':
  need(len(features)==2 and len(counts)==1 and features[0]['feature_id']!=features[1]['feature_id'],'invalid source-negative feature counts')
  negative=claim['source_negative_intersection']['per_feature_root_inside_cells'];filt=claim['source_negative_filter'];contain=claim['containment'];need(len(negative)==1 and isinstance(negative[0],dict) and isinstance(counts[0],dict),'invalid source-negative intersection')
  def valid_counts(d):
   return all(isinstance(k,str) and k.isascii() and k.isdigit() and str(int(k))==k and int(k)<0xffffffff and type(v) is int and v>0 for k,v in d.items())
  neg=negative[0];pos=counts[0];need(valid_counts(neg) and valid_counts(pos),'invalid source-negative cell counts')
  partial=contain['excluded_partial_components'];need(isinstance(partial,list) and contain['policy']=='all-source-cell-centers-v1' and contain.get('stage')=='positive_full_center_before_exclusion','invalid positive containment report')
  partial_ids=[]
  for item in partial:
   root=item['component_id_evidence_only'];inside=item['inside_cells'];whole=item['whole_cells'];need(type(root) is int and 0<=root<0xffffffff and type(inside) is int and type(whole) is int and 0<inside<whole and pos.get(str(root))==inside,'invalid partial containment root');partial_ids.append(root)
  need(len(set(partial_ids))==len(partial_ids) and contain['excluded_partial_count']==len(partial_ids) and contain['excluded_partial_cells']==sum(x['whole_cells'] for x in partial),'invalid partial containment summary')
  full={int(k) for k in pos}-set(partial_ids);negative_ids={int(k) for k in neg};selected=claim['component_ids'];excluded=filt['excluded_roots'];need(all(type(k) is int and 0<=k<0xffffffff for k in selected+excluded),'invalid source-negative roots')
  need(selected==sorted(full-negative_ids) and filt['selected_roots']==selected and excluded==sorted(full&negative_ids) and filt['selected_count']==len(selected) and filt['excluded_count']==len(excluded) and filt['negative_roots_outside_positive']==len(negative_ids-full),'source-negative filter partition mismatch')
  need(contain['selected_count']==len(full) and contain['selected_cells']==sum(pos[str(k)] for k in full),'invalid full-containment summary')
  return features[:1],counts
 need(len(counts)==len(features),'polygon feature counts mismatch');return features,counts

def claims_for(compiled,snapshot,resolution):
 aff={x['affiliation_id']:x for x in snapshot['affiliations']};bindings={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'}
 need(resolution.get('schema')=='source-point-component-report-v1' and resolution.get('status')=='research-only-not-a-build' and resolution.get('revision')==compiled['revision'] and resolution.get('entity_revision')==compiled['entity_revision'],'point resolution identity mismatch')
 claims=resolution.get('claims');need(isinstance(claims,list) and len(claims)==len(compiled['affiliation_ids']),'point claim count mismatch');roots={};seen=set()
 for c in claims:
  aid=c.get('affiliation_id');need(aid in aff and aid not in seen and aid in compiled['affiliation_ids'],'unknown or duplicate claim');a=aff[aid];root=c.get('component_id');code=bindings.get(a.get('entity_id'))
  need(c.get('method')==a.get('method')=='source_point_named_region_component_v1' and c.get('entity_id')==a.get('entity_id') and c.get('entity_code')==code and type(root) is int and 0<=root<0xffffffff,'claim/decision mismatch')
  roots.setdefault(root,[]).append({'affiliation_id':aid,'entry_ids':compiled['affiliation_entry_links'][aid],'code':code});seen.add(aid)
 need(seen==set(compiled['affiliation_ids']),'unconsumed selected affiliation');return roots

def run(config_path):
 with open(config_path,'rb') as f:cfg_bytes=f.read((2<<20)+1)
 need(len(cfg_bytes)<=2<<20,'config too large');cfg=json.loads(cfg_bytes);need(cfg.get('schema')=='stage3-selected-mixed-request-v1','bad request')
 def guard():pass  # Process and disk limits are enforced externally.
 def pinned(s):
  need(isinstance(s,dict) and set(s)=={'path','sha256'},'bad pin');p=Path(s['path']).resolve(strict=True);need(p.is_file() and writer.sha(p,guard)==s['sha256'],'pin mismatch: '+str(p));return p
 guard();codes=cfg['code'];optional={'federal_register_rectangle','negative_component_filter'};need(set(codes)-optional-{'line_side'}=={'driver','writer','overlay','contract','resolver','adapter','named_identity','identity_watch','geonames_extractor','geonames_airport_extractor','validator','polygon_policy','polygon_source','polygon_loader','polygon_intersection','polygon_resolution','mixed_claims','osm_extractor','osm_extractor_v3','osm_extractor_v4','osm_reef_extractor','osm_admin_extractor','osm_closed_way','land_archive_extractor','raw_city_extractor','osm_node_extractor','point_claim_validator','entry_evidence','full_coverage_policy','osm_anchor_extractor','corroboration_adapter','corroboration_source','corroboration_evaluate','corroboration_bridge','bering_adapter','bering_resolver','bering_bridge','bering_profiler','bering_intersection'} and (not (set(codes)&optional) or optional<=set(codes)),'missing trusted code pins')
 codepaths={'driver':Path(__file__).resolve(),'writer':HERE/'writer.py','overlay':HERE/'overlay.py','contract':HERE/'decision_contract.py','resolver':POINT/'resolve.py','adapter':POINT/'adapter.py','named_identity':POINT.parent/'named-identity-prototype'/'named_identity.py','identity_watch':POINT.parent/'named-identity-prototype'/'identity_watch.py','geonames_extractor':POINT/'geonames_extract.py','geonames_airport_extractor':POINT/'geonames_airport_extract.py','validator':STAGE2/'validate_stage2_candidate.py','osm_extractor':polygon_loader.OSM_CODE,'osm_extractor_v3':polygon_loader.OSM_CODE_V3,'osm_extractor_v4':polygon_loader.OSM_CODE_V4,'osm_reef_extractor':polygon_loader.REEF_CODE,'osm_admin_extractor':polygon_loader.ADMIN_CODE,'osm_closed_way':polygon_loader.WAY_CODE,'land_archive_extractor':polygon_loader.LAND_CODE,'osm_anchor_extractor':polygon_loader.ANCHOR_CODE,'raw_city_extractor':POINT/'raw_city_extract.py','osm_node_extractor':POINT/'osm_node_extract.py','point_claim_validator':POINT_VALIDATOR,'entry_evidence':HERE/'entry_evidence.py','full_coverage_policy':HERE/'full_coverage_policy.py',**{k:HERE/(k+'.py') for k in ('polygon_policy','polygon_source','polygon_loader','polygon_intersection','polygon_resolution','mixed_claims','corroboration_adapter','corroboration_source','corroboration_evaluate','corroboration_bridge','bering_adapter','bering_resolver','bering_bridge','bering_profiler','bering_intersection')}}
 if optional<=set(codes):codepaths.update({k:HERE/(k+'.py') for k in optional})
 if 'line_side' in codes:codepaths['line_side']=POINT/'line_side.py'
 need(codes['osm_extractor']==polygon_loader.OSM_CODE_SHA256 and codes['osm_extractor_v3']==polygon_loader.OSM_CODE_V3_SHA256 and codes['osm_extractor_v4']==polygon_loader.OSM_CODE_V4_SHA256 and codes['osm_reef_extractor']==polygon_loader.REEF_CODE_SHA256 and codes['osm_admin_extractor']==polygon_loader.ADMIN_CODE_SHA256 and codes['osm_closed_way']==polygon_loader.WAY_CODE_SHA256 and codes['land_archive_extractor']==polygon_loader.LAND_CODE_SHA256 and codes['osm_anchor_extractor']==polygon_loader.ANCHOR_CODE_SHA256,'unreviewed OSM extractor')
 for k,p in codepaths.items():need(writer.sha(p,guard)==codes[k],'code mismatch: '+k)
 stage2=cfg['stage2'];approval=read(pinned(cfg['stage2_approval']));need(approval['validator_sha256']==codes['validator'],'validator approval mismatch')
 sys.path.insert(0,str(STAGE2));validator=loadmodule('stage2_candidate_validator',codepaths['validator']);validation=validator.validate(stage2,approval['approved_code'],guard)
 request_path=pinned(cfg['point_request']);req=read(request_path);need(all(req.get(k+'_sha256')==codes[k] for k in ('resolver','adapter','named_identity','identity_watch')),'point code request mismatch');snapshot_path=pinned(req['snapshot']);snapshot=read(snapshot_path);base=read(stage2['snapshot']['path']);report=read(stage2['report']['path'])
 pins={k:cfg['policy_pins'][k] for k in ('baseline_report_sha256','baseline_rows_sha256','baseline_runs_sha256','baseline_decision_snapshot_sha256','physical_rows_sha256','physical_runs_sha256','component_rows_sha256','component_runs_sha256')}
 expected={'baseline_report_sha256':stage2['report']['sha256'],'baseline_rows_sha256':stage2['rows']['sha256'],'baseline_runs_sha256':stage2['runs']['sha256'],'baseline_decision_snapshot_sha256':stage2['snapshot']['sha256'],**{k+'_sha256':req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}}
 need(pins==expected and req['physical_rows']['sha256']==stage2['physical_rows']['sha256'] and req['physical_runs']['sha256']==stage2['physical_runs']['sha256'] and req['grid']==report['grid'],'point/baseline inputs mismatch')
 if any(a.get('method')=='component_containment_excluding_source_v1' and a.get('evidence',{}).get('execution_status')=='selected_for_research' for a in snapshot.get('affiliations',[])):need(optional<=set(codes),'source-negative helper code pins required')
 compiled=decision_contract.compile_policy(snapshot,base,report,pins,POINT_METHODS|{'component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','component_containment_excluding_source_v1','osm_archipelago_component_intersection_v1','osm_admin_group_containment_v1','osm_reef_envelope_component_containment_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1','osm_way_component_containment_v1','osm_relation_component_containment_v1','osm_land_archive_component_intersection_v1','osm_land_archive_component_containment_v1','label_contained_ecoregion_contact_v1'});evidence_files=cfg['evidence_source_files'];evidence=entry_evidence.resolve(snapshot,compiled,evidence_files,guard);
 for eid,links in evidence.items():compiled['entries'][eid]['geographic_membership_evidence']=links
 selected_point_ids={a['affiliation_id'] for a in snapshot['affiliations'] if a.get('affiliation_id') in compiled['affiliation_ids'] and a.get('method') in POINT_METHODS};need(selected_point_ids,'mixed driver requires selected point decisions');need(req.get('adapter_sha256')==codes['adapter'],'adapter request pin mismatch');
 if any(a.get('affiliation_id') in selected_point_ids and a.get('method')=='geonames_zip_line_side_component_v1' for a in snapshot['affiliations']):need('line_side' in codes and req.get('line_side_sha256')==codes['line_side'],'line side request pin missing')
 if any(a.get('affiliation_id') in selected_point_ids and a.get('method')=='raw_json_city_named_region_component_v1' for a in snapshot['affiliations']):need(req.get('raw_city_extractor_sha256')==codes['raw_city_extractor'],'raw city request pin mismatch')
 if any(a.get('affiliation_id') in selected_point_ids and a.get('method') in ('osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1') for a in snapshot['affiliations']):need(req.get('osm_node_extractor_sha256')==codes['osm_node_extractor'],'OSM node request pin mismatch')
 if any(a.get('affiliation_id') in selected_point_ids and a.get('method') in ('geonames_zip_island_named_region_component_v1','geonames_zip_named_list1_component_v1','geonames_zip_line_side_component_v1') for a in snapshot['affiliations']):need(req.get('geonames_extractor_sha256')==codes['geonames_extractor'] and req.get('named_identity_sha256')==codes['named_identity'] and req.get('identity_watch_sha256')==codes['identity_watch'],'GeoNames extractor or identity request pin mismatch')
 if any(a.get('affiliation_id') in selected_point_ids and a.get('method')=='geonames_zip_airport_named_region_component_v1' for a in snapshot['affiliations']):need(req.get('geonames_airport_extractor_sha256')==codes['geonames_airport_extractor'] and req.get('named_identity_sha256')==codes['named_identity'] and req.get('identity_watch_sha256')==codes['identity_watch'],'GeoNames airport extractor or identity request pin mismatch')
 sys.path.insert(0,str(POINT));resolver=loadmodule('stage3_point_resolver',codepaths['resolver']);resolution=resolver.resolve(req);need((not any(a.get('affiliation_id') in selected_point_ids and a.get('method') in ('geonames_zip_island_named_region_component_v1','geonames_zip_named_list1_component_v1','geonames_zip_line_side_component_v1') for a in snapshot['affiliations']) or resolution.get('geonames_extractor_sha256')==codes['geonames_extractor']) and (not any(a.get('affiliation_id') in selected_point_ids and a.get('method')=='geonames_zip_airport_named_region_component_v1' for a in snapshot['affiliations']) or resolution.get('geonames_airport_extractor_sha256')==codes['geonames_airport_extractor']) and resolution['snapshot_sha256']==req['snapshot']['sha256'] and resolution['input_sha256']=={k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'resolver input mismatch');lineage_specs=resolver.lineage_specs(read(req['component_manifest']['path']));lineage_paths=[pinned(s) for s in lineage_specs];point_validator=loadmodule('reviewed_point_claim_validator',POINT_VALIDATOR);point_subset={**compiled,'affiliation_ids':sorted(selected_point_ids)};point_validator.claims_for(point_subset,snapshot,resolution)
 poly_ids={a['affiliation_id'] for a in snapshot['affiliations'] if a.get('affiliation_id') in compiled['affiliation_ids'] and a.get('method') in ('component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','component_containment_excluding_source_v1','osm_archipelago_component_intersection_v1','osm_admin_group_containment_v1','osm_reef_envelope_component_containment_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1','osm_way_component_containment_v1','osm_relation_component_containment_v1','osm_land_archive_component_intersection_v1','osm_land_archive_component_containment_v1')};need(poly_ids,'mixed driver requires selected polygon decisions');poly=polygon_policy.adapt(snapshot,poly_ids);poly_inputs={k:req[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')};poly_resolution=polygon_resolution.resolve(poly,snapshot,cfg['polygon_source_files'],report['grid'],poly_inputs,guard);corroboration_files=cfg.get('corroboration_source_files',[]);need(isinstance(corroboration_files,list) and all(isinstance(x,dict) and isinstance(x.get('path'),str) for x in corroboration_files),'invalid corroboration files');corroboration_paths=[Path(x['path']).resolve(strict=True) for x in corroboration_files];other_source_paths={Path(x['path']).resolve(strict=True) for x in [*cfg['polygon_source_files'],*evidence_files,*req['source_files']]};need(len(set(corroboration_paths))==len(corroboration_paths) and not (set(corroboration_paths)&other_source_paths),'corroboration source paths overlap');corroboration=corroboration_bridge.resolve(snapshot,poly,poly_resolution,corroboration_files,report['grid'],{k:req[k]['path'] for k in poly_inputs},{k:req[k]['sha256'] for k in poly_inputs},guard);bering_ids={a['affiliation_id'] for a in snapshot['affiliations'] if a.get('affiliation_id') in compiled['affiliation_ids'] and a.get('method')=='label_contained_ecoregion_contact_v1'};bering_files=cfg.get('bering_source_files',[]);need(isinstance(bering_files,list),'invalid Bering source files');verify_bering_source_paths(bering_files,[*cfg['polygon_source_files'],*evidence_files,*req['source_files']],corroboration_files);bering_resolution=None;protected_specs=[];protected_checks=[];bering_protected=set();bering_proj=[]
 if snapshot.get('schema','').endswith('-v3'):
  need('bering_source_files' in cfg,'v3 Bering source field required');bp=bering_adapter.adapt(snapshot,compiled,bering_ids)
 else:
  need(not bering_ids and not bering_files,'Bering needs v3 snapshot');bp=None
 if bering_ids:
  import pyproj
  need(os.environ.get('PROJ_NETWORK')=='OFF' and not pyproj.network.is_network_enabled(),'PROJ network must be disabled');proj_spec=cfg.get('bering_proj_db');proj_path=pinned(proj_spec);need((Path(pyproj.datadir.get_data_dir())/'proj.db').resolve(strict=True)==proj_path,'active PROJ database mismatch');bering_proj=[proj_spec]
  derived=read(pinned(stage2['derived_manifest']));spec=derived.get('artifacts',{}).get('resolution_report');need(isinstance(spec,dict) and spec.get('sha256')==report.get('resolution_report_sha256'),'Bering protected report mismatch');protected_specs.append(spec);protected=read(pinned(spec));protected_req={'baseline_snapshot_sha256':stage2['snapshot']['sha256'],'component_manifest_sha256':req['component_manifest']['sha256'],'input_sha256':{k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'grid':req['grid']};bering_protected=bering_bridge.protected_roots(base,report,protected_req,protected,spec['sha256']);bering_resolution=bering_bridge.resolve(bp,snapshot,bering_files,poly_inputs,report['grid'],bering_protected,guard,bering_profiler.profile,polygon_source.extract,bering_intersection)
 else:need(not bering_files and 'bering_proj_db' not in cfg,'unused Bering sources or PROJ DB')
 reports=[resolution,poly_resolution]+([bering_resolution] if bering_resolution else []);claims=mixed_claims.combine(compiled,snapshot,reports,set(report['physical_coverage']['seed_roots']));requirements=mixed_claims.protected_requirements(snapshot,compiled)
 # Optional research hook uses the same freshly resolved selected-source reports.
 # No saved comparison or archived resolver report is accepted here.
 regional=None;regional_paths=[];region_rows=lambda y:[]
 if 'regional' in cfg:
  rc=cfg['regional'];need(isinstance(rc,dict) and set(rc)=={'hook','request'},'invalid regional driver config')
  hookpath=pinned(rc['hook']);regional_hook=loadmodule('regional_driver_hook',hookpath)
  regional=regional_hook.prepare(rc['request'],compiled,snapshot,reports,report['grid'],{k:req[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')},set(report['physical_coverage']['seed_roots']),mixed_claims,guard,snapshot_sha256=req['snapshot']['sha256'])
  need(regional['provenance']['decision_snapshot_sha256']==req['snapshot']['sha256'],'regional decision snapshot mismatch')
  regional['provenance']['driver_hook']=dict(rc['hook'])
  claims=regional['component_claims'];region_rows=regional['wrap_region_rows'](region_rows,regional['blocked_region_roots'])
  regional_paths=[hookpath]+[Path(p).resolve(strict=True) for p in regional['input_paths']]

 if requirements:
  derived=read(pinned(stage2['derived_manifest']));spec=derived.get('artifacts',{}).get('resolution_report');need(isinstance(spec,dict) and spec.get('sha256')==report.get('resolution_report_sha256'),'protected report pin mismatch');
  if spec not in protected_specs:protected_specs.append(spec)
  protected=read(pinned(spec));protected_req={'baseline_snapshot_sha256':stage2['snapshot']['sha256'],'component_manifest_sha256':req['component_manifest']['sha256'],'input_sha256':{k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'grid':req['grid']};protected_checks=mixed_claims.verify_protected(requirements,snapshot,base,report,protected_req,protected,spec['sha256'],poly_resolution)
 out=Path(cfg['output']).resolve()
 sources=[Path(config_path).resolve(),request_path,Path(cfg['stage2_approval']['path']).resolve(),*codepaths.values(),*lineage_paths,*(Path(s['path']).resolve() for s in protected_specs),*(Path(s['path']).resolve() for s in stage2.values()),*(Path(req[k]['path']).resolve() for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')),*(Path(s['path']).resolve() for s in req['source_files']),POINT/'adapter.py',POINT.parent/'named-identity-prototype'/'named_identity.py',POINT.parent/'named-identity-prototype'/'identity_watch.py',polygon_loader.OSM_CODE,*(Path(s['path']).resolve() for s in cfg['polygon_source_files']),*(Path(s['path']).resolve() for s in evidence_files),*(Path(s['path']).resolve() for s in corroboration_files),*(Path(s['path']).resolve() for s in bering_files),*(Path(s['path']).resolve() for s in bering_proj)]
 need(not out.exists() and out.parent.is_dir() and all(not out.is_relative_to(p.parent) and not p.is_relative_to(out) for p in sources+regional_paths),'output overlaps inputs or code')
 result=writer.write_streams(grid=report['grid'],physical_rows=req['physical_rows']['path'],physical_runs=req['physical_runs']['path'],component_rows=req['component_rows']['path'],component_runs=req['component_runs']['path'],baseline_rows=stage2['rows']['path'],baseline_runs=stage2['runs']['path'],component_claims=claims,mainland_roots=set(report['physical_coverage']['seed_roots']),region_rows=region_rows,output=out,guard=guard,disk_reserve_bytes=cfg['minimum_free_bytes'],polygon_affiliation_ids=poly_ids|bering_ids)
 stats=result['affiliation_statistics'];synthetic=regional['synthetic_affiliation_id'] if regional else None
 need(set(stats)-({synthetic} if synthetic else set())==set(compiled['affiliation_ids']) and all(stats[aid]['applied_cells']>0 for aid in compiled['affiliation_ids']),'selected claim absent from output')
 if regional:need(synthetic not in compiled['affiliation_ids'],'regional synthetic ID overlaps selected affiliation')
 extents={}
 for claim in poly_resolution['claims']:
  aid=claim['affiliation_id'];root_stats=result['polygon_root_statistics'][aid];positive_features,per_feature=positive_extent_features(claim);extents[aid]={}
  for root in claim['component_ids']:
   key=str(root);whole=root_stats.get(key,{}).get('applied_cells');need(type(whole) is int and whole>0,'polygon root not observed in output');per=[]
   for feature,counts in zip(positive_features,per_feature):
    inside=counts.get(key,0);need(type(inside) is int and 0<=inside<=whole,'polygon inside/whole count mismatch');per.append({'feature_id':feature['feature_id'],'inside_cells':inside,'outside_cells':whole-inside})
   validate_admin_group_extent(claim['method'],per,whole)
   extents[aid][key]={'whole_component_cells':whole,'per_feature':per}
 bering_extents={}
 if bering_resolution:
  for detail in bering_resolution['details']:
   aid=detail['affiliation_id'];counts={v['root']:v for v in detail['resolution']['root_counts']};claim=next(c for c in bering_resolution['claims'] if c['affiliation_id']==aid);bering_extents[aid]={}
   for root in claim['component_ids']:
    v=counts[root];stats_root=result['polygon_root_statistics'][aid].get(str(root),{});whole=stats_root.get('applied_cells');changed=stats_root.get('changed_cells');need(type(whole) is int and whole>0 and type(changed) is int and 0<=changed<=whole and all(type(v.get(k)) is int and v[k]>=0 for k in ('cells','label_inside','inside','outside','boundary','untested')) and v['label_inside']==whole==v['cells'] and v['inside']+v['outside']+v['boundary']+v['untested']==whole and v['inside']>0 and v['boundary']==v['untested']==0 and root not in bering_protected,'Bering extent or protection mismatch');bering_extents[aid][str(root)]={'whole_component_cells':whole,'label_inside_cells':v['label_inside'],'ecoregion_inside_cells':v['inside'],'ecoregion_outside_cells':v['outside'],'ecoregion_boundary_cells':v['boundary'],'ecoregion_untested_cells':v['untested']}
 for k,p in codepaths.items():need(writer.sha(p,guard)==codes[k],'code changed: '+k)
 for s in [cfg['point_request'],cfg['stage2_approval'],*stage2.values(),*lineage_specs,*protected_specs,*([req[k] for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')]),*({'path':x['path'],'sha256':x['sha256']} for x in req['source_files']),*({'path':x['path'],'sha256':x['sha256']} for x in cfg['polygon_source_files']),*({'path':x['path'],'sha256':x['sha256']} for x in corroboration_files),*({'path':x['path'],'sha256':x['sha256']} for x in bering_files),*bering_proj]:pinned(s)
 if regional:regional['verify']();pinned(cfg['regional']['hook'])
 need(entry_evidence.resolve(snapshot,compiled,evidence_files,guard)==evidence,'entry evidence changed')
 with open(config_path,'rb') as f:need(f.read((2<<20)+1)==cfg_bytes,'request changed')
 output={'schema':'stage3-selected-mixed-land-report-v1','status':'research-awaiting-monitor','publishable':False,'request_sha256':hashlib.sha256(cfg_bytes).hexdigest(),'decision_snapshot_sha256':req['snapshot']['sha256'],'baseline_validation':validation,'policy':compiled,'point_resolution':resolution,'polygon_resolution':poly_resolution,'polygon_source_custody':poly['source_pins'],'administrative_corroboration':corroboration,'bering_resolution':bering_resolution,'bering_proj_db_sha256':(bering_proj[0]['sha256'] if bering_proj else None),'bering_protected_witness_report_sha256':(protected_specs[0]['sha256'] if bering_resolution else None),'bering_component_extents':bering_extents,'polygon_component_extents':extents,'protected_witness_checks':protected_checks,'writer':result,'code_sha256':codes,'limitations':['Point identity labels corroborate the witness, not every cell of its physical component.','A hashed identity document alone does not establish an island claim.','Only supported selected point and polygon-component affiliations are applied; unselected decisions remain unresolved.', 'A containment decision checks cell centers rather than continuous geometry; a polygon contact alone does not prove whole-component identity. Per-feature inside counts may overlap and are not union counts.', 'A matched guideline excerpt supports a reviewed CRS assertion and does not prove every record datum.','Geographic membership evidence records a selected interpretation, not an executable selector; source hashes do not verify the cited section or interpretation.','Source origin, reuse and R2-readback notes are catalog assertions, not machine proof of rights or geographic truth; documentation URI is not a reuse-license grant.','NE label containment and coarse EPA ecoregion contact do not prove full island membership; operation bboxes do not establish exact applicability.','Water cells stay unassigned.','The separate process-group monitor is required; sampling can miss spikes and external disk use can race reserve checks.']}
 if regional:
  output['limitations']=[x for x in output['limitations'] if not x.startswith('Only supported selected point and polygon-component affiliations')]+['Selected source affiliations and a separate research-only regional rule are applied; other unselected decisions remain unresolved.']
  output['regional_island_rule']={'status':'research-profiling-standin' if regional['provenance']['profiling_standin'] else 'research-awaiting-review','provenance':regional['provenance'],'result':regional['regional_result'],'proposal_trace':regional['regional_proposal_trace'],'synthetic_affiliation_id':regional['synthetic_affiliation_id'],'synthetic_affiliation_statistics':stats.get(regional['synthetic_affiliation_id']),'limitation':'Withheld roots retain baseline codes; source interpretations and incomplete inventories are not proof of final geography.'}
 payload=(json.dumps(output,sort_keys=True,indent=2)+'\n').encode();need(shutil.disk_usage(out).free>=cfg['minimum_free_bytes']+len(payload)+(1<<20),'disk reserve reached before report');p=out/'report.json';tmp=None
 try:
  with tempfile.NamedTemporaryFile(dir=out,prefix='.report-',delete=False) as f:tmp=f.name;f.write(payload);f.flush();os.fsync(f.fileno())
  os.link(tmp,p)
  try:
   d=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
   try:os.fsync(d)
   finally:os.close(d)
  except OSError as e:raise RuntimeError('report linked but directory fsync failed; completion marker outcome uncertain') from e
 finally:
  if tmp is not None:os.unlink(tmp)
 return hashlib.sha256(payload).hexdigest()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('config');a=p.parse_args()
 try:print(run(a.config),flush=True)
 except Exception as e:print('stage3 failed: '+str(e),file=sys.stderr,flush=True);sys.exit(1)
