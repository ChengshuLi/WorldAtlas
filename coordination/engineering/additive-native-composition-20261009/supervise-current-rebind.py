"""Two fresh separately invoked Mac cold jobs; literal accepted owned cleanup."""
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

def supervise(issued_path,issued_sha,operation):
 assert issued_path.is_absolute() and '..' not in issued_path.parts
 for a in [issued_path,*issued_path.parents]:assert not a.is_symlink()
 assert issued_path.stat().st_size<=131072
 raw=issued_path.read_bytes();assert contract.digest(raw)==issued_sha;issued=json.loads(raw)
 assert issued['version']==1 and issued['kind']=='issued-current-rebind-execution-pre-use-v1'
 assert pathlib.Path(sys.executable).resolve()==pathlib.Path(next(p['path'] for p in issued['pre_use']['runtime'] if p['role']=='supervisor-python')).resolve(),'Actual Python executable differs from bound runtime'
 root=pathlib.Path(issued['root']);head=issued['execution_commit'];pre=issued['pre_use'];cmd=issued['command']
 assert operation.is_absolute() and operation.is_relative_to(root/'.cache') and '..' not in operation.parts and not os.path.lexists(operation)
 for a in operation.parents:assert a.is_dir() and not a.is_symlink()
 assert len(cmd)==6 and cmd[0]==next(p['path'] for p in pre['runtime'] if p['role']=='time') and cmd[1]=='-l' and cmd[2]==next(p['path'] for p in pre['runtime'] if p['role']=='node') and cmd[3]==pre['entry']['path'] and cmd[4]==pre['plan']['path']
 output=pathlib.Path(cmd[5]);assert output.is_relative_to(root/'.cache') and '..' not in output.parts and not os.path.lexists(output)
 for a in output.parents:assert a.is_dir() and not a.is_symlink()
 before=contract.capture(root,head,pre);plan=json.loads(pathlib.Path(pre['plan']['path']).read_bytes());limits=plan['limits']
 # Fresh original stock report and explicit prospective retained growth; no
 # stale receipt or shell continuation can authorize the actual command.
 guard_env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONUSERBASE','__PYVENV_LAUNCHER__')}
 guard_env['PATH']='/usr/bin:/bin'
 stock_raw=subprocess.check_output([cmd[2],str(root/'scripts/local-workspace.mjs'),'check'],cwd=root,env=guard_env)
 stock=json.loads(stock_raw);assert stock['freeBytes']-contract.OUTPUT>=10737418240 and stock['checkoutBytes']+contract.OUTPUT<=53687091200,'Fresh original stock/growth admission refused'
 vm=subprocess.check_output(['/usr/bin/vm_stat'],text=True,env=guard_env);page=int(re.search(r'page size of (\d+) bytes',vm).group(1));pages=sum(int(re.search(r'^Pages '+name+r':\s*(\d+)',vm,re.M).group(1)) for name in ['free','inactive','speculative']);assert pages*page>=805306368,'Fresh conservative host supply refused; reclaimability uncertain'
 extra=sum(p['bytes'] for p in pre['runtime'] if p['role'] not in ('node','git','installed-dependency'))
 assert issued['operating_phase_bytes']==limits['complete_phase_bytes']+extra+contract.OUTPUT+contract.META<=contract.PHASE
 assert limits['sampled_stop_bytes']<=402653184 and limits['rss_bytes']<=536870912 and limits['wall_seconds']<=1200 and limits['output_bytes']<=4194304
 # Whole helper bytes are already frozen/pre-use verified in the complete code
 # roster. These literal historical mechanisms are not rewritten or relabeled.
 loaders=[]
 for name in ['owned-child-termination-original.py','owned-group-original.py']:
  s=importlib.util.spec_from_file_location(name.replace('.','_'),HERE/name);m=importlib.util.module_from_spec(s);exec(compile((HERE/name).read_bytes(),str(HERE/name),'exec'),m.__dict__);loaders.append(m)
 termination,owned_group=loaders
 operation.mkdir(mode=0o700);(operation/'stock-report.json').write_bytes(stock_raw);(operation/'host-supply.json').write_bytes(contract.canonical({'vm_stat':vm,'supply_upper_bytes':pages*page,'required_bytes':805306368,'uncertainty':'Inactive/speculative reclaimability is an upper estimate, not guaranteed availability.'}));stdout=operation/'stdout.json';stderr=operation/'stderr.log';samples=operation/'samples.jsonl'
 def retained():return sum(p.stat().st_size for base in [operation,output] if base.exists() for p in base.rglob('*') if p.is_file())
 def logs():return all(not p.exists() or p.stat().st_size<= {'stdout.json':8192,'stderr.log':40960,'samples.jsonl':1048576}[p.name] for p in [stdout,stderr,samples])
 def usage(group):
  ps=next(p['path'] for p in pre['runtime'] if p['role']=='process-inspector');rows=[]
  for line in subprocess.check_output([ps,'-axo','pid=,ppid=,pgid=,rss=,command='],text=True).splitlines():
   f=line.split(None,4)
   if len(f)==5 and int(f[2])==group:rows.append({'pid':int(f[0]),'ppid':int(f[1]),'rss_bytes':int(f[3])*1024,'command':f[4]})
  return rows
 env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONUSERBASE','__PYVENV_LAUNCHER__')}
 # Literal helper subprocess uses ps by name; pin exactly the consumed /bin/ps
 # by putting that one authenticated directory first in the private child PATH.
 env['PATH']='/bin:/usr/bin';os.environ['PATH']='/bin:/usr/bin'
 env.update(WORLDATLAS_REBIND_EXECUTION_COMMIT=head,WORLDATLAS_REBIND_EXECUTION_PRE_USE=contract.canonical({'command':cmd,'pre_use':pre}).decode())
 start=time.monotonic();peak=0;reason=None;events=[]
 with stdout.open('xb') as out,stderr.open('xb') as err,samples.open('x') as sample:
  p=subprocess.Popen(cmd,cwd=root,env=env,stdout=out,stderr=err,start_new_session=True)
  identity,authority=own_launched_process(p,termination,owned_group)
  try:
   (operation/'launch.json').write_bytes(contract.canonical({'execution_commit':head,'command':cmd,'pid':p.pid,'identity':identity}))
   while p.poll() is None:
    rows=usage(p.pid);rss=sum(r['rss_bytes'] for r in rows);peak=max(peak,rss)
    sample.write(json.dumps({'elapsed_seconds':time.monotonic()-start,'rss_bytes':rss,'processes':rows})+'\n');sample.flush()
    if not logs():reason='whole raw log/sample bound'
    elif rss>=limits['sampled_stop_bytes']:reason='sampled owned process group bound'
    elif time.monotonic()-start>limits['wall_seconds']:reason='wall deadline'
    elif retained()>contract.OUTPUT:reason='complete retained output/log bound'
    if reason:events=authority.cleanup();break
    time.sleep(.25)
   exit_code=p.wait()
  except BaseException:
   authority.cleanup();p.wait(timeout=5)
   raise
 survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
 if survivors:events+=authority.cleanup();reason=reason or 'owned descendants after natural exit';survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
 assert logs(),'Terminal log bounds';after=contract.capture(root,head,pre)
 text=stderr.read_text();match=re.findall(r'^\s*(\d+)\s+maximum resident set size\s*$',text,re.M);lifetime=int(match[0]) if len(match)==1 else None
 if lifetime is None or lifetime>limits['rss_bytes']:reason=reason or 'raw external lifetime RSS bound'
 elapsed=time.monotonic()-start
 if elapsed>limits['wall_seconds']:reason=reason or 'actual external elapsed wall bound'
 code_source={'version':1,'kind':'whole-current-rebind-execution-custody-v1','execution_commit':head,'command':cmd,'pre_use':before,'post_use':after};source_raw=contract.canonical(code_source);(operation/'code-source.json').write_bytes(source_raw)
 def product(name):q=output/(name+'.json');assert q.is_file() and not q.is_symlink() and q.stat().st_size<=4194304;return contract.digest(q.read_bytes())
 request_sha=None;publication_sha=None
 if exit_code==0:
  try:
   products={name:product(name) for name in ['request','facts','result','publication']}
   assert sum((output/(name+'.json')).stat().st_size for name in products)<=limits['output_bytes']
   request=json.loads((output/'request.json').read_bytes());publication=json.loads((output/'publication.json').read_bytes());child=json.loads(stdout.read_bytes())
   assert request['execution_commit']==head and request['execution']=={'command':cmd,'pre_use':before}
   assert publication['request_sha256']==products['request'] and child['request_sha256']==products['request'] and child['publication_sha256']==products['publication'] and child['result_sha256']==products['result']
   request_sha=products['request'];publication_sha=products['publication']
  except (AssertionError,FileNotFoundError,KeyError,ValueError):reason=reason or 'missing/foreign actual child products or stdout bindings'
 terminal={'version':1,'kind':'current-rebind-external-terminal-v1','execution_commit':head,'command':cmd,'request_sha256':request_sha,'publication_sha256':publication_sha,'code_source_sha256':contract.digest(source_raw),'exit_code':exit_code,'signal':None if exit_code>=0 else -exit_code,'guard_reason':reason,'lifetime_rss_bytes':lifetime,'sampled_group_peak_bytes':peak,'sampled_stop_bytes':limits['sampled_stop_bytes'],'lifetime_ceiling_bytes':limits['rss_bytes'],'elapsed_seconds':elapsed,'wall_limit_seconds':limits['wall_seconds'],'owned_processes_remaining':survivors,'termination_events':events}
 (operation/'terminal.json').write_bytes(contract.canonical(terminal));assert retained()<=contract.OUTPUT
 assert exit_code==0 and reason is None and not survivors,'Unqualified actual command; retained history, no retry'
 return terminal
if __name__=='__main__':
 assert sys.flags.isolated and sys.dont_write_bytecode,'Use exact isolated Python -I -B entry'
 assert len(sys.argv)==4
 print(json.dumps(supervise(pathlib.Path(sys.argv[1]),sys.argv[2],pathlib.Path(sys.argv[3]))))
