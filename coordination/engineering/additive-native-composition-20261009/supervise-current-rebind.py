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

def require_stock_growth(stock,root,output_bytes):
 minimum=stock['limits']['minimumFree'];free=stock['freeBytes']
 assert type(minimum) is int and minimum>0 and type(free) is int and free>=0
 assert type(output_bytes) is int and output_bytes>0
 entries=[e for e in stock['entries'] if e['path']==str(root) and e['slot']=='work' and e['status']=='ready']
 assert len(entries)==1,'Fresh owned allocator entry required'
 reservation=entries[0]['reservation']
 assert type(reservation) is int and reservation>0 and output_bytes<=reservation,'Positive complete growth reservation required'
 slots=[s for s in stock['worktrees'] if s['path']==str(root) and s['managed'] is True]
 assert len(slots)==1,'Fresh measured owned allocator slot required'
 footprint=slots[0]['bytes']
 assert type(footprint) is int and footprint>=0 and footprint+output_bytes<=reservation,'Measured slot plus complete growth exceeds reservation'
 # Allocation admitted the reservation before setup. Fresh launch admits this
 # phase's complete growth against actual free space without reserving it twice.
 assert free-output_bytes>=minimum,'Fresh current stock/growth admission refused'

def platform_contract(pre):
 # The literal issuer roster is already part of the unchanged 28-file closure.
 # Comparing it prevents a caller-supplied issued file from selecting a different
 # time dialect, process inspector, Python body set or executable.
 name=HERE/'issue-current-rebind-execution.py'
 spec=importlib.util.spec_from_file_location('rebind_issuer_runtime',name)
 issuer=importlib.util.module_from_spec(spec)
 exec(compile(name.read_bytes(),str(name),'exec'),issuer.__dict__)
 runtime,option=issuer.platform_runtime()
 assert [p for p in pre['runtime'] if p['role']!='installed-dependency']==runtime,'Foreign platform runtime roster'
 return option,'/usr/bin:/bin' if sys.platform=='linux' else '/bin:/usr/bin'

def bounded_resource_text(path,limit=65536):
 # procfs reports zero st_size; admit a fixed 64 KiB maximum before opening.
 # Use the actual PID path, never the /proc/self symlink.
 path=pathlib.Path(path)
 for p in [path,*path.parents]:assert not p.is_symlink(),'Symlink resource path'
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  chunks=[];remaining=limit+1
  while remaining:
   chunk=os.read(fd,min(4096,remaining))
   if not chunk:break
   chunks.append(chunk);remaining-=len(chunk)
  raw=b''.join(chunks)
  assert len(raw)<=limit and not os.read(fd,1),'Truncated/oversized resource observation'
 finally:os.close(fd)
 return raw.decode('ascii')

def evaluate_linux_supply(evidence):
 # Reported prospective availability, matching the original Mac estimate.
 # Unknown hidden limits are disclosed; exposed finite limits always tighten it.
 values={}
 for name in ['MemAvailable','MemTotal']:
  matches=re.findall(r'^'+name+r':\s*(\d+) kB$',evidence['meminfo'],re.M)
  assert len(matches)==1,'Missing/duplicate host memory evidence'
  values[name]=int(matches[0])*1024
 assert 0<=values['MemAvailable']<=values['MemTotal'],'Malformed host memory totals'
 reserved=evidence['concurrent_reserved_bytes'];rss=evidence['observed_aggregate_rss_bytes']
 assert type(reserved) is int and reserved>=0 and type(rss) is int and rss>=0,'Missing coordinator reservation/aggregate observation'
 headroom=2147483648
 supply=min(values['MemAvailable'],max(0,values['MemTotal']-rss))
 ancestors=evidence['ancestors'];assert isinstance(ancestors,list) and len(ancestors)<=64
 seen=set()
 for row in ancestors:
  assert set(row)=={'path','maximum','current'} and row['path'] not in seen
  seen.add(row['path'])
  maximum=row['maximum'].strip();current=row['current'].strip()
  assert re.fullmatch(r'0|[1-9][0-9]*',current),'Malformed cgroup current bytes'
  assert maximum=='max' or re.fullmatch(r'0|[1-9][0-9]*',maximum),'Malformed cgroup maximum bytes'
  if maximum!='max':supply=min(supply,max(0,int(maximum)-int(current)))
 # Address-space/data rlimits remain additional negative gates, never RAM proof.
 for label,key in [('Max address space','VmSize'),('Max data size','VmData')]:
  ceiling=re.findall(r'^'+label+r'\s+(unlimited|[0-9]+)\s+(?:unlimited|[0-9]+)\s+bytes\s*$',evidence['limits'],re.M)
  usage=re.findall(r'^'+key+r':\s*(\d+) kB$',evidence['status'],re.M)
  assert len(ceiling)==len(usage)==1,'Unknown process memory ceiling/usage'
  if ceiling[0]!='unlimited':supply=min(supply,max(0,int(ceiling[0])-int(usage[0])*1024))
 residual=supply-headroom-reserved
 assert residual>=805306368,'Fresh reported residual Linux supply refused'
 return {'supply_upper_bytes':supply,'headroom_reserve_bytes':headroom,'concurrent_reserved_bytes':reserved,
         'residual_reported_bytes':residual,'required_bytes':805306368,'observations':evidence,
         'uncertainty':'Prospective reported availability only; unexposed limits are unknown, not unlimited. No swap credit or guaranteed allocation.'}

