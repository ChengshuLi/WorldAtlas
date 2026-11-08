"""Bind a completed selected-mixed research land report to water inputs.

Checks artifact identity and declared lineage, not independent scientific validation,
Neon authentication, complete source replay, or publication approval. The producer report binds and locates its request, so no water-side locator
or historical-path adapter is required.
"""
import hashlib,json
from pathlib import Path

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def need(v,message):
 if not v:raise ValueError(message)
def read(p):return json.loads(Path(p).read_bytes())
def digest(x):return isinstance(x,str) and len(x)==64 and all(c in '0123456789abcdef' for c in x)
def digest_map(value):
 """Validate nonempty code groups recursively, including every digest leaf."""
 return isinstance(value,dict) and bool(value) and all(isinstance(k,str) and bool(k) and (digest_map(v) if isinstance(v,dict) else digest(v)) for k,v in value.items())
def pinned(spec,root):
 need(isinstance(spec,dict) and isinstance(spec.get('path'),str),'missing lineage path')
 d=spec.get('sha256');need(isinstance(d,str) and len(d)==64 and all(x in '0123456789abcdef' for x in d),'invalid lineage hash')
 p=Path(spec['path']).resolve(strict=True);need(p.is_file() and p.is_relative_to(root),'lineage path outside input root or missing')
 need(sha(p)==d,'lineage artifact hash mismatch: '+str(p));return p

