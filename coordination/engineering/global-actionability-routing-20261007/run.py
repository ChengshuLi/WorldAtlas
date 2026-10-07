"""Exact immutable execution entry point; full metadata only, no spatial kernels."""
import argparse
import datetime
import pathlib
import platform
import re
import subprocess
import sys
import time
import producer
import controls

HERE = pathlib.Path(__file__).resolve().parent
FILES = ('run.py', 'producer.py', 'controls.py', 'inputs.py', 'immutable.py', 'input-config.json', 'source-code-provenance.json')


def checked_execution(repo, commit):
    if re.fullmatch('[a-f0-9]{40}', commit) is None:
        raise ValueError('Exact lowercase40hex execution commit required')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)
    actual = git('rev-parse', '--verify', '--end-of-options', commit + '^{commit}').decode().strip()
    if actual != commit:
        raise ValueError('Execution commit differs')
    git('merge-base', '--is-ancestor', commit, 'HEAD')
    prefix = HERE.relative_to(repo).as_posix()
    code = []
    for name in FILES:
        path = HERE/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Require ordinary executed code/config')
        raw = path.read_bytes()
        descriptor = dict(bytes=len(raw), sha256=producer.digest(raw))
        original = producer.inputs.ordinary_git(repo, commit, prefix + '/' + name, descriptor)
        if raw != original:
            raise ValueError('Executed owned code/config differs from immutable freeze')
        code.append(dict(path=prefix + '/' + name, **descriptor))
    imports = []
    for name, module in list(sys.modules.items()):
        source = getattr(module, '__file__', None)
        if source and pathlib.Path(source).resolve().parent == HERE:
            path = pathlib.Path(source)
            if path.name not in FILES or path.read_bytes() != (HERE/path.name).read_bytes():
                raise ValueError('Unmeasured transitive owned import')
            imports.append(dict(module=name, path=path.name, sha256=producer.digest(path.read_bytes())))
    return dict(execution_commit=commit, actual_head=git('rev-parse', 'HEAD').decode().strip(),
        complete_owned_code_and_config=code, actual_transitive_owned_imports=sorted(imports, key=lambda x: x['module']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--execution', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    repo = pathlib.Path(args.repo).resolve()
    destination = pathlib.Path(args.out).resolve()
    if destination.exists():
        raise ValueError('Exclusive new complete execution destination required')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clock = time.monotonic()
    code = checked_execution(repo, args.execution)
    config = producer.json.loads((HERE/'input-config.json').read_bytes())
    print('Authenticated immutable code/config; reading complete global ordinary inputs', flush=True)
    joined = producer.metadata_join(repo, config)
    print('Complete current/source/family/batch admission passed; directed actual-reader controls', flush=True)
    control_result = controls.run(joined, repo)
    code = checked_execution(repo, args.execution)
    products = producer.routing_products(joined)
    report = producer.write_products(products, destination)
    report.update(status='PASS', execution_commit=args.execution, source_delivery=producer.EXPECTED_DELIVERY,
        current_audited_cohort=config['candidate_delivery'], original_current_lineage=joined['current_lineage'],
        complete_input_receipts=joined['input_receipts'], complete_code_receipt=code,
        counts={k: config['expected'][k] for k in ('components','families','operational_batches','admin_bindings')},
        limits=producer.LIMITS)
    (destination/'report.json').write_bytes(producer.canonical(report))
    (destination/'controls.json').write_bytes(producer.canonical(control_result))
    ended = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt = dict(status='PASS', exit=0, actual_command=[sys.executable, *sys.argv],
        start_utc=started, end_utc=ended, elapsed_seconds=time.monotonic()-clock,
        python=sys.version, runtime=sys.executable, platform=platform.platform(),
        execution_commit=args.execution, complete_scientific_report_sha256=producer.digest((destination/'report.json').read_bytes()),
        complete_scientific_files=[dict(path=p.name, bytes=p.stat().st_size, sha256=producer.digest(p.read_bytes()))
            for p in sorted(destination.iterdir()) if p.is_file()])
    (destination/'actual-execution.json').write_bytes(producer.canonical(receipt))
    print(producer.json.dumps(dict(status='PASS', counts=report['counts'], controls=control_result['actual_directed_controls'],
        output_bytes=sum(d['bytes'] for d in report['outputs']), outputs=len(report['outputs']), elapsed_seconds=receipt['elapsed_seconds'])), flush=True)


if __name__ == '__main__':
    main()
