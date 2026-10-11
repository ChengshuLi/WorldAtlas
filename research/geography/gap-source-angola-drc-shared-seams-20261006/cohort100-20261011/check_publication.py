"""Exercise actual entry-point early refusals; no source or GIS reconstruction."""
import hashlib,json,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
VINTAGES=HERE.parent/'vintages'
HEAD=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
script=pathlib.Path(__file__).relative_to(ROOT).as_posix()
assert pathlib.Path(__file__).read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',HEAD+':'+script])
rows=[]
for producer,command,occupied_reason,symlink_reason in [
 ('current-neighbors',['node',str(HERE/'bind_current_neighbors.mjs')],'Occupied destination','Symlink destination'),
 ('handoff',[sys.executable,str(HERE/'build_handoff.py')],'Fresh run directory already exists','Symlink in output path')]:
 for kind,reason in [('occupied',occupied_reason),('dangling-symlink',symlink_reason)]:
  name='cohort100-control-'+producer+'-'+kind
  dest=VINTAGES/name; target=VINTAGES/(name+'-absent-target')
  assert not dest.exists() and not dest.is_symlink() and not target.exists()
  if kind=='occupied':
   dest.mkdir();(dest/'sentinel').write_bytes(b'unchanged custody sentinel\n')
  else:dest.symlink_to(target.name)
  before=(dest/'sentinel').read_bytes() if kind=='occupied' else dest.readlink().as_posix()
  try:
   result=subprocess.run(command+[HEAD,name],cwd=ROOT,capture_output=True,text=True)
   assert result.returncode!=0 and reason in result.stderr,(producer,kind,result.returncode,result.stderr)
   after=(dest/'sentinel').read_bytes() if kind=='occupied' else dest.readlink().as_posix()
   assert after==before and not target.exists()
   rows.append({'producer':producer,'case':kind,'exit_code':result.returncode,'expected_refusal':reason,'sentinel_preserved':True,'unexpected_target_created':False})
  finally:
   if kind=='occupied':(dest/'sentinel').unlink();dest.rmdir()
   else:dest.unlink()
print(json.dumps({'execution_commit':HEAD,'controls':rows,'passed':len(rows),'scientific_operations':0},sort_keys=True))
