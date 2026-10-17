import pathlib,subprocess,tempfile,json,hashlib,os
D=pathlib.Path(__file__).parent;W=pathlib.Path((D/'workspace.txt').read_text().strip());P=W/'coordination/engineering/denmark-repair-delivery-20261017';H=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip();results=[]
for name in ['prepare-source-stage.py','screen-whole-foreign-bounds.mjs','reconcile-retained-periodic-negatives.mjs','prepare-native-config.mjs','reconcile-authority.py']:
 with tempfile.TemporaryDirectory(dir=D,prefix='control-') as td:
  t=pathlib.Path(td).absolute();sentinel=t/'sentinel';sentinel.write_bytes(b'preserve\n');occupied=t/'occupied';occupied.mkdir();(occupied/'sentinel').write_bytes(b'preserve\n');dangling=t/'dangling';dangling.symlink_to(t/'missing');p=P/'probes'/name;runner=[str((D.parent/'delete-batch-preserved/cache/validation-venv/bin/python').absolute())]if name.endswith('.py')else ['node']
  for kind,out in [('occupied',occupied),('dangling',dangling),('drift',t/'fresh')]:
   method=p
   if kind=='drift':method=t/name;method.write_bytes(p.read_bytes()+b'\n# drift\n'if name.endswith('.py')else p.read_bytes()+b'\n// drift\n')
   r=subprocess.run(runner+[str(method),str(W),H,str(out)],capture_output=True,env={**os.environ,'NODE_OPTIONS':'','NODE_PATH':''});assert r.returncode!=0 and sentinel.read_bytes()==b'preserve\n'and(occupied/'sentinel').read_bytes()==b'preserve\n'and dangling.is_symlink()and not(t/'fresh').exists()
   results.append({'method':name,'control':kind,'exit':r.returncode,'stderr':r.stderr.decode()[-2000:],'existing_bytes_preserved':True,'no_fresh_output':True})
(P/'source-review/writer-controls.json').write_text(json.dumps({'executions':results,'count':len(results)},indent=2)+'\n');print('15 actual writer refusals; all sentinels unchanged; no fresh products')
