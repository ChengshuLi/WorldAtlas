#!/usr/bin/env /usr/bin/python3
"""Gated whole-group watchdog; no candidate selection or scientific approval.

Linux only. A guardian owns the process group and kills it if the monitor dies.
Sampling may miss brief spikes; escaped children or simultaneous monitor and
guardian failure are outside this guarantee. Failure can leave partial output.
"""
import argparse,ctypes,hashlib,json,os,select,signal,subprocess,sys,threading,time
from pathlib import Path

def need(v,msg):
 if not v:raise ValueError(msg)
def memory_available():
 with open('/proc/meminfo') as f:
  for line in f:
   if line.startswith('MemAvailable:'):return int(line.split()[1])
 raise RuntimeError('MemAvailable unavailable')
def group_rss(pgid,on_retry=lambda known_rss:None):
 total=members=0
 with os.scandir('/proc') as entries:
  for e in entries:
   if not e.name.isdigit():continue
   try:
    for attempt in range(51):
     stat=Path(e.path,'stat').read_text();tail=stat[stat.rfind(')')+2:].split()
     if int(tail[2])!=pgid or tail[0]=='Z':break
     with open(Path(e.path,'status')) as f:rss=next((int(x.split()[1]) for x in f if x.startswith('VmRSS:')),None)
     if rss is not None:
      total+=rss;members+=1;break
     if attempt<50:on_retry(total);time.sleep(.005)
     else:raise RuntimeError('group RSS unavailable after retries')
   except (FileNotFoundError,ProcessLookupError):continue
   except (PermissionError,IndexError,ValueError) as x:raise RuntimeError('group observation failed') from x
 return total,members

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def exited_unreaped(pid):return os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None
def die_with_parent():
 original=os.getppid();libc=ctypes.CDLL(None,use_errno=True)
 if libc.prctl(1,signal.SIGKILL,0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_SET_PDEATHSIG failed')
 if os.getppid()!=original or original==1:raise RuntimeError('monitor parent already gone')

def run(command,log_dir,disk_path,disk_floor,max_rss,timeout,interval=.05):
 die_with_parent();guardian=Path(__file__).with_name('guardian.py').resolve();selfpath=Path(__file__).resolve();log=Path(log_dir).resolve();diskpath=Path(disk_path).resolve()
 need(command and len(command)>=2 and log.parent.is_dir() and not log.exists(),'bad command or log directory')
 need(all(type(x) is int and x>0 for x in (disk_floor,max_rss)) and 0<timeout<=86400 and 0<interval<=.1,'invalid guard limits')
 need(hasattr(os,'pidfd_open') and hasattr(os,'waitid') and hasattr(os,'WNOWAIT'),'Linux pidfd/waitid unavailable')
 need(threading.active_count()==1 and signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'dedicated monitor required')
 def free():
  v=os.statvfs(diskpath);return v.f_bavail*v.f_frsize
 need(free()>=disk_floor,'disk floor before launch')
 own_sha=digest(selfpath);guardian_sha=digest(guardian);log.mkdir(exist_ok=False);fd=os.open(log.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 cr,cw=os.pipe();sr,sw=os.pipe();p=pidfd=None;reaped=finished=started=driver_started=False;start=time.monotonic();minimum=memory_available();maximum=samples=0;buffer=b''
 def retry_guard(known_rss):
  nonlocal minimum,maximum
  available=memory_available();minimum=min(minimum,available);maximum=max(maximum,known_rss)
  if free()<disk_floor:raise RuntimeError('disk floor')
  if known_rss>max_rss:raise RuntimeError('group RSS limit')
  if time.monotonic()-start>timeout:raise RuntimeError('time limit')
 try:
  with (log/'worker.log').open('xb') as worker:
   p=subprocess.Popen([sys.executable,str(guardian),str(cr),str(sw),*command],start_new_session=True,pass_fds=(cr,sw),stdout=subprocess.DEVNULL,stderr=worker,close_fds=True)
   os.close(cr);cr=None;os.close(sw);sw=None;pidfd=os.pidfd_open(p.pid)
   while not finished:
    if exited_unreaped(p.pid):raise RuntimeError('guardian exited unexpectedly')
    available=memory_available();rss,members=group_rss(p.pid,retry_guard);minimum=min(minimum,available);maximum=max(maximum,rss);samples+=1
    if not members:raise RuntimeError('guardian group unavailable')
    if free()<disk_floor:raise RuntimeError('disk floor')
    if rss>max_rss:raise RuntimeError('group RSS limit')
    if time.monotonic()-start>timeout:raise RuntimeError('time limit')
    ready,_,_=select.select([sr],[],[],interval)
    if ready:
     chunk=os.read(sr,4096)
     if not chunk:raise RuntimeError('guardian status pipe closed')
     buffer+=chunk;need(len(buffer)<=65536,'guardian status overflow')
     while b'\n' in buffer:
      line,buffer=buffer.split(b'\n',1);ev=json.loads(line);kind=ev.get('event')
      if kind=='ready':
       need(not started and ev.get('guardian')==p.pid and ev.get('group')==p.pid,'guardian identity mismatch');os.write(cw,b'START\n');started=True
      elif kind=='started':
       need(started and not driver_started and type(ev.get('driver_pid')) is int and ev['driver_pid']>0,'invalid driver event');driver_started=True
      elif kind=='done':
       need(started and driver_started and type(ev.get('returncode')) is int and ev['returncode']==0,'worker failed')
       _,live=group_rss(p.pid,retry_guard);need(live==1,'worker exited with live descendants');os.write(cw,b'RELEASE\n');finished=True
      else:raise RuntimeError('unknown guardian event')
   deadline=time.monotonic()+10
   while not exited_unreaped(p.pid):
    if time.monotonic()>deadline:raise RuntimeError('guardian release timeout')
    time.sleep(.02)
   _,live=group_rss(p.pid,retry_guard);need(live==0,'live group after guardian release');rc=p.wait();reaped=True;need(rc==0 and samples>0,'guardian failed');worker.flush();os.fsync(worker.fileno())
 finally:
  uncertain=False
  if p is not None and not reaped:
   try:os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT);owned=True
   except ChildProcessError:owned=False
   if owned:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    try:p.wait(timeout=5)
    except (subprocess.TimeoutExpired,ChildProcessError):uncertain=True
   else:uncertain=True
  if pidfd is not None:os.close(pidfd)
  for fd in (cr,cw,sr,sw):
   if fd is not None:
    try:os.close(fd)
    except OSError:pass
  if uncertain:raise RuntimeError('guardian cleanup uncertain; inspect before retry')
 need(digest(selfpath)==own_sha and digest(guardian)==guardian_sha,'watchdog code changed')
 result={'schema':'sampled-process-group-watchdog-v1','status':'complete','watchdog_sha256':own_sha,'guardian_sha256':guardian_sha,'minimum_available_kib':minimum,'memory_floor_kib':None,'peak_group_rss_kib':maximum,'group_rss_limit_kib':max_rss,'disk_floor_bytes':disk_floor,'timeout_seconds':timeout,'elapsed_seconds':round(time.monotonic()-start,3),'samples':samples,'sample_interval_seconds':interval,'limitations':['Sampling can miss short peaks; an unobservable process may delay an RSS sample by up to 0.25 seconds before failure. Escaped children and simultaneous monitor/guardian failure are not contained.','A successful guard is not scientific approval or input provenance.']}
 with (log/'watchdog.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(log,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--log-dir',required=True);p.add_argument('--disk-path',required=True);p.add_argument('--disk-floor-bytes',type=int,required=True);p.add_argument('--group-rss-kib',type=int,required=True);p.add_argument('--timeout',type=float,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();cmd=a.command[1:] if a.command and a.command[0]=='--' else a.command
 try:print(json.dumps(run(cmd,a.log_dir,a.disk_path,a.disk_floor_bytes,a.group_rss_kib,a.timeout),sort_keys=True))
 except Exception as e:print('watchdog failure; inspect outputs before retry: '+str(e),file=sys.stderr);sys.exit(1)
