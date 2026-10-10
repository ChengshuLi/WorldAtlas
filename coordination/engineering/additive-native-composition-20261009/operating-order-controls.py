"""Actual prelaunch branches with complete, explicit small resource fixtures.
No stock command, selected-bank command or scientific operation is executed.
New observations go to stdout; historical sibling receipts are never written.
"""
import pathlib,tempfile,json,sys,importlib.util,copy
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('supervisor_control',HERE/'supervise-current-rebind.py');s=importlib.util.module_from_spec(spec);exec(compile((HERE/'supervise-current-rebind.py').read_bytes(),str(HERE/'supervise-current-rebind.py'),'exec'),s.__dict__)
negative=0;positive=0
class LaunchSentinel(Exception):pass
with tempfile.TemporaryDirectory(prefix='rebind-operating-order-') as tmp:
 root=pathlib.Path(tmp).resolve();(root/'.cache').mkdir();plan=root/'plan.json';plan.write_bytes(s.contract.canonical({'limits':{'complete_phase_bytes':200000000,'rss_bytes':536870912,'sampled_stop_bytes':402653184,'wall_seconds':1200,'output_bytes':4194304}}))
 pre={'runtime':[{'role':'node','path':'/fixture/node','bytes':100,'sha256':'7'*64,'mode':493},{'role':'time','path':'/fixture/time','bytes':100,'sha256':'7'*64,'mode':493},{'role':'supervisor-python','path':sys.executable,'bytes':100,'sha256':'7'*64,'mode':493}], 'code':[],'entry':{'path':'/fixture/entry'},'supervisor':{'path':str(HERE/'supervise-current-rebind.py')},'plan':{'path':str(plan)}}
 stock={'limits':{'minimumFree':10737418240},'freeBytes':20000000000,'checkoutBytes':1000000,'entries':[{'path':str(root),'slot':'work','status':'ready','reservation':1073741824}],'worktrees':[{'path':str(root),'managed':True,'bytes':1000000}]}
 captured=[];commands=[];children=[];s.contract.capture=lambda *args:captured.append(args) or pre
 s.platform_contract=lambda pre:('-v','/usr/bin:/bin')
 def stop(*args,**kwargs):children.append(args);raise LaunchSentinel('Reached actual Popen after every prelaunch gate')
 s.subprocess.Popen=stop
 for mode,expected in [('positive',None),('stock-command-failure','stock command failed'),('stock-cap-refusal','Fresh current stock/growth'),('reservation-refusal','Measured slot'),('supply-refusal','fixture supply refused'),('operating-refusal','operating')]:
  operation=root/'.cache'/('operation-'+mode);output=root/'.cache'/('output-'+mode)
  issued={'version':1,'kind':'issued-current-rebind-execution-pre-use-v1','execution_commit':'1'*40,'root':str(root),'command':['/fixture/time','-v','/fixture/node','--expose-gc','/fixture/entry',str(plan),str(output)],'pre_use':pre,'operating_phase_bytes':200000000+200+s.contract.OUTPUT+s.contract.META,'output_log_reserve_bytes':s.contract.OUTPUT}
  if mode=='operating-refusal':issued['operating_phase_bytes']=1
  raw=s.contract.canonical(issued);f=root/('issued-'+mode+'.json');f.write_bytes(raw)
  def resource(args,**kwargs):
   commands.append(args);assert args[-1]=='check'
   if mode=='stock-command-failure':raise AssertionError('stock command failed')
   value=copy.deepcopy(stock)
   if mode=='stock-cap-refusal':value['freeBytes']=value['limits']['minimumFree']
   if mode=='reservation-refusal':value['worktrees'][0]['bytes']=value['entries'][0]['reservation']
   return s.contract.canonical(value)
  def supply(env):
   if mode=='supply-refusal':raise AssertionError('fixture supply refused')
   return {'fixture':True,'required_bytes':805306368,'supply_upper_bytes':805306368}
  s.subprocess.check_output=resource;s.fresh_host_supply=supply;before=len(children)
  try:s.supervise(f,s.contract.digest(raw),operation)
  except LaunchSentinel:
   assert mode=='positive' and operation.exists();positive+=1
  except AssertionError as error:
   assert mode!='positive'
   if mode!='operating-refusal':assert expected in str(error),(mode,str(error))
   assert len(children)==before and not operation.exists();negative+=1
  else:raise AssertionError('Expected exact branch marker')
  assert not output.exists()
 # The positive fixture is complete enough to reach Popen; every intended
 # negative is checked separately and must not be a missing-key failure.
 assert positive==1 and len(children)==1 and len(captured)==6

