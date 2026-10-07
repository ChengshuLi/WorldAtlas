"""Actual-entry adverse controls; bounded owned fixtures, no GIS calculation."""
import argparse, hashlib, json, pathlib, subprocess, sys, types

N = 'coordination/engineering/angola-original-envelope-20261007/'
ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def main():
    p = argparse.ArgumentParser(); p.add_argument('--commit', required=True); p.add_argument('--run', required=True); a = p.parse_args()
    captured = {}
    for name in ['controls.py', 'run.py', 'producer.py', 'input-plan.json', 'triage.json', 'source.geojson', 'runtime-plan.json']:
        path = N + name
        raw = subprocess.check_output(['git', '-C', str(REPO), 'show', a.commit + ':' + path])
        actual = REPO / path
        if actual.is_symlink() or actual.read_bytes() != raw:
            raise ValueError('Actually executed control writer drift')
        captured[name] = raw
    helper_path = 'scripts/evidence/immutable.py'
    helper = subprocess.check_output(['git', '-C', str(REPO), 'show', a.commit + ':' + helper_path])
    if (REPO / helper_path).read_bytes() != helper:
        raise ValueError('Actual control helper drift')
    immutable = types.ModuleType('immutable'); immutable.__file__ = str(REPO / helper_path)
    exec(compile(helper, immutable.__file__, 'exec'), immutable.__dict__)
    pins = [immutable.descriptor(N + n, raw) for n, raw in captured.items()] + [immutable.descriptor(helper_path, helper)]
    baseline = immutable.Baseline(REPO, a.commit, pins)
    fixtures = immutable.NewVintage(baseline, N, a.run + '-fixtures', ['duplicate.json', 'missing.json', 'join.json', 'source.geojson', 'sentinel.json'])
    result = immutable.NewVintage(baseline, N, a.run, ['controls.json'])
    scope = json.loads(captured['triage.json'])['cohorts'][0]['complete_families']
    clone = lambda: json.loads(json.dumps(scope))
    duplicate = clone(); duplicate[2]['complete_component_ids'][1] = duplicate[2]['complete_component_ids'][0]
    missing = clone(); missing[2]['complete_component_ids'].pop()
    join = clone(); join[0]['full_contacts'][0] = 'gb:AGO:ADM2:16411231B999999999'
    source = json.loads(captured['source.geojson']); geometry = source['features'][0]['geometry']
    ring = geometry['coordinates'][0][0] if geometry['type'] == 'MultiPolygon' else geometry['coordinates'][0]
    ring[0][0] += .0001; ring[-1][0] += .0001
    values = {'duplicate.json': duplicate, 'missing.json': missing, 'join.json': join, 'source.geojson': source, 'sentinel.json': {'original': 'preserve'}}
    fixtures.publish_bytes({n: immutable.canonical_json(v) for n, v in values.items()})
    rows = []
    entry = ROOT / 'run.py'
    def probe(name, extra=(), run_name=None, expected=None):
        run_name = run_name or a.run + '-' + name
        command = [sys.executable, '-I', '-B', N + 'run.py', '--commit', a.commit, '--run', run_name, *extra]
        before = sorted(str(p.relative_to(REPO)) for p in ROOT.iterdir())
        ran = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
        after = sorted(str(p.relative_to(REPO)) for p in ROOT.iterdir())
        failed_root = ROOT / 'vintages' / run_name
        if run_name not in [a.run + '-fixtures', a.run + '-dangling'] and failed_root.exists():
            raise ValueError('Failed control created scientific output')
        if ran.returncode == 0 or (expected and expected not in ran.stderr) or before != after:
            raise ValueError('Non-vacuous adverse control failed: ' + name)
        rows.append({'control': name, 'command': [pathlib.Path(command[0]).name, *command[1:3], N + 'run.py', *command[4:]], 'returncode': ran.returncode, 'stdout': ran.stdout, 'stderr': ran.stderr.replace(str(REPO), '<owned-checkout>'), 'no_scientific_output_created': before == after, 'expected_failure': expected})
    for name, filename, expected in [('duplicate', 'duplicate.json', 'Complete eight-family/ten-component roster'), ('missing', 'missing.json', 'Complete eight-family/ten-component roster'), ('join', 'join.json', 'independent frozen triage')]:
        probe(name, ['--scope-fixture', str((fixtures.root / filename).relative_to(REPO))], expected=expected)
    probe('consumed-source-drift', ['--source-fixture', str((fixtures.root / 'source.geojson').relative_to(REPO))], expected='Actually consumed source drift')
    for name, path in [('executed-producer-drift', ROOT / 'producer.py'), ('executed-helper-drift', REPO / helper_path)]:
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b'\nraise RuntimeError("UNAUTHENTICATED PROJECT CODE MUST NEVER EXECUTE")\n')
            probe(name, expected='Actually executed materialized code/input drift')
        finally:
            path.write_bytes(raw)
    sentinel_before = (fixtures.root / 'sentinel.json').read_bytes()
    probe('output-collision', run_name=a.run + '-fixtures', expected='Fresh run directory already exists')
    if (fixtures.root / 'sentinel.json').read_bytes() != sentinel_before:
        raise ValueError('Original collision sentinel changed')
    symlink_name = a.run + '-dangling'
    # Admit the complete fresh symlink-control path before its exclusive mutation.
    symlink = immutable.admit_destination(baseline, N, symlink_name, ['publication.json'])
    symlink.symlink_to('nonexistent-owned-control-target')
    try:
        probe('dangling-output-symlink', run_name=symlink_name, expected='Symlink')
        if not symlink.is_symlink() or symlink.readlink() != pathlib.Path('nonexistent-owned-control-target'):
            raise ValueError('Original dangling symlink changed')
    finally:
        symlink.unlink()
    result.publish({'controls.json': {'status': 'all-eight-actual-entry-adverse-controls-rejected-before-scientific-output', 'execution_commit': a.commit, 'controls': rows, 'positive_control': 'Both same-freeze scientific actual-entry executions must separately complete on unchanged inputs; not counted by this control writer.'}})
    print(json.dumps({'status': 'complete', 'controls': len(rows)}))


if __name__ == '__main__':
    main()
