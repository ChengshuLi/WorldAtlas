from pathlib import Path
from urllib.request import urlopen,Request
from concurrent.futures import ThreadPoolExecutor
import zipfile,io,json,hashlib,gzip
P=Path(__file__).parent;other=Path('/tmp/worldatlas-macro-coverage-africa-americas/geonames');(P/'geonames').mkdir(exist_ok=True);countries=['GR','CY','MT','IT','PT','ES','GG','JE','IM','IS','FO','SJ','FI','CX','CC','IN','MY','SG','TW','JP','RU','LK','MV','IO','AX']
def run(c):
 u=f'https://download.geonames.org/export/dump/{c}.zip';path=P/'geonames'/f'{c}.zip'
 try:
  if (other/f'{c}.zip').exists():b=(other/f'{c}.zip').read_bytes();method='reuse independently retained same public dump'
  elif path.exists():b=path.read_bytes();method='reuse own byte-preserved dump'
  else:
   with urlopen(Request(u,headers={'User-Agent':'WorldAtlas geographic gazetteer research'}),timeout=60) as r:b=r.read()
   path.write_bytes(b);method='HTTP public country dump retrieved2026-10-02'
  z=zipfile.ZipFile(io.BytesIO(b));raw=z.read(f'{c}.txt');lines=[];islands=[]
  for ln in raw.splitlines(keepends=True):
   a=ln.decode(errors='replace').rstrip('\n').split('\t')
   if len(a)<19 or a[6]!='T' or a[7] not in ('ISL','ISLS','RKS','ATOL','ISLET'):continue
   lines.append(ln);islands.append(dict(id=a[0],name=a[1],ascii_name=a[2],aliases=a[3].split(','),latitude=float(a[4]),longitude=float(a[5]),feature_class=a[6],feature_code=a[7],country=a[8],modified=a[18]))
  keep=b''.join(lines);(P/'geonames'/f'{c}-original-island-lines.tsv.gz').write_bytes(gzip.compress(keep,mtime=0));(P/'geonames'/f'{c}-islands.json').write_text(json.dumps(islands,separators=(',',':'))+'\n')
  return dict(country=c,url=u,source_zip_sha256=hashlib.sha256(b).hexdigest(),source_zip_bytes=len(b),country_text_sha256=hashlib.sha256(raw).hexdigest(),source_island_lines_sha256=hashlib.sha256(keep).hexdigest(),source_island_lines_path=f'geonames/{c}-original-island-lines.tsv.gz',island_records_path=f'geonames/{c}-islands.json',island_records=len(islands),retrieval=method,license='GeoNames CC BY4.0; https://www.geonames.org/about.html; modificationdate is edit timestamp, not geographic observation/history.',scope='Original byte-preserved island/rock/atoll source lines selected by featureclassT; countries are sourcecatalog context, not atlasregion ownership assignment.')
 except Exception as e:return dict(country=c,url=u,error=str(e))
with ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(run,countries))
(P/'geonames-source-inventory.json').write_text(json.dumps(rows,separators=(',',':'))+'\n');print('countries',len(rows),'successful',sum('error' not in r for r in rows),'failures',[(r['country'],r.get('error')) for r in rows if 'error'in r])
