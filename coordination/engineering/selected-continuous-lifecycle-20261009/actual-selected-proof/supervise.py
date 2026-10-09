import pathlib,json,hashlib,subprocess,os,re,time,datetime,types,signal,stat
D=pathlib.Path(__file__).resolve().parent;R=pathlib.Path('/Users/chengshuli/world-atlas-workspace')
P=D/'program';raw=(P/'issued-command.json').read_bytes();issued=json.loads(raw)
contract=json.loads((D/'operating-contract.json').read_bytes())
assert hashlib.sha256(raw).hexdigest()==contract['issued_command_sha256']
def check_source_custody():
 result=[]
 for row in issued['source_files']:
  p=P/row['path'];b=p.read_bytes();assert p.is_file() and not p.is_symlink() and len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
  q=pathlib.Path(row['consumed_path']);actual=q.read_bytes();assert q.is_file() and not q.is_symlink() and actual==b
  assert ('100755' if q.stat().st_mode&0o111 else '100644')==row['mode']
  assert hashlib.sha1(b'blob '+str(len(actual)).encode()+b'\0'+actual).hexdigest()==row['git_blob_oid']
  root=q
  for _ in pathlib.Path(row['path']).parts:root=root.parent
  tree=subprocess.check_output(['git','ls-tree',row['commit'],'--',row['path']],cwd=root,text=True).strip().split()
  assert tree==[row['mode'],'blob',row['git_blob_oid'],row['path']]
  result.append(row)
 return result
pre_use=check_source_custody()
for row in issued['execution_runtimes']:
 p=pathlib.Path(row['path']);assert p.stat().st_size==row['bytes'];h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 assert h.hexdigest()==row['sha256']
assert not (D/'checker.stdout').exists() and not (D/'operating-receipt.json').exists()
vm=subprocess.check_output(['vm_stat'],text=True);page=int(re.search(r'page size of (\d+)',vm).group(1));v={k:int(n) for k,n in re.findall(r'^([^:]+):\s+(\d+)\.',vm,re.M)};supply=page*sum(v.get(k,0) for k in ['Pages free','Pages inactive','Pages speculative'])
assert supply>=contract['maximum_RSS_bytes']+contract['minimum_host_reserve_bytes'],'Prospective host supply refusal before child launch'
W=R/'.worldatlas-workspaces/8c86b01772c1c827/3d62cf18b0b42e3ae3cd26d42f5e7ac90b65e45ead741649cedd79762724f9e7/work'
subprocess.run([issued['execution_runtimes'][0]['path'],str(W/'scripts/local-workspace.mjs'),'check'],cwd=W,stdout=subprocess.DEVNULL,check=True)
helper=pathlib.Path(contract['termination_helper_path']);b=helper.read_bytes();assert hashlib.sha256(b).hexdigest()==contract['termination_helper_sha256'];m=types.ModuleType('owned');exec(compile(b,str(helper),'exec'),m.__dict__)
def size():return sum(p.stat().st_size for p in D.rglob('*') if p.is_file() and not p.is_symlink())
initial=size();tick=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat();samples=[];observed={};reason=None;events=[]
env=dict(os.environ);env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None);env.pop('__PYVENV_LAUNCHER__',None)
cmd=['/usr/bin/time','-l',*issued['command']]
def cleanup_launch(process):
 # This Popen created the fresh session; no failed snapshot grants foreign authority.
 for sig in (signal.SIGTERM,signal.SIGKILL):
  try:os.killpg(process.pid,sig)
  except ProcessLookupError:pass
  if sig==signal.SIGTERM:time.sleep(.05)
 process.wait(timeout=5)
def own_launch(process):
 try:
  identity=m.snapshot().get(process.pid)
  assert identity and identity['pgid']==process.pid
  return identity
 except BaseException:
  cleanup_launch(process)
  raise
with (D/'checker.stdout').open('xb') as out,(D/'checker.stderr').open('xb') as err:
 p=subprocess.Popen(cmd,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
 try:
  identity=own_launch(p)
  while p.poll() is None:
   rows=m.snapshot();group={pid:r for pid,r in rows.items() if r['pgid']==p.pid};observed.update(group);rss=0
   for line in subprocess.check_output(['ps','-axo','pid=,pgid=,rss='],text=True).splitlines():
    z=line.split()
    if len(z)==3 and int(z[1])==p.pid:rss+=int(z[2])*1024
   samples.append({'elapsed_s':time.monotonic()-tick,'group_RSS_bytes':rss,'members':group})
   if rss>=contract['maximum_RSS_bytes']-contract['sample_margin_bytes'] or time.monotonic()-tick>contract['maximum_wall_seconds'] or size()-initial>contract['maximum_new_storage_bytes'] or (D/'checker.stdout').stat().st_size>contract['maximum_result_bytes'] or (D/'checker.stderr').stat().st_size>contract['maximum_stderr_bytes']:
    reason='Actual sampled RSS/wall/storage/result/stderr admission failed'
    if p.poll() is None:events=m.terminate_owned(p,identity)
    break
   time.sleep(.5)
  code=p.wait()
 except BaseException as failure:
  reason='Owned launch/sampling exception: '+type(failure).__name__+': '+str(failure)
  cleanup_launch(p)
  code=p.returncode
try:last=m.snapshot()
except BaseException:
 cleanup_launch(p)
 raise
survivors={pid:r for pid,r in last.items() if r['pgid']==p.pid};still=[pid for pid,r in observed.items() if pid in last and last[pid]['started']==r['started'] and last[pid]['pgid']==r['pgid']]
stderr=(D/'checker.stderr').read_bytes();match=re.findall(r'^\s*(\d+)\s+maximum resident set size\s*$',stderr.decode(),re.M);peak=int(match[-1]) if len(match)==1 else None
post_use=check_source_custody()
assert pre_use==post_use
qualified=code==0 and reason is None and peak is not None and peak<=contract['maximum_RSS_bytes'] and not survivors and not still
pins=[]
for name in ['checker.stdout','checker.stderr']:
 b=(D/name).read_bytes();pins.append({'path':str(D/name),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
receipt={'kind':'actual-full-selected-native-comparison-operating-receipt','code_head':issued['code_head'],'baseline':issued['baseline'],'candidate':issued['candidate'],'issued_command_sha256':hashlib.sha256(raw).hexdigest(),'contract':contract,'command':cmd,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':code,'stop_reason':reason,'elapsed_s':time.monotonic()-tick,'actual_external_lifetime_process_peak_RSS_bytes':peak,'max_sampled_group_RSS_bytes':max([x['group_RSS_bytes'] for x in samples],default=0),'VM_supply_upper_estimate_before_launch':supply,'operating_admission_qualified':qualified,'natural_terminal_owned_processes_absent':not survivors and not still,'new_storage_bytes':size()-initial,'samples':samples,'termination_events':events,'whole_output_pins':pins,'source_pre_use':pre_use,'source_post_use':post_use,'global_scientific_executions':0}
(D/'operating-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['samples','command','contract','termination_events']}));raise SystemExit(0 if qualified else 1)
