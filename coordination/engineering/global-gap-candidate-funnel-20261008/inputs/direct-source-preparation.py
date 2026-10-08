#!/usr/bin/env python3
"""Read-only exact-ID reconciliation of #1202 source witnesses and terminal decisions.
Consumes only already retained local manifests/outputs. Performs no GIS, source
acquisition, geometry operations, or edits to the WorldAtlas repository.
"""
import csv, gzip, hashlib, io, json, pathlib, sys
from collections import Counter

ROOT = pathlib.Path('/Users/chengshuli/world-atlas-workspace')
REPO = ROOT / 'WorldAtlas'
OUT = pathlib.Path(__file__).resolve().parent / 'direct-source-shards-v1'
OUT.mkdir(exist_ok=True)
ROUTING = REPO / 'coordination/engineering/global-actionability-routing-20261007/results'
NUMERIC = REPO / 'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2'
WITNESS = ROOT / '.cache/repair-readiness-1231-20261006/direct-source-coverage-screen'

TARGETS = {
 'physical-component:bb4a3e58a98cdc2a589c2e0d8bc2e8172e3147d7bc68fe755a0f1fc2df713121': {
  'target':'atlas:physical:CAN-103:QUE','geometry_sha256':'b8b357848262d2ccb59b0e9823439c76f329e5dc9baa7678fa0e5bdfb23b1265','source_relative_mapped_land_area_m2':20142.432883697165},
 'physical-component:1d458ddaf986b7485036312676a27f99539ecb743c8e093805cf4d4f49c55ed8': {
  'target':'atlas:physical:CAN-114:NFL','geometry_sha256':'172a25d939353bed6168c950cb0f9aaba75e7ff770aad053c7e36c963a6dc98e','source_relative_mapped_land_area_m2':4645.122244964981},
}
NORDIC = {
 'physical-component:000bb4f5335601ba33572e2aca833ec87188059fcdd1f5d830826fa3783c2f05',
 'physical-component:2b3823b49787cb624b7298ab8394ef521dd10a907c12c2a2b0249a6796970eb5',
 'physical-component:4d6cbd694c671b2f56683e931c11b97522823512c0542a6aa7aaa73843ed078b',
 'physical-component:9bdcd0999b59fbb4e5e8601729b4a4dadf0900ed8ead792d512aaa031e314ae9',
}

def sha(b): return hashlib.sha256(b).hexdigest()
def load_json(p): return json.loads(p.read_bytes())
def verified_raw(base, desc):
    p = base / desc['path']; enc = p.read_bytes()
    if len(enc) != desc['bytes'] or sha(enc) != desc['sha256']:
        raise ValueError('encoded-byte receipt mismatch: '+str(p))
    raw = gzip.decompress(enc)
    if len(raw) != desc['uncompressed_bytes'] or sha(raw) != desc['uncompressed_sha256']:
        raise ValueError('decoded-byte receipt mismatch: '+str(p))
    return raw

def number_order(path):
    return int(pathlib.PurePosixPath(path).name.split('.')[0].split('-')[-1])
def stream_rows(base, report, prefix):
    descs = [d for d in report['outputs'] if d['path'].startswith(prefix)]
    descs.sort(key=lambda d:number_order(d['path']))
    carry = b''
    for d in descs:
        data = carry + verified_raw(base, d)
        lines = data.split(b'\n'); carry = lines.pop()
        for line in lines:
            if line: yield json.loads(line)
    if carry: yield json.loads(carry)
    return

