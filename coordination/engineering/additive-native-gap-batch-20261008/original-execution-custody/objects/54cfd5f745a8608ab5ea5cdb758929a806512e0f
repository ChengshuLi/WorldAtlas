"""Fresh bounded operation supervision; no scientific calculations in this driver."""
import hashlib,importlib.util,json,os,pathlib,re,subprocess,sys,time
HERE=pathlib.Path(__file__).resolve().parent
helper=HERE/'owned_child_termination.py'
if hashlib.sha256(helper.read_bytes()).hexdigest()!='00c6028d814eabb67fd1986c7e7b0473836823dcfc81072d2b6563b0a5151c61':raise RuntimeError('Termination helper drift')
spec=importlib.util.spec_from_file_location('owned_child_termination',helper);cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
repo=pathlib.Path.cwd().resolve();node=pathlib.Path('/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
request_path=sys.argv[1];request_raw=(repo/request_path).read_bytes();request=json.loads(request_raw)
head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip();request_sha=hashlib.sha256(request_raw).hexdigest()
if subprocess.check_output(['git','show',head+':'+request_path])!=request_raw:raise RuntimeError('Request not frozen')
if os.environ.get('NODE_OPTIONS','').strip() or os.environ.get('NODE_PATH','').strip():raise RuntimeError('Plain Node required')
destination=repo/request['destination']
if os.path.lexists(destination):raise RuntimeError('Fresh output destination required')
for path in [destination.parent,repo/'.cache']:
 if path.exists() and (path.is_symlink() or not path.is_dir() or path.resolve()!=path):raise RuntimeError('Nonordinary parent')
operation=repo/'.cache'/(pathlib.Path(request_path).stem+'-operating')
if os.path.lexists(operation):raise RuntimeError('Fresh operating log destination required')
operation.mkdir()
command=['/usr/bin/time','-l',str(node),'scripts/additive-gap-repair.mjs',str(repo),head,request_path,request_sha,request['destination']]
cap=512*1024*1024;deadline_seconds=600;events=[];samples=[];refusal=None;start=time.monotonic()
def rss_group(pgid):
 rows=[]
 for line in subprocess.check_output(['ps','-axo','pid=,ppid=,pgid=,rss=,lstart=']).decode().splitlines():
  fields=line.split()
  if len(fields)>=9 and fields[2]==str(pgid):rows.append({'pid':int(fields[0]),'ppid':int(fields[1]),'pgid':int(fields[2]),'rss_bytes':int(fields[3])*1024,'started':' '.join(fields[4:])})
 return rows
with (operation/'stdout.txt').open('xb') as stdout,(operation/'stderr.txt').open('xb') as stderr:
 process=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
 identities=cleanup.snapshot();identity=identities.get(process.pid)
 if identity is None or identity['pgid']!=process.pid:raise RuntimeError('Fresh owned root identity missing')
 while process.poll() is None:
  rows=rss_group(process.pid);total=sum(row['rss_bytes'] for row in rows);samples.append({'elapsed_seconds':time.monotonic()-start,'rss_bytes':total,'members':rows})
  if total>cap or time.monotonic()-start>deadline_seconds:
   refusal='sampled-group-rss-cap' if total>cap else 'wall-deadline'
   events=cleanup.terminate_owned(process,identity);break
  time.sleep(.1)
 code=process.wait()
remaining=rss_group(process.pid)
if remaining:raise RuntimeError('Owned process group survived natural terminal')
stderr=(operation/'stderr.txt').read_text();match=re.search(r'(\d+)\s+maximum resident set size',stderr)
peak=max((sample['rss_bytes'] for sample in samples),default=0);lifetime=int(match[1]) if match else None
if lifetime is None:refusal=refusal or 'missing-time-lifetime-rss'
if lifetime is not None and lifetime>cap:refusal=refusal or 'time-lifetime-rss-cap'
qualified=code==0 and refusal is None and not remaining
result={'version':1,'execution_commit':head,'request_sha256':request_sha,'destination':request['destination'],'qualified':qualified,
 'exit':{'code':code if code>=0 else None,'signal':None if code>=0 else -code},'refusal':refusal,'owned_processes_remaining':remaining,
 'command':command,'owned_root_identity':identity,'elapsed_seconds':time.monotonic()-start,'rss_cap_bytes':cap,'wall_deadline_seconds':deadline_seconds,
 'peak_sampled_group_rss_bytes':peak,'time_lifetime_max_rss_bytes':lifetime,'termination_events':events,
 'monitoring_limits':'Sampled complete process group plus time child lifetime maximum; not a kernel-enforced memory ceiling.',
 'supervisor':{'path':str(pathlib.Path(__file__).resolve()),'sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
 'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'python_executable':sys.executable,'python_bytes':os.stat(sys.executable).st_size}}
(operation/'samples.json').write_text(json.dumps(samples)+'\n');(operation/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));sys.exit(0 if qualified else 1)
