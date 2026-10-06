"""Retain exact archived executed code bytes, distinct from current executable code."""
import argparse
import hashlib
import json
import pathlib
import subprocess

from evidence.immutable import Baseline, canonical_json, descriptor

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(reports, envelope, output):
    out = pathlib.Path(output).resolve()
    if ROOT / 'coordination/engineering' not in out.parents or out.exists():
        raise ValueError('Use a new owned code snapshot vintage')
    for ancestor in [pathlib.Path(output), *pathlib.Path(output).parents]:
        if ancestor.is_symlink():
            raise ValueError('Snapshot destination traverses symlink')
    executed = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    helper_path = 'scripts/retain-physical-audit-code.py'
    helper = subprocess.check_output(['git', 'show', executed + ':' + helper_path], cwd=ROOT)
    if (ROOT / helper_path).read_bytes() != helper:
        raise ValueError('Commit the exact code snapshot collector before generation')
    aliases, payloads = {}, {}
    for name in [*reports, envelope]:
        raw = (ROOT / name).read_bytes()
        report = json.loads(raw)
        commit = report['executed_code_commit']
        for item in report['code_inputs']:
            original = Baseline(ROOT, commit, [item]).read(item['path'])
            sha = hashlib.sha256(original).hexdigest()
            key = commit + ':' + item['path']
            binding = {'original_commit': commit, 'original': item,
                       'snapshot': descriptor(str((out / (sha + '.bin')).relative_to(ROOT)), original)}
            if key in aliases and aliases[key] != binding:
                raise ValueError('Conflicting archived execution code binding')
            aliases[key] = binding
            payloads[sha] = original
    out.mkdir(parents=True, exist_ok=False)
    for sha, raw in sorted(payloads.items()):
        with (out / (sha + '.bin')).open('xb') as stream:
            stream.write(raw)
    result = {'version': 1, 'executed_code_commit': executed,
              'collector': descriptor(helper_path, helper), 'aliases': aliases,
              'unique_files': len(payloads),
              'limits': ['Exact archived code bytes, not current executables or source/geography approval.']}
    with (out / 'manifest.json').open('xb') as stream:
        stream.write(canonical_json(result))
    print(json.dumps({'aliases': len(aliases), 'files': len(payloads),
                      'bytes': sum(len(raw) for raw in payloads.values())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='append', required=True)
    parser.add_argument('--envelope', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.report, args.envelope, args.output)