def stream_rows_located(base, report, prefix):
    """Stream JSONL records and retain immutable decoded-stream offsets."""
    descs = [d for d in report['outputs'] if d['path'].startswith(prefix)]
    descs.sort(key=lambda d:number_order(d['path']))
    carry=b''; carry_start=0; stream_end=0; ordinal=0
    boundaries=[]
    for d in descs:
        raw=verified_raw(base,d)
        boundaries.append((stream_end,stream_end+len(raw),d['path'],d['uncompressed_sha256']))
        data=carry+raw
        data_start=carry_start if carry else stream_end
        lines=data.split(b'\n'); carry=lines.pop()
        pos=data_start
        for line in lines:
            if line:
                owner=next((b for b in boundaries if b[0] <= pos < b[1]),None)
                if owner is None: raise ValueError('record locator outside source descriptor')
                yield json.loads(line), {'product_prefix':prefix,'record_ordinal':ordinal,'decoded_stream_byte_offset':pos,'starts_in_descriptor':owner[2],'descriptor_decoded_sha256':owner[3]}
                ordinal+=1
            pos+=len(line)+1
        carry_start=pos
        stream_end+=len(raw)
    if carry:
        owner=next((b for b in boundaries if b[0] <= carry_start < b[1]),None)
        if owner is None: raise ValueError('final record locator outside source descriptor')
        yield json.loads(carry), {'product_prefix':prefix,'record_ordinal':ordinal,'decoded_stream_byte_offset':carry_start,'starts_in_descriptor':owner[2],'descriptor_decoded_sha256':owner[3]}

def compact_row(x):
    return {k:x.get(k) for k in ('component','current_feature_sha256','current_geometry_sha256','family','physical_status','physical_source_vintage','next_prerequisite','physical_authority','source_fitness_prerequisite','dispatch_ready')}

route_report_bytes=(ROUTING/'report.json').read_bytes(); route_report=json.loads(route_report_bytes)
if route_report.get('status')!='PASS' or route_report.get('source_delivery')!='fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7':
    raise ValueError('unexpected #1298 report head/status')
route_components={}; component_locator={}
for x,loc in stream_rows_located(ROUTING,route_report,'components-'):
    cid=x['component']
    if cid in route_components: raise ValueError('duplicate current component '+cid)
    route_components[cid]=compact_row(x); component_locator[cid]=loc
if len(route_components)!=95173: raise ValueError('current component roster is incomplete')

admin_by_id={}; admin_locator={}
for x,loc in stream_rows_located(ROUTING,route_report,'admin-bindings-'):
    cid=x['component']
    if cid in admin_by_id or len(x.get('observations',[]))!=1:
        raise ValueError('duplicate or non-single observation for '+cid)
    admin_by_id[cid]=x['observations'][0]; admin_locator[cid]=loc
if len(admin_by_id)!=57785: raise ValueError('admin comparison roster is incomplete')

land_desc=next(d for d in route_report['outputs'] if d['path']=='land-source-fitness-000.bin.gz')
land_raw=verified_raw(ROUTING,land_desc); land_rows=json.loads(land_raw)
land_by_id={r['component']:r for r in land_rows}
land_locator={r['component']:{'product':'land-source-fitness-000.bin.gz','json_array_record_ordinal':i} for i,r in enumerate(land_rows)}
if len(land_rows)!=1005 or len(land_by_id)!=1005: raise ValueError('land+compatible roster mismatch')
for cid,r in land_by_id.items():
    obs=r['original_admin_observations']
    if len(obs)!=1 or obs[0]['status']!='one-compatible-recorded-subject-uniquely-covers-component': raise ValueError('invalid land-source row '+cid)
    if r['physical_authority']!='unapproved' or r['dispatch_ready'] is not False: raise ValueError('land-source row was unexpectedly approved/ready '+cid)

w555_path=WITNESS/'complete-current-unique-witness-dispatch-555-preserved.json'
w1391_path=WITNESS/'complete-current-unique-witness-dispatch.json'
w555_bytes=w555_path.read_bytes(); w1391_bytes=w1391_path.read_bytes()
w555=json.loads(w555_bytes); w1391=json.loads(w1391_bytes)
if (len(w555['all_rows'])!=555 or w555['full_witness_count']!=555 or w555['head']!='a26f8d8b50e7349054b86e70d1e6e552a9a2b0fd'):
    raise ValueError('historical 555 roster identity mismatch')
