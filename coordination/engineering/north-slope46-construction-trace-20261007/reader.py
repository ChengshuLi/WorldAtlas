"""Original whole-byte inputs and exact complete46 source/context bindings."""
import hashlib,json,pathlib,subprocess,sys,struct
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'legacy'))
import producer as old
import transport
LIMIT=33554432
NUMERIC='coordination/engineering/complete-numeric-closure-diagnosis-20261007/'
PHYSICAL='coordination/engineering/global-physical-comparison-20261006/'
ROUTING='coordination/engineering/global-actionability-routing-20261007/results/'
canonical=old.immutable.canonical_json
digest=old.digest

def validate_roster(rows,expected):
    names=[row['id'] for row in rows]
    if len(names)!=len(set(names)) or set(names)!=set(expected):
        raise ValueError('Foreign, duplicate or omitted complete scoped component')

def query_roster(queries,pin):
    if len(queries)!=pin['count'] or digest(canonical(queries))!=pin['ordered_whole_sha256']:
        raise ValueError('Missing, changed, duplicate or reordered whole query piece')


def whole(repo,pin):
    if pin.get('bytes',LIMIT+1)>LIMIT or pin.get('uncompressed_bytes',0)>LIMIT:
        raise ValueError('Declared ordinary input bounds')
    raw=old.inputs.ordinary_git(repo,pin['commit'],pin['path'],pin)
    meta=subprocess.check_output(['git','-C',str(repo),'ls-tree','-z',pin['commit'],'--',pin['path']]).decode().rstrip('\0').split('\t')[0].split()
    if meta[0]!=pin['mode'] or meta[2]!=pin['blob']:
        raise ValueError('Original whole mode/OID binding differs')
    return old.inputs.checked_decoded(raw,pin)

def query_bind(query,meta):
    fields={'source_id':meta['id'],'source_level':meta['level'],'source_container':meta['container'],
            'source_record_sha256':meta['record_sha256'],'source_pointset_sha256':meta['decoded_pointset_binary64_sha256']}
    if any(query.get(k)!=v for k,v in fields.items()) or query.get('periodic_offset') not in (-360,0,360):
        raise ValueError('Source record/container/level/native-frame binding differs')

