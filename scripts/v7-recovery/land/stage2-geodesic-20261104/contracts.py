"""Strict stage-2 input-chain validation; no historical assignment or checkpoint."""
from decimal import Decimal,InvalidOperation
import hashlib,json,math,re
HEX=re.compile(r'^[0-9a-f]{64}$')

def need(ok,msg):
 if not ok:raise ValueError(msg)
def text(v):return isinstance(v,str) and bool(v.strip())
def snap_policy(snapshot,revision,entity_revision,policy_id,policy_version):
 need(snapshot.get('schema')=='worldatlas-geography-decision-draft-evidence-v1' and snapshot.get('source')=='neon-export','draft Neon export required')
 dr=snapshot.get('decision_revision',{});er=snapshot.get('entity_revision',{})
 need(dr.get('id')==revision and er.get('id')==entity_revision and dr.get('entity_revision')==entity_revision and dr.get('status')=='draft' and er.get('status')=='draft','snapshot revision mismatch')
 policies=snapshot.get('distance_policies');need(isinstance(policies,list),'distance policies missing')
 selected=[x for x in policies if isinstance(x,dict) and x.get('policy_id')==policy_id and x.get('version')==policy_version and x.get('execution_status')=='selected_for_research']
 need(len(selected)==1 and selected[0].get('decision_revision')==revision,'selected distance policy missing or ambiguous');metric=selected[0]
 try:valid=metric.get('algorithm')=='wgs84_ellipsoidal_geodesic_inverse' and metric.get('units')=='metres' and Decimal(str(metric.get('semi_major_axis_m')))==Decimal('6378137') and Decimal(str(metric.get('inverse_flattening')))==Decimal('298.257223563')
 except InvalidOperation:valid=False
 need(valid,'unsupported geodesic policy')
 entities=snapshot.get('entities');bindings=snapshot.get('category_bindings');need(isinstance(entities,list) and isinstance(bindings,list),'category metadata missing')
 ent={}
 for e in entities:
  need(isinstance(e,dict) and type(e.get('id')) is int and e['id'] not in ent and text(e.get('name')),'invalid entity');ent[e['id']]=e
 land=[b for b in bindings if isinstance(b,dict) and b.get('physical_class')=='land'];codes={};entity_codes={}
 for b in land:
  code,eid=b.get('code'),b.get('entity_id');need(type(code) is int and code not in codes and type(eid) is int and eid in ent and ent[eid].get('level')=='continent' and eid not in entity_codes,'invalid land category bindings');codes[code]=ent[eid]['name'];entity_codes[eid]=code
 need(set(codes)==set(range(17,23)) and len(set(codes.values()))==6,'unsupported category encoding')
 return metric,codes,entity_codes

def resolution_roots(report,grid,pins,revision,entity_revision):
 need(report.get('schema')=='mainland-witness-resolution-v1' and report.get('status')=='selected-research-identity-claims-not-mainland-proof' and report.get('publishable') is False,'invalid mainland resolution')
 for k,v in {'grid':grid,'decision_revision':revision,'entity_revision':entity_revision,'snapshot_sha256':pins['decision_snapshot'],'component_manifest_sha256':pins['component_manifest'],'input_sha256':{x:pins[x] for x in ('physical_rows','physical_runs','component_rows','component_runs')}}.items():need(report.get(k)==v,'stale resolution binding: '+k)
 groups=report.get('groups');need(isinstance(groups,list) and 1<=len(groups)<=64,'invalid mainland groups');out={};roots=set()
 for g in groups:
  need(isinstance(g,dict) and text(g.get('group_id')) and g['group_id'] not in out and g.get('role') in ('mainland','sentinel'),'invalid mainland group')
  root=g.get('component_id_current_generation_only');targets=g.get('target_entity_ids');need(type(root) is int and 0<=root<2**32-1 and root not in roots and isinstance(targets,list) and len(set(targets))==len(targets) and (g['role']=='mainland')==bool(targets),'invalid group root or targets')
  roots.add(root);out[g['group_id']]=g
 need(any(g['role']=='mainland' for g in out.values()),'no selected mainland roots')
 return out

