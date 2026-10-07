"""Retain complete original ordinary bodies for issue1300; no measurement."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess

LIMIT = 33554432
MERGE = '0198938719a5666b6726fb6a1e45779926eefeb2'
PREFIX = 'coordination/engineering/global-actionability-routing-20261007/'

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--proposal', required=True)
    parser.add_argument('--scope', required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    here = Path(__file__).resolve().parent
    directory = here/'i'
    directory.mkdir(exist_ok=False)
    proof = []
    def git(*parts):
        return subprocess.check_output(['git', '-C', str(repo), *parts])
    def retain(path, pin, role):
        row = git('ls-tree', MERGE, '--', path).decode().strip().split()
        if len(row) != 4 or row[0] != '100644' or row[1] != 'blob':
            raise ValueError('Missing/nonordinary original: '+path)
        raw = git('cat-file', 'blob', row[2])
        if len(raw) != pin['bytes'] or sha(raw) != pin['sha256'] or len(raw)>LIMIT:
            raise ValueError('Original complete body mismatch: '+path)
        if 'uncompressed_sha256' in pin:
            decoded = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(LIMIT+1)
            if len(decoded) != pin['uncompressed_bytes'] or len(decoded)>LIMIT or sha(decoded)!=pin['uncompressed_sha256']:
                raise ValueError('Original complete decoded body mismatch: '+path)
        name = f'i/{len(proof):03}.bin'
        target = here/name
        target.write_bytes(raw)
        if target.read_bytes()!=raw:
            raise ValueError('Retained body readback differs')
        proof.append(dict(pin, original_commit=MERGE, original_path=path,
                          original_mode=row[0], original_oid=row[2], path=name, role=role))
    proposal = json.loads(Path(args.proposal).read_bytes())
    for pin in proposal['necessary_whole_input_files']:
        retain(pin['path'], pin, 'complete-original-physical-input')
    report_raw=git('show',MERGE+':'+PREFIX+'results/report.json')
    report=json.loads(report_raw)
    for pin in report['outputs']:
        retain(PREFIX+'results/'+pin['path'],pin,'complete-delivered-routing-input')
    for name in ('report.json','controls.json'):
        path=PREFIX+'results/'+name
        raw=git('show',MERGE+':'+path)
        retain(path,dict(bytes=len(raw),sha256=sha(raw),hash_kind='file-bytes'),'complete-delivered-routing-input')
    scope = Path(args.scope).read_bytes()
    if len(scope)!=8610767 or sha(scope)!='ada2db15a78524cd28c7a5f924df7bbe0fe616cdead91c429dd2c04384a156e9':
        raise ValueError('Wrong actual-merged complete scope')
    decoded=gzip.GzipFile(fileobj=io.BytesIO(scope)).read(LIMIT+1)
    if len(decoded)!=28911831 or sha(decoded)!='7f857e8c3c032ebfcedf3f602d96b1e563599d726834d2fd263dd4371ae70c9b':
        raise ValueError('Wrong scope decoded body')
    (here/'scope.json.gz').write_bytes(scope)
    proof.append(dict(path='scope.json.gz',bytes=len(scope),sha256=sha(scope),uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded),role='complete-actual-merged-scope',hash_kind='file-bytes'))
    (here/'input-index.json').write_bytes(canonical(dict(version=1,actual_merge=MERGE,files=proof,bytes=sum(x['bytes'] for x in proof))))
    print(json.dumps({'files':len(proof),'bytes':sum(x['bytes'] for x in proof)}))

if __name__=='__main__':
    main()
