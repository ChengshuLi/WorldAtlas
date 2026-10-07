"""Directed actual-method and custody failures; no whole-cohort generation."""
import copy
from fractions import Fraction
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from shapely.geometry import box, Polygon, shape
import diagnose
import kernel
import reader

HERE=Path(__file__).resolve().parent
records=[]

def check(name,condition):
    if not condition:raise AssertionError(name)
    records.append(dict(name=name,result='PASS'))

def rejected(name,call,reason=None):
    try:call()
    except (ValueError,FileNotFoundError) as error:
        if reason and reason not in str(error):raise AssertionError(name+': wrong rejection '+str(error))
        records.append(dict(name=name,result='PASS',actual_rejection=str(error)))
    else:raise AssertionError(name+': failed to reject')

def main():
    with patch.object(diagnose,'git',side_effect=AssertionError('Git must not run')):
        for value in ('main','abc','A'*40,'a'*39,'--output=unsafe'):
            rejected('immutable-selector-before-Git:'+value,lambda:diagnose.authenticate(HERE,value),'lowercase40hex')
    with tempfile.TemporaryDirectory(dir=HERE/'.cache') as directory:
        root=Path(directory)
        body=reader.canonical({'original':'complete'})
        raw=gzip.compress(body,mtime=0);(root/'positive.gz').write_bytes(raw)
        pin=dict(path='positive.gz',bytes=len(raw),sha256=reader.digest(raw),uncompressed_bytes=len(body),uncompressed_sha256=reader.digest(body))
        check('ordinary-positive-whole-byte-reader',reader.checked(root,pin)==body)
        for key,value in [('sha256','0'*64),('bytes',len(raw)+1),('uncompressed_sha256','0'*64),('uncompressed_bytes',len(body)+1),('path','missing')]:
            changed=dict(pin,**{key:value});rejected('whole-input-tamper:'+key,lambda:reader.checked(root,changed))
        for path in ('../escape','/absolute','a//b','a/./b','a\\b'):
            rejected('unsafe-input-path:'+path,lambda:reader.safe_path(root,path))
        (root/'linked.gz').symlink_to(root/'positive.gz')
        rejected('leaf-input-symlink',lambda:reader.safe_path(root,'linked.gz'),'symlink')
        (root/'linked-directory').symlink_to(root,target_is_directory=True)
        rejected('ancestor-input-symlink',lambda:reader.safe_path(root,'linked-directory/positive.gz'),'symlink')
        rejected('outside-owned-output',lambda:diagnose.output_guard(HERE,HERE/'outside-cache-output'),'owned cache')
    candidate=box(0,0,4,4)
    triangle=Polygon([(1,1),(2,1),(1,2),(1,1)])
    diagnosis=kernel.point_diagnostics(candidate,triangle)
    check('triangle-exact-derived-centroid-inside',diagnosis['status']=='diagnostic' and diagnosis['triangles'][0]['interior_witness_certified'] and diagnosis['triangles'][0]['exact_candidate_state']=='inside')
    check('derived-centroid-keeps-rational-third',any(x['denominator']=='3' for x in diagnosis['triangles'][0]['exact_rational_centroid']))
    check('derived-centroid-not-rounded-for-exact-membership',diagnosis['triangles'][0]['floating_observation']=='not-computed-for-derived-rational-point')
    outside=kernel.point_diagnostics(candidate,box(5,5,6,6))
    check('real-outside-gap-vertices-preserved',outside['status']=='diagnostic' and all(x['exact_candidate_state']=='outside' for x in outside['vertices']))
    check('nontriangle-has-no-invented-interior-certification',outside['nontriangle_polygons']==[dict(polygon=0,interior_witness='not-certified')] and outside['triangles']==[])
    contact=kernel.point_diagnostics(candidate,box(4,0,5,1))
    check('exact-contact-boundary-not-inside',any(x['exact_candidate_state']=='boundary' for x in contact['vertices']))
    hole=Polygon([(0,0),(4,0),(4,4),(0,4),(0,0)],holes=[[(1,1),(1,3),(3,3),(3,1),(1,1)]])
    hole_probe=kernel.point_diagnostics(hole,triangle)
    check('candidate-hole-whole-member-preserved',hole_probe['status']=='diagnostic' and hole_probe['triangles'][0]['exact_candidate_state']=='outside')
    bow=Polygon([(0,0),(2,2),(0,2),(2,0),(0,0)])
    invalid=kernel.point_diagnostics(bow,triangle)
    check('invalid-candidate-no-probe-approval',invalid['status']=='invalid' and invalid['vertices']==[] and not invalid['whole_component_certification'])
    none=kernel.point_diagnostics(candidate,shape({'type':'GeometryCollection','geometries':[]}))
    check('empty-nonpolygon-retained-unsupported',none['status']=='unsupported' and none['triangles']==[])
    unsupported=kernel.point_diagnostics(candidate,Polygon([(0,0),(1,0),(1,1),(0,0)]))
    check('triangle-probe-does-not-certify-wholecomponent',unsupported['whole_component_certification'] is False and unsupported['partition_repair_approval'] is False)
    gp=kernel.exact.prepare_geometry(kernel.ordinary_mapping(candidate))
    check('unchanged-helper-accepts-internal-rational-query',kernel.exact.geometry_state((Fraction(1,3),Fraction(1,3)),gp)=='inside')
    rejected('public-helper-rejects-rational-as-binary64',lambda:kernel.exact.point([Fraction(1,3),Fraction(1,3)]),'json-number')
    actual_scope=json.loads(gzip.decompress((HERE/'scope.json.gz').read_bytes()))
    check('actual-complete26276-scope-positive',len(reader.scope_rosters(actual_scope)[0])==26276)
    for name,change in [('missing',lambda s:s['rows'].pop()),
        ('duplicate',lambda s:s['rows'].__setitem__(0,s['rows'][1])),
        ('foreign-complement',lambda s:s['complement_ids'].__setitem__(0,s['rows'][0]['component'])),
        ('omitted-complement',lambda s:s['complement_ids'].pop())]:
        changed=copy.deepcopy(actual_scope);change(changed)
        rejected('actual-scope-roster:'+name,lambda:reader.scope_rosters(changed))
    feature=dict(type='Feature',id='complete-original',properties={'metadata':{'original':'retained'}},geometry=kernel.ordinary_mapping(candidate))
    binding=dict(current_feature_sha256=reader.digest(reader.canonical(feature)),current_geometry_sha256=reader.digest(reader.canonical(feature['geometry'])))
    reader.current_feature(feature,binding);check('whole-current-feature-positive',True)
    for name,mutate in [('pointset',lambda f:f['geometry']['coordinates'][0][0].__setitem__(0,99)),
                         ('original-context',lambda f:f['properties']['metadata'].__setitem__('original','changed'))]:
        changed=copy.deepcopy(feature);mutate(changed)
        rejected('whole-current-feature:'+name,lambda:reader.current_feature(changed,binding),'feature/pointset')
    sample=actual_scope['rows'][0]
    row={key:sample[key] for key in ('current_feature_sha256','current_geometry_sha256','whole_physical_row_sha256','family','operational_batch')}
    line=reader.canonical(row).rstrip(b'\n');expected=dict(sample,actual_routing_row_sha256=reader.digest(line+b'\n'))
    reader.routing_alias(row,line,sample['actual_routing_row_ordinal'],expected)
    check('complete-routing-byte-alias-positive',True)
    changed=dict(expected,actual_routing_row_ordinal=expected['actual_routing_row_ordinal']+1)
    rejected('wrong-routing-row-ordinal',lambda:reader.routing_alias(row,line,sample['actual_routing_row_ordinal'],changed),'row alias')
    changed=dict(row,whole_physical_row_sha256='0'*64)
    rejected('rehashed-routing-physical-row-mismatch',lambda:reader.routing_alias(changed,line,sample['actual_routing_row_ordinal'],expected),'metadata differs')
    # Actual bounded JSONL reader: complete current IDs, no point/geometry claim.
    ids=sorted([row['component'] for row in actual_scope['rows']]+actual_scope['complement_ids'])
    with tempfile.TemporaryDirectory(dir=HERE/'.cache') as directory:
        root=Path(directory);pins={};products=[];chunk=(len(ids)+70)//71
        context=SimpleNamespace(components={identity:({},'0'*64,'0'*64) for identity in ids})
        context.component=lambda row:reader.transport.Context.component(context,row)
        for ordinal in range(71):
            rows=[dict(component_id=identity,complete_current_record_metadata_alias='v1') for identity in ids[ordinal*chunk:(ordinal+1)*chunk]]
            raw=b''.join(reader.canonical(row) for row in rows)
            encoded=gzip.compress(raw,mtime=0);name=f'member-{ordinal:03}.gz';(root/name).write_bytes(encoded)
            pins[reader.PHYSICAL+f'results/components-{ordinal:03}.jsonl.gz']=dict(path=name,bytes=len(encoded),sha256=reader.digest(encoded),uncompressed_bytes=len(raw),uncompressed_sha256=reader.digest(raw))
            restored=b''.join(reader.canonical(reader.transport.restore_row(row,'components',context)) for row in rows)
            original_encoded=reader.old.immutable.deterministic_gzip(restored)
            products.append(dict(path=f'components-{ordinal:03}.jsonl.gz',bytes=len(original_encoded),sha256=reader.digest(original_encoded),uncompressed_bytes=len(restored),uncompressed_sha256=reader.digest(restored)))
        state=dict(originals=pins,routing={},context=context,physical_report={'products':products})
        with patch.object(reader,'HERE',root):
            check('actual71-shard-complete95173-membership-positive',list(reader.physical_rows(state))==[])
            last=next(reversed(pins.values()));raw=reader.checked(root,last)
            rows=[json.loads(line) for line in raw.splitlines()]
            old_identity=rows[-1]['component_id'];rows[-1]['component_id']='foreign-unselected-complement-id'
            # Rebind the fixture context/wholeoriginal file so membership is the
            # intended rejection, not an earlier missingmetadata/hash failure.
            context.component=lambda row:dict(original_context={},candidate_feature_sha256='0'*64,candidate_geometry_sha256='0'*64)
            changed=b''.join(reader.canonical(row) for row in rows);encoded=gzip.compress(changed,mtime=0)
            (root/last['path']).write_bytes(encoded);last.update(bytes=len(encoded),sha256=reader.digest(encoded),uncompressed_bytes=len(changed),uncompressed_sha256=reader.digest(changed))
            restored=b''.join(reader.canonical(reader.transport.restore_row(row,'components',context)) for row in rows);original_encoded=reader.old.immutable.deterministic_gzip(restored)
            products[-1].update(bytes=len(original_encoded),sha256=reader.digest(original_encoded),uncompressed_bytes=len(restored),uncompressed_sha256=reader.digest(restored))
            rejected('actual-rehashed-reader-foreign-complement-same95173-count',lambda:list(reader.physical_rows(state)),'bijection differs')
            rows.pop();changed=b''.join(reader.canonical(row) for row in rows);encoded=gzip.compress(changed,mtime=0)
            (root/last['path']).write_bytes(encoded);last.update(bytes=len(encoded),sha256=reader.digest(encoded),uncompressed_bytes=len(changed),uncompressed_sha256=reader.digest(changed))
            restored=b''.join(reader.canonical(reader.transport.restore_row(row,'components',context)) for row in rows);original_encoded=reader.old.immutable.deterministic_gzip(restored)
            products[-1].update(bytes=len(original_encoded),sha256=reader.digest(original_encoded),uncompressed_bytes=len(restored),uncompressed_sha256=reader.digest(restored))
            rejected('actual-rehashed-reader-omitted-complement',lambda:list(reader.physical_rows(state)),'bijection differs')
    witnesses=json.loads((HERE/'six-retained-control-inputs.json').read_bytes())
    replayed=[]
    for witness in witnesses['witnesses']:
        geometry=shape(witness['complete_candidate']['geometry'])
        row=witness['complete_original_scientific_row']
        result=kernel.replay(geometry,row,reader.old.comparison.alternating_support)
        check('actual-six-original-operator-all9-pointsets:'+witness['component_id'],result['status']=='replayed' and all(result['geometry_byte_container_equality'].values()) and all(result['hierarchy_geometry_equality'].values()))
        target=result['point_diagnostics'][witness['target_relation']]
        if witness['component_id'].endswith('fc5e0999f7d4dac806e138567d694558853c9ae0796427671c390b2cc3528198'):
            check('actual-largest-missing-remains-unsupported',target['status']=='unsupported' and target['reason']=='touching-or-crossing-rings')
        else:check('actual-five-supported-point-diagnostics:'+witness['component_id'],target['status']=='diagnostic')
        if witness['target_relation']=='extra_reconstruction':
            check('actual-extra-triangle-in-candidate-contradiction:'+witness['component_id'],any(r['relation']=='extra_reconstruction' for r in result['demonstrated_local_contradictions']))
        replayed.append(dict(component_id=witness['component_id'],target_relation=witness['target_relation'],target_diagnosis=target,geometry_equality=result['geometry_byte_container_equality'],hierarchy_equality=result['hierarchy_geometry_equality']))
    extra=next(w for w in witnesses['witnesses'] if w['target_relation']=='extra_reconstruction')
    changed=copy.deepcopy(extra['complete_original_scientific_row'])
    changed['complete_support']['extra_reconstruction']['geometry']={'type':'Polygon','coordinates':[]}
    mismatch=kernel.replay(shape(extra['complete_candidate']['geometry']),changed,reader.old.comparison.alternating_support)
    check('actual-original-operator-retained-mapping-mismatch-unknown',mismatch['status']=='original-replay-mismatch' and mismatch['geometry_byte_container_equality']['extra_reconstruction'] is False and mismatch['demonstrated_local_contradictions']==[] and mismatch['point_diagnostics']=={})
    check('mismatch-keeps-complete-fresh-geometry',mismatch['complete_geometry_mappings']['extra_reconstruction']['coordinates']!=[])
    generated=reader.old.comparison.alternating_support(candidate,{})
    synthetic=dict(query_relations=[],unresolved=[],complete_support={key:dict(geometry=kernel.ordinary_mapping(generated[key])) for key in kernel.RELATIONS})
    synthetic['complete_support']['hierarchy_disagreements']={key:dict(geometry=kernel.ordinary_mapping(value)) for key,value in generated['hierarchy_disagreements'].items()}
    def signed_zero(values):
        for ordinal,value in enumerate(values):
            if isinstance(value,list):
                if signed_zero(value):return True
            elif isinstance(value,float) and value==0:
                values[ordinal]=-0.0;return True
        return False
    check('signedzero-control-actually-changes-retained-canonicalbytes',signed_zero(synthetic['complete_support']['outside_mapped_L1_context']['geometry']['coordinates']))
    mismatch=kernel.replay(candidate,synthetic,reader.old.comparison.alternating_support)
    check('signedzero-container-equality-does-not-hide-byte-mismatch',mismatch['status']=='original-replay-mismatch' and mismatch['geometry_byte_container_equality']['outside_mapped_L1_context'] is False)
    out=dict(result='PASS',complete_directed_controls=len(records),controls=records,actual_six_retained_replays=replayed,
             limits=['Small directed controls only, not full26276 scientific execution or source/repair approval.'])
    print(json.dumps(out,sort_keys=True))

if __name__=='__main__':main()