def component_manifest(manifest,grid,pins):
 need(manifest.get('schema')=='single-generation-component-manifest-v1' and manifest.get('status')=='complete-research' and manifest.get('grid')==grid,'fresh component manifest required')
 for k in ('physical_rows','physical_runs','component_rows','component_runs'):need(manifest.get('pins',{}).get(k,{}).get('sha256')==pins[k],'component manifest mismatch: '+k)
 need(manifest.get('component_source_sha256')==pins['component_source'] and manifest.get('builder_binary_sha256')==pins['component_builder_binary'] and manifest.get('builder_binary',{}).get('sha256')==pins['component_builder_binary'] and manifest.get('physical_report',{}).get('sha256')==pins['physical_report'] and text(manifest.get('compiler_version')) and text(manifest.get('builder_output')),'component builder provenance mismatch')

def seed_report(report,grid,pins,revision,entity_revision,groups,entity_codes,seed_code_hashes):
 need(report.get('schema')=='worldatlas-stage2-mainland-seed-report-v1' and report.get('status')=='diagnostic-seed-pending-independent-provenance' and report.get('publishable') is False and report.get('grid')==grid,'fresh diagnostic stage-2 seed and matching grid required')
 expected={'decision_snapshot_sha256':pins['decision_snapshot'],'resolution_report_sha256':pins['resolution_report'],'physical_rows_sha256':pins['physical_rows'],'physical_runs_sha256':pins['physical_runs'],'component_rows_sha256':pins['component_rows'],'component_runs_sha256':pins['component_runs'],'component_manifest_sha256':pins['component_manifest'],'physical_report_sha256':pins['physical_report'],'seed_rows_sha256':pins['seed_rows'],'seed_runs_sha256':pins['seed_runs'],'decision_revision':revision,'entity_revision':entity_revision}
 for k,v in expected.items():need(report.get(k)==v,'seed report mismatch: '+k)
 need(report.get('physical_code_contract')=={'water':1,'land':17},'seed physical code contract mismatch')
 expected_roots=sorted(g['component_id_current_generation_only'] for g in groups.values() if g['role']=='mainland')
 need(report.get('seed_roots')==expected_roots and report.get('code_sha256')==seed_code_hashes and bool(seed_code_hashes),'seed roots or code provenance mismatch')
 rules,traces=report.get('seed_rules'),report.get('region_traces');need(isinstance(rules,list) and rules and isinstance(traces,list) and traces,'seed rules and region traces required')
 for r in rules:
  need(isinstance(r,dict) and set(r)=={'rule_id','group_id','component_id_current_generation_only','region_id','inside_entity_id','outside_entity_id','inside_code','outside_code'} and text(r['rule_id']) and r['group_id'] in groups and groups[r['group_id']]['role']=='mainland' and r['component_id_current_generation_only']==groups[r['group_id']]['component_id_current_generation_only'],'seed rule group mismatch')
  for side in ('inside','outside'):need(r[side+'_entity_id'] in groups[r['group_id']]['target_entity_ids'] and entity_codes.get(r[side+'_entity_id'])==r[side+'_code'],'seed rule entity/code mismatch')
 for t in traces:need(isinstance(t,dict) and t.get('revision_id')==revision and text(t.get('region_id')) and isinstance(t.get('geometry_sha256'),str) and HEX.fullmatch(t['geometry_sha256']) and isinstance(t.get('input_trace'),list) and t['input_trace'] and text(t.get('method')),'invalid region trace')
 return expected_roots