if len(w1391['all_rows'])!=1391 or w1391['full_witness_count']!=1391:
    raise ValueError('historical 1391 roster count mismatch')
ids555=[r['component'] for r in w555['all_rows']]; ids1391=[r['component'] for r in w1391['all_rows']]
if len(set(ids555))!=555 or len(set(ids1391))!=1391: raise ValueError('witness IDs are not unique')
set555=set(ids555); set1391=set(ids1391); setland=set(land_by_id); setadmin=set(admin_by_id)
if set1391 != {cid for cid,o in admin_by_id.items() if o['status']=='one-compatible-recorded-subject-uniquely-covers-component'}:
    raise ValueError('private 1391 roster does not match current accepted output-derived roster')
if not (set555 <= set1391 <= setadmin <= set(route_components)) or not (setland <= set1391):
    raise ValueError('nested cohort relation failed')
if len({r['source_subject']['id'] for r in w555['all_rows']})!=412: raise ValueError('555 source-subject count mismatch')
if len({admin_by_id[cid]['uniquely_covering_compatible_recorded_subject']['id'] for cid in set1391})!=925:
    raise ValueError('1391 unique source-subject count mismatch')

num_report_bytes=(NUMERIC/'report.json').read_bytes(); num_report=json.loads(num_report_bytes)
if num_report.get('status')!='complete' or num_report.get('execution_commit')!='3ef1b938a4813adcc62be632df29837c8122a1bb': raise ValueError('unexpected #1300 run/status')
num_by_id={}; numeric_locator={}
for x,loc in stream_rows_located(NUMERIC,num_report,'diagnoses-'):
    cid=x['component_id']
    if cid in num_by_id: raise ValueError('duplicate numeric diagnosis '+cid)
    num_by_id[cid]=x['conservative_class']; numeric_locator[cid]=loc
if len(num_by_id)!=26276: raise ValueError('numeric diagnosis roster incomplete')
num_counts=Counter(num_by_id.values())
if num_counts != Counter({'local-construction-contradiction-demonstrated':3666,'retained-unresolved-numerical-or-context-prerequisite':21316,'retained-unresolved-original-replay-mismatch':1294}):
    raise ValueError('numeric diagnosis class counts mismatch')

global_desc=next(d for d in route_report['outputs'] if d['path']=='global-summary-000.bin.gz')
global_summary=json.loads(verified_raw(ROUTING,global_desc))

if not set(TARGETS) <= set(route_components): raise ValueError('#1295 target missing from current roster')
if set(TARGETS) & set(num_by_id): raise ValueError('#1295 source corrections unexpectedly overlap numeric-first cohort')
if set(TARGETS) & setland: raise ValueError('#1295 targets unexpectedly present in #1298 land-source route; reconcile before claim')
if not NORDIC <= set(route_components): raise ValueError('Nordic packet IDs not in current cohort')

# Exact intersections and current classifications.
def status_counts(ids): return dict(sorted(Counter(route_components[c]['physical_status'] for c in ids).items()))
intersections={
 '555_in_57785':len(set555 & setadmin),
 '555_in_1391':len(set555 & set1391),
 '555_in_1005':len(set555 & setland),
 '1391_in_57785':len(set1391 & setadmin),
 '1391_in_1005':len(set1391 & setland),
 '1005_in_1391':len(setland & set1391),
 'numeric_555':len(set555 & set(num_by_id)),
 'numeric_1391':len(set1391 & set(num_by_id)),
 'numeric_1005':len(setland & set(num_by_id)),
 'numeric_1295_targets':len(set(TARGETS) & set(num_by_id)),
}
if intersections != {'555_in_57785':555,'555_in_1391':555,'555_in_1005':430,'1391_in_57785':1391,'1391_in_1005':1005,'1005_in_1391':1005,'numeric_555':60,'numeric_1391':142,'numeric_1005':0,'numeric_1295_targets':0}:
    raise ValueError('unexpected exact set intersection: '+repr(intersections))

# A 4-ID Nordic overlay is a geometric mismatch observation only, not a truth decision.
# Validate local packet set and preserve that limit explicitly.

