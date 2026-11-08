#!/usr/bin/env python3
"""Build a portable candidate 0–6/17–22 prefill RLE for the ocean seed-fill engine.

Inputs are a physical mask, either decision-derived research land or historical V6 land,
and continent-water layers. No V2 or V6 water label is read.
"""
from __future__ import annotations
import argparse,json,sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_binary_exclusive, create_directory_exclusive, write_json_exclusive, validate_fresh_output
import numpy as np
import compose_full_water_grid as c
from build_prefill_plan import validate_land_report, validate_physical_report, validate_shared_audit
from prefill_columns import LayerPolicy


def direct_land_water_code(report,report_sha,lineage):
 """Use the water encoding of the fully validated land producer."""
 mixed=report.get('schema') in ('stage3-selected-mixed-land-report-v1','stage3-provisional-diagnostic-land-report-v1')
 if not mixed:return 1
 if (not isinstance(lineage,dict) or lineage.get('status') not in ('research-lineage-bound','diagnostic-provisional-lineage-bound') or report.get('writer',{}).get('schema')!='stage3-land-writer-result-v1' or report.get('policy',{}).get('policy',{}).get('physical_water_policy')!='preserve_unassigned'):
  raise ValueError('unsupported mixed land water encoding')
 return 0

def validate_row_codes(phys,land,assigned,assigned_codes,starts,ends,y,water_code):
 land_mask=phys==17;water_mask=phys==1
 invalid=(~(land_mask|water_mask))|(land_mask&assigned)|(land_mask&((land<17)|(land>22)))
 if water_code is not None:invalid|=water_mask&(land!=water_code)
 invalid|=water_mask&assigned&((assigned_codes<1)|(assigned_codes>6))
 if np.any(invalid):
  j=int(np.flatnonzero(invalid)[0]);x=int(starts[j]);z=int(ends[j])
  if phys[j]==17:
   if assigned[j]:raise ValueError(f'continent-water span covers physical land row={y} x={x}:{z}')
   if not 17<=land[j]<=22:raise ValueError(f'unassigned final land row={y} x={x}:{z} code={land[j]}')
  elif phys[j]==1:
   if water_code is not None and land[j]!=water_code:raise ValueError(f'direct land grid disagrees with physical water row={y} x={x}:{z} code={land[j]}')
   if assigned[j] and not 1<=int(assigned_codes[j])<=6:raise ValueError(f'invalid prefill water code row={y} x={x}:{z}: {int(assigned_codes[j])}')
  else:raise ValueError(f'unexpected physical mask code {phys[j]} row={y}')
 return land_mask,water_mask

