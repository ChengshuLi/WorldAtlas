#!/usr/bin/env python3
"""Reproduce the six Choiseul source-fit and complete geographic-exclusion query.
Reads immutable retained inputs from Git. No snapping, tolerance, repair,
simplification, buffering, or reprojection is performed.
"""
import gzip, hashlib, json, re, subprocess
import shapely
from shapely import STRtree
from shapely.geometry import shape, mapping

REPO='.'
INVENTORY='c6a26e1caba54e1b81a89fbda3a64fff56da323d'
SUCCESSOR='7c7cdf2388e0e7200b937c2cfb440b53165d9d98'
ATLAS='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'
EVIDENCE='6951c117534f69742acd1f61820cfc21a4ad17f5'
TARGET='gb:SLB:ADM1:17018030B68013150931387'
SOURCE='gb:SLB:ADM1'
SOURCE_PATH='coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-SLB-ADM1-000.bin.gz'
COMPONENT_SHARDS=[f'coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-{i:03}.json.gz' for i in (9,10,11)]
IDS=[
'physical-component:5eb203ea755668e2f35e8cf2881ef73a06e42508867f9f364e17dfb084af37f9',
'physical-component:6b8adac6ee31bf0283aaaf5676765c5ec0baec0c44df1f4d5d7dab3e57662972',
'physical-component:87db1d0ffe6b7047239bf59f72d50bd218df161032b47281d9a5d12b7ab6f152',
'physical-component:8e0fe181abeb0fd2bcc9200c223ea1200c097ec7bd4886f1cb4cee86dcee062c',
'physical-component:d727a2836552df78c6b512a120fdfbb4b7bcda7da08da209e55482a083ab9ec1',
'physical-component:fbf01e09735b15dd65c32e3a5ea0259b3333fde69f9c9ae2d1f47c6fd51a6994']
OUT='research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/choiseul-six/analysis.json'
def git(commit,path): return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=REPO)
def decode(b): return json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b)
def canonical(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_json(v): return sha_bytes(canonical(v))
def pin(commit,path):
 b=git(commit,path);return {'commit':commit,'path':path,'bytes':len(b),'sha256':sha_bytes(b),'git_blob_oid':subprocess.check_output(['git','rev-parse',f'{commit}:{path}'],cwd=REPO,text=True).strip()}
assert shapely.__version__=='2.1.2' and shapely.geos_version_string.startswith('3.13.1')
# Recover original exact candidate records; apply only retained successor upserts.
inv=decode(git(INVENTORY,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'))
candidates={};candidate_paths={};successor_ids=set()
for pinrow in inv['complete_products']['components']:
 path=next(x['path'] for x in inv['source_descriptors'] if x['sha256']==pinrow['sha256'])
 for f in decode(git(ATLAS,path))['features']:
  if f.get('id') in IDS:candidates[f['id']]=f;candidate_paths[f['id']]=path
assert set(candidates)==set(IDS)
delta=decode(git(SUCCESSOR,'coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz'))
for f in delta['upsert_records']:
 if f.get('id') in IDS:candidates[f['id']]=f;successor_ids.add(f['id'])
# Bind each candidate to its exact independently retained source-comparison row.
comparison={}
for path in COMPONENT_SHARDS:
 for row in decode(git(EVIDENCE,path)):
  if row.get('component') in IDS:comparison[row['component']]=row
assert set(comparison)==set(IDS)
# Load the complete retained simplified product actually selected by administrative.py.
admin_registry_bytes=git(EVIDENCE,'data/administrative-sources.json');admin_registry=decode(admin_registry_bytes)
admin_code_bytes=git(EVIDENCE,'scripts/administrative.py');admin_code=admin_code_bytes.decode()
assert admin_registry[SOURCE]['simplifiedGeometryGeoJSON'].endswith('_simplified.geojson')
assert "replace('.geojson','_simplified.geojson')" in admin_code and "row['simplifiedGeometryGeoJSON']" in admin_code
src_bytes=git(EVIDENCE,SOURCE_PATH);source_collection=decode(src_bytes)
assert source_collection['type']=='FeatureCollection' and len(source_collection['features'])==10
source_feature=source_collection['features'][9];source_geom=shape(source_feature['geometry'])
assert source_feature['properties']['shapeID']=='17018030B68013150931387'
assert sha_json(source_feature)=='c82b0b46ee74bbefba004675b21fc452e9fd7dab2936ce9d4c5ac572a97c1a10'
assert sha_json(source_feature['geometry'])=='56a128a17f304f440cee40409195b976589f4df02e06451ba971d970c5fbc844'
# Collect all actual current geography features and pin all 34 complete parts.
parts=sorted(p for p in subprocess.check_output(['git','ls-tree','-r','--name-only',ATLAS,'--','data/geography'],cwd=REPO,text=True).splitlines() if re.fullmatch(r'data/geography/part-\d+\.json',p))
assert len(parts)==34
part_pins=[];all_features=[];target=None
for path in parts:
 b=git(ATLAS,path);part_pins.append({'commit':ATLAS,'path':path,'bytes':len(b),'sha256':sha_bytes(b),'git_blob_oid':subprocess.check_output(['git','rev-parse',f'{ATLAS}:{path}'],cwd=REPO,text=True).strip()})
 for f in decode(b)['features']:
  all_features.append((f,shape(f['geometry']),path))
  if f.get('id')==TARGET:target=f
assert target is not None
# Stable subject geometry is read exactly from the selected record.
target_feature,target_geom,target_path=next(v for v in all_features if v[0].get('id')==TARGET)
assert sha_json(target_feature)=='20780e254d9f23651603e8081009d8f899cba3edfadbbfde5f182400afe6c550'
assert sha_json(target_feature['geometry'])=='a647fd7d345703fbf04a282c3ba080cf447157dafb91efa41d38f748ccd9651e'
# Spatially bound query: exact candidate union bbox; retain every complete-file pin.
candidate_geoms={i:shape(candidates[i]['geometry']) for i in IDS}
cb=(min(g.bounds[0] for g in candidate_geoms.values()),min(g.bounds[1] for g in candidate_geoms.values()),max(g.bounds[2] for g in candidate_geoms.values()),max(g.bounds[3] for g in candidate_geoms.values()))
# Candidate bboxes query the complete 49,589-feature baseline; GEOS evaluates exact predicates only for bbox hits.
bbox_features=[(f,g,p) for f,g,p in all_features if not (g.bounds[2]<cb[0] or g.bounds[0]>cb[2] or g.bounds[3]<cb[1] or g.bounds[1]>cb[3])]
rows=[]
for fid in IDS:
 f=candidates[fid];g=candidate_geoms[fid];cmp=comparison[fid]
 assert sha_json(g.__geo_interface__ if False else f['geometry'])==cmp['component_geometry_sha256']
 assert cmp['status']=='one-compatible-recorded-subject-uniquely-covers-component'
 assert cmp['component_minus_source_union']['is_empty'] is True
 fits=[x for x in cmp['feature_intersections'] if x['binding']['source_id']==SOURCE and x['source_feature_covers_entire_component']]
 assert len(fits)==1 and fits[0]['binding']['feature_index']==9 and fits[0]['binding']['shapeID']=='17018030B68013150931387'
 assert g.difference(source_geom).is_empty
 gain=target_geom.union(g).difference(target_geom);loss=target_geom.difference(target_geom.union(g))
 positive_neighbors=[];bbox_exclusions=[]
 for nf,ng,np in bbox_features:
  if nf.get('id')==TARGET:continue
  bbox_exclusions.append({'id':nf.get('id'),'source_path':np})
  if g.intersection(ng).area>0:positive_neighbors.append({'id':nf.get('id'),'source_path':np,'area_deg2':g.intersection(ng).area})
 exact_gain=gain.equals(g);no_loss=loss.is_empty;no_neighbor=not positive_neighbors
 disposition='exact-source-fit-payload' if exact_gain and no_loss and no_neighbor else 'source-backed-additive-grid-candidate'
 rows.append({'component_id':fid,'candidate_feature_sha256':sha_json(f),'candidate_geometry_sha256':sha_json(f['geometry']),'candidate_geometry':f['geometry'],'candidate_source':{'original_inventory_commit':ATLAS,'original_inventory_path':candidate_paths[fid],'successor_upsert_commit':SUCCESSOR if fid in successor_ids else None,'successor_upsert_path':'coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz' if fid in successor_ids else None},'comparison_row':{'commit':EVIDENCE,'path':next(p for p in COMPONENT_SHARDS if any(z.get('component')==fid for z in decode(git(EVIDENCE,p)) )),'candidate_feature_sha256':cmp['full_component_feature_sha256'],'candidate_geometry_sha256':cmp['component_geometry_sha256'],'status':cmp['status'],'source_feature_sha256':fits[0]['binding']['feature_sha256'],'source_geometry_sha256':fits[0]['binding']['geometry_sha256'],'source_unique_binding_count':1,'component_minus_source_union_empty':cmp['component_minus_source_union']['is_empty']},'current_subject_id':TARGET,'current_subject_path':target_path,'target_intersection_area_deg2':g.intersection(target_geom).area,'candidate_equals_target_union_gain_exactly':exact_gain,'gain_vs_candidate_symmetric_difference_area_deg2':gain.symmetric_difference(g).area,'target_loss_empty_exactly':no_loss,'target_loss_area_deg2':loss.area,'new_positive_area_overlap_with_any_other_current_geography_feature':positive_neighbors,'overlapping_bbox_feature_exclusions':bbox_exclusions,'disposition':disposition,'proposed_subject_geometry':mapping(target_geom.union(g)) if disposition=='exact-source-fit-payload' else None})
report={'schema':'melanesia-choiseul-six-source-fit/v2','analysis_kind':'bounded retained-source-relative fit and complete-baseline neighbor exclusion query','runtime':{'python':'3.12.14','shapely':shapely.__version__,'geos':shapely.geos_version_string},'coordinate_policy':'literal GeoJSON lon/lat coordinate sequences; no snapping, tolerance, buffer, repair, simplification, or reprojection','exact_fit_rule':'source-covered candidate; unique compatible recorded stable subject; exact candidate equals target union gain; empty target loss; no new positive-area intersection with any other current geography feature','source_product':{'administrative_script_pin':pin(EVIDENCE,'scripts/administrative.py'),'source_registry_pin':pin(EVIDENCE,'data/administrative-sources.json'),'simplified_source_url':admin_registry[SOURCE]['simplifiedGeometryGeoJSON'],'source_id':SOURCE,'path':SOURCE_PATH,'commit':EVIDENCE,'compressed_bytes':len(src_bytes),'compressed_sha256':sha_bytes(src_bytes),'decoded_bytes':len(gzip.decompress(src_bytes)),'decoded_sha256':sha_bytes(gzip.decompress(src_bytes)),'feature_count':10,'feature_index':9,'shapeID':'17018030B68013150931387','feature_sha256':sha_json(source_feature),'geometry_sha256':sha_json(source_feature['geometry']),'consumption_basis':'scripts/administrative.py selects the *_simplified.geojson member; this retained source product is the byte-pinned consumed simplified member'},'current_baseline':{'commit':ATLAS,'all_geography_parts':part_pins,'feature_count':len(all_features),'candidate_union_bbox':cb,'bbox_query_feature_ids':[f.get('id') for f,g,p in bbox_features],'target_id':TARGET,'target_path':target_path,'target_feature_sha256':sha_json(target_feature),'target_geometry_sha256':sha_json(target_feature['geometry'])},'supporting_source_comparison_pins':[pin(EVIDENCE,p) for p in COMPONENT_SHARDS],'candidate_inventory_pins':[pin(INVENTORY,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'),pin(SUCCESSOR,'coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz')],'scope_counts':{'candidates':len(rows),'exact_source_fit_payloads':sum(x['disposition']=='exact-source-fit-payload' for x in rows),'source_backed_additive_grid_candidates':sum(x['disposition']=='source-backed-additive-grid-candidate' for x in rows)},'cases':rows,'limits':['2021 is represented source year, not an effective date or proof of current legal authority','does not infer physical present-day ground truth, historic water or ice, processing cause, or boundary authority','source-relative reference-map evidence is not authorization to change or publish the map','full 363-ID batch remains in progress; whole-world production-pipeline replay is not performed']}
open(OUT,'w').write(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps(report['scope_counts']))
