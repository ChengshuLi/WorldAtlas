"""Exercise exact original accounting with coherently committed bad constructor rows.
Usage: python accounting-refusals.py READ_ONLY_REPO EXISTING_SCRATCH_DIRECTORY
"""
import sys,pathlib,subprocess,os,json,hashlib,copy,tempfile,time
assert len(sys.argv)==3
W=pathlib.Path(sys.argv[1]).absolute();D=pathlib.Path(sys.argv[2]).absolute();assert W.is_dir() and D.is_dir()
P='coordination/engineering/estonia-native-repair-20261017';C=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
encode=lambda j:(json.dumps(j,ensure_ascii=False,separators=(',',':'))+'\n').encode();sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args,input=None,e=env):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],input=input,env=e)
name=P+'/native-authority-001/constructor-result.json';original=json.loads(git('show',C+':'+name));out=[]
for case in ['missing-constructor-row','duplicate-constructor-row','changed-constructor-owner']:
 data=copy.deepcopy(original)
 if case=='missing-constructor-row':data['ledger_rows'].pop()
 elif case=='duplicate-constructor-row':data['ledger_rows'].append(copy.deepcopy(data['ledger_rows'][0]))
 else:data['ledger_rows'][0]['pixelIndex']+=1
 with tempfile.TemporaryDirectory(prefix='est-accounting-probe-',dir=D) as tmp:
  index=pathlib.Path(tmp)/'index';e={**env,'GIT_INDEX_FILE':str(index)};git('read-tree',C,e=e)
  oid=git('hash-object','-w','--stdin',input=encode(data)).decode().strip();git('update-index','--cacheinfo','100644',oid,name,e=e)
  tree=git('write-tree',e=e).decode().strip();commit=git('commit-tree',tree,'-p',C,input=('Estonia accounting refusal probe '+case+'\n').encode()).decode().strip();dest=pathlib.Path(tmp)/'output';start=time.monotonic()
  p=subprocess.run([sys.executable,str(W/P/'method/check-accounting.py'),str(W),commit,str(dest)],env=env,capture_output=True,text=True)
  assert p.returncode!=0 and not dest.exists(),(case,p.returncode,p.stdout,p.stderr)
  out.append({'case':case,'base_commit':C,'mutant_commit':commit,'changed_constructor_body_retained_as_ordinary_git_blob':True,'exit_code':p.returncode,'no_output_created':True,'elapsed_seconds':time.monotonic()-start,'stderr':p.stderr})
print(json.dumps({'version':1,'method_sha256':sha((W/P/'method/check-accounting.py').read_bytes()),'experiments':out},indent=2))