def exposed_cgroup_headroom(cgroup,mountinfo):
 memberships=[]
 for line in cgroup.splitlines():
  fields=line.split(':',2);assert len(fields)==3,'Malformed cgroup membership'
  hierarchy,controllers,member=fields
  assert hierarchy.isdigit() and member.startswith('/') and '..' not in member.split('/') and '.' not in member.split('/')
  if hierarchy=='0' and controllers=='':memberships.append(('cgroup2',member))
  elif 'memory' in controllers.split(','):memberships.append(('cgroup',member))
 mounts=[]
 for line in mountinfo.splitlines():
  halves=line.split(' - ');assert len(halves)==2,'Malformed mountinfo'
  left=halves[0].split();right=halves[1].split();assert len(left)>=6 and len(right)>=3
  if right[0]=='cgroup2' or right[0]=='cgroup' and 'memory' in right[2].split(','):
   mountroot,mountpath=left[3:5]
   assert '\\' not in mountroot+mountpath and mountroot.startswith('/') and mountpath.startswith('/'),'Unsupported escaped cgroup mount'
   mounts.append((right[0],pathlib.Path(mountroot),pathlib.Path(mountpath)))
 rows=[];unknown=[]
 for kind,member in memberships:
  candidates=[(root,mount) for typ,root,mount in mounts if typ==kind and pathlib.Path(member).is_relative_to(root)]
  if not candidates:
   assert not any(typ==kind for typ,root,mount in mounts),'Known exposed hierarchy does not map membership'
   unknown.append('No exposed '+kind+' memory mount for membership');continue
  assert len(candidates)==1,'Ambiguous exposed memory hierarchy'
  root,mount=candidates[0];leaf=mount/pathlib.Path(member).relative_to(root)
  chain=[leaf,*list(leaf.parents)[:len(leaf.parts)-len(mount.parts)]]
  assert len(chain)<=64 and chain[-1]==mount
  for directory in chain:
   if kind=='cgroup2':
    maximum=directory/'memory.max';current=directory/'memory.current'
    if not maximum.exists() and directory==mount and root==pathlib.Path('/'):
     # The global root has no memory.max. A namespace root may hide parents.
     controllers=bounded_resource_text(directory/'cgroup.controllers',4096)
     assert 'memory' in controllers.split(),'Unknown root memory-controller exposure'
     unknown.append('Exposed root has no memory.max; hidden ancestors remain unknown');continue
   else:maximum=directory/'memory.limit_in_bytes';current=directory/'memory.usage_in_bytes'
   first=bounded_resource_text(maximum,4096);usage=bounded_resource_text(current,4096)
   assert bounded_resource_text(maximum,4096)==first,'Memory ceiling changed during admission'
   rows.append({'path':str(directory),'maximum':first,'current':usage})
  unknown.append('Ancestors outside the exposed '+kind+' mount/namespace remain unknown')
 assert len(rows)<=64
 if not memberships:unknown.append('No memory cgroup membership exposed')
 return rows,unknown

