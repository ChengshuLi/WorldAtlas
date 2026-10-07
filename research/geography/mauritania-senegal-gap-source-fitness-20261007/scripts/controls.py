"""Run focused positive and negative controls through the source_fit entrypoint."""
import json
import argparse
import pathlib
import shutil
import tempfile

from source_fit import OWNED, COMPONENT_ROOT, COMPONENTS, SOURCES, canonical, screen, sha

repo = pathlib.Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=pathlib.Path, required=True,
                    help='Fresh output file path relative to the repository root')
args = parser.parse_args()
results = []

def expect_reject(name, root, roster=None):
    try:
        screen(root, roster)
    except (ValueError, OSError, KeyError, json.JSONDecodeError):
        results.append({'name': name, 'outcome': 'rejected'})
    else:
        raise AssertionError(f'negative control accepted: {name}')

screen(repo)
results.append({'name': 'complete-pinned-inputs', 'outcome': 'passed'})
expect_reject('incomplete-family-roster', repo, list(COMPONENTS)[:1])
with tempfile.TemporaryDirectory(prefix='source-fit-control-', dir=repo / OWNED / 'reproduction') as tmp:
    root = pathlib.Path(tmp)
    # Copy only selected source products and component payloads; no complete corpus or GIS graph.
    srcdir = root / OWNED / 'sources/geoboundaries/original-consumed-simplified'
    srcdir.mkdir(parents=True)
    for country, (filename, *_rest) in SOURCES.items():
        original = repo / OWNED / 'sources/geoboundaries/original-consumed-simplified' / filename
        shutil.copyfile(original, srcdir / filename)
    payload_dir = root / COMPONENT_ROOT / 'payloads'
    payload_dir.mkdir(parents=True)
    for descriptor in COMPONENTS.values():
        name = descriptor['payload'] + '.bin'
        shutil.copyfile(repo / COMPONENT_ROOT / 'payloads' / name, payload_dir / name)
    # Tamper one consumed source byte. The entrypoint must reject before parsing/overlay.
    mrt = srcdir / SOURCES['MRT'][0]
    raw = mrt.read_bytes()
    mrt.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    expect_reject('altered-consumed-source-bytes', root)
report = {'version': 1, 'method': 'Controls invoke the same load/validation/overlay entrypoint as the report producer.',
          'outcomes': results}
output = (repo / args.output).resolve()
if repo.resolve() not in output.parents:
    raise ValueError('Output must stay inside the repository')
with output.open('xb') as stream:
    stream.write(canonical(report) + b'\n')
print(json.dumps(report))