def validate(report,report_path,physical,land,snapshot_hash,revision,input_root,physical_report_sha=None):
 root=Path(input_root).resolve();rp=Path(report_path).resolve();need(rp.is_relative_to(root),'mixed report outside input root')
 side=report.get('input_lineage',{});need(side.get('schema')=='water-selected-mixed-lineage-v1','missing producer input lineage')
 config_path=pinned(side.get('request'),root);need(sha(config_path)==report.get('request_sha256'),'mixed request mismatch');cfg=read(config_path)
 diagnostic=report.get('schema')=='stage3-provisional-diagnostic-land-report-v1'
 if diagnostic:
  need(side.get('mode')=='explicit-provisional-diagnostic' and cfg.get('schema')=='stage3-provisional-diagnostic-request-v1' and cfg.get('diagnostic_only') is True and cfg.get('publishable') is False and report.get('status')=='provisional-profiling-only-not-publishable' and report.get('publishable') is False and report.get('provisional_only') is True,'explicit nonpublishable diagnostic opt-in required')
 else:
  need(cfg.get('schema')=='stage3-selected-mixed-request-v1' and report.get('schema')=='stage3-selected-mixed-land-report-v1' and report.get('status')=='research-awaiting-review' and report.get('publishable') is False,'mixed report is not a completed research candidate')
 need(Path(cfg['output']).resolve()==rp.parent,'mixed output location mismatch')
 region=report.get('regional_island_rule');rr=cfg.get('regional',{}).get('request',{})
 if diagnostic:
  need(isinstance(region,dict) and region.get('status')=='research-profiling-standin' and rr.get('profiling_standin') is True and rr.get('pending_inventory_complete') is False and region.get('provenance',{}).get('profiling_standin') is True and region.get('provenance',{}).get('pending_inventory_complete') is False,'diagnostic regional profiling flags mismatch')
 else:
  need(isinstance(region,dict) and region.get('status')=='research-awaiting-review' and rr.get('profiling_standin') is False and rr.get('pending_inventory_complete') is True and region.get('provenance',{}).get('profiling_standin') is False and region.get('provenance',{}).get('pending_inventory_complete') is True,'profiling or incomplete regional result cannot drive requested full map')
 s=cfg['stage2'];req=read(pinned(cfg['point_request'],root));snap=read(pinned(req['snapshot'],root))
 need(report.get('decision_snapshot_sha256')==req['snapshot']['sha256'] and region.get('provenance',{}).get('decision_snapshot_sha256')==req['snapshot']['sha256'],'regional snapshot mismatch')
 base=read(pinned(s['snapshot'],root));baseline=read(pinned(s['report'],root));pinned(s['rows'],root);pinned(s['runs'],root)
 need(s['snapshot']['sha256']==snapshot_hash and all(base.get('decision_revision',{}).get(k)==revision.get(k) for k in ('id','status','entity_revision')),'base land snapshot or revision mismatch')
 if diagnostic:
  need(baseline.get('schema')=='stage2-source-geodesic-report-v1' and baseline.get('status')=='stage2-provisional-only' and baseline.get('publishable') is False and baseline.get('provisional_only') is True and baseline.get('orchestration',{}).get('provisional_only') is True,'genuine provisional Stage 2 required')
 else:
  need(baseline.get('schema')=='stage2-source-geodesic-report-v1' and baseline.get('status')=='stage2-research-complete' and baseline.get('publishable') is False and baseline.get('provisional_only') is not True and baseline.get('orchestration',{}).get('provisional_only') is not True,'completed Stage 2 candidate required')
 metric=baseline.get('distance_policy',{});lp=base.get('land_baseline_policy',{});need(metric in base.get('distance_policies',[]) and metric.get('algorithm')=='wgs84_ellipsoidal_geodesic_inverse' and str(metric.get('semi_major_axis_m'))=='6378137' and str(metric.get('inverse_flattening'))=='298.257223563' and metric.get('execution_status')=='selected_for_research' and metric.get('decision_revision')==revision.get('id') and lp.get('distance_policy_id')==metric.get('policy_id') and lp.get('distance_policy_version')==metric.get('version') and lp.get('endpoints')=='physical_land_cell_centers' and lp.get('execution_status')=='selected_for_research','Stage 2 WGS84 center distance policy mismatch')
 need(baseline.get('decision_snapshot_sha256')==snapshot_hash and baseline.get('decision_revision')==revision.get('id') and baseline.get('entity_revision')==revision.get('entity_revision') and baseline.get('output_rows_sha256')==s['rows']['sha256'] and baseline.get('output_runs_sha256')==s['runs']['sha256'],'baseline report mismatch')
 v=report.get('baseline_validation',{});need(v.get('schema')=='stage2-candidate-validation-v1' and v.get('status')==('provisional-diagnostic-candidate-bound' if diagnostic else 'diagnostic-candidate-bound') and v.get('report_sha256')==s['report']['sha256'] and v.get('decision_revision')==revision.get('id') and v.get('entity_revision')==revision.get('entity_revision') and v.get('output_rows_sha256')==s['rows']['sha256'] and v.get('output_runs_sha256')==s['runs']['sha256'] and v.get('physical_rows_sha256')==physical['rows_sha256'] and v.get('physical_runs_sha256')==physical['runs_sha256'],'baseline validation mismatch')
 if diagnostic:need(v.get('original_report_status')=='stage2-provisional-only' and v.get('provisional_only') is True and v.get('publishable') is False,'provisional baseline validation status mismatch')
 for k in ('physical_rows','physical_runs'):
  need(s[k]['sha256']==req[k]['sha256']==physical[k.replace('physical_','')+'_sha256'] and baseline.get('inputs_sha256',{}).get(k)==s[k]['sha256'],'physical stream mismatch')
 for k in ('component_rows','component_runs'):
  need(baseline.get('inputs_sha256',{}).get(k)==req[k]['sha256'],'component generation mismatch')
 pr=pinned(s['physical_report'],root);pd=read(pr);po=pd.get('physical_output_sha256',pd.get('output_sha256',{}))
 need(physical_report_sha is not None and s['physical_report']['sha256']==physical_report_sha and pd.get('status') in ('candidate-only','stage1-complete') and pd.get('grid')==baseline.get('grid')==req.get('grid')==v.get('grid') and po.get('rows.u32le')==physical['rows_sha256'] and po.get('runs.u32le')==physical['runs_sha256'] and baseline.get('inputs_sha256',{}).get('physical_report')==s['physical_report']['sha256'],'physical report mismatch')
 pol=report.get('policy',{});sr=snap.get('decision_revision',{});se=snap.get('entity_revision',{});sp=snap.get('list1_policy',{})
 need(sr.get('status')=='draft' and se.get('status')=='draft' and sr.get('entity_revision')==se.get('id') and sp.get('execution_status')=='selected_for_research' and pol.get('revision')==sr.get('id') and pol.get('entity_revision')==se.get('id') and pol.get('policy')==sp and (diagnostic or (pol.get('baseline_revision')==revision.get('id') and sp.get('baseline_revision')==revision.get('id'))),'regional policy revision mismatch')
 expected={'baseline_report_sha256':s['report']['sha256'],'baseline_rows_sha256':s['rows']['sha256'],'baseline_runs_sha256':s['runs']['sha256'],'baseline_decision_snapshot_sha256':snapshot_hash,**{k+'_sha256':req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}}
 need(cfg.get('policy_pins')==expected,'mixed policy input pins mismatch')
 if diagnostic:
  binding=pol.get('diagnostic_binding',{});provenance=report.get('diagnostic_provenance',{})
  derived=read(pinned(s.get('derived_manifest'),root));outer=read(pinned(s.get('outer_config'),root));approval=read(pinned(cfg['stage2_approval'],root));approved=approval.get('approved_code',{});orchestration=baseline.get('orchestration',{});code=derived.get('code_sha256',{})
  need(derived.get('schema')=='stage2-fresh-derived-v1' and derived.get('provisional_only') is True and outer.get('schema')=='stage2-fresh-orchestration-v1' and orchestration.get('derived_manifest')==s['derived_manifest'] and derived.get('outer_config_sha256')==s['outer_config']['sha256']==orchestration.get('outer_config_sha256') and digest(derived.get('orchestrator_sha256')) and derived['orchestrator_sha256']==orchestration.get('orchestrator_sha256')==code.get('orchestrate_stage2.py') and code==approved.get('orchestration_files') and digest_map(code) and digest_map(baseline.get('code_sha256')) and baseline['code_sha256']==approved.get('core_files') and digest_map(baseline.get('dependency_sha256')) and baseline['dependency_sha256']==approved.get('dependency_files'),'Stage 2 intrinsic orchestration mismatch')
  artifacts=derived.get('artifacts',{});need(isinstance(artifacts,dict) and artifacts,'Stage 2 derived artifacts missing')
  for name,spec in artifacts.items():
   pinned(spec,root);need(baseline.get('inputs_sha256',{}).get(name)==spec['sha256'],'Stage 2 derived artifact mismatch')
  need(artifacts.get('seed_report',{}).get('sha256')==baseline.get('seed_report_sha256'),'Stage 2 seed report mismatch')
  need(binding.get('actual_baseline_pins')==expected and binding.get('original_policy_baseline_revision')==sp.get('baseline_revision') and binding.get('original_policy_pins')=={k:sp.get(k) for k in expected} and pol.get('baseline_revision')==revision.get('id') and provenance.get('actual_baseline_pins')==expected and provenance.get('list1_policy_original')==sp and provenance.get('stage2')==s and provenance.get('stage2_report_schema')==baseline['schema'] and provenance.get('stage2_report_status')==baseline['status'] and provenance.get('stage2_provisional_only') is True and provenance.get('stage2_publishable') is False and provenance.get('list1_snapshot')==req['snapshot'] and provenance.get('profiling_standin') is True and provenance.get('pending_inventory_complete') is False and provenance.get('stage2_snapshot_source')==base.get('source') and base.get('source') in ('neon-export','local-derived-from-neon-export') and provenance.get('list1_snapshot_source')=='neon-export','diagnostic baseline or provenance mismatch')
 else:need(all(sp.get(k)==v for k,v in expected.items()),'mixed policy input pins mismatch')
 origin=side.get('snapshot_origin',{});source=read(pinned(origin.get('source_snapshot'),root));kind=origin.get('kind')
 if kind=='direct':need(origin['source_snapshot']['sha256']==req['snapshot']['sha256'],'direct regional source snapshot mismatch')
 else:raise ValueError('unknown regional snapshot origin')
 resolution=report.get('point_resolution',{});need(resolution.get('schema')=='source-point-component-report-v1' and resolution.get('status')=='research-only-not-a-build' and resolution.get('snapshot_sha256')==req['snapshot']['sha256'] and resolution.get('revision')==sr.get('id') and resolution.get('entity_revision')==se.get('id') and resolution.get('input_sha256')=={k:req[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'point resolution lineage mismatch')
 approval=read(pinned(cfg['stage2_approval'],root));codes=report.get('code_sha256');need(approval.get('validator_sha256')==cfg.get('code',{}).get('validator'),'Stage 2 validator approval mismatch');need(isinstance(codes,dict) and codes and codes==cfg.get('code') and all(isinstance(x,str) and len(x)==64 and all(ch in '0123456789abcdef' for ch in x) for x in codes.values()),'mixed code pin mismatch')
 w=report.get('writer',{});need(w.get('schema')=='stage3-land-writer-result-v1' and w.get('status')=='pending-caller-validation' and w.get('grid')==baseline['grid'] and w.get('output_rows_sha256')==land['rows_sha256'] and w.get('output_runs_sha256')==land['runs_sha256'],'mixed writer result mismatch')
 need(Path(land['resolved_rows']).resolve()==rp.parent/'rows.u32le' and Path(land['resolved_runs']).resolve()==rp.parent/'runs.u32le','mixed output location mismatch')
 need(sha(land['resolved_rows'])==land['rows_sha256'] and sha(land['resolved_runs'])==land['runs_sha256'],'mixed land output hash mismatch')
 return {'schema':'water-selected-mixed-lineage-check-v1','status':('diagnostic-provisional-lineage-bound' if diagnostic else 'research-lineage-bound'),'publishable':False,'baseline_status':baseline['status'],'baseline_report_sha256':s['report']['sha256'],'baseline_rows_sha256':s['rows']['sha256'],'baseline_runs_sha256':s['runs']['sha256'],'physical_report_sha256':s['physical_report']['sha256'],'regional_request_sha256':report['request_sha256'],'regional_revision':sr['id'],'stage2_derived_manifest_sha256':(s['derived_manifest']['sha256'] if diagnostic else None),'profiling_standin':diagnostic,'pending_inventory_complete':not diagnostic,'producer_status':report['status'],'writer_status':w['status'],'regional_status':region['status'],'base_snapshot_sha256':snapshot_hash,'regional_snapshot_sha256':req['snapshot']['sha256'],'regional_source_snapshot_sha256':origin['source_snapshot']['sha256'],'regional_snapshot_origin':kind,'stage2_snapshot_source':(provenance['stage2_snapshot_source'] if diagnostic else None),'list1_snapshot_source':(provenance['list1_snapshot_source'] if diagnostic else None),'limitations':['Artifact identity and producer assertions only; not independent scientific validation or Neon authentication.','Source files and producer code are not independently replayed by this check.']}
