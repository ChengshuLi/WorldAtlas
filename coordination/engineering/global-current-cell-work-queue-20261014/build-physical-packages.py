"""Partition exact physical-only intervals into broad source-disagreement work packages."""
import argparse,bisect,gzip,hashlib,json,struct,time
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,default=Path(__file__).resolve().parent);args=ap.parse_args();D=args.data;start=time.monotonic()
read=lambda p:json.loads((D/p).read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest();binding=read('ownership-binding.json');size=binding['size'];raw=(D/'native-latitudes.f64le').read_bytes();lat=list(struct.unpack('<'+'d'*size,raw));neg=[-v for v in lat]
# Broad geographic source-comparison sessions. Order does not rank cell counts.
specs=[
 ('arctic-greenland-east-canada','Greenland and eastern Canadian Arctic',[-90,60,-10,90],['gb:GRL:ADM1','gb:CAN:ADM1','gb:CAN:ADM2','gb:CAN:ADM3']),
 ('arctic-west-americas','Western Canadian Arctic and Alaska',[-180,60,-90,90],['gb:CAN:ADM1','gb:CAN:ADM2','gb:CAN:ADM3','gb:USA:ADM1','gb:USA:ADM2']),
 ('arctic-europe-atlantic','European Arctic and north Atlantic',[-10,60,60,90],['gb:NOR:ADM1','gb:NOR:ADM2','gb:RUS:ADM1','gb:RUS:ADM2','gb:ISL:ADM1']),
 ('arctic-eastern-eurasia','Eastern Eurasian Arctic and islands',[60,60,180,90],['gb:RUS:ADM1','gb:RUS:ADM2']),
 ('north-western-hemisphere','Northern western-hemisphere coasts and islands',[-180,30,-30,60],[]),
 ('tropical-western-hemisphere','Tropical western-hemisphere coasts and islands',[-180,0,-30,30],[]),
 ('europe-west-asia','Europe and western Asian coasts and islands',[-30,30,60,60],[]),
 ('north-africa-atlantic-indian','Northern African, Atlantic and western Indian coasts and islands',[-30,0,60,30],[]),
 ('north-east-asia-pacific','Northern eastern Asian and Pacific coasts and islands',[60,30,180,60],[]),
 ('tropical-asia-pacific','Tropical Asian and Pacific coasts and islands',[60,0,180,30],[]),
 ('south-western-hemisphere','Southern western-hemisphere coasts and islands',[-180,-60,-30,0],[]),
 ('south-africa-atlantic-indian','Southern African, Atlantic and Indian coasts and islands',[-30,-60,90,0],[]),
 ('south-australasia-pacific','Australasian and southern Pacific coasts and islands',[90,-60,180,0],[]),
 ('southern-l1-islands','Southern retained level-1 island-source discrepancies',[-180,-90,180,-60],[])]
ceil=lambda n,d:-((-n)//d)
def rect(box):
 west,south,east,north=box
 return [max(0,min(size,ceil(2*size*(west+180)-360,720))),max(0,min(size,ceil(2*size*(east+180)-360,720))),bisect.bisect_left(neg,-north),bisect.bisect_left(neg,-south)]
def pin(path):
 b=(D/path).read_bytes();return {'path':path,'bytes':len(b),'sha256':sha(b)}
records=read('gshhg-records.json');compact=[{k:m[k] for k in ['id','level','container','bounds','native_offset','native_record_bytes','decoded_sha256','category','qualification_issues']} for m in records]
roster=gzip.compress((json.dumps(compact,separators=(',',':'))+'\n').encode(),mtime=0);(D/'physical-package-source-roster.json.gz').write_bytes(roster);rosterpin=pin('physical-package-source-roster.json.gz')
packages=[]
for ident,title,box,partners in specs:
 x0,x1,y0,y1=rect(box);candidateids=[]
 for m in compact:
  if m['category']!='supported':continue
  a,b,c,d=m['bounds']
  if d<box[1] or b>box[3]:continue
  if any(a+s<=box[2] and c+s>=box[0] for s in [-360,0,360]):candidateids.append(m['id'])
 packages.append({'package_id':'physical-'+ident,'title':title,'category':'physical-territorial-source-disagreement','native_cells':0,'interval_segments':0,'native_blocks':[],'source_families':partners,'owners':[],'selector':{'kind':'native-cell-center-geographic-rectangle','longitude_latitude_bounds':box,'bounds_semantics':'west inclusive/east exclusive; native row start includes north and row end excludes south; exact native integer bounds are authoritative','x_start':x0,'x_end':x1,'row_start':y0,'row_end':y1,'input_pattern':'physical-only-block-{block:03d}.json.gz','portable_derivation':'physical-support minus complete source-candidates union'},'source_bbox_candidate_ids':candidateids,'source_candidate_scope':'Conservative complete physical-source bounding-box candidates, not asserted exact membership. Retain all level1–4/container source context for whole-geometry qualification.','input_blocks':[],'witness':None})
files=[]
for block in range((size+4095)//4096):
 name=f'physical-only-block-{block:03}.json.gz';facts=pin(name);rows=json.loads(gzip.decompress((D/name).read_bytes()));files.append(facts)
 for p in packages:
  s=p['selector'];n=0;segments=0
  for row in rows:
   y=row['y']
   if not s['row_start']<=y<s['row_end']:continue
   for a,b in row['runs']:
    a=max(a,s['x_start']);b=min(b,s['x_end'])
    if a<b:
     n+=b-a;segments+=1
     if p['witness'] is None:p['witness']={'x':a,'y':y,'longitude':360*(a+.5)/size-180,'latitude':lat[y]}
  if n:p['native_cells']+=n;p['interval_segments']+=segments;p['native_blocks'].append(block);p['input_blocks'].append({'block':block,**facts,'package_cells':n,'package_interval_segments':segments,'physical_input':pin(f'physical-support-block-{block:03}.json.gz'),'territorial_input':pin(f'source-candidates-block-{block:03}.json.gz'),'derived_canonical_sha256':sha((json.dumps([r for r in rows if r['runs']],separators=(',',':'))+'\n').encode())})
expected=read('source-physical-join-summary.json')['counts']['physical_land_without_any_retained_territorial_source'];assert sum(p['native_cells'] for p in packages)==expected
# Validate an exact disjoint full-world rectangle partition on row-break bands.
yedges=sorted({0,size,*[v for p in packages for v in [p['selector']['row_start'],p['selector']['row_end']]]})
for y in yedges[:-1]:
 spans=sorted((p['selector']['x_start'],p['selector']['x_end']) for p in packages if p['selector']['row_start']<=y<p['selector']['row_end']);at=0
 for a,b in spans:assert a==at;at=b
 assert at==size
for p in packages:
 p.update(accounting_role='disjoint-counted-global-work-domain',evidence={'ownership':pin('ownership-binding.json'),'physical_summary':pin('physical-unassigned-summary.json'),'territorial_join':pin('source-physical-join-summary.json'),'physical_source_roster':rosterpin,'source_native_custody':read('physical-source-summary.json')['native_source'],'territorial_catalogue':pin('retained-source-catalogue.json'),'arctic_two_source_sanity':pin('arctic-territorial-source-sanity.json') if p['package_id'].startswith('physical-arctic-') else None},cost={'native_interval_segments':p['interval_segments'],'native_blocks':len(p['native_blocks']),'physical_bbox_candidate_records':len(p['source_bbox_candidate_ids']),'compressed_interval_input_bytes':sum(r['bytes'] for r in p['input_blocks']),'max_rows_per_execution_frame':4096,'selection_does_not_scan_individual_cells':True},work={'question':'Compare complete original physical and territorial footprints in this geographic source session. Determine source coverage, observation-date, coastline/ice definition or topology disagreement before proposing any location assignment. The discrepancy itself is not an established repair error.','completion':'Classify every exact interval as source-supported territorial repair with an explicit current location and complete exclusions/competitors, physical/territorial source disagreement requiring new authority, or a documented non-repair exception. Preserve original bytes and immutable row selectors.','priority_basis':'Source availability, shared mismatch cause, source acquisition/qualification cost and downstream readiness; never raw cell count alone.','arctic_note':'Native Web Mercator cell density increases at high latitude; cell counts are not ground area.'},execution={'command':f"python physical-batch-intervals.py {p['package_id']} OUTPUT_DIRECTORY",'output':'intervals.jsonl.gz triples [row,startInclusive,endExclusive] plus manifest.json','mode':'Investigate exact scope; no ownership mutation or automatic repair permission.'})
packages=[p for p in packages if p['native_cells']]
unknown=read('physical-source-summary.json')['invalid_or_unsupported_records'];assert len(unknown)==1 and unknown[0]['id']==2380
special=[{'package_id':'physical-invalid-source-2380','title':'Resolve malformed original physical source 2380','category':'invalid-source-coverage-investigation','native_cells':None,'counted_global_work_cells':0,'envelope_cells':948,'unknown_outside_valid_physical_cells':938,'unknown_residual_territorial_overlap_cells':63,'unknown_residual_outside_global_work_union_cells':875,'overlap_note':'The948 envelope is supplemental context, not additiveworkload. Of938 outsidevalidphysicalsupport,63alreadybelongtoterritorialsource scope;875lieoutsidethecountedglobalunion.','known_physical_overlap_cells':10,'accounting_role':'supplemental-unknown-envelope-not-added-to-global-work-total','native_blocks':[23],'source_families':['gshhg:2380'],'owners':[],'selector':{'kind':'explicit-unknown-envelope','input_pattern':'physical-unknown-envelope-block-{block:03d}.json.gz'},'input_blocks':[{'block':23,**pin('physical-unknown-envelope-block-023.json.gz'),'package_cells':948}],'source_bbox_candidate_ids':[2380],'evidence':{'physical_source_roster':rosterpin,'source_record':unknown[0],'physical_summary':pin('physical-unassigned-summary.json')},'cost':{'native_interval_segments':None,'source_native_record_bytes':unknown[0]['native_record_bytes']},'work':{'question':'Determine whether a defensible alternate original source or documented invalidity resolution supports any cells in the retained invalid source envelope. Do not repair the polygon implicitly.','completion':'Replace unknown status only with whole-source evidence and exact current-cell qualification; distinguish the 938 unknown-physical cells from the 10 already supported cells and from any territorial candidates.','priority_basis':'Small bounded source investigation; not ranked as 948 confirmed repair cells.'},'execution':{'command':'python physical-batch-intervals.py physical-invalid-source-2380 OUTPUT_DIRECTORY','output':'Unknown-envelope intervals and original source metadata, explicitly outside counted-work arithmetic.'}}, {'package_id':'physical-antarctic-policy-coverage','title':'Confirm Antarctic excluded-domain coverage policy','category':'excluded-domain-policy-review','native_cells':None,'counted_global_work_cells':0,'excluded_source_records':673,'accounting_role':'policy-excluded-domain-not-measured-as-repair-cells','native_blocks':[],'source_families':['gshhg:L5','gshhg:L6'],'owners':[],'selector':{'kind':'excluded-source-records','source_category':'excluded-antarctica'},'source_bbox_candidate_ids':[m['id'] for m in compact if m['category']=='excluded-antarctica'],'evidence':{'physical_source_roster':rosterpin,'territorial_catalogue':pin('retained-source-catalogue.json'),'current_policy':'WorldAtlas AGENTS.md excludes Antarctica; retained territorial catalogue has no ATA product.'},'cost':{'source_records':673,'native_cells':'unmeasured, not zero'},'work':{'question':'Verify the intended Antarctic policy scope and preserve the difference between absent coverage and a zero missing-cell result. If scope changes, obtain the intended alternative Antarctic coastline/ice definition before any native recount.','completion':'Record explicit confirmed exclusion or a separately authorized source/ownership investigation scope; never add an invented Antarctic repair-cell count.','priority_basis':'Scope decision, separate from repair scheduling.'},'execution':{'command':'python physical-batch-intervals.py physical-antarctic-policy-coverage OUTPUT_DIRECTORY','output':'673 excluded original source metadata records and policy-review manifest; no known-repair interval claim.'}}]
specialrows=[m for m in compact if m['category']=='excluded-antarctica' or m['id']==2380];(D/'physical-package-special-source-records.json').write_text(json.dumps(specialrows,separators=(',',':'))+'\n');specialpin=pin('physical-package-special-source-records.json')
for p in special:p['evidence']['special_source_records']=specialpin
queue={'current_commit':binding['current_commit'],'packages':packages+special,'counts':{'physical_only_packages':len(packages),'physical_only_cells':expected,'supplemental_investigation_packages':len(special),'total_packages':len(packages)+len(special)},'source_roster':rosterpin,'partition_verification':{'complete_world_rectangle_partition':True,'overlap_cells':0,'uncovered_cells':0,'sum_matches_exact_physical_only_domain':True},'scheduling':'Broad source/geographic mismatch sessions; physical versus retained territorial disagreement is not an established repair error. Package counts are planning units and can change with source qualification. Do not rank by native cell count alone.','seconds':time.monotonic()-start}
cache_note={'optional_local_cache':True,'portable_reconstruction':'Use physical_metadata_repository commit and transport-map paths with physical-source-summary.json receipts. source_bbox_candidate_ids select original retained records; this cache is not required by physical-batch-intervals.py.'}
queue['source_roster'].update(cache_note)
for t in queue['packages']:
 if 'physical_source_roster' in t['evidence']:t['evidence']['physical_source_roster'].update(cache_note)
source_blocks={r['block']:r for r in read('source-census-summary.json')['blocks']}
for t in queue['packages']:
 for r in t.get('input_blocks',[]):
  if 'territorial_input' not in r:continue
  b=source_blocks[r['block']];r['territorial_input'].update({k:b[k] for k in ['decoded_bytes','decoded_sha256']})
  if b.get('parts'):r['territorial_input']['parts']=b['parts']
for t in queue['packages']:
 e=t['evidence']
 if 'source_native_custody' in e:e['source_native_custody'].update(repository_commit=queue['current_commit'],repository_prefix='coordination/engineering/gshhg-native-member-custody-20261007/results/',index_path='coordination/engineering/gshhg-native-member-custody-20261007/results/member-index.json')
 e['physical_metadata_repository']={'commit':queue['current_commit'],'prefix':'coordination/engineering/global-physical-comparison-20261006/results/','transport_map_path':'coordination/engineering/global-physical-comparison-20261006/results/transport-map.json','receipts':'physical-source-summary.json'}
(D/'physical-package-queue.json').write_text(json.dumps(queue,indent=2)+'\n');print(json.dumps({'counts':queue['counts'],'packages':[{'id':p['package_id'],'cells':p['native_cells']} for p in queue['packages']],'seconds':queue['seconds']}),flush=True)
