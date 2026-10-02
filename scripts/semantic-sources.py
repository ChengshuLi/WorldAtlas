"""Restore the reviewed, hashed public-source snapshot used by this atlas revision.

New source vintages need a new reviewed snapshot; a live API response may not
silently change the grouping of already imported historical entities.
"""
import io,hashlib,json,pathlib,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1];cache=ROOT/'.cache/semantic';cache.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'data/semantic-sources.json').read_text())
parts=[]
for entry in manifest['archive_parts']:
 raw=(ROOT/'data'/entry['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['sha256'];parts.append(raw)
archive=b''.join(parts);assert hashlib.sha256(archive).hexdigest()==manifest['archive_sha256']
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as t:
 for entry in manifest['files']:
  name=entry['path'];p=cache/name
  if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']:continue
  data=t.extractfile(name).read();assert hashlib.sha256(data).hexdigest()==entry['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
print('Verified',len(manifest['files']),'reviewed public-source evidence files')
