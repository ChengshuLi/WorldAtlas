"""Retain two actual complete run trees verbatim; no geometry execution."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

CASE=Path(__file__).resolve().parent
ROOT=CASE.parents[2]
spec=importlib.util.spec_from_file_location('owned_prepared_reader',CASE/'verify.py')
v=importlib.util.module_from_spec(spec);sys.modules[spec.name]=v;spec.loader.exec_module(v)
parser=argparse.ArgumentParser();parser.add_argument('--transport-commit',required=True);parser.add_argument('--science-commit',required=True)
args=parser.parse_args()
if not re.fullmatch('[a-f0-9]{40}',args.transport_commit):raise ValueError('Immutable transport commit required')
modules=[]
for module in list(sys.modules.values()):
    filename=getattr(module,'__file__',None)
    if filename:
        path=Path(filename).resolve()
        if path.is_relative_to(ROOT) and path.suffix=='.py':
            rel=str(path.relative_to(ROOT));raw=path.read_bytes()
            if raw!=v.p.read_git(args.transport_commit,rel):raise ValueError('Unbound transport actual module')
            modules.append(v.p.descriptor(rel,raw))
plan=[]
for name in ['one','two']:
    source=ROOT/'.cache/1293'/('final-run-'+name);target=CASE/('run-'+name)
    if not source.is_dir() or target.exists() or any(p.is_symlink() for p in [source,target,*source.parents,*target.parents]):
        raise ValueError('Use original ordinary source and absent owned delivery')
    raw=(source/'report.json').read_bytes();report=json.loads(raw)
    if report['code_commit']!=args.science_commit:raise ValueError('Wrong actual science vintage')
    expected={pin['path'] for pin in report['outputs']}|{'report.json'}
    if {p.name for p in source.iterdir()}!=expected:raise ValueError('Hidden or missing actual outputs')
    checked=[]
    for pin in report['outputs']:
        v.checked(source,pin);checked.append(pin)
    checked.append(v.p.descriptor('report.json',raw))
    for pin in checked:
        path=source/pin['path']
        if path.is_symlink():raise ValueError('Nonordinary actual output')
        body=path.read_bytes()
        if len(body)!=pin['bytes'] or hashlib.sha256(body).hexdigest()!=pin['sha256']:raise ValueError('Changed actual output')
    plan.append((source,target,checked))
relations=[]
for source,target,pins in plan:
    target.mkdir()
    for pin in pins:
        body=(source/pin['path']).read_bytes()
        with (target/pin['path']).open('xb') as out:out.write(body)
        if (target/pin['path']).read_bytes()!=body:raise ValueError('Delivery readback mismatch')
        relations.append({'actual_source':str(source/pin['path']),'delivered_path':str((target/pin['path']).relative_to(ROOT)),**pin})
receipt={'outcome':'passed','science_commit':args.science_commit,'transport_commit':args.transport_commit,
         'actual_transport_modules':modules,'whole_original_relations':relations,'retained_files':len(relations),
         'retained_bytes':sum(r['bytes'] for r in relations),'limits':['Verbatim transport of two actual run trees; no third scientific execution.']}
(CASE/'verification/transport.json').write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps({'outcome':'passed','files':len(relations),'bytes':receipt['retained_bytes']}))
