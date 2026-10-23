"""Actual fresh-output and immutable-method controls for the new USA adapters.
Usage: python check-preparation-boundaries.py REPO EXACT_METHOD_COMMIT FRESH_JSON
"""
import pathlib,json,hashlib,tempfile,subprocess,sys,os
assert len(sys.argv)==4
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P=W/'coordination/engineering/usa-repair-delivery-20261017';assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in(O,*O.parents))
methods=[('prepare-source-stage.py','source-stage-001'),('prepare-native-config.py','native-config-001'),('hold-unsupported-physical.py','native-config-002'),('prepare-qualified-scope.py','native-config-003'),('reconcile-authority.py','final-handoff-001')];results=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
def inventory(d):return{str(p.relative_to(d)):sha(p.read_bytes())for p in d.rglob('*')if p.is_file()}
with tempfile.TemporaryDirectory(prefix='usa-preparation-controls-',dir=str(O.parent))as temp:
 T=pathlib.Path(temp)
 for name,product in methods:
  program=P/'probes'/name;body=program.read_bytes();output=P/product;before=inventory(output)
  r=subprocess.run([sys.executable,str(program),str(W),C,str(output)],capture_output=True,timeout=15);assert r.returncode!=0 and inventory(output)==before
  results.append({'method':name,'case':'occupied-output','returncode':r.returncode,'original_inventory_unchanged':True,'stderr':r.stderr.decode()})
  link=T/(name+'.link');missing=T/(name+'.missing');link.symlink_to(missing)
  r=subprocess.run([sys.executable,str(program),str(W),C,str(link)],capture_output=True,timeout=15);assert r.returncode!=0 and link.is_symlink()and not missing.exists()
  results.append({'method':name,'case':'dangling-output-symlink','returncode':r.returncode,'link_and_missing_target_unchanged':True,'stderr':r.stderr.decode()})
  changed=T/name;changed.write_bytes(body+b'\n# Actual adverse executed-method drift.\n');fresh=T/(name+'.output')
  r=subprocess.run([sys.executable,str(changed),str(W),C,str(fresh)],capture_output=True,timeout=15);assert r.returncode!=0 and not fresh.exists()
  results.append({'method':name,'case':'executed-method-drift','returncode':r.returncode,'output_absent':True,'original_method_sha256':sha(body),'altered_method_sha256':sha(changed.read_bytes()),'stderr':r.stderr.decode()})
result={'kind':'executed-USA-preparation-boundary-controls','method_commit':C,'cases':len(results),'results':results,'limits':['These controls exercise fresh-output and immutable executed-method boundaries. They do not establish scientific source suitability, physical support or current selected delivery.']}
assert len(results)==15 and not O.exists()
with O.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print('Executed15 occupied-output, dangling-symlink and actual method-drift controls; all refused without changing original outputs.')
