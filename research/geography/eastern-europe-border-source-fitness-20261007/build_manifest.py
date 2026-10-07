#!/usr/bin/env python3
"""Construct the evidence-v1 manifest and exact metric bindings for issue #1344."""
import hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
BASE='432c5b8e0ac9b9597738a31f5386569312c75966'
ISSUE=1344
WORKER='01a112b9-e2b7-7d03-8000-eb2890649612'
SUBJECTS=[
'gb:BLR:ADM2:67162791B30498032594927',
'gb:POL:ADM2:97123803B24100086136213',
'gb:POL:ADM2:97123803B33088815311851',
'gb:POL:ADM2:97123803B66371363243422',
'gb:UKR:ADM2:74538382B51634820959847',
'gb:UKR:ADM2:74538382B5714887404176',
'gb:UKR:ADM2:74538382B72123275564902',
'gb:UKR:ADM2:74538382B9478118461291',
'gb:UKR:ADM2:74538382B97249439308301']
PACKET=ROOT.relative_to(REPO).as_posix()
def sha(b): return hashlib.sha256(b).hexdigest()
def descriptor(path, role=None, root=REPO):
 p=Path(root)/path; b=p.read_bytes(); x={'path':Path(path).as_posix(),'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'}
 if role: x['role']=role
 return x
