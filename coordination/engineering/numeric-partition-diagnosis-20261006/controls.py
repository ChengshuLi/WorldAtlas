"""Directed complete-pointset fixtures, not additional counted scientific runs."""
import pathlib,sys,json
from unittest.mock import patch
from shapely.geometry import box,mapping,LineString,Point,Polygon
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
    return {'directed_controls':len(passed),'passed':passed,'limits':['Small directed fixtures only; no complete current dataset result or source authority is certified.']}

if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
