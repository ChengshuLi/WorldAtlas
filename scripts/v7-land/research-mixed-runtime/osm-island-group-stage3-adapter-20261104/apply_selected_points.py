#!/usr/bin/env python3
"""Build a source-resolved land-only List 1 overlay. No reference-map input.

A process-group watchdog must supervise this worker; output is research-only
until its monitor is verified. Unselected or unsupported methods fail closed.
"""
import argparse,hashlib,importlib.util,json,os,sys,shutil,tempfile
from pathlib import Path
import decision_contract,writer
HERE=Path(__file__).resolve().parent
POINT=HERE.parent/'osm-island-group-integration-20261104/point-component-prototype'
SUPPORTED={'source_point_component_v1','source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'}
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

def claims_for(compiled,snapshot,resolution):
 aff={x['affiliation_id']:x for x in snapshot['affiliations']};bindings={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'}
 need(resolution.get('schema')=='source-point-component-report-v1' and resolution.get('status')=='research-only-not-a-build' and resolution.get('revision')==compiled['revision'] and resolution.get('entity_revision')==compiled['entity_revision'],'point resolution identity mismatch')
 claims=resolution.get('claims');need(isinstance(claims,list) and len(claims)==len(compiled['affiliation_ids']),'point claim count mismatch');roots={};seen=set()
 for c in claims:
  aid=c.get('affiliation_id');need(aid in aff and aid not in seen and aid in compiled['affiliation_ids'],'unknown or duplicate claim');a=aff[aid];root=c.get('component_id');code=bindings.get(a.get('entity_id'))
  need(c.get('method')==a.get('method') and c.get('method') in SUPPORTED and c.get('entity_id')==a.get('entity_id') and c.get('entity_code')==code and type(root) is int and 0<=root<0xffffffff,'claim/decision mismatch')
  if c['method']=='raw_json_city_named_region_component_v1':
   feats={x['feature_id']:x for x in snapshot.get('features',[])};feature=feats.get(a.get('feature_id'),{});evidence=a.get('evidence',{});sel=evidence.get('selector',{});ext=c.get('raw_city_extraction') or {};ge=c.get('coordinate_guideline_evidence') or {};refs=[x for x in snapshot.get('affiliation_source_refs',[]) if x.get('affiliation_id')==aid and x.get('role')=='coordinate_guideline'];need(len(refs)==1,'guideline reference missing or duplicate');ref=refs[0]
   assets=[x for x in snapshot.get('source_lineage_assets',[]) if (x.get('source_id'),x.get('version'))==(ref.get('source_id'),ref.get('source_version'))];need(len(assets)==1,'guideline asset missing or duplicate');asset=assets[0];point_assets=[x for x in snapshot.get('source_lineage_assets',[]) if (x.get('source_id'),x.get('version'))==(feature.get('source_id'),feature.get('source_version'))];need(len(point_assets)==1,'city asset missing or duplicate');point_asset=point_assets[0];point_trace=c.get('point_source') or {}
   need(ext.get('source_sha256')==point_asset.get('sha256')==point_trace.get('sha256') and point_trace.get('source_id')==feature.get('source_id') and point_trace.get('version')==feature.get('source_version'),'city source binding mismatch')
   need(ext.get('schema')=='raw-json-city-point-extraction-v1' and ext.get('record_id')==feature.get('source_feature_id') and ext.get('record_name')==sel.get('point_name') and ext.get('geometry_sha256')==feature.get('geometry_sha256') and ext.get('source_crs_assertion')==sel.get('source_crs_assertion')=='OGC:CRS84' and c.get('source_crs_scope')=='raw_record_coordinate_assertion','raw city extraction/decision mismatch')
   need(ge.get('source_id')==ref['source_id'] and ge.get('version')==ref['source_version'] and ge.get('sha256')==asset.get('sha256') and ge.get('uri')==asset.get('source_uri') and ge.get('selected_excerpt')==sel.get('coordinate_guideline_excerpt') and ge.get('matches')==1 and c.get('identity_check',{}).get('strict_contains') is True,'guideline or identity evidence mismatch')
  if c['method'] in ('osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'):
   feats={x['feature_id']:x for x in snapshot.get('features',[])};feature=feats.get(a.get('feature_id'),{});sel=a.get('evidence',{}).get('selector',{});ext=c.get('osm_node_extraction') or {};point_trace=c.get('point_source') or {};assets=[x for x in snapshot.get('source_lineage_assets',[]) if (x.get('source_id'),x.get('version'))==(feature.get('source_id'),feature.get('source_version'))];need(len(assets)==1,'OSM node asset missing or duplicate');asset=assets[0]
   need(ext.get('source_sha256')==asset.get('sha256')==point_trace.get('sha256') and point_trace.get('source_id')==feature.get('source_id') and point_trace.get('version')==feature.get('source_version'),'OSM node source binding mismatch')
   need(ext.get('schema')=='osm-api-node-point-extraction-v1' and ext.get('node_id')==feature.get('source_feature_id') and ext.get('node_version')==sel.get('node_version') and ext.get('verified_tags')=={'name':sel.get('island_name') if c['method']=='osm_api_island_node_group_component_v1' else sel.get('point_name'),'place':sel.get('place_tag')} and ext.get('source_crs')==sel.get('source_crs')=='OGC:CRS84' and ext.get('geometry_sha256')==feature.get('geometry_sha256') and c.get('source_crs_scope')=='osm_api_0_6_standard' and c.get('identity_check',{}).get('strict_contains') is True,'OSM node extraction/decision mismatch')
  if c['method']=='osm_api_island_node_group_component_v1':
   sel=a.get('evidence',{}).get('selector',{});check=c.get('identity_check') or {};need(sel.get('identity_scope')=='island_group' and sel.get('identity_class_value')=='Island group' and sel.get('place_tag')=='island' and c.get('identity_scope')==sel['identity_scope'] and c.get('island_identity')==sel.get('island_name') and c.get('point_name')==sel.get('island_name') and c.get('group_identity')==sel.get('group_identity') and check.get('identity_feature_class')=='Island group' and check.get('strict_contains') is True,'island/group identity mismatch')
  roots.setdefault(root,[]).append({'affiliation_id':aid,'entry_ids':compiled['affiliation_entry_links'][aid],'code':code});seen.add(aid)
 need(seen==set(compiled['affiliation_ids']),'unconsumed selected affiliation');return roots

def run(config_path):
 with open(config_path,'rb') as f:cfg_bytes=f.read((2<<20)+1)
 need(len(cfg_bytes)<=2<<20,'config too large');cfg=json.loads(cfg_bytes);need(cfg.get('schema')=='stage3-selected-points-request-v1','bad request');floor=cfg['minimum_memory_kib'];need(type(floor) is int and floor>=1730151,'bad floor')
 def guard():need(available()>=floor,'memory floor reached')
 def pinned(s):
  need(isinstance(s,dict) and set(s)=={'path','sha256'},'bad pin');p=Path(s['path']).resolve(strict=True);need(p.is_file() and writer.sha(p,guard)==s['sha256'],'pin mismatch: '+str(p));return p
 guard();codes=cfg['code'];need(set(codes)=={'driver','writer','overlay','contract','resolver','validator','raw_city_extractor','osm_node_extractor','adapter','named_identity','identity_watch'},'missing trusted code pins')
 codepaths={'driver':Path(__file__).resolve(),'writer':HERE/'writer.py','overlay':HERE/'overlay.py','contract':HERE/'decision_contract.py','resolver':POINT/'resolve.py','validator':STAGE2/'validate_stage2_candidate.py','raw_city_extractor':POINT/'raw_city_extract.py','osm_node_extractor':POINT/'osm_node_extract.py','adapter':POINT/'adapter.py','named_identity':POINT.parent/'named-identity-prototype'/'named_identity.py','identity_watch':POINT.parent/'named-identity-prototype'/'identity_watch.py'}
 for k,p in codepaths.items():need(writer.sha(p,guard)==codes[k],'code mismatch: '+k)
 stage2=cfg['stage2'];approval=read(pinned(cfg['stage2_approval']));need(approval['validator_sha256']==codes['validator'],'validator approval mismatch')
 sys.path.insert(0,str(STAGE2));validator=loadmodule('stage2_candidate_validator',codepaths['validator']);validation=validator.validate(stage2,approval['approved_code'],approval['approved_max_rss_kib'],guard)
 request_path=pinned(cfg['point_request']);req=read(request_path);snapshot_path=pinned(req['snapshot']);snapshot=read(snapshot_path);base=read(stage2['snapshot']['path']);report=read(stage2['report']['path'])
 pins={k:cfg['policy_pins'][k] for k in ('baseline_report_sha256','baseline_rows_sha256','baseline_runs_sha256','baseline_decision_snapshot_sha256','physical_rows_sha256','physical_runs_sha256','component_rows_sha256','component_runs_sha256')}
 expected={'baseline_report_sha256':stage2['report']['sha256'],'baseline_rows_sha256':stage2['rows']['sha256'],'baseline_runs_sha256':stage2['runs']['sha256'],'baseline_decision_snapshot_sha256':stage2['snapshot']['sha256'],**{k+'_sha256':req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}}
 need(pins==expected and req['physical_rows']['sha256']==stage2['physical_rows']['sha256'] and req['physical_runs']['sha256']==stage2['physical_runs']['sha256'] and req['grid']==report['grid'],'point/baseline inputs mismatch')
 compiled=decision_contract.compile_policy(snapshot,base,report,pins,SUPPORTED)
 need(req.get('adapter_sha256')==codes['adapter'],'adapter request pin mismatch')
 if any(a.get('method') in ('source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1') and a.get('affiliation_id') in compiled['affiliation_ids'] for a in snapshot['affiliations']):need(req.get('named_identity_sha256')==codes['named_identity'] and req.get('identity_watch_sha256')==codes['identity_watch'],'named identity request pin mismatch')
 if any(a.get('method') in ('osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1') and a.get('affiliation_id') in compiled['affiliation_ids'] for a in snapshot['affiliations']):need(req.get('osm_node_extractor_sha256')==codes['osm_node_extractor'],'OSM node extractor request pin mismatch')
 if any(a.get('method')=='raw_json_city_named_region_component_v1' and a.get('affiliation_id') in compiled['affiliation_ids'] for a in snapshot['affiliations']):need(req.get('raw_city_extractor_sha256')==codes['raw_city_extractor'],'raw city extractor request pin mismatch')
 sys.path.insert(0,str(POINT));resolver=loadmodule('stage3_point_resolver',codepaths['resolver']);resolution=resolver.resolve(req);need((resolution.get('osm_node_extractor_sha256') is None or resolution.get('osm_node_extractor_sha256')==codes['osm_node_extractor']) and (resolution.get('raw_city_extractor_sha256') is None or resolution.get('raw_city_extractor_sha256')==codes['raw_city_extractor']) and resolution['snapshot_sha256']==req['snapshot']['sha256'] and resolution['input_sha256']=={k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'resolver input mismatch')
 claims=claims_for(compiled,snapshot,resolution);out=Path(cfg['output']).resolve()
 lineage_specs=resolver.lineage_specs(read(pinned(req['component_manifest'])));lineage_paths=[pinned(spec) for spec in lineage_specs]
 sources=[Path(config_path).resolve(),request_path,Path(cfg['stage2_approval']['path']).resolve(),*codepaths.values(),*(Path(s['path']).resolve() for s in stage2.values()),*(Path(req[k]['path']).resolve() for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')),*(Path(s['path']).resolve() for s in req['source_files']),POINT/'adapter.py',POINT.parent/'named-identity-prototype'/'named_identity.py',POINT.parent/'named-identity-prototype'/'identity_watch.py',*lineage_paths]
 need(not out.exists() and out.parent.is_dir() and all(not out.is_relative_to(p.parent) and not p.is_relative_to(out) for p in sources),'output overlaps inputs or code')
 result=writer.write_streams(grid=report['grid'],physical_rows=req['physical_rows']['path'],physical_runs=req['physical_runs']['path'],component_rows=req['component_rows']['path'],component_runs=req['component_runs']['path'],baseline_rows=stage2['rows']['path'],baseline_runs=stage2['runs']['path'],component_claims=claims,mainland_roots=set(report['physical_coverage']['seed_roots']),region_rows=lambda y:[],output=out,guard=guard,disk_reserve_bytes=cfg['minimum_free_bytes'])
 stats=result['affiliation_statistics'];need(set(stats)==set(compiled['affiliation_ids']) and all(v['applied_cells']>0 for v in stats.values()),'selected claim absent from output')
 for k,p in codepaths.items():need(writer.sha(p,guard)==codes[k],'code changed: '+k)
 for s in [cfg['point_request'],cfg['stage2_approval'],*stage2.values(),*([req[k] for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source')]),*({'path':x['path'],'sha256':x['sha256']} for x in req['source_files']),*lineage_specs]:pinned(s)
 with open(config_path,'rb') as f:need(f.read((2<<20)+1)==cfg_bytes,'request changed')
 output={'schema':'stage3-selected-points-land-report-v1','status':'research-awaiting-monitor','publishable':False,'request_sha256':hashlib.sha256(cfg_bytes).hexdigest(),'decision_snapshot_sha256':req['snapshot']['sha256'],'baseline_validation':validation,'policy':compiled,'point_resolution':resolution,'writer':result,'code_sha256':codes,'limitations':['Point identity labels corroborate the witness, not every cell of its physical component. An island-group label does not establish satellite membership.','Only selected supported point-component affiliations are supported; unselected decisions remain unresolved.', 'Document-only identity evidence is hashed but does not independently establish the island claim.', 'A matched guideline excerpt supports a reviewed CRS assertion and does not prove every record datum.','Water cells stay unassigned.','The separate process-group monitor is required; sampling can miss spikes and external disk use can race reserve checks.']}
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
