#!/usr/bin/env python3
"""Restore the exact original RESOLVE object from the retained semantic archive."""
import hashlib
import io
import json
import pathlib
import platform
import subprocess
import tarfile

root = pathlib.Path(__file__).resolve().parents[3]
prefix = pathlib.Path(__file__).resolve().parent.relative_to(root).as_posix()
baseline = 'd0cc67eac85038159f88a673acbc39b77ab7461d'
head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
code_path = prefix+'/restore-original-vegetation.py'
code = pathlib.Path(__file__).read_bytes()
assert subprocess.check_output(['git','-C',str(root),'show',head+':'+code_path]) == code
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def read(name):
    return subprocess.check_output(['git','-C',str(root),'show',baseline+':'+name])
raw_index = read('data/semantic-sources.json')
index = json.loads(raw_index)
inputs = [{'path':'data/semantic-sources.json','bytes':len(raw_index),'sha256':sha(raw_index)}]
archive_parts = []
for part in index['archive_parts']:
    name = 'data/'+part['path']
    raw = read(name)
    assert 0 < len(raw) <= 32*1024*1024 and sha(raw) == part['sha256']
    inputs.append({'path':name,'bytes':len(raw),'sha256':sha(raw)})
    archive_parts.append(raw)
archive = b''.join(archive_parts)
assert sha(archive) == index['archive_sha256']
expected = next(p['sha256'] for p in index['files'] if p['path'] == 'resolve-ecoregions.geojson')
output = root/'.cache/reference-repair-991/resolve-original.geojson'
receipt = root/prefix/'vegetation-original-archive-restoration-v1.json'
assert not output.exists() and not receipt.exists()
native_sha = hashlib.sha256(); count = 0; matches = []
# Stream archive members. Never extract unrelated paths or allocate a full
# uncompressed national/world source collection merely to reach this member.
with tarfile.open(fileobj=io.BytesIO(archive),mode='r|gz') as retained:
    for member in retained:
        if pathlib.PurePosixPath(member.name).name != 'resolve-ecoregions.geojson':
            continue
        assert member.isfile() and not matches and member.size <= 256*1024*1024
        matches.append({'archive_entry':member.name,'bytes':member.size})
        source = retained.extractfile(member)
        with output.open('xb') as destination:
            while chunk := source.read(1048576):
                count += len(chunk)
                assert count <= member.size
                native_sha.update(chunk); destination.write(chunk)
assert len(matches) == 1 and count == matches[0]['bytes'] and native_sha.hexdigest() == expected
report = {'version':1,'execution_commit':head,'executed_code':{'path':code_path,'bytes':len(code),'sha256':sha(code)},
          'baseline_commit':baseline,'inputs':inputs,'archive_sha256':sha(archive),
          'native_object':{'path':'resolve-ecoregions.geojson','bytes':count,'sha256':expected,**matches[0]},
          'python_version':platform.python_version(),'restored_original':True,
          'current_provider_export_used':False,'installed':False,'published':False}
receipt.write_text(json.dumps(report,separators=(',',':'))+'\n')
print(json.dumps({'bytes':count,'sha256':expected,'restored_original':True}),flush=True)
