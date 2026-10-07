"""Directed actual-reader controls for the five duplicated-field aliases."""
import copy,json,pathlib,sys,tempfile,os
import transport as t
p=t.p
repo=t.HERE.parents[2]
source=repo/'.cache/gshhg1261-comparison/run-one-v2'
context=t.Context(repo)
report=json.loads((source/'report.json').read_bytes())
passed=[]
def check(name,fn):fn();passed.append(name)
def rejects(name,fn,expected):
 def run():
  try:fn()
  except ValueError as error:
   assert expected in str(error),str(error)
  else:raise AssertionError('Unexpected acceptance: '+name)
 check(name,run)
fixtures={}
for kind in ('components','sources'):
 old=next(d for d in report['products']if d['path'].startswith(kind+'-'))
 body,raw=t.read_ordinary(source,old)
 rows=[json.loads(line)for line in raw.splitlines()]
 packed_rows=[t.pack_row(r,kind,context)for r in rows]
 decoded=b''.join(p.immutable.canonical_json(r)for r in packed_rows)
 encoded=p.immutable.deterministic_gzip(decoded);desc=t.descriptor(old['path'],encoded,decoded)
 restored,restored_rows=t.exact_restore(encoded,desc,old,kind,context)
 assert restored==body and p.immutable.canonical_json(restored_rows)==p.immutable.canonical_json(rows)
 passed.append('actual-complete-'+kind+'-shard-byte-and-whole-row-restoration')
 fixtures[kind]=(old,packed_rows)
def changed(kind,mutate):
 old,original=fixtures[kind];rows=copy.deepcopy(original);mutate(rows)
 raw=b''.join(p.immutable.canonical_json(r)for r in rows);encoded=p.immutable.deterministic_gzip(raw)
 return t.exact_restore(encoded,t.descriptor(old['path'],encoded,raw),old,kind,context)
rejects('actual-correctly-rehashed-wrong-current-record-ID',lambda:changed('components',lambda rows:rows[0].update(component_id='wrong-current-ID')),'Wrong/missing current component')
rejects('actual-correctly-rehashed-missing-current-alias-marker',lambda:changed('components',lambda rows:rows[0].pop(t.COMPONENT_MARKER)),'Wrong/extra/missing')
rejects('actual-correctly-rehashed-extra-supplied-current-field',lambda:changed('components',lambda rows:rows[0].update(candidate_feature_sha256='0'*64)),'Wrong/extra/missing')
rejects('actual-correctly-rehashed-wrong-alias-product',lambda:changed('components',lambda rows:rows[0].update({t.SOURCE_MARKER:'v1'})),'Wrong/extra/missing')
rejects('actual-correctly-rehashed-changed-scientific-status',lambda:changed('components',lambda rows:rows[0].update(status='directed-changed-status')),'Restored whole scientific decoded')
rejects('actual-correctly-rehashed-component-row-omission',lambda:changed('components',lambda rows:rows.pop()),'Restored whole scientific decoded')
rejects('actual-correctly-rehashed-component-row-reorder',lambda:changed('components',lambda rows:rows.reverse()),'Restored whole scientific decoded')
rejects('actual-correctly-rehashed-extra-component-row',lambda:changed('components',lambda rows:rows.append(copy.deepcopy(rows[0]))),'Restored whole scientific decoded')
rejects('actual-correctly-rehashed-wrong-native-offset',lambda:changed('sources',lambda rows:rows[0].update(native_offset=rows[0]['native_offset']+1)),'Wrong native byte position')
rejects('actual-correctly-rehashed-noninteger-native-offset',lambda:changed('sources',lambda rows:rows[0].update(native_offset=False)),'Noninteger original')
rejects('actual-correctly-rehashed-wrong-native-member-identity',lambda:changed('sources',lambda rows:rows[0].update(id=9999999)),'Wrong native source identity')
rejects('actual-correctly-rehashed-wrong-native-whole-header',lambda:changed('sources',lambda rows:rows[0]['header_native_values'].__setitem__(2,0)),'Wrong whole original native header')
rejects('actual-correctly-rehashed-supplied-untrusted-native-SHA',lambda:changed('sources',lambda rows:rows[0].update(record_sha256='0'*64)),'Wrong/extra/missing')
old,rows=fixtures['components'];raw=b''.join(p.immutable.canonical_json(r)for r in rows);encoded=p.immutable.deterministic_gzip(raw);d=t.descriptor(old['path'],encoded,raw)
for key in ('bytes','uncompressed_bytes'):
 rejects('actual-original-restoration-'+key+'-overbound',lambda key=key:t.exact_restore(encoded,d,{**old,key:p.LIMIT+1},'components',context),'Original scientific ordinary encoded/decoded bound')
rejects('actual-original-reader-overbound-before-reading',lambda:t.read_ordinary(source,{**old,'uncompressed_bytes':p.LIMIT+1}),'Original scientific ordinary encoded/decoded bound')
rejects('actual-packed-body-corruption',lambda:t.exact_restore(encoded+b'x',d,old,'components',context),'Encoded whole input')
rejects('actual-declared-packed-decoded-bound',lambda:t.exact_restore(encoded,{**d,'uncompressed_bytes':p.LIMIT+1},old,'components',context),'Declared decoded')
rejects('actual-unsafe-product-path',lambda:t.read_ordinary(source,{**old,'path':'../'+old['path']}),'Unsafe/wrong scientific')
with tempfile.TemporaryDirectory(prefix='transport-controls-',dir=repo/'.cache/gshhg1261-comparison')as tmp:
 directory=pathlib.Path(tmp);(directory/'ordinary').write_bytes(encoded);os.symlink('ordinary',directory/old['path'])
 rejects('actual-filesystem-symlink-product-reader',lambda:t.read_ordinary(directory,{**d,'path':old['path']}),'Nonordinary/missing')
 rejects('actual-filesystem-symlink-execution-path',lambda:t.checked_path(directory/old['path'],repo),'Symlink artefact')
rejects('actual-immutable-transport-commit-branch-guard',lambda:t.code_guard(repo,'main'),'Exact current immutable transport')
receipt={'result':'PASS','mode':'Actual original source/context readers and complete real-shard restoration; correctly rehashed directed mutations reach intended semantic branches. No physical/world classification run.','count':len(passed),'passed':passed,'transport_sha256':p.digest(pathlib.Path(t.__file__).read_bytes()),'control_sha256':p.digest(pathlib.Path(__file__).read_bytes()),'complete_original_input_closure':context.receipt,'real_shards':[fixtures[k][0]for k in ('components','sources')]}
(repo/'.cache/gshhg1261-comparison/transport-controls-result.json').write_bytes(p.immutable.canonical_json(receipt))
print(json.dumps({'result':'PASS','controls':len(passed),'transport_sha256':receipt['transport_sha256']}))
