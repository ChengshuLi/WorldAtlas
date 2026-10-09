import pathlib,subprocess,json,time,hashlib,os
W=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/cf40d9d594efb1cc1cb6158e6803afea25baf2d6058a2324fe45a0b23a03fb41/work');R=pathlib.Path(__file__).parent;head='7743d731c33215cc926ba84d967b31631abac34f';PYEX='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12';Q='coordination/engineering/global-gap-candidate-refresh-20261009/'
report=json.load(open(R/'post-review-stock-report.json'));growth=100*1024*1024;assert report['freeBytes']-growth>=report['limits']['minimumFree'] and report['checkoutBytes']+growth<=report['limits']['maximumCheckouts'];(R/'corrected-metadata-operating-admission.json').write_text(json.dumps({'stock_report':str(R/'post-review-stock-report.json'),'complete_future_physical_growth':growth,'source_head':head,'no_scientific_or_source_replay':True,'scope':'Two sequential bounded metadata catalog executions; no native/scientific runtime qualification'},indent=2)+'\n');records=[]
for run in (1,2):
 for ordinal in range(1,8):
  destination=f'corrected-run-{run}-leaf-{ordinal:02}';stdout=R/(destination+'.stdout.json');stderr=R/(destination+'.stderr.log');env=dict(os.environ);env.pop('__PYVENV_LAUNCHER__',None);start=time.monotonic()
  with stdout.open('xb') as out,stderr.open('xb') as err:
   completed=subprocess.run(['/usr/bin/time','-l',PYEX,'-I','-B',Q+'refresh.py','leaf','--head',head,'--index',str(ordinal),'--destination',destination],cwd=W,env=env,stdout=out,stderr=err,timeout=120)
  record={'run':run,'ordinal':ordinal,'head':head,'destination':Q+'vintages/'+destination,'exit_code':completed.returncode,'elapsed_seconds':time.monotonic()-start,'stdout_sha256':hashlib.sha256(stdout.read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256(stderr.read_bytes()).hexdigest()};records.append(record);(R/'corrected-leaf-operating.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(record),flush=True)
  if completed.returncode:raise RuntimeError('Preserved terminal leaf failure; no automatic retry')
  record['publication']=json.load(open(stdout))
(R/'corrected-leaf-operating.json').write_text(json.dumps(records,indent=2)+'\n')
