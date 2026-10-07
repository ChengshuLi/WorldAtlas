"""Directed complete-method controls, including explicit fault injection."""
import copy
import json
import pathlib
import struct
from unittest.mock import patch
import io
import zipfile

from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, Point, box, mapping
from shapely.strtree import STRtree

import comparison
import producer as p

passed = []


def check(name, operation):
    operation()
    passed.append(name)


def rejects(name, operation, expected):
    def verify():
        try:
            operation()
        except ValueError as error:
            assert expected in str(error), str(error)
        else:
            raise AssertionError('Unexpected acceptance')
    check(name, verify)


def family():
    gs = {1: box(-2, -2, 12, 12), 2: box(2, 2, 8, 8),
          3: box(3, 3, 7, 7), 4: box(4, 4, 6, 6)}
    metas = {i: dict(id=i, level=i, container=i-1, record_sha256='control-native-' + str(i),
                     decoded_pointset_binary64_sha256='control-points-' + str(i), geometry_issues=[])
             for i in gs}
    containers = {i: dict(child=i, parent=i-1, **p.container_outcome(i, metas, gs)) for i in (2,3,4)}
    return metas, gs, containers


def compare(metas, gs, containers, geometry=None, context=None):
    ids = sorted(gs)
    envelopes = [gs[i] if gs[i] is not None else box(0, 0, 10, 10) for i in ids]
    record = dict(id='directed-control-complete-candidate', type='Feature',
                  geometry=mapping(geometry if geometry is not None else box(0,0,10,10)),
                  properties=context or {})
    return p.compare_component(record, metas, gs, containers, ids, STRtree(envelopes), {})


def nested():
    row = compare(*family())
    assert row['status'] == 'mixed-source-support' and not row['unresolved']
    assert row['complete_support']['mapped_land_support']['planar_area'] == 76
    assert row['complete_support']['mapped_inland_water_support']['planar_area'] == 24
    assert {r['source_id'] for r in row['query_relations']} == {1,2,3,4}
check('actual-complete-component-method-alternates-all-four-source-levels', nested)


def mixed_dimensional():
    for contact_kind in ('line','point','nested'):
      candidate=MultiPolygon([box(0,0,1,1),box(2,0,3,1) if contact_kind=='line' else box(2,2,3,3)])
      for level in (1,2,3,4):
        source=box(0,0,2,1) if contact_kind=='line' else box(0,0,2,2)
        gs={i:box(-10,-10,10,10) for i in range(1,level)};gs[level]=source
        metas={i:dict(id=i,level=i,container=i-1,record_sha256='directed-source',decoded_pointset_binary64_sha256='directed-points',geometry_issues=[]) for i in gs}
        containers={i:dict(child=i,parent=i-1,**p.container_outcome(i,metas,gs)) for i in gs if i>1}
        if contact_kind=='nested':
          whole=GeometryCollection([box(0,0,1,1),GeometryCollection([LineString([(2,2),(2,3)]),Point(2,2)])])
          original=comparison.relation
          def nested_relation(c,s,identity,offset=0):
            return ({'source_id':identity,'status':'checked','witness_geometry':mapping(whole)},whole) if identity==level else original(c,s,identity,offset)
          with patch.object(comparison,'relation',side_effect=nested_relation):
            row=compare(metas,gs,containers,geometry=candidate)
        else:
          row=compare(metas,gs,containers,geometry=candidate)
        assert not row['unresolved'],row['unresolved']
        query=next(r for r in row['query_relations'] if r['source_id']==level)
        witness=query['whole_mixed_operation']
        assert witness['geometry']['type']=='GeometryCollection' and witness['planar_area']==1
        assert len(witness['geometry']['geometries'])==2
        assert len(query['exact_polygon_members'])==1
        assert len(query['exact_contact_members'])==(2 if contact_kind=='nested' else 1)
        support=row['complete_support']
        assert sum(support[k]['planar_area'] for k in ('mapped_land_support','mapped_inland_water_support','outside_mapped_L1_context'))==2
        if level==1:
          assert support['mapped_land_support']['planar_area']==1 and support['outside_mapped_L1_context']['planar_area']==1
        else:
          assert support['mapped_land_support']['planar_area']==1 and support['mapped_inland_water_support']['planar_area']==1
