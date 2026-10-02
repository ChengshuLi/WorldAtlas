"""Restore pinned climate normals and the existing licensed semantic archive."""
import hashlib,json,pathlib,runpy,urllib.request,zipfile
R=pathlib.Path(__file__).resolve().parents[1];C=R/'.cache'
runpy.run_path(str(R/'scripts/semantic-sources.py'))
for source in json.loads((R/'data/attribute-sources.json').read_text())['sources']:
 p=C/source['cache_path'];p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():
  temp=p.with_suffix('.downloading')
  with urllib.request.urlopen(source['url'],timeout=120) as response,temp.open('wb') as out:
   while raw:=response.read(1024*1024):out.write(raw)
  assert hashlib.sha256(temp.read_bytes()).hexdigest()==source['sha256'],'Downloaded source hash mismatch';temp.replace(p)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==source['sha256'],'Cached source hash mismatch'
 with zipfile.ZipFile(p) as archive:
  for epoch in ['1901_1930','1931_1960','1961_1990','1991_2020']:
   name=epoch+'/koppen_geiger_0p00833333.tif';target=C/'research/koppen-tif'/name
   if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
print('Verified pinned environmental and settlement sources')
