#!/usr/bin/env python3
"""Admitted exact source-relative and complete-neighbor query for six cases."""
import datetime, gzip, hashlib, importlib.util, json, math, os, platform, struct, sys, time
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely import STRtree, __version__ as shapely_version, geos_version_string

ROOT=Path(__file__).resolve().parents[5]
PACKET='research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN='choiseul-six-exact-003'
PIN_FILE=Path(PACKET)/'vintages/choiseul-six/input-pins.json'
if (ROOT/PACKET/'vintages'/RUN).exists(): raise SystemExit('refusing existing vintage; choose a fresh run name')
pin_spec=json.loads((ROOT/PIN_FILE).read_text())
assert pin_spec['schema']=='choiseul-six-exact-inputs/v1'
helper_path='scripts/evidence/immutable.py'
helper_row=next(x for x in pin_spec['files'] if x['path']==helper_path)
import subprocess
helper_bytes=subprocess.check_output(['git','-C',str(ROOT),'show',pin_spec['baseline_commit']+':'+helper_path])
assert len(helper_bytes)==helper_row['bytes'] and hashlib.sha256(helper_bytes).hexdigest()==helper_row['sha256']
helper_ns={'__name__':'pinned_worldatlas_evidence_immutable','__file__':str(ROOT/helper_path)}
exec(compile(helper_bytes,str(ROOT/helper_path),'exec'),helper_ns)
Baseline=helper_ns['Baseline'];NewVintage=helper_ns['NewVintage'];canonical_json=helper_ns['canonical_json']
baseline=Baseline(ROOT,pin_spec['baseline_commit'],pin_spec['files'])
assert baseline.pinned_bytes(helper_path)==helper_bytes
started=time.monotonic()
def raw(path):return baseline.pinned_bytes(path)
def decode(b):return json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b)
def canonical(v):return canonical_json(v)
def sha(b):return hashlib.sha256(b).hexdigest()
def sha_json(v):return sha(canonical(v))
# Pre-admit every decoded gzip body from the custody index before decompressing it.
index=decode(raw(pin_spec['custody_index']))
source_path=pin_spec['source_product_path'];source_encoded=raw(source_path)
source_uncompressed_bytes=struct.unpack('<I',source_encoded[-4:])[0]
baseline.admit(source_path+':decoded',source_uncompressed_bytes)
component_payloads={}
for component_id,path in pin_spec['component_payloads'].items():
 aliases=[x for x in index['aliases'] if x.get('payload')==path]
 listed=[x for x in index['payloads'] if x['path']==path]
 assert len(aliases)>=1 and len(listed)==1
 alias=aliases[0]['original'];assert all(x['original']['sha256']==alias['sha256'] and x['original']['bytes']==alias['bytes'] and x['original']['uncompressed_sha256']==alias['uncompressed_sha256'] and x['original']['uncompressed_bytes']==alias['uncompressed_bytes'] for x in aliases)
 assert alias['bytes']==len(raw(path)) and alias['sha256']==sha(raw(path))
 baseline.admit(path+':decoded',alias['uncompressed_bytes'])
# Now decode all source/candidate bodies after the full admitted phase is known.
source_decoded=gzip.decompress(source_encoded)
assert len(source_decoded)==source_uncompressed_bytes
source_collection=json.loads(source_decoded)
assert source_collection['type']=='FeatureCollection' and len(source_collection['features'])==10
admin_registry=decode(raw('data/administrative-sources.json'))
admin_code=raw('scripts/administrative.py').decode()
assert admin_registry['gb:SLB:ADM1']['simplifiedGeometryGeoJSON'].endswith('_simplified.geojson')
assert "replace('.geojson','_simplified.geojson')" in admin_code and "row['simplifiedGeometryGeoJSON']" in admin_code
source_features=source_collection['features'];source_geometries=[shape(x['geometry']) for x in source_features]
feature_index=9;source_feature=source_features[feature_index]
assert source_feature['properties']['shapeID']=='17018030B68013150931387'
source_feature_hash=sha_json(source_feature);source_geometry_hash=sha_json(source_feature['geometry'])
assert source_feature_hash=='c82b0b46ee74bbefba004675b21fc452e9fd7dab2936ce9d4c5ac572a97c1a10'
assert source_geometry_hash=='56a128a17f304f440cee40409195b976589f4df02e06451ba971d970c5fbc844'
IDS=sorted(pin_spec['component_payloads'])
candidates={}
for cid,path in pin_spec['component_payloads'].items():
 alias=next(x['original'] for x in index['aliases'] if x.get('payload')==path)
 encoded=raw(path);decoded=gzip.decompress(encoded)
 assert len(decoded)==alias['uncompressed_bytes'] and sha(decoded)==alias['uncompressed_sha256']
 value=json.loads(decoded);features=value if isinstance(value,list) else value.get('features',[])
 matches=[f for f in features if f.get('id')==cid]
 assert len(matches)==1;candidates[cid]=matches[0]
