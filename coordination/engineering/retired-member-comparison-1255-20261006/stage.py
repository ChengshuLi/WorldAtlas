"""Exact ordinary custody staging only; no numerical geometry operations."""
import argparse,gzip,hashlib,json,pathlib,subprocess,sys
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2]
sys.path.insert(0,str(R/'scripts'))
from evidence.immutable import canonical_json as canon,deterministic_gzip,safe_path
SHA=lambda b:hashlib.sha256(b).hexdigest()
def write(path,body):
 if len(body)>32*1024*1024:raise ValueError('Oversized ordinary body')
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb')as f:f.write(body)
def descriptor(path,body,decoded=None):
 d={'path':str(path.relative_to(P)),'bytes':len(body),'sha256':SHA(body)}
 if decoded is not None:d.update(decoded_bytes=len(decoded),decoded_sha256=SHA(decoded))
 return d
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--preparation',required=True);a.add_argument('--plan',required=True);args=a.parse_args();prep=pathlib.Path(args.preparation)
 raw=(prep/'scope-and-whole-byte-preflight.json').read_bytes();scope=json.loads(raw)
 assert SHA(raw)=='edd2041bf46229f2782736066d247406b2d21e643afa27bf33f8bbe81467378a'
 assert scope['families']==2476 and scope['components']==20032 and len(scope['member_ids'])==2438 and len(scope['contact_ids'])==869
 write(P/'scope.json.gz',deterministic_gzip(raw))
 plan=pathlib.Path(args.plan).read_bytes();assert SHA(plan)=='be3c513eeb168901be0027620f5bc1869b2a9b5198cc420a72f42142ff964c00';assert len(gzip.decompress(plan))<32*1024*1024;write(P/'remaining-plan.json.gz',plan)
 aliases=[];archive=None
 for n,pin in enumerate(scope['ordinary_original_input_pins']):
  path=safe_path(pin['path']);b=subprocess.check_output(['git','show',pin['commit']+':'+path],cwd=R)
  assert len(b)==pin['bytes'] and SHA(b)==pin['sha256']
  mode=subprocess.check_output(['git','ls-tree',pin['commit'],'--',path],cwd=R).decode().split()[0];assert mode==pin['mode']in('100644','100755')
  if path=='data/geographic-migration-archive.json.gz':archive=b;archivepin=pin;continue
  raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b;assert len(raw)==pin['decoded_bytes']and SHA(raw)==pin['decoded_sha256']and len(raw)<=32*1024*1024
  target=P/'inputs'/('i%03d'%n+('.gz'if b[:2]==b'\x1f\x8b'else'.bin'));write(target,b);aliases.append({'original':pin,'ordinary':descriptor(target,b,raw),'codec':'original-ordinary-whole-bytes'})
 assert archive is not None;decoded=gzip.decompress(archive);assert len(decoded)==56672580 and SHA(decoded)=='c072bbe6e7f96789e3a6165e9075eb3271050e1e1614f2923f03169480537184'
 groups={}
 for name,body,compress in [('encoded',archive,False),('decoded',decoded,True)]:
  parts=[]
  for offset in range(0,len(body),8*1024*1024):
   raw=body[offset:offset+8*1024*1024];b=deterministic_gzip(raw)if compress else raw;target=P/'inputs'/('archive-'+name+'-%03d'%len(parts)+('.bin.gz'if compress else'.bin'));write(target,b)
   parts.append({'offset':offset,'ordinary':descriptor(target,b,raw if compress else None),'raw_bytes':len(raw),'raw_sha256':SHA(raw)})
  groups[name]={'whole_bytes':len(body),'whole_sha256':SHA(body),'parts':parts}
 assert len(groups['encoded']['parts'])==2 and len(groups['decoded']['parts'])==7
 extras=[]
 base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()
 for n,path in enumerate(['data/administrative-sources.json','coordination/engineering/original-geography-source-corpus-20261006/CITATION-AND-USE-geoBoundaries-original.txt','coordination/engineering/original-geography-source-corpus-20261006/individual-source-attribution.json','docs/DATA_SOURCES.md','docs/GRANULARITY.md']):
  b=subprocess.check_output(['git','show',base+':'+path],cwd=R);target=P/'inputs'/('attribution-%02d.bin'%n);write(target,b);extras.append({'original_commit':base,'original_path':path,'ordinary':descriptor(target,b,b)})
 index={'version':1,'scope':descriptor(P/'scope.json.gz',(P/'scope.json.gz').read_bytes(),(prep/'scope-and-whole-byte-preflight.json').read_bytes()),'complete_remaining_plan':descriptor(P/'remaining-plan.json.gz',plan,gzip.decompress(plan)),'aliases':aliases,'archive_original':archivepin,'archive':groups,'attribution_context':extras,'whole_archive_relation':'Concatenated encoded raw fragments decompress exactly to concatenated decoded raw fragments; both complete original SHA bindings mandatory. No standalone oversized gzip descriptor.'}
 write(P/'input-index.json',canon(index));print(json.dumps({'ordinary_aliases':len(aliases),'archive_parts':9,'attribution_inputs':len(extras),'bytes':sum(x.stat().st_size for x in P.rglob('*')if x.is_file())}))
