"""Actual helper/admission controls; small ordinary files, delegated Git metadata.
No stock report, installed runtime, cold command or selected bank is executed.
"""
import pathlib,tempfile,os,json,importlib.util,hashlib,sys
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('contract_controls',HERE/'execution-contract.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
protected={name:c.digest((HERE/name).read_bytes()) for name in ['owned-child-termination-original.py','owned-group-original.py','execution-contract.py','execution-code-paths.json','mac-execution-runtime-original.json']}
paths=json.loads((HERE/'execution-code-paths.json').read_bytes());head='1'*40
with tempfile.TemporaryDirectory(prefix='rebind-external-controls-') as tmp:
 root=pathlib.Path(tmp).resolve();code=[]
 for name in paths:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('ordinary fixture '+name+'\n').encode());code.append({'path':name,'bytes':p.stat().st_size,'sha256':c.digest(p.read_bytes())})
 def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':c.digest(p.read_bytes()),'mode':p.stat().st_mode&0o777}
 for name in ['node','git','entry','supervisor','plan']:(root/name).write_bytes(('fixture '+name+'\n').encode())
 pre={'runtime':[{'role':'node',**pin(root/'node')},{'role':'git',**pin(root/'git')}],'code':code,**{k:pin(root/k) for k in ['entry','supervisor','plan']}}
 actual=c.subprocess.check_output
 def git(args,**kwargs):
  if args[-2:]==['rev-parse','HEAD']:return head+'\n'
  if args[-2:]==['status','--porcelain']:return ''
  if 'ls-tree' in args:return ('100644 blob '+'2'*40+'\t'+args[-1]+'\0').encode()
  if 'show' in args:return (root/args[-1].split(':',1)[1]).read_bytes()
  raise AssertionError('Unexpected delegated Git operation')
 c.subprocess.check_output=git
 assert c.capture(root,head,pre)==pre
 positives=1;negatives=0
 def reject(fn):
  global negatives
  try:fn()
  except (AssertionError,FileNotFoundError):negatives+=1
  else:raise AssertionError('Expected actual helper refusal')
 opened=0;real_open=c.os.open
 def counted(*args,**kwargs):
  global opened
  opened+=1;return real_open(*args,**kwargs)
 c.os.open=counted
 before=opened;reject(lambda:c.admit([pre['runtime'][0]],output=c.PHASE));assert opened==before
 changed=json.loads(json.dumps(pre));changed['code'].pop();before=opened;reject(lambda:c.capture(root,head,changed));assert opened==before
 wrong={**pre['entry'],'sha256':'f'*64};reject(lambda:c.authenticate_file(wrong))
 wrong={**pre['entry'],'bytes':False};before=opened;reject(lambda:c.authenticate_file(wrong));assert opened==before
 link=root/'link';link.symlink_to(root/'entry');before=opened;reject(lambda:c.authenticate_file({**pre['entry'],'path':str(link)}));assert opened==before
 wrong={**pre['entry'],'mode':0o755};before=opened;reject(lambda:c.authenticate_file(wrong));assert opened==before
 # Real held-FD/pathname replacement, preserving complete bytes/mode, is refused.
 original_read=c.os.read;fired=False
 def replace(fd,count):
  global fired
  value=original_read(fd,count)
  if value and not fired:
   fired=True;replacement=root/'replacement';replacement.write_bytes((root/'entry').read_bytes());os.replace(replacement,root/'entry')
  return value
 c.os.read=replace;reject(lambda:c.authenticate_file(pre['entry']));c.os.read=original_read
 # A wrong immutable Git body cannot pass matching current filesystem custody.
 c.subprocess.check_output=lambda args,**kw:b'foreign' if 'show' in args else git(args,**kw)
 reject(lambda:c.capture(root,head,pre));c.subprocess.check_output=actual;c.os.open=real_open
 result={'version':1,'kind':'actual-external-helper-boundary-controls','positives':positives,'negatives':negatives,'complete_code_bodies':len(paths),'zero_open_phase_and_roster_refusals':2,'limits':['Actual production authenticate/admit/capture with ordinary fixtures, real held-FD replacement and explicitly delegated Git metadata. No installed runtime or actual cold invocation qualification.']}
 assert protected=={name:c.digest((HERE/name).read_bytes()) for name in protected}
 result['protected_bodies']=protected
 if sys.argv[1:]==['--installed-runtime']:
  assert sys.flags.isolated and sys.dont_write_bytecode
  loaded=[]
  for name in ['issue-current-rebind-execution.py','supervise-current-rebind.py']:
   spec=importlib.util.spec_from_file_location(name,HERE/name);m=importlib.util.module_from_spec(spec);exec(compile((HERE/name).read_bytes(),str(HERE/name),'exec'),m.__dict__);loaded.append(m)
  issuer,supervisor=loaded;runtime,option=issuer.platform_runtime()
  assert supervisor.platform_contract({'runtime':runtime})[0]==option
  admission=c.admit(runtime)
  for pin in runtime:c.authenticate_file(pin)
  platform=sys.platform
  try:
   sys.platform='darwin';mac,dialect=issuer.platform_runtime();assert dialect=='-l' and mac==json.loads((HERE/'mac-execution-runtime-original.json').read_bytes())['runtime']
   sys.platform='unreviewed'
   reject(issuer.platform_runtime)
  finally:sys.platform=platform
  result['installed_runtime']={'bodies':len(runtime),'bytes':sum(p['bytes'] for p in runtime),'admitted_bytes':admission,'mac_roster_unchanged':True,'unknown_platform_refused':True}
  result['reported_supply_observation']=supervisor.fresh_host_supply(dict(os.environ))
  timer=next(p['path'] for p in runtime if p['role']=='time')
  smoke=c.subprocess.run([timer,option,sys.executable,'-I','-B','-c','pass'],capture_output=True,text=True,timeout=5,env={**os.environ,'LC_ALL':'C','LANG':'C'})
  assert smoke.returncode==0 and not smoke.stdout and len(smoke.stderr.encode())<=40960
  rss,elapsed=supervisor.external_time_usage(smoke.stderr,option);assert rss<=536870912 and elapsed<=5
  result['genuine_time_smoke']={'exit_code':smoke.returncode,'lifetime_rss_bytes':rss,'elapsed_seconds':elapsed,'raw_stderr':smoke.stderr}
  result['limits'].append('Installed whole-byte runtime custody and read-only fresh supply observation only; no frozen-head execution or scientific command and no heavy-run reservation granted by this test.')
 elif sys.argv[1:]:raise AssertionError('Unknown control arguments')
 print(json.dumps(result))
