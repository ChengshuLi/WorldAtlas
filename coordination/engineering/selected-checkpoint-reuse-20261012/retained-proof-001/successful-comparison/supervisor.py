import os,sys,time,json,subprocess,signal,pathlib,hashlib
out=pathlib.Path('/tmp/selected-checkpoint-proof-002');out.mkdir(exist_ok=False)
GiB=1024**3;reserve=2*GiB;headroom=2*GiB;peer=512*1024**2;floor=768*1024**2
mem=lambda:int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
available=mem();assert available>=reserve+headroom+peer+floor,(available,'insufficient admission')
script='/tmp/selected-checkpoint-real-proof.mjs';head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head=='41a9e8c003e57914f5fe03afe62f3ce177d46a93'
admission=dict(head=head,mem_available=available,group_reserved=reserve,parent_headroom=headroom,peer_reservation=peer,residual_floor=floor,script_sha256=hashlib.sha256(pathlib.Path(script).read_bytes()).hexdigest(),allowance=dict(phase_bytes=GiB,rss_bytes=GiB),wall_seconds=420)
(out/'probe.mjs').write_bytes(pathlib.Path(script).read_bytes());(out/'supervisor.py').write_bytes(pathlib.Path(__file__).read_bytes())
(out/'admission.json').write_text(json.dumps(admission,indent=2)+'\n');(out/'coverage').mkdir();(out/'profiles').mkdir()
env=dict(os.environ,PROOF_DIR=str(out),NODE_V8_COVERAGE=str(out/'coverage'),GIT_NO_LAZY_FETCH='1',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0')
start=time.monotonic();seen=set();peak=0;stop=None
with open(out/'stdout.log','w') as stdout,open(out/'stderr.log','w') as stderr:
 p=subprocess.Popen(['node','--cpu-prof','--cpu-prof-dir='+str(out/'profiles'),script],stdout=stdout,stderr=stderr,env=env,start_new_session=True)
 while p.poll() is None:
  group=[];total=0
  for pid in pathlib.Path('/proc').iterdir():
   if not pid.name.isdigit():continue
   try:
    stat=(pid/'stat').read_text().split(') ',1)[1].split()
    if int(stat[2])!=p.pid:continue
    rss=int(stat[21])*os.sysconf('SC_PAGE_SIZE');total+=rss;group.append(int(pid.name));seen.add(int(pid.name))
   except (OSError,ValueError,IndexError):pass
  peak=max(peak,total)
  if total>reserve:stop='aggregate process-group RSS exceeds admission'
  if mem()<floor:stop='host residual floor'
  if time.monotonic()-start>420:stop='wall deadline'
  if stop:os.killpg(p.pid,signal.SIGTERM);time.sleep(.5);os.killpg(p.pid,signal.SIGKILL) if p.poll() is None else None;break
  time.sleep(.05)
 rc=p.wait()
operating=dict(exit_code=rc,elapsed_seconds=time.monotonic()-start,peak_process_group_rss=peak,stop_reason=stop,owned_pids=sorted(seen),owned_processes_remaining=[])
(out/'operating.json').write_text(json.dumps(operating,indent=2)+'\n');print(json.dumps(operating));print((out/'stdout.log').read_text());print((out/'stderr.log').read_text()[-7000:]);sys.exit(rc)
