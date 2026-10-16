import os, resource
resource.setrlimit(resource.RLIMIT_AS, (768*1024**2,768*1024**2))
resource.setrlimit(resource.RLIMIT_CPU, (45,45))
import json, gzip, hashlib, pathlib, collections, math, time
from shapely.geometry import shape, Point
from shapely.validation import explain_validity

ROOT=pathlib.Path(__file__).resolve().parent
AUTHOR=pathlib.Path('/workspace/scratch/127991fc8b8e/.worldatlas-workspaces/a7d1c19eff225d01/dda6ef44fc5bf26bb9ad5567433b4c1ac45920f1f1fc1ca27469c1f1e02b3af3/work/.cache')
started=time.monotonic()
pins=[]
def read(path, expected=None):
    body=path.read_bytes()
    got={'file':path.name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'git_blob_oid':hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()}
    if expected:
        for k in ('bytes','sha256','git_blob_oid'):
            if k in expected: assert got[k]==expected[k], (path,k,got[k],expected[k])
        got.update({k:v for k,v in expected.items() if k in ('commit','path','mode')})
    pins.append(got)
    decoded=gzip.decompress(body) if path.suffix=='.gz' else body
    assert len(decoded)<32*1024**2
    return json.loads(decoded)

stage=read(ROOT/'whole-new-source-stage-inputs.json',{'bytes':872634,'sha256':'620c3aab733389f4511491ba5c1f916f22c9235188b6e00d6a20053ef1020988','git_blob_oid':'ff12987f4bfb1df9fabc13e474614a4a31604ef0'})
raw=read(ROOT/'osm-full-county-relations.json',{'bytes':1894713,'sha256':'b625ee0e686f239dd8eecf3eb21799228371ca5a1eef1c34c79a38905cf2d692','git_blob_oid':'d1344471a7a39f157de2509de52fb42400ab20c9'})
exact=read(ROOT/'exact365-new-source-identity-inputs.json')
physical=read(ROOT/'actual-first12-result-review.json')
crosswalk=read(AUTHOR/'vietnam365-explicit-source-crosswalk.json',{'bytes':109411,'sha256':'44fa322248b6e328e9cd34fc77b1f44ef113adec7f5aa17a903901ac65c3f6b7'})
remaining=read(AUTHOR/'vietnam-original-remaining553.json')
author_contacts=read(AUTHOR/'vietnam365-original-global-source-contacts.json',{'bytes':582907,'sha256':'198a08f3c96ab27ee8db210e1062645030ae7c4bc7e5fab6927ae8a1aa070faa'})
aliases=json.loads((AUTHOR/'vietnam365-original-contact-inputs/local-aliases.json').read_text())
original={}
for a in aliases: original[pathlib.Path(a['local']).name]=read(pathlib.Path(a['local']),a['original_pin'])
roster={r['source_index']:r for r in original['source-feature-roster.json.gz']}
current={f['properties']['id']:f for f in original['current-targets-part-4.json']['features']}
catalogue=original['catalogue.json']['products']
source_rows={r['y']:r['runs'] for name in ['source-candidates-block-027.json.gz','source-candidates-block-028.json.gz'] for r in original[name]}
raw_byid={r['id']:r for r in raw['elements']}
assert len(raw_byid)==14 and len(stage)==12 and len(roster)==73567 and len(catalogue)==368
assert not original['source-census-summary.json']['source_features_excluded']
assert not original['source-raster-summary.json']['unsupported_source_features']

def key(k):return (k['owner'],k['y'],k['x'])
qkeys={key(r['original_key']) for r in exact['records']}
assert len(qkeys)==365==len(exact['records'])
assert {key(r) for r in crosswalk['original_keys']}==qkeys
remaining_keys={(o,r['y'],r['x']) for r in remaining['keys'] for o in r['original_owner']}
assert len(remaining_keys)==553 and qkeys<=remaining_keys
physical_keys={key(r['original_key']):r for r in physical['records']}
assert set(physical_keys)==qkeys
author_bykey={key(r['original_key']):r for r in author_contacts['records']}

