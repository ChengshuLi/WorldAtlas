import ast,importlib.util,json,sys,tempfile,types,hashlib
from pathlib import Path
from shapely.geometry import mapping,Point,LineString,Polygon,MultiPolygon,GeometryCollection,MultiPoint,MultiLineString
from shapely.affinity import translate
W=Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/3d62cf18b0b42e3ae3cd26d42f5e7ac90b65e45ead741649cedd79762724f9e7/work');P=W/'coordination/engineering/complete-replay-operand-restoration-20261007';C=Path(__file__).parent
sys.path.insert(0,str(P));import objects,products
node=next(n for n in ast.parse((P/'methods/kernel.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='ordinary_mapping');ns={'mapping':mapping,'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),str(P/'methods/kernel.py'),'exec'),ns);ordinary=ns['ordinary_mapping']
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=load('cohort_original',C/'original-numerical-cohort.py');new=types.ModuleType('cohort_proposal');exec(compile((Path('/Users/chengshuli/world-atlas-workspace/.cache/root1394-native-mapping-lifetime-remedy-20261008/numerical-cohort-proposed.py')).read_text(),str(Path('/Users/chengshuli/world-atlas-workspace/.cache/root1394-native-mapping-lifetime-remedy-20261008/numerical-cohort-proposed.py')),'exec'),new.__dict__)
geometries=[Point(-0.0,0.0),LineString([(0,-0.0),(1.0000000000000002,2)]),Polygon([(0,0),(2,0),(2,2),(0,0)],holes=[[(.2,.2),(.3,.2),(.3,.3),(.2,.2)]]),MultiPolygon([Polygon([(0,0),(1,0),(0,1),(0,0)]),Polygon([(3,3),(4,3),(3,4),(3,3)])]),GeometryCollection([Point(1,2),LineString([(0,0),(1,2)])]),MultiPoint([(1,2),(3,4)]),MultiLineString([[(0,0),(1,1)],[(2,2),(3,3)]]),GeometryCollection()]
equivalent=0
for g in geometries:
 for off in (-360,0,360):
  h=translate(g,xoff=off) if off else g
  assert objects.canonical(ordinary(h))==objects.canonical(mapping(h));equivalent+=1
root=Path(tempfile.mkdtemp(prefix='tiny-',dir=C)).resolve();(root/'.cache').mkdir()
kernel=types.SimpleNamespace(mapping=mapping,ordinary_mapping=ordinary)
g=geometries[2];feature={'id':'component','geometry':ordinary(g)};row={'component_id':'component','query_relations':[{'source_id':0,'periodic_offset':off} for off in (-360,0,360)]};loaded={'modules':{'kernel':kernel},'state':{'candidates':{'component':feature},'routing':{'component':{'current_feature_sha256':'abc'}}},'physical':{'component':(row,{'sha256':'original-row'})},'diagnoses':{'component':{'component_id':'component'}}};records={0:({},g)};aliases={0:{'original':True}}
def prepare(module,name):
 phase=types.SimpleNamespace(reserve=32*1024*1024,payloads=[],reads=set(),pins={},destination=root/'.cache'/name,repo=root)
 prod=module.BudgetedProducts(phase,products,types.SimpleNamespace(require=objects.require,FILE=33554432))
 obj=module.bounded_objects(objects,prod,loaded,records,aliases);return obj,prod
ob,op=prepare(old,'old');nb,np=prepare(new,'new')
assert ob.native==nb.native
for ali in [a for rows in ob.native.values() for a in rows]:assert ob._resolved_bytes(ali)==nb._resolved_bytes(ali)
for o in (ob,nb):o.begin('component')
value={'native':ordinary(translate(g,xoff=360)),'original':ordinary(g),'fresh':ordinary(Polygon([(5,5),(6,5),(5,6),(5,5)]))}
assert objects.canonical(ob.retain(value))==objects.canonical(nb.retain(value));assert op.finish()==np.finish()
for pin in op.outputs:assert (op.directory/pin['path']).read_bytes()==(np.directory/pin['path']).read_bytes()
base=next(iter(nb.native.values()))[0];neg=[]
def reject(name,fn):
 try:fn()
 except Exception as e:neg.append({'name':name,'error':str(e)});return
 raise AssertionError(name+' accepted')
for key,val in [('source_id','0'),('periodic_offset',1),('periodic_offset','0'),('original_native_record',{}),('whole_mapping_bytes',base['whole_mapping_bytes']+1),('whole_mapping_sha256','0'*64)]:
 a=dict(base);a[key]=val;reject(key+str(val),lambda a=a:nb._resolved_bytes(a))
original=kernel.mapping;kernel.mapping=lambda g:mapping(g);reject('mapping callable mutation',lambda:nb._resolved_bytes(base));kernel.mapping=original
origalias=aliases[0];aliases[0]={'tampered':True};reject('original native pin mutation',lambda:nb._resolved_bytes(base));aliases[0]=origalias
records[0]=({},translate(g,xoff=.125));reject('coordinate pointset drift',lambda:nb._resolved_bytes(base));records[0]=({},g)
result={'proposal_sha256':hashlib.sha256((Path('/Users/chengshuli/world-atlas-workspace/.cache/root1394-native-mapping-lifetime-remedy-20261008/numerical-cohort-proposed.py')).read_bytes()).hexdigest(),'literal_kernel_mapping_bytes_equivalent':equivalent,'native_indices_and_full_inverse_equal':True,'original_retain_and_products_full_output_bytes_equal':True,'negatives':neg,'scope':'Tiny actual original Objects/Products and literal original kernel function controls only; no full native0 or cohort scientific execution/RSS qualification.'};(C/'root-proposal-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