check('actual-positive-polygon-line-and-polygon-point-plus-directed-nestedmixed-exact-partition-at-all-four-levels',mixed_dimensional)



def wrong_level():
    metas, gs, containers = family()
    metas[3]['container'] = 1
    outcome = p.container_outcome(3, metas, gs)
    assert outcome['status'] == 'unknown'
    containers[3] = dict(child=3, parent=1, **outcome)
    row = compare(metas, gs, containers)
    assert row['status'] == 'unknown'
    assert any(r.get('source_id') == 3 for r in row['unresolved'])
check('actual-container-reader-rejects-level-substitution-and-keeps-contributing-unknown', wrong_level)


def missing_parent():
    metas, gs, containers = family()
    metas[2]['container'] = 999
    outcome = p.container_outcome(2, metas, gs)
    containers[2] = dict(child=2, parent=999, **outcome)
    row = compare(metas, gs, containers)
    assert row['status'] == 'unknown' and any(r.get('source_id') == 2 for r in row['unresolved'])
check('actual-whole-container-missing-parent-retains-complete-candidate-unknown', missing_parent)


def invalid_source():
    metas, gs, containers = family()
    gs[2] = None
    metas[2]['geometry_issues'] = ['invalid-original-source-polygon']
    row = compare(metas, gs, containers)
    assert row['status'] == 'unknown'
    assert any(r['source_id'] == 2 and r['status'] == 'unknown' for r in row['query_relations'])
check('actual-complete-method-invalid-source-envelope-not-silently-excluded', invalid_source)


def empty_candidate():
    row = compare(*family(), geometry=Polygon())
    assert row['status'] == 'unknown' and row['unresolved'][0]['issue'] == 'invalid-or-empty-complete-candidate'
check('actual-empty-complete-candidate-remains-explicit-unknown', empty_candidate)


for context, label in [({'touches_domain_boundary':True}, 'domain-edge'),
                       ({'unmeasured_fragment_ids':['original-unmeasured-member']}, 'unmeasured-fragment')]:
    def contextual(context=context):
        row = compare(*family(), context=context)
        assert row['status'] == 'unknown' and row['original_context'] == context
    check('existing-' + label + '-context-retained-as-unknown', contextual)


def operation_failure():
    with patch.object(comparison, 'alternating_support', side_effect=RuntimeError('directed injected overlay failure')):
        row = compare(*family())
    assert row['status'] == 'unknown' and row['query_relations']
    assert row['unresolved'][-1]['issue'] == 'support-operation-failed'
check('directed-injected-overlay-exception-retains-real-method-query-relations', operation_failure)

def contradictory_predicates():
    class DirectedPredicateGeometry:
        is_empty=False
        is_valid=True
        def covers(self,other):return False
        def intersects(self,other):return False
        def disjoint(self,other):return False
    row,piece=comparison.relation(DirectedPredicateGeometry(),DirectedPredicateGeometry(),42)
    assert row['status']=='unknown' and row['source_id']==42
    assert row['issue']=='contradictory-whole-geometry-predicates' and piece is None
check('directed-contradictory-predicates-cannot-be-discarded-as-empty',contradictory_predicates)


def zero_area():
    with patch.object(p.ellipsoidal_area, 'area', return_value=0.0):
        row = compare(*family())
    assert row['status'] == 'unknown'
    assert any(r['issue'] == 'nonempty-polygon-zero-ellipsoidal-area' for r in row['unresolved'])
check('directed-injected-nonempty-zero-area-is-not-discarded', zero_area)


