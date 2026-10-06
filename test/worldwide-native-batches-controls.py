import importlib.util, json, math, pathlib, sys
import numpy as np
from unittest.mock import patch
from shapely.errors import GEOSException
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from geographic_grid import CanonicalGrid
from evidence.immutable import deterministic_gzip, sha256
ROOT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('kernel',ROOT.parent/'scripts/worldwide_native_observations.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
def fixture(end):
    values={'rows':np.array([v for i in range(8)for v in(i,1)],dtype='<u4'),
            'runs':np.array([v for i in range(8)for v in(8,end-1)],dtype='<u4')}
    blobs={};parts=[]
    for name,words in values.items():
        logical=words.tobytes();shuffled=np.frombuffer(logical,dtype=np.uint8).reshape(-1,4).T.copy().tobytes()
        encoded=deterministic_gzip(shuffled);path=name+'.gz';blobs['fixture/'+path]=encoded
        parts.append({'kind':name,'offset':0,'words':len(words),'path':path,'encoding':'byte-shuffle',
                      'compressed_bytes':len(encoded),'sha256':sha256(encoded),'decoded_sha256':sha256(logical)})
    class Source:
        pins={'fixture/'+p['path']:p for p in parts}
        def read(self,path):
            b=blobs[path];assert sha256(b)==self.pins[path]['sha256'];return b
    return CanonicalGrid(Source(),{'version':2,'size':8,'coordinateBits':3,'runWords':16,'parts':parts},root='fixture',max_owner_id=2)
lat=np.array([math.degrees(math.atan(math.sinh(math.pi*(1-2*(y+.5)/8))))for y in range(8)])
features=[{'id':'wide','geometry':{'type':'Polygon','coordinates':[[[-179,-84],[179,-84],[179,84],[-179,84],[-179,-84]]]}},
          {'id':'tiny','geometry':{'type':'Polygon','coordinates':[[[-.001,-.001],[.001,-.001],[0,.001],[-.001,-.001]]]}},
          {'id':'line','geometry':{'type':'LineString','coordinates':[[0,0],[1,1]]}}]
probes=[k.component_probe(f,8,lat)for f in features];owned=fixture(8);half=fixture(4);owners=[None,'owner1','owner2']
obs,counts=k.observe_probes(probes,owned,owners);other,counts2=k.observe_probes(probes,half,owners)
assert obs[0]['native_status']=='inside-owned-grid-source-discrepancy'
assert obs[1]['native_status']=='outside-owned-centre-component-unchecked'
assert obs[2]['native_status']=='unknown-invalid-empty-or-nonpolygon-geometry'
assert other[0]['native_status']=='inside-unassigned-native-cell'
rows,full=k.full_owner_counts(owned,owners);rows2,partial=k.full_owner_counts(half,owners)
assert full['assigned_cells']==64 and full['unassigned_cells']==0 and rows[1]['represented_assigned_cell_count']==0
assert partial['assigned_cells']==32 and partial['unassigned_cells']==32
reverse,_=k.observe_probes(list(reversed(probes)),owned,owners);assert list(reversed(reverse))==obs
try:k.observe_probes(probes+probes[:1],owned,owners);raise AssertionError('duplicate accepted')
except ValueError:pass
class FailingPolygon:
    is_empty=False;geom_type='Polygon';is_valid=True
    bounds=(-1.,-1.,1.,1.)
    def representative_point(self):raise GEOSException('injected geometry-operation failure')
real_shape=k.shape
middle=[features[0],{'id':'failed-middle','geometry':{'type':'InjectedFailure'}},features[1]]
with patch.object(k,'shape',side_effect=lambda geometry:FailingPolygon()if geometry['type']=='InjectedFailure'else real_shape(geometry)):
    middle_probes=[k.component_probe(f,8,lat)for f in middle]
middle_obs,middle_counts=k.observe_probes(middle_probes,owned,owners)
assert [r['component']for r in middle_obs]==['wide','failed-middle','tiny']
assert middle_obs[1]['native_status']=='unknown-failed-geometry-probe'and middle_obs[1]['failure_class']=='GEOSException'
assert all(middle_obs[1][key]is None for key in ('owner_integer','owner_location_id','administrative_assignment','cell'))
assert middle_obs[2]['native_status']=='outside-owned-centre-component-unchecked'
result={'status':'committed-kernel-semantic-control-fixtures-not-global-observations','positive':counts,'half_grid':counts2,
        'full_rle_accounting':full,'partial_rle_accounting':partial,'sorted_query_order_preserved':True,
        'line_residue_retained_unknown':True,'zero_owner_cells_not_no_territory':True,'duplicate_probe_rejected':True,
        'geometry_failure_in_middle_retains_full_cohort_and_later_rows':middle_counts}
# Fixtures do not write into the test/source tree.
print(json.dumps(result))

# Queue permutation tests must also enforce each complete semantic tuple order.
spec=importlib.util.spec_from_file_location('producer',ROOT.parent/'scripts/build-worldwide-native-batches.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
from physical_gap_priority import attach_rank_positions,ORDER_NAMES
import copy
records=[{'component':c,'investigation_orders':{**{n:[0,c]for n in ORDER_NAMES},'limits':[]}}for c in ['a','b']]
attach_rank_positions(records);p.semantic_ranks(records)
bad=copy.deepcopy(records)
bad[0]['rank_positions']['measured_impact'],bad[1]['rank_positions']['measured_impact']=1,0
try:p.semantic_ranks(bad)
except ValueError:pass
else:raise AssertionError('Complete permutation with two swapped ranks escaped semantic order verification')
batch={'component_ids':['a','b'],'component_count':2,'component_ids_sha256':p.sha256(p.canonical_json(['a','b']))}
p.validate_batch_membership([batch],['a','b'])
for invalid in [[batch,batch],[{**batch,'component_ids':['a'],'component_count':1}]]:
    try:p.validate_batch_membership(invalid,['a','b'])
    except ValueError:pass
    else:raise AssertionError('Missing or duplicated batch member escaped')
print('Complete rank semantics and exhaustive disjoint batch controls PASS')
binding={'geographic_release':'frozen','footprints_sha256':'old-footprint','hierarchy_sha256':'hierarchy','size':8,'coordinateBits':3}
report={'frozen_native_candidate':dict(binding),'selected_release':{'id':'selected','footprints_sha256':'new-footprint','hierarchy_sha256':'hierarchy'}}
p.verify_native_binding(binding,report,'frozen-reviewed-native',8)
selected={**binding,'geographic_release':'selected','footprints_sha256':'new-footprint'}
p.verify_native_binding(selected,report,'selected-repository-native',8)
for label,good,field,value in [('frozen-reviewed-native',binding,'geographic_release','wrong'),('frozen-reviewed-native',binding,'footprints_sha256','wrong'),('selected-repository-native',selected,'footprints_sha256','wrong'),('selected-repository-native',selected,'size',16),('selected-repository-native',selected,'coordinateBits',4)]:
    try:p.verify_native_binding({**good,field:value},report,label,8)
    except ValueError:pass
    else:raise AssertionError('Cohort domain/release/footprint mutation escaped '+field)
import tempfile
with tempfile.TemporaryDirectory() as directory:
    target=pathlib.Path(directory)/'executed.py';target.write_bytes(b'original')
    p.executed_code_equal(target,b'original');target.write_bytes(b'changed')
    try:p.executed_code_equal(target,b'original')
    except ValueError:pass
    else:raise AssertionError('Changed actually executed code escaped original pin')
print('Exact frozen/selected release, footprint, probe-domain and executed-code mutation controls PASS')
runtime={'python':'3.12.14','numpy':'2.3.5','shapely':'2.1.2','geos':'3.13.1'}
p.verify_runtime(runtime)
try:p.verify_runtime({**runtime,'geos':'different'})
except ValueError:pass
else:raise AssertionError('Unpinned scientific runtime accepted')
from worldwide_gap_source_context import issue_rosters
for body in ['<!-- worldatlas-work:v1 [] -->','<!-- worldatlas-work:v1 {"evidence_quality": []} -->','<!-- worldatlas-work:v1 {} --><!-- worldatlas-work:v1 {} -->']:
    strong,weak,rejected=issue_rosters([[{'number':1,'state':'open','body':body}]])
    assert rejected and not strong
old=[{'component':'a','value':1},{'component':'b','value':2}]
new=[{'component':'b','value':3},{'component':'a','value':1}]
overlay=p.observation_overlay(old,new)
assert overlay['unchanged_count']==1 and overlay['changed_rows']==[{'component':'b','value':3}]
try:p.observation_overlay(old,new[:1])
except ValueError:pass
else:raise AssertionError('Incomplete comparison overlay accepted')
print('Malformed issue declarations retained; runtime and full comparison overlay controls PASS')
valid={'batch_id':'regional-review:'+'a'*16,'member_location_ids':['a'],'location_count':1,
       'member_location_ids_sha256':p.sha256(b'a'),'owned_evidence_path':'data/regional-review/regional-review-'+'a'*16+'/',
       'review_only':True,'original_scope_release':{'version':1,'id':'geography:review:'+'b'*64,'footprints_sha256':'c'*64,'hierarchy_sha256':'d'*64}}
body=lambda value:'```json\n'+json.dumps(value)+'\n```'
strong,weak,rejected=issue_rosters([[{'number':1,'state':'closed','body':body(valid)}]])
assert len(strong)==1 and strong[0]['work_role']=='archived-closed-predecessor-context' and not rejected
for field in ('id','footprints_sha256','hierarchy_sha256'):
    malformed=copy.deepcopy(valid);malformed['original_scope_release'][field]=1
    strong,weak,rejected=issue_rosters([[{'number':1,'state':'open','body':body(malformed)}]])
    assert not strong and rejected and weak
malformed=copy.deepcopy(valid);malformed['batch_id']=1
assert issue_rosters([[{'number':1,'state':'open','body':body(malformed)}]])[2]
print('Valid closed regional source predecessor retained; malformed typed release and batch fields rejected with provenance')
pin={'path':'original.json.gz','sha256':'a'*64};original={'component':'a'}
annotation={'component':'a','original_investigation':{'commit':p.C,'path':pin['path'],'file_sha256':pin['sha256'],'row_index':0},'native_observation_reference':{'family':'frozen-reviewed-native','component':'a'}}
p.verify_annotation_original(annotation,original,pin,0)
for field,value in [('commit','wrong'),('path','wrong'),('file_sha256','wrong'),('row_index',1)]:
    bad=copy.deepcopy(annotation);bad['original_investigation'][field]=value
    try:p.verify_annotation_original(bad,original,pin,0)
    except ValueError:pass
    else:raise AssertionError('Original investigation reference mutation escaped '+field)
for field,value in [('family','selected-repository-native'),('component','b')]:
    bad=copy.deepcopy(annotation);bad['native_observation_reference'][field]=value
    try:p.verify_annotation_original(bad,original,pin,0)
    except ValueError:pass
    else:raise AssertionError('Native reference cohort/identity mutation escaped '+field)
print('Complete original annotation identity/index/vintage/native-family controls PASS')