def baseline_descriptor(path, role='baseline-reference'):
 b=subprocess.run(['git','show',f'{BASE}:{path}'],cwd=REPO,check=True,stdout=subprocess.PIPE).stdout
 mode=subprocess.run(['git','ls-tree',BASE,'--',path],cwd=REPO,check=True,text=True,stdout=subprocess.PIPE).stdout.split()[0]
 if mode not in ('100644','100755'): raise ValueError(f'Not an ordinary baseline file: {path} {mode}')
 return {'path':path,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes','role':role,'git_mode':mode}
def inside(path): return f'{PACKET}/{path}'
def loadj(path): return json.loads((ROOT/path).read_text())
custody=loadj('inputs/source-custody.json')
fitness=loadj('runs/run-one/source-fitness.json')
run_summary=loadj('history/two-run-summary.json')
cat=loadj('inputs/baseline/source-corpus-catalogue.json')
existing_manifest=loadj('evidence-quality.json') if (ROOT/'evidence-quality.json').exists() else {}
# Exact baseline files are referenced as immutable Git paths; staged copies are independently listed as outputs.
baseline_files=[]; seen=set()
for rec in custody['files']:
 origin=rec['origin_path']
 if rec.get('transport_path'):
  item={'path':origin,'bytes':rec['transport_bytes'],'sha256':rec['transport_sha256'],'hash_kind':'file-bytes','role':'original-source','git_mode':rec['origin_mode'],'git_blob_oid':rec['origin_blob_oid']}
 else:
  role='original-source' if any(t in origin for t in ('data/geography/','data/administrative-sources','candidates-012','components-022','families-005','batches-001','admin-bindings-007','components-062','diagnoses-027','natural-earth-lakes','source-corpus')) else 'baseline-reference'
  item=baseline_descriptor(origin,role)
 if item['path'] not in seen: baseline_files.append(item);seen.add(item['path'])
# Contract pins are all explicit issue-level pins, with each hash tied to the actual immutable source path.
pins={
'audited_world_index':'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
'delivered_numeric_report':'e47379a74c053b57781fec04aaedc702ecba24adb773b42bb8c75d142326647a',
'delivered_routing_input_config':'7623fa8a61b72c33a1560f0ab612e70c463e8c25beef930043c985fd6657f173',
'delivered_routing_report':'2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265',
'whole_source_transport_gb_BLR_ADM2_0':'308fe6563c7735f625ee11b725a67dda2b729b3c1e1d72034a28edc4e06a120e',
'whole_source_transport_gb_POL_ADM2_0':'d6ddf97bcf615136b4be684ca630f4eb12eb675f0dd054e409efa492054ff24f',
'whole_source_transport_gb_UKR_ADM2_0':'35cef639ce0928d52a51699b0183d5369ba725befec9de43415e8b51664405b9',
'scoped_contact_part_0':'93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf',
'scoped_contact_part_1':'baeade0e3ad11cdd65beb101e7b79284ae2b6ee8794f9b08e86631c7f20e6269',
'scoped_contact_part_2':'dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394'}
pin_files={
'audited_world_index':'data/world-index.json',
'delivered_numeric_report':'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r1/report.json',
'delivered_routing_input_config':'coordination/engineering/global-actionability-routing-20261007/input-config.json',
'delivered_routing_report':'coordination/engineering/global-actionability-routing-20261007/results/report.json',
'whole_source_transport_gb_BLR_ADM2_0':'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-BLR-ADM2-000.bin.gz',
'whole_source_transport_gb_POL_ADM2_0':'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-POL-ADM2-000.bin.gz',
'whole_source_transport_gb_UKR_ADM2_0':'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-UKR-ADM2-000.bin.gz',
'scoped_contact_part_0':'data/geography/part-2.json','scoped_contact_part_1':'data/geography/part-19.json','scoped_contact_part_2':'data/geography/part-25.json'}
for path in pin_files.values():
 if path not in seen: baseline_files.append(baseline_descriptor(path,'original-source' if path.startswith(('data/geography/','coordination/engineering/')) else 'baseline-reference'));seen.add(path)
# Issue-scoped outputs: all packet bytes except the manifest itself and four/five source files claimed below.
source_paths={
inside('inputs/source-products/geoBoundaries-BLR-ADM2_simplified.geojson'),
inside('inputs/source-products/geoBoundaries-POL-ADM2_simplified.geojson'),
inside('inputs/source-products/geoBoundaries-UKR-ADM2_simplified.geojson'),
inside('inputs/source-products/natural-earth-10m-lakes.geojson'),
inside('inputs/source-transports/gb-BLR-ADM2-000.bin.gz'),
inside('inputs/source-transports/gb-POL-ADM2-000.bin.gz'),
inside('inputs/source-transports/gb-UKR-ADM2-000.bin.gz'),
inside('inputs/baseline/lakes-source.gz')}
outputs=[]
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or p.name=='evidence-quality.json' or p.name=='reproducibility.json' or '__pycache__' in p.parts or p.suffix=='.pyc': continue
 path=p.relative_to(REPO).as_posix()
 if path not in source_paths:
  role='generated-result'
  if p.suffix=='.py': role='reproduction-code'
  elif p.name=='README.md': role='research-summary'
  elif path.endswith('/inputs/source-custody.json'): role='source-custody-index'
  elif '/inputs/baseline/' in path: role='baseline-custody-copy'
  elif '/history/' in path: role='preserved-run-history'
  outputs.append(descriptor(path,role))
def sf(path): return descriptor(inside(path),root=REPO)
source_files={
'blr': [sf('inputs/source-products/geoBoundaries-BLR-ADM2_simplified.geojson'),sf('inputs/source-transports/gb-BLR-ADM2-000.bin.gz')],
'pol': [sf('inputs/source-products/geoBoundaries-POL-ADM2_simplified.geojson'),sf('inputs/source-transports/gb-POL-ADM2-000.bin.gz')],
'ukr': [sf('inputs/source-products/geoBoundaries-UKR-ADM2_simplified.geojson'),sf('inputs/source-transports/gb-UKR-ADM2-000.bin.gz')],
'ne': [sf('inputs/source-products/natural-earth-10m-lakes.geojson'),sf('inputs/baseline/lakes-source.gz')]}
products={}
for c,source_id in [('BLR','geoboundaries-blr-adm2-simplified'),('POL','geoboundaries-pol-adm2-simplified'),('UKR','geoboundaries-ukr-adm2-simplified')]:
 row=next(x for x in cat['products'] if x['key']==f'gb:{c}:ADM2')
 products[c]={'id':source_id,'url':row['recorded_consumed_url'],'role':f'Complete original consumed geoBoundaries gbOpen ADM2 simplified product; 100% full product and all features retained.','vintage':f"Upstream geoBoundaries tree 9469f09; source-represented year claim {row['source_represented_year_claim']}; no effective date inferred.",'retrieved_at':'2026-10-06 frozen source-corpus custody; exact member-level retrieval time unavailable in the retained per-product record.','license':{'status':'redistributable','terms':f"Recorded product license: {row['recorded_license']}; retained geoBoundaries attribution/use statement and source-corpus catalogue. Underlying source attribution, legal interpretation, authority and effective applicability remain unverified."},'retention':'retained','verification':'unverified','temporal_status':'unknown','restoration':f"Reassembled from the exact compressed ordinary Git blob in original-geography-source-corpus-20261006; source-custody binds its mode, blob OID, compressed bytes/hash, and decoded whole-file bytes/hash.",'limit':'Represented year/license/source fields are metadata claims; no per-feature positional accuracy, transformation error, current effective date, national legal border, or complete source lineage is established.','files':source_files[c.lower()]}
sources=[products[c] for c in ('BLR','POL','UKR')]
receipt=loadj('inputs/baseline/lakes-receipt.json')
sources.append({'id':'natural-earth-10m-lakes','url':receipt['url'],'role':'Independent modern major-lake context; not a complete hydrology or border authority source.','vintage':receipt['vintage'],'retrieved_at':receipt['retrieved_at'],'license':{'status':'redistributable','terms':'Public domain per retained receipt.'},'retention':'retained','verification':'unverified','temporal_status':'reference','restoration':'Verified full raw GeoJSON against whole-source hash and byte count; compressed original retained with its baseline custody record.','limit':'Major lakes/reservoirs only; no complete rivers/small water or time-specific wetness. No hit cannot establish dry land. Two unrelated invalid feature geometries were not repaired and have bbox disjoint from candidate.','files':source_files['ne']})
sources.append({'id':'gshhg-physical-context','url':'https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip','role':'Previously delivered GSHHG 2.3.7 source-relative physical context; only existing component-level outputs reused.','vintage':'Distributed 2.3.7, 2017-06-15; underlying observation dates unresolved.','retrieved_at':'Reused unchanged from the pinned original physical comparison packet; its acquisition record is in the retained baseline physical manifest.','license':{'status':'unknown','terms':'Original term files conflict on version wording; no resolution is inferred for this reuse.'},'retention':'restoration-only','verification':'unverified','temporal_status':'unknown','restoration':'See exact pinned physical comparison manifest/input configuration in baseline descriptors; this packet reuses one component row and does not recopy or rerun the global source.','limit':'Not a legal boundary or complete/candidate-scale physical truth; shoreline registration, missing/narrow channels, resolution, observation dates and authority remain unresolved.'})
# baseline pins and explicit source/contact-containing file map
subject_files={}
for sid in SUBJECTS:
 country=sid.split(':')[1]
 subject_files[sid]={'BLR':'data/geography/part-2.json','POL':'data/geography/part-19.json','UKR':'data/geography/part-25.json'}[country]
# Candidate output descriptors are declared above; source files are declared in their source entries.
fit_path=inside('runs/run-one/source-fitness.json')
ledger=[]; bindings=[]
def metric(mid,value,unit,input_sha,pointer,numerator=None,denominator=None):
 row={'id':mid,'value':value,'unit':unit,'input_sha256':input_sha,'evaluation_commit':BASE,'vintage':'baseline'}
 if numerator is not None: row.update({'numerator':numerator,'denominator':denominator})
 ledger.append(row);bindings.append({'metric_id':mid,'path':fit_path,'json_pointer':pointer})
fit=fitness; candidate_input=next(r['sha256'] for r in custody['files'] if r['path']=='inputs/baseline/candidate-source.gz')
metric('candidate-area-helper',fit['scope']['candidate_area_wgs84_helper_m2'],'m2',candidate_input,'/scope/candidate_area_wgs84_helper_m2')
metric('candidate-area-declared',fit['scope']['candidate_area_declared_m2'],'m2',candidate_input,'/scope/candidate_area_declared_m2')
metric('candidate-contact-count',fit['scope']['contact_count'],'contacts',candidate_input,'/scope/contact_count')
for c in ('BLR','POL','UKR'):
 srcsha=products[c]['files'][0]['sha256']
 row=fit['country_overlays'][c]; base=f'/country_overlays/{c}/'
 for name,key,unit in [('source-feature-count','complete_source_features_scanned','features'),('intersecting-feature-count','candidate_intersecting_features','features'),('positive-area-feature-count','positive_area_intersection_features','features'),('coverage-area','dissolved_country_coverage_area_m2','m2'),('coverage-fraction','dissolved_country_candidate_coverage_fraction','fraction')]:
  num=key=='dissolved_country_candidate_coverage_fraction'
  metric(f'{c.lower()}-{name}',row[key],unit,srcsha,base+key,row['dissolved_country_coverage_area_m2'] if num else None,fit['scope']['candidate_area_wgs84_helper_m2'] if num else None)
union=fit['all_three_country_products_union']; union_input=candidate_input
metric('three-source-union-coverage-area',union['positive_area_m2'],'m2',union_input,'/all_three_country_products_union/positive_area_m2')
metric('three-source-union-coverage-fraction',union['candidate_coverage_fraction'],'fraction',union_input,'/all_three_country_products_union/candidate_coverage_fraction',union['positive_area_m2'],fit['scope']['candidate_area_wgs84_helper_m2'])
metric('simplified-source-feature-count',sum(x['feature_count'] for x in fit['source_product_assessments'].values()),'features',candidate_input,'/scope/contact_count')
# The source-feature total is also deterministically reported as three individual counts; bind aggregate below to one declared numeric value.
ledger.pop(); bindings.pop()
contacts=fit['current_atlas_contact_source_comparisons']
for i,row in enumerate(contacts):
 c=row['country']; metric(f'contact-symdiff-{i+1}',row['sym_difference_area_m2'],'m2',products[c]['files'][0]['sha256'],f'/current_atlas_contact_source_comparisons/{i}/sym_difference_area_m2')
ne=fit['independent_physical_reference']; nesha=source_files['ne'][0]['sha256']
metric('natural-earth-feature-count',ne['feature_count'],'features',nesha,'/independent_physical_reference/feature_count')
metric('natural-earth-candidate-hit-count',ne['candidate_intersecting_feature_count'],'features',nesha,'/independent_physical_reference/candidate_intersecting_feature_count')
manifest={
'version':1,'issue':ISSUE,'lane':'geography','worker_id':WORKER,'subject_ids':SUBJECTS,'subject_ids_sha256':sha(json.dumps(sorted(SUBJECTS),separators=(',',':')).encode()),
'baseline':{'commit':BASE,'files':baseline_files,'pins':pins,'pin_files':pin_files,'subject_files':subject_files},
'sources':sources,'outputs':outputs,
'methods':[{'id':'complete-source-overlay','kind':'geography','description':'Bounded full-feature overlay for one authenticated candidate, all nine Atlas contact features, the complete three-country simplified ADM2 source products and the complete pinned Natural Earth major-lake product. No global producer rerun, repair, clipping or inferred administrative/physical assignment.','software':'Python 3.12.14; NumPy 2.3.5; PyProj 3.7.2; Shapely 2.1.2; GEOS 3.13.1; shared immutable helper source snapshots from baseline; exact imports/producer retained.','units':'m² WGS84 ellipsoidal source-edge area; feature counts; fractions of candidate area.','helper_version':'worldatlas-evidence-geometry-v1','axis_order':'longitude-latitude','crs':'EPSG:4326','area_method':'WGS84 straight-source-edge ellipsoidal integral','distance_method':'WGS84 inverse geodesic'},
{'id':'original-source-custody','kind':'source','description':'Reassemble and verify exact source-corpus compressed Git parts and complete decoded products against original corpus catalogue, custody manifests and Atlas source registry. Recorded dates/licenses are treated as claims.','software':'Python 3.12.14; hashlib; Python json/gzip; Git 2.50.1','units':'bytes, SHA-256, Git blob OID/mode, decoded feature counts.'}],
'metrics':ledger,'metric_bindings':bindings,
'summaries':[],
'conclusions':[
{'status':'supported','source_ids':['geoboundaries-blr-adm2-simplified','geoboundaries-pol-adm2-simplified','geoboundaries-ukr-adm2-simplified'],'text':'The three complete retained simplified ADM2 product bytes and feature inventories match the pinned original source-corpus records and the immutable Atlas registry; the represented-year and license values remain recorded source claims.'},
{'status':'supported','source_ids':['geoboundaries-blr-adm2-simplified','geoboundaries-pol-adm2-simplified','geoboundaries-ukr-adm2-simplified'],'text':'Each of the nine exact Atlas contact IDs joins uniquely by shapeID to a matching complete simplified source feature; all nine current geometries are topologically unequal to those features. Current Atlas metadata URL references unsimplified GeoJSON while the baseline acquisition code consumes the simplified URL; timing and cause remain unknown.'},
{'status':'supported','source_ids':['natural-earth-10m-lakes'],'text':'The retained Natural Earth major-lakes product has no valid candidate-intersecting feature; this is not evidence that the candidate is dry land.'},
{'status':'unresolved','source_ids':['geoboundaries-blr-adm2-simplified','geoboundaries-pol-adm2-simplified','geoboundaries-ukr-adm2-simplified','natural-earth-10m-lakes','gshhg-physical-context'],'text':'The complete candidate cause, partition, present physical status, legal boundary, historical ownership, effective dates, positional accuracy, source lineage and any permitted engineering or publication action remain unknown. Candidate-scale authoritative national boundary and suitable dated hydrography evidence are still required.'}],
'stages':{'research':'complete','implementation':'not-proposed','geographic_approval':'unapproved'},
'commands':['python3 research/geography/eastern-europe-border-source-fitness-20261007/stage_inputs.py','python3 research/geography/eastern-europe-border-source-fitness-20261007/execute.py','python3 research/geography/eastern-europe-border-source-fitness-20261007/control-checks.py','node scripts/evidence-quality.mjs research/geography/eastern-europe-border-source-fitness-20261007/evidence-quality.json'],
'validation':[{'method_id':'complete-source-overlay','kind':'positive-control','outcome':'passed','evidence_path':inside('controls/positive-control.json')},{'method_id':'complete-source-overlay','kind':'negative-control','outcome':'passed','evidence_path':inside('controls/negative-control.json')},{'method_id':'complete-source-overlay','kind':'reproducibility','outcome':'passed','evidence_path':inside('controls/reproducibility.json')}],
'change_receipts':existing_manifest.get('change_receipts',[])}
# Reproducibility receipt bound to the two equal full-output hashes.
hashes=run_summary['run_output_hashes']
r1=sha(json.dumps(hashes[0],sort_keys=True,separators=(',',':')).encode());r2=sha(json.dumps(hashes[1],sort_keys=True,separators=(',',':')).encode())
(ROOT/'controls/reproducibility.json').write_text(json.dumps({'method_id':'complete-source-overlay','kind':'reproducibility','outcome':'passed','run_one_sha256':r1,'run_two_sha256':r2,'run_one_outputs':hashes[0],'run_two_outputs':hashes[1]},sort_keys=True,indent=2)+'\n')
# Add a descriptor for the reproducibility receipt before writing manifest.
outputs.append(descriptor(inside('controls/reproducibility.json')))
(ROOT/'evidence-quality.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':'built','baseline_files':len(baseline_files),'sources':len(sources),'outputs':len(outputs),'metrics':len(ledger),'subject_ids':len(SUBJECTS),'manifest':inside('evidence-quality.json')},sort_keys=True))
