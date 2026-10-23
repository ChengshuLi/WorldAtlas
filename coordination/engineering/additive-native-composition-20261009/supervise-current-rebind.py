"""Fresh platform-bound separately invoked cold jobs; literal accepted owned cleanup."""
import pathlib,sys,json,os,time,re,subprocess,importlib.util,signal
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rebind_execution_contract',HERE/'execution-contract.py');contract=importlib.util.module_from_spec(spec);exec(compile((HERE/'execution-contract.py').read_bytes(),str(HERE/'execution-contract.py'),'exec'),contract.__dict__)

def own_launched_process(process,termination,owned_group):
 try:
  identity=termination.snapshot().get(process.pid)
  assert identity and identity['pgid']==process.pid
  return identity,owned_group.OwnedGroup(process,identity)
 except BaseException:
  # This exact Popen created the fresh session. No foreign PID lookup grants
  # authority; reap the owned launch even when its first snapshot is unavailable.
  for sig in (signal.SIGTERM,signal.SIGKILL):
   try:os.killpg(process.pid,sig)
   except ProcessLookupError:pass
   if sig==signal.SIGTERM:time.sleep(.05)
  process.wait(timeout=5)
  raise

def platform_contract(pre):
 # The literal issuer roster is already part of the unchanged 28-file closure.
 # Comparing it prevents a caller-supplied issued file from selecting a different
 # process inspector, Python body set or executable.
 name=HERE/'issue-current-rebind-execution.py'
 spec=importlib.util.spec_from_file_location('rebind_issuer_runtime',name)
 issuer=importlib.util.module_from_spec(spec)
 exec(compile(name.read_bytes(),str(name),'exec'),issuer.__dict__)
 runtime=issuer.platform_runtime()
 assert [p for p in pre['runtime'] if p['role']!='installed-dependency']==runtime,'Foreign platform runtime roster'
 return '/usr/bin:/bin' if sys.platform=='linux' else '/bin:/usr/bin'

def current_rebind_product_hashes(output):
 paths={name:output/(name+'.json') for name in ['request','facts','result','publication']}
 for q in paths.values():
  assert q.is_file() and not q.is_symlink() and q.stat().st_size>0
  assert all(not p.is_symlink() for p in q.parents),'Ordinary output ancestors required'
 return {name:contract.digest(q.read_bytes()) for name,q in paths.items()}

