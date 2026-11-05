from hydro_overlay import load_archive,overlay_graph
from hydro_graph import snap,route
from pyproj import Geod
from shapely import set_precision
from shapely.geometry import box
import json
archives=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd')];g=Geod(ellps='WGS84');dist=lambda a,b:g.inv(*a,*b)[2]
for name,bbox,st,en in [('gap00',[59.70,64.10,59.83,64.18],[59.747327720091995,64.13750025617915],[59.7871712860138,64.13925704344977]),('gap02',[59.40,61.92,59.52,62.02],[59.45350269821396,62.00234249461163],[59.457461723858984,61.93782179462459])]:
 f=[]
 for p,h in archives:f+=load_archive(p,h,bbox)
 grid=1e-12; fs=[(a,i,k,set_precision(geom,grid)) for a,i,k,geom in f];graph,diag=overlay_graph(fs,{2120043720},{3120001840},bbox,dist);ss,sd=snap(graph,st,1000,dist);ee,ed=snap(graph,en,1000,dist);line,length=route(graph,ss,ee,dist)
 print(json.dumps({'name':name,'precision_degrees':grid,'diagnostics':diag,'snapped_start':ss,'snap_start_wgs84_m':sd,'snapped_end':ee,'snap_end_wgs84_m':ed,'source_segment_sum_wgs84_m':length,'coordinates':line},sort_keys=True),flush=True)
