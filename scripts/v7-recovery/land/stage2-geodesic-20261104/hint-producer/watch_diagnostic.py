#!/usr/bin/python3
"""Observe the local diagnostic and bind its completion report.

RSS samples are informational only. A caller must require both zero exit and
the synced monitor.json before using results.
"""
import ctypes,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path

def bounded(path,limit):
 with open(path,'rb') as f:
  if os.fstat(f.fileno()).st_size>limit:raise ValueError('file exceeds bound')
  b=f.read(limit+1)
 if len(b)>limit:raise ValueError('file exceeds bound')
 return b
def rss(pid):
 with open(f'/proc/{pid}/status') as f:
  for line in f:
   if line.startswith('VmRSS:'):return int(line.split()[1])
 raise RuntimeError('process RSS unavailable')
def pdeath(parent):
 libc=ctypes.CDLL(None,use_errno=True)
 if libc.prctl(1,signal.SIGKILL,0,0,0)!=0:os._exit(126)
 if os.getppid()!=parent:os._exit(126)
def run(config,out,interval=.05):
 config=Path(config).resolve();out=Path(out).resolve()
 with open(config,'rb') as f:
  if os.fstat(f.fileno()).st_size>1048576:raise ValueError('request too large')
  data=f.read(1048577)
 if len(data)>1048576:raise ValueError('request too large')
 cfg=json.loads(data)
 if not 0<interval<=.1:raise ValueError('invalid sampling interval')
 if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):raise RuntimeError('pidfd watchdog unsupported')
 watcher=Path(__file__).resolve();watchhash=hashlib.sha256(bounded(watcher,1<<20)).hexdigest()
 env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
 parent=os.getpid();p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('run_diagnostic.py')),str(config),str(out)],preexec_fn=lambda:pdeath(parent),env=env,stdout=subprocess.DEVNULL)
 try:fd=os.pidfd_open(p.pid)
 except BaseException:
  try:p.kill()
  except ProcessLookupError:pass
  p.wait();raise
 peak=0;samples=0;reason=None
 try:
  while p.poll() is None:
   try:
    r=rss(p.pid);peak=max(peak,r);samples+=1
   except (OSError,RuntimeError):
    # A /proc entry can disappear between poll and sampling at normal exit.
    # Wait briefly for that exit; a still-running unobservable process fails.
    try:p.wait(timeout=.05)
    except subprocess.TimeoutExpired:reason='watchdog observation failed'
    if reason is None:break
   if reason:
    signal.pidfd_send_signal(fd,signal.SIGKILL);break
   time.sleep(interval)
  rc=p.wait()
 finally:os.close(fd)
 if reason or rc!=0 or not samples:raise RuntimeError(f'diagnostic not accepted: {reason or ("no process samples" if not samples else "child exit "+str(rc))}')
 report=out/'report.json'
 if not report.is_file():raise RuntimeError('diagnostic completion report missing')
 if hashlib.sha256(bounded(watcher,1<<20)).hexdigest()!=watchhash:raise RuntimeError('watchdog code changed')
 with open(config,'rb') as f:
  if os.fstat(f.fileno()).st_size>1048576 or f.read(1048577)!=data:raise RuntimeError('watchdog request changed')
 obj={'schema':'source-only-hints-watchdog-v1','status':'sampled-complete','diagnostic_report_sha256':hashlib.sha256(bounded(report,16<<20)).hexdigest(),'watchdog_sha256':watchhash,'peak_child_rss_kib':peak,'samples':samples,'sample_interval_seconds':interval,'limitation':'RSS sampling is informational and can miss transient peaks; source authentication and classification proof are independent.'}
 if os.statvfs(out).f_bavail*os.statvfs(out).f_frsize<cfg['minimum_free_bytes']:raise RuntimeError('disk reserve before monitor marker')
 tmp=out/'monitor.pending';final=out/'monitor.json';linked=False
 try:
  with open(tmp,'x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(tmp,final);linked=True;d=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d);os.unlink(tmp);d=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
 except Exception as e:
  if linked or final.exists():raise RuntimeError('monitor marker may exist; outcome requires inspection') from e
  raise
 return obj
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: watch_diagnostic.py REQUEST.json NEW_OUTPUT_DIR')
 print(json.dumps(run(sys.argv[1],sys.argv[2]),sort_keys=True))
