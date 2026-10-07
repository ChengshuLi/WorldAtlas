"""Fixed predecessor custody for the bounded1270 diagnostic; original reader reused."""
import pathlib,sys,json,gzip
R=pathlib.Path(__file__).resolve().parents[3]
OLD_PREFIX='coordination/engineering/retired-member-comparison-1255-20261006'
INPUT_COMMIT='ec4783fd9b2d2366ef00869c44b279f8d62add36'
sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(R/OLD_PREFIX))
from evidence.immutable import canonical_json as canon
from reader import Inputs,SHA,validate_family_scope,validate_pointsets
M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f';H='549cc2a863d4a487a662c2613e4d02888e39b5ba';N='a26f8d8b50e7349054b86e70d1e6e552a9a2b0fd';S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98'
ROSTERS={'unknown_components':(6281,'95b2777dbac0beae03680e5a68cd6742c7c04a09a99769427797b5113b7c01a6'),'families':(575,'8d63c07bf9e79eb1228fb0c527d6447f5651ca68e243520478d20fa9060db884'),'context_components':(12382,'82d3061e081a3443139214abb2f7fde0364904e48df9d0a0546427a113d693b0'),'members':(600,'83f62e9e329fcce26345dd551264c6d7749fc3ca3a5668f5647368fa4c28a954'),'contacts':(202,'799eee9bac52f9a4ee1b0996e4dc3758c22067f82292bf15987b3bd5d50a482a')}