def segments(points):
    return collections.Counter(tuple(sorted((tuple(a),tuple(b)))) for a,b in zip(points,points[1:]))
def geom_segments(g):
    polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
    result=collections.Counter()
    for poly in polys:
        for ring in poly: result.update(segments(ring))
    return result

geoms={r['target']:shape(r['consumed']['geometry']) for r in stage}
source_assessments=[]
for row in stage:
    s=row['target'];f=row['consumed'];j=row['existing_atlas_identity_join'];e=raw_byid[int(s.split(':')[-1])]
    raw_segments=collections.Counter();missing=[]
    for m in e['members']:
        if m['role'] not in ('outer','inner'):continue
        if m['type']!='way' or not m.get('geometry') or any(p is None for p in m['geometry']):missing.append(m['ref']);continue
        raw_segments.update(segments([(p['lon'],p['lat']) for p in m['geometry']]))
    g=geoms[s];old=shape(row['selected']['geometry']);owner=j['stable_owner'];source=roster[j['source_sid']]
    assert source==j['exact_source_roster_record'] and source['owners']==[owner] and source['source_id']==j['existing_atlas_id']
    assert current[j['existing_atlas_id']]==row['selected'],('current selected feature changed',s)
    assert f['properties']['OSM_tags']==e['tags']
    prov=f['properties']['source_provenance']
    assert prov['relation_version']==e['version'] and prov['relation_timestamp']==e['timestamp']
    assert prov['source_snapshot']==raw['osm3s']['timestamp_osm_base']
    assert not missing and raw_segments==geom_segments(f['geometry'])
    assert g.is_valid and not g.is_empty
    ref=Point(j['old_reference_point']);assert g.contains(ref)
    records=[r for r in exact['records'] if r['new_source_identity']==s]
    assert records and all(r['existing_atlas_id']==j['existing_atlas_id'] and r['stable_owner']==owner for r in records)
    source_assessments.append({'source_id':s,'relation_version':e['version'],'relation_edit_timestamp':e['timestamp'],'snapshot':raw['osm3s']['timestamp_osm_base'],'name':e['tags']['name'],'name_en':e['tags'].get('name:en'),'old_name':e['tags'].get('old_name'),'division_code':e['tags'].get('division_code'),'wikidata':e['tags'].get('wikidata'),'target_id':j['existing_atlas_id'],'stable_owner':owner,'predecessor_sid_identity_only':j['source_sid'],'retained_parent_id':j['existing_parent_id'],'retained_parent_name':j['actual_existing_parent_name'],'candidate_keys':len(records),'geometry_bounds_lonlat':list(g.bounds),'literal_segment_count':sum(raw_segments.values()),'literal_segments_equal_raw_multiset':True,'missing_boundary_members':missing,'valid_geometry':g.is_valid,'geometry_validity_reason':explain_validity(g),'current_selected_feature_exactly_equal':True,'current_source_roster_join_exact':True,'old_representative_point_strictly_inside':True,'source_identity_and_administrative_role_supported':True,'source_semantic_adoption':False,'native_adoption_approved_keys':0,'native_adoption_blocked_keys':len(records),'reason':'Contrary Vietnam fine-source contacts not substantively superseded; source accuracy, datum realisation and territorial boundary provenance unresolved at candidate centres.'})

between=[]
for i,a in enumerate(stage):
    for b in stage[i+1:]:
        if geoms[a['target']].intersection(geoms[b['target']]).area>0:between.append([a['target'],b['target']])
