#!/usr/bin/env python3
"""Reproduce the additive validation vintage for geography issue #1111.

All repository evidence reads come from BASELINE_COMMIT via Git blobs. This
checks identity, row-to-feature crosswalk integrity, exact review scope and
packet inventory; it does not validate source geometry or legal boundaries.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, subprocess, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = 'data/regional-review/southern-south-america-crosswalk-validation-20261006/'
OLD = 'data/regional-review/regional-review-afee7ce9a5601ab2/'
BASELINE = '27be77596f23304de6a720735538427e6d23e242'
AUTHOR = '01a10948-7d38-75d0-bc01-4cc28ea41f49'
EXPECTED_PINS = {
 'world-index':'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
 'hierarchy':'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',
 'original-scope':'4bca00a1683a0104ab69beedb962dfe59b7b26597d631fdd710067b456fd82e2',
 'original-crosswalk':'ba78a03b26321a56fb05736a08b791ccb485e4580471d58eed54053160b4b82e',
 'original-verifier':'dcadc34a6b2a1bb33889198f68bedb0b253be100ff853f99bd818e58789e4bb9',
 'original-reproducer':'58a98cb8952dfb30cb4925bf244e09849b8bc8a9280e8390ea17c1c5f4e0db0f',
 'original-packet-index':'dbaeb80bba6c8a67affd50f937337b6abe0574dc7ead8a96f96d32fd5abe29c9',
}
ISSUE_FILE = ROOT / OWNED / 'source/issue-1111-api-2026-10-06.json'
EXPECTED_ISSUE_BODY_SHA256 = 'fc1cc2acd03e2882be490d8786b1ce0283498b808737875f2d6dfc8166565051'

class Invalid(ValueError): pass

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{path}'],stderr=subprocess.PIPE)
def csv_rows(raw: bytes):
    text=raw.decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(text,newline=''))
    if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):
        raise Invalid('CSV header missing or duplicated')
    rows=list(reader)
    if any(None in row for row in rows): raise Invalid('CSV row has extra columns')
    return reader.fieldnames,rows

def issue_contract():
    issue=json.loads(ISSUE_FILE.read_text())
    if issue.get('number') != 1111 or hashlib.sha256(issue['body'].encode()).hexdigest() != EXPECTED_ISSUE_BODY_SHA256:
        raise Invalid('Issue snapshot number or exact body hash differs from the reviewed #1111 scope')
    match=re.search(r'<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->',issue['body'],re.S)
    if not match: raise Invalid('Issue machine contract missing')
    contract=json.loads(match.group(1)); eq=contract['evidence_quality']
    if contract.get('mode')!='geography' or contract.get('owned_paths')!=[OWNED]: raise Invalid('Issue owner scope mismatch')
    if contract.get('depends_on')!=[446] or eq.get('version')!=1 or eq.get('review_kind')!='source': raise Invalid('Issue dependency/evidence contract mismatch')
    if eq.get('pins')!=EXPECTED_PINS: raise Invalid('Issue pins differ from recorded task scope')
    ids=eq.get('subject_ids')
    if not isinstance(ids,list) or len(ids)!=263 or len(ids)!=len(set(ids)): raise Invalid('Issue subject list is not the exact 263 unique IDs')
    return issue,contract,ids

def descriptors(paths):
    result=[]
    for path in sorted(set(paths)):
        raw=git_blob(BASELINE,path)
        result.append({'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
    return result

def index_path_roster(index):
    paths=[x.get('path') for x in index.get('files',[])]
    if len(paths)!=len(set(paths)) or any(not isinstance(p,str) or not p.startswith(OLD) for p in paths):
        raise Invalid('Packet index has duplicate or out-of-packet path')
    if OLD+'packet-index.json' in paths: raise Invalid('Packet index cannot index itself')
    return paths

def audit_candidate_packet(index_bytes: bytes, overrides: dict[str,bytes], baseline_index: dict):
    try: candidate=json.loads(index_bytes)
    except Exception as e: raise Invalid('Candidate packet index is not JSON') from e
    if candidate.get('format')!='worldatlas-geography-packet-index:v1' or candidate.get('issue')!=446:
        raise Invalid('Candidate packet index identity/version mismatch')
    paths=index_path_roster(candidate)
    expected=set(index_path_roster(baseline_index))
    if set(paths)!=expected: raise Invalid('Candidate packet inventory has omitted, extra or substituted files')
    files={x['path']:x for x in candidate['files']}
    for path in sorted(expected):
        raw=overrides.get(path)
        if raw is None: raw=git_blob(BASELINE,path)
        desc=files[path]
        if not isinstance(desc.get('bytes'),int) or desc['bytes']!=len(raw) or desc.get('sha256')!=sha(raw):
            raise Invalid(f'Packet descriptor byte/hash mismatch: {path}')
        if len(raw)>32*1024*1024: raise Invalid(f'Packet file exceeds original retention bound: {path}')
    return candidate

def feature_lookup(subject_ids):
    # Shared immutable helper reads the exact pinned world-index and checks all
    # 36 part files for duplicate/missing requested identities, while returning
    # ordinary descriptors only for actual containing parts.
    sys.path.insert(0,str(ROOT/'scripts'))
    from evidence.immutable import Baseline as ImmutableBaseline
    names=['data/world-index.json','data/hierarchy.json']
    # Every original packet file is an immutable baseline input, including the
    # index's full source/review/output inventory.
    index=json.loads(git_blob(BASELINE,OLD+'packet-index.json'))
    names += index_path_roster(index)
    names += [OLD+'packet-index.json']
    pins=descriptors(names)
    baseline=ImmutableBaseline(ROOT,BASELINE,pins)
    found,containing=baseline.subjects(subject_ids,'data/world-index.json')
    return baseline,found,containing,pins,index

def source_mapping(features):
    result={}
    for fid,feature in features.items():
        props=feature.get('properties') or {}; meta=props.get('metadata') or {}
        if fid.startswith('gb:PRY:ADM2:'):
            shape_id=fid.rsplit(':',1)[1]
            if meta.get('source_id')!='gb:PRY:ADM2' or meta.get('original_id')!=shape_id:
                raise Invalid(f'Native Paraguay baseline identity metadata disagree: {fid}')
            row={'source_shape_id':shape_id,'source_name':props.get('name'),'source_level':'ADM2',
                 'mapping_type':'individual native location','atlas_location_id':fid,'atlas_location_name':props.get('name')}
            if shape_id in result: raise Invalid(f'Duplicate native/member source mapping: {shape_id}')
            result[shape_id]=row
        for member in meta.get('source_member_ids',[]):
            if not isinstance(member,str) or not member.startswith('gb:PRY:ADM2:'): continue
            shape_id=member.rsplit(':',1)[1]
            if shape_id in result: raise Invalid(f'Duplicate native/member source mapping: {shape_id}')
            result[shape_id]={'source_shape_id':shape_id,'source_name':None,'source_level':'ADM2',
                'mapping_type':'member of atlas aggregate','atlas_location_id':fid,'atlas_location_name':props.get('name'),
                '_aliases':meta.get('search_aliases',[])}
    return result

def validate_crosswalk(raw: bytes, baseline_rows, expected_mapping, features):
    headers,rows=csv_rows(raw)
    wanted=['source_shape_id','source_name','source_level','mapping_type','atlas_location_id','atlas_location_name']
    if headers!=wanted: raise Invalid('Crosswalk columns or order differ from original contract')
    shape_ids=[r['source_shape_id'] for r in rows]
    if len(rows)!=247 or len(shape_ids)!=len(set(shape_ids)): raise Invalid('Crosswalk has duplicate, omitted or extra source IDs')
    if set(shape_ids)!=set(expected_mapping): raise Invalid('Crosswalk source IDs differ from exact baseline native/member roster')
    old_by_id={r['source_shape_id']:r for r in baseline_rows}
    if len(old_by_id)!=len(baseline_rows): raise Invalid('Pinned original crosswalk has duplicate source IDs')
    for r in rows:
        sid=r['source_shape_id']; exp=expected_mapping[sid]; old=old_by_id[sid]
        if r['source_name']!=old['source_name']: raise Invalid(f'Source name changed from pinned baseline row: {sid}')
        if r['source_level']!='ADM2' or old['source_level']!='ADM2': raise Invalid(f'Source level/type mismatch: {sid}')
        if r['mapping_type']!=exp['mapping_type']: raise Invalid(f'Mapping type disagrees with baseline native/member identity: {sid}')
        if r['atlas_location_id']!=exp['atlas_location_id']: raise Invalid(f'Atlas target disagrees with baseline native/member mapping: {sid}')
        if r['atlas_location_name']!=exp['atlas_location_name']: raise Invalid(f'Atlas target name disagrees with target feature: {sid}')
        if r['atlas_location_id']!=old['atlas_location_id'] or r['atlas_location_name']!=old['atlas_location_name']:
            raise Invalid(f'Atlas target differs from immutable original crosswalk: {sid}')
        if exp['mapping_type']=='individual native location':
            if r['source_name']!=exp['source_name']: raise Invalid(f'Native source name differs from target feature: {sid}')
        else:
            if r['source_name'] not in exp['_aliases']: raise Invalid(f'Aggregate member source name is not in baseline metadata aliases: {sid}')
    return rows

def validate_unit_parent_ledgers(unit_raw: bytes,parent_raw: bytes,scope_raw: bytes,features):
    scope=json.loads(scope_raw); ids=scope['member_location_ids']
    if len(ids)!=215 or len(set(ids))!=215: raise Invalid('Original scope is not the exact 215 unique rows')
    uh,units=csv_rows(unit_raw); ph,parents=csv_rows(parent_raw)
    unit_ids=[r.get('id') for r in units]
    if len(units)!=215 or len(set(unit_ids))!=215 or set(unit_ids)!=set(ids): raise Invalid('Unit review ledger is not exactly the 215 scope IDs')
    expected_parents={p['id'] for p in scope['province_scopes']}
    if len(expected_parents)!=32: raise Invalid('Pinned scope does not contain exactly 32 parents')
    grouped=defaultdict(set)
    for row in units:
        fid=row['id']; feat=features[fid]; props=feat['properties']
        if row['name']!=props.get('name') or row['parent_id']!=props.get('parent_id'):
            raise Invalid(f'Unit review identity/name/parent differs from pinned feature: {fid}')
        grouped[row['parent_id']].add(fid)
    if set(grouped)!=expected_parents: raise Invalid('Unit rows do not span exactly the 32 issue parents')
    parent_ids=[r.get('parent_id') for r in parents]
    if len(parents)!=32 or len(set(parent_ids))!=32 or set(parent_ids)!=expected_parents:
        raise Invalid('Parent review ledger is not exactly the 32 issue parents')
    for row in parents:
        expected=grouped[row['parent_id']]
        actual=set(filter(None,row['scoped_child_ids'].split('|')))
        if actual!=expected or len(actual)!=len(expected) or int(row['scoped_child_count'])!=len(expected):
            raise Invalid(f'Parent child inventory mismatch: {row["parent_id"]}')
    return units,parents

def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFD',str(value).casefold()) if unicodedata.category(c)!='Mn' and c.isalnum())

def verify_results(features,expected_map,scope,unit_rows,baseline_files):
    rows_by_path={f['path']:git_blob(BASELINE,f['path']) for f in baseline_files}
    old_results=json.loads(rows_by_path[OLD+'reproduction-results.json'])
    cross_ids=set(expected_map); source_mapping_result=expected_map
    area=dict(sorted(Counter(r['scope_area'] for r in unit_rows).items()))
    native=sum(r['mapping_type']=='individual native location' for r in source_mapping_result.values())
    aggregates=[r for r in source_mapping_result.values() if r['mapping_type']=='member of atlas aggregate']
    aggregate_targets={r['atlas_location_id'] for r in aggregates}
    scoped=set(scope['member_location_ids'])
    scoped_records=sum(1 for r in source_mapping_result.values() if r['atlas_location_id'] in scoped or r['atlas_location_id']=='atlas:multipart:eab6ecd59520b6841455')
    multipart=features['atlas:multipart:eab6ecd59520b6841455']['properties']['metadata']['source_member_ids']
    ury_old=json.loads(rows_by_path[OLD+'ury-gb-2017.geojson'])['features']
    ury_now=json.loads(rows_by_path[OLD+'ury-igm-current.geojson'])['features']
    current={norm(f['properties'].get('nam')):f for f in ury_now if f['properties'].get('USE_')!=1000}
    old={norm(f['properties']['shapeName']):f for f in ury_old}
    exact_results={
      'area_row_counts':area,'baseline_commit':'702a55f8e03a2442a153eb1176919feaf84eb115','distinct_parents':len({r['parent_id'] for r in unit_rows}),
      'issue':446,'negative_control_duplicate_scope_rejected':True,'owned_paths':[OLD],
      'paraguay_distinct_aggregates':len(aggregate_targets),'paraguay_native_baseline_count':native,
      'paraguay_scoped_input_source_records':scoped_records,'paraguay_scoped_multipart_members':len(multipart),
      'paraguay_source_features':len(source_mapping_result),'paraguay_source_ids_unique':len(cross_ids),
      'paraguay_source_members_via_aggregates':len(aggregates),'paraguay_source_records_mapped_once':len(source_mapping_result),
      'scope_baseline_matches':len(unit_rows),'scope_expected':215,'scope_unique':215,
      'uruguay_2017_source_count':len(ury_old),'uruguay_current_contested_extras':[f['properties'].get('nam') for f in ury_now if f['properties'].get('USE_')==1000],
      'uruguay_current_department_named_feature_count':len(current),'uruguay_current_official_features':len(ury_now),
      'uruguay_department_names_matching':len(set(old)&set(current)),
      'limitations':old_results['limitations']
    }
    if exact_results!=old_results: raise Invalid('Original reproduction results do not agree with checked baseline rows/features')
    return exact_results

def index_fixture(index, path, data):
    candidate=json.loads(json.dumps(index))
    record=next(x for x in candidate['files'] if x['path']==path)
    record['bytes']=len(data); record['sha256']=sha(data)
    return json.dumps(candidate,sort_keys=True,separators=(',',':')).encode()+b'\n'

def expect_reject(label, fn, contains=None):
    try: fn()
    except Invalid as e:
        if contains and contains not in str(e): raise Invalid(f'{label}: rejected for unexpected reason: {e}')
        return {'id':label,'outcome':'passed','rejection':str(e)}
    raise Invalid(f'Negative control was accepted: {label}')

def main():
    issue,contract,subject_ids=issue_contract()
    baseline,features,subject_files,baseline_files,packet_index=feature_lookup(subject_ids)
    if len(features)!=263: raise Invalid('Pinned feature inventory does not resolve all 263 exact subjects')
    scope_raw=git_blob(BASELINE,OLD+'scope.json'); unit_raw=git_blob(BASELINE,OLD+'unit-review.csv'); parent_raw=git_blob(BASELINE,OLD+'parent-review.csv')
    baseline_cross=git_blob(BASELINE,OLD+'pry-source-crosswalk.csv')
    cross_headers,baseline_rows=csv_rows(baseline_cross)
    expected=source_mapping(features)
    if len(expected)!=247: raise Invalid(f'Baseline source membership roster is not 247: {len(expected)}')
    original_cross=validate_crosswalk(baseline_cross,baseline_rows,expected,features)
    unit_rows,parent_rows=validate_unit_parent_ledgers(unit_raw,parent_raw,scope_raw,features)
    scope=json.loads(scope_raw)
    target_ids={r['atlas_location_id'] for r in original_cross}
    if len(target_ids)!=243 or set(subject_ids)!=(set(scope['member_location_ids'])|target_ids):
        raise Invalid('The 263 issue subjects are not exactly 215 scoped units union 243 Paraguay targets')
    # The original packet index is checked against every actual immutable file,
    # including all file size/hash descriptors, exact roster, and excluded self.
    audit_candidate_packet(git_blob(BASELINE,OLD+'packet-index.json'),{},packet_index)
    results=verify_results(features,expected,scope,unit_rows,baseline_files)
    # Verify the historical nine-file baseline pinned by #446 independently;
    # these bytes are not relabeled as current #1111 baseline data.
    historical=json.loads(git_blob(BASELINE,OLD+'baseline-files.json'))
    old_verified=[]
    for row in historical['files']:
        raw=git_blob(row['commit'],row['path'])
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']: raise Invalid(f'Historical #446 input pin mismatch: {row["path"]}')
        old_verified.append({'path':row['path'],'commit':row['commit'],'bytes':len(raw),'sha256':sha(raw)})
    if len(old_verified)!=9: raise Invalid('Expected nine historical #446 baseline input pins')
    controls=[]
    pristine={}
    # The bad rehashed candidate passes packet byte/hash/inventory audit before
    # being rejected by the exact baseline source-ID to Atlas-target mapping.
    altered=list(original_cross); target=next(i for i,r in enumerate(altered) if r['source_shape_id']=='47425931B83994928044563')
    wrong=json.loads(json.dumps(altered[target])); wrong['atlas_location_id']='country-SPI'; wrong['atlas_location_name']=features['country-SPI']['properties']['name']; altered[target]=wrong
    def encode(rows):
        out=io.StringIO(newline=''); writer=csv.DictWriter(out,fieldnames=cross_headers,lineterminator='\n'); writer.writeheader(); writer.writerows(rows); return out.getvalue().encode()
    bad_cross=encode(altered); bad_index=index_fixture(packet_index,OLD+'pry-source-crosswalk.csv',bad_cross)
    audit_candidate_packet(bad_index,{OLD+'pry-source-crosswalk.csv':bad_cross},packet_index)
    controls.append(expect_reject('rehashed-wrong-atlas-target',lambda:validate_crosswalk(bad_cross,baseline_rows,expected,features),'Atlas target disagrees'))
    for field,value,label,err in [
      ('atlas_location_name','Made-up target','wrong-atlas-name','Atlas target name disagrees'),
      ('mapping_type','member of atlas aggregate','wrong-mapping-type','Mapping type disagrees'),
      ('source_name','Fabricated Paraguay name','wrong-source-name','Source name changed'),
      ('source_level','ADM1','wrong-source-level','Source level/type mismatch')]:
        changed=list(original_cross); row=dict(changed[target]); row[field]=value; changed[target]=row; raw=encode(changed); idx=index_fixture(packet_index,OLD+'pry-source-crosswalk.csv',raw)
        audit_candidate_packet(idx,{OLD+'pry-source-crosswalk.csv':raw},packet_index)
        controls.append(expect_reject(label,lambda raw=raw:validate_crosswalk(raw,baseline_rows,expected,features)))
    agg_index=next(i for i,r in enumerate(original_cross) if r['mapping_type']=='member of atlas aggregate')
    changed=list(original_cross); changed[agg_index]=dict(changed[agg_index]); changed[agg_index]['source_name']='Fabricated Aggregate Member'
    raw=encode(changed); idx=index_fixture(packet_index,OLD+'pry-source-crosswalk.csv',raw)
    audit_candidate_packet(idx,{OLD+'pry-source-crosswalk.csv':raw},packet_index)
    controls.append(expect_reject('wrong-aggregate-source-name',lambda:validate_crosswalk(raw,baseline_rows,expected,features),'Source name changed'))
    duplicate=list(original_cross); duplicate[-1]=dict(duplicate[0]); raw=encode(duplicate); idx=index_fixture(packet_index,OLD+'pry-source-crosswalk.csv',raw)
    audit_candidate_packet(idx,{OLD+'pry-source-crosswalk.csv':raw},packet_index)
    controls.append(expect_reject('duplicate-and-omitted-source-row',lambda:validate_crosswalk(raw,baseline_rows,expected,features),'duplicate, omitted or extra'))
    omitted=encode(original_cross[:-1]); idx=index_fixture(packet_index,OLD+'pry-source-crosswalk.csv',omitted)
    audit_candidate_packet(idx,{OLD+'pry-source-crosswalk.csv':omitted},packet_index)
    controls.append(expect_reject('omitted-source-row',lambda:validate_crosswalk(omitted,baseline_rows,expected,features),'duplicate, omitted or extra'))
    foreign=list(original_cross); foreign[0]=dict(foreign[0]); foreign[0]['source_shape_id']='27058087B22084813565519'; raw=encode(foreign); idx=index_fixture(packet_index,OLD+'pry-source-crosswalk.csv',raw)
    audit_candidate_packet(idx,{OLD+'pry-source-crosswalk.csv':raw},packet_index)
    controls.append(expect_reject('foreign-vintage-or-scope-row',lambda:validate_crosswalk(raw,baseline_rows,expected,features)))
    wrong_inventory=json.loads(json.dumps(packet_index)); wrong_inventory['files']=wrong_inventory['files'][:-1]
    controls.append(expect_reject('candidate-packet-index-omission',lambda:audit_candidate_packet(json.dumps(wrong_inventory).encode(),{},packet_index),'omitted, extra or substituted'))
    # Unit and parent ledgers also fail exact-scope mutation even after the
    # candidate packet index is coherently rehashed.
    uh,units=csv_rows(unit_raw); changed_units=[dict(r) for r in units]; changed_units[-1]['id']=changed_units[0]['id']
    buff=io.StringIO(newline=''); w=csv.DictWriter(buff,fieldnames=uh,lineterminator='\n');w.writeheader();w.writerows(changed_units); bad_units=buff.getvalue().encode()
    idx=json.loads(json.dumps(packet_index)); rec=next(x for x in idx['files'] if x['path']==OLD+'unit-review.csv');rec.update(bytes=len(bad_units),sha256=sha(bad_units))
    audit_candidate_packet(json.dumps(idx).encode(),{OLD+'unit-review.csv':bad_units},packet_index)
    controls.append(expect_reject('rehashed-duplicate-unit-id',lambda:validate_unit_parent_ledgers(bad_units,parent_raw,scope_raw,features),'Unit review ledger'))
    ph,parents=csv_rows(parent_raw); changed_parents=[dict(r) for r in parents]; changed_parents[0]['scoped_child_ids']='country-SPI'
    buff=io.StringIO(newline='');w=csv.DictWriter(buff,fieldnames=ph,lineterminator='\n');w.writeheader();w.writerows(changed_parents);bad_parents=buff.getvalue().encode()
    bad_parent_index=index_fixture(packet_index,OLD+'parent-review.csv',bad_parents)
    audit_candidate_packet(bad_parent_index,{OLD+'parent-review.csv':bad_parents},packet_index)
    controls.append(expect_reject('rehashed-wrong-parent-child-inventory',lambda:validate_unit_parent_ledgers(unit_raw,bad_parents,scope_raw,features),'Parent child inventory'))
    controls.sort(key=lambda x:x['id'])
    if len(controls)!=12: raise Invalid('Expected twelve distinct negative controls')
    mapping_rows=[]
    for sid in sorted(expected):
        row=expected[sid].copy(); row.pop('_aliases',None)
        if row['mapping_type']=='member of atlas aggregate': row['source_name']=next(r['source_name'] for r in original_cross if r['source_shape_id']==sid)
        mapping_rows.append(row)
    map_doc={'version':1,'issue':1111,'baseline_commit':BASELINE,'basis':'Pinned current Atlas source IDs and aggregate member metadata cross-checked against immutable original #446 crosswalk names; no independent Paraguay original-source geometry claim.','rows':mapping_rows}
    result={
      'version':1,'issue':1111,'issue_body_sha256':EXPECTED_ISSUE_BODY_SHA256,'baseline_commit':BASELINE,'exact_issue_subject_count':len(subject_ids),
      'scope_unit_count':len(unit_rows),'scope_parent_count':len(parent_rows),'source_record_count':len(expected),
      'native_location_count':sum(x['mapping_type']=='individual native location' for x in expected.values()),
      'aggregate_member_count':sum(x['mapping_type']=='member of atlas aggregate' for x in expected.values()),
      'unique_target_count':len(target_ids),'issue_scope_union_matches':True,
      'packet_index_file_count':len(packet_index['files']),'packet_index_files_hash_and_size_verified':len(packet_index['files']),
      'historical_original_baseline_files_verified':len(old_verified),'source_map_sha256':sha(json.dumps(map_doc,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()+b'\n'),
      'original_numeric_results_recomputed':True,'original_spatial_source_reproduction':'not rerun: exact 45,589,273-byte geoBoundaries source exceeds retained-file ceiling; source roster/target map are checked against baseline metadata only',
      'boundary_or_legal_accuracy':'not established','full historical/source geometry approval':'not established'
    }
    out=ROOT/OWNED
    (out/'expected-crosswalk-map.json').write_text(json.dumps(map_doc,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    (out/'verification-results.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    (out/'adversarial-controls.json').write_text(json.dumps({'version':1,'issue':1111,'controls':controls,'all_passed':True},ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'result':result,'controls':len(controls),'control_ids':[x['id'] for x in controls]},ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    try: main()
    except (Invalid,KeyError,ValueError,AssertionError) as e:
        print(f'validation failed: {e}',file=sys.stderr); sys.exit(1)