def load_original_inputs():
    inputs=Inputs(R,INPUT_COMMIT,OLD_PREFIX);index_raw=inputs.read('input-index.json')
    if SHA(index_raw)!='d5c79868705da0900253f2a56a2700b193bc0aff71589e33104eb1646a7cb2e3':raise ValueError('Original input index pin differs')
    index=json.loads(index_raw)
    scope=json.loads(inputs.read(index['scope']['path'],index['scope'],decode=True));plan=json.loads(inputs.read(index['complete_remaining_plan']['path'],index['complete_remaining_plan'],decode=True))
    allocations=[r for r in plan['complete_family_allocations']if r['disjoint_allocation']==scope['predicate'].split(' == ')[1]]
    if sorted(r['family']for r in allocations)!=scope['family_ids']or sorted(i for r in allocations for i in r['component_ids'])!=scope['component_ids']:raise ValueError('Full-family scope differs')
    report=inputs.original(N,'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json',index);families={};fidset=set(scope['family_ids']);idset=set(scope['component_ids'])
    for pin in report['outputs']['current-batches']:
        for row in inputs.original(N,pin['path'],index):
            if row['id']in fidset:
                if row['id']in families:raise ValueError('Duplicate family')
                families[row['id']]=row
    if set(families)!=fidset or sorted(i for row in families.values()for i in row['component_ids'])!=scope['component_ids']:raise ValueError('Complete component/family membership mismatch')
    if sorted({i for f in families.values()for i in f['contact_ids']})!=scope['contact_ids']:raise ValueError('Complete contact roster differs')
    for f in families.values():
        if len(f['component_ids'])!=f['component_count']or f['component_ids']!=sorted(set(f['component_ids']))or SHA(canon(f['component_ids']))!=f['component_ids_sha256']:raise ValueError('Family roster count/digest differs')
    validate_family_scope(scope,families)
    ir=inputs.original(M,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json',index);features={}
    for pin in ir['complete_products']['components']:
        path=next(p['path']for p in ir['source_descriptors']if p['sha256']==pin['sha256'])
        for f in inputs.original(M,path,index)['features']:
            if f['id']in idset:
                if f['id']in features:raise ValueError('Duplicate original component')
                features[f['id']]=f
    successor=inputs.original(S,'coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json',index)
    delta=inputs.original(S,'coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz',index)
    if set(delta['removed_ids'])&idset:raise ValueError('Removed component in selected scope')
    for f in delta['upsert_records']:
        if f['id']in idset:features[f['id']]=f
    expected_features={r['id']:r for r in scope['existing_current_component_and_member_pins']}
    if set(features)!=idset:raise ValueError('Missing current component')
    for i,f in features.items():
        if SHA(canon(f))!=expected_features[i]['canonical_feature_sha256']or SHA(canon(f['geometry']))!=expected_features[i]['geometry_sha256']:raise ValueError('Current full feature/geometry mismatch')
    contexts={};cr=inputs.original(H,'coordination/engineering/worldwide-contexts-1184-20261006/run-one/report.json',index)
    for pin in cr['outputs']:
        for row in inputs.original(H,pin['path'],index):
            if row['id']in contexts:raise ValueError('Duplicate original context')
            contexts[row['id']]=SHA(canon(row))  # Full bytes/fields consumed and retained; keep compact roster in memory.
    if len(contexts)!=49625 or not set(scope['contact_ids'])<=set(contexts):raise ValueError('Incomplete context/contact closure')
    archive=inputs.archive(index);members={r['id']:r for r in archive['locations']}
    if len(members)!=19050 or len(archive['locations'])!=19050:raise ValueError('Duplicate archive membership')
    if not set(scope['member_ids'])<=set(members):raise ValueError('Original member absent')
    for binding in scope['retired_member_complete_record_pins']:
        r=members[binding['id']]
        if SHA(canon(r))!=binding['canonical_record_sha256']or SHA(canon(r['geometry']))!=binding['canonical_geometry_sha256']or canon(r['metadata'])!=canon(binding['metadata']):raise ValueError('Changed original member geometry/metadata representation')
    validate_pointsets(scope,features,members)
    # Every declared alias is authenticated, including actual historical recipe and
    # metadata context not consumed by the literal geometry loop.
    for a in index['aliases']:inputs.original(a['original']['commit'],a['original']['path'],index,parse=False)
    for a in index['attribution_context']:inputs.read(a['ordinary']['path'],a['ordinary'])
    return inputs,scope,families,features,members


def check_rosters(rosters):
    if set(rosters)!=set(ROSTERS):raise ValueError('Incomplete bounded roster fields')
    for key,values in rosters.items():
        expected_count,expected_sha=ROSTERS[key]
        if values!=sorted(set(values)) or len(values)!=expected_count or SHA(canon(values))!=expected_sha:
            raise ValueError('Complete '+key+' scope/digest differs')


def load_complete_scientific_inputs(inputs,families):
    raw=inputs.read('run-one/report.json')
    if SHA(raw)!='13cd9b18fae16f1ce0a2197fcb832ca6da595168bb58a23b1f85c8998590a6c7':raise ValueError('Original full report pin differs')
    report=json.loads(raw);unknown_raw=inputs.read('diagnostic-unknowns.json.gz')
    if SHA(unknown_raw)!='c798574769811cec2075e28885427c7267c5bcf26b27f559e8f976759ceba614':raise ValueError('Original unknown aggregation pin differs')
    unknown=json.loads(gzip.decompress(unknown_raw));inputs.used[OLD_PREFIX+'/diagnostic-unknowns.json.gz'].update(decoded_bytes=len(gzip.decompress(unknown_raw)),decoded_sha256=SHA(gzip.decompress(unknown_raw)))
    def read(pin):return json.loads(inputs.read('run-one/'+pin['path'],pin,decode='decoded_sha256'in pin))
    index=read(report['object_index']);objects={}
    for pin in index['shards']:
        values=read(pin)
        if len(values)!=pin['records']:raise ValueError('Original object shard count differs')
        for value in values:
            h=value['id']
            if h in objects or SHA(canon(value['geometry']))!=h:raise ValueError('Duplicate/changed original full pointset')
            objects[h]=value['geometry']
    for h,entry in index['objects'].items():
        if entry['codec']=='canonical-json-exact-byte-fragments':
            body=[];offset=0
            for pin in entry['parts']:
                if pin['offset']!=offset:raise ValueError('Original pointset fragment offset differs')
                b=inputs.read('run-one/'+pin['path'],pin,decode=True);body.append(b);offset+=len(b)
            b=b''.join(body)
            if len(b)!=entry['canonical_bytes'] or SHA(b)!=h or h in objects:raise ValueError('Original complete pointset reconstruction differs')
            objects[h]=json.loads(b)
        elif entry['codec']!='canonical-json-object-in-indexed-shard':raise ValueError('Unsupported original pointset codec')
    if set(objects)!=set(index['objects']):raise ValueError('Incomplete original pointset index')
    for h,g in objects.items():
        if SHA(canon(g))!=h or len(canon(g))!=index['objects'][h]['canonical_bytes']:raise ValueError('Whole original geometry differs')
    family_records={};family_references={}
    for pin in report['family_outputs']:
        values=read(pin)
        if len(values)!=pin['records']:raise ValueError('Original family shard count differs')
        for n,value in enumerate(values):
            fid=value['family']['id']
            if fid in family_records or fid not in families or canon(value['family'])!=canon(families[fid]):raise ValueError('Original full family reassigned/missing')
            family_records[fid]=value;family_references[fid]={'commit':INPUT_COMMIT,'path':OLD_PREFIX+'/run-one/'+pin['path'],'file_sha256':pin['sha256'],'record_index':n,'canonical_record_sha256':SHA(canon(value))}
    if set(family_records)!=set(families):raise ValueError('Original full family closure incomplete')
    original_rows={};row_references={}
    for pin in report['component_outputs']:
        values=read(pin)
        if len(values)!=pin['records']:raise ValueError('Original component shard count differs')
        for n,value in enumerate(values):
            i=value['component'];fid=value['family']
            if i in original_rows or fid not in family_records or i not in families[fid]['component_ids']:raise ValueError('Original component duplicated/reassigned')
            f=family_records[fid]
            checks={'complete_member_ids':f['complete_original_member_ids'],'source_union_reference':f['literal_member_union'],'contacts':f['family']['contact_ids'],'edge_neighbor_ids':f['family']['edge_neighbor_ids'],'existing_related_issues':f['family']['existing_related_issues'],'original_native_scope_bucket':f['family']['grouping']['observed_scope_bucket']}
            if any(canon(value.get(k))!=canon(v)for k,v in checks.items()):raise ValueError('Original immutable component family/context extras differ')
            original_rows[i]=value;row_references[i]={'commit':INPUT_COMMIT,'path':OLD_PREFIX+'/run-one/'+pin['path'],'file_sha256':pin['sha256'],'record_index':n,'canonical_record_sha256':SHA(canon(value))}
    if len(original_rows)!=20032 or sorted(original_rows)!=sorted(i for f in families.values()for i in f['component_ids']):raise ValueError('Original complete component closure differs')
    selected=sorted(r['component']for r in unknown['complete_unknown_records']);fids=sorted({r['family']for r in unknown['complete_unknown_records']})
    if len(selected)!=len(set(selected)) or selected!=sorted(i for i,r in original_rows.items()if r['status']=='unknown-numerical-partition-disagreement'):raise ValueError('Unknown scope omitted/duplicated/promoted')
    rosters={'unknown_components':selected,'families':fids,'context_components':sorted(i for f in fids for i in families[f]['component_ids']),'members':sorted({i for f in fids for i in family_records[f]['complete_original_member_ids']}),'contacts':sorted({i for f in fids for i in families[f]['contact_ids']})}
    check_rosters(rosters)
    return report,objects,family_records,original_rows,family_references,row_references,rosters
