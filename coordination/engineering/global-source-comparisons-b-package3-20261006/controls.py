"""Directed controls execute the actual frozen producer loop and input reader."""
import ast, pathlib, json, hashlib, collections, time, gzip, argparse, re, types
from shapely import STRtree, union_all
from shapely.geometry import shape, mapping
from shapely.errors import GEOSException

def canon(v):return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
def sha(b):return hashlib.sha256(b).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=False)
root=pathlib.Path(__file__).parent;code=(root/'producer.py').read_bytes();tree=ast.parse(code)
loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='binding')
poly={'type':'Polygon','coordinates':[[[0,0],[3,0],[3,3],[0,3],[0,0]],[[1,1],[1,2],[2,2],[2,1],[1,1]]]}
def rectangle(x0,y0,x1,y1):return {'type':'Polygon','coordinates':[[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]]}
features={i:{'type':'Feature','id':i,'properties':{},'geometry':g} for i,g in [('inside',rectangle(.1,.1,.9,.9)),('hole',rectangle(1.1,1.1,1.9,1.9)),('zero',rectangle(3,.1,4,.9)),('invalid',rectangle(.1,.1,.9,.9))]}
sg=shape(poly);bow=shape({'type':'Polygon','coordinates':[[[0,0],[2,2],[0,2],[2,0],[0,0]]]});assert not bow.is_valid
subject={'id':'fixture-recorded-subject','reference_year':'2020'}
products={}
for sid,g in [('valid',sg),('invalid',bow)]:
 meta={'feature_index':0,'shapeID':sid,'feature_sha256':sha(canon(mapping(g))),'geometry_sha256':sha(canon(mapping(g))),'recorded_stable_subjects':[subject],'valid_polygon':g.is_valid}
 products[sid]={'geometries':[g],'rows':[meta],'tree':STRtree([g])}
targets={i:{'id':'family-'+i,'source_families':[{'source_id':'invalid' if i=='invalid' else 'valid'}],'best_rank':{},'component_count':1,'existing_related_issues':[]} for i in features}
objects={}
def preserve_union_object(v):
 b=canon(v);h=sha(b);objects[h]=v;return {'geometry_object_sha256':h,'canonical_geometry_bytes':len(b),'object_index':'source-union-object-index.json'}
def geometry(g):return {'geometry':mapping(g),'geometry_sha256':sha(canon(mapping(g))),'geometry_type':g.geom_type,'is_empty':g.is_empty,'is_valid':g.is_valid,'planar_area_coordinate_units_squared':g.area,'planar_length_coordinate_units':g.length}
ns=globals().copy();ns.update({'historical_rows':[{'component':i} for i in features],'family_summary':{},'current_upserts':{},'M':'original-fixture','S':'successor-fixture','registry':{'valid':{'boundaryYearRepresented':'2020'},'invalid':{'boundaryYearRepresented':'2020'}},'counts':collections.Counter(),'validity':collections.Counter(),'processed':[],'batch':[],'size':0,'start':time.monotonic(),'O':out})
exec(compile(ast.Module(body=[loop],type_ignores=[]),'actual-producer-loop','exec'),ns)
rows={v['component']:v for v in ns['batch']};assert rows['inside']['status']=='one-compatible-recorded-subject-uniquely-covers-component';assert rows['hole']['status']=='no-source-intersection-in-literal-domain';assert rows['zero']['status']=='zero-area-contact-only';assert rows['invalid']['status']=='unknown-invalid-source-candidate'
assert all(v['surface_status']=='unverified' and v['administrative_assignment'] is None and v['cause_status']=='unknown' for v in rows.values())
for i,v in rows.items():assert v['full_component_feature_sha256']==sha(canon(features[i])) and v['component_geometry_sha256']==sha(canon(features[i]['geometry']))
# Execute the actual bound input reader with retained bytes, then a changed body.
reader=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='git')
pin={'bytes':3,'sha256':sha(b'raw')};fixture={'alias_map':{('commit','path'):{'owned_path':'fixture','original_pin':pin}},'frozen':lambda _:b'raw','sha':sha}
exec(compile(ast.Module(body=[reader],type_ignores=[]),'actual-input-reader','exec'),fixture);assert fixture['git']('commit','path')==b'raw'
fixture['frozen']=lambda _:b'bad'
try:fixture['git']('commit','path')
except AssertionError:pass
else:raise AssertionError('actual reader accepted changed source bytes')
try:fixture['git']('commit','omitted')
except KeyError:pass
else:raise AssertionError('actual reader accepted missing source alias')
# Execute the actual verifier's numerical discrepancy branch on retained evidence.
verifier=ast.parse((root/'verify.py').read_bytes());outer=next(n for n in verifier.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='pin' and isinstance(n.iter,ast.Subscript) and isinstance(n.iter.value,ast.Name) and n.iter.value.id=='report');inner=next(n for n in outer.body if isinstance(n,ast.For));diagnostic=[]
for n in inner.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('unionarea','positive') for t in n.targets):diagnostic.append(n)
 if isinstance(n,ast.If) and any(isinstance(k,ast.Call) and isinstance(k.func,ast.Attribute) and isinstance(k.func.value,ast.Name) and k.func.value.id=='unknown' for k in ast.walk(n)):diagnostic.append(n)
