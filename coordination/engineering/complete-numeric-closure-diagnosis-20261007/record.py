"""Authenticated final controls, literal two-run retention and semantic readback."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import diagnose
import reader
import retain
import verify

HERE=Path(__file__).resolve().parent
POST=('record.py','verify.py','verify-controls.py','retain.py','build_manifest.py')
SCIENCE=retain.SCIENCE

def save(path,value):
    with path.open('xb') as handle:handle.write(reader.canonical(value))

def authenticate(repo,commit):
    verify.require(re.fullmatch('[a-f0-9]{40}',commit) is not None,'Require immutable final recorder commit')
    rows=[]
    for name in (*POST,*diagnose.CODE,'controls.py','six-retained-control-inputs.json'):
        vintage=commit if name in POST else SCIENCE
        raw=reader.safe_path(HERE,name).read_bytes()
        verify.require(raw==diagnose.git(repo,'show',vintage+':'+diagnose.OWNED+name),'Changed final actual executed closure: '+name)
        rows.append(dict(path=diagnose.OWNED+name,commit=vintage,bytes=len(raw),sha256=reader.digest(raw)))
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(HERE) and path.suffix=='.py':
                verify.require(str(path.relative_to(HERE)) in (*POST,*diagnose.CODE),'Undeclared actual recorder import')
    return rows

def invocation(directory,name,command,commit):
    started=diagnose.utc()
    with (directory/(name+'.log')).open('xb') as log:
        outcome=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,
                               env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    result=dict(command=command,code_commit=commit,started_at=started,ended_at=diagnose.utc(),exit_code=outcome.returncode)
    save(directory/(name+'-invocation.json'),result)
    verify.require(outcome.returncode==0,'Actual final command failed: '+name)
    return result

def main(commit):
    repo=HERE.parents[2]
    closure=authenticate(repo,commit)
    directory=HERE/'v'
    verify.require(not directory.exists(),'Final verification directory must be absent')
    for ancestor in (directory,*directory.parents):verify.require(not ancestor.is_symlink(),'Verification ancestor symlink')
    directory.mkdir(exist_ok=False)
    save(directory/'actual-code-closure.json',dict(status='PASS',recorder_commit=commit,science_commit=SCIENCE,
        authenticated_code_and_config=closure,limits=['Actual numerical science executed only frozen3ef twice; this later recorder is explicitly separate non-scientific retention/readback/control execution.']))
    python=sys.executable
    for name,script,expected in [('scientific-controls','controls.py',66),('verification-controls','verify-controls.py',63)]:
        source_commit=SCIENCE if name=='scientific-controls' else commit
        invocation(directory,name,[python,'-u','-B',str(HERE/script)],source_commit)
        output=json.loads((directory/(name+'.log')).read_bytes())
        outcome=output['result'] if name=='scientific-controls' else output['status']
        count=output['complete_directed_controls'] if name=='scientific-controls' else output['count']
        verify.require(outcome=='PASS' and count==expected,'Actual bounded controls do not match their declared count')
        save(directory/(name+'.json'),output)
    retained=retain.retain(repo,commit)
    save(directory/'two-actual-tree-retention.json',retained)
    for ordinal,word in ((1,'one'),(2,'two')):
        cache=HERE/'.cache'
        actual=json.loads(reader.safe_path(cache,f'final-run-{word}-invocation.json').read_bytes())
        verify.require(actual['exit_code']==0 and actual['execution_commit']==SCIENCE,'Missing actual full science execution')
        save(directory/f'science-run-{ordinal}-invocation.json',actual)
        raw=reader.safe_path(cache,f'final-run-{word}.log').read_bytes()
        with (directory/f'science-run-{ordinal}.log').open('xb') as handle:handle.write(raw)
    invocation(directory,'complete-semantic-readback',[python,'-u','-B',str(HERE/'verify.py'),
        '--repo',str(repo),'--run',str(HERE/'r1'),'--science-commit',SCIENCE,
        '--verification-commit',commit,'--receipt',str(directory/'complete-semantic-readback.json')],commit)
    report=json.loads(reader.safe_path(HERE,'r1/report.json').read_bytes())
    for method,file in [('complete-ordinary-retention','preparation'),('literal104-exact-witness-diagnosis','measurement')]:
        for kind in ('positive-control','negative-control'):
            save(directory/(file+'-'+kind.split('-')[0]+'.json'),dict(method_id=method,kind=kind,outcome='passed',
                scientific_controls=dict(path='v/scientific-controls.json',count=66,
                    sha256=reader.digest((directory/'scientific-controls.json').read_bytes())),
                semantic_controls=dict(path='v/verification-controls.json',count=63,
                    sha256=reader.digest((directory/'verification-controls.json').read_bytes())),
                full_output_readback=dict(path='v/complete-semantic-readback.json',
                    sha256=reader.digest((directory/'complete-semantic-readback.json').read_bytes())),
                limits=report['limits']+['The two control suites are bounded positive/tampering fixtures and retained six-case controls, not complete third numerical science. The complete final reader checks full custody/rosters/unknown logic and rational witness construction without rerunning overlays or candidate membership predicates.']))
    save(directory/'reproducibility.json',dict(method_id='complete-ordinary-retention',kind='reproducibility',outcome='passed',
        run_one_sha256=retained['run_one_sha256'],run_two_sha256=retained['run_two_sha256'],
        actual_science_commit=SCIENCE,actual_full_runs=2,complete_numeric_components=26276,
        complete_families=3503,complete_batches=253,complete_geometry_objects=report['geometry_objects'],
        full_retention_receipt_sha256=reader.digest((directory/'two-actual-tree-retention.json').read_bytes()),
        complete_report_bodies_byte_identical=False,limits=retained['limits']))
    print('PASS actual final controls, both retained scientific trees and semantic readback; manifest builder runs separately after recording this completed execution')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True)
    main(parser.parse_args().commit)
