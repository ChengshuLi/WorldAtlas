"""Directed actual-current binding, unknown-roster and existing reader controls."""
import copy,importlib.util,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('current',ROOT/'scripts/build-worldwide-current-native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('Intended complete binding rejection did not occur')
feature={'id':'a','properties':{'fragment_bindings':[{'id':'f'}],'unmeasured_fragment_ids':['f']},'geometry':{'type':'Polygon','coordinates':[]}}
lineage={'id':'a','full_feature_sha256':m.sha256(m.canonical_json(feature)),'fragment_ids':['f'],'unmeasured_fragment_ids':['f']}
m.verify_lineage_bindings([feature],[lineage])
for field,value in [('id','redirected'),('full_feature_sha256','changed'),('fragment_ids',[]),('unmeasured_fragment_ids',[])]:
    reject(lambda field=field,value=value:m.verify_lineage_bindings([feature],[{**lineage,field:value}]))
reject(lambda:m.verify_lineage_bindings([feature],[lineage,lineage]));reject(lambda:m.verify_lineage_bindings([feature],[]))
context={'id':'a','original_feature_sha256':'original-feature','original_metadata':{'nested':'old'},'selected_successor_context':{'feature_sha256':'current-feature','metadata':{'nested':'new'},'ancestry':[],'original_parent_id':None}}
proof={'id':'a','original_feature_sha256':'original-feature','current_feature_sha256':'current-feature','current_metadata_sha256':'whole-non-geometry-fields-not-nested-metadata'}
result=m.verify_source_proofs({'a':context},[proof]);assert result['a']['original_metadata']=={'nested':'new'}
for field,value in [('id','redirected'),('original_feature_sha256','changed'),('current_feature_sha256','changed')]:
    reject(lambda field=field,value=value:m.verify_source_proofs({'a':context},[{**proof,field:value}]))
reject(lambda:m.verify_source_proofs({'a':context},[]));reject(lambda:m.verify_source_proofs({'a':context},[proof,proof]))
inputs=m.base.Inputs();delta,reconstruct,binding=m.successor_readers(inputs)
original=[{'id':'a','unknown':['f']},{'id':'b','unknown':[]}];current=[{'id':'b','unknown':[]},{'id':'c','unknown':['u']}]
d=delta(original,current);assert reconstruct(original,d)==current
for field,value in [('retained_count',2),('removed_ids',[]),('current_count',3),('current_records_sha256','changed')]:
    reject(lambda field=field,value=value:reconstruct(original,{**d,field:value}))
assert binding['commit']==m.S and set(binding['functions'])=={'record_delta','reconstruct'}
print('Current whole-feature/context domains, full lineage/unknown rosters and exact source-defined delta reader controls PASS')
