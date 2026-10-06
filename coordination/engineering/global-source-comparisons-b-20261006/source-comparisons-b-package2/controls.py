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
print(json.dumps({'status':'PASS','controls':checks,'producer_sha256':namespace['sha'](source.encode()),'limits':'Small fixtures of actual loop; not a complete scientific run or final artifact acceptance.'},sort_keys=True))
