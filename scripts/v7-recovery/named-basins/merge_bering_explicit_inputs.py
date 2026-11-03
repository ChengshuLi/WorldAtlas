#!/usr/bin/env python3
"""Validate and merge the two disjoint, current-mask Bering Sea assignment row shards."""
import argparse, gzip, hashlib, json, os, re
from pathlib import Path
import sys
BASE=Path('/workspace/scratch/127991fc8b8e/audit/shared-output-safety-20261103/integration-copies/patched-v4')
sys.path.insert(0,str(BASE))
import build_named_basin_assignments_row_shards_v2 as m
from exclusive_outputs import create_binary_exclusive, create_directory_exclusive, create_gzip_text_exclusive, create_text_exclusive, create_run_directory, write_json_exclusive
parser=argparse.ArgumentParser(description='Merge validated immutable Bering row shards from explicit inputs')
parser.add_argument('--first',required=True);parser.add_argument('--second',required=True)
parser.add_argument('--first-log',required=True);parser.add_argument('--second-log',required=True)
args=parser.parse_args()
BY=m.BY
RANGES=[(9113,11756),(11756,14124)]
FRAGMENTS=[Path(args.first),Path(args.second)]
LOGS=[Path(args.first_log),Path(args.second_log)]
FINAL=BY/'source-24119.jsonl.gz'

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def done_stats(log,sid):
 for line in Path(log).read_text().splitlines():
  try:q=json.loads(line)
  except Exception:continue
  if q.get('phase')=='shared-done' and str(q.get('source_id'))==sid:return q
 raise RuntimeError(f'{sid}: no completed stats in {log}')

