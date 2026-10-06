"""Small directed controls execute the committed producer's actual geometry loop."""
import ast,collections,hashlib,json,pathlib,gzip,copy
import shapely
from shapely import STRtree,union_all
from shapely.geometry import shape,mapping,Polygon,box
from shapely.errors import GEOSException
CASE=pathlib.Path(__file__).resolve().parent
source=(CASE/'producer.py').read_text();tree=ast.parse(source)
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ('canon','sha','decode','geometry','verify_complete_roster','verify_historical_row')]
namespace={'json':json,'hashlib':hashlib,'gzip':gzip,'mapping':mapping}
exec(compile(ast.Module(body=functions,type_ignores=[]),'actual-producer-functions','exec'),namespace)
# Keep the actual row construction and complete geometric try/except unchanged.
loop=next(n for n in tree.body if isinstance(n,ast.For)and ast.unparse(n.target)=='i'and ast.unparse(n.iter)=='sorted(targets)')
stop=next(k for k,n in enumerate(loop.body)if isinstance(n,ast.If)and ast.unparse(n.test)=="'whole_relevant_source_union' in row")
probe=copy.deepcopy(loop);probe.body=probe.body[:stop]
probe.body.append(ast.parse('result.append(row)').body[0]);ast.fix_missing_locations(probe)
code=compile(ast.Module(body=[probe],type_ignores=[]),'actual-producer-geometric-loop','exec')
def run(g,gs,subjects=None):
 fs={'id':'family','source_families':[{'source_id':'source'}],'best_rank':{'measured_impact':1},'component_count':1,'existing_related_issues':[]}
 rows=[{'feature_index':n,'shapeID':str(n),'feature_sha256':'fixture','geometry_sha256':namespace['sha'](namespace['canon'](mapping(s))),'recorded_stable_subjects':(subjects or {}).get(n,[]),'valid_polygon':s.is_valid and not s.is_empty and s.geom_type in ('Polygon','MultiPolygon')}for n,s in enumerate(gs)]
 ns=dict(namespace,targets={'component':fs},features={'component':{'id':'component','geometry':mapping(g),'properties':{}}},products={'source':{'geometries':gs,'rows':rows,'tree':STRtree(gs)}},shape=shape,M='original',S='successor',current_upserts={},family_summary={},collections=collections,GEOSException=GEOSException,union_all=union_all,validity=collections.Counter(),registry={'source':{'boundaryYearRepresented':2000}},result=[])
 exec(code,ns);return ns['result'][0]
checks=[]
def check(name,condition):assert condition,name;checks.append(name)
g=box(0,0,1,1);subject={'id':'stable','reference_year':2000}
r=run(g,[box(-1,-1,2,2)],{0:[subject]});check('full one-compatible observed source coverage',r['status']=='one-compatible-recorded-subject-uniquely-covers-component');check('water/ownership/cause remain unapproved',r['administrative_assignment']is None and r['surface_status']=='unverified'and r['cause_status']=='unknown')
r=run(g,[box(-1,-1,2,2),box(.5,.5,2,2)],{0:[subject]});check('overlap cannot become unique owner',r['status']=='positive-source-coverage-mixed-partial-or-subject-unresolved'and len(r['positive_area_feature_ids'])==2)
hole=Polygon([(-1,-1),(2,-1),(2,2),(-1,2)],holes=[[(-.1,-.1),(1.1,-.1),(1.1,1.1),(-.1,1.1)]])
r=run(g,[hole]);check('holes preserve uncovered full pointset',r['source_union_intersection']['is_empty']and r['component_minus_source_union']['geometry_sha256']==namespace['sha'](namespace['canon'](mapping(g.difference(hole)))))
r=run(g,[box(1,0,2,1),box(1,1,2,2),box(9,9,10,10)]);check('edge and point zero contacts retained separately',len(r['zero_area_feature_ids'])==2 and not r['positive_area_feature_ids']and r['status']=='zero-area-contact-only');check('full product count includes noncontact feature',r['whole_product_bbox_queries'][0]['whole_product_feature_count']==3 and r['whole_product_bbox_queries'][0]['complete_bbox_candidate_indices']==[0,1])
bow=Polygon([(0,0),(1,1),(0,1),(1,0),(0,0)]);r=run(g,[bow]);check('invalid source retained unknown without repair',r['status']=='unknown-invalid-source-candidate'and r['unknowns'][0]['binding']['valid_polygon']is False)
r=run(bow,[g]);check('invalid component retained unknown',r['status']=='unknown-component-or-intersection-operation'and r['component_geometry']==mapping(bow))
for name,b,p in [('encoded whole pin mutation',b'{}',{'bytes':2,'sha256':'bad'}),('decoded whole pin mutation',gzip.compress(b'{}',mtime=0),{'bytes':len(gzip.compress(b'{}',mtime=0)),'sha256':namespace['sha'](gzip.compress(b'{}',mtime=0)),'uncompressed_bytes':2,'uncompressed_sha256':'bad'})]:
 try:namespace['decode'](b,p)
 except AssertionError:checks.append(name)
 else:raise AssertionError(name)
