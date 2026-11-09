#!/usr/bin/env python3
"""Prepare a fresh, provisional-only regional rerun; never launch or publish it."""
import argparse,hashlib,json,os,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
STAGE2=REPO/'scripts/stages/land/stage2-geodesic-20261104'

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while b:=f.read(1<<20):h.update(b)
 return h.hexdigest()
def pin(path):
 p=Path(path).resolve(strict=True)
 if not p.is_file():raise ValueError('not a file: '+str(p))
 return {'path':str(p),'sha256':sha(p)}
def read(p):return json.loads(Path(p).read_bytes())
def write(path,obj):
 with open(path,'x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def regional_code_paths():
 rule=HERE.parent/'lydekker-regional-rule';integration=HERE.parent/'lydekker-regional-writer-integration'
 result={name:rule/(name+'.py') for name in ('regional_rule','component_scan','replay_adapter','geonames_anchors','satellite_geodesic','regional_workflow','regional_group_convention')}
 result.update({name:integration/(name+'.py') for name in ('source_groups','adapter','live_driver')})
 result.update({'point_prototype':STAGE2/'point_prototype.py','run_pair':HERE.parent/'lydekker-regional-writer-integration/run_pair.py',**{name:HERE/(name+'.py') for name in ('land_archive_source','polygon_intersection')}})
 return result

def bind_regional_code(specs):
 paths=regional_code_paths()
 if not isinstance(specs,dict) or set(specs)!=set(paths):raise ValueError('regional code inventory mismatch')
 result={}
 for name,path in paths.items():
  spec=specs[name]
  if not isinstance(spec,dict) or set(spec)!={'path','sha256'} or sha(path)!=spec['sha256']:raise ValueError('regional policy code pin mismatch: '+name)
  result[name]=pin(path)
 return result

def equivalent_runtime_code():
 integration=HERE.parent/'lydekker-regional-writer-integration'
 return {name:pin(integration/(name+'.py')) for name in ('component_index','satellite_index','regional_runtime')}

def prepare(template_path,outer_path,work_path,output_path,dest_path,regional_output,*,template_sha256):
 dest=Path(dest_path).resolve();out=Path(regional_output).resolve()
 if dest.exists() or out.exists() or not dest.parent.is_dir() or not out.parent.is_dir() or dest==out or dest in out.parents or out in dest.parents:raise ValueError('fresh separate output paths required')
 if not isinstance(template_sha256,str) or len(template_sha256)!=64 or any(c not in '0123456789abcdef' for c in template_sha256) or sha(template_path)!=template_sha256:raise ValueError('regional template hash mismatch')
 cfg=read(template_path);outer=read(outer_path);work=Path(work_path).resolve(strict=True);stageout=Path(output_path).resolve(strict=True)
 if cfg.get('schema')!='stage3-provisional-diagnostic-request-v1' or cfg.get('publishable') is not False or outer.get('schema')!='stage2-fresh-orchestration-v1':raise ValueError('provisional template and fresh orchestration required')
 report=read(stageout/'report.json');derived=read(work/'derived/manifest.json');core=read(work/'core-requests/config.json')
 if report.get('status')!='stage2-provisional-only' or report.get('publishable') is not False or report.get('provisional_only') is not True or derived.get('provisional_only') is not True:raise ValueError('completed provisional Stage 2 required')
 if report.get('config_sha256')!=sha(work/'core-requests/config.json') or derived.get('outer_config_sha256')!=sha(outer_path):raise ValueError('same-run outer/core mismatch')
 inp=core['inputs'];stage2={'report':pin(stageout/'report.json'),'derived_manifest':pin(work/'derived/manifest.json'),'outer_config':pin(outer_path),'rows':pin(stageout/'rows.u32le'),'runs':pin(stageout/'runs.u32le'),'snapshot':inp['decision_snapshot'],'physical_rows':inp['physical_rows'],'physical_runs':inp['physical_runs'],'physical_report':inp['physical_report'],'physical_lineage_request':inp['physical_lineage_request'],'physical_lineage_report':core['orchestration']['physical_lineage_report']}
 code={'orchestrator':report['orchestration']['orchestrator_sha256'],'core':report['code_sha256']['build_stage2.py'],'core_files':report['code_sha256'],'dependency_files':report['dependency_sha256'],'orchestration_files':derived['code_sha256']}
 for name,digest in code['orchestration_files'].items():
  if sha(STAGE2/name)!=digest:raise ValueError('current runtime code mismatch: '+name)
 sys.path.insert(0,str(STAGE2));import validate_stage2_candidate as validator
 validation=validator.validate(stage2,code,provisional_diagnostic=True)
 if validation.get('status')!='provisional-diagnostic-candidate-bound':raise ValueError('independent stage 2 validation failed')
 if sha(cfg['point_request']['path'])!=cfg['point_request']['sha256']:raise ValueError('original point request pin mismatch')
 point=read(cfg['point_request']['path'])
 for name in ('physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source'):point[name]=inp[name]
 resolver=HERE.parent/'geonames-point-integration-20261105/point-component-prototype/resolve.py'
 point['resolver_sha256']=sha(resolver);cfg['code']['resolver']=point['resolver_sha256']
 point['runtime']=pin(resolver.parent/'point_runtime.py')
 if point['grid']!=report['grid']:raise ValueError('point grid mismatch')
 # A versioned module inventory selects repository code; retain every
 # approved policy hash rather than searching clones for matching bytes.
 cfg['regional']['request']['code']=bind_regional_code(cfg['regional']['request']['code'])
 cfg['regional']['request']['runtime']=equivalent_runtime_code()
 cfg['regional']['hook']=pin(HERE.parent/'lydekker-regional-writer-integration/driver_hook.py')
 cfg['polygon_runtime']=pin(HERE.parent/'lydekker-regional-writer-integration/polygon_runtime.py')
 cfg['stage2']=stage2;cfg['output']=str(out);cfg['code']['driver']=sha(HERE/'apply_selected_mixed.py');cfg['code']['validator']=sha(STAGE2/'validate_stage2_candidate.py')
 cfg['policy_pins']={'baseline_report_sha256':stage2['report']['sha256'],'baseline_rows_sha256':stage2['rows']['sha256'],'baseline_runs_sha256':stage2['runs']['sha256'],'baseline_decision_snapshot_sha256':stage2['snapshot']['sha256'],**{k+'_sha256':point[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}}
 dest.mkdir(mode=0o700)
 try:
  pointpath=dest/'point-request.json';write(pointpath,point);cfg['point_request']=pin(pointpath)
  approval={'validator_sha256':cfg['code']['validator'],'approved_code':code,'status':'same-run-provisional-code-pins-not-geographic-approval'};ap=dest/'stage2-code-pins.json';write(ap,approval);cfg['stage2_approval']=pin(ap)
  cfg.pop('stage2_recovery_evidence',None)
  cp=dest/'config.json';write(cp,cfg);write(dest/'preparation.json',{'schema':'stage3-fresh-provisional-preparation-v1','status':'validated-not-run','publishable':False,'template':pin(template_path),'stage2_validation':validation,'config':pin(cp),'limitations':['Original regional decision snapshot and policy remain unchanged.','Pending inventory remains incomplete; regional output is profiling-only.']})
 except BaseException:raise RuntimeError('Preparation failed; inspect partially created destination before retry') from None
 return dest/'config.json'
def main(argv=None, *, emit=print):
 p=argparse.ArgumentParser();p.add_argument('--template',required=True);p.add_argument('--template-sha256',required=True);p.add_argument('--outer',required=True);p.add_argument('--work',required=True);p.add_argument('--stage2-output',required=True);p.add_argument('--destination',required=True);p.add_argument('--regional-output',required=True);a=p.parse_args(argv);emit(prepare(a.template,a.outer,a.work,a.stage2_output,a.destination,a.regional_output,template_sha256=a.template_sha256))


if __name__ == '__main__':
    main()