def main():
 inv=json.load(open(m.INV));src=next(s for s in m.source_records(inv) if s['id']=='24119')
 sm,total,payload=m.read_spans(src)
 if payload.get('source_id')!='seavox-v19-mrgid-sr-24119':raise ValueError('unexpected source mask identity')
 if sha(src['path'])!=src['sha256']:raise ValueError('source mask hash changed')
 if FINAL.exists():raise FileExistsError(f'refusing to overwrite existing complete assignment {FINAL}')
 tmp=FINAL
 covered_rows=cell_counts={}
 cell_counts={}
 row_count=span_count=0;global_last=-1;shard_reports=[]
 with create_gzip_text_exclusive(tmp,encoding='utf8',compresslevel=6) as out:
  for (row_start,row_end),frag,log in zip(RANGES,FRAGMENTS,LOGS):
   stats=done_stats(log,'24119');shard_cells=0;shard_rows=0;shard_last=-1;shard_spans=0
   if not frag.exists():raise FileNotFoundError(f'fragment missing: {frag}')
   for line in gzip.open(frag,'rt',encoding='utf8'):
    q=json.loads(line);y=int(q['row'])
    if not row_start<=y<row_end:raise ValueError(f'{frag}: row {y} is outside [{row_start},{row_end})')
    if y<=shard_last or y<=global_last:raise ValueError(f'{frag}: duplicate/out-of-order row {y}')
    spans=q['spans'];last_x=-1;coverage=[]
    for z in spans:
     a,b,c=int(z['start']),int(z['end']),int(z['code'])
     if not(0<=a<b<=m.W) or a<last_x:raise ValueError(f'{frag}: invalid or overlapping span at row {y}: {z}')
     if c not in src['participants']:raise ValueError(f'{frag}: disallowed category {c} at row {y}')
     if z.get('rule_id')!='approved-named-basin-nearest-final-shore-v1':raise ValueError(f'{frag}: wrong rule at row {y}')
     if not str(z.get('member_id','')).startswith('seavox-v19-mrgid-sr-24119-nearest-'):raise ValueError(f'{frag}: wrong member at row {y}')
     last_x=b;shard_cells+=b-a;cell_counts[c]=cell_counts.get(c,0)+b-a;shard_spans+=1
     if coverage and coverage[-1][1]==a:coverage[-1]=(coverage[-1][0],b)
     else:coverage.append((a,b))
    if coverage!=sm.get(y,[]):raise ValueError(f'{frag}: source-mask coverage mismatch at row {y}')
    out.write(json.dumps(q,separators=(',',':'))+'\n')
    row_count+=1;shard_rows+=1;shard_last=y;global_last=y;span_count+=len(spans)
   expected_cells=sum(b-a for y,ints in sm.items() if row_start<=y<row_end for a,b in ints)
   expected_rows=sum(row_start<=y<row_end for y in sm)
   if shard_cells!=expected_cells or shard_rows!=expected_rows:raise ValueError(f'{frag}: cells/rows mismatch: {shard_cells}/{expected_cells}, {shard_rows}/{expected_rows}')
   if int(stats.get('assigned_cells',-1))!=shard_cells:raise ValueError(f'{frag}: log count mismatch')
   shard_reports.append({'row_range':[row_start,row_end],'path':str(frag),'sha256':sha(frag),'bytes':frag.stat().st_size,'row_count':shard_rows,'assigned_cells':shard_cells,'certified_cells':int(stats['certified']),'exact_nearest_cells':int(stats['exact']),'crop_boundary_uncertified_cells':int(stats['boundary_fail']),'log':str(log)})
 if row_count!=len(sm) or sum(cell_counts.values())!=total:raise ValueError(f'combined row/cell mismatch: {row_count}/{len(sm)}, {sum(cell_counts.values())}/{total}')
 # Verify each source row is covered exactly once, including rows that might have been omitted.
 with gzip.open(tmp,'rt',encoding='utf8') as f:
  actual=[int(json.loads(line)['row']) for line in f]
 if actual!=sorted(sm):raise ValueError('combined row sequence does not exactly equal source-mask row sequence')
 # Direct closed exclusive output; no replacement step.
 preserved=[str(frag) for frag in FRAGMENTS]  # Input shards stay immutable in place.
 report={'schema':'worldatlas-bering-shard-merge-qa-v1','status':'completed_candidate_not_published','source_id':'24119','source_geometry_sha256':src['source']['full_source_geometry_candidates'][0]['geometry_sha256_canonical_json'],'source_mask_path':src['path'],'source_mask_sha256':src['sha256'],'physical_mask_sha256':payload['grid']['physical_mask_sha256'],'assignment_script_sha256':sha(BASE/'build_named_basin_assignments_row_shards.py'),'row_ranges':[[a,b] for a,b in RANGES],'shards':shard_reports,'shard_script_sha256_by_range':{'9113-11756':'eed6014c478cf52170d90e93ec58b4ad6b5d25283af90be684e613d9abf8b44f','11756-14124':'37e569bfb460fe946eede54b52183510c46317e1b9378bae121f792c3f33577e'},'explicit_input_paths':[str(x) for x in FRAGMENTS],'preserved_shard_paths':preserved,'merged_output':{'path':str(FINAL),'sha256':sha(FINAL),'bytes':FINAL.stat().st_size,'rows':row_count,'spans':span_count,'cells':sum(cell_counts.values()),'cells_by_code':{str(k):v for k,v in sorted(cell_counts.items())}},'checks':{'all_5010_source_rows_present_once':True,'per_row_union_exactly_matches_physical_water_mask':True,'codes_within_approved_participants':True,'all_rule_ids_correct':True,'no_duplicate_rows_or_spans':True,'crop_boundary_uncertified_cells':sum(x['crop_boundary_uncertified_cells'] for x in shard_reports)}}
 out=m.OUT/'bering-24119-shard-merge-qa.json';write_json_exclusive(out,report)
 readme=m.OUT/'bering-24119-shards-readme.txt'
 with create_text_exclusive(readme,encoding='utf-8',newline='\n') as f:f.write('Validated Bering Sea 24119 row-shard fragments remain immutable beside the merged output. See bering-24119-shard-merge-qa.json for hashes and QA.\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
