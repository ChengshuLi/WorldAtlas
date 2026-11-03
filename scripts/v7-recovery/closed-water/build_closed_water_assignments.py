#!/usr/bin/env python3
"""Assign zero-source-cut closed-water components from final 1–6/17–22 classes.

This staged-only builder reuses the validated segment-midpoint/ exact spherical
nearest-shore kernel from `build_named_basin_assignments.py`. It accepts only a
final prefill class raster (land 17–22, water 1–6, residual eligible 0), never
the mask-only placeholder class 1. Direct assignment applies if all physical
land + final continental-water boundary contacts identify one continent. Mixed
components use per-cell nearest final assigned-land shore among those contacts.
Components touching any artificial source cut are rejected for this closed-
pocket procedure and retain their ocean-parent review path.
"""
from __future__ import annotations
import argparse,hashlib,json,math,struct,sys
from collections import Counter,defaultdict
from pathlib import Path
EXCLUSIVE_DIR=Path(__file__).resolve().parents[3]/'audit'/'shared-output-safety-20261103'/'integration-copies'/'patched-v4'
sys.path.insert(0,str(EXCLUSIVE_DIR))
from exclusive_outputs import create_directory_exclusive, create_text_exclusive, write_json_exclusive
import numpy as np
from scipy.spatial import cKDTree
from rle_inputs import RunRasterU32LE,code_intervals,validate_prefill_row

W,H=131072,54614;STEP=360/W
LABELS={1:'africa',2:'asia',3:'europe',4:'north-america',5:'south-america',6:'oceania'}
LAND_TO_WATER={17:1,18:2,19:3,20:4,21:5,22:6}

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def read_span_rows(run_dir):
 p=Path(run_dir);raw=(p/'unseeded_rows.u64le').read_bytes()
 offsets=struct.unpack('<%dQ'%(H+1),raw);data=p/'unseeded_component_spans.u32le'
 if offsets[0]!=0 or offsets[-1]*12!=data.stat().st_size or any(a>b for a,b in zip(offsets,offsets[1:])):
  raise ValueError('bad unseeded component span row offsets')
 per_component=defaultdict(list);count=cells=0
 with data.open('rb') as f:
  for y in range(H):
   f.seek(offsets[y]*12)
   for _ in range(offsets[y+1]-offsets[y]):
    a,b,root=struct.unpack('<III',f.read(12));per_component[root].append((y,a,b));count+=1;cells+=b-a
 return per_component,count,cells

def edge_counts_for_components(per_component,class_rle):
 """Count component boundary edges against final water 1–6 / land 17–22."""
 results={root:{'codes':Counter(),'unknown_zero_edges':0} for root in per_component}
 # Invert spans by row for a single sequential RLE scan.
 by_row=defaultdict(list)
 for root,spans in per_component.items():
  for y,a,b in spans:by_row[y].append((a,b,root))
 for spans in by_row.values():spans.sort()
 by_row_starts={y:[a for a,_,_ in spans] for y,spans in by_row.items()}
 cache={}
 def row(y):
  if y<0 or y>=H:return ([],[])
  if y not in cache:
   rr=class_rle.row(y);cache[y]=(rr,[e for e,_ in rr])
  return cache[y]
 def code_at(data,x):
  runs,ends=data;i=__import__('bisect').bisect_right(ends,x)
  return runs[i][1] if i<len(runs) else None
 def component_at(y,x):
  spans=by_row.get(y,())
  i=__import__('bisect').bisect_right(by_row_starts.get(y,()),x)-1
  return spans[i][2] if i>=0 and spans[i][0]<=x<spans[i][1] else None
 def external_parts(root,y,lo,hi):
  """Split a neighboring interval around cells belonging to this component."""
  cursor=lo
  for a,b,r in by_row.get(y,()):
   if r!=root or b<=cursor or a>=hi:continue
   if cursor<a:yield cursor,min(a,hi)
   cursor=max(cursor,b)
   if cursor>=hi:return
  if cursor<hi:yield cursor,hi
 def add_overlap(root,data,lo,hi):
  runs,ends=data;i=__import__('bisect').bisect_right(ends,lo);start=ends[i-1] if i else 0
  while i<len(runs) and start<hi:
   end,code=runs[i];n=max(0,min(hi,end)-max(lo,start))
   if n:
    target=code if code in range(1,7) else LAND_TO_WATER.get(code)
    if target:results[root]['codes'][target]+=n
    elif code==0:results[root]['unknown_zero_edges']+=n
   start=end;i+=1
 for y in range(H):
  spans=by_row.get(y,())
  if not spans:cache.clear();continue
  above=row(y-1);below=row(y+1);same=row(y)
  for a,b,root in spans:
   # The input class raster stores every eligible cell as 0, including the
   # cells of the component under review. Exclude self-membership so those
   # interior zero neighbors are not mistaken for unresolved external edges.
   for u,v in external_parts(root,y-1,a,b):add_overlap(root,above,u,v)
   for u,v in external_parts(root,y+1,a,b):add_overlap(root,below,u,v)
   for x in (a-1,b):
    if x<0:x=W-1
    elif x>=W:x=0
    if component_at(y,x)==root:continue
    code=code_at(same,x);target=code if code in range(1,7) else LAND_TO_WATER.get(code)
    if target:results[root]['codes'][target]+=1
    elif code==0:results[root]['unknown_zero_edges']+=1
  cache.clear()
 return results

