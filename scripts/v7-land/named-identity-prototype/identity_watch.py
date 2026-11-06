"""Run the pinned identity checker with process isolation and output bounds."""
import json,os,subprocess,time
TIMEOUT_SECONDS=120

def need(v,msg):
    if not v:raise ValueError(msg)

def run(checker_bytes,request):
    need(isinstance(checker_bytes,bytes) and len(checker_bytes)<=8*1024*1024,'invalid checker code')
    payload=json.dumps(request,sort_keys=True,separators=(',',':')).encode();need(len(payload)<=65536,'worker request too large')
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    child=subprocess.Popen(['/usr/bin/python3','-I','-c',checker_bytes.decode('utf-8')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    try:
        out,err=child.communicate(payload,timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        child.kill();child.communicate();raise ValueError('identity worker timed out')
    need(len(out)<=65536 and len(err)<=65536,'identity worker output too large')
    need(child.returncode==0,'identity worker failed: '+err.decode('utf-8','replace')[:500])
    result=json.loads(out);need(result.get('schema') in ('named-identity-worker-v1','named-identity-worker-v2'),'invalid identity worker result')
    return result['result']
