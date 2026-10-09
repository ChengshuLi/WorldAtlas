import pathlib,hashlib,subprocess,json,os,datetime
w=pathlib.Path.cwd();s=w/'.cache/side-acquisition';node='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
paths=['test/effective-geographic-regression.test.mjs','scripts/check-effective-geographic-regression.mjs','scripts/run-geographic-check.py','scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','src/ownership-codec.js','requirements.txt','package.json','.github/evidence-policy.json','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs']
sha=lambda b:hashlib.sha256(b).hexdigest()
def pins():
 return [{'path':p,'bytes':len((w/p).read_bytes()),'sha256':sha((w/p).read_bytes())} for p in paths]
head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip();assert head=='7e1ce1b71440201759fb3ab749d0786ebcbb2f93'
pre=pins();(s/'final-v6-source-before.json').write_text(json.dumps({'head':head,'files':pre},indent=2)+'\n')
env=dict(os.environ,WORLDATLAS_PREVENTION_CONTROLS=str(s/'final-fixture-objects-v6'))
with open(s/'final-focused-v6.log','xb') as f: r=subprocess.run([node,'--test','test/effective-geographic-regression.test.mjs'],stdout=f,stderr=subprocess.STDOUT,env=env)
post=pins();assert pre==post;assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==head
record={'head':head,'files':post,'exit_code':r.returncode,'pre_post_equal':pre==post,'command':[node,'--test','test/effective-geographic-regression.test.mjs'],'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':{'path':node,'bytes':pathlib.Path(node).stat().st_size,'sha256':sha(pathlib.Path(node).read_bytes()),'version':subprocess.check_output([node,'--version']).decode().strip()}}
(s/'final-v6-source-after.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