def main(argv=None, *, emit=print):
 processing_started=time.perf_counter()
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--input-root',required=True);ap.add_argument('--out',required=True)
 ap.add_argument('--allow-unverified-snapshot',action='store_true',help='test only: Neon acceptance cannot yet be authenticated by this tool')
 ap.add_argument('--allow-draft-snapshot',action='store_true',help='research only: allow a draft plan')
 ap.add_argument('--allow-research-shore',action='store_true',help='research only: allow the unapproved WGS84 coastal land-cell-center method')
 ap.add_argument('--allow-historical-v6',action='store_true',help='historical replay only: permit V6 land')
 ap.add_argument('--column-engine',action='store_true',help='research: resolve validated spans as numeric columns; verify full-input parity before adoption')
 a=ap.parse_args(argv)
 if not a.allow_unverified_snapshot:raise ValueError('authenticated Neon revision verification is not implemented; explicit test-only flag required')
 root=Path(a.input_root).resolve()
 if not root.is_dir():raise ValueError('input root must exist')
 plan_path=Path(a.plan).resolve()
 plan=json.loads(plan_path.read_text())
 if plan.get('schema')!='worldatlas-v7-full-grid-composition-plan-v1':raise ValueError('wrong plan schema')
 if plan.get('decision_revision_status')=='draft' and not a.allow_draft_snapshot:raise ValueError('draft plan requires explicit research opt-in')
 if plan.get('research_shore_method') is not None and (plan['research_shore_method']!='wgs84-coastal-4neighbor-center-v2' or not a.allow_research_shore):raise ValueError('WGS84 research shore method requires explicit opt-in; retired or unknown methods are rejected')
 out=validate_fresh_output(root,a.out,(plan_path,))
 if plan.get('grid',{}).get('width')!=c.W or plan.get('grid',{}).get('height')!=c.H:raise ValueError('plan grid mismatch')
 rles={}
 land_key='land' if 'land' in plan['rle_inputs'] else 'v6'
 if land_key=='v6' and not a.allow_historical_v6:raise ValueError('historical V6 replay requires explicit opt-in')
 if land_key=='land' and (plan.get('land_input_kind')!='direct-research' or plan.get('decision_revision_status') not in ('draft','accepted')):raise ValueError('direct land input kind or revision status mismatch')
 if set(plan['rle_inputs'])!={'physical',land_key}:raise ValueError('exactly one direct land or historical v6 grid is required')
 for key in ('physical',land_key):
  ent=plan['rle_inputs'][key];rp=c.resolve_input(ent['rows_path'],plan_path.parent,root);up=c.resolve_input(ent['runs_path'],plan_path.parent,root)
  if c.sha256(rp)!=ent['rows_sha256'] or c.sha256(up)!=ent['runs_sha256']:raise ValueError(f'{key} input RLE hash mismatch')
  rows=np.memmap(rp,dtype='<u4',mode='r');runs=np.memmap(up,dtype='<u4',mode='r')
  if len(rows)!=c.H+1 or len(runs)%2 or int(rows[0])!=0 or int(rows[-1])!=len(runs)//2 or np.any(rows[1:]<=rows[:-1]):
   raise ValueError(f'{key} invalid RLE offsets or size')
  rles[key]=(rows,runs)
 if 'report_path' in plan['rle_inputs']['physical']:
  pent=plan['rle_inputs']['physical'];ppath=c.resolve_input(pent['report_path'],plan_path.parent,root)
  if c.sha256(ppath)!=pent['report_sha256']:raise ValueError('physical report hash mismatch')
  validate_physical_report(json.loads(ppath.read_text()),pent)
 land_water_code=None
 if land_key=='land':
  ent=plan['rle_inputs']['land'];report_path=c.resolve_input(ent['report_path'],plan_path.parent,root)
  if c.sha256(report_path)!=ent['report_sha256']:raise ValueError('direct land report hash mismatch')
  physical=plan['rle_inputs']['physical']
  land={**ent,'resolved_rows':c.resolve_input(ent['rows_path'],plan_path.parent,root),'resolved_runs':c.resolve_input(ent['runs_path'],plan_path.parent,root)}
  report=json.loads(report_path.read_text())
  revision={'id':plan.get('decision_revision'),'entity_revision':plan.get('entity_revision'),'status':plan.get('decision_revision_status')}
  checked_land_lineage=validate_land_report(report,report_path,physical,land,plan.get('land_decision_snapshot_sha256',plan.get('decision_snapshot_sha256')),revision,root)
  if checked_land_lineage!=plan.get('land_lineage'):raise ValueError('land lineage differs from prefill plan')
  land_water_code=direct_land_water_code(report,ent['report_sha256'],checked_land_lineage)
 layers=[]
 for ent in plan.get('water_layers',[]):
  mp,m=c.read_pinned_manifest(ent,plan_path,root);m['_tiles']=m['tiles']
  source=m.get('source') or {};nearest=m.get('nearest_assignment_audit')
  if source.get('assignment_method')=='shared_nearest_assigned_shore' or nearest is not None:
   if (source.get('assignment_method')!='shared_nearest_assigned_shore'
       or plan.get('research_shore_method')!='wgs84-coastal-4neighbor-center-v2'
       or not isinstance(nearest,dict)
       or not nearest.get('shore_method')):
    raise ValueError('shared-shore manifest does not bind the WGS84 research method')
   try:validate_shared_audit(m)
   except ValueError as e:raise ValueError('shared-shore manifest does not bind the WGS84 research method: '+str(e)) from e
  if not isinstance(ent.get('priority'),int):raise ValueError(f"layer missing explicit priority: {ent}")
  layers.append((ent,m))
 create_directory_exclusive(out)
 cursors=[(ent,c.RowCursor(m,0,c.H,'water')) for ent,m in layers]
 policy=LayerPolicy([ent for ent,_ in layers]) if a.column_engine else None
 pr,pu=rles['physical'];landr,landu=rles[land_key];rawr=out/'prefill-rows.u32le';rawu=out/'prefill-runs.u32le'
 counts={str(k):0 for k in range(23)};runs_written=0;overlap_cells=0;assigned_cells=0;residual_cells=0;land_cells=0
 with create_binary_exclusive(rawr) as yf,create_binary_exclusive(rawu) as rf:
  yf.write(np.asarray([0],dtype='<u4').tobytes())
  for y in range(c.H):
   pe,pv=c.rle_row(pr,pu,y);ve,vv=c.rle_row(landr,landu,y)
   pe=np.asarray(pe,dtype=np.uint32);pv=np.asarray(pv,dtype=np.uint32);ve=np.asarray(ve,dtype=np.uint32);vv=np.asarray(vv,dtype=np.uint32)
   if (int(pe[-1])!=c.W or int(ve[-1])!=c.W or np.any(pe[1:]<=pe[:-1])
       or np.any(ve[1:]<=ve[:-1]) or int(pe[0])==0 or int(ve[0])==0):
    raise ValueError(f'bad RLE endpoints on row {y}')
   if policy is None:
    spans=[]
    for ent,cur in cursors:
     ss=cur.take(y)
     for s in ss:
      if s[3]>6:raise ValueError(f"prefill layers may only assign water code 1–6, got {s[3]} on row {y}")
      if 'allowed_codes' in ent and s[3] not in ent['allowed_codes']:
       raise ValueError(f"assignment code not allowed by selected basin policy on row {y}: {s[3]}")
     spans.extend(c.add_layer_identity(ss,int(ent['priority']),str(ent.get('layer_id',ent['manifest_path'])),set(ent.get('overrides',[]))))
    ass,conflicts=c.choose_assignments(spans,y,pe,pv)
    overlap_cells+=sum(b-a for a,b in {(a,b) for a,b,_,_ in conflicts})
    assignment_columns=c.assignment_arrays(ass)
   else:
    chunks=[(index,cur.take(y)) for index,(_,cur) in enumerate(cursors)]
    resolved=policy.resolve(chunks,y,pe,pv)
    overlap_cells+=resolved.overlap_cells
    assignment_columns=resolved.columns
   xx=c.merge_row_cuts(pe,ve,assignment_columns=assignment_columns)
   starts=xx[:-1];ends=xx[1:]
   phys=c.row_code_at(pe,pv,starts);land=c.row_code_at(ve,vv,starts)
   assigned_codes,assigned=c.assignment_codes((),starts,columns=assignment_columns)
   land_mask,water_mask=validate_row_codes(phys,land,assigned,assigned_codes,starts,ends,y,land_water_code)
   lens=(ends-starts).astype(np.uint64)
   codes=np.where(land_mask,land,np.where(assigned,assigned_codes,0)).astype(np.uint8,copy=False)
   land_cells+=int(lens[land_mask].sum())
   assigned_cells+=int(lens[water_mask&assigned].sum())
   residual_cells+=int(lens[water_mask&~assigned].sum())
   for v in np.unique(codes):counts[str(int(v))]+=int(lens[codes==v].sum())
   keep=np.r_[True,codes[1:]!=codes[:-1]];idx=np.flatnonzero(keep);nxt=np.r_[idx[1:],len(codes)]
   vals=codes[idx].astype('<u4');ends_out=ends[nxt-1].astype('<u4');rf.write(np.column_stack((ends_out,vals)).astype('<u4').ravel().tobytes())
   runs_written+=len(vals);yf.write(np.asarray([runs_written],dtype='<u4').tobytes())
 report={'schema':'worldatlas-v7-prefill-class-rle-audit-v1','status':'staged-not-published','grid':c.GRID,
  'source_plan_sha256':c.sha256(plan_path),'decision_snapshot_sha256':plan.get('decision_snapshot_sha256'),
  'land_input_kind':plan.get('land_input_kind','historical-v6-replay'),'land_lineage':plan.get('land_lineage'),'research_shore_method':plan.get('research_shore_method'),
  'decision_revision':plan.get('decision_revision'),'entity_revision':plan.get('entity_revision'),
  'physical_mask_sha256':plan['rle_inputs']['physical'].get('physical_mask_sha256'),
  'layer_manifests':[{'layer_id':x.get('layer_id'),'manifest_sha256':c.sha256(c.resolve_input(x['manifest_path'],plan_path.parent,root)),'priority':x['priority']} for x,_ in layers],
  'output':{'rows_path':rawr.name,'runs_path':rawu.name,'rows_sha256':c.sha256(rawr),'runs_sha256':c.sha256(rawu),'run_count':runs_written},
  'prefill_class_cells_by_code':counts,'physical_land_cells':land_cells,'assigned_continental_water_cells':assigned_cells,
  'residual_eligible_water_cells':residual_cells,'resolved_overlap_cells':overlap_cells,
  'direct_land_physical_water_code':land_water_code,'prior_ocean_water_labels_read':'none','physical_mask_invariance':'passed; every physical land/water center accounted exactly once'}
 report['processing_elapsed_seconds']=time.perf_counter()-processing_started
 write_json_exclusive(out/'prefill-audit.json',report)
 emit(json.dumps(report,indent=2))
if __name__=='__main__':main()

