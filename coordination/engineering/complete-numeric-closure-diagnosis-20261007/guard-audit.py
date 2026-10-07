"""Supplemental all-row guard audit; predecessor whole proof reused honestly."""
import argparse,json,re
from collections import Counter
from pathlib import Path
import diagnose,reader,verify
HERE=Path(__file__).resolve().parent
SCIENCE='3ef1b938a4813adcc62be632df29837c8122a1bb'
PREDECESSOR='45a6c00d7a9f1e9edd873ff9b8887231dca3608b'
PREDECESSOR_SHA='ac991c5617c808910a3d3d6d14454648aa8dbb4185e8289ec4ada58623b5585a'
def run(repo,commit,receipt):
    verify.require(re.fullmatch('[a-f0-9]{40}',commit) is not None,'Immutable correction commit required')
    executed=[]
    for name in ('verify.py','guard-controls.py','guard-audit.py'):
        raw=reader.safe_path(HERE,name).read_bytes()
        verify.require(raw==diagnose.git(repo,'show',commit+':'+diagnose.OWNED+name),'Changed corrected executed code')
        executed.append(dict(path=name,bytes=len(raw),sha256=reader.digest(raw)))
    for name in diagnose.CODE:
        raw=reader.safe_path(HERE,name).read_bytes()
        verify.require(raw==diagnose.git(repo,'show',SCIENCE+':'+diagnose.OWNED+name),'Changed frozen science code/config')
    raw=reader.safe_path(HERE,'v/complete-semantic-readback.json').read_bytes()
    verify.require(reader.digest(raw)==PREDECESSOR_SHA,'Changed literal predecessor whole proof')
    previous=json.loads(raw)
    verify.require(previous['verification_commit']==PREDECESSOR and previous['science_commit']==SCIENCE and
        previous['status']=='PASS' and previous['complete_components']==26276,'Wrong predecessor complete proof')
    report,pin=verify.read_report(HERE/'r1')
    verify.require(pin==previous['report'] and report['outputs']==previous['outputs'],'Changed complete reviewed data')
    counts=Counter();seen=set();families=set();batches=set();guarded=0
    for row in verify.rows(HERE/'r1',report,'diagnoses'):
        identity=row['component_id'];verify.require(identity not in seen,'Duplicate diagnostic row');seen.add(identity)
        families.add(row['family']);batches.add(row['operational_batch'])
        for probe in row['point_diagnostics'].values():
            counts[probe['status']]+=1
            if probe['status']!='diagnostic':
                guarded+=1
                verify.require(not probe['vertices'] and not probe['triangles'],
                    'Actual partial evidence requires separate complete geometry audit; never discard')
                verify.probe_structure(probe,{})
        if len(seen)%5000==0:print(json.dumps(dict(guard_audited=len(seen))),flush=True)
    verify.require(len(seen)==26276 and len(families)==3503 and len(batches)==253,'Incomplete supplemental scope')
    body=dict(status='PASS',kind='corrected guard audit of every retained row; literal predecessor complete proof reused at its original code',
        corrected_commit=commit,science_commit=SCIENCE,predecessor_verification_commit=PREDECESSOR,
        predecessor_receipt_sha256=PREDECESSOR_SHA,report=pin,outputs=report['outputs'],executed=executed,
        complete_components=len(seen),complete_families=len(families),complete_batches=len(batches),
        guarded_probes=guarded,probe_status_counts=dict(counts),actual_nonempty_partial_witnesses=0,
        limits=['No third global operator or exact membership-query execution. All179 inputs,71 whole restorations,88290 objects and complete semantic bindings remain authenticated by the completed literal predecessor proof; they are not re-executed or relabelled at this corrected code.',
        'No nonempty guarded witness exists in these complete outputs; valid failure-in-middle partial-prefix semantics are separately tested with actual unchanged bounded kernel fixtures.'])
    with receipt.open('xb') as h:h.write(reader.canonical(body))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('repo','commit','receipt'):parser.add_argument('--'+name,required=True)
    a=parser.parse_args();run(Path(a.repo).resolve(),a.commit,Path(a.receipt))
