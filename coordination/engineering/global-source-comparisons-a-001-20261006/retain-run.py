"""Retain whole emitted bytes and explicit paths; never execute scientific geometry."""
import argparse,gzip,hashlib,json,pathlib,sys,subprocess,re
CASE=pathlib.Path(__file__).resolve().parent
ROOT=CASE.parents[2]
p=argparse.ArgumentParser();p.add_argument('--producer-commit',required=True);p.add_argument('--run',required=True);p.add_argument('--ordinal',choices=['one','two'],required=True);a=p.parse_args();assert re.fullmatch('[a-f0-9]{40}',a.producer_commit);run=pathlib.Path(a.run)
assert run.is_absolute() and '..' not in run.parts and run.resolve().is_relative_to(ROOT/'.cache')
for parent in [run,*run.parents]:assert not parent.is_symlink()
assert run.is_dir()
for path in [pathlib.Path(__file__),ROOT/'scripts/evidence/immutable.py']:
 assert path.is_file() and not path.is_symlink()
 for parent in path.parents:assert not parent.is_symlink()
 relative=str(path.relative_to(ROOT));tree=subprocess.check_output(['git','ls-tree',a.producer_commit,'--',relative],cwd=ROOT).split();assert tree[0] in (b'100644',b'100755')
 assert path.read_bytes()==subprocess.check_output(['git','show',a.producer_commit+':'+relative],cwd=ROOT)
sys.path.insert(0,str(ROOT/'scripts/evidence'))
from immutable import deterministic_gzip
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def checked_source(relative):
 rel=pathlib.Path(relative);assert not rel.is_absolute() and '..' not in rel.parts
 path=run/rel;assert path.resolve().is_relative_to(run.resolve()) and path.is_file()
 for parent in [path,*path.parents]:
  assert not parent.is_symlink()
  if parent==run:break
 return path.read_bytes()
def retain(relative,body):
 relative=pathlib.Path(relative);assert not relative.is_absolute() and '..' not in relative.parts
 target=CASE/relative;assert target.resolve().is_relative_to(CASE.resolve())
 for parent in [target,*target.parents]:
  assert not parent.is_symlink()
  if parent==CASE:break
 assert len(body)<=32*1024*1024
 if body[:2]==b'\x1f\x8b':assert len(gzip.decompress(body))<=32*1024*1024
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():assert target.is_file() and target.read_bytes()==body,('existing retained bytes differ',str(target))
 else:
  with target.open('xb') as stream:stream.write(body)
 pin={'path':str(target.relative_to(ROOT)),'bytes':len(body),'sha256':sha(body),'hash_kind':'file-bytes'}
 assert len(body)<=32*1024*1024
 if body[:2]==b'\x1f\x8b':
  raw=gzip.decompress(body);assert len(raw)<=32*1024*1024;pin.update(uncompressed_bytes=len(raw),uncompressed_sha256=sha(raw))
 return pin
report=json.loads(checked_source('receipt.json'));assert report['producer_commit']==a.producer_commit
index=json.loads(checked_source('source-union-object-index.json'))
pins=report['outputs']+[report['source_input_receipt']]+index['shards']
for binding in index['objects'].values():
 if binding['codec']=='canonical-json-exact-byte-fragments':pins+=binding['parts']
unique={}
for pin in pins:
 if pin['path']in unique:assert unique[pin['path']]==pin
 unique[pin['path']]=pin
prepared=[]
for pin in unique.values():
 rel=pathlib.Path(pin['path']);assert not rel.is_absolute()and '..'not in rel.parts
 path=run/rel;body=checked_source(rel);assert len(body)==pin['bytes']and sha(body)==pin['sha256']
 if 'decoded_sha256'in pin:
  raw=gzip.decompress(body);assert len(raw)==pin['decoded_bytes']and sha(raw)==pin['decoded_sha256']
 assert len(body)<=32*1024*1024 and (body[:2]!=b'\x1f\x8b' or len(gzip.decompress(body))<=32*1024*1024)
 prepared.append((pin,rel,path,body))
aliases=[]
for pin,rel,path,body in prepared:
 retained=retain(pathlib.Path('scientific')/rel,body)
 aliases.append({'original_relative_descriptor':pin,'actual_original_path':str(path),'retained_file':retained,'relation':'Whole emitted encoded bytes identical; no pointset or row reserialization.'})
for name in ['receipt.json','source-union-object-index.json']:
 raw=checked_source(name);retained=retain('verification/run-'+a.ordinal+'-'+name+'.gz',deterministic_gzip(raw))
 aliases.append({'actual_original_path':str(run/name),'original_raw_bytes':len(raw),'original_raw_sha256':sha(raw),'retained_file':retained,'relation':'Ordinary gzip of the exact whole emitted raw bytes.'})
retain('verification/run-'+a.ordinal+'-ordinary-aliases.json',canon({'ordinal':a.ordinal,'immutable_producer_commit':report['producer_commit'],'original_output_root':str(run),'aliases':aliases,'limits':['Transport only, not an additional scientific execution. Original relative paths resolve through this explicit complete alias map.']}))
print(json.dumps({'outcome':'passed','ordinal':a.ordinal,'complete_components':report['complete_components'],'whole_aliases':len(aliases)}))
