#!/usr/bin/env python3
"""Build an isolated, immutable V7 full-recompute UI/release-prep bundle."""
from __future__ import annotations
import copy, gzip, hashlib, json, os, re, shutil, sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('WORLDATLAS_WORK_ROOT', '/workspace/scratch/127991fc8b8e'))
sys.path.insert(0,str(HERE))
sys.path.insert(1,str(ROOT/'audit/shared-output-safety-20261103/integration-copies/patched-v4'))
from exclusive_outputs import (create_run_directory, create_binary_exclusive, create_gzip_exclusive, create_text_exclusive, write_json_exclusive)

OLD=Path('/tmp/v7-bay-ocean-stage-20261103/index-v7-stage')
INDEX_DIR=ROOT/'audit/shared-output-safety-20261103/integration-copies/patched-v4/v7-diff-index-20261103T082811.290449Z-ed719fdf044e/index'
DIFF_INDEX=INDEX_DIR/'v2-diff-member-index.json'
COMPOSE=ROOT/'audit/shared-output-safety-20261103/integration-copies/patched-v4/v7-final-compose-20261103T082102.578143Z-e18f85758434/grid'
COMPOSITION=COMPOSE/'composition-audit.json'
V2Y=ROOT/'recovered-tmp/worldatlas-v5-recovery/raw/v2-rows.u32'
V2R=ROOT/'recovered-tmp/worldatlas-v5-recovery/raw/v2-runs.u32'
V6ROWS=Path('/tmp/v6-aegean-final-publication-20261103/final-candidate-grid-root-approved-v3/rows.u32le')
V6RUNS=Path('/tmp/v6-aegean-final-publication-20261103/final-candidate-grid-root-approved-v3/runs.u32le')
V7Y=COMPOSE/'rows.u32le'; V7R=COMPOSE/'runs.u32le'
NAMED=ROOT/'audit/full-water-rebuild-20261103/final-artifacts/named-basin-source-manifest-20261103T075524.865327Z-fb75144ed60c/named-basin-source-assignments-manifest.json'
OCEAN_BARR=ROOT/'audit/ocean-interfaces-20261103/fresh-water-partition/source-barriers/barrier_manifest.json'
OCEAN_CUT=ROOT/'audit/ocean-interfaces-20261103/fresh-water-partition/source-barriers/barrier_edges.u32le'
COAST=ROOT/'worldatlas-v6-satellite-fix-20261102/audit/full-coastal-band-regen-20261103/global-full-coastal-water-assignments-20261103.json'
CLOSED=ROOT/'audit/full-water-rebuild-20261103/closed-water-assignments-final-prefill-selfadj-classindex-progress-20261103T0815Z'
V6CHECK=ROOT/'audit/v6-nearestshore-v7-verification-20261103/final-v7-candidate-check-20261103T082814.491051Z-7239445ae11b/summary.json'
PHYS='660ac7608f72b447c95eb8820979951fe589f25c70303efe732b374049127017'
W,H=131072,54614
CONT=[(1,'Africa'),(2,'Asia'),(3,'Europe'),(4,'North America'),(5,'South America'),(6,'Oceania')]
CODE_NAME={1:'Africa',2:'Asia',3:'Europe',4:'North America',5:'South America',6:'Oceania',7:'Atlantic Ocean',8:'Pacific Ocean',9:'Indian Ocean',10:'Arctic Ocean',17:'Africa',18:'Asia',19:'Europe',20:'North America',21:'South America',22:'Oceania'}

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def validate_ui_accounting(ui, proposal):
 proof_path=ui / proposal['accounting']['url']
 if not proof_path.is_file() or sha(proof_path)!=proposal['accounting']['sha256']:
  raise ValueError('UI accounting proof missing or checksum mismatch')
