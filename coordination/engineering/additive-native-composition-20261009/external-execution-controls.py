"""Actual helper/admission controls; small ordinary files, delegated Git metadata.
No stock report, installed runtime, cold command or selected bank is executed.
"""
import pathlib,tempfile,os,json,importlib.util,hashlib
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('contract_controls',HERE/'execution-contract.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
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
 (HERE/'external-execution-controls.json').write_bytes(c.canonical(result));print(json.dumps(result))
