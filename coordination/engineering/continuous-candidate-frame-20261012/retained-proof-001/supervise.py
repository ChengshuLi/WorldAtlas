import subprocess,time,os,json,signal,pathlib,sys,datetime
repo=pathlib.Path.cwd().resolve();head='1933d49ce3840d0d10bd76ba30e1d849e56c5233';before='9473d184683ee8ff8546300f2313779c3cba1d2b';after='791576647adc41241ce9b438f1bb0034088eed4e'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
run=repo/'.scratch-1763/retained-proof-001';run.mkdir()
command=['node','coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs','continuous',str(repo),head,before,after,str(run/'complete'),str(pathlib.Path(sys.executable).resolve())]
env=dict(os.environ)
for name in ['GH_TOKEN','GITHUB_TOKEN','GH_DEBUG','DEBUG','NODE_OPTIONS','NODE_PATH']: env.pop(name,None)
env.update(GIT_NO_LAZY_FETCH='1',WORLDATLAS_CONCURRENT_RESERVED_BYTES='0')
mem=int(next(row.split()[1] for row in pathlib.Path('/proc/meminfo').read_text().splitlines() if row.startswith('MemAvailable:')))*1024
cap=4*1024**3;assert mem-cap-2*1024**3>=768*1024**2
admission={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'execution_commit':head,'baseline_commit':before,'candidate_commit':after,'execution_checkout':str(repo),'command':command,'mem_available_bytes':mem,'job_reserved_bytes':cap,'parent_reserved_bytes':2*1024**3,'concurrent_reserved_bytes':0,'minimum_residual_bytes':768*1024**2,'wall_seconds':1200,'sampling_interval_ms':50,'scope':'Node continuous operands only; exact retained operand equality permits unchanged prior Python polygon result reuse.'}
(run/'admission.json').write_text(json.dumps(admission,indent=2)+'\n')
with (run/'stdout.log').open('x') as out,(run/'stderr.log').open('x') as err:
 p=subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True,env=env)
 start=time.monotonic();maximum=0;count=0;stop=None
 while p.poll() is None:
  total=0
  for d in pathlib.Path('/proc').iterdir():
   if not d.name.isdigit(): continue
   try:
    fields=(d/'stat').read_text().split(') ',1)[1].split()
    if int(fields[2])!=p.pid: continue
    total+=int((d/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
   except (FileNotFoundError,ProcessLookupError,PermissionError): pass
  maximum=max(maximum,total);count+=1
  if total>cap or time.monotonic()-start>1200:
   stop='aggregate-rss-limit' if total>cap else 'wall-timeout';os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(.05)
 try: code=p.wait(timeout=5)
 except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL);code=p.wait()
result={'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,3),'sampled_process_group_peak_rss_bytes':maximum,'sampling_interval_ms':50,'samples':count,'stopped':stop};(run/'process-group.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(code)
