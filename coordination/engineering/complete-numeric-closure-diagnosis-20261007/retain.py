"""Exclusive byte-identical retention of the two actual completed local runs."""
import json
from pathlib import Path
import re
import verify
import reader
import diagnose

HERE=Path(__file__).resolve().parent
SCIENCE='3ef1b938a4813adcc62be632df29837c8122a1bb'

def retain(repo,commit):
    verify.require(re.fullmatch('[a-f0-9]{40}',commit) is not None,'Immutable retainer commit required')
    for name in ('retain.py','verify.py'):
        verify.require(reader.safe_path(HERE,name).read_bytes()==diagnose.git(repo,'show',commit+':'+diagnose.OWNED+name),
                       'Changed executed retention helper')
    # Authenticate every scientific whole body before either destination is created.
    reports=[];pins=[]
    for number in (1,2):
        root=HERE/'.cache'/('final-run-one' if number==1 else 'final-run-two')
        report,pin=verify.read_report(root)
        verify.require(report['execution_commit']==SCIENCE and report['status']=='complete','Wrong actual completed science')
        invocation=json.loads(reader.safe_path(HERE/'.cache',f'final-run-{("one" if number==1 else "two")}-invocation.json').read_bytes())
        verify.require(invocation['execution_commit']==SCIENCE and invocation['exit_code']==0,'Missing actual successful invocation')
        reports.append(report);pins.append(pin)
    verify.require(reports[0]['outputs']==reports[1]['outputs'],'Two complete scientific descriptor families differ')
    for descriptor in reports[0]['outputs']:
        left=reader.safe_path(HERE/'.cache/final-run-one',descriptor['path']).read_bytes()
        right=reader.safe_path(HERE/'.cache/final-run-two',descriptor['path']).read_bytes()
        verify.require(left==right,'Two actual whole scientific encoded bodies differ')
    for key in ('counts','geometry_objects','source_input_receipts','complete_original104_file_restoration','runtime','code',
                'original_reconstructor','original_config_sha256','derived_component_only_config_sha256','limits'):
        verify.require(reader.canonical(reports[0][key])==reader.canonical(reports[1][key]),'Two scientific report bodies differ: '+key)
    destinations=[HERE/'r1',HERE/'r2'];verify.require(not any(x.exists() for x in destinations),'Retention destination already exists')
    for path in destinations:
        for ancestor in (path,*path.parents):verify.require(not ancestor.is_symlink(),'Retention ancestor symlink')
    aliases=[]
    for number,report in enumerate(reports,1):
        original=HERE/'.cache'/('final-run-one' if number==1 else 'final-run-two');dest=destinations[number-1]
        dest.mkdir(exist_ok=False)
        for pin in [*report['outputs'],pins[number-1]]:
            source=reader.safe_path(original,pin['path']);raw=source.read_bytes()
            verify.require(len(raw)==pin['bytes'] and reader.digest(raw)==pin['sha256'],'Changed actual complete source')
            target=dest/pin['path']
            with target.open('xb') as handle:handle.write(raw)
            verify.require(target.read_bytes()==raw,'Delivered body differs from actual execution')
            aliases.append(dict(actual_path=str(source),delivered_path=str(target.relative_to(HERE)),**pin))
    family=reader.digest(reader.canonical(reports[0]['outputs']))
    return dict(status='PASS',execution_commit=SCIENCE,retention_commit=commit,
                complete_runs=2,complete_scientific_shards_per_run=len(reports[0]['outputs']),
                scientific_family_sha256=family,run_one_sha256=family,run_two_sha256=family,
                aliases=aliases,report_pins=pins,
                limits=['Both original emitted report bodies and both distinct actual command/time/outcome capsules are preserved; reports have distinct times/elapsed values and are not claimed byte-identical.',
                        'Byte-identical scientific payload comparison is readback of two real complete frozen executions, not a third numerical run or newly computed source fact.'])