def fresh_host_supply(env):
 if sys.platform=='darwin':
  vm=subprocess.check_output(['/usr/bin/vm_stat'],text=True,env=env)
  page=int(re.search(r'page size of (\d+) bytes',vm).group(1))
  pages=sum(int(re.search(r'^Pages '+name+r':\s*(\d+)',vm,re.M).group(1)) for name in ['free','inactive','speculative'])
  assert pages*page>=805306368,'Fresh conservative host supply refused; reclaimability uncertain'
  return {'vm_stat':vm,'supply_upper_bytes':pages*page,'required_bytes':805306368,'uncertainty':'Inactive/speculative reclaimability is an upper estimate, not guaranteed availability.'}
 assert sys.platform=='linux','Unreviewed execution platform'
 reservation=env.get('WORLDATLAS_CONCURRENT_RESERVED_BYTES','')
 assert re.fullmatch(r'0|[1-9][0-9]*',reservation),'Fresh coordinator concurrent reservation is required'
 proc=pathlib.Path('/proc')/str(os.getpid())
 evidence={name:bounded_resource_text(path) for name,path in {
  'meminfo':'/proc/meminfo','cgroup':proc/'cgroup','mountinfo':proc/'mountinfo',
  'limits':proc/'limits','status':proc/'status'}.items()}
 evidence['ancestors'],evidence['unknown_limits']=exposed_cgroup_headroom(evidence['cgroup'],evidence['mountinfo'])
 assert bounded_resource_text(proc/'cgroup')==evidence['cgroup'],'Cgroup membership changed during admission'
 ps=subprocess.check_output(['/usr/bin/ps','-axo','pid=,rss='],text=True,env=env)
 assert len(ps.encode())<=65536,'Oversized aggregate process report'
 rss=0
 for line in ps.splitlines():
  fields=line.split();assert len(fields)==2 and all(re.fullmatch(r'[0-9]+',x) for x in fields),'Malformed aggregate process report'
  rss+=int(fields[1])*1024
 evidence.update(concurrent_reserved_bytes=int(reservation),observed_aggregate_rss_bytes=rss,aggregate_ps=ps)
 assert len(contract.canonical(evidence))<=contract.META,'Resource observation metadata reserve exceeded'
 return evaluate_linux_supply(evidence)

def external_time_usage(text,option):
 assert option in ('-l','-v')
 rss_pattern=r'^\s*(\d+)\s+maximum resident set size\s*$' if option=='-l' else r'^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$'
 wall_pattern=r'^\s*(\d+(?:\.\d+)?)\s+real\s+\d+(?:\.\d+)?\s+user\s+\d+(?:\.\d+)?\s+sys\s*$' if option=='-l' else r'^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\d+(?::\d+){1,2}(?:\.\d+)?)\s*$'
 rss=re.findall(rss_pattern,text,re.M);wall=re.findall(wall_pattern,text,re.M)
 assert len(rss)==len(wall)==1,'Missing/duplicate raw time usage'
 lifetime=int(rss[0])*(1 if option=='-l' else 1024)
 elapsed=0.0
 for part in wall[0].split(':'):elapsed=elapsed*60+float(part)
 assert lifetime>0 and elapsed>=0,'Malformed raw time usage'
 return lifetime,elapsed

