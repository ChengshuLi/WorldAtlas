"""Deterministic interruption fixture for the executor contract tests."""
import argparse
from pathlib import Path
import tempfile

import stage_external


def main(argv=None, *, emit=print):
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--interrupt-once', type=Path)
    parser.add_argument('--wait-for', type=Path)
    args = parser.parse_args(argv)
    emit(tempfile.gettempdir())
    args.output.mkdir()
    result = args.output / 'result.bin'
    result.write_bytes(b'partial')
    if args.interrupt_once is not None and not args.interrupt_once.exists():
        args.interrupt_once.write_bytes(b'attempt interrupted')
        raise RuntimeError('fixture failed')
    if args.wait_for is not None:
        stage_external.run(['/bin/sh', '-c', 'touch "$1"; while [ ! -e "$2" ]; do sleep .01; done',
                            'fixture', str(args.output / 'waiting'), str(args.wait_for)], check=True)
    result.write_bytes(args.source.read_bytes())
