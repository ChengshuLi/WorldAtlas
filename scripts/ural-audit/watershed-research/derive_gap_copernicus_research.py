import sys,json,hashlib,time
sys.path.insert(0,'landed-1b494125')
from spring_connector_graph import basin_labels,graph_route
basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')]
cases=[('00','/tmp/ural-gap00-cop-30m-bilinear.tif','d661fee6218f9198f48cf3505a5303a4942cec602747fb82af3571c9548e4a86',[59.70,64.10,59.83,64.18],[59.747327720091995,64.13750025617915],[59.7871712860138,64.13925704344977]),('02','/tmp/ural-gap02-cop-30m-bilinear.tif','b35eff9756b70096e6ea2f1090249b6a60a31d4b7cc47dfd9d72eec646a0e169',[59.40,61.92,59.52,62.02],[59.45350269821396,62.00234249461163],[59.457461723858984,61.93782179462459])]
for name,p,h,bounds,start,end in cases:
 t0=time.monotonic()
 try:
  labels,t,geo,unknown=basin_labels(p,h,None,None,basins,bounds,[2120043720,3120001840,9999999999],30)
  result=graph_route(labels,t,geo,start,end);result.update({'name':name,'dem_sha256':h,'bounds':bounds,'unknown_valid_cells':unknown,'grid_shape':labels.shape,'root_order':[2120043720,3120001840,9999999999],'resolution_m':30,'status':'exploratory no selection','elapsed_seconds':time.monotonic()-t0,'caveats':['straight joins are not terrain validated','D8 and crosswalk are model-dependent','third label is deliberately unused sentinel','the local terrain extent and outlet labels can change the route']})
  dest='/tmp/ural-gap'+name+'-cop-d8-interface-research.json'
  with open(dest,'x') as f:json.dump(result,f,sort_keys=True,allow_nan=False)
  print(json.dumps({k:v for k,v in result.items() if k!='coordinates'}),flush=True)
 except Exception as e: print(json.dumps({'name':name,'error':str(e),'elapsed_seconds':time.monotonic()-t0}),flush=True)
