import json,os,pathlib,signal,subprocess,time
root=pathlib.Path(__file__).resolve().parent
commands=[['node','--max-old-space-size=640',str(root/'check.mjs')]]
cap=1024**3
with open('/proc/meminfo') as f: mem={r.split(':')[0]:int(r.split()[1])*1024 for r in f if len(r.split())>=2}
if mem['MemAvailable']<cap+1024**3: raise RuntimeError('current reviewer reservation unavailable')
env=dict(os.environ)
for key in ('GH_TOKEN','GITHUB_TOKEN','NODE_OPTIONS','NODE_PATH'):env.pop(key,None)
env.update(TMPDIR=str(root),PYTHONDONTWRITEBYTECODE='1',GIT_NO_LAZY_FETCH='1')
env['PYTHON']='/workspace/scratch/127991fc8b8e/worldatlas-primary/.dependency-envs/python-3.12-x86_64-1c3f3b9598e474af751e25ff0839cbf5c4a9931a59b4ffaaff1a56c6e2f0e2c9/bin/python'
env['WORLDATLAS_TEST_PYTHON']=env['PYTHON']
records=[]
def scan(pgid):
    raw=subprocess.check_output(['ps','-eo','pid=,pgid=,rss='],text=True)
    return [list(map(int,r.split())) for r in raw.splitlines() if int(r.split()[1])==pgid]
for i,cmd in enumerate(commands):
    start=time.monotonic();peak=0;error=None;p=None;terminal=None;cleanup=None
    with (root/f'{i}.stdout').open('xb') as out,(root/f'{i}.stderr').open('xb') as err:
      try:
        p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True,env=env)
        while p.poll() is None:
          rows=scan(p.pid);peak=max(peak,sum(r[2]*1024 for r in rows))
          if peak>cap:raise RuntimeError('group memory exceeded reservation')
          if time.monotonic()-start>180:raise RuntimeError('control deadline exceeded')
          time.sleep(.05)
        terminal=scan(p.pid)
      except BaseException as e:error=repr(e)
      finally:
        if p is not None:
          try:os.killpg(p.pid,signal.SIGKILL)
          except ProcessLookupError:pass
          p.wait();cleanup=scan(p.pid)
    records.append(dict(command=cmd,returncode=p.returncode if p else None,error=error,seconds=time.monotonic()-start,peak_group_rss_bytes=peak,reservation_bytes=cap,terminal_group=terminal,cleanup_group=cleanup))
    (root/'operating.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records[-1]),flush=True)
    if error or p.returncode or terminal or cleanup:raise SystemExit(1)
