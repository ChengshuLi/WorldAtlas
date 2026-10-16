from pathlib import Path
import subprocess,os,json,hashlib,time,resource
w=Path.cwd();b=w/'.takeover/private-recovery.git';d=w/'.takeover/remaining1295/inland-water23';env=os.environ|{'GIT_DIR':str(b),'GIT_INDEX_FILE':str(b/'water23-diagnostic.index'),'GIT_NO_LAZY_FETCH':'1','GIT_ALTERNATE_OBJECT_DIRECTORIES':str(b/'objects')}
for k in ['NODE_OPTIONS','NODE_PATH']:env.pop(k,None)
for k,c in [('GIT_AUTHOR_NAME','user.name'),('GIT_AUTHOR_EMAIL','user.email')]:env[k]=subprocess.check_output(['git','config',c]).decode().strip()
env['GIT_COMMITTER_NAME']=env['GIT_AUTHOR_NAME'];env['GIT_COMMITTER_EMAIL']=env['GIT_AUTHOR_EMAIL']
def git(*a,raw=None):return subprocess.check_output(['git','-c','protocol.allow=never',*a],env=env,input=raw)
def stage(p,raw):oid=git('hash-object','-w','--stdin',raw=raw).decode().strip();git('update-index','--add','--cacheinfo','100644',oid,p)
execution=json.load(open(w/'.takeover/full-foreign-variants834/adopted13-actual-execution-tree.json'))['actual_execution_tree'];git('read-tree',execution);groups=json.load(open(w/'.takeover/remaining1295/neither78-native-inputs.json'))['groups'];holds=json.load(open(w/'.takeover/original-package-completion-audit/repair-exception-review/repair907-evidence-backed-exceptions.json'))['records'];keys=[r['original_key']for r in holds if r['status']=='evidenced-original-whole-physical-coverage-exception'];assert len(keys)==23
prefix='coordination/engineering/myanmar-adm3-current-cells-20261014/inland-water23-existing-support-001/';files=[]
for g in groups[:2]:
 e=json.loads(git('show',g['source_evidence']['commit']+':'+g['source_evidence']['path']));owners={t['pixelIndex']for t in e['targets']};wanted=[k for k in keys if k['owner']in owners];assert wanted
 for t in e['targets']:assert t['coverage_classes']==['mapped_land_support'];t['coverage_classes']=['mapped_land_support','mapped_inland_water_support']
 rows=[]
 for k in sorted(wanted,key=lambda k:(k['y'],k['x'])):
  if not rows or rows[-1]['y']!=k['y']:rows.append({'y':k['y'],'runs':[]})
  rows[-1]['runs'].append([k['x'],k['x']+1,k['owner']])
 path=prefix+f'group{g["group"]}/';stage(path+'source-evidence.json',(json.dumps(e,indent=2)+'\n').encode());stage(path+'candidate-native-patch.json',(json.dumps({'rows':rows},indent=2)+'\n').encode());files.append((g['group'],path,len(wanted)))
tree=git('write-tree').decode().strip();inputs=git('commit-tree',tree,'-p',execution,raw=b'Observe exact23 inland-water keys using both already-retained physical support classes\n').decode().strip();git('update-ref','refs/heads/engineering/myanmar-water23-existing-support-inputs-20261016',inputs)
for n,path,count in files:
 config={'version':1,'source_evidence':{'commit':inputs,'path':path+'source-evidence.json'},'native_patch':{'commit':inputs,'path':path+'candidate-native-patch.json'}};cf=d/f'group{n}-config.json';cf.write_text(json.dumps(config,indent=2)+'\n');command=['node','scripts/prepare-delivery-handoff.mjs','native-diagnostic',str(cf.relative_to(w)),f'.cache/delivery-handoff/water23-group{n}-existing-support-diagnostic-001'];start=time.monotonic();p=subprocess.run(command,env=env,capture_output=True,timeout=120);(d/f'group{n}-stdout.json').write_bytes(p.stdout);(d/f'group{n}-stderr.log').write_bytes(p.stderr);receipt={'command':command,'actual_execution_tree':execution,'unchanged_code':'168ac2ab36663e31ca16f767340c0ab46bea4185','input_commit':inputs,'keys':count,'elapsed_seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'exit_code':p.returncode,'source_or_physical_producer_replays':0};(d/f'group{n}-execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True);print(p.stdout.decode()[:3000],flush=True);print(p.stderr.decode()[:3000],flush=True)
