"""Small in-memory controls exercise the actual extracted immutable reader functions.
Usage: python check-reader-custody.py REPO EXACT_COMMIT FRESH_JSON
No source predicates, physical production or native authority are rerun.
"""
import ast,gzip,hashlib,json,pathlib,subprocess,sys,time,types,os
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/argentina-repair-delivery-20261017/probes'
assert len(sys.argv)==4 and len(C)==40 and O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in(O,*O.parents))
def raw(n):return subprocess.check_output(['git','-C',str(W),'show',C+':'+P+'/'+n])
assert raw('check-reader-custody.py')==pathlib.Path(__file__).read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
methods=['prepare-source-stage.py','extract-prior-family.py','prepare-source-scope.py','corroborate-neighbor-contacts.py','prepare-native-config.py','prepare-qualified-scope.py','verify-qualified-evidence.py','reconcile-authority.py'];results=[]
for name in methods:
 body=raw(name);tree=ast.parse(body);fname='pin'if name=='reconcile-authority.py'else'read';fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==fname)
 assert not any(x in body.decode()for x in ['PHASE_BYTES','FILE_BYTES','OUTPUT_BYTES','1024*1024'])
 for case in ['valid-encoded','short-encoded','long-encoded','same-length-corrupt','wrong-mode','wrong-oid','valid-gzip','truncated-gzip','corrupt-gzip-crc']:
  payload=b'whole small exact immutable original body\n';encoded=gzip.compress(payload,mtime=0)if'gzip'in case else payload
  if case=='truncated-gzip':encoded=encoded[:-3]
  if case=='corrupt-gzip-crc':encoded=encoded[:-8]+bytes([encoded[-8]^1])+encoded[-7:]
  size=len(encoded);oid=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+encoded).hexdigest();given=encoded
  if case=='short-encoded':given=given[:-1]
  if case=='long-encoded':given+=b'x'
  if case=='same-length-corrupt':given=b'X'+given[1:]
  if case=='wrong-oid':oid='0'*40
  mode='100755'if case=='wrong-mode'else'100644';path='fixture.json.gz'if'gzip'in case else'fixture.json'
  def fake(*args,**kwargs):
   aa=args[0]if len(args)==1 and isinstance(args[0],list)else args
   if'ls-tree'in aa:return f'{mode} blob {oid}\t{path}\0'.encode()
   if'-s'in aa:return(str(size)+'\n').encode()
   assert'cat-file'in aa and'blob'in aa;return given
  ns=dict(C=C,H=C,W=W,R=W,total=0,inputs={},start=time.monotonic(),started=time.monotonic(),DEADLINE_SECONDS=300,hashlib=hashlib,gzip=gzip,time=time,os=os,env={},sha=sha,subprocess=types.SimpleNamespace(check_output=fake),git=fake)
  exec(compile(ast.Module(body=[fn],type_ignores=[]),name,'exec'),ns)
  try:
   if fname=='pin':pin,b=ns[fname](path,C);actual=gzip.decompress(b)if'gzip'in case else b
   elif fn.args.args[0].arg=='h':actual=ns[fname](C,path,'gzip'in case)
   else:actual=ns[fname](path,C)
   assert actual==payload
   if fname!='pin':
    pin=ns['inputs'][C,path];assert pin['bytes']==size and pin['sha256']==sha(encoded)
    if'gzip'in case:assert pin['decoded_bytes']==len(payload)and pin['decoded_sha256']==sha(payload)
   accepted=True;error=None
  except (AssertionError,EOFError,OSError,ValueError)as e:accepted=False;error=type(e).__name__
  assert accepted==(case in ['valid-encoded','valid-gzip']),(name,case,error)
  results.append({'method':name,'method_sha256':sha(body),'case':case,'accepted':accepted,'error':error})
result={'kind':'actual-reader-function-small-custody-controls','method_commit':C,'cases':len(results),'results':results,'limits':['The unchanged read/pin function AST is executed against deterministic mocked Git responses. No scientific source predicate is rerun.','These small fixtures prove integrity refusal, complete gzip/CRC and measured decoded pins. They do not measure large-input performance or available memory.','Declared decoded product sizes/hashes remain exact assertions in each scientific caller. No arbitrary byte or cumulative-byte ceiling remains in these active readers/writers.']}
with O.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':len(results)}))
