"""Verify completed, direct-run stage-2 land candidate before V7 comparison.

Research diagnostic only. Hashes establish artifact identity, not independent
Neon authentication or scientific correctness. This does not construct List 1.
"""
import json
from pathlib import Path
import contracts,verify_inputs,build_stage2,orchestrate_stage2,verify_physical_lineage,ural_delta

def validate(pins,approved_code, *, provisional_diagnostic=False):
 names={'report','derived_manifest','outer_config','rows','runs','snapshot','physical_rows','physical_runs','physical_report','physical_lineage_request','physical_lineage_report'}
 contracts.need(isinstance(pins,dict) and set(pins)==names,'exact candidate inputs required')
 paths={}
 for name,spec in pins.items():
  contracts.need(isinstance(spec,dict) and set(spec)=={'path','sha256'} and isinstance(spec['sha256'],str) and contracts.HEX.fullmatch(spec['sha256']),'invalid input pin')
  p=Path(spec['path']).resolve(strict=True);contracts.need(p.is_file() and verify_inputs.sha_file(p)==spec['sha256'],'candidate hash mismatch: '+name);paths[name]=p
 def read(name):return json.loads(verify_inputs.bounded_bytes(paths[name],16<<20))
 report=read('report');derived=read('derived_manifest');outer=read('outer_config');snapshot=read('snapshot');physical=read('physical_report');lineage=read('physical_lineage_report')
 contracts.need(isinstance(approved_code,dict) and set(approved_code)=={'orchestrator','core','core_files','dependency_files','orchestration_files'} and all(isinstance(approved_code.get(k),str) and contracts.HEX.fullmatch(approved_code[k]) for k in ('orchestrator','core')) and all(isinstance(approved_code.get(k),dict) and approved_code[k] for k in ('core_files','dependency_files','orchestration_files')),'complete approved code pins required')
 expected_dependencies={'seed_code_files':set(orchestrate_stage2.SEED_REPORT_NAMES)|{'rasterizer','rasterizer_kernel'},'resolution_code_files':{'resolver','helper','named_identity',},'hint_code_files':{'hints.py','run_diagnostic.py'}}
 expected_orchestration={'orchestrate_stage2.py','representatives.py','build_seed_tiles.py','seed-producer/seed_worker.py'}|{'seed-producer/'+x for x in orchestrate_stage2.SEED_NAMES}|{'hint-producer/'+x for x in orchestrate_stage2.HINT_NAMES}|set(build_stage2.CODE_NAMES)
 valid_digest=lambda x:isinstance(x,str) and contracts.HEX.fullmatch(x) is not None
 dep=approved_code['dependency_files'];contracts.need(set(approved_code['core_files'])==set(build_stage2.CODE_NAMES) and all(valid_digest(x) for x in approved_code['core_files'].values()) and set(approved_code['orchestration_files'])==expected_orchestration and all(valid_digest(x) for x in approved_code['orchestration_files'].values()) and set(dep)==set(expected_dependencies) and all(isinstance(dep[k],dict) and set(dep[k])==names and all(valid_digest(x) for x in dep[k].values()) for k,names in expected_dependencies.items()),'incomplete approved code closure')
 contracts.need(type(provisional_diagnostic) is bool,'invalid diagnostic mode')
 if provisional_diagnostic:
  contracts.need(report.get('schema')=='stage2-source-geodesic-report-v1' and report.get('status')=='stage2-provisional-only' and report.get('publishable') is False and report.get('provisional_only') is True and report.get('orchestration',{}).get('provisional_only') is True and snapshot.get('source')=='local-derived-from-neon-export','exact provisional diagnostic candidate required')
 else:
  contracts.need(report.get('schema')=='stage2-source-geodesic-report-v1' and report.get('status')=='stage2-research-complete' and report.get('publishable') is False and report.get('provisional_only') is not True and report.get('orchestration',{}).get('provisional_only') is not True and snapshot.get('source')=='neon-export','completed research candidate required; provisional-only outputs are not selectable')
 for k,n in (('output_rows_sha256','rows'),('output_runs_sha256','runs'),('decision_snapshot_sha256','snapshot')):contracts.need(report.get(k)==pins[n]['sha256'],'candidate report mismatch: '+k)
 for n in ('physical_rows','physical_runs','physical_report','physical_lineage_request'):contracts.need(report.get('inputs_sha256',{}).get(n)==pins[n]['sha256'],'candidate input mismatch: '+n)
 grid=report.get('grid');outputs=physical.get('physical_output_sha256',physical.get('output_sha256',{}))
 contracts.need(physical.get('status') in ('candidate-only','stage1-complete') and physical.get('grid')==grid and outputs.get('rows.u32le')==pins['physical_rows']['sha256'] and outputs.get('runs.u32le')==pins['physical_runs']['sha256'],'physical report mismatch')
 metric=report.get('distance_policy',{});rev=report.get('decision_revision');entity=report.get('entity_revision');actual,categories,_=contracts.snap_policy(snapshot,rev,entity,metric.get('policy_id'),metric.get('version'))
 policy=report.get('land_baseline_policy');contracts.need(actual==metric and isinstance(policy,dict) and policy==snapshot.get('land_baseline_policy') and policy.get('execution_status')=='selected_for_research' and policy.get('decision_revision')==rev and policy.get('distance_policy_id')==metric.get('policy_id') and policy.get('distance_policy_version')==metric.get('version'),'selected policy mismatch');contracts.policy_tolerance_metres(policy)
 contracts.validate_simple_policy(policy,rev,metric)
 contracts.need(contracts.grids_equal(policy['grid'],grid) and all(policy[k+'_sha256']==pins[k]['sha256'] for k in ('physical_rows','physical_runs','physical_report')),'selected policy physical/grid mismatch')
 contracts.need(report.get('physical_lineage_report_sha256')==pins['physical_lineage_report']['sha256'] and report.get('physical_lineage_status')=='selected-sources-match-reported-lineage' and derived.get('physical_lineage_report',{}).get('sha256')==pins['physical_lineage_report']['sha256'] and report.get('orchestration',{}).get('physical_lineage_report',{}).get('sha256')==pins['physical_lineage_report']['sha256'],'physical lineage report binding mismatch')
 verified=verify_physical_lineage.validate_combined(snapshot,pins['snapshot']['sha256'],paths['physical_lineage_request'],pins['physical_report']['sha256'],pins['physical_rows']['sha256'],pins['physical_runs']['sha256'],grid);contracts.need(verified==lineage,'physical lineage verification mismatch')
 contracts.need(report.get('categories')=={str(k):v for k,v in categories.items()},'category report mismatch')
 delta=ural_delta.compile_rule(snapshot,categories,grid);delta_report=report.get('ural_delta')
 contracts.need(isinstance(delta_report,dict) and all(delta_report.get(k)==delta[v] for k,v in (
  ('schema','schema'),('revision','revision'),('boundary_id','boundary_id'),
  ('boundary_sha256','boundary_sha256'),('route_id','route_id'),
  ('route_sha256','route_sha256'),('scope_bounds','scope_bounds'),
  ('europe_code','europe_code'),('asia_code','asia_code'))) and
  delta_report.get('status')=='applied-to-land-cell-centers','Ural delta report/selection mismatch')
 counts=delta_report.get('counts')
 contracts.need(isinstance(counts,dict) and set(counts)=={'land_centers','other_land_labels','europe_to_asia','asia_to_europe'} and all(type(counts[k]) is int and counts[k]>=0 for k in counts) and counts['land_centers']>0 and counts['other_land_labels']==0 and counts['europe_to_asia']+counts['asia_to_europe']<=counts['land_centers'],'invalid Ural delta counts')
 orchfiles=approved_code['orchestration_files'];corefiles=approved_code['core_files'];resolver_paths={'resolver':'v7-land/mainland-witness-prototype/resolve_mainland.py','helper':'v7-land/point-component-prototype/resolve.py','named_identity':'v7-land/named-identity-prototype/named_identity.py'}
 contracts.need(all(orchfiles[k]==v for k,v in corefiles.items()) and all(orchfiles['seed-producer/'+k]==dep['seed_code_files'][k] for k in orchestrate_stage2.SEED_REPORT_NAMES) and all(orchfiles['hint-producer/'+k]==v for k,v in dep['hint_code_files'].items()) and all(orchfiles[path]==dep['resolution_code_files'][k] for k,path in resolver_paths.items()),'approved code closure inconsistent')
 artifacts=derived.get('artifacts');expected_artifacts={'resolution_report','seed_rows','seed_runs','seed_report','hint_roots','hint_codes','hint_report','tile_manifest','representatives'}
 contracts.need(isinstance(artifacts,dict) and set(artifacts)==expected_artifacts and all(isinstance(artifacts[k],dict) and artifacts[k].get('sha256')==report.get('inputs_sha256',{}).get(k) and valid_digest(artifacts[k].get('sha256')) for k in expected_artifacts),'derived artifact/report mismatch')
 for k in ('resolution_report','seed_report','hint_report'):contracts.need(report.get(k+'_sha256')==artifacts[k]['sha256'],'derived report mismatch: '+k)
 orch=report.get('orchestration',{});contracts.need(isinstance(orch,dict) and orch.get('outer_config_sha256')==pins['outer_config']['sha256'] and outer.get('schema')=='stage2-fresh-orchestration-v1' and orch.get('orchestrator_sha256')==approved_code['orchestrator'] and orch.get('derived_manifest',{}).get('sha256')==pins['derived_manifest']['sha256'] and report.get('code_sha256')==approved_code['core_files'] and approved_code['core_files'].get('build_stage2.py')==approved_code['core'] and report.get('dependency_sha256')==approved_code['dependency_files'] and derived.get('schema')=='stage2-fresh-derived-v1' and derived.get('outer_config_sha256')==orch.get('outer_config_sha256') and derived.get('orchestrator_sha256')==approved_code['orchestrator'] and derived.get('code_sha256')==approved_code['orchestration_files'] and approved_code['orchestration_files'].get('orchestrate_stage2.py')==approved_code['orchestrator'] and derived.get('provisional_only',False) is provisional_diagnostic and orch.get('provisional_only',False) is provisional_diagnostic,'candidate code/derivation mismatch')
 for spec in pins.values():contracts.need(verify_inputs.sha_file(spec['path'])==spec['sha256'],'candidate changed during validation')
 return {'schema':'stage2-candidate-validation-v1','status':('provisional-diagnostic-candidate-bound' if provisional_diagnostic else 'diagnostic-candidate-bound'),'provisional_only':provisional_diagnostic,'publishable':False,'original_report_status':report['status'],'report_sha256':pins['report']['sha256'],'grid':grid,'decision_revision':rev,'entity_revision':entity,'output_rows_sha256':pins['rows']['sha256'],'output_runs_sha256':pins['runs']['sha256'],'physical_rows_sha256':pins['physical_rows']['sha256'],'physical_runs_sha256':pins['physical_runs']['sha256'],'limitations':['Hashes do not authenticate the Neon export or independently prove source geography.','The downstream comparator must validate complete RLE/physical coverage.','Physical-mask differences from V7 must be counted separately.','Research candidate only; no List 1 decision or public release is implied.']}
