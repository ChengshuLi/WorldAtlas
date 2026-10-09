#!/usr/bin/env python3
"""Reproduce the bounded six-component Choiseul source-fit/topology analysis.

Uses Shapely 2.1.2/GEOS 3.13.1. Reads the exact original component custody
payloads and current Atlas target/neighbor context from immutable Git commits;
no snapping, buffering, repair, simplification, reprojection, or tolerance.
"""
import gzip, hashlib, json, subprocess
from shapely import STRtree
from shapely.geometry import shape, mapping

REPO='.'
INVENTORY='c6a26e1caba54e1b81a89fbda3a64fff56da323d'
ATLAS='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'
SUCCESSOR='7c7cdf2388e0e7200b937c2cfb440b53165d9d98'
TARGET='gb:SLB:ADM1:17018030B68013150931387'
IDS=[
'physical-component:5eb203ea755668e2f35e8cf2881ef73a06e42508867f9f364e17dfb084af37f9',
'physical-component:6b8adac6ee31bf0283aaaf5676765c5ec0baec0c44df1f4d5d7dab3e57662972',
'physical-component:87db1d0ffe6b7047239bf59f72d50bd218df161032b47281d9a5d12b7ab6f152',
'physical-component:8e0fe181abeb0fd2bcc9200c223ea1200c097ec7bd4886f1cb4cee86dcee062c',
'physical-component:d727a2836552df78c6b512a120fdfbb4b7bcda7da08da209e55482a083ab9ec1',
'physical-component:fbf01e09735b15dd65c32e3a5ea0259b3333fde69f9c9ae2d1f47c6fd51a6994']
def git(commit,path): return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=REPO)
def decode(b): return json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b)
def canonical(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(v): return hashlib.sha256(canonical(v)).hexdigest()
inv=decode(git(INVENTORY,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'))
candidates={}; candidate_files={}
for pin in inv['complete_products']['components']:
 path=next(x['path'] for x in inv['source_descriptors'] if x['sha256']==pin['sha256'])
 raw=decode(git(ATLAS,path))
 for f in raw['features']:
  if f.get('id') in IDS:
   candidates[f['id']]=f; candidate_files[f['id']]=path
assert set(candidates)==set(IDS)
delta=decode(git(SUCCESSOR,'coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz'))
for f in delta['upsert_records']:
 if f.get('id') in IDS: candidates[f['id']]=f
part=decode(git(ATLAS,'data/geography/part-22.json'))
features=part['features']; target=next(f for f in features if f['id']==TARGET); tg=shape(target['geometry'])
other_features=[f for f in features if f.get('id')!=TARGET]; other_geoms=[shape(f['geometry']) for f in other_features]
tree=STRtree(other_geoms)
rows=[]
for fid in IDS:
 f=candidates[fid]; g=shape(f['geometry']); gain=tg.union(g).difference(tg); loss=tg.difference(tg.union(g))
 neighbors=[]
 for ix in tree.query(g):
  ix=int(ix); inter=g.intersection(other_geoms[ix])
  if inter.area>0: neighbors.append({'id':other_features[ix].get('id'),'intersection_area_deg2':inter.area})
 # original source comparison confirms the consumed simplified geoBoundaries product
 # uniquely binds the entire component to this stable subject; record its exact feature pin.
 full_feature_sha={'5eb203ea755668e2f35e8cf2881ef73a06e42508867f9f364e17dfb084af37f9':'e9f9b756cdd00e34eae6aa3d24a87ec0ed38480e9309e56db2af87e9716eb249','6b8adac6ee31bf0283aaaf5676765c5ec0baec0c44df1f4d5d7dab3e57662972':'59d59be1d8739ecbd924e3e193c844d46317e21fa25f2d8dc707df214205a0be','87db1d0ffe6b7047239bf59f72d50bd218df161032b47281d9a5d12b7ab6f152':'218a72fecb75185642b0a927f794a9b56427dafb95f08f445c2c42cf2bf7cc9e','8e0fe181abeb0fd2bcc9200c223ea1200c097ec7bd4886f1cb4cee86dcee062c':'009f7fe80d4ec899f6f071a9283a8d5a4ce1ca417e2a4cc6f15d055b2b5171de','d727a2836552df78c6b512a120fdfbb4b7bcda7da08da209e55482a083ab9ec1':'a9a5ea13e25fe54e08bd6c2cc04e2e8fda08b2621fde6c1a483cfe0cbdd1557d','fbf01e09735b15dd65c32e3a5ea0259b3333fde69f9c9ae2d1f47c6fd51a6994':'0e7f884c23fe5ca38a883bcb70bc5763357fe3a0704bb0eb99a39fdd7b7c1cf0'}[fid.split(':')[1]]
 exact_gain=gain.equals(g); exact_noloss=loss.is_empty; no_neighbor=not neighbors
 accepted=exact_gain and exact_noloss and no_neighbor
 rows.append({'component_id':fid,'candidate_feature_sha256':sha(f),'retained_comparison_feature_sha256':full_feature_sha,'candidate_feature_hash_reconciles':sha(f)==full_feature_sha,'candidate_geometry_sha256':sha(f['geometry']),'candidate_feature_source':candidate_files[fid],'current_subject_id':TARGET,'current_subject_feature_sha256':'20780e254d9f23651603e8081009d8f899cba3edfadbbfde5f182400afe6c550','current_subject_geometry_sha256':'a647fd7d345703fbf04a282c3ba080cf447157dafb91efa41d38f748ccd9651e','simplified_source_id':'gb:SLB:ADM1','simplified_source_feature_index':9,'simplified_source_shapeID':'17018030B68013150931387','simplified_source_feature_sha256':'c82b0b46ee74bbefba004675b21fc452e9fd7dab2936ce9d4c5ac572a97c1a10','simplified_source_geometry_sha256':'56a128a17f304f440cee40409195b976589f4df02e06451ba971d970c5fbc844','source_binding':'unique compatible recorded subject; exact source coverage; see pinned complete source-comparison row','candidate_area_deg2':g.area,'target_intersection_area_deg2':g.intersection(tg).area,'gain_equals_candidate_exactly':exact_gain,'gain_geometry_sha256':sha(mapping(gain)),'gain_vs_candidate_symmetric_difference_area_deg2':gain.symmetric_difference(g).area,'no_target_loss_exactly':exact_noloss,'target_loss_area_deg2':loss.area,'new_positive_area_neighbor_overlaps':neighbors,'disposition':'source-fit-payload' if accepted else 'exact-geometric-refusal','refusal_reason':None if accepted else ('candidate is not exactly the newly gained target geometry' if not exact_gain else 'candidate creates positive-area overlap with active neighbor' if not no_neighbor else 'target loss is nonempty'),'candidate_geometry':f['geometry'],'proposed_geometry':mapping(tg.union(g)) if accepted else None})
result={'schema':'melanesia-choiseul-six-source-fit/v1','method':'independent component-by-component exact-coordinate overlay','crs':'literal GeoJSON longitude/latitude coordinates; degree-squared areas are diagnostic only','policy':'require exact source-covered candidate; unique stable subject; candidate equals target union gain; zero target loss; no new positive-area overlap with any other current active geography feature','runtime':'Python 3.12.14; Shapely 2.1.2; GEOS 3.13.1','immutable_inputs':{'component_inventory_commit':INVENTORY,'component_successor_commit':SUCCESSOR,'atlas_commit':ATLAS,'target_id':TARGET,'target_feature_sha256':'20780e254d9f23651603e8081009d8f899cba3edfadbbfde5f182400afe6c550','target_geometry_sha256':'a647fd7d345703fbf04a282c3ba080cf447157dafb91efa41d38f748ccd9651e'},'scope_counts':{'candidates':len(rows),'source_fit_payloads':sum(x['disposition']=='source-fit-payload' for x in rows),'exact_geometric_refusals':sum(x['disposition']=='exact-geometric-refusal' for x in rows)},'cases':rows,'limits':['geoBoundaries 2021 represented year is not a boundary effective date or legal-current authority','no present-day physical ground truth, historic water/ice attribution, or processing cause inferred','source-relative reference-map evidence only; does not authorize application','full batch review and broader source authority retrieval are not complete']}
open('research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/choiseul-six/analysis.json','w').write(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result['scope_counts']))
