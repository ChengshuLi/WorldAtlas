"""Run the pinned named-identity checker in an isolated Python process."""
import json, os, subprocess

def run(checker_bytes, request):
    if not isinstance(checker_bytes, bytes) or len(checker_bytes) > 8 * 1024 * 1024:
        raise ValueError('invalid checker code')
    payload = json.dumps(request, sort_keys=True, separators=(',', ':')).encode()
    if len(payload) > 65536:
        raise ValueError('worker request too large')
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    child = subprocess.run(['/usr/bin/python3', '-I', '-c', checker_bytes.decode('utf-8')], input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if len(child.stdout) > 65536 or len(child.stderr) > 65536:
        raise ValueError('identity worker output too large')
    if child.returncode:
        raise ValueError('identity worker failed: ' + child.stderr.decode('utf-8', 'replace')[:500])
    result = json.loads(child.stdout)
    if result.get('schema') != 'named-identity-worker-v1':
        raise ValueError('worker result invalid')
    return result['result']