try:namespace['decode'](b'{bad')
except json.JSONDecodeError:checks.append('malformed full source body fatal')
else:raise AssertionError('malformed source accepted')
# Whole canonical pointsets retain interior coordinate changes and holes, with no rounding.
changed=copy.deepcopy(mapping(g));changed['coordinates']=(((0,0),(0,1),(1,1),(1.0000000000000002,0),(0,0)),)
check('sub-ulp-scale coordinate change not normalized',namespace['sha'](namespace['canon'](changed))!=namespace['sha'](namespace['canon'](mapping(g))))
for name,actual,wanted in [('missing complete member',['a'],['a','b']),('duplicate complete member',['a','a'],['a'])]:
 try:namespace['verify_complete_roster'](actual,wanted)
 except AssertionError:checks.append(name)
 else:raise AssertionError(name)
namespace['verify_complete_roster'](['b','a'],['a','b']);checks.append('complete reordered roster positive')
namespace['verify_historical_row']({'geometry':mapping(g)},namespace['sha'](namespace['canon']({'geometry':mapping(g)})))
try:namespace['verify_historical_row']({'geometry':changed},namespace['sha'](namespace['canon']({'geometry':mapping(g)})))
except AssertionError:checks.append('full historical pointset mismatch rejected')
else:raise AssertionError('changed pointset accepted')
# Directed historical roundoff disagreement executes the actual consistency branch;
# no epsilon is introduced and the scientific status remains untouched.
branch=next(n for n in loop.body if isinstance(n,ast.If)and ast.unparse(n.test)=="'source_union_intersection' in row")
branchcode=compile(ast.Module(body=[copy.deepcopy(branch)],type_ignores=[]),'actual-consistency-branch','exec')
unknowns=json.loads(gzip.decompress((CASE/'historical/operation-unknowns.json.gz').read_bytes()))
fixture=next(x['full_record']for x in unknowns if 'full_record'in x)
ns={'row':fixture,'i':fixture['component'],'consistency':[]};exec(branchcode,ns)
check('actual union-only positive remains explicit unknown',len(ns['consistency'])==1 and fixture['source_union_intersection']['planar_area_coordinate_units_squared']>0 and all(x['intersection']['planar_area_coordinate_units_squared']==0 for x in fixture['feature_intersections']))
positive=copy.deepcopy(fixture);positive['source_union_intersection']['planar_area_coordinate_units_squared']=0
ns={'row':positive,'i':positive['component'],'consistency':[]};exec(branchcode,ns);check('both literal zero areas consistent positive control',not ns['consistency'])
positive=copy.deepcopy(fixture);positive['feature_intersections'][0]['intersection']['planar_area_coordinate_units_squared']=fixture['source_union_intersection']['planar_area_coordinate_units_squared']
ns={'row':positive,'i':positive['component'],'consistency':[]};exec(branchcode,ns);check('both literal positive areas consistent control',not ns['consistency'])
# Exercise the producer's complete multipart source loading/indexing guard.
product_loop=next(n for n in tree.body if isinstance(n,ast.For)and ast.unparse(n.target)=='product')
product_code=compile(ast.Module(body=[copy.deepcopy(product_loop)],type_ignores=[]),'actual-whole-source-loader','exec')
feature={'type':'Feature','properties':{'shapeID':'one'},'geometry':mapping(g)}
raw=namespace['canon']({'type':'FeatureCollection','features':[feature]});part={'alias':'fixture','bytes':len(gzip.compress(raw,mtime=0)),'sha256':namespace['sha'](gzip.compress(raw,mtime=0)),'uncompressed_bytes':len(raw),'uncompressed_sha256':namespace['sha'](raw),'offset':0}
product={'key':'source','original_bytes':len(raw),'original_sha256':namespace['sha'](raw),'feature_count':1,'parts':[part]}
binding={'feature_index':0,'shapeID':'one','feature_sha256':namespace['sha'](namespace['canon'](feature)),'geometry_sha256':namespace['sha'](namespace['canon'](feature['geometry'])),'recorded_stable_subjects':[],'valid_polygon':True}
def load(product,registry_sha=None,binding_override=None):
 ns=dict(namespace,config={'source_products':[product]},products={},source_receipts=[],historical_sources={'source':{'complete_source':{'fixture':True},'complete_features':[binding_override or binding]}},registry={'source':{'sha256':registry_sha or namespace['sha'](raw)}},subjectmap={},shape=shape,STRtree=STRtree,gc=__import__('gc'),read_alias=lambda p:gzip.compress(raw,mtime=0))
 exec(product_code,ns);return ns
