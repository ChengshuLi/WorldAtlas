import subprocess,json,hashlib,pathlib,sys,copy,os
R='/workspace/scratch/127991fc8b8e/worldatlas-primary';P='coordination/engineering/papua-new-guinea-native-repair-20261017/';H=sys.argv[1];O=pathlib.Path(__file__).parent/'png-review-output';O.mkdir(exist_ok=True)
def git(*a,input=None):return subprocess.check_output(['git','-C',R,*a],input=input,env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'})
def read(p):return git('show',H+':'+P+p)
def encode(x):return (json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def tree_update(tree,parts,oid):
 entries=git('ls-tree','-z',tree).split(b'\0'); out=[]
 for entry in filter(None,entries):
  meta,name=entry.split(b'\t'); mode,typ,old=meta.decode().split()
  if name.decode()==parts[0]:
   new=tree_update(old,parts[1:],oid) if len(parts)>1 else oid
   entry=f'{mode} {typ} {new}\t'.encode()+name
  out.append(entry)
 return git('mktree','-z',input=b'\0'.join(out)+b'\0').decode().strip()
def altered(changes):
 tree=git('rev-parse',H+'^{tree}').decode().strip()
 for p,b in changes.items():tree=tree_update(tree,(P+p).split('/'),git('hash-object','-w','--stdin',input=b).decode().strip())
 return git('commit-tree',tree,'-p',H,input=b'Independent PNG adverse input; not for publication\n').decode().strip()
code=read('method/prepare-supported.py').decode();results=[]
def run(name,head=H,dest=None):
 dest=dest or O/name
 r=subprocess.run([sys.executable,'-c',code,R,head,str(dest)],capture_output=True,text=True)
 results.append({'probe':name,'head':head,'returncode':r.returncode,'output_exists':dest.exists(),'stderr_tail':r.stderr[-600:]})
 assert r.returncode!=0 and not (dest/'preparation.json').exists(),results[-1]
 return r
sentinel=O/'existing';sentinel.mkdir(exist_ok=True);(sentinel/'sentinel').write_text('keep')
run('existing-directory',dest=sentinel);assert (sentinel/'sentinel').read_text()=='keep'
link=O/'dangling';link.symlink_to(O/'absent');run('dangling-symlink',dest=link);assert link.is_symlink() and not (O/'absent').exists()
source=json.loads(read('compaction-001/source-evidence.json'));proof=json.loads(read('compaction-001/whole-negative-equivalence.json'));prep=json.loads(read('compaction-001/preparation.json'))
for name in ['changed-positive','missing-negative','empty-proof','changed-foreign-owner']:
 s=copy.deepcopy(source);p=copy.deepcopy(proof);pr=copy.deepcopy(prep)
 if name=='changed-positive':s['targets'][0]['base_geometry']={'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,0]]]}
 elif name=='missing-negative':next(t for t in s['targets'] if t['territorial_exclusions'])['territorial_exclusions']=[]
 elif name=='changed-foreign-owner':s['targets'][0]['pixelIndex']+=1
 else:
  p['targets']=[]
  for k in ['original_operands','retained_operands','omitted_whole_disjoint_operands']:p[k]=0
 changes={'compaction-001/source-evidence.json':encode(s),'compaction-001/whole-negative-equivalence.json':encode(p)}
 for path,b in changes.items():pr['outputs'][path.split('/')[-1]]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 changes['compaction-001/preparation.json']=encode(pr)
 run(name,altered(changes))
(O/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