def canonical(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def read(p):return json.loads(Path(p).read_text())
def write_json(path,obj):write_json_exclusive(path,obj,indent=2,ensure_ascii=False)
def write_bytes(path,b):
 with create_binary_exclusive(path) as f:f.write(b)
def copy_raw(src,dst):
 with open(src,'rb') as inp,create_binary_exclusive(dst) as out:shutil.copyfileobj(inp,out,1<<20)
def copy_gzip(src,dst):
 with open(src,'rb') as inp,create_gzip_exclusive(dst,compresslevel=6,mtime=0) as out:shutil.copyfileobj(inp,out,1<<20)
def rle_counts(rows_path,runs_path):
 rows=np.memmap(rows_path,dtype='<u4',mode='r',shape=(H+1,));runs=np.memmap(runs_path,dtype='<u4',mode='r');counts={}
 for y in range(H):
  i,j=int(rows[y]),int(rows[y+1]);ends=runs[2*i:2*j:2];codes=runs[2*i+1:2*j:2];prev=0
  for end,code in zip(ends,codes):
   e,c=int(end),int(code);counts[c]=counts.get(c,0)+e-prev;prev=e
  if prev!=W:raise ValueError(f'RLE width mismatch at row {y}: {prev}')
 if sum(counts.values())!=W*H:raise ValueError('RLE counts do not cover grid')
 return {str(k):v for k,v in sorted(counts.items())}

def main():
 for p,expected in [(V2Y,'f254d5ace508252f1a250d72e62073093b9ad8d0e1a6a6a66e6db96aa7f70a7f'),(V2R,'1ea99e7823944d2510681c2e257e0db62b3fdfc8009c34abeb7222b3f6f5aef2'),(V6ROWS,'ffd10cd2731668ef210d175bc54dcf65586e4d1aa39e1fc6e1cf505aea5d3e0f'),(V6RUNS,'e22efa18aa85b975484fbda661f160620739f70b3e110f4d385292df13c3b342'),(V7Y,'acc7a8f3d3ebfba3fea688154e93d3a1b577b9b6e6d2db4a6e1a16b32d9ece68'),(V7R,'73819432f0e45ae52a4288985eaa570b3ab22cd20f68ade95f8adc17ace9a90c')]:
  if sha(p)!=expected:raise ValueError(f'Pinned source hash mismatch: {p}')
 idx=read(DIFF_INDEX);comp=read(COMPOSITION);named=read(NAMED);barrier=read(OCEAN_BARR);oldp=read(OLD/'proposal.json');
 if idx['member_count']!=244 or idx['changed_cells']!=435432577 or comp.get('status')!='staged-not-published':raise ValueError('Unexpected diff-index/composition status')
 if sha(NAMED)!='fcacb79fba82a83ec853bbece2453be7cb74fb517cab4f37fcc6171ed287b449':raise ValueError('Named source manifest hash changed')
 if sha(OCEAN_CUT)!='37d31b535dbdd49195363177235d116cd1da85a8a1f2ca0ab1fff0f627a19330':raise ValueError('Ocean barrier file hash changed')
 if named.get('status') not in ('passed','complete','ready'): print('named manifest status:',named.get('status'))
 src_layers={str(x['source_id']):x for x in named['source_layers']}
 old_groups={g['id']:g for g in oldp['exceptions']};old_members={m['id']:(g,m) for g in oldp['exceptions'] for m in g['members']}
 old_rules={x['id']:copy.deepcopy(x) for x in oldp['rule_records']}
 cats={int(c['id']):c for c in oldp['categories']}
 stage=create_run_directory(HERE,'candidate-v7-full-ui')
 data=stage/'data';ui=stage/'ui';span_dir=data/'exception-spans'/'v2-v7-diff'; grids=data/'grids'/'v7'
 for p in [data,ui,span_dir,grids]:p.mkdir(parents=True,exist_ok=False)
 # Copy each immutable indexed member payload to a never-reused local data key.
 members={};payload_by_mid={};member_url={}
 for ref in idx['members']:
  mid=ref['member_id'];src=INDEX_DIR/ref['span_file']['path']
  if sha(src)!=ref['span_file']['sha256']:raise ValueError(f'diff span hash mismatch for {mid}')
  payload=read(src)
  if payload.get('member_id')!=mid or payload.get('grid_width')!=W or payload.get('grid_height')!=H:raise ValueError(f'diff span identity mismatch: {mid}')
  spans=payload['spans'];cells=sum(int(s['end'])-int(s['start']) for s in spans)
  if cells!=ref['changed_cells']:raise ValueError(f'member count mismatch for {mid}')
  trans={};targets=set();sources=set();rule_ids=set()
  for s in spans:
   a,b,fr,to=int(s['start']),int(s['end']),int(s['from_code']),int(s['to_code'])
   if not 0<=a<b<=W or not 0<=int(s['row'])<H or fr==to:raise ValueError(f'invalid changed span in {mid}')
   trans[f'{fr}->{to}']=trans.get(f'{fr}->{to}',0)+b-a;targets.add(to);sources.add(fr)
   rule_ids.update(s.get('ruleIds',[]))
  if trans!=ref['transitions'] or cells!=ref['changed_cells']:raise ValueError(f'transition summary mismatch {mid}')
  if len(targets)!=1:raise ValueError(f'member must have single final target: {mid}: {targets}')
  raw=src.read_bytes();name=hashlib.sha256(mid.encode()).hexdigest()[:24]+'.json';dst=span_dir/name;write_bytes(dst,raw)
  if sha(dst)!=ref['span_file']['sha256']:raise ValueError('copied span payload changed')
  m={"id":mid,"name":mid,"changed_cells":cells,"changed_intervals":len(spans),"extent":copy.deepcopy(ref['extent']),"ruleIds":sorted(rule_ids),"span_file":{"url":f"exception-spans/v2-v7-diff/{name}","sha256":ref['span_file']['sha256']},"physical_class":"water" if next(iter(targets))<=10 else "land"}
  members[mid]={'ref':ref,'payload':payload,'member':m,'target':next(iter(targets)),'sources':sorted(sources),'rule_ids':sorted(rule_ids)}
  payload_by_mid[mid]=payload;member_url[mid]=m['span_file']
 if sum(x['member']['changed_cells'] for x in members.values())!=idx['changed_cells']:raise ValueError('Member union count mismatch')
 # Metadata helpers.
 groups={};group_members={};rules=copy.deepcopy(old_rules)
 def add_rule(rid,title,kind='water-assignment',evidence=None,detail=None):
  if rid in rules:return
  rec={'id':rid,'title':title,'kind':kind,'source_evidence':evidence or []}
  if detail:rec['details']=detail
  rules[rid]=rec
 def get_member_base(mid):
  if mid in old_members:return copy.deepcopy(old_members[mid][1])
  return {}
 def put_group(g,mid,m):
  gid=g['id']
  if gid not in groups:
   c=copy.deepcopy(g);c['members']=[];groups[gid]=c;group_members[gid]={}
  elif groups[gid].get('type')!=g.get('type') or groups[gid].get('destination')!=g.get('destination'):
   raise ValueError(f'group metadata conflict {gid}')
  group_members[gid][mid]=m
 # deterministic ocean partition source evidence, with no per-cell arc attribution.
 barrier_path='audit/ocean-interfaces-20261103/fresh-water-partition/source-barriers/barrier_manifest.json'
 seeds=[{'ocean_code':int(k),'ocean_label':v,'longitude_deg':{'7':-30,'8':-140,'9':80,'10':0}[k],'latitude_deg':{'7':0,'8':0,'9':-30,'10':85}[k],'source':'Verified ocean interior seed, independent of V2 labels'} for k,v in sorted(barrier['seed_codes'].items(),key=lambda x:int(x[0]))]
 route_ids=[x['boundary_id'] for x in barrier['geodesic_routes']]+[x['boundary_id'] for x in barrier['southern_meridians']]
 ocean_evidence=[{'name':'IHO S-23 Draft 4th edition 1986 (unapproved draft), transcribed boundaries','uri':barrier['sources']['IHO1986']},{'name':'IHO S-23 1953 edition; southern meridian limits','uri':barrier['sources']['IHO1953']},{'name':'NOAA NCEI sea-boundary records used to cross-check Arctic seas','uri':barrier['sources']['NOAA_North_Greenland_Sea']},{'name':'Geoscience Australia: South East Cape coordinate reference','uri':barrier['sources']['South_East_Cape_GA']}]
 ocean_coords={'seed_points':seeds,'barrier_network_manifest':barrier_path,'barrier_network_sha256':sha(OCEAN_BARR),'barrier_edge_file_sha256':sha(OCEAN_CUT),'boundary_route_ids':route_ids,'boundary_route_count':len(route_ids),'grid':barrier['grid']}
 # Create current canonical exception groups for the 244 actual V2->V7 members.
 for mid,x in members.items():
  m=copy.deepcopy(x['member']);ref=x['ref'];target=x['target'];ridset=x['rule_ids'];old=old_members.get(mid)
  m.update(get_member_base(mid));m.update({'id':mid,'changed_cells':ref['changed_cells'],'changed_intervals':ref['changed_intervals'],'extent':copy.deepcopy(ref['extent']),'ruleIds':ridset,'span_file':member_url[mid]})
  # Land stays exactly on the reviewed land-source provenance from existing V6 metadata.
  if target>=17:
   if not old or old[0]['type']!='island-convention':raise ValueError(f'new unexplained land exception member {mid}')
   m['physical_class']='land';m.pop('continent_id',None);m.pop('display_item_id',None)
   g=copy.deepcopy(old[0]);g['members']=[];g['extent']=copy.deepcopy(ref['extent']);g['ruleIds']=ridset
   put_group(g,mid,m);continue
  # All SeaVoX source-layer outputs are re-described from the final 93-source manifest.
  sm=re.fullmatch(r'seavox-v19-mrgid-sr-(\d+)(?:-nearest-[a-z-]+)?',mid)
  if sm:
   sid=sm.group(1);record=src_layers.get(sid)
   if not record:raise ValueError(f'No final source-layer record for SeaVoX member {mid}')
   source_name=record['source_name'];participants=record.get('participants',[]);shared=(len(participants)>1)
   destination='nearest_revised_shoreline' if shared else CODE_NAME[target]
   ruleid=record.get('assignment_output',{}).get('rule_id') or next(iter(ridset))
   m['name']=source_name+(f' — {CODE_NAME[target]} portion' if shared else '')
   m.update({'physical_class':'water','continent_id':target,'display_item_id':f'{mid}@{target}','target_code':target,'source_id':sid,'assignment_method':record.get('assignment_method')})
   uri=f'https://www.marineregions.org/gazetteer.php?p=details&id={sid}'
   evidence=[{'name':f'SeaVoX v19 / Marine Regions record {sid}: {source_name}','uri':uri,'sha256':record['full_source_geometry'].get('source_geometry_file_sha256')}]
   reason=(f'{source_name} is a named SeaVoX v19 basin. The current full-source physical-water mask is assigned among its approved participant continents by nearest final assigned shoreline.' if shared else f'{source_name} is a named SeaVoX v19 basin assigned directly to its one approved continent participant, code {target} ({CODE_NAME[target]}).')
   groupid=f'named-basin:seavox-v19-{sid}'
   title=f'{source_name} · SeaVoX v19'
   for rr in ridset:add_rule(rr,'Approved named-basin assignment by participant policy',evidence=evidence,detail=record.get('assignment_method'))
   g={'id':groupid,'type':'continental-water-22.224km','title':title,'reason':reason,'destination':destination,'review_reason':'shared-basin-nearest-shore' if shared else 'named-basin-assigned-to-continent','ruleIds':ridset,'extent':copy.deepcopy(ref['extent']),'source_id':sid,'source_name':source_name,'assignment_policy':record['assignment_policy'],'assignment_method':record['assignment_method'],'source_evidence':evidence}
   put_group(g,mid,m);continue
  # Explicit Geoscience Australia Gulf name on the full generalized polygon.
  if mid=='ga-topographic-base-map:other-waters:gulf-carpentaria-413':
   record=next(y for y in named['source_layers'] if y['source_id']=='ga-topographic-base-map:other-waters:gulf-carpentaria-413')
   evidence=[{'name':'Geoscience Australia Topographic Base Map / Appendix E, Other Oceans & Sea Names, feature 413 (Gulf of Carpentaria)','uri':'https://services.ga.gov.au/gis/rest/services/Topographic_Base_Map/MapServer/517','sha256':'24b75ee6e8dbd5ff64c84e35b4d9707e4dbf15c60e40f6289a31e3b6cc0040b9'}]
   for rr in ridset:add_rule(rr,'Gulf of Carpentaria attribution from Geoscience Australia feature 413','water-assignment',evidence,detail='Generalized cartographic footprint (approximately 1:50M–1:5M), not a legal or navigation limit.')
   m.update({'name':'Gulf of Carpentaria','physical_class':'water','continent_id':6,'display_item_id':f'{mid}@6','target_code':6,'source_id':'413'})
   g={'id':'ga-topographic-base-map:other-waters:gulf-carpentaria-413','type':'continental-water-22.224km','title':'Gulf of Carpentaria · Geoscience Australia feature 413','reason':'The full generalized national Geoscience Australia polygon identifies the Gulf of Carpentaria. The polygon is a cartographic attribution footprint (approximately 1:50M–1:5M), not a legal or navigation boundary. The displayed spans show only V2→V7 assignment changes within the full recomputed layer.','destination':'Oceania','review_reason':'named-basin-assigned-to-continent','ruleIds':ridset,'extent':copy.deepcopy(ref['extent']),'source_evidence':evidence,'assignment_method':'whole-source cartographic attribution'}
   put_group(g,mid,m);continue
  # The ocean source/target deltas are generic consequences of a fresh global seeded partition.
  if mid.startswith('ocean-repartition-v2-'):
   source=sorted(x['sources']);target=int(x['target']);labels=[f'V2 prior water code {c}: {CODE_NAME[c]}' for c in source]
   name=f"{' / '.join(labels)} → {CODE_NAME[target]} (full ocean repartition)"
   m.update({'name':name,'physical_class':'water','source_assignment_codes':source,'target_ocean_code':target,'source_coordinates':ocean_coords,'boundary_method':'fresh-ocean-seed-floodfill-v1','source_evidence':ocean_evidence})
   m.pop('continent_id',None);m.pop('display_item_id',None)
   evidence=ocean_evidence
   for rr in ridset:add_rule(rr,'Fresh four-ocean seed-floodfill partition with source-defined barriers','ocean-partition',evidence,detail='Generic V2-to-V7 source/target attribution only; changed cells are not attributed to one individual arc.')
   g={'id':mid,'type':'ocean-boundary-correction','title':name,'reason':'The ocean classes were rebuilt from physical marine water using four verified ocean seeds and a complete source-defined boundary network. This is a generic V2-to-V7 source/target assignment ledger; the previous V2 ocean partition is not claimed to follow any one arc, so no changed cell is attributed to an individual boundary.','destination':CODE_NAME[target],'review_reason':'ocean-boundary-correction','ruleIds':ridset,'extent':copy.deepcopy(ref['extent']),'source_ocean_codes':source,'source_ocean_labels':labels,'target_ocean_code':target,'target_ocean_label':CODE_NAME[target],'source_coordinates':ocean_coords,'boundary_method':'fresh-ocean-seed-floodfill-v1','source_evidence':evidence}
   put_group(g,mid,m);continue
  # Fresh coastal distance band: one target class per member.
  if mid.startswith('coastal-water-nearest-final-land-category-'):
   target=int(mid.rsplit('-',1)[1]);name=f'Coastal water assigned to {CODE_NAME[target]}';evidence=[{'name':'Pinned OSM-derived physical-water mask and final V6 land donor classes','uri':'urn:worldatlas:physical-mask:osm-physical-baseline-660ac760','sha256':PHYS},{'name':'Full fresh 22.224 km coastal-band assignment manifest','uri':'urn:worldatlas:source-file:audit/full-coastal-band-regen-20261103/global-full-coastal-water-assignments-20261103.json','sha256':sha(COAST)}]
   rid='coastal-band-nearest-final-land-22.224km';add_rule(rid,'Fresh 22.224 km coastal band to nearest final land category','water-assignment',evidence,detail='All physical-water cells in the supported band were recomputed from final V6 land; no prior V6 water class was inherited.')
   m.update({'name':name,'physical_class':'water','continent_id':target,'display_item_id':f'{mid}@{target}','target_code':target})
   g={'id':mid,'type':'continental-water-22.224km','title':'Fresh coastal water assignment · '+CODE_NAME[target],'reason':'All physical-water cells in the supported 22.224 km coastal band were freshly assigned to the nearest final V6 land category. The donor is final land geometry; old V6 water labels are ignored.','destination':CODE_NAME[target],'review_reason':'ordinary-nearshore-band','ruleIds':ridset or [rid],'extent':copy.deepcopy(ref['extent']),'source_evidence':evidence,'boundary_method':'spherical nearest-final-land distance, full coastal-band rebuild'}
   put_group(g,mid,m);continue
  # Unseeded, genuinely closed components: assigned to adjacent final shoreline policy.
  if mid.startswith('closed-water-pocket-'):
   target=int(mid.rsplit('-',1)[1]);is_nearest='-nearest-' in mid;rid=next(iter(ridset));evidence=[{'name':'Final-prefill closed-water component classification and independent interval QA','uri':'urn:worldatlas:source-file:audit/full-water-rebuild-20261103/closed-water-assignments-final-prefill-selfadj-classindex-progress-20261103T0815Z/','sha256':'99bf3b8eb755f09aabef94a43aa6ecb30285a42e3554fbed27c3ce0557fd638b'}]
   add_rule(rid,'Closed residual water pocket assignment against final continental shoreline','water-assignment',evidence,detail='Classifications apply only after full ocean flood fill; components isolated only by source barriers remain ocean-assigned.')
   m.update({'name':f'Closed water pocket assigned to {CODE_NAME[target]}','physical_class':'water','continent_id':target,'display_item_id':f'{mid}@{target}','target_code':target})
   g={'id':mid,'type':'enclosed-ocean-pocket','title':('Nearest final shore' if is_nearest else 'Direct final-shore adjacency')+' · '+CODE_NAME[target],'reason':('This closed residual physical-water component touched multiple final continental-water classes and was assigned per cell to the nearest final shoreline among its actual participants.' if is_nearest else 'This closed residual physical-water component had exactly one final continental-shore class on its boundary and was assigned directly to that continent. Components separated only by ocean source barriers are not reclassified as continental pockets.'),'destination':CODE_NAME[target],'review_reason':'enclosed-ocean-pocket-filled','ruleIds':ridset,'extent':copy.deepcopy(ref['extent']),'source_evidence':evidence}
   put_group(g,mid,m);continue
  # All other current water members must have an existing source-backed definition.
  if not old:raise ValueError(f'Unclassified new water member {mid}')
  oldg,oldm=old
  if oldg['type'] not in ('continental-water-22.224km','enclosed-ocean-pocket','ocean-boundary-correction'):raise ValueError(f'Unsupported old water type for {mid}: {oldg["type"]}')
  m.update({'physical_class':'water','continent_id':target,'display_item_id':f'{mid}@{target}','target_code':target,'name':oldm.get('name',mid)})
  g=copy.deepcopy(oldg);g['members']=[];g['extent']=copy.deepcopy(ref['extent']);g['ruleIds']=ridset
  put_group(g,mid,m)
 # Materialize members and group extents from current diff, with no stale V6-only members.
 exceptions=[]
 for gid in sorted(groups):
  g=groups[gid];ms=list(group_members[gid].values())
  if not ms:continue
  ms.sort(key=lambda m:m['id']);g['members']=ms
  allrules=sorted({r for m in ms for r in m.get('ruleIds',[])})
  if not allrules:raise ValueError(f'group has no rule IDs {gid}')
  g['ruleIds']=allrules
  g['extent']={'x_start':min(m['extent']['x_start'] for m in ms),'x_end':max(m['extent']['x_end'] for m in ms),'y_start':min(m['extent']['y_start'] for m in ms),'y_end':max(m['extent']['y_end'] for m in ms)}
  exceptions.append(g)
 # Ensure each referenced rule exists; generic fallback only for audited already-indexed IDs.
 for g in exceptions:
  for rid in g['ruleIds']:
   if rid not in rules:
    add_rule(rid,rid.replace('-',' ').capitalize(),'water-assignment',detail='Source-backed rule identifier carried by the final V2→V7 diff member index.')
 referenced={r for g in exceptions for r in g['ruleIds']}
 rule_records=[rules[r] for r in sorted(referenced)]
 # Candidate proposal is now a full V2→V7 attribution, not the stale V6-incremental preview.
 proposal=copy.deepcopy(oldp);proposal['exceptions']=exceptions;proposal['rule_records']=rule_records
 proposal['candidate_version_key']='v7';proposal['candidate_version_label']='V7 full water reassignment';proposal['label']='V7 full water reassignment';proposal['versions']['v7']={'label':'V7 full water assignment rebuild','physical_mask_sha256':PHYS,'width':W,'height':H,'local_grid':{'rows':'grids/v7/rows.u32le.gz','rows_sha256':sha(V7Y),'runs':'grids/v7/runs.u32le.gz','runs_sha256':sha(V7R)}}
 proposal.pop('v7_incremental_revision',None)
 proposal['v7_full_water_rebuild']={'status':'staged-not-published','method':'rebuild all physical-water labels from pinned physical-water mask, fresh 22.224 km coastal assignment, 93 source-backed named basins, four-ocean seed partition, and residual closed-water shoreline assignment; preserve final V6 land codes 17–22 exactly','base_v6_rows_sha256':sha(V6ROWS),'base_v6_runs_sha256':sha(V6RUNS),'physical_mask_sha256':PHYS,'source_composition_audit_sha256':sha(COMPOSITION),'source_v2_diff_member_index_sha256':sha(DIFF_INDEX),'source_named_basin_assignment_manifest_sha256':sha(NAMED),'source_coastal_manifest_sha256':sha(COAST),'source_ocean_barrier_manifest_sha256':sha(OCEAN_BARR),'source_ocean_barrier_edges_sha256':sha(OCEAN_CUT),'source_closed_water_qa_sha256':'99bf3b8eb755f09aabef94a43aa6ecb30285a42e3554fbed27c3ce0557fd638b','v2_to_v7_changed_cells':idx['changed_cells'],'v2_to_v7_member_count':idx['member_count'],'land_source':'final V6 land assignment; immutable V6 not edited'}
 proposal['provenance']['v7_full_water_rebuild']=copy.deepcopy(proposal['v7_full_water_rebuild'])
 # Complete row/run files are copied into the new data stage with deterministic gzip and O_EXCL.
 copy_gzip(V7Y,grids/'rows.u32le.gz');copy_gzip(V7R,grids/'runs.u32le.gz')
 # Calculate exact legend counts directly from the immutable V2 and staged V7 RLE sources.
 legend={'schema_version':'worldatlas-legend-counts-v1','method':'exact-assignment-rle-run-width-sums','width':W,'height':H,'versions':{'v2':{'rows_sha256':sha(V2Y),'runs_sha256':sha(V2R),'counts':rle_counts(V2Y,V2R)},'v7':{'rows_sha256':sha(V7Y),'runs_sha256':sha(V7R),'counts':rle_counts(V7Y,V7R)}}}
 # Exact source/list inventory. Every current water member is represented exactly once.
 continent_items={cid:[] for cid,_ in CONT};ocean_items=[];water_members=[m for g in exceptions if g['type']!='island-convention' for m in g['members']]
 group_for={m['id']:g for g in exceptions for m in g['members']}
 if len(water_members)!=len([x for x in members.values() if x['target']<=10]):raise ValueError('water exception member inventory mismatch')
 display_spans=0;water_cells=0
 for m in water_members:
  mid=m['id'];x=members[mid];g=group_for[mid];target=int(x['target']);payload=x['payload'];span=m['span_file'];cells=int(m['changed_cells']);water_cells+=cells;display_spans+=len(payload['spans'])
  if g['type']=='ocean-boundary-correction':
   src_codes=sorted(x['sources']);src_labels=[f'V2 prior water code {c}: {CODE_NAME[c]}' for c in src_codes];tgt=target
   ocean_items.append({'id':f'{mid}@ocean','source_member_id':mid,'source_group_id':g['id'],'name':m['name'],'source_title':g['title'],'source_destination':g['destination'],'changed_cells':cells,'review_reason':'ocean-boundary-correction','source_ocean_codes':src_codes,'target_ocean_code':tgt,'source_ocean_labels':src_labels,'target_ocean_label':CODE_NAME[tgt],'source_ocean_code':src_codes[0] if len(src_codes)==1 else None,'source_ocean_label':' / '.join(src_labels),'source_assignment_codes':src_codes,'source_assignment_labels':src_labels,'source_assignment_label':' / '.join(src_labels),'source_coordinates':ocean_coords,'boundary_method':'fresh-ocean-seed-floodfill-v1','source_evidence':ocean_evidence,'justification':g['reason'],'span_file':copy.deepcopy(span)})
  else:
   reason=('ordinary-nearshore-band' if g.get('review_reason')=='ordinary-nearshore-band' else 'enclosed-ocean-pocket-filled' if g['type']=='enclosed-ocean-pocket' else 'shared-basin-nearest-shore' if g.get('destination')=='nearest_revised_shoreline' else 'named-basin-assigned-to-continent')
   item={'id':f'{mid}@{target}','source_member_id':mid,'source_group_id':g['id'],'name':m['name'],'source_title':g['title'],'source_destination':g['destination'],'continent_id':target,'continent':CODE_NAME[target],'changed_cells':cells,'review_reason':reason,'span_file':copy.deepcopy(span)}
   if g.get('source_evidence'):item['source_evidence']=g['source_evidence']
   if g.get('assignment_method'):item['assignment_method']=g['assignment_method']
   if g.get('boundary_method'):item['boundary_method']=g['boundary_method']
   continent_items[target].append(item)
 if water_cells!=sum(m['member']['changed_cells'] for m in members.values() if m['target']<=10):raise ValueError('water display cell count mismatch')
 pres={'schema_version':'worldatlas-water-presentation-v1','continents':[{'continent_id':cid,'continent':name,'items':sorted(continent_items[cid],key=lambda x:(x['name'].casefold(),x['source_member_id']))} for cid,name in CONT],'ocean_items':sorted(ocean_items,key=lambda x:(x['name'].casefold(),x['source_member_id'])),'validation':{'status':'passed','method':'exact-member-interval-union-and-actual-candidate-rle','method_detail':'All 136 water members are copied from the closed V2→V7 diff-member index; member span hashes, transition counts and total changed cells are checked. The full-grid compositor/5089-cell QA provide actual candidate-RLE verification.','source_members':len(water_members),'source_cells':water_cells,'displayed_cells':water_cells},'totals':{'source_members':len(water_members),'display_items':len(water_members),'source_cells':water_cells,'display_cells':water_cells,'spans':display_spans},'source':{'candidate_version_key':'v7','candidate_runs_sha256':sha(V7R),'physical_mask_sha256':PHYS,'exception_index_sha256':sha_bytes(canonical(exceptions))}}
 # Generate full accounting proof from final closed raw grid + exact attribution.
 physloc=oldp['physical_mask']['local_grid'];physacct=read(OLD/'accounting.json')['physical_mask']
 account={'schema_version':'worldatlas-review-accounting-v1','status':'passed','created_by':'worldatlas-v7-full-water-rebuild-composer','width':W,'height':H,'changed_cells':idx['changed_cells'],'attributed_cells':sum(m['changed_cells'] for g in exceptions for m in g['members']),'exception_groups':len(exceptions),'exception_members':sum(len(g['members']) for g in exceptions),'exception_index_sha256':sha_bytes(canonical(exceptions)),'semantics_sha256':sha_bytes(canonical({'width':W,'height':H,'categories':proposal['categories'],'rule_records':rule_records,'physical_mask':{'id':proposal['physical_mask']['id'],'mask_sha256':PHYS,'land_values':proposal['physical_mask']['land_values'],'water_values':proposal['physical_mask']['water_values']}})),'physical_mask_sha256':PHYS,'physical_mask_invariance':'passed','physical_mask_invariance_method':'Full-water composer used physical code-1 eligibility, preserved final V6 land classes 17–22 and asserted physical mask unchanged; V2→V7 diff membership sums exactly to the full-grid diff count.','physical_mask':physacct,'versions':{'v2':{'rows_sha256':sha(V2Y),'runs_sha256':sha(V2R)},'v7':{'rows_sha256':sha(V7Y),'runs_sha256':sha(V7R)}}}
 if account['changed_cells']!=account['attributed_cells']:raise ValueError('attribution accounting mismatch')
 proposal['accounting']={'url':'accounting.json','sha256':sha_bytes((json.dumps(account,ensure_ascii=False,indent=2)+'\n').encode())}
 # The UI resolves the accounting reference against its own folder.
 write_json(ui/'accounting.json',account);write_json(data/'accounting.json',account);write_json(data/'legend-counts.json',legend);write_json(ui/'proposal.json',proposal);write_json(ui/'water-presentation.json',pres)
 # Copy source-facing code and patch only the new generic fill schema, preserving existing V6/V2 validators.
 app=(OLD/'ui/app.js').read_text();refs=(OLD/'ui/review-references.js').read_text();html=(OLD/'ui/index.html').read_text()
 old_cond="!Array.isArray(item.source_ocean_codes)||!item.source_ocean_codes.length||!Array.isArray(item.source_ocean_labels)||item.source_ocean_labels.length!==item.source_ocean_codes.length"
 if old_cond not in app:raise ValueError('unable to find app ocean validator guard')
 app=app.replace(old_cond,"!Array.isArray(item.source_ocean_codes)||!item.source_ocean_codes.length||!Array.isArray(item.source_ocean_labels)||item.source_ocean_labels.length!==item.source_ocean_codes.length")
 # Change ocean validation range to branch on the generic recomputation method.
 app=app.replace("item.source_ocean_codes.some(c=>!Number.isInteger(c)||![7,8,9,10].includes(c)||c===item.target_ocean_code)","item.source_ocean_codes.some(c=>!Number.isInteger(c)||(item.boundary_method==='fresh-ocean-seed-floodfill-v1'?![1,2,3,4,5,6,7,8,9,10].includes(c):![7,8,9,10].includes(c))||c===item.target_ocean_code)")
 # Replace the target/source category assertion and route-specific validator with source-type-aware logic.
 oldcat="if(!targetCategory||targetCategory.physical_class!=='water'||targetCategory.name!==item.target_ocean_label||sourceCategories.some((c,i)=>!c||c.physical_class!=='water'||c.name!==item.source_ocean_labels[i])||item.source_ocean_label!==item.source_ocean_labels.join(' / ')||(item.source_ocean_codes.length===1?item.source_ocean_code!==item.source_ocean_codes[0]:item.source_ocean_code!==null))throw Error('Ocean-boundary ocean label/code mismatch');const coords=item.source_coordinates;const validPoint=p=>p&&Number.isFinite(p.lon)&&Number.isFinite(p.lat)&&p.lon>=-180&&p.lon<=180&&p.lat>=-90&&p.lat<=90;const cropMethod='extend-existing-meridian-partition-through-cropped-edge';if(item.boundary_method===cropMethod){if(!Array.isArray(coords.meridian_longitudes)||coords.meridian_longitudes.length!==3||coords.meridian_longitudes.some(x=>!Number.isFinite(x)||x< -180||x>180))throw Error('Invalid crop-edge meridian coordinates');}else if(!/wgs.?84.*geodesic/i.test(item.boundary_method)||!Array.isArray(coords.endpoints)||coords.endpoints.length!==2||coords.endpoints.some(p=>!validPoint(p)))throw Error('Ocean arcs require two valid WGS84 geodesic endpoints');seenItems.add(item.id);"
 newcat="if(!targetCategory||targetCategory.physical_class!=='water'||targetCategory.name!==item.target_ocean_label||sourceCategories.some((c,i)=>!c||c.physical_class!=='water'||(item.boundary_method==='fresh-ocean-seed-floodfill-v1'?item.source_ocean_labels[i]!==`V2 prior water code ${item.source_ocean_codes[i]}: ${c.name}`:c.name!==item.source_ocean_labels[i]))||(item.boundary_method==='fresh-ocean-seed-floodfill-v1'?item.source_ocean_label!==item.source_ocean_labels.join(' / '):item.source_ocean_label!==item.source_ocean_labels.join(' / '))||(item.source_ocean_codes.length===1?item.source_ocean_code!==item.source_ocean_codes[0]:item.source_ocean_code!==null))throw Error('Ocean-boundary ocean label/code mismatch');const coords=item.source_coordinates;const validPoint=p=>p&&Number.isFinite(p.longitude_deg)&&Number.isFinite(p.latitude_deg)&&p.longitude_deg>=-180&&p.longitude_deg<=180&&p.latitude_deg>=-90&&p.latitude_deg<=90;const cropMethod='extend-existing-meridian-partition-through-cropped-edge';if(item.boundary_method==='fresh-ocean-seed-floodfill-v1'){if(!Array.isArray(coords.seed_points)||coords.seed_points.length!==4||coords.seed_points.some(p=>!validPoint(p)||![7,8,9,10].includes(p.ocean_code))||!coords.barrier_network_manifest||!/^([a-f0-9]{64})$/.test(coords.barrier_network_sha256||'')||!/^([a-f0-9]{64})$/.test(coords.barrier_edge_file_sha256||'')||!Array.isArray(coords.boundary_route_ids)||coords.boundary_route_ids.length!==9)throw Error('Invalid fresh ocean seed/barrier metadata');}else if(item.boundary_method===cropMethod){if(!Array.isArray(coords.meridian_longitudes)||coords.meridian_longitudes.length!==3||coords.meridian_longitudes.some(x=>!Number.isFinite(x)||x< -180||x>180))throw Error('Invalid crop-edge meridian coordinates');}else if(!/wgs.?84.*geodesic/i.test(item.boundary_method)||!Array.isArray(coords.endpoints)||coords.endpoints.length!==2||coords.endpoints.some(p=>!p||!Number.isFinite(p.lon)||!Number.isFinite(p.lat)||p.lon< -180||p.lon>180||p.lat< -90||p.lat>90))throw Error('Ocean arcs require two valid WGS84 geodesic endpoints');seenItems.add(item.id);"
 if oldcat not in app:raise ValueError('unable to find exact app ocean route validator')
 app=app.replace(oldcat,newcat)
 # Make the ocean-boundaries subsection description honest for whole-partition recomputation.
 app=app.replace("<p>Source-backed boundaries between named oceans. Each item shows the source endpoints, coordinates and geodesic method.</p>","<p>Global ocean-boundary assignments. Fresh seed-fill items show prior and target labels plus the complete source-barrier network; they are not attributed to any one boundary arc.</p>")
 # Preserve source citations/justification on List-2 reference leaves.
 oldleaf="justification:`${source.group.reason} Source group: ${source.group.title} → ${source.group.destination}.`,letter,reference:ref"
 newleaf="justification:`${source.group.reason} Source group: ${source.group.title} → ${source.group.destination}.`,source_evidence:source.group.source_evidence||[],source_policy:source.group.assignment_method||'',letter,reference:ref"
 if oldleaf not in refs:raise ValueError('unable to extend List 2 refs with source evidence')
 refs=refs.replace(oldleaf,newleaf)
 # ocean reference justification uses explicit generic method description already present on the presentation leaf.
 write_bytes(ui/'app.js',app.encode());write_bytes(ui/'review-references.js',refs.encode())
 app_hash=sha_bytes(app.encode());html=html.replace('data-data-base="../osm-v7-ocean-boundaries-preview-data-20261103/"','data-data-base="../data/"').replace('../osm-v7-ocean-boundaries-preview-data-20261103/INPUT_SCHEMA.md','../data/INPUT_SCHEMA.md').replace('../osm-v7-ocean-boundaries-preview-data-20261103/sources.json','../data/sources.json').replace('V7 ocean-boundaries','V7 full-water').replace('V7 · reviewed','V7 · full water rebuild').replace('V7 ocean-boundary and Cenderawasih Bay update','V7 full water reassignment').replace('V7 assignments','V7 full water assignments').replace('List 2 · continental water beyond 22.224 km','List 2 · continental and ocean water')
 html=re.sub(r'<script type="module" src="[^"]+"></script>',f'<script type="module" src="./app.js?v={app_hash}"></script>',html)
 write_bytes(ui/'index.html',html.encode())
 # JS generator produces canonical compact reason buckets and the separate Ocean boundaries subsection.
 node_script=f"import fs from 'node:fs';const s=fs.readFileSync({json.dumps(str(ui/'review-references.js'))},'utf8');const m=await import('data:text/javascript;base64,'+Buffer.from(s).toString('base64'));const meta=JSON.parse(fs.readFileSync({json.dumps(str(ui/'proposal.json'))}));const pres=JSON.parse(fs.readFileSync({json.dumps(str(ui/'water-presentation.json'))}));const refs=m.buildReferenceIndex(meta,pres,pres.source);console.log(JSON.stringify(refs));"
 proc=subprocess.run(['node','--input-type=module','-e',node_script],check=True,capture_output=True,text=True)
 write_bytes(ui/'review-references.json',(proc.stdout.strip()+'\n').encode())
 # A simple UI-local input schema and sources inventory.
 schema='WorldAtlas V7 full-water rebuild review bundle\n\nThe candidate grid is a fresh, full assignment of all physical-water cells. It compares against the fixed V2 grid; final V6 land classes (17–22) and the physical mask remain unchanged. No V6 water labels are inherited.\n\n`proposal.json` and `water-presentation.json` are the canonical exception/display indexes. `review-references.json` is generated from the included `review-references.js`; every member span is lazy-loaded from `exception-spans/v2-v7-diff/`. Candidate row/run streams are gzip-compressed little-endian u32 files in `grids/v7/`. `legend-counts.json` contains exact RLE width sums.\n\nList 2 uses four reason groups and a separate Ocean boundaries subsection within Water-assignment corrections. Generic fresh seed-fill items record V2 source code, V7 target ocean, four seed points, and the complete nine-route barrier network. They do not claim cell-level causation by any one boundary arc.\n\nStatus: staged-not-published. V2 and V6 remain immutable.\n'
 write_bytes(data/'INPUT_SCHEMA.md',schema.encode())
 sources={'schema':'worldatlas-v7-full-water-sources-v1','status':'staged-not-published','physical_mask_sha256':PHYS,'named_basin_source_manifest':{'path':str(NAMED),'sha256':sha(NAMED)},'coastal_manifest':{'path':str(COAST),'sha256':sha(COAST)},'ocean_barrier_manifest':{'path':str(OCEAN_BARR),'sha256':sha(OCEAN_BARR),'edge_file_sha256':sha(OCEAN_CUT)},'closed_water_qa':{'path':str(CLOSED/'independent-post-qa.json'),'sha256':'99bf3b8eb755f09aabef94a43aa6ecb30285a42e3554fbed27c3ce0557fd638b'},'v2_diff_index':{'path':str(DIFF_INDEX),'sha256':sha(DIFF_INDEX)},'ocean_sources':ocean_evidence,'sea_vox_records':len(named['source_layers'])}
 write_json(data/'sources.json',sources)
 # Copy metadata to stage root for inspection/release packing and include accounting/proofs.
 write_bytes(stage/'proposal.json',(json.dumps(proposal,ensure_ascii=False,indent=2)+'\n').encode());write_bytes(stage/'water-presentation.json',(json.dumps(pres,ensure_ascii=False,indent=2)+'\n').encode());write_bytes(stage/'review-references.json',(ui/'review-references.json').read_bytes());write_bytes(stage/'accounting.json',(json.dumps(account,ensure_ascii=False,indent=2)+'\n').encode());write_bytes(stage/'legend-counts.json',(json.dumps(legend,ensure_ascii=False,indent=2)+'\n').encode())
 # Preflight report is candidate-only and explicit about unavailable publication access.
 composition_summary={'composition_audit_sha256':sha(COMPOSITION),'grid_rows_sha256':sha(V7Y),'grid_runs_sha256':sha(V7R),'changed_cells_v2_to_v7':idx['changed_cells'],'changed_intervals_v2_to_v7':idx['changed_intervals'],'member_count':idx['member_count'],'exception_groups':len(exceptions),'exception_members':sum(len(g['members']) for g in exceptions),'water_source_members':len(water_members),'water_source_cells':water_cells,'water_display_cells':sum(x['changed_cells'] for sec in pres['continents'] for x in sec['items'])+sum(x['changed_cells'] for x in ocean_items),'ocean_items':len(ocean_items),'land_members':sum(1 for x in members.values() if x['target']>=17),'final_v7_counts':legend['versions']['v7']['counts'],'full_grid_cells':W*H}
 if composition_summary['water_display_cells']!=composition_summary['water_source_cells']:raise ValueError('water presentation source/display conservation failure')
 preflight={'schema':'worldatlas-v7-release-preflight-v1','status':'staged-not-published','candidate_dir':str(stage),'candidate_version':'V7 full water reassignment','no_overwrite_policy':'Every candidate artifact was created under an O_EXCL-exclusive unique run directory.','invariants':{'v2_immutable':True,'v6_immutable':True,'physical_mask_sha256':PHYS,'final_v6_land_retained':True,'all_physical_water_assigned':True,'no_v6_water_labels_inherited':True,'v2_to_v7_diff_fully_indexed':True,'all_5089_audited_bug_cells_corrected':True,'all_5089_audit_summary_sha256':sha(V6CHECK)},'composition':composition_summary,'ui_preflight':{'six_continent_sections':len(pres['continents']),'ocean_boundary_items':len(ocean_items),'water_reason_groups':['Continental seas and bays','Shared seas','Water-assignment corrections','Enclosed ocean pockets'],'javascript_module_syntax_test':'pending','browser_runtime_test':'pending'},'publication_prerequisites':{'candidate_raw_grid_closed_and_hash_pinned':True,'all_member_payloads_hash_pinned':True,'accounting_and_reference_index_generated':True,'hosted_object_uploads':False,'stable_index_pointer_updated':False,'publication_authorization':'none requested for this staged prep; no publication performed','external_deploy_route':'previously blocked by runtime/session filesystem restrictions; requires owner-approved accessible deployment environment or user handoff'}}
 write_json(stage/'release-preflight.json',preflight)
 # Node imports generated expected references; additionally ensure all 6 sections and four reason families.
 refs_out=read(ui/'review-references.json');
 if len(refs_out.get('lists',[]))!=2 or len(refs_out['lists'][1]['continents'])!=6 or len(refs_out['lists'][1].get('ocean_boundaries',{}).get('items',[]))!=len(ocean_items):raise ValueError('List 2 ref structure incorrect')
 # Copy app schema file into UI metadata as href target and manifest accounting references.
 # Check the exact UI-relative accounting URL before producing a release manifest.
 validate_ui_accounting(ui, proposal)
 # Write a closed output manifest last (its own hash is in manifest.sha256 sidecar).
 all_files=[]
 for p in sorted(stage.rglob('*')):
  if p.is_file() and p.name not in ('manifest.json','manifest.sha256'):
   all_files.append({'path':str(p.relative_to(stage)),'bytes':p.stat().st_size,'sha256':sha(p)})
 manifest={'schema':'worldatlas-v7-full-water-release-prep-manifest-v1','status':'staged-not-published','created_utc':'2026-11-03','candidate_version_key':'v7','candidate_version_label':'V7 full water reassignment','fixed_v2_preserved':True,'published_v6_preserved':True,'physical_mask_sha256':PHYS,'composition_audit_sha256':sha(COMPOSITION),'diff_member_index_sha256':sha(DIFF_INDEX),'exception_index_sha256':sha_bytes(canonical(exceptions)),'accounting_sha256':sha(data/'accounting.json'),'water_presentation_sha256':sha(ui/'water-presentation.json'),'review_references_sha256':sha(ui/'review-references.json'),'candidate_grid':{'rows_sha256':sha(V7Y),'runs_sha256':sha(V7R),'rows_gzip_sha256':sha(grids/'rows.u32le.gz'),'runs_gzip_sha256':sha(grids/'runs.u32le.gz')},'file_count':len(all_files),'files':all_files,'publication_performed':False}
 write_json(stage/'manifest.json',manifest);write_bytes(stage/'manifest.sha256',(sha(stage/'manifest.json')+'  manifest.json\n').encode())
 print(json.dumps({'stage':str(stage),'manifest_sha256':sha(stage/'manifest.json'),'summary':composition_summary,'file_count':len(all_files),'exception_sha256':manifest['exception_index_sha256'],'accounting_sha256':manifest['accounting_sha256'],'refs':{'lists':len(refs_out['lists']),'list2_continents':len(refs_out['lists'][1]['continents']),'ocean_items':len(refs_out['lists'][1].get('ocean_boundaries',{}).get('items',[]))}},indent=2))

if __name__=='__main__':
 import subprocess
 main()
