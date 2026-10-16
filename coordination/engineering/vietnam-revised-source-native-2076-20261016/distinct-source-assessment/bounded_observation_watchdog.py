import json, subprocess, time, os, signal, pathlib, hashlib, sys
root=pathlib.Path(__file__).resolve().parent
script=root/sys.argv[1];prefix=sys.argv[2];limit=768*1024**2;deadline=120
free=os.statvfs('.').f_bavail*os.statvfs('.').f_frsize
assert free>10*1024**3+2*1024**2
mem={l.split(':')[0]:int(l.split()[1])*1024 for l in open('/proc/meminfo') if l.startswith(('MemTotal:','MemAvailable:'))};assert mem['MemAvailable']>limit*2
cfg={'kind':'bounded-independent-observation-prospective-admission','memory_rss_limit_bytes':limit,'wall_deadline_seconds':deadline,'poll_seconds':0.05,'free_bytes_before':free,'memory_available_before':mem,'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'command':['node','--max-old-space-size=512',str(script)],'scope':'Exact365 missing VNM708 native boundary/shared-interior proof; read-only operands; no global source-bank replay'}
admission=root/(prefix+'-admission.json');admission.write_text(json.dumps(cfg,indent=2)+'\n');start=time.monotonic();peak=0;reason=None
with open(root/(prefix+'-execution.log'),'w') as log:
 p=subprocess.Popen(cfg['command'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  rss=0
  for item in pathlib.Path('/proc').iterdir():
   if not item.name.isdigit():continue
   try:
    status=(item/'stat').read_text().split()
    if int(status[4])==p.pid:rss+=int((item/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
   except (OSError,ValueError,IndexError):pass
  peak=max(peak,rss)
  if rss>limit:reason='rss_limit'
  if time.monotonic()-start>deadline:reason='wall_deadline'
  if reason:os.killpg(p.pid,signal.SIGKILL);break
  time.sleep(.05)
 rc=p.wait()
receipt={'kind':'bounded-independent-observation-actual-execution','exit_code':rc,'enforced_memory_limit_bytes':limit,'observed_process_group_peak_rss_bytes':peak,'enforced_wall_deadline_seconds':deadline,'elapsed_seconds':time.monotonic()-start,'termination_reason':reason,'admission_sha256':hashlib.sha256(admission.read_bytes()).hexdigest(),'no_scientific_or_native_approval_implied':True}
(root/(prefix+'-execution.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print((root/(prefix+'-execution.log')).read_text());assert rc==0
