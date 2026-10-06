#!/usr/bin/env python3
"""Restore exact original reference bytes into a new, owned local cache file."""
import argparse
import hashlib
import json
import pathlib
import platform
import subprocess
import urllib.request

root = pathlib.Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--bytes', type=int, required=True)
parser.add_argument('--sha256', required=True)
parser.add_argument('--output', type=pathlib.Path, required=True)
parser.add_argument('--receipt', type=pathlib.Path, required=True)
args = parser.parse_args()
head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
relative_code = pathlib.Path(__file__).resolve().relative_to(root).as_posix()
code = pathlib.Path(__file__).read_bytes()
assert subprocess.check_output(['git', '-C', str(root), 'show', head + ':' + relative_code]) == code
assert args.url.startswith('https://') and 0 < args.bytes <= 256 * 1024 * 1024
assert len(args.sha256) == 64 and all(c in '0123456789abcdef' for c in args.sha256)
output = args.output.resolve()
receipt = args.receipt.resolve()
assert output.is_relative_to(root / '.cache/reference-repair-991')
assert receipt.is_relative_to(pathlib.Path(__file__).resolve().parent)
assert not output.exists() and not receipt.exists()
output.parent.mkdir(parents=True, exist_ok=True)
sha = hashlib.sha256()
count = 0
request = urllib.request.Request(args.url, headers={'User-Agent': 'WorldAtlas-reference-restoration/1'})
with urllib.request.urlopen(request, timeout=60) as response, output.open('xb') as stream:
    headers = {name: response.headers.get(name) for name in ['Content-Length', 'ETag', 'Last-Modified']}
    final_url = response.url
    while chunk := response.read(1024 * 1024):
        count += len(chunk)
        if count > args.bytes:
            raise ValueError('Provider object exceeds pinned original size')
        stream.write(chunk)
        sha.update(chunk)
if count != args.bytes or sha.hexdigest() != args.sha256:
    raise ValueError('Restored object differs from pinned original; retain diagnostic bytes, never use as source')
report = {'version': 1, 'source_url': args.url, 'resolved_url': final_url, 'bytes': count,
          'sha256': sha.hexdigest(), 'response_headers': headers, 'execution_commit': head,
          'executed_code': {'path': relative_code, 'bytes': len(code), 'sha256': hashlib.sha256(code).hexdigest()},
          'python_version': platform.python_version(), 'restored_original': True,
          'scientific_approval': False, 'installed': False, 'published': False}
receipt.write_text(json.dumps(report, separators=(',', ':')) + '\n')
print(json.dumps({'bytes': count, 'sha256': sha.hexdigest(), 'restored_original': True}), flush=True)
