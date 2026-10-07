"""Retain emitted ordinary bytes with explicit aliases; no scientific operations."""
import pathlib,json,gzip,hashlib,argparse,subprocess
CASE=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('run');parser.add_argument('ordinal',choices=['one','two']);args=parser.parse_args();RUN=pathlib.Path(args.run)
def canon(v):return(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def descriptor(p,b):
 d={'path':str(p.relative_to(CASE.parents[3])),'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'}
 if b[:2]==b'\x1f\x8b':r=gzip.decompress(b);d.update(uncompressed_bytes=len(r),uncompressed_sha256=sha(r));assert len(r)<=32*1024*1024
 assert len(b)<=32*1024*1024;return d
def write(p,b):
 p=CASE/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==b,'differing actual run payload: '+str(p)
 else:p.write_bytes(b)
 return descriptor(p,b)
report=json.loads((RUN/'report.json').read_bytes());resolved=subprocess.check_output(['git','rev-parse',report['code_commit']+'^{commit}'],cwd=CASE.parents[3]).decode().strip();assert resolved=='c0bb4c62a725f9d170a9c26db4baa1c477cbc905';idx=json.loads((RUN/'source-union-object-index.json').read_bytes());aliases=[]
for original in report['outputs']+idx['shards']:
 p=pathlib.Path(original['path']);b=p.read_bytes();assert len(b)==original['bytes']and sha(b)==original['sha256'];raw=gzip.decompress(b);assert len(raw)==original['decoded_bytes']and sha(raw)==original['decoded_sha256']
 rel=pathlib.Path('scientific')/p.relative_to(RUN);retained=write(rel,b);aliases.append({'actual_original_file':original,'retained_file':retained,'relation':'whole encoded and decoded bytes identical; no data or record reserialization'})
for name,kind in [('report.json','actual-report'),('source-union-object-index.json','actual-object-index'),('operation-consistency.json','actual-operation-consistency')]:
 raw=(RUN/name).read_bytes();retained=write('verification/run-'+args.ordinal+'-'+kind+'.json.gz',gzip.compress(raw,mtime=0));aliases.append({'actual_original_file':{'path':str(RUN/name),'bytes':len(raw),'sha256':sha(raw)},'retained_file':retained,'relation':'deterministic gzip of whole exact emitted raw file; decoded bytes identical'})
write('verification/run-'+args.ordinal+'-ordinary-aliases.json',canon({'ordinal':args.ordinal,'code_argument':report['code_commit'],'resolved_immutable_code_commit':resolved,'aliases':aliases,'limits':['This is ordinary byte retention/readback, not an additional scientific execution.','Cache path strings in original emitted envelopes remain unchanged; aliases explicitly bind their delivered ordinary files.']}))
print(json.dumps({'status':'PASS','ordinal':args.ordinal,'full_aliases':len(aliases),'components':report['complete_components']}))
