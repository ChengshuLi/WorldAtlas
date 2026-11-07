"""Deterministic process-interruption fixture for the executor contract tests."""
import argparse
import os
from pathlib import Path
import signal
import time

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--interrupt-once', type=Path)
parser.add_argument('--wait-for', type=Path)
args = parser.parse_args()
args.output.mkdir()
result = args.output / 'result.bin'
result.write_bytes(b'partial')
if args.interrupt_once is not None and not args.interrupt_once.exists():
    args.interrupt_once.write_bytes(b'attempt interrupted')
    os.kill(os.getpid(), signal.SIGTERM)
if args.wait_for is not None:
    (args.output / 'waiting').write_bytes(b'ready')
    while not args.wait_for.exists():
        time.sleep(.01)
result.write_bytes(args.source.read_bytes())
