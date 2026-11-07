#!/usr/bin/env python3
"""Prepare a fresh, provisional-only regional rerun; never launch or publish it."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
STAGE2=REPO/'scripts/v7-recovery/land/stage2-geodesic-20261104'

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
def remap_source_paths(value,old,new):
 if isinstance(value,str) and (value==old or value.startswith(old+'/')):return new+value[len(old):]
 if isinstance(value,list):return [remap_source_paths(x,old,new) for x in value]
 if isinstance(value,dict):return {k:remap_source_paths(v,old,new) for k,v in value.items()}
 return value

def prepare(template_path,outer_path,work_path,output_path,dest_path,regional_output,source_prefix=None):
 dest=Path(dest_path).resolve();out=Path(regional_output).resolve()
 if dest.exists() or out.exists() or not dest.parent.is_dir() or not out.parent.is_dir() or dest==out or dest in out.parents or out in dest.parents:raise ValueError('fresh separate output paths required')
 if sha(template_path)!='4668cac041f0dee1257c95a9e60c46d34fff53ffb5ab0010ec3647e114d909d0':raise ValueError('exact v24 regional request required')
 cfg=read(template_path);outer=read(outer_path);work=Path(work_path).resolve(strict=True);stageout=Path(output_path).resolve(strict=True)
 if source_prefix is not None:
  old,new=source_prefix
  if not old.startswith('/') or not new.startswith('/') or old=='/':raise ValueError('absolute non-root source prefixes required')
  cfg=remap_source_paths(cfg,old.rstrip('/'),new.rstrip('/'))
 if cfg.get('schema')!='stage3-provisional-diagnostic-request-v1' or cfg.get('publishable') is not False or outer.get('schema')!='stage2-fresh-orchestration-v1':raise ValueError('provisional template and fresh orchestration required')
 report=read(stageout/'report.json');derived=read(work/'derived/manifest.json');core=read(work/'core-requests/config.json')
 if report.get('status')!='stage2-provisional-only' or report.get('publishable') is not False or report.get('provisional_only') is not True or derived.get('provisional_only') is not True:raise ValueError('completed provisional Stage 2 required')
 if report.get('config_sha256')!=sha(work/'core-requests/config.json') or derived.get('outer_config_sha256')!=sha(outer_path):raise ValueError('same-run outer/core mismatch')
 inp=core['inputs'];stage2={'report':pin(stageout/'report.json'),'derived_manifest':pin(work/'derived/manifest.json'),'outer_config':pin(outer_path),'rows':pin(stageout/'rows.u32le'),'runs':pin(stageout/'runs.u32le'),'snapshot':inp['decision_snapshot'],'physical_rows':inp['physical_rows'],'physical_runs':inp['physical_runs'],'physical_report':inp['physical_report'],'physical_lineage_request':inp['physical_lineage_request'],'physical_lineage_report':core['orchestration']['physical_lineage_report'],'prior_physical_report':inp['prior_physical_report']}
 code={'orchestrator':report['orchestration']['orchestrator_sha256'],'core':report['code_sha256']['build_stage2.py'],'core_files':report['code_sha256'],'dependency_files':report['dependency_sha256'],'orchestration_files':derived['code_sha256']}
 for name,digest in code['orchestration_files'].items():
  if sha(STAGE2/name)!=digest:raise ValueError('current runtime code mismatch: '+name)
 sys.path.insert(0,str(STAGE2));import validate_stage2_candidate as validator
 validation=validator.validate(stage2,code,provisional_diagnostic=True)
 if validation.get('status')!='provisional-diagnostic-candidate-bound':raise ValueError('independent stage 2 validation failed')
 if sha(cfg['point_request']['path'])!=cfg['point_request']['sha256']:raise ValueError('original point request pin mismatch')
 point=read(cfg['point_request']['path'])
 if source_prefix is not None:point=remap_source_paths(point,*source_prefix)
 for name in ('physical_rows','physical_runs','component_rows','component_runs','component_manifest','component_source'):point[name]=inp[name]
 if point['grid']!=report['grid']:raise ValueError('point grid mismatch')
 # Remap every regional executable to the exact matching checked-in bytes.
 byhash={}
 for name in subprocess.check_output(['git','ls-files'],cwd=REPO,text=True).splitlines():
  p=REPO/name
  if p.is_file():byhash.setdefault(sha(p),[]).append(p)
 cfg['regional']['request']['code']['point_prototype']['path']=str(STAGE2/'point_prototype.py')
 for spec in [cfg['regional']['hook'],*cfg['regional']['request']['code'].values()]:
  matches=byhash.get(spec['sha256'],[])
  if not matches:raise ValueError('regional executable absent from checked-in tree: '+spec['sha256'])
  old=spec['path'].split('/scripts/',1)[-1];desired=REPO/'scripts'/old
  spec['path']=str(desired if desired in matches else matches[0])
 cfg['stage2']=stage2;cfg['output']=str(out);cfg['code']['driver']=sha(HERE/'apply_selected_mixed.py');cfg['code']['validator']=sha(STAGE2/'validate_stage2_candidate.py')
 cfg['policy_pins']={'baseline_report_sha256':stage2['report']['sha256'],'baseline_rows_sha256':stage2['rows']['sha256'],'baseline_runs_sha256':stage2['runs']['sha256'],'baseline_decision_snapshot_sha256':stage2['snapshot']['sha256'],**{k+'_sha256':point[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}}
 dest.mkdir(mode=0o700)
 try:
  pointpath=dest/'point-request.json';write(pointpath,point);cfg['point_request']=pin(pointpath)
  approval={'validator_sha256':cfg['code']['validator'],'approved_code':code,'status':'same-run-provisional-code-pins-not-geographic-approval'};ap=dest/'stage2-code-pins.json';write(ap,approval);cfg['stage2_approval']=pin(ap)
  handoff={'schema':'stage2-fresh-provisional-handoff-v1','status':'same-run-launcher-bound-by-derived-manifest','derived_manifest_sha256':stage2['derived_manifest']['sha256'],'core_config_sha256':report['config_sha256'],'seed_report_sha256':report['seed_report_sha256'],'launcher':pin(STAGE2/'seed-producer/seed_worker.py'),'limitation':'Research-only identity and code binding; not accepted geography or provider authentication.'}
  ev=dest/'stage2-handoff.json';write(ev,handoff);cfg['stage2_recovery_evidence']=pin(ev)
  cp=dest/'config.json';write(cp,cfg);write(dest/'preparation.json',{'schema':'stage3-fresh-provisional-preparation-v1','status':'validated-not-run','publishable':False,'template':pin(template_path),'stage2_validation':validation,'config':pin(cp),'limitations':['Original regional decision snapshot and policy remain unchanged.','Pending inventory remains incomplete; regional output is profiling-only.']})
 except BaseException:raise RuntimeError('Preparation failed; inspect partially created destination before retry') from None
 return dest/'config.json'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--template',required=True);p.add_argument('--outer',required=True);p.add_argument('--work',required=True);p.add_argument('--stage2-output',required=True);p.add_argument('--destination',required=True);p.add_argument('--regional-output',required=True);p.add_argument('--source-prefix',nargs=2,metavar=('OLD','NEW'));a=p.parse_args();print(prepare(a.template,a.outer,a.work,a.stage2_output,a.destination,a.regional_output,a.source_prefix))
