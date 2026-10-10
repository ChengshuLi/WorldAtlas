"""Tiny owned Linux process controls; no bank or scientific command.
Original cleanup bodies are loaded literally. Historical receipts are untouched.
"""
import pathlib,importlib.util,subprocess,sys,time,json,types,os,signal,select,tempfile
here=pathlib.Path(__file__).resolve().parent
modules=[]
for filename in ['supervise-current-rebind.py','owned-child-termination-original.py','owned-group-original.py','issue-current-rebind-execution.py']:
 spec=importlib.util.spec_from_file_location(filename.replace('.','_'),here/filename);module=importlib.util.module_from_spec(spec);exec(compile((here/filename).read_bytes(),str(here/filename),'exec'),module.__dict__);modules.append(module)
s,termination,group,issuer=modules
protected={name:s.contract.digest((here/name).read_bytes()) for name in ['owned-child-termination-original.py','owned-group-original.py']}
os.environ.update(PATH='/usr/bin:/bin' if sys.platform=='linux' else '/bin:/usr/bin',LC_ALL='C',LANG='C')
negative=0;live=0;algorithm=0
child="import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print('ready',flush=True);time.sleep(30)"
def ready(process):
 assert select.select([process.stdout],[],[],3)[0],'Tiny child readiness timeout'
 assert process.stdout.readline()==b'ready\n','Readiness follows SIG_IGN installation'
def absent(process):
 assert process.poll() is not None
 try:os.killpg(process.pid,0)
 except ProcessLookupError:return
 raise AssertionError('Owned group survived control')
