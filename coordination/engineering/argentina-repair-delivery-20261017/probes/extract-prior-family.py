"""Retain the complete original seven-component Argentina source-fitness family.
Only immutable whole Git bodies are read; no geometry operation is performed.
Usage: python extract-prior-family.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
"""
import gzip,hashlib,json,os,subprocess,sys,time
from pathlib import Path
assert len(sys.argv)==4 and __debug__
R=Path(sys.argv[1]).absolute();C=sys.argv[2];O=Path(sys.argv[3]).absolute();H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';I='c6a26e1caba54e1b81a89fbda3a64fff56da323d';M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f';S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98';P='coordination/engineering/argentina-repair-delivery-20261017'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)
assert O.parent.is_dir()and not O.exists()and not O.is_symlink()and all(not p.is_symlink()for p in [R,O,*R.parents,*O.parents])
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
inputs={};total=0;start=time.monotonic();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def read(h,p,decode=False):
 global total
 assert len(h)==40 and all(c in '0123456789abcdef'for c in h)and not p.startswith('/')and all(x not in ('','.','..')for x in p.split('/'))
 def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(R),*args],env=env,timeout=30)
 row=git('ls-tree','-z',h,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 n=int(git('cat-file','-s',oid));assert 0<n
 b=git('cat-file','blob',oid);assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':h,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if decode:
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b))as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(h,p)not in inputs:total+=n+pin.get('decoded_bytes',0)
 assert time.monotonic()-start<120;inputs[h,p]=pin;return b
assert read(C,P+'/probes/extract-prior-family.py')==Path(__file__).read_bytes()
fpath='research/geography/argentina-gap-source-fitness-20261007/vintages/argentina-run-replay-20261007154702696203-8d548285/source-fit.json';fit=json.loads(read(H,fpath));expected={r['component']:r for r in fit['complete_component_source_rows_in_family_order']};wanted=fit['family_scope']['component_ids'];assert len(expected)==len(wanted)==7 and sorted(expected)==wanted and sha(canon(wanted))==fit['family_scope']['component_ids_sha256']
assert all(r['original_component_commit']==M and r['current_component_relation']=='retained-full-original-feature-pointset'for r in expected.values())
inventory=json.loads(read(I,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'));found={}
for pin in inventory['complete_products']['components']:
 p=next(p['path']for p in inventory['source_descriptors']if p['sha256']==pin['sha256']);d=read(M,p,True);actual=inputs[M,p];assert actual['bytes']==pin['bytes']and actual['sha256']==pin['sha256']and len(d)==pin['uncompressed_bytes']and sha(d)==pin['uncompressed_sha256']
 collection=json.loads(d);assert collection['type']=='FeatureCollection'
 for f in collection['features']:
  if f['id']in expected:
   assert f['id']not in found;assert sha(canon(f))==expected[f['id']]['full_component_feature_sha256']and sha(canon(f['geometry']))==expected[f['id']]['component_geometry_sha256'];found[f['id']]=f
assert set(found)==set(expected)
sp='coordination/engineering/worldwide-successor-1215-20261006/run-one/';report=json.loads(read(S,sp+'report.json'));pin=next(p for p in report['products']if p['path']=='components-delta.json.gz');d=read(S,sp+pin['path'],True);actual=inputs[S,sp+pin['path']];assert actual['bytes']==pin['bytes']and actual['sha256']==pin['sha256']and len(d)==pin['uncompressed_bytes']and sha(d)==pin['uncompressed_sha256'];delta=json.loads(d);assert not set(wanted)&set(delta['removed_ids'])and not set(wanted)&{f['id']for f in delta['upsert_records']}
products={'candidate-components.geojson':{'type':'FeatureCollection','features':[found[i]for i in wanted]},'extraction.json':{'kind':'complete-original-seven-component-Argentina-family-extraction','family_id':fit['family_id'],'complete_component_ids':wanted,'source_fitness_assessment':fit['assessment'],'recorded_land_source_fitness_rows':fit['recorded_land_source_fitness_rows'],'input_encoded_decoded_bytes':total,'inputs':list(inputs.values()),'limits':['This authenticates complete retained original pointsets, not source fitness or native overlap.','The unresolved source-fitness prerequisite and all seven complete component dispositions remain retained.'],'elapsed_seconds':time.monotonic()-start}}
encoded={n:canon(v)for n,v in products.items()}
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in[O,*O.parents]);O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
print(json.dumps({'components':len(found),'inputs_encoded_decoded':total,'outputs':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in encoded.items()},'seconds':time.monotonic()-start}))
