"""Owned serial proposal pair; existing reviewed descendant termination, measured limits."""
import pathlib,subprocess,os,time,json,datetime,hashlib,importlib.util,re
W=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/13630faa807843641a6abb3484134a94a87e5c38c2665c17f5c9742c84749ddf/work')
R=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/arctic-three-repair-1520-20261008')
HEAD='043af92647438f21e1464c1dccc8b7aaf8a2ea35'
PYTHON='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python'
HELPER=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/1295-normal-consumer-materialization-20261008/final-author-cache-preserved-94495073/1295-owned-child-termination.py')
assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='00c6028d814eabb67fd1986c7e7b0473836823dcfc81072d2b6563b0a5151c61'
spec=importlib.util.spec_from_file_location('owned_termination',HELPER);termination=importlib.util.module_from_spec(spec);spec.loader.exec_module(termination)
assert hashlib.sha256((R/'owned-group.py').read_bytes()).hexdigest()=='9ac8aeca9c721968bf33e69e219dbfb103875263b994dff1bd2e94402d0750ce'
spec2=importlib.util.spec_from_file_location('owned_group',R/'owned-group.py');owned_group=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(owned_group)
STOP=640*1024*1024; CEILING=768*1024*1024; WALL=1200; GROWTH=2*18*1024*1024+4*1024*1024

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def usage(group):
 rows=[]
 for line in subprocess.check_output(['ps','-axo','pid=,ppid=,pgid=,rss=,command='],text=True).splitlines():
  fields=line.split(None,4)
  if len(fields)==5 and int(fields[2])==group:rows.append({'pid':int(fields[0]),'ppid':int(fields[1]),'rss_bytes':int(fields[3])*1024,'command':fields[4]})
 return rows

def retained():
 roots=[W/'.cache'/'arctic-proposal-043',R/'pair-execution-043']
 return sum(p.stat().st_size for root in roots if root.exists() for p in root.rglob('*') if p.is_file())

def run():
 assert hashlib.sha256(pathlib.Path('/Library/Developer/CommandLineTools/usr/bin/git').read_bytes()).hexdigest()=='4c5ca299b5311572b4f948d11efd7c66dcadf30950fbf260688ee32f4a63f6a4'
 assert subprocess.check_output(['/Library/Developer/CommandLineTools/usr/bin/git','rev-parse','HEAD'],cwd=W,text=True).strip()==HEAD
 assert not subprocess.check_output(['/Library/Developer/CommandLineTools/usr/bin/git','status','--porcelain'],cwd=W,text=True).strip()
 D=R/'pair-execution-043';D.mkdir(exist_ok=False)
 results=[]
 for number in (1,2):
  O=W/'.cache'/'arctic-proposal-043'/('run-'+str(number)); assert not O.exists()
  cmd=['/usr/bin/time','-l',PYTHON,'coordination/engineering/arctic-three-retained-land-fit-repair-20261008/producer.py','--commit',HEAD,'--out',str(O),'--code-source','/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/13630faa807843641a6abb3484134a94a87e5c38c2665c17f5c9742c84749ddf/work/.cache/arctic-code-source-043.json','--code-source-sha','28e6f56180beda7b6f6e3a3d2ac8c48b8292ae26ad41ef044aaf8b23b5607aca','--code-source-bytes','2527']
  start=now();tick=time.monotonic();peak=0;reason=None;events=[]
  stdout=D/f'run-{number}.stdout.json';stderr=D/f'run-{number}.stderr.log'
  with stdout.open('xb') as out,stderr.open('xb') as err,(D/f'run-{number}.samples.jsonl').open('x') as samples:
   p=subprocess.Popen(cmd,cwd=W,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=out,stderr=err,start_new_session=True)
   identity=termination.snapshot().get(p.pid)
   assert identity and identity['pgid']==p.pid
   authority=owned_group.OwnedGroup(p,identity)
   (D/f'run-{number}.launch.json').write_text(json.dumps({'pid':p.pid,'identity':identity,'command':cmd,'started_at':start,'head':HEAD,'output':str(O)})+'\n')
   print(json.dumps({'run':number,'pid':p.pid,'identity':identity,'command':cmd}),flush=True)
   while p.poll() is None:
    rows=usage(p.pid);total=sum(r['rss_bytes'] for r in rows);peak=max(peak,total)
    samples.write(json.dumps({'at':now(),'elapsed':time.monotonic()-tick,'rss_bytes':total,'processes':rows})+'\n');samples.flush()
    if total>STOP:reason='process-tree sampled RSS exceeds stricter640MiB stop'
    elif time.monotonic()-tick>WALL:reason='walltime exceeds1200s'
    elif retained()>GROWTH:reason='actual retained growth exceeds complete output/log reserve'
    if reason:events=authority.cleanup();break
    time.sleep(.25)
   exit_code=p.wait()
  survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
  if survivors:
   events+=authority.cleanup();reason=reason or 'Unexpected owned descendants after natural time exit; cleaned and unqualified'
   survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
  text=stderr.read_text();m=re.search(r'^\s*(\d+)\s+maximum resident set size',text,re.M);lifetime=int(m.group(1)) if m else None
  qualified=exit_code==0 and reason is None and not survivors and lifetime is not None and lifetime<=CEILING and peak<=CEILING
  receipt={'run':number,'head':HEAD,'command':cmd,'env':{'PYTHONDONTWRITEBYTECODE':'1'},'started_at':start,'ended_at':now(),'elapsed_seconds':time.monotonic()-tick,'exit_code':exit_code,'qualified':qualified,'guard_reason':reason,'sampled_group_peak_bytes':peak,'time_l_lifetime_max_rss_bytes':lifetime,'sampler_limit':'Sampling may miss transient group peaks; time-l is per-process lifetime maximum, not combined simultaneous RSS.','termination_events':events,'owned_group_survivors':survivors,'sampled_stop_bytes':STOP,'original_ceiling_bytes':CEILING,'wall_limit_seconds':WALL,'retained_growth_bytes':retained(),'retained_growth_limit':GROWTH}
  (D/f'run-{number}.terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');results.append(receipt);print(json.dumps(receipt),flush=True)
  if retained()>GROWTH:raise RuntimeError('Terminal receipt exceeds complete growth reserve')
  if not qualified:raise RuntimeError('Unqualified actual proposal run; no automatic retry')
 pairs=[]
 for one in sorted((W/'.cache'/'arctic-proposal-043'/'run-1').iterdir()):
  two=one.parent.parent/'run-2'/one.name;a=one.read_bytes();b=two.read_bytes();assert a==b and one.stat().st_mode&0o777==two.stat().st_mode&0o777
  pairs.append({'path':one.name,'bytes':len(a),'sha256':hashlib.sha256(a).hexdigest(),'mode':oct(one.stat().st_mode&0o777),'whole_equal':True})
 (D/'whole-pair-equality.json').write_text(json.dumps({'head':HEAD,'actual_two_qualified_runs':True,'products':pairs,'no_third_run':True},indent=2)+'\n')
 if retained()>GROWTH:raise RuntimeError('Final equality receipt exceeds complete growth reserve')
run()