assert len(diagnostic)==3
fixture_record=json.loads(gzip.decompress((root/'historical-consistency-fixture.json.gz').read_bytes()));actual=fixture_record['full_record'];assert sha(canon(actual))==fixture_record['original_binding']['full_row_sha256']
for label,row,expected in [('retained-real-disagreement',actual,True),('literal-zero-consistent',{'source_union_intersection':{'planar_area_coordinate_units_squared':0},'feature_intersections':[{'intersection':{'planar_area_coordinate_units_squared':0}}]},False),('literal-positive-consistent',{'source_union_intersection':{'planar_area_coordinate_units_squared':1},'feature_intersections':[{'intersection':{'planar_area_coordinate_units_squared':1}}]},False)]:
 context={'row':row,'unknown':[],'i':label};exec(compile(ast.Module(body=diagnostic,type_ignores=[]),'actual-consistency-branch','exec'),context);assert bool(context['unknown'])==expected
# Actual verifier ordinary reader rejects changed and missing source receipts.
byte_reader=next(n for n in verifier.body if isinstance(n,ast.FunctionDef) and n.name=='checked_bytes');json_reader=next(n for n in verifier.body if isinstance(n,ast.FunctionDef) and n.name=='checked')
reader_context={'run':out,'pathlib':pathlib,'sha':sha,'gzip':gzip,'json':json};exec(compile(ast.Module(body=[byte_reader,json_reader],type_ignores=[]),'actual-verifier-readers','exec'),reader_context)
receipt_body=gzip.compress(canon({'retained-source-receipt':True}),mtime=0);receipt_file=out/'source-receipt-fixture.json.gz';receipt_file.write_bytes(receipt_body);receipt_pin={'path':receipt_file.name,'bytes':len(receipt_body),'sha256':sha(receipt_body)}
assert reader_context['checked'](receipt_pin)=={'retained-source-receipt':True}
receipt_file.write_bytes(receipt_body[:-1])
try:reader_context['checked'](receipt_pin)
except AssertionError:pass
else:raise AssertionError('actual verifier accepted changed source receipt')
receipt_file.unlink()
try:reader_context['checked'](receipt_pin)
except AssertionError:pass
else:raise AssertionError('actual verifier accepted missing source receipt')
# Complete hash-matching bytes outside the run may not satisfy its receipt.
receipt_file.write_bytes(receipt_body)
escape_source=out.parent/(out.name+'-outside-source-receipt.json');assert not escape_source.exists();escape_source.write_bytes(receipt_body)
escape_link=out/'escape';escape_link.symlink_to(out.parent.resolve(),target_is_directory=True)
for bad in ['../'+escape_source.name,str(escape_source.resolve()),'escape/'+escape_source.name]:
 try:reader_context['checked'](dict(receipt_pin,path=bad))
 except AssertionError:pass
 else:raise AssertionError('actual verifier accepted external/symlink-ancestor receipt')