def row_nodes(run_dir):
 p=Path(run_dir);offs=struct.unpack('<%dQ'%(H+1),(p/'node_rows.u64le').read_bytes())
 return p/'node_intervals.bin',offs

def intervals_cover(candidate,required):
 """True iff sorted half-open candidate intervals cover every required cell."""
 j=0
 for a,b in required:
  while j<len(candidate) and candidate[j][1]<=a:j+=1
  if j>=len(candidate) or candidate[j][0]>a or candidate[j][1]<b:return False
 return True

def candidate_method(participant_codes,*,source_cut_edges=0,crop_edge=False,unknown_zero_edges=0):
 """Closed-water assignment decision; never turns unresolved zeros into a code."""
 if source_cut_edges:return 'retain-ocean-parent-source-cut-review'
 if crop_edge:return 'open-at-grid-crop-review'
 if unknown_zero_edges:return 'pending-unknown-code-0-boundary'
 codes=sorted(set(map(int,participant_codes)))
 if not codes:return 'no-known-shore-boundary-review'
 if len(codes)==1:return 'direct-single-final-shore-class'
 return 'nearest-final-assigned-shore'

def validate_zero_mask(per_class,run_dir,allow_extra=False,physical_rle=None,class_rle=None):
 """Prove provisional eligible cells remain zero; optionally allow more unknown 0s."""
 path,offs=row_nodes(run_dir);nodes=path.open('rb');checked=0
 for y in range(H):
  nodes.seek(offs[y]*12);xs=[]
  for _ in range(offs[y+1]-offs[y]):
   a,b,_=struct.unpack('<III',nodes.read(12))
   if xs and xs[-1][1]==a:xs[-1]=(xs[-1][0],b)
   else:xs.append((a,b))
  candidate=per_class(y)
  if physical_rle is not None and class_rle is not None:
   validate_prefill_row(physical_rle.row(y),class_rle.row(y),W)
  if not allow_extra:
   if xs!=candidate:raise ValueError(f'final class-0 eligibility differs from provisional ocean mask at row {y}')
   checked+=sum(b-a for a,b in xs)
  else:
   if not intervals_cover(candidate,xs):
    raise ValueError(f'provisional ocean-eligible cells are not all zero in partial class row {y}')
   checked+=sum(b-a for a,b in xs)
 nodes.close();return checked