assert set(candidates)==set(IDS)
# Exact candidate geometry hashes retained by the independent source-comparison rows.
EXPECTED={
'physical-component:5eb203ea755668e2f35e8cf2881ef73a06e42508867f9f364e17dfb084af37f9':'f648c77c8421bf1674704283924e881a4be7e951c951679cf0d17de5e5f79a73',
'physical-component:6b8adac6ee31bf0283aaaf5676765c5ec0baec0c44df1f4d5d7dab3e57662972':'1ebf1fd0fcca8e55fb7e95f395ef83b42797512d7f0dad3573af41f8f908da43',
'physical-component:87db1d0ffe6b7047239bf59f72d50bd218df161032b47281d9a5d12b7ab6f152':'cf21d172b76ff65fe2af9e5c6a9835ba8c4ff0c863ab3fda2c924ce451e1566f',
'physical-component:8e0fe181abeb0fd2bcc9200c223ea1200c097ec7bd4886f1cb4cee86dcee062c':'8971e555bbf28961da4c9cdbe51b40a539d585fc217c3d483208e558eab203a1',
'physical-component:d727a2836552df78c6b512a120fdfbb4b7bcda7da08da209e55482a083ab9ec1':'d18a0b1802de7f55be1e5e75613a011f3fa9ec50beb416a5dfd618cb4d2d8f10',
'physical-component:fbf01e09735b15dd65c32e3a5ea0259b3333fde69f9c9ae2d1f47c6fd51a6994':'788af7b5ffb374cbc4f39133681e317430835836fd04c44cd6e5e1c3099c3f4b'}
assert all(sha_json(candidates[i]['geometry'])==EXPECTED[i] for i in IDS)
candidate_geoms={i:shape(candidates[i]['geometry']) for i in IDS}
cb=(min(g.bounds[0] for g in candidate_geoms.values()),min(g.bounds[1] for g in candidate_geoms.values()),max(g.bounds[2] for g in candidate_geoms.values()),max(g.bounds[3] for g in candidate_geoms.values()))
def bbox_coords(coords):
 stack=[coords];lo_x=lo_y=math.inf;hi_x=hi_y=-math.inf
 while stack:
  v=stack.pop()
  if isinstance(v,(list,tuple)):
   if len(v)>=2 and isinstance(v[0],(int,float)) and isinstance(v[1],(int,float)):
    x,y=v[0],v[1];lo_x=min(lo_x,x);hi_x=max(hi_x,x);lo_y=min(lo_y,y);hi_y=max(hi_y,y)
   else:stack.extend(v)
 return (lo_x,lo_y,hi_x,hi_y)
def bboxes_intersect(a,b):return not(a[2]<b[0] or a[0]>b[2] or a[3]<b[1] or a[1]>b[3])
# Read all complete current Atlas part inputs; instantiate geometry only for the query window.
target_id='gb:SLB:ADM1:17018030B68013150931387';all_ids=set();feature_count=0;source_subjects={};bbox_features=[];target_feature=None;target_path=None
for path in pin_spec['geography_parts']:
 part=decode(raw(path))
 for f in part['features']:
  feature_count+=1;fid=f.get('id')
  assert isinstance(fid,str) and fid not in all_ids;all_ids.add(fid)
  meta=f.get('properties',{}).get('metadata',{})
  if meta.get('source_id')=='gb:SLB:ADM1' and isinstance(meta.get('original_id'),str):source_subjects.setdefault(meta['original_id'],[]).append(fid)
  if fid==target_id:target_feature=f;target_path=path
  gjson=f.get('geometry')
  if gjson and bboxes_intersect(bbox_coords(gjson.get('coordinates',[])),cb):bbox_features.append((f,shape(gjson),path))