fields=['component_id','terminal_physical_class','terminal_decision','numerical_diagnosis','source_comparison_status','source_comparison_packet','source_products','unique_source_subject_id','source_reference_year','source_geometry_sha256','historical_555_witness','historical_555_cohort','unique_source_witness_1391','land_plus_unique_route_1005','nordic_geometric_mismatch_observation','physical_status_source_relative','physical_source_vintage','next_prerequisite','current_feature_sha256','current_geometry_sha256','family']
MAX_SHARD=8*1024*1024
class BoundedWriter:
    def __init__(self,prefix,suffix): self.prefix=prefix; self.suffix=suffix; self.buf=bytearray(); self.parts=[]; self.i=0
    def _flush(self):
        if not self.buf: return
        self.i+=1; name=f'{self.prefix}-{self.i:02d}.{self.suffix}.gz'; p=OUT/name; raw=bytes(self.buf)
        with p.open('wb') as f:
            with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0,compresslevel=9) as gz: gz.write(raw)
        enc=p.read_bytes(); dec=gzip.decompress(enc)
        if dec!=raw or len(dec)>MAX_SHARD: raise ValueError('bounded shard validation failed')
        self.parts.append({'path':name,'encoded_bytes':len(enc),'encoded_sha256':sha(enc),'decoded_bytes':len(dec),'decoded_sha256':sha(dec)})
        self.buf.clear()
    def write(self,record):
        if len(record)>MAX_SHARD: raise ValueError('one source output record exceeds shard cap')
        if self.buf and len(self.buf)+len(record)>MAX_SHARD: self._flush()
        self.buf.extend(record)
    def close(self): self._flush(); return self.parts

def csv_record(rec, header=False):
    b=io.StringIO(newline=''); w=csv.DictWriter(b,fieldnames=fields,lineterminator='\n');
    if header: w.writeheader()
    else: w.writerow(rec)
    return b.getvalue().encode('utf-8')

roster_writer=BoundedWriter('components','csv')
provenance_writer=BoundedWriter('component-provenance','jsonl')
approval_path=ROOT/'.cache/root1295-funnel-approval-live-20261008.json'
approval_sha=sha(approval_path.read_bytes())
header_bytes=csv_record({},header=True); roster_writer.write(header_bytes)
roster_digest=hashlib.sha256(); roster_digest.update(header_bytes); roster_raw_bytes=len(header_bytes); row_count=0
hist_by_id={r['component']:r for r in w555['all_rows']}
for cid,x in route_components.items():
    obs=admin_by_id.get(cid,{})
    subject=obs.get('uniquely_covering_compatible_recorded_subject') or {}
    hist=hist_by_id.get(cid)
    rec={
     'component_id':cid,
     'terminal_physical_class':'confirmed_missing_land' if cid in TARGETS else 'unresolved_or_unadjudicated',
     'terminal_decision':'#1295 explicit narrow physical-region source-envelope approval; correction not activated' if cid in TARGETS else '',
     'numerical_diagnosis':num_by_id.get(cid,'not-in-#1300-numeric-first-cohort'),
     'source_comparison_status':obs.get('status','not-in-57,785-source-comparison-cohort'),
     'source_comparison_packet':obs.get('packet',''),
     'source_products':';'.join(obs.get('source_products',[])),
     'unique_source_subject_id':subject.get('id',''),
     'source_reference_year':subject.get('reference_year',''),
     'source_geometry_sha256':subject.get('original_feature_sha256',''),
     'historical_555_witness':'true' if cid in set555 else 'false',
     'historical_555_cohort':hist.get('cohort','') if hist else '',
     'unique_source_witness_1391':'true' if cid in set1391 else 'false',
     'land_plus_unique_route_1005':'true' if cid in setland else 'false',
     'nordic_geometric_mismatch_observation':'true' if cid in NORDIC else 'false',
     'physical_status_source_relative':x['physical_status'],
     'physical_source_vintage':x.get('physical_source_vintage') or '',
     'next_prerequisite':x.get('next_prerequisite') or '',
     'current_feature_sha256':x.get('current_feature_sha256') or '',
     'current_geometry_sha256':x.get('current_geometry_sha256') or '',
     'family':x.get('family') or '',
    }
    rowbytes=csv_record(rec); roster_writer.write(rowbytes); roster_digest.update(rowbytes); roster_raw_bytes+=len(rowbytes); row_count+=1
    prov={'component_id':cid,'component_record':component_locator[cid],
          'admin_comparison_record':admin_locator.get(cid),
          'numeric_diagnosis_record':numeric_locator.get(cid),
          'land_source_fitness_record':land_locator.get(cid),
          'historical_555_record':{'source_path':str(w555_path.relative_to(ROOT)),'source_sha256':sha(w555_bytes),'record_ordinal':next((i for i,r in enumerate(w555['all_rows']) if r['component']==cid),None)} if cid in set555 else None,
          'decision_capture':{'path':str(approval_path.relative_to(ROOT)),'sha256':approval_sha} if cid in TARGETS else None}
    provenance_writer.write((json.dumps(prov,separators=(',',':'),sort_keys=True)+'\n').encode())