def ensure_reaped(process):
 # Only this exact fresh test-owned group; never signal fixture/foreign PIDs.
 try:os.killpg(process.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 process.wait(timeout=5)
for failure in ('missing','foreign-group','constructor'):
 p=subprocess.Popen([sys.executable,'-I','-B','-c',child],stdout=subprocess.PIPE,start_new_session=True)
 try:
  ready(p);rows={} if failure=='missing' else {p.pid:{'pgid':p.pid+1 if failure=='foreign-group' else p.pid}}
  observed=[]
  def constructor(*args):observed.append('constructor');raise RuntimeError('Injected authority construction failure')
  try:s.own_launched_process(p,types.SimpleNamespace(snapshot=lambda:rows),types.SimpleNamespace(OwnedGroup=constructor))
  except (AssertionError,RuntimeError):negative+=1
  else:raise AssertionError('Expected actual launch rejection')
  assert observed==(['constructor'] if failure=='constructor' else [])
  assert p.returncode==-signal.SIGKILL;absent(p)
 finally:ensure_reaped(p);p.stdout.close()

# A genuine time wrapper reaps its direct child; no orphan is delegated to PID 1.
runtime,option=issuer.platform_runtime();timer=next(p['path'] for p in runtime if p['role']=='time')
for cleanup in ('owned-group','legacy-child-only'):
 with tempfile.TemporaryFile() as err:
  p=subprocess.Popen([timer,option,sys.executable,'-I','-B','-c',child],stdout=subprocess.PIPE,stderr=err,start_new_session=True)
  try:
   ready(p);identity,authority=s.own_launched_process(p,termination,group)
   events=authority.cleanup(grace=.05) if cleanup=='owned-group' else termination.terminate_owned(p,identity,grace=.05)
   assert any(e['signal']==signal.SIGTERM for e in events) and any(e['signal']==signal.SIGKILL for e in events)
   assert all(e['pid']!=p.pid and e['identity']['pgid']==p.pid for e in events);absent(p);live+=1
  finally:ensure_reaped(p);p.stdout.close()

# Deterministic PID/start/group adverses execute unchanged methods. Signals are
# explicitly recorded rather than delivered to invented process IDs.
real_snapshot=group.snapshot;real_kill=group.os.kill;sent=[]
parent=types.SimpleNamespace(pid=100,wait=lambda timeout:0);identity={'ppid':1,'pgid':100,'started':'root'}
base={100:identity,101:{'ppid':100,'pgid':100,'started':'child'},900:{'ppid':1,'pgid':900,'started':'foreign'}}
try:
 group.os.kill=lambda pid,sig:sent.append((pid,sig))
 for bad in ({},{100:{**identity,'started':'changed'}},{100:{**identity,'pgid':999}}):
  group.snapshot=lambda:bad
  try:group.OwnedGroup(parent,identity)
  except RuntimeError:negative+=1
  else:raise AssertionError('Expected exact root refusal')
 group.snapshot=lambda:base;authority=group.OwnedGroup(parent,identity)
 for changed in ({'started':'reused'},{'pgid':999}):
  state={pid:dict(row) for pid,row in base.items()};state[101].update(changed);group.snapshot=lambda:state;before=len(sent);authority.send(signal.SIGTERM);assert len(sent)==before;algorithm+=1
 state={101:{**base[101],'ppid':1},102:{'ppid':1,'pgid':100,'started':'late'},900:base[900]};group.snapshot=lambda:state
 assert set(authority.survivors())=={101,102};authority.send(signal.SIGTERM);assert {pid for pid,sig in sent}=={101,102};algorithm+=1
 # Check the second snapshot immediately before delivery, not only discovery.
 group.snapshot=lambda:base;authority=group.OwnedGroup(parent,identity);calls=0
 def drift():
  global calls
  calls+=1
  return base if calls==1 else {**base,101:{**base[101],'started':'reused'}}
 group.snapshot=drift;before=len(sent);authority.send(signal.SIGTERM);assert len(sent)==before;algorithm+=1
finally:group.snapshot=real_snapshot;group.os.kill=real_kill

# Actual supervisor exception wiring after the owned authority is acquired.
# Only metadata/capacity capture is delegated. Tiny timer->Python children run.
with tempfile.TemporaryDirectory(prefix='rebind-cleanup-wiring-') as tmp:
 root=pathlib.Path(tmp).resolve();(root/'.cache').mkdir();entry=root/'child.py'
 entry.write_text("import pathlib,signal,sys,time\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\npathlib.Path(sys.argv[1]+'.ready').write_text('ready')\ntime.sleep(30)\n")
 original_popen=s.subprocess.Popen;original_check=s.subprocess.check_output;original_write=pathlib.Path.write_bytes
 try:
  s.platform_contract=lambda pre:(option,os.environ['PATH']);s.contract.capture=lambda root,head,pre:pre;s.fresh_host_supply=lambda env:{'fixture':True}
  for mode in ('launch-report','sampling'):
   plan=root/(mode+'.json');plan.write_bytes(s.contract.canonical({'limits':{'complete_phase_bytes':200000000,'rss_bytes':536870912,'sampled_stop_bytes':402653184,'wall_seconds':1200,'output_bytes':4194304}}))
   ready_path=pathlib.Path(str(plan)+'.ready');owned=[];reached=[]
   def launch(*args,**kwargs):
    process=original_popen(*args,**kwargs)
    # Only the supervised start_new_session launch gets the readiness handshake.
    if kwargs.get('start_new_session'):
     owned.append(process);deadline=time.monotonic()+3
     while not ready_path.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
     assert ready_path.exists(),'Tiny wiring child not ready'
    return process
   def checks(args,**kwargs):
    if args[-1]=='check':return s.contract.canonical({'limits':{'minimumFree':10737418240},'freeBytes':20000000000,'entries':[{'path':str(root),'slot':'work','status':'ready','reservation':1073741824}],'worktrees':[{'path':str(root),'managed':True,'bytes':1000000}]})
    if mode=='sampling' and 'pid=,ppid=,pgid=,rss=,command=' in args:reached.append(mode);raise RuntimeError('Injected sampling failure')
    return original_check(args,**kwargs)
   def writes(path,raw):
    if mode=='launch-report' and path.name=='launch.json':reached.append(mode);raise RuntimeError('Injected launch report failure')
    return original_write(path,raw)
   runtime=[{'role':'node','path':sys.executable,'bytes':100},{'role':'time','path':timer,'bytes':100},{'role':'supervisor-python','path':sys.executable,'bytes':100},{'role':'process-inspector','path':'/usr/bin/ps','bytes':100}]
   pre={'runtime':runtime,'entry':{'path':str(entry)},'plan':{'path':str(plan)}}
   issued={'version':1,'kind':'issued-current-rebind-execution-pre-use-v1','execution_commit':'1'*40,'root':str(root),'command':[timer,option,sys.executable,str(entry),str(plan),str(root/'.cache'/('output-'+mode))],'pre_use':pre,'operating_phase_bytes':200000000+300+s.contract.OUTPUT+s.contract.META}
   raw=s.contract.canonical(issued);source=root/('issued-'+mode+'.json');source.write_bytes(raw)
   s.subprocess.Popen=launch;s.subprocess.check_output=checks;pathlib.Path.write_bytes=writes
   try:
    try:s.supervise(source,s.contract.digest(raw),root/'.cache'/('operation-'+mode))
    except RuntimeError as error:assert 'Injected' in str(error)
    else:raise AssertionError('Expected actual supervisor exception')
    assert reached==[mode] and len(owned)==1;absent(owned[0]);assert not (root/'.cache'/('operation-'+mode)/'terminal.json').exists();live+=1
   finally:
    for process in owned:ensure_reaped(process)
    s.subprocess.Popen=original_popen;s.subprocess.check_output=original_check;pathlib.Path.write_bytes=original_write
 finally:s.subprocess.Popen=original_popen;s.subprocess.check_output=original_check;pathlib.Path.write_bytes=original_write
assert protected=={name:s.contract.digest((here/name).read_bytes()) for name in protected}
print(json.dumps({'version':1,'kind':'actual-owned-launch-failure-controls','negative_controls':negative,'live_cleanup_controls':live,'identity_algorithm_controls':algorithm,'owned_processes_remaining':0,'protected_bodies':protected,'limits':['Real tiny wrapper/direct-child controls and production exception wiring; identity drift/late forks use explicit delegated snapshots and signal recorders. No scientific or selected-bank qualification.']}))
