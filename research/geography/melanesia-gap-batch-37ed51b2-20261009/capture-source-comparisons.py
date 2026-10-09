#!/usr/bin/env python3
"""Reconcile retained original source-comparison rows to the complete 363-ID batch."""
import datetime,gzip,hashlib,json,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OWNED='research/geography/melanesia-gap-batch-37ed51b2-20261009/';RUN='source-comparison-capture-001'
PINPATH=ROOT/OWNED/'source-comparison-capture-pins.json'
if (ROOT/OWNED/'vintages'/RUN).exists():raise SystemExit('refusing existing vintage')
pins=json.loads(PINPATH.read_text());commit=pins['baseline_commit'];helper='scripts/evidence/immutable.py';hrow=next(x for x in pins['files']if x['path']==helper);hb=subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+helper]);assert len(hb)==hrow['bytes'] and hashlib.sha256(hb).hexdigest()==hrow['sha256']
ns={'__name__':'pinned_evidence','__file__':str(ROOT/helper)};exec(compile(hb,str(ROOT/helper),'exec'),ns)
Baseline=ns['Baseline'];NewVintage=ns['NewVintage'];canon=ns['canonical_json'];baseline=Baseline(ROOT,commit,pins['files']);assert baseline.pinned_bytes(helper)==hb
started=time.monotonic();index={x['path']:x for x in pins['files']};decoded_pins=[x for x in pins['files']if x['path'].endswith('.json.gz')]
for x in decoded_pins:baseline.admit(x['path']+':decoded',x['decoded_bytes'])
def load(path):
 raw=baseline.pinned_bytes(path);return json.loads(gzip.decompress(raw)if raw[:2]==b'\x1f\x8b'else raw)
def digest(v):return hashlib.sha256(canon(v)).hexdigest()
def file_sha(raw):return hashlib.sha256(raw).hexdigest()
capture_path=pins['candidate_capture_path'];capture_bytes=baseline.pinned_bytes(capture_path);capture=json.loads(capture_bytes)
pub_path=next(x['path']for x in pins['files']if x['path'].endswith('/candidate-capture-001/publication.json'));pub=load(pub_path);assert pub['status']=='complete'
pubrow=next(x for x in pub['outputs']if x['path']==capture_path);assert pubrow['bytes']==len(capture_bytes)and pubrow['sha256']==file_sha(capture_bytes)
assert capture['batch_id']=='gap-operational-batch:37ed51b2c2eac38570c40a87'
features={x['component_id']:x for x in capture['candidate_records']};assert len(features)==363
catalog={}
for path in pins['catalog_subset_paths']:
 for item in load(path)['catalog_snapshot_rows']:
  assert item['component_id']not in catalog;catalog[item['component_id']]=item['catalog_row']
assert set(catalog)==set(features)
comparisons={};scanned=0
for path in pins['comparison_shards']:
 for row in load(path):
  scanned+=1;i=row.get('component')
  if i in features:
   assert i not in comparisons
   captured=features[i]
   assert row['component_geometry_sha256']==captured['component_geometry_sha256'],i
   assert catalog[i]['source_evidence']['source_comparison_status']==row['status'],i
   comparisons[i]=row
assert len(comparisons)==276
joined=[];summary={}
for i in sorted(features):
 cat=catalog[i];row=comparisons.get(i);subject_ids=set();positive_features=[]
 if row:
  for hit in row.get('feature_intersections',[]):
   inter=hit['intersection']
   if not inter['is_empty'] and inter.get('planar_area_coordinate_units_squared',0)>0:
    binding=hit['binding'];subjects=binding.get('recorded_stable_subjects',[])
    positive_features.append({'source_id':binding['source_id'],'feature_index':binding['feature_index'],'shapeID':binding['shapeID'],'feature_sha256':binding['feature_sha256'],'geometry_sha256':binding['geometry_sha256'],'positive_area_deg2':inter['planar_area_coordinate_units_squared'],'recorded_stable_subjects':subjects,'intersection_geometry':inter['geometry']})
    subject_ids.update(s['id'] for s in subjects)
  complete=row['component_minus_source_union']['is_empty']
  source_subjects=sorted(subject_ids)
  if cat['source_evidence']['physical_status_source_relative']=='mapped-land-support' and len(source_subjects)==1 and positive_features:
   disposition='native-grid-source-payload'
  elif cat['source_evidence']['physical_status_source_relative']=='mapped-land-support' and len(source_subjects)>1:
   disposition='ambiguous-multiple-recorded-subjects'
  elif cat['source_evidence']['physical_status_source_relative']=='mapped-land-support' and not positive_features:
   disposition='no-positive-area-recorded-source-subject'
  elif cat['source_evidence']['physical_status_source_relative']=='mapped-land-support':
   disposition='source-fit-incomplete-binding'
  else:disposition='retained-routing-only-not-land-supported'
 else:
  complete=None;source_subjects=[]
  disposition='targeted-source-match-needed' if cat['source_evidence']['physical_status_source_relative']=='mapped-land-support' else 'not-in-retained-source-comparison-cohort'
 row_summary={'component_id':i,'candidate_feature_sha256':features[i]['component_feature_sha256'],'candidate_geometry_sha256':features[i]['component_geometry_sha256'],'source_product_codes':cat['source_evidence']['source_products'],'prior_physical_support':cat['source_evidence']['physical_status_source_relative'],'prior_pipeline_state':cat['pipeline_status']['state'],'original_next_prerequisite':cat['source_evidence']['next_prerequisite'],'source_comparison_status':row['status']if row else 'not-in-57,785-source-comparison-cohort','source_coverage_complete_in_prior_comparison':complete,'positive_area_recorded_source_subject_ids':source_subjects,'positive_area_source_feature_intersections':positive_features,'disposition':disposition,'source_comparison_record':row}
 joined.append(row_summary);summary[disposition]=summary.get(disposition,0)+1
result={'schema':'melanesia-complete-source-comparison-join/v1','batch_id':capture['batch_id'],'candidate_count':len(joined),'matched_source_comparison_rows':len(comparisons),'source_comparison_rows_scanned':scanned,'catalog_rows_joined':len(catalog),'source_comparison_source_commits':[commit],'input_pins':[{'path':x['path'],'bytes':x['bytes'],'sha256':x['sha256']}for x in pins['files']],'disposition_counts':summary,'cases':joined,'limits':['prior source-comparison geometries and classifications are reused; no source overlay is recomputed in this capture phase','source-comparison cohort absence is a missing retained comparison, not proof of no source overlap','source years are represented dates, not effective dates or legal authority','a native-grid payload requires later current-owner testing and must preserve all existing assignments']}
script=Path(__file__).read_bytes();execution={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.executable+' '+str(Path(__file__).relative_to(ROOT)),'baseline_commit':commit,'script':{'path':str(Path(__file__).relative_to(ROOT)),'bytes':len(script),'sha256':file_sha(script)},'python':platform.python_version(),'helper':'pinned Baseline + exclusive NewVintage','admitted_input_bytes':sum(baseline.consumed.values()),'elapsed_seconds':time.monotonic()-started}
values={'batch-source-comparisons.json':canon(result),'execution.json':canon(execution),'capture-source-comparisons.py':script,'source-comparison-capture-pins.json':PINPATH.read_bytes()}
NewVintage(baseline,OWNED,RUN,list(values)).publish_bytes(values)
print(json.dumps({'status':'published','candidates':len(joined),'comparison_rows':len(comparisons),'dispositions':summary,'admitted_input_bytes':sum(baseline.consumed.values())}))
