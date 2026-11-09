#!/usr/bin/env python3
"""Bind completed research prefill, ocean and enclosed outputs for composition."""
import hashlib,json,os,time
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p,digest):
 p=Path(p);before=p.stat();raw=p.read_bytes();after=p.stat()
 if p.is_symlink() or hashlib.sha256(raw).hexdigest()!=digest or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('input pin mismatch')
 return json.loads(raw)
def validate(plan,audit,ocean,summary,closed,partition,partition_sha):
 if plan.get('schema')!='worldatlas-full-grid-composition-plan-v1' or audit.get('schema')!='worldatlas-prefill-class-rle-audit-v1' or audit.get('status')!='staged-not-published':raise ValueError('invalid research prefill')
 snapshot=plan['decision_snapshot_sha256'];rev=plan['decision_revision'];entity=plan['entity_revision'];output=audit['output'];source_keys={'prefill_rows_sha256':output['rows_sha256'],'prefill_runs_sha256':output['runs_sha256'],'decision_snapshot_sha256':snapshot,'decision_revision':rev,'entity_revision':entity}
 for label,m in [('ocean',ocean),('enclosed',closed)]:
  if m.get('schema')!='worldatlas-full-water-assignment-tiles-v1' or m.get('status')!='completed_unverified_candidate_not_published' or m.get('coverage',{}).get('complete') is not True or any(m.get('source',{}).get(k)!=v for k,v in source_keys.items()):raise ValueError(label+' manifest or lineage mismatch')
 if summary.get('status')!='unverified-candidate-not-published' or summary.get('snapshot_sha256')!=snapshot or summary.get('layer_manifest_sha256')!=sha_value(ocean):raise ValueError('ocean summary mismatch')
 if partition.get('unseeded_cell_count')!=summary.get('unseeded_cell_count') or partition.get('inputs',{}).get('prefill_rows_sha256')!=output['rows_sha256'] or partition.get('inputs',{}).get('prefill_runs_sha256')!=output['runs_sha256']:raise ValueError('partition lineage mismatch')
 if closed.get('source',{}).get('partition_manifest_sha256')!=partition_sha or closed.get('pending_cells')!=0 or closed.get('assigned_cells')!=summary.get('unseeded_cell_count') or summary.get('assigned_cells_total',0)+closed.get('assigned_cells',0)!=audit.get('residual_eligible_water_cells'):raise ValueError('ocean/enclosed conservation mismatch')
 return source_keys
# Actual raw manifest hash is injected by the caller after pinned byte read.
def sha_value(manifest):return manifest.get('_verified_manifest_sha256')
def make(spec,out):
 processing_started=time.perf_counter()
 docs={k:read(v['path'],v['sha256']) for k,v in spec.items() if k in ('plan','audit','ocean','summary','closed','partition')};docs['ocean']['_verified_manifest_sha256']=spec['ocean']['sha256'];docs['closed']['_verified_manifest_sha256']=spec['closed']['sha256'];validate(docs['plan'],docs['audit'],docs['ocean'],docs['summary'],docs['closed'],docs['partition'],spec['partition']['sha256']);plan=docs['plan'];audit=docs['audit'];
 if docs['ocean']['source'].get('prefill_audit_sha256')!=spec['audit']['sha256'] or docs['closed']['source'].get('prefill_audit_sha256')!=spec['audit']['sha256'] or docs['closed']['source'].get('prefill_plan_sha256')!=spec['plan']['sha256'] or docs['ocean']['source'].get('source_cut_edges_sha256')!=docs['summary'].get('barrier_sha256') or docs['closed']['source'].get('source_cut_edges_sha256')!=docs['summary'].get('barrier_sha256'):raise ValueError('ocean/closed provenance mismatch')
 if audit['source_plan_sha256']!=spec['plan']['sha256'] or audit['output']['rows_sha256']!=spec['rows']['sha256'] or audit['output']['runs_sha256']!=spec['runs']['sha256']:raise ValueError('prefill hashes mismatch')
 for key in ('rows','runs'):
  if sha(spec[key]['path'])!=spec[key]['sha256']:raise ValueError('prefill RLE changed')
 result={'schema':'worldatlas-direct-final-plan-v1','grid':plan['grid'],'decision_revision_status':plan['decision_revision_status'],'decision_snapshot_sha256':plan['decision_snapshot_sha256'],'decision_revision':plan['decision_revision'],'entity_revision':plan['entity_revision'],'prefill':{k+'_'+v:spec[k][v] for k in ('rows','runs','audit','plan') for v in ('path','sha256')},'water_layers':[{'layer_id':'ocean','manifest_path':spec['ocean']['path'],'manifest_sha256':spec['ocean']['sha256'],'priority':1,'overrides':[],'allowed_codes':[7,8,9,10]},{'layer_id':'enclosed-water','manifest_path':spec['closed']['path'],'manifest_sha256':spec['closed']['sha256'],'priority':1,'overrides':[],'allowed_codes':[1,2,3,4,5,6]}],'research_provenance':{'ocean_summary_sha256':spec['summary']['sha256'],'partition_manifest_sha256':spec['partition']['sha256'],'publishable':False}}
 for k in ('plan','audit','ocean','summary','closed','partition','rows','runs'):
  if sha(spec[k]['path'])!=spec[k]['sha256']:raise ValueError('input changed before plan: '+k)
 out=Path(out)
 if out.is_symlink():raise ValueError('output symlink')
 result['processing_elapsed_seconds']=time.perf_counter()-processing_started
 with out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return result
def main(argv=None, *, emit=print):
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--spec-sha256',required=True);p.add_argument('--out',required=True);a=p.parse_args(argv);s=read(a.spec,a.spec_sha256);make(s,a.out);emit('provisional final composition plan prepared')


if __name__ == '__main__':
    main()
