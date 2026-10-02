from pathlib import Path
from urllib.request import urlopen,Request
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,re
P=Path('/tmp/worldatlas-macro-coverage-africa-americas');(P/'gazetteer-pages').mkdir(exist_ok=True)
names=['Madeira','Porto_Santo_Island','Desertas_Islands','Savage_Islands','Ilhéu_Chão','Bugio_Island','Deserta_Grande_Island','Selvagem_Grande','Selvagem_Pequena','Ilhéu_de_Fora','Canary_Islands','La_Graciosa','Alegranza','Montaña_Clara','Lobos_Island','Roque_del_Oeste','Roque_del_Este','Cape_Verde','Santa_Luzia,_Cape_Verde','Branco,_Cape_Verde','Raso','Socotra','Abd_al_Kuri','Samhah','Darsah','Sabuniyah','Ka\'l_Fir\'awn','Comoros','Mayotte','Seychelles','Aldabra','Cosmoledo','Assumption_Island','Astove_Island','Farquhar_Atoll','Providence_Atoll','Alphonse_Atoll','Desroches_Island','Amirante_Islands','Platte_Island','Coëtivy_Island','Scattered_Islands_in_the_Indian_Ocean','Europa_Island','Bassas_da_India','Juan_de_Nova_Island','Glorioso_Islands','Tromelin_Island','Tristan_da_Cunha','Inaccessible_Island','Nightingale_Island','Middle_Island_(Tristan_da_Cunha)','Stoltenhoff_Island','Gough_Island','Greenland','Bermuda','Saint_Pierre_and_Miquelon','Bahamas','Turks_and_Caicos_Islands','Caribbean','Clipperton_Island','Galápagos_Islands','Juan_Fernández_Islands','Desventuradas_Islands','Falkland_Islands','South_Georgia_and_the_South_Sandwich_Islands']
def run(n):
 u='https://en.wikipedia.org/wiki/'+__import__('urllib.parse',fromlist=['quote']).quote(n,safe='_(),')
 try:
  with urlopen(Request(u,headers={'User-Agent':'WorldAtlas geographical source audit research'}),timeout=40) as r:b=r.read();status=r.status
  fn=hashlib.sha256(n.encode()).hexdigest()[:16]+'.html';(P/'gazetteer-pages'/fn).write_bytes(b)
  text=b.decode(errors='replace');geo=re.findall(r'<span class="(?:geo|latitude|longitude)"[^>]*>(.*?)</span>',text,re.S)
  return dict(name=n,url=u,status=status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),path='gazetteer-pages/'+fn,coordinate_spans=geo[:6],license='CC-BY-SA Wikipedia article text; underlying cited-source facts separately attributable',vintage='live revision retrieved2026-10-02')
 except Exception as e:return dict(name=n,url=u,error=str(e))
with ThreadPoolExecutor(max_workers=6) as ex:rows=list(ex.map(run,names))
(P/'gazetteer-source-inventory.json').write_text(json.dumps(rows,separators=(',',':')));print('sources',len(rows),'200',sum(x.get('status')==200 for x in rows));print([(r['name'],r.get('coordinate_spans')) for r in rows if r.get('status')!=200])
