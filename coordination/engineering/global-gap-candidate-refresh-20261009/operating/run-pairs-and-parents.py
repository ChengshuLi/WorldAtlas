import pathlib,subprocess,json,time,os,hashlib
W=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/cf40d9d594efb1cc1cb6158e6803afea25baf2d6058a2324fe45a0b23a03fb41/work');R=pathlib.Path(__file__).parent;Q='coordination/engineering/global-gap-candidate-refresh-20261009/';PY='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12';H=subprocess.check_output(['git','rev-parse','HEAD'],cwd=W).decode().strip();records=[]
commands=[(f'complete-pair-{i:02}',[Q+'compare.py','--ordinal',str(i)]) for i in range(1,8)]+[(f'parent-run-{r}',[Q+'refresh.py','parent']) for r in (1,2)]
for name,args in commands:
 env=dict(os.environ);env.pop('__PYVENV_LAUNCHER__',None);start=time.monotonic();out=R/(name+'.stdout.json');err=R/(name+'.stderr.log')
 with out.open('xb') as o,err.open('xb') as e:c=subprocess.run(['/usr/bin/time','-l',PY,'-I','-B',*args,'--head',H,'--destination',name],cwd=W,env=env,stdout=o,stderr=e,timeout=120)
 rec={'name':name,'execution_commit':H,'exit_code':c.returncode,'elapsed_seconds':time.monotonic()-start,'stdout_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256(err.read_bytes()).hexdigest()};records.append(rec);(R/'pair-parent-operating.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(rec),flush=True)
 if c.returncode:raise RuntimeError('Preserved terminal metadata failure')
 rec['publication']=json.load(open(out))
(R/'pair-parent-operating.json').write_text(json.dumps(records,indent=2)+'\n')
