#!/usr/bin/env /usr/bin/python3
"""Monitor a fresh component builder Linux process group; emit acceptance marker last.

The guardian holds the process-group ID and kills its group if this monitor
dies. Sampling can miss short spikes. A process that deliberately leaves the
group, or simultaneous guardian/monitor failure, is outside this guarantee.
Any failure leaves unaccepted output/checkpoints; inspect before retry.
"""
import hashlib,json,os,select,signal,subprocess,sys,threading,time
from pathlib import Path

def need(v,msg):
 if not v:raise ValueError(msg)
def memory_available():
 with open('/proc/meminfo') as f:
  for line in f:
   if line.startswith('MemAvailable:'):return int(line.split()[1])
 raise RuntimeError('MemAvailable unavailable')
def group_rss(pgid):
 total=0;members=0
 with os.scandir('/proc') as entries:
  for entry in entries:
   if not entry.name.isdigit():continue
   try:
    for attempt in range(4):
     stat=Path(entry.path,'stat').read_text();tail=stat[stat.rfind(')')+2:].split();state=tail[0];group=int(tail[2])
     if group!=pgid or state=='Z':break
     rss=None
     with open(Path(entry.path,'status')) as f:
      for line in f:
       if line.startswith('VmRSS:'):rss=int(line.split()[1]);break
     if rss is not None:total+=rss;members+=1;break
     # Linux can transiently omit VmRSS during process teardown or exec.
     # Re-read group/state before each retry; an unobservable live process
     # that remains after this bounded window still fails closed.
     if attempt<3:time.sleep(.005)
     else:raise RuntimeError('process group RSS unavailable')
   except (FileNotFoundError,ProcessLookupError):continue
   except (PermissionError,IndexError,ValueError) as e:raise RuntimeError('process group observation failed') from e
 return total,members
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def exited_unreaped(pid):
 return os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None

