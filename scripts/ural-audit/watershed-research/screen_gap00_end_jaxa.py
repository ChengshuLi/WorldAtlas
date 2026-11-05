import sys,json
sys.path.insert(0,'landed-1b494125')
from smoothed_transect_screen import screen
basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')]
a=screen('/tmp/ural-gap00-jaxa-30m-masked.tif','49bbd6b4413d991ebb871b9fb77dd339f30f50c890499a555c5c346bd6f4b14a',basins,'/tmp/ural-gap00-end-15m-join.json','dad49556ea40ce2f3a0b9a8937258ef2cd3c1a21626365cc57907a671c1cea2f',2.,[2.],[50.,100.])
with open('/tmp/ural-gap00-end-15m-join-jaxa-transect.json','x') as f:json.dump(a,f,sort_keys=True)
print(json.dumps([{'station':s['station_wgs84_m'],'pairs':[(d['offset_wgs84_m'],[x['main_basins'] if x else None for x in d['samples']]) for d in s['directions'] if d['mode']=='2.0']} for s in a['stations']]))