def pack_row_spans(row_spans,spans):
 """Append non-overlapping assigned intervals and coalesce identical neighbors."""
 for a,b,code,rule,member in spans:
  if b<=a:continue
  z={'start':a,'end':b,'code':code,'rule_id':rule,'member_id':member}
  if row_spans and a<row_spans[-1]['end']:raise ValueError(f'closed-water output overlap: {a}:{b}')
  if row_spans and a==row_spans[-1]['end'] and all(row_spans[-1][k]==z[k] for k in ('code','rule_id','member_id')):row_spans[-1]['end']=b
  else:row_spans.append(z)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--run-dir',required=True);ap.add_argument('--prefill-rows',required=True);ap.add_argument('--prefill-runs',required=True);ap.add_argument('--prefill-audit',required=True);ap.add_argument('--prefill-plan')
 ap.add_argument('--physical-rows',required=True);ap.add_argument('--physical-runs',required=True);ap.add_argument('--land-rows',required=True);ap.add_argument('--land-runs',required=True)
 ap.add_argument('--output-dir',required=True);ap.add_argument('--chunk',type=int,default=5000);ap.add_argument('--partial',action='store_true',help='allow additional unknown code-0 cells; never assign components touching them')
 args=ap.parse_args()
 out=create_directory_exclusive(args.output_dir)
 run=Path(args.run_dir);run_manifest=json.loads((run/'manifest.json').read_text())
 pre_audit=json.loads(Path(args.prefill_audit).read_text())
 allowed_schemas={'worldatlas-v7-prefill-class-rle-audit-v1'}
 if args.partial:allowed_schemas.add('worldatlas-v7-partial-known-class-unknown-shared-mask-audit-v1')
 if pre_audit.get('schema') not in allowed_schemas:raise ValueError(f'unsupported prefill audit schema: {pre_audit.get("schema")}')
 if args.partial and 'partial' not in str(pre_audit.get('status','')).lower():raise ValueError('partial mode requires an explicitly partial class audit')
 if pre_audit.get('status')=='mask-only-placeholder-not-final-assignment':raise ValueError('mask-only code 1 cannot be treated as a continent class')
 for arg,expected in ((args.prefill_rows,pre_audit['output']['rows_sha256']),(args.prefill_runs,pre_audit['output']['runs_sha256'])):
  if sha(arg)!=expected:raise ValueError(f'prefill hash mismatch: {arg}')
 legacy_read=pre_audit.get('prior_ocean_water_labels_read',pre_audit.get('legacy_water_labels_read'))
 if str(legacy_read).lower() not in ('none','false'):raise ValueError('prefill must not inherit old ocean labels')
 pins=pre_audit.get('rle_input_sha256',{})
 if pins:
  for key,arg in (('physical_rows',args.physical_rows),('physical_runs',args.physical_runs),('v6_land_rows',args.land_rows),('v6_land_runs',args.land_runs)):
   if pins.get(key)!=sha(arg):raise ValueError(f'prefill source pin mismatch for {key}: {arg}')
  prefill_plan_sha=None
 else:
  # The final prefill audit pins its plan, not its raw RLE paths. Verify that
  # immutable plan against the supplied physical and land inputs before use.
  if not args.prefill_plan:raise ValueError('prefill audit has no raw RLE pins; --prefill-plan is required')
  plan_path=Path(args.prefill_plan);plan_sha=sha(plan_path)
  if plan_sha!=pre_audit.get('source_plan_sha256'):raise ValueError('prefill plan SHA does not match final audit')
  plan=json.loads(plan_path.read_text());rp=plan.get('rle_inputs',{})
  expected=(('physical','rows_path',args.physical_rows),('physical','runs_path',args.physical_runs),('v6','rows_path',args.land_rows),('v6','runs_path',args.land_runs))
  for group,key,arg in expected:
   item=rp.get(group,{})
   hash_key='rows_sha256' if key=='rows_path' else 'runs_sha256'
   if item.get(hash_key)!=sha(arg):raise ValueError(f'prefill plan input hash mismatch for {group}.{key}: {arg}')
  if plan.get('status')!='final-source-backed-prefill-candidate':raise ValueError('prefill plan is not the final source-backed candidate')
  if rp.get('physical',{}).get('physical_mask_sha256')!=pre_audit.get('physical_mask_sha256'):
   raise ValueError('prefill plan physical-mask fingerprint differs from final audit')
  prefill_plan_sha=plan_sha
 rinputs=run_manifest['inputs']
 if rinputs.get('physical_rows',{}).get('sha256')!=sha(args.physical_rows) or rinputs.get('physical_runs',{}).get('sha256')!=sha(args.physical_runs):
  raise ValueError('physical RLE does not match provisional ocean run')
 prefill=RunRasterU32LE(args.prefill_rows,args.prefill_runs,W,H,offset_bytes=4)
 physical_rle=RunRasterU32LE(args.physical_rows,args.physical_runs,W,H,offset_bytes=4)
 # Exact eligibility identity is mandatory because the precomputed components
 # may only be reused if the final continental assignments did not change the 0 mask.
 n_eligible=validate_zero_mask(lambda y:code_intervals(prefill.row(y),0),run,allow_extra=args.partial,physical_rle=physical_rle,class_rle=prefill)
 if n_eligible!=run_manifest.get('eligible_water_cells'):raise ValueError('provisional ocean eligible-cell total differs from the run manifest')
 all_prefill_zero=sum((b-a) for y in range(H) for a,b in code_intervals(prefill.row(y),0))
 extra_zero=all_prefill_zero-n_eligible
 print(json.dumps({'phase':'validated-prefill','eligible_cells':n_eligible,'extra_zero_cells':extra_zero,'prefill_rows_sha256':sha(args.prefill_rows),'prefill_runs_sha256':sha(args.prefill_runs)},separators=(',',':')),flush=True)
 if extra_zero and not args.partial:raise ValueError('final class layer has unknown code-0 cells beyond provisional ocean eligibility; use --partial only for an explicitly partial prefill')
 per_component,nspans,ncells=read_span_rows(run)
 if len(per_component)!=395 or ncells!=6_660_288 or nspans!=24_233:
  raise ValueError(f'unexpected provisional residual census: {len(per_component)} components / {ncells} cells / {nspans} spans')
 for q in run_manifest['components']:
  if q['ocean_code'] is None and q['source_barrier_contact_edge_count']!=0:raise ValueError('source-cut component cannot enter closed-water pocket path')
 adjacency=edge_counts_for_components(per_component,prefill)
 print(json.dumps({'phase':'validated-components','components':len(per_component),'spans':nspans,'cells':ncells,'components_with_external_zero_edges':sum(v['unknown_zero_edges']>0 for v in adjacency.values())},separators=(',',':')),flush=True)
 participants={r:sorted(adjacency[r]['codes']) for r in per_component}
 pending={r for r in per_component if adjacency[r]['unknown_zero_edges']>0}
 open_crop={r for r,spans in per_component.items() if any(y==0 or y==H-1 for y,_,_ in spans)}
 pending|=open_crop
 if open_crop and not args.partial:raise ValueError(f'{len(open_crop)} unseeded components touch the latitude crop edge and are not enclosed pockets')
 if any(not x and r not in pending for r,x in participants.items()):raise ValueError('component with no known 1–6/17–22 boundary and no code-0 uncertainty')
 if pending and not args.partial:raise ValueError('final class layer unexpectedly leaves code-0 cells adjacent to a closed component')
 for root,codes in participants.items():
  if root in pending:continue
  if not codes or any(c not in range(1,7) for c in codes):raise AssertionError(codes)
 # Load the pinned physical and final-land RLEs for nearest-shore classification.
 import numpy as np
 physical_rows=np.memmap(args.physical_rows,dtype='<u4',mode='r',shape=(H+1,));physical_runs=np.memmap(args.physical_runs,dtype='<u4',mode='r')
 land_rows=np.memmap(args.land_rows,dtype='<u4',mode='r',shape=(H+1,));land_runs=np.memmap(args.land_runs,dtype='<u4',mode='r')
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'full-water-rebuild-20261103'))
 import build_named_basin_assignments as shore
 shore.PAD_DEG=8.0
 assigned_by_row=defaultdict(list);code_counts=Counter();component_methods={};nearest_qas={}
 pending_cells=sum(sum(b-a for _,a,b in per_component[r]) for r in pending)
 for root,spans in sorted(per_component.items()):
  codes=participants[root]
  crop_edge=any(y==0 or y==H-1 for y,_,_ in spans)
  method=candidate_method(codes,unknown_zero_edges=adjacency[root]['unknown_zero_edges'],crop_edge=crop_edge)
  if method in ('open-at-grid-crop-review','pending-unknown-code-0-boundary'):
   print(json.dumps({'phase':'component-pending','root':root,'method':method,'cells':sum(b-a for _,a,b in spans),'unknown_external_zero_edges':adjacency[root]['unknown_zero_edges']},separators=(',',':')),flush=True)
   component_methods[str(root)]={'method':method,'participant_codes_known':codes,
     'unknown_code0_boundary_edges':adjacency[root]['unknown_zero_edges'],'cells':sum(b-a for _,a,b in spans)}
   continue
  if method=='direct-single-final-shore-class':
   code=codes[0]
   for y,a,b in spans:assigned_by_row[y].append((a,b,code,'closed-water-pocket-direct-final-shore-v1',f'closed-water-pocket-direct-final-shore-category-{code}'));code_counts[code]+=b-a
   component_methods[str(root)]={'method':method,'participant_codes':codes,'cells':sum(b-a for _,a,b in spans)}
   print(json.dumps({'phase':'component-direct','root':root,'code':code,'cells':sum(b-a for _,a,b in spans)},separators=(',',':')),flush=True)
   continue
  if method!='nearest-final-assigned-shore':raise ValueError(f'component {root} cannot be safely assigned: {method}')
  print(json.dumps({'phase':'component-nearest-start','root':root,'participant_codes':codes,'cells':sum(b-a for _,a,b in spans)},separators=(',',':')),flush=True)
  # Mixed-continent enclosed body: nearest physical shore among all final
  # participant classes, using the same certified midpoint-bound/exact-spherical
  # kernel as named-basin assignments.
  sm=defaultdict(list)
  for y,a,b in spans:sm[y].append((a,b))
  x0,x1,y0,y1=shore.crop_for_group([None],[sm])
  edges,nedge=shore.build_edges(x0,x1,y0,y1,set(codes),physical_rows,physical_runs,land_rows,land_runs)
  if not len(edges['mids']) or not set(codes).issubset(set(map(int,edges['_category_values']))):
   raise ValueError(f'component {root} nearest-shore crop lacks participant shoreline categories {codes}')
  class_edges={};class_trees={}
  for code in codes:
   mask=edges['category']==code
   class_edges[code]={k:edges[k][mask] for k in ('mids','lat0','lon0','lat1','lon1','kind','half_lengths','category')}
   class_trees[code]=cKDTree(class_edges[code]['mids'],compact_nodes=True,balanced_tree=True)
  tree=None;certified=exactn=0;maxdist=maxbd=0.0
  for y,ints in shore.unwrapped_rows(sm,x0,x1):
   latc=90-(y+.5)*STEP
   for a,b in ints:
    for st in range(a,b,args.chunk):
     en=min(st+args.chunk,b);xx=np.arange(st,en,dtype=np.float64);lat=np.full(len(xx),latc);lon=-180+(xx+.5)*STEP
     bd=shore.boundary_lower(lat,lon,x0,x1,y0,y1);pts=shore.geom.unit(lat,lon)
     result,exact,dist,invalid,cert=shore.classify(pts,lat,lon,bd,edges,tree,codes,class_edges,class_trees)
     if invalid:raise ValueError(f'component {root} nearest shore not certified inside crop ({invalid} cells)')
     certified+=cert;exactn+=int(exact.sum());maxdist=max(maxdist,float(dist.max()) if len(dist) else 0);maxbd=max(maxbd,float(bd.max()) if len(bd) else 0)
     cuts=np.r_[0,np.flatnonzero(np.diff(result)!=0)+1,len(result)]
     for ia,ib in zip(cuts[:-1],cuts[1:]):
      code=int(result[ia]);cur=st+int(ia);stop=st+int(ib)
      while cur<stop:
       edge=((cur//W)+1)*W;limit=min(stop,edge);gx=cur%W;gb=gx+(limit-cur)
       assigned_by_row[y].append((gx,gb,code,'closed-water-pocket-nearest-final-shore-v1',f'closed-water-pocket-nearest-final-shore-category-{code}'))
       code_counts[code]+=limit-cur;cur=limit
  nearest_qas[str(root)]={'participant_codes':codes,'shore_segments':len(edges['mids']),'crop_bounds':[x0,x1,y0,y1],'certified_cells':certified,'exact_cells':exactn,'crop_uncertified_cells':0,'max_nearest_distance_m':maxdist,'max_crop_lower_bound_m':maxbd}
  component_methods[str(root)]={'method':'nearest-final-assigned-shore','participant_codes':codes,'cells':sum(b-a for _,a,b in spans)}
  print(json.dumps({'phase':'component-nearest-done','root':root,'certified':certified,'exact':exactn,'max_distance_m':maxdist},separators=(',',':')),flush=True)
  del tree,class_trees,class_edges,edges
 print(json.dumps({'phase':'classification-complete','assigned_cells':sum(code_counts.values()),'pending_cells':pending_cells,'methods':dict(Counter(v['method'] for v in component_methods.values()))},separators=(',',':')),flush=True)
 # Complete-row JSONL output, with exactly one non-overlapping class per residual cell.
 out_file=out/'closed-water-component-assignments.jsonl';total=outspans=0
 with create_text_exclusive(out_file,encoding='utf8',newline='\n') as f:
  for y in range(H):
   xs=sorted(assigned_by_row.get(y,()),key=lambda z:z[0]);row=[]
   for z in xs:pack_row_spans(row,[z])
   outspans+=len(row);total+=sum(z['end']-z['start'] for z in row)
   f.write(json.dumps({'row':y,'spans':row},separators=(',',':'))+'\n')
 if total+pending_cells!=ncells:raise AssertionError(f'assigned {total} + pending {pending_cells}, expected {ncells}')
 if not args.partial and pending_cells:raise AssertionError('final layer may not leave pending closed-water components')
 layer_manifest={'schema':'worldatlas-full-water-assignment-tiles-v1',
  'status':'partial' if args.partial else 'completed_candidate_not_published',
  'grid':{'width':W,'height':H,'angular_step_deg':STEP,'row_convention':'north-to-south; cell centers; half-open [start,end) x spans'},
  'coverage':{'complete':not args.partial,'meaning':'provisional closed-water component assignments; partial mode omits components adjacent to unknown code-0 water' if args.partial else 'all zero-source-cut closed-water components assigned to codes 1–6'},
  'precedence':{'after':'approved named-basin and coastal-band continental assignments; only components with zero artificial source-cut contact are eligible'},
  'source_assignment_rules':{'single_participant':'direct to the sole boundary continent from final assigned water classes and/or actual land classes 17–22','shared_participant':'cellwise nearest final assigned-land shore among boundary participant categories, certified midpoint bounds plus exact spherical segment fallback','nearest_tie':'uses the named-basin shared spherical kernel stable lower category-code tie'},
  'provenance':{'audit':'closed-water-assignment-audit.json','legacy_ocean_labels_read':False,'mask_only_placeholder_code_1_used':False,'partial_input_mode':args.partial},
  'tiles':[{'core_rows':[0,H],'core_cols':[0,W],'span_file':{'path':out_file.name,'sha256':sha(out_file)}}]}
 layer_path=out/'layer-manifest.json';write_json_exclusive(layer_path,layer_manifest,indent=2)
 report={'schema':'closed-water-pocket-continent-assignments-v1','status':'partial-candidate-not-published' if args.partial else 'staged-candidate-not-published','grid':{'width':W,'height':H,'step_degrees':STEP},
  'inputs':{'classifier_script_path':str(Path(__file__).resolve()),'classifier_script_sha256':sha(__file__),'ocean_run_manifest_sha256':sha(run/'manifest.json'),'component_spans_sha256':sha(run/'unseeded_component_spans.u32le'),
   'prefill_audit_sha256':sha(args.prefill_audit),'prefill_plan_sha256':prefill_plan_sha,'prefill_rows_sha256':sha(args.prefill_rows),'prefill_runs_sha256':sha(args.prefill_runs),
   'physical_rows_sha256':sha(args.physical_rows),'physical_runs_sha256':sha(args.physical_runs),'final_land_rows_sha256':sha(args.land_rows),'final_land_runs_sha256':sha(args.land_runs),
   'legacy_ocean_label_inheritance':False,'mask_only_placeholder_interpretation':False,'partial_input_mode':args.partial,
   'provisional_ocean_eligible_cells_retained_zero':n_eligible,'additional_unknown_code0_cells':extra_zero},
  'policy':'Only components with zero source-cut contact and a boundary touching final 1–6 water and/or actual 17–22 land were assigned. One distinct boundary continent maps the whole component directly; multiple participant continents are assigned cellwise by certified nearest final assigned-land shoreline using the shared spherical kernel. Exact ties follow the kernel lower-stable-code rule.',
  'component_count':len(per_component),'component_span_count':nspans,'assigned_cells':total,'pending_cells':pending_cells,'assigned_spans':outspans,'assigned_cells_by_code':{str(k):code_counts[k] for k in range(1,7)},
  'component_method_counts':dict(Counter(v['method'] for v in component_methods.values())),'component_methods':component_methods,'nearest_shore_qa':nearest_qas,
  'output':{'path':str(out_file),'sha256':sha(out_file),'format':'one JSONL row per y, spans start/end/code/rule_id/member_id, end-exclusive',
    'layer_manifest':str(layer_path),'layer_manifest_sha256':sha(layer_path)},
  'component_adjacency':{str(root):{'participant_codes':participants[root],
    'boundary_edge_counts_by_code':{str(k):v for k,v in adjacency[root]['codes'].items()},
    'unknown_code0_boundary_edges':adjacency[root]['unknown_zero_edges']} for root in per_component}}
 write_json_exclusive(out/'closed-water-assignment-audit.json',report,indent=2)
 print(json.dumps({'status':'staged-candidate-not-published','components':len(per_component),'cells':total,'spans':outspans,'methods':report['component_method_counts'],'code_counts':report['assigned_cells_by_code'],'output_sha256':report['output']['sha256']},indent=2))

if __name__=='__main__':main()
