import sys,json,hashlib
sys.path.insert(0,'landed-1b494125')
from smoothed_transect_screen import screen
basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')]
for n,dem,sha in [('00','/tmp/ural-gap00-cop-30m-bilinear.tif','d661fee6218f9198f48cf3505a5303a4942cec602747fb82af3571c9548e4a86'),('02','/tmp/ural-gap02-cop-30m-bilinear.tif','b35eff9756b70096e6ea2f1090249b6a60a31d4b7cc47dfd9d72eec646a0e169')]:
 coords=json.load(open('/tmp/ural-gap'+n+'-d8-15m-research.json'))['coordinates']
 for name,points in [('start',coords[:2]),('end',coords[-2:])]:
  p='/tmp/ural-gap'+n+'-'+name+'-15m-join-cop.json'
  with open(p,'x') as f:json.dump(points,f)
  h=hashlib.sha256(open(p,'rb').read()).hexdigest()
  try:
   a=screen(dem,sha,basins,p,h,2.,[2.],[50.,100.]);out='/tmp/ural-gap'+n+'-'+name+'-15m-join-cop-transect.json'
   with open(out,'x') as f:json.dump(a,f,sort_keys=True)
   print(json.dumps({'gap':n,'join':name,'line_sha':h,'route_m':a['route_length_wgs84_m_approx'],'stations':[{'station_m':s['station_wgs84_m'],'pairs':[(d['offset_wgs84_m'],[x['main_basins'] if x else None for x in d['samples']]) for d in s['directions'] if d['mode']=='2.0']} for s in a['stations']]}),flush=True)
  except Exception as e:print(json.dumps({'gap':n,'join':name,'error':str(e)}),flush=True)
