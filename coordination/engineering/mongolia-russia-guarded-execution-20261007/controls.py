"""Literal entry controls; no source comparison, extraction or global calculation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE=Path(__file__).absolute().parent

def execute(commit, out):
    spec=importlib.util.spec_from_file_location('controlled_entry',HERE/'run.py')
    run=importlib.util.module_from_spec(spec);sys.modules[spec.name]=run;spec.loader.exec_module(run)
    rows=[]
    def case(name,fn,expected):
        try:fn()
        except expected as error:
            rows.append(dict(name=name,passed=True,error=str(error)));return
        raise AssertionError('Control failed: '+name)
    def invoke(destination):
        old=sys.argv;sys.argv=['run.py','--commit',commit,'--out',str(destination),'--input-only']
        try:return run.main()
        finally:sys.argv=old
    with tempfile.TemporaryDirectory(prefix='1421-controls-',dir=run.REPO/'.cache') as scratch:
        root=Path(scratch); parent=root/'ordinary';parent.mkdir()
        ordinary_file=root/'file';ordinary_file.write_bytes(b'ordinary file')
        symlink=root/'linked';symlink.symlink_to(parent,target_is_directory=True)
        broken=root/'broken';broken.symlink_to(root/'absent')
        occupied=parent/'occupied';occupied.mkdir()
        cases=[('relative',Path('relative')),('outside owned cache',Path('/tmp/1421-foreign-output')),('regular-file ancestor',ordinary_file/'child'),('missing parent',root/'missing'/'child'),('symlink ancestor',symlink/'child'),('broken leaf',broken),('occupied output',occupied),('dotdot traversal',parent/'..'/'escape')]
        for name,path in cases:
            def check(path=path):
                old=run.load
                def canary(*args):raise AssertionError('Output rejection reached frozen/load boundary')
                run.load=canary
                try:invoke(path)
                finally:run.load=old
            case(name,check,ValueError)
        old=run.load
        class Reached(Exception):pass
        def positive(*args):raise Reached('fresh ordinary destination admitted exactly once')
        run.load=positive
        try:case('fresh ordinary parent positive',lambda:invoke(parent/'fresh'),Reached)
        finally:run.load=old
        case('short execution commit',lambda:run.whole(commit[:12],run.OWNED+'run.py'),ValueError)
        case('Git option commit',lambda:run.whole('--help',run.OWNED+'run.py'),ValueError)
        case('unsafe frozen path',lambda:run.whole(commit,'../run.py'),ValueError)
        # Real consumed-body negatives through the actual main/load branch.
        # HERE alone redirects materialized bytes to this owned disposable copy;
        # immutable Git authority remains the accepted author repository/commit.
        fixture=root/'materialized';shutil.copytree(HERE,fixture)
        original_here=run.HERE;run.HERE=fixture
        try:
            for name,relative in [('actual helper byte drift','methods/ellipsoidal_area.py'),('actual materialized candidate byte drift','inputs/001.bin'),('actual materialized source byte drift','inputs/006.bin'),('actual execution body drift','run.py')]:
                path=fixture/relative;raw=path.read_bytes();path.write_bytes(raw+b' ')
                try:case(name,lambda:invoke(parent/'negative-no-output'),ValueError)
                finally:path.write_bytes(raw)
            # A missing whole pin cannot be disguised by a coherently rebound
            # source inventory; exercise the actual pre-import inventory branch.
            original_whole=run.whole
            def missing_pin(commit_arg,name):
                body=original_whole(commit_arg,name)
                if name==run.OWNED+'code-list.json':
                    inventory=json.loads(body);inventory.remove('methods/ellipsoidal_area.py');return json.dumps(inventory).encode()
                return body
            inventory_path=fixture/'code-list.json';inventory_before=inventory_path.read_bytes()
            inventory_path.write_bytes(missing_pin(commit,run.OWNED+'code-list.json'))
            run.whole=missing_pin
            try:case('missing helper pin in coherent inventory',lambda:invoke(parent/'negative-no-output'),ValueError)
            finally:
                run.whole=original_whole;inventory_path.write_bytes(inventory_before)
            if (parent/'negative-no-output').exists():raise AssertionError('Rejected entry wrote output')
        finally:run.HERE=original_here
    if any(name.startswith(('shapely','pyproj')) for name in sys.modules):
        raise AssertionError('Entry negatives imported scientific packages')
    receipt=dict(status='PASS',execution_commit=commit,controls=rows,count=len(rows),science_imports=False,no_source_comparison=True,caller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),entry_sha256=hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest(),limits=['Disposable materialized-body copy uses actual immutable Git authority; coherent missing-pin control injects only inventory getter bytes. No source/target geometry processing or scientific package import. Positive actual complete frozen input-only execution is recorded separately.'])
    out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(status='PASS',controls=len(rows),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--receipt',required=True,type=Path);a=p.parse_args();execute(a.commit,a.receipt)