base={'concurrent_reserved_bytes':0,'observed_aggregate_rss_bytes':1048576,'meminfo':'MemAvailable: 4194304 kB\nMemTotal: 8388608 kB\n','ancestors':[{'path':'/parent/leaf','maximum':'max\n','current':'0\n'},{'path':'/parent','maximum':str(2147483648+805306368+1000),'current':'1000'}],'limits':'Max address space         unlimited            unlimited            bytes\nMax data size             unlimited            unlimited            bytes\n','status':'VmSize: 1024 kB\nVmData: 512 kB\n','unknown_limits':['Explicit fixture hidden-ancestor uncertainty']}
assert s.evaluate_linux_supply(base)['residual_reported_bytes']==805306368;positive+=1
unexposed=copy.deepcopy(base);unexposed['ancestors']=[];assert s.evaluate_linux_supply(unexposed)['residual_reported_bytes']>805306368;positive+=1
for mutate in [lambda x:x.update(concurrent_reserved_bytes=1),lambda x:x.update(meminfo='MemAvailable: 1 kB\nMemTotal: 8388608 kB\n'),lambda x:x.update(meminfo=x['meminfo']*2),lambda x:x['ancestors'][1].update({'current':'1001'}),lambda x:x['ancestors'][0].update({'maximum':'-1'}),lambda x:x['ancestors'][0].update({'current':'unknown'}),lambda x:x.update(observed_aggregate_rss_bytes=8388608*1024),lambda x:x.update(limits=x['limits'].replace('unlimited            unlimited','1                    1',1)),lambda x:x.update(status='VmSize: 1 kB\n')]:
 value=copy.deepcopy(base);mutate(value)
 try:s.evaluate_linux_supply(value)
 except AssertionError:negative+=1
 else:raise AssertionError('Expected specific Linux supply refusal')
# Exact exposed ancestor traversal, including a finite parent shared by siblings.
with tempfile.TemporaryDirectory(prefix='rebind-cgroup-') as tmp:
 mount=pathlib.Path(tmp).resolve();leaf=mount/'parent'/'leaf';leaf.mkdir(parents=True)
 (mount/'cgroup.controllers').write_text('memory cpu\n')
 for directory,maximum,current in [(mount/'parent','3000000000','100000000'),(leaf,'max','1000')]:
  (directory/'memory.max').write_text(maximum);(directory/'memory.current').write_text(current)
 line='10 1 0:1 / '+str(mount)+' rw - cgroup2 cgroup rw\n'
 rows,unknown=s.exposed_cgroup_headroom('0::/parent/leaf\n',line)
 assert [r['path'] for r in rows]==[str(leaf),str(mount/'parent')] and unknown;positive+=1
 (leaf/'memory.current').unlink()
 try:s.exposed_cgroup_headroom('0::/parent/leaf\n',line)
 except FileNotFoundError:negative+=1
 else:raise AssertionError('Known exposed unreadable control must refuse')
rows,unknown=s.exposed_cgroup_headroom('0::/\n','');assert not rows and unknown;positive+=1
mac=' 0.02 real 0.01 user 0.01 sys\n 1024 maximum resident set size\n';gnu='Maximum resident set size (kbytes): 1\nElapsed (wall clock) time (h:mm:ss or m:ss): 0:00.02\n'
assert s.external_time_usage(mac,'-l')==(1024,.02);assert s.external_time_usage(gnu,'-v')==(1024,.02);positive+=2
for text,option in [(mac,'-v'),(gnu,'-l'),(mac+mac,'-l'),(gnu+gnu,'-v'),(gnu.replace('(kbytes)','(bytes)'),'-v'),(gnu.replace('0:00.02','unknown'),'-v'),(gnu.replace(': 1\n',': 0\n'),'-v')]:
 try:s.external_time_usage(text,option)
 except AssertionError:negative+=1
 else:raise AssertionError('Expected raw time dialect/unit/duplicate refusal')
print(json.dumps({'version':1,'kind':'actual-supervisor-prelaunch-order-controls','positives':positive,'negatives':negative,'launch_sentinel_calls':len(children),'actual_children':0,'limits':['Actual supervisor prelaunch gates with complete stock/supply fixtures, delegated whole capture and a Popen sentinel. Reported-supply fixtures include finite exposed ancestors, unknown limits, the 2 GiB reserve and concurrent demand; they do not guarantee allocatable capacity or scientific qualification.']}))