def hints_report(report,grid,pins,revision,entity_revision,metric,seed_roots,hint_code_hashes):
 need(report.get('schema')=='source-only-hints-diagnostic-report-v1' and report.get('status')=='diagnostic-not-independently-authenticated' and report.get('publishable') is False and report.get('synthetic_fixture') is not True,'invalid hints report')
 need(report.get('grid')==grid and report.get('decision_revision')==revision and report.get('entity_revision')==entity_revision and report.get('distance_policy')==metric and report.get('seed_roots')==seed_roots,'hints policy/revision mismatch')
 for k in ('physical_rows','physical_runs','component_rows','component_runs','seed_rows','seed_runs','representatives','tile_manifest','resolution_report','decision_snapshot','component_manifest'):need(report.get('inputs_sha256',{}).get(k)==pins[k],'stale hint input: '+k)
 need(report.get('roots_sha256')==pins['hint_roots'] and report.get('hints_sha256')==pins['hint_codes'] and type(report.get('root_count')) is int and 0<report['root_count']<2**32 and report.get('code_sha256')==hint_code_hashes,'hints artifact/code mismatch')
 return report['root_count']

def policy_tolerance_metres(policy):
 value=policy.get('tie_tolerance_metres') if isinstance(policy,dict) else None
 need(type(value) in (int,float,str),'invalid selected tie tolerance')
 try:
  dec=Decimal(str(value));need(dec.is_finite() and dec>=0,'invalid selected tie tolerance');result=float(dec)
  need(result<float('inf') and (result!=0.0 or dec==0),'invalid selected tie tolerance')
 except (InvalidOperation,OverflowError,ValueError):raise ValueError('invalid selected tie tolerance') from None
 return result

def grid_numeric(grid):
 need(isinstance(grid,dict) and set(grid)=={'width','height','west','north','step'} and type(grid['width']) is int and type(grid['height']) is int and grid['width']>1 and grid['height']>0,'invalid selected policy grid')
 try:
  values=[]
  for key in ('west','north','step'):
   value=grid[key];need(type(value) in (int,float,str),'invalid selected policy grid');d=Decimal(str(value));need(d.is_finite(),'invalid selected policy grid');values.append(d)
  west,north,step=values;need(west==Decimal(-180) and north==Decimal(90) and step>0 and step*grid['width']==Decimal(360) and step*grid['height']<=Decimal(180),'invalid selected policy grid')
 except (InvalidOperation,OverflowError,ValueError):raise ValueError('invalid selected policy grid') from None
 return (grid['width'],grid['height'],west,north,step)

def grids_equal(a,b):return grid_numeric(a)==grid_numeric(b)

def validate_simple_policy(policy,revision,metric):
 need(isinstance(policy,dict) and policy.get('decision_revision')==revision and policy.get('execution_status')=='selected_for_research' and text(policy.get('policy_id')) and text(policy.get('version')) and policy.get('island_overrides')=='none','missing selected simple land policy')
 for k,v in {'distance_policy_id':metric.get('policy_id'),'distance_policy_version':metric.get('version'),'connectivity':'four_neighbor_longitude_wrapped','aggregation':'minimum_over_component_and_mainland_cells','endpoints':'physical_land_cell_centers','tie':'lowest_category_code'}.items():need(policy.get(k)==v,'land policy mismatch: '+k)
 policy_tolerance_metres(policy)
 grid_numeric(policy.get('grid'))
 need(all(isinstance(policy.get(k),str) and HEX.fullmatch(policy[k]) for k in ('physical_rows_sha256','physical_runs_sha256','physical_report_sha256')),'missing selected physical pins')

# Deliberate allowlist: unknown relationships require a reviewed contract update.
SUPPORTING_RELATIONSHIPS = frozenset(['independent_original_terrain_research_not_watershed_or_construction_proof', 'independent_terrain_research_anapa_not_full_watershed_verification_or_construction', 'independent_terrain_research_east_not_watershed_verification_or_construction', 'independent_terrain_research_east_original_not_watershed_verification_or_construction', 'independent_terrain_research_sections_2_3_not_watershed_verification_or_construction', 'independent_terrain_research_west_original_not_watershed_verification_or_construction', 'research_comparison_evidence_not_independent_verification_or_proof_of_construction', 'secondary_terrain_points_not_independent_of_srtm_or_watershed_validation', 'srtm_cross_sensor_research_not_independent_hydrobasins_or_watershed_verification', 'supporting research evidence only; not production geometry selection', 'supporting_geographic_evidence_not_complete_construction_lineage', 'temporary research-only named-waterway corroboration; not a selected pipeline input', 'terrain_quality_mask_for_eastern_research', 'historical_relation_membership_support_not_complete_coordinate_lineage', 'historical_way_membership_support_not_complete_coordinate_lineage', 'companion_mask_for_independent_terrain_screen', 'current_mainstream_source_comparison_not_historical_bytes_or_terrain_proof', 'independent_terrain_screen_mask_zero_only_not_proof_of_divide', 'local_geographic_comparison_not_terrain_or_construction_proof'])
CONSTRUCTION_RELATIONSHIP = "construction_input"



