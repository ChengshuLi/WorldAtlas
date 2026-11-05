#!/usr/bin/env python3
"""Build a source-resolved land-only List 1 overlay. No reference-map input.

A process-group watchdog must supervise this worker; output is research-only
until its monitor is verified. Unselected or unsupported methods fail closed.
"""
import argparse,hashlib,importlib.util,json,os,sys,shutil,tempfile
from pathlib import Path
import decision_contract,writer,polygon_policy,polygon_resolution,mixed_claims,polygon_loader,polygon_source,entry_evidence,corroboration_bridge,bering_adapter,bering_resolver,bering_bridge,bering_profiler,bering_intersection
HERE=Path(__file__).resolve().parent
POINT=HERE.parent/'draft24-reduced-floor-point-20261105/point-component-prototype'
POINT_VALIDATOR=HERE.parent/'osm-island-group-stage3-adapter-20261104/apply_selected_points.py'
POINT_METHODS={'source_point_component_v1','source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'}
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
 need(len(cfg_bytes)<=2<<20,'config too large');cfg=json.loads(cfg_bytes);need(cfg.get('schema')=='stage3-selected-mixed-request-v1','bad request');floor=cfg['minimum_memory_kib'];need(type(floor) is int and floor>=1048576,'bad floor')
 def guard():need(available()>=floor,'memory floor reached')
 def pinned(s):
  need(isinstance(s,dict) and set(s)=={'path','sha256'},'bad pin');p=Path(s['path']).resolve(strict=True);need(p.is_file() and writer.sha(p,guard)==s['sha256'],'pin mismatch: '+str(p));return p
 guard();codes=cfg['code'];need(set(codes)=={'driver','writer','overlay','contract','resolver','adapter','named_identity','identity_watch','validator','polygon_policy','polygon_source','polygon_loader','polygon_intersection','polygon_resolution','mixed_claims','osm_extractor','osm_extractor_v3','osm_extractor_v4','raw_city_extractor','osm_node_extractor','point_claim_validator','entry_evidence','full_coverage_policy','osm_anchor_extractor','corroboration_adapter','corroboration_source','corroboration_evaluate','corroboration_bridge','bering_adapter','bering_resolver','bering_bridge','bering_profiler','bering_intersection'},'missing trusted code pins')
 codepaths={'driver':Path(__file__).resolve(),'writer':HERE/'writer.py','overlay':HERE/'overlay.py','contract':HERE/'decision_contract.py','resolver':POINT/'resolve.py','adapter':POINT/'adapter.py','named_identity':POINT.parent/'named-identity-prototype'/'named_identity.py','identity_watch':POINT.parent/'named-identity-prototype'/'identity_watch.py','validator':STAGE2/'validate_stage2_candidate.py','osm_extractor':polygon_loader.OSM_CODE,'osm_extractor_v3':polygon_loader.OSM_CODE_V3,'osm_extractor_v4':polygon_loader.OSM_CODE_V4,'osm_anchor_extractor':polygon_loader.ANCHOR_CODE,'raw_city_extractor':POINT/'raw_city_extract.py','osm_node_extractor':POINT/'osm_node_extract.py','point_claim_validator':POINT_VALIDATOR,'entry_evidence':HERE/'entry_evidence.py','full_coverage_policy':HERE/'full_coverage_policy.py',**{k:HERE/(k+'.py') for k in ('polygon_policy','polygon_source','polygon_loader','polygon_intersection','polygon_resolution','mixed_claims','corroboration_adapter','corroboration_source','corroboration_evaluate','corroboration_bridge','bering_adapter','bering_resolver','bering_bridge','bering_profiler','bering_intersection')}}
 need(codes['osm_extractor']==polygon_loader.OSM_CODE_SHA256 and codes['osm_extractor_v3']==polygon_loader.OSM_CODE_V3_SHA256 and codes['osm_extractor_v4']==polygon_loader.OSM_CODE_V4_SHA256 and codes['osm_anchor_extractor']==polygon_loader.ANCHOR_CODE_SHA256,'unreviewed OSM extractor')
 for k,p in codepaths.items():need(writer.sha(p,guard)==codes[k],'code mismatch: '+k)
 stage2=cfg['stage2'];approval=read(pinned(cfg['stage2_approval']));need(approval['validator_sha256']==codes['validator'],'validator approval mismatch')
 sys.path.insert(0,str(STAGE2));validator=loadmodule('stage2_candidate_validator',codepaths['validator']);validation=validator.validate(stage2,approval['approved_code'],approval['approved_max_rss_kib'],guard)
 request_path=pinned(cfg['point_request']);req=read(request_path);need(all(req.get(k+'_sha256')==codes[k] for k in ('resolver','adapter','named_identity','identity_watch')),'point code request mismatch');snapshot_path=pinned(req['snapshot']);snapshot=read(snapshot_path);base=read(stage2['snapshot']['path']);report=read(stage2['report']['path'])
 pins={k:cfg['policy_pins'][k] for k in ('baseline_report_sha256','baseline_rows_sha256','baseline_runs_sha256','baseline_decision_snapshot_sha256','physical_rows_sha256','physical_runs_sha256','component_rows_sha256','component_runs_sha256')}
 expected={'baseline_report_sha256':stage2['report']['sha256'],'baseline_rows_sha256':stage2['rows']['sha256'],'baseline_runs_sha256':stage2['runs']['sha256'],'baseline_decision_snapshot_sha256':stage2['snapshot']['sha256'],**{k+'_sha256':req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}}
 need(pins==expected and req['physical_rows']['sha256']==stage2['physical_rows']['sha256'] and req['physical_runs']['sha256']==stage2['physical_runs']['sha256'] and req['grid']==report['grid'],'point/baseline inputs mismatch')
 compiled=decision_contract.compile_policy(snapshot,base,report,pins,POINT_METHODS|{'component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1','label_contained_ecoregion_contact_v1'});evidence_files=cfg['evidence_source_files'];evidence=entry_evidence.resolve(snapshot,compiled,evidence_files,guard);
 for eid,links in evidence.items():compiled['entries'][eid]['geographic_membership_evidence']=links
 selected_point_ids={a['affiliation_id'] for a in snapshot['affiliations'] if a.get('affiliation_id') in compiled['affiliation_ids'] and a.get('method') in POINT_METHODS};need(selected_point_ids,'mixed driver requires selected point decisions');need(req.get('adapter_sha256')==codes['adapter'],'adapter request pin mismatch');
 if any(a.get('affiliation_id') in selected_point_ids and a.get('method')=='raw_json_city_named_region_component_v1' for a in snapshot['affiliations']):need(req.get('raw_city_extractor_sha256')==codes['raw_city_extractor'],'raw city request pin mismatch')
 if any(a.get('affiliation_id') in selected_point_ids and a.get('method') in ('osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1') for a in snapshot['affiliations']):need(req.get('osm_node_extractor_sha256')==codes['osm_node_extractor'],'OSM node request pin mismatch')
 sys.path.insert(0,str(POINT));resolver=loadmodule('stage3_point_resolver',codepaths['resolver']);resolution=resolver.resolve(req);need(resolution['snapshot_sha256']==req['snapshot']['sha256'] and resolution['input_sha256']=={k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'resolver input mismatch');lineage_specs=resolver.lineage_specs(read(req['component_manifest']['path']));lineage_paths=[pinned(s) for s in lineage_specs];point_validator=loadmodule('reviewed_point_claim_validator',POINT_VALIDATOR);point_subset={**compiled,'affiliation_ids':sorted(selected_point_ids)};point_validator.claims_for(point_subset,snapshot,resolution)
 poly_ids={a['affiliation_id'] for a in snapshot['affiliations'] if a.get('affiliation_id') in compiled['affiliation_ids'] and a.get('method') in ('component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1')};need(poly_ids,'mixed driver requires selected polygon decisions');poly=polygon_policy.adapt(snapshot,poly_ids);poly_inputs={k:req[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')};poly_resolution=polygon_resolution.resolve(poly,snapshot,cfg['polygon_source_files'],report['grid'],poly_inputs,guard);corroboration_files=cfg.get('corroboration_source_files',[]);need(isinstance(corroboration_files,list) and all(isinstance(x,dict) and isinstance(x.get('path'),str) for x in corroboration_files),'invalid corroboration files');corroboration_paths=[Path(x['path']).resolve(strict=True) for x in corroboration_files];other_source_paths={Path(x['path']).resolve(strict=True) for x in [*cfg['polygon_source_files'],*evidence_files,*req['source_files']]};need(len(set(corroboration_paths))==len(corroboration_paths) and not (set(corroboration_paths)&other_source_paths),'corroboration source paths overlap');corroboration=corroboration_bridge.resolve(snapshot,poly,poly_resolution,corroboration_files,report['grid'],{k:req[k]['path'] for k in poly_inputs},{k:req[k]['sha256'] for k in poly_inputs},guard);bering_ids={a['affiliation_id'] for a in snapshot['affiliations'] if a.get('affiliation_id') in compiled['affiliation_ids'] and a.get('method')=='label_contained_ecoregion_contact_v1'};bering_files=cfg.get('bering_source_files',[]);need(isinstance(bering_files,list),'invalid Bering source files');verify_bering_source_paths(bering_files,[*cfg['polygon_source_files'],*evidence_files,*req['source_files']],corroboration_files);bering_resolution=None;protected_specs=[];protected_checks=[];bering_protected=set();bering_proj=[]
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
 if requirements:
  derived=read(pinned(stage2['derived_manifest']));spec=derived.get('artifacts',{}).get('resolution_report');need(isinstance(spec,dict) and spec.get('sha256')==report.get('resolution_report_sha256'),'protected report pin mismatch');
  if spec not in protected_specs:protected_specs.append(spec)
  protected=read(pinned(spec));protected_req={'baseline_snapshot_sha256':stage2['snapshot']['sha256'],'component_manifest_sha256':req['component_manifest']['sha256'],'input_sha256':{k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'grid':req['grid']};protected_checks=mixed_claims.verify_protected(requirements,snapshot,base,report,protected_req,protected,spec['sha256'],poly_resolution)
 out=Path(cfg['output']).resolve()
 sources=[Path(config_path).resolve(),request_path,Path(cfg['stage2_approval']['path']).resolve(),*codepaths.values(),*lineage_paths,*(Path(s['path']).resolve() for s in protected_specs),*(Path(s['path']).resolve() for s in stage2.values()),*(Path(req[k]['path']).resolve() for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')),*(Path(s['path']).resolve() for s in req['source_files']),POINT/'adapter.py',POINT.parent/'named-identity-prototype'/'named_identity.py',POINT.parent/'named-identity-prototype'/'identity_watch.py',polygon_loader.OSM_CODE,*(Path(s['path']).resolve() for s in cfg['polygon_source_files']),*(Path(s['path']).resolve() for s in evidence_files),*(Path(s['path']).resolve() for s in corroboration_files),*(Path(s['path']).resolve() for s in bering_files),*(Path(s['path']).resolve() for s in bering_proj)]
 need(not out.exists() and out.parent.is_dir() and all(not out.is_relative_to(p.parent) and not p.is_relative_to(out) for p in sources),'output overlaps inputs or code')
 result=writer.write_streams(grid=report['grid'],physical_rows=req['physical_rows']['path'],physical_runs=req['physical_runs']['path'],component_rows=req['component_rows']['path'],component_runs=req['component_runs']['path'],baseline_rows=stage2['rows']['path'],baseline_runs=stage2['runs']['path'],component_claims=claims,mainland_roots=set(report['physical_coverage']['seed_roots']),region_rows=lambda y:[],output=out,guard=guard,disk_reserve_bytes=cfg['minimum_free_bytes'],polygon_affiliation_ids=poly_ids|bering_ids)
 stats=result['affiliation_statistics'];need(set(stats)==set(compiled['affiliation_ids']) and all(v['applied_cells']>0 for v in stats.values()),'selected claim absent from output')
 extents={}
 for claim in poly_resolution['claims']:
  aid=claim['affiliation_id'];root_stats=result['polygon_root_statistics'][aid];per_feature=claim['intersection']['per_feature_root_inside_cells'];need(len(per_feature)==len(claim['source_features']),'polygon feature counts mismatch');extents[aid]={}
  for root in claim['component_ids']:
   key=str(root);whole=root_stats.get(key,{}).get('applied_cells');need(type(whole) is int and whole>0,'polygon root not observed in output');per=[]
   for feature,counts in zip(claim['source_features'],per_feature):
    inside=counts.get(key,0);need(type(inside) is int and 0<=inside<=whole,'polygon inside/whole count mismatch');per.append({'feature_id':feature['feature_id'],'inside_cells':inside,'outside_cells':whole-inside})
   extents[aid][key]={'whole_component_cells':whole,'per_feature':per}
 bering_extents={}
 if bering_resolution:
  for detail in bering_resolution['details']:
   aid=detail['affiliation_id'];counts={v['root']:v for v in detail['resolution']['root_counts']};claim=next(c for c in bering_resolution['claims'] if c['affiliation_id']==aid);bering_extents[aid]={}
   for root in claim['component_ids']:
    v=counts[root];stats_root=result['polygon_root_statistics'][aid].get(str(root),{});whole=stats_root.get('applied_cells');changed=stats_root.get('changed_cells');need(type(whole) is int and whole>0 and type(changed) is int and 0<=changed<=whole and all(type(v.get(k)) is int and v[k]>=0 for k in ('cells','label_inside','inside','outside','boundary','untested')) and v['label_inside']==whole==v['cells'] and v['inside']+v['outside']+v['boundary']+v['untested']==whole and v['inside']>0 and v['boundary']==v['untested']==0 and root not in bering_protected,'Bering extent or protection mismatch');bering_extents[aid][str(root)]={'whole_component_cells':whole,'label_inside_cells':v['label_inside'],'ecoregion_inside_cells':v['inside'],'ecoregion_outside_cells':v['outside'],'ecoregion_boundary_cells':v['boundary'],'ecoregion_untested_cells':v['untested']}
 for k,p in codepaths.items():need(writer.sha(p,guard)==codes[k],'code changed: '+k)
 for s in [cfg['point_request'],cfg['stage2_approval'],*stage2.values(),*lineage_specs,*protected_specs,*([req[k] for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')]),*({'path':x['path'],'sha256':x['sha256']} for x in req['source_files']),*({'path':x['path'],'sha256':x['sha256']} for x in cfg['polygon_source_files']),*({'path':x['path'],'sha256':x['sha256']} for x in corroboration_files),*({'path':x['path'],'sha256':x['sha256']} for x in bering_files),*bering_proj]:pinned(s)
 need(entry_evidence.resolve(snapshot,compiled,evidence_files,guard)==evidence,'entry evidence changed')
 with open(config_path,'rb') as f:need(f.read((2<<20)+1)==cfg_bytes,'request changed')
 output={'schema':'stage3-selected-mixed-land-report-v1','status':'research-awaiting-monitor','publishable':False,'request_sha256':hashlib.sha256(cfg_bytes).hexdigest(),'decision_snapshot_sha256':req['snapshot']['sha256'],'baseline_validation':validation,'policy':compiled,'point_resolution':resolution,'polygon_resolution':poly_resolution,'polygon_source_custody':poly['source_pins'],'administrative_corroboration':corroboration,'bering_resolution':bering_resolution,'bering_proj_db_sha256':(bering_proj[0]['sha256'] if bering_proj else None),'bering_protected_witness_report_sha256':(protected_specs[0]['sha256'] if bering_resolution else None),'bering_component_extents':bering_extents,'polygon_component_extents':extents,'protected_witness_checks':protected_checks,'writer':result,'code_sha256':codes,'limitations':['Point identity labels corroborate the witness, not every cell of its physical component.','A hashed identity document alone does not establish an island claim.','Only supported selected point and polygon-component affiliations are applied; unselected decisions remain unresolved.', 'A containment decision checks cell centers rather than continuous geometry; a polygon contact alone does not prove whole-component identity. Per-feature inside counts may overlap and are not union counts.', 'A matched guideline excerpt supports a reviewed CRS assertion and does not prove every record datum.','Geographic membership evidence records a selected interpretation, not an executable selector; source hashes do not verify the cited section or interpretation.','Source origin, reuse and R2-readback notes are catalog assertions, not machine proof of rights or geographic truth; documentation URI is not a reuse-license grant.','NE label containment and coarse EPA ecoregion contact do not prove full island membership; operation bboxes do not establish exact applicability.','Water cells stay unassigned.','The separate process-group monitor is required; sampling can miss spikes and external disk use can race reserve checks.']}
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
