from hydro_overlay import load_archive,overlay_graph
from pyproj import Geod
from shapely import set_precision
archives=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd')]
g=Geod(ellps='WGS84');dist=lambda a,b:g.inv(*a,*b)[2]
for name,bbox in [('gap00',[59.70,64.10,59.83,64.18]),('gap02',[59.40,61.92,59.52,62.02])]:
 f=[]
 for p,h in archives:f+=load_archive(p,h,bbox)
 for precision in [1e-12,1e-11,1e-10,1e-9]:
  fs=[(a,i,k,set_precision(geom,precision)) for a,i,k,geom in f]
  try:
   graph,d=overlay_graph(fs,{2120043720},{3120001840},bbox,dist);print(name,precision,'SUCCESS',d,flush=True)
  except Exception as e:print(name,precision,'FAIL',str(e),getattr(e,'diagnostics',{}),flush=True)