def load(repo):
    index=json.loads((HERE/'input-index.json').read_bytes());pins=index['source_files']
    if len(pins)!=246 or len({(p['commit'],p['path'])for p in pins})!=246 or sum(p['bytes']for p in pins)!=237274443:
        raise ValueError('Incomplete admitted ordinary input closure')
    receipts=[]
    for pin in pins:
        body=whole(repo,pin)
        receipts.append(dict(commit=pin['commit'],path=pin['path'],mode=pin['mode'],blob=pin['blob'],bytes=pin['bytes'],sha256=pin['sha256'],decoded_bytes=len(body),decoded_sha256=digest(body)))
    print('All246 whole original inputs authenticated',flush=True)
    scope=json.loads((HERE/'scope.json').read_bytes());features_raw=(HERE/'scope-candidates.json').read_bytes()
    if digest(features_raw)!=scope['candidate_file_sha256']:raise ValueError('Changed scoped pointset preparation')
    prepared=json.loads(features_raw);expected=scope['family']['complete_component_ids'];validate_roster(prepared,expected)
    if len(expected)!=46 or len(set(expected))!=46:raise ValueError('Incomplete46 family')
    routing={r['component']:r for r in scope['routing_rows']}
    if set(routing)!=set(expected):raise ValueError('Incomplete routing scope')
    config=json.loads((HERE/'legacy/input-config.json').read_bytes())
    derived=dict(config,inputs=[p for p in config['inputs']if p['kind']!='archive_part'])
    current,lineage,candidate_receipts,reconstructor,audit=old.load_candidates(repo,derived)
    if len(current['components'])!=95173 or len({f['id']for f in current['components']})!=95173:raise ValueError('Incomplete current reconstruction')
    lookup={f['id']:f for f in current['components']};selected={}
    for feature in prepared:
        identity=feature['id'];actual=lookup[identity];row=routing[identity]
        if canonical(actual)!=canonical(feature) or digest(canonical(feature))!=row['current_feature_sha256'] or digest(canonical(feature['geometry']))!=row['current_geometry_sha256']:
            raise ValueError('Whole candidate/current context binding differs')
        selected[identity]=feature
    class Context:
        def component(self,row):
            f=lookup[row['component_id']]
            return {'original_context':f['properties'],'candidate_feature_sha256':digest(canonical(f)),'candidate_geometry_sha256':digest(canonical(f['geometry']))}
    context=Context();rows={};restore=[]
    originals={p['original_relation']['original_path']:p for p in pins if p.get('original_relation') and 'original_path' in p['original_relation']}
    physical_report=json.loads(whole(repo,originals[PHYSICAL+'results/report.json']))
    descriptors={d['path']:d for d in physical_report['products']}
    names=sorted({routing[i]['whole_physical_containing_file']for i in expected})
    if len(names)!=33:raise ValueError('Incomplete33 containing physical shards')
    for name in names:
        pin=originals[name];raw=whole(repo,pin);original=descriptors[name.rsplit('/',1)[-1]];transport.original_bounds(original)
        restored=bytearray()
        for ordinal,line in enumerate(raw.splitlines()):
            packed=json.loads(line);row=transport.restore_row(packed,'components',context);body=canonical(row)
            if len(restored)+len(body)>LIMIT:raise ValueError('Original restored ordinary bound')
            restored.extend(body)
            identity=row['component_id']
            if identity in expected:
                if identity in rows or digest(canonical(packed))!=routing[identity]['whole_physical_row_sha256']:raise ValueError('Duplicate or changed packed physical row')
                # Literal aliases for support are expanded exactly as the original104 caller.
                for key,value in row.get('complete_support',{}).items():
                    values=value.values() if key=='hierarchy_disagreements' else [value]
                    for evidence in values:
                        if evidence.get('kind')=='complete-candidate-alias':evidence['geometry']=selected[identity]['geometry']
                rows[identity]=row
        if len(restored)!=original['uncompressed_bytes'] or digest(restored)!=original['uncompressed_sha256']:raise ValueError('Complete original104 physical raw restoration differs')
        encoded=old.immutable.deterministic_gzip(restored)
        if len(encoded)!=original['bytes'] or digest(encoded)!=original['sha256']:raise ValueError('Complete original104 physical gzip restoration differs')
        restore.append(dict(original,actual_original_restoration=True))
    if set(rows)!=set(expected) or sum(len(r['query_relations'])for r in rows.values())!=209:raise ValueError('Incomplete46/209 original rows')
    for identity,row in rows.items():query_roster(row['query_relations'],scope['original_query_roster'][identity])
    # Stream all complete accepted numeric rows; preserve original28 dispositions.
    diagnoses={}
    for pin in pins:
        if pin['path'].startswith(NUMERIC+'r1/diagnoses-'):
            for line in whole(repo,pin).splitlines():
                row=json.loads(line);identity=row.get('component_id')
                if identity in expected:
                    if identity in diagnoses:raise ValueError('Duplicate numerical sibling')
                    diagnoses[identity]=row
    if len(diagnoses)!=28:raise ValueError('Incomplete28 accepted numerical siblings')
    # Whole native member original bytes; parse every header, decode only contributing
    # identities and complete parent chains. No source resampling or online retrieval.
    native=old.original_native(repo,config);wanted={q['source_id']for row in rows.values()for q in row['query_relations']}
    records={};headers={};offset=ordinal=0
    while offset<len(native):
        if offset+44>len(native):raise ValueError('Trailing original native bytes')
        values=old.comparison.HEADER.unpack(native[offset:offset+44]);length=44+values[1]*8
        if offset+length>len(native) or values[0]in headers:raise ValueError('Incomplete/duplicate native record')
        headers[values[0]]=(offset,length,ordinal,values);offset+=length;ordinal+=1
    if ordinal!=188612 or offset!=len(native):raise ValueError('Incomplete native header roster')
    closure=set(wanted)
    for identity in tuple(wanted):
        visited=set();cur=identity
        while headers[cur][3][2]&255 in (2,3,4):
            if cur in visited:break
            visited.add(cur);parent=headers[cur][3][9]
            if parent not in headers:break
            closure.add(parent);cur=parent
    for identity in sorted(closure):
        offset,length,ordinal,values=headers[identity];meta,geometry=old.comparison.decode_record(native[offset:offset+44],native[offset+44:offset+length],ordinal,offset)
        records[identity]=(meta,geometry)
    native_proof={'whole_original_bytes':len(native),'whole_original_sha256':digest(native),'complete_headers':len(headers),'contributing_ids':sorted(wanted),'parent_closure_ids':sorted(closure)}
    for row in rows.values():
        for query in row['query_relations']:query_bind(query,records[query['source_id']][0])
    # Scoped contact equality at actual author base, not a relabeling of global v8.
    contact='atlas:physical:01966024a7da3c19f62b';contact_pin=next(p for p in pins if p['path']=='data/geography/part-25.json')
    baseline_raw=whole(repo,contact_pin)
    baseline_contact=next(f for f in json.loads(baseline_raw)['features']if f['id']==contact)
    actual_raw=subprocess.check_output(['git','-C',str(repo),'show',scope['current_base']+':data/geography/part-25.json'])
    actual_contact=next(f for f in json.loads(actual_raw)['features']if f['id']==contact)
    if actual_raw!=baseline_raw:raise ValueError('Current whole scoped contact containing file changed; declaration refresh required')
    current_contact_proof={'commit':scope['current_base'],'path':'data/geography/part-25.json','bytes':len(actual_raw),'sha256':digest(actual_raw),'whole_byte_equal_original_containing_input':True}
    if canonical(actual_contact)!=canonical(baseline_contact):raise ValueError('Current scoped contact changed; coordination required')
    del native,current,lookup
    return {'scope':scope,'features':selected,'physical':rows,'diagnoses':diagnoses,'sources':records,
            'receipts':receipts,'candidate_input_receipts':candidate_receipts,'reconstructor':reconstructor,'original_physical_restoration':restore,'native_proof':native_proof,'contact':baseline_contact,'current_contact_proof':current_contact_proof}
