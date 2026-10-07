"""Record actual bounded control commands separately from world measurements."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
CASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--science-commit',required=True);parser.add_argument('--recorder-commit',required=True)
args=parser.parse_args()
relative=str(Path(__file__).resolve().relative_to(ROOT))
actual=Path(__file__).read_bytes()
if actual!=subprocess.check_output(['git','-C',str(ROOT),'show',args.recorder_commit+':'+relative]):raise ValueError('Unbound recorder')
node='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
commands=[([sys.executable,'-B','test/geographic-regression.py'],40),
          ([sys.executable,'-B','test/geographic-adjudication.py'],14),
          ([sys.executable,'-B',str(CASE/'controls.py'),'--code-commit',args.science_commit],9),
          ([node,'--test','--test-reporter=tap','test/trusted-geography-check.test.mjs','test/merge-integration.test.mjs','test/merge-integration-entrypoint.test.mjs'],51)]
out=CASE/'verification';out.mkdir(exist_ok=True)
records=[]
for ordinal,(command,count) in enumerate(commands):
    started=datetime.now(timezone.utc).isoformat()
    result=subprocess.run(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHON=sys.executable),capture_output=True)
    raw=result.stdout+result.stderr
    name=f'actual-controls-{ordinal:02d}.log';(out/name).write_bytes(raw)
    if result.returncode!=0:raise ValueError('Actual control command failed: '+name)
    expected=(f'Ran {count} tests'.encode() if ordinal<3 else f'# pass {count}'.encode())
    if expected not in raw:raise ValueError('Unexpected actual test count: '+name)
    records.append({'command':command,'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),'exit_code':result.returncode,
                    'passed_tests':count,'log_path':str((out/name).relative_to(ROOT)),'log_sha256':hashlib.sha256(raw).hexdigest(),'log_bytes':len(raw)})
for kind in ['positive-control','negative-control']:
    receipt={'method_id':'prepared-domain-validation','kind':kind,'outcome':'passed','science_commit':args.science_commit,
             'recorder_commit':args.recorder_commit,'actual_recorder_sha256':hashlib.sha256(actual).hexdigest(),'actual_commands':records,
             'limits':['Actual small fixtures and production custody/CLI tests; these receipts are not worldwide geometry executions or factual approvals.']}
    (out/(kind+'.json')).write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps({'outcome':'passed','actual_commands':len(records),'actual_passed_tests':sum(c for _,c in commands)}))
