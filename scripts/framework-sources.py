"""Restore checksum-pinned, licensed framework source snapshots to staging."""
import hashlib,json,pathlib,shutil
r=pathlib.Path(__file__).resolve().parents[1];d=r/'data/framework-sources';c=r/'.cache/framework';c.mkdir(parents=True,exist_ok=True)
for item in json.loads((d/'manifest.json').read_text())['sources']:
 p=d/item['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],p
 shutil.copy2(p,c/item['path'])
