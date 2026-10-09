"""Real live codec callback mutations; unchanged codec source bytes."""
import pathlib,importlib.util,json,sys
script=pathlib.Path(__file__).with_name('serialize-release-groups.py')
spec=importlib.util.spec_from_file_location('serializer',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
codec=m.load_codec(str(script.parents[3]));bindings=m.capture_serialization_bindings(codec);m.require_serialization_bindings(bindings)
negative=0
for scope,name in ((codec,'json'),(codec,'gzip'),(codec,'io'),(m.json,'dumps'),(m.json,'loads'),
    (m.gzip,'GzipFile'),(codec.io,'BytesIO'),(m.hashlib,'sha256'),(m.gzip,'decompress'),(m.gzip.zlib,'compressobj')):
    old=getattr(scope,name);setattr(scope,name,lambda *a,**k:None)
    try:
        try:m.require_serialization_bindings(bindings)
        except AssertionError:negative+=1
        else:raise AssertionError('Changed live module callback accepted')
    finally:setattr(scope,name,old)
    m.require_serialization_bindings(bindings)
for fn in (m.json.dumps,m.json.loads,m.gzip.GzipFile.write,m.json.JSONEncoder.iterencode):
    old=fn.__code__;fn.__code__=(lambda *a,**k:None).__code__
    try:
        try:m.require_serialization_bindings(bindings)
        except AssertionError:negative+=1
        else:raise AssertionError('Changed live callback code accepted')
    finally:fn.__code__=old
    m.require_serialization_bindings(bindings)
fn=m.json.dumps;old=fn.__kwdefaults__;fn.__kwdefaults__={**old,'sort_keys':True}
try:
    try:m.require_serialization_bindings(bindings)
    except AssertionError:negative+=1
    else:raise AssertionError('Changed kwdefaults accepted')
finally:fn.__kwdefaults__=old
m.require_serialization_bindings(bindings)
# In-place mutation must also fail, not merely dictionary identity replacement.
old_value=old['sort_keys'];old['sort_keys']=not old_value
try:
    try:m.require_serialization_bindings(bindings)
    except AssertionError:negative+=1
    else:raise AssertionError('In-place defaults mutation accepted')
finally:old['sort_keys']=old_value
m.require_serialization_bindings(bindings)
print(json.dumps({'positive':1,'negative':negative,'real_module_code_defaults_mutations':True,'science_rerun':False}))
