import pathlib,subprocess,os,json,hashlib,copy,tempfile,time
D=pathlib.Path(__file__).resolve().parent;W=pathlib.Path((D/'workspace.txt').read_text());P='coordination/engineering/estonia-native-repair-20261017';C=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip();PYTHON=str(D.parent/'reusable1922-preserved/cache-complete/source-python/bin/python');env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'};encode=lambda j:(json.dumps(j,ensure_ascii=False,separators=(',',':'))+'\n').encode();sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args,input=None,e=env):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],input=input,env=e)
names=['native-config-001/source-config.json','native-config-001/negative-equivalence.json','native-config-001/preparation.json','native-inputs-001/source-evidence.json'];original={n:json.loads(git('show',C+':'+P+'/'+n)) for n in names};out=[]
for case in ['deleted-retained-negative','changed-base-geometry','empty-equivalence-proof','changed-owner']:
 data=copy.deepcopy(original);config=data[names[0]];proof=data[names[1]];source=data[names[3]];ix=next(i for i,t in enumerate(source['targets']) if t['territorial_exclusions']);t=source['targets'][ix];q=config['source_evidence']['targets'][ix]
 if case=='deleted-retained-negative':t['territorial_exclusions'].pop();q['territorial_exclusions'].pop()
 elif case=='changed-base-geometry':
  for z in [t,q]:
   a=z['base_geometry']['coordinates']
   while isinstance(a[0],list):a=a[0]
   a[0]+=0.000001
 elif case=='empty-equivalence-proof':proof['targets']=[]
 else:t['pixelIndex']+=1;q['pixelIndex']+=1;proof['targets'][ix]['pixelIndex']+=1
 for n in ['source-config.json','negative-equivalence.json']:
  b=encode(data['native-config-001/'+n]);data[names[2]]['outputs'][n]={'bytes':len(b),'sha256':sha(b)}
 with tempfile.TemporaryDirectory(prefix='est-negative-probe-',dir=D) as tmp:
  index=pathlib.Path(tmp)/'index';e={**env,'GIT_INDEX_FILE':str(index)};git('read-tree',C,e=e)
  for n,j in data.items():
   oid=git('hash-object','-w','--stdin',input=encode(j)).decode().strip();git('update-index','--cacheinfo','100644',oid,P+'/'+n,e=e)
  tree=git('write-tree',e=e).decode().strip();commit=git('commit-tree',tree,'-p',C,input=('Estonia independent negative refusal probe '+case+'\n').encode()).decode().strip();dest=pathlib.Path(tmp)/'output';start=time.monotonic();p=subprocess.run([PYTHON,str(W/P/'method/verify-native-preparation.py'),str(W),commit,str(dest)],env=env,capture_output=True,text=True);assert p.returncode!=0 and not dest.exists(),(case,p.returncode,p.stdout,p.stderr);out.append({'case':case,'base_commit':C,'mutant_commit':commit,'coherent_config_and_preparation_hashes_refreshed':True,'exit_code':p.returncode,'no_output_created':True,'elapsed_seconds':time.monotonic()-start,'stderr':p.stderr})
print(json.dumps({'version':1,'method_sha256':sha((W/P/'method/verify-native-preparation.py').read_bytes()),'experiments':out},indent=2))
