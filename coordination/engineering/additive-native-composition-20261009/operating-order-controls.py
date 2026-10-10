"""Actual supervisor prelaunch refusals; capture/Git and resource commands
explicitly delegated to tiny fixtures. No actual scientific/stock command.
"""
import pathlib,tempfile,json,sys,importlib.util
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('supervisor_control',HERE/'supervise-current-rebind.py');s=importlib.util.module_from_spec(spec);exec(compile((HERE/'supervise-current-rebind.py').read_bytes(),str(HERE/'supervise-current-rebind.py'),'exec'),s.__dict__)
negative=0
with tempfile.TemporaryDirectory(prefix='rebind-operating-order-') as tmp:
 root=pathlib.Path(tmp).resolve();(root/'.cache').mkdir();plan=root/'plan.json';plan.write_bytes(s.contract.canonical({'limits':{'complete_phase_bytes':200000000,'rss_bytes':536870912,'sampled_stop_bytes':402653184,'wall_seconds':1200,'output_bytes':4194304}}))
 pre={'runtime':[{'role':'node','path':'/fixture/node','bytes':100,'sha256':'7'*64,'mode':493},{'role':'time','path':'/fixture/time','bytes':100,'sha256':'7'*64,'mode':493},{'role':'supervisor-python','path':sys.executable,'bytes':100,'sha256':'7'*64,'mode':493}], 'code':[],'entry':{'path':'/fixture/entry'},'supervisor':{'path':str(HERE/'supervise-current-rebind.py')},'plan':{'path':str(plan)}}
 issued={'version':1,'kind':'issued-current-rebind-execution-pre-use-v1','execution_commit':'1'*40,'root':str(root),'command':['/fixture/time','-l','/fixture/node','/fixture/entry',str(plan),str(root/'.cache'/'output')],'pre_use':pre,'operating_phase_bytes':1,'output_log_reserve_bytes':12582912}
 raw=s.contract.canonical(issued);f=root/'issued.json';f.write_bytes(raw);captured=[];commands=[];children=[]
 s.contract.capture=lambda *args:captured.append(args) or pre
 def stop(*args,**kwargs):children.append(args);raise AssertionError('Popen must not occur')
 s.subprocess.Popen=stop
 for mode in ['stock-command-failure','stock-cap-refusal','vm-cap-refusal']:
  def resource(args,**kwargs):
   commands.append(args)
   if mode=='stock-command-failure':raise s.subprocess.CalledProcessError(1,args)
   if args[-1]=='check':return s.contract.canonical({'freeBytes':100 if mode=='stock-cap-refusal' else 20000000000,'checkoutBytes':40000000000})
   return 'Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free: 0.\nPages inactive: 0.\nPages speculative: 0.\n'
  s.subprocess.check_output=resource
  try:s.supervise(f,s.contract.digest(raw),root/'.cache'/'operation')
  except (AssertionError,s.subprocess.CalledProcessError):negative+=1
  else:raise AssertionError('Expected actual resource refusal')
  assert not children and not (root/'.cache'/'operation').exists() and not (root/'.cache'/'output').exists()
 result={'version':1,'kind':'actual-supervisor-prelaunch-order-controls','negatives':negative,'child_commands':len(children),'output_directories_created':0,'limits':['Actual supervise function and resource branches; whole execution capture/Git and resource-command results explicitly stubbed. No actual capacity report, runtime qualification or cold bank read.']}
 (HERE/'operating-order-controls.json').write_bytes(s.contract.canonical(result));print(json.dumps(result))
