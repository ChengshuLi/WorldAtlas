import json,gzip,pathlib,urllib.request,urllib.parse,concurrent.futures,hashlib,xml.etree.ElementTree as ET,re,time
root=pathlib.Path(__file__).resolve().parent;gaz={x['name']:x for x in json.load(open(root/'gazetteers.json'))}
names=['Canton/Kanton/Abariringa','Enderbury','Rawaki/Phoenix','Birnie','McKean','Manra/Sydney','Orona/Hull','Nikumaroro/Gardner','Malden','Starbuck','Vostok','Flint','Caroline/Millennium','Kingman Reef','Pitcairn','Ducie','Oeno','Manuae','Takutea','Nassau','Suwarrow','Nukunonu','Bounty Islands','Baker','Banaba/Ocean Island','Teraina/Washington','Mitiaro','Palmerston','Manihiki','Snares']
def coord(s):
 v=[float(x) for x in re.findall(r'[\d.]+',s)];a=sum(x/60**i for i,x in enumerate(v));return -a if 'S' in s or 'W' in s else a
fallback={'Palmerston':[-163.166667,-18.05]}
def f(name):
 if name in fallback:lon,lat=fallback[name]
 else:lat,lon=[coord(c) for c in gaz[name]['coordinate_html']]
 rad=.13 if name not in ['Bounty Islands','Snares'] else .08; bbox=[lon-rad,lat-rad,lon+rad,lat+rad];url='https://api.openstreetmap.org/api/0.6/map?bbox='+','.join(str(round(x,7))for x in bbox);fn='osm-'+hashlib.sha256(name.encode()).hexdigest()[:12]+'.xml.gz'
 try:
  data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'WorldAtlas source audit/1.0'}),timeout=90).read();(root/fn).write_bytes(gzip.compress(data,mtime=0));x=ET.fromstring(data);ways=[w for w in x.findall('way')if any(t.get('k')=='natural' and t.get('v')=='coastline'for t in w.findall('tag'))];r={'name':name,'url':url,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'path':fn,'bbox':bbox,'retrieved_on':'2026-10-02','copyright':x.get('copyright'),'license':x.get('license'),'coastline_ways':len(ways),'source_node_count':len(x.findall('node'))};print(name,len(data),len(ways),flush=True);return r
 except Exception as e:print(name,str(e),flush=True);return {'name':name,'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(3)as ex:r=list(ex.map(f,names))
(root/'osm-sources.json').write_text(json.dumps(r,separators=(',',':')))