check('complete multipart source positive',len(load(product)['products']['source']['rows'])==1)
for name,mutate,registry_sha,binding_override in [('wrong original source whole SHA',lambda p:p.update(original_sha256='bad'),None,None),('wrong multipart offset',lambda p:p['parts'][0].update(offset=1),None,None),('missing full source feature',lambda p:p.update(feature_count=2),None,None),('wrong original registry vintage',lambda p:None,'bad',None),('changed full source feature binding',lambda p:None,None,{**binding,'feature_sha256':'bad'})]:
 value=copy.deepcopy(product);mutate(value)
 try:load(value,registry_sha,binding_override)
 except AssertionError:checks.append(name)
 else:raise AssertionError(name)
# Execute the actual final readback report-custody assertions with directed changes.
reader_tree=ast.parse((CASE/'verify-runs.py').read_text())
reader_loop=next(n for n in reader_tree.body if isinstance(n,ast.For)and ast.unparse(n.target)=='directory')
start=next(k for k,n in enumerate(reader_loop.body)if isinstance(n,ast.Assign)and any(ast.unparse(t)=='report'for t in n.targets))+1
stop=next(k for k,n in enumerate(reader_loop.body)if isinstance(n,ast.Assign)and any(ast.unparse(t)=='objects'for t in n.targets))
guards=compile(ast.Module(body=copy.deepcopy(reader_loop.body[start:stop]),type_ignores=[]),'actual-report-custody-guards','exec')
actual_report=json.loads(gzip.decompress((CASE/'verification/run-one-actual-report.json.gz').read_bytes()));config=json.loads((CASE/'input-config.json').read_bytes());scope=json.loads((CASE/'scope.json').read_bytes());expected_rows=json.loads(gzip.decompress((CASE/'historical/expected-complete-records.json.gz').read_bytes()));expected={x['component']:x for x in expected_rows}
def verify_report(report):
 ns=dict(namespace,CASE=CASE,subprocess=__import__('subprocess'),report=report,config=config,scope=scope,expected=expected);exec(guards,ns)
verify_report(actual_report);checks.append('actual complete execution receipt positive')
for name,change in [('missing actual source product receipt',lambda r:r['source_input_products'].pop()),('wrong executed producer bytes',lambda r:r.update(script_sha256='bad')),('wrong executed scope bytes',lambda r:r.update(scope_sha256='bad')),('undeclared claimed immutable input',lambda r:r['immutable_input_aliases'].append({'bad':'binding'}))]:
 value=copy.deepcopy(actual_report);change(value)
 try:verify_report(value)
 except AssertionError:checks.append(name)
 else:raise AssertionError(name)
print(json.dumps({'status':'PASS','controls':checks,'producer_sha256':namespace['sha'](source.encode()),'limits':'Small fixtures of actual loop; not a complete scientific run or final artifact acceptance.'},sort_keys=True))