assert feature_count==49589 and target_feature is not None
subject_source_meta=target_feature['properties']['metadata']
assert subject_source_meta['source_id']=='gb:SLB:ADM1' and subject_source_meta['original_id']==source_feature['properties']['shapeID']
assert source_subjects[subject_source_meta['original_id']]==[target_id]
target_geom=shape(target_feature['geometry'])
assert sha_json(target_feature)=='20780e254d9f23651603e8081009d8f899cba3edfadbbfde5f182400afe6c550'
assert sha_json(target_feature['geometry'])=='a647fd7d345703fbf04a282c3ba080cf447157dafb91efa41d38f748ccd9651e'
# For every candidate, recompute complete-product coverage and unique recorded-source subject binding.
rows=[]
for cid in IDS:
 f=candidates[cid];g=candidate_geoms[cid]
 covering=[i for i,sg in enumerate(source_geometries) if sg.covers(g)]
 assert len(covering)==1 and covering[0]==feature_index
 assert g.difference(source_geometries[feature_index]).is_empty
 candidate_source_subject=f"gb:SLB:ADM1:{source_features[feature_index]['properties']['shapeID']}"
 assert candidate_source_subject==target_id
 gain=target_geom.union(g).difference(target_geom);loss=target_geom.difference(target_geom.union(g))
 positive=[];bbox_exclusions=[]
 for nf,ng,np in bbox_features:
  if nf.get('id')==target_id:continue
  bbox_exclusions.append({'id':nf['id'],'input_path':np})
  intersection=g.intersection(ng)
  if intersection.area>0:positive.append({'id':nf['id'],'input_path':np,'area_deg2':intersection.area})
 exact_gain=gain.equals(g);no_loss=loss.is_empty;no_neighbor=not positive
 disposition='exact-source-fit' if exact_gain and no_loss and no_neighbor else 'source-backed-native-grid-recheck'
 rows.append({'component_id':cid,'component_feature_sha256':sha_json(f),'component_geometry_sha256':sha_json(f['geometry']),'candidate_geometry':f['geometry'],'custody_payload_path':pin_spec['component_payloads'][cid],'source_product_feature_index':feature_index,'source_product_shapeID':source_features[feature_index]['properties']['shapeID'],'source_product_feature_sha256':source_feature_hash,'source_product_geometry_sha256':source_geometry_hash,'source_coverage_exact':True,'unique_recorded_source_subject_id':candidate_source_subject,'unique_recorded_subject_count':1,'target_intersection_area_deg2':g.intersection(target_geom).area,'candidate_equals_target_union_gain_exactly':exact_gain,'gain_vs_candidate_symmetric_difference_area_deg2':gain.symmetric_difference(g).area,'target_loss_empty_exactly':no_loss,'target_loss_area_deg2':loss.area,'all_other_baseline_feature_bbox_exclusions':bbox_exclusions,'new_positive_area_overlap_with_any_other_current_feature':positive,'disposition':disposition,'fit_proposal_subject_geometry':mapping(target_geom.union(g)) if disposition=='exact-source-fit' else None,'native_grid_recheck_required':disposition=='source-backed-native-grid-recheck'})
