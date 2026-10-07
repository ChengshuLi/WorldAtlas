"""Authenticated actual entry point for the bounded #1423 diagnostic."""
import argparse, hashlib, json, pathlib, re, subprocess, sys, types

NAMESPACE = 'coordination/engineering/angola-original-envelope-20261007/'
ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
CAP = 32 * 1024 * 1024


def captured(commit, name):
    row = subprocess.check_output(['git', '-C', str(REPO), 'ls-tree', commit, '--', name]).decode().strip().split()
    if len(row) != 4 or row[0] != '100644' or row[1] != 'blob':
        raise ValueError('Executed code must be ordinary frozen Git bytes')
    expected = subprocess.check_output(['git', '-C', str(REPO), 'cat-file', 'blob', row[2]])
    target = REPO / name
    if any(p.is_symlink() for p in [target, *target.parents]) or target.read_bytes() != expected or len(expected) > CAP:
        raise ValueError('Actually executed materialized code/input drift: ' + name)
    return expected


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--commit', required=True)
    p.add_argument('--run', required=True)
    p.add_argument('--validate-inputs-only', action='store_true')
    p.add_argument('--scope-fixture')
    p.add_argument('--source-fixture')
    a = p.parse_args()
    if not re.fullmatch('[a-f0-9]{40}', a.commit):
        raise ValueError('Exact execution freeze required')
    # This guard precedes every project import and every installed GIS import.
    own = {name: captured(a.commit, NAMESPACE + name) for name in
           ['run.py', 'producer.py', 'input-plan.json', 'triage.json', 'source.geojson', 'runtime-plan.json']}
    helper = captured(a.commit, 'scripts/evidence/immutable.py')
    module = types.ModuleType('immutable')
    module.__file__ = str(REPO / 'scripts/evidence/immutable.py')
    exec(compile(helper, module.__file__, 'exec'), module.__dict__)
    files = [module.descriptor(NAMESPACE + n, raw) for n, raw in own.items()]
    files.append(module.descriptor('scripts/evidence/immutable.py', helper))
    code = module.Baseline(REPO, a.commit, files)
    loaded = code.load_modules({'producer': NAMESPACE + 'producer.py'})['producer']
    loaded.run(REPO, a, module, code, own)


if __name__ == '__main__':
    main()
