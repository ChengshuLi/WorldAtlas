"""Retain whole emitted bytes and explicit paths; never execute scientific geometry."""
import argparse,gzip,hashlib,json,pathlib,sys
CASE=pathlib.Path(__file__).resolve().parent
ROOT=CASE.parents[3]
sys.path.insert(0,str(ROOT/'scripts/evidence'))
from immutable import deterministic_gzip
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--ordinal',choices=['one','two'],required=True);a=p.parse_args();run=pathlib.Path(a.run).resolve()
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def retain(relative,body):
 target=CASE/relative;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():assert target.read_bytes()==body,('existing retained bytes differ',str(target))
 else:target.write_bytes(body)
 pin={'path':str(target.relative_to(ROOT)),'bytes':len(body),'sha256':sha(body),'hash_kind':'file-bytes'}
 assert len(body)<=32*1024*1024
 if body[:2]==b'\x1f\x8b':
  raw=gzip.decompress(body);assert len(raw)<=32*1024*1024;pin.update(uncompressed_bytes=len(raw),uncompressed_sha256=sha(raw))
 return pin
report=json.loads((run/'receipt.json').read_bytes());assert report['producer_commit']=='3b4ca9e9f42d692530a4139efe2bd8f72ce15723'
index=json.loads((run/'source-union-object-index.json').read_bytes())
pins=report['outputs']+[report['source_input_receipt']]+index['shards']
for binding in index['objects'].values():
 if binding['codec']=='canonical-json-exact-byte-fragments':pins+=binding['parts']
unique={}
for pin in pins:
 if pin['path']in unique:assert unique[pin['path']]==pin
 unique[pin['path']]=pin
aliases=[]
for pin in unique.values():
 rel=pathlib.Path(pin['path']);assert not rel.is_absolute()and '..'not in rel.parts
 path=run/rel;assert path.is_file()and not path.is_symlink();body=path.read_bytes();assert len(body)==pin['bytes']and sha(body)==pin['sha256']
 if 'decoded_sha256'in pin:
  raw=gzip.decompress(body);assert len(raw)==pin['decoded_bytes']and sha(raw)==pin['decoded_sha256']
 retained=retain(pathlib.Path('scientific')/rel,body)
 aliases.append({'original_relative_descriptor':pin,'actual_original_path':str(path),'retained_file':retained,'relation':'Whole emitted encoded bytes identical; no pointset or row reserialization.'})
for name in ['receipt.json','source-union-object-index.json']:
 raw=(run/name).read_bytes();retained=retain('verification/run-'+a.ordinal+'-'+name+'.gz',deterministic_gzip(raw))
 aliases.append({'actual_original_path':str(run/name),'original_raw_bytes':len(raw),'original_raw_sha256':sha(raw),'retained_file':retained,'relation':'Ordinary gzip of the exact whole emitted raw bytes.'})
retain('verification/run-'+a.ordinal+'-ordinary-aliases.json',canon({'ordinal':a.ordinal,'immutable_producer_commit':report['producer_commit'],'original_output_root':str(run),'aliases':aliases,'limits':['Transport only, not an additional scientific execution. Original relative paths resolve through this explicit complete alias map.']}))
print(json.dumps({'outcome':'passed','ordinal':a.ordinal,'complete_components':report['complete_components'],'whole_aliases':len(aliases)}))
