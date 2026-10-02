import json,gzip,hashlib,re,html
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from config import DOMAINS,ALIASES,ADDITIONAL
P=Path(__file__).parent;(P/'gazetteer-pages').mkdir(exist_ok=True)
names=sorted(set([ALIASES.get(n,n.replace(' ','_')) for n in DOMAINS]+[m for a in ADDITIONAL.values() for m in a]))
def run(n):
 u='https://en.wikipedia.org/wiki/'+quote(n,safe='_(),')
 try:
  with urlopen(Request(u,headers={'User-Agent':'WorldAtlas sourced geographic coverage audit'}),timeout=40) as r:b=r.read();status=r.status
  fn=hashlib.sha256(n.encode()).hexdigest()[:16]+'.html.gz';(P/'gazetteer-pages'/fn).write_bytes(gzip.compress(b,mtime=0))
  s=b.decode(errors='replace');span=re.findall(r'<span class="geo"[^>]*>(.*?)</span>',s,re.S);coords=[]
  for a in span:
   a=html.unescape(re.sub('<[^>]+>','',a));ma=re.fullmatch(r'\s*(-?[\d.]+)\s*;\s*(-?[\d.]+)\s*',a)
   if ma:coords.append([float(ma.group(2)),float(ma.group(1))])
  rev=re.findall(r'(?:wgRevisionId["\s:]+|oldid=)([0-9]+)',s)
  title=re.findall(r'<title>(.*?)</title>',s,re.S)
  return dict(name=n,title=title[:1],url=u,http_status=status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),compressed_path='gazetteer-pages/'+fn,coordinates=coords[:6],revision_ids=list(dict.fromkeys(rev))[:5],license='Wikipedia article text CC BY-SA; page authors/history URL retained; underlying cited facts separately attributable.',vintage='Live article retrieved 2026-10-02 UTC; names/association evidence only, not current shoreline survey.')
 except Exception as e:return dict(name=n,url=u,error=str(e))
with ThreadPoolExecutor(max_workers=6) as ex:rows=list(ex.map(run,names))
(P/'gazetteer-source-inventory.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
print('pages',len(rows),'successful',sum(x.get('http_status')==200 for x in rows),'failed',[(r['name'],r.get('error')) for r in rows if r.get('http_status')!=200])
