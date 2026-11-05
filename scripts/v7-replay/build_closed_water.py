#!/usr/bin/env python3
"""Bounded-memory direct closed-water research stage."""
import argparse,json
from pathlib import Path
import build_coastal_tile as base
import closed_water_core as core
import streaming_closed_water as stream
from decision_snapshot import read_snapshot
from direct_lineage import validate_physical_report,validate_direct_land


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('snapshot','snapshot-sha256','physical-rows','physical-rows-sha256','physical-runs','physical-runs-sha256','physical-report','physical-report-sha256',
           'land-rows','land-rows-sha256','land-runs','land-runs-sha256','land-report','land-report-sha256',
           'prefill-rows','prefill-rows-sha256','prefill-runs','prefill-runs-sha256','prefill-audit','prefill-audit-sha256',
           'prefill-plan','prefill-plan-sha256','partition-manifest','partition-manifest-sha256',
           'component-rows','component-rows-sha256','component-spans','component-spans-sha256','barrier-edges','barrier-edges-sha256','input-root','out'):
  ap.add_argument('--'+k,required=True)
 ap.add_argument('--pad-degrees',type=float,required=True);ap.add_argument('--sqlite-cache-kib',type=int,default=32768);ap.add_argument('--max-coastal-centers',type=int,default=1000000);ap.add_argument('--allow-unverified-snapshot',action='store_true');ap.add_argument('--allow-draft',action='store_true');ap.add_argument('--allow-selected-research-policy',action='store_true')
 a=ap.parse_args()
 if not a.allow_unverified_snapshot:raise ValueError('unverified snapshot requires explicit research opt-in')
 pairs=[(getattr(a,k),getattr(a,k+'_sha256')) for k in ('snapshot','physical_rows','physical_runs','physical_report','land_rows','land_runs','land_report',
    'prefill_rows','prefill_runs','prefill_audit','prefill_plan','partition_manifest','component_rows','component_spans','barrier_edges')]
 if any(Path(p).stat().st_size>16*1024*1024 for p in (a.snapshot,a.prefill_plan,a.prefill_audit)):raise ValueError('control JSON exceeds size limit')
 if any(base.sha(p)!=h for p,h in pairs):raise ValueError('input hash mismatch')
 snapshot=read_snapshot(Path(a.snapshot),a.snapshot_sha256,allow_draft=a.allow_draft);core.policy(snapshot,allow_selected_research=a.allow_selected_research_policy)
 root=Path(a.input_root).resolve();out=Path(a.out).resolve()
 if not root.is_dir() or any(not Path(p).resolve().is_relative_to(root) for p,_ in pairs):raise ValueError('all inputs must be inside input root')
 if any(out==Path(p).resolve() or Path(p).resolve().is_relative_to(out) for p,_ in pairs):raise ValueError('output overlaps input')
 width,height=131072,54614
 physical={'rows_sha256':a.physical_rows_sha256,'runs_sha256':a.physical_runs_sha256}
 land={'rows_sha256':a.land_rows_sha256,'runs_sha256':a.land_runs_sha256,
       'resolved_rows':Path(a.land_rows).resolve(),'resolved_runs':Path(a.land_runs).resolve()}
 def check_lineage():
  validate_physical_report(a.physical_report,a.physical_report_sha256,physical,width,height)
  validate_direct_land(a.land_report,a.land_report_sha256,physical,land,a.snapshot_sha256,snapshot['decision_revision'],root,a.physical_report_sha256)
 check_lineage()
 plan=json.loads(Path(a.prefill_plan).read_text());audit=json.loads(Path(a.prefill_audit).read_text())
 if (audit.get('schema')!='worldatlas-v7-prefill-class-rle-audit-v1' or audit.get('status')!='staged-not-published'
     or audit.get('land_input_kind')!='direct-research' or audit.get('prior_ocean_water_labels_read')!='none'
     or plan.get('land_input_kind')!='direct-research' or plan.get('decision_revision')!=snapshot['decision_revision']['id']
     or plan.get('entity_revision')!=snapshot['decision_revision']['entity_revision']
     or audit.get('source_plan_sha256')!=a.prefill_plan_sha256 or audit.get('decision_snapshot_sha256')!=a.snapshot_sha256
     or audit.get('decision_revision')!=snapshot['decision_revision']['id'] or audit.get('entity_revision')!=snapshot['decision_revision']['entity_revision']
     or audit.get('output',{}).get('rows_sha256')!=a.prefill_rows_sha256 or audit.get('output',{}).get('runs_sha256')!=a.prefill_runs_sha256
     or plan.get('decision_snapshot_sha256')!=a.snapshot_sha256 or plan.get('rle_inputs',{}).get('physical',{}).get('rows_sha256')!=a.physical_rows_sha256
     or plan.get('rle_inputs',{}).get('physical',{}).get('runs_sha256')!=a.physical_runs_sha256
     or plan.get('rle_inputs',{}).get('land',{}).get('rows_sha256')!=a.land_rows_sha256
     or plan.get('rle_inputs',{}).get('land',{}).get('runs_sha256')!=a.land_runs_sha256
     or plan.get('rle_inputs',{}).get('land',{}).get('report_sha256')!=a.land_report_sha256):
  raise ValueError('prefill plan/audit does not bind this snapshot, direct land and physical grid')
 partition_path=Path(a.partition_manifest).resolve()
 if (Path(a.component_rows).resolve()!=(partition_path.parent/'unseeded_rows.u64le').resolve()
     or Path(a.component_spans).resolve()!=(partition_path.parent/'unseeded_component_spans.u32le').resolve()):
  raise ValueError('unseeded files must belong to pinned partition')
 inputs={k+'_sha256':getattr(a,k+'_sha256') for k in ('physical_rows','physical_runs','physical_report','land_rows','land_runs','land_report',
         'prefill_rows','prefill_runs','prefill_audit','prefill_plan','partition_manifest','component_rows','component_spans','barrier_edges')}
 inputs['source_cut_edges_sha256']=a.barrier_edges_sha256
 def recheck():
  if any(base.sha(p)!=h for p,h in pairs):raise ValueError('input changed during closed-water generation')
  check_lineage()
 result=stream.run(snapshot,a.snapshot_sha256,base.open_grid(a.physical_rows,a.physical_runs,width,height),
   base.open_grid(a.prefill_rows,a.prefill_runs,width,height),base.open_grid(a.land_rows,a.land_runs,width,height),
   partition_path,a.component_rows,a.component_spans,a.barrier_edges,out,width,height,a.pad_degrees,inputs,
   verify_inputs=recheck,allow_selected_research=a.allow_selected_research_policy,
   max_coastal_centers=a.max_coastal_centers,cache_kib=a.sqlite_cache_kib)
 print(json.dumps({'status':result['status'],'assigned':result['assigned_cells'],'pending':result['pending_cells'],'output':str(out)}))

if __name__=='__main__':main()
