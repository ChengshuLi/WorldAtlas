import sys,json,hashlib
sys.path.insert(0,'landed-1b494125')
from smoothed_transect_screen import screen
basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')]
for n,dem,sha in [('00','/tmp/ural-gap00-12km-nearest.tif','3dbc4da15948791a70b78346eaba7174ccb464226bf9adf292184757f7c6af6b'),('02','/tmp/ural-gap02-16km-nearest.tif','dc04a55cdc1b742a21dfdb1f050f493c621a6ae0f3f66f7cdd0042c2cb893635')]:
 coords=json.load(open('/tmp/ural-gap'+n+'-d8-15m-research.json'))['coordinates']
 for name,points in [('start',coords[:2]),('end',coords[-2:])]:
  p='/tmp/ural-gap'+n+'-'+name+'-15m-join.json'
  with open(p,'x') as f:json.dump(points,f)
  h=hashlib.sha256(open(p,'rb').read()).hexdigest()
  try:
   a=screen(dem,sha,basins,p,h,2.,[2.],[50.,100.]);out='/tmp/ural-gap'+n+'-'+name+'-15m-join-transect.json'
   with open(out,'x') as f:json.dump(a,f,sort_keys=True)
   print(json.dumps({'gap':n,'join':name,'line_sha':h,'route_m':a['route_length_wgs84_m_approx'],'stations':[{'station_m':s['station_wgs84_m'],'pairs':[(d['offset_wgs84_m'],[x['main_basins'] if x else None for x in d['samples']]) for d in s['directions'] if d['mode']=='2.0']} for s in a['stations']]}),flush=True)
  except Exception as e:print(json.dumps({'gap':n,'join':name,'error':str(e)}),flush=True)