def validate_selected_seed_decisions(snapshot,seed,groups,entity_codes,metric,guard=lambda:None):
 """Provisional strict v1 crosswalk; execution remains gated externally.

 Verify selected policy, component rules, geometry traces, source citations and
 proof pins independently of the producer's self-reported decision IDs.
 """
 guard();rev=snapshot.get('decision_revision',{}).get('id');policy=snapshot.get('land_baseline_policy')
 validate_simple_policy(policy,rev,metric)
 need(grids_equal(policy['grid'],seed.get('grid')) and all(policy[k]==seed.get(k) for k in ('physical_rows_sha256','physical_runs_sha256','physical_report_sha256')),'selected policy physical/grid mismatch')
 def selected_ids(name):
  x=policy.get(name);need(isinstance(x,list) and all(text(y) for y in x) and len(x)==len(set(x)),'invalid selected IDs: '+name);return x
 rule_ids=selected_ids('mainland_rule_ids');region_ids=selected_ids('region_ids');boundary_ids=selected_ids('boundary_ids');route_ids=selected_ids('route_ids');need(bool(rule_ids),'no selected mainland rules')
 def index(name,key):
  rows=snapshot.get(name);need(isinstance(rows,list) and len(rows)<=10000,'invalid decision array: '+name);out={}
  for r in rows:need(isinstance(r,dict) and text(r.get(key)) and r[key] not in out,'duplicate/invalid '+name);out[r[key]]=r
  return out
 rules=index('mainland_component_rules','rule_id');regions=index('seed_regions','region_id');boundaries=index('mainland_boundaries','boundary_id');routes=index('routes','route_id')
 need(all(x in rules for x in rule_ids) and all(x in regions for x in region_ids) and all(x in boundaries for x in boundary_ids) and all(x in routes for x in route_ids),'missing selected rule or geometry')
 generated=[];used_groups=set();used_regions=set()
 for rid in rule_ids:
  r=rules[rid];need(set(r)=={'rule_id','decision_revision','execution_status','group_id','region_id','inside_entity_id','outside_entity_id'} and r['decision_revision']==rev and r['execution_status']=='selected_for_research','invalid selected component rule')
  gid=r['group_id'];g=groups.get(gid);a,b=r['inside_entity_id'],r['outside_entity_id'];region=r['region_id']
  need(isinstance(g,dict) and g.get('role')=='mainland' and gid not in used_groups and set(g.get('target_entity_ids',[]))=={a,b} and a in entity_codes and b in entity_codes,'rule group/category mismatch')
  if region is None:need(a==b,'unpartitioned rule has unequal targets')
  else:need(region in region_ids and a!=b,'invalid selected partition');used_regions.add(region)
  used_groups.add(gid);generated.append({'rule_id':rid,'group_id':gid,'component_id_current_generation_only':g['component_id_current_generation_only'],'region_id':region,'inside_entity_id':a,'outside_entity_id':b,'inside_code':entity_codes[a],'outside_code':entity_codes[b]})
 need(used_groups=={k for k,v in groups.items() if v.get('role')=='mainland'} and used_regions==set(region_ids) and {x for r in generated for x in (r['inside_code'],r['outside_code'])}==set(entity_codes.values()),'unused group, region or land category')
 need(seed.get('seed_rules')==generated,'seed rules differ from selected decisions')
 traces=seed.get('region_traces');need(isinstance(traces,list) and len(traces)==len(region_ids),'seed region trace count mismatch');trace_by={}
 for t in traces:need(isinstance(t,dict) and text(t.get('region_id')) and t['region_id'] not in trace_by,'duplicate region trace');trace_by[t['region_id']]=t
 need(set(trace_by)==set(region_ids),'seed region trace IDs mismatch')
 sources=snapshot.get('sources');need(isinstance(sources,list),'missing source catalog');source_by={}
 for source in sources:
  need(isinstance(source,dict) and text(source.get('source_id')) and text(source.get('version')),'invalid source');key=(source['source_id'],source['version']);need(key not in source_by,'duplicate source');source_by[key]=source
 assets=snapshot.get('source_lineage_assets');dependencies=snapshot.get('source_lineage_dependencies');need(isinstance(assets,list) and isinstance(dependencies,list),'missing raw source lineage');asset_by={}
 for asset in assets:
  need(isinstance(asset,dict) and text(asset.get('source_id')) and text(asset.get('version')),'invalid source lineage');key=(asset['source_id'],asset['version']);need(key not in asset_by,'duplicate source lineage');asset_by[key]=asset
 need(all(isinstance(x,dict) and text(x.get('source_id')) and text(x.get('version')) for x in dependencies),'invalid source dependency')
 derived={(x['source_id'],x['version']) for x in dependencies}
 def geom(g):
  need(isinstance(g,dict) and set(g)=={'type','coordinates'} and g['type']=='LineString' and isinstance(g['coordinates'],list) and 2<=len(g['coordinates'])<=200000,'invalid stored geometry')
  try:
   pts=[]
   for n,p in enumerate(g['coordinates']):
    if n%1024==0:guard()
    need(isinstance(p,list) and len(p)==2 and all(type(x) in (int,float,str) and not isinstance(x,bool) for x in p),'invalid geometry coordinate')
    pts.append([Decimal(str(p[0])),Decimal(str(p[1]))])
   need(len(pts)==len(g['coordinates']) and all(x.is_finite() and y.is_finite() and -180<=x<=180 and -90<=y<=90 for x,y in pts),'invalid geometry coordinate')
  except (InvalidOperation,ValueError,OverflowError):raise ValueError('invalid geometry coordinate') from None
  need(all(a!=b and abs(a[0]-b[0])<=180 for a,b in zip(pts,pts[1:])),'duplicate vertex or unsupported antimeridian geometry')
  return pts
 def geomhash(pts,kind='LineString'):
  coords=[[float(x),float(y)] for x,y in pts];coords=[coords] if kind=='Polygon' else coords
  return hashlib.sha256(json.dumps({'type':kind,'coordinates':coords},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 used_b=set();used_r=set();pins=seed.get('input_sha256',{});need(isinstance(pins,dict) and all(isinstance(pins.get(k),str) and HEX.fullmatch(pins[k]) for k in ('physical_rows','physical_runs','physical_report','closure_contract','closure_checker','terminal_checker')),'seed input pins missing')
 for region_id in region_ids:
  guard();r=regions[region_id];t=trace_by[region_id];need(r.get('decision_revision')==rev and r.get('execution_status')=='selected_for_research' and r.get('geometry_hash_method')=='binary64-sorted-compact-geojson-v1' and t.get('revision_id')==rev and t.get('geometry_sha256')==r.get('geometry_sha256') and isinstance(r.get('segments'),list) and isinstance(t.get('input_trace'),list) and len(r['segments'])==len(t['input_trace']),'region decision/trace mismatch')
  ring=[]
  for segment,trace in zip(r['segments'],t['input_trace']):
   guard();need(isinstance(segment,dict) and set(segment)=={'kind','id','start','end','reverse'} and isinstance(trace,dict) and all(trace.get(k)==segment[k] for k in segment),'region segment/trace mismatch')
   kind,rid=segment['kind'],segment['id'];need(kind in ('boundary','route'),'unsupported selected geometry');record=(boundaries if kind=='boundary' else routes).get(rid);allowed=boundary_ids if kind=='boundary' else route_ids
   need(rid in allowed and isinstance(record,dict) and record.get('decision_revision')==rev and record.get('execution_status')=='selected_for_research' and record.get('geometry_hash_method')=='binary64-sorted-compact-geojson-v1','stale selected geometry');pts=geom(record.get('geometry'));need(geomhash(pts)==record.get('geometry_sha256')==trace.get('geometry_sha256'),'geometry hash mismatch')
   a,b=segment['start'],segment['end'];need(type(a) is int and type(b) is int and type(segment['reverse']) is bool and 0<=a<b<=len(pts) and b-a>=2,'invalid geometry slice');selected=pts[a:b];selected=selected[::-1] if segment['reverse'] else selected
   need(not ring or ring[-1]==selected[0],'selected region segments do not join exactly');ring.extend(selected if not ring else selected[1:]);need(len(ring)<=250000,'selected region vertex limit exceeded')
   if kind=='boundary':
    used_b.add(rid);need(record.get('method')=='stored_linestring_v1' and record.get('coordinate_reference')=='OGC:CRS84','unsupported boundary method');prov=record.get('provenance',{});refs=prov.get('source_refs');need(isinstance(refs,list) and refs and prov.get('lineage_status') in ('complete','incomplete') and trace.get('lineage_status')==prov['lineage_status'] and trace.get('closure_proof') is None and trace.get('route_provenance') is None,'invalid boundary provenance');cit=[]
    relationships=prov.get('source_relationships');need(isinstance(relationships,list) and len(relationships)==len(refs),'boundary source relationships missing');relmap={}
    for item in relationships:
     need(isinstance(item,dict) and set(item)=={'source_id','version','relationship'} and text(item['source_id']) and text(item['version']) and text(item['relationship']),'invalid boundary source relationship');key=(item['source_id'],item['version']);relationship=item['relationship'];need(key not in relmap and relationship in SUPPORTING_RELATIONSHIPS|{CONSTRUCTION_RELATIONSHIP},'duplicate or unsupported boundary source relationship');relmap[key]=relationship
    used_refs=set();construction_count=0
    for ref in refs:
     need(isinstance(ref,dict) and set(ref)=={'source_id','version'} and (ref['source_id'],ref['version']) in source_by,'invalid boundary source');key=(ref['source_id'],ref['version']);need(key not in used_refs and key in relmap,'boundary source relationship mismatch');used_refs.add(key);source=source_by[key];asset=asset_by.get(key);need(isinstance(asset,dict) and key not in derived and asset.get('kind')=='raw' and text(asset.get('provider')) and text(asset.get('source_uri')) and all(asset.get(k)==source.get(k) for k in ('sha256','r2_bucket','r2_key','size_bytes')) and isinstance(source.get('sha256'),str) and HEX.fullmatch(source['sha256']) and text(source.get('r2_bucket')) and text(source.get('r2_key')) and type(source.get('size_bytes')) is int and source['size_bytes']>0,'invalid raw source custody')
     relationship=relmap[key];role='construction_input' if relationship==CONSTRUCTION_RELATIONSHIP else 'supporting_research_evidence'
     if role=='construction_input':
      ap=asset.get('provenance');need(isinstance(ap,dict) and ap.get('representation')=='provider_original' and text(ap.get('origin')),'invalid construction source provenance');construction_count+=1
     cit.append({'source_id':ref['source_id'],'version':ref['version'],'relationship':relationship,'role':role,'sha256':source.get('sha256'),'bucket':source.get('r2_bucket'),'key':source.get('r2_key')})
    need(used_refs==set(relmap) and (prov.get('lineage_status')!='complete' or construction_count>0),'boundary lineage or source relationship mismatch')
    need(trace.get('source_citations')==cit,'boundary citations mismatch')
   else:
    used_r.add(rid);proof=trace.get('closure_proof');method=record.get('closure_method');prov=record.get('provenance');need(record.get('route_type')=='stored_linestring_v1' and record.get('coordinate_reference')=='OGC:CRS84' and record.get('role')=='water_closure' and method in ('physical_water_closure_v1','physical_terminal_closure_v1') and isinstance(prov,dict) and trace.get('route_provenance')==prov and trace.get('lineage_status')==prov.get('lineage_status') and prov.get('lineage_status') in ('complete','incomplete'),'route provenance mismatch')
    refs=prov.get('source_refs');selected_sources=snapshot.get('stage1_source_inputs');need(isinstance(refs,list) and isinstance(selected_sources,list) and all(isinstance(x,dict) and set(x)=={'source_id','version'} for x in refs),'route source refs missing')
    selected_keys={(x.get('source_id'),x.get('source_version')) for x in selected_sources if isinstance(x,dict) and x.get('decision_revision')==rev and x.get('execution_status')=='selected_for_research'};need(len(refs)==len(selected_keys) and {(x['source_id'],x['version']) for x in refs}==selected_keys,'route source selection mismatch');cit=[]
    for ref in refs:
     key=(ref['source_id'],ref['version']);src=source_by.get(key);asset=asset_by.get(key);need(isinstance(src,dict) and isinstance(asset,dict) and key not in derived and asset.get('kind')=='raw' and all(src.get(k)==asset.get(k) for k in ('sha256','r2_bucket','r2_key','size_bytes')) and isinstance(src.get('sha256'),str) and HEX.fullmatch(src['sha256']) and text(src.get('r2_bucket')) and text(src.get('r2_key')) and isinstance(asset.get('provenance'),dict) and text(asset['provenance'].get('origin')),'invalid route source custody');cit.append({'source_id':key[0],'version':key[1],'sha256':src['sha256'],'bucket':src['r2_bucket'],'key':src['r2_key'],'origin':asset['provenance']['origin']})
    need(trace.get('source_citations')==cit and all(prov.get(k+'_sha256')==pins.get(k) for k in ('physical_rows','physical_runs','physical_report')) and prov.get('contract_sha256')==pins.get('closure_contract') and prov.get('checker_sha256')==pins.get('terminal_checker' if method=='physical_terminal_closure_v1' else 'closure_checker'),'route source/provenance mismatch')
    need(isinstance(proof,dict) and proof.get('status')=='valid' and proof.get('geometry_sha256')==geomhash(selected) and proof.get('physical_rows_sha256')==pins.get('physical_rows') and proof.get('physical_runs_sha256')==pins.get('physical_runs') and proof.get('physical_report_sha256')==pins.get('physical_report') and proof.get('contract_sha256')==pins.get('closure_contract'),'closure proof mismatch')
    if method=='physical_water_closure_v1':need(proof.get('schema')=='physical-water-closure-proof-v1' and proof.get('checker_sha256')==pins.get('closure_checker'),'water closure checker mismatch')
    else:
     need(a==0 and b==len(pts) and proof.get('schema')=='physical-terminal-closure-proof-v1' and proof.get('checker_sha256')==pins.get('terminal_checker') and proof.get('support_checker_sha256')==pins.get('closure_checker') and proof.get('no_land_land_edge_touched') is True,'terminal closure checker mismatch')
     for out_side,in_side in zip(('start','end'),(('end','start') if segment['reverse'] else ('start','end'))):
      ref=record.get(in_side+'_terminal');need(isinstance(ref,dict) and set(ref)=={'boundary_id','endpoint'} and ref['boundary_id'] in boundary_ids and ref['endpoint'] in ('start','end'),'invalid closure terminal');br=boundaries[ref['boundary_id']];bp=geom(br.get('geometry'));need(geomhash(bp)==br.get('geometry_sha256')==proof.get(out_side+'_geometry_sha256') and proof.get(out_side+'_endpoint')==ref['endpoint'] and selected[0 if out_side=='start' else -1]==bp[0 if ref['endpoint']=='start' else -1],'terminal boundary mismatch')
  need(len(ring)>=4 and ring[0]==ring[-1] and all(abs(a[0]-b[0])<=180 for a,b in zip(ring,ring[1:])) and geomhash(ring,'Polygon')==r.get('geometry_sha256'),'selected region polygon hash/closure mismatch')
 need(used_b==set(boundary_ids) and used_r==set(route_ids),'unused selected boundary or route')
 return policy