assert not between
records=[];family_counts=collections.Counter();new_issues=[]
for r in exact['records']:
    k=r['original_key'];hits=[run for run in source_rows[k['y']] if run[0]<=k['x']<run[1]]
    assert len(hits)==1
    run=hits[0];contacts=[roster[sid] for sid in run[3]]
    claimed=author_bykey[key(k)]
    assert [c['source_index'] for c in contacts]==[c['source_index'] for c in claimed['complete_original_contacts']]
    for c,ac in zip(contacts,claimed['complete_original_contacts']):
        assert all(ac[x]==v for x,v in c.items())
        assert ac['source_family']==catalogue[c['family_index']]['key']
    families=sorted({catalogue[c['family_index']]['key'] for c in contacts});family_counts.update(families)
    assert any(c['source_id'].startswith('gb:VNM:ADM2:') for c in contacts)
    p=Point(r['longitude'],r['latitude']);geo_hits=[sid for sid,g in geoms.items() if g.covers(p)]
    point_boundary=any(g.boundary.covers(p) for g in geoms.values())
    if geo_hits!=[r['new_source_identity']] or point_boundary:new_issues.append(k)
    ph=physical_keys[key(k)]
    assert ph['new_source_target']==r['new_source_identity'] and ph['physical_interpretation']=='mapped_land_only'
    records.append({'original_key':k,'new_source_id':r['new_source_identity'],'proposed_target_id':r['existing_atlas_id'],'proposed_target_owner':r['stable_owner'],'point_lonlat_from_retained_proposal':[r['longitude'],r['latitude']],'rounded_point_literal_osm_hits':geo_hits,'rounded_point_on_new_boundary':point_boundary,'retained_physical_interpretation':ph['physical_interpretation'],'original_fine_source_contacts':[{'source_id':c['source_id'],'source_index':c['source_index'],'owners':c['owners'],'name':c['name'],'family':catalogue[c['family_index']]['key']} for c in contacts],'source_contact_families':families,'disposition':'blocked','holds':['unresolved-competing-Vietnam-fine-source','no-demonstrated-boundary-source-supersession'],'native_adoption_approved':False})

result={'kind':'distinct-scientific-source-assessment-bounded-original-Vietnam365','assessor':'/root/assess_vietnam_revised_sources','assessment_date_utc':'2026-10-16','accepted_code_and_current_target_commit':'cd68e89523901acf477d0365470410b8b970bb48','scope_original_keys':365,'original_question_owner_count':len({k[0] for k in qkeys}),'raw_relation_count':14,'proposed_relation_count':12,'original_key_scope_is_subset_of_remaining553':True,'input_pins':pins,'snapshot_metadata':raw['osm3s'],'source_assessments':source_assessments,'pairwise_new_source_positive_area_overlaps':between,'rounded_point_new_source_issues':new_issues,'original_contact_family_counts':dict(family_counts),'source_identity_role_supported_relation_ids':[r['source_id'] for r in source_assessments],'native_adoption_approved_keys':[],'native_adoption_blocked_keys':records,'full_current_competing_geography_validated':False,'source_semantic_adoption':False,'native_qualification':False,'accepted_repair_credit':0,'method_limits':['The literal source/geometry/identity inspection is independent. Original global raster results and physical results are reused, not rerun.','The old source census covers its pinned 368-product corpus only; it is not an exhaustive inventory of every later or external geographic source.','Shapely point probes consume retained rounded longitude/latitude values; they are source-geography diagnostics, not the exact native rational grid predicate.','Complete actual current country/fine-source competition, native boundary ties, occupied keys and predecessor conservation are not established by this source assessment.','The complete raw physical result was not locally available; this assessment verifies the immutable public independent review/execution view only, without manufacturing a qualified receipt.'],'execution':{'elapsed_seconds':time.monotonic()-started,'address_space_limit_bytes':768*1024**2,'cpu_limit_seconds':45,'max_rss_linux_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}}
out=ROOT/'independent-source-assessment.json'
with out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ['scope_original_keys','original_question_owner_count','raw_relation_count','proposed_relation_count','original_contact_family_counts','rounded_point_new_source_issues','source_semantic_adoption','native_qualification','accepted_repair_credit','execution']},indent=2))
print('OUTPUT',out.name,out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