escape_link.unlink();escape_source.unlink()
assert reader_context['checked'](receipt_pin)=={'retained-source-receipt':True}
# Execute the actual full-family loading loop and its complete-roster assertion.
family_loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='pin' and isinstance(n.iter,ast.Subscript) and isinstance(n.iter.value,ast.Subscript) and isinstance(n.iter.value.value,ast.Name) and n.iter.value.value.id=='report')
family_assert=tree.body[tree.body.index(family_loop)+1];assert isinstance(family_assert,ast.Assert)
family_block=compile(ast.Module(body=[family_loop,family_assert],type_ignores=[]),'actual-complete-family-reader','exec')
def family_fixture(records,expected):
 context={'report':{'outputs':{'current-batches':[{'path':'fixture'}]}},'HEAD':'fixture','git':lambda *_:records,'decode':lambda body,*_:body,'family_ids':{'family'},'targets':{},'families':[],'scope':{'complete_component_ids':expected},'sha':sha,'canon':canon}
 exec(family_block,context)
 return context
full={'id':'family','component_ids':['c1','c2'],'component_count':2,'component_ids_sha256':sha(canon(['c1','c2']))}
assert set(family_fixture([full],['c1','c2'])['targets'])=={'c1','c2'}
for records,expected in [([dict(full,component_ids=['c1','c1'])],['c1','c2']),([full],['c1']),([full,full],['c1','c2'])]:
 try:family_fixture(records,expected)
 except AssertionError:pass
 else:raise AssertionError('actual family reader accepted duplicate or omitted members')
# Exercise actual immutable expectation and selector functions, preserving body mutation failures.
selector=next(n for n in verifier.body if isinstance(n,ast.FunctionDef) and n.name=='validate_selector')
selector_context={'re':re};exec(compile(ast.Module(body=[selector],type_ignores=[]),'actual-selector', 'exec'),selector_context)
selector_context['validate_selector']('a'*40)
for bad in ['not-an-immutable-commit','A'*40,'a'*39]:
 try:selector_context['validate_selector'](bad)
 except AssertionError:pass
 else:raise AssertionError('actual verifier accepted invalid producer selector')
expected_reader=next(n for n in verifier.body if isinstance(n,ast.FunctionDef) and n.name=='frozen_expected')
expected_root=out/'immutable-expectations';expected_root.mkdir();original={'scope.json':canon({'complete_component_ids':['original']}),'historical-original-rows.json.gz':gzip.compress(canon([{'component':'original'}]),mtime=0)}
for name,body in original.items():(expected_root/name).write_bytes(body)
class FrozenGitFixture:
 @staticmethod
 def check_output(command,cwd):
  if command[1]=='ls-tree':return b'100644 blob '+b'a'*40+b'\t'+command[-1].encode()+b'\n'
  assert command[1]=='show';return original[command[2].split(':',1)[1].split('/',1)[1]]
expected_context={'pathlib':pathlib,'subprocess':FrozenGitFixture,'root':expected_root,'ROOT':out,'PREFIX':'fixture','a':types.SimpleNamespace(producer_commit='a'*40)}
exec(compile(ast.Module(body=[expected_reader],type_ignores=[]),'actual-immutable-expectation-reader','exec'),expected_context)
for name,body in original.items():
 assert expected_context['frozen_expected'](name)==body
 (expected_root/name).write_bytes(b'coherently-rebound-local-expectation')
 try:expected_context['frozen_expected'](name)
 except AssertionError:pass
 else:raise AssertionError('actual verifier accepted mutable expected scope/rows')
 (expected_root/name).write_bytes(body)
