"""Meaningful entry/method/source/unknown controls; no world calculation."""
import copy,json,pathlib
from collections import defaultdict
from shapely.geometry import box,mapping,Polygon,MultiPolygon
import reader,trace

def main():
    passed=[]
    def positive(name,fn):fn();passed.append({'name':name,'outcome':'passed'})
    def negative(name,fn):
        try:fn()
        except (ValueError,AssertionError,KeyError):passed.append({'name':name,'outcome':'passed'});return
        raise AssertionError('Negative accepted '+name)
    feature={'id':'test-candidate','type':'Feature','properties':{},'geometry':mapping(box(0,0,2,1))}
    candidate=box(0,0,2,1);levels=defaultdict(list,{1:[box(0,0,1,1)]})
    def equivalence(c,l):
        actual,local,events=trace.trace_operator(c,l);plain=reader.old.comparison.alternating_support(c,l)
        assert len(local)==9 and events
        for k in trace.RELATIONS:assert reader.canonical(trace.kernel.ordinary_mapping(actual[k]))==reader.canonical(trace.kernel.ordinary_mapping(plain[k]))
        for k,v in plain['hierarchy_disagreements'].items():assert reader.canonical(trace.kernel.ordinary_mapping(actual['hierarchy_disagreements'][k]))==reader.canonical(trace.kernel.ordinary_mapping(v))
        assert reader.canonical(trace.kernel.ordinary_mapping(local['missing']))==reader.canonical(trace.kernel.ordinary_mapping(actual['missing_reconstruction']))
    positive('literal-trace-vs-original-valid-simple',lambda:equivalence(candidate,levels))
    positive('near-collinear-original-method-equivalence',lambda:equivalence(Polygon([(0,0),(2,0),(2,1e-15),(1,1e-16),(0,0)]),defaultdict(list,{1:[box(0,0,1,1)]})))
    positive('mixed-polygon-contact-source-equivalence',lambda:equivalence(MultiPolygon([box(0,0,1,1),box(2,0,3,1)]),defaultdict(list,{1:[box(0,0,2,1)]})))
    positive('empty-level-contact-zero-context-equivalence',lambda:equivalence(candidate,defaultdict(list)))
    expected=['a','b'];positive('complete-roster-positive',lambda:reader.validate_roster([{'id':'a'},{'id':'b'}],expected))
    for name,rows in [('omit',[{'id':'a'}]),('duplicate',[{'id':'a'},{'id':'a'}]),('foreign',[{'id':'a'},{'id':'c'}])]:negative('complete-roster-'+name,lambda rows=rows:reader.validate_roster(rows,expected))
    meta={'id':7,'level':2,'container':3,'record_sha256':'a'*64,'decoded_pointset_binary64_sha256':'b'*64}
    query={'source_id':7,'source_level':2,'source_container':3,'source_record_sha256':'a'*64,'source_pointset_sha256':'b'*64,'periodic_offset':0}
    positive('source-record-container-frame-positive',lambda:reader.query_bind(query,meta))
    for key,value in [('source_id',8),('source_level',1),('source_container',4),('source_record_sha256','c'*64),('source_pointset_sha256','d'*64),('periodic_offset',180)]:negative('native-query-'+key,lambda key=key,value=value:reader.query_bind(dict(query,**{key:value}),meta))
    invalid=Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)])
    positive('invalid-candidate-real-relation-unknown',lambda:assert_status(reader.old.comparison.relation(invalid,candidate,1)[0],'unknown'))
    positive('invalid-source-real-relation-unknown',lambda:assert_status(reader.old.comparison.relation(candidate,invalid,1)[0],'unknown'))
    class Broken:
        is_empty=False;is_valid=True
        def covers(self,x):raise RuntimeError('actual-operation-control')
    positive('actual-relation-operation-failure-retained',lambda:assert_status(reader.old.comparison.relation(candidate,Broken(),1)[0],'unknown'))
    # Exact canonical byte comparison intentionally distinguishes signed zero and
    # list/tuple representation only after standard JSON container serialization.
    positive('signed-zero-canonical-mismatch',lambda:assert_not_equal({'x':-0.0},{'x':0.0}))
    positive('geometry-key-order-canonical-identity',lambda:assert_equal({'type':'Polygon','coordinates':[]},{'coordinates':[],'type':'Polygon'}))
    # A coherently rehashed retained pointset still cannot gain old-attributed
    # agreement: test the production mapping comparator itself.
    maps={k:trace.kernel.ordinary_mapping(candidate)for k in trace.RELATIONS}
    hierarchy={k:trace.kernel.ordinary_mapping(candidate)for k in ('L2-outside-L1','L3-outside-L2','L4-outside-L3')}
    reference={'complete_support':{k:{'geometry':copy.deepcopy(v)}for k,v in maps.items()}}
    reference['complete_support']['hierarchy_disagreements']={k:{'geometry':copy.deepcopy(v)}for k,v in hierarchy.items()}
    positive('actual-mapping-production-positive',lambda:require(trace.mapping_equality(maps,hierarchy,reference)[2]))
    for key in trace.RELATIONS:
        changed=copy.deepcopy(reference);changed['complete_support'][key]['geometry']=trace.kernel.ordinary_mapping(box(0,0,3,1))
        positive('actual-rehashed-retained-'+key+'-unknown',lambda changed=changed:require(not trace.mapping_equality(maps,hierarchy,changed)[2]))
    signed=copy.deepcopy(reference);signed['complete_support']['mapped_land_support']['geometry']['coordinates'][0][2]=(-0.0,1.0)
    positive('actual-retained-signedzero-mismatch-unknown',lambda:require(not trace.mapping_equality(maps,hierarchy,signed)[2]))
    queries=[dict(query),dict(query,source_id=8)]
    pin={'count':2,'ordered_whole_sha256':reader.digest(reader.canonical(queries))}
    positive('actual-ordered-query-roster-positive',lambda:reader.query_roster(queries,pin))
    for name,bad in [('omit',queries[:1]),('duplicate',[queries[0],queries[0]]),('reorder',list(reversed(queries))),('changed',[dict(query,source_container=9),queries[1]])]:
        negative('actual-ordered-query-roster-'+name,lambda bad=bad:reader.query_roster(bad,pin))
    negative('actual-input-encoded-cap-before-git',lambda:reader.whole(None,{'bytes':reader.LIMIT+1}))
    negative('actual-input-decoded-cap-before-git',lambda:reader.whole(None,{'bytes':0,'uncompressed_bytes':reader.LIMIT+1}))
    full_meta={'id':7,'level':1,'container':-1,'record_sha256':'a'*64,'decoded_pointset_binary64_sha256':'b'*64}
    q,piece=reader.old.comparison.relation(candidate,box(0,0,1,1),7)
    q.update(source_level=1,source_container=-1,source_record_sha256='a'*64,source_pointset_sha256='b'*64)
    measured=reader.old.comparison.alternating_support(candidate,defaultdict(list,{1:[piece]}))
    complete={k:{'geometry':trace.kernel.ordinary_mapping(measured[k])}for k in trace.RELATIONS}
    complete['hierarchy_disagreements']={k:{'geometry':trace.kernel.ordinary_mapping(v)}for k,v in measured['hierarchy_disagreements'].items()}
    row={'query_relations':[q],'complete_support':complete,'unresolved':[]}
    source={7:(full_meta,box(0,0,1,1))}
    def valid_execute():
        result=trace.execute(feature,row,source)
        assert result['status']=='original-mappings-matched' and len(result['query_replays'])==1
        assert all(result['mapping_equality'].values()) and all(result['hierarchy_mapping_equality'].values())
    positive('actual-valid-trace-execute-full-output-equivalence',valid_execute)
    def invalid_execute():
        bad=dict(feature,geometry=trace.kernel.ordinary_mapping(invalid));original=trace.trace_operator
        def forbidden(*a,**k):raise AssertionError('Invalid candidate construction was called')
        try:
            trace.trace_operator=forbidden;result=trace.execute(bad,row,source)
        finally:trace.trace_operator=original
        assert result['status']=='unknown-invalid-candidate' and len(result['query_replays'])==1
        assert result['query_replays'][0]['fresh']['status']=='unknown'
        assert result['query_replays'][0]['original']==q and not result['stage_pointsets']
        assert result['original_contradiction_claim_allowed'] is False
    positive('actual-invalid-trace-execute-retains-query-without-construction',invalid_execute)
    def source_order_and_frame():
        from shapely.affinity import translate
        source2=box(1,0,1.5,1);meta2=dict(full_meta,id=8)
        q2,p2=reader.old.comparison.relation(candidate,source2,8);q2.update(source_level=1,source_container=-1,source_record_sha256='a'*64,source_pointset_sha256='b'*64)
        ordered,_=trace.original_levels(candidate,{'query_relations':[q2,q]},source|{8:(meta2,source2)}, {})
        assert [reader.canonical(trace.kernel.ordinary_mapping(g))for g in ordered[1]]==[reader.canonical(trace.kernel.ordinary_mapping(source2)),reader.canonical(trace.kernel.ordinary_mapping(source[7][1]))]
        moved=translate(candidate,xoff=360);moved_source=translate(source[7][1],xoff=360)
        frame=dict(q,periodic_offset=360)
        shifted,_=trace.original_levels(moved,{'query_relations':[frame]},source,{})
        assert reader.canonical(trace.kernel.ordinary_mapping(shifted[1][0]))==reader.canonical(trace.kernel.ordinary_mapping(moved_source))
    positive('actual-whole-source-operands-query-order-and-native-periodic-frame',source_order_and_frame)
    print(json.dumps({'method_id':'north-slope46-literal-stage-observation','kind':'controls','outcome':'passed','actual_controls':len(passed),'controls':passed},sort_keys=True))

def require(value):assert value

def assert_status(row,status):assert row['status']==status

def assert_equal(a,b):assert reader.canonical(a)==reader.canonical(b)

def assert_not_equal(a,b):assert reader.canonical(a)!=reader.canonical(b)
if __name__=='__main__':main()
