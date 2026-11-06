"""Independent same-namespace child RSS and host MemAvailable watchdog."""
import json,os,subprocess,time
POLL_SECONDS=.05
TIMEOUT_SECONDS=120

def need(v,msg):
    if not v:raise ValueError(msg)
def child_rss(pid):
    try:
        with open(f'/proc/{pid}/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):return int(line.split()[1])
    except FileNotFoundError:return None
    return None

def run(checker_bytes,request,available):
    need(isinstance(checker_bytes,bytes) and len(checker_bytes)<=8*1024*1024,'invalid checker code')
    payload=json.dumps(request,sort_keys=True,separators=(',',':')).encode();need(len(payload)<=65536,'worker request too large')
    initial=available()
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    child=subprocess.Popen(['/usr/bin/python3','-I','-c',checker_bytes.decode('utf-8')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    minimum=initial;peak_observed=0;started=time.monotonic();reason=None
    try:
        child.stdin.write(payload);child.stdin.close()
        while child.poll() is None:
            mem=available();minimum=min(minimum,mem);rss=child_rss(child.pid);peak_observed=max(peak_observed,rss or 0)
            if time.monotonic()-started>TIMEOUT_SECONDS:reason='identity worker timed out';break
            time.sleep(POLL_SECONDS)
        if reason:
            child.terminate()
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            raise ValueError(reason)
        final_available=available();minimum=min(minimum,final_available)
        out=child.stdout.read(65537);err=child.stderr.read(65537);need(len(out)<=65536 and len(err)<=65536,'identity worker output too large')
        need(child.returncode==0,'identity worker failed: '+err.decode('utf-8','replace')[:500])
        result=json.loads(out);peak=result.get('peak_rss_kib');need(result.get('schema')=='named-identity-worker-v1','worker result invalid')
        return {'result':result['result'],'memory_monitor':{'host_floor_kib':None,'initial_available_kib':initial,'minimum_sampled_available_kib':minimum,'rss_cap_kib':None,'maximum_sampled_rss_kib':peak_observed,'worker_reported_peak_rss_kib':peak,'poll_seconds':POLL_SECONDS,'limitation':'Memory samples are observational only; worker-reported RSS is telemetry.'}}
    finally:
        if child.poll() is None:child.kill();child.wait()
        for f in (child.stdin,child.stdout,child.stderr):
            if f and not f.closed:f.close()