roster_parts=roster_writer.close(); provenance_parts=provenance_writer.close()
roster_raw_sha=roster_digest.hexdigest()
if row_count!=95173 or roster_raw_bytes!=54176325 or roster_raw_sha!='3f45e56dd8ba6eb0b4f0634eaac1539f1193509d0fcd5756af7a7f2a828162a0':
    raise ValueError(f'direct output differs from prior authenticated canonical CSV: rows={row_count} bytes={roster_raw_bytes} sha={roster_raw_sha}')
roster_encoded_sha=''.join(x['encoded_sha256'] for x in roster_parts)
provenance_manifest=[]
for report,base,prefix in [(route_report,ROUTING,'components-'),(route_report,ROUTING,'admin-bindings-'),(num_report,NUMERIC,'diagnoses-')]:
    for d in sorted([d for d in report['outputs'] if d['path'].startswith(prefix)],key=lambda x:number_order(x['path'])):
        provenance_manifest.append({'root':str(base.relative_to(ROOT)),'path':d['path'],'encoded_bytes':d['bytes'],'encoded_sha256':d['sha256'],'decoded_bytes':d['uncompressed_bytes'],'decoded_sha256':d['uncompressed_sha256']})
provenance_manifest.append({'root':str(ROUTING.relative_to(ROOT)),'path':land_desc['path'],'encoded_bytes':land_desc['bytes'],'encoded_sha256':land_desc['sha256'],'decoded_bytes':land_desc['uncompressed_bytes'],'decoded_sha256':land_desc['uncompressed_sha256']})
source_encoded_total=sum(d['encoded_bytes'] for d in provenance_manifest)
source_decoded_total=sum(d['decoded_bytes'] for d in provenance_manifest)
source_max_decoded=max(d['decoded_bytes'] for d in provenance_manifest)