def supervise(issued_path,issued_sha,operation):
 assert issued_path.is_absolute() and '..' not in issued_path.parts
 for a in [issued_path,*issued_path.parents]:assert not a.is_symlink()
 raw=issued_path.read_bytes();assert contract.digest(raw)==issued_sha;issued=json.loads(raw)
 assert issued['version']==1 and issued['kind']=='issued-current-rebind-execution-pre-use-v1'
 assert pathlib.Path(sys.executable).resolve()==pathlib.Path(next(p['path'] for p in issued['pre_use']['runtime'] if p['role']=='supervisor-python')).resolve(),'Actual Python executable differs from bound runtime'
 root=pathlib.Path(issued['root']);head=issued['execution_commit'];pre=issued['pre_use'];cmd=issued['command']
 private_path=platform_contract(pre)
 assert operation.is_absolute() and operation.is_relative_to(root/'.cache') and '..' not in operation.parts and not os.path.lexists(operation)
 for a in operation.parents:assert a.is_dir() and not a.is_symlink()
 assert isinstance(cmd,list) and len(cmd)==4
 assert cmd[0]==next(p['path'] for p in pre['runtime'] if p['role']=='node') and cmd[1]==pre['entry']['path'] and cmd[2]==pre['plan']['path']
 output=pathlib.Path(cmd[3]);assert output.is_relative_to(root/'.cache') and '..' not in output.parts and not os.path.lexists(output)
 for a in output.parents:assert a.is_dir() and not a.is_symlink()
 contract.authenticate_file(pre['plan'])
 plan=json.loads(pathlib.Path(pre['plan']['path']).read_bytes());assert plan['execution_commit']==head
 before=contract.capture(root,head,pre)
 # Recheck actual disk availability before any operation/output generation.
 guard_env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONUSERBASE','__PYVENV_LAUNCHER__')}
 guard_env.update(PATH=private_path,LC_ALL='C',LANG='C')
 subprocess.check_output([cmd[0],str(root/'scripts/local-workspace.mjs'),'check'],cwd=root,env=guard_env)
 # Preserve the accepted owned-process cleanup mechanics. Execution uses the
 # normal runtime defaults and its complete logs remain available after failure.
 loaders=[]
 for name in ['owned-child-termination-original.py','owned-group-original.py']:
  s=importlib.util.spec_from_file_location(name.replace('.','_'),HERE/name);m=importlib.util.module_from_spec(s);exec(compile((HERE/name).read_bytes(),str(HERE/name),'exec'),m.__dict__);loaders.append(m)
 termination,owned_group=loaders
 operation.mkdir(mode=0o700);stdout=operation/'stdout.json';stderr=operation/'stderr.log'
 env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONUSERBASE','__PYVENV_LAUNCHER__')}
 env.update(PATH=private_path,LC_ALL='C',LANG='C');os.environ.update(PATH=private_path,LC_ALL='C',LANG='C')
 env.update(WORLDATLAS_REBIND_EXECUTION_COMMIT=head,WORLDATLAS_REBIND_EXECUTION_PRE_USE=contract.canonical({'command':cmd,'pre_use':pre}).decode())
 start=time.monotonic();reason=None;events=[]
 with stdout.open('xb') as out,stderr.open('xb') as err:
  p=subprocess.Popen(cmd,cwd=root,env=env,stdout=out,stderr=err,start_new_session=True)
  identity,authority=own_launched_process(p,termination,owned_group)
  try:
   (operation/'launch.json').write_bytes(contract.canonical({'execution_commit':head,'command':cmd,'pid':p.pid,'identity':identity}))
   exit_code=p.wait()
  except BaseException:
   # The plain Node root is directly owned by this Popen. Terminate/reap that
   # exact root as well as the accepted isolated-group descendant cleanup.
   if p.poll() is None:
    p.terminate()
    try:p.wait(timeout=2)
    except subprocess.TimeoutExpired:p.kill();p.wait()
   authority.cleanup();p.wait()
   raise
 survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
 if survivors:events+=authority.cleanup();reason='owned descendants after natural exit';survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
 after=contract.capture(root,head,pre)
 elapsed=time.monotonic()-start
 code_source={'version':1,'kind':'whole-current-rebind-execution-custody-v1','execution_commit':head,'command':cmd,'pre_use':before,'post_use':after};source_raw=contract.canonical(code_source);(operation/'code-source.json').write_bytes(source_raw)
 request_sha=None;publication_sha=None
 if exit_code==0:
  try:
   products=current_rebind_product_hashes(output)
   request=json.loads((output/'request.json').read_bytes());publication=json.loads((output/'publication.json').read_bytes());child=json.loads(stdout.read_bytes())
   assert request['execution_commit']==head and request['execution']=={'command':cmd,'pre_use':before}
   assert publication['request_sha256']==products['request'] and child['request_sha256']==products['request'] and child['publication_sha256']==products['publication'] and child['result_sha256']==products['result']
   request_sha=products['request'];publication_sha=products['publication']
  except (AssertionError,FileNotFoundError,KeyError,ValueError):reason=reason or 'missing/foreign actual child products or stdout bindings'
 terminal={'version':1,'kind':'current-rebind-external-terminal-v1','execution_commit':head,'command':cmd,'request_sha256':request_sha,'publication_sha256':publication_sha,'code_source_sha256':contract.digest(source_raw),'exit_code':exit_code,'signal':None if exit_code>=0 else -exit_code,'guard_reason':reason,'elapsed_seconds':elapsed,'owned_processes_remaining':survivors,'termination_events':events}
 (operation/'terminal.json').write_bytes(contract.canonical(terminal))
 assert exit_code==0 and reason is None and not survivors,'Unqualified actual command; output history retained'
 return terminal
if __name__=='__main__':
 assert sys.flags.isolated and sys.dont_write_bytecode,'Use exact isolated Python -I -B entry'
 assert len(sys.argv)==4
 print(json.dumps(supervise(pathlib.Path(sys.argv[1]),sys.argv[2],pathlib.Path(sys.argv[3]))))
