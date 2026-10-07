"""Directed complete-pointset fixtures, not additional counted scientific runs."""
import pathlib,sys,json,copy,subprocess,tempfile
from unittest.mock import patch
from shapely.geometry import box,mapping,LineString,Point,Polygon,GeometryCollection
from shapely.errors import GEOSException
P=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(P))
import numeric_kernel as k


def run():
    passed=[]
    def positive(name,g,u,status):
        d=k.diagnose(mapping(g),mapping(u),mapping(g.intersection(u)),mapping(g.difference(u)))
        assert d['status']=='complete-literal-reconstruction-diagnosis'
        assert d['coverage_observation']['status']==status,(name,d['coverage_observation'])
        for key in ['reconstructed_partition','original_minus_partition','partition_minus_original']:
            assert 'geometry'in d[key] and 'nonempty_pointset_dimension'in d[key]
        passed.append(name)
    g=box(0,0,10,10)
    positive('complete-full-input-coverage',g,box(-1,-1,11,11),'literal-original-pointset-fully-covered-by-member-union')
    positive('complete-positive-partial-overlap',g,box(5,5,15,15),'literal-positive-area-overlap-and-outside-member-union')
    positive('complete-disjoint-inputs',g,box(20,20,30,30),'literal-original-pointset-disjoint-from-member-union')
    positive('complete-zero-area-boundary-contact',g,box(10,0,20,10),'literal-zero-area-source-contact')
    for x,dim in [(LineString([(0,0),(1,1)]),1),(Point(0,0),0)]:
        p=k.pointset(x);assert not p['is_empty'] and p['planar_area_coordinate_units_squared']==0 and p['nonempty_pointset_dimension']==dim and 'geometry'in p
        passed.append('nonempty-zero-area-dimension-'+str(dim))
    d=k.diagnose({'type':'Polygon','coordinates':[[[0,0],[1,1],[1,0],[0,1],[0,0]]]},mapping(g),mapping(g),mapping(Polygon()))
    assert d['status']=='unknown-invalid-complete-operand' and d['coverage_observation']['status']=='unknown-unmeasured';passed.append('invalid-original-retains-unknown')
    d=k.diagnose({'type':'bad'},mapping(g),mapping(g),mapping(Polygon()))
    assert d['status']=='unknown-failed-diagnostic-operation' and d['failed_stage']=='read-complete-operands';passed.append('malformed-original-retains-failure')
    original=k.union_all;calls=0
    def middle(geoms):
        nonlocal calls
        calls+=1
        if calls==2:raise GEOSException('directed failure in middle')
        return original(geoms)
    with patch.object(k,'union_all',middle):
        rows=[k.diagnose(mapping(g),mapping(g),mapping(g),mapping(Polygon()))for _ in range(3)]
    assert len(rows)==3 and rows[0]['status']==rows[2]['status']=='complete-literal-reconstruction-diagnosis' and rows[1]['status']=='unknown-failed-diagnostic-operation';passed.append('failed-middle-row-and-later-rows-retained')
    predicates={'original_relate_union':'2FF1FF212','union_covers_original':False,'original_covered_by_union':True,'original_disjoint_union':False,'original_intersects_union':True}
    d=k.coverage(predicates,g,g,g,Polygon());assert d['status']=='unknown-predicate-or-overlay-disagreement' and not d['direct_predicate_consensus'];passed.append('direct-predicate-disagreement-never-promoted')
    whole=k.diagnose(mapping(g),mapping(g),mapping(box(0,0,5,5)),mapping(Polygon()))
    assert whole['coverage_observation']['status']=='unknown-predicate-or-overlay-disagreement' and whole['predicates']['partition_equals_original']is False;passed.append('incomplete-overlay-never-full-coverage')
    contaminated=k.diagnose(mapping(g),mapping(g),mapping(box(0,0,15,15)),mapping(Polygon()))
    assert contaminated['coverage_observation']['status']=='unknown-predicate-or-overlay-disagreement';passed.append('contaminated-overlay-never-full-coverage')
    u=box(5,5,15,15)
    partial=k.diagnose(mapping(g),mapping(u),mapping(box(6,6,9,9)),mapping(box(0,0,4,4)))
    assert partial['coverage_observation']['status']=='literal-positive-area-overlap-and-outside-member-union' and partial['predicates']['partition_equals_original']is False and partial['coverage_observation']['partition_recovery']=='not-certified-by-coverage-observation';passed.append('partial-relation-does-not-certify-complete-partition')
    line=LineString([(10,10),(11,11)])
    residual=k.diagnose(mapping(g),mapping(g),mapping(GeometryCollection([g,line])),mapping(Polygon()))
    assert residual['observed_reason']=='nonempty-zero-coordinate-area-overlay-remainder' and residual['partition_minus_original']['is_empty']is False and residual['partition_minus_original']['nonempty_pointset_dimension']==1 and residual['coverage_observation']['status']=='unknown-predicate-or-overlay-disagreement';passed.append('actual-nonempty-zero-area-remainder-diagnosis')
    import custody,importlib.util
    spec=importlib.util.spec_from_file_location('numeric_verify',P/'verify.py');verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
    from reader import output_target,authenticate_executed_modules
    def reject(name,fn):
        try:fn()
        except ValueError:passed.append(name);return
        raise AssertionError('Intended rejection absent: '+name)
    # Every diagnostic field, including absent fields and exact numeric
    # representation, participates in whole canonical replay equality.
    expected=k.diagnose(mapping(g),mapping(g),mapping(g),mapping(Polygon()))
    stored=verify.old.normalized_diagnostic(expected);objects={}
    for name in ['reconstructed_partition','original_minus_partition','partition_minus_original']:
        objects[custody.SHA(custody.canon(expected[name]['geometry']))]=expected[name]['geometry']
    original={'component':'c','family':'f','status':'unknown-numerical-partition-disagreement','component_full_feature_sha256':'a'*64,'component_geometry_sha256':'b'*64,'contacts':['n'],'edge_neighbor_ids':['n'],'existing_related_issues':[1]}
    family={'complete_original_member_ids':['m']};ref={'commit':'c'*40,'path':'ordinary.json','canonical_record_sha256':'d'*64}
    extras={'component':'c','family':'f','archived_original_diagnostic':{'reference':ref,'record':original},'complete_member_ids':['m'],'original_family_reference':ref,'component_full_feature_sha256':'a'*64,'component_geometry_sha256':'b'*64,'contacts':['n'],'edge_neighbor_ids':['n'],'existing_related_issues':[1]}
    row={**stored,**extras}
    verify.validate_row(row,expected,objects,original,family,ref,ref);passed.append('complete-diagnostic-and-archived-original-positive')
    mutations=[('coherently-rehashed-status-mutation','status','unknown-unmeasured'),('coverage-authority-mutation','physical_status','land'),('member-reassignment','complete_member_ids',['other']),('contact-loss','contacts',[]),('edge-neighbor-loss','edge_neighbor_ids',[]),('existing-related-work-loss','existing_related_issues',[]),('original-row-promotion','archived_original_diagnostic',{'reference':ref,'record':{**original,'status':'measured'}}),('source-reference-mutation','original_family_reference',{**ref,'commit':'e'*40}),('mandatory-remainder-pointset-loss','original_minus_partition',None),('numeric-representation-mutation','coordinate_area_arithmetic',{**row['coordinate_area_arithmetic'],'original':100})]
    for name,key,value in mutations:
        changed=copy.deepcopy(row)
        if value is None:del changed[key]
        else:changed[key]=value
        reject(name,lambda c=changed:verify.validate_row(c,expected,objects,original,family,ref,ref))
    reject('complete-generated-geometry-loss',lambda:verify.validate_row(row,expected,{},original,family,ref,ref))
    f={'original_family_reference':ref,'original_complete_family':family,'diagnosed_unknown_component_ids':['c'],'diagnosis_counts':{'complete':1},'limits':['Coordinated family contacts are not newly measured component adjacency.','Original family pointset references belong to the frozen predecessor object namespace.']}
    verify.validate_family(f,family,ref,['c'],{'complete':1});passed.append('complete-family-positive')
    for name,key,value in [('family-member-reassignment','original_complete_family',{'complete_original_member_ids':['other']}),('family-component-loss','diagnosed_unknown_component_ids',[]),('family-status-count-rebound','diagnosis_counts',{'unknown':1})]:
        changed={**f,key:value};reject(name,lambda c=changed:verify.validate_family(c,family,ref,['c'],{'complete':1}))
    report={'counts':{'complete':1},'observed_reasons':{'reason':1},'literal_coverage_observations':{'unknown':1}}
    verify.validate_complete_counts({'c':row},['c'],{'complete':1},{'reason':1},{'unknown':1},report);passed.append('complete-status-count-positive')
    reject('global-status-count-rebound',lambda:verify.validate_complete_counts({'c':row},['c'],{'complete':1},{'reason':1},{'unknown':1},{**report,'counts':{'unknown':1}}))
    reject('global-component-omission',lambda:verify.validate_complete_counts({},['c'],{'complete':1},{'reason':1},{'unknown':1},report))
    frozen=k.diagnose({'type':'bad'},mapping(g),mapping(g),mapping(Polygon()));changed=copy.deepcopy(frozen);changed['failure_class']='Other'
    reject('unknown-failure-class-mutation',lambda:verify.old.validate_diagnostic(changed,frozen,{}))
    for key in custody.ROSTERS:
        reject('missing-complete-roster-'+key,lambda x=key:custody.check_rosters({a:[]for a in custody.ROSTERS if a!=x}))
    with tempfile.TemporaryDirectory(dir=P/'.cache')as directory:
        tmp=pathlib.Path(directory);target=tmp/'git-option-output'
        # Actual command entry must reject before Git can interpret any option.
        result=subprocess.run([sys.executable,'-B',str(P/'producer.py'),'--code-commit','--output='+str(target),'--output',str(tmp/'science')],capture_output=True)
        assert result.returncode!=0 and not target.exists() and not(tmp/'science').exists();passed.append('actual-invalid-commit-cli-no-write')
        reject('git-option-auth-no-write',lambda:authenticate_executed_modules(custody.R,'--output='+str(target),[]));assert not target.exists()
        reject('output-escape',lambda:output_target(custody.R,str(P.relative_to(custody.R)),'scripts/out'))
        reject('output-traversal',lambda:output_target(custody.R,str(P.relative_to(custody.R)),str(P.relative_to(custody.R))+'/../bad'))
        linked=tmp/'linked';linked.symlink_to(tmp,target_is_directory=True)
        reject('symlink-output-parent',lambda:output_target(custody.R,str(P.relative_to(custody.R)),str((linked/'out').relative_to(custody.R))))
        ordinary=tmp/'ordinary.json';ordinary.write_text('{}')
        reject('ordinary-read-traversal',lambda:verify.checked_output(tmp,'../ordinary.json'))
        reject('ordinary-read-absolute',lambda:verify.checked_output(tmp,str(ordinary)))
        reject('ordinary-read-symlink-ancestor',lambda:verify.checked_output(tmp,'linked/ordinary.json'))
        assert verify.checked_output(tmp,'ordinary.json').read_bytes()==b'{}';passed.append('ordinary-read-complete-local-positive')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=custody.R,text=True).strip();module=P/'numeric_kernel.py';original_read=pathlib.Path.read_bytes
    def dirty_read(path):return original_read(path)+b'\n# directed executed-code mutation\n' if path==module else original_read(path)
    with patch.object(pathlib.Path,'read_bytes',dirty_read):
        reject('executed-code-byte-mutation',lambda:authenticate_executed_modules(custody.R,commit,[str(module.relative_to(custody.R))]))
    return {'directed_controls':len(passed),'passed':passed,'limits':['Small directed fixtures only; no complete current dataset result or source authority is certified.']}

if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