summary={
 'purpose':'Exact-ID, read-only reconciliation generated directly from verified routing/admin/numeric records; no GIS, geometry operation, source collection, issue edit, or repository change.', 'decision_evidence_capture':{'path':str(approval_path.relative_to(ROOT)),'sha256':approval_sha,'scope':'Only the two #1295 named physical-region source-envelope fits; remain unactivated. Not administrative-boundary truth, regional interiors, legal territory, historical validity/affiliation, shoreline authority, general source-date suitability, production publication, or other candidates.'},
 'current_cohort':{'components':95173,'current_cohort_sha256':route_report['current_audited_cohort'],'source_delivery':route_report['source_delivery'],'routing_report_sha256':sha(route_report_bytes),'routing_report_status':route_report['status']},
 'source_comparison':{'unique_component_rows':57785,'packet_counts':global_summary.get('admin_packets'),'status_counts':dict(sorted(Counter(o['status'] for o in admin_by_id.values()).items())),'source_comparison_manifest':'coordination/engineering/global-actionability-routing-20261007/results/report.json'},
 'historical_555':{'meaning':'Distinct physical-component rows with one compatible recorded-source subject uniquely covering the component, from the first terminally reviewed source cohorts; not source subjects, classification decisions, or repairs.','unique_component_ids':555,'unique_source_subject_ids':412,'cohorts':w555['cohort_counts'],'private_head':w555['head'],'private_roster_path':str(w555_path.relative_to(ROOT)),'private_roster_bytes':len(w555_bytes),'private_roster_sha256':sha(w555_bytes),'all_surface_status_unverified':all(r['physical_surface_status']=='unverified' for r in w555['all_rows']),'all_no_admin_assignment':all(r['administrative_assignment'] is None for r in w555['all_rows']),'all_cause_unknown':all(r['cause_status']=='unknown' for r in w555['all_rows']),'current_source_relative_status_counts':status_counts(set555)},
 'current_unique_coverage_witnesses':{'unique_component_ids':1391,'unique_source_subject_ids':925,'derived_independently_from_accepted_57,785_admin_bindings_status':'one-compatible-recorded-subject-uniquely-covers-component','private_join_roster_sha256':sha(w1391_bytes),'private_join_roster_path':str(w1391_path.relative_to(ROOT)),'all_surface_status_unverified':all(o['surface_status']=='unverified' for cid,o in admin_by_id.items() if cid in set1391),'all_cause_unknown':all(o['cause_status']=='unknown' for cid,o in admin_by_id.items() if cid in set1391)},
 'current_land_plus_unique_route':{'unique_component_ids':1005,'complete_families':len({r['family'] for r in land_rows}),'all_source_status_unique_cover':True,'all_physical_status':'mapped-land-support (source-relative only)','all_physical_authority':'unapproved','all_dispatch_ready':False,'all_next_action':'GEO-source-fitness-before-processing-reproduction'},
 'exact_joins':intersections,
 '555_current_route_statuses':status_counts(set555),
 '1391_current_route_statuses':status_counts(set1391),
 '1391_not_in_1005_status_counts':status_counts(set1391-setland),
 '555_not_in_1005_status_counts':status_counts(set555-setland),
 'numeric_first':{'unique_component_ids':26276,'execution_commit':num_report['execution_commit'],'report_sha256':sha(num_report_bytes),'report_status':num_report['status'],'class_counts':dict(sorted(num_counts.items())),'overlap_with_555_1391_1005_and_#1295_targets':{'555':intersections['numeric_555'],'1391':intersections['numeric_1391'],'1005':intersections['numeric_1005'],'#1295_targets':intersections['numeric_1295_targets']},'all_1005_excluded_from_numeric_first':intersections['numeric_1005']==0},
 'terminal_decision_lower_bound':{'confirmed_missing_land':{'count':2,'ids':list(TARGETS),'decision':'#1295 explicit AAFC native-source envelope approval; source named physical-region subdivision, not administrative boundary; both remain unactivated','source_relative_targets':TARGETS,'approval_vintage':'current #1295 issue body/2026-10-08; two corrections originally scoped in PR1 #1317, PR2 activation remains blocked'},'confirmed_water':{'count':0,'reason':'No whole-component, source-approved water decision found in current campaign checkpoint; 411 mapped-inland-water-support rows remain source-relative.'},'mixed_land_water_needing_split':{'count':0,'reason':'No authoritative per-component mixed surface split has been approved; 19,962 mixed-source-support rows remain source-relative.'},'reference_data_mismatch_as_adjudicated_cause':{'count':0,'reason':'57,785 comparison rows are not 57,785 mismatch decisions; geometric differences and source coverage are not adjudication of which reference is wrong.'},'unresolved_or_unadjudicated_physical_class':{'count':95171,'scope':'All current IDs except the two #1295 narrow approvals. Includes source witnesses, local numeric diagnoses and source-relative physical classes that do not resolve whole-component surface truth.'}},
 'orthogonal_diagnostic_sets':{'local_construction_contradiction_demonstrated':{'count':num_counts['local-construction-contradiction-demonstrated'],'meaning':'Exact #1300 local constructed-difference contradiction for a component; does not classify the entire component as land/water or prove release/rendering impact.','report':'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2/report.json'},'nordic_geometric_source_atlas_mismatch_observation':{'count':4,'ids':sorted(NORDIC),'meaning':'Complete consumed simplified NOR/SWE source vs Atlas source geometry mismatch and candidate outside-source residuals; no source-truth, dry-land or repair approval.','packet':'research/geography/gap-source-nordic-shared-seams-20261006/README.md'},'mapped_land_source_relative':global_summary.get('physical_status_counts',{}).get('mapped-land-support',None),'mapped_water_source_relative':global_summary.get('physical_status_counts',{}).get('mapped-inland-water-support',None),'mixed_source_relative':global_summary.get('physical_status_counts',{}).get('mixed-source-support',None)},
 'roster':{'format':'ordered deterministic gzip CSV shards generated directly while joining verified original source rows; one row per current component','rows':row_count,'decoded_bytes':roster_raw_bytes,'decoded_sha256':roster_raw_sha,'shards':roster_parts,'fields':fields,'header_convention':'Header appears only in first shard; concatenate decoded shard streams in listed order with no inserted bytes.'}, 'row_provenance':{'format':'deterministic gzip JSONL shards; one locator record per candidate row','shards':provenance_parts,'decoded_shards_max_bytes':MAX_SHARD,'source_descriptors':provenance_manifest,'source_descriptor_totals':{'count':len(provenance_manifest),'encoded_bytes':source_encoded_total,'decoded_bytes':source_decoded_total,'max_single_decoded_bytes':source_max_decoded},'processing_cap_statement':'All individually consumed authenticated source output descriptors decode to at most 8 MiB each. Aggregate decoded input across the 67 descriptors is 539,120,612 bytes, so this is not asserted to fit a 32 MiB aggregate-phase cap; claim only per-file boundedness. The earlier oversized canonical CSV was not read or used by this direct producer. Output CSV and locator shards are each <=8 MiB decoded.','prior_transport_only_artifact':{'path':'.cache/root1202-evidence-reconciliation-20261008/bounded-csv-shards-v1/manifest.json','role':'Preserved prior attempt; transport-only split of existing CSV and not an input to this producer.'},'locator_fields':'Original decoded JSONL product stream offset, record ordinal, and descriptor containing record start; land source uses original array ordinal; historical 555 uses preserved roster path/hash/ordinal.'},
 'source_paths':{'routing':'coordination/engineering/global-actionability-routing-20261007/results/report.json and results/*.bin.gz','numeric':'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2/report.json and diagnoses-*.jsonl.gz','historical_555_private':str(w555_path.relative_to(ROOT))},
 'limits':['The 555 roster is a partial historical cohort, though its 555 distinct IDs match the later merged source-comparison and unique-witness rosters exactly.','The current 1,391 witness count is reproducible directly from the accepted 57,785 admin-binding rows; it is not 1,391 source subjects or repairs.','The 1,005 routing subset is a GEO source-fitness prerequisite with physical_authority=unapproved and dispatch_ready=false.','The 3,666 numeric diagnoses and four Nordic source/Atlas mismatch observations are orthogonal to terminal physical classification.','The global terminal physical labels have only two approved positive IDs; 95,171 remain unresolved under the current #1202 decision checkpoint. No complete global water/land truth roster exists.'],
}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'summary':str(OUT/'summary.json'),'summary_sha256':sha((OUT/'summary.json').read_bytes()),'output':str(OUT),'roster_decoded_sha256':roster_raw_sha,'rows':row_count,'csv_shards':len(roster_parts),'provenance_shards':len(provenance_parts),'sets':intersections,'numeric_classes':dict(num_counts)},indent=2))
