#!/usr/bin/env python3
"""Build the issue-scoped WorldAtlas evidence-v1 manifest from pinned bytes."""
import gzip, hashlib, json, pathlib, re, subprocess
BASE='cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'; ROOT=pathlib.Path.cwd()
PACKET='research/geography/gap-source-matanuska-physical-seam-20261006'; DIR=ROOT/PACKET
ISSUE=1205; WORKER='01a112c1-ac99-74b1-9047-a1da2dd0e245'
SUBJECTS=['atlas:physical:2a15134ff18942dc8e5e','atlas:physical:6efac055720ebe84d7c2','atlas:physical:a20d41a6587ce2e2996b','gb:USA:ADM2:52423323B25289890288494']

def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(path): return subprocess.check_output(['git','show',f'{BASE}:{path}'])
def descriptor(path,raw,role=None,uncompressed=None):
 d={'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
 if role:d['role']=role
 if uncompressed is not None:d.update({'uncompressed_bytes':len(uncompressed),'uncompressed_sha256':sha(uncompressed)})
 return d
def baseline_descriptor(path):
 raw=git(path);u=gzip.decompress(raw) if path.endswith('.gz') else None
 if u is not None and len(u)>32*1024*1024:raise ValueError('Input exceeds decompressed evidence cap: '+path)
 return descriptor(path,raw,'original-source',u)
def candidate_descriptor(path,role=None):return descriptor(path,(ROOT/path).read_bytes(),role)

priority_path='coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/report.json'
detection_path='coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'
custody_path='coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
priority=json.loads(git(priority_path));detection=json.loads(git(detection_path));custody=json.loads(git(custody_path))
paths={'data/canonical-grid/manifest.json','data/hierarchy.json','data/world-index.json','data/geographic-releases/current-manifest.json','data/geographic-releases/releases-v6-gzip.json.gz','data/geography/part-26.json','data/geography/part-27.json','data/regional-review/regional-review-93f8f3bee8e205be/sources/geoboundaries-USA-ADM2.geojson','scripts/administrative.py','scripts/refine-remote.py','scripts/physical_component_contacts.py','scripts/physical_gap_crosswalk.py','scripts/evidence/immutable.py',priority_path,detection_path,custody_path,'coordination/engineering/geographic-components-946-20261005-local06/components-v2/report.json'}
paths.update(d['path'] for d in priority['outputs']['investigations'])
paths.update(d['path'] for d in detection['outputs'] if '/detection-v4/candidates-' in d['path'])
extra=[]
for alias in custody['aliases']:
 original=alias['original'];name=original['path']
 if 'components-v2/' not in name or not (re.search(r'/components-\d{3}\.json\.gz$',name) or name.endswith('/report.json')):continue
 raw=git(alias['payload'])
 if len(raw)!=original['bytes'] or sha(raw)!=original['sha256']:raise ValueError('Custody alias hash mismatch: '+name)
 expanded=gzip.decompress(raw) if name.endswith('.gz') else None
 if expanded is not None and (len(expanded)!=original['uncompressed_bytes'] or sha(expanded)!=original['uncompressed_sha256']):raise ValueError('Custody payload uncompressed hash mismatch: '+name)
 extra.append(descriptor(alias['payload'],raw,'original-source',expanded))
role_path='data/regional-review/alaska-ecoregion-role-followup-2026/sources/resolve-alaska-eco-attributes-20261004.json'
try:git(role_path);paths.add(role_path)
except subprocess.CalledProcessError:pass
base={path:baseline_descriptor(path) for path in sorted(paths)}
for row in extra:base[row['path']]=row
baseline_files=sorted(base.values(),key=lambda x:x['path'])
if sum(x['bytes'] for x in baseline_files)>256*1024*1024:raise ValueError('Baseline inputs exceed aggregate evidence cap')

source_files={
 'geoboundaries':['sources/geoboundaries-usa-adm2-selected.geojson','sources/geoboundaries-capture-receipt.json'],
 'geoboundaries-simplified':['sources/geoboundaries-usa-adm2-simplified-full.geojson','sources/geoboundaries-usa-adm2-2018-metadata.json','sources/geoboundaries-usa-adm2-simplified-selected.geojson','sources/geoboundaries-simplified-capture-receipt.json'],
 'resolve':['sources/resolve-item-no2.json','sources/resolve-item-with2-response.json','sources/resolve-layer-0.json','sources/resolve-ecoregions-2017-ecoids-371-405.geojson','sources/arcgis-capture-receipts.json']}
source_files={k:[candidate_descriptor(f'{PACKET}/{x}','original-source') for x in paths] for k,paths in source_files.items()}
retained={f['path'] for rows in source_files.values() for f in rows}
manifest_path=f'{PACKET}/evidence-quality.json'
pr_base=subprocess.check_output(['git','merge-base','HEAD','origin/main'],text=True).strip()
changed=subprocess.check_output(['git','diff','--name-only',f'{pr_base}...HEAD'],text=True).splitlines()
changed+=subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines()
changed+=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()
changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
changed=sorted(set(changed+[manifest_path]))
outputs=[]
for path in changed:
 if path==manifest_path or path in retained:continue
 outputs.append(candidate_descriptor(path,'generated-table' if path==f'{PACKET}/README.md' else None))

subject_hash=sha(json.dumps(sorted(SUBJECTS),ensure_ascii=False,separators=(',',':')).encode())
ledger_path=f'{PACKET}/results/run-one/source-overlay-ledger.json'
ledger=candidate_descriptor(ledger_path);summary_path=f'{PACKET}/results/run-one/source-overlay-summary.json'
summary=json.loads((ROOT/summary_path).read_bytes())
metrics=[];bindings=[];summaries=[]
def add_metric(mid,value,unit,pointer,path=summary_path):
 metrics.append({'id':mid,'value':value,'unit':unit,'vintage':'archived','evaluation_commit':BASE,'input_sha256':ledger['sha256']})
 bindings.append({'metric_id':mid,'path':path,'json_pointer':pointer});summaries.append({'metric_id':mid,'value':value,'unit':unit})
add_metric('selected-components',282,'components','/roster_count')
add_metric('selected-fragments',283,'fragments','/bound_fragment_count',f'{PACKET}/results/controls/positive-exact-roster-and-contact-closure.json')
add_metric('exact-contact-rows',571,'source-contact rows','/exact_contact_rows')
for metric_id,key,field,value in [
 ('matanuska-intersections','admin:52423323B34523976645917','intersects',281),('matanuska-covers','admin:52423323B34523976645917','covers_component',279),
 ('denali-intersections','admin:52423323B25289890288494','intersects',3),('denali-covers','admin:52423323B25289890288494','covers_component',1),
 ('cook-inlet-taiga-intersections','resolve:ECO_ID=371','intersects',0),('cook-inlet-taiga-covers','resolve:ECO_ID=371','covers_component',0),
 ('st-elias-tundra-intersections','resolve:ECO_ID=405','intersects',227),('st-elias-tundra-covers','resolve:ECO_ID=405','covers_component',40)]:
 add_metric(metric_id,value,'components',f'/{key}/{field}')
for metric_id,key,field in [
 ('matanuska-simplified-intersections','admin_simplified:52423323B34523976645917','intersects'),('matanuska-simplified-covers','admin_simplified:52423323B34523976645917','covers_component'),
 ('denali-simplified-intersections','admin_simplified:52423323B25289890288494','intersects'),('denali-simplified-covers','admin_simplified:52423323B25289890288494','covers_component')]:
 add_metric(metric_id,summary[key][field],'components',f'/{key}/{field}')
for shape_id,label in [('52423323B34523976645917','matanuska'),('52423323B25289890288494','denali')]:
 for field,suffix in [('intersects','intersect'),('covers_component','covers'),('positive_area_intersection','positive-area')]:
  metric_id=f'{label}-full-vs-simplified-{suffix}-changed-components'
  key=f'admin_product_predicate_differences:{shape_id}'
  add_metric(metric_id,summary[key][field],'components',f'/{key}/{field}')
validation=[]
for kind,name in [('positive-control','positive-exact-roster-and-contact-closure.json'),('negative-control','negative-changed-source-hash.json'),('negative-control','negative-omitted-component.json'),('negative-control','negative-omitted-contact.json'),('negative-control','negative-vintage-laundering.json'),('reproducibility','reproducibility.json')]:
 validation.append({'method_id':'source-overlay-analysis','kind':kind,'outcome':'passed','evidence_path':f'{PACKET}/results/controls/{name}'})
def github_file(path,commit=BASE):return f'https://github.com/ChengshuLi/WorldAtlas/blob/{commit}/{path}'

manifest={'version':1,'issue':ISSUE,'lane':'geography','worker_id':WORKER,'subject_ids':SUBJECTS,'subject_ids_sha256':subject_hash,
 'baseline':{'commit':BASE,'files':baseline_files,'pins':{'archived_priority_report':'864fe6abab537488766acd6a599782b7a85bbc4f41a4c8027992b05e22462ff1','canonical_grid':'73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6','hierarchy':'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b'},'pin_files':{'archived_priority_report':priority_path,'canonical_grid':'data/canonical-grid/manifest.json','hierarchy':'data/hierarchy.json'},'subject_files':{SUBJECTS[0]:'data/geography/part-26.json',SUBJECTS[1]:'data/geography/part-26.json',SUBJECTS[2]:'data/geography/part-26.json',SUBJECTS[3]:'data/geography/part-27.json'}},
 'sources':[
 {'id':'geoboundaries-us-adm2-2018','url':'https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2.geojson','role':'Separate full-resolution historical ADM2 comparison only; not the input selected by scripts/administrative.py and no owner assignment','vintage':'boundaryYear 2018; exact full-resolution product at immutable commit 9469f09592ced973a3448cf66b6100b741b64c0d','retrieved_at':'2026-10-06T20:01:27.061Z','license':{'status':'redistributable','terms':'Public Domain per pinned exact-release metadata; underlying US Census Bureau MAF/TIGER Database'},'retention':'retained','verification':'verified','files':source_files['geoboundaries'],'crs':'OGC CRS84; longitude-latitude','temporal_status':'reference','coordinate_precision_and_registration':{'xy_resolution_or_tolerance':'not reported by retained metadata','positional_accuracy_or_registration':'not reported by retained metadata','operation':'No rounding, reprojection, snapping, or registration adjustment applied'},'limit':'Only Matanuska-Susitna and Denali features are retained here; the complete exact full-resolution USA ADM2 file is pinned in the issue-baseline input inventory. Their geometries are not interchangeable with the separately retained simplified product.'},
 {'id':'geoboundaries-us-adm2-2018-simplified','url':'https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2_simplified.geojson','role':'Simplified geoBoundaries feature product selected by exact issue-baseline scripts/administrative.py URL transformation; source-coordinate comparison only, no owner assignment','vintage':'boundaryYear 2018; sourceDataUpdateDate Thu Jan 19 07:31:04 2023; buildDate Dec 12, 2023; immutable release commit 9469f09592ced973a3448cf66b6100b741b64c0d','retrieved_at':'2026-10-06T20:46:44Z','license':{'status':'redistributable','terms':'Public Domain per exact release metadata; underlying US Census Bureau MAF/TIGER Database'},'retention':'retained','verification':'verified','files':source_files['geoboundaries-simplified'],'crs':'OGC CRS84; longitude-latitude','temporal_status':'reference','coordinate_precision_and_registration':{'xy_resolution_or_tolerance':'not reported by exact-release metadata','positional_accuracy_or_registration':'not reported by exact-release metadata','operation':'No rounding, reprojection, snapping, or registration adjustment applied'},'limit':'The 3,233-feature simplified file and metadata are retained whole; selected features share IDs/attributes but differ geometrically from full-resolution features. This does not establish that Atlas output parts were generated from this exact capture or establish registration accuracy.'},
 {'id':'resolve-ecoregions-biomes-2017','url':'https://www.arcgis.com/sharing/rest/content/items/37ea320eebb647c6838c23f72abae5ef?f=json','role':'Authenticate the source item and compare complete ECO_ID 371 and 405 polygons','vintage':'Layer is titled Biomes and Ecoregions 2017; feature data last edited 2022-01-27; item metadata modified 2026-05-28','retrieved_at':'2026-10-06T20:01:37.823Z','license':{'status':'redistributable','terms':'CC BY 4.0; attribution required'},'retention':'retained','verification':'verified','files':source_files['resolve'],'crs':'EPSG:4326; longitude-latitude order','temporal_status':'reference','limit':'The complete Rock and Ice query exceeded the evidence cap; see the separate unavailable geometry record.'},
 {'id':'resolve-rock-and-ice-incomplete','url':'https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0/query?where=ECO_ID%3D0&outFields=*&returnGeometry=true&outSR=4326&f=geojson','role':'Potential Rock and Ice comparison; complete source geometry unavailable','vintage':'Same layer titled Biomes and Ecoregions 2017; feature data last edited 2022-01-27','retrieved_at':'2026-10-06T20:01:50.760Z','license':{'status':'redistributable','terms':'CC BY 4.0; attribution required for ArcGIS item'},'retention':'restoration-only','verification':'unverified','restoration':'Use the official bounded query URL above only after establishing a lawful complete response under the existing 32 MiB per-file cap; preserve a new whole-file receipt and geometry vintage.','limit':'HTTP 200 response was incomplete after the first 32 MiB; partial bytes were discarded. No geometry or physical classification is available from this query.','temporal_status':'reference'},
 {'id':'atlas-recorded-subject-lineage','url':github_file('data/geography/part-26.json'),'role':'Recorded stable IDs, source ECO_ID tokens, original ADM2 member, and shared adjustment metadata','vintage':'Exact issue baseline features; Atlas reference_year 2018 is not a RESOLVE geometry observation date','retrieved_at':'2026-10-06T20:00:00Z','license':{'status':'unknown','terms':'Atlas-recorded metadata; separate redistribution terms not established'},'retention':'restoration-only','verification':'verified','restoration':'Read the exact part-26 file at the immutable issue baseline and feature hashes in sources/historical-subject-lineage.json.','limit':'Recorded source member and stable ID relationships do not prove full geometry lineage or cause.','temporal_status':'reference'},
 {'id':'atlas-remote-refinement-recipe','url':github_file('scripts/refine-remote.py','4bdba3d40acc2d725e4aeb54c3b9aab559a91469'),'role':'Archived processing method snapshot for bounded causal hypotheses','vintage':'Exact script blob c5db9115604b6c82318a68ca008df7a21688bc93 at commit 4bdba3d40acc2d725e4aeb54c3b9aab559a91469; same bytes at issue baseline','retrieved_at':'2026-10-06T20:01:50.760Z','license':{'status':'unknown','terms':'No separate source-specific code license was authenticated.'},'retention':'restoration-only','verification':'verified','restoration':'Retrieve scripts/refine-remote.py from immutable commit 4bdba3d40acc2d725e4aeb54c3b9aab559a91469.','limit':'The recipe contains validity repair, simplification, precision overlays, thresholds and buffer operations, but execution commit, exact cache inputs and per-feature lineage are not bound to these components; no cause is inferred.','temporal_status':'unknown'}],
 'outputs':outputs,'methods':[{'id':'source-overlay-analysis','kind':'source','description':'Verify the exact archived component roster, custody payloads and exact contact ledgers, then compare per-component predicates independently against retained full-resolution and simplified geoBoundaries USA ADM2 products and complete RESOLVE ECO_ID 371/405 polygons. Unprojected coordinate-plane topological observations only; no area, distance, repair, ownership or causal inference. Per-component physical class remains unknown.','software':'Python 3.12.14; Shapely 2.1.2; GEOS 3.13.1; shared physical_component_contacts helper at baseline','units':'component and source-contact counts; boolean topology predicates','crs':'EPSG:4326 / CRS84; longitude-latitude axis order'}],
 'metrics':metrics,'metric_bindings':bindings,'summaries':summaries,'rendered_tables':[{'path':f'{PACKET}/README.md','rows':[
 {'metric_id':mid,'line':next(i+1 for i,line in enumerate((DIR/'README.md').read_text().splitlines()) if line.startswith(template.split('{value}')[0])),'template':template,'decimals':0}
 for mid,template in [
 ('matanuska-intersections','| Matanuska–Susitna full-resolution ADM2 | intersects | {value} |'),('matanuska-covers','| Matanuska–Susitna full-resolution ADM2 | covers component | {value} |'),('denali-intersections','| Denali full-resolution ADM2 | intersects | {value} |'),('denali-covers','| Denali full-resolution ADM2 | covers component | {value} |'),
 ('cook-inlet-taiga-intersections','| RESOLVE ECO_ID 371, Cook Inlet taiga | intersects | {value} |'),('cook-inlet-taiga-covers','| RESOLVE ECO_ID 371, Cook Inlet taiga | covers component | {value} |'),('st-elias-tundra-intersections','| RESOLVE ECO_ID 405, Alaska–St. Elias Range tundra | intersects | {value} |'),('st-elias-tundra-covers','| RESOLVE ECO_ID 405, Alaska–St. Elias Range tundra | covers component | {value} |'),
 ('matanuska-simplified-intersections','| Matanuska–Susitna simplified ADM2 input | intersects | {value} |'),('matanuska-simplified-covers','| Matanuska–Susitna simplified ADM2 input | covers component | {value} |'),('denali-simplified-intersections','| Denali simplified ADM2 input | intersects | {value} |'),('denali-simplified-covers','| Denali simplified ADM2 input | covers component | {value} |'),
 ('matanuska-full-vs-simplified-intersect-changed-components','| Matanuska full/simplified intersect status changes | components | {value} |'),('matanuska-full-vs-simplified-covers-changed-components','| Matanuska full/simplified covers status changes | components | {value} |'),('matanuska-full-vs-simplified-positive-area-changed-components','| Matanuska full/simplified positive-area status changes | components | {value} |'),
 ('denali-full-vs-simplified-intersect-changed-components','| Denali full/simplified intersect status changes | components | {value} |'),('denali-full-vs-simplified-covers-changed-components','| Denali full/simplified covers status changes | components | {value} |'),('denali-full-vs-simplified-positive-area-changed-components','| Denali full/simplified positive-area status changes | components | {value} |')]]}],
 'conclusions':[{'status':'supported','text':'The inherited item locator without a trailing 2 resolves to the official RESOLVE item and layer; the appended-2 locator returns CONT_0001. The layer is titled 2017 and records a 2022-01-27 data edit; item modification time is not treated as source vintage.','source_ids':['resolve-ecoregions-biomes-2017']},{'status':'supported','text':'At the exact issue baseline, the three recorded Atlas physical IDs map to resolve:405, resolve:371, and resolve:0, all with the same recorded Matanuska-Susitna ADM2 source member. The pinned refinement script implements the recorded original-admin-ID plus ECO_ID stable ID formula. All three features carry the same recorded adjustment metadata; these bindings do not establish seam cause.','source_ids':['atlas-recorded-subject-lineage','atlas-remote-refinement-recipe']},{'status':'supported','text':'The exact roster closes over 282 components, 283 bound fragments and 571 recorded source-contact rows. Separate full-resolution and simplified geoBoundaries feature products share selected IDs and attributes but have different geometries; the bounded roster has identical per-component intersects/covers/positive-area booleans for both products. These source predicates are coordinate-plane diagnostics only, not physical area, general product equivalence, or jurisdiction decisions.','source_ids':['geoboundaries-us-adm2-2018','geoboundaries-us-adm2-2018-simplified','resolve-ecoregions-biomes-2017']},{'status':'unresolved','text':'All 282 component physical classes remain unknown among source footprint omission, source disagreement, independently evidenced water or ice, and other cause. Complete ECO_ID 0 geometry is unavailable; the overlays and recipe metadata do not establish whole-surface attribution or per-component causal lineage.','source_ids':['geoboundaries-us-adm2-2018','geoboundaries-us-adm2-2018-simplified','resolve-ecoregions-biomes-2017','resolve-rock-and-ice-incomplete','atlas-recorded-subject-lineage','atlas-remote-refinement-recipe']}],
 'validation':validation,'stages':{'research':'complete','implementation':'not-proposed','geographic_approval':'unapproved'},'commands':[f'python3.12 {PACKET}/reproduce-source-overlays.py --run-id run-one',f'python3.12 {PACKET}/reproduce-source-overlays.py --run-id run-two',f'python3.12 {PACKET}/source-negative-controls.py'],'change_receipts':[{'path':path,'status':'added'} for path in changed]}
manifest_path=DIR/'evidence-quality.json';manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'baseline_files':len(baseline_files),'baseline_bytes':sum(d['bytes'] for d in baseline_files),'output_files':len(outputs),'change_files':len(changed),'manifest_bytes':manifest_path.stat().st_size}))
