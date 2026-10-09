import importlib.util,pathlib,json,gzip,copy,base64
p=pathlib.Path('coordination/engineering/selected-geography-effective-prevention-20261009/qualification');s=importlib.util.spec_from_file_location('inverse',p/'verify-original-custody.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);v=json.loads(gzip.decompress((p/'original-execution-custody.json.gz').read_bytes()));positive=m.verify(v);neg=[]
def missing_object(q):q['objects'].pop(q['bindings'][0]['original_pin']['commit'])
def changed_body(q):
 k=next(iter(q['objects']));q['objects'][k]['base64']=base64.b64encode(b'changed').decode()
def changed_path(q):q['bindings'][0]['original_pin']['path']='foreign/path'
def changed_mode(q):q['bindings'][0]['original_pin']['mode']='100755'
def changed_hash(q):q['bindings'][0]['original_pin']['sha256']='0'*64
def changed_alias(q):
 a=next(b for b in q['bindings'] if 'published_whole_alias'in b);a['published_whole_alias']['git_blob_oid']='0'*40
for f in [missing_object,changed_body,changed_path,changed_mode,changed_hash,changed_alias]:
 q=copy.deepcopy(v);f(q)
 try:m.verify(q)
 except (AssertionError,KeyError,ValueError):neg.append(f.__name__)
 else:raise AssertionError('accepted '+f.__name__)
print(json.dumps({'positive':positive,'negative_controls':neg,'scope':'archive-only complete Git object/path inverse, no geography/source execution'},indent=2))