def disjoint_chain():
    metas, gs, containers = family()
    candidate = box(4,4,6,6)
    gs = {1:gs[1],2:Polygon(box(2,2,8,8).exterior.coords, [box(3,3,7,7).exterior.coords])}
    metas = {1:metas[1],2:metas[2]}
    metas[2]['container'] = 999
    containers = {2:dict(child=2,parent=999,**p.container_outcome(2,metas,gs))}
    row = compare(metas,gs,containers,geometry=candidate)
    assert row['status'] == 'mapped-land-support' and not row['unresolved']
    query = next(r for r in row['query_relations'] if r['source_id']==2)
    assert query['container_chain_issues'] and query['intersects'] is False
check('proved-disjoint-source-keeps-chain-context-without-fabricating-component-uncertainty', disjoint_chain)

points = [(0,0),(1000000,0),(1000000,1000000),(0,0)]
header = comparison.HEADER.pack(0,4,1+(9<<8),0,1000000,0,1000000,1,1,-1,-1)
native = header + b''.join(struct.pack('>2i',*point) for point in points)
rejects('actual-native-parser-trailing-byte-branch', lambda:list(p.native_records(native+b'x')), 'Trailing/truncated')
rejects('actual-native-parser-truncated-coordinate-branch', lambda:list(p.native_records(native[:-1])), 'Truncated original coordinate')
rejects('actual-native-parser-incomplete-complete-roster', lambda:list(p.native_records(native)), 'Incomplete original native source roster')
for invalid in ('main', 'abcd1234', 'A'*40):
    rejects('actual-execution-commit-guard:' + invalid, lambda invalid=invalid:p.freeze_guard(pathlib.Path.cwd(),invalid), 'Exact immutable')

# Hash-valid synthetic ZIPs reach the actual archive identity branches, rather
# than being rejected by an unrelated checksum failure first.
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w') as zipped:
    zipped.writestr('gshhs_f.b',native)
    for index in range(17):
        zipped.writestr('directed-original-member-'+str(index),b'original-control-bytes')
archive_body=stream.getvalue()
config={'inputs':[{'kind':'archive_part','ordinal':0,'offset':0,'commit':'a'*40,'path':'fixture.bin','bytes':len(archive_body),'sha256':p.digest(archive_body)}],
        'source_archive':{'member':'gshhs_f.b','member_bytes':len(native),'member_sha256':p.digest(native),
                          'original_bytes':len(archive_body),'original_sha256':p.digest(archive_body)}}
with patch.object(p.inputs,'ordinary_git',return_value=archive_body):
    assert p.original_native(pathlib.Path.cwd(),config)==native
    passed.append('actual-whole-archive-reader-hash-valid-18-member-positive')
    wrong=copy.deepcopy(config);wrong['source_archive']['member']='gshhs_c.b'
    rejects('actual-whole-archive-reader-wrong-member-identity',lambda:p.original_native(pathlib.Path.cwd(),wrong),'Wrong complete original native member identity')
    wrong=copy.deepcopy(config);wrong['inputs'][0]['ordinal']=1
    rejects('actual-whole-archive-reader-missing-original-part',lambda:p.original_native(pathlib.Path.cwd(),wrong),'Missing/reordered original source fragment')
    wrong=copy.deepcopy(config);wrong['source_archive']['member_bytes']+=1
    rejects('actual-whole-archive-reader-wrong-whole-member-size',lambda:p.original_native(pathlib.Path.cwd(),wrong),'Wrong/incomplete complete original native member')

receipt = dict(kind='Directed actual complete producer controls; injected uncertainty is a control, not an observed GEOS defect.',
               passed=passed,count=len(passed),producer_sha256=p.digest(pathlib.Path(p.__file__).read_bytes()),
               controls_sha256=p.digest(pathlib.Path(__file__).read_bytes()))
pathlib.Path(__file__).with_name('producer-controls-result.json').write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps(receipt))