def run(config,work,output,max_tree_rss_kib,*,resume=False,interval=.05):
 config,work,output=map(lambda x:Path(x).resolve(),(config,work,output));driver=Path(__file__).with_name('build_components.py').resolve();watcher=Path(__file__).resolve();guardian=Path(__file__).with_name('guardian.py').resolve()
 with open(config,'rb') as f:
  need(os.fstat(f.fileno()).st_size<=1048576,'config too large');raw=f.read(1048577)
 need(len(raw)<=1048576,'config too large');cfg=json.loads(raw);controls=cfg.get('controls',{});floor=controls.get('minimum_memory_kib');disk=controls.get('minimum_free_bytes')
 need(type(floor) is int and floor>0 and type(disk) is int and disk>0 and type(max_tree_rss_kib) is int and max_tree_rss_kib>0 and 0<interval<=.1,'invalid watchdog limits')
 need(not output.exists() and output.parent.is_dir() and work.parent.is_dir() and os.stat(work.parent).st_dev==os.stat(output.parent).st_dev,'fresh output and same-filesystem work required');need(hasattr(os,'pidfd_open') and hasattr(os,'waitid') and hasattr(os,'WNOWAIT'),'Linux pidfd/waitid unavailable')
 need(threading.active_count()==1 and signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'dedicated single-threaded monitor with default SIGCHLD required')
 need(memory_available()>=floor and os.statvfs(output.parent).f_bavail*os.statvfs(output.parent).f_frsize>=disk,'resource floor before launch')
 self_sha=digest(watcher);guardian_sha=digest(guardian);driver_sha=digest(driver);config_sha=hashlib.sha256(raw).hexdigest();env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
 control_r,control_w=os.pipe();status_r,status_w=os.pipe();p=None;pidfd=None;finished=False;started=False;driver_started=False;normal=False;reaped=False
 try:
  cmd=[sys.executable,str(driver),str(config),str(work),str(output)]+(['--resume'] if resume else [])
  p=subprocess.Popen([sys.executable,str(guardian),str(control_r),str(status_w),*cmd],start_new_session=True,pass_fds=(control_r,status_w),env=env,stdout=subprocess.DEVNULL,close_fds=True)
  os.close(control_r);control_r=None;os.close(status_w);status_w=None
  # All setup errors below kill the still-unreaped guardian group.
  pidfd=os.pidfd_open(p.pid);minimum=memory_available();maximum=samples=0;buffer=b'';deadline=time.monotonic()+30
  while not finished:
   if exited_unreaped(p.pid):raise RuntimeError('guardian exited unexpectedly; inspect output')
   available=memory_available();rss,members=group_rss(p.pid);minimum=min(minimum,available);maximum=max(maximum,rss)
   if not members:raise RuntimeError('live guardian group not observed')
   samples+=1
   if available<floor:raise RuntimeError('host memory floor')
   if any(os.statvfs(p).f_bavail*os.statvfs(p).f_frsize<disk for p in (work.parent,output.parent)):raise RuntimeError('disk reserve floor')
   if rss>max_tree_rss_kib:raise RuntimeError('process group RSS limit')
   ready,_,_=select.select([status_r],[],[],interval)
   if ready:
    chunk=os.read(status_r,4096)
    if not chunk:raise RuntimeError('guardian status pipe closed')
    buffer+=chunk
    need(len(buffer)<=65536,'guardian status overflow')
    while b'\n' in buffer:
     line,buffer=buffer.split(b'\n',1);event=json.loads(line);kind=event.get('event')
     if kind=='ready':
      need(not started and event.get('guardian')==p.pid and event.get('group')==p.pid,'guardian identity mismatch')
      # The driver cannot execute until the monitor has checked a live group.
      os.write(control_w,b'START\n');started=True
     elif kind=='started':
      need(started and not driver_started and type(event.get('driver_pid')) is int and event['driver_pid']>0,'invalid driver start event');driver_started=True
     elif kind=='done':
      need(started and driver_started and type(event.get('returncode')) is int,'invalid driver completion event')
      if event['returncode']!=0:raise RuntimeError('driver exit '+str(event['returncode']))
      _,live=group_rss(p.pid)
      if live!=1:raise RuntimeError('driver exited with live process-group members')
      os.write(control_w,b'RELEASE\n');finished=True
     else:raise RuntimeError('unexpected guardian event')
   if not started and time.monotonic()>deadline:raise RuntimeError('guardian startup timeout')
  # Keep the guardian unreaped until it exits and the group is confirmed empty.
  deadline=time.monotonic()+10
  while not exited_unreaped(p.pid):
   if time.monotonic()>deadline:raise RuntimeError('guardian release timeout')
   time.sleep(.02)
  _,live=group_rss(p.pid)
  if live:raise RuntimeError('live group members after guardian release')
  rc=p.wait();reaped=True;need(rc==0 and samples>0,'guardian did not exit cleanly');normal=True
 finally:
  cleanup_uncertain=False
  if p is not None and not reaped:
   # A dedicated process with default SIGCHLD has no competing reaper. Still
   # revalidate waitable ownership before signaling the reserved PID/PGID.
   try:os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT);owned=True
   except ChildProcessError:owned=False
   if owned:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    try:p.wait(timeout=5)
    except (subprocess.TimeoutExpired,ChildProcessError):cleanup_uncertain=True
   else:cleanup_uncertain=True
  if pidfd is not None:os.close(pidfd)
  for fd in (control_r,control_w,status_r,status_w):
   if fd is not None:
    try:os.close(fd)
    except OSError:pass
  if cleanup_uncertain:raise RuntimeError('guardian ownership or cleanup uncertain; inspect before retry')
 report=output/'report.json';need(report.is_file(),'component report missing; inspect output');need(digest(watcher)==self_sha and digest(guardian)==guardian_sha and digest(driver)==driver_sha and digest(config)==config_sha,'watchdog input or code changed')
 with open(report,'rb') as f:
  need(os.fstat(f.fileno()).st_size<=16*1024*1024,'stage-2 report too large');result_report=json.load(f)
 need(result_report.get('schema')=='fresh-physical-components-report-v1' and result_report.get('status')=='research-awaiting-monitor' and result_report.get('publishable') is False and result_report.get('config_sha256')==config_sha and result_report.get('driver_sha256')==driver_sha,'component report does not bind watched driver/config')
 result={'schema':'fresh-physical-components-watchdog-v1','status':'sampled-complete','report_sha256':digest(report),'config_sha256':config_sha,'driver_sha256':driver_sha,'watchdog_sha256':self_sha,'guardian_sha256':guardian_sha,'minimum_available_kib':minimum,'minimum_memory_kib':floor,'peak_process_group_rss_kib':maximum,'maximum_process_group_rss_kib':max_tree_rss_kib,'samples':samples,'sample_interval_seconds':interval,'limitation':'Sampling can miss short-lived peaks; escaped children and simultaneous monitor/guardian failure are not contained. Independent scientific and provenance review remains required.'}
 need(memory_available()>=floor and os.statvfs(output).f_bavail*os.statvfs(output).f_frsize>=disk,'resource floor before monitor marker')
 tmp=output/'monitor.pending';final=output/'monitor.json';linked=False
 try:
  with open(tmp,'x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(tmp,final);linked=True;fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);os.unlink(tmp);fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 except Exception as e:
  if linked or final.exists():raise RuntimeError('monitor marker may exist; inspect before retry') from e
  raise
 return result

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('work');p.add_argument('output');p.add_argument('maximum_process_group_rss_kib',type=int);p.add_argument('--resume',action='store_true');a=p.parse_args()
 try:print(json.dumps(run(a.config,a.work,a.output,a.maximum_process_group_rss_kib,resume=a.resume),sort_keys=True))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