report={'schema':'melanesia-choiseul-six-source-fit/v3','analysis_kind':'pinned consumed simplified-source fit plus complete current geography neighbor exclusion','runtime':{'python':platform.python_version(),'shapely':shapely_version,'geos':geos_version_string},'policy':'coverage objective for an existing stable reference location; retain source-supported land candidate geometry; exact source-fit payloads require exact candidate=target gain, no target loss, and no new positive-area overlap; remaining source-backed candidates proceed to additive native-grid checking that preserves every existing assignment','coordinate_method':'literal GeoJSON longitude/latitude coordinates; no snapping, buffering, tolerance, repair, simplification, or reprojection; planar degree-squared values are diagnostic only','consumed_simplified_source':{'source_id':'gb:SLB:ADM1','path':pin_spec['source_product_path'],'compressed_sha256':sha(source_encoded),'compressed_bytes':len(source_encoded),'uncompressed_sha256':sha(source_decoded),'uncompressed_bytes':len(source_decoded),'feature_count':len(source_features),'feature_index':feature_index,'shapeID':source_features[feature_index]['properties']['shapeID'],'feature_sha256':source_feature_hash,'geometry_sha256':source_geometry_hash,'selected_source_url':admin_registry['gb:SLB:ADM1']['simplifiedGeometryGeoJSON'],'consumption_code_path':'scripts/administrative.py','consumption_code_sha256':sha(raw('scripts/administrative.py')),'consumption_check':'source registry selects *_simplified.geojson and administrative.py reads simplifiedGeometryGeoJSON'},'current_atlas_context':{'commit':pin_spec['baseline_commit'],'complete_geography_part_count':len(pin_spec['geography_parts']),'complete_feature_count':feature_count,'complete_unique_feature_id_count':len(all_ids),'target_id':target_id,'target_path':target_path,'target_feature_sha256':sha_json(target_feature),'target_geometry_sha256':sha_json(target_feature['geometry']),'candidate_union_bbox':cb,'bbox_query_feature_count':len(bbox_features),'bbox_query_feature_ids':[x[0]['id'] for x in bbox_features],'other_current_feature_intersection_test':'all current features in all 34 pinned part files with bbox intersecting the full six-candidate union window'},'input_admission':{'baseline_commit':pin_spec['baseline_commit'],'file_count':len(pin_spec['files']),'encoded_bytes':sum(x['bytes'] for x in pin_spec['files']),'admitted_total_bytes':sum(baseline.consumed.values()),'consumed':baseline.consumed},'scope_counts':{'components':len(rows),'exact_source_fit_proposals':sum(x['disposition']=='exact-source-fit' for x in rows),'source_backed_native_grid_rechecks':sum(x['native_grid_recheck_required'] for x in rows),'positive_area_other_feature_overlaps':sum(bool(x['new_positive_area_overlap_with_any_other_current_feature']) for x in rows)},'cases':rows,'limits':['2021 is the source represented year, not an effective date or present-day ground-truth claim','historic water or ice, processing cause, and boundary authority remain unresolved','source-relative assignment does not establish political/legal affiliation or authorize publication','all six payloads are ready for additive native-grid checking; those grid-cell ownership results are not included here','the broader 363-ID batch is still being worked; this is not a whole-world production-pipeline replay']}
script_bytes=Path(__file__).read_bytes();elapsed=time.monotonic()-started
exec_record={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.executable+' '+str(Path(__file__).relative_to(ROOT)),'baseline_commit':pin_spec['baseline_commit'],'input_manifest_sha256':sha(PIN_FILE.read_bytes()),'executed_script':{'path':str(Path(__file__).relative_to(ROOT)),'bytes':len(script_bytes),'sha256':sha(script_bytes)},'runtime':report['runtime'],'elapsed_seconds':elapsed,'helper':'scripts/evidence/immutable.py:Baseline + NewVintage','admitted_input_bytes':report['input_admission']['admitted_total_bytes'],'output_files':['analysis.json','execution.json','analyze.py','input-pins.json']}
values={'analysis.json':canonical_json(report),'execution.json':canonical_json(exec_record),'analyze.py':script_bytes,'input-pins.json':PIN_FILE.read_bytes()}
new=NewVintage(baseline,PACKET,RUN,list(values))
new.publish_bytes(values)
print(json.dumps({'status':'published','vintage':RUN,'analysis_counts':report['scope_counts'],'admitted_bytes':report['input_admission']['admitted_total_bytes']}))
