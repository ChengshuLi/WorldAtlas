"""Retain one real full execution's exact command, UTC window and outcome."""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

import producer

parser=argparse.ArgumentParser()
parser.add_argument('--execution',required=True)
parser.add_argument('--out',type=pathlib.Path,required=True)
parser.add_argument('--receipt',type=pathlib.Path,required=True)
parser.add_argument('--log',type=pathlib.Path,required=True)
args=parser.parse_args()
repo=producer.HERE.parents[2]
closure=producer.freeze_guard(repo,args.execution)
for path in (args.out,args.receipt,args.log):
    if not path.is_absolute() or '..' in path.parts or path.exists() or path.is_symlink():
        raise ValueError('Require fresh absolute ordinary execution paths')
    if not path.resolve().is_relative_to(repo/'.cache'):
        raise ValueError('Execution artefact escapes owned cache')
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError('Symlink execution parent')
        if parent==repo:
            break
command=[sys.executable,'-B',str(producer.HERE/'producer.py'),'--repo',str(repo),
         '--execution',args.execution,'--out',str(args.out)]
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt=dict(command=command,execution_commit=args.execution,executed_code=closure,
             working_directory=str(repo),started_utc=utc(),status='running',
             limits=['One actual complete numerical process. No automatic retry, physical approval or geometry repair.'])
def save():args.receipt.write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n')
with args.log.open('xb') as stream:
    process=subprocess.Popen(command,cwd=repo,stdout=stream,stderr=subprocess.STDOUT)
    receipt['pid']=process.pid
    save()
    status=process.wait()
receipt.update(finished_utc=utc(),exit_code=status,status='complete'if status==0 else'failed')
save()
print(json.dumps(receipt))
sys.exit(status)
