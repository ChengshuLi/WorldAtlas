"""Exercise the actual Argentina adapters' non-mutating refusal boundaries.
Usage: python check-preparation-boundaries.py REPO EXACT_METHOD_COMMIT FRESH_JSON
"""
import pathlib,json,hashlib,tempfile,subprocess,sys,os
assert len(sys.argv)==4
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P=W/'coordination/engineering/argentina-repair-delivery-20261017'
assert len(C)==40 and all(c in'0123456789abcdef'for c in C)
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in(O,*O.parents))
methods=[('prepare-source-stage.py','source-stage-001'),('extract-prior-family.py','source-review/prior-family-001'),('measure-prior-family-keys.mjs','source-review/prior-family-keys-001'),('prepare-source-scope.py','source-review/complete-scope-002'),('corroborate-neighbor-contacts.py','source-review/neighbor-points-002'),('prepare-native-config.py','native-config-001'),('prepare-qualified-scope.py','native-config-002'),('verify-qualified-evidence.py','source-review/qualified-evidence-preservation-001'),('reconcile-authority.py','final-handoff-001')];results=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'};env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None)
def raw(p):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',C+':coordination/engineering/argentina-repair-delivery-20261017/'+p],env=env,timeout=15)
assert subprocess.check_output(['git','-C',str(W),'cat-file','-t',C],env=env).strip()==b'commit'
assert raw('probes/check-preparation-boundaries.py')==pathlib.Path(__file__).read_bytes()
for name,_ in methods:assert raw('probes/'+name)==(P/'probes'/name).read_bytes()
def inventory(d):return{str(p.relative_to(d)):sha(p.read_bytes())for p in d.rglob('*')if p.is_file()}
def run(name,program,out):return subprocess.run(['node'if name.endswith('.mjs')else sys.executable,str(program),str(W),C,str(out)],capture_output=True,timeout=15,env=env)
with tempfile.TemporaryDirectory(prefix='argentina-preparation-controls-',dir=str(O.parent))as temp:
 T=pathlib.Path(temp)
 for name,product in methods:
  program=P/'probes'/name;body=program.read_bytes();output=P/product;before=inventory(output);assert before
  r=run(name,program,output);assert r.returncode!=0 and inventory(output)==before
  results.append({'method':name,'case':'occupied-output','returncode':r.returncode,'materialized_output_inventory_unchanged':True,'stderr':r.stderr.decode()})
  link=T/(name+'.link');missing=T/(name+'.missing');link.symlink_to(missing)
  r=run(name,program,link);assert r.returncode!=0 and link.is_symlink()and not missing.exists()
  results.append({'method':name,'case':'dangling-output-symlink','returncode':r.returncode,'link_and_missing_target_unchanged':True,'stderr':r.stderr.decode()})
  changed=T/name;changed.write_bytes(body+(b'\n// Actual adverse executed-method drift.\n'if name.endswith('.mjs')else b'\n# Actual adverse executed-method drift.\n'));fresh=T/(name+'.output')
  r=run(name,changed,fresh);assert r.returncode!=0 and not fresh.exists()and b'CalledProcessError'not in r.stderr and b'fatal:'not in r.stderr
  assert (b'Executed method drift'in r.stderr if name.endswith('.mjs')else b'AssertionError'in r.stderr)
  results.append({'method':name,'case':'executed-method-drift','returncode':r.returncode,'output_absent':True,'original_method_sha256':sha(body),'altered_method_sha256':sha(changed.read_bytes()),'stderr':r.stderr.decode()})
result={'kind':'executed-Argentina-preparation-boundary-controls','method_commit':C,'cases':len(results),'results':results,'limits':['Actual outputs and an existing exact method commit make these controls nonvacuous.','These controls exercise fresh-output and immutable executed-method boundaries; they do not establish scientific source suitability, physical support or selected delivery.']}
assert len(results)==27 and not O.exists()
with O.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print('Executed 27 occupied-output, dangling-symlink and actual method-drift controls; all refused without changing original outputs.')
