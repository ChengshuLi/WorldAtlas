"""Observe one stock direct CLI without an elapsed-time kill; never a cold fallback."""
import datetime, hashlib, json, os, pathlib, re, signal, subprocess, sys, time

p=pathlib.Path(__file__).resolve().parent
repo='/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/267133ee5fd33696ea7c63ec50cf78bebfb3c92f9a18ca0fb1c4db8be3e0c49e/review'
if len(sys.argv)!=3 or any(not re.fullmatch('[0-9a-f]{40}',v) for v in sys.argv[1:]):
    raise SystemExit('Pass the actual trusted code and canonical candidate commits explicitly')
trusted=sys.argv[1]
baseline='675cf6285b8d1cdaed3a7d8915146e7d45ce9052'
candidate=sys.argv[2]
node='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
entry=repo+'/coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs'
destination=p/'joint-products-001'
assert not destination.exists() and not (p/'joint-execution-001.json').exists()
assert sys.prefix!=sys.base_prefix and '__PYVENV_LAUNCHER__' not in os.environ
env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',
         GITHUB_REPOSITORY='ChengshuLi/WorldAtlas')
env.pop('WORLDATLAS_MEMORY_HEADROOM_BYTES',None);env.pop('WORLDATLAS_CONCURRENT_RESERVED_BYTES',None)
env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None)
credential_source='existing GH_TOKEN'
if not env.get('GH_TOKEN'):
    credential_source='existing gh auth token'
    auth=subprocess.run(['/usr/local/bin/gh','auth','token'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20)
    if auth.returncode==0 and auth.stdout.strip(): env['GH_TOKEN']=auth.stdout.decode().strip()
command=['/usr/bin/time','-l',node,entry,repo,trusted,baseline,candidate,str(destination),sys.executable]
at=datetime.datetime.now(datetime.timezone.utc).isoformat();started=time.monotonic();cancelled=False
with (p/'joint-acknowledgement-001.json').open('xb') as stdout,(p/'joint-time-stderr-001.log').open('xb') as stderr:
    child=subprocess.Popen(command,cwd=p,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
    def forward_cancellation(signum,frame):
        global cancelled
        cancelled=True
        if child.poll() is None:
            try: os.killpg(child.pid,signum)
            except ProcessLookupError: pass
    signal.signal(signal.SIGINT,forward_cancellation)
    signal.signal(signal.SIGTERM,forward_cancellation)
    status=child.wait()
elapsed=time.monotonic()-started
terminal=(p/'joint-time-stderr-001.log').read_text();peak=re.search(r'^\s*(\d+)\s+maximum resident set size',terminal,re.M)
ack=None
if status==0:
    try: ack=json.loads((p/'joint-acknowledgement-001.json').read_bytes())
    except (ValueError,OSError): pass
products=[]
for f in sorted(destination.iterdir()) if destination.exists() else []:
    digest=hashlib.sha256()
    with f.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    products.append(dict(path=str(f.relative_to(p)),bytes=f.stat().st_size,sha256=digest.hexdigest()))
result=dict(at_utc=at,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=command,
    actual_trusted_checkout=repo,actual_trusted_head=trusted,execution_acceptance_at_launch='accepted',baseline=baseline,candidate=candidate,
    exit_code=status,elapsed_seconds=elapsed,deadline_seconds=None,deadline_terminated=False,cancellation_requested=cancelled,
    direct_child_lifetime_peak_rss_bytes=int(peak.group(1)) if peak else None,
    actual_parent_python=sys.executable,application_memory_policy_configured=False,
    numeric_phase_or_rss_override=False,credential_source=credential_source,existing_credential_available=bool(env.get('GH_TOKEN')),
    credentials_created_or_changed=False,child_exited=True,reservation_released=True,emitted_inventory=products,
    joint_mode=ack.get('mode') if isinstance(ack,dict) else None,
    reuse_unavailable=ack.get('reuse_unavailable') if isinstance(ack,dict) else None,
    native_status=ack.get('native',{}).get('status') if isinstance(ack,dict) else None,
    public_action=False)
if status:
    tail=terminal[-7000:]
    if env.get('GH_TOKEN'):tail=tail.replace(env['GH_TOKEN'],'[REDACTED]')
    result['actual_stderr_tail']=tail
with (p/'joint-execution-001.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result),flush=True)
raise SystemExit(status if status>=0 else 1)