root_link=out.parent/(out.name+'-run-root-link');root_link.symlink_to(out.resolve(),target_is_directory=True)
reader_context['run']=root_link
try:reader_context['checked'](receipt_pin)
except AssertionError:pass
else:raise AssertionError('actual verifier accepted symlink run root')
root_link.unlink();reader_context['run']=out
# Exercise actual retainer source/target containment and whole-byte positive path.
retainer=ast.parse((root/'retain-run.py').read_bytes());functions=[n for n in retainer.body if isinstance(n,ast.FunctionDef) and n.name in ['checked_source','retain']];assert len(functions)==2
retained_root=out/'retained-fixture';retained_root.mkdir();retainer_context={'pathlib':pathlib,'run':out,'CASE':retained_root,'ROOT':out,'gzip':gzip,'sha':sha}
exec(compile(ast.Module(body=functions,type_ignores=[]),'actual-retainer-readers','exec'),retainer_context)
assert retainer_context['checked_source'](receipt_file.name)==receipt_body
positive_pin=retainer_context['retain']('ordinary/source.json.gz',receipt_body);assert(retained_root/'ordinary/source.json.gz').read_bytes()==receipt_body
source_link=out/'source-parent-link';source_link.symlink_to(out.resolve(),target_is_directory=True)
try:retainer_context['checked_source']('source-parent-link/'+receipt_file.name)
except AssertionError:pass
else:raise AssertionError('actual retainer accepted symlink source ancestor')
source_link.unlink();target_link=retained_root/'target-parent-link';target_link.symlink_to(out.resolve(),target_is_directory=True)
try:retainer_context['retain']('target-parent-link/new.json.gz',receipt_body)
except AssertionError:pass
else:raise AssertionError('actual retainer wrote through target ancestor symlink')
target_link.unlink()
# Actual process entry rejects mutable/option selectors before writes or Git reads.
import subprocess,sys
for label,selector in [('short-selector','abc123'),('uppercase-selector','A'*40),('option-selector','--output=injected')]:
 destination=out/(label+'-science')
 command=[sys.executable,'-B',str(root/'producer.py'),'--repo',str(root.parents[2]),'--producer-commit='+selector,'--output',str(destination.resolve()),'--validate-inputs-only']
 observed=subprocess.run(command,capture_output=True)
 assert observed.returncode!=0 and not destination.exists()
result={'outcome':'passed','actual_producer_sha256':sha(code),'actual_control_sha256':sha(pathlib.Path(__file__).read_bytes()),'controls':['whole component original pointset hashes','full source polygon hole retained','positive source coverage retains unknown surface/ownership/cause','zero-area boundary contact retained','invalid source feature remains explicit unknown','actual input reader rejects changed whole source bytes','actual input reader rejects omitted alias','retained actual numerical inconsistency remains unknown','zero and positive consistent diagnostics remain consistent','actual verifier rejects changed and missing source receipts','actual verifier rejects escaping and symlink-ancestor matching receipt bytes','actual family reader accepts complete roster','actual family reader rejects duplicated component members','actual family reader rejects omitted scope members','actual family reader rejects duplicated family records','actual verifier rejects invalid immutable selector','actual immutable reader rejects locally rebound expected scope','actual immutable reader rejects locally rebound expected rows','actual verifier rejects symlink run root','actual retainer accepts exact ordinary complete bytes','actual retainer rejects source ancestor symlink','actual retainer rejects target ancestor symlink','actual producer short selector rejects before output creation','actual producer uppercase selector rejects before output creation','actual producer Git option selector rejects before output creation'],'units':'literal source coordinate diagnostics and whole-byte custody; no geographic area/distance or water approval','row_statuses':{i:v['status']for i,v in rows.items()}}
(out/'positive-control.json').write_bytes(canon(result));(out/'negative-control.json').write_bytes(canon(result));print(json.dumps(result))
