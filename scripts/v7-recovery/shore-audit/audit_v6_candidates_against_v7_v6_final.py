#!/usr/bin/env python3
"""Exact 5,089-cell final V7 check against V6 nearest-shore candidates.

Uses the complete per-source named-basin manifest and its explicit overlap
precedence, plus pinned V6/physical RLE and a closed final V7 RLE+manifest.
No V6/V7/source inputs are changed. Outputs are fresh O_EXCL snapshots.
"""
from __future__ import annotations
import argparse,collections,gzip,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'shared-output-safety-20261103'))
from exclusive_outputs import create_gzip_text_exclusive,create_run_directory,write_json_exclusive
spec=importlib.util.spec_from_file_location('audit_v3',HERE/'audit_v6_candidates_against_v7_v3.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
NAMED_MANIFEST_SHA='fcacb79fba82a83ec853bbece2453be7cb74fb517cab4f37fcc6171ed287b449'
PHYSICAL_MASK_SHA='660ac7608f72b447c95eb8820979951fe589f25c70303efe732b374049127017'


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def read_mask(path):
 b=Path(path).read_bytes()
 try:b=gzip.decompress(b)
 except OSError:pass
 return json.loads(b)

def validate_named_sources(path,byrow):
 if sha(path)!=NAMED_MANIFEST_SHA:raise ValueError('named-basin source manifest SHA mismatch')
 m=json.loads(Path(path).read_text());cov=m.get('coverage',{})
 if m.get('status')!='complete_candidate_not_published' or cov.get('complete') is not True or cov.get('source_count')!=93 or cov.get('per_source_assignment_outputs_validated')!=93:
  raise ValueError('named-basin source manifest is not the complete 93-source candidate manifest')
 if m.get('input_pins',{}).get('physical_mask_sha256')!=PHYSICAL_MASK_SHA:raise ValueError('named-basin manifest physical-mask pin mismatch')
 if m.get('input_pins',{}).get('final_land_rows_sha256')!=a.V6_ROWS_SHA or m.get('input_pins',{}).get('final_land_runs_sha256')!=a.V6_RUNS_SHA:raise ValueError('named-basin manifest final-land pin mismatch')
 srcs=m.get('source_layers',[])
 if len(srcs)!=93:raise ValueError(f"expected 93 source layers, got {len(srcs)}")
 pins=m.get('input_pins',{})
 inventory=Path(pins.get('inventory_path',''))
 qa_path=Path(pins.get('source_mask_integrity_qa_path',''))
 if not inventory.is_file() or sha(inventory)!=pins.get('inventory_sha256'):raise ValueError('source inventory pin mismatch')
 if not qa_path.is_file() or sha(qa_path)!=pins.get('source_mask_integrity_qa_sha256'):raise ValueError('source-mask QA pin mismatch')
 qa=json.loads(qa_path.read_text());qa_by_sha={str(r['mask_sha256']):r for r in qa.get('mask_results',[])}
 if qa.get('status')!='pass' or len(qa_by_sha)!=93:raise ValueError('source-mask physical QA is not complete/pass')
 byid={};mask_hits=collections.defaultdict(list)
 for s in srcs:
  sid=str(s.get('source_id')); 
  if not sid or sid in byid:raise ValueError(f"missing/duplicate source id: {sid}")
  byid[sid]=s
  mask=s.get('full_source_mask',{}); assignment=s.get('assignment_output',{})
  if not mask.get('path') or not assignment.get('path') or not mask.get('sha256') or not assignment.get('sha256'):raise ValueError(f"source {sid} lacks pinned artifacts")
  if assignment.get('source_mask_coverage_exact') is not True:raise ValueError(f"source {sid} mask coverage is not exact")
  if mask.get('physical_mask_sha256') not in (None,PHYSICAL_MASK_SHA):raise ValueError(f"source {sid} physical-mask mismatch")
  mp=Path(mask['path']);ap=Path(assignment['path'])
  if sha(mp)!=mask['sha256']:raise ValueError(f"source mask hash mismatch: {sid}")
  qrec=qa_by_sha.get(mask['sha256'])
  if not qrec or int(qrec.get('physical_nonwater_cells',-1))!=0:raise ValueError(f"source mask is not QA-verified physical water: {sid}")
  if sha(ap)!=assignment['sha256']:raise ValueError(f"source assignment hash mismatch: {sid}")
  # Source mask is the authority for whether a named rule covers a candidate cell.
  obj=read_mask(mp); spans=obj.get('spans')
  if not isinstance(spans,list):raise ValueError(f"bad source mask spans for {sid}")
  for z in spans:
   if isinstance(z,list):y,x0,x1=map(int,z[:3])
   else:y,x0,x1=int(z['row']),int(z['start']),int(z['end'])
   for c in byrow.get(y,[]):
    x=int(c['x'])
    if x0<=x<x1:mask_hits[(y,x)].append(sid)
 # Resolve the declared pairwise priority only. There is no implicit global ranking.
 explicit={}
 precedence=m.get('precedence',{})
 if precedence.get('unapproved_or_unresolved_overlaps')!=0:raise ValueError('unapproved/unresolved source overlaps remain')
 for rule in precedence.get('measured_inter_basin_precedence',[]):
  explicit[(str(rule['winner_source_id']),str(rule['loser_source_id']))]=rule
 assignments={}; relevant=set(sid for vals in mask_hits.values() for sid in vals)
 for sid in relevant:
  s=byid[sid];ap=Path(s['assignment_output']['path']);expected_rule=s['assignment_output'].get('rule_id')
  if not str(expected_rule).startswith('approved-'):raise ValueError(f"non-approved source rule {sid}: {expected_rule}")
  hits={}
  with gzip.open(ap,'rt',encoding='utf-8') as f:
   for ln,line in enumerate(f,1):
    if not line.strip():continue
    row=json.loads(line);y=int(row['row'])
    if y not in byrow:continue
    for span in row.get('spans',[]):
     x0,x1,code=int(span['start']),int(span['end']),int(span['code'])
     if span.get('rule_id')!=expected_rule:raise ValueError(f"assignment rule mismatch {sid}:{ln}")
     if not (span.get('member_id') or span.get('source_member_id')):raise ValueError(f"assignment member missing {sid}:{ln}")
     if not 1<=code<=6:raise ValueError(f"invalid named basin code {sid}:{ln}")
     for c in byrow[y]:
      x=int(c['x']);key=(y,x)
      if sid in mask_hits.get(key,[]) and x0<=x<x1:
       if key in hits:raise ValueError(f"duplicate assignment within {sid} at {key}")
       hits[key]={'source_id':sid,'code':code,'member_id':span.get('member_id') or span.get('source_member_id'),'rule_id':expected_rule}
  for key,ids in mask_hits.items():
   if sid in ids:
    if key not in hits:raise ValueError(f"candidate mask cell lacks completed assignment: {sid} {key}")
    assignments.setdefault(key,[]).append(hits[key])
 resolved={}
 for key,vals in assignments.items():
  if len(vals)==1:resolved[key]=vals[0];continue
  # Find the unique declared winner over all other overlapping sources.
  ids={v['source_id'] for v in vals};wins=[]
  for candidate in ids:
   if all(candidate==other or (candidate,other) in explicit for other in ids):wins.append(candidate)
  if len(wins)!=1:raise ValueError(f"ambiguous source priority at candidate {key}: {sorted(ids)}")
  winner=wins[0];selected=[v for v in vals if v['source_id']==winner]
  if len(selected)!=1:raise ValueError(f"duplicate winner assignment at {key}")
  resolved[key]=selected[0]
 return m,resolved,{'source_count':len(srcs),'source_mask_hashes_checked':len(srcs),'source_assignment_hashes_checked':len(srcs),'candidate_mask_cells':len(mask_hits),'candidate_cells_with_multiple_masks':sum(len(v)>1 for v in mask_hits.values()),'candidate_source_ids':dict(collections.Counter(sid for ids in mask_hits.values() for sid in ids)),'precedence_overlap_cells':cov.get('approved_overlap_cells_resolved'),'unresolved_source_overlaps':precedence.get('unapproved_or_unresolved_overlaps')}


def validate_v7_manifest(path,rows,runs):
 m=json.loads(Path(path).read_text());status=str(m.get('status','')).lower()
 schema=m.get('schema')
 row_range=m.get('row_range')
 if row_range is not None and row_range != [0,a.H]:
  raise ValueError(f"V7 manifest does not cover the complete grid row range: {row_range}")
 completed_status=(any(z in status for z in ('complete','final','passed')) and
                   not any(z in status for z in ('partial','provisional','running','active','failed')))
 # The full compositor's closed output audit deliberately says staged-not-published;
 # accept it only for its exact schema and full-grid row range, never for a partial shard.
 completed_composition=(schema=='worldatlas-v7-full-grid-composition-audit-v1' and
                        status=='staged-not-published' and row_range==[0,a.H])
 if not (completed_status or completed_composition):
  raise ValueError(f"V7 manifest not final/complete: {m.get('status')}")
 g=m.get('grid',m.get('invariants',{}).get('grid',{}))
 if int(g.get('width',-1))!=a.W or int(g.get('height',-1))!=a.H:raise ValueError('V7 grid dimensions mismatch')
 def find(obj,names):
  if isinstance(obj,dict):
   for k,v in obj.items():
    if k in names and isinstance(v,str) and len(v)==64:return v.lower()
   for v in obj.values():
    h=find(v,names)
    if h:return h
  elif isinstance(obj,list):
   for v in obj:
    h=find(v,names)
    if h:return h
  return None
 rh=find(m,{'rows_sha256','raw_rows_sha256','grid_rows_sha256','final_rows_sha256','rows_u32le_sha256','raw_rows_u32le_sha256'})
 uh=find(m,{'runs_sha256','raw_runs_sha256','grid_runs_sha256','final_runs_sha256','runs_u32le_sha256','raw_runs_u32le_sha256'})
 if not rh or not uh:raise ValueError('final V7 manifest must pin raw rows and runs SHA-256')
 if sha(rows)!=rh or sha(runs)!=uh:raise ValueError('V7 raw files differ from final manifest pins')
 return {'status':m.get('status'),'manifest':str(path),'rows_sha256':rh,'runs_sha256':uh}


def run(args):
 byrow,cells,span_count=a.load_candidates(args.candidate_spans)
 v6=a.load_rle(args.v6_rows,args.v6_runs,expected_rows=a.V6_ROWS_SHA,expected_runs=a.V6_RUNS_SHA)
 phys=a.load_rle(args.physical_rows,args.physical_runs,expected_rows=a.PHYSICAL_ROWS_SHA,expected_runs=a.PHYSICAL_RUNS_SHA)
 v7meta=validate_v7_manifest(args.v7_manifest,args.v7_rows,args.v7_runs)
 v7=a.load_rle(args.v7_rows,args.v7_runs)
 named_manifest,named,namedmeta=validate_named_sources(args.named_source_manifest,byrow)
 totals=collections.Counter();pairs=collections.defaultdict(collections.Counter);ledger=[];groups=collections.Counter();java=[];north=[];feedback=[]
 for (y,x),c in sorted(cells.items()):
  old=a.code_at(v6,y,x);physical=a.code_at(phys,y,x);actual=a.code_at(v7,y,x)
  if old!=c['from_code']:raise ValueError(f"candidate V6 mismatch at {(y,x)}: {old} vs {c['from_code']}")
  if physical!=1:raise ValueError(f"physical mask is not WATER code 1 at {(y,x)}: {physical}")
  basin=named.get((y,x));expected=int(basin['code']) if basin else int(c['to_code'])
  # Classify by the observed final value first. A basin/coast policy difference
  # is diagnostic only; it cannot excuse an actual value that misses policy.
  if actual==expected and actual!=old:
   reason='confirmed_v6_wrong_corrected'
  elif actual==expected==old and basin is not None:
   reason='valid_due_named_basin'
  else:
   reason='unresolved_or_other'
  named_vs_coast=('not_applicable_no_named_basin' if basin is None else
   ('named_matches_coast_candidate' if expected==int(c['to_code']) else 'named_changes_coast_candidate'))
  expected_source='named_basin_assignment' if basin is not None else 'coastal_candidate'
  totals[reason]+=1;pair=f"{c['from_code']}->{c['to_code']}";pairs[pair][reason]+=1
  group=a.region(y,x);groups[group or 'other']+=1
  item={'row':y,'x':x,'lon_center':-180+(x+.5)*a.STEP,'lat_center':90-(y+.5)*a.STEP,'candidate_from_code':int(c['from_code']),'candidate_to_code':int(c['to_code']),'v6_code':old,'physical_code':physical,'named_basin':basin,'expected_v7_code':expected,'expected_code_source':expected_source,'actual_v7_code':actual,'named_vs_coast_candidate':named_vs_coast,'classification':reason,'geographic_group':group}
  ledger.append(item)
  if group=='Java':java.append(item)
  if group=='North_Halmahera':north.append(item)
  if (y,x) in a.JAVA_FEEDBACK:feedback.append(item)
 if len(java)!=37 or len(north)!=12 or len(feedback)!=3:raise ValueError('Java/North-Halmahera or Java feedback subset count changed')
 summary={'schema':'v6-nearestshore-final-v7-cell-check-v1','status':'complete','candidate_spans':span_count,'candidate_cells':len(cells),'classifications':dict(totals),'by_transition':{k:dict(v) for k,v in sorted(pairs.items())},'geographic_groups':dict(groups),'java_cells':java,'north_halmahera_cells':north,'java_feedback_cells':feedback,'v7_manifest':v7meta,'named_basin_source_manifest':{'sha256':NAMED_MANIFEST_SHA,'status':named_manifest.get('status'),'coverage':named_manifest.get('coverage'),'precedence':named_manifest.get('precedence'),'candidate_validation':namedmeta},'candidate_sha256':sha(args.candidate_spans),'v6_rows_sha256':sha(args.v6_rows),'v6_runs_sha256':sha(args.v6_runs),'physical_rows_sha256':sha(args.physical_rows),'physical_runs_sha256':sha(args.physical_runs),'interpretation':{'confirmed_v6_wrong_corrected':'V6 is candidate from_code and actual V7 equals policy-expected code different from V6','valid_due_named_basin':'fresh approved named source assignment expects and V7 preserves V6 code','unresolved_or_other':'expected/actual mismatch or other unexplained code; not counted as fixed'}}
 return summary,ledger

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--candidate-spans',type=Path,required=True);ap.add_argument('--v6-rows',type=Path,required=True);ap.add_argument('--v6-runs',type=Path,required=True)
 ap.add_argument('--physical-rows',type=Path,required=True);ap.add_argument('--physical-runs',type=Path,required=True)
 ap.add_argument('--v7-rows',type=Path,required=True);ap.add_argument('--v7-runs',type=Path,required=True);ap.add_argument('--v7-manifest',type=Path,required=True)
 ap.add_argument('--named-source-manifest',type=Path,required=True);ap.add_argument('--output-parent',type=Path,required=True)
 args=ap.parse_args();summary,ledger=run(args);out=create_run_directory(args.output_parent,'final-v7-candidate-check')
 with create_gzip_text_exclusive(out/'candidate-cell-ledger.jsonl.gz') as f:
  for x in ledger:f.write(json.dumps(x,separators=(',',':'),sort_keys=True)+'\n')
 write_json_exclusive(out/'summary.json',summary,indent=2)
 print(json.dumps({'status':'complete','run_dir':str(out),'classifications':summary['classifications'],'by_transition':summary['by_transition'],'java_feedback':summary['java_feedback_cells']},indent=2))
if __name__=='__main__':main()
