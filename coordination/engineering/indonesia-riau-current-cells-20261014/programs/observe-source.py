"""Observe one finite admitted source run through the existing standalone route."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
prep=Path(__file__).resolve().parent
node='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
# This observer is already resident while the admission observes free memory.
with (prep/'source-admission-001.stdout.log').open('xb') as log:
    admitted=subprocess.run([node,str(prep/'admit-source.mjs'),sys.argv[1],str(prep)],stdin=subprocess.DEVNULL,stdout=log,check=False)
assert admitted.returncode==0, 'Fresh source admission failed before producer starts'
admission=json.loads((prep/'source-admission-001.json').read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
assert time.time()-admission['observed_unix_seconds']<60
assert sha((prep/'check-riau-sources.py').read_bytes())==admission['program_sha256']
assert sha(Path(__file__).read_bytes())==admission['observer_sha256']
out=prep/'source-run-001';out.mkdir(exist_ok=False)
stdout=prep/'source-run-001.stdout.log';stderr=prep/'source-run-001.stderr.log'
assert not stdout.exists() and not stderr.exists()
python='/Users/chengshuli/.cache/worldatlas-python-envs/requirements-a911b499659c266373447ffef081b16be803c5b5b2cd22889cc5c7a22811c0ae-python-3.12.14-macos-arm64/bin/python'
env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',PYTHONDONTWRITEBYTECODE='1')
command=['/usr/bin/time','-l',python,'-I','-B',str(prep/'check-riau-sources.py')]
started=time.monotonic()
with stdout.open('xb') as output,stderr.open('xb') as errors:
    run=subprocess.run(command,env=env,cwd=sys.argv[1],stdin=subprocess.DEVNULL,stdout=output,stderr=errors,check=False)
elapsed=time.monotonic()-started
text=stderr.read_text(errors='replace')
peaks=[int(line.split()[0]) for line in text.splitlines() if 'maximum resident set size' in line]
products=[]
for p in [stdout,stderr,*sorted(out.iterdir())]:
    if p.is_file():products.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
receipt={'version':1,'command':command,'cwd':sys.argv[1],'exit_code':run.returncode,'elapsed_seconds':elapsed,'external_darwin_peak_rss_bytes':peaks[-1] if peaks else None,'fresh_admission':admission,'products':products,'limits':['External time observes process peak RSS; no aggregate process-tree RSS or enforced termination claim.','No optional supervisor, process-group operation or denied API is used. Planned limits are checked at source boundaries and measured after completion.','Source-prerequisite evidence is not physical/native/current-owner-zero/selected-consumer or accepted repair proof.']}
(prep/'source-run-001.entry-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['fresh_admission','products']}))
sys.exit(run.returncode)