def supervise(issued_path,issued_sha,operation):
 assert issued_path.is_absolute() and '..' not in issued_path.parts
 for a in [issued_path,*issued_path.parents]:assert not a.is_symlink()
 assert issued_path.stat().st_size<=131072
 raw=issued_path.read_bytes();assert contract.digest(raw)==issued_sha;issued=json.loads(raw)
 assert issued['version']==1 and issued['kind']=='issued-current-rebind-execution-pre-use-v1'
 assert pathlib.Path(sys.executable).resolve()==pathlib.Path(next(p['path'] for p in issued['pre_use']['runtime'] if p['role']=='supervisor-python')).resolve(),'Actual Python executable differs from bound runtime'
 root=pathlib.Path(issued['root']);head=issued['execution_commit'];pre=issued['pre_use'];cmd=issued['command']
 time_option,private_path=platform_contract(pre)
 assert operation.is_absolute() and operation.is_relative_to(root/'.cache') and '..' not in operation.parts and not os.path.lexists(operation)
 for a in operation.parents:assert a.is_dir() and not a.is_symlink()
 assert isinstance(cmd,list) and (len(cmd)==6 or len(cmd)==7 and cmd[3]=='--expose-gc')
 bound_cmd=cmd[:3]+cmd[4:] if len(cmd)==7 else cmd
 assert len(bound_cmd)==6 and bound_cmd[0]==next(p['path'] for p in pre['runtime'] if p['role']=='time') and bound_cmd[1]==time_option and bound_cmd[2]==next(p['path'] for p in pre['runtime'] if p['role']=='node') and bound_cmd[3]==pre['entry']['path'] and bound_cmd[4]==pre['plan']['path']
 output=pathlib.Path(bound_cmd[5]);assert output.is_relative_to(root/'.cache') and '..' not in output.parts and not os.path.lexists(output)
 for a in output.parents:assert a.is_dir() and not a.is_symlink()
 before=contract.capture(root,head,pre);plan=json.loads(pathlib.Path(pre['plan']['path']).read_bytes());limits=plan['limits']
 # Fresh original stock report and explicit prospective retained growth; no
 # stale receipt or shell continuation can authorize the actual command.
 guard_env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONUSERBASE','__PYVENV_LAUNCHER__')}
 guard_env.update(PATH=private_path,LC_ALL='C',LANG='C')
 stock_raw=subprocess.check_output([cmd[2],str(root/'scripts/local-workspace.mjs'),'check'],cwd=root,env=guard_env)
 stock=json.loads(stock_raw);require_stock_growth(stock,root,contract.OUTPUT)
 supply=fresh_host_supply(guard_env)
 extra=sum(p['bytes'] for p in pre['runtime'] if p['role'] not in ('node','git','installed-dependency'))
 assert issued['operating_phase_bytes']==limits['complete_phase_bytes']+extra+contract.OUTPUT+contract.META<=contract.PHASE
 assert limits['sampled_stop_bytes']<=402653184 and limits['rss_bytes']<=536870912 and limits['wall_seconds']<=1200 and limits['output_bytes']<=4194304
 # Whole helper bytes are already frozen/pre-use verified in the complete code
 # roster. These literal historical mechanisms are not rewritten or relabeled.
 loaders=[]
 for name in ['owned-child-termination-original.py','owned-group-original.py']:
  s=importlib.util.spec_from_file_location(name.replace('.','_'),HERE/name);m=importlib.util.module_from_spec(s);exec(compile((HERE/name).read_bytes(),str(HERE/name),'exec'),m.__dict__);loaders.append(m)
 termination,owned_group=loaders
 operation.mkdir(mode=0o700);(operation/'stock-report.json').write_bytes(stock_raw);(operation/'host-supply.json').write_bytes(contract.canonical(supply));stdout=operation/'stdout.json';stderr=operation/'stderr.log';samples=operation/'samples.jsonl'
 def retained():return sum(p.stat().st_size for base in [operation,output] if base.exists() for p in base.rglob('*') if p.is_file())
 def logs():return all(not p.exists() or p.stat().st_size<= {'stdout.json':8192,'stderr.log':40960,'samples.jsonl':1048576}[p.name] for p in [stdout,stderr,samples])
 def usage(group):
  ps=next(p['path'] for p in pre['runtime'] if p['role']=='process-inspector');rows=[]
  for line in subprocess.check_output([ps,'-axo','pid=,ppid=,pgid=,rss=,command='],text=True).splitlines():
   f=line.split(None,4)
   if len(f)==5 and int(f[2])==group:rows.append({'pid':int(f[0]),'ppid':int(f[1]),'rss_bytes':int(f[3])*1024,'command':f[4]})
  return rows
 env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONUSERBASE','__PYVENV_LAUNCHER__')}
 # Literal helper subprocess uses ps by name; choose only the platform's
 # authenticated directory and stable C locale for PID/start/group snapshots.
 env.update(PATH=private_path,LC_ALL='C',LANG='C');os.environ.update(PATH=private_path,LC_ALL='C',LANG='C')
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
 text=stderr.read_text();lifetime=None;raw_elapsed=None
 try:lifetime,raw_elapsed=external_time_usage(text,time_option)
 except (AssertionError,ValueError):reason=reason or 'raw external time usage malformed'
 if lifetime is None or lifetime>limits['rss_bytes']:reason=reason or 'raw external lifetime RSS bound'
 elapsed=time.monotonic()-start
 if elapsed>limits['wall_seconds']:reason=reason or 'actual external elapsed wall bound'
 if raw_elapsed is not None and (raw_elapsed>limits['wall_seconds'] or raw_elapsed>elapsed+.01):reason=reason or 'raw external elapsed wall bound'
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
