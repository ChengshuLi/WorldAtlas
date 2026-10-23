"""Bind one immutable AAFC adoption document into a retained source config.
The raw launch copy is optional disposable staging. Its compressed copy restores
exactly and is the durable configuration; no scientific operand is changed.
"""
import argparse,pathlib,json,gzip,hashlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--batch',required=True);p.add_argument('--output',required=True);p.add_argument('--retained-config',required=True);a=p.parse_args();W=pathlib.Path(a.repo);H='84e32803554';P='coordination/engineering/canada-repair-delivery-20261017/aafc-native-operands-001/'+a.batch
assert a.batch in ['batch-%03d'%i for i in range(1,6)]
def raw(p):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',H+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):
 b=raw(p);return {'path':p,'commit':subprocess.check_output(['git','-C',str(W),'rev-parse',H]).decode().strip(),'mode':'100644','git_blob_oid':subprocess.check_output(['git','-C',str(W),'rev-parse',H+':'+p]).decode().strip(),'bytes':len(b),'sha256':sha(b)}
x=json.loads(raw(P+'/source-evidence-template.json'));x['source_evidence']['adopted_provider_families']=pin(P+'/adopted-provider-families.json');b=(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode();z=gzip.compress(b,mtime=0);assert gzip.decompress(z)==b
out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);ret=pathlib.Path(a.retained_config);ret.parent.mkdir(parents=True,exist_ok=True)
with out.open('xb') as f:f.write(b)
with ret.open('xb') as f:f.write(z)
with ret.with_suffix('.custody.json').open('x') as f:json.dump({'kind':'lossless-source-configuration-encoding','retained_path':str(ret.relative_to(W)),'bytes':len(z),'sha256':sha(z),'decoded_bytes':len(b),'decoded_sha256':sha(b)},f,indent=2);f.write('\n')
print(json.dumps({'batch':a.batch,'raw_bytes':len(b),'retained_bytes':len(z),'raw_sha256':sha(b)}))
