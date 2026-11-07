"""Controlled parent-kill fixture; uses the normal direct-execution API."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_pipeline import Pipeline

config, output, source, release = map(Path, sys.argv[1:])
runner = Pipeline(config, output, allow_provisional=True)
try:
    runner.command('water', 'fixture-stage', 'v7-pipeline/fixtures/partial_stage.py',
                   source, output / 'result', wait_for=release,
                   _outputs=[output / 'result'])
finally:
    runner.close()
